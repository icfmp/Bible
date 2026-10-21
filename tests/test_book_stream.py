import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from tests.test_ui import installed_fixture,spin


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK/Pango')
class BookStreamTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bible.ui import Gtk
        Gtk.init();cls.widget=Gtk.TextView()

    def source(self,directory,long=False):
        from bible.library import Library
        from bible.sword_provider import Reader
        from bible.paged_sources import BibleBookPages
        root=installed_fixture(directory,entries=[('Gen.1.1','FIRST SOURCE '* (220 if long else 1)),
                                                ('Gen.2.1','SECOND CHAPTER SOURCE'),
                                                ('Exod.1.1','NEXT BOOK SOURCE')])
        return BibleBookPages(Reader(root,'Test'),Library(Path(directory)/'translations').resource('Test'))

    def ready(self,stream):
        spin(lambda:(stream.poll(),stream.cursor is not None and 'Exod' in stream.cache)[1])

    def test_chapters_share_a_page_and_odd_book_leaves_right_page_blank(self):
        from bible.book_stream import BookStream
        from bible.pagination import Anchor
        from bible.preferences import ReadingPreferences
        with tempfile.TemporaryDirectory() as directory:
            source=self.source(directory);stream=BookStream(self.widget,source,ReadingPreferences())
            try:
                stream.configure(400,700,Anchor('Gen.1.1'),'Gen');self.ready(stream)
                plan=stream.plan('Gen')
                self.assertEqual(len(plan.pages),1)
                self.assertIn('FIRST SOURCE',plan.document.text);self.assertIn('SECOND CHAPTER SOURCE',plan.document.text)
                self.assertEqual(len(stream.spread(2)),1)
                self.assertTrue(stream.turn(1,2));self.assertEqual((stream.cursor.key,stream.cursor.index),('Exod',0))
                self.assertTrue(stream.turn(-1,2));self.assertEqual((stream.cursor.key,stream.cursor.index),('Gen',0))
            finally:stream.close()

    def test_even_book_returns_to_last_full_spread_without_extra_blank_spread(self):
        from bible.book_stream import BookStream
        from bible.pagination import Anchor
        from bible.paged_sources import PageAddress
        from bible.preferences import ReadingPreferences
        with tempfile.TemporaryDirectory() as directory:
            stream=BookStream(self.widget,self.source(directory,long=True),ReadingPreferences())
            try:
                for height in (240,300,360,420,480):
                    stream.configure(320,height,Anchor('Gen.1.1'),'Gen');self.ready(stream)
                    count=len(stream.plan('Gen').pages)
                    if count>=2 and count%2==0:break
                self.assertEqual(count%2,0)
                stream.cursor=PageAddress('Exod',0)
                self.assertTrue(stream.turn(-1,2));self.assertEqual(stream.cursor,PageAddress('Gen',count-2))
                self.assertEqual(len(stream.spread(2)),2)
                self.assertTrue(stream.turn(1,2));self.assertEqual(stream.cursor,PageAddress('Exod',0))
            finally:stream.close()

    def test_main_loop_runs_while_book_preparation_is_waiting(self):
        from gi.repository import GLib
        from bible.book_stream import BookStream
        from bible.pagination import Anchor
        from bible.preferences import ReadingPreferences
        with tempfile.TemporaryDirectory() as directory:
            stream=BookStream(self.widget,self.source(directory),ReadingPreferences())
            release=threading.Event();build=stream.build;ticks=[]
            def delayed(*args):
                if not release.wait(3):raise TimeoutError('Fixture worker not released')
                return build(*args)
            try:
                with patch.object(stream,'build',side_effect=delayed):
                    stream.configure(400,700,Anchor('Gen.1.1'),'Gen')
                    GLib.idle_add(lambda:ticks.append(True) and False)
                    spin(lambda:bool(ticks));self.assertIsNone(stream.cursor)
                    release.set();self.ready(stream)
                self.assertIsNotNone(stream.cursor)
            finally:release.set();stream.close()
