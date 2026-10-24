"""Actual X11 chapter following and manual browsing; disposable SWORD fixtures."""
import inspect,json,tempfile
from pathlib import Path
from bible.ui import Application,Window,Library,Gtk
from tests.test_ui import installed_fixture,spin
from tools.check_alpha_ui import X11Input
from tools.check_passage_actions import point


def main():
    app=Application();app.register();native=X11Input()
    with tempfile.TemporaryDirectory() as directory:
        installed_fixture(directory,entries=[(f'Acts.1.{i}',f'EXACT SOURCE FIXTURE {i}. '+('Test text '*80)) for i in range(1,27)]+[('Acts.2.1','NEXT CHAPTER')])
        w=Window(app,Library(Path(directory)/'translations'));w.set_default_size(1250,780);w.present();spin()
        try:
            tab=w.active_tab;tab.navigate('Test','Acts.1.1');w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes')
            p=w.study.notes
            for verse in [2,8,8,15,25]:w.notes_store.save('Personal note '+str(verse)+'. '+('Retained writing '*20),[],versification='KJV',start=f'Acts.1.{verse}',end=f'Acts.1.{verse}',origin_translation='Test',origin_language='en')
            w.highlights.set('KJV',['Acts.1.8'],'blue','Test');p.refresh(force=True)
            spin(lambda:not tab._restoring_scroll and bool(p.cards) and p.cards[-1].get_height()>0)
            cards=list(p.cards);history=list(tab.state.history);native.activate(w)
            p.resume.grab_focus();focus=w.get_focus();before=tab.state.reference
            native.wheel(tab.text,14)
            spin(lambda:tab.state.reference==tab.visible_reference() and tab.state.reference!=before)
            assert p.cards==cards and w.get_focus() is focus
            first=tab.state.reference;native.wheel(tab.text,-8)
            spin(lambda:tab.state.reference==tab.visible_reference() and tab.state.reference!=first)
            assert tab.state.history==history
            # A real notes wheel suspends following and never navigates Scripture.
            reference=tab.state.reference;native.wheel(p.list,4);spin()
            assert not p.following and p.resume.get_visible() and tab.state.reference==reference
            native.click(p.resume);spin();assert p.following
            # A marker reveals the chapter list without editing.
            tab.reveal_reference('Acts.1.2');spin(lambda:not tab._restoring_scroll)
            native.click_at(tab.text,*point(tab.text,tab._verse_offsets['Acts.1.2']));spin()
            assert w.study.tool=='notes' and p.editor is None
            # Keyboard editing remains on the captured note through Bible input.
            p.scroll.get_vadjustment().set_value(0);spin();card=next(c for c in p.cards if hasattr(c,'note_id'))
            native.click(card.open_button);spin(lambda:p.editor is not None);editor=p.editor
            native.click(editor.body);native.key('x');spin();body=editor.body.get_buffer().props.text;context=dict(editor.context)
            native.wheel(tab.text,5);spin()
            assert not p.following and editor.body.get_buffer().props.text==body and editor.context==context
            editor._discard=True;editor.close();p.resume_following();spin()
            assert not hasattr(tab,'note_button') and not hasattr(p,'add')
            print(json.dumps(dict(status='PASS',app_import=inspect.getfile(Window),native_bible_wheel_both_directions=True,native_notes_wheel_suspends_without_navigation=True,native_resume=True,stable_cards_and_history=True,focus_preserved=True,marker_reveals_without_edit=True,captured_draft_retained=True,redundant_controls_absent=True,manual_client_gnome_validation=False)))
        finally:
            if w.note_editor and not w.note_editor.closed:w.note_editor._discard=True;w.note_editor.close()
            w.close();native.close()


if __name__=='__main__':main()
