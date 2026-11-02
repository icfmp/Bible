import unittest
from bible.resource_details import plain


class MetadataTests(unittest.TestCase):
    def test_youversion_summary_does_not_claim_unfetched_conditions_are_absent(self):
        from bible.resource_details import details
        from bible.i18n import tr
        from bible.youversion_catalogue import resource_from_listing
        from tests.test_youversion_catalogue import listing
        text=details(resource_from_listing(listing(),'spa'))
        self.assertIn(tr('Loading edition details…'),text)
        self.assertNotIn(tr('No additional conditions supplied by the source.'),text)

    def test_legacy_paragraphs_keep_attribution_words(self):
        value = r'First paragraph. \\par\\parSource: Richard Lemay. \\parPermission retained.'
        text = plain(value)
        self.assertNotIn('\\par', text)
        for attribution in ['First paragraph.', 'Source: Richard Lemay.', 'Permission retained.']:
            self.assertIn(attribution, text)
        self.assertIn('\n', text)
        self.assertEqual(plain(r'Keep \\parallel unknown text'), r'Keep \\parallel unknown text')
