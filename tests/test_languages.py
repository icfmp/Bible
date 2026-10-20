"""Missing native CLDR names must not prevent catalogue searches."""
import unittest
from unittest.mock import patch

from bible.languages import language_info, search_terms


class LanguageTests(unittest.TestCase):
    def tearDown(self):
        language_info.cache_clear()

    def test_coptic_without_native_name_in_both_interfaces(self):
        for interface, expected in [('fr', 'copte'), ('en', 'Coptic')]:
            with self.subTest(interface=interface), patch('bible.languages.LANGUAGE', interface):
                language_info.cache_clear()
                with patch('babel.Locale.get_display_name', return_value=None):
                    self.assertEqual(language_info('cop'), (expected, ''))
                    terms = search_terms('cop')
                for term in ('cop', 'copte', 'Coptic'):
                    self.assertIn(term, terms)
                self.assertNotIn('None', terms)

    def test_real_cldr_names_and_exact_variants(self):
        for interface in ('fr', 'en'):
            self.assertEqual(language_info('cop', interface)[1], '')
            self.assertTrue(language_info('fr', interface)[1])
        for code in ('zzz', 'sr-Latn', 'pt-BR', 'fra'):
            self.assertIn(code, search_terms(code))
