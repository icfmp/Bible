"""Profile an actual installed alpha without adding a frame-clock tick.

Use the same disposable resource/data profile across version switches and cycles.
Consumption runs and instrumented Python/native-allocation runs are separate.
Diagnostic blur removal affects this process only, never product preferences.
"""
import argparse
import cProfile
import ctypes
import gc
import hashlib
import inspect
import json
import os
from pathlib import Path
import pstats
import subprocess
import sys
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--mode',choices=['single','comparison','study','combined'],default='single')
    p.add_argument('--resource',default='FreSegond1910');p.add_argument('--reference',default='Ps.119.1')
    p.add_argument('--cycles',type=int,default=4);p.add_argument('--toolbar',action='store_true')
    p.add_argument('--backdrop',choices=['native','radius-zero','disabled'],default='native')
    p.add_argument('--instrument',action='store_true');p.add_argument('--require-packaged',action='store_true')
    p.add_argument('--input-interpreter',nargs='+',default=[sys.executable],help='Local runtime loader plus Python only; installed runs use their own Python')
    p.add_argument('--stop-layout-polling',action='store_true',help='Diagnostic ablation at fixed geometry only')
    p.add_argument('--cache-resource-metadata',action='store_true',help='Diagnostic ablation with unchanged test resources only')
    p.add_argument('--input-kind',choices=['wheel','scrollbar'],default='wheel')
    args=p.parse_args();args.output.parent.mkdir(parents=True,exist_ok=True)
    started=time.monotonic();import_started=time.monotonic()
    from bible.ui import Application,Window,Library,GLib,Gtk
    from tests.test_ui import spin
    from tools.check_alpha_ui import X11Input
    import bible.passage_actions as actions
    from tools.alpha_performance_input import sample
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    if args.cache_resource_metadata:
        from functools import lru_cache
        Library.resource=lru_cache(maxsize=128)(Library.resource)
    diagnostic_calls={}
    layout_ticks=[];original_tick=Gtk.Widget.add_tick_callback
    if args.stop_layout_polling:
        def register_tick(widget,callback,*data):
            tick=original_tick(widget,callback,*data)
            name=getattr(callback,'__name__','')
            owner=type(getattr(callback,'__self__',None)).__name__
            if name in ('adapt_comparison','fit_reader_controls') or name=='adapt' and owner=='StudyDivider':
                layout_ticks.append((widget,tick))
            return tick
        Gtk.Widget.add_tick_callback=register_tick
    if args.backdrop=='radius-zero':actions.BACKDROP_BLUR=0
    if args.backdrop=='disabled':
        class NoBackdrop(actions.Backdrop):
            def do_snapshot(self,snapshot):pass
        actions.Backdrop=NoBackdrop
        actions.ActionSurface.set_backdrop=lambda surface,view:surface.clear_backdrop()
    if args.instrument:
        import tracemalloc
        tracemalloc.start(15)
    app=Application();app.register();window=Window(app,Library(args.profile/'translations'))
    window.set_default_size(1180,780);window.present();spin()
    tab=window.active_tab;tab.state.comparison=None;window.sync_comparison();window.study_button.set_active(False)
    assert tab.navigate(args.resource,args.reference)
    spin(lambda:not tab._restoring_scroll,duration=.6)
    if args.mode in ('comparison','combined'):tab.state.comparison='KJV';window.sync_comparison();spin(duration=.5)
    if args.mode in ('study','combined'):
        window.study_button.set_active(True);window.study.tools.set_visible_child_name('commentaries')
        window.study.choices.set_selected(window.study.names.index('Wesley'));window.study.refresh(force=True);spin(duration=.5)
    if hasattr(tab,'inline_markers'):spin(lambda:not tab.inline_markers.pending,duration=.3)
    native=X11Input();native.activate(window)
    scale=window.get_scale_factor()
    def screen_point(widget,local_x,local_y):
        found,bounds=widget.compute_bounds(window);assert found
        x,y,child_window=ctypes.c_int(),ctypes.c_int(),ctypes.c_ulong()
        native.x11.XTranslateCoordinates(native.display,window.get_surface().get_xid(),native.x11.XDefaultRootWindow(native.display),0,0,ctypes.byref(x),ctypes.byref(y),ctypes.byref(child_window))
        dx,dy=window.get_surface_transform()
        return round(x.value+(dx+bounds.origin.x+local_x)*scale),round(y.value+(dy+bounds.origin.y+local_y)*scale)
    x,y=screen_point(tab.text,tab.text.get_width()/2,tab.text.get_height()/2)
    native.xtest.XTestFakeMotionEvent(native.display,-1,x,y,0);native.x11.XFlush(native.display)
    bar_geometry=None
    if args.input_kind=='scrollbar':
        track=tab.scroll.get_vscrollbar().get_first_child()
        low,high=track.get_slider_range();half=(high-low)/2;rect=track.get_range_rect()
        x,top=screen_point(track,track.get_width()/2,(low+high)/2)
        _,bottom=screen_point(track,track.get_width()/2,rect.y+rect.height-half-2)
        assert bottom>top,'No usable native scrollbar travel'
        bar_geometry=dict(x=x,top=top,bottom=bottom)
    spin(duration=.5)
    if args.toolbar:
        buffer=tab.text.get_buffer();offset=tab._marker_ends[args.reference]
        buffer.select_range(buffer.get_iter_at_offset(offset),buffer.get_iter_at_offset(offset+8))
        window.passage_actions.capture(tab.text,lambda:window.passage_actions.ordinary(tab),None);spin(duration=.3)
    if args.stop_layout_polling:
        Gtk.Widget.add_tick_callback=original_tick
        for widget,tick in layout_ticks:widget.remove_tick_callback(tick)
    # No screenshot/tick observer, queue_draw, forced GC or memory trim in a consumption run.
    first_sample=sample(os.getpid());clock=window.get_frame_clock();paints=[];beats=[];positions=[];adjustments=[];menu_visibility=[];last=[time.monotonic()]
    window.passage_actions.bar.connect('notify::visible',lambda bar,*_:menu_visibility.append([time.monotonic(),bar.get_visible()]))
    tab.scroll.get_vadjustment().connect('value-changed',lambda adj:adjustments.append([time.monotonic(),adj.get_value()]))
    paint=clock.connect('after-paint',lambda *_:paints.append(time.monotonic()))
    def beat():
        now=time.monotonic();beats.append([now,now-last[0]]);last[0]=now
        positions.append([now,tab.scroll.get_vadjustment().get_value(),window.passage_actions.bar.get_visible()])
        if child.poll() is not None:loop.quit();return False
        return True
    prof=cProfile.Profile();allocation_before=None
    if args.instrument:
        allocation_before=tracemalloc.take_snapshot();prof.enable()
    loop=GLib.MainLoop();sid=GLib.timeout_add(50,beat)
    inputfile=args.output.with_suffix('.input.json')
    child=subprocess.Popen([*args.input_interpreter,'-m','tools.alpha_performance_input',str(inputfile),str(os.getpid()),str(args.cycles),args.input_kind,json.dumps(bar_geometry)])
    loop.run();assert child.wait()==0,'Independent input/sampler process failed';clock.disconnect(paint)
    if args.instrument:
        prof.disable();prof.dump_stats(str(args.output.with_suffix('.prof')))
        stats=pstats.Stats(prof)
        top=[]
        for (file,line,name),(cc,nc,total,cumulative,callers) in sorted(stats.stats.items(),key=lambda item:item[1][3],reverse=True)[:60]:
            top.append(dict(file=file,line=line,name=name,calls=nc,self_seconds=total,cumulative_seconds=cumulative))
        for key,row in stats.stats.items():
            if key[0].endswith('/bible/passage_actions.py'):diagnostic_calls[f'{key[2]}:{key[1]}']=dict(calls=row[1],self_seconds=row[2],cumulative_seconds=row[3])
        after=tracemalloc.take_snapshot()
        allocations=[dict(trace=item.traceback.format(),bytes=item.size_diff,count=item.count_diff) for item in after.compare_to(allocation_before,'traceback')[:35]]
        python_current,python_peak=tracemalloc.get_traced_memory()
    inputs=json.loads(inputfile.read_text());summaries=[]
    for phase in inputs['phases']:
        rows=[row for row in inputs['samples'] if row['phase']==phase['name'] and row['cycle']==phase.get('cycle')]
        begin,end=rows[0],rows[-1];elapsed=end['time']-begin['time']
        gaps=[gap for when,gap in beats if begin['time']<=when<=end['time']]
        frames=[x for x in paints if begin['time']<=x<=end['time']]
        summaries.append(dict(phase=phase['name'],cycle=phase.get('cycle'),seconds=elapsed,
                              cpu_one_core_percent=100*(end['cpu_seconds']-begin['cpu_seconds'])/elapsed,
                              rss_begin=begin['rss_bytes'],rss_end=end['rss_bytes'],rss_peak=max(r['rss_bytes'] for r in rows),
                              pss_begin=begin['pss_bytes'],pss_end=end['pss_bytes'],
                              anonymous_end=end['anonymous_bytes'],main_loop_max_ms=max(gaps,default=0)*1000,
                              main_loop_over_100ms=sum(x>.1 for x in gaps),actual_paints=len(frames)))
    report=dict(app_import=inspect.getfile(Window),gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],
                app_ui_sha256=hashlib.sha256(Path(inspect.getfile(Window)).read_bytes()).hexdigest(),
                passage_actions_sha256=hashlib.sha256(Path(inspect.getfile(actions)).read_bytes()).hexdigest(),
                renderer=type(window.get_renderer()).__name__,renderer_env=os.environ.get('GSK_RENDERER'),
                logical_cpus=os.cpu_count(),resource=args.resource,reference=args.reference,mode=args.mode,
                comparison=tab.state.comparison,study_open=window.split.get_show_sidebar(),study_tool=window.study.tool,
                scale_factor=scale,
                input_kind=args.input_kind,scrollbar_geometry=bar_geometry,
                preferences=vars(tab.preferences),geometry=[window.get_width(),window.get_height()],
                startup_to_ready_seconds=first_sample['time']-started,startup_ready_memory=first_sample,
                initially_visible_toolbar=args.toolbar,diagnostic_backdrop=args.backdrop,instrumented=args.instrument,
                diagnostic_layout_ticks_removed=len(layout_ticks),
                diagnostic_resource_cache=args.cache_resource_metadata,
                phases=summaries,measurements=dict(beats=beats,paints=paints,positions=positions,adjustments=adjustments,menu_visibility=menu_visibility),
                menu_final_visible=window.passage_actions.bar.get_visible(),
                backdrop_released=getattr(window.passage_actions.bar,'backdrop',None) is None,
                placement_tick=getattr(window.passage_actions,'adapt_tick',None),
                process_end=sample(os.getpid()),data_profile_reused=str(args.profile))
    first_input=inputs['events'][0][0]
    first_move=next((when for when,value in adjustments if when>=first_input),None)
    first_paint=next((when for when in paints if first_move and when>=first_move),None)
    report['first_scroll_latency_seconds']=first_move-first_input if first_move else None
    report['first_paint_latency_seconds']=first_paint-first_input if first_paint else None
    first_hide=next((when for when,visible in menu_visibility if when>=first_input and not visible),None)
    report['first_menu_hide_latency_seconds']=first_hide-first_input if first_hide else None
    stops=[]
    for index,phase in enumerate(inputs['phases']):
        if phase['name']!='after_scroll_idle':continue
        stop=phase['start'];end=inputs['phases'][index+1]['start'] if index+1<len(inputs['phases']) else inputs['end']
        late=[when-stop for when,value in adjustments if stop+.5<when<end]
        stops.append(dict(cycle=phase['cycle'],adjustments_later_than_500ms=len(late),last_late_seconds=max(late,default=0)))
    report['after_stop']=stops
    if args.instrument:
        report.update(python_profile=top,menu_profile=diagnostic_calls,python_allocation_changes=allocations,
                      python_traced_current=python_current,python_traced_peak=python_peak)
        class MallInfo(ctypes.Structure):
            _fields_=[(name,ctypes.c_size_t) for name in ('arena','ordblks','smblks','hblks','hblkhd','usmblks','fsmblks','uordblks','fordblks','keepcost')]
        libc=ctypes.CDLL(None);libc.mallinfo2.restype=MallInfo
        report['native_malloc_end']={name:getattr(value:=libc.mallinfo2(),name) for name,_ in MallInfo._fields_}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('measurements','python_profile','python_allocation_changes')},indent=2),flush=True)
    window.study_button.set_active(False);tab.state.comparison=None;window.sync_comparison();window.close();native.close()


if __name__=='__main__':main()
