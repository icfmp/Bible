"""Measure sustained real X11 input; the input process never waits for GTK.

Disposable profile only. Real source resources; optional installed-import check.
Frames, adjustment samples, input timestamps and main-loop gaps are retained.
"""
from pathlib import Path
import time,json,sys,subprocess,cProfile,pstats,io,argparse,inspect
from bible.ui import Application,Window,Library,GLib,Gtk
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input

def main():
    p=argparse.ArgumentParser();p.add_argument('profile',type=Path);p.add_argument('output',type=Path);p.add_argument('--mode',default='single');p.add_argument('--cpu',action='store_true');p.add_argument('--toolbar',action='store_true');p.add_argument('--require-packaged',action='store_true');p.add_argument('--check',action='store_true');args=p.parse_args()
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    a=Application();a.register();w=Window(a,Library(args.profile/'translations'));w.set_default_size(1180,780);w.present();spin();t=w.active_tab
    t.state.comparison=None;w.sync_comparison();w.study_button.set_active(False);assert t.navigate('FreSegond1910','Ps.119.1');spin(lambda:not t._restoring_scroll,duration=.6)
    if args.mode=='comparison':t.state.comparison='KJV';w.sync_comparison();spin(duration=.8)
    if args.mode=='study':w.study_button.set_active(True);w.study.tools.set_visible_child_name('commentaries');w.study.choices.set_selected(w.study.names.index('Wesley'));w.study.refresh(force=True);spin(duration=.8)
    spin(lambda:not t.inline_markers.pending,duration=.5) if hasattr(t,'inline_markers') else None
    native=X11Input();native.activate(w);native.move_at(t.text,t.text.get_width()/2,t.text.get_height()/2);spin(duration=.3)
    if args.toolbar:
        span=next(s for s in t._document.spans if s.reference=='Ps.119.1')
        buffer=t.text.get_buffer();buffer.select_range(buffer.get_iter_at_offset(span.body),buffer.get_iter_at_offset(span.body+5))
        w.passage_actions.capture(t.text,lambda:w.passage_actions.ordinary(t),None);spin(duration=.2)
    assert w.passage_actions.bar.get_visible()==args.toolbar
    dismissals=[];original_dismiss=w.passage_actions.dismiss
    def observed_dismiss():
        visible=w.passage_actions.bar.get_visible();began=time.monotonic()
        result=original_dismiss()
        if visible:dismissals.append(dict(start=began,end=time.monotonic(),backdrop_released=w.passage_actions.bar.backdrop is None,placement_stopped=w.passage_actions.adapt_tick==0))
        return result
    w.passage_actions.dismiss=observed_dismiss
    adjustment_events=[];adjustment=t.scroll.get_vadjustment();last_value=[adjustment.get_value()]
    def adjustment_changed(adj):
        value=adj.get_value()
        if abs(value-last_value[0])>.5:adjustment_events.append([time.monotonic(),value])
        last_value[0]=value
    adjustment.connect('value-changed',adjustment_changed)
    paints=[];frame_clock=t.text.get_frame_clock()
    paint_handler=frame_clock.connect('after-paint',lambda *_:paints.append([time.monotonic(),w.passage_actions.bar.get_visible()]))
    rows=[];beats=[];frames=[];last=[time.monotonic()];prof=cProfile.Profile();start=time.monotonic();loop=GLib.MainLoop();inputfile=args.output.with_suffix('.input.json')
    def beat():
     now=time.monotonic();beats.append(now-last[0]);last[0]=now
     adj=t.scroll.get_vadjustment();rows.append([now,adj.get_value(),t.text.get_visible_rect().y,t.state.reference])
     if now>start+12 and child.poll() is not None:loop.quit();return False
     return True
    def frame(widget,clock):frames.append(time.monotonic());return True
    sid=GLib.timeout_add(10,beat);fid=t.text.add_tick_callback(frame)
    child=subprocess.Popen([sys.executable,'-m','tools.sustained_scroll_input',str(inputfile)])
    if args.cpu:prof.enable()
    loop.run()
    if args.cpu:
     prof.disable();prof.dump_stats(str(args.output.with_suffix('.prof')))
     out=io.StringIO();pstats.Stats(prof,stream=out).sort_stats('cumulative').print_stats(35);args.output.with_suffix('.profile.txt').write_text(out.getvalue())
    t.text.remove_tick_callback(fid);frame_clock.disconnect(paint_handler);child.wait();inputs=json.loads(inputfile.read_text());event_end=inputs['end'];changes=[r for a,r in zip(rows,rows[1:]) if abs(a[1]-r[1])>.5]
    report=dict(app_import=inspect.getfile(Window),mode=args.mode,resource='FreSegond1910',chapter='Ps.119',geometry=[w.get_width(),w.get_height()],preferences=vars(t.preferences),animations=Gtk.Settings.get_default().get_property('gtk-enable-animations'),renderer=__import__('os').environ.get('GSK_RENDERER'),study_visible=w.split.get_show_sidebar(),comparison=t.state.comparison,toolbar_visible=w.passage_actions.bar.get_visible(),input=inputs,heartbeat=dict(count=len(beats),maximum=max(beats),over_100ms=sum(x>.1 for x in beats)),frames=frames,samples=rows,last_adjustment_change=changes[-1][0] if changes else None,changes_during_input=sum(inputs['start']<=r[0]<=event_end for r in changes),changes_after_500ms=sum(r[0]>event_end+.5 for r in changes),duration=time.monotonic()-start)
    reversals=[]
    for previous,event in zip(inputs['events'],inputs['events'][1:]):
        if previous[1]==event[1]:continue
        sign=1 if event[1]==5 else -1
        moves=[r[0]-event[0] for a,r in zip(rows,rows[1:]) if r[0]>=event[0] and r[0]<event[0]+.5 and (r[1]-a[1])*sign>1]
        reversals.append(min(moves) if moves else None)
    report['reversal_latency_seconds']=reversals
    first_input=inputs['events'][0][0]
    first_change=next((r[0] for r in adjustment_events if r[0]>=first_input),None)
    report['first_scroll_latency_seconds']=first_change-first_input if first_change else None
    report['bar_dismissals']=dismissals
    report['adjustment_events']=adjustment_events
    first_paint=next((p for p in paints if first_change and p[0]>=first_change),None)
    report['first_gtk_paint_latency_seconds']=first_paint[0]-first_input if first_paint else None
    report['bar_visible_at_first_scroll_paint']=first_paint[1] if first_paint else None
    if dismissals:
     d=dismissals[0];report['first_bar_transition']=dict(input_to_dismiss_start_seconds=d['start']-first_input,dismiss_duration_seconds=d['end']-d['start'],dismiss_end_to_first_motion_seconds=first_change-d['end'] if first_change else None,**d)
    args.output.write_text(json.dumps(report,indent=2))
    if args.check:
     during=[x for x in frames if inputs['start']<=x<=event_end]
     assert all(x is not None and x<.4 for x in reversals),('Delayed direction changes',reversals)
     assert len(during)>=80,('Reader frames starved during sustained input',len(during))
     assert report['changes_after_500ms']==0,('Late event backlog',report['changes_after_500ms'])
     assert max(beats)<.5,('GTK main-loop stall',max(beats))
     assert first_change and first_change-first_input<.25,('First scroll delayed',report['first_scroll_latency_seconds'])
     assert first_paint and first_paint[0]-first_input<.25,('First GTK paint delayed',report['first_gtk_paint_latency_seconds'])
     if args.toolbar:
      assert dismissals and dismissals[0]['end']<=first_change,dismissals
      assert dismissals[0]['backdrop_released'] and dismissals[0]['placement_stopped'],dismissals
      assert not first_paint[1],'Bar remained visible in the first scroll frame'
    args.output.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('samples','input','frames','adjustment_events')},indent=2));w.close();native.close()

if __name__=='__main__':main()
