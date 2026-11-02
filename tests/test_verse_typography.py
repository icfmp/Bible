import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture, spin


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires GTK/Pango')
class VerseTypographyTests(unittest.TestCase):
    def test_no_space_script_wraps_without_detaching_its_marker_or_changing_copy(self):
        from bible.ui import Gtk
        from bible.bible_render import render
        from bible.preferences import ReadingPreferences
        from bible.sword_provider import Reader
        text='甲乙丙丁戊己庚辛壬癸'*8
        with tempfile.TemporaryDirectory() as directory:
            root=installed_fixture(directory,entries=[('Gen.1.1',text)])
            reader=Reader(root,'Test');view=Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
            view.set_left_margin(20);view.set_right_margin(20)
            scroll=Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER);scroll.set_child(view)
            window=Gtk.Window(default_width=360,default_height=400);window.set_child(scroll);window.present()
            try:
                for size in (16,28):
                    preferences=ReadingPreferences(size=size)
                    document,offsets,ranges,markers=render(view,reader,reader.chapter('Gen.1.1'),preferences)
                    spin();buffer=view.get_buffer();span=document.spans[0]
                    visible=view.get_visible_rect()
                    right=max(view.get_iter_location(buffer.get_iter_at_offset(i)).x for i in range(span.body,span.end))
                    self.assertLessEqual(right,visible.x+visible.width-20+2)
                    self.assertEqual(view.get_line_yrange(buffer.get_iter_at_offset(offsets['Gen.1.1']))[0],
                                     view.get_line_yrange(buffer.get_iter_at_offset(span.body))[0])
                    self.assertEqual(document.copy(span.body,span.end),text)
            finally:window.destroy();spin()

    def test_marker_and_first_word_stay_on_one_line_and_page(self):
        from bible.ui import Application, Window, Library
        from bible.paged_sources import BiblePages
        from bible.pagination import paginate
        app = Application.get_default() or Application(); app.register()
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory, entries=[(f'Ps.119.{v}', '\u2009Au commencement, mots de contrôle. '*3) for v in [1, 12, 123]])
            window = Window(app, Library(Path(directory)/'translations')); window.present()
            try:
                tab = window.active_tab; tab.navigate('Test','Ps.119.1')
                for family in ['DejaVu Serif', 'DejaVu Sans']:
                    for spacing in ['tight','very-airy']:
                        window.appearance.update('font',family)
                        window.appearance.update('line_spacing',spacing)
                        spin(lambda:not tab._restoring_scroll)
                        buffer = tab.text.get_buffer()
                        for reference, marker in tab._verse_offsets.items():
                            body = tab._marker_ends[reference]
                            first = buffer.get_iter_at_offset(marker)
                            word = buffer.get_iter_at_offset(body+1)
                            self.assertEqual(tab.text.get_line_yrange(first)[0],tab.text.get_line_yrange(word)[0])
                        document = BiblePages(tab.reader,window.library.resource('Test')).document('Ps.119',tab.preferences)
                        plan = paginate(tab.text,document,tab.preferences,210,130)
                        for page in plan.pages:
                            for style in document.styles:
                                if style.kind=='verse-start':
                                    self.assertFalse(style.start < page.end < style.end)
                        self.assertNotIn('\u2060',document.text)
                        self.assertNotIn('\u00a0',document.copy(0,len(document.text)))
                        # Native Ctrl+C uses the original characters rather than
                        # the nonbreaking presentation spaces in its buffer.
                        buffer.select_range(buffer.get_start_iter(),buffer.get_end_iter())
                        values=[]
                        tab.text.emit('copy-clipboard')
                        def copied(clipboard,result):values.append(clipboard.read_text_finish(result))
                        tab.text.get_clipboard().read_text_async(None,copied)
                        spin(lambda:bool(values))
                        self.assertEqual(values[0],tab._document.copy(0,len(tab._document.text)))
                        self.assertNotIn('\u00a0',values[0])
            finally:window.close()
