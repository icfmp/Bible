"""Native editorial views use synthetic text and preserve personal annotations."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class EditorialUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bible.ui import Application
        cls.app=Application.get_default() or Application();cls.app.register()

    def test_notes_are_lazy_chapter_scoped_readonly_and_personal_notes_survive(self):
        from bible.ui import Window,Library
        from tests.test_ui import installed_fixture,spin,close_test_dialogs
        import Sword
        with tempfile.TemporaryDirectory() as directory:
            root=installed_fixture(directory,entries=[('John.1.1','<p>TEXT <hi type="italic">STYLE</hi><note n="1.1" osisRef="John.1.1" type="study">EDITORIAL ONLY</note></p>'),('John.1.2','SECOND TEXT'),('John.2.1','NEXT TEXT')])
            conf=next((root/'mods.d').glob('*.conf'))
            conf.write_text(conf.read_text().replace('SourceType=Plaintext','SourceType=OSIS')+'GlobalOptionFilter=OSISFootnotes\n')
            window=Window(self.app,Library(Path(directory)/'translations'));window.present();spin()
            try:
                tab=window.active_tab;tab.navigate('Test','John.1.1');spin()
                before=window.notes_store.all()
                with patch.object(tab.reader,'editorial_notes',wraps=tab.reader.editorial_notes) as read:
                    window.study.translation_notes.refresh(force=True);read.assert_not_called()
                    window.study_button.set_active(True)
                    window.study.tools.set_visible_child_name('translation-notes');spin()
                    self.assertIn('EDITORIAL ONLY',window.study.translation_notes.text.get_buffer().props.text)
                    self.assertFalse(window.study.translation_notes.text.get_editable())
                    calls=read.call_count;tab.select_verse('John.1.2');window.study.refresh();spin()
                    self.assertEqual(read.call_count,calls)
                    window.study_button.set_active(False);spin();window.study.translation_notes.refresh(force=True)
                    self.assertEqual(read.call_count,calls)
                self.assertNotIn('EDITORIAL ONLY',tab.text.get_buffer().props.text)
                self.assertEqual(window.notes_store.all(),before)
                self.assertEqual(window.study_settings.tool,'translation-notes')
            finally:window.close();close_test_dialogs();spin()

    def test_introduction_preserves_inline_words_and_leaves_passage_unchanged(self):
        from bible.ui import Window,Library
        from tests.test_ui import installed_fixture,spin,close_test_dialogs
        from bible.editorial_view import show_introduction,introduction_text
        from bible.youversion_content import parse
        import Sword
        self.assertEqual(introduction_text(parse('<root><p>1<hi type="super">er</hi> document</p><p>Suite</p></root>')),'1er document\n\nSuite')
        with tempfile.TemporaryDirectory() as directory:
            root=installed_fixture(directory,entries=[('John.1.1','READING DATA')])
            module=Sword.RawText(str(root/'modules/texts/rawtext/test'),'Test','Synthetic')
            key=Sword.VerseKey();key.setIntros(True);key.setAutoNormalize(False);key.setText('John.0.0')
            module.setKey(key);module.setEntry('<div type="introduction"><title>INTRO TITLE</title><p>1<hi type="super">er</hi> document</p></div>');del module
            window=Window(self.app,Library(Path(directory)/'translations'));window.present();spin()
            dialog=None
            try:
                tab=window.active_tab;tab.navigate('Test','John.1.1');spin()
                before=(tab.state.reference,window.notes_store.all(),tab.text.get_buffer().props.text)
                intro=tab.reader.introduction('John');self.assertIsNotNone(intro)
                self.assertIn('1er document',introduction_text(intro))
                dialog=show_introduction(window,tab.reader,'John');spin()
                window.set_default_size(360,560);dialog.set_default_size(320,400);spin()
                self.assertEqual((tab.state.reference,window.notes_store.all(),tab.text.get_buffer().props.text),before)
            finally:
                if dialog:dialog.close()
                window.close();close_test_dialogs();spin()
