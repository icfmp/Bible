"""Source identities stay distinct even when their printed numbers overlap."""
import copy
import unittest
from bible.source_sections import SectionIndex,SourceChapter


class SectionIndexTests(unittest.TestCase):
    def index(self):
        return SectionIndex.allocate([
            SourceChapter('Sir.INTRO1','Introduction',False),
            SourceChapter('Sir.1','1',True),
            SourceChapter('Sir.1_1','1',True),
            SourceChapter('Sir.2','2',True)])

    def test_overlapping_printed_chapters_keep_original_ids_and_roles(self):
        value=self.index()
        self.assertEqual(value.to_native('Sir.1.1'),'Sir.1.1')
        self.assertEqual(value.to_native('Sir.1_1.1'),'Sir.2.1')
        self.assertEqual(value.to_native('Sir.2.17'),'Sir.3.17')
        self.assertEqual(value.to_source('Sir.2.1'),'Sir.1_1.1')
        self.assertEqual(value.to_source('Sir.3.17'),'Sir.2.17')
        self.assertEqual([c.canonical for c in value.chapters],[False,True,True,True])
        self.assertEqual([c.human for c in value.chapters],['Introduction','1','1','2'])
        self.assertEqual(value.order['Sir'],['Sir.1','Sir.1_1','Sir.2'])
        with self.assertRaises(ValueError):value.to_native('Sir.INTRO1.1')

    def test_roundtrip_and_unaffected_books(self):
        value=self.index();restored=SectionIndex.from_data(value.data())
        for reference in ('Sir.1.1','Sir.1_1.30','Sir.2.17','Gen.11.3'):
            self.assertEqual(restored.to_source(restored.to_native(reference)),reference)
        self.assertEqual(restored.to_source('Sir.2'),'Sir.1_1')
        self.assertEqual(restored.to_native('Sir.1_1.0',allow_zero=True),'Sir.2.0')
        with self.assertRaises(ValueError):restored.to_native('Sir.1_1.0')

    def test_explicit_metadata_order_is_not_replaced_by_numeric_sort(self):
        value=SectionIndex.allocate([SourceChapter('Gen.2_2','Second section',True),
                                    SourceChapter('Gen.2_1','First section',True)])
        self.assertEqual(value.order['Gen'],['Gen.2_2','Gen.2_1'])
        self.assertEqual(value.to_source('Gen.1.3'),'Gen.2_2.3')

    def test_untrusted_maps_cannot_alias_or_reclassify_source_sections(self):
        original=self.index().data()
        for mutate in (lambda x:x['chapters'][2].update(storage='Sir.1'),
                       lambda x:x['chapters'][2].update(storage='Gen.2'),
                       lambda x:x['chapters'][2].update(storage='Sir.256'),
                       lambda x:x['chapters'][2].update(canonical=False),
                       lambda x:x['chapters'][0].update(storage='Sir.4'),
                       lambda x:x['chapters'][2].update(reference='Sir.1'),
                       lambda x:x.update(schema=True)):
            value=copy.deepcopy(original);mutate(value)
            with self.assertRaises(ValueError):SectionIndex.from_data(value)
        for reference in ('Sir.1_2.1','Gen.1_1.1','Sir.1_1.2001','Sir.1_1.-1','Sir.1_1.1+Sir.1_1.2'):
            with self.assertRaises(ValueError):self.index().to_native(reference)


if __name__=='__main__':unittest.main()
