"""Native SWORD dictionary fixtures exercise lifecycle, never shipped content."""

from dataclasses import replace
import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from bible.library import Library, config, resource_from_section
from bible.module_lifecycle import ModuleLifecycle
from bible.module_updates import applicable_update
from bible.providers import CROSSWIRE
from bible.sword_provider import DictionaryReader, GeneralBookReader
from tests.test_library import archive_bytes


def package(driver, version):
    import Sword

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        folder = "genbook" if driver == "RawGenBook" else "lexdict"
        base = root / "modules" / folder / driver.lower() / "fixture"
        base.parent.mkdir(parents=True)
        factory = getattr(Sword, driver)
        factory.createModule(str(base))
        if driver == "zLD":
            compressor = Sword.ZipCompress()
            module = factory(str(base), "Test", "Synthetic lifecycle fixture", 200, compressor)
            # zStr takes ownership; keep SWIG from deleting that same pointer
            # when this local Python wrapper is collected after the writer.
            compressor.thisown = False
        else:
            module = factory(str(base), "Test", "Synthetic lifecycle fixture")
        if driver == "RawGenBook":
            key = Sword.TreeKey.castTo(module.getKey())
            key.assureKeyPath("/ENTRY")
            key.save()
        else:
            module.setKey(Sword.SWKey("ENTRY"))
        module.setEntry("EXACT SYNTHETIC TOOL FIXTURE " + version)
        key = None
        del module
        conf = (
            f"[Test]\nDescription=Synthetic lifecycle fixture\nLang=en\nVersion={version}\n"
            f"DataPath=./modules/{folder}/{driver.lower()}/fixture\nModDrv={driver}\n"
            "Category=Lexicons / Dictionaries\nSourceType=Plaintext\nCompressType=ZIP\nEncoding=UTF-8\nDistributionLicense=Public Domain\n"
            "TextSource=Identified synthetic test edition\n"
        ).encode()
        (root / "mods.d").mkdir()
        (root / "mods.d/test.conf").write_bytes(conf)
        payload = archive_bytes(
            {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        )
        return resource_from_section("Test", config(conf)["Test"], CROSSWIRE), payload


class NativeDictionaryLifecycleTests(unittest.TestCase):
    def test_native_decoder_failure_is_confined_and_never_marks_the_module_installed(self):
        import io, zipfile

        old, payload = package("zLD", "1.0")
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            files = {n: archive.read(n) for n in archive.namelist()}
        # Keep the actual ZIP-compressed data, but declare an incompatible
        # decoder. This formerly stopped the process inside native SWORD.
        files["mods.d/test.conf"] = files["mods.d/test.conf"].replace(
            b"CompressType=ZIP", b"CompressType=LZSS"
        )
        damaged = archive_bytes(files)
        with tempfile.TemporaryDirectory() as temporary:
            library = Library(Path(temporary) / "translations")
            personal = Path(temporary) / "personal-note"
            personal.write_bytes(b"KEEP PERSONAL NOTE")
            with patch(
                "bible.library.download", side_effect=lambda url, out, progress: out.write(damaged)
            ):
                with self.assertRaisesRegex(ValueError, "could not verify"):
                    library.install(old)
            self.assertEqual(library.installed(), [])
            self.assertEqual(personal.read_bytes(), b"KEEP PERSONAL NOTE")

    def test_native_dictionary_install_update_rollback_remove_and_classification(self):
        for driver in ("RawLD", "RawLD4", "zLD", "RawGenBook"):
            with self.subTest(driver=driver), tempfile.TemporaryDirectory() as temporary:
                print("Native dictionary format:", driver, flush=True)
                old, before = package(driver, "1.0")
                new, after = package(driver, "1.1")
                library = Library(Path(temporary) / "translations")
                lifecycle = ModuleLifecycle(library)
                self.assertEqual(old.kind, "general" if driver == "RawGenBook" else "dictionary")
                self.assertTrue(old.installable)
                self.assertEqual(applicable_update(old, new), "available")
                with patch(
                    "bible.library.download",
                    side_effect=lambda url, out, progress: out.write(before),
                ):
                    library.install(old)
                self.assertEqual(library.installed("bible"), [])
                (GeneralBookReader if driver == "RawGenBook" else DictionaryReader)(
                    library.root / old.id, old.name
                ).verify_readable()
                with patch(
                    "bible.library.download",
                    side_effect=lambda url, out, progress: out.write(after),
                ):
                    lifecycle.update(new)
                self.assertEqual(library.resource(old.id).version, "1.1")
                lifecycle.rollback(old.id)
                self.assertEqual(library.resource(old.id).version, "1.0")
                self.assertTrue(lifecycle.remove(old.id)["removed"])
                self.assertTrue(lifecycle.was_removed(old.id))
                self.assertEqual(library.installed(), [])

    def test_general_book_and_unknown_formats_are_not_mislabelled_or_invented(self):
        from bible.library import Resource

        resource = Resource("General", "Provider book", "en", "Unknown", driver="RawGenBook")
        self.assertEqual(resource.kind, "general")
        self.assertTrue(resource.installable)
        self.assertFalse(replace(resource, driver="UnknownDriver").installable)
