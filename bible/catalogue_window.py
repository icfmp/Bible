"""Catalogue/download UI kept separate from the reading surface."""
from concurrent.futures import ThreadPoolExecutor
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, GLib, Gtk, Pango

from .i18n import tr
from .library import catalogue


class CatalogueWindow(Adw.Window):
    def __init__(self, parent, library, on_installed):
        super().__init__(transient_for=parent, modal=True, title=tr('Translations'),
                         default_width=560, default_height=350)
        self.library, self.on_installed = library, on_installed
        self.owner = parent
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='bible-download')
        self.resources = []
        self.busy = False
        self.closed = False
        self.connect('close-request', self.on_close)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title=tr('Translations')))
        layout.append(header)
        self.catalogue_button = Gtk.Button(label=tr('Load catalogue'), margin_start=12, margin_end=12)
        self.catalogue_button.connect('clicked', self.load_catalogue)
        layout.append(self.catalogue_button)
        self.choices = Gtk.DropDown(model=Gtk.StringList.new([]), margin_start=12, margin_end=12)
        factory = Gtk.SignalListItemFactory()
        factory.connect('setup', lambda _, item: item.set_child(Gtk.Label(
            xalign=0, ellipsize=Pango.EllipsizeMode.END, max_width_chars=44)))
        factory.connect('bind', lambda _, item: item.get_child().set_text(item.get_item().get_string()))
        self.choices.set_factory(factory)
        self.choices.set_list_factory(factory)
        layout.append(self.choices)
        self.download_button = Gtk.Button(label=tr('Download'), sensitive=False,
                                          margin_start=12, margin_end=12)
        self.download_button.connect('clicked', self.install)
        layout.append(self.download_button)
        layout.append(Gtk.Label(label=tr('Downloadable resources — source: CrossWire'),
                                wrap=True, margin_start=12, margin_end=12))
        self.progress = Gtk.ProgressBar(margin_start=12, margin_end=12)
        layout.append(self.progress)
        self.status = Gtk.Label(xalign=0, wrap=True, selectable=True,
                                margin_start=12, margin_end=12, margin_bottom=12)
        layout.append(self.status)
        self.set_content(layout)

    def refresh_controls(self):
        self.catalogue_button.set_sensitive(not self.busy)
        self.download_button.set_sensitive(bool(self.resources) and not self.busy)
        self.choices.set_sensitive(not self.busy)

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
            self.choices.set_model(Gtk.StringList.new([
                f'{r.language} — {r.description} ({r.name}) — {r.license}' for r in resources]))
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
        index = self.choices.get_selected()
        if index >= len(self.resources):
            return
        resource = self.resources[index]

        def installed(_):
            self.on_installed(resource.name)
            self.status.set_text(tr('Ready'))
        self.task('Downloading…', lambda: self.library.install(resource, self.report_progress), installed)

