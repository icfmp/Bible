import os
from pathlib import Path
import tempfile
import unittest
from bible.pagination import Anchor,Document,PassageSpan,StyleSpan,paginate
from bible.preferences import ReadingPreferences
from bible.paged_sources import BiblePages,PagedStream
from bible.immersion_hints import ImmersionHints


class HintTests(unittest.TestCase):
    def test_notification_hint_is_only_local_and_preserves_bad_original(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'hint.json';hints=ImmersionHints(path)
            self.assertFalse(hints.disabled);self.assertTrue(hints.disable())
            self.assertTrue(ImmersionHints(path).disabled)
            path.write_text('{broken');hints=ImmersionHints(path)
            self.assertFalse(hints.disable());self.assertEqual(path.read_text(),'{broken')


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native Pango/GTK')
class PaginationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bible.ui import Gtk
        Gtk.init();cls.widget=Gtk.TextView()

    def test_exact_unicode_partition_long_verse_inside_words_and_reflow_anchor(self):
        text='TITLE\n\n'+('Écriture Ελληνικά עברית العربية e\u0301 — source text. '*230)
        doc=Document('test',text,(PassageSpan('Gen.1.1',0,7,len(text)),),(StyleSpan('heading',0,5),))
        # Distinct title-prefix endpoints must not collapse to the verse start.
        for offset in range(7):self.assertEqual(doc.locate(doc.anchor(offset)),offset)
        for size in [12,19,64]:
            prefs=ReadingPreferences(size=size)
            plan=paginate(self.widget,doc,prefs,285,360)
            self.assertGreater(len(plan.pages),2)
            self.assertEqual(''.join(text[p.start:p.end] for p in plan.pages),text)
            for page in plan.pages:
                if page.start:self.assertFalse(__import__('unicodedata').combining(text[page.start]))
            old=plan.pages[len(plan.pages)//2];anchor=doc.anchor(old.start)
            resized=paginate(self.widget,doc,prefs,415,490,anchor)
            page=resized.pages[resized.containing(doc.locate(anchor))]
            self.assertEqual(doc.anchor(page.start),anchor)

    def test_real_sword_chapter_boundaries_and_spread_roundtrip(self):
        from tests.test_ui import installed_fixture
        from bible.sword_provider import Reader
        from bible.library import Library
        with tempfile.TemporaryDirectory() as directory:
            root=installed_fixture(directory,entries=[('Gen.1.1','FIRST SOURCE '*180),('Gen.1.2','SECOND SOURCE '*180),('Gen.2.1','NEXT CHAPTER SOURCE '*180)])
            source=BiblePages(Reader(root,'Test'),Library(Path(directory)/'translations').resource('Test'))
            stream=PagedStream(self.widget,source,ReadingPreferences())
            stream.configure(300,320,Anchor('Gen.1.1'),source.key('Gen.1.1'))
            initial=stream.cursor;seen=[]
            while True:
                for address in stream.spread(2):
                    plan=stream.plan(address.key);page=plan.pages[address.index]
                    seen.append((address,plan.document.text[page.start:page.end]))
                old=stream.cursor
                if not stream.turn(1,2):break
                self.assertTrue(stream.turn(-1,2));self.assertEqual(stream.cursor,old)
                self.assertTrue(stream.turn(1,2))
            expected=''.join(source.document(key,stream.preferences).text for key in ['Gen.1','Gen.2'])
            self.assertEqual(''.join(text for _,text in seen),expected)
            self.assertEqual(len({address for address,_ in seen}),len(seen))
