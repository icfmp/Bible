import unittest
from bible.resource_details import plain


class MetadataTests(unittest.TestCase):
    def test_legacy_paragraphs_keep_attribution_words(self):
        value = r'First paragraph. \\par\\parSource: Richard Lemay. \\parPermission retained.'
        text = plain(value)
        self.assertNotIn('\\par', text)
        for attribution in ['First paragraph.', 'Source: Richard Lemay.', 'Permission retained.']:
            self.assertIn(attribution, text)
        self.assertIn('\n', text)
        self.assertEqual(plain(r'Keep \\parallel unknown text'), r'Keep \\parallel unknown text')
