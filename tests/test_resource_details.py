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

    def test_only_explicit_http_links_are_displayed(self):
        from bible.resource_details import linkable_url, first_link
        self.assertEqual(linkable_url('https://crosswire.org/'), 'https://crosswire.org/')
        self.assertEqual(linkable_url('javascript:alert(1)'), '')
        self.assertEqual(linkable_url('https://evil.test@crosswire.org/'), '')
        self.assertEqual(linkable_url('https://crosswire.org/\n'), 'https://crosswire.org/')
        self.assertEqual(first_link('CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)'),
                         'https://creativecommons.org/licenses/by/4.0/')
        self.assertEqual(first_link('No link supplied'), '')

    def test_legacy_paragraphs_keep_attribution_words(self):
        value = r'First paragraph. \\par\\parSource: Richard Lemay. \\parPermission retained.'
        text = plain(value)
        self.assertNotIn('\\par', text)
        for attribution in ['First paragraph.', 'Source: Richard Lemay.', 'Permission retained.']:
            self.assertIn(attribution, text)
        self.assertIn('\n', text)
        self.assertEqual(plain(r'Keep \\parallel unknown text'), r'Keep \\parallel unknown text')
