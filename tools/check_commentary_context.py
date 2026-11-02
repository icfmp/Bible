"""Actual Psalm title/verse mapping in a marked disposable resource profile."""
import argparse,hashlib,inspect,json
from pathlib import Path
from unittest.mock import patch


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--require-packaged',action='store_true');p.add_argument('--baseline',action='store_true');a=p.parse_args()
    assert (a.profile/'.source-rendering-research').is_file();a.output.mkdir(parents=True,exist_ok=True)
    from bible.ui import Application,Window,Library,Gtk
    from tests.test_ui import spin
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    def digests():return {str(f.relative_to(a.profile)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((a.profile/'translations').rglob('*')) if f.is_file()}
    before=digests();app=Application.get_default() or Application();app.register();records=[]
    with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False),patch('bible.catalogue_session.CatalogueSession.load_youversion_language',return_value=None):
        w=Window(app,Library(a.profile/'translations'));w.set_default_size(1200,820);w.present();n=X11Input();n.activate(w);screen=Screen(n)
        try:
            t=w.active_tab;t.state.comparison=None;w.sync_comparison();w.appearance.update('size',20)
            with SystemStyleOverride() as style:
                for dark in (False,True):
                    style.set(dark=dark,high=False);w.appearance.update('mode','night' if dark else 'day')
                    for module,refs in [('ebible~francl2022eb',['Ps.17.1','Ps.17.2','Ps.17.1','Gen.2.1']),('FreSegond1910',['Ps.17.1'])]:
                        for i,ref in enumerate(refs):
                            t.navigate(module,ref);w.study_button.set_active(True);s=w.study
                            s.tools.set_visible_child_name('commentaries');s.refresh(force=True);s.choices.set_selected(s.names.index('MHC'))
                            spin(lambda:not t._restoring_scroll and not s._positioning,duration=.4)
                            section=s.reader.index.sections[s.current_position] if s.current_position is not None else None
                            row=dict(module=module,reference=t.state.reference,status=s.status.get_text(),intro_contexts=getattr(s,'alignment_introductions',()),section=section.start if section else None,section_is_intro=bool(section and section.introduction),bible_spans=len(t._document.spans))
                            expected={r for r,_ in t.reader.chapter(ref).unique_verses()}
                            assert expected=={span.reference for span in t._document.spans},row
                            if not a.baseline:
                                assert section is not None,row
                                assert t.state.reference==ref,row
                                if module=='ebible~francl2022eb' and ref=='Ps.17.1':
                                    assert row['section_is_intro'] and row['intro_contexts']==('Ps.17.0',),row
                                    assert any(not s.reader.index.sections[pos].introduction for pos in s.loaded)
                                else:assert not row['intro_contexts'],row
                                assert 'Invalid reference' not in row['status'],row
                            case=f'{"dark" if dark else "light"}-{module}-{ref}-{i}'
                            screen.grab(a.output/(case+'.png'));records.append(row)
                    t.navigate('ebible~francl2022eb','Ps.17.1');spin(lambda:not t._restoring_scroll and not s._positioning)
                    w.study_button.set_active(False);w.study_button.set_active(True);spin(lambda:not s._positioning)
                    assert t.state.reference=='Ps.17.1'
        finally:w.close();n.close()
        if not a.baseline:
            with patch('urllib.request.urlopen',side_effect=AssertionError('Offline restart')):
                w=Window(app,Library(a.profile/'translations'));w.present()
                try:
                    spin(lambda:not w.active_tab._restoring_scroll and not w.study._positioning)
                    assert w.active_tab.state.reference=='Ps.17.1'
                    assert w.study.current_position is not None,w.study.status.get_text()
                finally:w.close()
    assert before==digests(),'Source resources changed'
    (a.output/'verification.json').write_text(json.dumps(dict(app_import=inspect.getfile(Window),baseline=a.baseline,gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],cases=records,resource_files_unchanged=len(before),offline_restart=not a.baseline),ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
