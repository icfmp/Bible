"""Place evidence, bounded/atomic indexing and map failure are independent of notes."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from bible import place_data
from bible.place_data import PlaceData,ReferenceDataError,status,coordinates


def inputs(root):
    modern={'id':'m123456','friendly_id':'Known modern place','coordinates_source':{'type':'wikidata','id':'Q123'}}
    source={'id':'s123456','display_name':'Test bibliography (2020)','year':2020}
    base=dict(id='a123456',friendly_id='Jerusalem',url_slug='jerusalem',translation_name_counts={'Jerusalem':1},
        identification_sources={'s123456':{'title':'Test identification'}},verses=[{'osis':'John.1.5'}],
        media={'thumbnail':{'url':'https://untrusted.test/NEVER_FETCH.jpg'}},extra='NEVER_IMPORT_IMAGE_METADATA')
    resolution=dict(modern_basis_id='m123456',lonlat='35.234167,31.776667',lonlat_type='point',best_path_score=500,
        description='<modern id="m123456">Known modern place</modern>',paths=[[{'modern_id':'m123456'}]])
    base['identifications']=[{'score':{'vote_total':500,'time_total':1000},'resolutions':[resolution]}]
    coastline={'type':'FeatureCollection','features':[{'geometry':{'type':'LineString','coordinates':[[30,30],[32,32],[36,34]]}}]}
    values={'ancient':json.dumps(base)+'\n','modern':json.dumps(modern)+'\n','sources':json.dumps(source)+'\n',
            'license':'TEST-ONLY PUBLISHER LICENSE','coastline':json.dumps(coastline)}
    paths={}
    for name,value in values.items():paths[name]=root/name;paths[name].write_text(value)
    return paths


def pins(paths):
    return {name:(place_data.FILES[name][0],hashlib.sha256(path.read_bytes()).hexdigest(),place_data.FILES[name][2])
            for name,path in paths.items()}


class PlaceDataTests(unittest.TestCase):
    def test_supplied_relationships_candidate_identity_and_reopen_without_image_payloads(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);files=inputs(root);store=PlaceData(root/'study-data')
            with patch.object(place_data,'FILES',pins(files)):metadata=store.install_files(files)
            self.assertEqual(metadata['places'],1)
            reopened=PlaceData(store.root);rows=reopened.query(['John.1.5','John.1.5'])
            self.assertEqual(rows[0]['status'],'known');self.assertEqual(rows[0]['source_verse_count'],1)
            self.assertEqual(rows[0]['candidates'][0]['longitude'],35.234167)
            self.assertNotIn('NEVER_IMPORT',json.dumps(rows));self.assertNotIn('NEVER_FETCH',json.dumps(rows))
            self.assertEqual(reopened.query(['John.3.16']),[])
            self.assertEqual(reopened.coastlines((28,25,40,40)),[[[30.0,30.0],[32.0,32.0],[36.0,34.0]]])

    def test_unknown_high_score_and_competing_modern_locations_are_not_falsely_known(self):
        known=dict(longitude=35.2,modern_id='m123456',path_score=500,vote_total=500,vote_tags={})
        self.assertEqual(status([known]),'known')
        self.assertEqual(status([dict(known,longitude=None)]),'unknown')
        self.assertEqual(status([known,dict(known,modern_id='m654321',path_score=50,vote_total=50)]),'disputed')
        self.assertEqual(status([dict(known,path_score=20,vote_total=20,vote_tags={'confidence_likely':2})]),'probable')
        self.assertEqual(status([dict(known,path_score=-20,vote_total=-20)]),'disputed')

    def test_failed_corrupt_and_interrupted_updates_retain_the_working_index_and_personal_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);files=inputs(root);store=PlaceData(root/'study-data')
            with patch.object(place_data,'FILES',pins(files)):store.install_files(files)
            before=store.path.read_bytes();notes=root/'notes.sqlite3';notes.write_bytes(b'KEEP PERSONAL DATA')
            files['ancient'].write_text('INVALID CHECKSUM')
            with self.assertRaises(ReferenceDataError):store.install_files(files)
            files=inputs(root)
            with patch.object(place_data,'FILES',pins(files)),patch.object(place_data.os,'replace',side_effect=OSError('interrupted')):
                with self.assertRaises(OSError):store.install_files(files)
            self.assertEqual(store.path.read_bytes(),before);self.assertEqual(notes.read_bytes(),b'KEEP PERSONAL DATA')
            self.assertEqual(store.query(['John.1.5'])[0]['id'],'a123456')
            self.assertFalse(list(store.root.glob('.places-*')))

    def test_unsafe_address_coordinates_duplicate_records_and_geometry_cannot_replace_an_index(self):
        for corruption in ('coordinates','reference','duplicate','geometry'):
            with self.subTest(corruption=corruption),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);files=inputs(root);store=PlaceData(root/'study-data')
                if corruption=='coordinates':
                    record=json.loads(files['ancient'].read_text());record['identifications'][0]['resolutions'][0]['lonlat']='181,90'
                    files['ancient'].write_text(json.dumps(record)+'\n')
                elif corruption=='reference':
                    record=json.loads(files['ancient'].read_text());record['verses']=[{'osis':'John.999.1'}]
                    files['ancient'].write_text(json.dumps(record)+'\n')
                elif corruption=='duplicate':files['ancient'].write_text(files['ancient'].read_text()*2)
                else:
                    record=json.loads(files['coastline'].read_text());record['features'][0]['geometry']['type']='Polygon'
                    files['coastline'].write_text(json.dumps(record))
                with patch.object(place_data,'FILES',pins(files)):
                    with self.assertRaises(ReferenceDataError):store.install_files(files)
                self.assertFalse(store.path.exists())
        for value in ['nan,20','30,inf',[-181,40],[True,30],['35','30']]:
            with self.subTest(value=value),self.assertRaises(ReferenceDataError):coordinates(value)

    def test_unavailable_map_retains_place_metadata_and_is_repairable(self):
        from bible.study_resources import StudyResources,PLACE_RESOURCE_ID
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);files=inputs(root);store=PlaceData(root/'study-data')
            with patch.object(place_data,'FILES',pins(files)):store.install_files(files)
            with sqlite3.connect(store.path) as connection:connection.execute('DROP TABLE coastlines')
            self.assertEqual(store.query(['John.1.5'])[0]['name'],'Jerusalem')
            self.assertFalse(store.has_map())
            resources=StudyResources(store.root)
            self.assertIn(PLACE_RESOURCE_ID,resources.installed());self.assertFalse(resources.current(PLACE_RESOURCE_ID))

    def test_unsupported_personal_or_future_database_remains_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            store=PlaceData(directory);store.path.write_bytes(b'NOT A PLACE DATABASE')
            with self.assertRaises(ReferenceDataError):store.metadata()
            self.assertEqual(store.path.read_bytes(),b'NOT A PLACE DATABASE')
