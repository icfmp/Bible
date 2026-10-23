"""Actual Library startup latency/heartbeat; disposable real-resource profiles."""
import argparse
import inspect
import json
from pathlib import Path
import time
from gi.repository import GLib,Gtk
from bible.ui import Application,Window,Library


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--baseline',action='store_true');parser.add_argument('--offline',action='store_true')
    parser.add_argument('--require-packaged',action='store_true')
    parser.add_argument('--wait-refresh',action='store_true')
    parser.add_argument('--native',action='store_true');parser.add_argument('--captures',type=Path)
    args=parser.parse_args()
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    if args.offline:assert len(Path('/proc/net/route').read_text().splitlines())<=1
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    app=Application();app.register();loop=GLib.MainLoop();errors=[]
    report={'app_import':inspect.getfile(Window),'offline':args.offline,'accessibility':'Deferred; not tested',
            'reported_crash':'Not reproduced; no historical crash mechanism is claimed'}
    gaps=[];last=[time.monotonic()];dialog=[None]
    def heartbeat():
        now=time.monotonic();gaps.append(now-last[0]);last[0]=now;return True
    timer=GLib.timeout_add(10,heartbeat)
    application_start=time.monotonic()
    window=Window(app,Library(args.profile/'translations'));window.present()
    report['application_constructor_seconds']=time.monotonic()-application_start
    notes=window.notes_store.all();resources=window.library.installed()
    report['startup_scroll_preparation']=window.active_tab._restoring_scroll
    native=None
    if args.native:
        from tools.check_alpha_ui import X11Input
        native=X11Input()
    def capture(name):
        if args.captures:
            from PIL import ImageGrab
            args.captures.mkdir(parents=True,exist_ok=True);ImageGrab.grab().save(args.captures/(name+'.png'))
    # Measure Library latency separately from the synchronous application shell.
    gaps.clear();last[0]=time.monotonic();start=last[0]
    dialog[0]=window.open_library();report['constructor_seconds']=time.monotonic()-start
    frames=[0];deadline=start+80
    def frame(*_):
        frames[0]+=1
        if frames[0]<2:return True
        report['first_painted_frame_seconds']=time.monotonic()-start;return False
    dialog[0].add_tick_callback(frame)
    def finish():
        d=dialog[0]
        if time.monotonic()<=deadline:
            if 'first_painted_frame_seconds' not in report:return True
            if getattr(d,'preparing',False) or getattr(d,'_building_rows',False):return True
            if not d.resources and d.refreshing:return True
            if args.wait_refresh and d.refreshing:return True
        try:
            if time.monotonic()>deadline:raise AssertionError('Library did not settle')
            # Real caches can be stale: keep the cached view interactive while
            # its refresh is running rather than waiting for every provider.
            report.update(resources=len(d.resources),languages=len(d.languages),
                ready_seconds=time.monotonic()-start,maximum_heartbeat_gap_seconds=max(gaps,default=0),
                refresh_running=d.refreshing,stages=dict(d.timings))
            before=(window.active_tab.state.reference,list(window.active_tab.state.history))
            capture('ready')
            d.search.set_text('fr');d.filter_resources()
            if d.filtered_resources:d.open_details(None,0);d.back_to_list()
            d.close()
            reopened_at=time.monotonic()
            if native:
                native.activate(window);native.click(window.library_button);reopened=window.catalogue_window
                report['native_pointer_reopen']=reopened is not d and reopened.get_mapped()
                assert report['native_pointer_reopen']
            else:reopened=window.open_library()
            dialog[0]=reopened
            report['reopen_constructor_seconds']=time.monotonic()-reopened_at
            assert before==(window.active_tab.state.reference,window.active_tab.state.history)
            assert window.notes_store.all()==notes and window.library.installed()==resources
            if not args.baseline:
                assert report['constructor_seconds']<1,report
                assert report['first_painted_frame_seconds']<1.5,report
                assert report['maximum_heartbeat_gap_seconds']<.5,report
            report['notes_resources_reading_preserved']=True;report['status']='OBSERVED' if args.baseline else 'PASS'
        except Exception as error:errors.append(repr(error))
        finally:
            d=dialog[0]
            if d and not d.closed:d.close()
            window.close();loop.quit()
            if native:native.close()
        return False
    GLib.timeout_add(30,finish);loop.run();GLib.source_remove(timer)
    assert not errors,errors
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
