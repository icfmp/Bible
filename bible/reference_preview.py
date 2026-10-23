"""One native, non-navigating preview shared by study links and note citations."""
from gi.repository import Gtk,Pango,Adw
from .i18n import tr
from .notes_window import passage_label
from .reference_targets import local_excerpt
from .reference_resolution import VersificationMismatch
from .reading_style import apply_direction


def passage_title(start,end=None,system=None):
    end=end or start
    if start.rsplit('.',1)[0]==end.rsplit('.',1)[0]:return passage_label(start,end,system)
    return passage_label(start,versification=system)+' – '+passage_label(end,versification=system)


class ReferencePreview:
    def __init__(self,owner):
        self.owner=owner;self.popover=None;self.target=None

    def detach(self,popover):
        root=getattr(popover,'_reference_root',None)
        if root:
            entries=root._reading_popovers
            if popover in entries:entries.remove(popover)
            handler=getattr(popover,'_reference_unrealize',0)
            if handler:root.disconnect(handler)
            popover._reference_root=None
        anchor=getattr(popover,'_reference_anchor',None)
        handler=getattr(popover,'_reference_anchor_unmap',0)
        if anchor and handler:anchor.disconnect(handler)
        popover._reference_anchor=None;popover._reference_anchor_unmap=0
        dialog=getattr(popover,'_reference_dialog',None)
        if dialog:
            handler=getattr(popover,'_reference_dialog_handler',0)
            if handler:dialog.disconnect(handler)
            dialog.set_can_close(popover._reference_dialog_can_close)
            popover._reference_dialog=None;popover._reference_dialog_handler=0
        if popover.get_parent():popover.unparent()
        if self.popover is popover:self.popover=None;self.target=None

    def dismiss(self):
        popover=self.popover
        if popover:
            popover.popdown();self.detach(popover)

    def show(self,anchor,resource,reader,start,end=None,*,source_system='openbible',provenance='',navigation_guard=None,pointing_to=None):
        self.dismiss()
        root=anchor.get_root()
        if not isinstance(root,Gtk.Window):return
        popover=Gtk.Popover(autohide=False)
        self.popover=popover
        if not hasattr(root,'_reading_popovers'):
            from .popover_dismissal import install
            root._reading_popovers=[];root._reference_dismissal=install(root,root._reading_popovers)
        root._reading_popovers.append(popover)
        popover._reference_root=root
        popover._reference_unrealize=root.connect('unrealize',lambda *_:self.dismiss())
        dialog=anchor.get_ancestor(Adw.Dialog)
        if dialog:
            # Adwaita's modal Escape action runs before window key controllers.
            # Let the first close attempt dismiss only this nested preview.
            popover._reference_dialog=dialog
            popover._reference_dialog_can_close=dialog.get_can_close()
            popover._reference_dialog_handler=dialog.connect('close-attempt',lambda *_:self.dismiss())
            dialog.set_can_close(False)
        popover._reference_anchor=anchor
        popover._reference_anchor_unmap=anchor.connect('unmap',lambda *_:self.dismiss())
        popover.connect('closed',lambda *_:self.detach(popover))
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,
                    margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
        header=Gtk.Box(spacing=6)
        title=Gtk.Label(label=tr('Passage preview'),xalign=0,hexpand=True,wrap=True)
        title.add_css_class('heading');header.append(title)
        close=Gtk.Button(icon_name='window-close-symbolic',tooltip_text=tr('Close'))
        close.add_css_class('flat');close.connect('clicked',lambda *_:self.dismiss());header.append(close)
        box.append(header)
        version=Gtk.Label(label=resource or tr('No active Bible translation'),xalign=0,wrap=True,max_width_chars=36)
        version.add_css_class('dim-label');box.append(version)
        body=Gtk.TextView(editable=False,cursor_visible=False,wrap_mode=Gtk.WrapMode.WORD_CHAR,
                          left_margin=4,right_margin=4,top_margin=4,bottom_margin=4)
        body.update_property([Gtk.AccessibleProperty.LABEL],[tr('Local passage text')])
        scroll=Gtk.ScrolledWindow(min_content_width=240,min_content_height=160,max_content_height=300,
                                  propagate_natural_height=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_child(body);box.append(scroll)
        status=Gtk.Label(xalign=0,wrap=True,max_width_chars=36);status.add_css_class('dim-label');box.append(status)
        actions=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        here=Gtk.Button(label=tr('Open in current tab'));new=Gtk.Button(label=tr('Open in new tab'))
        actions.append(here);actions.append(new);box.append(actions)
        try:
            if reader is None:raise ValueError('No active Bible translation')
            excerpt=local_excerpt(reader,start,end,source_system=source_system)
            title.set_text(passage_title(excerpt.start,excerpt.end,reader.versification))
            body.get_buffer().set_text(excerpt.text);apply_direction(body,reader)
            status.set_text(tr('Beginning of passage; open it to read more.') if excerpt.more else tr('Text from your installed translation.'))
            target=(resource,excerpt.start)
            self.target=target
        except (ValueError,OSError) as error:
            body.get_buffer().set_text('');scroll.set_visible(False)
            title.set_text(passage_title(start,end,source_system if source_system!='openbible' else None))
            status.set_text(tr('Open an installed Bible translation to preview this reference.') if reader is None else
                            tr('No verified alignment for this passage.') if isinstance(error,VersificationMismatch)
                            else tr('This passage is unavailable in the selected translation.'))
            status.set_tooltip_text(str(error));here.set_sensitive(False);new.set_sensitive(False);target=None
        def open_target(new_tab):
            self.dismiss()
            if not target or self.owner.closed:return
            name,reference=target
            if name not in self.owner.library.installed('bible'):
                self.owner.report_session_error(tr('Translation unavailable.'),ValueError(name));return
            def navigate():
                tab=self.owner.new_tab() if new_tab else self.owner.active_tab
                if tab:tab.navigate(name,reference)
                self.owner.main_pages.set_visible_child_name('reading')
            if navigation_guard:navigation_guard(navigate)
            elif self.owner.main_pages.get_visible_child_name()=='notes':self.owner.notes_space.guard(navigate)
            else:navigate()
        here.connect('clicked',lambda *_:open_target(False));new.connect('clicked',lambda *_:open_target(True))
        if provenance:
            attribution=Gtk.Label(label=provenance,xalign=0,wrap=True,max_width_chars=36)
            attribution.add_css_class('caption');attribution.set_selectable(True);box.append(attribution)
        popover.set_child(box);popover.set_parent(anchor)
        if pointing_to is not None:popover.set_pointing_to(pointing_to)
        popover.popup()
        self.body,self.status,self.open_here,self.open_new=body,status,here,new
        return popover
