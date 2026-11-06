import os
from pathlib import Path
import tempfile
import unittest
from bible.pagination import Anchor,Document,PassageSpan,StyleSpan,paginate
from bible.preferences import ReadingPreferences
from bible.paged_sources import BiblePages,PagedStream


class AnchorTests(unittest.TestCase):
    def test_chapter_anchor_displays_the_chapter_after_its_leading_separator(self):
        from bible.pagination import Page,PagePlan
        document=Document('fixture','A\n\nChapter\nB',(
            PassageSpan('Gen.1.1',0,0,1),PassageSpan('Gen.2.1',1,11,12)))
        plan=PagePlan(document,(Page(0,3),Page(3,12)))
        anchor=Anchor('Gen.2.1',0,False)
        self.assertEqual(document.locate(anchor),1)
        self.assertEqual(plan.page_for_anchor(anchor),1)
        self.assertEqual(document.locate(anchor),1)  # Copy/selection offsets stay exact.


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native Pango/GTK')
class PaginationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bible.ui import Gtk
        Gtk.init();cls.widget=Gtk.TextView()

    def test_bounded_shaping_matches_one_native_layout_exactly(self):
        from bible.pagination import attributes,shaped_lines
        from bible.reading_metrics import line_spacing
        from gi.repository import Pango
        # Exercise real paragraph boundaries, neutral lines, bidi, combining
        # marks and formatting that crosses the bounded-layout boundary.
        text=('Title\n\nÉcriture e\u0301 Ελληνικά עברית العربية — '+('mixed words '*28)+'\n123 —\n')*30
        document=Document('fixture',text,(),(StyleSpan('heading',0,5),
            StyleSpan('italic',2800,6500),StyleSpan('number',4400,4402)))
        for size,alignment in [(12,'left'),(19,'justified'),(64,'left')]:
            with self.subTest(size=size,alignment=alignment):
                prefs=ReadingPreferences(size=size,alignment=alignment)
                layout=self.widget.create_pango_layout(text)
                layout.set_font_description(Pango.FontDescription(f'{prefs.font} {size}'))
                layout.set_width(290*Pango.SCALE);layout.set_wrap(Pango.WrapMode.WORD_CHAR)
                layout.set_justify(alignment=='justified');layout.set_spacing(line_spacing(prefs)*Pango.SCALE)
                layout.set_attributes(attributes(document,context=self.widget.get_pango_context(),preferences=prefs))
                offsets={0:0};byte=0
                for index,char in enumerate(text):byte+=len(char.encode());offsets[byte]=index+1
                iterator=layout.get_iter();expected=[]
                while True:
                    line=iterator.get_line_readonly();_,logical=iterator.get_line_extents()
                    expected.append((offsets[line.start_index],logical.y/Pango.SCALE,logical.height/Pango.SCALE))
                    if not iterator.next_line():break
                self.assertEqual(list(shaped_lines(self.widget,document,prefs,290,0,len(text))),expected)

    def test_heading_visibility_removes_generated_prefix_only(self):
        from tests.test_ui import installed_fixture
        from bible.sword_provider import Reader
        from bible.library import Library
        with tempfile.TemporaryDirectory() as directory:
            root=installed_fixture(directory,entries=[('Gen.1.1','SOURCE TEXT'),('Gen.1.2','SECOND VERSE')])
            source=BiblePages(Reader(root,'Test'),Library(Path(directory)/'translations').resource('Test'))
            shown=source.document('Gen.1',ReadingPreferences())
            hidden=source.document('Gen.1',ReadingPreferences(chapter_numbers=False))
            prefix=shown.text.index('1\u00a0SOURCE')
            self.assertEqual(hidden.text,shown.text[prefix:])
            self.assertFalse(any(s.kind=='chapter' for s in hidden.styles))
            self.assertEqual([s.reference for s in hidden.spans],[s.reference for s in shown.spans])
            self.assertEqual(hidden.copy(0,len(hidden.text)),shown.copy(prefix,len(shown.text)))

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
