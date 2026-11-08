"""Shared contextual host and source-backed verse/word presentation."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.test_ui import installed_fixture,spin,close_test_dialogs
from tests.test_step_data import fixtures


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class ContextualStudyTests(unittest.TestCase):
    def setUp(self):
        from bible.ui import Application,Window,Library
        from bible import step_data
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        installed_fixture(self.root,entries=[('John.1.1','FIRST ORIGINAL WORDING'),('John.1.2','SECOND ORIGINAL WORDING')])
        installed_fixture(self.root,'Other',entries=[('John.1.1','OTHER VERSION WORDING')])
        files,pins=fixtures(self.root)
        with patch.object(step_data,'FILES',pins),patch.object(step_data,'EXPECTED_COUNTS',{'tagnt-na27':2,'tahot-main':4}):
            step_data.StepData(self.root/'study-data').install_files(files)
        app=Application.get_default() or Application();app.register()
        self.w=Window(app,Library(self.root/'translations'));self.w.set_default_size(1200,850);self.w.present()
        self.w.active_tab.navigate('Test','John.1.1');spin(lambda:not self.w.active_tab._restoring_scroll)

    def tearDown(self):
        close_test_dialogs();self.w.close()

    def target(self):
        from bible.passage_actions import target
        tab=self.w.active_tab;source=self.w.passage_actions.ordinary(tab)
        buffer=tab.text.get_buffer()
        buffer.select_range(buffer.get_iter_at_offset(tab._marker_ends['John.1.1']),
                            buffer.get_iter_at_offset(tab._verse_ranges['John.1.2'][1]))
        return target(tab.text,source,lambda:self.w.passage_actions.ordinary(tab))

    def test_verse_excerpts_follow_only_dialog_version_without_fabricated_missing_verse(self):
        from bible.ui import Gtk
        words=self.w.study.words;words.open(self.target());spin(lambda:not words.pending,duration=.2)
        def excerpts():return {x._translated_reference:x.get_text() for x in words.children() if hasattr(x,'_translated_reference')}
        self.assertEqual(excerpts(),{'John.1.1':'FIRST ORIGINAL WORDING','John.1.2':'SECOND ORIGINAL WORDING'})
        self.assertFalse(words.selection_label.get_visible())
        tokens=[x for x in words.children() if hasattr(x,'_source_token')]
        self.assertEqual(len(tokens),1)
        tile=tokens[0].get_child()
        self.assertEqual(tile.get_first_child().get_text(),'λόγος')
        self.assertEqual(tile.get_first_child().get_next_sibling().get_text(),'word')
        history=list(self.w.active_tab.state.history)
        words.translation.set_selected(words.translations.index('Other'));spin(lambda:not words.pending,duration=.2)
        from bible.i18n import tr
        self.assertEqual(excerpts(),{'John.1.1':'OTHER VERSION WORDING','John.1.2':tr('This passage is unavailable in the selected translation.')})
        self.assertEqual(self.w.active_tab.state.resource,'Test')
        self.assertEqual(self.w.active_tab.state.history,history)
        tokens=[x for x in words.children() if hasattr(x,'_source_token')]
        self.assertEqual(tokens[0]._source_token['form'],'λόγος')
        self.assertEqual(self.w.passage_study_dialog.get_title(),tr('Study passage'))

    def test_four_tabs_preserve_context_and_one_word_component(self):
        w=self.w;w.study.tools.set_visible_child_name('notes');tool=w.study.tool
        before=(w.active_tab.state.resource,w.active_tab.state.reference,list(w.active_tab.state.history),w.notes_store.all())
        host=w.open_passage_study(target=self.target());spin(lambda:not w.study.words.pending)
        self.assertEqual(host.tabs.get_pages().get_n_items(),4)
        context=host.context;words=host.words
        for name in ('map','dictionary','people','original','map','original'):
            host.tabs.set_visible_child_name(name);spin()
            self.assertEqual(host.context,context)
            self.assertIs(host.words,words)
            self.assertEqual(w.study.tool,tool)
        self.assertEqual((w.active_tab.state.resource,w.active_tab.state.reference,list(w.active_tab.state.history),w.notes_store.all()),before)
        host.close();spin()
        self.assertIsNone(w.passage_study_dialog);self.assertIsNone(words.dialog)
        self.assertIsNone(words.get_parent())

    def test_missing_and_supplied_glosses_remain_source_text(self):
        words=self.w.study.words;words.open(self.target());spin(lambda:not words.pending)
        original=words.data.verse('tagnt-na27','John.1.1')[0]
        for gloss in ('sens français fourni','supplied English sense',''):
            with patch.object(words.data,'verse',return_value=[dict(original,gloss=gloss)]):
                words.verse_choices();spin(lambda:not words.pending)
            token=next(x for x in words.children() if hasattr(x,'_source_token'))
            second=token.get_child().get_first_child().get_next_sibling()
            if gloss:self.assertEqual(second.get_text(),gloss)
            else:self.assertIsNone(second)
