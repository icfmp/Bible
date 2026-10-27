"""Real-resource native before/after evidence; use disposable profile copies only.

No downloaded corpora are exported. Captures are unedited native root surfaces.
Baseline mode records the delivered implementation without applying new rules.
"""
import argparse
import ctypes
import inspect
import json
import os
from pathlib import Path
import signal
import subprocess
from unittest.mock import patch


def walk(widget):
    yield widget
    child=widget.get_first_child()
    while child:
        yield from walk(child);child=child.get_next_sibling()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--baseline',action='store_true');p.add_argument('--require-packaged',action='store_true')
    p.add_argument('--section',choices=['comparison','markers','notes','preferences','navigation','immersion','all'],default='all')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    from bible.ui import Application,Window,Library,Gtk
    from bible.place_data import PlaceData
    from bible.application_surfaces import show_preferences
    from tests.test_ui import spin,close_test_dialogs
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    app=Application();app.register();report=dict(app_import=inspect.getfile(Window),baseline=args.baseline,sections={})
    with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):
        w=Window(app,Library(args.profile/'translations'));w.set_default_size(1440,950);w.present()
        n=X11Input();n.activate(w);screen=Screen(n)
        report.update(gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],renderer=type(w.get_renderer()).__name__)
        if args.require_packaged:assert 'GL' in report['renderer']
        def settled():spin(lambda:not w.active_tab._restoring_scroll,duration=.4)
        def shot(name):
            n.move_at(w,2,2);spin(duration=.15);return screen.grab(args.output/(name+'.png'))
        def palette(mode,name,style,high=False):
            style.set(dark=mode=='night',high=high);w.appearance.update('mode',mode)
            if not high:w.appearance.update('day_palette' if mode=='day' else 'night_palette',name)
            settled()
        def chosen(section):return args.section in (section,'all')
        try:
            t=w.active_tab;t.state.comparison=None;w.sync_comparison();w.study_button.set_active(False)
            w.appearance.update('size',24)
            with SystemStyleOverride() as style:
                if chosen('comparison'):
                    t.navigate('youversion~YV21','John.1.1');t.state.comparison='KJV';w.sync_comparison();settled()
                    cases=[]
                    for mode,name in [('day','white'),('night','dark')]:
                        palette(mode,name,style);rows=t.comparison_rows
                        points=[[v.get_iter_location(v.get_buffer().get_iter_at_offset(offsets[refs[0]])).y if refs else None
                                 for row in rows.rows for refs in [(row.primary if side==0 else row.secondary)]]
                                for side,v,offsets in [(0,t.text,t._marker_ends),(1,t.comparison_text,t._comparison_markers)]]
                        maximum=max(abs(a-b) for a,b in zip(*points) if a is not None and b is not None)
                        assert t.scroll.get_vadjustment() is t.comparison_scroll.get_vadjustment()
                        if not args.baseline:assert maximum<=1,maximum
                        cases.append(dict(palette=name,rows=len(rows.rows),maximum_body_delta_pixels=maximum));shot('comparison-'+name)
                    report['sections']['comparison']=cases;w.end_comparison();settled()
                if chosen('markers'):
                    cases=[]
                    for title,ref in [('Shinar','Gen.11.2'),('Haran','Acts.7.2')]:
                        t.navigate('FreBDM1707',ref);settled()
                        w.notes_store.save('Synthetic native marker check.',[],versification=t.reader.versification,start=ref,end=ref,origin_translation=t.state.resource,origin_language='fr');w.notes_changed();settled()
                        place=next(v for v in PlaceData(args.profile/'study-data').query([ref]) if v['name']==title)
                        for mode,name in [('day','white'),('night','dark')]:
                            palette(mode,name,style)
                            button=next(b for b in t.text._inline_buttons if b._marker_kind=='place' and b._marker_reference==ref)
                            pos=next(pos for pos,(r,k,payload) in t._document.inline.items() if r==ref and k=='place')
                            t.text.scroll_to_iter(t.text.get_buffer().get_iter_at_offset(pos),0,True,0,.3);settled();shot(title+'-'+name+'-markers')
                            n.click(button);spin();dialog=getattr(w,'place_dialog',None)
                            if not dialog:
                                pop=next(pop for pop in w._reading_popovers if pop.get_visible())
                                n.click(next(b for b in walk(pop) if getattr(b,'_place_id',None)==place['id']));spin();dialog=w.place_dialog
                            if hasattr(dialog.map_widget,'ready'):spin(lambda:dialog.map_widget.ready or dialog.map_widget.retry.get_visible(),timeout=45)
                            else:spin(duration=.7)
                            if isinstance(dialog,Gtk.Window):
                                n.x11.XMoveWindow.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_int]
                                n.x11.XMoveWindow(n.display,dialog.get_surface().get_xid(),340,40);n.x11.XFlush(n.display);n.activate(dialog)
                            spin(duration=.4);shot(title+'-'+name+'-map')
                            row=dict(place=title,palette=name,reader_mapped=w.get_mapped(),transient=isinstance(dialog,Gtk.Window) and dialog.get_transient_for() is w,map_ready=getattr(dialog.map_widget,'ready',None))
                            if not args.baseline:assert row['transient'] and row['map_ready'],row
                            cases.append(row);dialog.close();spin();n.activate(w)
                    report['sections']['markers']=cases
                if chosen('notes'):
                    t.navigate('FreSegond1910','John.1.5');settled();notes=[]
                    for ref,body,labels in [('John.1.5','**Validation note**\n\nA retained note with labels. See John 3:16.',['Reading','Hope']),('John.1.5','A distinct second annotation.',['Review']),('Gen.1.1','Long editing test.\n\n'+'\n'.join(f'Paragraph {i}: synthetic editing text, no Scripture quotation.' for i in range(80)),['Long note'])]:
                        notes.append(w.notes_store.save(body,labels,versification=t.reader.versification,start=ref,end=ref,origin_translation=t.state.resource,origin_language='fr'))
                    w.highlights.set(t.reader.versification,['John.1.5','John.3.16'],'yellow',t.state.resource);w.notes_changed();s=w.open_notes()
                    for mode,name,high in [('day','white',False),('night','dark',False),('day','paper',False),('night','black',False),('day','contrast',True)]:
                        palette(mode,name,style,high);s.reveal(('note',notes[0].id));spin(duration=.4);shot('notes-'+name)
                    palette('day','white',style);s.open_note(notes[2]);spin();shot('notes-long')
                    w.set_default_size(560,800);spin(duration=.5);shot('notes-narrow-detail');s.back_to_list();spin();shot('notes-narrow-list')
                    settings=Gtk.Settings.get_default();font=settings.get_property('gtk-font-name')
                    try:
                        settings.set_property('gtk-font-name','Cantarell 16');s.open_note(notes[0]);spin(duration=.4);shot('notes-narrow-large-type')
                    finally:settings.set_property('gtk-font-name',font)
                    if not args.baseline:
                        assert not hasattr(s,'new_button') and not w.lookup_action('note').get_enabled()
                        assert w.new_note(force_new=True) is None
                    s.leave();spin();w.set_default_size(1440,950);settled();report['sections']['notes']=dict(distinct_notes=len(notes),records=len(s.rows),native_editor_scroll=True)
                if chosen('preferences'):
                    for mode,name in [('day','white'),('night','dark')]:
                        palette(mode,name,style)
                        for small in (False,True):
                            w.set_default_size(560 if small else 1280,760 if small else 900);spin()
                            settings=Gtk.Settings.get_default();font=settings.get_property('gtk-font-name')
                            try:
                                if small:settings.set_property('gtk-font-name','Cantarell 16')
                                d=show_preferences(w)
                                if not args.baseline:d.set_visible_page_name('reading')
                                spin(duration=.5);n.activate(d.get_native());spin(duration=.3)
                                scrolls=[v for v in walk(d) if isinstance(v,Gtk.ScrolledWindow) and v.get_mapped() and v.get_vadjustment().get_upper()>v.get_vadjustment().get_page_size()]
                                if scrolls:scrolls[0].get_vadjustment().set_value(0);spin()
                                prefix='preferences-'+name+('-small' if small else '-wide');shot(prefix+'-top')
                                if scrolls:
                                    adj=scrolls[0].get_vadjustment();adj.set_value(adj.get_upper()-adj.get_page_size());spin();shot(prefix+'-bottom')
                                d.close();spin();n.activate(w)
                            finally:settings.set_property('gtk-font-name',font)
                    report['sections']['preferences']=dict(reading_page=not args.baseline)
                if chosen('navigation'):
                    t.navigate('FreSegond1910','John.3.16');settled()
                    for mode,name in [('day','white'),('night','dark')]:
                        palette(mode,name,style)
                        for small in (False,True):
                            w.set_default_size(560 if small else 1280,800 if small else 900);spin();w.choose_passage();spin(duration=.5);shot('navigation-'+name+('-small' if small else '-wide'));w.navigation.popdown();spin()
                    report['sections']['navigation']=dict(verse_controls_present=hasattr(w.navigation,'verse'))
                if chosen('immersion'):
                    cases=[];w.appearance.update('size',24)
                    for mode,name,width in [('day','white',1600),('night','dark',720)]:
                        palette(mode,name,style);w.set_default_size(width,900);spin();t.navigate('FreBDM1707','Gen.6.1');settled();w.study_button.set_active(False);w.enter_immersion('bible');v=w.immersion;spin(lambda:v.layout_ready,timeout=90);v.hide_controls();spin(duration=.5)
                        prefix='immersion-'+name;shot(prefix+'-start');video=None;inputs=[]
                        try:
                            video=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','x11grab','-framerate','60','-video_size',f'{screen.width}x{screen.height}','-i',os.environ['DISPLAY'],'-c:v','libx264','-preset','ultrafast','-crf','18','-pix_fmt','yuv420p',str(args.output/(prefix+'.mp4'))],stdin=subprocess.DEVNULL)
                            spin(duration=.4)
                            for key in ['Right','Left','Right','Right','Left','Left']:
                                before=v.stream.cursor;n.key(key);spin(duration=.35);inputs.append(dict(key=key,turned=v.stream.cursor!=before))
                            shot(prefix+'-end')
                        finally:
                            if video:video.send_signal(signal.SIGINT);video.wait(timeout=15);assert video.returncode in (0,255)
                        assert all(r['turned'] for r in inputs);cases.append(dict(palette=name,inputs=inputs,columns=v.count,reading_box=list(v.reading_box)));w.leave_immersion();spin()
                    report['sections']['immersion']=cases
        finally:
            (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');close_test_dialogs();w.close();n.close()
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
