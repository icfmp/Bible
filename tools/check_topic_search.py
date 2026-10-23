"""Native real-resource integrated search; only use a disposable validation profile."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import time
from gi.repository import Gtk,GLib
from bible.ui import Application,Window,Library
from bible.topic_data import TopicData
from bible.topic_vocabulary import suggestions
from bible.reference_targets import local_excerpt
from bible.i18n import tr
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input


def wait(predicate,timeout=90):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        GLib.MainContext.default().iteration(False)
        if predicate():spin(duration=.2);return
        time.sleep(.005)
    raise AssertionError('Search did not settle')


def walk(widget):
    yield widget
    child=widget.get_first_child()
    while child:yield from walk(child);child=child.get_next_sibling()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--download',action='store_true');p.add_argument('--offline',action='store_true')
    p.add_argument('--require-packaged',action='store_true');p.add_argument('--captures',type=Path)
    args=p.parse_args()
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    if args.offline:assert len(Path('/proc/net/route').read_text().splitlines())<=1
    app=Application();app.register();native=X11Input();Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    w=Window(app,Library(args.profile/'translations'));w.set_default_size(1440,950);w.present()
    report=dict(app_import=inspect.getfile(Window),network_disabled=args.offline,accessibility='Deferred; not tested')
    original_resources=w.library.installed();original_notes=w.notes_store.all()
    def capture(name):
        if args.captures:
            from PIL import ImageGrab
            args.captures.mkdir(parents=True,exist_ok=True);native.move_at(w,2,2);spin();ImageGrab.grab().save(args.captures/(name+'.png'))
    def settled():spin(lambda:not w.active_tab._restoring_scroll,duration=.3)
    def mode(name):
        native.click(next(b for b in walk(nav.mode_switcher) if isinstance(b,Gtk.ToggleButton) and b.get_child().get_text()==tr(name)));spin()
    def open_search(resource='FreSegond1910'):
        if w.navigation.get_visible():w.navigation.popdown();spin()
        w.active_tab.navigate(resource,'John.1.5');settled();native.click(w.passage_button);spin();return w.navigation
    def choose(source_id):
        button=next(b for b in walk(search.topics) if isinstance(b,Gtk.Button) and getattr(b,'_topic',('',))[0]==source_id and b.get_mapped())
        native.click(button);wait(lambda:not search.pending);assert search.rows
    def first_result(panel):
        return next(b for b in walk(panel.results) if isinstance(b,Gtk.Button) and hasattr(b,'_result') and b.get_mapped())
    try:
        nav=open_search();mode('Topics');search=nav.topic_search
        if args.download:
            assert not args.offline and search.download.get_visible();native.click(search.download);library=w.catalogue_window
            spin(lambda:library.download_button.get_mapped());assert not library._catalogue_requested
            assert 'creativecommons.org/licenses/by/4.0/' in library.metadata.get_text()
            started=time.monotonic();native.click(library.download_button);wait(lambda:not library.busy)
            assert library._phase!='error',library.status.get_text()
            report['native_library_download_seconds']=round(time.monotonic()-started,3)
            library.close();native.activate(w);native.click(w.passage_button);spin();mode('Topics')
        metadata=search.data.metadata();assert (metadata['topics'],metadata['relationships'],metadata['supported_topics'])==(6712,71358,50)
        report['dataset']=metadata
        search.entry.set_text('pardon');spin(duration=.3)
        assert {search.topic_model.get_item(i).value[0] for i in range(search.topic_model.get_n_items())}=={'forgiveness','forgiveness of sins','forgiving others','reconciliation'}
        capture('pardon-suggestions');choose('forgiveness of sins');capture('forgiveness-results')
        tab=w.active_tab;before=(tab.state.reference,list(tab.state.history),w.view.get_n_pages())
        button=first_result(search);native.click(button);spin();row=button._result[0]
        assert w.reference_preview.body.get_buffer().props.text==local_excerpt(nav.reader,row.start,row.end).text
        assert (tab.state.reference,tab.state.history,w.view.get_n_pages())==before;capture('local-preview')
        native.key('Escape');assert w.reference_preview.popover is None
        assert nav.get_visible(),'Escape dismissed the search instead of only the preview'
        button.grab_focus();native.key('Return');assert w.reference_preview.popover
        target=w.reference_preview.target;native.click(w.reference_preview.open_new);settled()
        assert not nav.get_visible() and w.view.get_n_pages()==before[2]+1
        assert (w.active_tab.state.resource,w.active_tab.state.reference)==target
        assert tab.state.reference==before[0] and tab.state.history==before[1]
        report['topic_preview']=dict(exact_installed_French=True,preserves_reading_and_history=True,native_pointer_keyboard_escape=True,explicit_new_tab=True)
        nav=open_search();mode('Topics');search.entry.set_text('réCONCILIATION');spin(duration=.3)
        assert search.topic_model.get_n_items()==1;choose('reconciliation')
        button=first_result(search);native.click(button);spin();target=w.reference_preview.target
        native.click(w.reference_preview.open_here);settled();assert w.active_tab.state.reference==target[1]
        nav=open_search('KJV');mode('Topics');search.entry.set_text('grace');spin(duration=.3);choose('grace')
        button=first_result(search);native.click(button);spin()
        assert w.reference_preview.body.get_buffer().props.text==local_excerpt(nav.reader,button._result[0].start,button._result[0].end).text
        native.key('Escape');search.entry.set_text('unrepresentedzzz');spin(duration=.3)
        assert search.topic_model.get_n_items()==0 and search.model.get_n_items()==0
        search.entry.set_text('pardon');spin(duration=.3);choose('forgiving others')
        ticks=[0];last=[time.monotonic()];gaps=[]
        def heartbeat():
            now=time.monotonic();gaps.append(now-last[0]);last[0]=now;ticks[0]+=1;return True
        timer=GLib.timeout_add(10,heartbeat)
        mode('Text');text=nav.text_search;text.entry.set_text('light of the world');spin(duration=.3)
        text.entry.grab_focus();ticks[0]=0;gaps.clear();last[0]=time.monotonic()
        started=time.monotonic();native.key('Return');wait(lambda:not text.pending)
        GLib.source_remove(timer)
        assert [r.start for r in text.rows]==['Matt.5.14','John.8.12','John.9.5'],text.status.get_text()
        assert ticks[0]>=10 and max(gaps)<.5,(ticks,max(gaps))
        report['literal_search']=dict(query='light of the world',references=[r.start for r in text.rows],seconds=round(time.monotonic()-started,3),gtk_heartbeat_ticks=ticks[0],maximum_heartbeat_gap_seconds=round(max(gaps),3))
        button=first_result(text);native.click(button);spin();assert w.reference_preview.target==('KJV','Matt.5.14')
        assert w.reference_preview.body.get_buffer().props.text==local_excerpt(nav.reader,'Matt.5.14',source_system='KJV').text
        native.key('Escape');text.entry.set_text('[not a regex]');text.entry.grab_focus();native.key('Return');wait(lambda:not text.pending)
        assert not text.rows
        mode('Passage');nav.direct.set_text('John 3:16');nav.direct.grab_focus();native.key('Return');settled()
        assert w.active_tab.state.reference=='John.3.16';report['passage_navigation_preserved']=True
        nav=open_search('FreSegond1910');mode('Text');text.entry.set_text('lumière du monde');spin(duration=.3)
        text.entry.grab_focus();native.key('Return');wait(lambda:not text.pending)
        assert {r.start for r in text.rows}=={'Matt.5.14','John.8.12','John.9.5'}
        mode('Topics');search.entry.set_text('peur');spin(duration=.3);choose('fear')
        button=next(b for b in walk(search.results) if isinstance(b,Gtk.Button) and hasattr(b,'_result') and b._result[0].start=='Ps.34.4')
        button.grab_focus();spin();native.key('Return');spin()
        assert w.reference_preview.target==('FreSegond1910','Ps.34.5')
        assert w.reference_preview.body.get_buffer().props.text==local_excerpt(nav.reader,'Ps.34.4').text
        report['verified_french_psalm']={'source':'Ps.34.4','installed':'Ps.34.5','exact_text':True}
        capture('renumbered-psalm');native.key('Escape')
        search.entry.set_text('priere');spin(duration=.3);choose('prayer')
        from tests.test_appearance import SystemStyleOverride
        with SystemStyleOverride() as theme:
            for label,dark,high in [('day',False,False),('night',True,False),('contrast-emulated',False,True)]:
                theme.set(dark=dark,high=high);spin();capture('topics-'+label)
        nav.popdown();spin(lambda:not nav.get_mapped(),duration=.2)
        w.set_default_size(360,800);spin(lambda:w.get_width()<=380,duration=.3)
        native.click(w.passage_button);spin();mode('Topics');search.entry.set_text('pardon');spin(duration=.3);capture('topics-narrow')
        nav.popdown()
        before=hashlib.sha256(search.data.path.read_bytes()).hexdigest();bad=args.profile/'invalid-topic-update';bad.write_bytes(b'INVALID UPDATE')
        try:search.data.install_archive(bad);raise AssertionError('Accepted corrupt topic data')
        except ValueError:pass
        bad.unlink();assert hashlib.sha256(search.data.path.read_bytes()).hexdigest()==before
        assert w.notes_store.all()==original_notes and w.library.installed()==original_resources
        w.close();restored=Window(app,Library(args.profile/'translations'));restored.present()
        try:assert len(TopicData(args.profile/'study-data').query('forgiveness of sins'))==12
        finally:restored.close()
        report.update(offline_restart=True,failed_update_preserves_index=True,notes_and_modules_preserved=True,narrow_and_themes=True,status='PASS')
    finally:
        if not w.closed:w.close()
        native.close()
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
