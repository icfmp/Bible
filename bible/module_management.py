"""Library actions over the shared provider, installer and module lifecycle."""
from gi.repository import Adw,Gtk,GLib
from .i18n import tr
from .providers import BY_ID
from .resource_details import plain
from .module_lifecycle import ModuleLifecycle
from .module_updates import applicable_update
from .module_ui_lifecycle import ModuleViewChange

SUPPORTED={'bible-resources','crosswire','ebible','andbible-extra'}
REASONS={
    'not-checked':'Check for updates to compare this installed edition.',
    'current':'The installed version matches the checked source catalogue.',
    'available':'Update available',
    'offline':'The source check failed. Saved metadata is not proof that this module is up to date.',
    'missing':'This installed edition is absent from the checked source catalogue.',
    'provider-unavailable':'Updates from this source are not supported.',
    'identity-changed':'Source identity or verse numbering changed. The installed module was preserved.',
    'edition-changed':'The source describes a different edition. No replacement is offered.',
    'edition-unverified':'The source does not supply enough edition identity to verify an update.',
    'identity-unverified':'The source does not supply enough edition identity to verify an update.',
    'same-version-content-changed':'The package changed without a new version. No replacement is offered.',
    'encrypted-unavailable':'Encrypted modules cannot be updated safely by this version.',
    'version-unavailable':'A comparable source version is unavailable.',
    'older-catalogue':'The checked catalogue version is older than the installed version.',
    'local-unverified':'Original package fingerprints are unavailable or local files changed. No replacement is offered.',
}


def checked_modules(library,resources,errors):
    """Worker only: edition checks and full receipt hashes never block GTK."""
    available={r.id:r for r in resources};reports={}
    lifecycle=ModuleLifecycle(library)
    for identifier in library.installed():
        try:old=library.resource(identifier)
        except (OSError,ValueError,TypeError,KeyError) as failure:
            reports[identifier]=dict(state='local-unverified',available=None,error=str(failure));continue
        new=available.get(identifier);error=''
        state=('provider-unavailable' if old.provider_id not in SUPPORTED else
               'offline' if old.source in errors or 'Library' in errors else
               'missing' if new is None else applicable_update(old,new))
        if state=='available':
            try:lifecycle.owned(identifier,unchanged=True)
            except (OSError,ValueError,TypeError) as failure:state='local-unverified';error=str(failure)
        reports[identifier]=dict(state=state,available=new,error=error)
    return reports


