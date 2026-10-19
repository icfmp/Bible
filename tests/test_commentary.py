import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from bible.library import Library, catalogue, config, resource_from_section
from bible.sword_provider import Reader, CommentaryReader, VersificationMismatch
from tests.fixtures import module_fixture
from tests.test_library import archive_bytes


def commentary_fixture(directory, name='Notes', versification='KJV', entries=None):
    root = Path(directory) / 'translations' / name
    module_fixture(root, name, entries if entries is not None else [
        ('Gen.1.1', 'COMMENTARY TEST DATA α — ελληνικά עברית <literal>'),
        ('John.3.16', 'JOHN COMMENTARY TEST DATA')],
        versification=versification, commentary=True)
    (root / '.complete').write_text(name)
    return root


class CommentaryTests(unittest.TestCase):
    def test_exact_lookup_missing_blank_and_versification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = commentary_fixture(directory, entries=[
                ('John.3.16', 'COMMENTARY TEST DATA α — ελληνικά עברית <literal>'),
                ('John.3.18', ' ')])
            reader = CommentaryReader(root, 'Notes')
            self.assertEqual(reader.first_reference(), 'John.3.16')
            self.assertEqual(reader.entry('Jean 3:16', 'KJV'),
                             'COMMENTARY TEST DATA α — ελληνικά עברית <literal>')
            self.assertIsNone(reader.entry('John.3.17', 'KJV'))
            self.assertIsNone(reader.entry('John.3.18', 'KJV'))
            with self.assertRaises(VersificationMismatch):
                reader.entry('John.3.16', 'Catholic')
            with self.assertRaises(ValueError):
                Reader(root, 'Notes')

    def test_linked_entries_follow_sword_indices(self):
        import Sword
        with tempfile.TemporaryDirectory() as directory:
            root = commentary_fixture(directory)
            path = root / 'modules/texts/rawtext/test'
            module = Sword.RawCom(str(path), 'Notes', 'Test data only')
            module.setKey(Sword.VerseKey('John.3.17'))
            module.linkEntry(Sword.VerseKey('John.3.16'))
            del module
            reader = CommentaryReader(root, 'Notes')
            self.assertTrue(reader.module.isLinked(reader.key('John.3.16'), reader.key('John.3.17')))
            self.assertEqual(reader.entry('John.3.17', 'KJV'), reader.entry('John.3.16', 'KJV'))
            self.assertIsNone(reader.entry('John.3.18', 'KJV'))

    def test_catalogue_types_authors_and_unavailable_formats(self):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode='w:gz') as archive:
            for name, driver, extra in [('Bible', 'RawText', ''), ('Notes', 'RawCom', ''),
                                        ('LockedNotes', 'zCom', 'CipherKey=\n'),
                                        ('OtherNotes', 'HREFCom', 'Category=Commentaries\n'),
                                        ('Dictionary', 'RawLD', '')]:
                content = (f'[{name}]\nModDrv={driver}\nLang=fr\nAuthor=Fixture Author\n'
                           f'DistributionLicense=Copyrighted\n{extra}').encode()
                entry = tarfile.TarInfo(f'mods.d/{name}.conf')
                entry.size = len(content)
                archive.addfile(entry, io.BytesIO(content))
        with patch('bible.library.download', side_effect=lambda url, out, **kw: out.write(data.getvalue())):
            resources = {r.name: r for r in catalogue()}
        self.assertEqual(set(resources), {'Bible', 'Notes', 'LockedNotes', 'OtherNotes'})
        self.assertEqual(resources['Notes'].kind, 'commentary')
        self.assertEqual(resources['Notes'].author, 'Fixture Author')
        self.assertTrue(resources['Notes'].installable)
        self.assertFalse(resources['LockedNotes'].installable)
        self.assertFalse(resources['OtherNotes'].installable)

    def test_commentary_install_and_attribution_offline(self):
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as directory:
            root = commentary_fixture(source)
            path = root / 'mods.d/test.conf'
            path.write_bytes(path.read_bytes() + b'Author=Test Author\nCopyrightNotes=Test conditions\n')
            resource = resource_from_section('Notes', config(path.read_bytes())['Notes'])
            payload = archive_bytes({str(p.relative_to(root)): p.read_bytes()
                                     for p in root.rglob('*') if p.is_file() and p.name != '.complete'})
            library = Library(directory)
            with patch('bible.library.download', side_effect=lambda url, out, progress: out.write(payload)):
                library.install(resource)
            with patch('urllib.request.urlopen', side_effect=AssertionError('Offline')):
                self.assertEqual(library.installed('bible'), [])
                self.assertEqual(library.installed('commentary'), ['Notes'])
                self.assertEqual(library.resource('Notes'), resource)
                reader = CommentaryReader(Path(directory) / 'Notes', 'Notes')
                self.assertIn('COMMENTARY TEST DATA', reader.entry(reader.first_reference(), 'KJV'))

    def test_type_change_cannot_install_a_commentary_as_a_bible(self):
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as source, tempfile.TemporaryDirectory() as directory:
            root = commentary_fixture(source)
            resource = resource_from_section('Notes', config((root / 'mods.d/test.conf').read_bytes())['Notes'])
            payload = archive_bytes({str(p.relative_to(root)): p.read_bytes()
                                     for p in root.rglob('*') if p.is_file() and p.name != '.complete'})
            with patch('bible.library.download', side_effect=lambda url, out, progress: out.write(payload)):
                with self.assertRaisesRegex(ValueError, 'Resource type changed'):
                    Library(directory).install(replace(resource, driver='RawText'))
            self.assertEqual(list(Path(directory).iterdir()), [])
