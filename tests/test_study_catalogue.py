"""Checked resource revisions, atomic updates and independent vocabulary delivery."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import hashlib,json,tempfile,unittest,zipfile
from unittest.mock import patch
from bible.study_catalogue import BUNDLED,CATALOGUE_URL,FORMATS,ResourceRevision,StudyCatalogue,parse
from bible.topic_vocabulary import BUNDLED as WORDS,TopicVocabulary,suggestions,title
from bible.reference_data import ReferenceData,ReferenceDataError
from bible.topic_data import TopicData


def revision(identifier,data,generation='2026-11-02',version=None):
    digest=hashlib.sha256(data).hexdigest()
    return ResourceRevision(version or generation,generation,digest,len(data),FORMATS[identifier][0],
        'https://github.com/icfmp/Bible/releases/download/study-resource-archives/'+identifier+'-'+digest[:12]+('.json' if identifier=='topic-vocabulary' else '.zip'))


def catalogue(**overrides):
    result=json.loads(BUNDLED.read_bytes())
    for identifier,item in overrides.items():result['resources'][identifier]=asdict(item)
    return json.dumps(result).encode()


def archive(path,kind,generation,rows):
    name,header=('cross_references.txt','From Verse\tTo Verse\tVotes\t#www.openbible.info CC-BY '+generation) if kind=='references' else (
        'topic-scores.txt','Topic\tOSIS\tQuality Score (based on percentage of votes for the passage)\t# Generated '+generation+'. CC-BY License: www.openbible.info/topics')
    with zipfile.ZipFile(path,'w') as output:output.writestr(name,header+'\n'+rows)
    return path.read_bytes()


class StudyCatalogueTests(unittest.TestCase):
    def transport(self,payloads,called):
        def receive(url,output,progress=lambda *_:None,limit=None,**_):
            called.append(url);data=payloads[url]
            if isinstance(data,BaseException):raise data
            self.assertLessEqual(len(data),limit)
            output.write(data);progress(len(data),len(data))
        return patch('bible.library.download',side_effect=receive)

    def test_malformed_catalogue_is_rejected_without_replacing_known_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            store=StudyCatalogue(directory);good=BUNDLED.read_bytes();store.path.write_bytes(good)
            for change in ('hash','origin','format','date','schema'):
                value=json.loads(good);item=value['resources']['openbible-topics']
                if change=='hash':item['sha256']='invalid'
                elif change=='origin':item['url']='https://example.org/topics.zip'
                elif change=='format':item['format']='unsupported-v2'
                elif change=='date':item['generation']='2026-02-30'
                else:value['schema']=True
                with self.transport({CATALOGUE_URL:json.dumps(value).encode()},[]),self.assertRaises(ValueError):store.refresh()
                self.assertEqual(store.path.read_bytes(),good)
            self.assertTrue(store.load())

    def test_compatible_new_generation_updates_data_and_bad_payload_keeps_working_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);old=archive(root/'old.zip','references','2026-10-19','John.1.5\tGen.1.3\t1\n')
            new=archive(root/'new.zip','references','2026-11-02','John.1.5\tIsa.9.2\t18\n')
            before=revision('openbible-cross-references',old,'2026-10-19');after=revision('openbible-cross-references',new)
            store=ReferenceData(root/'study');store.install_archive(root/'old.zip',revision=before)
            sentinel=root/'notes.sqlite3';sentinel.write_bytes(b'UNCHANGED PERSONAL DATA')
            current=catalogue(**{'openbible-cross-references':after});calls=[]
            with self.transport({CATALOGUE_URL:current,after.url:new},calls):store.install()
            self.assertEqual(store.metadata()['source_date'],'2026-11-02');self.assertEqual(store.metadata()['archive_sha256'],after.sha256)
            self.assertEqual(store.query(['John.1.5'])[0].start,'Isa.9.2');working=store.path.read_bytes()
            bad=archive(root/'bad.zip','references','2026-11-03','John.999.1\tIsa.9.2\t18\n')
            bad_version=revision('openbible-cross-references',bad,'2026-11-03')
            for payload in (b'truncated',bad):
                wanted=after if payload==b'truncated' else bad_version
                metadata=catalogue(**{'openbible-cross-references':wanted})
                with self.transport({CATALOGUE_URL:metadata,wanted.url:payload},[]),self.assertRaises(ValueError):store.install()
                self.assertEqual(store.path.read_bytes(),working)
            with self.transport({CATALOGUE_URL:OSError('Offline metadata')},[]),self.assertRaises(ReferenceDataError):store.install()
            self.assertEqual(store.path.read_bytes(),working);self.assertEqual(sentinel.read_bytes(),b'UNCHANGED PERSONAL DATA')
            self.assertEqual(ReferenceData(store.root).query(['John.1.5'])[0].start,'Isa.9.2')

    def test_vocabulary_update_keeps_index_bytes_and_rejects_malformed_names_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);data=archive(root/'topics.zip','topics','2026-11-02','forgiveness\tJohn.3.16\t30\nnew source topic\tJohn.1.1\t12\n')
            index=revision('openbible-topics',data);store=TopicData(root/'study');store.install_archive(root/'topics.zip',revision=index)
            original=store.path.read_bytes();words=json.loads(WORDS.read_bytes());words['revision']='2026-11-04.2'
            words['entries'].append(dict(id='new source topic',names={'fr':'','en':'Synthetic reviewed topic'},synonyms=['new vocabulary']))
            payload=json.dumps(words,ensure_ascii=False).encode();vocabulary=revision('topic-vocabulary',payload,version=words['revision'])
            metadata=catalogue(**{'openbible-topics':index,'topic-vocabulary':vocabulary});calls=[]
            with self.transport({CATALOGUE_URL:metadata,vocabulary.url:payload},calls):store.install()
            self.assertNotIn(index.url,calls);self.assertEqual(store.path.read_bytes(),original)
            installed=TopicVocabulary(store.root);entries=installed.read()[1]
            chosen=suggestions('new vocabulary',entries=entries)[0]
            self.assertEqual(chosen[0],'new source topic');self.assertEqual(title(chosen,'fr'),'Synthetic reviewed topic')
            self.assertEqual(store.query(chosen[0])[0].start,'John.1.1')
            saved=installed.path.read_bytes();words['revision']='2026-11-04.3';words['entries'][0]['names']['fr']=42
            malformed=json.dumps(words).encode();invalid=revision('topic-vocabulary',malformed,version=words['revision'])
            metadata=catalogue(**{'openbible-topics':index,'topic-vocabulary':invalid})
            with self.transport({CATALOGUE_URL:metadata,invalid.url:malformed},[]),self.assertRaises(ReferenceDataError):store.install()
            self.assertEqual(installed.path.read_bytes(),saved);self.assertEqual(store.path.read_bytes(),original)
            self.assertEqual(TopicData(store.root).query('forgiveness')[0].start,'John.3.16')

    def test_vocabulary_only_publication_retains_both_index_revisions(self):
        from tools.study_resource_updates import prepare
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);words=json.loads(WORDS.read_bytes());words['revision']='2026-11-04.2'
            words['entries'][0]['synonyms'].append('synthetic reviewed synonym')
            source=root/'words.json';source.write_text(json.dumps(words))
            assets,proof=prepare(root/'out',source,previous=BUNDLED.read_bytes())
            self.assertEqual(len(assets),1);self.assertEqual(set(proof),{'topic-vocabulary'})
            before=parse(BUNDLED.read_bytes());after=parse((root/'out/catalogue.json').read_bytes())
            for identifier in ('openbible-cross-references','openbible-topics'):self.assertEqual(before[identifier],after[identifier])
            self.assertNotEqual(before['topic-vocabulary'].sha256,after['topic-vocabulary'].sha256)
            words['revision']='2026-11-04.1';source.write_text(json.dumps(words))
            with self.assertRaises(ValueError):prepare(root/'bad',source,previous=BUNDLED.read_bytes())
