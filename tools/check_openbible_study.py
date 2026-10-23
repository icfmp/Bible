"""Real OpenBible/GTK acceptance; only disposable profiles, never client data."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import time
from gi.repository import GLib,Gtk
from bible.ui import Application,Window,Library
from bible.reference_data import ReferenceData,ARCHIVE_SHA256,ReferenceDataError
from bible.reference_targets import local_excerpt,source_references
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input


def wait(predicate,timeout=150):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        GLib.MainContext.default().iteration(False)
        if predicate():spin(duration=.2);return
        time.sleep(.005)
    raise AssertionError('GTK reference operation did not finish')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--download',action='store_true');parser.add_argument('--offline',action='store_true')
    parser.add_argument('--require-packaged',action='store_true');parser.add_argument('--captures',type=Path)
    args=parser.parse_args()
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    if args.offline:assert len(Path('/proc/net/route').read_text().splitlines())<=1
    app=Application();app.register();native=X11Input()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    window=Window(app,Library(args.profile/'translations'));window.set_default_size(1440,950);window.present()
    window.appearance.update('mode','day')
    report=dict(app_import=inspect.getfile(Window),network_disabled=args.offline,accessibility='Deferred; not tested')
    def capture(name):
        if args.captures:
            from PIL import ImageGrab
            args.captures.mkdir(parents=True,exist_ok=True);native.move_at(window.study.header,10,10);spin(duration=.2)
            ImageGrab.grab().save(args.captures/(name+'.png'))
    refs=window.study.references
    def ready():wait(lambda:not refs.pending,timeout=10)
    def select(resource,reference):
        assert window.active_tab.navigate(resource,reference)
        window.study_button.set_active(True);window.study.tools.set_visible_child_name('references');refs.refresh();ready()
    def walk(widget):
        if isinstance(widget,Gtk.Button) and getattr(widget,'_reference_item',None) and widget.get_mapped():yield widget
        child=widget.get_first_child()
        while child:yield from walk(child);child=child.get_next_sibling()
    def first_button():
        return next(button for button in walk(refs.list) if button._reference_item.relationship==refs.rows[0])
    try:
        select('FreSegond1910','John.1.5')
        original_installed=window.library.installed()
        if args.download:
            assert not args.offline
            dialog=window.open_library('study');spin(duration=.3)
            assert not dialog._catalogue_requested
            assert 'creativecommons.org/licenses/by/4.0/' in dialog.selected_resource().conditions
            dialog.open_details(None,0);spin();started=time.monotonic()
            native.click(dialog.download_button);wait(lambda:not dialog.busy)
            assert dialog._phase!='error',dialog.status.get_text()
            report['native_library_download_seconds']=round(time.monotonic()-started,3)
            dialog.close();spin()
            # Xvfb has no WM to reactivate the transient parent. Supply only
            # that handoff; all actions below still use actual pointer/keys.
            native.activate(window);refs.invalidate();ready()
        metadata=refs.data.metadata();assert metadata['archive_sha256']==ARCHIVE_SHA256
        assert metadata['relationships']==344799
        assert window.library.installed()==original_installed
        report['dataset']=metadata
        assert len(refs.rows)>5 and refs.model.get_n_items()==5
        tab=window.active_tab;before=(tab.state.reference,list(tab.state.history),window.view.get_n_pages())
        first=refs.rows[0];expected=local_excerpt(tab.reader,first.start,first.end)
        native.click(first_button());spin();preview=window.reference_preview
        assert preview.popover and preview.popover.get_visible()
        assert preview.body.get_buffer().props.text==expected.text
        assert (tab.state.reference,tab.state.history,window.view.get_n_pages())==before
        capture('preview');native.key('Escape');assert preview.popover is None
        assert first_button().has_focus(),window.get_focus()
        # Keyboard activation and the normal outside-click dismissal route.
        first_button().grab_focus();native.key('Return');assert preview.popover
        native.click(window.study.header);assert preview.popover is None
        first_button().grab_focus();native.key('space');assert preview.popover
        native.key('Escape');assert preview.popover is None
        assert first_button().has_focus(),window.get_focus()
        assert (tab.state.reference,tab.state.history,window.view.get_n_pages())==before
        native.click(first_button());native.click(preview.open_new);spin()
        assert window.view.get_n_pages()==before[2]+1
        assert window.active_tab.state.resource=='FreSegond1910' and window.active_tab.state.reference==expected.start
        assert (tab.state.reference,tab.state.history)==(before[0],before[1])
        window.view.set_selected_page(window.view.get_page(tab));window.study_button.set_active(True);ready()
        native.click(first_button());native.click(preview.open_here);spin();ready()
        assert tab.state.reference==expected.start and len(tab.state.history)==len(before[1])+1
        report['native_preview_navigation']=dict(preview_keeps_passage_history=True,keyboard_and_escape=True,
            outside_dismissal=True,space_activation=True,focus_return=True,new_tab_preserves_original=True,current_tab_explicit=True)
        # Deliberate passage range: actual directed rows and documented aggregation.
        select('FreSegond1910','John.1.5');buffer=tab.text.get_buffer()
        buffer.select_range(buffer.get_iter_at_offset(tab._marker_ends['John.1.5']),
                            buffer.get_iter_at_offset(tab._verse_ranges['John.1.7'][1]))
        wait(lambda:not refs.pending and refs.context[2:]==('John.1.5','John.1.7'),timeout=10)
        assert refs.rows==refs.data.query(source_references(tab.reader,'John.1.5','John.1.7'))
        assert len({(r.start,r.end) for r in refs.rows})==len(refs.rows)
        report['selected_range']=dict(source_verses=3,destinations=len(refs.rows),deduplicated=True)
        buffer.place_cursor(buffer.get_start_iter());spin()
        # Superseded async results cannot replace the last requested context.
        for name,reference in [('KJV','Gen.1.1'),('FreSegond1910','John.3.16'),('KJV','John.1.5'),('FreSegond1910','Ps.3.2')]:
            tab.navigate(name,reference)
        ready();assert refs.context[0]=='FreSegond1910' and refs.context[2:]==('Ps.3.2','Ps.3.2')
        assert refs.rows==refs.data.query(['Ps.3.1'])
        checks=[]
        for resource,reference in [('KJV','Gen.1.1'),('FreSegond1910','Ps.3.2'),('KJV','John.1.5'),
                                   ('KJV','3John.1.14'),('FreSegond1910','3John.1.15')]:
            select(resource,reference);origins=source_references(tab.reader,reference,reference)
            assert refs.rows==refs.data.query(origins)
            checked=0
            for row in refs.rows[:3]:
                excerpt=local_excerpt(tab.reader,row.start,row.end,limit=1)
                for ref,text in excerpt.verses:
                    tab.reader.module.setKey(tab.reader.key(ref));direct=tab.reader.module.stripText()
                    if not isinstance(direct,str):direct=direct.c_str()
                    assert text==direct
                    checked+=1
            checks.append(dict(resource=resource,reference=reference,source_addresses=origins,
                               relationships=len(refs.rows),exact_excerpts_checked=checked))
        report['real_numbering_and_source_text']=checks
        before_hash=hashlib.sha256(refs.data.path.read_bytes()).hexdigest()
        bad=args.profile/'invalid-reference-update.zip';bad.write_bytes(b'CORRUPT UPDATE VALIDATION ONLY')
        try:refs.data.install_archive(bad);raise AssertionError('Corrupt update accepted')
        except ReferenceDataError:pass
        assert hashlib.sha256(refs.data.path.read_bytes()).hexdigest()==before_hash
        bad.unlink();report['failed_update_retains_working_index']=True
        select('KJV','Gen.1.1');native.click(refs.view_all);spin()
        assert refs.model.get_n_items()==len(refs.rows)
        assert len(refs.rows)>50
        reference,history=tab.state.reference,list(tab.state.history)
        native.wheel(refs.list.get_parent(),4);spin()
        assert (tab.state.reference,tab.state.history)==(reference,history)
        capture('references-wide')
        if hasattr(refs,'show_initial'):
            native.click(refs.return_results);spin()
            assert refs.model.get_n_items()==5 and not refs.return_results.get_visible()
            assert (tab.state.reference,tab.state.history)==(reference,history)
            assert str(len(refs.rows)) in refs.view_all.get_label()
            report['expanded_return_and_exact_total']=True
        window.set_default_size(360,800)
        spin(lambda:window.split.get_collapsed() and window.get_width()<=380 and not tab._restoring_scroll,duration=.3)
        if not window.split.get_show_sidebar():native.key('F9')
        wait(lambda:window.split.get_show_sidebar() and window.study.header.get_mapped(),timeout=10)
        assert window.study.get_width()<=window.get_width();capture('references-narrow')
        window.set_default_size(1440,950);spin(lambda:not window.split.get_collapsed(),duration=.3)
        window.study_button.set_active(True);window.appearance.update('mode','night');spin();capture('references-dark')
        from tests.test_appearance import SystemStyleOverride
        with SystemStyleOverride() as system:
            system.set(dark=False,high=True);window.appearance.update('mode','day');spin()
            assert window.reading_style.manager.get_high_contrast()
            assert any(walk(refs.list));capture('references-high-contrast-emulated')
        report['narrow_long_list_theme']=True
        report['emulated_high_contrast']=True
        window.close()
        restored=Window(app,Library(args.profile/'translations'));restored.present()
        try:
            wait(lambda:not restored.study.references.pending)
            assert restored.study.tool=='references'
            assert restored.study.references.data.metadata()['archive_sha256']==ARCHIVE_SHA256
            assert restored.study.references.rows
        finally:restored.close()
        report['restart_with_installed_relationships']=True;report['status']='PASS'
    finally:
        if not window.closed:window.close()
        native.close()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
