"""Installed metadata refresh must retain native resource-row identities."""
import os,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
from tests.test_ui import installed_fixture,spin


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires native GTK')
class LibraryPositionTests(unittest.TestCase):
    def test_metadata_status_refresh_does_not_rebuild_or_move_bible_or_commentary_rows(self):
        from bible.ui import Application,Window,Library
        from bible.library import Resource
        app=Application.get_default() or Application();app.register()
        for kind in ('bible','commentary'):
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as directory,patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False),patch('bible.catalogue_session.CatalogueSession.load_youversion_language',return_value=None):
                root=Path(directory);installed_fixture(root);w=Window(app,Library(root/'translations'));w.present();spin()
                try:
                    w.application_settings.set('library_language','');d=w.open_library()
                    spin(lambda:not d.preparing,duration=.3)
                    d.resources=[Resource('R'+str(i),f'Resource {i:04}','fr','Public Domain',
                        category='Commentaries' if kind=='commentary' else 'Biblical Texts') for i in range(200)]
                    d._installed_metadata={};d._language_records={'fr':('French','French','french')};d._search_terms={};d.language_choice=''
                    d.kind.set_selected(1 if kind=='commentary' else 0);d.update_languages()
                    spin(lambda:not d._building_rows,duration=1)
                    a=d.list_scroll.get_vadjustment();self.assertGreater(a.get_upper(),a.get_page_size()*3)
                    a.set_value(a.get_upper()*.6);spin(duration=.3);before=a.get_value()
                    items=[d.choice_model.get_item(i) for i in range(200)];changes=[]
                    d.choice_model.connect('items-changed',lambda _,p,r,a:changes.append((p,r,a)))
                    d._installed_metadata={d.resources[120].id:replace(d.resources[120],description='Verified installed attribution')}
                    d.filter_resources();spin(duration=.4)
                    self.assertEqual(changes,[])
                    self.assertEqual(items,[d.choice_model.get_item(i) for i in range(200)])
                    self.assertAlmostEqual(a.get_value(),before,delta=2)
                    self.assertEqual(d.filtered_resources[120].description,'Verified installed attribution')
                    d.search.set_text('Resource 01');d.filter_resources();spin(lambda:not d._building_rows,duration=.3)
                    self.assertTrue(d.filtered_resources);self.assertLess(len(d.filtered_resources),200)
                finally:
                    if w.catalogue_window and not w.catalogue_window.closed:w.catalogue_window.close()
                    w.close();spin()
