"""Native SWORD links are shared source units, not repeated text matches."""
import os
from pathlib import Path
import tempfile
import unittest


def linked_fixture(directory,name='Linked'):
    from tests.test_ui import installed_fixture
    import Sword
    root=installed_fixture(directory,name,entries=[
        ('Gen.1.1','ONE SHARED SOURCE UNIT'),('Gen.1.2','REPLACED ALIAS SLOT'),
        ('Gen.1.3','IDENTICAL UNLINKED TEXT'),('Gen.1.4','IDENTICAL UNLINKED TEXT')])
    module=Sword.RawText(str(root/'modules/texts/rawtext/test'),name,'Synthetic links')
    module.setKey(Sword.VerseKey('Gen.1.2'));module.linkEntry(Sword.VerseKey('Gen.1.1'))
    del module
    return root


class LinkedReaderTests(unittest.TestCase):
    def test_alias_lookup_keeps_all_references_and_unique_units_keep_real_repetition(self):
        from bible.sword_provider import Reader,passage_verses
        with tempfile.TemporaryDirectory() as directory:
            reader=Reader(linked_fixture(directory),'Linked');chapter=reader.chapter('Gen.1.2')
            self.assertEqual(chapter.links,(('Gen.1.2','Gen.1.1'),))
            self.assertEqual(dict(chapter.verses)['Gen.1.2'],'ONE SHARED SOURCE UNIT')
            self.assertEqual([ref for ref,_ in chapter.unique_verses()],['Gen.1.1','Gen.1.3','Gen.1.4'])
            self.assertEqual(sum(text=='IDENTICAL UNLINKED TEXT' for _,text in chapter.unique_verses()),2)
            self.assertEqual(chapter.label('Gen.1.2'),'1–2')
            self.assertEqual(passage_verses(reader,['Gen.1.2','Gen.1.1','Gen.1.4']),
                             (('Gen.1.2','ONE SHARED SOURCE UNIT'),('Gen.1.4','IDENTICAL UNLINKED TEXT')))
            from bible.reference_targets import local_excerpt
            excerpt=local_excerpt(reader,'Gen.1.1','Gen.1.2',source_system='KJV')
            self.assertEqual((excerpt.start,excerpt.end),('Gen.1.1','Gen.1.2'))
            self.assertEqual(excerpt.verses,(('Gen.1.1','ONE SHARED SOURCE UNIT'),))
            from bible.text_search import index,query_index
            path=index(Path(directory)/'translations','Linked',reader)
            self.assertEqual(query_index(path,'SHARED')['references'],['Gen.1.1'])
            self.assertEqual(query_index(path,'IDENTICAL')['references'],['Gen.1.3','Gen.1.4'])


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK')
class LinkedLayoutTests(unittest.TestCase):
    def test_note_on_alias_remains_visible_and_draft_data_is_unchanged(self):
        from bible.ui import Application,Window,Library
        from tests.test_ui import spin,close_test_dialogs
        with tempfile.TemporaryDirectory() as directory:
            linked_fixture(directory)
            app=Application.get_default() or Application();app.register()
            window=Window(app,Library(Path(directory)/'translations'));window.present();spin()
            try:
                tab=window.active_tab;tab.navigate('Linked','Gen.1.2')
                note=window.notes_store.save('Alias-specific personal note',[],versification='KJV',
                    start='Gen.1.2',end='Gen.1.2',origin_translation='Linked',origin_language='en')
                before=window.notes_store.all();window.notes_changed();spin()
                self.assertEqual(len(tab.text._inline_buttons),1)
                tab.text._inline_buttons[0].emit('clicked');spin()
                self.assertEqual(window.study.tool,'notes')
                self.assertEqual(len(window.study.notes.rows),1)
                self.assertEqual(window.notes_store.all(),before)
                self.assertEqual(window.notes_store.all()[0].start,'Gen.1.2')
                self.assertEqual(tab._document.copy(0,len(tab._document.text)).count('ONE SHARED SOURCE UNIT'),1)
            finally:close_test_dialogs();window.close()

    def test_render_alias_navigation_selection_and_copy_use_one_unit(self):
        from bible.ui import Application,Window,Library
        from bible.pagination import Anchor
        from bible.passage_actions import target
        from tests.test_ui import spin
        with tempfile.TemporaryDirectory() as directory:
            linked_fixture(directory)
            app=Application.get_default() or Application();app.register()
            window=Window(app,Library(Path(directory)/'translations'));window.present();spin()
            try:
                tab=window.active_tab;self.assertTrue(tab.navigate('Linked','Gen.1.2'));spin(lambda:not tab._restoring_scroll)
                document=tab._document;span=document.spans[0]
                self.assertEqual(span.members,('Gen.1.1','Gen.1.2'))
                self.assertEqual(document.copy(0,len(document.text)).count('ONE SHARED SOURCE UNIT'),1)
                self.assertEqual(document.copy(0,len(document.text)).count('IDENTICAL UNLINKED TEXT'),2)
                self.assertEqual(tab._verse_offsets['Gen.1.1'],tab._verse_offsets['Gen.1.2'])
                self.assertEqual(document.locate(Anchor('Gen.1.2',0,True)),span.body)
                self.assertTrue(tab.select_verse('Gen.1.2'))
                self.assertEqual(tab.selected_passage(),('Gen.1.1','Gen.1.2'))
                buffer=tab.text.get_buffer();buffer.select_range(buffer.get_iter_at_offset(span.body),buffer.get_iter_at_offset(span.end))
                source=window.passage_actions.ordinary(tab)
                value=target(tab.text,source,lambda:source)
                self.assertEqual(value.references,span.members)
                self.assertEqual(value.verses,('ONE SHARED SOURCE UNIT',))
            finally:window.close()

    def test_shared_comparison_aligns_a_linked_unit_with_both_other_verses(self):
        from bible.ui import Application,Window,Library
        from tests.test_ui import installed_fixture,spin
        with tempfile.TemporaryDirectory() as directory:
            linked_fixture(directory)
            installed_fixture(directory,'Other',entries=[(f'Gen.1.{v}',f'OTHER SOURCE {v}') for v in range(1,5)])
            app=Application.get_default() or Application();app.register()
            window=Window(app,Library(Path(directory)/'translations'));window.set_default_size(1200,850);window.present();spin()
            try:
                tab=window.active_tab;tab.navigate('Linked','Gen.1.1')
                tab.state.comparison='Other';window.sync_comparison();spin(duration=.5)
                self.assertTrue(tab._shared_comparison)
                row=tab.comparison_rows.rows[0]
                self.assertEqual(row.primary,('Gen.1.1','Gen.1.2'))
                self.assertEqual(row.secondary,('Gen.1.1','Gen.1.2'))
                self.assertEqual(tab._document.copy(0,len(tab._document.text)).count('ONE SHARED SOURCE UNIT'),1)
                self.assertEqual(tab._comparison_document.copy(0,len(tab._comparison_document.text)).count('OTHER SOURCE'),4)
                window.end_comparison();spin()
                self.assertEqual(tab._document.spans[0].members,('Gen.1.1','Gen.1.2'))
            finally:window.close()
