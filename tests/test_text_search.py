"""Source-backed words/phrases, scopes, paging and normalization boundaries."""
from pathlib import Path
import tempfile
import unittest
from bible.search_terms import normalized,terms,match_ranges


class SearchTermsTests(unittest.TestCase):
    def test_french_accents_apostrophes_phrases_and_source_highlighting(self):
        self.assertEqual(terms('"grâce de Dieu" amour','fr'),('grace de dieu','amour'))
        self.assertEqual(terms("l'homme",'fr'),('l homme',))
        self.assertNotEqual(normalized('ἄνθρωπος','el'),normalized('ανθρωπος','el'))
        self.assertEqual(normalized('ά','el'),normalized('α\u0301','el'))
        self.assertEqual(match_ranges('gra\u0302ce','grace','fr'),((0,6),))
        text='La grâce, l’amour et la GRÂCE.'
        self.assertEqual([text[a:b] for a,b in match_ranges(text,'grace','fr')],['grâce','GRÂCE'])
        with self.assertRaises(ValueError):terms('"unfinished','fr')

    def test_actual_sword_index_scope_count_pages_and_phrase_order(self):
        from bible.text_search import search
        from tests.test_ui import installed_fixture
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,entries=[('Gen.1.1','grace and love'),('Gen.1.2','love then grace'),('John.1.1','Grace and love'),('John.1.2','lovely graceless')])
            root=Path(directory)/'translations'
            result=search(root,'Test','grace love',limit=1)
            self.assertEqual(result['total'],3);self.assertEqual(result['references'],['Gen.1.1'])
            self.assertEqual(search(root,'Test','grace love',offset=1,limit=1)['references'],['Gen.1.2'])
            self.assertEqual(search(root,'Test','"grace and love"')['total'],2)
            self.assertEqual(search(root,'Test','grace',scope='nt')['references'],['John.1.1'])
            self.assertEqual(search(root,'Test','grace',scope='book',book='Gen')['references'],['Gen.1.1','Gen.1.2'])
            self.assertEqual(search(root,'Test','unavailable')['total'],0)
