"""Inline objects are source-aware, independent and absent from copied Scripture."""
import os
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from unittest.mock import patch


class MarkerDocumentTests(unittest.TestCase):
    def test_end_group_preserves_copy_and_canonical_positions(self):
        from bible.pagination import Document,PassageSpan
        from bible.inline_document import decorate
        text='1 First sentence.\n\n2 Second sentence.'
        second=text.index('2 Second')
        source=Document('Gen.1',text,(PassageSpan('Gen.1.1',0,2,second),
                                      PassageSpan('Gen.1.2',second,second+2,len(text))))
        marked=decorate(source,{'Gen.1.1':(('note',[1]),('place',[2])),
                                'Gen.1.2':(('note',[3]),)})
        self.assertIn('sentence.\ufffc\ufffc\n\n2 Second',marked.text)
        self.assertEqual(marked.copy(0,len(marked.text)),text)
        for offset in range(len(text)+1):
            shifted=marked.source_shift(offset)
            self.assertEqual(marked.anchor(shifted),source.anchor(offset))
            self.assertEqual(marked.locate(source.anchor(offset)),marked.source_shift(source.locate(source.anchor(offset))))


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires GTK')
class InlineMarkerTests(unittest.TestCase):
    def test_native_multi_place_chooser_after_scrolling_the_anchor(self):
        if os.environ.get('BIBLE_TEST_ISOLATED_CLICK')!='1':
            result=subprocess.run(['dbus-run-session','--','xvfb-run','-a',sys.executable,
                                   '-m','unittest',self.id(),'-v'],
                                  env=dict(os.environ,BIBLE_TEST_ISOLATED_CLICK='1'),
                                  capture_output=True,text=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr);return
        import json
        from bible.ui import Application,Window,Library
        from tests.test_ui import installed_fixture,spin,close_test_dialogs
        from tests.test_place_data import inputs,pins
        from bible import place_data
        from tools.check_alpha_ui import X11Input
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            installed_fixture(directory,entries=[(f'John.1.{i}','Exact synthetic Scripture sentence. '*12) for i in range(1,20)])
            files=inputs(root);first=json.loads(files['ancient'].read_text())
            second=dict(first,id='a654321',friendly_id='Another place',url_slug='another-place')
            files['ancient'].write_text(json.dumps(first)+'\n'+json.dumps(second)+'\n')
            with patch.object(place_data,'FILES',pins(files)):place_data.PlaceData(root/'study-data').install_files(files)
            app=Application.get_default() or Application();app.register()
            w=Window(app,Library(root/'translations'));w.set_default_size(1180,800);w.present();spin()
            native=X11Input();native.activate(w)
            try:
                t=w.active_tab;t.navigate('Test','John.1.5')
                spin(lambda:any(b._marker_reference=='John.1.5' for b in t.text._inline_buttons),timeout=10)
                offset=next(o for o,(r,k,p) in t._document.inline.items() if r=='John.1.5' and k=='place')
                t.text.scroll_to_iter(t.text.get_buffer().get_iter_at_offset(offset),0,True,0,.4);spin(duration=.3)
                button=next(b for b in t.text._inline_buttons if b._marker_reference=='John.1.5')
                native.click(button);spin()
                pop=next(p for p in w._reading_popovers if p.get_visible())
                def walk(widget):
                    yield widget;child=widget.get_first_child()
                    while child:yield from walk(child);child=child.get_next_sibling()
                choices=[x for x in walk(pop) if hasattr(x,'_place_id')]
                self.assertEqual({c._place_id for c in choices},{'a123456','a654321'})
                with patch.object(t.inline_markers,'place') as open_place:
                    native.click(next(c for c in choices if c._place_id=='a654321'));spin()
                    self.assertEqual(open_place.call_args.args[2]['id'],'a654321')
                self.assertFalse(w.passage_actions.bar.get_visible())
            finally:native.close();close_test_dialogs();w.close()

    def test_native_note_click_and_hovered_marker_rebuild_in_both_readers(self):
        if os.environ.get('BIBLE_TEST_ISOLATED_CLICK')!='1':
            result=subprocess.run(['dbus-run-session','--','xvfb-run','-a',sys.executable,
                                   '-m','unittest',self.id(),'-v'],
                                  env=dict(os.environ,BIBLE_TEST_ISOLATED_CLICK='1'),
                                  capture_output=True,text=True,timeout=45)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr);return
        from bible.ui import Application,Window,Library
        from tests.test_ui import installed_fixture,spin,close_test_dialogs
        from tools.check_alpha_ui import X11Input
        with tempfile.TemporaryDirectory() as directory:
            for name in ('Test','Other'):
                installed_fixture(directory,name,entries=[('Gen.1.1','First exact sentence.'),('Gen.1.2','Second exact sentence.')])
            app=Application.get_default() or Application();app.register()
            w=Window(app,Library(Path(directory)/'translations'));w.set_default_size(1280,850);w.present();spin()
            native=X11Input();native.activate(w)
            try:
                t=w.active_tab;t.navigate('Test','Gen.1.1')
                for body in ('First note','Second note'):
                    w.notes_store.save(body,[],versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation='Test',origin_language='en')
                w.notes_changed();spin()
                for comparison in (False,True,False,True):
                    t.state.comparison='Other' if comparison else None;w.sync_comparison();spin()
                    view=t.comparison_text if comparison else t.text
                    for tool,opened in (('commentaries',False),('references',True)):
                        w.study.tools.set_visible_child_name(tool);w.study_button.set_active(opened);spin()
                        button=next(b for b in view._inline_buttons if b._marker_kind=='note')
                        native.click(button);spin()
                        self.assertTrue(w.study_button.get_active());self.assertEqual(w.study.tool,'notes',(comparison,tool,opened))
                        self.assertEqual(len(w.study.notes.rows),2);self.assertIsNone(w.study.notes.editor)
                        self.assertFalse(w.passage_actions.bar.get_visible())
                    # Rebuild while the native pointer still hovers the child:
                    # unmap must happen before deleting the buffer's anchor tree.
                    w.appearance.update('verse_numbers',not w.preferences.value.verse_numbers);spin()
            finally:native.close();close_test_dialogs();w.close()

    def test_notes_ranges_hidden_numbers_copy_and_live_edits(self):
        from bible.ui import Application,Window,Library
        from tests.test_ui import installed_fixture,spin,close_test_dialogs
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,entries=[('Gen.1.1','First source words.'),('Gen.1.2','Second source words.'),('Gen.1.3','Third source words.')])
            app=Application.get_default() or Application();app.register()
            window=Window(app,Library(Path(directory)/'translations'));window.present();spin()
            try:
                tab=window.active_tab;tab.navigate('Test','Gen.1.1')
                original=tab._document.copy(0,len(tab._document.text))
                for start,end,body in [('Gen.1.1','Gen.1.2','A personal note'),('Gen.1.1','Gen.1.1','Another note')]:
                    window.notes_store.save(body,[],versification='KJV',start=start,end=end,origin_translation='Test',origin_language='en')
                window.highlights.set('KJV',['Gen.1.3'],'blue','Test')
                window.notes_changed();spin()
                self.assertEqual(len(tab.text._inline_buttons),1)
                self.assertEqual(tab._document.copy(0,len(tab._document.text)),original)
                self.assertNotIn('\ufffc',tab._document.copy(0,len(tab._document.text)))
                self.assertEqual(tab.text.get_buffer().get_char_count(),len(tab._document.text))
                for offset,(reference,kind,_) in tab._document.inline.items():
                    span=next(s for s in tab._document.spans if s.reference==reference)
                    self.assertGreater(offset,span.body)
                    self.assertTrue(tab._document.text[span.body:offset].rstrip().endswith('.'))
                before=tab.scroll.get_vadjustment().get_value()
                tab.text._inline_buttons[0].emit('clicked');spin()
                self.assertEqual(window.study.tool,'notes');self.assertIsNone(window.study.notes.editor)
                self.assertEqual(len(window.study.notes.rows),2)
                window.appearance.update('verse_numbers',False);spin()
                self.assertEqual(len(tab.text._inline_buttons),1)
                window.appearance.update('note_indicators',False);spin()
                self.assertFalse(tab.text._inline_buttons)
                self.assertNotIn('\ufffc',tab._document.text)
                self.assertEqual(len(window.notes_store.all()),2)
                window.appearance.update('note_indicators',True);spin()
                editor=window.study.notes.open_note(window.notes_store.all()[0])
                editor.body.get_buffer().set_text('Draft kept')
                tab.text._inline_buttons[0].emit('clicked');spin()
                self.assertIs(window.study.notes.editor,editor)
                self.assertEqual(editor.body.get_buffer().props.text,'Draft kept')
                editor._discard=True;editor.close()
                self.assertGreaterEqual(before,0)
            finally:close_test_dialogs();window.close()

    def test_place_fallback_and_note_coexist_after_verified_mapping_without_network(self):
        from bible.ui import Application,Window,Library
        from tests.test_ui import installed_fixture,spin,close_test_dialogs
        from tests.test_place_data import inputs,pins
        from bible import place_data
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);installed_fixture(directory,entries=[('John.1.5','Exact scripture without geographic name matching.')])
            files=inputs(root);data=place_data.PlaceData(root/'study-data')
            with patch.object(place_data,'FILES',pins(files)):data.install_files(files)
            app=Application.get_default() or Application();app.register()
            window=Window(app,Library(root/'translations'));window.present();spin()
            try:
                tab=window.active_tab;tab.navigate('Test','John.1.5')
                window.notes_store.save('Note',[],versification='KJV',start='John.1.5',end='John.1.5',origin_translation='Test',origin_language='en')
                window.notes_changed();spin(lambda:len(tab.text._inline_buttons)==2,duration=.5)
                self.assertEqual(len(tab.text._inline_buttons),2)
                self.assertIn('Exact scripture',tab._document.copy(0,len(tab._document.text)))
                geographic=next(b for b in tab.text._inline_buttons if b._marker_kind=='place')
                with patch('urllib.request.urlopen',side_effect=AssertionError('Offline')):
                    geographic.emit('clicked');spin()
                    self.assertEqual(window.place_dialog.current_place['id'],'a123456')
                    window.place_dialog.close();spin()
                window.appearance.update('place_markers',False);spin()
                self.assertEqual(len(tab.text._inline_buttons),1)
                self.assertFalse(hasattr(window.study,'places_button'))
            finally:close_test_dialogs();window.close()
