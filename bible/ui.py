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
        self.connect('close-request', self.on_close)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title='Bible'))
        new = Gtk.Button(icon_name='tab-new-symbolic', tooltip_text=tr('New tab'),
                         action_name='win.new-tab')
        header.pack_start(new)
        library_button = Gtk.Button(icon_name='view-grid-symbolic', tooltip_text=tr('Translations'),
                                     action_name='win.translations')
        header.pack_end(library_button)
        self.study_button = Gtk.ToggleButton(icon_name='sidebar-show-symbolic',
                                              tooltip_text=tr('Study'))
        self.study_button.connect('toggled', self.toggle_study)
        header.pack_end(self.study_button)
        layout.append(header)
        self.session_status = Gtk.Label(wrap=True, xalign=0, visible=False,
                                        margin_start=12, margin_end=12)
        layout.append(self.session_status)
        self.view = Adw.TabView(vexpand=True)
        self.bar = Adw.TabBar(view=self.view, autohide=False)
        layout.append(self.bar)
        self.split = Adw.OverlaySplitView(content=self.view, show_sidebar=False,
                                          min_sidebar_width=260, max_sidebar_width=320,
                                          sidebar_position=Gtk.PackType.END)
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        panel.append(Adw.StatusPage(title=tr('Study'), icon_name='accessories-dictionary-symbolic',
                                   description=tr('Study tools are not implemented yet.'), vexpand=True))
        self.split.set_sidebar(panel)
        self.split.connect('notify::show-sidebar', self.sidebar_changed)
        layout.append(self.split)
        self.set_content(layout)
        breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.parse('max-width: 760px'))
        breakpoint.add_setter(self.split, 'collapsed', True)
        self.add_breakpoint(breakpoint)
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
        self.add_action_callback('study', lambda *_: self.study_button.set_active(not self.study_button.get_active()))
        app.set_accels_for_action('win.new-tab', ['<Control>t'])
        app.set_accels_for_action('win.close-tab', ['<Control>w'])
        app.set_accels_for_action('win.translations', ['<Control>l'])
        app.set_accels_for_action('win.study', ['F9'])
        try:
            session = self.store.load()
        except (OSError, SessionError) as error:
            self._session_writable = False
            self.report_session_error(tr('Unable to restore the session. The original file has been preserved.') + '\n' + tr('Session saving is disabled to preserve the original file.'), error)
            session = Session()
        if not session.tabs:
            names = self.library.installed()
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

    def append_tab(self, state):
        tab = ReadingTab(self.library, state, self.tab_changed, self.open_passage_in_new)
        page = self.view.append(tab)
        page.set_title(tab.title())
        return page

    def new_tab(self):
        current = self.active_tab
        names = self.library.installed()
        state = TabState(current.state.resource, current.state.reference) if current else TabState(
            resource=names[0] if names else None)
        page = self.append_tab(state)
        self.view.set_selected_page(page)
        self.schedule_save()
        page.get_child().reference.grab_focus()
        return page.get_child()

    def open_passage_in_new(self, resource, reference):
        current = self.active_tab
        if current and current.reader:
            try:
                reference = current.reader.key(reference).getOSISRef()
            except Exception as error:
                current.status.set_text(f'{tr("Unable to read this passage.")} {error}')
                return
        if current and current.current:
            current.reference.set_text(current.current.reference)
        page = self.append_tab(TabState(resource, reference))
        self.view.set_selected_page(page)
        self.schedule_save()

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
        self.schedule_save()

    def selected_changed(self, *_):
        tab = self.active_tab
        if tab is None:
            return
        self._syncing_study = True
        self.study_button.set_active(tab.state.study_visible)
        self.split.set_show_sidebar(tab.state.study_visible)
        self._syncing_study = False
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

    def open_library(self):
        if self.catalogue_window is None or self.catalogue_window.closed:
            self.catalogue_window = CatalogueWindow(self, self.library, self.resource_installed)
        self.catalogue_window.present()
        return self.catalogue_window

    def resource_installed(self, name):
        if self.closed:
            return
        for tab in self.tabs():
            if tab.state.resource is None and tab is self.active_tab:
                tab.state.resource = name
            tab.refresh_resources()
            if tab.state.resource == name:
                tab.load_resource()
                self.tab_changed(tab)

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
        if self._save_id:
            GLib.source_remove(self._save_id)
            self._save_id = 0
        self.save_session()
        self.closed = True
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
