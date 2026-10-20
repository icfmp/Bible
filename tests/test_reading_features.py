"""State and fidelity checks for reading appearance/history/language names."""
import json
from pathlib import Path
import tempfile
import unittest

from bible import history
from bible.preferences import Preferences
from bible.session import Session, SessionStore, TabState
from bible.structured_text import extract
from bible.languages import language_info, search_terms


class ReadingFeaturesTests(unittest.TestCase):
    def test_history_branches_and_restores_per_tab(self):
        a=TabState('Test');b=TabState('Other')
        history.seed(a);history.seed(b)
        a.scroll=.42
        history.visit(a,'Test','Gen.2.1')
        a.reference='Gen.2.1';a.history_index=0
        history.visit(a,'Other','John.1.1')
        self.assertEqual([e['reference'] for e in a.history],['Gen.1.1','John.1.1'])
        self.assertEqual(a.history[0]['scroll'],.42)
        self.assertEqual(len(b.history),1)
        a.comparison='Test'
        with tempfile.TemporaryDirectory() as directory:
            store=SessionStore(Path(directory)/'session.json');store.save(Session([a,b],1))
            self.assertEqual(store.load(),Session([a,b],1))
        for i in range(150):history.visit(a,'Test',f'Gen.{i+1}.1')
        self.assertEqual(len(a.history),100)

    def test_first_visit_has_no_fictitious_default_passage(self):
        state=TabState()
        history.visit(state,'Other','John.1.1')
        self.assertEqual([e['reference'] for e in state.history],['John.1.1'])

    def test_preferences_roundtrip_and_invalid_original_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'reading.json';prefs=Preferences(path)
            prefs.value.font='Noto Serif';prefs.value.size=26;prefs.value.verse_numbers=False
            prefs.save();self.assertEqual(Preferences(path).value,prefs.value)
            path.write_text('{broken');invalid=Preferences(path)
            self.assertFalse(invalid.writable)
            with self.assertRaises(ValueError):invalid.save()
            self.assertEqual(path.read_text(),'{broken')

    def test_source_structure_retains_words_and_ignores_unsafe_notes(self):
        raw='<title>Source heading</title><p>First<note>Private note</note> words.</p><l>Second line.</l><l>Third line.</l>'
        segments=extract(raw,'First words.Second line.Third line.','OSIS')
        self.assertEqual(''.join(s.text for s in segments if s.kind=='text'),'First words.Second line.Third line.')
        self.assertIn('Source heading',[s.text for s in segments if s.kind=='heading'])
        self.assertNotIn('Private note',''.join(s.text for s in segments))
        self.assertTrue(any(s.kind=='poetry' for s in segments))
        self.assertEqual(extract('<script>bad</script>different','Original','OSIS')[0].text,'Original')
        self.assertEqual(extract('<literal>','<literal>','Plain')[0].text,'<literal>')

    def test_paragraph_milestones_do_not_invent_book_divisions(self):
        segments=extract('Before<p eID="1"/><p sID="2"/>After</div>','BeforeAfter','OSIS')
        self.assertEqual([s.text for s in segments],['Before','\n\n','After'])
        segments=extract('<div type="book">Text</div>','Text','OSIS')
        self.assertEqual([s.text for s in segments],['Text'])

    def test_localized_languages_keep_variants_and_unknown_codes(self):
        self.assertIn('français',language_info('fra','fr')[0].lower())
        self.assertNotEqual(language_info('az','fr')[0],language_info('azb','fr')[0])
        self.assertIn('méridional',language_info('azb','fr')[0].lower())
        self.assertIn('latin',language_info('sr-Latn','fr')[0].lower())
        self.assertIn('brésil',language_info('pt-BR','fr')[0].lower())
        self.assertIn('English',search_terms('en'))
        self.assertIn('zzz',language_info('zzz','fr')[0])
