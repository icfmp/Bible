"""Real X11 workspace editing, read-only failure, guarding and deletion checks."""
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from unittest.mock import patch
from bible.ui import Application,Window,Library,Gtk,GLib,Adw
from bible.i18n import tr
from tools.check_alpha_ui import X11Input


def spin(until=lambda:True,duration=.15):
    minimum=time.monotonic()+duration;deadline=time.monotonic()+15
    while time.monotonic()<deadline:
        GLib.MainContext.default().iteration(False)
        if time.monotonic()>=minimum and until():return
        time.sleep(.003)
    raise AssertionError('Native annotation workspace did not settle')


def descendants(widget):
    yield widget
    child=widget.get_first_child()
    while child:
        yield from descendants(child);child=child.get_next_sibling()


def digest_tree(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def main():
    with tempfile.TemporaryDirectory(prefix='bible-workspace-') as directory:
        root=Path(directory)
        if os.environ.get('BIBLE_WORKSPACE_PROFILE'):shutil.copytree(os.environ['BIBLE_WORKSPACE_PROFILE'],root,dirs_exist_ok=True)
        else:
            from tests.test_ui import installed_fixture
            installed_fixture(root,'Test')
        resources=digest_tree(root/'translations')
        app=Application.get_default() or Application();app.register();w=Window(app,Library(root/'translations'));w.set_default_size(1280,800);w.present();spin()
        native=X11Input();screens=os.environ.get('BIBLE_WORKSPACE_CAPTURE_DIR')
        def shot(name):
            if screens:
                from PIL import ImageGrab
                Path(screens).mkdir(parents=True,exist_ok=True);spin();ImageGrab.grab().save(Path(screens)/('native-workspace-'+name+'.png'))
        def choose(widget,last):
            native.click(widget);native.key('End' if last else 'Home');native.key('Return');spin()
        def chord(modifier,key):
            code=native.x11.XKeysymToKeycode(native.display,native.x11.XStringToKeysym(modifier.encode()))
            native.xtest.XTestFakeKeyEvent(native.display,code,True,0);native.key(key);native.xtest.XTestFakeKeyEvent(native.display,code,False,0);native.x11.XFlush(native.display);spin()
        try:
            tab=w.active_tab;assert tab.reader
            start=tab.state.reference
            note=w.notes_store.save('Native editing test **note**, see '+start+'.', ['Native'],versification=tab.reader.versification,start=start,end=start,origin_translation=tab.state.resource,origin_language=w.library.resource(tab.state.resource).language)
            w.highlights.set(tab.reader.versification,[start],'green',tab.state.resource)
            baseline={n.id:n for n in w.notes_store.all()}
            native.activate(w);choose(w.space_selector,True);s=w.notes_space
            assert w.main_pages.get_visible_child_name()=='notes';s.open_note(note);spin()
            editor=s.editor;native.click(editor.body);chord('Control_L','End')
            for key in ['x','y','z']:native.key(key)
            spin(lambda:w.notes_store.get(note.id).body.endswith('xyz'))
            assert not editor.dirty;assert editor.context['start']==start
            with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):
                native.click(s.main_menu);native.click(s.main_menu.global_actions[0]);spin(lambda:w.catalogue_window.get_mapped())
                assert w.main_pages.get_visible_child_name()=='notes';w.catalogue_window.close();native.activate(w)
            shot('saved')
            # An actual SQLite write prohibition, rather than a mocked save.
            w.notes_store.db.execute('PRAGMA query_only=ON')
            native.click(editor.body);chord('Control_L','End');native.key('e')
            spin(lambda:editor.dirty and editor._autosave_id==0)
            assert w.notes_store.get(note.id).body.endswith('xyz')
            assert tr('Unable to save this note. Your draft is kept.') in editor.status.get_text()
            choose(s.space_selector,False);spin(lambda:editor._confirmation and editor._confirmation.get_mapped())
            native.activate(editor._confirmation);native.key('Escape');spin()
            assert not editor.closed and w.main_pages.get_visible_child_name()=='notes'
            assert editor.body.get_buffer().props.text.endswith('xyze');shot('write-error-draft-kept')
            w.notes_store.db.execute('PRAGMA query_only=OFF');native.activate(w);choose(s.space_selector,False)
            spin(lambda:w.main_pages.get_visible_child_name()=='reading');assert w.notes_store.get(note.id).body.endswith('xyze')
            choose(w.space_selector,True);spin(lambda:s.editor is not None);assert s.editor.note.id==note.id
            # Browse a highlight, cancel its real confirmation, then confirm.
            native.click(s.categories['highlights']);spin();native.click_at(s.list,80,24);spin(lambda:s.highlight_detail.get_visible())
            delete=s.highlight_detail.get_last_child();native.click(delete)
            def confirmation():return next((d for d in Gtk.Window.list_toplevels() if isinstance(d,Adw.MessageDialog) and d.get_mapped()),None)
            spin(lambda:confirmation() is not None);dialog=confirmation();native.activate(dialog);native.key('Escape');spin()
            key=(tab.reader.versification,start);assert key in w.highlights.entries
            native.activate(w);native.click(delete);spin(lambda:confirmation() is not None);dialog=confirmation();native.activate(dialog)
            confirm=next(b for b in descendants(dialog) if isinstance(b,Gtk.Button) and b.get_label()==tr('Confirm'))
            native.click(confirm);spin(lambda:key not in w.highlights.entries)
            assert w.notes_store.get(note.id) is not None
            for identifier,original in baseline.items():
                current=w.notes_store.get(identifier)
                assert current is not None
                assert current.start==original.start and current.origin_translation==original.origin_translation
                if identifier!=note.id:assert current==original
            native.activate(w);native.click(s.categories['all']);native.click(s.search);chord('Control_L','a')
            for char in ['x','y','z']:native.key(char)
            spin(lambda:len(s.rows)==1 and s.rows[0].note.id==note.id);shot('content-search')
            assert digest_tree(root/'translations')==resources
            report=dict(status='PASS',app_import=inspect.getfile(Window),native_workspace_switch=True,native_typing_autosaved=True,actual_sqlite_write_failure_guard=True,draft_kept_on_cancel=True,flush_on_workspace_change=True,library_from_notes=True,highlight_confirmation_cancel_and_remove=True,related_note_retained=True,full_content_search=True,existing_note_identities_retained=True,resource_files_unchanged=len(resources),manual_client_gnome_validation=False)
            print(json.dumps(report),flush=True)
        finally:
            w.notes_store.db.execute('PRAGMA query_only=OFF')
            if w.note_editor:w.note_editor._discard=True;w.note_editor.cancel_autosave()
            w.close();native.close()


if __name__=='__main__':main()
