"""Real-resource GTK evidence for Ready reading/notes, in a marked test profile.

Captures remain private. JSON records identities/checks, not Scripture or note
bodies. --prepare installs requested real resources without resetting a profile.
"""
import argparse
from dataclasses import asdict
import hashlib
import inspect
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    for name in ('prepare','baseline','require-packaged','offline'):parser.add_argument('--'+name,action='store_true')
    args=parser.parse_args();marker=args.profile/'.ready-reading-notes-profile'
    if args.prepare:
        assert not args.profile.exists() or marker.exists(),'Unmarked profile'
        args.profile.mkdir(parents=True,exist_ok=True);marker.write_text('Retained disposable Ready validation profile\n')
    assert marker.is_file();args.output.mkdir(parents=True,exist_ok=True)
    if args.offline:assert len(Path('/proc/net/route').read_text().splitlines())<=1
    from bible.library import Library,catalogue
    library=Library(args.profile/'translations')
    if args.prepare:
        resources=catalogue()
        for identifier in ('KJV','FreJND','FreSegond1910','Wesley'):
            if identifier not in library.installed():library.install(next(r for r in resources if r.id==identifier))
        from bible.youversion_install import fetch_resource,acknowledgement
        for identifier in (21,93,104):
            if f'youversion~YV{identifier}' not in library.installed():
                item=fetch_resource(identifier);library.install(item,permission=acknowledgement(item))
        from bible.reference_data import ReferenceData
        from bible.topic_data import TopicData
        for data in (ReferenceData(args.profile/'study-data'),TopicData(args.profile/'study-data')):
            if data.revision is None:data.install()
    from bible.ui import Application,Window,Gtk
    from bible.i18n import tr,LANGUAGE
    from bible.paged_sources import BiblePages
    from tests.test_ui import spin
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    app=Application();app.register();w=Window(app,library);w.set_default_size(1200,860);w.present()
    native=X11Input();screen=Screen(native);native.activate(w)
    report=dict(app_import=inspect.getfile(Window),ui_sha256=hashlib.sha256(Path(inspect.getfile(Window)).read_bytes()).hexdigest(),
        gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],renderer=type(w.get_renderer()).__name__,
        language=LANGUAGE,baseline=args.baseline,offline=args.offline,cases=[])
    def save():(args.output/'ready.json').write_text(json.dumps(report,indent=2)+'\n')
    def settled():spin(lambda:not w.active_tab._restoring_scroll and not getattr(w.active_tab,'_comparison_positioning',False),duration=.3,timeout=60)
    def capture(name,keep_pointer=False):
        if not keep_pointer:native.move_at(w,2,2)
        spin(duration=.2);screen.grab(args.output/(name+'.png'))
    def hashes():return {str(p.relative_to(library.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in library.root.rglob('*') if p.is_file()}
    before=hashes();settings=asdict(w.preferences.value);retained=w.notes_store.all()
    try:
        if args.require_packaged:assert report['app_import'].startswith('/app/') and 'GL' in report['renderer']
        for edition,reference in [('youversion~YV21','Mark.11.29'),('youversion~YV93','Gen.11.1'),('FreJND','Gen.11.1'),('KJV','John.3.16')]:
            assert w.active_tab.navigate(edition,reference);settled()
            w.appearance.update('chapter_numbers',True);settled()
            for mode in ('day','night'):
                w.appearance.update('mode',mode);w.study_button.set_active(True);w.study.tools.set_visible_child_name('references')
                spin(lambda:not w.study.references.pending,duration=.3,timeout=30)
                capture(edition.replace('~','-')+'-'+mode+'-study')
            before_doc=w.active_tab._document
            w.appearance.update('chapter_numbers',False);settled();after_doc=w.active_tab._document
            assert not any(s.kind=='chapter' for s in after_doc.styles) if not args.baseline else True
            if not args.baseline:
                left=before_doc.copy(before_doc.spans[0].body,len(before_doc.text));right=after_doc.copy(after_doc.spans[0].body,len(after_doc.text))
                assert left==right
            capture(edition.replace('~','-')+'-heading-off');w.appearance.update('chapter_numbers',settings['chapter_numbers'])
            report['cases'].append(dict(edition=edition,reference=reference,heading_body_preserved=not args.baseline));save()
        w.study_button.set_active(False);w.active_tab.navigate('youversion~YV21','Mark.11.29');settled()
        for mode in ('day','night'):
            w.appearance.update('mode',mode);settled();tab=w.active_tab
            if not args.baseline:
                markers=[b for b in tab.text._inline_buttons if b._marker_kind=='translation-note']
                assert markers,'Real translation must supply source-note markers'
                button=next((b for b in markers if b._marker_reference=='Mark.11.29'),markers[0])
                # The source reference is stable; no Scripture coordinates or
                # edition-specific application exception is introduced.
                ref=button._marker_reference;offset=tab._marker_ends[ref]
                tab.text.scroll_to_iter(tab.text.get_buffer().get_iter_at_offset(offset),.1,True,.5,.3);spin(duration=.5)
                native.move_at(button,button.get_width()/2,button.get_height()/2);spin(duration=1.2)
                capture('source-note-tooltip-'+mode,True)
                native.click(button);spin();assert button._source_note_popover and button._source_note_popover.get_visible()
                capture('source-note-popover-'+mode);native.key('Escape')
                button.grab_focus();native.key('space');assert button._source_note_popover and button._source_note_popover.get_visible();native.key('Escape')
            buffer=tab.text.get_buffer();start=tab._marker_ends['Mark.11.29']
            buffer.select_range(buffer.get_iter_at_offset(start),buffer.get_iter_at_offset(start+20))
            actions=w.passage_actions;actions.capture(tab.text,lambda:actions.ordinary(tab),None);spin()
            capture('selection-'+mode);w.dismiss_popovers();buffer.place_cursor(buffer.get_iter_at_offset(start))
            w.study_button.set_active(True)
            for tool in ('notes','references','commentaries'):
                w.study.tools.set_visible_child_name(tool);spin(lambda:not w.study.references.pending,duration=.3,timeout=30)
                capture('study-'+tool+'-'+mode)
            if not args.baseline:
                width=w.study_settings.width;w.study_divider.grab_focus();native.key('Left');spin()
                assert w.study_settings.width!=width
                w.study_divider.grab_focus();native.key('Right');spin()
            w.study_button.set_active(False)
        from bible.application_surfaces import show_preferences
        dialog=show_preferences(w);dialog.set_visible_page(dialog.reading_settings.page);spin(duration=.4)
        capture('reading-preferences');dialog.close();spin();native.activate(w)
        for width in (1200,680,360):
            w.set_default_size(width,760);spin(lambda:not w._controls_tick,duration=.4)
            for mode in ('day','night'):
                w.appearance.update('mode',mode);capture(f'reader-{width}-{mode}')
                w.show_search('text');spin(duration=.4);capture(f'search-text-{width}-{mode}')
                text_width=w.search_popover.content.get_width()
                w.search_popover.modes.set_visible_child_name('topics');spin(duration=.4);capture(f'search-topics-{width}-{mode}')
                if not args.baseline:assert w.search_popover.content.get_width()==text_width
                w.search_popover.popdown();w.choose_passage();spin(duration=.4);capture(f'passage-{width}-{mode}');w.navigation.popdown()
                # At narrow widths the reading controls have one adaptive owner.
                if w.appearance_button.get_parent() is w.reader_overflow_box:w.reading_tools_menu.popup();spin()
                w.appearance_button.popup();spin(duration=.4);capture(f'appearance-{width}-{mode}');w.dismiss_popovers()
                if not args.baseline:assert w.appearance.get_child().get_width()+24<=w.get_width()
        if not args.baseline:
            settings_gtk=Gtk.Settings.get_default();old_font=settings_gtk.props.gtk_font_name
            try:
                settings_gtk.props.gtk_font_name='Sans 18';spin(duration=.4)
                w.reading_tools_menu.popup();spin();w.appearance_button.popup();spin(duration=.4)
                # Composited native surfaces include transparent outer shadows.
                assert w.appearance.get_child().get_width()+24<=w.get_width()
                capture('appearance-360-large-ui-text');w.dismiss_popovers()
            finally:settings_gtk.props.gtk_font_name=old_font
        w.set_default_size(1200,860);w.study_button.set_active(False);settled()
        note=w.notes_store.save('Developer validation **bold** and *italic*.\n- Retained list item\n1. Numbered item\nJohn 3:16',('Ready validation',),
            versification=w.active_tab.reader.versification,start='Mark.11.29',end='Mark.11.30',origin_translation='youversion~YV21',origin_language='fr')
        w.notes_changed();report['validation_note_id']=note.id
        for mode in ('day','night'):
            w.appearance.update('mode',mode)
            editor=w.edit_note(note=w.notes_store.get(note.id));spin(duration=.3);native.activate(editor)
            capture('note-dialog-'+mode)
            if not args.baseline:
                assert not editor.dirty;editor.links.entry.set_text('Jean 3:16')
                if not editor.links.values:assert editor.links.add()
                else:editor.links.entry.set_text('')
                assert editor.save(close=False);assert w.notes_store.get(note.id).body==note.body
            editor.close();spin();native.activate(w)
            space=w.open_notes();space.open_note(w.notes_store.get(note.id));spin(duration=.4);capture('note-workspace-'+mode)
            space.leave();spin();native.activate(w)
        if not args.baseline:
            from bible import personal_backup
            from bible.notes import NoteStore
            from bible.highlights import HighlightStore
            backup=args.output/'validation-annotations.json';personal_backup.export(w.notes_store,w.highlights,backup)
            restored=args.output/'restore-proof';restored.mkdir(exist_ok=True)
            notes=NoteStore(restored/'notes.sqlite3')
            try:
                marks=HighlightStore(restored/'highlights.json');personal_backup.restore(notes,marks,backup)
                assert notes.get(note.id)==w.notes_store.get(note.id)
                report['linked_backup_roundtrip']=True
            finally:notes.close()
            # Only private synthetic annotation evidence, never full Bible data.
            backup.unlink()
        assert before==hashes();assert all(w.notes_store.get(n.id)==n for n in retained)
        report.update(translations_preserved=True,retained_notes_preserved=True,complete=True);save()
    finally:
        w.dismiss_popovers()
        for key,value in settings.items():setattr(w.preferences.value,key,value)
        w.preferences.save()
        if w.note_editor and not w.note_editor.closed:w.note_editor._discard=True;w.note_editor.close()
        w.close();native.close();save()


if __name__=='__main__':main()
