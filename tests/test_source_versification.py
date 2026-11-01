"""Native bounds, partial canons and exact generic conversion; synthetic text only."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from bible.source_versification import write_index,register_index,native_loader


def native_available():
    try:native_loader();return True
    except (ImportError,ValueError):return False


@unittest.skipUnless(native_available(),'Requires the packaged source-index extension')
class NativeSourceIndexTests(unittest.TestCase):
    def test_reference_only_index_reuse_conflict_and_receipt_integrity(self):
        import Sword
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'.source-versification'
            sha=write_index(path,'YouVersion900081',{'Tob':[3,4],'Matt':[2]},dict(Tob=1,Matt=2))
            (path.parent/'.verified.json').write_text(json.dumps(dict(reference_index_sha256=sha)))
            register_index(path);register_index(path)
            key=Sword.VerseKey();key.setVersificationSystem('YouVersion900081')
            key.setText('Tob.2.4');self.assertEqual(key.getOSISRef(),'Tob.2.4')
            self.assertEqual(key.getVerseMax(),4)
            write_index(path,'YouVersion900081',{'Tob':[3,5],'Matt':[2]},dict(Tob=1,Matt=2))
            with self.assertRaisesRegex(ValueError,'changed'):register_index(path)
            with self.assertRaisesRegex(ValueError,'conflicts'):register_index(path,verified=False)

    def test_native_parser_rejects_invalid_testaments_and_oversized_indexes(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'index'
            for rows in ['0 Tob 1 3','1 Tob 1 2001','2 Matt 1 3\n1 Tob 1 3',
                         '1 Tob 1 3\n1 Tob 1 3','1 Tob 2 3','1 Tob 1 3 trailing']:
                path.write_text('BIBLE-VRS-1 YouVersion900082\n'+rows+'\n')
                with self.subTest(rows=rows),self.assertRaises(ValueError):register_index(path,verified=False)

    def test_nt_only_rtl_prefix_missing_verse_and_bridge_survive_full_readback(self):
        from tools.research.test_yves_source import metadata,chapter
        from bible.youversion_worker import build
        from bible.sword_provider import Reader
        from bible.youversion_content import normalized
        compiler=os.environ.get('BIBLE_OSIS2MOD') or shutil.which('osis2mod')
        if not compiler:self.skipTest('Requires osis2mod')
        identifier=900083
        data=metadata(('JHN.INTRO1','JHN.1'));data['id']=identifier
        data['offline']['url']=f'//offline-bibles-cdn.youversionapi.com/bible/text/offline/{identifier}-1.zip'
        data['language'].update(language_tag='fra',text_direction='rtl')
        data['books'][0]['canon']='nt'
        samples={
            'JHN.INTRO1':'<div class="iot">Synthetic outline</div><div class="io3"><span class="pn">Synthetic name</span></div>',
            'JHN.1':'<div class="s1">Synthetic heading</div><div class="nb">Unnumbered synthetic prefix.'
                    '<span class="note x"><span class="fk">Synthetic keyword</span> Synthetic chapter note.</span></div>'
                    '<div class="p"><span class="verse" data-usfm="JHN.1.1">Synthetic first verse.</span>'
                    '<span class="verse" data-usfm="JHN.1.5"><span class="sls">Synthetic moved verse.</span></span>'
                    '<span class="verse" data-usfm="JHN.1.3+JHN.1.4">Synthetic linked unit.</span></div>'}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);archive=root/'source.zip';source=root/'metadata.json'
            source.write_text(json.dumps(data))
            with zipfile.ZipFile(archive,'w') as output:
                for ref,content in samples.items():
                    book,number=ref.split('.')
                    output.writestr(f'{book}/{number}.yves',chapter(ref,content,version=identifier))
            target=root/'module'
            with patch('bible.youversion_worker.emit'):build(archive,source,target,compiler,identifier)
            reader=Reader(target,'youversion~YV900083');loaded=reader.chapter('John.1.1')
            self.assertEqual(reader.first_reference(),'John.1.1');self.assertTrue(reader.rtl)
            self.assertEqual([book.code for book in reader.books],['John'])
            self.assertEqual({ref:normalized(value) for ref,value in loaded.unique_verses()},
                             {'John.1.1':'Synthetic first verse.','John.1.5':'Synthetic moved verse.','John.1.3':'Synthetic linked unit.'})
            self.assertEqual([ref for ref,_ in loaded.verses],['John.1.1','John.1.5','John.1.3','John.1.4'])
            self.assertEqual(loaded.links,(('John.1.4','John.1.3'),))
            segments=reader.structured_chapter(loaded)['John.1.1']
            self.assertIn('Unnumbered synthetic prefix.',''.join(s.text for s in segments))
            self.assertIsNotNone(reader.introduction('John'))
            self.assertEqual(reader.editorial_notes('John.1.1')[0].reference,'John.1')
            self.assertTrue(json.loads((target/'.verified.json').read_text())['all_text_notes_headings_verified'])
            (target/'.source-verse-order.json').write_text('{"John.1":[1,3,4,5]}')
            with self.assertRaisesRegex(ValueError,'order changed'):Reader(target,'youversion~YV900083').chapter('John.1.1')
