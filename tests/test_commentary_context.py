"""Mapped Psalm titles remain source contexts, never ordinary verse zero."""
import os,tempfile,unittest
from pathlib import Path
from bible.reference_resolution import resolve,VersificationMismatch
from bible.sword_provider import CommentaryReader
from tests.test_commentary import commentary_fixture


def context_fixture(root,with_intro=True):
    import Sword
    path=commentary_fixture(root,entries=[('Ps.17.1','COMMENTARY VERSE ONE'),('Ps.17.2','COMMENTARY VERSE TWO'),('Ps.18.1','NEXT CHAPTER')])
    if with_intro:
        module=Sword.RawCom(str(path/'modules/texts/rawtext/test'),'Notes','Synthetic context')
        key=Sword.VerseKey();key.setIntros(True);key.setText('Ps.17.0')
        assert key.popError()=='\x00' and key.getVerse()==0
        module.setKey(key);module.setEntry('ACTUAL INTRODUCTION ENTRY');del module
    return path


class CommentaryContextTests(unittest.TestCase):
    def test_verified_combined_title_and_verse_do_not_weaken_annotation_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            reader=CommentaryReader(context_fixture(directory),'Notes')
            with self.assertRaises(VersificationMismatch):resolve('Ps.17.1','Catholic2',reader)
            result=resolve('Ps.17.1','Catholic2',reader,include_introductions=True)
            self.assertEqual((result.start,result.end,result.introductions),('Ps.17.1','Ps.17.1',('Ps.17.0',)))
            with self.assertRaises(ValueError):resolve('Ps.17.0','Catholic2',reader,include_introductions=True)
            ordinary=resolve('Ps.17.2','Catholic2',reader,include_introductions=True)
            self.assertEqual(ordinary.introductions,());self.assertEqual(ordinary.start,'Ps.17.2')

    @unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
    def test_follow_intro_body_missing_intro_and_later_verse_without_changing_reference(self):
        from bible.ui import Application,Window,Library
        from tests.test_ui import installed_fixture,spin
        app=Application.get_default() or Application();app.register()
        for with_intro in (True,False):
            with self.subTest(with_intro=with_intro),tempfile.TemporaryDirectory() as directory:
                installed_fixture(directory,versification='Catholic2',entries=[('Ps.17.1','SOURCE TITLE AND VERSE'),('Ps.17.2','SOURCE SECOND VERSE'),('Ps.18.1','NEXT SOURCE CHAPTER')])
                context_fixture(directory,with_intro)
                w=Window(app,Library(Path(directory)/'translations'));w.present()
                try:
                    t=w.active_tab;t.navigate('Test','Ps.17.1');w.study_button.set_active(True)
                    s=w.study;s.tools.set_visible_child_name('commentaries');s.refresh(force=True)
                    s.choices.set_selected(s.names.index('Notes'));spin(lambda:not s._positioning and s.current_position is not None)
                    self.assertEqual(s.reader.index.sections[s.current_position].introduction,with_intro)
                    self.assertEqual(t.state.reference,'Ps.17.1')
                    self.assertEqual(s.alignment_introductions,('Ps.17.0',))
                    self.assertNotIn('Invalid reference',s.status.get_text())
                    history=list(t.state.history)
                    t.select_verse('Ps.17.2');spin(lambda:not s._positioning)
                    self.assertFalse(s.reader.index.sections[s.current_position].introduction)
                    self.assertEqual(s.status.get_text(),'');self.assertEqual(s.alignment_introductions,())
                    t.select_verse('Ps.17.1');spin(lambda:not s._positioning)
                    w.study_button.set_active(False);w.study_button.set_active(True);spin(lambda:not s._positioning)
                    self.assertEqual(t.state.history,history);self.assertEqual(t.state.reference,'Ps.17.1')
                    self.assertIn('SOURCE TITLE AND VERSE',t.text.get_buffer().props.text)
                    self.assertIn('COMMENTARY VERSE ONE',s.text.get_buffer().props.text)
                    if with_intro:self.assertIn('ACTUAL INTRODUCTION ENTRY',s.text.get_buffer().props.text)
                finally:w.close()
