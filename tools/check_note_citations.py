"""Real offline GTK note citations; disposable profile and installed Bible only."""
import argparse
import inspect
import json
from pathlib import Path
from gi.repository import Gtk
from bible.ui import Application,Window,Library
from bible.note_preview import NotePreview
from bible.reference_targets import local_excerpt
from bible.notes_window import buffer_text
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input


def walk(widget):
    yield widget
    child=widget.get_first_child()
    while child:yield from walk(child);child=child.get_next_sibling()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--captures',type=Path);parser.add_argument('--require-packaged',action='store_true')
    args=parser.parse_args()
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    assert len(Path('/proc/net/route').read_text().splitlines())<=1
    app=Application();app.register();native=X11Input()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    w=Window(app,Library(args.profile/'translations'));w.set_default_size(1440,950);w.present()
    report=dict(app_import=inspect.getfile(Window),network_disabled=True,accessibility='Deferred; not tested')
    def settled():spin(lambda:not w.active_tab._restoring_scroll,duration=.3)
    def capture(name):
        if args.captures:
            from PIL import ImageGrab
            args.captures.mkdir(parents=True,exist_ok=True);native.move_at(w,2,2);spin()
            ImageGrab.grab().save(args.captures/(name+'.png'))
    def click_citation(preview,index):
        citation=preview.citations[index]
        rect=preview.get_iter_location(preview.get_buffer().get_iter_at_offset(citation.begin+1))
        x,y=preview.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,rect.x,rect.y)
        native.click_at(preview,x+max(1,rect.width/2),y+max(1,rect.height/2))
        spin();assert w.reference_preview.popover and w.reference_preview.popover.get_visible()
    try:
        w.appearance.update('mode','day');w.active_tab.navigate('KJV','John.1.5');settled()
        body='Voir **Romains 8.28–30**, Psaumes 3:2 et 3 Jean 1:15.\n`Jean 3:16` et [John 3:16](https://example.test) restent du texte.'
        note=next((n for n in w.notes_store.all() if n.body==body),None)
        if note is None:note=w.notes_store.save(body,('Citation validation',),versification='Segond',start='John.1.5',end='John.1.5',origin_translation='FreSegond1910',origin_language='fr')
        w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes');w.study.notes.refresh(force=True);settled()
        preview=next(p for p in walk(w.study.notes.list) if isinstance(p,NotePreview))
        assert len(preview.citations)==3
        before=(w.active_tab.state.reference,list(w.active_tab.state.history),w.view.get_n_pages())
        click_citation(preview,0)
        expected=local_excerpt(w.active_tab.reader,'Rom.8.28','Rom.8.30',source_system='Segond')
        assert w.reference_preview.body.get_buffer().props.text==expected.text
        assert w.active_tab.scroll.get_width()>0
        capture('passage-note-preview');native.key('Escape');assert w.reference_preview.popover is None
        assert (w.active_tab.state.reference,w.active_tab.state.history,w.view.get_n_pages())==before
        assert w.notes_store.get(note.id)==note
        # A drag still selects native preview text; it must not open a link.
        first=preview.citations[0]
        def pointer(offset):
            rect=preview.get_iter_location(preview.get_buffer().get_iter_at_offset(offset))
            x,y=preview.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,rect.x,rect.y)
            native.move_at(preview,x+1,y+rect.height/2)
        pointer(first.begin+1);native.xtest.XTestFakeButtonEvent(native.display,1,True,0);native.x11.XFlush(native.display);spin()
        pointer(first.begin+9);spin();native.xtest.XTestFakeButtonEvent(native.display,1,False,0);native.x11.XFlush(native.display);spin()
        assert preview.get_buffer().get_has_selection() and w.reference_preview.popover is None
        preview.get_buffer().place_cursor(preview.get_buffer().get_start_iter())
        # Actual Tab entry, Return, next reference and Space, then focus return.
        preview.get_parent().get_parent().get_first_child().get_last_child().grab_focus()
        native.key('Tab');assert w.get_focus() is preview and preview._citation_focus==0,(w.get_focus(),preview._citation_focus)
        native.key('Return');assert w.reference_preview.popover
        native.key('Escape');assert w.get_focus() is preview
        native.key('Tab');assert preview._citation_focus==1
        native.key('space');assert w.reference_preview.target==('KJV','Ps.3.1')
        assert w.reference_preview.body.get_buffer().props.text==local_excerpt(w.active_tab.reader,'Ps.3.2',source_system='Segond').text
        native.key('Escape');native.key('Tab');native.key('Return')
        assert w.reference_preview.target==('KJV','3John.1.14');native.key('Escape')
        report['native_inline_preview']=dict(pointer=True,tab_return_space=True,escape_focus_return=True,
            exact_romans_range=True,segond_psalm_to_kjv=True,split_john=True,reader_history_preserved=True,stored_note_unchanged=True,native_drag_selection=True)
        from tests.test_appearance import SystemStyleOverride
        with SystemStyleOverride() as theme:
            for mode,contrast in [('day',False),('night',False),('day',True)]:
                theme.set(dark=mode=='night',high=contrast);w.appearance.update('mode',mode);spin()
                preview.get_buffer().place_cursor(preview.get_buffer().get_start_iter())
                click_citation(preview,0);capture('theme-'+mode+('-contrast-emulated' if contrast else ''))
                native.key('Escape')
        # Existing My notes mounts the same preview and keeps its filter context.
        native.click(w.my_notes_button);space=w.notes_space;space.open_note(note);editor=space.editor
        spin(lambda:editor.body.get_mapped())
        toggle=next(x for x in walk(editor.embedded_content) if isinstance(x,Gtk.ToggleButton) and x.get_mapped())
        native.click(toggle);spin(lambda:editor.preview.get_mapped())
        click_citation(editor.preview,1);assert w.reference_preview.target==('KJV','Ps.3.1')
        capture('my-notes-preview');native.key('Escape')
        assert w.notes_store.get(note.id)==note
        native.click(toggle);editor.body.grab_focus();native.key('End')
        for letter in ' draft':native.key('space' if letter==' ' else letter)
        draft=buffer_text(editor.body);assert draft!=note.body and editor.dirty
        native.click(toggle);click_citation(editor.preview,1)
        native.click(w.reference_preview.open_new);spin()
        assert editor._confirmation.get_visible() and w.view.get_n_pages()==before[2]
        cancel=next(x for x in walk(editor._confirmation) if isinstance(x,Gtk.Button) and x.get_label() in ('Keep editing','Continuer à écrire','Continuer à modifier','Continuer l’édition'))
        native.click(cancel);spin();assert not editor.closed and buffer_text(editor.body)==draft
        assert w.notes_store.get(note.id)==note
        # Reuse explicit close guards; discard affects the disposable draft only.
        click_citation(editor.preview,1);native.click(w.reference_preview.open_new);spin()
        discard=next(x for x in walk(editor._confirmation) if isinstance(x,Gtk.Button) and x.get_label() in ('Discard','Abandonner'))
        native.click(discard);spin()
        assert w.view.get_n_pages()==before[2]+1
        assert w.active_tab.state.resource=='KJV' and w.active_tab.state.reference=='Ps.3.1'
        assert w.tabs()[0].state.reference==before[0] and w.notes_store.get(note.id)==note
        report['my_notes_and_draft_guard']=dict(shared_preview=True,native_draft_typing=True,cancel_keeps_draft=True,
            discard_then_explicit_new_tab=True,original_note_context_unchanged=True)
        # Bare Xvfb does not restore parent focus after the native dialog.
        native.activate(w)
        w.active_tab.navigate('KJV','John.1.5');w.study_button.set_active(True)
        w.study.tools.set_visible_child_name('notes');w.study.notes.refresh(force=True);settled()
        w.set_default_size(360,800);spin(lambda:w.split.get_collapsed(),duration=.3)
        if not w.split.get_show_sidebar():native.key('F9')
        spin(lambda:w.study.header.get_mapped())
        preview=next(p for p in walk(w.study.notes.list) if isinstance(p,NotePreview))
        click_citation(preview,0);capture('narrow-note-preview');native.key('Escape')
        assert w.notes_store.get(note.id)==note
        report['narrow_and_themes']=True
        w.close();restored=Window(app,Library(args.profile/'translations'));restored.present()
        try:
            spin(lambda:not restored.active_tab._restoring_scroll,duration=.3)
            assert restored.notes_store.get(note.id)==note
            restored.study_button.set_active(True);restored.active_tab.navigate('KJV','John.1.5')
            restored.study.tools.set_visible_child_name('notes');restored.study.notes.refresh(force=True);spin()
            assert any(isinstance(p,NotePreview) and len(p.citations)==3 for p in walk(restored.study.notes.list))
        finally:restored.close()
        report['offline_restart_unchanged_note']=True;report['status']='PASS'
    finally:
        if not w.closed:w.close()
        native.close()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
