"""Catalogue/download UI kept separate from the reading surface."""
from concurrent.futures import ThreadPoolExecutor
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, GLib, Gtk, Pango

from .i18n import tr
from .library import catalogue
from .book_names import normalized
from .resource_details import details, language_name


class CatalogueWindow(Adw.Window):
    def __init__(self, parent, library, on_installed):
        super().__init__(transient_for=parent, modal=True, title=tr('Library'),
                         default_width=560, default_height=640)
        self.library, self.on_installed = library, on_installed
        self.owner = parent
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='bible-download')
        self.resources = []
        self.filtered_resources = []
        self.languages = []
        self._filtering = False
        self.busy = False
        self.closed = False
        self.connect('close-request', self.on_close)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=tr('Library')))
        layout.append(header)
        self.catalogue_button = Gtk.Button(label=tr('Load catalogue'), margin_start=12, margin_end=12)
        self.catalogue_button.connect('clicked', self.load_catalogue)
        layout.append(self.catalogue_button)
        layout.append(Gtk.Label(label=tr('Resource type'), xalign=0, margin_start=12))
        self.kind = Gtk.DropDown(model=Gtk.StringList.new([tr('Bibles'), tr('Commentaries')]),
                                 margin_start=12, margin_end=12)
        self.kind.update_property([Gtk.AccessibleProperty.LABEL], [tr('Resource type')])
        self.kind.connect('notify::selected', self.update_languages)
        layout.append(self.kind)
        self.installed_only = Gtk.CheckButton(label=tr('Installed resources'),
                                               margin_start=12, margin_end=12)
        self.installed_only.connect('toggled', self.update_languages)
        layout.append(self.installed_only)
        layout.append(Gtk.Label(label=tr('Language'), xalign=0, margin_start=12))
        self.language = Gtk.DropDown(margin_start=12, margin_end=12)
        self.language.update_property([Gtk.AccessibleProperty.LABEL], [tr('Language')])
        self.language.connect('notify::selected', self.filter_resources)
        layout.append(self.language)
        self.search = Gtk.SearchEntry(placeholder_text=tr('Search resources'),
                                      margin_start=12, margin_end=12)
        self.search.update_property([Gtk.AccessibleProperty.LABEL], [tr('Search resources')])
        self.search.connect('search-changed', self.filter_resources)
        layout.append(self.search)
        self.choices = Gtk.DropDown(model=Gtk.StringList.new([]), margin_start=12, margin_end=12)
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', lambda _, item: item.set_child(Gtk.Label(
            xalign=0, ellipsize=Pango.EllipsizeMode.END, width_chars=1, max_width_chars=44)))
        factory.connect('bind', lambda _, item: item.get_child().set_text(item.get_item().get_string()))
        self.choices.set_factory(factory)
        self.choices.set_list_factory(factory)
        self.choices.update_property([Gtk.AccessibleProperty.LABEL], [tr('Resources')])
        self.choices.connect('notify::selected', self.selection_changed)
        layout.append(self.choices)
        self.metadata = Gtk.Label(xalign=0, yalign=0, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR, selectable=True,
                                  margin_start=12, margin_end=12, max_width_chars=60)
        metadata_scroll = Gtk.ScrolledWindow(vexpand=True, min_content_height=140,
                                             hscrollbar_policy=Gtk.PolicyType.NEVER)
        metadata_scroll.set_child(self.metadata)
        layout.append(metadata_scroll)
        self.download_button = Gtk.Button(label=tr('Download'), sensitive=False,
                                          margin_start=12, margin_end=12)
        self.download_button.connect('clicked', self.install)
        layout.append(self.download_button)
        layout.append(Gtk.Label(label=tr('Source: CrossWire'),
                                wrap=True, margin_start=12, margin_end=12))
        self.progress = Gtk.ProgressBar(margin_start=12, margin_end=12)
        layout.append(self.progress)
        self.status = Gtk.Label(xalign=0, wrap=True, selectable=True,
                                margin_start=12, margin_end=12, margin_bottom=12)
        layout.append(self.status)
        self.set_content(layout)
        self.update_languages()

    def current_resources(self):
        resources = ([self.library.resource(name) for name in self.library.installed()]
                     if self.installed_only.get_active() else self.resources)
        kind = 'commentary' if self.kind.get_selected() == 1 else 'bible'
        return [resource for resource in resources if resource.kind == kind]

    def update_languages(self, *_):
        previous = (self.languages[self.language.get_selected()]
                    if self.language.get_selected() < len(self.languages) else '')
        self._filtering = True
        self.languages = [''] + sorted({r.language for r in self.current_resources()})
        self.language.set_model(Gtk.StringList.new([
            language_name(code) if code else tr('All languages') for code in self.languages]))
        self.language.set_selected(self.languages.index(previous) if previous in self.languages else 0)
        self._filtering = False
        self.filter_resources()

    def filter_resources(self, *_):
        if self._filtering:
            return
        index = self.language.get_selected()
        language = self.languages[index] if index < len(self.languages) else ''
        query = normalized(self.search.get_text())
        self.filtered_resources = [r for r in self.current_resources()
                                   if (not language or r.language == language)
                                   and query in normalized(' '.join((r.name, r.description,
                                                                    r.language, language_name(r.language))))]
        self.choices.set_model(Gtk.StringList.new([
            f'{r.description} ({r.name})' for r in self.filtered_resources]))
        self.choices.set_selected(0)
        self.selection_changed()

    def selected_resource(self):
        index = self.choices.get_selected()
        return self.filtered_resources[index] if index < len(self.filtered_resources) else None

    def selection_changed(self, *_):
        resource = self.selected_resource()
        self.metadata.set_text(details(resource) if resource else tr('No matching resource.'))
        self.refresh_controls()

    def refresh_controls(self):
        resource = self.selected_resource()
        self.catalogue_button.set_sensitive(not self.busy)
        self.download_button.set_sensitive(bool(resource and resource.installable
                                               and resource.name not in self.library.installed())
                                           and not self.busy)
        for widget in (self.choices, self.language, self.search, self.installed_only, self.kind):
            widget.set_sensitive(not self.busy)

    def on_close(self, *_):
        if self.busy and not self.owner.closed:
            self.set_visible(False)
            return True
        self.closed = True
        self.executor.shutdown(wait=False, cancel_futures=True)
        return False

    def task(self, message, action, finished):
        if self.busy:
            return
        self.busy = True
        self.status.set_text(tr(message))
        self.progress.set_fraction(0)
        self.refresh_controls()
        future = self.executor.submit(action)

        def complete():
            if self.closed:
                return False
            self.busy = False
            try:
                value = future.result()
                finished(value)
            except Exception as error:
                self.status.set_text(f'{error}\n{tr("Retry using the same button.")}')
            finally:
                self.progress.set_fraction(0)
                self.refresh_controls()
            return False

        future.add_done_callback(lambda _: GLib.idle_add(complete))

    def load_catalogue(self, *_):
        def loaded(resources):
            self.resources = resources
            self.installed_only.set_active(False)
            self.update_languages()
            self.status.set_text(tr('Ready') if resources else tr('No supported resource found.'))
        self.task('Loading catalogue…', catalogue, loaded)

    def report_progress(self, done, total):
        def update():
            if self.closed or not self.busy:
                return False
            if total:
                self.progress.set_fraction(min(done / total, 1))
            else:
                self.progress.pulse()
            self.progress.set_show_text(True)
            self.progress.set_text(f'{done // 1024} KiB' + (f' / {total // 1024} KiB' if total else ''))
            return False
        GLib.idle_add(update)

    def install(self, *_):
        resource = self.selected_resource()
        if not resource or not resource.installable or self.busy:
            return

        def installed(_):
            self.on_installed(resource.name)
            self.status.set_text(tr('Ready'))
            self.selection_changed()
        self.task('Downloading…', lambda: self.library.install(resource, self.report_progress), installed)

