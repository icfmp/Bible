"""Compile/read neutral structures through the actual native source pipeline."""
from contextlib import redirect_stdout
from pathlib import Path
import io,json,os,tempfile,unittest,zipfile
from tools.research.test_yves_source import metadata,chapter


def compiler_available():
    try:
        from bible.source_versification import native_loader
        native_loader()
        return Path(os.environ.get('BIBLE_OSIS2MOD','/app/bin/osis2mod')).is_file()
    except (ValueError,ImportError):return False


@unittest.skipUnless(compiler_available(),'Requires packaged source-index compiler and SWORD')
class NativeUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from bible.youversion_worker import build
        from bible.sword_provider import Reader
        cls.temporary=tempfile.TemporaryDirectory();base=Path(cls.temporary.name)
        cls.root=base/'module';cls.identifier=900153
        refs=['SIR.INTRO1','SIR.1','SIR.1_1','SIR.43','SIR.44']
        data=metadata(refs);data['id']=cls.identifier;data['books'][0]['canon']='dc'
        data['offline']=None
        for row in data['books'][0]['chapters']:row['human']=row['usfm'].split('.')[1].split('_')[0]
        def verse(ref,text,label=None):
            return '<div class="p"><span class="verse" data-usfm="'+ref+'">'+('<span class="label">'+label+'</span>' if label else '')+text+'</span></div>'
        bodies=[
            '<div class="ip">SYNTHETIC INTRODUCTION</div>',
            verse('SIR.1.1','FIRST DISTINCT SECTION'),
            verse('SIR.1_1.1','SECOND DISTINCT SECTION'),
            verse('SIR.43.17','<span class="bd">FIRST FRAGMENT</span><span class="note"><span class="fr">17a</span><span class="ft">FIRST EDITORIAL NOTE</span></span>','17a')+verse('SIR.43.16','MIDDLE VERSE','16')+verse('SIR.43.17','LAST FRAGMENT<span class="note"><span class="fr">17b</span><span class="ft">LAST EDITORIAL NOTE</span></span>','17b'),
            verse('SIR.44.22+SIR.44.23','SHARED CONTENT','22–23')+verse('SIR.44.23','TAIL CONTENT','23')]
        archive=base/'synthetic.zip';meta=base/'metadata.json';meta.write_text(json.dumps(data))
        with zipfile.ZipFile(archive,'w') as z:
            for ref,body in zip(refs,bodies):
                book,number=ref.split('.');z.writestr(book+'/'+number+'.yves',chapter(ref,body,version=cls.identifier))
        with redirect_stdout(io.StringIO()):build(archive,meta,cls.root,os.environ.get('BIBLE_OSIS2MOD','/app/bin/osis2mod'),cls.identifier)
        cls.reader=Reader(cls.root,'youversion~YV'+str(cls.identifier))
        cls.archive=archive
        from bible.youversion_source import read_edition
        cls.edition=read_edition(data,cls.identifier)

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def test_distinct_sections_keep_labels_roles_and_native_coordinates_private(self):
        r=self.reader
        self.assertIn('FIRST DISTINCT SECTION',r.chapter('Sir.1.1').text_by_reference['Sir.1.1'])
        self.assertIn('SECOND DISTINCT SECTION',r.chapter('Sir.1_1.1').text_by_reference['Sir.1_1.1'])
        self.assertEqual(list(r.books[0].chapters),[1,'1_1',43,44])
        self.assertEqual(r.neighbours('Sir.1_1.1'),('Sir.1.1','Sir.43.17'))
        self.assertEqual([c.canonical for c in r.addresses.sections.chapters],[False,True,True,True,True])
        self.assertEqual(r.chapter_label('Sir.1_1'),'1')
        from bible.reference_resolution import resolve,VersificationMismatch
        self.assertEqual(resolve('Sir.1_1.1',r.versification,r).start,'Sir.1_1.1')
        from bible.reference_targets import Canon
        with self.assertRaises(VersificationMismatch):resolve('Sir.1_1.1',r.versification,Canon('KJV'))

    def test_public_alias_of_partial_bridge_and_search_do_not_collide(self):
        r=self.reader;a=r.key('Sir.44.22');b=r.key('Sir.44.23')
        self.assertEqual(a.getIndex(),b.getIndex())
        self.assertEqual(a.getOSISRef(),'Sir.44.22');self.assertEqual(b.getOSISRef(),'Sir.44.23')
        value=r.chapter('Sir.44.23')
        self.assertIn('SHARED CONTENT',value.text_by_reference['Sir.44.22'])
        self.assertNotIn('TAIL CONTENT',value.text_by_reference['Sir.44.22'])
        self.assertIn('TAIL CONTENT',value.text_by_reference['Sir.44.23'])
        from bible.text_search import index,query_index
        result=query_index(index(self.root.parent,'synthetic-source',r),'tail content')
        self.assertEqual(result['references'],['Sir.44.23'])

    def test_display_copy_and_every_body_anchor_keep_interleaved_fragments(self):
        from bible.paged_sources import BiblePages
        from bible.preferences import ReadingPreferences
        from bible.sword_provider import passage_verses
        r=self.reader;doc=BiblePages(r,None).document('Sir.43',ReadingPreferences())
        positions=[doc.copy_text.index(text) for text in ['FIRST FRAGMENT','MIDDLE VERSE','LAST FRAGMENT']]
        self.assertEqual(positions,sorted(positions))
        self.assertEqual([s.number for s in doc.spans],['17a','16','17b'])
        for span in doc.spans:
            for offset in range(span.body,span.end):self.assertEqual(doc.locate(doc.anchor(offset)),offset)
        self.assertGreater(doc.anchor(positions[2]).offset,0)
        rows=passage_verses(r,['Sir.43.16','Sir.43.17'])
        self.assertEqual([text.strip() for ref,text in rows],['FIRST FRAGMENT','MIDDLE VERSE','LAST FRAGMENT'])
        bridge=BiblePages(r,None).document('Sir.44',ReadingPreferences())
        self.assertEqual(bridge.copy_text.count('SHARED CONTENT'),1)
        self.assertEqual(bridge.copy_text.count('TAIL CONTENT'),1)
        self.assertEqual([text.strip() for ref,text in passage_verses(r,['Sir.44.22','Sir.44.23'])],['SHARED CONTENT','TAIL CONTENT'])

    def test_existing_numeric_annotations_and_new_section_annotations_roundtrip(self):
        from bible.notes import NoteStore,parts
        from bible.passage_annotations import PassageAnnotations
        r=self.reader
        with tempfile.TemporaryDirectory() as directory:
            store=NoteStore(Path(directory)/'notes.sqlite3')
            self.addCleanup(store.close)
            note=store.save('Section note',[],versification=r.versification,start='Sir.1_1.1',origin_translation='synthetic',origin_language='fr')
            ordinary=store.save('EXISTING NOTE',[],versification='KJV',start='John.3.16',origin_translation='existing',origin_language='en')
            self.assertEqual(store.get(ordinary.id),ordinary)
            self.assertEqual(store.get(note.id).start,'Sir.1_1.1')
            self.assertEqual(parts(note.start),('Sir','1_1',1))
            projection=PassageAnnotations()
            self.assertEqual([n.id for n in projection.notes(r,note.start,note.end,store)],[note.id])
            self.assertEqual(projection.notes(r,'Sir.1.1','Sir.1.1',store),[])
            backup=Path(directory)/'backup.json';store.export(backup)
            other=NoteStore(Path(directory)/'restored.sqlite3');self.addCleanup(other.close);other.restore(backup)
            self.assertEqual(other.get(note.id).start,note.start)
            self.assertEqual(other.get(ordinary.id),ordinary)

    def test_independent_source_dom_confirms_every_unit_and_editorial_content(self):
        from tools.research.check_source_units import audit
        result=audit(self.archive,self.edition,self.reader)
        self.assertEqual((result['physical_files'],result['chapters'],result['introductions'],result['units']),(5,4,1,7))
        self.assertEqual(result['notes'],2)

    def test_comparison_rows_keep_shared_continuation_once_and_refuse_fragment_reordering(self):
        from bible.paged_sources import BiblePages
        from bible.preferences import ReadingPreferences
        from bible.comparison_layout import Correspondence,row_document
        pages=BiblePages(self.reader,None)
        shared=pages.document('Sir.44',ReadingPreferences())
        rows=(Correspondence(('Sir.44.22','Sir.44.23'),()),)
        rendered,_=row_document(shared,rows,0,'GAP')
        self.assertEqual(rendered.copy_text.count('SHARED CONTENT'),1)
        self.assertEqual(rendered.copy_text.count('TAIL CONTENT'),1)
        interleaved=pages.document('Sir.43',ReadingPreferences())
        with self.assertRaisesRegex(ValueError,'Non-monotonic source fragments'):
            row_document(interleaved,(Correspondence(('Sir.43.17',),()),Correspondence(('Sir.43.16',),())),0,'GAP')

    @unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK')
    def test_native_reader_keeps_fragment_highlights_markers_and_appearance_anchors(self):
        import shutil
        from unittest.mock import patch
        from bible.ui import Application,Window,Library
        from tests.test_ui import spin,close_test_dialogs
        from bible.pagination import Anchor
        with tempfile.TemporaryDirectory() as directory:
            profile=Path(directory);name='youversion~YV'+str(self.identifier)
            target=profile/'translations'/name;shutil.copytree(self.root,target)
            (target/'.complete').write_text(name)
            (target/'.source.json').write_text(json.dumps(dict(provider_id='youversion',module_name='YV'+str(self.identifier))))
            app=Application.get_default() or Application();app.register()
            window=Window(app,Library(profile/'translations'));window.set_default_size(1000,760);window.present();spin()
            self.addCleanup(close_test_dialogs)
            try:
                tab=window.active_tab;tab.navigate(name,'Sir.43.17');spin()
                window.notes_store.save('FRAGMENT PERSONAL NOTE',[],versification=tab.reader.versification,start='Sir.43.17',origin_translation=name,origin_language='fr')
                window.highlights.set(tab.reader.versification,['Sir.43.17'],'yellow',name)
                tab.render_chapter(tab.current);spin()
                doc=tab._document;third=next(s for s in reversed(doc.spans) if s.reference=='Sir.43.17')
                offset=third.body+3;position=tab.position_anchor(offset)
                self.assertIsInstance(position[1],Anchor)
                self.assertEqual(tab.anchor_offset(position),offset)
                self.assertEqual(len([r for r,a,b in tab.text._verse_fragments if r=='Sir.43.17']),2)
                tag=tab.text.get_buffer().get_tag_table().lookup('highlight-yellow')
                for span in doc.spans:
                    self.assertEqual(tab.text.get_buffer().get_iter_at_offset(span.body+1).has_tag(tag),span.reference=='Sir.43.17')
                self.assertEqual(len([b for b in tab.text._inline_buttons if b._marker_reference=='Sir.43.17']),1)
                for span in doc.spans:
                    for offset in range(span.body,span.end):
                        # Inline child objects and their adjacent whitespace are
                        # intentionally excluded from canonical character IDs.
                        if doc.text[offset].isalpha():self.assertEqual(tab.anchor_offset(tab.position_anchor(offset)),offset)
                window.appearance.update('size',22);spin()
                self.assertEqual(tab._document.copy_text.count('FIRST FRAGMENT'),1)
                self.assertEqual(tab._document.copy_text.count('LAST FRAGMENT'),1)
                tab.navigate(name,'Sir.1_1.1');spin()
                self.assertEqual(tab.state.reference,'Sir.1_1.1')
                self.assertIn('SECOND DISTINCT SECTION',tab._document.copy_text)
            finally:window.close();spin()


if __name__=='__main__':unittest.main()
