"""Resource evidence is distinct from mathematical native canon transforms."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK/SWORD')
class ResourceAlignmentTests(unittest.TestCase):
    def test_existing_verified_native_conversion_convention_remains_usable(self):
        import json
        from bible.sword_provider import Reader
        from tests.test_ui import installed_fixture
        with tempfile.TemporaryDirectory() as directory:
            root=installed_fixture(directory,'YV1')
            conf=root/'mods.d/test.conf';conf.write_text(conf.read_text()+'BibleSource=YouVersion\n')
            proof=dict(all_text_notes_headings_verified=True,source_numbering='eng',storage_numbering='KJV')
            receipt=root/'.verified.json';receipt.write_text(json.dumps(proof))
            self.assertTrue(Reader(root,'youversion~YV1').can_align_reference('Gen.1.1'))
            for changed in ({'all_text_notes_headings_verified':False},{'source_numbering':'org'},{'storage_numbering':'NRSV'}):
                receipt.write_text(json.dumps({**proof,**changed}))
                self.assertFalse(Reader(root,'youversion~YV1').can_align_reference('Gen.1.1'))

    def test_same_registry_name_does_not_prove_edition_numbering(self):
        from bible.sword_provider import Reader
        from bible.reference_resolution import resolve_readers,VersificationMismatch
        from tests.test_ui import installed_fixture
        with tempfile.TemporaryDirectory() as directory:
            for name in ('ActualSource','OtherSource'):
                installed_fixture(directory,name,versification='NRSV')
            root=Path(directory)/'translations'
            left=Reader(root/'ActualSource','ActualSource');right=Reader(root/'OtherSource','OtherSource')
            for source,target in ((left,right),(right,left)):
                with self.assertRaises(VersificationMismatch):resolve_readers('Gen.1.1',source,target)
            self.assertEqual(resolve_readers('Gen.1.1',left,left).start,'Gen.1.1')

    def test_capability_is_checked_on_both_sides_before_claiming_absence(self):
        from bible.sword_provider import Reader
        from bible.reference_resolution import resolve_readers,VersificationMismatch
        from tests.test_ui import installed_fixture
        with tempfile.TemporaryDirectory() as directory:
            installed_fixture(directory,'Source',versification='NRSV',entries=[('Eccl.12.1','SOURCE SENTINEL')])
            installed_fixture(directory,'Target',versification='Segond',entries=[('Eccl.12.3','TARGET SENTINEL')])
            root=Path(directory)/'translations'
            a=Reader(root/'Source','Source');b=Reader(root/'Target','Target')
            with patch.object(a,'can_align_reference',return_value=True):
                with self.assertRaises(VersificationMismatch):resolve_readers('Eccl.12.1',a,b)
                with patch.object(b,'can_align_reference',return_value=True):
                    self.assertEqual(resolve_readers('Eccl.12.1',a,b).start,'Eccl.12.3')
                    self.assertEqual(resolve_readers('Eccl.12.3',b,a).start,'Eccl.12.1')

    def test_independent_panes_preserve_all_entries_and_do_not_follow_in_either_direction(self):
        from bible.ui import Application,Window,Library
        from tests.test_ui import installed_fixture,spin
        app=Application.get_default() or Application();app.register()
        with tempfile.TemporaryDirectory() as directory:
            for name,system,count in (('Source','NRSV',14),('Target','Segond',16)):
                installed_fixture(directory,name,versification=system,entries=[(f'Eccl.12.{n}',f'{name} SENTINEL{n} '*12) for n in range(1,count+1)])
            w=Window(app,Library(Path(directory)/'translations'));w.present()
            try:
                tab=w.active_tab
                for left,right in (('Source','Target'),('Target','Source')):
                    tab.navigate(left,'Eccl.12.1');tab.state.comparison=right;w.sync_comparison()
                    spin(lambda:not tab._restoring_scroll and not tab._comparison_positioning)
                    self.assertFalse(getattr(tab,'_shared_comparison',False));self.assertFalse(tab._comparison_aligned)
                    for reader,doc in ((tab.reader,tab._document),(tab._comparison_reader,tab._comparison_document)):
                        self.assertEqual({r for span in doc.spans for r in span.members},set(dict(reader.chapter('Eccl.12.1').verses)))
                        self.assertNotIn('No verse in this edition',doc.text)
                    before=(tab.state.reference,tab.comparison_reference)
                    for side in ('primary','comparison'):
                        tab.comparison_sync.intent(side);tab.comparison_sync.synchronize()
                        self.assertEqual((tab.state.reference,tab.comparison_reference),before)
            finally:w.close()
