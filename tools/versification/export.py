"""Rebuild packaged tables using the pinned original JSword implementation.

Run: python3 tools/versification/export.py /tmp/bible-mappings --check
Java (including its compiler) is a development tool only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
REVISION = '6ebd10a005fa7761e611c048ececea1430e22546'
DEPENDENCIES = [
    ('org.apache.commons', 'commons-compress', '1.12'),
    ('com.chenlb.mmseg4j', 'mmseg4j-analysis', '1.8.6'),
    ('com.chenlb.mmseg4j', 'mmseg4j-core', '1.8.6'),
    ('com.chenlb.mmseg4j', 'mmseg4j-dic', '1.8.6'),
    ('org.jdom', 'jdom2', '2.0.6.1'),
    ('org.apache.lucene', 'lucene-analyzers', '3.6.2'),
    ('org.apache.lucene', 'lucene-core', '3.6.2'),
    ('org.slf4j', 'slf4j-api', '1.7.6'),
    ('org.slf4j', 'slf4j-simple', '1.7.6'),
    ('junit', 'junit', '4.13'),
    ('org.hamcrest', 'hamcrest-core', '1.3'),
]


def serialize(row):
    lines = ['{']
    for field, value in row.items():
        if isinstance(value, dict):
            lines.append('  '+json.dumps(field)+': {')
            lines.extend('    '+json.dumps(k)+': '+json.dumps(v, ensure_ascii=False)+
                         (',' if i+1 < len(value) else '') for i, (k, v) in enumerate(value.items()))
            lines.append('  },')
        else:
            lines.append('  '+json.dumps(field)+': '+json.dumps(value)+',')
    lines[-1] = lines[-1].rstrip(','); lines.append('}')
    return '\n'.join(lines)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('work_dir', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    work = args.work_dir.resolve(); work.mkdir(parents=True, exist_ok=True)
    archive = ROOT/'third_party/jsword'/f'jsword-{REVISION}.tar.gz'
    # Archive checksum is also stated in the adjacent provenance notice.
    notice = json.loads((ROOT/'third_party/jsword/provenance.json').read_text())
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == notice['archive_sha256']
    with tarfile.open(archive) as bundle:
        bundle.extractall(work, filter='data')
    source = work/f'jsword-{REVISION}'
    jars = work/'jars'; jars.mkdir(exist_ok=True)
    lock = json.loads((Path(__file__).with_name('dependencies.json')).read_text())
    for group, name, version in DEPENDENCIES:
        filename = f'{name}-{version}.jar'; jar = jars/filename
        if not jar.exists():
            url = f'https://repo.maven.apache.org/maven2/{group.replace(".", "/")}/{name}/{version}/{filename}'
            with urllib.request.urlopen(url, timeout=60) as response: jar.write_bytes(response.read())
        assert hashlib.sha256(jar.read_bytes()).hexdigest() == lock[filename], filename
    classes = work/'classes'; classes.mkdir(exist_ok=True)
    sources = list((source/'src/main/java').rglob('*.java'))+[Path(__file__).with_name('ExportMappings.java')]
    selected = ['FileVersificationMappingTest', 'VersificationToKJVMapperTest', 'VersificationsMapperTest']
    test_root = source/'src/test/java/org/crosswire/jsword/versification'
    sources += [test_root/(name+'.java') for name in selected+['TestData']]
    listing = work/'sources.txt'; listing.write_text('\n'.join(map(str, sources))+'\n')
    classpath = ':'.join(map(str, sorted(jars.glob('*.jar'))))
    subprocess.run(['java', 'com.sun.tools.javac.Main', '-encoding', 'UTF-8', '-nowarn',
                    '-cp', classpath, '-d', str(classes), '@'+str(listing)], check=True)
    classpath += ':'+str(classes)+':'+str(source/'src/main/resources')+':'+str(source/'src/test/resources')
    command = ['java', '-Duser.language=en', '-Duser.country=US', '-cp', classpath]
    subprocess.run(command+['org.junit.runner.JUnitCore']+
                   ['org.crosswire.jsword.versification.'+name for name in selected], check=True)
    systems = sorted(path.stem for path in (ROOT/'bible/versification_data').glob('*.json') if path.stem not in ('Original','YouVersion93','YouVersion131'))
    output = subprocess.check_output(command+['ExportMappings']+systems, text=True)
    for name, row in json.loads(output).items():
        path = ROOT/'bible/versification_data'/(name+'.json'); expected = serialize(row)
        if args.check: assert path.read_text() == expected, name
        else: path.write_text(expected)
    print(f'{len(systems)} tables reproduced byte for byte' if args.check else 'Tables regenerated')


if __name__ == '__main__': main()
