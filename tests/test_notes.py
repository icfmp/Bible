from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from bible.notes import NoteStore, NoteConflict, NotesError, APPLICATION_ID
from bible.markdown import render


def create(store, body='**Sentinel note** ελληνικά עברית', start='John.3.16', end=None, labels=('Foi', 'Étude')):
    return store.save(body, labels, versification='KJV', start=start, end=end,
                      origin_translation='OriginalBible', origin_language='fr')


class NoteTests(unittest.TestCase):
    def store(self, directory):
        store = NoteStore(Path(directory) / 'notes.sqlite3')
        self.addCleanup(store.close)
        return store

    def test_initial_schema_persistence_passages_and_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory)
            first = create(store, end='John.3.18')
            second = create(store, 'Second note', 'Gen.1.1', labels=('foi', 'Ancien'))
            self.assertEqual(store.db.execute('PRAGMA user_version').fetchone()[0], 1)
            self.assertEqual(store.db.execute('PRAGMA application_id').fetchone()[0], APPLICATION_ID)
            reopened = self.store(directory)
            self.assertEqual(reopened.get(first.id), first)
            self.assertEqual(set(reopened.labels()), {'Foi', 'Étude', 'Ancien'})
            self.assertEqual(reopened.passage('KJV', 'John.3.17'), [first])
            self.assertEqual(reopened.passage('Catholic', 'John.3.17'), [])
            self.assertEqual(reopened.passage('KJV', 'John.3.19'), [])
            self.assertEqual([n.id for n in reopened.search('Jean 3:16', ['FOI'])], [first.id])
            self.assertEqual([n.id for n in reopened.search('second', ['foi'])], [second.id])
            self.assertEqual(reopened.search('second', ['foi', 'Étude']), [])
            self.assertEqual([n.start for n in reopened.search(order='bible')], ['Gen.1.1', 'John.3.16'])
            self.assertEqual(reopened.search(order='recent')[0].id, second.id)
            self.assertEqual(reopened.search(order='oldest')[0].id, first.id)

    def test_cross_chapter_range_roundtrip_keeps_schema_identity_and_legacy_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            store=self.store(directory);legacy=create(store)
            crossing=create(store,'Cross-chapter retained body','John.3.36','John.4.2')
            self.assertTrue(crossing.covers('John.4.1'));self.assertFalse(crossing.covers('John.4.3'))
            self.assertEqual(store.passage('KJV','John.4.1'),[crossing])
            self.assertEqual(store.passage('KJV','John.3.1','John.3.36'),[legacy,crossing])
            self.assertEqual(store.db.execute('PRAGMA user_version').fetchone()[0],1)
            backup=Path(directory)/'backup.json';store.export(backup)
            reopened=self.store(directory);self.assertEqual(reopened.get(crossing.id),crossing)
            self.assertEqual(reopened.get(legacy.id),legacy)
            target=NoteStore(Path(directory)/'restored.sqlite3');self.addCleanup(target.close)
            target.restore(backup);self.assertEqual(target.get(crossing.id),crossing)
            self.assertEqual(target.get(legacy.id),legacy)

    def test_future_or_unrelated_database_is_not_modified(self):
        for version, app in [(2, APPLICATION_ID), (1, 0), (0, 0)]:
            with self.subTest(version=version, app=app), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'notes.sqlite3'
                with sqlite3.connect(path) as db:
                    db.execute('CREATE TABLE precious_data (body TEXT)')
                    db.execute("INSERT INTO precious_data VALUES ('keep me')")
                    db.execute(f'PRAGMA user_version={version}')
                    db.execute(f'PRAGMA application_id={app}')
                before = path.read_bytes()
                with self.assertRaises(NotesError):
                    NoteStore(path)
                self.assertEqual(path.read_bytes(), before)

    def test_empty_database_migrates_explicitly_and_private_files(self):
        import stat
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'notes.sqlite3'
            store = self.store(directory)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(store.all(), [])
            backup = Path(directory) / 'backup.json'
            store.export(backup)
            self.assertEqual(stat.S_IMODE(backup.stat().st_mode), 0o600)

    def test_optimistic_edits_and_failed_write_preserve_old_note(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory)
            first = create(store)
            other = self.store(directory)
            updated = other.save('Updated elsewhere', ['New'], existing=first)
            with self.assertRaises(NoteConflict):
                store.save('Unsaved draft', ['Keep'], existing=first)
            with self.assertRaises(NoteConflict):
                store.delete(first)
            self.assertEqual(store.get(first.id), updated)
            with patch.object(store, '_write', side_effect=OSError('disk failed')):
                with self.assertRaises(OSError):
                    store.save('Keep old data', [], existing=updated)
            self.assertEqual(store.get(first.id), updated)
            self.assertEqual(store.labels(), ['New'])

    def test_backup_merge_conflicts_duplicates_and_unicode(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory)
            first = create(store)
            backup = Path(directory) / 'notes.json'
            store.export(backup)
            edited = store.save('Local edited version', ['Local'], existing=first)
            self.assertEqual(store.restore(backup), (1, 0, 1))
            self.assertEqual(len(store.all()), 2)
            self.assertEqual(store.get(first.id), edited)
            self.assertTrue(any(n.body == first.body and n.labels == first.labels for n in store.all()))
            self.assertEqual(store.restore(backup), (0, 1, 0))
            with tempfile.TemporaryDirectory() as target:
                restored = self.store(target)
                self.assertEqual(restored.restore(backup), (1, 0, 0))
                self.assertEqual(restored.get(first.id), first)

    def test_invalid_restore_validates_every_record_before_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory)
            original = create(store)
            backup = Path(directory) / 'bad.json'
            for value in [{}, {'format': 'bible-notes', 'version': 2, 'notes': []},
                          {'format': 'bible-notes', 'version': 1, 'notes': [asdict(original), {'body': 'invalid'}]},
                          {'format': 'bible-notes', 'version': 1, 'notes': [asdict(original), asdict(original)]}]:
                backup.write_text(json.dumps(value))
                with self.assertRaises(NotesError):
                    store.restore(backup)
                self.assertEqual(store.all(), [original])
            backup.write_text('{not json')
            with self.assertRaises(NotesError):
                store.restore(backup)
            self.assertEqual(store.all(), [original])

    def test_restore_transaction_rolls_back_after_a_partial_write_failure(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as target:
            original = self.store(source)
            create(original, 'Imported first')
            create(original, 'Imported second', 'Gen.1.1')
            backup = Path(source) / 'backup.json'
            original.export(backup)
            store = self.store(target)
            existing = create(store, 'Keep local', labels=['Local'])
            write = store._write
            calls = []
            def fail_on_second(note):
                calls.append(note.id)
                if len(calls) == 2:
                    raise OSError('disk full')
                write(note)
            with patch.object(store, '_write', side_effect=fail_on_second):
                with self.assertRaises(OSError):
                    store.restore(backup)
            self.assertEqual(store.all(), [existing])
            self.assertEqual(store.labels(), ['Local'])

    def test_failed_export_preserves_existing_backup_and_protects_database(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory)
            first = create(store)
            backup = Path(directory) / 'backup.json'
            backup.write_text('previous backup')
            with patch('bible.notes.os.replace', side_effect=OSError('disk failure')):
                with self.assertRaises(OSError):
                    store.export(backup)
            self.assertEqual(backup.read_text(), 'previous backup')
            with self.assertRaises(NotesError):
                store.export(store.path)
            self.assertEqual(store.get(first.id), first)
            self.assertEqual(list(Path(directory).glob('.notes-backup-*')), [])

    def test_delete_is_transactional_and_does_not_touch_other_notes(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory)
            first = create(store)
            second = create(store, 'Other', 'Gen.1.1', labels=['Other'])
            store.delete(first)
            self.assertEqual(store.all(), [second])
            self.assertEqual(store.labels(), ['Other'])

    def test_invalid_passage_body_labels_and_backup_size(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self.store(directory)
            for start, end in [('John.3.18', 'John.3.16'), ('John.4.1', 'John.3.16'), ('John.3.16','Acts.1.1'), ('../escape', None)]:
                with self.assertRaises(NotesError):
                    create(store, start=start, end=end)
            for body in ['', '\x00', 'a' * 200001]:
                with self.assertRaises(NotesError):
                    create(store, body=body)
            for labels in [[''], ['a' * 81], ['\n'], list(map(str, range(33)))]:
                with self.assertRaises(NotesError):
                    create(store, labels=labels)
            self.assertEqual(store.all(), [])
            oversized = Path(directory) / 'large.json'
            with oversized.open('wb') as stream:
                stream.truncate(32 * 1024 * 1024 + 1)
            with self.assertRaises(NotesError):
                store.restore(oversized)

    def test_markdown_is_inert_and_preserves_untrusted_text(self):
        source = '**Gras** et *italique*\n- στοιχείο עברית\n<script>bad()</script>\n[x](javascript:bad) [web](https://example.test) ![image](file:///secret)'
        text, spans = render(source)
        self.assertIn('Gras et italique', text)
        self.assertIn('• στοιχείο עברית', text)
        self.assertIn('<script>bad()</script>', text)
        self.assertIn('javascript:bad', text)
        self.assertIn('file:///secret', text)
        self.assertEqual(text[spans[0][1]:spans[0][2]], 'Gras')
        self.assertEqual({kind for kind, _, _ in spans}, {'bold', 'italic', 'link'})
