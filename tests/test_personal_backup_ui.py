"""Native regression coverage for the October desktop finishing batch."""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_ui import spin,installed_fixture
from bible.i18n import tr

@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class PersonalBackupUITests(unittest.TestCase):
    def setUp(self):
        from bible.ui import Application,Window,Library
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()));installed_fixture(self.root,long_text=True)
        self.app=Application.get_default() or Application();self.app.register()
        self.window=Window(self.app,Library(self.root/'translations'));self.window.present();spin()
    def tearDown(self):self.window.close()

    def test_backup_native_cancel_and_declined_merge_leave_annotations_unchanged(self):
        from bible.application_surfaces import choose_personal_backup
        from bible import personal_backup
        from bible.ui import Gtk,Gio
        from tests.test_notes import create
        # Construct the real native chooser and exercise its response boundary.
        # Do not synthesize portal replies while an IPC request is outstanding.
        self.enterContext(patch.object(Gtk.NativeDialog,'show',return_value=None))
        w=self.window;create(w.notes_store);w.highlights.set('KJV',['Gen.1.1'],'yellow','Test')
        before=personal_backup.snapshot(w.notes_store,w.highlights);status=Gtk.Label()
        choose_personal_backup(w,status,False);chooser=w._personal_backup_chooser
        self.assertIsInstance(chooser,Gtk.FileChooserNative)
        chooser.emit('response',Gtk.ResponseType.CANCEL);self.assertIsNone(w._personal_backup_chooser)
        self.assertEqual(personal_backup.snapshot(w.notes_store,w.highlights),before)
        path=self.root/'incoming.json';personal_backup.export(w.notes_store,w.highlights,path)
        def decline(owner,heading,body,accepted,*args):return None
        with patch('bible.notes_window.message',side_effect=decline) as confirm:
            choose_personal_backup(w,status,True);chooser=w._personal_backup_chooser
            chooser.set_file(Gio.File.new_for_path(str(path)));spin()
            chooser.emit('response',Gtk.ResponseType.ACCEPT);self.assertEqual(confirm.call_count,1)
        self.assertEqual(personal_backup.snapshot(w.notes_store,w.highlights),before)
        self.assertFalse((self.root/'backups').exists())

