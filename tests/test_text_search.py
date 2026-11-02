"""Source-backed words/phrases, scopes, paging and normalization boundaries."""
from pathlib import Path
from contextlib import closing
import tempfile
import unittest
from bible.search_terms import normalized,terms,match_ranges


class SearchTermsTests(unittest.TestCase):
    def test_french_accents_apostrophes_phrases_and_source_highlighting(self):
        self.assertEqual(terms('"grâce de Dieu" amour','fr'),('grace de dieu','amour'))
        self.assertEqual(terms("l'homme",'fr'),('l homme',))
        self.assertEqual(normalized('AIMÉ','fra'),'aime')
        self.assertEqual(normalized('GRÂCE','fr-CA'),'grace')
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

class CloseMatchTests(unittest.TestCase):
    """Synthetic prose in the existing SQLite schema; no fabricated corpus text."""
    def query(self,rows,query,language='en',**options):
        import sqlite3
        from bible.text_search import query_index
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'index.sqlite3'
            with closing(sqlite3.connect(path)) as db,db:
                db.executescript('CREATE TABLE metadata(language TEXT); CREATE TABLE verses(position INTEGER PRIMARY KEY,reference TEXT,book TEXT,testament INTEGER,normalized TEXT);')
                db.execute('INSERT INTO metadata VALUES(?)',(language,))
                for i,(ref,text) in enumerate(rows):
                    db.execute('INSERT INTO verses VALUES(?,?,?,?,?)',(i,ref,ref.split('.')[0],1 if ref.startswith('Gen.') else 2,' '+normalized(text,language).strip()+' '))
            return query_index(path,query,**options)

    def test_strict_terms_precede_close_wording_and_paging_preserves_order(self):
        rows=[('Gen.1.1','brave traveler crossed the river'),('John.1.1','brave traveler crosses river'),('John.1.2','brave traveler did not cross the river')]
        result=self.query(rows,'brave traveler crosses river')
        self.assertEqual(result['references'],['John.1.1','Gen.1.1'])
        self.assertEqual([m['kind'] for m in result['matches']],['strict','close'])
        self.assertEqual(self.query(rows,'brave traveler crosses river',offset=1,limit=1)['references'],['Gen.1.1'])
        self.assertEqual(self.query(rows,'brave traveler crosses river',scope='nt')['references'],['John.1.1'])
        self.assertEqual(self.query(rows,'brave traveler crosses river',scope='book',book='Gen')['references'],['Gen.1.1'])

    def test_quotes_remain_strict_and_common_words_do_not_create_close_results(self):
        rows=[('Gen.1.1','brave traveler crossed the river')]
        self.assertEqual(self.query(rows,'"brave traveler crosses river"')['total'],0)
        self.assertEqual(self.query(rows,'the and of')['close_total'],0)
        self.assertEqual(self.query(rows,'brave river')['close_total'],0)

    def test_negation_is_not_dropped_and_distant_overlap_is_not_a_close_phrase(self):
        rows=[('Gen.1.1','marcheur courageux ne traverse pas la rivière'),('Gen.1.2','marcheur courageux traverse la rivière'),('Gen.1.3','marcheur '+('chemin '*25)+' courageux ne franchit pas la rivière')]
        result=self.query(rows,'marcheur courageux ne franchit pas la riviere','fr')
        # The remote words satisfy strict AND semantics and remain labeled as such.
        self.assertEqual(result['matches'][0]['kind'],'strict')
        self.assertEqual([m['reference'] for m in result['matches'] if m['kind']=='close'],['Gen.1.1'])
        far=[('Gen.1.1','brave '+('sideways '*25)+' traveler crossed river')]
        self.assertEqual(self.query(far,'brave traveler crosses river')['total'],0)

    def test_accents_punctuation_limits_and_unsupported_segmentation(self):
        rows=[(f'Gen.1.{i+1}','Marcheur courageux : traversée de la rivière !') for i in range(40)]
        result=self.query(rows,'MARCHEUR courageux traverse rivière','fr')
        self.assertEqual(result['close_total'],20)
        self.assertLessEqual(result['approximate_candidates'],256)
        self.assertEqual(result['references'][0],'Gen.1.1')
        self.assertEqual(self.query(rows,'MARCHEUR courageux traverse rivière','el')['close_total'],0)
