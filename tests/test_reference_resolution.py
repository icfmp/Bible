"""Exercise SWORD's real mapping tables, including changed Psalm numbering."""
from pathlib import Path
import tempfile
import unittest
from tests.fixtures import module_fixture
from bible.sword_provider import Reader, CommentaryReader
from bible.reference_resolution import resolve, VersificationMismatch


class ResolutionTests(unittest.TestCase):
    def test_segond_psalm_mapping_and_native_commentary(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            module_fixture(root,'Notes',[('Gen.1.25','GENESIS TEST'),
                                        ('Ps.3.1','PSALM TEST')],commentary=True)
            reader=CommentaryReader(root,'Notes')
            self.assertEqual(reader.entry('Gen.1.25','Segond'),'GENESIS TEST')
            mapped=resolve('Ps.3.2','Segond',reader)
            self.assertEqual((mapped.start,mapped.end),('Ps.3.1','Ps.3.1'))
            self.assertEqual(reader.entry('Ps.3.2','Segond'),'PSALM TEST')
            self.assertIsNone(reader.entry('Gen.1.26','Segond'))
            self.assertEqual(resolve('Gen.1.25','Catholic',reader).start,'Gen.1.25')
            with self.assertRaises(VersificationMismatch):resolve('Gen.1.25','LXX',reader)

    def test_reverse_mapping_and_unavailable_target(self):
        with tempfile.TemporaryDirectory() as directory:
            module_fixture(directory,'Bible',[('Ps.3.2','SEGOND TEST'),
                                               ('Gen.1.25','GENESIS TEST')],versification='Segond')
            reader=Reader(Path(directory),'Bible')
            self.assertEqual(resolve('Ps.3.1','KJV',reader).start,'Ps.3.2')
            self.assertEqual(resolve('Gen.1.25','KJV',reader).start,'Gen.1.25')
            with self.assertRaises(ValueError):resolve('John.3.16','KJV',reader)
