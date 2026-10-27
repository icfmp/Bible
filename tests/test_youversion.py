"""Synthetic acquisition failures/resume and source identity; no publisher text."""
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

from bible.library import Library,catalogue
from bible.providers import YOUVERSION
from bible.youversion_install import (acknowledgement,cached_download,
    resource_from_metadata,SourceRedirect,run_conversion)
from bible.youversion_content import parse,project
from tools.research.test_yves_source import metadata


def edition_metadata(identifier=21):
    from bible.youversion_editions import EDITIONS
    value=metadata();value.update(id=identifier,vrs=EDITIONS[identifier][0])
    value['language']['iso_639_3']=EDITIONS[identifier][2]
    value['offline']['url']=f'https://offline-bibles-cdn.youversionapi.com/bible/text/offline/{identifier}-7.zip'
    return value


class Response(io.BytesIO):
    def __init__(self,body,url,status=200,headers=None):
        super().__init__(body);self.url=url;self.status=status
        self.headers=headers or {'Content-Length':str(len(body)),'ETag':'"test-1"'}


class AcquisitionTests(unittest.TestCase):
    def test_one_metadata_refusal_keeps_other_editions_and_the_cached_record(self):
        from bible.catalogue_cache import CatalogueCache
        from bible.library import catalogues
        old=resource_from_metadata(edition_metadata(93),93)
        with tempfile.TemporaryDirectory() as directory:
            cache=CatalogueCache(directory);cache.write(YOUVERSION,[old])
            def fetch(url,out,**options):
                identifier=int(url.rsplit('=',1)[1])
                if identifier==93:raise urllib.error.HTTPError(url,403,'Refused',{},None)
                out.write(json.dumps(edition_metadata(identifier)).encode())
            with patch('bible.library.download',side_effect=fetch):result=catalogues((YOUVERSION,),cache=cache)
            self.assertEqual(len(result.resources),7)
            self.assertEqual(next(item for item in result.resources if item.name=='YV93'),old)
            self.assertIn(YOUVERSION.name,result.errors)
            self.assertEqual(len(cache.read(YOUVERSION)[0]),7)
    def test_cancellation_terminates_the_isolated_conversion_process(self):
        import subprocess,sys,time
        actual_popen=subprocess.Popen;processes=[];cancel=[False]
        def spawn(command,**options):
            self.assertTrue(options['start_new_session'])
            child=actual_popen([sys.executable,'-u','-c',
                'import time;print(\'{"phase":"converting","done":1,"total":5}\',flush=True);time.sleep(20)'],**options)
            processes.append(child);return child
        def phase(*args):cancel[0]=True
        start=time.monotonic()
        with patch('bible.youversion_install.subprocess.Popen',side_effect=spawn):
            with self.assertRaises(OSError):run_conversion(Path('synthetic.zip'),Path('synthetic.json'),Path('synthetic-target'),phase,lambda:cancel[0])
        self.assertLess(time.monotonic()-start,3)
        self.assertLess(processes[0].returncode,0)
    def test_catalogue_is_metadata_only_and_exact_conditions_survive(self):
        from bible.youversion_editions import EDITIONS,METADATA_URL
        data=edition_metadata();requests=[]
        def fetch(url,out,**options):
            requests.append(url);identifier=int(url.rsplit('=',1)[1]);value=edition_metadata()
            value.update(id=identifier,vrs=EDITIONS[identifier][0]);value['language']['iso_639_3']=EDITIONS[identifier][2]
            value['offline']['url']=value['offline']['url'].replace('/21-7.zip',f'/{identifier}-7.zip')
            out.write(json.dumps(value).encode())
        with patch('bible.library.download',side_effect=fetch):resources=catalogue(YOUVERSION)
        resource=next(item for item in resources if item.name=='YV21')
        self.assertEqual(set(requests),{METADATA_URL.format(edition=i) for i in EDITIONS})
        self.assertEqual(len(requests),7);self.assertEqual(len(resources),7)
        self.assertEqual(resource.id,'youversion~YV21')
        self.assertEqual(resource.versification,'Original')
        self.assertEqual(json.loads(resource.acquisition),data)
        self.assertNotIn('provider_approval',resource.acquisition)
        changed=edition_metadata();changed['offline']['agreement_version']=3
        self.assertNotEqual(acknowledgement(resource),acknowledgement(resource_from_metadata(changed)))

    def test_unknown_numbering_and_no_returned_package(self):
        data=edition_metadata();data['vrs']='unknown'
        with self.assertRaises(ValueError):resource_from_metadata(data)
        data=edition_metadata();data['offline']=None
        self.assertFalse(resource_from_metadata(data).installable)

    def test_retained_complete_download_never_requests_redownload(self):
        url='https://offline-bibles-cdn.youversionapi.com/bible/text/offline/21-7.zip'
        with tempfile.TemporaryDirectory() as directory:
            calls=[]
            def opener(request,**kw):calls.append(request);return Response(b'SYNTHETIC ZIP BYTES',url)
            path=cached_download(url,Path(directory),lambda *x:None,lambda:False,opener=opener)
            self.assertEqual(cached_download(url,Path(directory),lambda *x:None,lambda:False,
                opener=lambda *a,**k:self.fail('Unexpected redownload')),path)
            self.assertEqual(len(calls),1)

    def test_damaged_completed_cache_restarts_without_an_invalid_eof_range(self):
        url='https://offline-bibles-cdn.youversionapi.com/bible/text/offline/21-7.zip'
        with tempfile.TemporaryDirectory() as directory:
            cache=Path(directory)
            path=cached_download(url,cache,lambda *x:None,lambda:False,opener=lambda *a,**k:Response(b'ORIGINAL',url))
            path.write_bytes(b'DAMAGED!')
            def restarted(request,**options):
                self.assertIsNone(request.get_header('Range'))
                return Response(b'ORIGINAL',url)
            self.assertEqual(cached_download(url,cache,lambda *x:None,lambda:False,opener=restarted).read_bytes(),b'ORIGINAL')

    def test_interrupted_transfer_resumes_with_validator_and_exact_range(self):
        url='https://offline-bibles-cdn.youversionapi.com/bible/text/offline/21-7.zip'
        with tempfile.TemporaryDirectory() as directory:
            cache=Path(directory)
            class Interrupted(Response):
                def read1(self,size):
                    if self.tell():raise OSError('Interrupted connection')
                    return self.read(3)
            with self.assertRaises(OSError):
                cached_download(url,cache,lambda *x:None,lambda:False,
                    opener=lambda *a,**k:Interrupted(b'abcdef',url))
            def resumed(request,**kw):
                self.assertEqual(request.get_header('Range'),'bytes=3-')
                self.assertEqual(request.get_header('If-range'),'"test-1"')
                return Response(b'def',url,206,{'Content-Range':'bytes 3-5/6','Content-Length':'3','ETag':'"test-1"'})
            self.assertEqual(cached_download(url,cache,lambda *x:None,lambda:False,opener=resumed).read_bytes(),b'abcdef')

    def test_cancel_and_oversize_never_mark_download_complete(self):
        url='https://offline-bibles-cdn.youversionapi.com/bible/text/offline/21-7.zip'
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(OSError):cached_download(url,Path(directory),lambda *x:None,lambda:True)
            with self.assertRaises(ValueError):
                cached_download(url,Path(directory),lambda *x:None,lambda:False,
                    opener=lambda *a,**k:Response(b'',url,headers={'Content-Length':str(33*1024*1024)}))
            self.assertFalse(list(Path(directory).glob('*.json')))

    def test_redirect_cannot_move_to_http_or_another_host(self):
        request=urllib.request.Request('https://offline-bibles-cdn.youversionapi.com/source')
        for url in ['http://offline-bibles-cdn.youversionapi.com/source','https://example.invalid/source']:
            with self.assertRaises(ValueError):SourceRedirect().redirect_request(request,None,302,'',{},url)

    def test_authentication_refusal_is_not_retried_or_bypassed(self):
        url='https://offline-bibles-cdn.youversionapi.com/bible/text/offline/21-7.zip'
        for code in (401,403):
            with tempfile.TemporaryDirectory() as directory:
                with patch('urllib.request.OpenerDirector.open',side_effect=urllib.error.HTTPError(url,code,'Refused',{},None)) as opened:
                    with self.assertRaises(urllib.error.HTTPError):cached_download(url,Path(directory),lambda *x:None,lambda:False)
                    self.assertEqual(opened.call_count,1)

    def test_rate_limit_honours_retry_after_and_long_wait_is_reported(self):
        from bible.youversion_install import open_response
        request=urllib.request.Request('https://example.invalid/source')
        limited=urllib.error.HTTPError(request.full_url,429,'Wait',{'Retry-After':'0'},None)
        with patch('urllib.request.urlopen',side_effect=[limited,'response']) as opened:
            self.assertEqual(open_response(opened,request,lambda:False),'response')
            self.assertEqual(opened.call_count,2)
        limited=urllib.error.HTTPError(request.full_url,429,'Wait',{'Retry-After':'120'},None)
        with patch('urllib.request.urlopen',side_effect=limited) as opened:
            with self.assertRaises(urllib.error.HTTPError):open_response(opened,request,lambda:False)
            self.assertEqual(opened.call_count,1)

    def test_failed_conversion_does_not_register_or_modify_existing_data(self):
        resource=resource_from_metadata(edition_metadata())
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);library=Library(root/'translations')
            notes=root/'notes.sqlite3';notes.write_bytes(b'PERSONAL DATA')
            original=root/'preferences.json';original.write_bytes(b'ORIGINAL SETTINGS')
            def fetch(url,out,**kw):out.write(resource.acquisition.encode())
            archive=root/'source.zip';archive.write_bytes(b'Synthetic retained archive')
            with patch('bible.library.download',side_effect=fetch),patch('bible.youversion_install.cached_download',return_value=archive),patch('bible.youversion_install.run_conversion',side_effect=ValueError('Failed')):
                with self.assertRaises(ValueError):library.install(resource,permission=acknowledgement(resource))
            self.assertEqual(library.installed(),[])
            self.assertEqual(list(library.root.iterdir()),[])
            self.assertEqual(notes.read_bytes(),b'PERSONAL DATA');self.assertEqual(original.read_bytes(),b'ORIGINAL SETTINGS')
            self.assertTrue(archive.exists())

    def test_permission_and_changed_metadata_stop_before_acquisition(self):
        resource=resource_from_metadata(edition_metadata())
        with tempfile.TemporaryDirectory() as directory:
            library=Library(directory)
            with patch('bible.library.download') as fetch:
                with self.assertRaises(ValueError):library.install(resource)
                fetch.assert_not_called()
            changed=json.loads(resource.acquisition);changed['offline']['agreement_version']=5
            with patch('bible.library.download',side_effect=lambda url,out,**kw:out.write(json.dumps(changed).encode())),patch('bible.youversion_install.cached_download') as acquired:
                with self.assertRaises(ValueError):library.install(resource,permission=acknowledgement(resource))
                acquired.assert_not_called()

    def test_commit_is_atomic_provenance_is_offline_and_repeat_is_noop(self):
        resource=resource_from_metadata(edition_metadata())
        with tempfile.TemporaryDirectory() as directory:
            library=Library(Path(directory)/'translations');events=[]
            def converted(archive,metadata,target,*args,**options):
                self.assertEqual(library.installed(),[])
                (target/'mods.d').mkdir(parents=True)
                (target/'mods.d/yv21.conf').write_text('[YV21]\nModDrv=RawText\nVersification=Original\nDescription=Synthetic\n')
            with patch('bible.library.download',side_effect=lambda url,out,**kw:out.write(resource.acquisition.encode())),patch('bible.youversion_install.cached_download',return_value=Path(directory)/'cache.zip'),patch('bible.youversion_install.run_conversion',side_effect=converted):
                library.install(resource,installing=lambda:events.append('commit'),permission=acknowledgement(resource))
            self.assertEqual(events,['commit']);self.assertEqual(library.installed(),[resource.id])
            installed=library.resource(resource.id)
            self.assertEqual(installed.acquisition,resource.acquisition)
            self.assertEqual(installed.conditions,resource.conditions)
            recorded=json.loads((library.root/resource.id/'.source.json').read_text())
            self.assertFalse(recorded['provider_agreement_submitted'])
            with patch('bible.library.download',side_effect=AssertionError('Offline')):library.install(resource)


