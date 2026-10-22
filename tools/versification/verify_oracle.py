"""Generate independent JSword vectors, or verify them with Bible's table bridge.

After export.py WORK --check:
  python3 -m tools.versification.verify_oracle generate WORK OUTPUT_DIRECTORY
  PYTHONPATH=. python3 -m tools.versification.verify_oracle verify OUTPUT_DIRECTORY/oracle.tsv REPORT.json
The verify phase needs SWORD; Java is used only by the generate phase.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from .export import ROOT, REVISION


def generate(work, output):
    output.mkdir(parents=True,exist_ok=True)
    systems={p.stem:json.loads(p.read_text()) for p in sorted((ROOT/'bible/versification_data').glob('*.json'))}
    from bible.reference_resolution import MAPPED_SYSTEMS
    requests=output/'requests.tsv'
    with requests.open('w') as stream:
        for source,row in systems.items():
            references=set(row.get('forward',{}))
            for book,chapters in row['canon'].items():
                for chapter,size in enumerate(chapters,1):
                    references.update((f'{book}.{chapter}.1',f'{book}.{chapter}.{size}'))
            for reference in sorted(references):
                if reference.endswith('.0'):continue
                for target in systems:
                    if source!=target and not {source,target}<=MAPPED_SYSTEMS:
                        stream.write('\t'.join((source,reference,target))+'\n')
    source=work/f'jsword-{REVISION}'
    classpath=':'.join(map(str,sorted((work/'jars').glob('*.jar'))))+':'+str(work/'classes')
    subprocess.run(['java','com.sun.tools.javac.Main','-cp',classpath,'-d',str(work/'classes'),
                    str(Path(__file__).with_name('ComposedOracle.java'))],check=True)
    classpath+=':'+str(source/'src/main/resources')
    with requests.open() as stdin,(output/'oracle.tsv').open('w') as stdout:
        subprocess.run(['java','-Xmx768m','-Duser.language=en','-Duser.country=US','-cp',classpath,
                        'ComposedOracle'],stdin=stdin,stdout=stdout,check=True)


def verify(path, output):
    from bible.versification_mapping import table,to_base,from_base
    start=time.monotonic();count=0;empty=0;unsupported=0;parts=0;differences=[]
    for line in path.open():
        source,reference,target,expected=line.rstrip('\n').split('\t')
        result=set()
        for qualified in to_base(reference,source):
            parts+=('!' in qualified or qualified.startswith('?'))
            result.update(from_base(qualified,target))
        unsupported+=expected=='UNSUPPORTED'
        expected=set(expected.split(',')) if expected and expected!='UNSUPPORTED' else set()
        if result!=expected and len(differences)<25:
            differences.append([source,reference,target,sorted(expected),sorted(result)])
        count+=1;empty+=not expected
    names=sorted(p.stem for p in (ROOT/'bible/versification_data').glob('*.json'))
    report=dict(rows=count,empty_results=empty,unsupported_qualified_ranges=unsupported,
                qualified_intermediates=parts,differences=differences,seconds=time.monotonic()-start,
                oracle_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                canon_match={system:table(system) is not None for system in names})
    output.write_text(json.dumps(report,indent=2)+'\n')
    assert not differences and all(report['canon_match'].values()),report
    print(json.dumps(report,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['generate','verify'])
    parser.add_argument('input',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args()
    (generate if args.action=='generate' else verify)(args.input.resolve(),args.output.resolve())


if __name__=='__main__':main()
