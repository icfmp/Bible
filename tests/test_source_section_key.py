"""Real SWORD storage retains distinct, unchanged source identities."""
from pathlib import Path
import tempfile
import unittest
from bible.source_sections import SourceChapter,SectionIndex


class SourceSectionKeyTests(unittest.TestCase):
    def test_native_fields_and_public_section_id_are_distinct_and_roundtrip(self):
        import Sword
        from bible.source_section_key import key_type
        from tests.test_ui import installed_fixture
        from bible.sword_provider import Reader
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,entries=[('Gen.1.1','SYNTHETIC FIRST SECTION'),
                                                ('Gen.2.1','SYNTHETIC SECOND SECTION'),
                                                ('Gen.3.1','SYNTHETIC CHAPTER TWO')])
            reader=Reader(Path(directory)/'translations/Test','Test')
            index=SectionIndex.allocate([SourceChapter('Gen.1','1',True),
                                         SourceChapter('Gen.1_1','1',True),
                                         SourceChapter('Gen.2','2',True)])
            SourceKey=key_type(Sword,index,'KJV')
            key=SourceKey('Gen.1_1.1')
            self.assertEqual(key.getOSISRef(),'Gen.1_1.1')
            self.assertEqual(Sword.VerseKey.getOSISRef(key),'Gen.2.1')
            self.assertTrue(reader.module.hasEntry(key));reader.module.setKey(key)
            self.assertIn('SYNTHETIC SECOND SECTION',reader.module.stripText())
            copied=SourceKey(key);self.assertEqual(copied.getOSISRef(),'Gen.1_1.1')
            copied.setText('Genesis 2:1')
            self.assertEqual(copied.getOSISRef(),'Gen.2.1')
            self.assertEqual(Sword.VerseKey.getOSISRef(copied),'Gen.3.1')
            reader.module.setKey(copied)
            self.assertIn('SYNTHETIC CHAPTER TWO',reader.module.stripText())
            self.assertEqual(key.getOSISRef(),'Gen.1_1.1','Another query cannot change the original source context')
            for invalid in ('Gen.1_2.1','Gen.52.1','Gen.1_1.000','Unknown 1:1'):
                with self.assertRaises(ValueError):SourceKey(invalid)


if __name__=='__main__':unittest.main()
