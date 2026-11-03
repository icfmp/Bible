"""Read the actual GUI-installed NBS offline; aggregate checks only."""
import inspect,json,hashlib,sys
from pathlib import Path
from bible.ui import Application,Window,Library
from bible.sword_provider import Reader
from tests.test_ui import spin,close_test_dialogs


def main():
    root=Path(sys.argv[1]);out=Path(sys.argv[2]);assert (root/'.selection-batch-profile').is_file()
    assert inspect.getfile(Window).startswith('/app/')
    assert len(Path('/proc/net/route').read_text().splitlines())<=1,'Network remains shared'
    library=Library(root/'translations');name='youversion~YV104';assert name in library.installed()
    content=library.root/name;receipt=json.loads((content/'.verified.json').read_text())
    assert receipt['all_text_notes_headings_verified'] and receipt['entries']==1245
    def snapshot():return {str(p.relative_to(library.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in library.root.rglob('*') if p.is_file()}
    before=snapshot();app=Application();app.register();w=Window(app,library);w.set_default_size(1100,800);w.present();spin()
    try:
        t=w.active_tab;w.study_button.set_active(False);checks=[]
        for ref in ('Gen.1.1','Num.1.1','Judg.1.1','Ps.119.1','Rev.22.21'):
            assert t.navigate(name,ref);spin(lambda:not t._restoring_scroll,duration=.2)
            assert t._document.spans and t.text.get_buffer().get_char_count()>100
            assert t.reader.module.getConfigEntry('Abbreviation')=='NBS'
            checks.append(dict(reference=ref,rendered=True))
        assert t.reader.introduction('Gen') is not None
        assert snapshot()==before
        out.write_text(json.dumps(dict(result='PASS',source=inspect.getfile(Window),edition=104,offline=True,reopened_after_actual_library_install=True,all_worker_entries_verified=receipt['entries'],samples=checks,existing_resource_files_unchanged=len(before)),indent=2))
    finally:w.close();close_test_dialogs();spin()


if __name__=='__main__':main()
