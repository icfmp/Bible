"""Additive note relationships, verified migration and portable recovery."""
from dataclasses import asdict
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from bible.notes import NoteStore,PassageLink,NoteConflict,NotesError
from bible.highlights import HighlightStore
from bible import personal_backup
from tests.test_notes import create


class LinkedNoteTests(unittest.TestCase):
    def open(self,root):
        store=NoteStore(root/'notes.sqlite3');self.addCleanup(store.close);return store

    def legacy(self,root):
        store=NoteStore(root/'notes.sqlite3');note=create(store);store.close()
        with sqlite3.connect(root/'notes.sqlite3') as db:
            db.execute('DROP TABLE note_passages');db.execute('PRAGMA user_version=1')
        return note

    def test_verified_v1_migration_keeps_identity_dates_body_labels_and_private_backup(self):
        import stat
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);original=self.legacy(root);store=self.open(root)
            self.assertEqual(store.get(original.id),original)
            backups=list((root/'backups').glob('notes-before-schema-2-*.sqlite3'));self.assertEqual(len(backups),1)
            self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode),0o600)
            with sqlite3.connect(backups[0]) as old:
                self.assertEqual(old.execute('PRAGMA user_version').fetchone()[0],1)
                self.assertEqual(old.execute('PRAGMA quick_check').fetchone()[0],'ok')
                self.assertEqual(old.execute('SELECT id,body,created,modified,revision FROM notes').fetchone(),
                                 (original.id,original.body,original.created,original.modified,original.revision))
            self.assertEqual(store.db.execute('PRAGMA user_version').fetchone()[0],2)

    def test_failed_migration_rolls_back_and_keeps_original_and_verified_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);original=self.legacy(root);before=(root/'notes.sqlite3').read_bytes()
            with patch.object(NoteStore,'_create_passages',side_effect=OSError('Interrupted schema write')):
                with self.assertRaises(OSError):NoteStore(root/'notes.sqlite3')
            self.assertEqual((root/'notes.sqlite3').read_bytes(),before)
            self.assertEqual(len(list((root/'backups').glob('*.sqlite3'))),1)
            self.assertEqual(self.open(root).get(original.id),original)

    def test_multiple_passages_deduplicate_keep_uuid_and_survive_reopen_export_and_legacy_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);store=self.open(root);note=create(store)
            link=PassageLink('KJV','Gen.1.1','Gen.1.3')
            saved=store.save(note.body,note.labels,existing=note,links=(link,link,note.passages[0]))
            self.assertEqual(saved.id,note.id);self.assertEqual(saved.created,note.created)
            self.assertEqual(saved.links,(link,));self.assertEqual(store.passage('KJV','Gen.1.2'),[saved])
            self.assertEqual(self.open(root).get(note.id),saved)
            with self.assertRaises(NoteConflict):store.save('Stale draft',(),existing=note,links=())
            backup=root/'new.json';store.export(backup)
            restored=NoteStore(root/'other.sqlite3');self.addCleanup(restored.close)
            restored.restore(backup);self.assertEqual(restored.get(note.id),saved)
            legacy=asdict(note);legacy.pop('links');backup.write_text(json.dumps(dict(format='bible-notes',version=1,notes=[legacy])))
            target=NoteStore(root/'legacy.sqlite3');self.addCleanup(target.close)
            target.restore(backup);self.assertEqual(target.get(note.id),note)
            removed=store.save(saved.body,saved.labels,existing=saved,links=())
            self.assertEqual(removed.id,note.id);self.assertEqual(store.passage('KJV','Gen.1.2'),[])

    def test_combined_conflict_merge_preserves_all_relationships_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);store=self.open(root);marks=HighlightStore(root/'highlights.json')
            note=create(store);link=PassageLink('Catholic','Ps.33.2','Ps.33.4')
            note=store.save(note.body,note.labels,existing=note,links=(link,))
            marks.set('KJV',['Gen.1.1'],'green','AbsentModule')
            file=root/'all.json';personal_backup.export(store,marks,file)
            store.save('Local draft already saved',note.labels,existing=note,links=())
            first=personal_backup.restore(store,marks,file)
            self.assertEqual(first['conflicts'],1);self.assertEqual(len(store.all()),2)
            imported=next(n for n in store.all() if n.id!=note.id)
            self.assertEqual(imported.links,(link,));self.assertEqual(imported.body,note.body)
            second=personal_backup.restore(store,marks,file);self.assertEqual(second['added_notes'],0)
            data=json.loads(file.read_text());data['notes'][0]['links'][0]['end']='John.1.1'
            file.write_text(json.dumps(data));before=personal_backup.snapshot(store,marks)
            with self.assertRaises((NotesError,ValueError)):personal_backup.restore(store,marks,file)
            self.assertEqual(personal_backup.snapshot(store,marks),before)
