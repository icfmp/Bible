"""Native GTK 4/libadwaita window; network work runs outside the GTK thread."""
from concurrent.futures import ThreadPoolExecutor
import locale
import os
from pathlib import Path

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, GLib, Gtk  # noqa: E402

from .library import Library, catalogue
from .sword_provider import Reader

FR = {
    'Translations': 'Traductions', 'Load catalogue': 'Charger le catalogue',
    'Download': 'Télécharger', 'Open': 'Ouvrir', 'Previous chapter': 'Chapitre précédent',
    'Next chapter': 'Chapitre suivant', 'No translation installed. Load the catalogue to choose one.':
        'Aucune traduction installée. Chargez le catalogue pour en choisir une.',
    'Loading catalogue…': 'Chargement du catalogue…', 'Downloading…': 'Téléchargement…',
    'Ready': 'Prêt', 'Retry using the same button.': 'Réessayez avec le même bouton.',
    'Reference (e.g. John 1:1)': 'Référence (par ex. John 1:1)',
    'Public domain resources — source: CrossWire': 'Ressources du domaine public — source : CrossWire',
    'No supported resource found.': 'Aucune ressource compatible trouvée.',
}
LANGUAGE = os.environ.get('LANGUAGE') or locale.getlocale()[0] or 'en'


def tr(message):
    return FR.get(message, message) if LANGUAGE.startswith('fr') else message


class Window(Adw.ApplicationWindow):
    def __init__(self, app, library):
        super().__init__(application=app, title='Bible', default_width=900, default_height=700)
        self.library = library
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='bible-download')
        self.resources = []
        self.reader = None
        self.current = None
        self.busy = False
        self.closed = False
        self.connect('close-request', self.on_close)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        header = Adw.HeaderBar()
        header.set_title_widget(Adw.WindowTitle(title='Bible', subtitle=tr('Translations')))
        layout.append(header)
        controls = Gtk.Box(spacing=8, margin_start=12, margin_end=12)
        self.catalogue_button = Gtk.Button(label=tr('Load catalogue'))
        self.catalogue_button.connect('clicked', self.load_catalogue)
        controls.append(self.catalogue_button)
        self.choices = Gtk.DropDown(model=Gtk.StringList.new([]), hexpand=True)
        controls.append(self.choices)
        self.download_button = Gtk.Button(label=tr('Download'), sensitive=False)
        self.download_button.connect('clicked', self.install)
        controls.append(self.download_button)
        layout.append(controls)
        layout.append(Gtk.Label(label=tr('Public domain resources — source: CrossWire'),
                                xalign=0, margin_start=12, wrap=True))
        installed = Gtk.Box(spacing=8, margin_start=12, margin_end=12)
        self.local = Gtk.DropDown(model=Gtk.StringList.new(self.library.installed()), hexpand=True)
        installed.append(self.local)
        self.open_button = Gtk.Button(label=tr('Open'))
        self.open_button.connect('clicked', self.open_selected)
        installed.append(self.open_button)
        layout.append(installed)
        navigation = Gtk.Box(spacing=8, margin_start=12, margin_end=12)
        self.previous = Gtk.Button(icon_name='go-previous-symbolic',
                                   tooltip_text=tr('Previous chapter'), sensitive=False)
        self.previous.connect('clicked', lambda *_: self.show(self.current.previous))
        navigation.append(self.previous)
        self.reference = Gtk.Entry(placeholder_text=tr('Reference (e.g. John 1:1)'), hexpand=True)
        self.reference.connect('activate', lambda entry: self.show(entry.get_text()))
        navigation.append(self.reference)
        self.following = Gtk.Button(icon_name='go-next-symbolic',
                                    tooltip_text=tr('Next chapter'), sensitive=False)
        self.following.connect('clicked', lambda *_: self.show(self.current.following))
        navigation.append(self.following)
        layout.append(navigation)
        self.progress = Gtk.ProgressBar(margin_start=12, margin_end=12)
        layout.append(self.progress)
        self.status = Gtk.Label(xalign=0, wrap=True, selectable=True,
                                margin_start=12, margin_end=12)
        layout.append(self.status)
        scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.text = Gtk.TextView(editable=False, cursor_visible=False,
                                 wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                 left_margin=24, right_margin=24,
                                 top_margin=16, bottom_margin=24)
        self.text.add_css_class('reading')
        scroll.set_child(self.text)
        layout.append(scroll)
        css = Gtk.CssProvider()
        css.load_from_data(b'textview.reading { font-size: 18pt; }')
        Gtk.StyleContext.add_provider_for_display(self.get_display(), css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.set_content(layout)
        if self.library.installed():
            self.open_selected()
        else:
            self.status.set_text(tr('No translation installed. Load the catalogue to choose one.'))
        self.refresh_controls()

    def refresh_controls(self):
        self.catalogue_button.set_sensitive(not self.busy)
        self.download_button.set_sensitive(bool(self.resources) and not self.busy)
        self.choices.set_sensitive(not self.busy)
        self.open_button.set_sensitive(bool(self.library.installed()) and not self.busy)
        self.local.set_sensitive(not self.busy)
        self.reference.set_sensitive(self.reader is not None)

    def on_close(self, *_):
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
                f'{r.language} — {r.description} ({r.name})' for r in resources]))
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
            names = self.library.installed()
            self.local.set_model(Gtk.StringList.new(names))
            self.local.set_selected(names.index(resource.name))
            self.open_selected()
        self.task('Downloading…', lambda: self.library.install(resource, self.report_progress), installed)

    def open_selected(self, *_):
        names = self.library.installed()
        index = self.local.get_selected()
        if index >= len(names):
            return
        name = names[index]
        try:
            reader = Reader(self.library.root / name, name)
            self.reader = reader
            self.show('Gen.1.1')
            self.refresh_controls()
        except Exception as error:
            self.status.set_text(str(error))

    def show(self, reference):
        if not self.reader or not reference:
            return
        try:
            chapter = self.reader.chapter(reference)
            self.current = chapter
            self.reference.set_text(chapter.reference)
            self.text.get_buffer().set_text('\n\n'.join(
                f'{ref.rsplit(".", 1)[-1]}  {text}' for ref, text in chapter.verses))
            self.previous.set_sensitive(chapter.previous is not None)
            self.following.set_sensitive(chapter.following is not None)
            self.status.set_text(tr('Ready'))
        except Exception as error:
            self.status.set_text(str(error))


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
