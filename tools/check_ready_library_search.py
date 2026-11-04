"""Installed native checks for #150/#165/#169/#172; export bounded receipts only."""
import argparse,faulthandler,gzip,hashlib,inspect,json,os,sys,traceback,urllib.request
from pathlib import Path

def main():
    faulthandler.enable()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--prepare',action='store_true');p.add_argument('--require-packaged',action='store_true');p.add_argument('--baseline',action='store_true')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    marker=args.profile/'.ready-library-search-profile'
    from bible.library import Library,catalogue
    if args.prepare:
        assert not args.profile.exists() or marker.exists(),'Unmarked profile'
        args.profile.mkdir(parents=True,exist_ok=True);marker.write_text('Disposable installed Library/search validation\n')
        lib=Library(args.profile/'translations')
        if 'KJV' not in lib.installed():lib.install(next(r for r in catalogue() if r.name=='KJV'))
        url='https://raw.githubusercontent.com/icfmp/Bible/1c82609a0947822908fdfab7d3b42f7b79146265/docs/evidence/alpha-performance/fixtures/openbible-topics.sqlite3.gz'
        payload=urllib.request.urlopen(url,timeout=60).read(2*1024*1024)
        assert hashlib.sha256(payload).hexdigest()=='f8d8ebe33c339f3f910c930fef1af5713ee9a154bdbb363d7abf1844452a8c2e'
        data=gzip.decompress(payload);assert hashlib.sha256(data).hexdigest()=='90db0daa43b1981a82d66481dc07211e395eba5ab56c15a8ee57cdb06d1ec209'
        target=args.profile/'study-data/openbible-topics.sqlite3';target.parent.mkdir(exist_ok=True)
        if not target.exists():target.write_bytes(data)
    assert marker.is_file()
    from bible.ui import Application,Window,Gtk
    from bible.i18n import tr
    from tests.test_ui import spin
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    errors=[]
    def exception(kind,value,tb):
        errors.append(dict(type=kind.__name__,functions=[f.name for f in traceback.extract_tb(tb)]));traceback.print_exception(kind,value,tb)
    sys.excepthook=exception
    app=Application.get_default() or Application();app.register()
    w=Window(app,Library(args.profile/'translations'));w.set_default_size(1200,850);w.present();spin()
    w.application_settings.set('automatic_catalogue_refresh',False)
    n=X11Input();n.activate(w);screen=Screen(n);t=w.active_tab
    report=dict(baseline=args.baseline,app_import=inspect.getfile(Window),ui_sha256=hashlib.sha256(Path(inspect.getfile(Window)).read_bytes()).hexdigest(),gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],renderer=type(w.get_renderer()).__name__,language=os.environ.get('LANGUAGE'),captures=[],geometry=[],search=[],exceptions=errors)
    if args.require_packaged:assert 'GL' in report['renderer']
    def save():(args.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    def shot(name):
        n.move_at(w,1,1);spin(duration=.15);screen.grab(args.output/(name+'.png'));report['captures'].append(name+'.png');save()
    def settled():spin(lambda:not t._restoring_scroll and not getattr(t,'_comparison_positioning',False),duration=.3,timeout=90)
    def control_key(name):
        code=n.x11.XKeysymToKeycode(n.display,n.x11.XStringToKeysym(b'Control_L'))
        n.xtest.XTestFakeKeyEvent(n.display,code,True,0)
        try:n.key(name)
        finally:n.xtest.XTestFakeKeyEvent(n.display,code,False,0);n.x11.XFlush(n.display)
    try:
        # Real catalogue and HTTPS transfer through the application's Library.
        d=w.open_library('bible');spin(lambda:not d.preparing,duration=.2,timeout=90)
        d.source_filter.set_selected(d.source_ids.index('crosswire'));d.load_catalogue(force=True)
        spin(lambda:not d.busy and not d._building_rows,duration=.3,timeout=150)
        assert 'fr' in d.language.codes,d._catalogue_errors
        d.language.set_selected(d.language.codes.index('fr'));spin(lambda:not d._building_rows,duration=.3)
        d.search.set_text('FreSegond1910');d.filter_resources();spin(lambda:not d._building_rows,duration=.3)
        index=next(i for i,r in enumerate(d.filtered_resources) if r.id=='FreSegond1910')
        d.open_details(None,index);spin(duration=.3);n.click(d.download_button)
        spin(lambda:not d._transfer_busy,duration=.2,timeout=180)
        assert 'FreSegond1910' in w.library.installed(),d.status.get_text()
        toast=getattr(d,'_success_toast',None)
        if not args.baseline:
            assert toast and toast.get_title().startswith(tr('Installed: {name}').split('{')[0])
            assert not d.status.get_visible() and not d.progress.get_visible()
        report['download']=dict(resource='FreSegond1910',installed=True,toast=toast.get_title() if toast else None,footer_visible=d.status.get_visible(),progress_visible=d.progress.get_visible())
        shot('library-install-completion');spin(duration=5,timeout=7);shot('library-after-five-seconds')
        if not args.baseline:assert not d.status.get_visible() and not d.progress.get_visible()
        d.close();spin();d=w.open_library('bible');spin(lambda:not d.busy,duration=.2,timeout=90)
        if not args.baseline:assert d._success_toast is None and not d.status.get_visible()
        d.close();spin();n.activate(w)
        assert t.navigate('FreSegond1910','John.1.1');settled()
        with SystemStyleOverride() as style:
            for dark in (False,True):
                style.set(dark=dark,high=False);w.appearance.update('mode','night' if dark else 'day')
                for width in (1200,360):
                    w.set_default_size(width,850);spin(lambda:not w._controls_tick,duration=.4)
                    prefix=('dark' if dark else 'light')+'-'+str(width)
                    shot(prefix+'-header')
                    # Native shortcut and pointer entry exercise the same dedicated popup.
                    nav=w.navigation if args.baseline else w.search_popover
                    control_key('g' if args.baseline else 'f');spin(lambda:nav.get_visible(),duration=.3)
                    search=nav.text_search;n.click(nav.mode_buttons['text'])
                    search.entry.set_text('commencement');n.click(search.entry);n.key('Return');spin(lambda:not search.pending,duration=.5,timeout=90)
                    assert search.rows;before=list(search.rows);generation=search.generation;shot(prefix+'-text-search')
                    n.key('Escape');spin(lambda:not nav.get_mapped(),duration=.3)
                    control_key('g');spin(duration=.3)
                    focus=w.get_focus()
                    if args.baseline:n.click(w.navigation.mode_buttons['passage'])
                    report['passage_state']=dict(width=w.get_width(),navigation_visible=w.navigation.get_visible(),navigation_mapped=w.navigation.get_mapped(),active=w.is_active(),focus=type(focus).__name__,focus_mapped=focus.get_mapped() if focus else None,passage_button_active=w.passage_button.get_active())
                    shot(prefix+'-passage-state')
                    assert w.navigation.get_visible()
                    if not args.baseline:assert not w.search_popover.get_visible() and not hasattr(w.navigation,'modes')
                    shot(prefix+'-passage-only');n.key('Escape');spin(lambda:not w.navigation.get_mapped(),duration=.3)
                    control_key('g' if args.baseline else 'f');spin()
                    if not args.baseline:assert search.entry.get_text()=='commencement' and search.rows==before and search.generation==generation
                    n.click(nav.mode_buttons['topics']);topics=nav.topic_search
                    topics.entry.set_text('pardon');spin(duration=.4)
                    assert topics.topic_model.get_n_items()==4;shot(prefix+'-topic-search')
                    report['search'].append(dict(width=w.get_width(),dark=dark,text_results=len(before),pardon_concepts=topics.topic_model.get_n_items(),retained=not args.baseline))
                    n.key('Escape');spin(lambda:not nav.get_mapped(),duration=.3)
                    # #150: exercise each directly exposed colour with native
                    # clicks, including repeated selection of the same colour.
                    actions=w.passage_actions;b=t.text.get_buffer()
                    start=t._marker_ends['John.1.1']+3;end=start+8
                    first=t.text.get_iter_location(b.get_iter_at_offset(start));last=t.text.get_iter_location(b.get_iter_at_offset(end))
                    x,y=t.text.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,first.x,first.y+first.height//2)
                    ex,ey=t.text.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,last.x,last.y+last.height//2)
                    n.move_at(t.text,x,y);n.xtest.XTestFakeButtonEvent(n.display,1,True,0);n.x11.XFlush(n.display);spin(duration=.06)
                    n.move_at(t.text,ex,ey);n.xtest.XTestFakeButtonEvent(n.display,1,False,0);n.x11.XFlush(n.display)
                    spin(lambda:actions.bar.get_visible(),duration=.3)
                    selected=tuple(i.get_offset() for i in b.get_selection_bounds());assert selected
                    assert set(actions.highlight_buttons)=={'yellow','green','blue'} and not hasattr(actions,'compare_button')
                    for color in ('yellow','green','blue','blue'):
                        button=actions.highlight_buttons[color][0];assert button.get_mapped();n.click(button)
                        assert all(w.highlights.entries[(t.reader.versification,r)]['color']==color for r in actions.target.references)
                        assert tuple(i.get_offset() for i in b.get_selection_bounds())==selected
                    shot(prefix+'-direct-colours');n.click(actions.close_button);spin()
            for width,study in ((1200,False),(1200,True),(850,False)):
                w.set_default_size(width,850);w.study_button.set_active(study)
                t.state.comparison='KJV';w.sync_comparison();settled();spin(lambda:not w._controls_tick,duration=.4)
                for chooser,pane in ((w.primary_version,t.primary_controls),(w.compared_version,t.comparison_controls)):
                    ok,bounds=chooser.caption.compute_bounds(chooser);assert ok
                    center=bounds.origin.x+bounds.size.width/2
                    record=dict(width=w.get_width(),study=study,comparison=chooser is w.compared_version,button=chooser.get_width(),pane=pane.get_width(),caption_center=center)
                    report['geometry'].append(record);save()
                    if not args.baseline:assert chooser.get_width()>=pane.get_width()-4 and abs(center-chooser.get_width()/2)<=2,record
                shot('comparison-'+str(width)+('-study' if study else ''))
        assert not errors,errors
        report['completed']=True;save()
    finally:save();w.close();spin();n.close()

if __name__=='__main__':main()
