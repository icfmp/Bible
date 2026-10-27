"""Fetch the requested metadata-returned research ZIP into a NEW private folder.

No API key, cookies, guessed suffix, agreement submission or installation.
Provider permission is not inferred from HTTP access. Raw material is private;
only counts/hashes/requirements may be published by the validation workflow.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

from .yves_source import read_edition


def fetch(url,limit):
    with urlopen(url,timeout=45) as response:
        before,after=urlsplit(url),urlsplit(response.geturl())
        if after.scheme!='https' or after.hostname!=before.hostname or after.username or after.password:
            raise ValueError('Unexpected fixture redirect')
        data=response.read(limit+1)
        if len(data)>limit:raise ValueError('Fixture size limit exceeded')
        expected=response.headers.get('Content-Length')
        if expected is not None and len(data)!=int(expected):raise ValueError('Truncated fixture')
        return data


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('output',type=Path);p.add_argument('--version',type=int,default=21)
    args=p.parse_args()
    if args.version<1:raise ValueError('Invalid edition')
    args.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    raw=fetch(f'https://nodejs.bible.com/api/bible/version/3.3?id={args.version}',4*1024*1024)
    metadata=json.loads(raw);edition=read_edition(metadata,args.version)
    (args.output/'metadata.json').write_bytes(raw)
    if edition.archive_url is None:raise ValueError('No offline package is returned')
    data=fetch(edition.archive_url,32*1024*1024)
    with (args.output/'source.zip').open('xb') as output:output.write(data)
    print(json.dumps(dict(version=edition.identifier,indexed_chapters=len(edition.chapters),
                          bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                          upstream_requirements=edition.metadata.get('offline'),
                          provider_approval_asserted=False,agreement_submitted=False)))


if __name__=='__main__':main()
