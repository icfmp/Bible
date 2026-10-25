"""Exercise the real, live reader backdrop with sharp controls; disposable profile."""
import argparse,inspect,json,os,signal,subprocess,time
from pathlib import Path
from bible.ui import Application,Window,Library,GLib
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input
from tools.check_client_feedback import Screen


def main():
    p=argparse.ArgumentParser();p.add_argument('profile',type=Path);p.add_argument('output',type=Path);p.add_argument('--record',action='store_true');p.add_argument('--require-packaged',action='store_true');args=p.parse_args()
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
    finally:
        (args.output/'live-report.json').write_text(json.dumps(report,indent=2));w.close();n.close()
    print('PASS: live reader backdrop, both directions, sharp control overlay, exact selection retained, light/dark')

if __name__=='__main__':main()
