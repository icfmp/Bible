"""Real-resource GTK checks for the study/navigation follow-up batch.

Use a marked disposable profile only. Captures remain private; JSON contains
references, metadata and measurements, never a Scripture dump or user notes.
"""
import argparse,hashlib,inspect,json,time
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    for flag in ('prepare','offline','baseline','require-packaged'):p.add_argument('--'+flag,action='store_true')
    a=p.parse_args();marker=a.profile/'.study-followups-profile';a.output.mkdir(parents=True,exist_ok=True)
    if a.prepare:
        assert not a.profile.exists() or marker.exists(),'Unmarked profile'
        a.profile.mkdir(parents=True,exist_ok=True);marker.write_text('Disposable study follow-up verification\n')
    assert marker.is_file()
    if a.offline:assert not a.prepare and len(Path('/proc/net/route').read_text().splitlines())<=1
    from bible.library import Library,catalogue
    from bible.youversion_install import fetch_resource,acknowledgement
    library=Library(a.profile/'translations')
    if a.prepare:
        resources=catalogue()
        for name in ('KJV','FreJND','FreSegond1910'):
            if name not in library.installed():library.install(next(r for r in resources if r.id==name))
        for identifier in (21,93,104):
            if f'youversion~YV{identifier}' not in library.installed():
                resource=fetch_resource(identifier);library.install(resource,permission=acknowledgement(resource))
        from bible.reference_data import ReferenceData
        from bible.topic_data import TopicData
        for data in (ReferenceData(a.profile/'study-data'),TopicData(a.profile/'study-data')):
            if data.revision is None:data.install()
    from bible.ui import Application,Window,Gtk
    from bible.step_data import StepData
    from bible.reference_resolution import resolve
    from bible.passage_actions import target
    from bible.i18n import tr
    from tests.test_ui import spin
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    app=Application();app.register();w=Window(app,library);w.set_default_size(1200,900);w.present()
    native=X11Input();screen=Screen(native);Gtk.Settings.get_default().props.gtk_enable_animations=False
    report=dict(app_import=inspect.getfile(Window),ui_sha256=hashlib.sha256(Path(inspect.getfile(Window)).read_bytes()).hexdigest(),
        gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],renderer=type(w.get_renderer()).__name__,
        baseline=a.baseline,offline=a.offline,cases=[])
    if a.require_packaged:assert 'GL' in report['renderer']
    def hashes():return {str(p.relative_to(library.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in library.root.rglob('*') if p.is_file()}
    before=hashes();notes_before=w.notes_store.all()
    def save():(a.output/('followups-offline.json' if a.offline else 'followups.json')).write_text(json.dumps(report,indent=2)+'\n')
    def settled():spin(lambda:not w.active_tab._restoring_scroll and not getattr(w.active_tab,'_comparison_positioning',False),duration=.25,timeout=60)
    def capture(name):
        native.move_at(w,2,2);spin(duration=.2);screen.grab(a.output/(('offline-' if a.offline else '')+name+'.png'))
    def wait(predicate,seconds=180):
        spin(predicate,duration=.1,timeout=seconds)
    def walk(widget):
        yield widget
        child=widget.get_first_child()
        while child:yield from walk(child);child=child.get_next_sibling()
    try:
        if a.prepare:
            # Exercise actual active transfer, cancellation, retry and success
            # through Library. STEP is large enough to observe real progress.
            dialog=w.open_library('study');wait(lambda:not dialog.busy)
            resource=dialog.study_resources.resource('step-word-study')
            if StepData(a.profile/'study-data').revision is None:
                dialog.install(resource=resource)
                wait(lambda:dialog.progress.get_fraction()>0 or not dialog._transfer_busy)
                assert dialog._transfer_busy,'Download completed before cancellation observation'
                from tests.test_appearance import SystemStyleOverride
                with SystemStyleOverride() as style:
                    for dark in (False,True):
                        style.set(dark=dark,high=False)
                        for width in (1200,360):
                            dialog.set_default_size(width,760);spin(duration=.3)
                            capture('library-active-'+('dark' if dark else 'light')+'-'+str(width))
                            if not a.baseline:
                                assert dialog.transfer_footer.get_mapped()
                                assert not dialog.progress.get_show_text()
                                assert dialog.cancel_button.get_mapped()
                native.click(dialog.cancel_button);wait(lambda:not dialog._transfer_busy)
                assert StepData(a.profile/'study-data').revision is None
                report['library_cancelled_without_partial_index']=True;capture('library-cancelled')
                dialog.install(resource=resource);wait(lambda:dialog._transfer_busy)
                wait(lambda:dialog.progress.get_fraction()>0 or not dialog._transfer_busy)
                capture('library-retry-active');wait(lambda:not dialog._transfer_busy,600)
                assert dialog._phase!='error',dialog.status.get_text()
                assert StepData(a.profile/'study-data').revision is not None
                if not a.baseline:assert not dialog.transfer_footer.get_visible()
                capture('library-success');spin(duration=4.5)
                assert not dialog.status.get_visible() and not dialog.progress.get_visible()
                capture('library-success-dismissed');report['library_real_step_download_success']=True
            dialog.close();native.activate(w)
        elif StepData(a.profile/'study-data').revision is None:raise AssertionError('STEP data missing')
        pairs=(('FreJND','youversion~YV104','Gen.11.1','Gen.11.1'),
               ('youversion~YV104','FreJND','Gen.11.1','Gen.11.1'),
               ('youversion~YV21','youversion~YV104','Ps.33.1','Ps.33.1'),
               ('youversion~YV104','youversion~YV21','Ps.33.1','Ps.33.1'),
               ('KJV','FreSegond1910','Ps.3.1','Ps.3.2'),
               ('FreSegond1910','KJV','Ps.3.2','Ps.3.1'),
               ('KJV','youversion~YV104','Gen.31.55','Gen.32.1'),
               ('youversion~YV104','KJV','Gen.32.1','Gen.31.55'),
               ('youversion~YV21','youversion~YV93','Gen.11.3','Gen.11.3'),
               ('youversion~YV93','youversion~YV21','Gen.11.3','Gen.11.3'))
        for source,secondary,ref,expected in pairs:
            w.end_comparison();t=w.active_tab;t.navigate(source,ref);settled();t.state.comparison=secondary;w.sync_comparison();settled()
            record=dict(source=source,target=secondary,source_system=t.reader.versification,target_system=t._comparison_reader.versification,
                requested=ref,comparison=t.comparison_reference,document=t._comparison_document.key,
                aligned=t._comparison_aligned,diagnostic=t.comparison_status.get_tooltip_text(),directions=[])
            if not a.baseline:
                assert t.comparison_reference==expected,record
                assert t._comparison_aligned,record
                # Native gestures drive both directions; expected destinations
                # always come from the shared resolver, never pixel ratios.
                for side,view in (('primary',t.text),('comparison',t.comparison_text)):
                    for amount in (3,3,-2):
                        native.wheel(view,amount);spin(duration=.35);settled()
                        origin=t.visible_reference() if side=='primary' else t.comparison_visible_reference()
                        reader=t._comparison_reader if side=='primary' else t.reader
                        system=t.reader.versification if side=='primary' else t._comparison_reader.versification
                        try:mapped=resolve(origin,system,reader)
                        except ValueError:
                            record['directions'].append(dict(side=side,origin=origin,local_gap=True));continue
                        actual=t.comparison_visible_reference() if side=='primary' else t.visible_reference()
                        group=None
                        if getattr(t,'_shared_comparison',False):
                            group=next((row for row in t.comparison_rows.rows if origin in (row.primary if side=='primary' else row.secondary)),None)
                        matches_group=group is not None and actual in (group.secondary if side=='primary' else group.primary)
                        body_delta=None
                        if group is not None:
                            # Padding above a longer verse may leave the prior
                            # verse as the first native text iterator. Verify
                            # actual corresponding body anchors, not that
                            # iterator's printed number or a scroll ratio.
                            first=t._marker_ends if side=='primary' else t._comparison_markers
                            second=t._comparison_markers if side=='primary' else t._marker_ends
                            other=t.comparison_text if side=='primary' else t.text
                            group_source=next((r for r in (group.primary if side=='primary' else group.secondary) if r in first),None)
                            group_target=next((r for r in (group.secondary if side=='primary' else group.primary) if r in second),None)
                            if group_source and group_target:
                                y=view.get_iter_location(view.get_buffer().get_iter_at_offset(first[group_source])).y-view.get_visible_rect().y
                                other_y=other.get_iter_location(other.get_buffer().get_iter_at_offset(second[group_target])).y-other.get_visible_rect().y
                                body_delta=abs(y-other_y)
                        assert actual in (mapped.start,mapped.end) or matches_group or body_delta is not None and body_delta<=3,(source,secondary,side,origin,actual,mapped,body_delta)
                        record['directions'].append(dict(side=side,origin=origin,target=actual,
                            exact_target=mapped.start,body_anchor_delta_px=body_delta,
                            shared_group=dict(primary=group.primary,secondary=group.secondary) if group else None))
            report['cases'].append(record);save()
        w.end_comparison();t.navigate('youversion~YV21','Ps.34.18');settled()
        for mode in ('day','night'):
            w.appearance.update('mode',mode);w.set_default_size(1200,900);settled()
            w.study_button.set_active(True);w.study.tools.set_visible_child_name('references');refs=w.study.references
            wait(lambda:not refs.pending);adjustment=refs.scroll.get_vadjustment()
            report[mode+'_reference_start']=dict(value=adjustment.get_value(),maximum=adjustment.get_upper()-adjustment.get_page_size(),count=len(refs.rows))
            if not a.baseline:assert adjustment.get_value()==0
            capture('references-'+mode)
            if not a.baseline:
                adjustment.set_value(min(200,adjustment.get_upper()-adjustment.get_page_size()));spin()
                position=adjustment.get_value();refs.refresh();spin();assert abs(adjustment.get_value()-position)<1
            for width in (1200,360):
                w.set_default_size(width,820);spin(duration=.3);settled()
                w.split.set_show_sidebar(True);spin(duration=.3)
                assert refs.heading.get_mapped(),'Preview trigger is hidden'
                w.reference_preview.show(refs.heading,t.state.resource,t.reader,'Ps.91.15',source_system=t.reader.versification,
                    provenance='OpenBible.info · CC BY 4.0\nhttps://www.openbible.info/labs/cross-references/')
                spin();assert w.reference_preview.popover is not None
                capture('preview-'+mode+'-'+str(width))
                if not a.baseline:
                    assert not w.reference_preview.status.get_visible()
                    assert w.reference_preview.open_here.get_mapped() and w.reference_preview.open_new.get_mapped()
                w.reference_preview.dismiss()
                if w.split.get_collapsed():w.split.set_show_sidebar(False);spin(duration=.3)
                w.show_search('topics');spin();search=w.search_popover.topic_search
                from bible.topic_vocabulary import suggestions
                entries=suggestions('confiance' if tr('Themes')=='Thèmes' else 'trust')
                entry=next(e for e in entries if e[0]=='trust');search.choose(entry);wait(lambda:not search.pending)
                if not a.baseline:
                    search.results.scroll_to(search.model.get_n_items()-1,Gtk.ListScrollFlags.NONE,None);spin(duration=.4)
                    last=next(b for b in walk(search.results) if isinstance(b,Gtk.Button) and hasattr(b,'_result') and b._result[0]==search.rows[-1])
                    ok,bounds=last.compute_bounds(search.result_scroll);assert ok
                    assert bounds.get_y()+bounds.get_height()<=search.result_scroll.get_height()+1,(bounds,search.result_scroll.get_height())
                    assert last.has_css_class('reference-card')
                capture('themes-last-'+mode+'-'+str(width));w.search_popover.popdown()
            w.set_default_size(1200,900);t.navigate('youversion~YV21','Ps.34.10');settled()
            buffer=t.text.get_buffer();buffer.select_range(buffer.get_iter_at_offset(t._marker_ends['Ps.34.10']),buffer.get_iter_at_offset(t._verse_ranges['Ps.34.11'][1]))
            source=w.passage_actions.ordinary(t);value=target(t.text,source,lambda:w.passage_actions.ordinary(t))
            assert value.references==('Ps.34.10','Ps.34.11'),value.references
            words=w.study.words;words.open(value);wait(lambda:not words.pending);capture('original-passage-'+mode)
            if not a.baseline:
                buttons=[b for b in words.children() if hasattr(b,'_source_token')];assert buttons
                refs_in_order=tuple(dict.fromkeys(b._source_token['reference'] for b in buttons));assert len(refs_in_order)>=2
                native.click(buttons[0]);wait(lambda:not words.pending);assert words.stage=='word';capture('original-word-'+mode)
                assert not any(isinstance(c,Gtk.Expander) and c.get_label()==tr('Source notices') for c in words.children())
                action=next(b for b in words.children() if isinstance(b,Gtk.Button) and isinstance(b.get_child(),Gtk.Label) and b.get_child().get_text()==tr('Occurrences of this lemma'))
                native.click(action);wait(lambda:not words.pending);assert words.stage=='occurrences';capture('original-occurrences-'+mode)
                native.click(words.go_back);spin();native.click(words.go_back);wait(lambda:not words.pending);assert words.stage=='passage'
            words.leave();spin();t.text.get_buffer().place_cursor(t.text.get_buffer().get_start_iter())
            t.navigate('KJV','John.1.1');settled()
            source=w.passage_actions.ordinary(t);value=target(t.text,source,lambda:w.passage_actions.ordinary(t),t._marker_ends['John.1.1'])
            words.open(value);wait(lambda:not words.pending)
            if not a.baseline:
                tokens=[b._source_token for b in words.children() if hasattr(b,'_source_token')]
                assert tokens and all(token['language']=='grc' for token in tokens)
            capture('original-greek-'+mode);words.leave();spin()
            t.navigate('youversion~YV21','Ps.34.18');settled()
        assert before==hashes(),'Existing translations changed'
        assert notes_before==w.notes_store.all(),'Notes changed'
        report['existing_resource_files_preserved']=len(before);report['notes_preserved']=True;report['completed']=True;save()
    finally:save();w.close();native.close()


if __name__=='__main__':main()
