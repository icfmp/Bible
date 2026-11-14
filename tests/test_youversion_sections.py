"""Neutral reproductions of actual section inventories and introduction styles."""
from pathlib import Path
import tempfile
import unittest
import zipfile
from xml.etree import ElementTree as E
from tools.research.test_yves_source import metadata,chapter,encode,VERSION
from bible.youversion_source import read_edition,to_osis,parse_chapter,decode_bytes
from bible.youversion_worker import converted_chapters,NS


class SectionTests(unittest.TestCase):
    def test_explicit_reference_attribute_alias_preserves_target_and_rejects_conflicts(self):
        ref='GEN.1';edition=read_edition(metadata([ref]),VERSION)
        raw=decode_bytes(chapter(ref,'<div class="p"><span class="verse" data-usfm="GEN.1.1">Synthetic verse.<span class="note f"><span class="ft"><span class="ref" data-usfm="PRO.3.19">Literal source pointer</span></span></span></span></div>')).decode()
        expected,_=to_osis(parse_chapter(encode(raw.encode()),ref,edition),edition)
        alias=raw.replace('class="ref" data-usfm=','class="ref" usfm=')
        parsed=parse_chapter(encode(alias.encode()),ref,edition)
        self.assertEqual(parsed['source_html'],alias)
        actual,_=to_osis(parsed,edition)
        self.assertEqual(E.tostring(E.fromstring(actual)),E.tostring(E.fromstring(expected)))
        invalid=alias.replace('usfm="PRO.3.19"','usfm="PRO.3.19" data-usfm="PRO.3.20"')
        with self.assertRaisesRegex(ValueError,'Conflicting explicit source reference'):
            to_osis(parse_chapter(encode(invalid.encode()),ref,edition),edition)

    def test_declared_introduction_with_chapter_wrapper_keeps_raw_content_and_semantics(self):
        ref='GEN.INTRO1';edition=read_edition(metadata([ref]),VERSION)
        original=chapter(ref,'<div class="is">Synthetic heading</div><div class="ip">Unchanged test introduction.</div>')
        raw=decode_bytes(original).decode().replace('intro intro1','chapter chINTRO1')
        parsed=parse_chapter(encode(raw.encode()),ref,edition)
        self.assertEqual(parsed['source_html'],raw)
        self.assertEqual(parsed['reference'],ref)
        self.assertEqual(parsed['verses'],[])
        expected,_=to_osis(parse_chapter(original,ref,edition),edition)
        actual,_=to_osis(parsed,edition)
        self.assertEqual(E.tostring(E.fromstring(actual)),E.tostring(E.fromstring(expected)))

    def test_introduction_wrapper_still_requires_exact_identity_and_one_container(self):
        ref='GEN.INTRO1';edition=read_edition(metadata([ref]),VERSION)
        raw=decode_bytes(chapter(ref,'<div class="ip">Synthetic introduction.</div>')).decode().replace('intro intro1','chapter chINTRO1')
        for invalid in (raw.replace('data-usfm="GEN.INTRO1"','data-usfm="GEN.INTRO2"'),
                        raw.replace('data-vid="'+str(VERSION)+'"','data-vid="999"'),
                        raw.replace('<div class="ip">','<div class="intro" data-usfm="GEN.INTRO1"><div class="ip">').replace('</div></div></div>','</div></div></div></div>')):
            with self.subTest(invalid=invalid),self.assertRaises(ValueError):parse_chapter(encode(invalid.encode()),ref,edition)
        ref='GEN.1';edition=read_edition(metadata([ref]),VERSION)
        invalid=decode_bytes(chapter(ref,'<div class="p"><span class="verse" data-usfm="GEN.1.1">Test verse.</span></div>')).decode().replace('chapter ch1','intro intro1')
        with self.assertRaises(ValueError):parse_chapter(encode(invalid.encode()),ref,edition)

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
