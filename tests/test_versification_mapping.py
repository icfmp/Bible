"""Independent upstream reference vectors, plus actual SWORD target entries."""
import json
from pathlib import Path
import tempfile
import unittest
from tests.fixtures import module_fixture
from bible.sword_provider import Reader
from bible.reference_resolution import resolve, VersificationMismatch
from bible.versification_mapping import table, to_base, from_base


class MappingTests(unittest.TestCase):
    def test_independent_upstream_vectors_and_canon_compatibility(self):
        oracle=json.loads((Path(__file__).parent/'fixtures/versification-oracle.json').read_text())
        for source,reference,target,expected in oracle['rows']:
            with self.subTest(source=source,reference=reference,target=target):
                self.assertIsNotNone(table(source));self.assertIsNotNone(table(target))
                actual={ref for q in to_base(reference,source) for ref in from_base(q,target)}
                self.assertEqual(actual,set(expected))
        self.assertIsNone(table('LXX'))
        self.assertIsNone(to_base('Gen.1.1','LXX'))

    def test_real_keys_boundaries_parts_and_merged_verses(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            module_fixture(root,'Base',[(ref,'SYNTHETIC '+ref) for ref in
                ['Gen.31.55','Ps.3.1','1Sam.21.14','1Sam.21.15','Acts.19.40','Acts.19.41','3John.1.14']])
            base=Reader(root,'Base')
            for source,reference,start,end in [
                ('Luther','Gen.32.1','Gen.31.55','Gen.31.55'),
                ('Luther','Ps.3.2','Ps.3.1','Ps.3.1'),
                ('Luther','Acts.19.40','Acts.19.40','Acts.19.41'),
                ('NRSVA','3John.1.15','3John.1.14','3John.1.14')]:
                result=resolve(reference,source,base)
                self.assertEqual((result.start,result.end),(start,end))
            with self.assertRaises(VersificationMismatch):resolve('Ps.3.1','Luther',base)
            with self.assertRaises(ValueError):resolve('John.3.16','Luther',base)
            module_fixture(root/'other','Other',[(ref,'SYNTHETIC '+ref) for ref in
                ['Gen.32.1','Ps.3.2','Ps.51.2','Ps.51.3','Acts.19.40']],versification='Luther')
            other=Reader(root/'other','Other')
            self.assertEqual(resolve('Gen.31.55','KJV',other).start,'Gen.32.1')
            self.assertEqual(resolve('Ps.3.1','KJV',other).start,'Ps.3.2')
            result=resolve('Ps.51.3','Segond',other)
            self.assertEqual((result.start,result.end),('Ps.51.2','Ps.51.3'))
            self.assertEqual(resolve('Acts.19.40','German',other).start,'Acts.19.40')
            self.assertEqual(resolve('Acts.19.41','KJV',other).start,'Acts.19.40')

    def test_disjoint_and_qualified_ranges_are_not_filled_or_truncated(self):
        with tempfile.TemporaryDirectory() as directory:
            module_fixture(directory,'Apocrypha',[('Tob.10.14','SYNTHETIC'),('Tob.11.1','SYNTHETIC')],versification='KJVA')
            reader=Reader(Path(directory),'Apocrypha')
            result=resolve('Tob.10.14','Catholic2',reader)
            self.assertEqual((result.start,result.end),('Tob.11.1','Tob.11.1'))
            with self.assertRaises(VersificationMismatch):resolve('1Kgs.18.34','SynodalProt',reader)
            module_fixture(Path(directory)/'disjoint','Other',
                           [('Hos.2.1','SYNTHETIC'),('Hos.12.11','SYNTHETIC')],versification='Catholic2')
            target=Reader(Path(directory)/'disjoint','Other')
            with self.assertRaisesRegex(VersificationMismatch,'Non-contiguous'):
                resolve('Hos.12.11','Catholic',target)
