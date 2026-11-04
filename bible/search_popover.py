"""Dedicated native Text/Topics entry point over the existing search models."""
from gi.repository import Gdk,GLib,Gtk
from .i18n import tr
from .study_search import StudySearch


class SearchPopover(Gtk.Popover):
    def __init__(self,owner):
        super().__init__()
        self.owner=owner;self.reader=None;self._resource=None;self._layout_stamp=None;self._focus_idle=0
        self.add_css_class('passage-selector')
        self.content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12)
        self.modes=Gtk.Stack(hhomogeneous=False,vhomogeneous=False)
        self.text_search=StudySearch(self,'text');self.topic_search=StudySearch(self,'topics')
        self.modes.add_titled(self.text_search,'text',tr('Text'));self.modes.add_titled(self.topic_search,'topics',tr('Themes'))
        self.mode_switcher=Gtk.Box(halign=Gtk.Align.FILL);self.mode_switcher.add_css_class('linked');self.mode_buttons={}
        first=None
        for name,label in [('text','Text'),('topics','Themes')]:
            button=Gtk.ToggleButton(label=tr(label),hexpand=True)
            if first:button.set_group(first)
            else:first=button
            button.connect('toggled',lambda b,n=name:self.modes.set_visible_child_name(n) if b.get_active() else None)
            self.mode_switcher.append(button);self.mode_buttons[name]=button
        first.set_active(True)
        self.content.append(self.mode_switcher);self.content.append(self.modes)
        self.scroll=Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,propagate_natural_height=True)
        self.scroll.set_child(self.content);self.set_child(self.scroll)
        self.modes.connect('notify::visible-child-name',self.mode_changed)
        self.connect('notify::visible',self.visibility_changed)
        keys=Gtk.EventControllerKey();keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect('key-pressed',self.preview_key_pressed);self.add_controller(keys)

    def selected_resource(self):return self._resource

    def sync(self):
        tab=self.owner.active_tab if hasattr(self.owner,'view') else None
        self.reader=tab.reader if tab else None;self._resource=tab.state.resource if tab else None
        self.active_panel().refresh()

    def active_panel(self):
        return self.topic_search if self.modes.get_visible_child_name()=='topics' else self.text_search

    def mode_changed(self,*_):
        mode=self.modes.get_visible_child_name()
        for name,panel in [('text',self.text_search),('topics',self.topic_search)]:
            if name!=mode:panel.pause()
        self.mode_buttons[mode].set_active(True)
        self.owner.reference_preview.dismiss();self._layout_stamp=None
        self.sync();self.adapt()
        if self.get_visible():self.focus_query()

    def focus_query(self):
        if self._focus_idle:GLib.source_remove(self._focus_idle)
        def focus():
            self._focus_idle=0
            if self.get_visible() and not self.owner.closed:self.active_panel().entry.grab_focus()
            return False
        self._focus_idle=GLib.idle_add(focus)

    def visibility_changed(self,*_):
        if self.get_visible():
            for other in self.owner._reading_popovers:
                if other is not self and not self.is_ancestor(other) and other.get_visible():other.popdown()
            self.sync();self.adapt();self.focus_query()
        else:
            if self._focus_idle:GLib.source_remove(self._focus_idle);self._focus_idle=0
            self.text_search.pause();self.topic_search.pause()
            anchor=self.get_parent()
            if anchor and anchor.get_mapped():anchor.grab_focus()

    def adapt(self):
        if not self.get_visible():return
        size=(self.owner.get_width(),self.owner.get_height(),self.modes.get_visible_child_name())
        if size==self._layout_stamp:return
        self._layout_stamp=size;topics=size[2]=='topics'
        self.content.set_size_request(min(680,max(240,size[0]-64)),-1)
        available=min(540,max(160,size[1]-140))
        self.scroll.set_min_content_height(-1);self.scroll.set_max_content_height(available)
        self.scroll.set_min_content_height(available if topics else -1)
        self.scroll.set_size_request(-1,available if topics else -1)
        self.scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.NEVER if topics else Gtk.PolicyType.AUTOMATIC)
        self.modes.set_vexpand(topics)
        from .popover_dismissal import fit_reader_popover
        fit_reader_popover(self,self.owner)

    def preview_key_pressed(self,controller,key,code,state):
        if key!=Gdk.KEY_Escape:return False
        event=controller.get_current_event()
        if event and event.get_surface() not in (self.get_surface(),self.owner.get_surface()):return False
        if self.owner.reference_preview.popover:self.owner.reference_preview.dismiss();return True
        self.popdown();return True

    def close(self):
        if self._focus_idle:GLib.source_remove(self._focus_idle);self._focus_idle=0
        self.text_search.close();self.topic_search.close()
