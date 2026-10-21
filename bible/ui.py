"""Native tabbed GNOME reader; downloads live in a dedicated window."""
from pathlib import Path

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gio, GLib, Gtk, Pango  # noqa: E402

from .catalogue_window import CatalogueWindow
from .providers import module_name
from .i18n import tr
from .library import Library
from .reading_tab import ReadingTab
from .study_panel import StudyPanel
from .navigation import PassagePopover
from .notes import NoteStore
from .preferences import Preferences
from .appearance import AppearancePopover
from .reading_style import ReadingStyle
from .reading_sync import ReadingSync
from .immersion import Immersion
from .immersion_hints import ImmersionHints
from .pagination import Anchor
from .paged_sources import BibleBookPages, CommentaryPages
from .notes_window import NoteEditor, NotesWindow, NotesSpace
from .session import Session, SessionError, SessionStore, TabState


class Window(Adw.ApplicationWindow):
    def __init__(self, app, library, session_path=None):
        super().__init__(application=app, title='Bible', default_width=960, default_height=700)
        self.set_size_request(360, 320)
        self.library = library
        self.store = SessionStore(session_path or library.root.parent / 'session.json')
        self.preferences = Preferences(library.root.parent / 'reading-preferences.json')
        self.reading_style = ReadingStyle(self)
        self.closed = False
        self.immersion=None;self._immersion_help_seen=False
        self.immersion_hints=ImmersionHints(library.root.parent/'immersion-help.json')
        self._initializing = True
        self._syncing_study = False
        self._save_id = 0
        self._session_writable = True
        self.catalogue_window = None
        self.notes_window = None
        self.notes_space = None
        self.note_editor = None
        self.notes_error = ''
        try:
            self.notes_store = NoteStore(library.root.parent / 'notes.sqlite3')
        except Exception as error:
            self.notes_store = None
            self.notes_error = str(error)
        self.connect('close-request', self.on_close)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header = Adw.HeaderBar()
        header.set_centering_policy(Adw.CenteringPolicy.LOOSE)
        self.heading = Adw.WindowTitle(title=tr('Choose a passage'))
        # Bound both title and version even with long affiliated module IDs.
        def constrain_labels(widget):
            if isinstance(widget,Gtk.Label):
                widget.set_max_width_chars(18);widget.set_width_chars(1);widget.set_ellipsize(Pango.EllipsizeMode.END)
            child=widget.get_first_child()
            while child:
                constrain_labels(child);child=child.get_next_sibling()
        constrain_labels(self.heading)
        heading_box = Gtk.Box(spacing=4)
        heading_box.append(self.heading)
        heading_box.append(Gtk.Image(icon_name='pan-down-symbolic'))
        self.passage_button = Gtk.MenuButton(child=heading_box, tooltip_text=tr('Choose a passage'))
        self.passage_button.add_css_class('flat')
        self.navigation = PassagePopover(self)
        self.passage_button.set_popover(self.navigation)
        header.set_title_widget(self.passage_button)
        new = Gtk.Button(icon_name='tab-new-symbolic', tooltip_text=tr('New tab'),
                         action_name='win.new-tab')
        header.pack_start(new)
        commands = Gio.Menu()
        for label,action in [('Passage note','note'),('My notes','notes'),('New tab','new-tab'),
                             ('Library','translations'),('History back','history-back'),('History forward','history-forward'),
                             ('Previous chapter','previous-chapter'),('Next chapter','next-chapter'),
                             ('Reading appearance','appearance'),('Compare translations','compare'),('Immersive mode','immersive')]:
            commands.append(tr(label),'win.'+action)
        self.menu = Gtk.MenuButton(icon_name='open-menu-symbolic',menu_model=commands,tooltip_text=tr('Notes and commands'))
        self.menu.update_property([Gtk.AccessibleProperty.LABEL],[tr('Notes and commands')])
        self.library_button = library_button = Gtk.Button(icon_name='bible-library-symbolic',tooltip_text=tr('Library'),action_name='win.translations')
        self.my_notes_button=Gtk.Button(icon_name='bible-notes-symbolic',tooltip_text=tr('My notes'),action_name='win.notes')
        self.study_button=Gtk.ToggleButton(icon_name='sidebar-show-symbolic',tooltip_text=tr('Study'))
        self.study_button.connect('toggled',self.toggle_study)
        self.immersive_button=Gtk.ToggleButton(icon_name='view-fullscreen-symbolic',tooltip_text=tr('Immersive mode'))
        self.immersive_button.connect('clicked',lambda *_:self.toggle_immersion())
        self.appearance_button=Gtk.MenuButton(label='Aa',tooltip_text=tr('Reading appearance'))
        self.appearance_button.add_css_class('flat')
        self.appearance=AppearancePopover(self);self.appearance_button.set_popover(self.appearance)
        self.comparison_button=Gtk.MenuButton(icon_name='view-dual-symbolic',tooltip_text=tr('Compare translations'))
        self.comparison_popover=Gtk.Popover()
        self.comparison_choices=Gtk.DropDown()
        self.comparison_choices.connect('notify::selected',self.comparison_selected)
        self.comparison_popover.set_child(self.comparison_choices)
        self.comparison_button.set_popover(self.comparison_popover)
        self._comparison_syncing=False
        # pack_end packs from the outside in: menu is immediately before the
        # native window controls, library before menu, My notes before library.
        for widget,label in [(self.menu,'Notes and commands'),(library_button,'Library'),
                             (self.my_notes_button,'My notes'),(self.study_button,'Study')]:
            widget.add_css_class('flat')
            widget.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
            header.pack_end(widget)
        self.reader_controls=Gtk.Box(spacing=6,halign=Gtk.Align.END,valign=Gtk.Align.START,
                                    margin_top=12,margin_end=12)
        for widget,label in [(self.comparison_button,'Compare translations'),
                             (self.appearance_button,'Reading appearance'),(self.immersive_button,'Immersive mode')]:
            widget.add_css_class('flat')
            widget.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
            self.reader_controls.append(widget)
        layout.append(header)
        self.session_status = Gtk.Label(wrap=True, xalign=0, visible=False,
                                        margin_start=12, margin_end=12)
        layout.append(self.session_status)
        self.notes_status = Gtk.Label(wrap=True, xalign=0, visible=bool(self.notes_error),
                                       margin_start=12, margin_end=12,
                                       label=(tr('Notes unavailable. The original file has been preserved.') + '\n' + self.notes_error) if self.notes_error else '')
        layout.append(self.notes_status)
        self.view = Adw.TabView(vexpand=True)
        self.bar = Adw.TabBar(view=self.view, autohide=False)
        layout.append(self.bar)
        self.split = Adw.OverlaySplitView(content=self.view, show_sidebar=False,
                                          min_sidebar_width=300, max_sidebar_width=420,
                                          sidebar_position=Gtk.PackType.END)
        self.study = StudyPanel(self)
        self.reading_style.decorate(self.study.text)
        self.reading_sync=ReadingSync(self)
        self.split.set_sidebar(self.study)
        self.split.connect('notify::show-sidebar', self.sidebar_changed)
        layout.append(self.split)
        self.main_pages=Gtk.Stack(hhomogeneous=False,vhomogeneous=False)
        self.main_pages.add_named(layout,'reading')
        self.set_content(self.main_pages)
        breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.parse('max-width: 760px'))
        breakpoint.add_setter(self.split, 'collapsed', True)
        self.add_breakpoint(breakpoint)
        tiny_header = Adw.Breakpoint.new(Adw.BreakpointCondition.parse('max-width: 420px'))
        tiny_header.add_setter(self.split, 'collapsed', True)
        tiny_header.add_setter(library_button, 'visible', False)
        tiny_header.add_setter(new, 'visible', False)
        tiny_header.add_setter(self.my_notes_button,'visible',False)
        tiny_header.add_setter(self.study_button,'visible',False)
        self.add_breakpoint(tiny_header)
        icons = Gtk.IconTheme.get_for_display(self.get_display())
        icons.add_search_path(str(Path(__file__).parent / 'icons'))
        css = Gtk.CssProvider()
        css.load_from_data(b'textview.reading { } '
                           b'button.chapter-navigation { min-width: 40px; min-height: 40px; '
                           b'padding: 0; border-radius: 9999px; } '
                           b'box.navigation-books { background-color: alpha(currentColor, 0.04); '
                           b'padding: 8px; border-radius: 12px; } '
                           b'popover.passage-selector > contents { border-radius: 18px; }')
        Gtk.StyleContext.add_provider_for_display(self.get_display(), css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.view.connect('notify::selected-page', self.selected_changed)
        self.view.connect('page-detached', self.page_detached)
        self.view.connect('page-reordered', lambda *_: self.schedule_save())
        self.add_action_callback('new-tab', lambda *_: self.new_tab())
        self.add_action_callback('close-tab', lambda *_: self.close_tab())
        self.add_action_callback('translations', lambda *_: self.open_library())
        self.add_action_callback('choose-passage', lambda *_: self.choose_passage())
        self.add_action_callback('reference', lambda *_: self.choose_passage(direct=True))
        self.add_action_callback('previous-chapter', lambda *_: self.step_chapter(-1))
        self.add_action_callback('next-chapter', lambda *_: self.step_chapter(1))
        self.add_action_callback('previous-verse', lambda *_: self.active_tab.step_verse(-1))
        self.add_action_callback('next-verse', lambda *_: self.active_tab.step_verse(1))
        self.add_action_callback('appearance',lambda *_:self.show_appearance())
        self.add_action_callback('compare',lambda *_:self.show_comparison())
        self.add_action_callback('immersive',lambda *_:self.toggle_immersion())
        self.add_action_callback('previous-commentary-entry',lambda *_:self.immersion.change_entry(-1) if self.immersion and self.immersion.kind=='commentary' else self.study.step_entry(-1))
        self.add_action_callback('next-commentary-entry',lambda *_:self.immersion.change_entry(1) if self.immersion and self.immersion.kind=='commentary' else self.study.step_entry(1))
        self.add_action_callback('immersive-open-bible',lambda *_:self.immersion.open_in_bible() if self.immersion and self.immersion.kind=='commentary' else None)
        self.add_action_callback('history-back',lambda *_:self.active_tab.travel(self.active_tab.state.history_index-1))
        self.add_action_callback('history-forward',lambda *_:self.active_tab.travel(self.active_tab.state.history_index+1))
        self.add_action_callback('copy-passage',lambda *_:self.copy_passage())
        self.add_action_callback('copy-with-reference',lambda *_:self.copy_passage(True))
        self.add_action_callback('copy-reference',lambda *_:self.copy_passage(reference_only=True))
        self.add_action_callback('note', lambda *_: self.new_note())
        self.add_action_callback('notes', lambda *_: self.open_notes())
        self.lookup_action('note').set_enabled(self.notes_store is not None)
        self.lookup_action('notes').set_enabled(self.notes_store is not None)
        self.add_action_callback('study', lambda *_: self.study_button.set_active(not self.study_button.get_active()))
        app.set_accels_for_action('win.immersive',['F11'])
        app.set_accels_for_action('win.new-tab', ['<Control>t'])
        app.set_accels_for_action('win.close-tab', ['<Control>w'])
        app.set_accels_for_action('win.translations', ['<Control>l'])
        app.set_accels_for_action('win.study', ['F9'])
        app.set_accels_for_action('win.note', ['<Control>n'])
        app.set_accels_for_action('win.notes', ['<Control><Shift>n'])
        app.set_accels_for_action('win.previous-verse', ['<Alt>Up'])
        app.set_accels_for_action('win.next-verse', ['<Alt>Down'])
        app.set_accels_for_action('win.choose-passage', ['<Control>g'])
        app.set_accels_for_action('win.reference', ['<Control>k'])
        app.set_accels_for_action('win.previous-chapter', ['<Alt>Page_Up'])
        app.set_accels_for_action('win.history-back',['<Alt>Left'])
        app.set_accels_for_action('win.next-chapter', ['<Alt>Page_Down'])
        app.set_accels_for_action('win.history-forward',['<Alt>Right'])
        try:
            session = self.store.load()
        except (OSError, SessionError) as error:
            self._session_writable = False
            self.report_session_error(tr('Unable to restore the session. The original file has been preserved.') + '\n' + tr('Session saving is disabled to preserve the original file.'), error)
            session = Session()
        if not session.tabs:
            names = self.library.installed('bible')
            session.tabs = [TabState(resource=names[0] if names else None)]
        for state in session.tabs:
            self.append_tab(state)
        self.view.set_selected_page(self.view.get_nth_page(session.selected))
        self._initializing = False
        self.selected_changed()

    def copy_passage(self,with_reference=False,reference_only=False):
        from .notes_window import passage_label
        tab=self.active_tab
        if not tab or not tab.reader:return
        if self.immersion:
            if self.immersion.kind!='bible':return
            first,last=self.immersion.selected_passage();reader=self.immersion.source.reader
            version=self.immersion.source.resource.name
        else:first,last=tab.selected_passage();reader=tab.reader;version=module_name(tab.state.resource)
        label=passage_label(first,last,reader.versification)+' — '+version
        if reference_only:value=label
        else:
            start,end=reader.key(first).getIndex(),reader.key(last).getIndex()
            chapter=reader.chapter(first)
            value='\n'.join(text for ref,text in chapter.verses if start<=reader.key(ref).getIndex()<=end)
            if with_reference:value=label+'\n'+value
        self.get_clipboard().set(value)

    def show_appearance(self):
        if self.immersion:self.immersion.reveal_controls();self.immersion.aa.popup()
        else:self.appearance_button.popup()

    def show_comparison(self):
        if self.immersion:self.leave_immersion()
        self.comparison_button.popup()

    def toggle_immersion(self):
        if self.immersion:self.leave_immersion()
        else:self.enter_immersion('bible')

    def enter_immersion(self,kind='bible'):
        if self.immersion:self.leave_immersion()
        tab=self.active_tab
        if not tab or not tab.reader:return False
        if kind=='commentary':
            study=self.study
            if not study.reader or study.current_position is None:return False
            source=CommentaryPages(study.reader,self.library.resource(tab.state.commentary))
            key=study.current_position
            doc=source.document(key,self.preferences.value);anchor=doc.anchor(0)
            saved=tab.state.commentary_positions.get(tab.state.commentary)
            if saved and saved.get('immersive'):
                positions=[i for i,section in enumerate(source.reader.index.sections) if section.index==saved['index']]
                if positions:
                    key=positions[0];doc=source.document(key,self.preferences.value)
                    anchor=Anchor(doc.spans[0].reference,saved['offset'],True)
            else:
                current=study.anchor()
                if current:
                    key,offset=current;doc=source.document(key,self.preferences.value);anchor=doc.anchor(offset)
        else:
            source=BibleBookPages(tab.reader,self.library.resource(tab.state.resource))
            anchor=Anchor(tab.state.reference)
            if tab.text.get_mapped() and not tab._restoring_scroll:
                rect=tab.text.get_visible_rect();_,iterator=tab.text.get_iter_at_location(rect.x,rect.y)
                position=tab.position_anchor(iterator.get_offset())
                if position:
                    reference,offset=position;buffer=tab.text.get_buffer();first=tab._marker_ends[reference]
                    text=buffer.get_text(buffer.get_iter_at_offset(first),buffer.get_iter_at_offset(first+offset),False)
                    anchor=Anchor(reference,sum(not c.isspace() for c in text),iterator.get_offset()>=first)
            key=source.key(anchor.reference)
        self.navigation.popdown();self.appearance.popdown()
        self.reading_sync.driver=None
        immersion=Immersion(self,source,key,anchor);self.immersion=immersion
        self.main_pages.add_named(immersion,'immersive');self.main_pages.set_visible_child_name('immersive')
        self.immersive_button.set_active(True);self.lookup_action('note').set_enabled(kind=='bible' and self.notes_store is not None)
        self.fullscreen();return True

    def leave_immersion(self):
        immersion=self.immersion
        if not immersion:return
        anchor,key=immersion.finish();tab=immersion.tab;self.immersion=None
        self.main_pages.set_visible_child_name('reading');self.main_pages.remove(immersion)
        if not immersion.was_fullscreen:self.unfullscreen()
        self.immersive_button.set_active(False);self.lookup_action('note').set_enabled(self.notes_store is not None)
        self.reading_sync.driver=None
        if immersion.kind=='bible' and tab.reader:
            tab._travelling=True
            try:tab.show(anchor.reference)
            finally:tab._travelling=False
            if anchor.reference in tab._verse_ranges:
                first,last=tab._verse_ranges[anchor.reference];body=tab._marker_ends[anchor.reference]
                buffer=tab.text.get_buffer();text=buffer.get_text(buffer.get_iter_at_offset(body),buffer.get_iter_at_offset(last),False)
                remaining=anchor.offset;offset=0
                for offset,char in enumerate(text):
                    if not char.isspace():
                        if remaining<=0:break
                        remaining-=1
                tab._appearance_anchor=(anchor.reference,offset) if anchor.at_body else None
                tab._jump_reference=None if anchor.at_body else anchor.reference;tab.schedule_scroll_restore()
        elif immersion.kind=='commentary':
            section=immersion.source.reader.index.sections[key]
            tab.state.commentary_positions[tab.state.commentary]=dict(reference=section.start,index=section.index,offset=anchor.offset,canonical=True,immersive=True)
            if tab is self.active_tab:self.study.resume(key,anchor)
        self.update_navigation() if immersion.kind=='bible' else None
        self.schedule_save()

    def add_action_callback(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        self.add_action(action)

    @property
    def active_tab(self):
        page = self.view.get_selected_page()
        return page.get_child() if page else None

    @property
    def previous(self):
        return self.active_tab.previous

    @property
    def following(self):
        return self.active_tab.following

    def tabs(self):
        return [self.view.get_nth_page(index).get_child() for index in range(self.view.get_n_pages())]

    def append_tab(self, state, jump_to_reference=False):
        tab = ReadingTab(self.library, state, self.tab_changed, jump_to_reference,
                         self.notes_store, self.open_passage_notes, self.preferences.value)
        self.reading_sync.bind(tab.scroll,tab.text,'bible',tab)
        tab.text.add_css_class(self.reading_style.scope)
        tab.reading_overlay.add_css_class(self.reading_style.scope+'-surface')
        self.reading_style.decorate(tab.comparison_text)
        page = self.view.append(tab)
        page.set_title(tab.title())
        return page

    def new_tab(self):
        if self.immersion:self.leave_immersion()
        current = self.active_tab
        names = self.library.installed('bible')
        state = TabState(current.state.resource, current.state.reference, current.state.scroll,
                         commentary=current.state.commentary) if current else TabState(
            resource=names[0] if names else None)
        page = self.append_tab(state)
        self.view.set_selected_page(page)
        self.schedule_save()
        page.get_child().text.grab_focus()
        return page.get_child()

    def navigate_selection(self, resource, reference, new_tab=False):
        try:
            if new_tab:
                from .sword_provider import Reader
                reader = Reader(self.library.root / resource, resource)
                if not reader.has_reference(reference):
                    raise ValueError(tr('This passage is not available in this translation.'))
                page = self.append_tab(TabState(resource, reader.key(reference).getOSISRef(),
                                                commentary=self.active_tab.state.commentary if self.active_tab else None),
                                       jump_to_reference=True)
                self.view.set_selected_page(page)
                self.schedule_save()
                return True
            return bool(self.active_tab and self.active_tab.navigate(resource, reference))
        except Exception as error:
            if self.active_tab:
                self.active_tab.status.set_text(f'{tr("Unable to read this passage.")} {error}')
                self.active_tab.status.set_visible(True)
            return False

    def choose_passage(self, direct=False):
        if self.immersion and self.immersion.kind=='commentary':self.leave_immersion()
        button=self.immersion.passage_button if self.immersion else self.passage_button
        if self.immersion:self.immersion.reveal_controls()
        button.set_active(True)
        self.navigation.sync(force=True)
        (self.navigation.direct if direct else self.navigation.search).grab_focus()

    def step_chapter(self, direction):
        tab = self.active_tab
        if tab and tab.reader:
            previous, following = tab.reader.neighbours(tab.state.reference)
            reference = previous if direction < 0 else following
            if reference:
                tab.show(reference)

    def update_navigation(self):
        tab = self.active_tab
        if not tab:
            return
        parent=self.reader_controls.get_parent()
        if parent is not tab.reading_overlay:
            if parent:parent.remove_overlay(self.reader_controls)
            tab.reading_overlay.add_overlay(self.reader_controls)
        self.immersive_button.set_sensitive(tab.reader is not None)
        self.lookup_action('immersive').set_enabled(tab.reader is not None)
        for name in ['copy-passage','copy-with-reference','copy-reference']:
            self.lookup_action(name).set_enabled(tab.reader is not None and not (self.immersion and self.immersion.kind=='commentary'))
        self.heading.set_title(tab.passage_title())
        subtitle = module_name(tab.state.resource) if tab.state.resource else tr('Choose a translation')
        if tab.state.resource and tab.state.resource not in self.library.installed():
            subtitle += f' ({tr("Missing translation")})'
        self.heading.set_subtitle(subtitle)
        self.passage_button.set_tooltip_text(f'{tab.passage_title()} — {subtitle}\n{tr("Choose a passage")} (Ctrl+G)')
        self.passage_button.update_property([Gtk.AccessibleProperty.LABEL],
                                             [f'{tr("Choose a passage")}: {tab.passage_title()} — {subtitle}'])
        previous, following = tab.reader.neighbours(tab.state.reference) if tab.reader else (None, None)
        self.lookup_action('previous-chapter').set_enabled(previous is not None)
        self.lookup_action('next-chapter').set_enabled(following is not None)
        self.navigation.sync()
        self.sync_comparison()
        self.lookup_action('history-back').set_enabled(tab.state.history_index>0)
        self.lookup_action('history-forward').set_enabled(tab.state.history_index+1<len(tab.state.history))
        self.study.refresh()
        tab.update_notes()

    def apply_appearance(self,reflow=True):
        self.reading_style.apply_mode()
        if not reflow:return
        for tab in self.tabs():tab.apply_appearance()
        self.reading_style.apply_text(self.study.text)
        if self.active_tab:self.active_tab.refresh_comparison()
        if self.immersion:self.immersion.reflow()

    def sync_comparison(self):
        tab=self.active_tab
        self._comparison_syncing=True
        self._comparison_names=[None]+[name for name in self.library.installed('bible') if name!=tab.state.resource]
        labels=[tr('No comparison')]+[self.library.resource(name).description for name in self._comparison_names[1:]]
        # Never replace the dropdown's model recursively from its notification.
        if getattr(self,'_comparison_labels',None)!=labels:
            self.comparison_choices.set_model(Gtk.StringList.new(labels));self._comparison_labels=labels
        self.comparison_choices.set_selected(self._comparison_names.index(tab.state.comparison) if tab.state.comparison in self._comparison_names else 0)
        self.comparison_choices.update_property([Gtk.AccessibleProperty.LABEL],[tr('Compare translations')])
        self._comparison_syncing=False
        tab.refresh_comparison()

    def comparison_selected(self,widget,*_):
        if self._comparison_syncing or not self.active_tab:return
        index=widget.get_selected()
        self.active_tab.state.comparison=self._comparison_names[index] if index<len(self._comparison_names) else None
        self.active_tab.refresh_comparison()
        self.schedule_save()

    def close_tab(self):
        if self.immersion:self.leave_immersion()
        page = self.view.get_selected_page()
        if page:
            self.view.close_page(page)

    def page_detached(self, *_):
        if self.closed:
            return
        if self.view.get_n_pages() == 0:
            self.append_tab(TabState())
        self.schedule_save()

    def tab_changed(self, tab):
        if self.immersion and self.immersion.kind=='bible' and tab is self.immersion.tab:
            current=self.immersion.stream.anchor() if self.immersion.stream.cursor else self.immersion.initial_anchor
            if current.reference!=tab.state.reference or self.immersion.source.reader is not tab.reader:
                source=BiblePages(tab.reader,self.library.resource(tab.state.resource))
                self.immersion.source=source;self.immersion.stream.source=source
                self.immersion.go_to_reference(tab.state.reference)
        if self._initializing:
            return
        for index in range(self.view.get_n_pages()):
            page = self.view.get_nth_page(index)
            if page.get_child() is tab:
                page.set_title(tab.title())
                break
        if tab is self.active_tab:
            self.update_navigation()
        self.schedule_save()

    def selected_changed(self, *_):
        if self.immersion:self.leave_immersion()
        self.reading_sync.driver=None
        tab = self.active_tab
        if tab is None:
            return
        self._syncing_study = True
        self.study_button.set_active(tab.state.study_visible)
        self.split.set_show_sidebar(tab.state.study_visible)
        self._syncing_study = False
        self.update_navigation()
        self.schedule_save()

    def toggle_study(self, *_):
        if not self._syncing_study:
            self.split.set_show_sidebar(self.study_button.get_active())

    def sidebar_changed(self, *_):
        if self._syncing_study:
            return
        visible = self.split.get_show_sidebar()
        self._syncing_study = True
        self.study_button.set_active(visible)
        if self.active_tab:
            self.active_tab.state.study_visible = visible
        self._syncing_study = False
        self.schedule_save()

    def open_library(self, kind=None):
        if self.immersion:self.leave_immersion()
        if self.catalogue_window is None or self.catalogue_window.closed:
            self.catalogue_window = CatalogueWindow(self, self.library, self.resource_installed)
        if kind is not None:
            self.catalogue_window.kind.set_selected(1 if kind == 'commentary' else 0)
        self.catalogue_window.present()
        return self.catalogue_window

    def resource_installed(self, name):
        if self.closed:
            return
        resource = self.library.resource(name)
        if resource.kind == 'commentary':
            self.study._readers.pop(name, None)
            if self.active_tab:
                self.active_tab.state.commentary = name
                self.study_button.set_active(True)
                self.study.refresh(force=True)
                self.schedule_save()
            return
        for tab in self.tabs():
            if tab.state.resource is None and tab is self.active_tab:
                tab.state.resource = name
            if tab.state.resource == name:
                tab.load_resource()
                self.tab_changed(tab)
        self.update_navigation()

    def notes_changed(self):
        for tab in self.tabs():
            tab.update_notes(force=True)
        if self.notes_window and not self.notes_window.closed:
            self.notes_window.labels.set_suggestions(self.notes_store.labels())
            self.notes_window.refresh()

    def open_notes(self):
        if self.immersion:self.leave_immersion()
        if self.notes_store is None:return
        if self.notes_space is None:
            self.notes_space=NotesSpace(self)
            self.notes_window=self.notes_space
            self.main_pages.add_named(self.notes_space,'notes')
        self.notes_space.refresh();self.notes_space.present()
        return self.notes_space

    def new_note(self, force_new=False):
        override=self.immersion.selected_passage() if self.immersion and self.immersion.kind=='bible' else None
        if self.immersion:self.leave_immersion()
        tab = self.active_tab
        if not self.notes_store or tab is None or tab.reader is None:
            self.notes_status.set_text(tr('Open a Bible passage before creating a note.'))
            self.notes_status.set_visible(True)
            return
        start, end = override or tab.selected_passage()
        matching = self.notes_store.passage(tab.reader.versification, start, end)
        if matching and not force_new:
            return self.open_passage_notes((start,end))
        context = dict(versification=tab.reader.versification, start=start, end=end,
                       origin_translation=tab.state.resource,
                       origin_language=self.library.resource(tab.state.resource).language)
        return self.edit_note(context=context)

    def open_passage_notes(self, passage=None):
        tab = self.active_tab
        if not self.notes_store or not tab or not tab.reader:
            return
        start, end = passage or tab.selected_passage()
        notes = self.notes_store.passage(tab.reader.versification, start, end)
        if len(notes) == 1:
            return self.edit_note(note=notes[0])
        if not notes:
            return self.new_note(force_new=True)
        window = self.open_notes()
        window.search.set_text('')
        window.labels.set_values([])
        window.passage_filter = (tab.reader.versification, start, end)
        window.refresh()
        return window

    def edit_note(self, note=None, context=None, explanation=''):
        if self.note_editor and not self.note_editor.closed:
            self.note_editor.status.set_text(tr('Save or close the current note before opening another.'))
            self.note_editor.present()
            return self.note_editor
        self.notes_status.set_visible(False)
        self.note_editor = NoteEditor(self, note=note, context=context, explanation=explanation)
        self.note_editor.present()
        return self.note_editor

    def open_saved_note(self, note, edit=True):
        note = self.notes_store.get(note.id)
        if note is None:
            return
        if edit and self.main_pages.get_visible_child_name()=='notes':
            return self.notes_space.open_note(note)
        from .sword_provider import Reader
        tab = self.active_tab
        candidates = list(dict.fromkeys([tab.state.resource if tab else None,
                                         note.origin_translation, *self.library.installed('bible')]))
        explanation = tr('No compatible translation installed. The note remains available.')
        for name in candidates:
            if name not in self.library.installed('bible'):
                continue
            try:
                reader = tab.reader if tab and tab.state.resource == name and tab.reader else Reader(self.library.root / name, name)
                if (reader.versification == note.versification and reader.has_reference(note.start)
                        and reader.has_reference(note.end)):
                    if self.navigate_selection(name, note.start):
                        explanation = ''
                        break
            except Exception:
                continue
        if explanation:
            explanation += f' [{note.versification}]'
        return self.edit_note(note=note, explanation=explanation) if edit else not explanation

    def schedule_save(self):
        if self._initializing or self.closed or not self._session_writable:
            return
        if self._save_id:
            GLib.source_remove(self._save_id)
        self._save_id = GLib.timeout_add(300, self.save_session)

    def save_session(self):
        self._save_id = 0
        if not self._session_writable:
            return False
        pages = self.tabs()
        if not pages:
            return False
        selected = pages.index(self.active_tab) if self.active_tab in pages else 0
        try:
            self.store.save(Session([tab.state for tab in pages], selected))
            self.session_status.set_visible(False)
        except OSError as error:
            self.report_session_error(tr('Unable to save the session.'), error)
        return False

    def report_session_error(self, message, error):
        self.session_status.set_text(f'{message}\n{error}')
        self.session_status.set_visible(True)

    def on_close(self, *_):
        if self.immersion:self.leave_immersion()
        if self.note_editor and not self.note_editor.closed:
            self.note_editor.after_close = self.close
            self.note_editor.close()
            return True
        if self._save_id:
            GLib.source_remove(self._save_id)
            self._save_id = 0
        self.save_session()
        self.closed = True
        self.study.cancel_reveal()
        self.reading_style.close()
        Gtk.StyleContext.remove_provider_for_display(self.get_display(),self.appearance.swatch_css)
        if self.notes_space:self.notes_space.closed=True
        if self.notes_store:
            self.notes_store.close()
        if self.catalogue_window is not None and not self.catalogue_window.closed:
            self.catalogue_window.close()
        return False


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id='io.github.icfmp.Bible')

    def do_activate(self):
        if not self.get_active_window():
            root = Path(GLib.get_user_data_dir()) / 'bible' / 'translations'
            Window(self, Library(root)).present()
        else:
            self.get_active_window().present()


def main():
    return Application().run()
