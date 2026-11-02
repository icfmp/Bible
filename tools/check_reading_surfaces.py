"""Real ordinary/comparison/immersion and RTL rendering in a marked test profile."""
import argparse,hashlib,inspect,io,json
from pathlib import Path
from unittest.mock import patch


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--baseline',action='store_true');p.add_argument('--require-packaged',action='store_true');p.add_argument('--prepare',action='store_true');a=p.parse_args()
    assert (a.profile/'.source-rendering-research').is_file();a.output.mkdir(parents=True,exist_ok=True)
    from bible.ui import Application,Window,Library,Gtk
    from tests.test_ui import spin
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    library=Library(a.profile/'translations')
    if a.prepare and 'youversion~YV13' not in library.installed():
        from bible.library import download
        from bible.youversion_editions import METADATA_URL
        from bible.youversion_install import resource_from_metadata,acknowledgement
        received=io.BytesIO();download(METADATA_URL.format(edition=13),received,limit=2*1024*1024,same_origin=True)
        resource=resource_from_metadata(json.loads(received.getvalue()),13)
        library.install(resource,permission=acknowledgement(resource))
    def hashes():return {str(f.relative_to(library.root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in library.root.rglob('*') if f.is_file()}
    before=hashes();app=Application.get_default() or Application();app.register();records=[]
    with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False),patch('bible.catalogue_session.CatalogueSession.load_youversion_language',return_value=None):
        w=Window(app,library);w.set_default_size(1200,820);w.present();n=X11Input();n.activate(w);screen=Screen(n)
        try:
            w.appearance.update('size',20);w.appearance.update('line_spacing','normal');t=w.active_tab
            with SystemStyleOverride() as style:
                for dark in (False,True):
                    style.set(dark=dark,high=False);w.appearance.update('mode','night' if dark else 'day');w.appearance.update('night_palette' if dark else 'day_palette','dark' if dark else 'white')
                    for resource,ref in [('ebible~fraLSG1910eb','Ps.13.1'),('youversion~YV13','Ps.13.1')]:
                        t.state.comparison=None;w.sync_comparison();w.study_button.set_active(False);t.navigate(resource,ref);spin(lambda:not t._restoring_scroll,duration=.3)
                        # Rendered source text/offsets are checked by the ordinary reader
                        # and shared pagination model; image glyph layout is native GTK.
                        assert t.text.get_direction()==(Gtk.TextDirection.RTL if t.reader.rtl else Gtk.TextDirection.LTR)
                        t.state.comparison='FreSegond1910';w.sync_comparison();spin(lambda:not t._restoring_scroll and not getattr(t,'_comparison_positioning',False),duration=.4,timeout=90)
                        screen.grab(a.output/(f'{"dark" if dark else "light"}-{resource}-comparison.png'))
                        records.append(dict(surface='comparison',resource=resource,reference=t.state.reference,rtl=t.reader.rtl,body_sha256=hashlib.sha256(t._document.text.encode()).hexdigest()))
                        t.state.comparison=None;w.sync_comparison();spin(lambda:not t._restoring_scroll)
                        assert w.enter_immersion('bible'),(resource,ref)
                        spin(lambda:w.immersion and w.immersion.stream.cursor is not None,duration=.4,timeout=90)
                        screen.grab(a.output/(f'{"dark" if dark else "light"}-{resource}-immersion.png'))
                        immersion=w.immersion
                        assert immersion.source.rtl==t.reader.rtl
                        records.append(dict(surface='bible-immersion',resource=resource,reference=t.state.reference,rtl=t.reader.rtl))
                        w.leave_immersion();spin(lambda:w.immersion is None and not t._restoring_scroll)
                        assert t.state.resource==resource
                    t.navigate('FreSegond1910','Gen.1.1');w.study_button.set_active(True);s=w.study;s.tools.set_visible_child_name('commentaries');s.refresh(force=True);s.choices.set_selected(s.names.index('MHC'));spin(lambda:not s._positioning,duration=.4)
                    position=s.current_position;assert position is not None
                    w.enter_immersion('commentary');spin(lambda:w.immersion and w.immersion.stream.cursor is not None,duration=.4,timeout=90)
                    screen.grab(a.output/(f'{"dark" if dark else "light"}-MHC-immersion.png'))
                    assert w.immersion.source.reader.name=='MHC'
                    records.append(dict(surface='commentary-immersion',resource='MHC',position=position))
                    w.leave_immersion();spin(lambda:w.immersion is None)
                    assert t.state.reference=='Gen.1.1'
        finally:w.close();n.close()
    assert before==hashes(),'Source files changed'
    (a.output/'verification.json').write_text(json.dumps(dict(app_import=inspect.getfile(Window),baseline=a.baseline,gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],cases=records,unchanged_resource_files=len(before)),ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
