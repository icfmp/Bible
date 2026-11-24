import unittest
from bible.commentary_format import format_entry


class CommentaryFormatTests(unittest.TestCase):
    def test_native_numeric_entity_filter_keeps_provenance_and_literal_sequences(self):
        raw='<title>Source title</title><hi type="italic">A&amp;B; named &amp;#224; numeric &#38;#224; proper &#224;.</hi>'
        native='Source title * A&B; named &#224; numeric #224; proper . *'
        text,styles,titles=format_entry(raw,native,'OSIS')
        hidden={i for kind,a,b in styles if kind=='hidden' for i in range(a,b)}
        self.assertEqual(''.join(c for i,c in enumerate(text) if i not in hidden),native.replace('*',''))
        self.assertEqual(len(hidden),2);self.assertEqual(titles,())
        self.assertIn('named &#224;',text);self.assertIn('numeric #224;',text)
        nested='<hi type="italic">litera &amp;#224; qu&amp;#226; words</hi>'
        native_nested='* litera #224; qu#226; words *'
        value,ranges,_=format_entry(nested,native_nested,'OSIS')
        self.assertEqual(value,native_nested)
        self.assertEqual(sum(b-a for kind,a,b in ranges if kind=='hidden'),2)
        # An authored sequence retained by a different filter remains exact.
        retained='* litera &#224; qu&#226; words *'
        self.assertEqual(format_entry(nested,retained,'OSIS')[0],retained)
        changed=native.replace('Source title','Another title')
        self.assertEqual(format_entry(raw,changed,'OSIS'),(changed,(),()))

    def test_real_mhc_title_kept_by_native_filter_does_not_force_raw_stars_fallback(self):
        # Bible Resources MHC 0.1.0, derived from public-domain CrossWire 2.2,
        # Genesis 1:9–13: bounded literal source/native excerpt, not test prose
        # inserted into a resource. Its heading filter retains the OSIS title.
        raw=('<div eID="gen38" type="x-p"/> <title type="x-s3">The Creation. '
             '(<hi type="small-caps">b. c.</hi> 4004.)</title> <div sID="gen39" type="x-p"/> '
             '<hi type="super">9</hi> And God said, Let the waters under the heaven be gathered '
             'together unto one place, and let the dry <hi type="italic">land</hi> appear: and it was so.')
        native=(' The Creation. (* b. c. * 4004.)\n  * 9 * And God said, Let the waters under the heaven '
                'be gathered together unto one place, and let the dry * land * appear: and it was so.')
        text,styles,titles=format_entry(raw,native,'OSIS')
        hidden={i for kind,a,b in styles if kind=='hidden' for i in range(a,b)}
        visible=''.join(c for i,c in enumerate(text) if i not in hidden)
        self.assertEqual(len(text),len(native));self.assertEqual(titles,())
        self.assertEqual(len(hidden),6);self.assertNotIn('*',visible)
        self.assertTrue(any(kind=='heading' and 'The Creation.' in text[a:b] for kind,a,b in styles))
        self.assertTrue(any(kind=='italic' and text[a:b]=='land' for kind,a,b in styles))
        self.assertTrue(any(kind=='small-caps' and text[a:b]=='b. c.' for kind,a,b in styles))
        self.assertTrue(format_entry(raw+' *authored*',native+' *authored*','OSIS')[0].endswith('*authored*'))
        changed=native.replace('waters','different words')
        self.assertEqual(format_entry(raw,changed,'OSIS'),(changed,(),()))

    def test_nested_native_markers_keep_literal_stars_and_semantic_emphasis(self):
        raw='<hi type="italic"><hi type="small-caps">choikos</hi></hi>—<hi type="italic">dusty,</hi> *literal*'
        plain='* choikos * * *—* dusty, * *literal*'
        text,styles,_=format_entry(raw,plain,'OSIS')
        hidden={i for kind,start,end in styles if kind=='hidden' for i in range(start,end)}
        visible=''.join(c for i,c in enumerate(text) if i not in hidden)
        self.assertEqual(''.join(visible.split()),'choikos—dusty,*literal*')
        self.assertEqual(len(hidden),6)
        self.assertTrue(any(kind=='small-caps' for kind,_,_ in styles))
        for unsafe in [plain+'*',plain.replace('dusty,','different,'),plain.replace('choikos','choi*kos')]:
            self.assertEqual(format_entry(raw,unsafe,'OSIS'),(unsafe,(),()))

    def test_native_filter_retaining_source_preface_keeps_literal_stars(self):
        raw=('<div subType="x-preverse" sID="pv1"/><title>PREFACE</title>'
             '<p>Source <hi type="italic">foreword</hi> with *literal*.</p>'
             '<div subType="x-preverse" eID="pv1"/><title>Body title</title>'
             '<hi type="super">1</hi> Body words.')
        plain='PREFACE  Source * foreword * with *literal*. Body title * 1 * Body words.'
        text,styles,titles=format_entry(raw,plain,'OSIS')
        hidden={i for kind,a,b in styles if kind=='hidden' for i in range(a,b)}
        visible=''.join(c for i,c in enumerate(text) if i not in hidden)
        self.assertEqual(len(hidden),4);self.assertIn('*literal*',visible)
        self.assertIn('foreword',visible);self.assertIn('Body title',visible)
        self.assertEqual(titles,());self.assertEqual(len(text),len(plain))

    def test_actual_preverse_prose_is_separate_and_keeps_source_case_and_styles(self):
        from bible.commentary_format import preverse_layout
        raw=('<div type="x-milestone" subType="x-preverse" sID="pv1"/>'
             '<title>PREFACE</title><div type="x-p" sID="p1"/>Actual <hi type="italic">foreword</hi>.'
             '<note>Excluded note.</note><div type="x-p" eID="p1"/>'
             '<div type="x-milestone" subType="x-preverse" eID="pv1"/>'
             '<title>Current entry</title><hi type="super">1</hi> Body * literal.')
        plain='* 1 * Body * literal.'
        text,styles,titles=format_entry(raw,plain,'OSIS')
        self.assertEqual(len(text),len(plain));self.assertEqual(titles,('Current entry',))
        self.assertTrue(any(kind=='number' for kind,_,_ in styles))
        prefix,prefix_styles,_=preverse_layout(raw)
        self.assertIn('PREFACE',prefix);self.assertIn('Actual foreword.',prefix)
        self.assertNotIn('Excluded note.',prefix);self.assertNotIn('Body',prefix)
        self.assertTrue(any(kind=='italic' and prefix[first:last]=='foreword' for kind,first,last in prefix_styles))

    def test_only_verified_osis_decorations_are_hidden(self):
        raw='<title>Actual heading</title><div type="x-p"/>Literal * star. <hi type="italic">Real emphasis</hi><div type="x-p"/>Next paragraph.'
        plain='  Literal * star. * Real emphasis *   Next paragraph.'
        text,styles,titles=format_entry(raw,plain,'OSIS')
        self.assertEqual(len(text),len(plain))  # Legacy body offsets stay valid.
        self.assertEqual(titles,('Actual heading',))
        hidden={i for kind,start,end in styles if kind=='hidden' for i in range(start,end)}
        visible=''.join(c for i,c in enumerate(text) if i not in hidden)
        self.assertIn('Literal * star.',visible)
        self.assertNotIn('* Real emphasis *',visible)
        self.assertIn('Real emphasis',visible)
        self.assertIn('\n',visible)
        self.assertTrue(any(kind=='italic' for kind,_,_ in styles))

    def test_unknown_filter_output_keeps_original_text(self):
        self.assertEqual(format_entry('<hi type="italic">Different</hi>','Original * unchanged','OSIS'),('Original * unchanged',(),()))
        self.assertEqual(format_entry('* actual plain *','* actual plain *','Plaintext'),('* actual plain *',(),()))

    def test_thml_encodes_styles_without_guessing_structure_from_plain_prose(self):
        raw='<h3>Source title</h3><p>Keep <b>bold</b>.</p><blockquote>Quoted.</blockquote><ul><li>First</li><li>Second</li></ul><p>Original.</p>'
        plain='Source title  Keep bold.  Quoted.  First Second  Original.'
        text,styles,titles=format_entry(raw,plain,'ThML')
        self.assertEqual(''.join(text.split()),''.join(plain.split()))
        self.assertEqual(titles,())
        kinds={kind for kind,_,_ in styles}
        self.assertTrue({'heading','bold','quotation','list-item'}<=kinds)
        self.assertEqual(format_entry(raw,'Different native output','ThML'),('Different native output',(),()))

    def test_osis_line_milestones_and_stanzas_preserve_authorial_words(self):
        raw='<lg><l sID="line1"/>First line.<l eID="line1"/><l>Second line.</l></lg><p>Final prose.</p>'
        plain='  First line. Second line.  Final prose.'
        text,styles,_=format_entry(raw,plain,'OSIS')
        self.assertEqual(''.join(text.split()),''.join(plain.split()))
        self.assertEqual([text[a:b] for kind,a,b in styles if kind=='poetry'],['First line.','Second line.'])
        self.assertNotIn('quotation',{kind for kind,_,_ in styles})


