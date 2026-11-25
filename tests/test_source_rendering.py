"""Source milestones and editorial roles, independent of module names."""
import re
import unittest
from bible.structured_text import extract


class SourceRenderingTests(unittest.TestCase):
    def test_note_milestones_cannot_add_a_body_paragraph_or_poetry_line(self):
        raw='Before<note><l eID="note-line"/><lg eID="note-stanza"/>Note only.</note> after.'
        self.assertEqual(''.join(s.text for s in extract(raw,'Before after.','OSIS')),'Before after.')

    def test_verified_native_emphasis_does_not_hide_authored_asterisks_or_poetry(self):
        raw='<hi type="small-caps">Exact source</hi> * literal.<lb/><lb/>Poetry.'
        native='* Exact source * * literal. Poetry.'
        parts=extract(raw,native,'OSIS')
        self.assertEqual(''.join(s.text for s in parts if 'native-decoration' not in s.styles),
                         'Exact source * literal.\n\nPoetry.')
        self.assertEqual(''.join(s.text for s in parts if s.styles==('native-decoration',)),'* * ')
        self.assertTrue(any(s.styles==('small-caps',) and s.text=='Exact source' for s in parts))
        unknown=extract(raw,'* Different source * * literal. Poetry.','OSIS')
        self.assertEqual(unknown[0].text,'* Different source * * literal. Poetry.')
        self.assertEqual(len(unknown),1)

    def test_explicit_repeated_line_breaks_are_not_paired_milestone_duplicates(self):
        parts=extract('Prose.<lb/><lb/>First line.<lb/>Second line.',
                      'Prose. First line. Second line.','OSIS')
        self.assertEqual(''.join(s.text for s in parts),'Prose.\n\nFirst line.\nSecond line.')
        blank=extract('Before.<milestone type="x-source-blank-line"/>After.',
                      'Before. After.','OSIS')
        self.assertEqual(''.join(s.text for s in blank),'Before.\n\nAfter.')

    def test_separator_styles_preserve_exact_text_and_do_not_cover_content(self):
        from bible.pagination import paragraph_spaces
        text='Éditorial\n\nBody\nPoetry line\n\nNext paragraph.'
        spaces=paragraph_spaces(text)
        self.assertEqual(len(spaces),2)
        for span in spaces:
            self.assertEqual(text[span.start:span.end],'\n')
            self.assertEqual(text[span.start-1],'\n')
        self.assertEqual(text,'Éditorial\n\nBody\nPoetry line\n\nNext paragraph.')

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

    def test_end_milestone_can_reference_its_start_without_repeating_the_type(self):
        parts=extract('<div type="x-p" sID="p"/>First paragraph.<div eID="p"/>After paragraph.',
                      'First paragraph. After paragraph.','OSIS')
        self.assertIn('First paragraph.\n\nAfter paragraph.',''.join(p.text for p in parts))
