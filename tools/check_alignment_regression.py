"""Real-resource #215 matrix on a marked disposable profile; no corpus export.

Run --prepare before baseline/candidate checks, then --offline after restart.
Resource IDs and expected vectors here are test data, never application policy.
"""
import argparse
from dataclasses import asdict
import hashlib
import inspect
import itertools
import json
from pathlib import Path
from unittest.mock import patch

BIBLES=('FreSegond1910','KJV','FreJND',*(f'youversion~YV{n}' for n in (21,93,104,133,152,2367)))
REPORTED=tuple(f'youversion~YV{n}' for n in (133,152,2367))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    for flag in ('prepare','baseline','offline','require-packaged','quick'):
        p.add_argument('--'+flag,action='store_true')
    a=p.parse_args();marker=a.profile/'.alignment-test-profile'
    if a.prepare:
        assert not a.profile.exists() or marker.is_file(),'Refusing an unmarked profile'
        a.profile.mkdir(parents=True,exist_ok=True);marker.write_text('Disposable alignment validation\n')
    assert marker.is_file();a.output.mkdir(parents=True,exist_ok=True)
    if a.offline:assert len(Path('/proc/net/route').read_text().splitlines())<=1
    from bible.library import Library,catalogue
    lib=Library(a.profile/'translations')
    if a.prepare:
        resources=catalogue()
        for name in ('FreSegond1910','KJV','FreJND','MHC','Wesley'):
            if name not in lib.installed():lib.install(next(r for r in resources if r.id==name))
        from bible.youversion_install import fetch_resource,acknowledgement
        for n in (21,93,104,133,152,2367):
            if f'youversion~YV{n}' not in lib.installed():
                resource=fetch_resource(n);lib.install(resource,permission=acknowledgement(resource))
    from bible.sword_provider import Reader,CommentaryReader
    from bible.reference_resolution import resolve,VersificationMismatch
    import bible.source_versification as source_metadata
    reference_mapping=getattr(source_metadata,'reference_mapping',lambda system:None)
    from bible.notes import NoteStore
    from bible.highlights import HighlightStore
    from bible.preferences import Preferences
    notes=NoteStore(a.profile/'notes.sqlite3')
    if not notes.all():notes.save('Synthetic retained alignment validation note',('retained',),versification='KJV',start='John.3.16',end='John.3.16',origin_translation='KJV',origin_language='en')
    highlights=HighlightStore(a.profile/'highlights.json')
    if not highlights.entries:highlights.set('KJV',['John.3.16'],'yellow','KJV')
    prefs=Preferences(a.profile/'reading-preferences.json')
    if not prefs.path.exists():prefs.save()
    saved_preferences=prefs.path.read_bytes()
    def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    def preserved():
        return dict(notes=digest([asdict(n) for n in notes.all()]),highlights=hashlib.sha256(highlights.path.read_bytes()).hexdigest(),
            preferences=hashlib.sha256(prefs.path.read_bytes()).hexdigest(),
            modules={str(f.relative_to(lib.root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in lib.root.rglob('*') if f.is_file()})
    before=preserved()
    from bible.ui import Application,Window,Gtk
    from bible.i18n import LANGUAGE
    from tests.test_ui import spin
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    if a.require_packaged:assert inspect.getfile(Window).startswith('/app/') and inspect.getfile(Reader).startswith('/app/')
    readers={name:Reader(lib.root/name,name) for name in BIBLES}
    report=dict(app_import=inspect.getfile(Window),source_sha256=hashlib.sha256(Path(inspect.getfile(resolve)).read_bytes()).hexdigest(),
        mapping_sha256=hashlib.sha256(Path(inspect.getfile(source_metadata)).read_bytes()).hexdigest(),
        language=LANGUAGE,baseline=a.baseline,offline=a.offline,resources={},resolver=[],gui=[],gestures=[],commentaries=[],unsupported=[],captures=[],complete=False)
    def save():(a.output/'alignment.json').write_text(json.dumps(report,indent=2)+'\n')
    for name,r in readers.items():
        capability=reference_mapping(r.versification)
        receipt=r.root/'.verified.json'
        source=json.loads(receipt.read_text()) if receipt.is_file() else {}
        report['resources'][name]=dict(system=r.versification,driver=r.module.getConfigEntry('ModDrv'),
            version=r.module.getConfigEntry('Version'),addresses=bool(r.addresses),declared=capability.get('declared_convention') if capability else None,
            verification={key:source.get(key) for key in ('source_numbering','storage_numbering','archive_sha256',
                'reference_index_sha256','source_addresses_sha256','all_text_notes_headings_verified')})
    if not a.baseline:
        # Expected references are independent of resolve(): KJV does not number
        # the Psalm 3 superscription as a verse; the other selected sources do.
        for left,right in itertools.permutations(BIBLES,2):
            source,target=readers[left],readers[right]
            vectors=[('Gen.1.1','Gen.1.1'),('Gen.11.3','Gen.11.3'),('John.3.16','John.3.16'),
                     ('Ps.3.2' if left=='KJV' else 'Ps.3.3','Ps.3.2' if right=='KJV' else 'Ps.3.3')]
            for origin,expected in vectors:
                mapped=resolve(origin,source.versification,target)
                assert (mapped.start,mapped.end)==(expected,expected),(left,right,origin,mapped,expected)
                report['resolver'].append(dict(source=left,target=right,reference=origin,expected=[expected,expected]))
        # The pinned JSword Segond verse-part table includes the numbered
        # superscription in an unqualified first-verse mapping. Do not collapse
        # that range to match a native SWORD route's narrower result.
        for left,origin,right,first,last in [('KJV','Ps.3.1','FreSegond1910','Ps.3.2','Ps.3.2'),
                ('FreSegond1910','Ps.3.2','KJV','Ps.3.1','Ps.3.1'),
                ('KJV','Ps.3.1','youversion~YV93','Ps.3.1','Ps.3.2'),
                ('youversion~YV93','Ps.3.2','KJV','Ps.3.1','Ps.3.1')]:
            mapped=resolve(origin,readers[left].versification,readers[right])
            assert (mapped.start,mapped.end)==(first,last)
            report['resolver'].append(dict(source=left,target=right,reference=origin,expected=[first,last]))
        # Actual chapter-boundary shift, not equal printed verse numbers.
        for left,origin,right,expected in [('KJV','Gen.31.55','youversion~YV104','Gen.32.1'),
                ('youversion~YV104','Gen.32.1','KJV','Gen.31.55')]:
            assert resolve(origin,readers[left].versification,readers[right]).start==expected
            report['resolver'].append(dict(source=left,target=right,reference=origin,expected=expected))
        # Modified/transformed books remain unavailable without a new claim.
        for name,ref in [('youversion~YV152','Num.25.1'),('youversion~YV133','Zech.4.1'),
                         ('youversion~YV133','Acts.19.1'),('youversion~YV2367','Acts.19.1')]:
            for reverse in (False,True):
                source,target=(readers['KJV'],readers[name]) if reverse else (readers[name],readers['KJV'])
                try:resolve(ref,source.versification,target,require_entry=False)
                except VersificationMismatch:pass
                else:raise AssertionError(('Unverified book gained a correspondence',name,ref,reverse))
                report['unsupported'].append(dict(resource=name,reference=ref,reverse=reverse))
    app=Application.get_default() or Application();app.register()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    w=Window(app,lib);w.set_default_size(1440,960);w.present();spin()
    native=X11Input();native.activate(w);screen=Screen(native)
    report.update(renderer=type(w.get_renderer()).__name__,gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()])
    def settled():
        t=w.active_tab
        spin(lambda:not t._restoring_scroll and not getattr(t,'_comparison_positioning',False),duration=.15,timeout=30)
        assert not t._restoring_scroll and not getattr(t,'_comparison_positioning',False)
    def shot(name):
        native.move_at(w,2,2);spin(duration=.1);screen.grab(a.output/(name+'.png'));report['captures'].append(name+'.png')
    def pair(left,right,ref):
        t=w.active_tab
        assert t.navigate(left,ref),(left,ref,t.status.get_text())
        t.state.comparison=right;w.sync_comparison();settled()
        assert t._comparison_reader and t._comparison_document,(left,right,t.comparison_status.get_text())
        assert t.current.reference==ref.rsplit('.',1)[0]
        row=dict(primary=left,secondary=right,requested=ref,primary_chapter=t.current.reference,
            comparison_reference=t.comparison_reference,comparison_document=str(t._comparison_document.key),
            aligned=t._comparison_aligned,shared_rows=getattr(t,'_shared_comparison',False),status=t.comparison_status.get_text())
        if not a.baseline:assert row['aligned'],row
        assert t._comparison_document.spans and t._document.spans
        if ref.startswith('Gen.'):
            assert all(s.reference.startswith(ref.rsplit('.',1)[0]+'.') for s in t._comparison_document.spans),row
        report['gui'].append(row);return t
    succeeded=False
    try:
        with patch('urllib.request.urlopen',side_effect=AssertionError('No network during reading validation')):
            expected_session=a.profile/'alignment-expected-session.json'
            if expected_session.is_file() and not a.baseline:
                restored=json.loads(expected_session.read_text());t=w.active_tab
                settled()
                assert t.state.resource==restored['primary'] and t.state.comparison==restored['secondary']
                assert t.state.reference.rsplit('.',1)[0]==restored['chapter'] and t._comparison_aligned
                report['restored_session_verified']=restored
            w.study.tools.set_visible_child_name('commentaries')
            if a.baseline:
                for name in REPORTED:
                    for left,right in [('FreSegond1910',name),(name,'FreSegond1910')]:
                        t=pair(left,right,'Gen.1.1');assert not t._comparison_aligned
                        w.study_button.set_active(True);t.state.commentary='MHC';w.study.refresh(force=True);settled()
                        assert bool(w.study.entry_text)==(left=='FreSegond1910')
                        report['commentaries'].append(dict(primary=left,name='MHC',has_text=bool(w.study.entry_text),status=w.study.status.get_text()))
                        shot(left.replace('~','-')+'-'+right.replace('~','-')+'-before')
            else:
                w.study_button.set_active(False)
                gui_pairs=itertools.permutations(BIBLES,2) if not a.quick else [('FreSegond1910',name) for name in REPORTED]+[(name,'FreSegond1910') for name in REPORTED]
                for left,right in gui_pairs:
                    for ref in ('Gen.1.1','Gen.11.3'):
                        pair(left,right,ref)
                for name in BIBLES:
                    t=pair(name,'KJV' if name!='KJV' else 'FreSegond1910','Gen.1.1')
                    w.study_button.set_active(True)
                    for commentary in ('MHC','Wesley','MHC'):
                        w.study.refresh(force=True)
                        w.study.choices.set_selected(w.study.names.index(commentary));settled()
                        target=w.study.reader;assert target and target.name==commentary
                        expected=resolve('Gen.1.1',t.reader.versification,target,require_entry=False)
                        assert w.study.entry_text and w.study.current_position==target.index.locate(expected.start),(name,commentary,w.study.status.get_text())
                        report['commentaries'].append(dict(primary=name,name=commentary,target=expected.start,index=w.study.current_position))
                    if name in REPORTED:shot(name.replace('~','-')+'-MHC-after')
                    w.study_button.set_active(False)
                for name in (*REPORTED,'youversion~YV104','youversion~YV21','FreJND'):
                    for left,right in [('KJV',name),(name,'KJV')]:
                        ref='Ps.119.1';t=pair(left,right,ref)
                        for side in ('primary','comparison','primary','comparison'):
                            view=t.text if side=='primary' else t.comparison_text
                            scroll=t.scroll if side=='primary' else t.comparison_scroll
                            before_scroll=scroll.get_vadjustment().get_value()
                            native.wheel(view,3 if side=='primary' else -2);settled()
                            assert t._comparison_aligned,(left,right,side,t.comparison_status.get_text())
                            assert abs(scroll.get_vadjustment().get_value()-before_scroll)>1,(left,right,side,'No actual scroll movement')
                            active=t.visible_reference() if side=='primary' else t.comparison_visible_reference()
                            source,target=(t.reader,t._comparison_reader) if side=='primary' else (t._comparison_reader,t.reader)
                            mapped=resolve(active,source.versification,target)
                            other=t.comparison_text if side=='primary' else t.text
                            offsets=t._comparison_offsets if side=='primary' else t._verse_offsets
                            assert mapped.start in offsets
                            location=other.get_iter_location(other.get_buffer().get_iter_at_offset(offsets[mapped.start]))
                            rect=other.get_visible_rect()
                            assert rect.y-40<=location.y<rect.y+rect.height,(left,right,side,active,mapped,location.y,rect.y)
                        report['gestures'].append(dict(primary=left,secondary=right,passage=ref,alternating_native_wheel=True))
                # Exercise native chooser activation, not just navigate().
                pair('FreSegond1910','youversion~YV104','Gen.11.3')
                for chooser,expected in ((w.primary_version,'youversion~YV152'),(w.compared_version,'youversion~YV2367'),
                                         (w.primary_version,'youversion~YV133'),(w.compared_version,'FreSegond1910')):
                    chooser.popup();spin(duration=.2)
                    row=chooser.choices.list.get_row_at_index(chooser.names.index(expected))
                    row.grab_focus();spin(duration=.2);native.key('Return');settled()
                    current=w.active_tab.state.comparison if chooser.comparison else w.active_tab.state.resource
                    assert current==expected,(current,expected)
                    assert w.active_tab._comparison_aligned
                report['native_selector_changes']=4
                for name in REPORTED:
                    t=pair('FreSegond1910',name,'Gen.1.1')
                    for mode in ('day','night'):
                        w.appearance.update('mode',mode);settled();shot(name.replace('~','-')+'-'+mode+'-after')
                # Restoring the original preference bytes below is only test
                # cleanup, never a production/profile reset.
                t=pair('youversion~YV133','youversion~YV2367','Gen.11.3')
                w.study_button.set_active(True);t.state.commentary='MHC';w.study.refresh(force=True);settled()
                assert w.study.entry_text
                expected_session.write_text(json.dumps(dict(primary=t.state.resource,secondary=t.state.comparison,chapter='Gen.11'))+'\n')
            succeeded=True
    finally:
        w.close();native.close()
        # Appearance changes were deliberate test actions. Return their exact
        # saved values before asserting preservation of all existing settings.
        if prefs.path.read_bytes()!=saved_preferences:prefs.path.write_bytes(saved_preferences)
        after=preserved();report['preserved']=before==after;report['checked_module_files']=len(before['modules'])
        report['complete']=succeeded and report['preserved'];save();notes.close()
        if succeeded:assert report['preserved'],'Existing annotations, preferences or module files changed'


if __name__=='__main__':
    main()
