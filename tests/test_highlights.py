from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bible.highlights import HighlightStore


class HighlightStoreTests(unittest.TestCase):
    def test_canonical_identity_colors_backup_and_merge_preserve_other_passages(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'highlights.json';store=HighlightStore(path)
            store.set('KJV',['Gen.1.1','Gen.1.2'],'yellow','Test')
            store.set('KJV',['Gen.1.1'],'green','Other')
            store.set('Segond',['Gen.1.1'],'blue','FreSegond1910')
            self.assertEqual(len(store.entries),3)
            self.assertEqual(store.entries[('KJV','Gen.1.1')]['color'],'green')
            self.assertEqual(HighlightStore(path).entries,store.entries)
            backup=Path(directory)/'backup.json';store.backup(backup)
            store.set('KJV',['John.3.16'],'blue','Test')
            store.set('KJV',['Gen.1.2'],None,'Test')
            store.restore(backup)
            self.assertIn(('KJV','John.3.16'),store.entries)
            self.assertIn(('KJV','Gen.1.2'),store.entries)

    def test_corrupt_or_unknown_file_is_preserved_and_invalid_restore_does_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'highlights.json'
            for original in ('{broken','{"version":2,"marks":[]}','{"version":true,"marks":[]}'):
                path.write_text(original);store=HighlightStore(path)
                self.assertTrue(store.error)
                with self.assertRaises(ValueError):store.set('KJV',['Gen.1.1'],'yellow','Test')
                self.assertEqual(path.read_text(),original)
            path.unlink();store=HighlightStore(path);store.set('KJV',['Gen.1.1'],'yellow','Test')
            before=path.read_bytes();bad=Path(directory)/'bad.json';bad.write_text('{broken')
            with self.assertRaises(ValueError):store.restore(bad)
            self.assertEqual(path.read_bytes(),before)

    def test_failed_atomic_replace_preserves_file_and_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'highlights.json';store=HighlightStore(path)
            store.set('KJV',['Gen.1.1'],'yellow','Test');before=path.read_bytes();entries=dict(store.entries)
            with patch('bible.highlights.os.replace',side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):store.set('KJV',['Gen.1.1'],'blue','Test')
            self.assertEqual(path.read_bytes(),before);self.assertEqual(store.entries,entries)
            self.assertEqual(list(Path(directory).iterdir()),[path])