class EditorialTests(unittest.TestCase):
    def test_empty_declared_verse_and_unindexed_poetry_keep_distinct_identities(self):
        source=parse('<root><l type="x-centered">HEADING</l><verse osisID="Ps.119.1" sID="Ps.119.1"/><note n="1">NOTE</note><verse eID="Ps.119.1"/></root>')
        native=parse('<root><?source-unit Ps.119.0?><l type="x-centered">HEADING</l><?source-unit Ps.119.1?><note n="1">NOTE</note></root>')
        expected=project(source,milestones=True,preverse='Ps.119.0')
        self.assertEqual(expected,project(native))
        self.assertEqual(expected[0],{'Ps.119.0':'HEADING','Ps.119.1':''})
    def test_native_poetry_end_milestones_do_not_duplicate_source_roles(self):
        from bible.youversion_content import semantic_roles
        source=parse('<root><l level="1">SOURCE</l></root>')
        native=parse('<root><l level="1" sID="line1"/>SOURCE<l eID="line1" level="1"/></root>')
        self.assertEqual(semantic_roles(source),semantic_roles(native))
    def test_native_fragments_notes_headings_and_inline_words(self):
        root=parse('<root><?source-unit John.1.1?><list><item>Premier <hi type="italic">mot</hi><?source-unit John.1.2?>suite<note n="1.2" osisRef="John.1.2" type="study">Note &amp; fin</note></item></list><title>Titre<note n="1.3">Note du titre</note></title></root>')
        bodies,notes,titles=project(root)
        self.assertEqual(bodies,{'John.1.1':'Premier mot','John.1.2':'suite'})
        self.assertEqual([note.text for note in notes],['Note & fin','Note du titre'])
        self.assertEqual(titles,('Titre',));self.assertEqual(notes[0].reference,'John.1.2')
        with self.assertRaises(ValueError):parse('<!DOCTYPE root [<!ENTITY x "bad">]><root>&x;</root>')

    def test_original_reference_data_is_reproducible_and_boundaries_are_explicit(self):
        from tools.versification.original import build,ROOT
        data=build();self.assertEqual(data,json.loads((ROOT/'bible/versification_data/Original.json').read_text()))
        self.assertEqual(data['forward']['Joel.4.1'],['Joel.3.1'])
        self.assertEqual(data['forward']['Neh.7.72'],['Neh.7.73'])
        self.assertEqual(data['forward']['Neh.7.68'],['Neh.7.68','Neh.7.69'])
        self.assertEqual(data['forward']['Ps.3.9'],['Ps.3.8'])
        self.assertEqual(data['forward']['Num.25.19'],[])
        self.assertEqual(data['forward']['3John.1.15'],['3John.1.14!b'])


