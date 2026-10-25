"""Exercise the real, live reader backdrop with sharp controls; disposable profile."""
import argparse,inspect,json,os,signal,subprocess,time,cProfile
from pathlib import Path
from bible.ui import Application,Window,Library,GLib
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input
from tools.check_client_feedback import Screen


def measure_scroll(window):
    """Compare identical scrollbar motion; no production renderer/test hooks."""
    w=window;w.appearance.update('mode','day');w.appearance.update('day_palette','white');w.appearance.update('size',14)
    t=w.active_tab;t.navigate('FreSegond1910','Ps.119.1');spin(lambda:not t._restoring_scroll,duration=.5)
    b=t.text.get_buffer();start=t._marker_ends['Ps.119.1'];b.select_range(b.get_iter_at_offset(start),b.get_iter_at_offset(start+20))
    a=w.passage_actions;adj=t.scroll.get_vadjustment();results=[]
    for phase in ('without_bar','visible_bar','visible_idle','hidden_after_dismiss'):
        adj.set_value(0)
        visible=phase in ('visible_bar','visible_idle')
        if visible:a.capture(t.text,lambda:a.ordinary(t),None)
        else:a.dismiss()
        spin(duration=.4)
        if not visible:assert a.bar.backdrop is None and not a.bar._backdrop_signals and a.adapt_tick==0
        frames=[];beats=[];began=time.monotonic();cpu=time.process_time();last=[began];prof=cProfile.Profile()
        def move():
            elapsed=time.monotonic()-began
            if elapsed>=6:return False
            adj.set_value(min(elapsed,6-elapsed)*60)
            return True
        def beat():
            now=time.monotonic();beats.append(now-last[0]);last[0]=now
            return now-began<6
        def frame(widget,clock):frames.append(time.monotonic());return True
        tick=t.text.add_tick_callback(frame)
        if phase!='visible_idle':GLib.timeout_add(16,move)
        GLib.timeout_add(5,beat)
        prof.enable();spin(duration=6.1,timeout=10);prof.disable();t.text.remove_tick_callback(tick)
        elapsed=time.monotonic()-began;cpu=time.process_time()-cpu
        calls={name:0 for name in ('do_snapshot','changed','adapt','watch')};snapshot_cpu=0
        for entry in prof.getstats():
            code=entry.code
            if isinstance(code,str) or not code.co_filename.endswith('/bible/passage_actions.py'):continue
            if code.co_name in calls:calls[code.co_name]+=entry.callcount
            if code.co_name=='do_snapshot':snapshot_cpu+=entry.inlinetime
        gaps=[y-x for x,y in zip(frames,frames[1:])]
        result=dict(phase=phase,elapsed_seconds=elapsed,cpu_seconds=cpu,cpu_percent=100*cpu/elapsed,frames=len(frames),frame_gap_p95_ms=1000*sorted(gaps)[int(.95*(len(gaps)-1))],main_loop_max_ms=max(beats)*1000,python_calls=calls,snapshot_python_cpu_ms=snapshot_cpu*1000,renderer=type(w.get_renderer()).__name__)
        assert a.bar.get_visible()==visible
        if phase=='visible_bar':assert calls['do_snapshot']>0
        else:assert calls['do_snapshot']==calls['changed']==calls['adapt']==calls['watch']==0,calls
        results.append(result)
    return dict(scroll_impact=results,method='Same 6-second forward/back reader scrollbar adjustment; no wheel lifecycle override. Actual wheel dismisses floating actions on its first event.')


def main():
    p=argparse.ArgumentParser();p.add_argument('profile',type=Path);p.add_argument('output',type=Path);p.add_argument('--record',action='store_true');p.add_argument('--require-packaged',action='store_true');p.add_argument('--measure',action='store_true');args=p.parse_args()
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    args.output.mkdir(parents=True,exist_ok=True)
    app=Application();app.register();w=Window(app,Library(args.profile/'translations'));w.set_default_size(1000,760);w.present();spin();n=X11Input();n.activate(w);screen=Screen(n);report=[]
    try:
        for palette,mode in [('white','day'),('dark','night')]:
            w.appearance.update('mode',mode);w.appearance.update('day_palette' if mode=='day' else 'night_palette',palette);w.appearance.update('size',24)
            t=w.active_tab;t.navigate('FreSegond1910','Ps.119.1');spin(lambda:not t._restoring_scroll,duration=.5)
            b=t.text.get_buffer();start=t._marker_ends['Ps.119.1'];b.select_range(b.get_iter_at_offset(start),b.get_iter_at_offset(start+20));a=w.passage_actions;a.capture(t.text,lambda:a.ordinary(t),None);spin();n.move_at(w,2,2)
            screen.grab(args.output/(palette+'-start.png'));video=None
            if args.record:video=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','x11grab','-framerate','20','-video_size',str(screen.width)+'x'+str(screen.height),'-i',os.environ['DISPLAY'],'-c:v','libx264','-preset','ultrafast','-crf','18','-pix_fmt','yuv420p',str(args.output/(palette+'-live-backdrop.mp4'))],stdin=subprocess.DEVNULL)
            adj=t.scroll.get_vadjustment();origin=adj.get_value();began=time.monotonic();samples=[]
            # Drive the same adjustment used by the scrollbar. Wheel intentionally
            # dismisses floating actions; this keeps a real selection visible to
            # expose live backdrop updates while the reader moves beneath it.
            def move():
                elapsed=time.monotonic()-began
                if elapsed>=6:return False
                distance=elapsed*35 if elapsed<3 else (6-elapsed)*35
                adj.set_value(origin+distance);samples.append((elapsed,adj.get_value(),a.bar.get_visible()))
                return True
            GLib.timeout_add(33,move);spin(duration=3.1,timeout=8);screen.grab(args.output/(palette+'-reversal.png'));spin(duration=3.1,timeout=8)
            assert len(samples)>80 and all(s[2] for s in samples)
            assert a.valid() and a.target.text and b.get_has_selection()
            screen.grab(args.output/(palette+'-end.png'))
            if video:video.send_signal(signal.SIGINT);video.wait(timeout=10);assert video.returncode in (0,255)
            report.append(dict(palette=palette,renderer=type(w.get_renderer()).__name__,source_import=inspect.getfile(Window),samples=samples,selection=a.target.text,scroll_method='reader scrollbar adjustment; wheel dismisses the floating bar by design'))
            a.dismiss();b.place_cursor(b.get_start_iter())
        if args.measure:
            measurement=measure_scroll(w);report.append(measurement);print(json.dumps(measurement,indent=2),flush=True)
    finally:
        (args.output/'live-report.json').write_text(json.dumps(report,indent=2));w.close();n.close()
    print('PASS: live reader backdrop, both directions, sharp control overlay, exact selection retained, light/dark')

if __name__=='__main__':main()
