"""Isolated local SWORD literal phrase search; never mutate the GTK reader."""
import json
from pathlib import Path
import subprocess
import sys


def search(root,name,query):
    query=query.strip()
    if not query or len(query)>200 or any(ord(c)<32 for c in query):raise ValueError('Enter a phrase of 1–200 characters')
    result=subprocess.run([sys.executable,'-m','bible.text_search',str(root),name,query],
                          capture_output=True,text=True,timeout=30,check=True)
    if len(result.stdout)>128*1024:raise ValueError('Text search response too large')
    value=json.loads(result.stdout)
    if not isinstance(value.get('references'),list) or len(value['references'])>500:raise ValueError('Invalid text search')
    return value


def main():
    from .sword_provider import Reader
    root,name,query=sys.argv[1:]
    if Path(name).name!=name or name in ('.','..'):raise ValueError('Invalid module name')
    reader=Reader(Path(root)/name,name)
    results=reader.module.doSearch(query,-1,2)
    count=results.getCount();references=[]
    for index in range(min(count,500)):
        key=results.getElement(index)
        reference=reader.sword.VerseKey.castTo(key).getOSISRef()
        reader.key(reference);references.append(reference)
    print(json.dumps(dict(total=count,references=references,versification=reader.versification)))


if __name__=='__main__':main()
