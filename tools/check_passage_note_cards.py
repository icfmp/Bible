"""Real GTK pointer/keyboard checks for passage annotation cards (#90).

Run in an isolated Xvfb display. Uses disposable, explicitly synthetic SWORD
content; real-resource visual evidence is recorded separately.
"""
import argparse
import inspect
import json
import tempfile
from pathlib import Path
from tests.test_ui import installed_fixture, spin
from tools.check_alpha_ui import X11Input
from bible.ui import Application, Window, Library, Gtk
from bible.notes_window import buffer_text


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--require-packaged',action='store_true')
    args=parser.parse_args()
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    app=Application();app.register();native=X11Input();report={}
    with tempfile.TemporaryDirectory() as directory:
        installed_fixture(directory,entries=[('Acts.1.22','SYNTHETIC VERSE 22'),('Acts.1.23','SYNTHETIC VERSE 23'),('John.3.16','SYNTHETIC CITATION')])
        w=Window(app,Library(Path(directory)/'translations'));w.set_default_size(1200,900);w.present();spin()
        settings=Gtk.Settings.get_default();settings.set_property('gtk-enable-animations',False)
        try:
            w.active_tab.navigate('Test','Acts.1.22');w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes')
            context=dict(versification='KJV',start='Acts.1.22',end='Acts.1.22',origin_translation='Test',origin_language='en')
            note=w.notes_store.save('John 3:16. **Personal observation**. '+('Long personal writing. '*30),['Keep'],**context)
            notes=w.study.notes;notes.refresh(force=True);spin();native.activate(w)
            card=notes.cards[0];preview=card.preview
            # Click the actual Pango link, rather than calling its callback.
            layout=preview.get_layout();citation=preview.citations[0]
            rect=layout.index_to_pos(len(preview.get_text()[:citation.begin+2].encode()))
            x,y=preview.get_layout_offsets()
            native.click_at(preview,x+rect.x/1024+2,y+rect.y/1024+rect.height/2048)
            assert w.reference_preview.target==('Test','John.3.16')
            assert notes.editor is None and w.active_tab.state.reference=='Acts.1.22'
            native.key('Escape');spin()
            native.click_at(preview,preview.get_width()/2,preview.get_height()-3);spin()
            assert notes.editor and notes.editor.note.id==note.id,'Preview click must open inline editor'
            editor=notes.editor;editor.body.get_buffer().set_text('Deliberate draft **kept**')
            w.active_tab.navigate('Test','Acts.1.23');w.study_button.set_active(False);spin()
            w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes');spin()
            assert buffer_text(editor.body)=='Deliberate draft **kept**' and editor.context==context
            # Actual keyboard activation of Expand keeps the exact buffer.
            original=editor.body.get_buffer();expand=notes.editor_commands.get_last_child()
            expand.grab_focus();native.key('space');spin()
            assert not editor.embedded and editor.body.get_buffer() is original
            assert editor.save();assert w.notes_store.get(note.id).body=='Deliberate draft **kept**'
            report['native_citation_preview_and_inline_click']=True
            report['draft_context_buffer_and_expansion_preserved']=True
            w.active_tab.navigate('Test','Acts.1.22');spin();native.activate(w)
            # Creation remains in the real contextual selection toolbar.
            assert not hasattr(notes,'add') and not hasattr(w.active_tab,'note_button')
            from tools.check_passage_actions import point
            tab=w.active_tab;tab.select_verse('Acts.1.23');spin()
            offset=tab._marker_ends['Acts.1.23']
            native.click_at(tab.text,*point(tab.text,offset+3));spin()
            assert w.passage_actions.target is None
            from tools.check_passage_actions import hold
            hold(native,'Shift_L',True);native.key('Right');hold(native,'Shift_L',False)
            spin(lambda:w.passage_actions.target is not None)
            actions=w.passage_actions;native.click(actions.highlight_button);native.key('Escape');spin()
            assert not w.highlights.entries
            native.click(actions.highlight_button);native.click(actions.highlight_popover.get_child().get_first_child());spin()
            assert w.highlights.entries[('KJV','Acts.1.23')]['color']=='yellow'
            native.click(actions.note_button);spin()
            assert w.note_editor and w.note_editor.context['start']=='Acts.1.23'
            w.note_editor.body.get_buffer().set_text('Independent annotation');assert w.note_editor.save();spin()
            assert len(notes.rows)==2 and len(notes.marks)==1
            original_notes=w.notes_store.all()
            menu=next(c for c in notes.cards if hasattr(c,'highlight_key')).actions
            # Scroll the mark into view before actual pointer input.
            menu.grab_focus();spin();native.click(menu);spin()
            native.click(menu.get_popover().get_child().get_last_child());spin()
            assert not notes.marks and w.notes_store.all()==original_notes
            report['native_contextual_creation_cancel_note_remove_independence']=True
            w.set_default_size(360,700);spin(lambda:w.split.get_collapsed());spin()
            w.split.set_show_sidebar(True);spin()
            editor=notes.open_note(w.notes_store.get(note.id));spin();assert editor.embedded and notes.editor_panel.get_mapped()
            dpi=settings.get_property('gtk-xft-dpi')
            for enlarged in (False,True):
                if enlarged:settings.set_property('gtk-xft-dpi',147456);spin()
                assert w.get_width()<=360,w.get_width()
                assert notes.editor_commands.get_mapped()
                assert notes.editor_panel.get_width()<=w.study.get_width()-24,(notes.editor_panel.get_width(),w.study.get_width())
                assert notes.editor_commands.get_width()<=notes.editor_panel.get_width()
                for child in (notes.editor_commands.get_first_child(),notes.editor_commands.get_last_child()):
                    found,bounds=child.compute_bounds(notes.editor_panel)
                    assert found and bounds.origin.x>=0 and bounds.origin.x+bounds.size.width<=notes.editor_panel.get_width()+1
            settings.set_property('gtk-xft-dpi',dpi);editor._discard=True;editor.close()
            report['360px_window_and_150_percent_text_editor_commands']=True
            report.update(status='PASS',app_import=inspect.getfile(Window),manual_client_gnome_validation=False)
        finally:
            if w.note_editor and not w.note_editor.closed:w.note_editor._discard=True;w.note_editor.close()
            w.close();native.close()
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
