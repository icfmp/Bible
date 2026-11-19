"""Synthetic fixtures only: no downloaded scripture in the repository."""
import unittest

from tools.research.youversion_osis import (
    NS, Unsupported, convert, osis_ref, read_document,
)
from lxml import etree as E


class ConversionProofTests(unittest.TestCase):
    def document(self, blocks, ref='JHN.1', prefix='abc_'):
        raw = f'<html><div class="{prefix}chapter" data-usfm="{ref}">{blocks}</div></html>'.encode()
        return read_document(raw, ref, source_url='https://example.invalid/sample',
                             attribution='Synthetic test material')

    def verse(self, n, body):
        return f'<span class="abc_verse" data-usfm="JHN.1.{n}"><span class="abc_label">{n}</span><span class="abc_content">{body}</span></span>'

    def tree(self, blocks):
        xml, report = convert(self.document(blocks))
        return E.fromstring(xml), report

    def test_fragment_continuation_crosses_paragraphs_once(self):
        t, r = self.tree('<div class="abc_p">'+self.verse(1, 'Alpha ')+
                         '</div><div class="abc_p">'+self.verse(1, 'Beta')+
                         self.verse(2, ' Gamma')+'</div>')
        self.assertEqual(r['verse_ids'], ['John.1.1', 'John.1.2'])
        self.assertEqual(r['verse_fragments']['John.1.1'], 2)
        self.assertEqual(len(t.xpath('//*[local-name()="verse"][@sID="John.1.1"]')), 1)
        self.assertEqual(len(t.xpath('//*[local-name()="verse"][@eID="John.1.1"]')), 1)
        self.assertEqual(len(t.xpath('//*[local-name()="p"]')), 2)

    def test_notes_separated_and_references_mapped(self):
        note = '<span class="abc_note"><span class="abc_label">#</span><span class="abc_body"><span class="abc_fr">1.1 </span><span class="ft">Editorial <span class="ref" data-usfm="MAT.2.1+MAT.2.2">target</span></span></span></span>'
        t, r = self.tree('<div class="abc_p">'+self.verse(1, 'Alpha'+note+' Beta')+'</div>')
        n = t.xpath('//*[local-name()="note"]')[0]
        self.assertEqual(n.get('osisRef'), 'John.1.1')
        self.assertEqual(n.get('n'), '1.1')
        self.assertEqual(''.join(n.itertext()), 'Editorial target')
        self.assertEqual(n[0].get('osisRef'), 'Matt.2.1 Matt.2.2')
        self.assertEqual(r['note_count'], 1)

    def test_poetry_preserves_multiple_lines_of_one_verse(self):
        t, r = self.tree('<div class="abc_q1">'+self.verse(1, 'Alpha')+
                         '</div><div class="abc_q4">'+self.verse(1, 'Beta')+'</div>')
        self.assertEqual([x.get('level') for x in t.xpath('//*[local-name()="l"]')], ['1', '4'])
        self.assertEqual(r['verse_ids'], ['John.1.1'])

    def test_intro_keeps_bare_tails(self):
        doc = self.document('<div class="abc_imt"><span class="abc_content">Introduction</span></div><div class="abc_ip"><span class="abc_content">Alpha (</span>4.42<span class="abc_content">) Beta</span></div>', 'JHN.INTRO1')
        xml, r = convert(doc)
        self.assertIn('Alpha (4.42) Beta', ''.join(E.fromstring(xml).itertext()))
        self.assertEqual(r['verse_ids'], [])

    def test_generated_prefix_is_not_pinned(self):
        doc = self.document('<div class="new_p"><span class="new_verse" data-usfm="JHN.1.1"><span class="new_content">Alpha</span></span></div>', prefix='new_')
        self.assertEqual(convert(doc)[1]['verse_ids'], ['John.1.1'])

    def test_words_of_jesus_do_not_generate_quotes(self):
        t, _ = self.tree('<div class="abc_p">'+self.verse(1, '<span class="abc_wj">Alpha</span>')+'</div>')
        q = t.xpath('//*[local-name()="q"]')[0]
        self.assertEqual((q.get('who'), q.get('marker')), ('Jesus', ''))

    def test_noncontiguous_repeated_verse_rejected(self):
        with self.assertRaises(Unsupported):
            self.tree('<div class="abc_p">'+self.verse(1, 'A')+self.verse(2, 'B')+self.verse(1, 'C')+'</div>')

    def test_unknown_element_rejected(self):
        with self.assertRaises(Unsupported):
            self.tree('<div class="abc_p"><span class="abc_newthing">Lost?</span></div>')

    def test_range_requires_explicit_future_support(self):
        with self.assertRaises(Unsupported):
            self.tree('<div class="abc_p"><span class="abc_verse" data-usfm="JHN.1.1-2">Range</span></div>')

    def test_numbered_book_mapping(self):
        self.assertEqual(osis_ref('2SA.15.13'), '2Sam.15.13')
        with self.assertRaises(Unsupported):
            osis_ref('ZZZ.1.1')

    def test_empty_chapter_and_missing_attribution_rejected(self):
        with self.assertRaises(Unsupported):
            self.tree('<div class="abc_p">Empty</div>')
        with self.assertRaises(Unsupported):
            read_document(b'<html/>', 'JHN.1', source_url='x', attribution='')

    def test_untrusted_attributes_rejected(self):
        with self.assertRaises(Unsupported):
            self.tree('<div class="abc_p"><span class="abc_content" onclick="bad()">A</span></div>')


if __name__ == '__main__':
    unittest.main()
