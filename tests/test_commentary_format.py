import unittest
from bible.commentary_format import format_entry


class CommentaryFormatTests(unittest.TestCase):
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
