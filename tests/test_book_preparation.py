"""Real headless Pango checks; synthetic text is never a Bible resource."""
from concurrent.futures import CancelledError
from threading import Event
import time
import unittest

from bible.book_stream import BookStream, LayoutContext
from bible.pagination import Anchor, Document, PassageSpan, StyleSpan, heading_groups, paginate
from bible.preferences import ReadingPreferences
from bible.preparation import checkpoint


def synthetic_document(key='Mark', chapters=True, verses=True):
    pieces=[];styles=[];spans=[];offset=0
    for chapter in (7,8):
        prefix=(f'SYNTHETIC {key} {chapter}' if chapters else f'SYNTHETIC {key}')+'\n\n'
        styles.append(StyleSpan('chapter',offset,offset+len(prefix)-2))
        first=offset;pieces.append(prefix);offset+=len(prefix)
        heading='Synthetic section heading\n'
        styles.append(StyleSpan('heading',offset,offset+len(heading)))
        pieces.append(heading);offset+=len(heading)
        for verse in range(1,5):
            start=first if verse==1 else offset
            number=str(verse)+'\u00a0' if verses else ''
            if number:styles.append(StyleSpan('number',offset,offset+len(number)))
            pieces.append(number);offset+=len(number);body=offset
            text=('Écriture Ελληνικά עברית العربية e\u0301 — SYNTHETIC test. '*35)+'\n\n'
            if number:styles.append(StyleSpan('verse-start',body-len(number),body+8))
            pieces.append(text);offset+=len(text)
            spans.append(PassageSpan(f'{key}.{chapter}.{verse}',start,body,offset))
    text=''.join(pieces)
    return Document(key,text,tuple(spans),tuple(styles),text.replace('\u00a0',' '))


class SyntheticSource:
    """Controllable source with actual worker/layout execution, no SWORD mock."""
    def __init__(self):
        self.calls=[];self.clones=0;self.wait_for=None;self.entered=Event()
        self.cancelled=Event();self.release=Event()

    def clone(self):self.clones+=1;return self

    def document(self,key,preferences,*,cancelled=None):
        self.calls.append((key,preferences.chapter_numbers,preferences.verse_numbers))
        if key==self.wait_for:
            self.entered.set()
            try:
                while not self.release.wait(.005):checkpoint(cancelled)
            except CancelledError:
                self.cancelled.set();raise
        checkpoint(cancelled)
        return synthetic_document(key,preferences.chapter_numbers,preferences.verse_numbers)

    def neighbour(self,key,direction):
        keys=['Mark','Luke','John','Acts','Rom'];index=keys.index(key)+direction
        return keys[index] if 0<=index<len(keys) else None


