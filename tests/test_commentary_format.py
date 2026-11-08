import unittest
from bible.commentary_format import format_entry


class CommentaryFormatTests(unittest.TestCase):
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


class CommentaryLayoutTests(unittest.TestCase):
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
