"""Actual X11 selection/study/download checks against a disposable real profile.

Original PNGs and fixed aggregate receipts only; never export a profile or corpus.
"""
import argparse,hashlib,inspect,json,sys,traceback
from pathlib import Path
from unittest.mock import patch


def walk(widget):
    yield widget
    child=widget.get_first_child()
    while child:
        yield from walk(child);child=child.get_next_sibling()


def prepare(root,topics):
    from bible.library import Library,catalogue
    from bible.youversion_install import fetch_resource,acknowledgement
    from bible.step_data import StepData
    from bible.place_data import PlaceData
    import gzip
    marker=root/'.selection-batch-profile'
    if root.exists() and not marker.exists():raise ValueError('Refusing an existing unmarked profile')
    root.mkdir(parents=True,exist_ok=True);marker.write_text('Disposable selection batch proof\n')
    library=Library(root/'translations');resources=catalogue()
    for name in ('KJV','FreSegond1910','MHC'):
        if name not in library.installed():library.install(next(r for r in resources if r.name==name))
    for identifier in (21,93):
        if 'youversion~YV'+str(identifier) not in library.installed():
            resource=fetch_resource(identifier);library.install(resource,permission=acknowledgement(resource))
    for data in (StepData(root/'study-data'),PlaceData(root/'study-data')):
        if data.revision is None:data.install()
    references=gzip.decompress((Path(__file__).resolve().parents[1]/'docs/evidence/client-feedback-20261027/fixtures/openbible-cross-references.sqlite3.gz').read_bytes())
    assert hashlib.sha256(references).hexdigest()=='9b3659752c477e1e3be89ae55562734eae55328d2299eac4b7985b8825b9e993'
    refpath=root/'study-data/openbible-cross-references.sqlite3'
    if not refpath.exists():refpath.write_bytes(references)
    if topics:
        payload=gzip.decompress(topics.read_bytes())
        assert hashlib.sha256(payload).hexdigest()=='90db0daa43b1981a82d66481dc07211e395eba5ab56c15a8ee57cdb06d1ec209'
        path=root/'study-data/openbible-topics.sqlite3'
        if not path.exists():path.write_bytes(payload)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--prepare',action='store_true');p.add_argument('--topics',type=Path)
    p.add_argument('--downloads-only',action='store_true');p.add_argument('--baseline',action='store_true');p.add_argument('--require-packaged',action='store_true');p.add_argument('--downloads',action='store_true')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    if args.prepare:prepare(args.profile,args.topics)
    assert (args.profile/'.selection-batch-profile').is_file(),'Disposable marked profile required'
    from bible.ui import Application,Window,Library,Gtk,GLib
    from bible.i18n import tr
    from tests.test_ui import spin,close_test_dialogs
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    from bible.topic_vocabulary import VOCABULARY
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    exceptions=[]
    def exception(kind,value,tb):
        exceptions.append(dict(type=kind.__name__,functions=[f.name for f in traceback.extract_tb(tb)]))
        traceback.print_exception(kind,value,tb)
    sys.excepthook=exception
    app=Application.get_default() or Application();app.register();library=Library(args.profile/'translations')
    with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):
        w=Window(app,library);w.set_default_size(1280,900);w.present();spin()
    n=X11Input();n.activate(w);screen=Screen(n);t=w.active_tab;actions=w.passage_actions
    report=dict(source_import=inspect.getfile(Window),gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],renderer=type(w.get_renderer()).__name__,baseline=args.baseline,captures=[],cases=[],downloads=[],exceptions=exceptions)
    if args.require_packaged:assert 'GL' in report['renderer']
    def save(): (args.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    def shot(name):
        n.move_at(w,1,1);spin(duration=.12);screen.grab(args.output/(name+'.png'));report['captures'].append(name+'.png');save()
    def settled():spin(lambda:not t._restoring_scroll,duration=.15,timeout=90)
    def pointer_selection(multiple=False):
        actions.dismiss();spin(duration=.4);b=t.text.get_buffer();start=t._marker_ends['John.1.1']+1
        end=t._marker_ends['John.1.2']+12 if multiple else start+8
        if not multiple:
            text=b.get_text(b.get_start_iter(),b.get_end_iter(),False);start=text.index('commencement',start);end=start+len('commencement')
        first=t.text.get_iter_location(b.get_iter_at_offset(start));last=t.text.get_iter_location(b.get_iter_at_offset(end))
        x,y=t.text.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,first.x,first.y+first.height//2)
        ex,ey=t.text.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,last.x,last.y+last.height//2)
        n.move_at(t.text,x,y);n.xtest.XTestFakeButtonEvent(n.display,1,True,0);n.x11.XFlush(n.display);spin(duration=.08)
        n.move_at(t.text,ex,ey);spin(duration=.08);n.xtest.XTestFakeButtonEvent(n.display,1,False,0);n.x11.XFlush(n.display)
        try:spin(lambda:actions.bar.get_visible(),duration=.15)
        except AssertionError:
            report['selection_failure']=dict(multiple=multiple,expected=[start,end],actual=[i.get_offset() for i in b.get_selection_bounds()],dragging=actions.dragging,intent=actions.intent,capture_idle=actions.capture_idle,points=[x,y,ex,ey])
            shot('selection-failure');raise
        assert actions.target and actions.target.native_selection
        return tuple(i.get_offset() for i in b.get_selection_bounds())
    def download(identifier):
        from bible.youversion_catalogue import editions
        resource=next(r for r in editions('fra') if r.name=='YV'+str(identifier))
        with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):d=w.open_library('bible')
        spin(lambda:not d.preparing and not d._building_rows);d._catalogue_requested=True
        d.source_filter.set_selected(d.source_ids.index('youversion'))
        d.language.set_selected(d.language.codes.index('fr'));d.request_youversion_language(force=True)
        spin(lambda:not d.session.youversion_loading and not d._building_rows and any(r.id==resource.id for r in d.filtered_resources),duration=.3,timeout=90)
        index=next(i for i,r in enumerate(d.filtered_resources) if r.id==resource.id)
        d.open_details(None,index);spin(lambda:not d.busy and not d._building_rows,duration=.3,timeout=90)
        assert d.selected_resource().id==resource.id
        if d.download_button.get_sensitive():n.click(d.download_button)
        spin(duration=.3)
        dialogs=[v for v in Gtk.Window.get_toplevels() if hasattr(v,'get_response_label') and v.get_mapped()]
        if not dialogs:
            spin(lambda:not d.busy,duration=.3,timeout=90)
            dialogs=[v for v in Gtk.Window.get_toplevels() if hasattr(v,'get_response_label') and v.get_mapped()]
        if dialogs:
            dialog=dialogs[-1];n.activate(dialog)
            button=next(v for v in walk(dialog) if isinstance(v,Gtk.Button) and v.get_label()==tr('I have the required permission'))
            n.click(button)
        spin(lambda:not d.busy,duration=.4,timeout=240)
        installed=resource.id in library.installed();message=d.status.get_text()
        report['downloads'].append(dict(edition=identifier,title=resource.description,installed=installed,error=message if not installed else None))
        shot('download-'+str(identifier));d.close();spin();n.activate(w)
        if not args.baseline:
            if identifier==104:assert installed,message
            if identifier==2367:assert not installed and 'SIR.1' in message,message
    try:
        if args.downloads:
            download(104);download(2367)
            if args.downloads_only:
                report['result']='PASS';save();return
        t.state.comparison=None;w.sync_comparison();w.study_button.set_active(False)
        # Independent passage-switch/commentary diagnosis uses genuine editions.
        for ref in ('Gen.10.1','Gen.11.1','Gen.12.2','Ps.3.3','Ps.51.3'):
            assert t.navigate('youversion~YV21',ref);settled();before=t.state.reference
            assert w.switch_translation('youversion~YV93');settled();after=t.state.reference
            if not args.baseline:assert before.rsplit('.',1)[0]==after.rsplit('.',1)[0],(before,after)
            report['cases'].append(dict(kind='translation-switch',before=before,after=after))
            assert w.switch_translation('youversion~YV21');settled()
        assert t.navigate('youversion~YV93','Gen.1.1');settled();w.study_button.set_active(True)
        w.study.tools.set_visible_child_name('commentaries');w.study.choices.set_selected(w.study.names.index('MHC'));w.study.refresh(force=True);spin(duration=.4)
        report['cases'].append(dict(kind='MHC',loaded=len(w.study.loaded),status=w.study.status.get_text()))
        if not args.baseline:assert w.study.loaded
        w.study_button.set_active(False)
        with SystemStyleOverride() as style:
            for dark,high,name in [(False,False,'light'),(True,False,'dark'),(False,True,'hc-light'),(True,True,'hc-dark')]:
                style.set(dark=dark,high=high);w.appearance.update('mode','night' if dark else 'day')
                if not high:w.appearance.update('night_palette' if dark else 'day_palette','dark' if dark else 'white')
                for width in (1280,560):
                    prefix=name+'-'+str(width);w.set_default_size(width,850);spin()
                    assert t.navigate('youversion~YV21','John.1.1');settled();w.study_button.set_active(False)
                    shot(prefix+'-header')
                    selected=pointer_selection();shot(prefix+'-selection')
                    if not args.baseline:
                        n.click(actions.highlight_buttons['yellow'][0]);n.click(actions.highlight_buttons['blue'][0]);n.click(actions.highlight_buttons['blue'][0])
                        assert all(w.highlights.entries[(t.reader.versification,r)]['color']=='blue' for r in actions.target.references)
                        assert tuple(i.get_offset() for i in t.text.get_buffer().get_selection_bounds())==selected
                    previous=(w.study.tool,w.study_button.get_active(),t.state.reference)
                    n.click(actions.word_button);spin(duration=.35)
                    words=w.study.words
                    if args.baseline and words.popover:
                        n.click(words.popover.get_child().get_child().get_last_child());spin(duration=.3)
                    spin(lambda:not words.pending,duration=.2,timeout=90);shot(prefix+'-word-study')
                    if not args.baseline:
                        assert words.dialog and words.dialog.get_visible();assert previous==(w.study.tool,w.study_button.get_active(),t.state.reference)
                        n.activate(words.dialog);n.key('Escape');spin();assert words.dialog is None and not words.pending
                    else:words.leave();w.study_button.set_active(previous[1]);spin()
                    n.activate(w);pointer_selection(True);shot(prefix+'-multi-selection');actions.dismiss()
                    w.show_search();w.search_popover.modes.set_visible_child_name('text');search=w.search_popover.text_search
                    search.source.set_selected(search.search_names.index('youversion~YV21'));search.entry.set_text('Je suis le chemin la vérité la vie');search.changed();search.run_text()
                    spin(lambda:not search.pending,duration=.3,timeout=90);shot(prefix+'-text-results');assert search.rows
                    w.search_popover.modes.set_visible_child_name('topics');topics=w.search_popover.topic_search
                    if topics.data.revision is not None:
                        topics.choose(next(e for e in VOCABULARY if e[0]=='anger'));spin(lambda:not topics.pending,duration=.25,timeout=90);shot(prefix+'-topic-results')
                    w.search_popover.popdown();assert t.navigate('youversion~YV21','Gen.11.3');settled();w.study_button.set_active(True)
                    w.study.tools.set_visible_child_name('references');w.study.refresh(force=True);refs=w.study.references
                    spin(lambda:not refs.pending,duration=.2,timeout=90);shot(prefix+'-references')
                    if not args.baseline:assert refs.model.get_n_items()==len(refs.rows) and not refs.view_all.get_visible()
                    report['cases'].append(dict(palette=name,width=w.get_width(),references=len(refs.rows),visible_references=refs.model.get_n_items()))
                    w.study_button.set_active(False)
                    from bible.place_cards import PlaceCards
                    assert t.navigate('youversion~YV21','Gen.11.2');settled();d=PlaceCards(w);d.set_default_size(min(width,640),700);d.present(w)
                    spin(lambda:not d.pending,duration=.2,timeout=90)
                    if d.rows:
                        d.open_place(d.rows[0]);spin(duration=.4);shot(prefix+'-place')
                        d.card_scroll.get_vadjustment().set_value(d.card_scroll.get_vadjustment().get_upper());spin();shot(prefix+'-place-last-reference')
                    d.close();spin();n.activate(w)
        # A very small window and large GNOME text must keep native controls
        # inside the Header Bar, without adding a second selector row.
        w.set_default_size(360,750);settings=Gtk.Settings.get_default();font=settings.props.gtk_font_name
        try:
            settings.props.gtk_font_name='Sans 18';spin(lambda:not w._controls_tick,duration=.4)
            shot('narrow-360-large-text')
            if not args.baseline:
                assert w.header.get_width()<=w.get_width()+4
                assert w.passage_button.get_height()<=w.menu.get_height()+16
                caption=w.primary_version.caption
                if len(caption.get_text())<=4:
                    assert caption.get_width()>=caption.create_pango_layout(caption.get_text()).get_pixel_size()[0]
        finally:settings.props.gtk_font_name=font
        assert not exceptions,exceptions
        report['result']='PASS';save()
    finally:w.close();close_test_dialogs();spin();n.close();save()


if __name__=='__main__':main()
