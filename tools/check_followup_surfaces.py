"""Retained real study data and native reader follow-up evidence, no client profile."""
import argparse,gzip,hashlib,inspect,json,time
from pathlib import Path
from unittest.mock import patch


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--ui-font');p.add_argument('--baseline',action='store_true');p.add_argument('--require-packaged',action='store_true');p.add_argument('--maps',action='store_true');a=p.parse_args()
    assert (a.profile/'.source-rendering-research').is_file();a.output.mkdir(parents=True,exist_ok=True)
    from bible.ui import Application,Window,Library,Gtk
    from tests.test_ui import spin
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    if a.ui_font:Gtk.init();Gtk.Settings.get_default().props.gtk_font_name=a.ui_font
    evidence_root=Path(__file__).resolve().parents[1]
    fixtures=[('docs/evidence/client-feedback-20261027/fixtures/openbible-cross-references.sqlite3.gz','9b3659752c477e1e3be89ae55562734eae55328d2299eac4b7985b8825b9e993'),('docs/evidence/topic-followups-146-147/fixtures/openbible-topics.sqlite3.gz','90db0daa43b1981a82d66481dc07211e395eba5ab56c15a8ee57cdb06d1ec209')]
    data_root=a.profile/'study-data';data_root.mkdir(exist_ok=True)
    for file,digest in fixtures:
        data=gzip.decompress((evidence_root/file).read_bytes());assert hashlib.sha256(data).hexdigest()==digest
        target=data_root/Path(file).stem
        if not target.exists():target.write_bytes(data)
    def hashes():return {str(f.relative_to(a.profile)):hashlib.sha256(f.read_bytes()).hexdigest() for base in ('translations','study-data') for f in (a.profile/base).rglob('*') if f.is_file()}
    if a.maps:
        from bible.place_data import PlaceData
        places=PlaceData(data_root)
        if places.revision is None:places.install()
    before=hashes();app=Application.get_default() or Application();app.register();records=[]
    def walk(widget):
        yield widget
        child=widget.get_first_child()
        while child:yield from walk(child);child=child.get_next_sibling()
    with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False),patch('bible.catalogue_session.CatalogueSession.load_youversion_language',return_value=None):
        w=Window(app,Library(a.profile/'translations'));w.set_default_size(1200,820);w.present();n=X11Input();n.activate(w);screen=Screen(n)
        try:
            t=w.active_tab;t.state.comparison=None;w.sync_comparison();t.navigate('FreSegond1910','Gen.11.3');spin(lambda:not t._restoring_scroll)
            with SystemStyleOverride() as style:
                for palette,mode in [('white','day'),('dark','night'),('paper','day'),('black','night')]:
                    style.set(dark=mode=='night',high=False);w.appearance.update('mode',mode);w.appearance.update('day_palette' if mode=='day' else 'night_palette',palette)
                    w.study_button.set_active(False);w.set_default_size(1200,820);spin(duration=.3);n.activate(w)
                    w.study_button.set_active(True);s=w.study;s.tools.set_visible_child_name('references');s.references.refresh(force=True)
                    spin(lambda:not s.references.pending,duration=.3)
                    refs=s.references
                    refs.list.scroll_to(0,Gtk.ListScrollFlags.FOCUS,None)
                    def first_reference():
                        return next((b for b in walk(refs.list) if isinstance(b,Gtk.Button)
                            and hasattr(b,'_reference_item') and b._reference_item.generation==refs.generation
                            and b._reference_item.relationship==refs.rows[0] and b.get_mapped()
                            and b.get_width()>0 and b.get_height()>0),None) if refs.rows else None
                    spin(lambda:first_reference() is not None,duration=.2)
                    button=first_reference();screen.grab(a.output/(palette+'-references.png'))
                    target=button._reference_item.relationship.start
                    n.click(button);spin();assert w.reference_preview.popover is not None,(palette,refs.generation)
                    assert t.state.reference=='Gen.11.3';w.reference_preview.dismiss()
                    records.append(dict(surface='references',palette=palette,total=len(refs.rows),first_source_target=target))
                    w.study_button.set_active(False)
                    for width,height in [(1000,800),(360,440)]:
                        w.set_default_size(width,height);spin(duration=.3);w.show_search();nav=w.search_popover;nav.modes.set_visible_child_name('topics');panel=nav.topic_search
                        panel.entry.set_text('');panel.changed();spin(duration=.3)
                        panel.topic_scroll.get_vadjustment().set_value(0);spin(duration=.2)
                        screen.grab(a.output/(f'{palette}-topics-{width}.png'))
                        row=dict(surface='topics',palette=palette,width=w.get_width(),height=w.get_height(),entries=panel.topic_model.get_n_items(),list_height=panel.topic_scroll.get_height(),popover_height=nav.get_height(),first_labels=[panel.topic_model.get_item(i).value[0] for i in range(min(4,panel.topic_model.get_n_items()))])
                        if not a.baseline:
                            assert row['entries']==50,row
                            n.click(panel.credit);spin(lambda:panel.credit.get_popover().get_mapped())
                            n.key('Escape');spin()
                            assert nav.get_visible() and not panel.credit.get_popover().get_visible(),row
                            assert row['list_height']>=(60 if width<600 else 200),row
                            assert abs(panel.topic_pages.get_height()-row['list_height'])<=2,row
                            assert row['popover_height']<=w.get_height(),row
                            first=next(b for b in walk(panel.topics) if isinstance(b,Gtk.Button) and hasattr(b,'_topic'))
                            first.grab_focus();spin(duration=.2);n.key('End');spin()
                            adj=panel.topic_scroll.get_vadjustment()
                            row['keyboard_end_scroll']=adj.get_value()
                            assert adj.get_value()>0,row
                            n.wheel(panel.topics,40);spin()
                            assert adj.get_value()+adj.get_page_size()>=adj.get_upper()-2,row
                            screen.grab(a.output/(f'{palette}-topics-bottom-{width}.png'))
                        records.append(row);nav.popdown();spin()
                    if not a.baseline:
                        # Retained real topic relationships: pointer first/subsequent
                        # rows, keyboard activation, dismissal and reopening.
                        w.set_default_size(1000,800);spin();w.show_search();nav.modes.set_visible_child_name('topics')
                        panel.entry.set_text('love');panel.changed()
                        topic_button=lambda:next((b for b in walk(panel.topics) if isinstance(b,Gtk.Button)
                            and hasattr(b,'_topic') and b._topic[0]=='love' and b.get_mapped()
                            and b.get_width()>0 and b.get_height()>0),None)
                        spin(lambda:topic_button() is not None,duration=.1);n.click(topic_button())
                        spin(lambda:not panel.pending and len(panel.rows)>1,duration=.1)
                        generation=panel.generation;origin=(t.state.resource,t.state.reference)
                        for index,key in [(0,False),(1,False),(0,True)]:
                            panel.results.scroll_to(index,Gtk.ListScrollFlags.FOCUS,None)
                            def result_button():
                                return next((b for b in walk(panel.results) if isinstance(b,Gtk.Button)
                                    and getattr(b,'_result',None)==(panel.rows[index],panel.generation)
                                    and b.get_mapped() and b.get_width()>0 and b.get_height()>0),None)
                            spin(lambda:result_button() is not None,duration=.2)
                            button=result_button()
                            if key:button.grab_focus();n.key('Return')
                            else:n.click(button)
                            spin(lambda:w.reference_preview.popover is not None,duration=.3)
                            assert panel.generation==generation and w.reference_preview.target is not None
                            assert (t.state.resource,t.state.reference)==origin
                            records.append(dict(surface='topic-activation',palette=palette,index=index,
                                keyboard=key,target=w.reference_preview.target,generation=generation))
                            if index==0 and not key:screen.grab(a.output/(palette+'-topic-first-preview.png'))
                            w.reference_preview.dismiss();spin()
                        nav.popdown();spin();w.show_search();spin()
                        assert len(panel.rows)>1 and panel.generation==generation
                        nav.popdown();spin()
            if a.maps:
                w.set_default_size(1200,820);spin()
                from bible.place_data import PlaceData
                store=PlaceData(data_root)
                for reference,name in [('Gen.11.2','Shinar'),('Josh.10.1','Jerusalem'),('Luke.24.13','Emmaus'),('Gen.4.16','Nod')]:
                    t.navigate('FreSegond1910',reference);spin(lambda:not t._restoring_scroll)
                    host=w.open_places();dialog=host.places;spin(lambda:not dialog.pending)
                    place=next(row for row in dialog.rows if row['name']==name)
                    dialog.open_place(place)
                    if dialog.map_widget:spin(lambda:dialog.map_widget.ready or dialog.map_widget.retry.get_visible(),timeout=40)
                    else:assert not any(c['longitude'] is not None for c in place['candidates'])
                    for palette,mode in [('white','day'),('dark','night')]:
                        # Use the same native source tiles and geometry in both themes.
                        with SystemStyleOverride() as map_style:
                            map_style.set(dark=mode=='night',high=False)
                            w.appearance.update('mode',mode)
                            w.appearance.update('day_palette' if mode=='day' else 'night_palette',palette)
                            for width in (640,360):
                                dialog.set_default_size(width,720);spin(duration=.4)
                                screen.grab(a.output/(f'place-{name}-{palette}-{width}.png'))
                    records.append(dict(surface='places',name=name,map_ready=dialog.map_widget.ready if dialog.map_widget else None,candidates=len(place['candidates']),status=place['status'],description=getattr(dialog,'location_description',dialog.passage_context).get_text()))
                    dialog.close();spin()
        finally:w.close();n.close()
    assert before==hashes(),'Research source data changed'
    (a.output/'verification.json').write_text(json.dumps(dict(app_import=inspect.getfile(Window),baseline=a.baseline,gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],cases=records,unchanged_source_files=len(before)),ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
