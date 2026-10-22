import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

root = Path('/tmp/bible-57')
source = root / 'jsword-6ebd10a005fa7761e611c048ececea1430e22546'
jars = root / 'jars'; jars.mkdir(exist_ok=True)
dependencies = [
    ('org.apache.commons','commons-compress','1.12'),
    ('com.chenlb.mmseg4j','mmseg4j-analysis','1.8.6'),
    ('com.chenlb.mmseg4j','mmseg4j-core','1.8.6'),
    ('com.chenlb.mmseg4j','mmseg4j-dic','1.8.6'),
    ('org.jdom','jdom2','2.0.6.1'),
    ('org.apache.lucene','lucene-analyzers','3.6.2'),
    ('org.apache.lucene','lucene-core','3.6.2'),
    ('org.slf4j','slf4j-api','1.7.6'),
    ('org.slf4j','slf4j-simple','1.7.6'),
    ('junit','junit','4.13'),
    ('org.hamcrest','hamcrest-core','1.3'),
]
def download(entry):
    group, name, version = entry
    filename = f'{name}-{version}.jar'
    path = jars / filename
    url = f'https://repo.maven.apache.org/maven2/{group.replace(".","/")}/{name}/{version}/{filename}'
    if not path.exists():
        with urllib.request.urlopen(url, timeout=30) as response: path.write_bytes(response.read())
    return filename, hashlib.sha256(path.read_bytes()).hexdigest()
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    hashes = dict(pool.map(download, dependencies))
(root / 'jars-sha256.json').write_text(json.dumps(hashes, indent=2) + '\n')
classes = root / 'classes'; classes.mkdir(exist_ok=True)
files = list((source / 'src/main/java').rglob('*.java'))
tests = source / 'src/test/java/org/crosswire/jsword/versification'
selected = ['FileVersificationMappingTest','VersificationToKJVMapperTest','VersificationsMapperTest']
files += [tests / (name + '.java') for name in selected]
files += [tests / 'TestData.java']
listing = root / 'sources.txt'
listing.write_text('\n'.join(map(str,files)) + '\n')
classpath = ':'.join(map(str,sorted(jars.glob('*.jar'))))
subprocess.run(['java','com.sun.tools.javac.Main','-encoding','UTF-8','-nowarn',
                '-cp',classpath,'-d',str(classes),'@'+str(listing)], check=True)
classpath += ':' + str(classes) + ':' + str(source / 'src/main/resources') + ':' + str(source / 'src/test/resources')
subprocess.run(['java','-Duser.language=en','-Duser.country=US','-cp',classpath,
               'org.junit.runner.JUnitCore',
               *['org.crosswire.jsword.versification.'+name for name in selected]], check=True)
