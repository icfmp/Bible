"""Neutral overlapping/interleaved source structures, with no edition corpus."""
import copy
import unittest
from bible.source_units import AddressIndex,ChapterUnits,SourceUnit
from bible.source_sections import SectionIndex,SourceChapter
from bible.youversion_source import read_edition,parse_chapter,source_document
from bible.youversion_osis import convert,NS
from bible.youversion_content import parse,project
from tools.research.test_yves_source import metadata,chapter,VERSION


class UnitTests(unittest.TestCase):
    def document(self,refs,texts):
        ref='SIR.43';edition=read_edition(metadata([ref]),VERSION)
        html=''.join('<div class="p"><span class="verse" data-usfm="'+members+'"><span class="label">'+label+'</span>'+body+'</span></div>' for members,label,body in zip(refs,['17a','16','17b'],texts))
        return source_document(parse_chapter(chapter(ref,html),ref,edition),edition)

    def test_interleaved_fragments_are_stored_once_in_source_order(self):
        doc=self.document(['SIR.43.17','SIR.43.16','SIR.43.17'],['FIRST FRAGMENT','MIDDLE VERSE','LAST FRAGMENT'])
        units=ChapterUnits.from_document(doc)
        self.assertTrue(units.overlaps)
        self.assertEqual(units.by_reference['Sir.43.17'],[1,3])
        self.assertEqual([u.label for u in units.units],['17a','16','17b'])
        xml,_=convert(units.storage_document(doc,'Sir.44'))
        bodies=project(parse(xml.decode()),milestones=True)[0]
        self.assertEqual(list(bodies),['Sir.44.1','Sir.44.2','Sir.44.3'])
        self.assertEqual(list(bodies.values()),['FIRST FRAGMENT','MIDDLE VERSE','LAST FRAGMENT'])
        self.assertEqual([n.attrs['data-usfm'] for n in units.verse_nodes(doc)],['SIR.43.17','SIR.43.16','SIR.43.17'])

    def test_partial_bridge_retains_shared_unit_and_verse_continuation(self):
        units=ChapterUnits('Sir.44',[SourceUnit(('Sir.44.22','Sir.44.23'),'22–23'),SourceUnit(('Sir.44.23',),'23')])
        sections=SectionIndex.allocate([SourceChapter('Sir.44','44',True)])
        index=AddressIndex(sections,[units]);restored=AddressIndex.from_data(index.data())
        self.assertEqual(restored.to_native('Sir.44.22'),'Sir.1.1')
        self.assertEqual(restored.to_native('Sir.44.23'),'Sir.1.1')
        self.assertEqual(restored.to_sources('Sir.1.1'),('Sir.44.22','Sir.44.23'))
        self.assertEqual(restored.to_sources('Sir.1.2'),('Sir.44.23',))
        self.assertEqual(restored.chapters['Sir.44'].by_reference['Sir.44.23'],[1,2])
        self.assertEqual(restored.to_native('Gen.11.3'),'Gen.11.3')
        for invalid in ('Sir.44.24','Sir.44.0','Sir.44.000','Sir.44.2001'):
            with self.assertRaises(ValueError):restored.to_native(invalid)

    def test_untrusted_units_cannot_invent_cross_chapter_members_or_oversized_coordinates(self):
        value=ChapterUnits('Sir.43',[SourceUnit(('Sir.43.17',),'17a')]).data()
        for member in ('Sir.44.17','Sir.43.0','Sir.43.2001','Sir.43.017'):
            changed=copy.deepcopy(value);changed['units'][0]['members']=[member]
            with self.assertRaises(ValueError):ChapterUnits.from_data(changed)
        with self.assertRaises(ValueError):ChapterUnits('Sir.43',[SourceUnit(('Sir.43.17',),'x\n')])


if __name__=='__main__':unittest.main()
