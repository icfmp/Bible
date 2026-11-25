"""Library actions over the shared provider, installer and module lifecycle."""
from gi.repository import Adw,Gtk
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
            try:
                import os
                if library.root.stat().st_uid!=os.getuid() or not os.access(library.root,os.W_OK):
                    raise ValueError('This library is externally managed or read-only')
                lifecycle.owned(identifier,unchanged=True)
            except (OSError,ValueError,TypeError) as failure:state='local-unverified';error=str(failure)
        reports[identifier]=dict(state=state,available=new,installed=old,error=error)
    return reports


class ModuleManagement:
    def __init__(self,dialog,detail,primary=None):
        self.dialog=dialog;self.reports={};self.revision=0
        dialog.updates.subscribe(self.discovery_changed)
        self.notice=Gtk.Label(xalign=0,wrap=True,selectable=True,visible=False)
        status_parent=dialog.installed_state.get_parent()
        status_parent.insert_child_after(self.notice,dialog.installed_state)
        # Checking refreshes all installed providers. Keep its single global
        # entry in Library actions, rather than an edition-looking text button.
        self.actions=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,visible=False)
        self.update_button=Gtk.Button(label=tr('Update'));self.update_button.connect('clicked',lambda *_:self.run('update'))
        self.rollback_button=Gtk.Button(label=tr('Restore previous version'));self.rollback_button.connect('clicked',lambda *_:self.confirm('rollback'))
        self.remove_button=Gtk.Button(icon_name='user-trash-symbolic',tooltip_text=tr('Remove'))
        self.remove_button.add_css_class('flat')
        self.remove_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Remove')])
        self.remove_button.connect('clicked',lambda *_:self.confirm('remove'))
        if primary is None:self.actions.append(self.update_button)
        else:primary.append(self.update_button)
        self.actions.append(self.rollback_button)
        self.remove_row=Adw.ActionRow(title=tr('Remove'),subtitle=tr('Personal notes and highlights are retained when removing a resource.'),use_markup=False)
        self.remove_row.set_subtitle_lines(0);self.remove_row.add_suffix(self.remove_button)
        self.remove_row.set_activatable_widget(self.remove_button)
        group=Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE);group.add_css_class('boxed-list');group.append(self.remove_row)
        self.actions.append(group)
        detail.append(self.actions)
        narrow=Adw.Breakpoint.new(Adw.BreakpointCondition.parse('max-width: 440px'))
        narrow.add_setter(self.actions,'orientation',Gtk.Orientation.VERTICAL);dialog.add_breakpoint(narrow)

    def discovery_changed(self):
        self.reports=self.dialog.updates.reports
        self.revision+=1
        if hasattr(self,'actions') and not self.dialog.closed:
            self.dialog.selection_changed();self.dialog.refresh_rows()
            manager=self.dialog.updates
            self.dialog.refresh_status.set_text(tr('Checking for module updates…') if manager.checking else
                tr('The source check failed. Saved metadata is not proof that this module is up to date.') if manager.state in ('offline','failed') else
                tr('Module check complete.') if manager.state=='checked' else '')
            self.dialog.refresh_status.set_tooltip_text(manager.error or None)

    def available(self,identifier):return self.reports.get(identifier,{}).get('state')=='available'

    def update_all(self):
        d=self.dialog
        if d.busy:return
        resources=[report['available'] for report in self.reports.values() if report['state']=='available']
        if not resources:return
        prompt=Adw.MessageDialog.new(d,tr('Update verified modules?'),'\n'.join(plain(r.description)+' — '+r.source+' · '+(r.revision if r.kind=='study' else r.version) for r in resources))
        prompt.add_response('cancel',tr('Cancel'));prompt.add_response('update',tr('Update all'))
        prompt.set_default_response('cancel');prompt.set_close_response('cancel')
        def respond(_,response):
            if response=='update':
                for resource in resources:d.queue_request(resource,operation='install' if resource.kind=='study' else 'update')
        prompt.connect('response',respond);prompt.present()

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
        self.update_button.set_visible(False)
        self.remove_button.set_visible(False)
        if not installed:return
        old=d._installed_metadata[resource.id];report=self.reports.get(resource.id,dict(state='not-checked'))
        new=report.get('available');state=report['state']
        lines=[]
        if new:
            if new.version!=old.version:lines.append(tr('Source catalogue version')+': '+(new.version or tr('Unknown')))
            if new.provider_id=='bible-resources':
                from .curated_catalogue import package_record
                entry=package_record(new);lines.append(tr('Download size')+': '+f"{entry['download']['size_bytes']/1024/1024:.1f} MiB")
            else:lines.append(tr('Download size')+': '+tr('Size unknown'))
        if state!='not-checked':lines.append(tr(REASONS[state]))
        self.notice.set_text('\n'.join(lines));self.notice.set_visible(bool(lines))
        self.notice.set_tooltip_text(report.get('error') or None)
        queued=d.downloads.find(resource.id)
        self.update_button.set_visible(state=='available');self.update_button.set_sensitive(not queued or queued.state=='failed')
        try:backup=ModuleLifecycle(d.library).rollback_candidate(resource.id)
        except (OSError,ValueError,KeyError,TypeError):backup=None
        pending=any(r.state in ('active','queued') for r in d.downloads.requests)
        self.rollback_button.set_visible(bool(backup));self.rollback_button.set_sensitive(not d.busy and not pending)
        # SUPPORTED gates verified update offers, not removal. The shared
        # lifecycle independently checks private ownership before deleting.
        removable=not old.locked
        self.remove_button.set_visible(removable)
        self.remove_row.set_visible(removable)
        self.remove_button.set_sensitive(removable and not d.busy and not pending)
        self.remove_button.set_tooltip_text(None)

    def check(self):
        if not self.dialog.busy:self.dialog.updates.check(force=True)

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

    def run(self,operation,*,resource=None,queued=False):
        d=self.dialog;resource=resource or d.selected_resource()
        if not resource or resource.id not in d._installed_metadata:return
        if operation=='update' and not queued:
            if not self.available(resource.id):return
            resource=self.reports[resource.id]['available']
            d.queue_request(resource,operation='update');return
        if d._transfer_busy or operation!='update' and (d.busy or any(r.state in ('active','queued') for r in d.downloads.requests)):return
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
        d.task(caption,perform,ready,resource=resource,success_text=success,settled=bridge.resume)
