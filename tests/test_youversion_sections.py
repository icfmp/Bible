"""Neutral reproductions of actual section inventories and introduction styles."""
from pathlib import Path
import tempfile
import unittest
import zipfile
from xml.etree import ElementTree as E
from tools.research.test_yves_source import metadata,chapter,VERSION
from bible.youversion_source import read_edition,to_osis,parse_chapter
from bible.youversion_worker import converted_chapters,NS


class SectionTests(unittest.TestCase):
    def sections(self,root,refs,verses):
        edition=read_edition(metadata(refs),VERSION);archive=root/'fixture.zip'
        with zipfile.ZipFile(archive,'w') as z:
            for ref,number in zip(refs,verses):
                book,section=ref.split('.')
                z.writestr(book+'/'+section+'.yves',chapter(ref,
                    '<div class="p"><span class="verse" data-usfm="'+ref+'.'+str(number)+'">Synthetic section '+str(number)+'</span></div>'))
        return archive,edition

    def test_consecutive_sections_keep_all_explicit_verses_and_physical_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            archive,edition=self.sections(Path(directory),['ESG.1_1','ESG.1_2','ESG.2'],[1,18,1])
            results=list(converted_chapters(archive,edition))
            self.assertEqual(len(results),2)
            first,root,parts=results[0]
            self.assertEqual([p['reference'] for p in parts],['ESG.1_1','ESG.1_2'])
            self.assertEqual([n.get('osisID') for n in root.iter() if n.tag=='{'+NS+'}verse' and n.get('sID')],['EsthGr.1.1','EsthGr.1.18'])

    def test_overlapping_sections_are_not_dropped_renumbered_or_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            archive,edition=self.sections(Path(directory),['SIR.1','SIR.1_1'],[1,1])
            with self.assertRaisesRegex(ValueError,'Overlapping source chapter sections: SIR.1 / SIR.1_1'):
                list(converted_chapters(archive,edition))

    def test_introduction_styles_and_deuterocanonical_note_text_survive(self):
        ref='GEN.INTRO1';edition=read_edition(metadata([ref]),VERSION)
        raw=chapter(ref,'<div class="is">Synthetic heading</div><div class="im">First paragraph.</div>'
            '<div class="imi">Indented paragraph.<span class="note f"><span class="fdc">Test locator</span></span></div>'
            '<div class="li">Synthetic list item</div>')
        xml,_=to_osis(parse_chapter(raw,ref,edition),edition);root=E.fromstring(xml)
        self.assertIn('Indented paragraph.',''.join(root.itertext()))
        self.assertEqual(root.find('.//{'+NS+'}item').text.strip(),'Synthetic list item')
        self.assertEqual(root.find('.//{'+NS+'}note/{'+NS+'}seg').text,'Test locator')


if __name__=='__main__':unittest.main()
