"""Existing-provider consumption: metadata identity, native staging and cache safety."""

import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from bible.providers import BIBLE_RESOURCES, DEFAULT_PROVIDERS
from bible.curated_catalogue import entries, catalogue, package_record
from bible.library import Library, resource_from_section, config, catalogues
from bible.catalogue_cache import CatalogueCache
from tests.test_library import fixture, archive_bytes, CONF


def record(payload=b"package"):
    return dict(
        id="test-edition",
        canonical_edition_id="identified-test-edition",
        sword_id="Test",
        version="1.0",
        edition="faithful",
        category="bible",
        language="en",
        versification="KJV",
        title={"en": "Test fixture"},
        download=dict(
            url=BIBLE_RESOURCES.packages_url + "Test.zip",
            size_bytes=len(payload),
            sha256=hashlib.sha256(payload).hexdigest(),
        ),
    )


def body(records):
    return json.dumps(
        dict(
            schema_version=1,
            repository="Bible Resources",
            repository_url=BIBLE_RESOURCES.url,
            modules=records,
        )
    ).encode()


def sword_metadata(conf):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        member = tarfile.TarInfo("mods.d/test.conf")
        member.size = len(conf)
        archive.addfile(member, io.BytesIO(conf))
    return output.getvalue()


class CuratedCatalogueTests(unittest.TestCase):
    def test_malformed_saved_package_identity_is_not_treated_as_a_valid_offline_catalogue(self):
        from dataclasses import replace

        item = replace(
            resource_from_section("Test", config(CONF)["Test"], BIBLE_RESOURCES),
            acquisition="malformed",
        )
        with tempfile.TemporaryDirectory() as temporary:
            cache = CatalogueCache(temporary)
            cache.write(BIBLE_RESOURCES, [item])
            path = Path(temporary) / "bible-resources.json"
            before = path.read_bytes()
            self.assertIsNone(cache.read(BIBLE_RESOURCES))
            self.assertEqual(path.read_bytes(), before)

    def test_optional_provider_is_not_added_to_existing_automatic_defaults(self):
        self.assertNotIn(BIBLE_RESOURCES, DEFAULT_PROVIDERS)
        with patch("bible.library.catalogue", return_value=[]) as fetch:
            catalogues()
        self.assertNotIn(BIBLE_RESOURCES, [call.args[0] for call in fetch.call_args_list])

    def test_json_and_sword_metadata_must_agree_without_inventing_missing_fields(self):
        conf = CONF + b"Version=1.0\n"
        calls = []

        def fetch(url, out, **kwargs):
            calls.append(url)
            out.write(body([record()]) if url.endswith(".json") else sword_metadata(conf))

        with patch("bible.library.download", side_effect=fetch):
            resource = catalogue()[0]
        self.assertEqual(resource.id, "bible-resources~Test")
        self.assertEqual(resource.version, "1.0")
        self.assertEqual(resource.license, "Public Domain")
        self.assertEqual(
            package_record(resource)["canonical_edition_id"], "identified-test-edition"
        )
        with patch(
            "bible.library.download",
            side_effect=lambda url, out, **kw: out.write(
                body([record()]) if url.endswith(".json") else sword_metadata(CONF)
            ),
        ):
            with self.assertRaisesRegex(ValueError, "disagree"):
                catalogue()
        with patch(
            "bible.library.download", side_effect=lambda url, out, **kw: out.write(body([]))
        ) as fetch:
            self.assertEqual(catalogue(), [])
            self.assertEqual(fetch.call_count, 1)

    def test_duplicates_rebranding_and_bad_package_identity_are_rejected(self):
        for records in (
            [record(), record()],
            [record(), dict(record(), id="renamed", sword_id="Other")],
            [dict(record(), canonical_edition_id="")],
            [
                dict(
                    record(),
                    download=dict(
                        record()["download"], url=BIBLE_RESOURCES.packages_url + "../Test.zip"
                    ),
                )
            ],
            [dict(record(), download=None)],
        ):
            with self.subTest(records=records), self.assertRaises(ValueError):
                entries(body(records))

    def test_dictionary_without_verse_system_does_not_block_supported_editions(self):
        bible = record()
        dictionary = dict(
            record(),
            id="dictionary",
            canonical_edition_id="dictionary",
            sword_id="Dictionary",
            category="dictionary",
            versification=None,
            download=dict(
                record()["download"], url=BIBLE_RESOURCES.packages_url + "Dictionary.zip"
            ),
        )
        self.assertEqual(entries(body([dictionary, bible])), [bible])
        calls = []

        def fetch(url, out, **kwargs):
            calls.append(url)
            out.write(
                body([dictionary, bible])
                if url.endswith(".json")
                else sword_metadata(CONF + b"Version=1.0\n")
            )

        with patch("bible.library.download", side_effect=fetch):
            resources = catalogue()
        self.assertEqual([r.name for r in resources], ["Test"])
        self.assertEqual(package_record(resources[0]), bible)
        self.assertEqual(len(calls), 2)
        with patch(
            "bible.library.download",
            side_effect=lambda url, out, **kw: out.write(body([dictionary])),
        ) as fetch:
            self.assertEqual(catalogue(), [])
            self.assertEqual(fetch.call_count, 1)

    def test_ignored_dictionary_still_requires_safe_identity_and_integrity(self):
        dictionary = dict(record(), category="dictionary", versification=None)
        for invalid in (
            dict(dictionary, canonical_edition_id=""),
            dict(dictionary, download=dict(dictionary["download"], sha256="invalid")),
            dict(
                dictionary,
                download=dict(
                    dictionary["download"], url=BIBLE_RESOURCES.packages_url + "../Test.zip"
                ),
            ),
            dict(dictionary, category="commentary"),
            dict(dictionary, category="unknown"),
        ):
            with self.subTest(record=invalid), self.assertRaises(ValueError):
                entries(body([invalid]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            entries(body([dictionary, record()]))
        from dataclasses import replace

        resource = replace(
            resource_from_section("Test", config(CONF)["Test"], BIBLE_RESOURCES),
            acquisition=json.dumps(
                dict(catalogue_url=BIBLE_RESOURCES.catalogue_url, entry=dictionary)
            ),
        )
        with self.assertRaisesRegex(ValueError, "Unsupported curated resource type"):
            package_record(resource)

    def test_hashed_initial_install_reads_native_text_and_preserves_unrelated_files(self):
        from dataclasses import replace
        from bible.sword_provider import Reader

        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as directory:
            fixture(source)
            path = Path(source) / "mods.d/test.conf"
            path.write_bytes(CONF + b"Version=1.0\n")
            payload = archive_bytes(
                {
                    str(p.relative_to(source)): p.read_bytes()
                    for p in Path(source).rglob("*")
                    if p.is_file()
                }
            )
            entry = record(payload)
            resource = replace(
                resource_from_section("Test", config(path.read_bytes())["Test"], BIBLE_RESOURCES),
                acquisition=json.dumps(
                    dict(catalogue_url=BIBLE_RESOURCES.catalogue_url, entry=entry)
                ),
            )
            root = Path(directory)
            personal = root / "personal-notes"
            personal.write_bytes(b"UNCHANGED PERSONAL RECORD")
            library = Library(root / "translations")
            with patch(
                "bible.library.download", side_effect=lambda url, out, progress: out.write(payload)
            ):
                library.install(resource)
            self.assertEqual(library.resource(resource.id), resource)
            reader = Reader(library.root / resource.id, "Test")
            self.assertIn("SENTINEL", reader.chapter("Gen.1.1").verses[0][1])
            self.assertEqual(personal.read_bytes(), b"UNCHANGED PERSONAL RECORD")
            installed = {
                p: p.read_bytes() for p in (library.root / resource.id).rglob("*") if p.is_file()
            }
            # Same-ID native CrossWire roots are separate and never overwritten.
            original = library.root / "Test"
            original.mkdir()
            (original / "keep").write_bytes(b"OTHER PUBLISHER")
            with patch("bible.library.download", side_effect=AssertionError("No overwrite")):
                library.install(resource)
            self.assertEqual(installed, {p: p.read_bytes() for p in installed})
            self.assertEqual((original / "keep").read_bytes(), b"OTHER PUBLISHER")
            for damaged in (payload + b"x", payload[:-1] + b"x"):
                other = Library(root / ("bad-" + hashlib.sha256(damaged).hexdigest()[:8]))
                with patch(
                    "bible.library.download",
                    side_effect=lambda url, out, progress: out.write(damaged),
                ):
                    with self.assertRaisesRegex(ValueError, "size|checksum"):
                        other.install(resource)
                self.assertEqual(other.installed(), [])
            cancelled = Library(root / "cancelled")
            with self.assertRaises(InterruptedError):
                cancelled.install(resource, cancelled=lambda: True)
            self.assertEqual(cancelled.installed(), [])

    def test_bad_refresh_preserves_cached_edition_and_conditional_304(self):
        from dataclasses import replace

        resource = replace(
            resource_from_section("Test", config(CONF + b"Version=1.0\n")["Test"], BIBLE_RESOURCES),
            acquisition=json.dumps(
                dict(catalogue_url=BIBLE_RESOURCES.catalogue_url, entry=record())
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            cache = CatalogueCache(directory)
            cache.write(BIBLE_RESOURCES, [resource], {"ETag": '"verified"'})
            path = Path(directory) / "bible-resources.json"
            old = path.read_bytes()
            with patch(
                "bible.library.download",
                side_effect=lambda url, out, **kw: out.write(b"broken JSON"),
            ):
                result = catalogues((BIBLE_RESOURCES,), cache=cache, force=True)
            self.assertEqual(result.resources, (resource,))
            self.assertIn(BIBLE_RESOURCES.name, result.errors)
            self.assertEqual(path.read_bytes(), old)

            def unchanged(url, out, **kwargs):
                self.assertEqual(kwargs["headers"]["If-None-Match"], '"verified"')
                raise HTTPError(url, 304, "Not modified", {}, None)

            with patch("bible.library.download", side_effect=unchanged):
                result = catalogues((BIBLE_RESOURCES,), cache=cache, force=True)
            self.assertEqual(result.resources, (resource,))
            self.assertFalse(result.errors)