class SourceReaderTests(unittest.TestCase):
    def test_source_body_preserves_case_and_characters_without_native_display_transforms(self):
        try:import Sword
        except ImportError:self.skipTest('Requires SWORD')
        from tests.fixtures import module_fixture
        from bible.sword_provider import Reader
        from bible.youversion_content import normalized
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'youversion~YV21'
            module_fixture(root,'YV21',[
                ('John.1.1','<title type="parallel"><reference osisRef="Ps.3.1">EDITORIAL REFERENCE</reference></title><list><item>Exact <divineName>Dieu</divineName> <hi type="emphasis">emphasis</hi> &amp; tail<note n="1.1">PRIVATE EDITORIAL</note>'),
                ('John.1.2','CONTINUATION</item></list>')])
            conf=next((root/'mods.d').glob('*.conf'))
            conf.write_text(conf.read_text().replace('SourceType=Plaintext','SourceType=OSIS')+'BibleSource=YouVersion\nGlobalOptionFilter=OSISFootnotes\nGlobalOptionFilter=OSISHeadings\n')
            loaded=Reader(root,'youversion~YV21').chapter('John.1.1')
            self.assertEqual([(ref,normalized(text)) for ref,text in loaded.verses],
                [('John.1.1','Exact Dieu emphasis & tail'),('John.1.2','CONTINUATION')])


