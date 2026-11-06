"""Measure actual entry-to-usable-paint in a marked retained test profile.

Run one case per process for cold-process comparisons. OS/font/disk caches are
not flushed. The second entry is a re-entry in that same process. No profiler
is enabled for these measurements; JSON contains no Scripture or note bodies.
"""
import argparse
from dataclasses import asdict
import hashlib
import inspect
import json
from pathlib import Path
import resource
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--case',default='youversion~YV21:Ps.34.2')
    parser.add_argument('--require-packaged',action='store_true')
    args=parser.parse_args()
    assert any((args.profile/name).is_file() for name in ('.ready-reading-notes-profile','.ready-benchmark-profile')),'Unmarked test profile'
    args.output.mkdir(parents=True,exist_ok=True)
    from bible.ui import Application,Window,Library,Gtk,GLib
    from tests.test_ui import spin
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    app=Application();app.register();window=Window(app,Library(args.profile/'translations'))
    window.set_default_size(1200,860);window.present();native=X11Input();screen=Screen(native)
    report=dict(app_import=inspect.getfile(Window),ui_sha256=hashlib.sha256(Path(inspect.getfile(Window)).read_bytes()).hexdigest(),
        gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],renderer=type(window.get_renderer()).__name__,
        cold_definition='First immersion entry in a fresh app process; OS/font/disk caches not flushed.',
        warm_definition='Re-entry in the same process; the book stream is recreated normally.',entries=[])
    def save():
        (args.output/'entry.json').write_text(json.dumps(report,indent=2)+'\n')
    def settled():
        spin(lambda:not window.active_tab._restoring_scroll and not getattr(window.active_tab,'_comparison_positioning',False),duration=.3,timeout=30)
    def cpu():
        value=resource.getrusage(resource.RUSAGE_SELF);return value.ru_utime+value.ru_stime
    def rss():
        for line in Path('/proc/self/status').read_text().splitlines():
            if line.startswith('VmRSS:'):return int(line.split()[1])/1024
    try:
        if args.require_packaged:
            assert report['app_import'].startswith('/app/')
            assert 'GL' in report['renderer']
        assert window.notes_store is not None,'Existing notes must be readable; do not replace/reset the profile'
        resource_name,reference=args.case.split(':',1)
        window.active_tab.navigate(resource_name,reference);settled()
        report.update(resource=resource_name,reference=reference,preferences=asdict(window.preferences.value),
            window=[window.get_width(),window.get_height()],ui_font=Gtk.Settings.get_default().props.gtk_font_name)
        initial_notes=window.notes_store.all();save()
        for iteration in ('cold-process-entry','warm-reentry'):
            gaps=[];paint=[];last=[time.monotonic()];start=time.monotonic();cpu_start=cpu();rss_start=rss()
            def heartbeat():
                now=time.monotonic();gaps.append(now-last[0]);last[0]=now;return True
            timer=GLib.timeout_add(10,heartbeat)
            def painted(*_):
                view=window.immersion
                if not view or not view.addresses:return
                pages=view.views[:len(view.addresses)]
                if not all(p.get_mapped() and p.get_width()>0 and p.get_buffer().get_char_count()>0 for p in pages):return
                for page in pages:
                    end=len(page.get_buffer().props.text.rstrip())
                    if not end:continue
                    box=page.get_iter_location(page.get_buffer().get_iter_at_offset(end-1))
                    if box.y+box.height+page.get_top_margin()>page.get_height()+1:return
                if not paint:paint.append(dict(seconds=time.monotonic()-start,cpu_seconds=cpu()-cpu_start,rss_mib=rss()))
            handler=window.get_frame_clock().connect('after-paint',painted)
            try:
                assert window.enter_immersion('bible')
                enter_return=time.monotonic()-start
                spin(lambda:bool(paint) and window.immersion.layout_ready,duration=.05,timeout=180)
            finally:
                GLib.source_remove(timer);window.get_frame_clock().disconnect(handler)
            record=dict(iteration=iteration,enter_return_seconds=enter_return,first_usable_paint_seconds=paint[0]['seconds'],
                cpu_seconds_to_usable_paint=paint[0]['cpu_seconds'],rss_before_mib=rss_start,rss_after_mib=paint[0]['rss_mib'],
                max_main_loop_gap_ms=1000*max(gaps,default=0),heartbeat_samples=len(gaps),
                reading_pages=len(window.immersion.addresses),anchor=asdict(window.immersion.stream.anchor()))
            screen.grab(args.output/(iteration+'.png'));report['entries'].append(record);save()
            print(json.dumps(record),flush=True)
            window.leave_immersion();settled()
        assert window.notes_store.all()==initial_notes
        report['notes_preserved']=True;report['complete']=True;save()
    finally:
        if window.immersion:window.leave_immersion()
        window.close();native.close();save()


if __name__=='__main__':main()
