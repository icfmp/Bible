import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from bible.session import Session, SessionError, SessionStore, TabState


class SessionTests(unittest.TestCase):
    def test_new_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / 'session.json')
            self.assertEqual(store.load(), Session())
            self.assertFalse(store.path.exists())

    def test_roundtrip_preserves_order_selection_positions_and_missing_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / 'session.json')
            session = Session([TabState('KJV', 'John.3.16', 0.53, True),
                               TabState('RemovedTranslation', 'Gen.2.1', 0.3)], 1)
            store.save(session)
            self.assertEqual(store.load(), session)
            self.assertEqual(stat.S_IMODE(store.path.stat().st_mode), 0o600)

    def test_failed_atomic_replace_preserves_existing_session(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SessionStore(Path(directory) / 'session.json')
            original = Session([TabState('KJV')])
            store.save(original)
            with patch('bible.session.os.replace', side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):
                    store.save(Session([TabState('Other')]))
            self.assertEqual(store.load(), original)
            self.assertEqual(list(Path(directory).iterdir()), [store.path])

    def test_corrupt_or_future_formats_are_not_rewritten(self):
        for content in ['{', '{"version":2,"tabs":[]}', '[]',
                        '{"version":1,"tabs":[],"selected":4}']:
            with self.subTest(content=content), tempfile.TemporaryDirectory() as directory:
                store = SessionStore(Path(directory) / 'session.json')
                store.path.write_text(content)
                with self.assertRaises(SessionError):
                    store.load()
                self.assertEqual(store.path.read_text(), content)

    def test_untrusted_values_are_rejected(self):
        for field, value in [('resource', '../outside'), ('reference', 3),
                             ('scroll', float('nan')), ('scroll', -1),
                             ('scroll', 2), ('study_visible', 'false')]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                tab = {'resource': 'KJV', 'reference': 'Gen.1.1', 'scroll': 0, 'study_visible': False}
                tab[field] = value
                store = SessionStore(Path(directory) / 'session.json')
                store.path.write_text(json.dumps({'version': 1, 'tabs': [tab]}))
                with self.assertRaises(SessionError):
                    store.load()