class CommentaryLayoutTests(unittest.TestCase):

    @unittest.skipUnless(__import__('os').environ.get('DISPLAY'),'Requires GTK')
    def test_matching_source_title_survives_with_body_anchors_and_copy(self):
        import tempfile
        from pathlib import Path
        from bible.ui import Application,Window,Library
        from bible.paged_sources import CommentaryPages
        from tests.test_ui import installed_fixture,spin
        from tests.test_commentary import commentary_fixture
        app=Application.get_default() or Application();app.register()
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            root=commentary_fixture(directory,entries=[('Gen.1.1','<title>Verse 1</title><p>UNCHANGED SOURCE BODY.</p>'),
                ('Gen.1.2','<title>Verses 2–3</title><p>DIFFERENT SOURCE COVERAGE.</p>'),
                ('Gen.1.3','<p><hi type="bold">Verse 3</hi> SOURCE BOLD LABEL.</p>')])
            conf=root/'mods.d/test.conf';conf.write_text(conf.read_text().replace('SourceType=Plaintext','SourceType=OSIS')+'GlobalOptionFilter=OSISHeadings\n')
            w=Window(app,Library(Path(directory)/'translations'));w.present()
            try:
                w.study_button.set_active(True);panel=w.study
                panel.choices.set_selected(panel.names.index('Notes'));spin(lambda:not panel._positioning and not panel._choice_idle)
                source=CommentaryPages(panel.reader,w.library.resource('Notes'))
                text=panel.text.get_buffer().props.text
                for ref,match,title in [('Gen.1.1',True,'Verse 1'),('Gen.1.2',False,'Verses 2–3'),('Gen.1.3',True,'Verse 3')]:
                    pos=panel.reader.index.locate(ref);doc=source.document(pos,w.preferences.value)
                    self.assertEqual(doc.text[:doc.context_length],panel.reader.index.label(pos)+'\n')
                    self.assertIn(title,doc.copy(0,len(doc.text)))
                    start,body,end=panel.ranges[pos]
                    self.assertTrue(text[start:end].startswith(panel.reader.index.label(pos)))
                    self.assertNotIn(panel.reader.index.label(pos),doc.copy(0,len(doc.text)))
                    self.assertEqual(text[body:end],doc.text[doc.spans[0].body:])
                    if ref=='Gen.1.3':
                        panel.current_position=pos;panel.reveal(pos,force=True);spin(lambda:not panel._positioning)
                        ink=panel.text.get_iter_location(panel.text.get_buffer().get_iter_at_offset(body+2))
                        self.assertGreaterEqual(ink.y,panel.text.get_visible_rect().y)
                self.assertIn('UNCHANGED SOURCE BODY.',text)
            finally:w.close()

    @unittest.skipUnless(__import__('os').environ.get('DISPLAY'),'Requires GTK')
    def test_source_preface_is_readable_without_moving_the_native_body_or_changing_modules(self):
        import hashlib,tempfile
        from pathlib import Path
        from bible.ui import Application,Window,Library
        from tests.test_ui import installed_fixture,spin
        from tests.test_commentary import commentary_fixture
        raw=('<div type="x-milestone" subType="x-preverse" sID="pv1"/>'
             '<title>SOURCE PREFACE</title><p>'+('Actual foreword. '*500)+'</p>'
             '<div type="x-milestone" subType="x-preverse" eID="pv1"/>'
             '<title>Current source heading</title><p><hi type="super">1</hi> ACTUAL BODY.</p>')
        app=Application.get_default() or Application();app.register()
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory)
            root=commentary_fixture(directory,entries=[('Gen.1.1',raw)])
            conf=root/'mods.d/test.conf'
            conf.write_text(conf.read_text().replace('SourceType=Plaintext','SourceType=OSIS')+
                            'GlobalOptionFilter=OSISHeadings\nGlobalOptionFilter=OSISFootnotes\n')
            files={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
            window=Window(app,Library(Path(directory)/'translations'));window.set_default_size(1000,700);window.present()
            try:
                window.study_button.set_active(True);panel=window.study
                panel.choices.set_selected(panel.names.index('Notes'));spin(lambda:not panel._positioning,duration=.4)
                self.assertNotIn('Actual foreword.',panel.text.get_buffer().props.text)
                self.assertIn('ACTUAL BODY.',panel.text.get_buffer().props.text)
                self.assertTrue(panel.entry_actions['source-preface'].get_enabled())
                reference=window.active_tab.state.reference;position=panel.anchor()
                panel.entry_actions['source-preface'].activate(None);spin()
                preface=window.commentary_preface
                self.assertEqual(preface.source_document.text.count('Actual foreword.'),500)
                self.assertIn('SOURCE PREFACE',preface.text.get_buffer().props.text)
                self.assertNotIn('ACTUAL BODY.',preface.text.get_buffer().props.text)
                buffer=preface.text.get_buffer();foreword=buffer.get_iter_at_offset(buffer.props.text.index('Actual foreword.'))
                self.assertNotIn('source-heading',[t.props.name for t in foreword.get_tags()])
                expected=preface.source_document.copy(0,len(preface.source_document.text))
                preface.set_default_size(340,400);spin(duration=.3)
                self.assertEqual(preface.source_document.copy(0,len(preface.source_document.text)),expected)
                preface.close();spin()
                self.assertIsNone(window.commentary_preface)
                self.assertEqual(window.active_tab.state.reference,reference);self.assertEqual(panel.anchor(),position)
                self.assertEqual({p:hashlib.sha256(p.read_bytes()).hexdigest() for p in files},files)
            finally:window.close()

    @unittest.skipUnless(__import__('os').environ.get('DISPLAY'),'Requires GTK')
    def test_verified_decorations_have_zero_advance_without_invisible_indices(self):
        from bible.ui import Application,Gtk
        from bible.commentary_format import apply
        from bible.preferences import ReadingPreferences
        from bible.pagination import Document,StyleSpan
        from tests.test_ui import spin
        app=Application.get_default() or Application();app.register()
        raw='<hi type="italic">Élève — naïf Ω</hi> après. '
        plain='* Élève — naïf Ω * après. '
        text,styles,_=format_entry(raw*150,plain*150,'OSIS')
        view=Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        window=Gtk.Window(default_width=340,default_height=320);window.set_child(view)
        try:
            view.get_buffer().set_text(text)
            apply(view,styles,ReadingPreferences(),'white');window.present();spin()
            tag=view.get_buffer().get_tag_table().lookup('source-hidden')
            self.assertFalse(tag.props.invisible)
            self.assertEqual(tag.props.scale,0)
            for kind,start,end in styles:
                if kind=='hidden':
                    self.assertEqual(view.get_iter_location(view.get_buffer().get_iter_at_offset(start)).width,0)
            # Hit-test wrapped, non-ASCII paragraphs through the complete layout.
            end=view.get_iter_location(view.get_buffer().get_end_iter()).y
            for y in range(0,end+1,11):
                _,iterator=view.get_iter_at_location(0,y)
                self.assertLessEqual(iterator.get_offset(),len(text))
            document=Document('entry',text,(),tuple(StyleSpan(*s) for s in styles))
            self.assertEqual(document.copy(0,len(text)),plain.replace('*','')*150)
        finally:window.destroy()
