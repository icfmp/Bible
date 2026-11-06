"""Distinct native acceptance checks for the November Ready reading/notes batch."""
import os
from pathlib import Path
import tempfile
import unittest
import subprocess
import sys
from functools import wraps
from unittest.mock import patch
from tests.test_ui import installed_fixture,spin,close_test_dialogs


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK and native X11 input')
class ReadyReadingNotesTests(unittest.TestCase):
    def setUp(self):
        if os.environ.get('BIBLE_TEST_ISOLATED_CLICK')!='1':return
        from bible.ui import Application,Window,Library
        from tools.check_alpha_ui import X11Input
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        entries=[('Gen.1.1','FIRST SOURCE <note n="a" type="translation">SOURCE NOTE &amp; literal</note>'),
            ('Gen.1.2','NEXT VERSE'),('Gen.2.1','ANOTHER CHAPTER'),('John.3.16','ANOTHER BOOK'),('Jude.1.1','ONE CHAPTER')]
        installed_fixture(self.root,'First',entries=entries)
        config=self.root/'translations/First/mods.d/test.conf'
        config.write_text(config.read_text().replace('SourceType=Plaintext','SourceType=OSIS')+'GlobalOptionFilter=OSISFootnotes\n')
        installed_fixture(self.root,'Second',entries=[('Gen.1.1','SECOND SOURCE'),('Gen.2.1','SECOND CHAPTER')])
        app=Application.get_default() or Application();app.register()
        self.w=Window(app,Library(self.root/'translations'));self.w.set_default_size(1200,860);self.w.present()
        self.assertEqual((self.w.active_tab.state.resource,self.w.active_tab.state.reference),('First','Gen.1.1'))
        spin(lambda:not self.w._controls_tick and not self.w.active_tab._restoring_scroll,duration=.3,timeout=15)
        self.native=X11Input();self.native.activate(self.w)

    def tearDown(self):
        if os.environ.get('BIBLE_TEST_ISOLATED_CLICK')!='1':return
        if self.w.note_editor:self.w.note_editor._discard=True;self.w.note_editor.cancel_autosave()
        close_test_dialogs();self.w.close();self.native.close()

    def note(self):
        return self.w.notes_store.save('Existing **bold** and *italic* Unicode é.',('Retained',),
            versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation='First',origin_language='en')

    def chord(self,modifier,key):
        n=self.native;code=n.x11.XKeysymToKeycode(n.display,n.x11.XStringToKeysym(modifier.encode()))
        n.xtest.XTestFakeKeyEvent(n.display,code,True,0)
        try:n.key(key)
        finally:n.xtest.XTestFakeKeyEvent(n.display,code,False,0);n.x11.XFlush(n.display);spin()

    def test_185_source_note_mouse_and_keyboard_keep_scripture_and_other_markers(self):
        w=self.w;view=w.active_tab.text
        button=next(b for b in view._inline_buttons if b._marker_kind=='translation-note')
        original=w.active_tab._document.copy(0,len(w.active_tab._document.text))
        self.assertNotIn('SOURCE NOTE',original);self.assertEqual(button.get_cursor().get_name(),'pointer')
        self.native.move_at(button,button.get_width()/2,button.get_height()/2);spin(duration=.9)
        self.assertFalse(w.has_css_class('source-note-tooltip'))
        for keyboard in (False,True,False):
            if keyboard:button.grab_focus();self.native.key('space')
            else:self.native.click(button)
            spin();self.assertTrue(button._source_note_popover and button._source_note_popover.get_visible())
            self.assertIs(button._source_note_popover.get_parent(),w.active_tab.reading_overlay)
            self.assertGreater(button._source_note_popover.get_child().get_width(),200)
            self.native.key('Escape');spin();self.assertFalse(button._source_note_popover and button._source_note_popover.get_visible())
        self.assertEqual(w.active_tab._document.copy(0,len(w.active_tab._document.text)),original)
        self.assertEqual(w.active_tab.state.reference,'Gen.1.1')

    def test_187_execution_uses_current_translation_and_enter(self):
        w=self.w;w.show_search('text');panel=w.search_popover.text_search
        spin(duration=.3)
        self.assertLess(w.search_popover.get_height(),240)
        panel.entry.set_text('SECOND');w.active_tab.navigate('Second','Gen.1.1');spin()
        panel.entry.grab_focus();self.native.key('Return');spin(lambda:not panel.pending,timeout=20)
        self.assertEqual(panel.context[0],'Second');self.assertFalse(panel.source.get_visible())
        self.assertTrue(panel.rows)
        self.assertTrue(panel.result_scroll.get_mapped())
        panel.entry.set_text('');spin(duration=.3)
        self.assertLess(w.search_popover.get_height(),240)

    def test_188_text_and_topics_keep_the_same_bounded_width(self):
        w=self.w;widths=[]
        for mode in ('text','topics','text'):
            w.show_search(mode);spin(lambda:w.search_popover.get_mapped(),duration=.3);widths.append(w.search_popover.content.get_width())
        self.assertEqual(len(set(widths)),1,widths);self.assertGreaterEqual(widths[0],450);self.assertLessEqual(widths[0],500)

    def test_189_three_tabs_and_separate_translation_notes_action(self):
        w=self.w;w.study_button.set_active(True);spin()
        self.assertEqual(w.study.tools.get_pages().get_n_items(),3)
        self.assertFalse(w.study.notes.heading.get_parent());self.assertFalse(w.study.references.heading.get_parent())
        for tool in ('notes','references','commentaries'):
            w.study.tools.set_visible_child_name(tool);spin();self.assertTrue(w.study.context_heading.get_mapped())
        self.native.click(w.study.translation_notes_button);spin();self.assertEqual(w.study.tool,'translation-notes')
        self.native.click(w.study.translation_notes_button);spin();self.assertEqual(w.study.tool,'commentaries')

    def test_190_download_actions_are_secondary_and_share_the_library_route(self):
        w=self.w
        for chooser,target in ((w.primary_version,'bible'),(w.compared_version,'comparison')):
            self.assertTrue(chooser.download_more.has_css_class('flat'))
            with patch.object(w,'contextual_library') as open_library:
                chooser.download_more.emit('clicked');open_library.assert_called_once_with('bible',target)
        self.assertTrue(w.download_comparison.has_css_class('flat'))

    def test_191_visible_elements_state_survives_reopening_without_layout_controls(self):
        w=self.w;w.appearance.visible_elements.set_expanded(False)
        self.assertFalse(w.preferences.value.visible_elements_expanded)
        from bible.preferences import Preferences
        self.assertFalse(Preferences(self.root/'reading-preferences.json').value.visible_elements_expanded)
        self.assertFalse(hasattr(w.appearance,'line_spacing'));self.assertFalse(hasattr(w.appearance,'column_width'))

    def test_193_header_order_matches_visible_and_keyboard_order(self):
        w=self.w;buttons=(w.search_button,w.comparison_button,w.appearance_button,w.immersive_button,w.study_button,w.menu)
        bounds=[button.compute_bounds(w)[1].get_x() for button in buttons]
        self.assertEqual(bounds,sorted(bounds));self.assertEqual(len(set(bounds)),len(buttons))
        child=w.reader_controls.get_first_child();ordered=[]
        while child:ordered.append(child);child=child.get_next_sibling()
        self.assertEqual(ordered,list(buttons[:4]))

    def test_192_hiding_generated_heading_preserves_source_text_and_preference(self):
        w=self.w;tab=w.active_tab;before=tab._document
        source_body=before.copy(before.spans[0].body,len(before.text))
        w.appearance.chapter_numbers.set_active(False);spin()
        after=tab._document
        self.assertFalse(any(s.kind=='chapter' for s in after.styles))
        self.assertEqual(after.copy(after.spans[0].body,len(after.text)),source_body)
        self.assertEqual(tab.state.reference,'Gen.1.1')
        from bible.preferences import Preferences
        self.assertFalse(Preferences(self.root/'reading-preferences.json').value.chapter_numbers)

    def test_198_swatches_match_applied_highlights_and_original_text_is_icon_only(self):
        from bible.highlights import COLORS
        from gi.repository import Gtk,Gdk
        from bible.i18n import tr
        w=self.w;tab=w.active_tab;actions=w.passage_actions;buffer=tab.text.get_buffer()
        first=tab._marker_ends['Gen.1.1'];buffer.select_range(buffer.get_iter_at_offset(first),buffer.get_iter_at_offset(first+5))
        actions.capture(tab.text,lambda:actions.ordinary(tab,False),None);spin()
        self.assertIsInstance(actions.word_button.get_child(),Gtk.Image)
        self.assertEqual(actions.word_button.get_child().get_icon_name(),'accessories-dictionary-symbolic')
        self.assertTrue(Gtk.IconTheme.get_for_display(w.get_display()).has_icon('accessories-dictionary-symbolic'))
        self.assertEqual(actions.word_button.get_tooltip_text(),tr('Study original text'))
        for color,(hexcolor,_) in COLORS.items():
            actions.highlight_buttons[color][0].emit('clicked');spin()
            self.assertEqual(w.highlights.entries[('KJV','Gen.1.1')]['color'],color)
            actual=buffer.get_tag_table().lookup('highlight-'+color).props.background_rgba
            expected=Gdk.RGBA();expected.parse(hexcolor)
            self.assertEqual(actual.to_string(),expected.to_string())

    def test_194_font_slots_and_study_size_are_independent_and_persisted(self):
        w=self.w;p=w.preferences.value
        w.appearance.update('serif_font','DejaVu Serif');w.appearance.update('sans_font','DejaVu Sans Mono')
        w.appearance.fonts['simple'].emit('clicked');self.assertEqual(p.font,'DejaVu Sans Mono')
        w.appearance.update('study_size',19);self.assertEqual(w.study.sidebar_preferences.size,19)
        self.assertEqual(p.size,14);w.appearance.fonts['book'].emit('clicked');self.assertEqual(p.font,'DejaVu Serif')
        from bible.preferences import Preferences
        self.assertEqual(Preferences(self.root/'reading-preferences.json').value,p)
        from bible.application_surfaces import show_preferences
        dialog=show_preferences(w);dialog.set_visible_page(dialog.reading_settings.page);spin()
        self.assertTrue(dialog.reading_settings.typography_heading.get_mapped())
        dialog.close()

    def test_196_single_sidebar_owner_and_keyboard_resizing(self):
        w=self.w;w.study_button.set_active(True);spin()
        self.assertFalse(w.study.has_css_class('sidebar-pane'))
        self.assertTrue(w.study_divider.get_mapped());w.study_divider.grab_focus()
        before=w.study_settings.width;self.native.key('Left');spin()
        self.assertNotEqual(w.study_settings.width,before);self.assertEqual(w.active_tab.state.reference,'Gen.1.1')

    def test_197_single_chapter_book_opens_directly(self):
        w=self.w;w.choose_passage();spin();nav=w.navigation
        row=nav.book_rows['Jude'];nav.book_list.emit('row-activated',row);spin()
        self.assertEqual(w.active_tab.state.reference,'Jude.1.1');self.assertFalse(nav.get_visible())

    def test_200_direct_formatting_typing_and_undo_preserve_markdown(self):
        w=self.w;note=self.note();editor=w.edit_note(note=note);spin();self.native.activate(editor)
        buffer=editor.body.get_buffer();self.assertEqual(editor.body.source(),note.body);self.assertFalse(editor.dirty)
        self.assertNotIn('**',buffer.get_text(*buffer.get_bounds(),False));self.assertFalse(hasattr(editor,'stack'))
        buffer.set_text('');editor.body.grab_focus();self.chord('Control_L','b');self.native.key('x')
        self.assertIn('x',editor.body.source());self.assertIn('**',editor.body.source())
        self.assertEqual(buffer.get_text(*buffer.get_bounds(),False),'x')
        self.assertTrue(buffer.get_iter_at_offset(editor.body.source().index('x')).has_tag(editor.body.tags['bold']))
        self.chord('Control_L','z');self.assertNotIn('x',editor.body.source())
        buffer.set_text(note.body);self.assertTrue(editor.save(close=False));self.assertEqual(w.notes_store.get(note.id).body,note.body)

    def test_201_workspace_autosaves_without_a_redundant_menu(self):
        w=self.w;note=self.note();space=w.open_notes();space.open_note(note);spin()
        self.assertFalse(hasattr(space,'save_button'));self.assertFalse(hasattr(space,'delete_button'))
        space.editor.body.get_buffer().insert_at_cursor(' Updated')
        spin(lambda:w.notes_store.get(note.id).body.endswith(' Updated'),timeout=5)
        self.assertEqual(w.notes_store.get(note.id).id,note.id)

    def test_200_legacy_lists_remain_rendered_and_unchanged_when_only_labels_change(self):
        w=self.w;note=self.note()
        original='- Legacy **bold** item\n* Another *italic* item'
        note=w.notes_store.save(original,note.labels,existing=note)
        editor=w.edit_note(note=note);spin();buffer=editor.body.get_buffer()
        self.assertEqual(buffer.get_text(*buffer.get_bounds(),False),'• Legacy bold item\n• Another italic item')
        self.assertEqual(editor.body.source(),original);self.assertFalse(editor.dirty)
        editor.labels.entry.set_text('Added');self.assertTrue(editor.save(close=False))
        self.assertEqual(w.notes_store.get(note.id).body,original)
        editor.close();spin();editor=w.edit_note(note=w.notes_store.get(note.id));spin()
        self.assertEqual(editor.body.source(),original);self.assertFalse(editor.dirty)

    def test_201_continuous_typing_is_committed_before_the_burst_ends(self):
        from gi.repository import GLib
        from bible.notes import NoteStore
        from bible.notes_window import buffer_text
        w=self.w;note=self.note();space=w.open_notes();space.open_note(note);spin()
        editor=space.editor;typed=[0]
        def type_more():
            editor.body.get_buffer().insert_at_cursor('x');typed[0]+=1
            return typed[0]<20
        timer=GLib.timeout_add(80,type_more)
        try:
            spin(lambda:typed[0]>=12,duration=.01,timeout=5)
            self.assertLess(typed[0],20)
            # A separate connection observes a durable write during typing.
            witness=NoteStore(self.root/'notes.sqlite3')
            try:self.assertNotEqual(witness.get(note.id).body,note.body)
            finally:witness.close()
            self.assertIs(space.editor,editor)
            spin(lambda:typed[0]==20,timeout=5)
            spin(lambda:w.notes_store.get(note.id).body==buffer_text(editor.body),timeout=5)
        finally:
            if typed[0]<20:GLib.source_remove(timer)

    def test_202_offline_manual_links_are_shared_and_restored_once(self):
        from bible.notes import NoteStore
        from bible.highlights import HighlightStore
        from bible import personal_backup
        w=self.w;note=self.note();editor=w.edit_note(note=note)
        with patch('urllib.request.urlopen',side_effect=AssertionError('Offline')):
            editor.links.entry.set_text('Jean 3:16');self.assertTrue(editor.links.add())
            editor.links.entry.set_text('John 3:16');self.assertFalse(editor.links.add());editor.links.entry.set_text('')
            self.assertTrue(editor.save())
        saved=w.notes_store.get(note.id);self.assertEqual(len(saved.links),1);self.assertEqual(saved.body,note.body)
        w.active_tab.navigate('First','John.3.16');w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes');spin()
        self.assertEqual([n.id for n in w.study.notes.rows],[note.id])
        self.assertTrue(any(b._marker_kind=='note' for b in w.active_tab.text._inline_buttons))
        file=self.root/'links.json';personal_backup.export(w.notes_store,w.highlights,file)
        target=self.root/'restored';target.mkdir();notes=NoteStore(target/'notes.sqlite3')
        try:
            marks=HighlightStore(target/'highlights.json');personal_backup.restore(notes,marks,file)
            self.assertEqual(notes.get(note.id),saved);self.assertEqual(len(notes.all()),1)
        finally:notes.close()

    def test_202_existing_cross_references_offer_explicit_non_blocking_suggestions(self):
        from tests.test_reference_data import archive
        from bible import reference_data
        w=self.w;file=self.root/'references.zip';digest=archive(file,'Gen.1.1\tJohn.3.16\t15\n')
        with patch.object(reference_data,'ARCHIVE_SHA256',digest):w.study.references.data.install_archive(file)
        note=self.note();editor=w.edit_note(note=note);spin();self.native.activate(editor)
        links=editor.links;self.native.click(links.add_button)
        spin(lambda:links.suggestions.get_visible(),timeout=10)
        self.assertEqual(links.values,());self.assertEqual(w.notes_store.get(note.id).links,())
        links.suggestions.set_expanded(True);spin()
        choice=next(child for child in self.children(links.suggestion_rows) if hasattr(child,'_linked_passage'))
        self.native.click(choice);spin()
        self.assertEqual([(link.start,link.end) for link in links.values],[('John.3.16','John.3.16')])
        self.assertEqual(w.notes_store.get(note.id).links,())
        self.assertTrue(editor.save(close=False));self.assertEqual(w.notes_store.get(note.id).links,links.values)

    @staticmethod
    def children(widget):
        child=widget.get_first_child()
        while child:yield child;child=child.get_next_sibling()


def isolated_input(method):
    """Native grabs/focus must not be inherited from unrelated suite windows."""
    @wraps(method)
    def run(self):
        if os.environ.get('BIBLE_TEST_ISOLATED_CLICK')=='1':return method(self)
        result=subprocess.run(['dbus-run-session','--','xvfb-run','-a',sys.executable,
            '-m','tools.composited_x11',sys.executable,'-X','faulthandler',
            '-m','unittest',self.id(),'-v'],env=dict(os.environ,BIBLE_TEST_ISOLATED_CLICK='1'),
            capture_output=True,text=True,timeout=90)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
    return run


for name in unittest.defaultTestLoader.getTestCaseNames(ReadyReadingNotesTests):
    setattr(ReadyReadingNotesTests,name,isolated_input(getattr(ReadyReadingNotesTests,name)))
