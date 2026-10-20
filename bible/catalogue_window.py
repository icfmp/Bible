"""Catalogue/download UI kept separate from the reading surface."""
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, GLib, Gtk, Pango, Gio, GObject

from .i18n import tr
from .library import catalogues as catalogue
from .providers import PROVIDERS
from .book_names import normalized
from .resource_details import details, language_name, plain
from .language_picker import LanguagePicker


class ResourceItem(GObject.Object):
    def __init__(self,resource):
        super().__init__();self.resource=resource


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
        self.source_ids = [None] + [p.id for p in PROVIDERS]
        self._filtering = False
        self.busy = False
        self.closed = False
        self._task_id = 0
        self._pulse_id = 0
        self._phase = "idle"
        self._indeterminate = False
        self._pending_progress = None
        self._progress_lock = Lock()
        self.connect('close-request', self.on_close)
        layout=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header=Adw.HeaderBar()
        self.back_button=Gtk.Button(icon_name='go-previous-symbolic',tooltip_text=tr('Back'),visible=False)
        self.back_button.connect('clicked',self.back_to_list);header.pack_start(self.back_button)
        header.set_title_widget(Adw.WindowTitle(title=tr('Library')))
        self.catalogue_button=Gtk.Button(icon_name='view-refresh-symbolic',tooltip_text=tr('Refresh catalogue'))
        self.catalogue_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Refresh catalogue')])
        self.catalogue_button.connect('clicked',self.load_catalogue);header.pack_end(self.catalogue_button)
        layout.append(header)
        self.pages=Gtk.Stack(vexpand=True)
        explorer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10)
        views=Gtk.Box(spacing=0,halign=Gtk.Align.CENTER);views.add_css_class('linked')
        self.explore_button=Gtk.ToggleButton(label=tr('Explore'),active=True)
        self.installed_only=Gtk.ToggleButton(label=tr('Installed resources'),group=self.explore_button)
        self.installed_only.connect('toggled',self.update_languages)
        views.append(self.explore_button);views.append(self.installed_only);explorer.append(views)
        self.search=Gtk.SearchEntry(placeholder_text=tr('Search resources'),margin_start=12,margin_end=12)
        self.search.update_property([Gtk.AccessibleProperty.LABEL],[tr('Search resources')])
        self.search.connect('search-changed',self.filter_resources);explorer.append(self.search)
        filters=Gtk.Box(spacing=8,margin_start=12,margin_end=12)
        self.kind=Gtk.DropDown(model=Gtk.StringList.new([tr('Bibles'),tr('Commentaries')]))
        self.kind.update_property([Gtk.AccessibleProperty.LABEL],[tr('Resource type')])
        self.kind.connect('notify::selected',self.update_languages)
        filters.append(self.kind)
        self.language=LanguagePicker(self.filter_resources);self.language.set_hexpand(True)
        self.language.update_property([Gtk.AccessibleProperty.LABEL],[tr('Language')]);filters.append(self.language)
        explorer.append(filters)
        self.source_filter=Gtk.DropDown(model=Gtk.StringList.new([tr('All sources')]+[p.name for p in PROVIDERS]),margin_start=12,margin_end=12)
        self.source_filter.update_property([Gtk.AccessibleProperty.LABEL],[tr('Source')])
        self.source_filter.connect('notify::selected',self.update_languages);explorer.append(self.source_filter)
        self.choice_model=Gio.ListStore.new(ResourceItem)
        self.choices=Gtk.SingleSelection(model=self.choice_model)
        self.choices.connect('notify::selected',self.selection_changed)
        factory=Gtk.SignalListItemFactory()
        factory.connect('setup',self.setup_resource_row);factory.connect('bind',self.bind_resource_row)
        self.resource_list=Gtk.ListView(model=self.choices,factory=factory,single_click_activate=True)
        self.resource_list.add_css_class('navigation-sidebar')
        self.resource_list.connect('activate',self.open_details)
        self.list_scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.list_scroll.set_child(self.resource_list);explorer.append(self.list_scroll)
        self.empty=Gtk.Label(label=tr('No matching resource.'),wrap=True,visible=False,margin_top=20,margin_bottom=20)
        explorer.append(self.empty)
        self.pages.add_named(explorer,'list')
        detail=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,margin_start=20,margin_end=20,margin_top=12,margin_bottom=12)
        self.metadata=Gtk.Label(xalign=0,yalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,selectable=True,max_width_chars=55)
        metadata_scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        metadata_scroll.set_child(self.metadata);detail.append(metadata_scroll)
        self.download_button=Gtk.Button(label=tr('Download'),sensitive=False,halign=Gtk.Align.CENTER)
        self.download_button.add_css_class('suggested-action')
        self.download_button.connect('clicked',self.install);detail.append(self.download_button)
        self.pages.add_named(detail,'detail');layout.append(self.pages)
        self.progress=Gtk.ProgressBar(margin_start=12,margin_end=12,visible=False)
        layout.append(self.progress)
        self.status=Gtk.Label(xalign=0,wrap=True,selectable=True,margin_start=12,margin_end=12,margin_bottom=12,visible=False)
        layout.append(self.status)
        self.set_content(layout)
        self.update_languages()
        self._catalogue_requested=False
        self.connect('map',lambda *_:GLib.timeout_add(100,self.auto_load))

    def auto_load(self,*_):
        if not self.closed and not self._catalogue_requested and not self.busy and not self.resources and not self.installed_only.get_active():self.load_catalogue()
        return False

    def setup_resource_row(self,_,item):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,margin_start=12,margin_end=12,margin_top=10,margin_bottom=10)
        title=Gtk.Label(xalign=0,ellipsize=Pango.EllipsizeMode.END,max_width_chars=40,width_chars=1)
        title.add_css_class('heading');box.append(title)
        subtitle=Gtk.Label(xalign=0,wrap=True,max_width_chars=40)
        subtitle.add_css_class('dim-label');box.append(subtitle)
        item.set_child(box)

    def bind_resource_row(self,_,item):
        resource=item.get_item().resource
        box=item.get_child();title=box.get_first_child();subtitle=title.get_next_sibling()
        title.set_text(plain(resource.description))
        installed=resource.id in getattr(self,'_installed_ids',set())
        subtitle.set_text(language_name(resource.language)+' — '+resource.source+(' · '+tr('Installed') if installed else ''))
        box.set_tooltip_text(resource.name+' · '+resource.language)

    def open_details(self,_,index):
        self._list_position=self.list_scroll.get_vadjustment().get_value()
        self.choices.set_selected(index);self.selection_changed()
        self.pages.set_visible_child_name('detail');self.back_button.set_visible(True)

    def back_to_list(self,*_):
        self.pages.set_visible_child_name('list');self.back_button.set_visible(False)
        self.list_scroll.get_vadjustment().set_value(getattr(self,'_list_position',0))

    def current_resources(self):
        resources = ([self.library.resource(name) for name in self.library.installed()]
                     if self.installed_only.get_active() else self.resources)
        kind = 'commentary' if self.kind.get_selected() == 1 else 'bible'
        index = self.source_filter.get_selected()
        provider_id = self.source_ids[index] if index < len(self.source_ids) else None
        return [resource for resource in resources if resource.kind == kind
                and (provider_id is None or resource.provider_id == provider_id)]

    def update_languages(self, *_):
        self._filtering=True
        self.languages=['']+sorted({r.language for r in self.current_resources()},key=lambda code:language_name(code).casefold())
        self.language.set_codes(self.languages)
        self._filtering=False
        self.filter_resources()
        if not self.installed_only.get_active() and not self.busy and not self.resources and self.get_mapped():
            GLib.idle_add(self.auto_load)

    def filter_resources(self, *_):
        if self.closed:return False
        if self._filtering:
            return
        index = self.language.get_selected()
        language = self.languages[index] if index < len(self.languages) else ''
        query = normalized(self.search.get_text())
        self.filtered_resources = [r for r in self.current_resources()
                                   if (not language or r.language == language)
                                   and query in normalized(' '.join((r.name, r.description,
                                                                    r.language, language_name(r.language))))]
        self._installed_ids=set(self.library.installed())
        self.choice_model.splice(0,self.choice_model.get_n_items(),[ResourceItem(r) for r in self.filtered_resources])
        self.choices.set_selected(0)
        self.empty.set_visible(not self.filtered_resources)
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
                                               and resource.id not in self.library.installed())
                                           and not self.busy)
        # Browsing/back navigation stays available during a transfer. The
        # captured resource, not the current selection, owns that task.
        self.progress.set_visible(self.busy)


    def on_close(self, *_):
        if self.busy and not self.owner.closed:
            self.set_visible(False)
            return True
        self.closed = True
        self.stop_animation()
        self.executor.shutdown(wait=False, cancel_futures=True)
        return False

    def task(self, message, action, finished, success_text=None):
        if self.busy:
            return
        self.busy = True
        self._task_id += 1
        self._phase = "downloading"
        self._indeterminate = True
        self.status.set_visible(True)
        self.progress.set_visible(True)
        self.status.set_text(tr(message))
        self.progress.set_fraction(0)
        self.progress.set_show_text(True)
        self.progress.set_text(tr(message))
        self._pulse_id = GLib.timeout_add(80, self.animate_progress)
        self.refresh_controls()
        future = self.executor.submit(action)

        def complete():
            if self.closed:
                return False
            self.busy = False
            self.stop_animation()
            try:
                value = future.result()
                finished(value)
                self._phase = "complete"
                self.progress.set_fraction(1 if success_text else 0)
                self.progress.set_text(success_text or "")
            except Exception as error:
                self._phase = "error"
                self.progress.set_fraction(0)
                self.progress.set_text(tr("Failed"))
                self.status.set_text(f'{error}\n{tr("Retry using the same button.")}')
            finally:
                self.refresh_controls()
            return False

        future.add_done_callback(lambda _: GLib.idle_add(complete))

    def load_catalogue(self, *_):
        self._catalogue_requested=True
        def loaded(result):
            errors = getattr(result, 'errors', {})
            resources = getattr(result, 'resources', result)
            self.resources = list(resources)
            self.installed_only.set_active(False)
            self.update_languages()
            self.status.set_text(
                tr('Partial catalogue. Retry to reload unavailable sources.') + '\n' +
                '\n'.join(f'{name}: {error}' for name, error in errors.items())
                if errors else tr('Ready') if resources else tr('No supported resource found.'))
        self.task('Loading catalogue…', catalogue, loaded)

    def stop_animation(self):
        if self._pulse_id:
            GLib.source_remove(self._pulse_id)
            self._pulse_id = 0
        with self._progress_lock:
            self._pending_progress = None

    def queue_progress(self, phase, done=0, total=0):
        # Worker threads only publish data. The GTK timeout coalesces updates
        # and animates while a network read or validation is waiting.
        with self._progress_lock:
            self._pending_progress = (self._task_id, phase, done, total)

    def animate_progress(self):
        if self.closed or not self.busy:
            self._pulse_id = 0
            return False
        with self._progress_lock:
            pending, self._pending_progress = self._pending_progress, None
        if pending and pending[0] == self._task_id:
            _, self._phase, done, total = pending
            self._indeterminate = self._phase == 'installing' or not total
            if self._phase == 'installing':
                self.status.set_text(tr('Installing and checking…'))
                self.progress.set_fraction(0)
                self.progress.set_text(tr('Installing and checking…'))
            else:
                self.progress.set_fraction(min(done / total, 1) if total else 0)
                self.progress.set_text(f'{done / 1024:.1f} KiB' +
                                       (f' / {total / 1024:.1f} KiB ({min(done * 100 // total, 100)}%)'
                                        if total else ' — ' + tr('Size unknown')))
        if self._indeterminate:
            self.progress.pulse()
        return True

    def report_progress(self, done, total):
        self.queue_progress('downloading', done, total)

    def install(self, *_):
        resource = self.selected_resource()
        if not resource or not resource.installable or self.busy:
            return

        def installed(_):
            self.on_installed(resource.id)
            self.filter_resources()
            self.status.set_text(tr('Installed: {name}').format(name=resource.name))
            self.selection_changed()
        self.task(tr('Downloading {name}…').format(name=resource.name),
                  lambda: self.library.install(resource, self.report_progress,
                                                installing=lambda: self.queue_progress('installing')),
                  installed, success_text=tr('Installed: {name}').format(name=resource.name))

