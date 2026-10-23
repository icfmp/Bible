"""Synthetic-only GTK place flow; real geography is checked separately."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from tests.test_ui import installed_fixture,spin,close_test_dialogs
from tests.test_place_data import inputs,pins
from bible import place_data


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class PlaceCardTests(unittest.TestCase):
    def setUp(self):
        from bible.ui import Application,Window,Library
        self.directory=self.enterContext(tempfile.TemporaryDirectory());self.root=Path(self.directory)
        installed_fixture(self.directory,'French',versification='Segond',entries=[('Ps.3.2','EXACT FRENCH PSALM TEST'),('John.1.5','SOURCE TEST')])
        self.files=inputs(self.root)
        record=json.loads(self.files['ancient'].read_text());record['verses']=[{'osis':'Ps.3.1'}]
        self.files['ancient'].write_text(json.dumps(record)+'\n')
        self.app=Application.get_default() or Application();self.app.register()
        self.window=Window(self.app,Library(self.root/'translations'));self.window.set_default_size(1200,900);self.window.present()
        self.window.active_tab.navigate('French','Ps.3.2');spin(lambda:not self.window.active_tab._restoring_scroll,duration=.2)

    def tearDown(self):
        close_test_dialogs()
        if self.window.catalogue_window and not self.window.catalogue_window.closed:self.window.catalogue_window.close()
        if getattr(self.window,'place_dialog',None):self.window.place_dialog.close();spin()
        self.window.close()

    def install(self):
        store=place_data.PlaceData(self.root/'study-data')
        with patch.object(place_data,'FILES',pins(self.files)):store.install_files(self.files)
        return store

    def test_local_card_and_mapped_preview_keep_reader_until_explicit_new_tab(self):
        w=self.window;self.install();before=(w.active_tab.state.reference,list(w.active_tab.state.history),w.view.get_n_pages())
        dialog=w.open_places();spin(lambda:not dialog.pending,duration=.2)
        self.assertEqual([p['name'] for p in dialog.rows],['Jerusalem'])
        dialog.open_place(dialog.rows[0]);spin(lambda:bool(dialog.map_widget.lines),duration=.2)
        self.assertEqual(dialog.current_place['status'],'known')
        button=next(x for x in self.walk(dialog.references) if hasattr(x,'_reference'))
        button.emit('clicked');spin()
        self.assertEqual(w.reference_preview.target,('French','Ps.3.2'))
        self.assertEqual(w.reference_preview.body.get_buffer().props.text,'EXACT FRENCH PSALM TEST')
        self.assertEqual((w.active_tab.state.reference,w.active_tab.state.history,w.view.get_n_pages()),before)
        w.reference_preview.open_new.emit('clicked');spin()
        self.assertEqual(w.view.get_n_pages(),before[2]+1)
        self.assertEqual(w.active_tab.state.resource,'French');self.assertEqual(w.active_tab.state.reference,'Ps.3.2')
        self.assertEqual((w.tabs()[0].state.reference,w.tabs()[0].state.history),before[:2])

    def walk(self,widget):
        yield widget
        child=widget.get_first_child()
        while child:yield from self.walk(child);child=child.get_next_sibling()

    def test_map_failure_keeps_card_coordinates_and_related_references(self):
        store=self.install()
        with sqlite3.connect(store.path) as connection:connection.execute('DROP TABLE coastlines')
        dialog=self.window.open_places();spin(lambda:not dialog.pending,duration=.2)
        dialog.open_place(dialog.rows[0]);spin(lambda:not dialog.map_widget.get_visible(),duration=.2)
        self.assertTrue(dialog.current_place['candidates']);self.assertEqual(dialog.reference_model.get_n_items(),1)
        self.assertEqual(self.window.active_tab.state.reference,'Ps.3.2')

    def test_missing_data_opens_the_same_library_resource_and_install_does_not_change_bibles(self):
        from bible.study_resources import PLACE_RESOURCE_ID
        w=self.window;before=w.library.installed();dialog=w.open_places();spin()
        self.assertTrue(dialog.download.get_visible())
        with patch('bible.catalogue_window.catalogue',side_effect=AssertionError('No SWORD refresh for place data')):
            dialog.open_library();library=w.catalogue_window;spin()
            self.assertEqual(library.selected_resource().id,PLACE_RESOURCE_ID)
            self.assertFalse(library._catalogue_requested)
            self.assertIn('opendatacommons.org',library.metadata.get_text())
            self.install();w.resource_installed(PLACE_RESOURCE_ID);library.filter_resources()
            spin(lambda:not dialog.pending,duration=.2)
            self.assertTrue(dialog.rows);self.assertEqual(w.library.installed(),before)
            self.assertNotIn(PLACE_RESOURCE_ID,w.library.installed('bible'))
