import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture,spin


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class PassageActionTests(unittest.TestCase):
    def test_frozen_comparison_source_copy_note_and_stale_selection(self):
        from bible.ui import Application,Window,Library
        app=Application.get_default() or Application();app.register()
        with tempfile.TemporaryDirectory() as directory:
            for name,system in [('Test','KJV'),('Other','Segond')]:
                installed_fixture(directory,name,entries=[(f'Gen.1.{i}',f'{name} verse {i} source words '*8) for i in range(1,5)],versification=system)
            window=Window(app,Library(Path(directory)/'translations'));window.present()
            try:
                tab=window.active_tab;tab.navigate('Test','Gen.1.1');tab.state.comparison='Other';window.sync_comparison()
                spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_positioning',False))
                actions=window.passage_actions;view=tab.comparison_text;buffer=view.get_buffer()
                first,last=tab._comparison_markers['Gen.1.2']+1,tab._comparison_markers['Gen.1.3']+5
                buffer.select_range(buffer.get_iter_at_offset(first),buffer.get_iter_at_offset(last));spin()
                self.assertFalse(actions.bar.get_visible(),'Programmatic selection must not open the bar')
                factory=lambda:actions.ordinary(tab,True)
                actions.capture(view,factory,None)
                self.assertEqual(actions.target.references,('Gen.1.2','Gen.1.3'))
                self.assertEqual(actions.target.source.resource,'Other')
                self.assertEqual(actions.target.source.reader.versification,'Segond')
                copied=[];expected=actions.target.text;actions.copy()
                window.get_clipboard().read_text_async(None,lambda clipboard,result:copied.append(clipboard.read_text_finish(result)))
                spin(lambda:bool(copied));self.assertEqual(copied[0],expected)
                self.assertEqual(tuple(i.get_offset() for i in buffer.get_selection_bounds()),(first,last))
                actions.note();editor=window.note_editor
                self.assertEqual(editor.context['origin_translation'],'Other')
                self.assertEqual(editor.context['versification'],'Segond')
                self.assertEqual((editor.context['start'],editor.context['end']),('Gen.1.2','Gen.1.3'))
                editor.close();spin()
                # A new selection must invalidate the old frozen action target.
                changed=tab._comparison_markers['Gen.1.4']
                buffer.select_range(buffer.get_iter_at_offset(changed),buffer.get_iter_at_offset(changed+5))
                self.assertFalse(actions.valid());actions.copy();self.assertFalse(actions.bar.get_visible())
                self.assertEqual(tab.state.resource,'Test')
                if not hasattr(window,'highlights'):self.assertIsNone(actions.highlight_button)
            finally:window.close()

    def test_programmatic_anchor_and_study_updates_do_not_open_actions(self):
        from bible.ui import Application,Window,Library
        app=Application.get_default() or Application();app.register()
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            window=Window(app,Library(Path(directory)/'translations'));window.present()
            try:
                tab=window.active_tab;tab.select_verse('Gen.1.2')
                tab.mark_commentary_range('Gen.1.1','Gen.1.2');spin()
                self.assertFalse(window.passage_actions.bar.get_visible())
            finally:window.close()
