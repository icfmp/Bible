"""Actual installed Library study updates with retained annotations and offline restart."""
import argparse,faulthandler,gzip,hashlib,inspect,json,sys,traceback,urllib.request
from dataclasses import asdict
from pathlib import Path

def preservation(root):
    from bible.notes import NoteStore
    from bible.preferences import Preferences
    from bible.highlights import HighlightStore
    notes=NoteStore(root/'notes.sqlite3')
    return dict(notes=[asdict(n) for n in notes.all()],preferences=vars(Preferences(root/'reading-preferences.json').value),highlights=HighlightStore(root/'highlights.json').entries,
        modules={str(p.relative_to(root/'translations')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'translations').rglob('*') if p.is_file()})

def main():
    faulthandler.enable()
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--prepare',action='store_true');p.add_argument('--offline',action='store_true');p.add_argument('--require-packaged',action='store_true')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True);root=args.profile;marker=root/'.ready-study-profile'
    if args.prepare:
        assert not root.exists() or marker.exists(),'Unmarked profile'
        root.mkdir(parents=True,exist_ok=True);marker.write_text('Disposable installed study validation\n')
        from bible.library import Library,catalogue
        lib=Library(root/'translations')
        if 'KJV' not in lib.installed():lib.install(next(r for r in catalogue() if r.name=='KJV'))
        base='https://raw.githubusercontent.com/icfmp/Bible/1c82609a0947822908fdfab7d3b42f7b79146265/docs/evidence/'
        for name,path,digest in [('openbible-cross-references','client-feedback-20261027/fixtures/openbible-cross-references.sqlite3.gz','9b3659752c477e1e3be89ae55562734eae55328d2299eac4b7985b8825b9e993'),('openbible-topics','alpha-performance/fixtures/openbible-topics.sqlite3.gz','90db0daa43b1981a82d66481dc07211e395eba5ab56c15a8ee57cdb06d1ec209')]:
            target=root/'study-data'/(name+'.sqlite3');target.parent.mkdir(exist_ok=True)
            if not target.exists():
                url=base+path
                if name=='openbible-cross-references':url=url.replace('1c82609a0947822908fdfab7d3b42f7b79146265','fcfd908857c1c36e1ef0f371849e1a20a62fbeca')
                payload=gzip.decompress(urllib.request.urlopen(url,timeout=60).read(8*1024*1024));assert hashlib.sha256(payload).hexdigest()==digest
                target.write_bytes(payload)
        from bible.notes import NoteStore
        from bible.preferences import Preferences
        from bible.highlights import HighlightStore
        notes=NoteStore(root/'notes.sqlite3')
        if not notes.all():notes.save('Retain this study-update validation note',['preserve'],versification='KJV',start='John.3.16',end='John.3.16',origin_translation='KJV',origin_language='en')
        settings=Preferences(root/'reading-preferences.json');settings.value.size=24;settings.save()
        highlights=HighlightStore(root/'highlights.json')
        if not highlights.entries:highlights.set('KJV',['John.3.16'],'blue','KJV')
    assert marker.is_file()
    before=preservation(root)
    from bible.ui import Application,Window,Library,Gtk
    from tests.test_ui import spin
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    from bible.study_resources import REFERENCE_RESOURCE_ID,TOPIC_RESOURCE_ID
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    errors=[]
    def exception(kind,value,tb):
        errors.append(dict(type=kind.__name__,functions=[f.name for f in traceback.extract_tb(tb)]));traceback.print_exception(kind,value,tb)
    sys.excepthook=exception
    app=Application.get_default() or Application();app.register();w=Window(app,Library(root/'translations'));w.set_default_size(1100,850);w.present();spin()
    w.application_settings.set('automatic_catalogue_refresh',False)
    n=X11Input();n.activate(w);screen=Screen(n)
    report=dict(offline=args.offline,app_import=inspect.getfile(Window),ui_sha256=hashlib.sha256(Path(inspect.getfile(Window)).read_bytes()).hexdigest(),gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],renderer=type(w.get_renderer()).__name__,resources=[],exceptions=errors)
    if args.require_packaged:assert 'GL' in report['renderer']
    def save():(args.output/('study-offline.json' if args.offline else 'study-downloads.json')).write_text(json.dumps(report,indent=2)+'\n')
    try:
        d=w.open_library('study');spin(lambda:not d.busy and not d._building_rows,duration=.3,timeout=90)
        if not args.offline:
            n.click(d.catalogue_button);spin(lambda:not d.busy and not d._building_rows,duration=.3,timeout=90)
        for name in (REFERENCE_RESOURCE_ID,TOPIC_RESOURCE_ID):
            assert name in d.installed_ids(),'Previously installed data is not recognized'
            if not args.offline:assert name not in d._study_current,'Old fixture incorrectly reported current'
            index=next(i for i,r in enumerate(d.filtered_resources) if r.id==name)
            d.open_details(None,index);spin(duration=.3)
            if not args.offline:
                assert d.download_button.get_visible() and d.download_button.get_sensitive()
                task=d._task_id;clicked=[]
                signal=d.download_button.connect('clicked',lambda *_:clicked.append(True))
                ok,bounds=d.download_button.compute_bounds(d);picked=d.pick(bounds.origin.x+bounds.size.width/2,bounds.origin.y+bounds.size.height/2,Gtk.PickFlags.DEFAULT) if ok else None
                n.click(d.download_button);d.download_button.disconnect(signal)
                report['last_click']=dict(requested=name,selected=d.selected_resource().id,clicked=bool(clicked),task_before=task,task_after=d._task_id,picked=type(picked).__name__,toast=getattr(d,'_success_toast',None).get_title() if getattr(d,'_success_toast',None) else None)
                save()
                if task==d._task_id:screen.grab(args.output/'update-click-not-started.png')
                assert task!=d._task_id,report['last_click']
                spin(lambda:not d._transfer_busy,duration=.3,timeout=150)
                spin(lambda:name in d._study_current,duration=.3,timeout=90)
            store=d.study_resources.stores[name];metadata=store.metadata()
            assert metadata['source_date']=='2026-11-02',metadata['source_date']
            expected=d.study_resources.catalogue.load()[name]
            assert metadata['archive_sha256']==expected.sha256
            rows=store.query(['John.3.16'] if name==REFERENCE_RESOURCE_ID else 'forgiveness');assert rows
            record=dict(id=name,generation=metadata['source_date'],archive_sha256=metadata['archive_sha256'],relationships=metadata['relationships'],results=len(rows),current=d.study_resources.current(name))
            assert record['current'];report['resources'].append(record);save()
            with SystemStyleOverride() as style:
                for dark in (False,True):
                    style.set(dark=dark,high=False);spin(duration=.3)
                    screen.grab(args.output/(('offline-' if args.offline else 'updated-')+name+('-dark' if dark else '-light')+'.png'))
            d.back_to_list();spin(duration=.2)
        d.close();w.close();spin()
        after=preservation(root);report['preserved']={key:before[key]==after[key] for key in before}
        assert all(report['preserved'].values()),report['preserved'];assert not errors,errors
        report['completed']=True;save()
    finally:save();w.close();spin();n.close()

if __name__=='__main__':main()
