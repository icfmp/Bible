"""Native references/preview state, async invalidation and the Library data flow."""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.test_ui import installed_fixture,spin,close_test_dialogs
from tests.test_reference_data import archive
from bible import reference_data


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class StudyReferenceTests(unittest.TestCase):
    def setUp(self):
        self.directory=self.enterContext(tempfile.TemporaryDirectory());self.root=Path(self.directory)
        installed_fixture(self.directory,entries=[('John.1.5','SOURCE VERSE FIVE'),('John.1.6','SOURCE VERSE SIX'),
            ('John.3.16','DESTINATION SIXTEEN'),('John.3.17','DESTINATION SEVENTEEN'),('Ps.3.1','PSALM SOURCE')])
        source=self.root/'data.zip'
        digest=archive(source,'John.1.5\tJohn.3.16\t14\nJohn.1.6\tJohn.3.16\t19\nJohn.1.5\tJohn.3.17\t12\n')
        self.source=source;self.digest=digest
        from bible.ui import Application,Window,Library
        app=Application.get_default() or Application();app.register()
        self.window=Window(app,Library(self.root/'translations'));self.window.set_default_size(1100,850);self.window.present()

    def tearDown(self):
        close_test_dialogs()
        if self.window.note_editor:self.window.note_editor._discard=True
        self.window.close()

    def install(self):
        with patch.object(reference_data,'ARCHIVE_SHA256',self.digest):
            self.window.study.references.data.install_archive(self.source)

    def show(self,reference='John.1.5'):
        w=self.window;w.active_tab.navigate('Test',reference);w.study_button.set_active(True)
        w.study.tools.set_visible_child_name('references');w.study.references.refresh()
        spin(lambda:not w.study.references.pending,duration=.2)
        return w.study.references

    def test_preview_does_not_navigate_and_explicit_actions_keep_translation_and_other_tabs(self):
        self.install();refs=self.show();w=self.window;tab=w.active_tab
        self.assertEqual(len(refs.rows),2)
        before=(tab.state.reference,list(tab.state.history),w.view.get_n_pages())
        anchor=refs.teaser_rows.get_first_child()
        # A mapped anchor is needed; use the References header in this test.
        popover=w.reference_preview.show(refs.heading,'Test',tab.reader,'John.3.16')
        spin();self.assertTrue(popover.get_visible())
        self.assertEqual(w.reference_preview.body.get_buffer().props.text,'DESTINATION SIXTEEN')
        self.assertEqual((tab.state.reference,tab.state.history,w.view.get_n_pages()),before)
        w.reference_preview.open_new.emit('clicked');spin()
        self.assertEqual(w.view.get_n_pages(),before[2]+1)
        self.assertEqual(w.active_tab.state.reference,'John.3.16')
        self.assertEqual(w.active_tab.state.resource,'Test')
        self.assertEqual((tab.state.reference,tab.state.history),(before[0],before[1]))
        w.view.set_selected_page(w.view.get_page(tab));w.study_button.set_active(True);spin()
        w.reference_preview.show(refs.heading,'Test',tab.reader,'John.3.17');spin()
        w.reference_preview.open_here.emit('clicked');spin()
        self.assertEqual(tab.state.reference,'John.3.17')
        self.assertEqual(len(tab.state.history),len(before[1])+1)

    def test_range_aggregation_rapid_navigation_and_preview_dismissal(self):
        self.install();refs=self.show();w=self.window;tab=w.active_tab
        buffer=tab.text.get_buffer()
        buffer.select_range(buffer.get_iter_at_offset(tab._marker_ends['John.1.5']),
                            buffer.get_iter_at_offset(tab._verse_ranges['John.1.6'][1]))
        spin(lambda:not refs.pending and refs.context[2:] == ('John.1.5','John.1.6'),duration=.2)
        self.assertEqual(refs.rows[0].score,19);self.assertEqual(refs.rows[0].source_count,2)
        w.reference_preview.show(refs.heading,'Test',tab.reader,'John.3.16')
        tab.navigate('Test','John.1.5');tab.navigate('Test','Ps.3.1');tab.navigate('Test','John.1.6')
        spin(lambda:not refs.pending and refs.context[2:] == ('John.1.6','John.1.6'),duration=.2)
        self.assertIsNone(w.reference_preview.popover)
        self.assertEqual([(r.start,r.score) for r in refs.rows],[('John.3.16',19)])

    def test_missing_data_library_flow_and_offline_browse_do_not_change_bible_resources(self):
        from bible.study_resources import REFERENCE_RESOURCE_ID
        refs=self.show();self.assertTrue(refs.download.get_visible())
        original=self.window.library.installed()
        with patch('bible.catalogue_window.catalogue',side_effect=AssertionError('Study data needs no SWORD refresh')):
            dialog=self.window.open_library('study');spin(duration=.2)
            self.assertFalse(dialog._catalogue_requested)
            self.assertEqual(dialog.filtered_resources[0].id,REFERENCE_RESOURCE_ID)
            dialog.open_details(None,0)
            self.assertIn(reference_data.LICENSE_URL,dialog.metadata.get_text())
            self.install();self.window.resource_installed(REFERENCE_RESOURCE_ID);dialog.filter_resources()
            spin(lambda:not refs.pending,duration=.2)
            self.assertTrue(dialog.installed_state.get_visible() or dialog.download_button.get_visible())
            self.assertEqual(self.window.library.installed(),original)
            self.assertNotIn(REFERENCE_RESOURCE_ID,self.window.library.installed('bible'))
            self.assertTrue(refs.rows)

    def test_missing_local_text_keeps_preview_non_navigating_and_data_available(self):
        self.install();refs=self.show();w=self.window;tab=w.active_tab
        before=(tab.state.reference,list(tab.state.history))
        w.reference_preview.show(refs.heading,'Test',tab.reader,'Gen.1.1');spin()
        self.assertFalse(w.reference_preview.open_here.get_sensitive())
        self.assertFalse(w.reference_preview.open_new.get_sensitive())
        self.assertEqual((tab.state.reference,tab.state.history),before)
        self.assertEqual(len(refs.rows),2)
        tab.state.resource=None;tab.load_resource();w.tab_changed(tab);spin()
        self.assertEqual(refs.rows,[])
        self.assertEqual(refs.model.get_n_items(),0)
        self.assertIsNone(refs.context)

    def test_complete_range_titles_and_bounded_unavailable_excerpt_keep_records(self):
        from bible.study_references import ReferenceItem
        from bible.reference_data import Relationship
        from bible.reference_preview import passage_title
        self.install();refs=self.show();w=self.window
        item=ReferenceItem(Relationship('John.3.16','John.3.18',20,1),refs.context,refs.generation)
        button=refs.button();refs.fill(button,item);title,excerpt=button._reference_labels
        self.assertEqual(title.get_text(),passage_title('John.3.16','John.3.18','KJV'))
        self.assertNotIn('…',title.get_text());self.assertEqual(excerpt.get_lines(),3)
        self.assertTrue(excerpt.get_text())  # Missing final verse retains the complete target.
        self.assertEqual(len(button._reference_labels),2)
        self.assertEqual(len(refs.rows),2);self.assertFalse(refs.view_all.get_visible())

    def test_inline_footer_exact_total_expand_and_return_preserve_source_and_order(self):
        from bible.reference_data import Relationship
        self.install();refs=self.show();w=self.window;tab=w.active_tab
        rows=[Relationship(f'John.3.{i+1}',f'John.3.{i+1}',99-i,1) for i in range(30)]
        refs.rows=rows;refs.populate();spin()
        self.assertEqual(refs.model.get_n_items(),5)
        self.assertIn('30',refs.view_all.get_label());self.assertTrue(refs.view_all.get_visible())
        self.assertIs(refs.footer.get_first_child(),refs.view_all)
        self.assertIsNotNone(refs.footer.get_ancestor(type(refs.list)))
        before=(tab.state.reference,list(tab.state.history))
        refs.show_all();spin();self.assertEqual(refs.model.get_n_items(),30)
        self.assertTrue(refs.return_results.get_visible());self.assertFalse(refs.view_all.get_visible())
        self.assertEqual(refs.rows,rows)
        refs.show_initial();spin();self.assertEqual(refs.model.get_n_items(),5)
        self.assertFalse(refs.return_results.get_visible())
        self.assertEqual((tab.state.reference,tab.state.history),before)
