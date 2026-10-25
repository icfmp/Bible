"""Full source alignment is required; grouped/partial selections stay honest."""
import unittest
import importlib.util
from bible.word_metadata import aligned_identifiers


class WordMetadataTests(unittest.TestCase):
    def test_verified_translated_word_supplies_lexical_id_without_inflected_claim(self):
        raw='Au <w lemma="strong:H7225">commencement</w>, <w lemma="strong:H0430">Dieu</w>.'
        value=aligned_identifiers(raw,'Au commencement, Dieu.','Au commencement, ','Dieu')
        self.assertEqual(value['identifiers'],('H0430',))
        self.assertNotIn('form',value)
        self.assertIsNone(aligned_identifiers(raw,'Other source wording.','','Other'))
        self.assertIsNone(aligned_identifiers(raw,'Au commencement, Dieu.','Au commencement, ','Die'))

    def test_grouped_multiple_strongs_and_hidden_markup_never_pick_an_arbitrary_lemma(self):
        raw='<w lemma="strong:G3588 strong:G3056 lemma.TR:ο lemma.TR:λογος" morph="robinson:N-NSM">the Word</w><note>not Scripture</note>.'
        value=aligned_identifiers(raw,'the Word.','','the Word')
        self.assertEqual(value['identifiers'],('G3588','G3056'))
        self.assertIsNone(aligned_identifiers(raw,'the Word.','the ','Word'))
        self.assertIsNone(aligned_identifiers(raw,'the Word.','','the Word.'))


class SourceVerseTests(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('Sword'),'Requires SWORD')
    def test_real_numbered_psalm_titles_never_become_body_verse_words(self):
        from bible.word_metadata import source_verse_references
        from bible.reference_targets import Canon
        source=Canon('Segond')
        for title in ('Ps.3.1','Ps.51.1','Ps.51.2'):
            with self.assertRaises(ValueError):source_verse_references(title,source)
        self.assertEqual(source_verse_references('Ps.3.2',source),('Ps.3.1',))
        self.assertEqual(source_verse_references('Ps.51.3',source),('Ps.51.1',))
        self.assertEqual(source_verse_references('Ps.51.4',source),('Ps.51.2',))
        self.assertEqual(source_verse_references('3John.1.14',Canon('KJV')),('3John.1.14','3John.1.15'))
