"""Real resource/context study walkthrough; disposable profiles, native GTK input."""
import argparse,hashlib,inspect,json
from pathlib import Path
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk
from bible.ui import Application,Window,Library
from bible.i18n import tr
from bible.reference_targets import local_excerpt
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input
from tools.check_client_feedback import Screen


def walk(widget):
    yield widget;child=widget.get_first_child()
    while child:yield from walk(child);child=child.get_next_sibling()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--require-packaged',action='store_true');p.add_argument('--dark',action='store_true');p.add_argument('--narrow',action='store_true');p.add_argument('--places-only',action='store_true')
    a=p.parse_args();assert (a.profile/'.ready-batch-test-profile').is_file()
    if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    a.output.mkdir(parents=True,exist_ok=True);app=Application();app.register()
    w=Window(app,Library(a.profile/'translations'));w.set_default_size(1280,900);w.present();spin()
    w.appearance.update('mode','night' if a.dark else 'day');native=X11Input();screen=Screen(native)
    report=dict(complete=False,app_import=inspect.getfile(Window),word_cases=[],place_cases=[],narrow=a.narrow,dark=a.dark)
    notes=w.notes_store.all()
    def shot(name):native.move_at(w,2,2);spin(duration=.25);screen.grab(a.output/(name+'.png'))
    def open_words(resource,start,end):
        tab=w.active_tab;tab.navigate(resource,start);spin(lambda:not tab._restoring_scroll)
        before=(tab.state.resource,tab.state.reference,list(tab.state.history))
        buf=tab.text.get_buffer();buf.select_range(buf.get_iter_at_offset(tab._marker_ends[start]),buf.get_iter_at_offset(tab._verse_ranges[end][1]))
        actions=w.passage_actions;actions.capture(tab.text,lambda:actions.ordinary(tab),None);spin()
        native.activate(w);actions.word_button.grab_focus();native.key('Return')
        words=w.study.words;spin(lambda:words.dialog is not None and not words.pending,timeout=40)
        host=words.dialog
        if a.narrow:host.set_default_size(360,620);spin();assert host.get_width()<=360,host.get_width()
        native.activate(host)
        return tab,before,host,words
    try:
        for resource in (() if a.places_only else ('youversion~YV21','youversion~YV104','FreSegond1910','KJV')):
            for start,end in (('Gen.11.4','Gen.11.6'),('Mark.11.29','Mark.11.30')):
                tab,before,host,words=open_words(resource,start,end)
                expected=local_excerpt(tab.reader,start,end,source_system=tab.reader.versification,limit=40)
                excerpts={x._translated_reference:x.get_text() for x in words.children() if hasattr(x,'_translated_reference')}
                assert excerpts==dict(expected.verses),(resource,excerpts,dict(expected.verses))
                tokens=[x for x in words.children() if hasattr(x,'_source_token')];assert tokens,(resource,start)
                for tile in tokens:
                    token=tile._source_token;labels=[x.get_text() for x in walk(tile) if isinstance(x,Gtk.Label)]
                    assert token['form'] in labels
                    if token['gloss']:assert token['gloss'] in labels
                assert not words.selection_label.get_visible()
                other='youversion~YV104' if resource!='youversion~YV104' else 'youversion~YV21'
                words.translation.grab_focus();native.key('space');native.key('Escape')
                words.translation.set_selected(words.translations.index(other));spin(lambda:not words.pending)
                alternate=words.verse_reader
                changed={x._translated_reference:x.get_text() for x in words.children() if hasattr(x,'_translated_reference')}
                for reference in words.target.references:
                    assert changed[reference]==local_excerpt(alternate,reference,source_system=tab.reader.versification,limit=40).text
                assert (tab.state.resource,tab.state.reference,tab.state.history)==before
                words.translation.set_selected(words.translations.index(resource));spin(lambda:not words.pending)
                tokens=[x for x in words.children() if hasattr(x,'_source_token')]
                if start.startswith('Gen'):assert any(t.get_direction()==Gtk.TextDirection.RTL for t in walk(words) if isinstance(t,Gtk.FlowBox))
                shot(resource+'-'+start+'-passage')
                chosen=next(t for t in tokens if any(words.data.lookup(key) for key in (t._source_token['tags'] if t._source_token['language']=='grc' else [x[0] for x in t._source_token['lexical']])))
                # Native focus activation also verifies the reparented dialog path.
                chosen.grab_focus();native.key('Return');spin(lambda:not words.pending,timeout=40)
                if not hasattr(words,'entry') or words.entry is None:
                    raise AssertionError('Expected a real lexical entry for the chosen token')
                chips=[x for x in words.children() if hasattr(x,'_word_reference')]
                assert chips and len(chips)<=8
                result=words.data.occurrences(words.corpus,words.entry['id'],limit=8)
                assert [c._word_reference for c in chips]==list(result['references'])
                shot(resource+'-'+start+'-word')
                details=next(x for x in words.children() if isinstance(x,Gtk.Expander))
                details.grab_focus();native.key('Return');assert details.get_expanded()
                native.key('space');assert not details.get_expanded()
                chips[0].grab_focus();native.key('Return');spin()
                assert w.reference_preview.popover and w.reference_preview.popover.get_visible()
                native.key('Escape');spin();assert w.reference_preview.popover is None and not host.closed
                words.go_back.grab_focus();native.key('Return');spin(lambda:not words.pending)
                assert words.stage=='passage'
                for page in ('dictionary','map','people','original'):
                    button=next(b for b in walk(host.switcher) if isinstance(b,Gtk.ToggleButton) and b.get_child() and any(isinstance(l,Gtk.Label) and l.get_text()==tr({'dictionary':'Dictionary','map':'Map','people':'People','original':'Original text'}[page]) for l in walk(b)))
                    button.grab_focus();native.key('Return');spin()
                    assert host.tabs.get_visible_child_name()==page
                    if page!='map' and host.places.map_widget:assert host.places.map_widget.canvas is None
                assert (tab.state.resource,tab.state.reference,tab.state.history)==before
                report['word_cases'].append(dict(resource=resource,start=start,end=end,verses=len(excerpts),tokens=len(tokens),lexical_entry=words.entry['id'],real_occurrence_chips=len(chips),native_keyboard=True))
                host.close();spin()
        for ref,identity in (('Mark.7.1','a15257a'),('Gen.12.6','a38ad9f'),('Judg.7.1','a772880'),('Luke.24.13','ae7274b'),('Gen.4.16','a1ad8e1')):
            tab=w.active_tab;tab.navigate('FreSegond1910',ref);spin(lambda:not tab._restoring_scroll)
            host=w.open_passage_study(context=(tab.state.resource,tab.reader,ref,ref),mode='map');places=host.places
            if a.narrow:host.set_default_size(360,620)
            spin(lambda:not places.pending,timeout=30)
            assert places.data.revision is not None,'Existing OpenBible place index must be installed for this walkthrough'
            place=next((x for x in places.rows if x['id']==identity),None)
            assert place is not None,(ref,identity,places.status.get_text(),[(x['id'],x['name']) for x in places.rows])
            places.open_place(place);spin();native.activate(host)
            assert not hasattr(places,'contexts')
            assert not any(hasattr(x,'photo_path') for x in walk(places))
            if identity=='a38ad9f':assert len(place['candidates'])==3
            if identity=='a1ad8e1':assert places.map_widget is None
            shot(identity+'-place')
            if places.map_widget:
                camera=places.map_widget
                host.tabs.set_visible_child_name('people');spin();assert camera.canvas is None and camera.layer is None
                host.tabs.set_visible_child_name('map');spin();assert camera.canvas is not None
            report['place_cases'].append(dict(id=identity,status=place['status'],proposals=len(place['candidates']),unavailable_enrichment=True,hidden_map_stopped=True))
            host.close();spin()
        assert w.notes_store.all()==notes
        report['complete']=True;report['notes_unchanged']=True
    finally:
        if getattr(w,'passage_study_dialog',None):w.passage_study_dialog.close();spin()
        w.close();native.close();(a.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
