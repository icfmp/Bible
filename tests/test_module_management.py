"""Update offers require fresh source identity and original-file evidence."""

from __future__ import annotations

from dataclasses import replace
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from bible.library import Library
from bible.module_management import checked_modules
from tests.test_module_lifecycle import package


class ModuleManagementTests(unittest.TestCase):
    def test_fresh_identity_local_changes_and_offline_are_distinct(self) -> None:
        old, payload = package("1.0", "ORIGINAL SOURCE FIXTURE")
        new, _ = package("1.1", "NEXT SOURCE FIXTURE")
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(Path(temporary) / "translations")
            with patch(
                "bible.library.download", side_effect=lambda url, out, progress: out.write(payload)
            ):
                library.install(old)

            def state(resources, errors={}):
                return checked_modules(library, resources, errors)[old.id]["state"]

            self.assertEqual(state([new]), "available")
            self.assertEqual(state([old]), "current")
            self.assertEqual(state([]), "missing")
            self.assertEqual(state([new], {old.source: "Synthetic offline"}), "offline")
            self.assertEqual(state([replace(new, versification="Luther")]), "identity-changed")
            receipt = library.root / old.id / ".source.json"
            value = json.loads(receipt.read_text())
            value.pop("files_sha256")
            receipt.write_text(json.dumps(value))
            self.assertEqual(state([new]), "local-unverified")
            # Do not adopt today's bytes as a supposed original fingerprint.
            self.assertNotIn("files_sha256", json.loads(receipt.read_text()))

    def test_one_source_failure_does_not_invent_a_current_or_other_publisher_update(self) -> None:
        from bible.providers import CROSSWIRE, EBIBLE

        curated, payload = package("1.0", "ORIGINAL SOURCE FIXTURE")
        old = replace(
            curated,
            provider_id=CROSSWIRE.id,
            source=CROSSWIRE.name,
            source_url=CROSSWIRE.url,
            acquisition="",
        )
        other = replace(
            old, provider_id=EBIBLE.id, source=EBIBLE.name, source_url=EBIBLE.url, version="2.0"
        )
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(Path(temporary) / "translations")
            with patch(
                "bible.library.download", side_effect=lambda url, out, progress: out.write(payload)
            ):
                library.install(old)
            self.assertEqual(checked_modules(library, [other], {})[old.id]["state"], "missing")

    def test_one_damaged_installation_receipt_does_not_block_other_verified_sources(self) -> None:
        from bible.providers import CROSSWIRE

        old, payload = package("1.0", "ORIGINAL SOURCE FIXTURE")
        new, _ = package("1.1", "NEXT SOURCE FIXTURE")
        direct = replace(
            old,
            provider_id=CROSSWIRE.id,
            source=CROSSWIRE.name,
            source_url=CROSSWIRE.url,
            acquisition="",
        )
        next_direct = replace(
            new,
            provider_id=CROSSWIRE.id,
            source=CROSSWIRE.name,
            source_url=CROSSWIRE.url,
            acquisition="",
        )
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(Path(temporary) / "translations")
            with patch(
                "bible.library.download", side_effect=lambda url, out, progress: out.write(payload)
            ):
                library.install(old)
                library.install(direct)
            (library.root / old.id / ".source.json").write_bytes(b"[")
            report = checked_modules(library, [new, next_direct], {})
            self.assertEqual(report[old.id]["state"], "local-unverified")
            self.assertEqual(report[direct.id]["state"], "available")
