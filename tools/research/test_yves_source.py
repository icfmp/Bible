"""Synthetic-only #26 fixtures; no downloaded Scripture or publisher content."""
import copy
import io
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree as E
import zipfile

from .semantic_osis import NS, Unsupported
from .yves_source import (TreeParser, archive_chapters, decode_bytes, parse_chapter,
                          read_edition, to_osis)

VERSION = 900001


def metadata(refs=('JHN.INTRO1', 'JHN.1', 'PSA.3')):
    books = {}
    for ref in refs:
        code = ref.split('.')[0]
        books.setdefault(code, dict(usfm=code, text=True, chapters=[]))['chapters'].append(
            dict(usfm=ref, canonical='.INTRO' not in ref))
    return dict(id=VERSION, local_title='Synthetic conversion fixture — not Scripture',
                language=dict(iso_639_3='fra'), copyright_short=dict(text='Synthetic test material.'),
                offline=dict(url=f'//offline-bibles-cdn.youversionapi.com/bible/text/offline/{VERSION}-2.zip',
                             require_email_agreement=True, allow_redownload=False, agreement_version=2),
                books=list(books.values()), vrs='unverified-source-system', metadata_build=999)


def encode(data):
    # Inverse expressed independently, matching the reference tests in #26.
    data = bytearray(data)
    for index in range(1, len(data), 2):
        data[index - 1], data[index] = data[index], data[index - 1]
    return bytes((value >> 3) + ((value % 8) * 32) for value in data)


def chapter(ref='JHN.1', content=None, version=VERSION):
    if content is None:
        content = '''<div class="label">1</div>
<div class="s1"><span class="heading">Titre synthétique</span></div>
<div class="p"><span class="verse" data-usfm="JHN.1.1"><span class="label">1</span><span class="content">Premier fragment de test &amp; </span><span class="add">ajout synthétique</span><span class="note" id="test-note"><span class="fr">1.1</span><span class="ft">Note de test, référence <span class="ref" data-usfm="PSA.3.9">Ps 3:9</span>.</span></span></span></div>
<div class="q1"><span class="verse" data-usfm="JHN.1.1"><span class="content"> ; suite du test.</span></span><span class="verse" data-usfm="JHN.1.3"><span class="label">3</span><span class="nd">NOM DE TEST</span> — <span class="wj">paroles synthétiques שָׁלוֹם.</span><br/>Fin du test.</span></div>'''
    role = 'intro intro1' if '.INTRO' in ref else 'chapter ch1'
    raw = f'<div class="version vid{version} iso6393fra" data-vid="{version}" data-iso6393="fra"><div class="{role}" data-usfm="{ref}">{content}</div></div>'
    return encode(raw.encode())


def synthetic_archive(path):
    refs = ['JHN.INTRO1', 'JHN.1', 'PSA.3']
    samples = {
        'JHN.INTRO1': chapter('JHN.INTRO1', '<div class="imt"><span class="heading">Introduction de test</span></div><div class="ip">Document synthétique, aucun texte biblique.</div>'),
        'JHN.1': chapter(),
        'PSA.3': chapter('PSA.3', '<div class="d"><span class="verse" data-usfm="PSA.3.9"><span class="label">9</span>Numérotation de test uniquement.</span></div>'),
    }
    with zipfile.ZipFile(path, 'w') as archive:
        for ref in reversed(refs):
            book, number = ref.split('.')
            archive.writestr(f'{VERSION}/{book}/{number}.yves', samples[ref])
    return read_edition(metadata(), VERSION)


class BinaryTests(unittest.TestCase):
    def test_known_vector_and_all_bytes_pairs(self):
        self.assertEqual(decode_bytes(bytes.fromhex('010204')), bytes.fromhex('100820'))
        for value in range(256):
            self.assertEqual(decode_bytes(encode(bytes([value]))), bytes([value]))
        data = bytes(item for pair in range(65536) for item in divmod(pair, 256))
        self.assertEqual(decode_bytes(encode(data)), data)

    def test_lengths_and_odd_tail(self):
        for length in range(1025):
            data = bytes(index % 256 for index in range(length))
            self.assertEqual(decode_bytes(encode(data)), data)

    def test_invalid_utf8_fails(self):
        with self.assertRaises(UnicodeDecodeError):
            parse_chapter(encode(b'\xff'), 'JHN.1', read_edition(metadata(), VERSION))


