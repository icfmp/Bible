"""Actual GTK input and source fidelity for #44/#60; disposable profile only."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
from tests.test_ui import spin


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--require-packaged',action='store_true')
    parser.add_argument('--captures',type=Path)
    args=parser.parse_args()
    from bible.ui import Application,Window,Library,Gtk
    from tools.check_alpha_ui import X11Input
    from bible.notes_window import buffer_text
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/'),inspect.getfile(Window)
    app=Application();app.register();native=X11Input()
    settings=Gtk.Settings.get_default();settings.set_property('gtk-enable-animations',False)
    window=Window(app,Library(args.profile/'translations'));window.set_default_size(1440,950);window.present()
    report=dict(app_import=inspect.getfile(Window),accessibility='Deferred; not tested')
    def settled():
        spin(lambda:not window.active_tab._restoring_scroll and not window.study._positioning,duration=.2)
    def capture(name):
        if args.captures:
            from PIL import ImageGrab
            args.captures.mkdir(parents=True,exist_ok=True)
            native.move_at(window,2,2);spin(duration=.2)
            ImageGrab.grab().save(args.captures/(name+'.png'))
    try:
        tab=window.active_tab;assert tab.navigate('FreSegond1910','John.1.5')
        tab.state.commentary='MHC';window.study_button.set_active(True)
        window.study.tools.set_visible_child_name('commentaries');window.study.refresh();settled()
        study=window.study;source=study.entry_text;heading=study.current_position
        assert source and study.text.get_buffer().props.text
        # Preserve exact source copying while typography changes independently.
        document=study.text._bible_copy_source[0]
        source_hash=hashlib.sha256(document.copy(0,len(document.text)).encode()).hexdigest()
        typography=study.text.get_buffer().get_tag_table().lookup('reader-typography')
        assert typography.props.family=='sans-serif' and typography.props.size_points==12
        assert abs(typography.props.line_height-1.5)<.001
        window.appearance.update('size',24);window.appearance.update('font','DejaVu Serif')
        window.appearance.update('line_spacing','very-airy');window.appearance.update('column_width','wide');settled()
        assert typography.props.size_points==12 and study.text.get_pixels_inside_wrap()==0
        assert study.text.get_left_margin()==24 and study.entry_text==source
        assert hashlib.sha256(document.copy(0,len(document.text)).encode()).hexdigest()==source_hash
        window.appearance.reset();settled()
        history=list(tab.state.history);reference=tab.state.reference
        buffer=study.text.get_buffer();buffer.select_range(buffer.get_iter_at_offset(25),buffer.get_iter_at_offset(40))
        selected=buffer.get_text(*buffer.get_selection_bounds(),False)
        # Actual horizontal pointer drag on the GTK divider. Move in window
        # coordinates so the moving divider does not add its own displacement.
        divider=window.study_divider
        surface=window.split
        _,bounds=divider.compute_bounds(surface);x=bounds.origin.x+divider.get_width()/2;y=bounds.origin.y+180
        start=window.study_settings.width
        native.move_at(surface,x,y);spin(duration=.15)
        native.xtest.XTestFakeButtonEvent(native.display,1,True,0);native.x11.XFlush(native.display);spin(duration=.1)
        for step in range(1,9):native.move_at(surface,x-step*10,y);spin(duration=.04)
        native.xtest.XTestFakeButtonEvent(native.display,1,False,0);native.x11.XFlush(native.display);settled()
        preferred=window.study_settings.width
        assert preferred>start+50,(start,preferred)
        assert abs(window.split.get_sidebar().get_width()-preferred)<=2
        assert divider.get_width()==8,divider.get_width()
        assert buffer.get_selection_bounds() and buffer.get_text(*buffer.get_selection_bounds(),False)==selected
        buffer.place_cursor(buffer.get_start_iter());spin(duration=.2)
        buffer=tab.text.get_buffer();buffer.select_range(buffer.get_iter_at_offset(25),buffer.get_iter_at_offset(40))
        spin(duration=.2)
        selected=buffer.get_text(*buffer.get_selection_bounds(),False)
        divider.grab_focus();spin(duration=.2)
        assert buffer.get_selection_bounds(), 'Selection cleared before keyboard resizing'
        native.key('Right');settled()
        assert window.study_settings.width==preferred-32
        preferred=window.study_settings.width
        assert tab.state.reference==reference and tab.state.history==history
        assert study.current_position==heading and study.entry_text==source
        assert buffer.get_selection_bounds() and buffer.get_text(*buffer.get_selection_bounds(),False)==selected, 'Selection changed during keyboard resizing'
        buffer.place_cursor(buffer.get_start_iter())
        report['native_drag_keyboard_resize']=dict(before=start,after=preferred,divider_width=8,reference_preserved=True,history_preserved=True)
        native.move_at(divider,4,180);spin(duration=.15)
        native.xtest.XTestFakeButtonEvent(native.display,1,True,0);native.x11.XFlush(native.display);spin(duration=.1)
        native.key('F9');settled()
        native.xtest.XTestFakeButtonEvent(native.display,1,False,0);native.x11.XFlush(native.display);settled()
        assert not window.split.get_show_sidebar() and not window._study_resizing, (window.split.get_show_sidebar(),window._study_resizing)
        native.key('F9');settled();assert window.split.get_show_sidebar()
        report['native_drag_keyboard_resize'].update(selection_preserved=True,close_during_held_drag=True)
        capture('comments-wide')
        # Emulated desktop text enlargement: point sizing remains native.
        dpi=settings.get_property('gtk-xft-dpi');baseline=study.text.get_iter_location(study.text.get_buffer().get_start_iter()).height
        try:
            settings.set_property('gtk-xft-dpi',144*1024);spin(duration=.35)
            enlarged=study.text.get_iter_location(study.text.get_buffer().get_start_iter()).height
            assert enlarged>baseline,(baseline,enlarged)
            report['emulated_text_scale']=dict(line_height_before=baseline,line_height_after=enlarged)
        finally:settings.set_property('gtk-xft-dpi',dpi);settled()
        context=dict(versification=tab.reader.versification,start='John.1.5',end='John.1.5',origin_translation=tab.state.resource,origin_language='fr')
        if not any(n.body=='**Validation note** — retained data. See Romans 8:28.' for n in window.notes_store.all()):
            window.notes_store.save('**Validation note** — retained data. See Romans 8:28.',('Study',),**context)
            window.notes_store.save('Second note for the same passage.',(),**context)
        window.highlights.set(tab.reader.versification,['John.1.5'],'blue',tab.state.resource)
        study.tools.set_visible_child_name('notes');settled();notes=study.notes
        assert len(notes.rows)>=2 and len(notes.marks)==1
        assert tab.state.reference==reference and tab.state.history==history
        assert divider.get_width()==8
        capture('notes-wide')
        # Real native nested menu, change color then remove the original mark.
        menu=notes.highlight_list.get_first_child().get_last_child();native.click(menu);spin()
        colors=menu.get_popover().get_child();native.click(colors.get_first_child())
        assert window.highlights.entries[(tab.reader.versification,'John.1.5')]['color']=='yellow'
        menu=notes.highlight_list.get_first_child().get_last_child();native.click(menu);spin()
        native.key('Escape');assert not menu.get_popover().get_visible()
        # Existing editor captures its source; changing the reader cannot
        # silently retarget its unsaved note.
        notes.add_note();editor=window.note_editor;editor.body.get_buffer().set_text('Captured study draft')
        captured=dict(editor.context);tab.navigate('KJV','John.3.16');settled()
        assert editor.context==captured and buffer_text(editor.body)=='Captured study draft'
        assert editor.save()
        stored=next(n for n in window.notes_store.all() if n.body=='Captured study draft')
        assert stored.start=='John.1.5' and stored.origin_translation=='FreSegond1910'
        tab.navigate('FreSegond1910','John.1.5');settled()
        report['notes_highlights_draft']=dict(multiple_notes=True,native_highlight_color_change=True,
                                           native_popup_escape=True,draft_target_preserved=True)
        # Resize and compare without changing the preferred desktop width.
        tab.state.comparison='KJV';window.sync_comparison();settled()
        window.set_default_size(1100,950);settled();capture('notes-comparison')
        assert tab.comparison_text.get_buffer().get_char_count()>0
        assert window.study_settings.width==preferred
        window.set_default_size(360,800);spin(lambda:window.split.get_collapsed());settled()
        if not window.split.get_show_sidebar():native.key('F9');settled()
        assert window.split.get_show_sidebar() and study.notes.get_mapped()
        assert window.study_settings.width==preferred
        assert study.get_width()<=window.get_width()
        assert not divider.get_visible();capture('notes-narrow')
        window.set_default_size(1440,950);spin(lambda:not window.split.get_collapsed());settled()
        assert abs(window.split.get_sidebar().get_width()-preferred)<=2
        window.appearance.update('mode','night');settled();capture('notes-dark')
        report['adaptive_comparison']=True
        report['typography']=dict(family='sans-serif',points=12,line_height=1.5,independent_of_Aa=True,source_copy_sha256=source_hash)
        report['saved_width']=preferred;report['selected_tool']='notes'
        window.close()
        restored=Window(app,Library(args.profile/'translations'));restored.set_default_size(1440,950);restored.present()
        try:
            spin(duration=.3)
            assert restored.study.tool=='notes' and restored.study_settings.width==preferred
            assert any(n.body=='Captured study draft' for n in restored.notes_store.all())
            assert len(restored.highlights.entries)>=1
            report['offline_restart_and_saved_annotations']=True
        finally:restored.close()
        report['status']='PASS'
    finally:
        if not window.closed:window.close()
        native.close()
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
