"""Research oracle checks; lxml is not an application runtime dependency."""
import unittest
try:
    from .check_yves_fidelity import compiled_chapter
    from lxml.etree import XMLSyntaxError
except ImportError:
    compiled_chapter=None


@unittest.skipIf(compiled_chapter is None,'Requires the isolated research lxml oracle')
class NativeFragmentOracleTests(unittest.TestCase):
    def test_list_crosses_native_entries_without_recovery_or_lost_body(self):
        bodies,notes,titles=compiled_chapter([
            ('Gen.1.0','<list>'),('Gen.1.1','<item>First test body.'),
            ('Gen.1.3','</item><item>Second test body.</item></list>')])
        self.assertEqual(bodies,{'Gen.1.1':'First test body.','Gen.1.3':'Second test body.'})
        self.assertEqual(notes,[]);self.assertEqual(titles,[])

    def test_heading_note_stays_separate_and_inline_ordinal_has_no_inserted_space(self):
        bodies,notes,titles=compiled_chapter([
            ('Gen.1.0','<title>Test heading<note n="1.1">Header note.</note></title>'),
            ('Gen.1.1','1<hi type="super">er</hi> test &amp; continuation.')])
        self.assertEqual(bodies,{'Gen.1.1':'1er test & continuation.'})
        self.assertEqual(len(notes),1);self.assertEqual(notes[0].get('n'),'1.1')
        self.assertEqual(len(titles),1)

    def test_unbalanced_complete_chapter_is_rejected(self):
        with self.assertRaises(XMLSyntaxError):compiled_chapter([('Gen.1.1','<list><item>Test')])
