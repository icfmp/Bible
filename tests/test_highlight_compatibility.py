"""Annotation v2 identity, migration, import conflicts and write isolation."""
from dataclasses import asdict
import json
import multiprocessing
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

from bible.highlights import HighlightStore, payload, merge, decode
from bible.notes import NoteStore
from bible import personal_backup
from tests.test_notes import create


def legacy(color='yellow'):
    return dict(version=1, marks=[dict(system='KJV', reference='Gen.1.1', color=color, resource='Absent')])


def hold_lock(path, connection):
    store = HighlightStore(path)
    with store.locked():
        connection.send('locked')
        connection.recv()


class CompatibilityTests(unittest.TestCase):
    def test_migration_restart_recolor_delete_and_clean_restore_preserve_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); path=root/'highlights.json'; original=json.dumps(legacy()).encode();path.write_bytes(original)
            store=HighlightStore(path);self.assertFalse(store.error)
            mark=dict(next(iter(store.entries.values())));self.assertIsNone(mark['created']);self.assertIsNone(mark['modified'])
            safety=next((root/'backups').glob('highlights-before-schema-2-*.json'))
            self.assertEqual(safety.read_bytes(),original);self.assertEqual(safety.stat().st_mode & 0o777,0o600)
            self.assertEqual(HighlightStore(path).entries,store.entries)
            store.set('KJV',['Gen.1.1'],'blue','Other');edited=store.entries[('KJV','Gen.1.1')]
            self.assertEqual(edited['id'],mark['id']);self.assertEqual(edited['revision'],2)
            self.assertEqual(edited['origin_resource'],'Absent');self.assertIsNone(edited['created']);self.assertIsNotNone(edited['modified'])
            before=dict(edited);store.set('KJV',['Gen.1.1'],'blue','Other');self.assertEqual(store.entries[('KJV','Gen.1.1')],before)
            portable=root/'portable.json';store.backup(portable)
            target=HighlightStore(root/'clean'/'highlights.json');target.restore(portable);target.restore(portable)
            self.assertEqual(target.entries,store.entries)
            store.set('KJV',['Gen.1.1'],None,'Other');store.set('KJV',['Gen.1.1'],'blue','Other')
            self.assertNotEqual(store.entries[('KJV','Gen.1.1')]['id'],mark['id'])
            self.assertEqual(len(list((root/'backups').glob('highlights-before-schema-2-*.json'))),1)

    def test_failed_or_interrupted_migration_is_repeatable_without_unsafe_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=root/'highlights.json';original=json.dumps(legacy()).encode();path.write_bytes(original)
            expected=payload(path)
            with patch('bible.highlights.os.replace',side_effect=OSError('Interrupted migration')):
                failed=HighlightStore(path)
            self.assertTrue(failed.error);self.assertEqual(path.read_bytes(),original)
            with self.assertRaises(ValueError):failed.set('KJV',['Gen.1.1'],'green','Absent')
            self.assertEqual(HighlightStore(path).entries,expected)
            # A failed private backup verification cannot authorize a migration.
            path.write_bytes(original)
            safety=next((root/'backups').glob('*.json'));safety.write_bytes(b'corrupted safety copy')
            self.assertTrue(HighlightStore(path).error);self.assertEqual(path.read_bytes(),original)

    def test_legacy_and_current_conflicts_are_retained_and_repeated_imports_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);store=HighlightStore(root/'highlights.json');store.set('KJV',['Gen.1.1'],'green','Absent')
            path=root/'legacy.json';path.write_text(json.dumps(legacy('green')))
            self.assertEqual(store.restore(path)['conflicts'],0);original=dict(store.entries)
            path.write_text(json.dumps(legacy('blue')))
            result=store.restore(path);self.assertEqual(result['conflicts'],1);self.assertEqual(store.entries,original)
            recovery=Path(result['backup']);self.assertEqual(payload(recovery)[('KJV','Gen.1.1')]['color'],'blue')
            self.assertEqual(store.restore(path)['backup'],str(recovery));self.assertEqual(store.entries,original)
            mark=dict(next(iter(store.entries.values())))
            for incoming in (dict(mark,color='yellow'),dict(mark,reference='Gen.1.2'),dict(mark,id=str(uuid.uuid4()))):
                merged,rejected=merge(store.entries,{(incoming['system'],incoming['reference']):incoming})
                self.assertEqual(merged,original);self.assertEqual(list(rejected.values()),[incoming])

    def test_stale_writer_unknown_metadata_and_duplicate_ids_cannot_erase_data(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'highlights.json';a=HighlightStore(path);b=HighlightStore(path)
            a.set('KJV',['Gen.1.1'],'yellow','Absent');before=path.read_bytes()
            with self.assertRaises(ValueError):b.set('KJV',['John.3.16'],'blue','Absent')
            self.assertEqual(path.read_bytes(),before)
            good=json.loads(before)
            for value in (dict(good,version=99),dict(good,unknown=True),dict(good,marks=[dict(good['marks'][0],unknown='keep')]),
                          dict(good,marks=[good['marks'][0],dict(good['marks'][0],reference='Gen.1.2')])):
                path.write_text(json.dumps(value));saved=path.read_bytes();store=HighlightStore(path);self.assertTrue(store.error)
                with self.assertRaises(ValueError):store.set('KJV',['Gen.1.1'],'blue','Absent')
                self.assertEqual(path.read_bytes(),saved)

    @unittest.skipIf(os.name=='nt','POSIX process-lock integration')
    def test_another_process_lock_refuses_autosave_without_waiting_or_replacing(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'highlights.json';store=HighlightStore(path);store.set('KJV',['Gen.1.1'],'green','Absent');before=path.read_bytes()
            parent,child=multiprocessing.Pipe();process=multiprocessing.Process(target=hold_lock,args=(path,child));process.start()
            try:
                self.assertTrue(parent.poll(5));self.assertEqual(parent.recv(),'locked')
                with self.assertRaises(OSError):store.set('KJV',['Gen.1.1'],'blue','Absent')
                self.assertEqual(path.read_bytes(),before)
            finally:
                parent.send('done');process.join(5)
                if process.is_alive():process.terminate();process.join()
                parent.close();child.close()

    def test_combined_versions_and_pending_legacy_recovery_preserve_notes_and_ids(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);notes=NoteStore(root/'notes.sqlite3');self.addCleanup(notes.close);note=create(notes)
            high=HighlightStore(root/'highlights.json');high.set('KJV',['Gen.1.1'],'blue','Absent')
            notes_before=[asdict(n) for n in notes.all()];original=personal_backup.snapshot(notes,high)
            self.assertEqual(json.loads(original)['version'],3)
            for version in (1,2):
                incoming=dict(format='bible-personal-annotations',version=version,notes=[asdict(note)],highlights=legacy()['marks'])
                path=root/f'old{version}.json';path.write_text(json.dumps(incoming))
                result=personal_backup.restore(notes,high,path);self.assertEqual(result['added_notes'],0)
                self.assertEqual(len(high.entries),1);self.assertTrue(result['highlight_conflicts_backup'])
                self.assertEqual([asdict(n) for n in notes.all()],notes_before)
            # A recovery journal from an older alpha still restores all notes and
            # deterministic legacy IDs; startup must not migrate ahead of recovery.
            import hashlib
            data=json.dumps(incoming).encode();safety=root/'backups'/'before-restore-old.json';personal_backup.atomic(safety,data)
            marker=root/'annotation-restore.pending.json';personal_backup.atomic(marker,json.dumps(dict(backup=safety.name,sha256=hashlib.sha256(data).hexdigest())).encode())
            high.path.write_text(json.dumps(legacy()))
            reopened=HighlightStore(high.path);self.assertFalse(reopened.error);self.assertEqual(json.loads(high.path.read_text())['version'],1)
            self.assertTrue(personal_backup.recover(notes,reopened));self.assertFalse(personal_backup.recover(notes,reopened))
            self.assertEqual([asdict(n) for n in notes.all()],notes_before);self.assertIsNone(next(iter(reopened.entries.values()))['created'])
            self.assertEqual(HighlightStore(high.path).entries,reopened.entries)

    def test_process_interruption_after_highlight_replace_recovers_original_stores(self):
        class SimulatedPowerLoss(BaseException):
            pass
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);notes=NoteStore(root/'notes.sqlite3');self.addCleanup(notes.close);note=create(notes)
            high=HighlightStore(root/'highlights.json');high.set('KJV',['Gen.1.1'],'blue','Absent')
            original=personal_backup.snapshot(notes,high);value=json.loads(original)
            value['notes'][0]['body']='Interrupted imported note'
            value['highlights'][0]['color']='green';value['highlights'][0]['reference']='Gen.1.2'
            value['highlights'][0]['id']=str(uuid.uuid4())
            path=root/'incoming.json';path.write_text(json.dumps(value));actual=personal_backup.write_marks
            def power_loss(*args):
                actual(*args)
                raise SimulatedPowerLoss()
            with patch('bible.personal_backup.write_marks',side_effect=power_loss):
                with self.assertRaises(SimulatedPowerLoss):personal_backup.restore(notes,high,path)
            self.assertTrue(high.pending.exists());self.assertIn(('KJV','Gen.1.2'),payload(high.path))
            reopened=HighlightStore(high.path);self.assertTrue(personal_backup.recover(notes,reopened))
            self.assertEqual(personal_backup.snapshot(notes,reopened),original)
            self.assertEqual(notes.get(note.id),note);self.assertFalse(high.pending.exists())
