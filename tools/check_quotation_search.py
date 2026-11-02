"""Actual offline Semeur/KJV quotations and native search latency; research only."""
import argparse,hashlib,inspect,io,json,time
from pathlib import Path
from unittest.mock import patch


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--baseline',action='store_true');p.add_argument('--require-packaged',action='store_true');p.add_argument('--prepare',action='store_true');a=p.parse_args()
    assert (a.profile/'.source-rendering-research').is_file();a.output.mkdir(parents=True,exist_ok=True)
    from bible.ui import Application,Window,Library,Gtk,GLib
    from bible.library import catalogue,download
    from bible.providers import PROVIDERS
    from bible.youversion_install import resource_from_metadata,acknowledgement
    from bible.youversion_editions import METADATA_URL
    from tests.test_ui import spin
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    library=Library(a.profile/'translations')
    if a.prepare:
        if 'youversion~YV21' not in library.installed():
            received=io.BytesIO();download(METADATA_URL.format(edition=21),received,limit=2*1024*1024,same_origin=True)
            resource=resource_from_metadata(json.loads(received.getvalue()),21)
            library.install(resource,permission=acknowledgement(resource))
        if 'KJV' not in library.installed():
            resources=catalogue(next(p for p in PROVIDERS if p.id=='crosswire'))
            library.install(next(r for r in resources if r.name=='KJV'))
    def hashes():return {str(f.relative_to(library.root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in library.root.rglob('*') if f.is_file()}
    before=hashes();app=Application.get_default() or Application();app.register();records=[]
    def walk(widget):
        yield widget
        child=widget.get_first_child()
        while child:yield from walk(child);child=child.get_next_sibling()
    with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False),patch('bible.catalogue_session.CatalogueSession.load_youversion_language',return_value=None):
        w=Window(app,library);w.set_default_size(1100,820);w.present();n=X11Input();n.activate(w);screen=Screen(n)
        try:
            t=w.active_tab;t.state.comparison=None;w.sync_comparison();t.navigate('FreSegond1910','Gen.1.1');w.study_button.set_active(False);spin(lambda:not t._restoring_scroll)
            with SystemStyleOverride() as style:
                for dark in (False,True):
                    style.set(dark=dark,high=False);w.appearance.update('mode','night' if dark else 'day');w.appearance.update('night_palette' if dark else 'day_palette','dark' if dark else 'white')
                    for module,query,expected in [('youversion~YV21','Car Dieu a tant aimé le monde','close'),('youversion~YV21','"Car Dieu a tant aimé le monde"','none'),('youversion~YV21','DIEU TANT AIME MONDE','strict'),('KJV','For God so loved the world','strict'),('KJV','For God dearly loved the world','close')]:
                        w.choose_passage();nav=w.navigation;nav.modes.set_visible_child_name('text');panel=nav.text_search
                        panel.source.set_selected(panel.search_names.index(module));panel.scope.set_selected(panel.scope_names.index('all'))
                        panel.entry.set_text(query);panel.changed();spin(duration=.2)
                        intervals=[];previous=time.monotonic()
                        def heartbeat():
                            nonlocal previous
                            now=time.monotonic();intervals.append((now-previous)*1000);previous=now;return True
                        timer=GLib.timeout_add(16,heartbeat);started=time.monotonic();panel.run_text()
                        try:spin(lambda:not panel.pending,duration=.1,timeout=90)
                        finally:GLib.source_remove(timer)
                        spin(duration=.2)  # A completed worker precedes the native row allocation/paint.
                        refs=[r.start for r in panel.rows];kinds=[getattr(r,'kind','strict') for r in panel.rows]
                        row=dict(module=module,query=query,references=refs[:20],kinds=kinds[:20],elapsed_seconds=time.monotonic()-started,max_main_loop_interval_ms=max(intervals,default=0),total=panel.total)
                        if not a.baseline:
                            if expected=='none':assert not refs,row
                            else:
                                assert refs and refs[0]=='John.3.16',row
                                assert kinds[0]==expected,row
                        records.append(row);screen.grab(a.output/(f'{"dark" if dark else "light"}-{module}-{expected}-{len(records)}.png'))
                        if refs and (not a.baseline or expected=='strict'):
                            buttons=[b for b in walk(panel.results) if isinstance(b,Gtk.Button) and hasattr(b,'_result')]
                            n.click(buttons[0]);spin()
                            assert w.reference_preview.target==(module,refs[0]),(row,dict(preview_open=w.reference_preview.popover is not None,generation=panel.generation,model_rows=panel.model.get_n_items(),pending=panel.pending))
                            assert t.state.resource=='FreSegond1910' and t.state.reference=='Gen.1.1'
                            w.reference_preview.dismiss()
                        nav.popdown();spin()
                    # Same query with an explicit scope excluding John must not leak it.
                    w.choose_passage();nav.modes.set_visible_child_name('text');panel.source.set_selected(panel.search_names.index('KJV'))
                    panel.scope.set_selected(panel.scope_names.index('book'));panel.entry.set_text('For God dearly loved the world');panel.changed();spin(duration=.2);panel.run_text();spin(lambda:not panel.pending,timeout=90)
                    assert 'John.3.16' not in [r.start for r in panel.rows]
                    nav.popdown()
        finally:w.close();n.close()
    assert before==hashes(),'A source resource changed during search'
    (a.output/'verification.json').write_text(json.dumps(dict(app_import=inspect.getfile(Window),baseline=a.baseline,gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],cases=records,unchanged_resource_files=len(before),manual_client_gnome_validation=False),ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
