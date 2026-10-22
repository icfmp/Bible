"""Recognition is conservative, source-numbered and independent of installed text."""
import unittest
from bible.citations import citations
from bible.markdown import render


class CitationTests(unittest.TestCase):
    def parse(self,text,system='Segond'):
        plain,spans=render(text)
        return [(plain[c.begin:c.finish],c.start,c.end) for c in citations(plain,system,spans)]

    def test_french_english_accents_numbered_books_abbreviations_and_ranges(self):
        for source,start,end in [('Voir Romains 8.28–30.','Rom.8.28','Rom.8.30'),
                ('Romans 8:28–30','Rom.8.28','Rom.8.30'),('Ésaïe 9.2','Isa.9.2','Isa.9.2'),
                ('ESAIE 9:2','Isa.9.2','Isa.9.2'),('E\u0301sai\u0308e 9:2','Isa.9.2','Isa.9.2'),
                ('1 Corinthiens 13.4–7','1Cor.13.4','1Cor.13.7'),('1John 1:5','1John.1.5','1John.1.5'),
                ('1 Co 13.4','1Cor.13.4','1Cor.13.4'),('Rm. 8.28','Rom.8.28','Rom.8.28'),
                ('John.3.16','John.3.16','John.3.16'),('Romans 8:28–9:2','Rom.8.28','Rom.9.2')]:
            with self.subTest(source=source):
                result=self.parse(source);self.assertEqual(len(result),1,result)
                self.assertEqual(result[0][1:],(start,end))
                self.assertIn(result[0][0],source)

    def test_invalid_numbers_dates_ambiguous_words_and_partial_ranges_stay_inert(self):
        for source in ['22/10/2026','2026.10.22','12:30','may 3:16','he 3:16','is 3:16',
                       '4 John 3:16','John 999:1','John 3:999','John 3:16-999','John 3:18-16',
                       'John 3:16-x','John 3:16-Romans 8:28','John 3:16abc','reportJohn 3:16','John 3:16.20']:
            with self.subTest(source=source):self.assertEqual(self.parse(source),[])

    def test_code_existing_links_urls_and_html_do_not_create_generated_links(self):
        for source in ['`John 3:16`','``John 3:16``','```python\nJohn 3:16\n```',
                       '~~~\nJohn 3:16\n~~~','```\nJohn 3:16',
                       '[John 3:16](https://example.test)','[x](javascript:John 3:16)',
                       'https://example.test/John.3.16','javascript:John 3:16',
                       '<a href="file:///tmp/x">John 3:16</a>','<script>John 3:16</script>','<a>John 3:16','<!-- John 3:16 -->']:
            with self.subTest(source=source):self.assertEqual(self.parse(source),[])
        self.assertEqual(self.parse('`John 3:16` then Romans 8:28')[0][1],'Rom.8.28')
        self.assertEqual(self.parse('**Romans 8:28**')[0][0],'Romans 8:28')

    def test_citations_use_the_authored_note_numbering_without_requiring_module_text(self):
        self.assertEqual(self.parse('3 Jean 1:15','Segond')[0][1],'3John.1.15')
        self.assertEqual(self.parse('3 John 1:15','KJV'),[])
        self.assertEqual(self.parse('Psaumes 3:2','Segond')[0][1],'Ps.3.2')
        self.assertEqual(self.parse('John 3:16','UnknownFutureSystem'),[])
