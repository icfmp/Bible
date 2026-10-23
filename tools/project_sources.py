"""Archive the exact project's build sources without historical GUI evidence.

Application/build inputs, original icons, third-party sources, notices, tests and
scripts remain in their original paths. Published historical source archives are
never rewritten. Full historical visual evidence remains in the Git repository.
"""
import argparse
from pathlib import Path
import re
import subprocess

EVIDENCE_PATHS=('docs/captures','docs/evidence','wiki/images')


def create_project_archive(destination,source):
    if not re.fullmatch(r'[0-9a-f]{40}',source):raise ValueError('Expected a full source commit')
    destination=Path(destination)
    subprocess.run(['git','archive','--format=tar','-o',str(destination),source,'.',
                    *(':(exclude)'+path for path in EVIDENCE_PATHS)],check=True)
    return destination


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source');parser.add_argument('destination',type=Path)
    args=parser.parse_args();create_project_archive(args.destination,args.source)


if __name__=='__main__':main()