class HeadlessPaginationTests(unittest.TestCase):
    def setUp(self):self.layout=LayoutContext(96,'en')

    def test_titles_stay_with_body_across_font_geometry_and_number_visibility(self):
        for size in (12,14,32,64):
            for height in (260,400,700):
                for numbers in (False,True):
                    with self.subTest(size=size,height=height,numbers=numbers):
                        prefs=ReadingPreferences(size=size,verse_numbers=numbers)
                        document=synthetic_document(verses=numbers)
                        plan=paginate(self.layout,document,prefs,350,height)
                        self.assertEqual(''.join(document.text[p.start:p.end] for p in plan.pages),document.text)
                        self.assertEqual(''.join(document.copy(p.start,p.end) for p in plan.pages),document.copy_text)
                        for first,last in heading_groups(document):
                            # This same group on an otherwise empty page tells
                            # whether keep-with-next can fit at this font/height.
                            text=document.text[first:last]
                            styles=tuple(StyleSpan(s.kind,max(0,s.start-first),min(last,s.end)-first)
                                         for s in document.styles if s.end>first and s.start<last)
                            probe=Document('group',text,(),styles)
                            if len(paginate(self.layout,probe,prefs,350,height).pages)==1:
                                self.assertEqual(plan.containing(first),plan.containing(last-1))
                        for style in document.styles:
                            if style.kind=='verse-start':
                                # If a marker/word itself exceeds the page's
                                # height, progress takes priority over grouping.
                                text=document.text[style.start:style.end]
                                probe=Document('word',text,(),(StyleSpan('number',0,2),))
                                if len(paginate(self.layout,probe,prefs,350,height).pages)==1:
                                    self.assertFalse(any(style.start<p.end<style.end for p in plan.pages))

    def test_anchor_in_heading_gap_keeps_chapter_and_section_with_body(self):
        doc=synthetic_document();title=next(s for s in doc.styles if s.kind=='heading')
        anchor=doc.anchor(title.end)
        plan=paginate(self.layout,doc,ReadingPreferences(),350,600,anchor)
        first,last=heading_groups(doc)[0]
        self.assertEqual(plan.containing(first),plan.containing(last-1))
        # A distant in-verse reflow still starts at its exact canonical anchor.
        anchor=doc.anchor(doc.spans[3].body+60)
        plan=paginate(self.layout,doc,ReadingPreferences(),400,600,anchor)
        self.assertEqual(doc.anchor(plan.pages[plan.containing(doc.locate(anchor))].start),anchor)

    def test_oversized_heading_makes_progress_and_unicode_text_is_unchanged(self):
        text=('OVERSIZED SYNTHETIC TITLE '*100)+'\n\n'+'Body e\u0301 עברית العربية '*40
        end=text.index('\n')
        doc=Document('long',text,(PassageSpan('Mark.8.1',0,end+2,len(text)),),
                     (StyleSpan('heading',0,end),))
        plan=paginate(self.layout,doc,ReadingPreferences(size=64),160,160)
        self.assertGreater(len(plan.pages),2)
        self.assertTrue(all(page.end>page.start for page in plan.pages))
        self.assertEqual(''.join(text[p.start:p.end] for p in plan.pages),text)

    def test_cancellation_reaches_native_layout_iteration(self):
        doc=synthetic_document();calls=0
        def cancelled():
            nonlocal calls
            calls+=1
            return calls>len(doc.styles)*4+50
        with self.assertRaises(CancelledError):
            paginate(self.layout,doc,ReadingPreferences(),350,400,cancelled=cancelled)

    def test_cancelled_sword_operations_do_not_touch_the_reader(self):
        from bible.sword_provider import Reader
        reader=object.__new__(Reader)  # No native manager is needed after cancellation.
        for operation in (reader.discover_books,reader.chapter,
                          lambda **kwargs:reader.structured_chapter(None,**kwargs)):
            with self.assertRaises(CancelledError):operation(cancelled=lambda:True)

    def test_book_composition_stops_before_reading_later_chapters(self):
        from bible.paged_sources import BibleBookPages
        from bible.sword_provider import Book,Chapter
        from bible.structured_text import Segment
        calls=[];stop=Event()
        class Key:
            def getOSISBookName(self):return 'Mark'
            def getBookName(self):return 'Mark'
            def getChapter(self):return int(calls[-1].split('.')[1])
        class Reader:
            def __init__(self):self.books=(Book('Mark','Mark',{7:(1,),8:(1,)}),)
            def key(self,reference):return Key()
            def chapter(self,reference,*,cancelled=None):
                calls.append(reference)
                return Chapter(reference.rsplit('.',1)[0],((reference,'SYNTHETIC BODY'),),None,None)
            def structured_chapter(self,chapter,*,cancelled=None):
                stop.set()
                return {reference:(Segment(text),) for reference,text in chapter.verses}
        source=BibleBookPages(Reader(),None)
        with self.assertRaises(CancelledError):
            source.document('Mark',ReadingPreferences(),cancelled=stop.is_set)
        self.assertEqual(calls,['Mark.7.1'])


