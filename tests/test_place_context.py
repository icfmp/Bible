"""Reviewed source identity and bounded, offline-first place photographs."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from bible.place_context import context,cached_image


class PlaceContextTests(unittest.TestCase):
    def test_stable_identity_does_not_apply_jerusalem_enrichment_to_namesakes_or_unknown_places(self):
        self.assertIsNotNone(context(dict(id='a15257a',name='Jerusalem')))
        for place in (dict(id='a123456',name='Jerusalem'),dict(id='a15257a',name='Other place'),
                      dict(id='a1ad8e1',name='Nod'),dict(id='ae7274b',name='Emmaus')):
            self.assertIsNone(context(place))

    def test_download_is_explicit_verified_and_reopens_offline_without_touching_annotations(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);notes=root/'notes.sqlite3';notes.write_bytes(b'KEEP PERSONAL DATA')
            data=b'test-only photograph bytes';digest=hashlib.sha256(data).hexdigest()
            image=dict(url='https://example.test/curated.jpg',sha256=digest)
            with patch('bible.library.download',side_effect=lambda url,output,**kw:output.write(data)) as fetch:
                self.assertIsNone(cached_image(root,image));fetch.assert_not_called()
                path=cached_image(root,image,True);fetch.assert_called_once()
            with patch('bible.library.download',side_effect=AssertionError('Offline')):
                self.assertEqual(cached_image(root,image),path);self.assertEqual(path.read_bytes(),data)
            self.assertEqual(notes.read_bytes(),b'KEEP PERSONAL DATA')
            with patch('bible.library.download',side_effect=lambda url,output,**kw:output.write(b'WRONG CONTENT')):
                other=dict(image,sha256='1'*64)
                with self.assertRaisesRegex(ValueError,'checksum'):cached_image(root,other,True)
            self.assertEqual(path.read_bytes(),data);self.assertFalse((path.parent/('1'*64+'.jpg')).exists())
            with patch('bible.library.download') as fetch:
                with self.assertRaises(InterruptedError):cached_image(root,image,True,cancelled=lambda:True)
                fetch.assert_not_called()

class IndependentContextTests(unittest.TestCase):
    def test_moreh_related_entity_never_becomes_ancient_identity_and_evidence_is_retained(self):
        from bible.place_context import PlaceContexts
        store=PlaceContexts()
        proposals=[dict(modern_id='m657590',name='Tell Balatah',coordinate_source={'id':'Q7951237'},role=role)
                   for role in ('center','settlement','representative point')]
        place=dict(id='a38ad9f',name='Moreh 1',candidates=proposals)
        actual=store.read()['places'][place['id']]['openbible_name'];place['name']=actual
        direct,related=store.entries(place)
        self.assertIsNone(direct);self.assertEqual(len(related),1)
        self.assertEqual(related[0]['proposals'],proposals)
        self.assertEqual(related[0]['entry']['scope'],'coordinate-source-entity')
        wrong=dict(place,candidates=[dict(proposals[0],coordinate_source={'id':'Q999'})])
        self.assertEqual(store.entries(wrong),(None,[]))
        self.assertEqual(store.entries(dict(place,name='Namesake')),(None,[]))

    def test_independent_update_is_atomic_offline_and_does_not_modify_the_place_index(self):
        from copy import deepcopy
        from dataclasses import asdict
        import json
        from bible.place_context import BUNDLED,PlaceContexts
        from bible.study_catalogue import ResourceRevision,StudyCatalogue
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);store=PlaceContexts(root)
            index=root/'openbible-places.sqlite3';index.write_bytes(b'UNCHANGED PLACE INDEX')
            original=BUNDLED.read_bytes();store.path.write_bytes(original)
            value=json.loads(original);value['revision']='2026-11-08.test';value['coverage']['test_only']=True
            updated=json.dumps(value).encode();digest=hashlib.sha256(updated).hexdigest()
            revision=ResourceRevision(value['revision'],value['generation'],digest,len(updated),'bible-place-context-v2',
                'https://icfmp.github.io/Bible-Resources/place-context/v1/place-context-'+digest+'.json')
            with patch.object(StudyCatalogue,'load',return_value={'place-context':revision}),patch('bible.library.download',side_effect=lambda url,out,*args,**kw:out.write(updated)):
                store.install()
            self.assertEqual(store.read()['revision'],value['revision'])
            with patch('bible.library.download',side_effect=AssertionError('Offline read must not download')):
                self.assertEqual(PlaceContexts(root).metadata()['revision'],value['revision'])
            with patch.object(StudyCatalogue,'load',return_value={'place-context':revision}),patch('bible.library.download',side_effect=lambda url,out,*args,**kw:out.write(b'TRUNCATED')):
                with self.assertRaises(ValueError):store.install()
            self.assertEqual(store.path.read_bytes(),updated);self.assertEqual(index.read_bytes(),b'UNCHANGED PLACE INDEX')
            store.path.write_bytes(b'INVALID LOCAL RESOURCE')
            self.assertEqual(PlaceContexts(root).read()['revision'],json.loads(original)['revision'])

    def test_loading_context_reuses_the_validated_resource_until_the_file_changes(self):
        from bible.place_context import PlaceContexts,parse,BUNDLED
        with tempfile.TemporaryDirectory() as directory:
            store=PlaceContexts(directory)
            with patch('bible.place_context.parse',wraps=parse) as read:
                first=store.read();self.assertIs(store.read(),first);self.assertEqual(read.call_count,1)
                store.path.write_bytes(BUNDLED.read_bytes())
                self.assertIsNot(store.read(),first);self.assertEqual(read.call_count,2)
