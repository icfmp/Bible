"""Actual pointer actions on the installed baseline; disposable profile only."""
import argparse,inspect,json,sys,traceback
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('profile',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    from bible.library import Library,catalogue
    from bible.ui import Application,Window,Gtk
    from tests.test_ui import spin
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    assert inspect.getfile(Window).startswith('/app/')
    lib=Library(a.profile/'translations');resources=catalogue()
    for name in ['KJV','FreSegond1910']:
        if name not in lib.installed():lib.install(next(r for r in resources if r.name==name))
    a.output.mkdir(parents=True,exist_ok=True);errors=[]
    def error(kind,value,tb):
        errors.append(dict(type=kind.__name__,message=str(value),frames=[dict(function=f.name,file=Path(f.filename).name,line=f.lineno) for f in traceback.extract_tb(tb)]))
        traceback.print_exception(kind,value,tb)
    sys.excepthook=error
    app=Application();app.register();w=Window(app,lib);w.set_default_size(1280,900);w.present();spin()
    n=X11Input();n.activate(w);screen=Screen(n);t=w.active_tab;actions=w.passage_actions
    report=dict(source=inspect.getfile(Window),gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],renderer=type(w.get_renderer()).__name__,cases=[],exceptions=errors)
    def save(): (a.output/'diagnosis.json').write_text(json.dumps(report,indent=2))
    try:
        for resource,multiple in [('KJV',False),('KJV',True),('FreSegond1910',False)]+[('youversion~YV21',i%2==0) for i in range(12)]+[('KJV',False) for i in range(12)]:
            if resource.startswith('youversion') and resource not in lib.installed():
                from bible.youversion_install import fetch_resource,acknowledgement
                from bible.step_data import StepData
                r=fetch_resource(21);lib.install(r,permission=acknowledgement(r));StepData(a.profile/'study-data').install()
            t.navigate(resource,'John.1.1');spin(lambda:not t._restoring_scroll)
            b=t.text.get_buffer();start=t._marker_ends['John.1.1']+1;end=t._marker_ends['John.1.2']+12 if multiple else start+2
            if resource=='KJV' and not multiple:
                txt=b.get_text(b.get_start_iter(),b.get_end_iter(),False);start=txt.index('beginning',start);end=start+len('beginning')
            b.select_range(b.get_iter_at_offset(start),b.get_iter_at_offset(end));t.text.grab_focus()
            actions.capture(t.text,lambda:actions.ordinary(t),None);spin()
            case=dict(resource=resource,multiple=multiple,before_toolbar=actions.bar.get_visible(),before_exceptions=len(errors));report['cases'].append(case);save()
            screen.grab(a.output/(resource+('-multi' if multiple else '-single')+'-before.png'))
            n.click(actions.word_button);spin(duration=.6)
            case.update(after_offer=bool(w.study.words.popover),after_exceptions=len(errors));save();pop=w.study.words.popover
            if pop:
                screen.grab(a.output/(resource+('-multi' if multiple else '-single')+'-offer.png'))
                n.click(pop.get_child().get_child().get_last_child());spin(duration=.8)
                case.update(after_open=True,after_open_exceptions=len(errors));save();w.study.words.leave();spin()
            actions.dismiss()
        report['status']='completed';save()
    finally:w.close();n.close();save()
if __name__=='__main__':main()
