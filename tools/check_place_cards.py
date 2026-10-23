"""Actual downloaded geography and native inputs; disposable profile only."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import time
from gi.repository import Gtk,GLib
from bible.ui import Application,Window,Library
from bible.place_data import FILES,SOURCE_COMMIT,ReferenceDataError
from bible.reference_targets import local_excerpt,source_references
from bible.i18n import tr
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input


def wait(predicate,timeout=150):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        GLib.MainContext.default().iteration(False)
        if predicate():spin(duration=.2);return
        time.sleep(.005)
    raise AssertionError('Place operation did not settle')


def walk(widget):
    yield widget
    child=widget.get_first_child()
    while child:yield from walk(child);child=child.get_next_sibling()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--inputs',required=True,type=Path)
    parser.add_argument('--download',action='store_true');parser.add_argument('--offline',action='store_true')
    parser.add_argument('--require-packaged',action='store_true');parser.add_argument('--captures',type=Path)
    args=parser.parse_args();expected=json.loads((args.inputs/'expected-cases.json').read_text())
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    if args.offline:assert len(Path('/proc/net/route').read_text().splitlines())<=1
    app=Application();app.register();native=X11Input();Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    w=Window(app,Library(args.profile/'translations'));w.set_default_size(1440,950);w.present()
    report=dict(app_import=inspect.getfile(Window),network_disabled=args.offline,accessibility='Deferred; not tested')
    original_resources=w.library.installed();original_notes=w.notes_store.all()
    def capture(name):
        if args.captures:
            from PIL import ImageGrab
            args.captures.mkdir(parents=True,exist_ok=True);native.move_at(w,2,2);spin()
            ImageGrab.grab().save(args.captures/(name+'.png'))
    def settled():spin(lambda:not w.active_tab._restoring_scroll,duration=.3)
    def open_dialog(resource,reference):
        w.active_tab.navigate(resource,reference);w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes');settled()
        native.click(w.study.places_button);dialog=w.place_dialog
        wait(lambda:not dialog.pending,timeout=10);return dialog
    def place_button(dialog,name):
        return next(b for b in walk(dialog.list) if isinstance(b,Gtk.Button) and getattr(b,'_place',{}).get('name')==name and b.get_mapped())
    def open_card(dialog,name):
        native.click(place_button(dialog,name));wait(lambda:dialog.map_widget is None or bool(dialog.map_widget.lines),timeout=10)
        spin(duration=.3);place=dialog.current_place;proof=expected.get(name)
        if proof:
            assert place['id']==proof['id']
            assert [[p['longitude'],p['latitude']] for p in place['candidates'] if p['longitude'] is not None]==proof['coordinates']
            assert set(place['references'])==set(proof['references'])
        return place
    def reveal(dialog,widget):
        for _ in range(30):
            found,bounds=widget.compute_bounds(dialog.card_scroll)
            if found and 0<=bounds.origin.y and bounds.origin.y+bounds.size.height<=dialog.card_scroll.get_height():return
            native.move_at(dialog.card_scroll,3,dialog.card_scroll.get_height()/2)
            button=5 if not found or bounds.origin.y>0 else 4
            for _ in range(3):native.xtest.XTestFakeButtonEvent(native.display,button,True,0);native.xtest.XTestFakeButtonEvent(native.display,button,False,0)
            native.x11.XFlush(native.display);spin(duration=.15)
        raise AssertionError('Native card scrolling did not reveal reference')
    def reference_button(dialog,reference):
        return next(b for b in walk(dialog.references) if isinstance(b,Gtk.Button) and getattr(b,'_reference',None)==reference)
    def close(dialog):
        button=next(b for b in walk(dialog) if isinstance(b,Gtk.Button) and b.get_tooltip_text()==tr('Close') and b.get_mapped())
        native.click(button);wait(lambda:dialog.closed,timeout=10)
    try:
        w.appearance.update('mode','day');dialog=open_dialog('KJV','Luke.24.13')
        if args.download:
            assert not args.offline and dialog.download.get_visible()
            native.click(dialog.download);library=w.catalogue_window;spin(lambda:library.download_button.get_mapped())
            assert not library._catalogue_requested
            assert 'opendatacommons.org' in library.metadata.get_text();assert 'naturalearthdata.com' in library.metadata.get_text()
            start=time.monotonic();native.click(library.download_button);wait(lambda:not library.busy)
            assert library._phase!='error',library.status.get_text()
            report['native_library_download_seconds']=round(time.monotonic()-start,3)
            library.close();native.activate(w);dialog.refresh();wait(lambda:not dialog.pending,timeout=10)
        metadata=dialog.data.metadata();assert metadata['source_commit']==SOURCE_COMMIT
        assert (metadata['places'],metadata['modern_locations'],metadata['bibliographic_sources'])==(1342,1596,442)
        report['dataset']=metadata;assert w.library.installed()==original_resources
        assert {p['name'] for p in dialog.rows}=={'Emmaus','Jerusalem'};capture('passage-places')
        place=open_card(dialog,'Emmaus');assert place['status']=='disputed' and len(place['candidates'])==6
        capture('emmaus-six-candidates')
        tab=w.active_tab;before=(tab.state.reference,list(tab.state.history),w.view.get_n_pages())
        button=reference_button(dialog,'Luke.24.28');reveal(dialog,button);native.click(button);spin()
        assert w.reference_preview.body.get_buffer().props.text==local_excerpt(tab.reader,'Luke.24.28').text
        assert (tab.state.reference,tab.state.history,w.view.get_n_pages())==before
        native.key('Escape');assert w.reference_preview.popover is None
        button.grab_focus();native.key('Return');assert w.reference_preview.popover
        native.click(w.reference_preview.open_new);wait(lambda:dialog.closed,timeout=10);settled()
        assert w.active_tab.state.resource=='KJV' and w.active_tab.state.reference=='Luke.24.28'
        assert w.view.get_n_pages()==before[2]+1 and tab.state.reference==before[0] and tab.state.history==before[1]
        report['preview_navigation']=dict(native_pointer_and_keyboard=True,escape=True,exact_installed_text=True,
            preview_preserves_history=True,explicit_new_tab_keeps_original=True)
        w.view.set_selected_page(w.view.get_page(tab));dialog=open_dialog('KJV','Luke.24.13')
        place=open_card(dialog,'Jerusalem');assert place['status']=='known' and len(expected['Jerusalem']['coordinates'])==1
        capture('jerusalem-known');target=place['references'][0]
        button=reference_button(dialog,target);reveal(dialog,button);native.click(button);spin();native.click(w.reference_preview.open_here)
        wait(lambda:dialog.closed,timeout=10);settled();assert w.active_tab.state.reference==target
        report['preview_navigation']['explicit_current_tab']=True
        dialog=open_dialog('KJV','Gen.4.16');place=open_card(dialog,'Nod')
        assert place['status']=='unknown' and dialog.map_widget is None
        assert not any(p['longitude'] is not None for p in place['candidates']);capture('nod-unknown');close(dialog)
        dialog=open_dialog('FreSegond1910','Ps.42.7')
        assert source_references(w.active_tab.reader,'Ps.42.7','Ps.42.7')==['Ps.42.6']
        place=open_card(dialog,'Mount Mizar');button=reference_button(dialog,'Ps.42.6');reveal(dialog,button);native.click(button);spin()
        assert w.reference_preview.target==('FreSegond1910','Ps.42.7')
        assert w.reference_preview.body.get_buffer().props.text==local_excerpt(w.active_tab.reader,'Ps.42.6').text
        capture('french-renumbered-psalm');native.key('Escape');close(dialog)
        report['real_place_evidence']=dict(jerusalem='known, one modern point',emmaus='disputed, six supplied candidates',nod='unknown, no invented coordinates',
            coordinates_equal_pinned_source=True,french_psalm_source='Ps.42.6',french_psalm_target='Ps.42.7')
        before_hash=hashlib.sha256(dialog.data.path.read_bytes()).hexdigest()
        invalid=args.profile/'invalid-place-update';invalid.write_bytes(b'INVALID UPDATE VALIDATION ONLY')
        files={'ancient':invalid,'modern':args.inputs/'data-modern.jsonl','sources':args.inputs/'data-source.jsonl',
               'license':args.inputs/'license.txt','coastline':args.inputs/'ne_50m_coastline.geojson'}
        try:dialog.data.install_files(files);raise AssertionError('Invalid update accepted')
        except ReferenceDataError:pass
        invalid.unlink();assert hashlib.sha256(dialog.data.path.read_bytes()).hexdigest()==before_hash
        report['failed_update_preserves_index']=True
        dialog=open_dialog('KJV','Luke.24.13');open_card(dialog,'Emmaus')
        from tests.test_appearance import SystemStyleOverride
        with SystemStyleOverride() as theme:
            for mode,high in [('day',False),('night',False),('day',True)]:
                theme.set(dark=mode=='night',high=high);w.appearance.update('mode',mode);spin();capture('map-'+mode+('-contrast-emulated' if high else ''))
        w.set_default_size(360,800);spin(lambda:w.get_width()<=380,duration=.3);capture('place-card-narrow');close(dialog)
        assert w.notes_store.all()==original_notes and w.library.installed()==original_resources
        w.close();restored=Window(app,Library(args.profile/'translations'));restored.present()
        try:
            restored.active_tab.navigate('KJV','Luke.24.13');spin(lambda:not restored.active_tab._restoring_scroll,duration=.3)
            reopened=restored.open_places();wait(lambda:not reopened.pending,timeout=10)
            assert {p['name'] for p in reopened.rows}=={'Emmaus','Jerusalem'}
            assert reopened.data.has_map() and restored.notes_store.all()==original_notes
            reopened.close();spin()
        finally:restored.close()
        report.update(narrow_and_themes=True,offline_restart_with_local_map=True,notes_and_bible_resources_preserved=True,status='PASS')
    finally:
        if getattr(w,'place_dialog',None):w.place_dialog.close();spin()
        if not w.closed:w.close()
        native.close()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
