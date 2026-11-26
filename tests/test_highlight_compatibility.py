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

from bible.highlights import HighlightStore, payload, merge, decode as decode
from bible.notes import NoteStore
from bible import personal_backup
from tests.test_notes import create


def legacy(color="yellow"):
    return dict(
        version=1, marks=[dict(system="KJV", reference="Gen.1.1", color=color, resource="Absent")]
    )


def hold_lock(path, connection):
    store = HighlightStore(path)
    with store.locked():
        connection.send("locked")
        connection.recv()


class CompatibilityTests(unittest.TestCase):
    def test_migration_restart_recolor_delete_and_clean_restore_preserve_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "highlights.json"
            original = json.dumps(legacy()).encode()
            path.write_bytes(original)
            store = HighlightStore(path)
            self.assertFalse(store.error)
            mark = dict(next(iter(store.entries.values())))
            self.assertIsNone(mark["created"])
            self.assertIsNone(mark["modified"])
            safety = next((root / "backups").glob("highlights-before-schema-2-*.json"))
            self.assertEqual(safety.read_bytes(), original)
            self.assertEqual(safety.stat().st_mode & 0o777, 0o600)
            self.assertEqual(HighlightStore(path).entries, store.entries)
            store.set("KJV", ["Gen.1.1"], "blue", "Other")
            edited = store.entries[("KJV", "Gen.1.1")]
            self.assertEqual(edited["id"], mark["id"])
            self.assertEqual(edited["revision"], 2)
            self.assertEqual(edited["origin_resource"], "Absent")
            self.assertIsNone(edited["created"])
            self.assertIsNotNone(edited["modified"])
            before = dict(edited)
            store.set("KJV", ["Gen.1.1"], "blue", "Other")
            self.assertEqual(store.entries[("KJV", "Gen.1.1")], before)
            portable = root / "portable.json"
            store.backup(portable)
            target = HighlightStore(root / "clean" / "highlights.json")
            target.restore(portable)
            target.restore(portable)
            self.assertEqual(target.entries, store.entries)
            store.set("KJV", ["Gen.1.1"], None, "Other")
            store.set("KJV", ["Gen.1.1"], "blue", "Other")
            self.assertNotEqual(store.entries[("KJV", "Gen.1.1")]["id"], mark["id"])
            self.assertEqual(
                len(list((root / "backups").glob("highlights-before-schema-2-*.json"))), 1
            )

    def test_failed_or_interrupted_migration_is_repeatable_without_unsafe_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "highlights.json"
            original = json.dumps(legacy()).encode()
            path.write_bytes(original)
            expected = payload(path)
            with patch("bible.highlights.os.replace", side_effect=OSError("Interrupted migration")):
                failed = HighlightStore(path)
            self.assertTrue(failed.error)
            self.assertEqual(path.read_bytes(), original)
            with self.assertRaises(ValueError):
                failed.set("KJV", ["Gen.1.1"], "green", "Absent")
            self.assertEqual(HighlightStore(path).entries, expected)
            # A failed private backup verification cannot authorize a migration.
            path.write_bytes(original)
            safety = next((root / "backups").glob("*.json"))
            safety.write_bytes(b"corrupted safety copy")
            self.assertTrue(HighlightStore(path).error)
            self.assertEqual(path.read_bytes(), original)

    def test_legacy_and_current_conflicts_are_retained_and_repeated_imports_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            store = HighlightStore(root / "highlights.json")
            store.set("KJV", ["Gen.1.1"], "green", "Absent")
            path = root / "legacy.json"
            path.write_text(json.dumps(legacy("green")))
            self.assertEqual(store.restore(path)["conflicts"], 0)
            original = dict(store.entries)
            path.write_text(json.dumps(legacy("blue")))
            result = store.restore(path)
            self.assertEqual(result["conflicts"], 1)
            self.assertEqual(store.entries, original)
            recovery = Path(result["backup"])
            self.assertEqual(payload(recovery)[("KJV", "Gen.1.1")]["color"], "blue")
            self.assertEqual(store.restore(path)["backup"], str(recovery))
            self.assertEqual(store.entries, original)
            mark = dict(next(iter(store.entries.values())))
            for incoming in (
                dict(mark, color="yellow"),
                dict(mark, reference="Gen.1.2"),
                dict(mark, id=str(uuid.uuid4())),
            ):
                merged, rejected = merge(
                    store.entries, {(incoming["system"], incoming["reference"]): incoming}
                )
                self.assertEqual(merged, original)
                self.assertEqual(list(rejected.values()), [incoming])

    def test_stale_writer_unknown_metadata_and_duplicate_ids_cannot_erase_data(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "highlights.json"
            a = HighlightStore(path)
            b = HighlightStore(path)
            a.set("KJV", ["Gen.1.1"], "yellow", "Absent")
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                b.set("KJV", ["John.3.16"], "blue", "Absent")
            self.assertEqual(path.read_bytes(), before)
            good = json.loads(before)
            for value in (
                dict(good, version=99),
                dict(good, unknown=True),
                dict(good, marks=[dict(good["marks"][0], unknown="keep")]),
                dict(good, marks=[good["marks"][0], dict(good["marks"][0], reference="Gen.1.2")]),
            ):
                path.write_text(json.dumps(value))
                saved = path.read_bytes()
                store = HighlightStore(path)
                self.assertTrue(store.error)
                with self.assertRaises(ValueError):
                    store.set("KJV", ["Gen.1.1"], "blue", "Absent")
                self.assertEqual(path.read_bytes(), saved)

    @unittest.skipIf(os.name == "nt", "POSIX process-lock integration")
    def test_another_process_lock_refuses_autosave_without_waiting_or_replacing(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "highlights.json"
            store = HighlightStore(path)
            store.set("KJV", ["Gen.1.1"], "green", "Absent")
            before = path.read_bytes()
            parent, child = multiprocessing.Pipe()
            process = multiprocessing.Process(target=hold_lock, args=(path, child))
            process.start()
            try:
                self.assertTrue(parent.poll(5))
                self.assertEqual(parent.recv(), "locked")
                with self.assertRaises(OSError):
                    store.set("KJV", ["Gen.1.1"], "blue", "Absent")
                self.assertEqual(path.read_bytes(), before)
            finally:
                parent.send("done")
                process.join(5)
                if process.is_alive():
                    process.terminate()
                    process.join()
                parent.close()
                child.close()

    def test_combined_versions_and_pending_legacy_recovery_preserve_notes_and_ids(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            notes = NoteStore(root / "notes.sqlite3")
            self.addCleanup(notes.close)
            note = create(notes)
            high = HighlightStore(root / "highlights.json")
            high.set("KJV", ["Gen.1.1"], "blue", "Absent")
            notes_before = [asdict(n) for n in notes.all()]
            original = personal_backup.snapshot(notes, high)
            self.assertEqual(json.loads(original)["version"], 3)
            for version in (1, 2):
                incoming = dict(
                    format="bible-personal-annotations",
                    version=version,
                    notes=[asdict(note)],
                    highlights=legacy()["marks"],
                )
                path = root / f"old{version}.json"
                path.write_text(json.dumps(incoming))
                result = personal_backup.restore(notes, high, path)
                self.assertEqual(result["added_notes"], 0)
                self.assertEqual(len(high.entries), 1)
                self.assertTrue(result["highlight_conflicts_backup"])
                self.assertEqual([asdict(n) for n in notes.all()], notes_before)
            # A recovery journal from an older alpha still restores all notes and
            # deterministic legacy IDs; startup must not migrate ahead of recovery.
            import hashlib

            data = json.dumps(incoming).encode()
            safety = root / "backups" / "before-restore-old.json"
            personal_backup.atomic(safety, data)
            marker = root / "annotation-restore.pending.json"
            personal_backup.atomic(
                marker,
                json.dumps(
                    dict(backup=safety.name, sha256=hashlib.sha256(data).hexdigest())
                ).encode(),
            )
            high.path.write_text(json.dumps(legacy()))
            reopened = HighlightStore(high.path)
            self.assertFalse(reopened.error)
            self.assertEqual(json.loads(high.path.read_text())["version"], 1)
            self.assertTrue(personal_backup.recover(notes, reopened))
            self.assertFalse(personal_backup.recover(notes, reopened))
            self.assertEqual([asdict(n) for n in notes.all()], notes_before)
            self.assertIsNone(next(iter(reopened.entries.values()))["created"])
            self.assertEqual(HighlightStore(high.path).entries, reopened.entries)

    def test_process_interruption_after_highlight_replace_recovers_original_stores(self):
        class SimulatedPowerLoss(BaseException):
            pass

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            notes = NoteStore(root / "notes.sqlite3")
            self.addCleanup(notes.close)
            note = create(notes)
            high = HighlightStore(root / "highlights.json")
            high.set("KJV", ["Gen.1.1"], "blue", "Absent")
            original = personal_backup.snapshot(notes, high)
            value = json.loads(original)
            value["notes"][0]["body"] = "Interrupted imported note"
            value["highlights"][0]["color"] = "green"
            value["highlights"][0]["reference"] = "Gen.1.2"
            value["highlights"][0]["id"] = str(uuid.uuid4())
            path = root / "incoming.json"
            path.write_text(json.dumps(value))
            actual = personal_backup.write_marks

            def power_loss(*args):
                actual(*args)
                raise SimulatedPowerLoss()

            with patch("bible.personal_backup.write_marks", side_effect=power_loss):
                with self.assertRaises(SimulatedPowerLoss):
                    personal_backup.restore(notes, high, path)
            self.assertTrue(high.pending.exists())
            self.assertIn(("KJV", "Gen.1.2"), payload(high.path))
            reopened = HighlightStore(high.path)
            self.assertTrue(personal_backup.recover(notes, reopened))
            self.assertEqual(personal_backup.snapshot(notes, reopened), original)
            self.assertEqual(notes.get(note.id), note)
            self.assertFalse(high.pending.exists())

    def test_valid_large_legacy_store_has_room_for_new_identity_fields(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "highlights.json"
            value = dict(
                version=1,
                marks=[
                    dict(
                        system="S" * 64,
                        reference=f"Gen.{i // 1000 + 1}.{i % 1000 + 1}",
                        color="yellow",
                        resource="R" * 256,
                    )
                    for i in range(19000)
                ],
            )
            data = json.dumps(value).encode()
            self.assertLess(len(data), 8 * 1024 * 1024)
            path.write_bytes(data)
            store = HighlightStore(path)
            self.assertFalse(store.error)
            self.assertEqual(len(store.entries), 19000)
            self.assertGreater(path.stat().st_size, 8 * 1024 * 1024)
            self.assertEqual(payload(path), store.entries)

    def test_note_autosave_rechecks_recovery_after_obtaining_sqlite_write_lock(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            notes = NoteStore(root / "notes.sqlite3")
            self.addCleanup(notes.close)
            note = create(notes)
            source = root / "notes-backup.json"
            notes.export(source)
            original = [asdict(n) for n in notes.all()]
            marker = root / "annotation-restore.pending.json"
            actual = notes.ensure_recovered
            for action in (
                lambda: notes.save("Keep existing draft", (), existing=note),
                lambda: notes.save(
                    "Keep new draft",
                    (),
                    versification="KJV",
                    start="Gen.1.1",
                    origin_translation="Absent",
                    origin_language="en",
                ),
                lambda: notes.delete(note),
                lambda: notes.restore(source),
                lambda: notes.export(root / "blocked-export.json"),
            ):
                calls = []

                def restore_starts_after_early_check():
                    actual()
                    calls.append(1)
                    if len(calls) == 1:
                        marker.write_text(
                            "Pending restore sentinel; never execute this as recovery"
                        )

                with patch.object(
                    notes, "ensure_recovered", side_effect=restore_starts_after_early_check
                ):
                    with self.assertRaises(ValueError):
                        action()
                self.assertEqual([asdict(n) for n in notes.all()], original)
                marker.unlink()
            self.assertFalse((root / "blocked-export.json").exists())

    def test_unknown_note_only_backup_fields_are_preserved_without_partial_import(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            notes = NoteStore(root / "notes.sqlite3")
            self.addCleanup(notes.close)
            note = create(notes)
            path = root / "newer-fields.json"
            value = dict(
                format="bible-notes",
                version=2,
                notes=[asdict(note)],
                future_metadata={"keep": "unchanged"},
            )
            path.write_text(json.dumps(value))
            before = path.read_bytes()
            for action in (lambda: notes.restore(path), lambda: personal_backup.decode(before)):
                with self.assertRaises(ValueError):
                    action()
                self.assertEqual(notes.get(note.id), note)
                self.assertEqual(path.read_bytes(), before)

    def test_expanded_import_capacity_is_validated_before_restore_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            notes = NoteStore(root / "notes.sqlite3")
            self.addCleanup(notes.close)
            note = create(notes)
            high = HighlightStore(root / "highlights.json")
            path = root / "oversized-expanded.json"
            value = legacy()
            value["marks"] = [dict(value["marks"][0], reference=f"Gen.1.{i}") for i in range(1, 20)]
            path.write_text(json.dumps(value))
            with patch("bible.highlights.MAX_BYTES", 1000):
                with self.assertRaises(ValueError):
                    personal_backup.restore(notes, high, path)
            self.assertEqual(notes.get(note.id), note)
            self.assertFalse(high.pending.exists())
            self.assertFalse(high.path.exists())
            self.assertFalse((root / "backups").exists())

    def test_legacy_identity_does_not_hide_divergent_v2_provenance_or_revision(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            store = HighlightStore(root / "highlights.json")
            store.set("KJV", ["Gen.1.1"], "yellow", "Absent")
            raw = root / "legacy.json"
            raw.write_text(json.dumps(legacy()))
            normalized = payload(raw)
            key = ("KJV", "Gen.1.1")
            for altered in (
                dict(normalized[key], revision=2),
                dict(normalized[key], origin_resource="Other"),
            ):
                merged, conflicts = merge(store.entries, {key: altered})
                self.assertEqual(merged, store.entries)
                self.assertEqual(conflicts, {key: altered})

    def test_wall_clock_correction_cannot_prevent_recoloring_or_reassign_identity(self):
        with tempfile.TemporaryDirectory() as d:
            store = HighlightStore(Path(d) / "highlights.json")
            store.set("KJV", ["Gen.1.1"], "yellow", "Absent")
            original = store.entries[("KJV", "Gen.1.1")]
            with patch("bible.highlights.now", return_value="2000-01-01T00:00:00+00:00"):
                store.set("KJV", ["Gen.1.1"], "blue", "Absent")
            edited = payload(store.path)[("KJV", "Gen.1.1")]
            self.assertEqual(edited["id"], original["id"])
            self.assertEqual(edited["created"], original["created"])
            self.assertEqual(edited["modified"], "2000-01-01T00:00:00+00:00")
            self.assertEqual(edited["revision"], original["revision"] + 1)
