"""Dataset identity, safe atomic updates and verified numbering with real SWORD."""
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from bible import reference_data as data
from bible.reference_data import ReferenceData,ReferenceDataError


def archive(path,rows):
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as output:
        output.writestr('cross_references.txt','From Verse\tTo Verse\tVotes\t#www.openbible.info CC-BY '+data.SOURCE_DATE+'\n'+rows)
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReferenceDataTests(unittest.TestCase):
    def test_directed_relationship_ranking_range_deduplication_and_offline_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'data.zip'
            digest=archive(source,'John.1.5\tIsa.9.2\t15\nJohn.1.6\tIsa.9.2\t20\nJohn.1.5\tPs.18.28\t20\nJohn.1.5\tGen.1.3\t-5\n')
            store=ReferenceData(root/'study-data')
            with patch.object(data,'ARCHIVE_SHA256',digest):metadata=store.install_archive(source)
            self.assertEqual(metadata['relationships'],4)
            self.assertEqual(metadata['archive_sha256'],digest)
            reopened=ReferenceData(root/'study-data')
            rows=reopened.query(['John.1.5','John.1.6','John.1.5'])
            self.assertEqual([(r.start,r.score,r.source_count) for r in rows],
                             [('Ps.18.28',20,1),('Isa.9.2',20,2),('Gen.1.3',-5,1)])
            self.assertEqual(reopened.query(['Isa.9.2']),[],'Directed links must not become reciprocal')
            self.assertEqual(reopened.query([]),[])
            self.assertEqual(reopened.metadata()['license_url'],data.LICENSE_URL)

    def test_failed_corrupt_and_interrupted_replacement_preserve_the_previous_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'data.zip';digest=archive(source,'John.1.5\tGen.1.3\t8\n')
            store=ReferenceData(root/'study-data')
            with patch.object(data,'ARCHIVE_SHA256',digest):store.install_archive(source)
            previous=store.path.read_bytes();sentinel=root/'notes.sqlite3';sentinel.write_bytes(b'UNCHANGED PERSONAL DATA')
            source.write_bytes(b'not a zip')
            with self.assertRaises(ReferenceDataError):store.install_archive(source)
            digest=archive(source,'John.1.5\tIsa.9.2\t19\n')
            with patch.object(data,'ARCHIVE_SHA256',digest),patch.object(data.os,'replace',side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):store.install_archive(source)
            self.assertEqual(store.path.read_bytes(),previous)
            self.assertEqual(store.query(['John.1.5'])[0].start,'Gen.1.3')
            self.assertEqual(sentinel.read_bytes(),b'UNCHANGED PERSONAL DATA')
            self.assertFalse(list(store.root.glob('.reference-*')))

    def test_archive_layout_headers_limits_and_identifiers_are_untrusted(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'data.zip'
            for name in ('../escape.txt','/cross_references.txt','cross_references.txt/extra'):
                with zipfile.ZipFile(path,'w') as output:output.writestr(name,'untrusted')
                with self.assertRaises(ReferenceDataError):list(data.parse_archive(path))
            with zipfile.ZipFile(path,'w') as output:
                output.writestr('cross_references.txt','x');output.writestr('other.txt','x')
            with self.assertRaises(ReferenceDataError):list(data.parse_archive(path))
            for row in ('John.1.999\tGen.1.1\t1\n','John.1.1\tFake.1.1\t1\n',
                        'John.1.1\tJohn.1.5-John.1.2\t1\n','John.1.1\tJohn.1.5\tnan\n',
                        'John.1.1\tJohn.1.5\t1\tunsafe\n'):
                archive(path,row)
                with self.assertRaises(ReferenceDataError):list(data.parse_archive(path))
            archive(path,'John.1.1\tGen.1.1\t1\n')
            with patch.object(data,'MAX_TEXT',20):
                with self.assertRaises(ReferenceDataError):list(data.parse_archive(path))

    def test_corrupt_or_future_local_schema_is_explicit_and_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            store=ReferenceData(directory);store.path.write_bytes(b'CORRUPT LOCAL FILE')
            with self.assertRaises(ReferenceDataError):store.metadata()
            self.assertEqual(store.path.read_bytes(),b'CORRUPT LOCAL FILE')
            with self.assertRaises(ReferenceDataError):data.reference_key('3John.1.16')
            self.assertEqual(list(data.reference_span('3John.1.14','Jude.1.1')),['3John.1.14','3John.1.15','Jude.1.1'])

    def test_damaged_relationship_table_remains_repairable_from_library(self):
        from bible.study_resources import StudyResources,REFERENCE_RESOURCE_ID
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'data.zip';digest=archive(source,'John.1.5\tGen.1.3\t8\n')
            store=ReferenceData(root/'study-data')
            with patch.object(data,'ARCHIVE_SHA256',digest):store.install_archive(source)
            store.metadata()
            with sqlite3.connect(store.path) as connection:connection.execute('DROP TABLE relationships')
            with self.assertRaises(ReferenceDataError):store.metadata()
            library=StudyResources(store.root)
            self.assertEqual(library.installed(),[])
            self.assertFalse(library.current(REFERENCE_RESOURCE_ID))


class ReferenceNumberingTests(unittest.TestCase):
    def test_verified_psalm_and_split_john_boundaries_in_both_directions(self):
        from bible.reference_targets import Canon,destination,source_references
        from bible.reference_resolution import resolve
        kjv,segond=Canon('KJV'),Canon('Segond')
        self.assertEqual(source_references(segond,'Ps.3.2','Ps.3.2'),['Ps.3.1'])
        self.assertEqual(source_references(kjv,'3John.1.14','3John.1.14'),['3John.1.14','3John.1.15'])
        self.assertEqual(source_references(segond,'3John.1.15','3John.1.15'),['3John.1.15'])
        mapped=resolve('3John.1.14','KJV',segond,require_entry=False)
        self.assertEqual((mapped.start,mapped.end),('3John.1.14','3John.1.15'))
        mapped=resolve('3John.1.15','NRSV',kjv,require_entry=False)
        self.assertEqual((mapped.start,mapped.end),('3John.1.14','3John.1.14'))
        with self.assertRaises(ValueError):resolve('3John.1.15','KJV',segond,require_entry=False)

    def test_exact_local_excerpts_boundaries_and_missing_text_without_network(self):
        from tests.test_ui import installed_fixture
        from bible.sword_provider import Reader
        from bible.reference_targets import local_excerpt
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,'French',versification='Segond',entries=[
                ('Ps.3.2','EXACT FRENCH TEST VERSE'),('3John.1.14','FIRST SPLIT TEST'),('3John.1.15','SECOND SPLIT TEST')])
            reader=Reader(Path(directory)/'translations/French','French')
            with patch('urllib.request.urlopen',side_effect=AssertionError('No network')):
                excerpt=local_excerpt(reader,'Ps.3.1')
                self.assertEqual(excerpt.verses,(('Ps.3.2','EXACT FRENCH TEST VERSE'),))
                excerpt=local_excerpt(reader,'3John.1.14','3John.1.15',limit=1)
                self.assertTrue(excerpt.more);self.assertEqual(excerpt.text,'FIRST SPLIT TEST')
                excerpt=local_excerpt(reader,'3John.1.15')
                self.assertEqual(excerpt.start,'3John.1.15');self.assertEqual(excerpt.text,'SECOND SPLIT TEST')
                with self.assertRaises(ValueError):local_excerpt(reader,'John.1.5')