def original_available():
    try:
        import Sword
        key=Sword.VerseKey();key.setVersificationSystem('Original')
        return key.getVersificationSystem()=='Original'
    except ImportError:return False


@unittest.skipUnless(original_available(),'Requires the packaged Original native system')
class OriginalNativeTests(unittest.TestCase):
    def test_publisher_indexes_preserve_source_bounds_without_guessing_alignment(self):
        import Sword
        from bible.versification_mapping import table,to_base
        from tools.versification.youversion import check
        check()
        for system in ('YouVersion93','YouVersion131'):
            self.assertIsNotNone(table(system))
            self.assertEqual(to_base('John.1.1',system),[])
        key=Sword.VerseKey();key.setAutoNormalize(False);key.setVersificationSystem('YouVersion93')
        key.setText('Mark.10.53');self.assertEqual(key.getOSISRef(),'Mark.10.53')
        self.assertEqual(key.popError(),'\x00')
    def test_exact_native_bounds_verified_mapping_and_original_note_roundtrip(self):
        from tests.test_ui import installed_fixture
        from bible.sword_provider import Reader
        from bible.reference_resolution import resolve,VersificationMismatch
        from bible.versification_mapping import table
        from bible.notes import NoteStore
        with tempfile.TemporaryDirectory() as directory:
            original=Reader(installed_fixture(directory,'OriginalFixture',entries=
                [('Neh.7.68','SOURCE JOIN'),('Neh.7.72','SOURCE LAST')],versification='Original'),'OriginalFixture')
            target=Reader(installed_fixture(directory,'BaseFixture',entries=[
                ('Neh.7.68','BASE FIRST'),('Neh.7.69','BASE SECOND'),('Neh.7.73','BASE LAST')]),'BaseFixture')
            self.assertIsNotNone(table('Original'))
            with self.assertRaises(ValueError):original.key('Neh.7.73')
            with self.assertRaises(ValueError):original.key('2Kgs.15.39')
            mapped=resolve('Neh.7.68','Original',target)
            self.assertEqual((mapped.start,mapped.end),('Neh.7.68','Neh.7.69'))
            self.assertEqual(resolve('Neh.7.72','Original',target).start,'Neh.7.73')
            with self.assertRaises(VersificationMismatch):resolve('Num.25.19','Original',target)
            path=Path(directory)/'notes.sqlite3';store=NoteStore(path)
            saved=store.save('PERSONAL SOURCE NOTE',(),versification='Original',
                start='Neh.7.68',end='Neh.7.68',origin_translation='OriginalFixture',origin_language='fra')
            self.assertEqual(list(NoteStore(path).all()),[saved])
