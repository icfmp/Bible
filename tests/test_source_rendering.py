"""Source milestones and editorial roles, independent of module names."""
import re
import unittest
from bible.structured_text import extract


class SourceRenderingTests(unittest.TestCase):
    def test_paired_poetry_milestones_have_one_line_boundary(self):
        raw=(' <lg sID="stanza"/> <l level="1" sID="line1"/>First line.'
             '<l eID="line1"/> \n <l sID="line2" level="2"/>Second line.'
             '<l eID="line2"/> <lg eID="stanza"/>')
        parts=extract(raw,'First line. Second line.','OSIS')
        text=''.join(p.text for p in parts)
        self.assertEqual(text,'\n\nFirst line.\nSecond line.\n\n')
        self.assertEqual([(p.kind,p.text) for p in parts if p.kind=='poetry'],[('poetry','\n')])
        self.assertTrue(all(p.styles==('poetry',) for p in parts if p.kind=='poetry'))

    def test_paired_paragraphs_collapse_only_adjacent_markup_whitespace(self):
        raw=('<div type="x-p" sID="p1"/>Exact * punctuation. <hi type="italic">Élève Ω</hi>'
             '<div type="x-p" eID="p1"/> \n <div type="x-p" sID="p2"/>'
             'Second paragraph.<div type="x-p" eID="p2"/>')
        plain='Exact * punctuation. Élève Ω Second paragraph.'
        parts=extract(raw,plain,'OSIS');text=''.join(p.text for p in parts)
        self.assertEqual(text,'\n\nExact * punctuation. Élève Ω\n\nSecond paragraph.\n\n')
        self.assertEqual(re.sub(r'\s','',text),re.sub(r'\s','',plain))
        self.assertEqual([p.text for p in parts if p.styles==('italic',)],['Élève Ω'])

    def test_source_distinguishes_parallel_references_from_section_titles(self):
        raw=('<title type="parallel">V. 1–3: cf. <reference osisRef="Gen.1.1">Gen 1:1</reference>.</title>'
             '<title type="sub">Actual section</title><p>Exact body.</p>')
        parts=extract(raw,'Exact body.','OSIS')
        self.assertEqual(''.join(p.text for p in parts if p.kind=='editorial'),'V. 1–3: cf. Gen 1:1.')
        self.assertEqual(''.join(p.text for p in parts if p.kind=='heading'),'Actual section')
        self.assertEqual(''.join(p.text for p in parts if p.kind=='text'),'Exact body.')

    def test_unknown_conversion_keeps_native_output(self):
        parts=extract('<p>Different body.</p>','Native output.','OSIS')
        self.assertEqual(len(parts),1);self.assertEqual(parts[0].text,'Native output.')
