"""Installed GTK comparison contexts over real downloaded resources."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--prepare',action='store_true');p.add_argument('--offline',action='store_true')
    p.add_argument('--require-packaged',action='store_true');a=p.parse_args()
    marker=a.profile/'.ready-alignment-profile'
    if a.prepare:
        assert not a.profile.exists() or marker.is_file(),'Unmarked profile'
        a.profile.mkdir(parents=True,exist_ok=True);marker.write_text('Disposable real-resource comparison validation\n')
    assert marker.is_file()
    if a.offline:
        assert not a.prepare
        assert len(Path('/proc/net/route').read_text().splitlines())<=1,'Network routes remain available'
    from bible.library import Library,catalogue
    from bible.youversion_install import fetch_resource,acknowledgement
    library=Library(a.profile/'translations')
    if a.prepare:
        resources=catalogue()
        for name in ('KJV','FreJND','FreSegond1910'):
            if name not in library.installed():library.install(next(r for r in resources if r.id==name))
        for edition in (104,21,93):
            if f'youversion~YV{edition}' not in library.installed():
                item=fetch_resource(edition);library.install(item,permission=acknowledgement(item))
    names=('KJV','FreJND','FreSegond1910','youversion~YV104','youversion~YV21','youversion~YV93')
    assert all(name in library.installed() for name in names)
    def hashes():
        return {str(p.relative_to(library.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in library.root.rglob('*') if p.is_file()}
    before=hashes()
    from bible.ui import Application,Window,Gtk
    from tests.test_ui import spin
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    app=Application();app.register();w=Window(app,library);w.set_default_size(1200,900);w.present();spin()
    n=X11Input();n.activate(w);screen=Screen(n);a.output.mkdir(parents=True,exist_ok=True)
    report=dict(app_import=inspect.getfile(Window),ui_sha256=hashlib.sha256(Path(inspect.getfile(Window)).read_bytes()).hexdigest(),
                gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],
                renderer=type(w.get_renderer()).__name__,network_disabled=a.offline,cases=[])
    if a.require_packaged:assert 'GL' in report['renderer']
    def save():(a.output/('alignment-offline.json' if a.offline else 'alignment.json')).write_text(json.dumps(report,indent=2)+'\n')
    def settled():
        spin(lambda:not w.active_tab._restoring_scroll and not getattr(w.active_tab,'_comparison_positioning',False),duration=.4,timeout=60)
    def choose(button,name):
        n.click(button);spin(duration=.2)
        index=button.names.index(name);row=button.choices.list.get_row_at_index(index)
        button.choices.get_vadjustment().set_value(row.get_allocation().y);spin(duration=.2)
        n.click(row);spin(lambda:not button.popover.get_visible(),duration=.2);settled()
    def state():
        t=w.active_tab;b=t.comparison_text.get_buffer();first=b.get_start_iter();last=first.copy();last.forward_line()
        key=t._comparison_document.key
        document=key if isinstance(key,str) else key[0]
        return dict(source=t.state.resource,target=t.state.comparison,source_system=t.reader.versification,
                    target_system=t._comparison_reader.versification,primary=t.state.reference,
                    primary_chapter=t.current.reference,comparison=t.comparison_reference,
                    document=document,document_key=key,visible=t.comparison_visible_reference(),
                    title=b.get_text(first,last,False).strip(),aligned=t._comparison_aligned,
                    status=t.comparison_status.get_text(),saved=t.state.comparison_position)
    try:
        for source,target,reference,expected in (
                ('FreJND','youversion~YV104','Gen.11.1','Gen.11.1'),
                ('youversion~YV104','FreJND','Gen.11.1','Gen.11.1'),
                ('youversion~YV21','youversion~YV93','Gen.11.3','Gen.11.3'),
                ('youversion~YV93','youversion~YV21','Gen.11.3','Gen.11.3'),
                ('KJV','FreSegond1910','Ps.3.1','Ps.3.2'),
                ('FreSegond1910','KJV','Ps.3.2','Ps.3.1')):
            w.end_comparison();assert w.active_tab.navigate(source,reference);settled()
            w.active_tab.state.comparison=target;w.sync_comparison();settled()
            record=state();assert record['comparison']==expected,record
            assert record['document']==expected.rsplit('.',1)[0],record
            assert record['visible'].rsplit('.',1)[0]==record['document'],record
            if source in ('FreJND','youversion~YV104'):
                assert not record['aligned'] and record['status'],record
                assert record['primary_chapter']==record['document']=='Gen.11',record
            else:assert record['aligned'],record
            report['cases'].append(record);save()
        # Real selector changes must use the same context as initial opening.
        w.end_comparison();assert w.active_tab.navigate('FreJND','Gen.11.1');settled()
        w.active_tab.state.comparison='KJV';w.sync_comparison();settled()
        choose(w.compared_version,'youversion~YV104')
        assert state()['document']=='Gen.11',state()
        report['selector_change']=state()
        with SystemStyleOverride() as style:
            for dark in (False,True):
                style.set(dark=dark,high=False)
                for width in (1200,760):
                    w.set_default_size(width,820);spin(duration=.5);settled()
                    record=state();assert record['document']=='Gen.11',record
                    screen.grab(a.output/(('offline-' if a.offline else '')+('dark' if dark else 'light')+'-'+str(width)+'-darby-nbs.png'))
        # An unsupported pair reads independently when the primary navigates.
        n.wheel(w.active_tab.comparison_text,3);settled()
        assert w.active_tab.navigate('FreJND','Gen.12.1');settled()
        w.sync_comparison();settled();assert state()['document']=='Gen.11',state()
        report['independent_refresh']=state()
        w.close();spin();w=Window(app,library);w.set_default_size(1200,900);w.present();settled()
        report['restart']=state();assert report['restart']['document']=='Gen.11',report['restart']
        assert report['restart']['primary_chapter']=='Gen.12',report['restart']
        assert hashes()==before,'Downloaded module bytes changed'
        report['module_files_preserved']=len(before);report['completed']=True;save()
    finally:save();w.close();n.close();spin()


if __name__=='__main__':main()
