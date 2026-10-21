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