class MetadataTests(unittest.TestCase):
    def test_absent_notice_is_preserved_and_not_inferred_as_public_domain(self):
        data=metadata();data['copyright_short']={'text':None,'html':None}
        edition=read_edition(data,VERSION)
        self.assertEqual(edition.attribution,'')
        self.assertEqual(edition.metadata,data)
        data['copyright_short']['text']=['not a notice']
        with self.assertRaises(Unsupported):read_edition(data,VERSION)

    def test_identity_envelope_and_unchanged_agreement(self):
        data = metadata()
        edition = read_edition({'response': {'data': data}}, VERSION)
        self.assertEqual(edition.chapters, ('JHN.INTRO1', 'JHN.1', 'PSA.3'))
        self.assertTrue(edition.metadata['offline']['require_email_agreement'])
        self.assertFalse(edition.metadata['offline']['allow_redownload'])
        self.assertEqual(edition.metadata['vrs'], 'unverified-source-system')
        self.assertIn(f'{VERSION}-2.zip', edition.archive_url)
        self.assertEqual(data, metadata())

    def test_unknown_offline_package_is_not_invented(self):
        data = metadata(); data['offline'] = None
        self.assertIsNone(read_edition(data, VERSION).archive_url)

    def test_untrusted_urls_and_identity(self):
        for url in ['http://offline-bibles-cdn.youversionapi.com/bible/text/offline/900001-2.zip',
                    'https://attacker.invalid/900001-2.zip',
                    'https://user:password@offline-bibles-cdn.youversionapi.com/bible/text/offline/900001-2.zip',
                    '//offline-bibles-cdn.youversionapi.com:443/bible/text/offline/900001-2.zip',
                    '//offline-bibles-cdn.youversionapi.com/bible/text/offline/21-17.zip',
                    '//offline-bibles-cdn.youversionapi.com/bible/text/offline/../900001-2.zip']:
            with self.subTest(url=url):
                data=metadata();data['offline']['url']=url
                with self.assertRaises(Unsupported):read_edition(data, VERSION)
        with self.assertRaises(Unsupported):read_edition(metadata(), 21)
        data=metadata();data['id']=True
        with self.assertRaises(Unsupported):read_edition(data, VERSION)

    def test_invalid_inventory_is_not_silently_reduced(self):
        for mutation in ['duplicate', 'mismatch', 'role', 'missing']:
            data=metadata()
            if mutation=='duplicate':data['books'].append(copy.deepcopy(data['books'][0]))
            elif mutation=='mismatch':data['books'][0]['chapters'][0]['usfm']='PSA.1'
            elif mutation=='role':data['books'][0]['chapters'][0]['canonical']=True
            else:data['books'][0]['chapters']=[]
            with self.subTest(mutation=mutation),self.assertRaises(Unsupported):read_edition(data, VERSION)


class AdditionalEditionStructures(unittest.TestCase):
    def test_selah_stays_in_verse_and_unindexed_centered_line_does_not(self):
        edition=read_edition(metadata(('PSA.3',)),VERSION)
        encoded=chapter('PSA.3','<div class="q"><span class="verse" data-usfm="PSA.3.1">FIRST <span class="qs">SELAH</span></span></div><div class="qc"><span class="content">UNINDEXED HEADING</span></div><div class="q1"><span class="verse" data-usfm="PSA.3.2">SECOND</span></div>')
        raw,_=to_osis(parse_chapter(encoded,'PSA.3',edition),edition)
        from bible.youversion_content import project
        bodies,_,titles=project(E.fromstring(raw),milestones=True)
        self.assertEqual(bodies,{'Ps.3.1':'FIRST SELAH','Ps.3.2':'SECOND'})
        self.assertEqual(titles,('UNINDEXED HEADING',))
        self.assertNotIn('Ps.3.0',raw.decode())

    def test_introduction_table_preserves_header_cells_and_inline_word_boundaries(self):
        edition=read_edition(metadata(('JHN.INTRO1',)),VERSION)
        encoded=chapter('JHN.INTRO1','<div class="imt2">TITLE</div><table class="table"><tr class="row"><th class="cell">HEAD</th><td class="cell">1<span class="ord">er</span> VALUE</td></tr></table>')
        raw,_=to_osis(parse_chapter(encoded,'JHN.INTRO1',edition),edition)
        root=E.fromstring(raw);cells=root.findall('.//{'+NS+'}cell')
        self.assertEqual(cells[0].get('role'),'label')
        self.assertEqual(''.join(cells[1].itertext()).strip(),'1er VALUE')


