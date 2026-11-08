"""Explicit, read-only Library check over actual local module metadata."""
from gi.repository import Adw,Gtk,GLib
from .i18n import tr
from .metadata_workers import MetadataExecutor
from .module_updates import ModuleCatalogue,installed_modules,assessment


class ModuleUpdatesWindow(Adw.Window):
    def __init__(self,owner,library):
        super().__init__(transient_for=owner,modal=True,destroy_with_parent=True,title=tr('Module updates'),default_width=560,default_height=480)
        self.closed=False;self.worker=MetadataExecutor(thread_name_prefix='bible-module-check')
        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header=Adw.HeaderBar();root.append(header)
        self.status=Gtk.Label(label=tr('Checking installed modules…'),xalign=0,wrap=True,margin_start=16,margin_end=16,margin_top=12,margin_bottom=12)
        self.spinner=Gtk.Spinner(spinning=True);header.pack_end(self.spinner);root.append(self.status)
        self.rows=Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE);self.rows.add_css_class('boxed-list')
        scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER,margin_start=12,margin_end=12)
        scroll.set_child(self.rows);root.append(scroll)
        self.notice=Gtk.Label(label=tr('This check reports installed versions and curated edition availability. It does not install or replace modules.'),
            xalign=0,wrap=True,margin_start=16,margin_end=16,margin_top=12,margin_bottom=12)
        self.notice.add_css_class('caption');root.append(self.notice);self.set_content(root)
        self.connect('close-request',self.on_close)
        self.connect('unrealize',self.on_close)
        def check():
            installed,errors=installed_modules(library.root)
            try:report=ModuleCatalogue(library.root.parent/'catalogue-cache').check()
            except (OSError,ValueError,TypeError) as error:report=dict(error=str(error),catalogue=None,cached=False)
            return installed,errors,report
        future=self.worker.submit(check)
        def complete():
            if self.closed:return False
            self.spinner.set_spinning(False);self.spinner.set_visible(False)
            try:installed,errors,report=future.result()
            except Exception as error:self.status.set_text(str(error));return False
            self.report=report;self.installed=installed
            self.status.set_text(tr('Saved catalogue — the network check failed.') if report['cached'] else
                tr('Unable to check the curated catalogue.') if report['catalogue'] is None else
                tr('No curated modules have been published yet.') if not report['catalogue']['modules'] else tr('Module check complete.'))
            if report['error']:self.status.set_tooltip_text(report['error'])
            for module in installed:
                row=Adw.ActionRow(use_markup=False,title=module.title,subtitle=tr('Installed version')+': '+(module.version or tr('Unknown'))+
                    (' · '+module.source if module.source else ''))
                state=assessment(module,report['catalogue']) if report['catalogue'] else 'unavailable'
                label=Gtk.Label(label=tr('Edition identity not verified') if state=='identity-unverified' else
                    tr('No verified curated edition'),wrap=True,max_width_chars=20)
                label.add_css_class('dim-label');row.add_suffix(label);self.rows.append(row)
            if not installed:self.status.set_text(tr('No installed SWORD modules found.'))
            if errors:self.notice.set_tooltip_text('\n'.join(message for _,message in errors))
            return False
        future.add_done_callback(lambda _:GLib.idle_add(complete))

    def on_close(self,*_):
        self.closed=True;self.worker.shutdown(wait=False,cancel_futures=True)
        return False
