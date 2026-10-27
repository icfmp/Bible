"""Native raster HTTP/cache/lifetime checks against a local synthetic tile server."""
import os
import struct
import threading
import unittest
import zlib
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
from tests.test_ui import spin


def tile_png():
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    pixels=(b'\0'+b'\x88\xaa\x99'*256)*256
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',256,256,8,2,0,0,0))
            +chunk(b'IDAT',zlib.compress(pixels))+chunk(b'IEND',b''))


def require_native_map():
    try:
        from bible.place_map import Shumate
    except (ImportError,ValueError) as error:
        if os.environ.get('BIBLE_REQUIRE_NATIVE_MAP')=='1':raise AssertionError('Packaged native map is missing') from error
        raise unittest.SkipTest('Requires the packaged libshumate 1.5.5 dependency') from error


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native Shumate/GTK')
class PlaceMapTests(unittest.TestCase):
    def test_identified_cached_view_and_no_requests_after_close(self):
        require_native_map()
        from bible.place_map import PlaceMap,USER_AGENT
        from gi.repository import Gtk
        requests=[];payload=tile_png()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def do_GET(self):
                body=b'invalid synthetic image' if self.path.startswith('/invalid/') else payload
                requests.append((self.path,self.headers.get('User-Agent'),self.headers.get('Cache-Control')))
                self.send_response(200);self.send_header('Content-Type','image/png')
                self.send_header('Content-Length',str(len(body)))
                self.send_header('Cache-Control','public, max-age=604800');self.send_header('ETag','"synthetic-tile"')
                self.end_headers();self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with patch('bible.place_map.TILE_URL',f'http://127.0.0.1:{server.server_port}/{{z}}/{{x}}/{{y}}.png'):
                w=Gtk.Window(default_width=600,default_height=360)
                self.addCleanup(w.destroy)
                canvas=PlaceMap([dict(latitude=32.5,longitude=44.4)]);w.set_child(canvas)
                self.assertFalse(requests,'No map request before the detail is actually visible')
                w.present();spin(lambda:canvas.ready,timeout=15)
                self.assertTrue(requests);self.assertLess(len(requests),30)
                self.assertTrue(all(agent==USER_AGENT and cache!='no-cache' for _,agent,cache in requests))
                before=len(requests);w.close();spin(duration=.2)
                self.assertIsNone(canvas.canvas)
                spin(duration=.3);self.assertEqual(len(requests),before)
                again=Gtk.Window(default_width=600,default_height=360)
                self.addCleanup(again.destroy)
                cached=PlaceMap([dict(latitude=32.5,longitude=44.4)]);again.set_child(cached);again.present()
                spin(lambda:cached.ready,timeout=15)
                self.assertEqual(len(requests),before,'Reopening an unchanged region reuses the native disk cache')
                again.close();spin()
            with patch('bible.place_map.TILE_URL',f'http://127.0.0.1:{server.server_port}/invalid/{{z}}/{{x}}/{{y}}.png'):
                failed=Gtk.Window(default_width=600,default_height=360);self.addCleanup(failed.destroy)
                broken=PlaceMap([dict(latitude=32.5,longitude=44.4)]);failed.set_child(broken);failed.present()
                spin(lambda:broken.retry.get_visible(),timeout=15)
                self.assertFalse(broken.ready,'A failed native image decode must never mark an empty map successful')
                held=broken.canvas.get_viewport();before=len(requests);failed.close();spin()
                held.set_zoom_level(9);spin(duration=.3)
                self.assertEqual(len(requests),before,'No map loading remains after closing its window')
        finally:server.shutdown();server.server_close();thread.join(timeout=2)
