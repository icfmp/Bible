import os
from pathlib import Path
import tempfile
import unittest
from tests.test_ui import installed_fixture, spin


@unittest.skipUnless(os.environ.get('DISPLAY'), 'Requires GTK/Pango')
class VerseTypographyTests(unittest.TestCase):
    def test_marker_and_first_word_stay_on_one_line_and_page(self):
        from bible.ui import Application, Window, Library
        from bible.paged_sources import BiblePages
        from bible.pagination import paginate
        app = Application.get_default() or Application(); app.register()
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory, entries=[(f'Ps.119.{v}', 'Au commencement, mots de contrôle. '*3) for v in [1, 12, 123]])
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
                        self.assertNotIn('\u00a0',document.text)
            finally:window.close()
