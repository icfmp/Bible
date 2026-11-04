"""Reproduce the reference-only LSG bridge using locally authorized resources.

No text is written or downloaded. Input: converted YouVersion 93 resource root,
then independently installed CrossWire FreSegond1910 root. All unmatched verses
remain unmapped; equal numbering or an equal chapter size is never sufficient.
"""
import argparse,hashlib,json,re,unicodedata
from pathlib import Path
from bible.sword_provider import Reader
from bible.versification_mapping import to_base,verified_identity


def wording(value):
    value=''.join(c for c in unicodedata.normalize('NFD',value.casefold()) if not unicodedata.combining(c))
    return re.findall(r'[^\W_]+',value)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('control',type=Path);a=p.parse_args()
    pinned=json.loads((Path(__file__).resolve().parents[2]/'bible/versification_data/YouVersion93.json').read_text())
    receipt=json.loads((a.source/'.verified.json').read_text());assert receipt['archive_sha256']==pinned['provenance']['archive_sha256']
    files={str(f.relative_to(a.control)):hashlib.sha256(f.read_bytes()).hexdigest() for f in a.control.rglob('*') if f.is_file()}
    assert hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()==pinned['provenance']['alignment']['control_files_sha256']
    source=Reader(a.source,'youversion~YV93');control=Reader(a.control,'FreSegond1910')
    forward={};reverse={};compared=0
    for book in source.books:
        for chapter,numbers in book.chapters.items():
            origin=dict(source.chapter(f'{book.code}.{chapter}.{numbers[0]}').verses)
            try:other=dict(control.chapter(f'{book.code}.{chapter}.1').verses)
            except ValueError:continue
            compared+=len(origin)
            for ref,body in origin.items():
                if ref not in other or wording(body)!=wording(other[ref]):continue
                qualified=to_base(ref,'Segond')
                if not qualified:continue
                forward[ref]=qualified
                for target in qualified:reverse.setdefault(target,[]).append(ref)
    expected={f'{chapter}.{verse}' for chapter,ranges in pinned['verified_identity']['chapters'].items()
              for first,last in ranges for verse in range(first,last+1)}
    assert set(forward)==expected,'Pinned semantic bridge differs from the real source comparison'
    assert all(verified_identity(ref,pinned) for ref in forward)
    print(json.dumps(dict(compared=compared,verified=len(forward),unmapped=compared-len(forward),references_only=True)))


if __name__=='__main__':main()
