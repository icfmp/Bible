"""Two-store annotation safety: whole-input validation and interrupted recovery."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bible.notes import NoteStore
from bible.highlights import HighlightStore
from bible import personal_backup as backup
from tests.test_notes import create

class PersonalBackupTests(unittest.TestCase):
    def stores(self,root):
        notes=NoteStore(root/'notes.sqlite3');self.addCleanup(notes.close)
        return notes,HighlightStore(root/'highlights.json')

    def test_unicode_markdown_labels_ranges_missing_resources_roundtrip_merge(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);notes,marks=self.stores(root)
            original=create(notes,end='John.4.2');marks.set('KJV',['John.3.16','Gen.1.1'],'yellow','AbsentModule')
            path=root/'all.json';backup.export(notes,marks,path);data=path.read_bytes()
            self.assertIn('ελληνικά',data.decode());self.assertNotIn('credential',data.decode())
            notes.save('Edited local',('Local',),existing=original)
            marks.set('KJV',['John.3.16'],'blue','LocalModule')
            result=backup.restore(notes,marks,path)
            self.assertEqual(len(notes.all()),2);self.assertEqual(result['conflicts'],2)
            self.assertIn(original.body,[n.body for n in notes.all()]);self.assertEqual(marks.entries[('KJV','John.3.16')]['color'],'blue')
            self.assertEqual(len(backup.decode(Path(result['backup']).read_bytes())[0]),1)
            result=backup.restore(notes,marks,path);self.assertEqual(result['added_notes'],0)
            target=root/'target';target.mkdir();other,colors=self.stores(target)
            backup.restore(other,colors,path);self.assertEqual(other.get(original.id),original);self.assertEqual(len(colors.entries),2)

    def test_invalid_entire_input_or_backup_write_failure_changes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);notes,marks=self.stores(root);create(notes);marks.set('KJV',['Gen.1.1'],'green','Test')
            good=backup.snapshot(notes,marks);path=root/'incoming.json'
            for mutate in (lambda v:v.update(version=2),lambda v:v['notes'].append({'bad':'note'}),lambda v:v['highlights'].append({'bad':'mark'})):
                value=json.loads(good);mutate(value);path.write_text(json.dumps(value))
                with self.assertRaises((ValueError,KeyError)):backup.restore(notes,marks,path)
                self.assertEqual(backup.snapshot(notes,marks),good)
            path.write_bytes(good)
            with patch('bible.personal_backup.atomic',side_effect=OSError('read only')):
                with self.assertRaises(OSError):backup.restore(notes,marks,path)
            self.assertEqual(backup.snapshot(notes,marks),good);self.assertFalse((root/'annotation-restore.pending.json').exists())

    def test_highlight_write_failure_recovers_both_stores_and_restart_is_repeatable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);notes,marks=self.stores(root);note=create(notes);marks.set('KJV',['Gen.1.1'],'green','Test')
            before=backup.snapshot(notes,marks);incoming=json.loads(before);incoming['notes'][0]['body']='Imported change'
            path=root/'incoming.json';path.write_text(json.dumps(incoming))
            actual=backup.write_marks;calls=[]
            def interrupted(*args):
                calls.append(1)
                if len(calls)==1:raise OSError('disk interrupted')
                return actual(*args)
            with patch('bible.personal_backup.write_marks',side_effect=interrupted):
                with self.assertRaises(OSError):backup.restore(notes,marks,path)
            self.assertEqual(backup.snapshot(notes,marks),before)
            # Simulate power loss after durable marker and one store changed.
            import hashlib
            safety=root/'backups'/'before-restore-crash.json';backup.atomic(safety,before)
            backup.atomic(root/'annotation-restore.pending.json',json.dumps(dict(backup=safety.name,sha256=hashlib.sha256(before).hexdigest())).encode())
            notes.save('Uncommitted restore outcome',(),existing=note)
            self.assertTrue(backup.recover(notes,marks));self.assertEqual(backup.snapshot(notes,marks),before)
            self.assertFalse(backup.recover(notes,marks))

    def test_legacy_notes_and_highlights_backups_remain_importable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);notes,marks=self.stores(root);original=create(notes)
            marks.set('KJV',['Gen.1.1'],'yellow','AbsentModule')
            note_file=root/'legacy-notes.json';notes.export(note_file)
            mark_file=root/'legacy-marks.json';marks.backup(mark_file)
            target=root/'target';target.mkdir();other,colors=self.stores(target)
            backup.restore(other,colors,note_file);backup.restore(other,colors,mark_file)
            self.assertEqual(other.get(original.id),original);self.assertEqual(colors.entries,marks.entries)
