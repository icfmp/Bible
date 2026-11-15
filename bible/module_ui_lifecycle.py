"""Quiesce native resource consumers on GTK's thread before a file switch."""
import gc
from pathlib import Path
from threading import Event
from gi.repository import GLib
from .i18n import tr
from .module_lifecycle import changing


def clear_view(view):
    # Child anchors must be unmapped while their text tree is still intact.
    for button in getattr(view,'_inline_buttons',()):view.remove(button)
    view._inline_buttons=[];view.get_buffer().set_text('')
    view._verse_fragments=();view._verse_labels={}


class ModuleViewChange:
    def __init__(self,dialog,identifier):
        self.dialog=dialog;self.identifier=identifier;self.root=(dialog.library.root/identifier).resolve()
        self.windows=[];self.paused=False;self.tabs=[]

    def matches(self,reader):return bool(reader and Path(reader.root).resolve()==self.root)

    def before_switch(self,identifier):
        done=Event();errors=[]
        def prepare():
            try:
                if self.dialog.owner.closed:raise InterruptedError('Module operation cancelled')
                self.pause()
            except Exception as error:errors.append(error)
            finally:done.set()
            return False
        GLib.idle_add(prepare)
        for _ in range(300):
            if done.wait(.05):break
            if self.dialog.owner.closed:raise InterruptedError('Module operation cancelled')
        else:raise OSError('The application could not release this resource; its files were preserved')
        if errors:raise errors[0]

    def pause(self):
        from .ui import Window
        changing(self.root,True);self.paused=True
        for window in self.dialog.owner.get_application().get_windows():
            if not isinstance(window,Window) or window.closed or window.library.root.resolve()!=self.dialog.library.root.resolve():continue
            self.windows.append(window)
            window.reading_sync.driver=None;window.reading_sync.needs_sync=False
            window.passage_actions.dismiss();window.reference_preview.dismiss();window.dismiss_popovers()
            if window.immersion and self.matches(window.immersion.source.reader):window.leave_immersion()
            host=getattr(window,'passage_study_dialog',None)
            if host and (self.matches(host.context[1]) if host.context else False):
                host.close();host.target=None;host.context=None;host.places.context=None
            words=window.study.words
            if self.matches(getattr(words,'verse_reader',None)) or (getattr(words,'target',None) and self.matches(words.target.source.reader)):
                words.leave(restore_focus=False);words.target=None;words.context=None;words.verse_reader=None
            for tab in window.tabs():
                primary=self.matches(tab.reader) or tab.state.resource==self.identifier
                comparison=self.matches(tab._comparison_reader) or tab.state.comparison==self.identifier
                # Leaving aligned rows rerenders the chapter and may populate
                # the editorial cache. Clear retained owners after that render.
                if not primary and not comparison:
                    for key in list(tab.inline_markers.editorial):
                        if self.matches(key[0]):tab.inline_markers.editorial.pop(key)
                    continue
                anchor=None
                if primary and tab.current and tab.text.get_mapped():
                    rect=tab.text.get_visible_rect();_,iterator=tab.text.get_iter_at_location(rect.x,rect.y)
                    anchor=tab.position_anchor(iterator.get_offset())
                self.tabs.append((window,tab,primary,comparison,anchor))
                if getattr(tab,'_comparison_tick',0):
                    tab.comparison_text.remove_tick_callback(tab._comparison_tick);tab._comparison_tick=0
                tab._comparison_positioning=False
                tab.scroll_motion.cancel();tab.cancel_adapt();tab.comparison_sync.driver=None;tab.comparison_rows.leave()
                if primary:
                    if tab._tick_id:tab.remove_tick_callback(tab._tick_id);tab._tick_id=0
                    tab._restoring_scroll=False;tab._appearance_anchor=None
                    tab.reader=None;tab.current=None;tab._document=None;tab._verse_offsets={};tab._verse_ranges={};tab._marker_ends={}
                    clear_view(tab.text);tab.status.set_text(tr('Updating resource…'));tab.status.set_visible(True)
                if comparison:
                    tab._comparison_reader=None;tab._comparison_name=None;tab._comparison_document=None;tab._comparison_signature=None
                    clear_view(tab.comparison_text)
                for key in list(tab.inline_markers.editorial):
                    if self.matches(key[0]):tab.inline_markers.editorial.pop(key)
            if self.matches(getattr(window.navigation,'reader',None)):window.navigation.reader=None
            search=window.search_popover
            for panel in (search.text_search,search.topic_search):
                panel.pause();panel.context=None;panel._refresh_stamp=None
                if self.matches(panel.search_reader):panel.search_reader=None
            if self.matches(search.reader):search.reader=None
            refs=window.study.references
            if refs.context and self.matches(refs.context[1]):
                refs.generation+=1;refs.context=None;refs.stamp=None;refs.pending=False
                refs.clear_rows();refs.chapter_cache={};refs.row_cache={}
            study=window.study
            for name,reader in list(study._readers.items()):
                if self.matches(reader):study._readers.pop(name)
            if self.matches(study.reader):study.clear_content();study.reader=None;study._display_context=None
            # Leaving immersion/rendering may queue an annotation reveal with
            # the old reader. Cancel it before collecting disposed consumers;
            # resume refreshes normal following against the new source.
            study.notes.cancel_follow()
            if window.notes_space:
                space=window.notes_space
                for name,reader in list(space._reader_cache.items()):
                    if self.matches(reader):space._reader_cache.pop(name)
                space._excerpt_cache.clear()
        # Loop temporaries must not themselves retain a reader/index cycle
        # during the main-thread collection before the worker takes its lease.
        reader=None;key=None;host=None
        gc.collect()

    def resume(self):
        if not self.paused:return
        changing(self.root,False);self.paused=False
        for window,tab,primary,comparison,anchor in self.tabs:
            if window.closed or tab not in window.tabs():continue
            if primary:
                tab.load_resource()
                if tab.reader and anchor:
                    tab._appearance_anchor=anchor;tab._jump_reference=None;tab.schedule_scroll_restore()
            if comparison:tab._comparison_stamp=None
            tab.refresh_comparison();window.tab_changed(tab)
        for window in self.windows:
            if window.closed:continue
            if window.catalogue_session:window.catalogue_session.reload_installed()
            window.study.refresh(force=True);window.primary_version.sync();window.compared_version.sync();window.sync_comparison()
            window.search_popover._layout_stamp=None
            if window.notes_space:
                window.notes_space.refresh()
                if window.notes_space.selected_annotation:window.notes_space.update_context(window.notes_space.selected_annotation)
            editors={window.note_editor,window.study.notes.editor,
                     window.notes_space.editor if window.notes_space else None}
            for editor in editors:
                if editor and not editor.closed and editor.context['origin_translation']==self.identifier:
                    # Refresh the read-only source excerpt, never remount the
                    # editor or replace its live buffer/undo/autosave state.
                    editor.excerpt.set_text(editor.source_excerpt())
        self.tabs=[];self.windows=[]
