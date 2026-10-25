"""Real-resource study/navigation smoke check; disposable profiles only."""
import argparse
from dataclasses import asdict
import hashlib
import inspect
import json
from pathlib import Path
import time


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--prepare',action='store_true');parser.add_argument('--offline',action='store_true')
    parser.add_argument('--require-packaged',action='store_true');args=parser.parse_args()
    from bible.library import Library,catalogue
    from bible.step_data import StepData
    profile=args.profile;profile.mkdir(parents=True,exist_ok=True)
    library=Library(profile/'translations');data=StepData(profile/'study-data')
    if args.offline:
        assert not args.prepare
        assert len(Path('/proc/net/route').read_text().splitlines())<=1,'Network routes remain available'
    if args.prepare:
        resources=catalogue()
        for name in ('FreSegond1910','KJV','Wesley'):
            if name not in library.installed():library.install(next(r for r in resources if r.name==name))
        if data.revision is None:data.install()
    assert all(name in library.installed() for name in ('FreSegond1910','KJV','Wesley'))
    from bible.ui import Application,Window,GLib
    from bible.passage_actions import target
    from tests.test_ui import spin
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    def wait(predicate,timeout=90):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            GLib.MainContext.default().iteration(False)
            if predicate():spin(duration=.15);return
            time.sleep(.005)
        raise AssertionError('Study task did not settle')
    def hashes():
        return {str(p.relative_to(library.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in library.root.rglob('*') if p.is_file()}
    resources_before=hashes()
    app=Application();app.register();window=Window(app,library);window.set_default_size(1280,850);window.present();spin()
    report=dict(app_import=inspect.getfile(Window),network_disabled=args.offline)
    try:
        tab=window.active_tab
        if not window.notes_store.all():window.notes_store.save('Disposable validation note',[],versification='KJV',start='John.1.1',end='John.1.1',origin_translation='KJV',origin_language='en')
        notes_before=[asdict(n) for n in window.notes_store.all()]
        schema=window.notes_store.db.execute('PRAGMA user_version').fetchone()[0]
        tab.navigate('FreSegond1910','Ps.51.1');tab.state.comparison='KJV';window.sync_comparison();spin(duration=.8)
        assert tab._shared_comparison,tab.comparison_status.get_text()
        rows=tab.comparison_rows
        assert rows.rows[0].primary==('Ps.51.1','Ps.51.2','Ps.51.3')
        assert rows.rows[0].secondary==('Ps.51.1',)
        starts=[[view.get_iter_location(view.get_buffer().get_iter_at_offset(a)).y for a,b in rows.bounds[side]]
                for side,view in enumerate((tab.text,tab.comparison_text))]
        maximum=max(abs(a-b) for a,b in zip(*starts));assert maximum<=1
        assert tab.scroll.get_vadjustment() is tab.comparison_scroll.get_vadjustment()
        report['real_psalm_comparison']=dict(rows=len(rows.rows),maximum_row_delta_pixels=maximum)
        from bible.word_metadata import source_verse_references
        for title in ('Ps.3.1','Ps.51.1','Ps.51.2'):
            try:source_verse_references(title,tab.reader)
            except ValueError:pass
            else:raise AssertionError('Source title was collapsed into body words: '+title)
        assert source_verse_references('Ps.51.3',tab.reader)==('Ps.51.1',)
        source_tokens=data.verse('tahot-main','Ps.51.1')
        assert source_tokens and source_tokens[0]['form'].startswith('חָנֵּ')
        report['source_psalm_title_guard']=dict(rejected_numbered_titles=3,verified_body_mapping='Segond Ps.51.3 -> NRSV Ps.51.1')
        window.end_comparison();tab.navigate('FreSegond1910','John.1.1');spin(lambda:not tab._restoring_scroll)
        window.study_button.set_active(True);window.study.tools.set_visible_child_name('commentaries')
        window.study.choices.set_selected(window.study.names.index('Wesley'));window.study.refresh(force=True);spin(duration=.3)
        assert window.study.reader.name=='Wesley' and window.study.loaded
        loaded=list(window.study.loaded);document=window.study.text.get_buffer()
        tab.select_verse('John.1.2');window.study.refresh(force=True);spin(duration=.3)
        assert window.study.loaded==loaded and window.study.text.get_buffer() is document
        report['continuous_commentary_entries']=len(loaded)
        tab.navigate('FreSegond1910','Gen.1.1');spin(lambda:not tab._restoring_scroll)
        source=window.passage_actions.ordinary(tab)
        value=target(tab.text,source,lambda:window.passage_actions.ordinary(tab),tab._marker_ends['Gen.1.1'])
        words=window.study.words;words.open(value);wait(lambda:not words.pending)
        tokens=data.verse('tahot-main','Gen.1.1');assert len(tokens)==7
        token=next(t for t in tokens if 'H1254A' in t['tags']);words.token_detail('tahot-main',token);wait(lambda:not words.pending)
        assert words.entry['id']=='H1254A'
        counts=data.occurrences('tahot-main','H1254A');assert (counts['tokens'],counts['verses'])==(53,45)
        greek=data.occurrences('tagnt-na27','G3056');assert (greek['tokens'],greek['verses'])==(330,317)
        words.all_occurrences('tahot-main',words.entry);search=window.navigation.text_search;wait(lambda:not search.pending)
        assert search.total==counts['addresses'] and search.lemma_query==('tahot-main','H1254A')
        window.navigation.popdown();words.leave()
        report['real_step']=dict(greek_tokens=greek['tokens'],greek_verses=greek['verses'],hebrew_tokens=counts['tokens'],hebrew_verses=counts['verses'],source_words=len(tokens),shared_occurrence_search=True)
        assert [asdict(n) for n in window.notes_store.all()]==notes_before
        assert window.notes_store.db.execute('PRAGMA user_version').fetchone()[0]==schema
        assert hashes()==resources_before
        report.update(status='PASS',notes_unchanged=len(notes_before),module_files_unchanged=len(resources_before),sqlite_schema=schema)
    finally:window.close()
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
