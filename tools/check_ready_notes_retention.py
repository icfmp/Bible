"""Installed-Flatpak evidence for shared linked notes and narrow native editing.

Uses only an explicitly marked developer profile; no client profile reset.
"""
import argparse
from dataclasses import asdict
import hashlib
import inspect
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('output',type=Path);p.add_argument('--require-packaged',action='store_true');a=p.parse_args()
    assert (a.profile/'.ready-reading-notes-profile').is_file();a.output.mkdir(parents=True,exist_ok=True)
    from bible.ui import Application,Window,Library,Gtk
    from bible.notes import NoteStore,PassageLink
    from bible.highlights import HighlightStore
    from bible import personal_backup
    from tests.test_ui import spin
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    app=Application();app.register();w=Window(app,Library(a.profile/'translations'));w.set_default_size(1200,860);w.present();n=X11Input();screen=Screen(n);n.activate(w)
    report=dict(app_import=inspect.getfile(Window),renderer=type(w.get_renderer()).__name__,checks={})
    settings=asdict(w.preferences.value);gtk=Gtk.Settings.get_default();font=gtk.props.gtk_font_name;retained=w.notes_store.all()
    def settle():spin(lambda:not w.active_tab._restoring_scroll,duration=.3,timeout=40)
    def tree():return {str(p.relative_to(w.library.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in w.library.root.rglob('*') if p.is_file()}
    def shot(name):n.move_at(w,2,2);spin(duration=.2);screen.grab(a.output/(name+'.png'))
    before=tree()
    try:
        if a.require_packaged:assert report['app_import'].startswith('/app/') and 'GL' in report['renderer']
        w.active_tab.navigate('youversion~YV21','Mark.11.29');settle();system=w.active_tab.reader.versification
        note=w.notes_store.save('**Developer validation**. Jean 3:16.\n- Existing item',('Linked-note validation',),versification=system,start='Mark.11.29',end='Mark.11.30',origin_translation='youversion~YV21',origin_language='fr')
        editor=w.edit_note(note=note);spin();n.activate(editor)
        editor.links.entry.set_text('Jean 3:16');assert editor.links.add()
        editor.links.entry.set_text('John 3:16');assert not editor.links.add();editor.links.entry.set_text('')
        assert editor.save();note=w.notes_store.get(note.id);assert len(note.links)==1
        # Use the same UUID across real providers, then cover overlapping links.
        note=w.notes_store.save(note.body,note.labels,existing=note,links=(*note.links,PassageLink(system,'John.3.15','John.3.17')))
        for edition in ('youversion~YV21','KJV','FreSegond1910'):
            assert w.active_tab.navigate(edition,'John.3.16');settle();w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes');w.study.notes.refresh(force=True);spin()
            assert [v.id for v in w.study.notes.rows].count(note.id)==1,edition
            markers=[b for b in w.active_tab.text._inline_buttons if b._marker_kind=='note' and b._marker_reference=='John.3.16']
            assert len(markers)==1,(edition,len(markers))
            shot('linked-note-'+edition.replace('~','-'))
        report['checks']['same_uuid_across_real_providers_and_overlapping_links']=True
        width=w.study_settings.width;reference=w.active_tab.state.reference
        found,bounds=w.study_divider.compute_bounds(w);assert found and w.study_divider.get_mapped()
        x,y=bounds.origin.x+bounds.size.width/2,bounds.origin.y+100
        n.move_at(w,x,y);n.xtest.XTestFakeButtonEvent(n.display,1,True,0);n.x11.XFlush(n.display);spin()
        for index in range(1,9):n.move_at(w,x-8*index,y);spin(duration=.04)
        n.xtest.XTestFakeButtonEvent(n.display,1,False,0);n.x11.XFlush(n.display);settle()
        assert w.study_settings.width!=width and w.active_tab.state.reference==reference
        report['checks']['native_study_divider_drag']=True;shot('study-divider-after-drag')
        w.study_settings.width=width;w.study_divider.apply();w.study_settings.save()
        w.study_button.set_active(False)
        w.active_tab.navigate('KJV','Mark.11.1');settle();w.active_tab.state.comparison='youversion~YV21';w.sync_comparison();settle()
        spin(lambda:bool(w.active_tab.comparison_text._inline_buttons),duration=.3,timeout=30)
        button=next(b for b in w.active_tab.comparison_text._inline_buttons if b._marker_kind=='translation-note')
        n.click(button);spin();assert button._source_note_popover and button._source_note_popover.get_visible()
        assert button._source_note_popover.get_parent() is w.active_tab.comparison_overlay
        shot('source-note-secondary-pane');n.key('Escape');w.end_comparison();settle()
        report['checks']['secondary_pane_source_note_native_popup']=True
        editor=w.edit_note(note=note);spin();n.activate(editor)
        c=editor.body.citations[0];rect=editor.body.get_iter_location(editor.body.get_buffer().get_iter_at_offset(c.begin+1))
        x,y=editor.body.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,rect.x,rect.y)
        control=n.x11.XKeysymToKeycode(n.display,n.x11.XStringToKeysym(b'Control_L'))
        n.xtest.XTestFakeKeyEvent(n.display,control,True,0)
        try:n.click_at(editor.body,x+1,y+rect.height/2)
        finally:n.xtest.XTestFakeKeyEvent(n.display,control,False,0);n.x11.XFlush(n.display)
        assert w.reference_preview.popover and w.reference_preview.popover.get_visible();n.key('Escape')
        assert not editor.dirty;report['checks']['native_ctrl_click_direct_editor_citation']=True
        for mode in ('day','night'):
            w.appearance.update('mode',mode);editor.set_default_size(360,700);gtk.props.gtk_font_name='Sans 16';spin(duration=.6)
            assert editor.get_width()<=400,(editor.get_width(),editor.get_height())
            shot('quick-note-360-large-text-'+mode)
        gtk.props.gtk_font_name=font
        for link in tuple(editor.links.values):editor.links.remove(link)
        assert editor.save();unlinked=w.notes_store.get(note.id)
        assert unlinked.id==note.id and unlinked.start==note.start and unlinked.body==note.body and not unlinked.links
        report['checks']['unlink_preserves_primary_and_body']=True
        # Retain one relationship for the new backup and real window restart.
        note=w.notes_store.save(unlinked.body,unlinked.labels,existing=unlinked,links=note.links[:1]);w.notes_changed()
        backup=a.output/'combined.json';personal_backup.export(w.notes_store,w.highlights,backup)
        restored=NoteStore(a.output/'restore.sqlite3');marks=HighlightStore(a.output/'restore-highlights.json')
        try:personal_backup.restore(restored,marks,backup);assert restored.get(note.id)==note
        finally:restored.close();backup.unlink()
        legacy=asdict(note);legacy.pop('links');legacy['id']='9a8776de-3f3c-4d85-ae07-2d74f1ef0d24'
        backup.write_text(json.dumps(dict(format='bible-notes',version=1,notes=[legacy])))
        old=NoteStore(a.output/'legacy-restore.sqlite3')
        try:old.restore(backup);assert old.get(legacy['id']).body==note.body and not old.get(legacy['id']).links
        finally:old.close();backup.unlink()
        report['checks']['new_links_backup_and_legacy_import']=True
        assert tree()==before and all(w.notes_store.get(v.id)==v for v in retained)
        for k,v in settings.items():setattr(w.preferences.value,k,v)
        w.preferences.save();w.close()
        reopened=Window(app,Library(a.profile/'translations'));reopened.present();spin()
        try:assert reopened.notes_store.get(note.id)==note
        finally:reopened.close()
        report['checks'].update(real_window_reopen=True,retained_notes_and_translations_preserved=True);report['complete']=True
    finally:
        gtk.props.gtk_font_name=font
        if not w.closed:
            if w.note_editor and not w.note_editor.closed:w.note_editor._discard=True;w.note_editor.close()
            for k,v in settings.items():setattr(w.preferences.value,k,v)
            w.preferences.save();w.close()
        n.close();(a.output/'retention.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