class ModuleManagement:
    def __init__(self,dialog,detail):
        self.dialog=dialog;self.reports={};self.revision=0;self.queue=[];self._next=0
        self.notice=Gtk.Label(xalign=0,wrap=True,selectable=True,visible=False)
        detail.append(self.notice)
        self.actions=Gtk.Box(spacing=8,halign=Gtk.Align.CENTER,visible=False)
        self.update_button=Gtk.Button(label=tr('Update'));self.update_button.connect('clicked',lambda *_:self.run('update'))
        self.rollback_button=Gtk.Button(label=tr('Restore previous version'));self.rollback_button.connect('clicked',lambda *_:self.confirm('rollback'))
        self.remove_button=Gtk.Button(label=tr('Remove'));self.remove_button.add_css_class('destructive-action')
        self.remove_button.connect('clicked',lambda *_:self.confirm('remove'))
        for button in (self.update_button,self.rollback_button,self.remove_button):self.actions.append(button)
        detail.append(self.actions)
        narrow=Adw.Breakpoint.new(Adw.BreakpointCondition.parse('max-width: 440px'))
        narrow.add_setter(self.actions,'orientation',Gtk.Orientation.VERTICAL);dialog.add_breakpoint(narrow)

    def available(self,identifier):return self.reports.get(identifier,{}).get('state')=='available'

    def update_all(self):
        d=self.dialog
        if d.busy:return
        resources=[report['available'] for report in self.reports.values() if report['state']=='available']
        if not resources:return
        prompt=Adw.MessageDialog.new(d,tr('Update verified modules?'),'\n'.join(plain(r.description)+' — '+r.source+' · '+r.version for r in resources))
        prompt.add_response('cancel',tr('Cancel'));prompt.add_response('update',tr('Update all'))
        prompt.set_default_response('cancel');prompt.set_close_response('cancel')
        def respond(_,response):
            if response=='update':
                d._phase='idle';self.queue=[r.id for r in resources];self.next_when_ready()
        prompt.connect('response',respond);prompt.present()

    def next_when_ready(self):
        d=self.dialog
        if d.closed or d.owner.closed:self.queue=[];return
        if not self.queue or d.busy or self._next:return
        def next_one():
            self._next=0
            if d.closed or d.owner.closed:self.queue=[];return False
            if d.busy:return False
            if d._phase=='error':self.queue=[];return False
            identifier=self.queue.pop(0)
            resource=d._installed_metadata.get(identifier)
            if resource and self.available(identifier):self.run('update',resource=resource)
            else:self.queue=[]
            return False
        self._next=GLib.idle_add(next_one)

    def failed(self):self.queue=[]

    def version_notes(self,resource):
        """Keep potentially long source prose in the existing metadata scroller."""
        if not resource:return ''
        new=self.reports.get(resource.id,{}).get('available')
        if not new:return ''
        changes=getattr(new,'release_notes','')
        if new.provider_id=='bible-resources':
            from .curated_catalogue import package_record
            entry=package_record(new)
            if isinstance(entry.get('changelog'),str):changes=entry['changelog']
        if not changes:return tr('No version notes supplied by the source.')
        old=self.dialog._installed_metadata.get(resource.id)
        if old and old.version==new.version and getattr(old,'release_notes','')==changes:return ''
        return tr('Catalogue version notes')+' ('+new.version+'):\n'+plain(changes)

    def refresh(self,resource):
        d=self.dialog;installed=resource and resource.id in d._installed_metadata
        self.actions.set_visible(bool(installed));self.notice.set_visible(bool(installed))
        if not installed:return
        old=d._installed_metadata[resource.id];report=self.reports.get(resource.id,dict(state='not-checked'))
        new=report.get('available');state=report['state']
        lines=[tr('Installed version')+': '+(old.version or tr('Unknown'))]
        if new:
            lines.append(tr('Source catalogue version')+': '+(new.version or tr('Unknown')))
            if new.provider_id=='bible-resources':
                from .curated_catalogue import package_record
                entry=package_record(new);lines.append(tr('Download size')+': '+f"{entry['download']['size_bytes']/1024/1024:.1f} MiB")
            else:lines.append(tr('Download size')+': '+tr('Size unknown'))
        lines.append(tr(REASONS[state]));self.notice.set_text('\n'.join(lines))
        self.notice.set_tooltip_text(report.get('error') or None)
        self.update_button.set_visible(state=='available');self.update_button.set_sensitive(not d.busy)
        try:backup=ModuleLifecycle(d.library).rollback_candidate(resource.id)
        except (OSError,ValueError,KeyError,TypeError):backup=None
        self.rollback_button.set_visible(bool(backup));self.rollback_button.set_sensitive(not d.busy)
        self.remove_button.set_sensitive(not d.busy and not old.locked)
        self.remove_button.set_tooltip_text(tr('Encrypted modules cannot be removed safely by this version.') if old.locked else None)

    def check(self):
        d=self.dialog
        if d.busy:return
        identifiers=tuple(d._installed_metadata)
        providers=tuple(BY_ID[key] for key in sorted({d._installed_metadata[i].provider_id for i in identifiers}&SUPPORTED))
        def perform():
            from .library import catalogues
            if providers:
                future=d.session.refresh(catalogues,True,providers)
                if future:future.result()
            if d._cancel.is_set():raise InterruptedError(tr('Download cancelled.'))
            with d.session.lock:
                resources=tuple(r for rows in d.session.providers.values() for r in rows);errors=dict(d.session.errors)
            return checked_modules(d.library,resources,errors)
        def ready(reports):
            self.reports=reports;self.revision+=1;d.selection_changed();d.refresh_rows()
        d.task(tr('Checking for module updates…'),perform,ready,
               success_text=tr('Module check complete.'))

    def confirm(self,operation):
        d=self.dialog;resource=d.selected_resource()
        if not resource or d.busy or resource.id not in d._installed_metadata:return
        installed=d._installed_metadata[resource.id]
        title=tr('Remove resource?') if operation=='remove' else tr('Restore previous version?')
        body=(plain(installed.description)+'\n'+installed.source+'\n'+installed.source_url+'\n\n'+
              tr('Downloaded resource files will be removed. Personal notes, highlights and the saved reading passage will be retained.') if operation=='remove' else
              plain(installed.description)+'\n'+installed.source+'\n\n'+tr('Restore the previous verified package. Personal annotations will be retained.'))
        if operation=='remove' and installed.kind=='bible' and len(d.library.installed('bible'))==1:
            body+='\n'+tr('This is the last installed Bible. You can download it again from Library.')
        prompt=Adw.MessageDialog.new(d,title,body);prompt.add_response('cancel',tr('Cancel'))
        prompt.add_response('confirm',tr('Remove') if operation=='remove' else tr('Restore'))
        prompt.set_response_appearance('confirm',Adw.ResponseAppearance.DESTRUCTIVE if operation=='remove' else Adw.ResponseAppearance.SUGGESTED)
        prompt.set_default_response('cancel');prompt.set_close_response('cancel')
        prompt.connect('response',lambda _,response:self.run(operation,resource=installed) if response=='confirm' else None)
        prompt.present()

    def run(self,operation,*,resource=None):
        d=self.dialog;resource=resource or d.selected_resource()
        if not resource or d.busy or resource.id not in d._installed_metadata:return
        if operation=='update':
            if not self.available(resource.id):return
            resource=self.reports[resource.id]['available']
        lifecycle=ModuleLifecycle(d.library);bridge=ModuleViewChange(d,resource.id)
        def before(identifier):
            if d._cancel.is_set():raise InterruptedError(tr('Download cancelled.'))
            d.begin_installation();bridge.before_switch(identifier)
        def perform():
            if operation=='update':return lifecycle.update(resource,d.report_progress,cancelled=d._cancel.is_set,
                installing=d.begin_installation,before_switch=before)
            if operation=='rollback':return lifecycle.rollback(resource.id,before_switch=before)
            return lifecycle.remove(resource.id,before_switch=before)
        def ready(record):
            self.reports.pop(resource.id,None);self.revision+=1
            d.preparing=True;d.session.reload_installed()
            d._completed_resource=resource.id;d.selection_changed()
            cleanup=record.get('cleanup_error') or '\n'.join(record.get('cleanup_errors',()))
            if cleanup:raise OSError(tr('The resource operation completed, but some stored files could not be cleaned up.')+' '+cleanup)
        caption=tr({'update':'Updating resource…','rollback':'Restoring resource…','remove':'Removing resource…'}[operation])
        success=tr({'update':'Resource updated.','rollback':'Previous version restored.','remove':'Resource removed. Personal annotations were retained.'}[operation])
        d.task(caption,perform,ready,resource=resource,success_text=success,settled=bridge.resume,failed=self.failed)
