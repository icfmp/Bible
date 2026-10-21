"""Native offline #51 regression with real MHC; disposable TEST profile only.

Run against the published /app code (or explicitly identify a source candidate).
No module downloads, source edits or channel configuration changes are made.
"""
import argparse
import faulthandler
import signal
from pathlib import Path
from unittest.mock import patch
from bible.ui import Application,Window,Library,Gtk,GLib
from bible.notes import NoteStore
from bible.session import SessionStore
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input
from tools.check_scroll_sync import drag_scrollbar


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile')
    parser.add_argument('--steps',type=int,default=45);parser.add_argument('--require-packaged',action='store_true')
    parser.add_argument('--screenshot');args=parser.parse_args()
    import bible
    if args.require_packaged:assert bible.__file__.startswith('/app/'),bible.__file__
    print('IMPORT',bible.__file__,flush=True)
    faulthandler.enable(all_threads=True);faulthandler.register(signal.SIGTRAP,all_threads=True,chain=True)
    root=Path(args.profile);app=Application.get_default() or Application();app.register();native=X11Input()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline test')):
        w=Window(app,Library(root/'translations'));w.set_default_size(1440,900);w.present()
        try:
            w.appearance.reset();tab=w.active_tab;tab.navigate('FreSegond1910','Gen.1.1')
            tab.state.commentary='MHC';w.study_button.set_active(True);w.study.refresh();study=w.study
            spin(lambda:not tab._restoring_scroll and not study._positioning)
            print('MODULES',[(r.module.getName(),r.module.getConfigEntry('Version'),r.versification)
                             for r in (tab.reader,study.reader)],flush=True)
            note=w.notes_store.save('SENTINEL #51 TEST NOTE — not user data',[],versification=tab.reader.versification,
                start='Gen.1.1',origin_translation='FreSegond1910',origin_language='fr')
            history=len(tab.state.history);initial=tuple(study.loaded);transitions=[]
            original=study.load_more
            def load(direction):
                before=tuple(study.loaded);result=original(direction)
                if tuple(study.loaded)!=before:
                    transitions.append((before[0],before[-1],study.loaded[0],study.loaded[-1]))
                    print('LOAD',transitions[-1],'chars',study.text.get_buffer().get_char_count(),flush=True)
                assert len(study.loaded)<=20
                return result
            study.load_more=load;study.scroll.set_overlay_scrolling(False)
            for i in range(args.steps):
                if i>=20:
                    bar=study.scroll.get_vscrollbar();native.click_at(bar,bar.get_width()/2,bar.get_height()-4)
                native.wheel(study.text,10 if i<20 else 30)
            spin(lambda:not study._positioning and not tab._restoring_scroll)
            assert len(transitions)>=3,(initial,study.loaded,transitions)
            assert len(tab.state.history)==history
            native.wheel(study.text,-5);study.text.grab_focus();native.key('Page_Up');native.key('Page_Down')
            drag_scrollbar(native,study.scroll,None)
            spin(lambda:not study._positioning and not tab._restoring_scroll)
            assert w.reading_sync.driver=='commentary'
            native.wheel(tab.text,3);spin(lambda:not study._positioning and not tab._restoring_scroll)
            assert w.reading_sync.driver=='bible'
            # Pending work is cancelled on tab/source changes and hiding study.
            study.scrolled();w.new_tab();spin(lambda:not study._positioning and not w.active_tab._restoring_scroll)
            w.active_tab.state.commentary=None;study.refresh()
            assert not study.loaded and not study._load_idle and not study._scroll_idle
            w.active_tab.state.commentary='MHC';w.study_button.set_active(True)
            study.refresh();spin(lambda:not study._positioning)
            study.scrolled();w.study_button.set_active(False)
            assert not study._scroll_idle and not study._load_idle
            w.study_button.set_active(True);spin(lambda:not study._positioning)
            # Jump to the last genuinely indexed entry, not just the loaded chunk.
            final=study.reader.index.sections[-1];assert not final.introduction
            from bible.reference_resolution import resolve
            target=resolve(final.end,study.reader.versification,w.active_tab.reader).end
            w.active_tab.navigate('FreSegond1910',target)
            spin(lambda:not study._positioning and not w.active_tab._restoring_scroll)
            for _ in range(12):native.wheel(study.text,30)
            spin(lambda:not study._positioning and not study._loading and not w.active_tab._restoring_scroll)
            assert study.loaded[-1]==len(study.reader.index.sections)-1
            assert study.current_position==study.loaded[-1],(study.current_position,study.loaded)
            adj=study.scroll.get_vadjustment()
            assert adj.get_upper()-adj.get_page_size()-adj.get_value()<2
            count=len(transitions)
            for _ in range(3):native.wheel(study.text,20)
            assert len(transitions)==count and not study._load_idle and not study._loading
            assert w.notes_store.get(note.id)==note
            if args.screenshot:
                from PIL import ImageGrab
                ImageGrab.grab().save(args.screenshot)
            print('TRUE END',final.start,final.end,'loaded',study.loaded,flush=True)
            study.scrolled();w.close();assert not study._scroll_idle and not study._load_idle
            saved=SessionStore(root/'session.json').load();assert saved.tabs[saved.selected].commentary=='MHC'
            store=NoteStore(root/'notes.sqlite3')
            try:assert store.get(note.id)==note
            finally:store.close()
            reopened=Window(app,Library(root/'translations'));reopened.present()
            try:
                spin(lambda:not reopened.study._positioning and not reopened.active_tab._restoring_scroll)
                assert reopened.active_tab.state.reference==saved.tabs[saved.selected].reference
                assert reopened.study.loaded[-1]==len(reopened.study.reader.index.sections)-1
                assert reopened.notes_store.get(note.id)==note
            finally:reopened.close()
            print('PASS: progressive boundaries, bounded 20-entry buffer, native reverse/wheel/keyboard/long drag, '
                  'both sync directions, tab/source/hide cancellation, real resource end, notes/session reopen',flush=True)
        finally:
            if not w.closed:w.close()
            native.close()


if __name__=='__main__':main()
