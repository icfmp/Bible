"""Reviewed source identity and bounded, offline-first place photographs."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bible.place_context import context,cached_image


class PlaceContextTests(unittest.TestCase):
    def test_stable_identity_does_not_apply_jerusalem_enrichment_to_namesakes_or_unknown_places(self):
        self.assertIsNotNone(context(dict(id='a15257a',name='Jerusalem')))
        for place in (dict(id='a123456',name='Jerusalem'),dict(id='a15257a',name='Other place'),
                      dict(id='a1ad8e1',name='Nod'),dict(id='ae7274b',name='Emmaus')):
            self.assertIsNone(context(place))

    def test_download_is_explicit_verified_and_reopens_offline_without_touching_annotations(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);notes=root/'notes.sqlite3';notes.write_bytes(b'KEEP PERSONAL DATA')
            data=b'test-only photograph bytes';digest=hashlib.sha256(data).hexdigest()
            image=dict(url='https://example.test/curated.jpg',sha256=digest)
            with patch('bible.library.download',side_effect=lambda url,output,**kw:output.write(data)) as fetch:
                self.assertIsNone(cached_image(root,image));fetch.assert_not_called()
                path=cached_image(root,image,True);fetch.assert_called_once()
            with patch('bible.library.download',side_effect=AssertionError('Offline')):
                self.assertEqual(cached_image(root,image),path);self.assertEqual(path.read_bytes(),data)
            self.assertEqual(notes.read_bytes(),b'KEEP PERSONAL DATA')
            with patch('bible.library.download',side_effect=lambda url,output,**kw:output.write(b'WRONG CONTENT')):
                other=dict(image,sha256='1'*64)
                with self.assertRaisesRegex(ValueError,'checksum'):cached_image(root,other,True)
            self.assertEqual(path.read_bytes(),data);self.assertFalse((path.parent/('1'*64+'.jpg')).exists())
            with patch('bible.library.download') as fetch:
                with self.assertRaises(InterruptedError):cached_image(root,image,True,cancelled=lambda:True)
                fetch.assert_not_called()
