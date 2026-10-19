"""Native tabbed GNOME reader; downloads live in a dedicated window."""
from pathlib import Path

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from .catalogue_window import CatalogueWindow
from .i18n import tr
from .library import Library
from .reading_tab import ReadingTab
from .study_panel import StudyPanel
from .navigation import PassagePopover
from .notes import NoteStore
from .notes_window import NoteEditor, NotesWindow
from .session import Session, SessionError, SessionStore, TabState


class Window(Adw.ApplicationWindow):
    def __init__(self, app, library, session_path=None):
        super().__init__(application=app, title='Bible', default_width=960, default_height=700)
        self.set_size_request(360, 320)
        self.library = library
        self.store = SessionStore(session_path or library.root.parent / 'session.json')
        self.closed = False
        self._initializing = True
        self._syncing_study = False
        self._save_id = 0
        self._session_writable = True
        self.catalogue_window = None
        self.notes_window = None
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
        self.previous = Gtk.Button(icon_name='go-previous-symbolic', tooltip_text=tr('Previous chapter'),
                                   action_name='win.previous-chapter')
        self.following = Gtk.Button(icon_name='go-next-symbolic', tooltip_text=tr('Next chapter'),
                                    action_name='win.next-chapter')
        header.pack_start(self.previous)
        header.pack_start(self.following)
        library_button = Gtk.Button(icon_name='view-grid-symbolic', tooltip_text=tr('Library'),
                                     action_name='win.translations')
        header.pack_end(library_button)
        self.study_button = Gtk.ToggleButton(icon_name='sidebar-show-symbolic',
                                              tooltip_text=tr('Study'))
        self.study_button.connect('toggled', self.toggle_study)
        header.pack_end(self.study_button)
        commands = Gio.Menu()
        commands.append(tr('Passage note'), 'win.note')
        commands.append(tr('My notes'), 'win.notes')
        commands.append(tr('New tab'), 'win.new-tab')
        commands.append(tr('Library'), 'win.translations')
        menu = Gtk.MenuButton(icon_name='open-menu-symbolic', menu_model=commands,
                              tooltip_text=tr('Notes and commands'))
        menu.update_property([Gtk.AccessibleProperty.LABEL], [tr('Notes and commands')])
        header.pack_end(menu)
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
        self.split.set_sidebar(self.study)
        self.split.connect('notify::show-sidebar', self.sidebar_changed)
        layout.append(self.split)
        self.set_content(layout)
        breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.parse('max-width: 760px'))
        breakpoint.add_setter(self.split, 'collapsed', True)
        self.add_breakpoint(breakpoint)
        narrow_header = Adw.Breakpoint.new(Adw.BreakpointCondition.parse('max-width: 560px'))
        narrow_header.add_setter(self.split, 'collapsed', True)
        narrow_header.add_setter(self.previous, 'visible', False)
        narrow_header.add_setter(self.following, 'visible', False)
        self.add_breakpoint(narrow_header)
        tiny_header = Adw.Breakpoint.new(Adw.BreakpointCondition.parse('max-width: 420px'))
        tiny_header.add_setter(self.split, 'collapsed', True)
        tiny_header.add_setter(self.previous, 'visible', False)
        tiny_header.add_setter(self.following, 'visible', False)
        tiny_header.add_setter(library_button, 'visible', False)
        tiny_header.add_setter(new, 'visible', False)
        self.add_breakpoint(tiny_header)
        css = Gtk.CssProvider()
        css.load_from_data(b'textview.reading { font-size: 18pt; }')
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
        self.add_action_callback('note', lambda *_: self.new_note())
        self.add_action_callback('notes', lambda *_: self.open_notes())
        self.lookup_action('note').set_enabled(self.notes_store is not None)
        self.lookup_action('notes').set_enabled(self.notes_store is not None)
        self.add_action_callback('study', lambda *_: self.study_button.set_active(not self.study_button.get_active()))
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
        app.set_accels_for_action('win.previous-chapter', ['<Alt>Left'])
        app.set_accels_for_action('win.next-chapter', ['<Alt>Right'])
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

    def add_action_callback(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        self.add_action(action)

    @property
    def active_tab(self):
        page = self.view.get_selected_page()
        return page.get_child() if page else None

    def tabs(self):
        return [self.view.get_nth_page(index).get_child() for index in range(self.view.get_n_pages())]

    def append_tab(self, state, jump_to_reference=False):
        tab = ReadingTab(self.library, state, self.tab_changed, jump_to_reference,
                         self.notes_store, self.open_passage_notes)
        page = self.view.append(tab)
        page.set_title(tab.title())
        return page

    def new_tab(self):
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
        self.passage_button.set_active(True)
        self.navigation.sync(force=True)
        self.navigation.direct_expander.set_expanded(direct)
        (self.navigation.direct if direct else self.navigation.book).grab_focus()

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
        self.heading.set_title(tab.passage_title())
        subtitle = tab.state.resource or tr('Choose a translation')
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
        self.study.refresh()
        tab.update_notes()

    def close_tab(self):
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
        if self.notes_store is None:
            return
        if self.notes_window is None or self.notes_window.closed:
            self.notes_window = NotesWindow(self)
        self.notes_window.show_all()
        self.notes_window.present()
        return self.notes_window

    def new_note(self, force_new=False):
        tab = self.active_tab
        if not self.notes_store or tab is None or tab.reader is None:
            self.notes_status.set_text(tr('Open a Bible passage before creating a note.'))
            self.notes_status.set_visible(True)
            return
        start, end = tab.selected_passage()
        matching = self.notes_store.passage(tab.reader.versification, start, end)
        if matching and not force_new:
            return self.open_passage_notes()
        context = dict(versification=tab.reader.versification, start=start, end=end,
                       origin_translation=tab.state.resource,
                       origin_language=self.library.resource(tab.state.resource).language)
        return self.edit_note(context=context)

    def open_passage_notes(self):
        tab = self.active_tab
        if not self.notes_store or not tab or not tab.reader:
            return
        start, end = tab.selected_passage()
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

    def open_saved_note(self, note):
        note = self.notes_store.get(note.id)
        if note is None:
            return
        if self.note_editor and not self.note_editor.closed:
            self.note_editor.status.set_text(tr('Save or close the current note before opening another.'))
            self.note_editor.present()
            return self.note_editor
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
        return self.edit_note(note=note, explanation=explanation)

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
        if self.note_editor and not self.note_editor.closed:
            self.note_editor.after_close = self.close
            self.note_editor.close()
            return True
        if self._save_id:
            GLib.source_remove(self._save_id)
            self._save_id = 0
        self.save_session()
        self.closed = True
        if self.notes_window and not self.notes_window.closed:
            self.notes_window.close()
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
