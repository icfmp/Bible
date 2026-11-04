"""Native input regression probes for #151/#168; no app mutation or corpus export."""
import argparse,faulthandler,hashlib,inspect,json,subprocess,sys,traceback
from pathlib import Path
from unittest.mock import patch

def walk(widget):
    yield widget
    child=widget.get_first_child()
    while child:
        yield from walk(child);child=child.get_next_sibling()

def main():
    faulthandler.enable()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--baseline-captures',action='store_true');p.add_argument('--prepare',action='store_true');p.add_argument('--require-packaged',action='store_true')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    marker=args.profile/'.ready-word-selection-profile'
    if args.prepare:
        assert not args.profile.exists() or marker.exists(),'Unmarked profile'
        args.profile.mkdir(parents=True,exist_ok=True);marker.write_text('Disposable native input diagnostic\n')
        from bible.library import Library,catalogue
        from bible.youversion_install import fetch_resource,acknowledgement
        from bible.step_data import StepData
        lib=Library(args.profile/'translations')
        resources=catalogue()
        for name in ('KJV','Wesley'):
            if name not in lib.installed():lib.install(next(r for r in resources if r.name==name))
        if 'youversion~YV21' not in lib.installed():
            item=fetch_resource(21);lib.install(item,permission=acknowledgement(item))
        data=StepData(args.profile/'study-data')
        if data.revision is None:data.install()
    assert marker.is_file()
    from bible.ui import Application,Window,Library,Gtk
    from tests.test_ui import spin
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    exceptions=[]
    def exception(kind,value,tb):
        exceptions.append(dict(type=kind.__name__,functions=[f.name for f in traceback.extract_tb(tb)]))
        traceback.print_exception(kind,value,tb)
    sys.excepthook=exception
    app=Application.get_default() or Application();app.register()
    with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):
        w=Window(app,Library(args.profile/'translations'));w.set_default_size(1280,900);w.present();spin()
    n=X11Input();n.activate(w);screen=Screen(n);t=w.active_tab;a=w.passage_actions
    report=dict(app_import=inspect.getfile(Window),ui_sha256=hashlib.sha256(Path(inspect.getfile(Window)).read_bytes()).hexdigest(),gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],renderer=type(w.get_renderer()).__name__,word_cycles=[],selection_cycles=[],exceptions=exceptions)
    if args.require_packaged:assert 'GL' in report['renderer']
    def save(): (args.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    def settled():spin(lambda:not t._restoring_scroll,duration=.2,timeout=60)
    def select(start,end):
        a.dismiss();spin(duration=.05);b=t.text.get_buffer()
        first=t.text.get_iter_location(b.get_iter_at_offset(start));last=t.text.get_iter_location(b.get_iter_at_offset(end))
        x,y=t.text.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,first.x,first.y+first.height//2)
        ex,ey=t.text.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,last.x,last.y+last.height//2)
        n.move_at(t.text,x,y);n.xtest.XTestFakeButtonEvent(n.display,1,True,0);n.x11.XFlush(n.display);spin(duration=.04)
        for i in range(1,7):n.move_at(t.text,x+(ex-x)*i/6,y+(ey-y)*i/6);spin(duration=.018)
        n.xtest.XTestFakeButtonEvent(n.display,1,False,0);n.x11.XFlush(n.display);spin(duration=.22)
        bounds=tuple(i.get_offset() for i in b.get_selection_bounds())
        return dict(expected=[start,end],actual=bounds,visible=a.bar.get_visible(),dragging=a.dragging,capture_pending=bool(a.capture_idle))
    save()
    recorder=None
    def immersion_captures():
        from tests.test_appearance import SystemStyleOverride
        t.state.comparison=None;w.sync_comparison();assert t.navigate('KJV','John.1.1');settled()
        t.state.commentary='Wesley';w.study.tools.set_visible_child_name('commentaries')
        w.study_button.set_active(True);w.study.refresh(force=True)
        spin(lambda:bool(w.study.loaded) and not w.study._positioning,duration=.2,timeout=60)
        with SystemStyleOverride() as style:
            for dark in (False,True):
                style.set(dark=dark,high=False);spin(duration=.2)
                for width in (1200,360):
                    w.set_default_size(width,820);spin(duration=.3)
                    for kind in ('bible','commentary'):
                        assert w.enter_immersion(kind)
                        spin(lambda:w.immersion and w.immersion.layout_ready,duration=.3,timeout=60)
                        if not args.baseline_captures:assert not hasattr(w.immersion,'notification_help')
                        screen.grab(args.output/(('dark' if dark else 'light')+'-'+str(width)+'-'+kind+'-immersion.png'))
                        w.leave_immersion();spin(lambda:not w.study._positioning,duration=.2)
        w.set_default_size(1280,900);w.study_button.set_active(False);spin(duration=.3)
    try:
        if args.baseline_captures:
            immersion_captures();report['baseline_captures']=True;report['completed']=True;save();return
        t.state.comparison=None;w.sync_comparison()
        for cycle in range(12):
            w.study_button.set_active(cycle%2==1)
            assert t.navigate('youversion~YV21','Mark.11.29');settled()
            result=select(t._marker_ends['Mark.11.29']+1,t._marker_ends['Mark.11.30']+15)
            assert result['visible'],result
            refs=a.target.references;assert refs==('Mark.11.29','Mark.11.30'),refs
            n.click(a.word_button);spin(duration=.25);words=w.study.words
            assert words.dialog and words.dialog.get_visible()
            choices=[v for v in words.children() if isinstance(v,Gtk.Button)]
            assert len(choices)==2,len(choices)
            n.click(choices[cycle%2]);spin(lambda:not words.pending,duration=.2,timeout=60)
            tokens=[v for v in words.children() if isinstance(v,Gtk.Button)]
            assert tokens
            report['last_stage']={'cycle':cycle,'phase':'original-token-click'};save()
            n.click(tokens[cycle%len(tokens)]);spin(lambda:not words.pending,duration=.2,timeout=60)
            further=[v for v in words.children() if isinstance(v,Gtk.Button)]
            if not getattr(words,'entry',None) and further:
                n.click(further[0]);spin(lambda:not words.pending,duration=.2,timeout=60)
            if cycle in (0,1):screen.grab(args.output/('bds-mark-11-'+str(29+cycle)+'.png'))
            n.activate(words.dialog);n.key('Escape');spin(duration=.15)
            assert words.dialog is None and not words.pending
            assert t.state.reference=='Mark.11.29'
            report['word_cycles'].append(dict(cycle=cycle,selection=result,choice=cycle%2,closed=True,study_open=w.study_button.get_active()));save()
        immersion_captures()
        w.study_button.set_active(False);assert t.navigate('youversion~YV21','Gen.1.1');settled()
        import os
        recorder=subprocess.Popen(['ffmpeg','-nostdin','-loglevel','error','-y','-f','x11grab','-video_size','1440x1100','-framerate','15','-i',os.environ['DISPLAY'],'-an','-c:v','libx264','-preset','ultrafast','-crf','28',str(args.output/'selection-repeated.mp4')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for cycle in range(40):
            start=t._marker_ends['Gen.1.'+str(1+cycle%3)]+2
            end=start+5+(cycle%4)*8
            if cycle%2:start,end=end,start
            result=select(start,end);result['cycle']=cycle
            report['selection_cycles'].append(result);save()
        report['missing_toolbar']=sum(not x['visible'] for x in report['selection_cycles'])
        assert not exceptions,exceptions
        report['completed']=True;save()
    finally:
        if recorder:
            recorder.terminate()
            try:recorder.wait(timeout=10)
            except subprocess.TimeoutExpired:recorder.kill();recorder.wait()
        save();w.close();n.close();spin()
    print(json.dumps({k:report[k] for k in ('gtk','renderer','missing_toolbar','completed','exceptions')}))
if __name__=='__main__':main()
