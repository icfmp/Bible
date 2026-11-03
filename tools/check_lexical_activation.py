"""Actual installed pointer activation of proven OSIS lexical units."""
import argparse,hashlib,inspect,json,sys,traceback
from pathlib import Path
from unittest.mock import patch


def main():
    p=argparse.ArgumentParser();p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--prepare',action='store_true');p.add_argument('--baseline',action='store_true');p.add_argument('--require-packaged',action='store_true');a=p.parse_args()
    from bible.ui import Application,Window,Library
    from bible.library import catalogue
    from bible.youversion_install import fetch_resource,acknowledgement
    from bible.step_data import StepData
    from bible.word_metadata import selected_metadata
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    from tests.test_ui import spin,close_test_dialogs
    if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    marker=a.profile/'.selection-batch-profile'
    if a.prepare:
        if a.profile.exists() and not marker.exists():raise ValueError('Existing unmarked profile refused')
        a.profile.mkdir(parents=True,exist_ok=True);marker.write_text('Disposable selection batch proof\n')
    assert marker.is_file()
    lib=Library(a.profile/'translations')
    if a.prepare:
        if 'KJV' not in lib.installed():lib.install(next(r for r in catalogue() if r.name=='KJV'))
        if 'youversion~YV21' not in lib.installed():
            r=fetch_resource(21);lib.install(r,permission=acknowledgement(r))
        if StepData(a.profile/'study-data').revision is None:StepData(a.profile/'study-data').install()
    a.output.mkdir(parents=True,exist_ok=True)
    report=dict(source=inspect.getfile(Window),baseline=a.baseline,cases=[],exceptions=[])
    def save():(a.output/'lexical-verification.json').write_text(json.dumps(report,indent=2))
    def exception(kind,value,tb):
        report['exceptions'].append(dict(type=kind.__name__,functions=[r.name for r in traceback.extract_tb(tb)]));save();traceback.print_exception(kind,value,tb)
    sys.excepthook=exception
    app=Application.get_default() or Application();app.register()
    data=a.profile/'study-data/step-word-study.sqlite3';retained=data.with_suffix('.retained')
    original=hashlib.sha256(data.read_bytes()).hexdigest()
    for absent in (False,True):
        if absent:data.rename(retained)
        try:
            with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):w=Window(app,lib)
            w.set_default_size(1280,850);w.present();spin();n=X11Input();n.activate(w);screen=Screen(n);t=w.active_tab;actions=w.passage_actions
            try:
                cases=[('KJV','was',False),('KJV','the Word',False),('KJV','the beginning',False),('KJV','beginning',False),('KJV',None,True),('youversion~YV21','commencement',False)]+[('KJV','was',False)]*6
                for index,(resource,word,multi) in enumerate(cases):
                    w.study_button.set_active(False);assert t.navigate(resource,'John.1.1');spin(lambda:not t._restoring_scroll,duration=.2)
                    b=t.text.get_buffer();body=b.get_text(b.get_start_iter(),b.get_end_iter(),False);start=t._marker_ends['John.1.1']
                    start=body.index(word,start) if word else start+1;end=t._marker_ends['John.1.2']+8 if multi else start+len(word)
                    b.select_range(b.get_iter_at_offset(start),b.get_iter_at_offset(end));t.text.grab_focus();actions.capture(t.text,lambda:actions.ordinary(t),None);spin()
                    metadata=selected_metadata(actions.target)
                    case=dict(resource=resource,selected_unit=word or 'multiple verses',missing_step=absent,identifiers=list(metadata['identifiers']) if metadata else [],phase='before-pointer');report['cases'].append(case);save()
                    if resource=='KJV' and word in ('was','the Word','the beginning'):assert metadata,case
                    if multi or resource.startswith('youversion') or word=='beginning':assert metadata is None,case
                    n.click(actions.word_button);spin(duration=.3);words=w.study.words
                    case['phase']='after-toolbar-pointer';save()
                    if a.baseline:
                        assert words.popover;pop=words.popover;n.click(pop.get_child().get_child().get_last_child())
                    spin(lambda:not words.pending,duration=.25,timeout=90)
                    case['phase']='detail-visible';case['data_unavailable']=words.data.revision is None;save()
                    if index<6:screen.grab(a.output/(('missing-' if absent else 'present-')+str(index)+'.png'))
                    if not a.baseline:assert words.dialog and words.dialog.get_visible()
                    words.leave();spin(duration=.2);w.study_button.set_active(False);actions.dismiss();case['phase']='closed';save()
                assert not report['exceptions']
            finally:w.close();close_test_dialogs();spin();n.close();save()
        finally:
            if absent:
                assert not data.exists();retained.rename(data)
    assert hashlib.sha256(data.read_bytes()).hexdigest()==original
    report.update(result='PASS',step_data_restored=True);save()


if __name__=='__main__':main()
