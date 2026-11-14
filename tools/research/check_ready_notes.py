"""Actual note hosts with real installed excerpts; isolated synthetic personal notes."""
import argparse,hashlib,inspect,json,os,tempfile
from dataclasses import asdict
from pathlib import Path
from bible.ui import Application,Window,Library,Gtk
from bible.i18n import tr
from bible.notes import PassageLink
from bible.notes_window import NoteEditor
from tests.test_ui import spin
from tests.test_appearance import SystemStyleOverride
from tools.check_alpha_ui import X11Input
from tools.check_client_feedback import Screen


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('resources',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--require-packaged',action='store_true');a=p.parse_args()
    assert (a.resources/'.ready-batch-test-profile').is_file()
    if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    a.output.mkdir(parents=True,exist_ok=True);app=Application();app.register();native=X11Input();screen=Screen(native)
    report=dict(complete=False,app_import=inspect.getfile(Window),note_editor_sha256=hashlib.sha256(Path(inspect.getfile(NoteEditor)).read_bytes()).hexdigest(),gtk_version=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],language=os.environ.get('LANGUAGE'),captures=[],cases=[])
    try:
        for linked in (False,True):
            with tempfile.TemporaryDirectory(prefix='bible-note-hosts-') as directory:
                root=Path(directory);(root/'translations').symlink_to((a.resources/'translations').resolve(),target_is_directory=True)
                if (a.resources/'study-data').is_dir():(root/'study-data').symlink_to((a.resources/'study-data').resolve(),target_is_directory=True)
                w=Window(app,Library(root/'translations'));w.set_default_size(1280,900);w.present();spin();native.activate(w)
                try:
                    tab=w.active_tab;tab.navigate('FreSegond1910','Gen.18.16');spin(lambda:not tab._restoring_scroll)
                    system=tab.reader.versification
                    note=w.notes_store.save('**Personal observation**\n\nA synthetic personal note for interface validation.\n\nCompare John 3:16.',('Validation',),
                        versification=system,start='Gen.18.16',end='Gen.18.18',origin_translation='FreSegond1910',origin_language='fr',
                        links=(PassageLink(system,'John.3.16','John.3.16'),) if linked else ())
                    before=[asdict(n) for n in w.notes_store.all()]
                    def shot(name):
                        native.move_at(w,2,2);spin(duration=.2);filename=('linked-' if linked else 'unlinked-')+name+'.png'
                        screen.grab(a.output/filename);report['captures'].append(filename)
                    with SystemStyleOverride() as style:
                        for mode in ('day','night'):
                            style.set(dark=mode=='night',high=False);w.appearance.update('mode',mode)
                            for narrow in (False,True):
                                w.set_default_size(560 if narrow else 1280,750 if narrow else 900);spin()
                                prefix=mode+('-narrow' if narrow else '-wide')
                                w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes');w.study.notes.refresh(force=True);spin()
                                shot(prefix+'-summary');editor=w.study.notes.open_note(note);spin();shot(prefix+'-inline')
                                expand=w.study.notes.editor_commands.get_first_child()
                                while expand and expand.get_tooltip_text()!=tr('Expand note'):expand=expand.get_next_sibling()
                                assert expand is not None
                                buffer=editor.body.get_buffer();expand.grab_focus();native.key('space');spin()
                                assert not editor.embedded and editor.body.get_buffer() is buffer
                                shot(prefix+'-expanded');editor.close();spin()
                                editor=NoteEditor(w,note=note);w.note_editor=editor
                                if narrow:editor.set_default_size(360,600)
                                editor.present();spin();shot(prefix+'-quick');editor.close();spin()
                                w.open_notes();spin();w.notes_space.open_note(note);spin();shot(prefix+'-workspace');w.notes_space.leave();spin()
                    assert [asdict(n) for n in w.notes_store.all()]==before
                    report['cases'].append(dict(linked=linked,notes_unchanged=True,expanded_buffer_preserved=True))
                finally:
                    if w.note_editor and not w.note_editor.closed:w.note_editor.close();spin()
                    w.close();spin()
        report['complete']=True
    finally:
        native.close();(a.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
