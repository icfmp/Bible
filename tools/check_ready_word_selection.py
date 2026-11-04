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
    p.add_argument('--selection-only',action='store_true');p.add_argument('--selection-matrix',action='store_true');p.add_argument('--baseline-captures',action='store_true');p.add_argument('--prepare',action='store_true');p.add_argument('--require-packaged',action='store_true')
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
        if not args.selection_only:
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
    def select(start,end,view=None):
        view=view or t.text;spin(duration=.05);b=view.get_buffer()
        first=view.get_iter_location(b.get_iter_at_offset(start));last=view.get_iter_location(b.get_iter_at_offset(end))
        x,y=view.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,first.x,first.y+first.height//2)
        ex,ey=view.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,last.x,last.y+last.height//2)
        n.move_at(view,x,y);n.xtest.XTestFakeButtonEvent(n.display,1,True,0);n.x11.XFlush(n.display);spin(duration=.04)
        for i in range(1,7):n.move_at(view,x+(ex-x)*i/6,y+(ey-y)*i/6);spin(duration=.018)
        n.xtest.XTestFakeButtonEvent(n.display,1,False,0);n.x11.XFlush(n.display);spin(duration=.22)
        bounds=tuple(i.get_offset() for i in b.get_selection_bounds())
        value=a.target;placement=None
        if value and a.bar.get_visible():
            ok,rect=a.bar.compute_bounds(value.source.parent)
            if ok:placement=dict(x=round(rect.origin.x),y=round(rect.origin.y),width=round(rect.size.width),height=round(rect.size.height),parent_width=value.source.parent.get_width(),parent_height=value.source.parent.get_height())
        return dict(expected=[start,end],actual=bounds,visible=a.bar.get_visible(),mapped=a.bar.get_mapped(),dragging=a.dragging,capture_pending=bool(a.capture_idle),target_resource=value.source.resource if value else None,target_refs=value.references if value else None,intent=a.intent,placement=placement)
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
        for cycle in range(0 if args.selection_only else 12):
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
        if not args.selection_only:immersion_captures()
        w.study_button.set_active(False);assert t.navigate('youversion~YV21','Gen.1.1');settled()
        import os
        recorder=subprocess.Popen(['ffmpeg','-nostdin','-loglevel','error','-y','-f','x11grab','-video_size','1440x1100','-framerate','15','-i',os.environ['DISPLAY'],'-an','-c:v','libx264','-preset','ultrafast','-crf','28',str(args.output/'selection-repeated.mp4')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for cycle in range(0 if args.selection_matrix else 120):
            start=t._marker_ends['Gen.1.'+str(1+cycle%3)]+2
            end=start+5+(cycle%4)*8
            if cycle%2:start,end=end,start
            result=select(start,end);result['cycle']=cycle
            report['selection_cycles'].append(result);save()
        if args.selection_matrix:
            report['bar_events']=[]
            a.bar.connect('notify::visible',lambda *_:report['bar_events'].append(dict(visible=a.bar.get_visible(),intent=a.intent,dragging=a.dragging)))
            for resource,chapter,width,study,comparison in (
                    ('youversion~YV21','Gen.1',1200,False,None),
                    ('youversion~YV21','Gen.1',360,False,None),
                    ('KJV','John.1',1200,True,None),
                    ('youversion~YV21','Gen.1',1200,False,'KJV'),
                    ('youversion~YV21','Gen.1',1200,True,'KJV')):
                t.state.comparison=None;w.sync_comparison();w.set_default_size(width,900)
                assert t.navigate(resource,chapter+'.1');settled();w.study_button.set_active(study)
                t.state.comparison=comparison;w.sync_comparison()
                spin(lambda:not t._restoring_scroll and not getattr(t,'_comparison_positioning',False),duration=.4,timeout=60)
                for side in ('primary','comparison') if comparison else ('primary',):
                    view=t.comparison_text if side=='comparison' else t.text
                    markers=t._comparison_markers if side=='comparison' else t._marker_ends
                    for cycle in range(24):
                        start=markers[chapter+'.1']+2
                        end=markers[chapter+('.3' if cycle%3 else '.1')]+(10 if cycle%3 else 7)
                        if cycle%2:start,end=end,start
                        event_start=len(report['bar_events'])
                        result=select(start,end,view);result.update(case='replacement-multiline',resource=resource,width=width,study=study,side=side,cycle=cycle,bar_events=report['bar_events'][event_start:])
                        result['expected_resource']=comparison if side=='comparison' else resource
                        report['selection_cycles'].append(result);save()
            # Native keyboard completion and deliberate dismissal/reopening.
            t.state.comparison=None;w.sync_comparison();w.study_button.set_active(False)
            assert t.navigate('youversion~YV21','Gen.1.1');settled()
            first=t._marker_ends['Gen.1.1']+3;rect=t.text.get_iter_location(t.text.get_buffer().get_iter_at_offset(first))
            x,y=t.text.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,rect.x,rect.y+rect.height//2)
            n.click_at(t.text,x,y);spin(duration=.2)
            code=n.x11.XKeysymToKeycode(n.display,n.x11.XStringToKeysym(b'Shift_L'))
            n.xtest.XTestFakeKeyEvent(n.display,code,True,0)
            for _ in range(7):n.key('Right')
            n.xtest.XTestFakeKeyEvent(n.display,code,False,0);n.x11.XFlush(n.display);spin(duration=.3)
            bounds=[i.get_offset() for i in t.text.get_buffer().get_selection_bounds()]
            report['keyboard']=dict(selection=bounds,visible=a.bar.get_visible(),resource=a.target.source.resource if a.target else None)
            assert bounds and a.bar.get_visible(),report['keyboard']
            n.key('Escape');spin();assert not a.bar.get_visible()
            result=select(first,first+12);result['case']='reopen-after-escape';report['selection_cycles'].append(result)
            n.wheel(t.text,1);assert not a.bar.get_visible() and a.bar.backdrop is None and not a.adapt_tick
            n.wheel(t.text,-1);spin(duration=.3)
            result=select(first,first+12);result['case']='reopen-after-wheel';report['selection_cycles'].append(result)
            # A real drag reaches the viewport edge and invokes GTK's native
            # selection autoscroll. Release it before observing completion.
            n.move_at(t.text,x,y);n.xtest.XTestFakeButtonEvent(n.display,1,True,0);n.x11.XFlush(n.display);spin(duration=.06)
            for i in range(1,21):n.move_at(t.text,x,y+(t.text.get_height()-y-2)*i/20);spin(duration=.025)
            spin(duration=.7)
            n.xtest.XTestFakeButtonEvent(n.display,1,False,0);n.x11.XFlush(n.display);spin(duration=.4)
            report['selection_cycles'].append(dict(case='viewport-edge-autoscroll',actual=[i.get_offset() for i in t.text.get_buffer().get_selection_bounds()],visible=a.bar.get_visible(),mapped=a.bar.get_mapped(),dragging=a.dragging,capture_pending=bool(a.capture_idle),intent=a.intent,target_resource=a.target.source.resource if a.target else None))
            # Switching tabs/resources must invalidate the old target without
            # suppressing the next completed selection in either tab.
            w.new_tab();t=w.active_tab;assert t.navigate('KJV','John.1.1');settled()
            result=select(t._marker_ends['John.1.1']+2,t._marker_ends['John.1.2']+12);result.update(case='new-tab-source',expected_resource='KJV');report['selection_cycles'].append(result)
            w.close_tab();t=w.active_tab;assert t.navigate('youversion~YV21','Gen.1.1');settled()
            result=select(t._marker_ends['Gen.1.1']+2,t._marker_ends['Gen.1.2']+12);result.update(case='returned-tab-source',expected_resource='youversion~YV21');report['selection_cycles'].append(result)
            assert all(c.get('target_resource') for c in report['selection_cycles'] if c['visible'])
            report['wrong_target_count']=sum(c.get('expected_resource')!=c.get('target_resource') for c in report['selection_cycles'] if c.get('expected_resource') and c['visible'])
        report['missing_toolbar']=sum(bool(x['actual']) and not x['visible'] for x in report['selection_cycles'])
        report['collapsed_drag_count']=sum(not x['actual'] for x in report['selection_cycles'])
        report['native_replacement_without_programmatic_dismissal']=True
        if args.selection_matrix:assert not report['missing_toolbar'] and not report['collapsed_drag_count'] and not report['wrong_target_count'],report['selection_cycles'][-1]
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
