"""Offline read-only SWORD/Pango checks on an existing TEST profile.

Run from /tmp with /app/lib/bible-python before the checkout on PYTHONPATH for
--require-packaged. No downloads, installation, window/session or preference
writes are performed. Output distinguishes source from installed-package code.
"""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import re
import time
from unittest.mock import patch


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('profile');parser.add_argument('--resource',default='FreSegond1910')
    parser.add_argument('--references',nargs='+',default=['Gen.1.1','Mark.7.1','Luke.13.1'])
    parser.add_argument('--require-packaged',action='store_true');parser.add_argument('--output')
    args=parser.parse_args()
    from bible.book_stream import BookStream,LayoutContext
    from bible.paged_sources import BibleBookPages
    from bible.pagination import Anchor,Document,StyleSpan,heading_groups,paginate
    from bible.preferences import ReadingPreferences
    from bible.sword_provider import Reader
    from gi.repository import Pango
    imports={kind.__name__:inspect.getfile(kind) for kind in
             (BookStream,BibleBookPages,Document,ReadingPreferences,Reader)}
    packaged=all(Path(path).is_relative_to('/app/lib/bible-python/bible') for path in imports.values())
    if args.require_packaged:assert packaged,imports
    profile=Path(args.profile)
    source=BibleBookPages(Reader(profile/'translations'/args.resource,args.resource),None)
    preferences=ReadingPreferences()
    context=LayoutContext(96,'en');stream=BookStream(context,source,preferences)
    report={'code':'installed-package' if packaged else 'source', 'imports':imports,
            'resource':args.resource,'pango':Pango.version_string(),'network':'forbidden',
            'gui_validation':False,'books':[]}

    def settle():
        deadline=time.monotonic()+60;ticks=[]
        while time.monotonic()<deadline:
            ticks.append(time.monotonic());stream.poll()
            if stream.error:raise AssertionError(stream.error)
            if stream.cursor:
                return len(ticks),max((b-a for a,b in zip(ticks,ticks[1:])),default=0)
            time.sleep(.005)
        raise AssertionError('Book preparation timed out')

    with patch('socket.create_connection',side_effect=AssertionError('Offline check')), \
         patch('urllib.request.urlopen',side_effect=AssertionError('Offline check')):
        try:
            for reference in args.references:
                key=source.key(reference);anchor=Anchor(reference)
                preferences.size=14;started=time.monotonic()
                stream.configure(450,700,anchor,key);ticks,gap=settle()
                elapsed=time.monotonic()-started;plan=stream.plan(key);document=plan.document
                assert ''.join(document.text[p.start:p.end] for p in plan.pages)==document.text
                copy=document.copy(0,len(document.text))
                assert ''.join(document.copy(p.start,p.end) for p in plan.pages)==copy
                # Independent direct SWORD text for every actually present verse.
                for span in document.spans:
                    source.reader.module.setKey(source.reader.key(span.reference))
                    plain=source.reader.module.stripText()
                    if not isinstance(plain,str):plain=plain.c_str()
                    normalize=lambda text:re.sub(r'\s+','',text)
                    assert normalize(document.copy(span.body,span.end))==normalize(plain),span.reference
                groups=heading_groups(document);checked=0
                for first,last in groups:
                    styles=tuple(StyleSpan(s.kind,max(first,s.start)-first,min(last,s.end)-first)
                                 for s in document.styles if s.end>first and s.start<last)
                    probe=Document('group',document.text[first:last],(),styles)
                    if len(paginate(context,probe,preferences,450,700).pages)==1:
                        assert plan.containing(first)==plan.containing(last-1),(key,first,last)
                        checked+=1
                target=document.anchor(plan.pages[len(plan.pages)//2].start)
                preferences.size=19;started=time.monotonic()
                stream.configure(400,650,target,key);settle()
                assert stream.plan(key).document is document,'Typography re-read the source book'
                assert stream.anchor()==target
                reflow=time.monotonic()-started
                cached=stream.plan(key)
                stream.configure(400,650,target,key);settle()
                assert stream.plan(key) is cached
                report['books'].append(dict(key=key,pages=len(plan.pages),characters=len(document.text),
                    sha256=hashlib.sha256(copy.encode()).hexdigest(),source_verses=len(document.spans),
                    kept_heading_groups=checked,exact_partition=True,exact_source_words=True,
                    preparation_seconds=elapsed,reflow_seconds=reflow,document_reused=True,plan_reused=True,
                    poll_heartbeat_ticks=ticks,largest_poll_gap_seconds=gap))
            # Supersede active/prefetched layout work with a final known request.
            for size in (20,24,32,14):
                preferences.size=size;stream.configure(450,700,anchor,key)
            settle();assert stream.cursor.key==key and stream.anchor()==anchor
            assert len(stream.cache)<=3 and len(stream.documents)<=3 and len(stream.plans)<=3
            report['superseded_requests']=True
        finally:
            started=time.monotonic();stream.close()
            report['close_seconds']=time.monotonic()-started
            assert all(not thread.is_alive() for thread in stream.executor._threads)
            report['worker_joined']=True
    payload=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    if args.output:Path(args.output).write_text(payload)
    print(payload,end='')


if __name__=='__main__':main()