class TreeTests(unittest.TestCase):
    def setUp(self):self.edition=read_edition(metadata(), VERSION)

    def test_ordered_fragments_notes_unicode_and_raw(self):
        result=parse_chapter(chapter(),'JHN.1',self.edition)
        self.assertEqual([v['reference'] for v in result['verses']],['JHN.1.1','JHN.1.3'])
        self.assertEqual(len(result['verses'][0]['fragments']),2)
        self.assertEqual(result['verses'][0]['text'],'Premier fragment de test & ajout synthétique ; suite du test.')
        self.assertNotIn('Note de test',result['verses'][0]['text'])
        self.assertIn('שָׁלוֹם',result['verses'][1]['text'])
        self.assertIn('test-note',result['source_html'])
        self.assertEqual(result['source_html'],decode_bytes(chapter()).decode())
        for verse in result['verses']:
            for fragment in verse['fragments']:
                node=result['tree']
                for index in fragment['tree_path']:node=node['children'][index]
                self.assertIn(('data-usfm',verse['reference']),node['attrs'])

    def test_unknown_tree_preserved_conversion_refuses(self):
        raw=chapter(content='<div class="p"><span class="verse" data-usfm="JHN.1.1"><span class="mystery" data-extra="retained">Test</span></span></div>')
        result=parse_chapter(raw,'JHN.1',self.edition)
        self.assertIn('data-extra',str(result['tree']))
        with self.assertRaises(Unsupported):to_osis(result,self.edition)

    def test_bridges_suffixes_preserved_not_guessed(self):
        for ref in ('JHN.1.2-3','JHN.1.3a'):
            result=parse_chapter(chapter(content=f'<div class="p"><span class="verse" data-usfm="{ref}">Test</span></div>'),'JHN.1',self.edition)
            self.assertEqual(result['verses'][0]['reference'],ref)
            with self.assertRaises(Unsupported):to_osis(result,self.edition)

    def test_malformed_or_wrong_identity_rejected(self):
        for raw in [chapter(version=21),encode(b'<div>'),encode(b'<div></span>'),
                    chapter(content='<div class="p"><span class="verse" data-usfm="PSA.3.1">Test</span></div>'),
                    chapter(content='<div class="p"><span class="verse" data-usfm="JHN.1.1">&#0;</span></div>'),
                    chapter(content='<div class="p" class="q1">Test</div>')]:
            with self.subTest(raw=raw[:8]),self.assertRaises(Unsupported):parse_chapter(raw,'JHN.1',self.edition)

    def test_parser_limits(self):
        for parser in (TreeParser(max_nodes=2),TreeParser(max_depth=2)):
            with self.assertRaises(Unsupported):parser.parse('<div><span>test</span></div>')

    def test_osis_semantics_and_note_isolation(self):
        result=parse_chapter(chapter(),'JHN.1',self.edition)
        raw,report=to_osis(result,self.edition);tree=E.fromstring(raw);ns={'o':NS}
        self.assertEqual(report['verse_ids'],['John.1.1','John.1.3'])
        self.assertEqual(report['note_count'],1)
        self.assertEqual(report['verse_fragments']['John.1.1'],2)
        self.assertEqual(tree.find('.//o:note',ns).get('n'),'1.1')
        self.assertEqual(tree.find('.//o:note/o:reference',ns).get('osisRef'),'Ps.3.9')
        self.assertEqual(tree.find('.//o:transChange',ns).get('type'),'added')
        self.assertIsNotNone(tree.find('.//o:divineName',ns))
        self.assertEqual(tree.find('.//o:q',ns).get('who'),'Jesus')
        self.assertEqual(tree.find('.//o:lg/o:l',ns).get('level'),'1')

    def test_noncontiguous_fragments_rejected(self):
        source=chapter(content='<div class="p">'+''.join(f'<span class="verse" data-usfm="JHN.1.{v}">Test</span>' for v in (1,3,1))+'</div>')
        with self.assertRaises(Unsupported):to_osis(parse_chapter(source,'JHN.1',self.edition),self.edition)

    def test_explicit_bridge_preserves_members_label_and_one_text_stream(self):
        source=chapter(content='<div class="p"><span class="verse" data-usfm="JHN.1.1+JHN.1.3"><span class="label">1,3</span>Texte de test regroupé.</span><span class="verse" data-usfm="JHN.1.4">Suite de test.</span></div>')
        raw,report=to_osis(parse_chapter(source,'JHN.1',self.edition),self.edition)
        tree=E.fromstring(raw);ns={'o':NS};verses=tree.findall('.//o:verse',ns)
        self.assertEqual(report['verse_ids'],['John.1.1 John.1.3','John.1.4'])
        self.assertEqual(verses[0].attrib,dict(osisID='John.1.1 John.1.3',sID='John.1.1',n='1,3'))
        self.assertEqual(verses[1].get('eID'),'John.1.1')
        self.assertEqual(''.join(tree.itertext()).count('Texte de test regroupé.'),1)
        self.assertNotIn('John.1.2',raw.decode())
        for ref in ['JHN.1.3+JHN.1.1','JHN.1.1+JHN.1.1','JHN.1.1+JHN.2.1']:
            plain=chapter(content=f'<div class="p"><span class="verse" data-usfm="{ref}">Test</span></div>')
            with self.subTest(ref=ref),self.assertRaises(Unsupported):to_osis(parse_chapter(plain,'JHN.1',self.edition),self.edition)

    def test_fragment_continues_across_heading_without_reopening_verse(self):
        source=chapter(content='<div class="p"><span class="verse" data-usfm="JHN.1.1">Début de test.</span></div><div class="s1"><span class="heading">Titre de test</span></div><div class="p"><span class="verse" data-usfm="JHN.1.1"> Suite de test.</span><span class="verse" data-usfm="JHN.1.3">Autre test.</span></div>')
        raw,report=to_osis(parse_chapter(source,'JHN.1',self.edition),self.edition)
        tree=E.fromstring(raw);ns={'o':NS}
        self.assertEqual(report['verse_ids'],['John.1.1','John.1.3'])
        self.assertEqual(report['verse_fragments']['John.1.1'],2)
        self.assertEqual(len(tree.findall('.//o:verse[@sID="John.1.1"]',ns)),1)
        self.assertEqual(len(tree.findall('.//o:verse[@eID="John.1.1"]',ns)),1)
        self.assertEqual(tree.find('.//o:title[@type="x-section"]',ns).text.strip(),'Titre de test')

    def test_heading_note_keeps_body_locator_and_following_source_anchor(self):
        source=chapter(content='<div class="s1"><span class="heading">Titre de test</span><span class="note"><span class="fr">1.3</span><span class="ft">Note du titre.</span></span></div><div class="p"><span class="verse" data-usfm="JHN.1.3">Texte de test.</span></div>')
        raw,report=to_osis(parse_chapter(source,'JHN.1',self.edition),self.edition)
        tree=E.fromstring(raw);ns={'o':NS};note=tree.find('.//o:title/o:note',ns)
        self.assertEqual(note.get('osisRef'),'John.1.3')
        self.assertEqual(note.get('n'),'1.3')
        self.assertEqual(''.join(note.itertext()),'Note du titre.')
        self.assertEqual(report['note_count'],1)
        self.assertEqual(report['verse_ids'],['John.1.3'])

    def test_reviewed_usfm_inline_and_footnote_roles_remain_separate(self):
        source=chapter(content='<div class="p"><span class="verse" data-usfm="JHN.1.1">Test<span class="ord">er</span> <span class="tl">mot étranger</span> <span class="bk">titre cité</span> <span class="em">accentué</span><span class="note"><span class="fr">1.1</span><span class="fq">citation de test</span><span class="ft"> note <span class="fv">3</span></span></span></span></div>')
        raw,report=to_osis(parse_chapter(source,'JHN.1',self.edition),self.edition)
        tree=E.fromstring(raw);ns={'o':NS}
        self.assertEqual(tree.find('.//o:note/o:catchWord',ns).text,'citation de test')
        self.assertEqual(tree.find('.//o:note/o:hi[@type="super"]',ns).text,'3')
        self.assertEqual(tree.find('.//o:seg[@type="x-transliteration"]',ns).text,'mot étranger')
        self.assertEqual(tree.find('.//o:name[@type="x-book-title"]',ns).text,'titre cité')
        self.assertEqual(tree.find('.//o:hi[@type="emphasis"]',ns).text,'accentué')
        self.assertEqual(report['note_count'],1)
        for role in ['fq','fv']:
            bad=chapter(content=f'<div class="p"><span class="verse" data-usfm="JHN.1.1"><span class="{role}">Test</span></span></div>')
            with self.subTest(role=role),self.assertRaises(Unsupported):to_osis(parse_chapter(bad,'JHN.1',self.edition),self.edition)

    def test_list_indentation_and_embedded_no_break_paragraphs_retained(self):
        source=chapter(content='<div class="li2"><span class="verse" data-usfm="JHN.1.1">Test indenté.</span></div><div class="li1"><span class="verse" data-usfm="JHN.1.3">Test principal.</span></div><div class="pm"><span class="verse" data-usfm="JHN.1.4">Test enchâssé.</span></div><div class="nb"><span class="verse" data-usfm="JHN.1.5">Suite sans rupture.</span></div>')
        raw,report=to_osis(parse_chapter(source,'JHN.1',self.edition),self.edition)
        tree=E.fromstring(raw);ns={'o':NS}
        self.assertEqual([n.get('type') for n in tree.findall('.//o:list/o:item',ns)],['x-level-2','x-level-1'])
        self.assertIsNotNone(tree.find('.//o:p[@type="x-embedded"]',ns))
        self.assertIsNotNone(tree.find('.//o:p[@type="x-no-break"]',ns))
        self.assertEqual(len(report['verse_ids']),4)

    def test_introduction_lists_and_explicit_blank_line_do_not_create_verses(self):
        source=chapter('JHN.INTRO1','<div class="ili1">Introduction synthétique.</div><div class="ili2">Détail synthétique.</div><div class="ib"></div>')
        raw,report=to_osis(parse_chapter(source,'JHN.INTRO1',self.edition),self.edition)
        tree=E.fromstring(raw);ns={'o':NS}
        self.assertEqual(report['verse_ids'],[])
        self.assertEqual(len(tree.findall('.//o:list/o:item',ns)),2)
        self.assertEqual(len(tree.findall('.//o:milestone[@type="x-source-blank-line"]',ns)),1)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'test.zip';self.edition=read_edition(metadata(), VERSION)

    def test_metadata_order_including_introductions_and_complete_inventory(self):
        synthetic_archive(self.path)
        records=list(archive_chapters(self.path,self.edition,complete=True))
        self.assertEqual([r['reference'] for r in records],list(self.edition.chapters))
        self.assertEqual(records[0]['verses'],[])
        self.assertEqual(len(list(Path(self.tmp.name).iterdir())),1)

    def test_missing_chapter_and_wrong_archive(self):
        with zipfile.ZipFile(self.path,'w') as z:z.writestr('JHN/1.yves',chapter())
        self.assertEqual(len(list(archive_chapters(self.path,self.edition))),1)
        with self.assertRaises(Unsupported):list(archive_chapters(self.path,self.edition,complete=True))
        with zipfile.ZipFile(self.path,'w') as z:z.writestr('JHN/2.yves',chapter())
        with self.assertRaises(Unsupported):list(archive_chapters(self.path,self.edition))

    def test_security_names_duplicates_and_symlinks(self):
        for bad in ['../escape.yves','/JHN/1.yves','JHN\\1.yves','JHN//1.yves','JHN/./1.yves','C:/JHN/1.yves']:
            with zipfile.ZipFile(self.path,'w') as z:z.writestr(bad,chapter())
            with self.subTest(name=bad),self.assertRaises(Unsupported):list(archive_chapters(self.path,self.edition))
        with zipfile.ZipFile(self.path,'w') as z:
            z.writestr('a/JHN/1.yves',chapter());z.writestr('b/JHN/1.yves',chapter())
        with self.assertRaises(Unsupported):list(archive_chapters(self.path,self.edition))
        with zipfile.ZipFile(self.path,'w') as z:
            item=zipfile.ZipInfo('JHN/1.yves');item.external_attr=(0o120777<<16);z.writestr(item,b'target')
        with self.assertRaises(Unsupported):list(archive_chapters(self.path,self.edition))

    def test_limits_and_crc(self):
        synthetic_archive(self.path)
        for limits in [dict(max_member=2),dict(max_total=3),dict(max_entries=1)]:
            with self.subTest(limits=limits),self.assertRaises(Unsupported):list(archive_chapters(self.path,self.edition,**limits))
        with zipfile.ZipFile(self.path,'w',compression=zipfile.ZIP_STORED) as z:z.writestr('JHN/1.yves',chapter())
        raw=bytearray(self.path.read_bytes());raw[45]^=1;self.path.write_bytes(raw)
        with self.assertRaises(zipfile.BadZipFile):list(archive_chapters(self.path,self.edition))


if __name__=='__main__':unittest.main()
