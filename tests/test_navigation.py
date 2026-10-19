from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bible.library import Library, Resource
from bible.sword_provider import Reader
from tests.fixtures import module_fixture
from tests.test_library import archive_bytes

NT_ENTRIES = [('Matt.1.1', 'MATTHEW TEST DATA'), ('John.3.16', 'JOHN 16 TEST DATA'),
              ('John.3.18', 'JOHN 18 TEST DATA'), ('Rev.22.21', 'REVELATION TEST DATA')]


class CapabilityTests(unittest.TestCase):
    def test_nt_only_uses_actual_entries_not_the_default_canon(self):
        with tempfile.TemporaryDirectory() as directory:
            module_fixture(directory, 'NTTest', NT_ENTRIES, nt_only=True)
            reader = Reader(directory, 'NTTest')
            self.assertEqual([book.code for book in reader.books], ['Matt', 'John', 'Rev'])
            self.assertEqual(reader.first_reference(), 'Matt.1.1')
            john = reader.books[1]
            self.assertEqual(john.chapters, {3: (16, 18)})
            self.assertFalse(reader.has_reference('John.3.17'))
            self.assertFalse(reader.has_reference('Gen.1.1'))
            self.assertEqual(reader.neighbours('John.3.16'), ('Matt.1.1', 'Rev.22.21'))
            self.assertEqual(reader.key('Jean 3:16').getOSISRef(), 'John.3.16')

    def test_catholic_versification_exposes_tobit_and_its_own_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            module_fixture(directory, 'CatholicTest', [('Tob.3.16', 'TOBIT TEST DATA'),
                           ('Tob.3.17', 'SECOND TEST DATA')], versification='Catholic')
            reader = Reader(directory, 'CatholicTest')
            self.assertEqual([book.code for book in reader.books], ['Tob'])
            self.assertEqual(reader.books[0].chapters, {3: (16, 17)})
            self.assertEqual(reader.first_reference(), 'Tob.3.16')
            self.assertEqual(reader.key('Tobie 3:17').getVerseMax(), 17)
            with self.assertRaises(ValueError):
                reader.key('Tob.3.18')
            self.assertIn('TOBIT TEST DATA', reader.chapter(reader.first_reference()).verses[0][1])

    def test_unknown_versification_is_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            module_fixture(directory, 'Test', [('Gen.1.1', 'TEST DATA')])
            path = Path(directory) / 'mods.d/test.conf'
            path.write_text(path.read_text().replace('Versification=KJV', 'Versification=UnknownSystem'))
            with self.assertRaisesRegex(ValueError, 'Unsupported versification'):
                Reader(directory, 'Test')

    def test_install_nt_translation_validates_its_first_real_chapter(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as directory:
            module_fixture(source, 'NTTest', NT_ENTRIES, nt_only=True)
            payload = archive_bytes({str(path.relative_to(source)): path.read_bytes()
                                     for path in Path(source).rglob('*') if path.is_file()})
            def fetch(url, output, progress):
                output.write(payload)
            with patch('bible.library.download', side_effect=fetch):
                Library(directory).install(Resource('NTTest', 'Test fixture', 'en', 'Public Domain'))
            self.assertEqual(Library(directory).installed(), ['NTTest'])
            reader = Reader(Path(directory) / 'NTTest', 'NTTest')
            self.assertEqual(reader.first_reference(), 'Matt.1.1')
            self.assertTrue(reader.has_reference('Jean 3:16'))
