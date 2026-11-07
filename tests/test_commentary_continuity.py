"""Incremental commentary extension preserves native selection and source styling."""
import os,tempfile,unittest
from pathlib import Path
from tests.test_ui import installed_fixture,spin
from tests.test_commentary import commentary_fixture


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK')
class CommentaryContinuityTests(unittest.TestCase):
    def test_append_prepend_keep_selected_text_and_do_not_inherit_heading_or_emphasis(self):
        from bible.ui import Application,Window,Library
        app=Application.get_default() or Application();app.register()
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,entries=[('Gen.1.1','BIBLE FIRST'),('Gen.1.2','BIBLE SECOND'),('Gen.2.1','BIBLE THIRD'),('Gen.2.2','BIBLE FOURTH')])
            root=commentary_fixture(directory,entries=[
                ('Gen.1.1','<p>EARLY plain text.</p>'),
                ('Gen.1.2','<p>SECOND plain text.</p>'),
                ('Gen.2.1','<p>Normal before <hi type="italic">EMPHASIS</hi> normal after.</p>'),
                ('Gen.2.2','<p>LATER plain text.</p>')])
            conf=root/'mods.d/test.conf';conf.write_text(conf.read_text().replace('SourceType=Plaintext','SourceType=OSIS')+'GlobalOptionFilter=OSISHeadings\n')
            w=Window(app,Library(Path(directory)/'translations'));w.set_default_size(1180,700);w.present();spin()
            try:
                w.study_button.set_active(True);s=w.study;s.choices.set_selected(s.names.index('Notes'));spin(lambda:not s._positioning)
                middle=s.reader.index.locate('Gen.2.1');last=s.reader.index.locate('Gen.2.2')
                s.loaded=[middle];s.current_position=middle;s.rebuild();spin(lambda:not s._positioning)
                buffer=s.text.get_buffer();offset=buffer.props.text.index('EMPHASIS')
                buffer.select_range(buffer.get_iter_at_offset(offset),buffer.get_iter_at_offset(offset+8))
                s.load_more(1);spin(lambda:not s._positioning)
                self.assertEqual(buffer.get_text(*buffer.get_selection_bounds(),True),'EMPHASIS')
                self.assertTrue(buffer.get_iter_at_offset(buffer.props.text.index('EMPHASIS')).has_tag(buffer.get_tag_table().lookup('source-italic')))
                normal=buffer.get_iter_at_offset(buffer.props.text.index('LATER'))
                self.assertFalse(normal.has_tag(buffer.get_tag_table().lookup('source-italic')))
                self.assertFalse(normal.has_tag(buffer.get_tag_table().lookup('entry-heading')))
                s.load_more(-1);spin(lambda:not s._positioning)
                self.assertEqual(buffer.get_text(*buffer.get_selection_bounds(),True),'EMPHASIS')
                self.assertIn('EARLY plain text.',buffer.props.text);self.assertIn(last,s.loaded)
                normal=buffer.get_iter_at_offset(buffer.props.text.index('EARLY'))
                self.assertFalse(normal.has_tag(buffer.get_tag_table().lookup('entry-heading')))
                self.assertEqual(w.active_tab.state.reference,'Gen.1.1')
            finally:w.close()
