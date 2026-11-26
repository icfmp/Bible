"""Actual SWORD staging, atomic directory exchange, rollback and restart safety."""

from __future__ import annotations

from dataclasses import replace
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bible.library import Library, config, resource_from_section
from bible.providers import BIBLE_RESOURCES
from bible.module_lifecycle import ModuleLifecycle, exchange, operation_lock, tree_manifest
from bible.module_updates import applicable_update
from tests.test_library import fixture, archive_bytes, CONF
from tests.test_curated_catalogue import record


def package(version, text, *, omit_second_chapter: bool = False):
    import Sword

    with tempfile.TemporaryDirectory() as source:
        fixture(source)
        root = Path(source)
        module = Sword.RawText(
            str(root / "modules/texts/rawtext/test"), "Test", "Synthetic lifecycle fixture"
        )
        module.setKey(Sword.VerseKey("Gen.1.1"))
        module.setEntry(text)
        if omit_second_chapter:
            module.setKey(Sword.VerseKey("Gen.2.1"))
            module.setEntry("")
        del module
        conf = (
            CONF
            + f"Version={version}\nTextSource=Identified synthetic lifecycle edition\n".encode()
        )
        (root / "mods.d/test.conf").write_bytes(conf)
        payload = archive_bytes(
            {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        )
    entry = dict(record(payload), version=version)
    resource = replace(
        resource_from_section("Test", config(conf)["Test"], BIBLE_RESOURCES),
        acquisition=json.dumps(dict(catalogue_url=BIBLE_RESOURCES.catalogue_url, entry=entry)),
    )
    return resource, payload


class ModuleLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.old, cls.old_zip = package("1.0", "OLD EXACT SOURCE FIXTURE")
        cls.new, cls.new_zip = package("1.1", "NEW EXACT SOURCE FIXTURE")

    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.library = Library(self.root / "translations")
        self.lifecycle = ModuleLifecycle(self.library)
        self.personal = self.root / "notes-and-preferences"
        self.personal.write_bytes(b"PERSONAL DATA IS OUTSIDE MODULE ROOTS")
        with self.download(self.old_zip):
            self.library.install(self.old)

    def download(self, payload):
        return patch(
            "bible.library.download", side_effect=lambda url, out, progress: out.write(payload)
        )

    def text(self):
        from bible.sword_provider import Reader

        return (
            Reader(self.library.root / self.old.id, self.old.name).chapter("Gen.1.1").verses[0][1]
        )

    def test_verified_update_then_rollback_keeps_exact_source_and_personal_data(self) -> None:
        before = tree_manifest(self.library.root / self.old.id)
        with self.download(self.new_zip):
            result = self.lifecycle.update(self.new)
        self.assertEqual(result["state"], "committed")
        self.assertIn("NEW EXACT SOURCE", self.text())
        self.assertEqual(self.library.resource(self.old.id).version, "1.1")
        self.assertEqual(self.lifecycle.rollback(self.old.id)["state"], "rolled-back")
        self.assertEqual(tree_manifest(self.library.root / self.old.id), before)
        self.assertIn("OLD EXACT SOURCE", self.text())
        self.assertEqual(self.personal.read_bytes(), b"PERSONAL DATA IS OUTSIDE MODULE ROOTS")

    def test_cancel_corrupt_package_and_atomic_exchange_failure_retain_usable_old_version(
        self,
    ) -> None:
        before = tree_manifest(self.library.root / self.old.id)
        for payload, cancelled in ((self.new_zip + b"bad", False), (self.new_zip, True)):
            with (
                self.subTest(cancelled=cancelled),
                self.download(payload),
                self.assertRaises((ValueError, InterruptedError)),
            ):
                self.lifecycle.update(self.new, cancelled=lambda: cancelled)
            self.assertEqual(tree_manifest(self.library.root / self.old.id), before)
        with (
            self.download(self.new_zip),
            patch(
                "bible.module_lifecycle.exchange",
                side_effect=PermissionError("Synthetic permission failure"),
            ),
        ):
            with self.assertRaises(PermissionError):
                self.lifecycle.update(self.new)
        self.assertEqual(tree_manifest(self.library.root / self.old.id), before)
        self.assertIn("OLD EXACT SOURCE", self.text())
        self.assertFalse(self.lifecycle.rollback_candidate(self.old.id))

    def test_restart_recovers_exchange_interrupted_before_commit_record(self) -> None:
        before = tree_manifest(self.library.root / self.old.id)
        stage = Library(self.root / "candidate")
        with self.download(self.new_zip):
            stage.install(self.new)
        folder, journal = self.lifecycle.begin(self.old.id, "update", before)
        (stage.root / self.new.id).rename(folder / "backup")
        journal.update(state="prepared", after=tree_manifest(folder / "backup"))
        self.lifecycle.journal(folder, journal)
        exchange(self.library.root / self.old.id, folder / "backup")
        self.assertIn("NEW EXACT SOURCE", self.text())
        reopened = Library(self.library.root)
        self.assertFalse(reopened.recovery_errors)
        self.assertEqual(tree_manifest(reopened.root / self.old.id), before)
        self.assertIn("OLD EXACT SOURCE", self.text())

    def test_local_changes_and_lost_reference_coverage_are_never_overwritten(self) -> None:
        missing, payload = package("1.1", "NEW SOURCE", omit_second_chapter=True)
        before = tree_manifest(self.library.root / self.old.id)
        with self.download(payload), self.assertRaisesRegex(ValueError, "reference coverage"):
            self.lifecycle.update(missing)
        self.assertEqual(tree_manifest(self.library.root / self.old.id), before)
        path = self.library.root / self.old.id / "mods.d/test.conf"
        path.write_bytes(path.read_bytes() + b"About=Local modification\n")
        changed = tree_manifest(self.library.root / self.old.id)
        with (
            self.download(self.new_zip),
            self.assertRaisesRegex(ValueError, "Local module changes"),
        ):
            self.lifecycle.update(self.new)
        self.assertEqual(tree_manifest(self.library.root / self.old.id), changed)

    def test_shared_root_links_extra_local_files_and_concurrent_operations_are_refused(
        self,
    ) -> None:
        folder = self.library.root / self.old.id
        with (
            operation_lock(self.library.root),
            self.assertRaisesRegex(ValueError, "already running"),
        ):
            self.lifecycle.remove(self.old.id)
        extra = folder / "personal-local-file"
        extra.write_bytes(b"UNRELATED LOCAL FILE")
        with self.assertRaisesRegex(ValueError, "Additional local files"):
            self.lifecycle.remove(self.old.id)
        self.assertEqual(extra.read_bytes(), b"UNRELATED LOCAL FILE")
        extra.unlink()
        original = self.root / "external-copy"
        folder.rename(original)
        folder.symlink_to(original, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "External"):
            self.lifecycle.remove(self.old.id)
        self.assertTrue((original / ".complete").exists())

    def test_a_retained_native_reader_prevents_removal_instead_of_becoming_stale(self) -> None:
        from bible.sword_provider import Reader

        reader = Reader(self.library.root / self.old.id, self.old.name)
        before = tree_manifest(self.library.root / self.old.id)
        with (
            patch("bible.module_lifecycle.LEASE_TIMEOUT", 0.1),
            self.assertRaisesRegex(ValueError, "still in use"),
        ):
            self.lifecycle.remove(self.old.id)
        self.assertEqual(tree_manifest(self.library.root / self.old.id), before)
        self.assertIn("OLD EXACT SOURCE", reader.chapter("Gen.1.1").verses[0][1])

    def test_removal_affects_only_the_selected_owned_module_and_keeps_annotations(self) -> None:
        from bible.providers import CROSSWIRE
        from bible.sword_provider import Reader

        other = replace(
            self.old,
            provider_id=CROSSWIRE.id,
            source=CROSSWIRE.name,
            source_url=CROSSWIRE.url,
            acquisition="",
        )
        with self.download(self.old_zip):
            self.library.install(other)
        before = tree_manifest(self.library.root / other.id)
        reader = Reader(self.library.root / self.old.id, self.old.name)
        self.assertIn("OLD EXACT SOURCE", reader.chapter("Gen.1.1").verses[0][1])
        # The GUI must quiesce/drop native consumers before the switch. The
        # earlier counterexample showed an old lazy handle can no longer read
        # reliably afterwards; this headless caller follows that contract.
        del reader
        self.assertTrue(self.lifecycle.remove(self.old.id)["removed"])
        self.assertEqual(self.lifecycle.removed_resources()[self.old.id], self.old)
        self.assertEqual(
            ModuleLifecycle(Library(self.library.root)).removed_resources()[self.old.id], self.old
        )
        self.assertEqual(self.library.installed(), [other.id])
        self.assertEqual(tree_manifest(self.library.root / other.id), before)
        with self.assertRaises(ValueError):
            Reader(self.library.root / self.old.id, self.old.name)
        self.assertEqual(self.personal.read_bytes(), b"PERSONAL DATA IS OUTSIDE MODULE ROOTS")

    def test_same_version_repacked_or_different_curated_edition_is_not_an_update(self) -> None:
        record = json.loads(self.new.acquisition)
        self.assertEqual(applicable_update(self.old, self.new), "available")
        record["entry"]["canonical_edition_id"] = "another-edition"
        self.assertEqual(
            applicable_update(self.old, replace(self.new, acquisition=json.dumps(record))),
            "edition-changed",
        )
        changed = replace(self.new, version="1.0")
        record["entry"]["canonical_edition_id"] = "identified-test-edition"
        record["entry"]["version"] = "1.0"
        self.assertEqual(
            applicable_update(self.old, replace(changed, acquisition=json.dumps(record))),
            "same-version-content-changed",
        )
        self.assertEqual(
            applicable_update(self.old, replace(self.new, license="Different source rights")),
            "edition-changed",
        )
        self.assertEqual(
            applicable_update(
                self.old, replace(self.new, text_source="Another original publisher")
            ),
            "edition-changed",
        )

    def test_failed_removal_commit_restores_source_immediately_and_cleans_cancelled_intent(
        self,
    ) -> None:
        before = tree_manifest(self.library.root / self.old.id)
        write = self.lifecycle.journal

        def journal(folder, record) -> None:
            if record["state"] == "committed":
                raise OSError("Synthetic commit write failure")
            write(folder, record)

        with (
            patch.object(self.lifecycle, "journal", side_effect=journal),
            self.assertRaises(OSError),
        ):
            self.lifecycle.remove(self.old.id)
        self.assertEqual(tree_manifest(self.library.root / self.old.id), before)
        self.assertFalse(self.lifecycle.was_removed(self.old.id))
        self.assertFalse(list(self.lifecycle.records() or ()))

        def cancel(_: object) -> None:
            raise InterruptedError("Synthetic cancellation before switch")

        with self.assertRaises(InterruptedError):
            self.lifecycle.remove(self.old.id, before_switch=cancel)
        self.assertEqual(tree_manifest(self.library.root / self.old.id), before)
        self.assertFalse(list(self.lifecycle.records() or ()))

    def test_failed_and_interrupted_rollback_preserve_the_current_version_until_commit(
        self,
    ) -> None:
        with self.download(self.new_zip):
            self.lifecycle.update(self.new)
        current = tree_manifest(self.library.root / self.old.id)

        def stop(_: object) -> None:
            raise InterruptedError("Synthetic rollback cancellation")

        with self.assertRaises(InterruptedError):
            self.lifecycle.rollback(self.old.id, before_switch=stop)
        self.assertEqual(tree_manifest(self.library.root / self.old.id), current)
        for swapped in (False, True):
            with self.subTest(swapped=swapped):
                folder, record = self.lifecycle.rollback_candidate(self.old.id)
                record["state"] = "rollback-prepared"
                self.lifecycle.journal(folder, record)
                if swapped:
                    exchange(self.library.root / self.old.id, folder / "backup")
                reopened = Library(self.library.root)
                self.assertFalse(reopened.recovery_errors)
                self.assertEqual(tree_manifest(self.library.root / self.old.id), current)
                self.assertIsNotNone(ModuleLifecycle(reopened).rollback_candidate(self.old.id))

    def test_direct_provider_staging_uses_each_source_and_restores_exact_previous_files(
        self,
    ) -> None:
        from bible.providers import CROSSWIRE, EBIBLE, EXTRA

        for provider in (CROSSWIRE, EBIBLE, EXTRA):
            with self.subTest(provider=provider.id), tempfile.TemporaryDirectory() as temporary:
                library = Library(Path(temporary) / "translations")
                lifecycle = ModuleLifecycle(library)

                def sourced(resource):
                    return replace(
                        resource,
                        provider_id=provider.id,
                        source=provider.name,
                        source_url=provider.url,
                        acquisition="",
                    )

                old = sourced(self.old)
                new = sourced(self.new)
                self.assertEqual(
                    applicable_update(
                        replace(old, text_source="First source\nSecond source"),
                        replace(new, text_source="First source\nDifferent source"),
                    ),
                    "edition-changed",
                )
                with self.download(self.old_zip):
                    library.install(old)
                before = tree_manifest(library.root / old.id)
                with self.download(self.new_zip) as fetch:
                    lifecycle.update(new)
                self.assertEqual(fetch.call_args.args[0], provider.packages_url + "Test.zip")
                self.assertEqual(library.resource(old.id).source, provider.name)
                self.assertEqual(library.resource(old.id).version, "1.1")
                lifecycle.rollback(old.id)
                self.assertEqual(tree_manifest(library.root / old.id), before)

    def test_missing_crash_journal_preserves_reading_and_blocks_mutation_without_guessing(
        self,
    ) -> None:
        before = tree_manifest(self.library.root / self.old.id)
        folder = self.library.root / ".transactions" / ("a" * 32)
        folder.mkdir(parents=True)
        unknown = folder / "uncommitted-journal.tmp"
        unknown.write_bytes(b"INCOMPLETE PRIVATE OPERATION METADATA")
        reopened = Library(self.library.root)
        self.assertTrue(reopened.recovery_errors)
        lifecycle = ModuleLifecycle(reopened)
        self.assertEqual(lifecycle.removed_resources(), {})
        self.assertTrue(lifecycle.was_removed("SavedMissingResource"))
        self.assertIn("OLD EXACT SOURCE", self.text())
        with self.assertRaisesRegex(ValueError, "recovery metadata"):
            lifecycle.remove(self.old.id)
        self.assertEqual(tree_manifest(self.library.root / self.old.id), before)
        self.assertEqual(unknown.read_bytes(), b"INCOMPLETE PRIVATE OPERATION METADATA")