class HeadlessBookStreamTests(unittest.TestCase):
    def setUp(self):
        self.source=SyntheticSource()
        self.stream=BookStream(LayoutContext(96,'en'),self.source,ReadingPreferences())
        self.addCleanup(self.stream.close)

    def settle(self,predicate):
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            self.stream.poll()
            if predicate():return
            time.sleep(.005)
        self.fail('Background preparation did not settle')

    def configure(self,key='Mark',width=350,anchor=None):
        self.stream.configure(width,600,anchor or Anchor(key+'.7.1'),key)
        self.settle(lambda:self.stream.cursor is not None)

    def test_entry_anchor_does_not_manufacture_a_short_previous_page(self):
        self.configure();doc=self.stream.plan('Mark').document
        anchor=doc.anchor(len(doc.text)//2)
        natural=tuple(self.stream.plan('Mark').pages)
        self.configure(anchor=anchor)
        self.assertEqual(tuple(self.stream.plan('Mark').pages),natural)
        self.assertEqual(self.stream.anchor(),anchor)

    def test_reflow_reuses_source_document_but_number_visibility_invalidates_it(self):
        self.configure();doc=self.stream.plan('Mark').document
        anchor=doc.anchor(doc.spans[2].body+60)
        self.stream.preferences.size=32
        self.configure(width=390,anchor=anchor)
        self.assertIs(self.stream.plan('Mark').document,doc)
        self.assertEqual(self.stream.anchor(),anchor)
        self.assertEqual(self.source.calls.count(('Mark',True,True)),1)
        self.assertEqual(self.source.clones,1)
        self.stream.preferences.verse_numbers=False
        self.configure(width=390,anchor=anchor)
        self.assertIsNot(self.stream.plan('Mark').document,doc)
        self.assertEqual(self.source.calls.count(('Mark',True,False)),1)

    def test_identical_reconfiguration_reuses_plan_and_can_restore_cleared_cursor(self):
        self.configure();plan=self.stream.plan('Mark')
        self.configure();self.assertIs(self.stream.plan('Mark'),plan)
        self.stream.cursor=None  # Existing immersion reflow contract.
        self.configure();self.assertIs(self.stream.plan('Mark'),plan)

    def test_superseded_book_stops_and_never_overwrites_the_new_request(self):
        self.source.wait_for='Mark'
        self.stream.configure(350,600,Anchor('Mark.7.1'),'Mark')
        self.assertTrue(self.source.entered.wait(2))
        self.stream.configure(360,600,Anchor('John.7.1'),'John')
        self.settle(lambda:self.stream.cursor is not None)
        self.assertTrue(self.source.cancelled.is_set())
        self.assertEqual(self.stream.cursor.key,'John')
        self.assertNotIn('Mark',self.stream.cache)
        self.assertIsNone(self.stream.error)

    def test_close_cancels_active_work_and_leaves_no_worker_or_cache(self):
        self.source.wait_for='Mark'
        self.stream.configure(350,600,Anchor('Mark.7.1'),'Mark')
        self.assertTrue(self.source.entered.wait(2))
        self.stream.close()
        self.assertTrue(self.source.cancelled.is_set())
        self.assertFalse(self.stream.futures)
        self.assertFalse(self.stream.documents)
        self.assertFalse(self.stream.plans)
        self.assertIsNone(self.stream.poll())
        self.assertTrue(all(not t.is_alive() for t in self.stream.executor._threads))

    def test_reflow_cancels_before_waiting_for_geometry_to_settle(self):
        self.source.wait_for='Mark'
        self.stream.configure(350,600,Anchor('Mark.7.1'),'Mark')
        self.assertTrue(self.source.entered.wait(2))
        self.stream.cancel_pending()
        self.assertTrue(self.source.cancelled.wait(2))
        self.assertIsNone(self.stream.pending)
        self.assertFalse(self.stream.futures)
        self.assertIsNone(self.stream.poll())
        self.assertIsNone(self.stream.cursor)
        self.source.release.set()
        self.configure()
        self.assertEqual(self.stream.cursor.key,'Mark')

    def test_navigation_prunes_obsolete_prefetch_and_all_caches_are_bounded(self):
        self.configure()
        for key in ('Luke','John','Acts','Rom'):
            self.configure(key)
            self.settle(lambda:not self.stream.futures)
            self.assertLessEqual(len(self.stream.documents),3)
            self.assertLessEqual(len(self.stream.plans),3)
            self.assertLessEqual(len(self.stream.cache),3)
            retained={key,self.source.neighbour(key,-1),self.source.neighbour(key,1)}
            self.assertTrue(set(self.stream.cache)<=retained)
            self.assertTrue({sig[0] for sig in self.stream.documents}<=retained)
            self.assertTrue({sig[0][0] for sig in self.stream.plans}<=retained)

    def test_revisiting_initial_configuration_after_turn_repositions_the_cursor(self):
        self.configure();initial=self.stream.plan('Mark')
        self.settle(lambda:'Luke' in self.stream.cache)
        from bible.paged_sources import PageAddress
        self.stream.cursor=PageAddress('Luke',0);self.stream.requested_anchor=None
        self.configure()
        self.assertEqual(self.stream.cursor.key,'Mark')
        self.assertIs(self.stream.plan('Mark'),initial)


if __name__=='__main__':unittest.main()
