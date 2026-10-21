"""Small native highlight list and paint-only tags; never change scripture words."""
from gi.repository import Adw,Gio,GObject,Gtk,Pango
from .highlights import COLORS
from .i18n import tr,LANGUAGE
from .book_names import display_name,normalized
from .notes import parts
from .notes_window import passage_label,message
from .reading_style import PALETTES


def text_changed(buffer):
    buffer._highlight_revision+=1


def paint(view,store,system,ranges,visible,high,palette):
    buffer=view.get_buffer();table=buffer.get_tag_table()
    if not hasattr(buffer,'_highlight_revision'):
        buffer._highlight_revision=0
        buffer.connect('changed',text_changed)
    ranges=tuple(ranges)
    state=(buffer,buffer._highlight_revision,system,ranges,visible,high,palette,
           tuple((reference,store.entries.get((system,reference),{}).get('color'))
                 for reference,_,_ in ranges))
    # Comparison can rebuild from an adjustment notification during GTK layout.
    # Do not invalidate the unchanged primary view while GTK validates it.
    if getattr(view,'_highlight_paint_state',None)==state:return
    for color,(background,label) in COLORS.items():
        tag=table.lookup('highlight-'+color)
        if tag is None:tag=buffer.create_tag('highlight-'+color)
        style=(PALETTES[palette][0] if high else background,
               PALETTES[palette][1] if high else '#202020',
               Pango.Underline.DOUBLE if high else Pango.Underline.NONE)
        if getattr(tag,'_highlight_style',None)!=style:
            tag.props.background,tag.props.foreground,tag.props.underline=style
            tag._highlight_style=style
        buffer.remove_tag(tag,buffer.get_start_iter(),buffer.get_end_iter())
    if visible:
        for reference,start,end in ranges:
            mark=store.entries.get((system,reference))
            if mark and end>start:
                buffer.apply_tag(table.lookup('highlight-'+mark['color']),buffer.get_iter_at_offset(start),buffer.get_iter_at_offset(end))
    view._highlight_paint_state=state


class MarkItem(GObject.Object):
    def __init__(self,mark):super().__init__();self.mark=mark


class HighlightsWindow(Adw.Window):
    def __init__(self,owner):
        super().__init__(transient_for=owner,title=tr('Highlights'),default_width=500,default_height=560)
        self.owner=owner;self.closed=False;self.rows=[];self.choosers=[]
        self.set_destroy_with_parent(True)
        self.connect('close-request',self.closed_request)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        header=Adw.HeaderBar();header.set_title_widget(Adw.WindowTitle(title=tr('Highlights')))
        menu=Gtk.MenuButton(icon_name='open-menu-symbolic',tooltip_text=tr('Highlight actions'));popover=Gtk.Popover()
        actions=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6,margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
        for label,restore in [('Back up highlights',False),('Restore highlights',True)]:
            button=Gtk.Button(label=tr(label));button.connect('clicked',lambda _,r=restore:self.choose_file(r));actions.append(button)
        popover.set_child(actions);menu.set_popover(popover);header.pack_end(menu);box.append(header)
        self.search=Gtk.SearchEntry(placeholder_text=tr('Search highlighted passages'),margin_start=12,margin_end=12)
        self.search.update_property([Gtk.AccessibleProperty.LABEL],[tr('Search highlighted passages')])
        self.search.connect('search-changed',lambda *_:self.refresh());box.append(self.search)
        self.status=Gtk.Label(wrap=True,xalign=0,margin_start=12,margin_end=12);box.append(self.status)
        self.model=Gio.ListStore.new(MarkItem);selection=Gtk.NoSelection(model=self.model)
        factory=Gtk.SignalListItemFactory()
        factory.connect('setup',lambda _,item:item.set_child(Gtk.Label(xalign=0,wrap=True,margin_start=12,margin_end=12,margin_top=10,margin_bottom=10)))
        def bind(_,item):
            mark=item.get_item().mark
            item.get_child().set_text(passage_label(mark['reference'],versification=mark['system'])+' — '+tr(COLORS[mark['color']][1]))
            item.get_child().set_tooltip_text(mark['resource']+' · '+mark['system'])
        factory.connect('bind',bind)
        self.list=Gtk.ListView(model=selection,factory=factory,single_click_activate=True)
        self.list.connect('activate',self.activate)
        scroll=Gtk.ScrolledWindow(vexpand=True);scroll.set_child(self.list);box.append(scroll)
        self.set_content(box);self.refresh()

    def closed_request(self,*_):self.closed=True;return False

    def refresh(self):
        query=normalized(self.search.get_text());self.rows=[]
        for mark in reversed(list(self.owner.highlights.entries.values())):
            code,chapter,verse=parts(mark['reference'])
            name=display_name(code,code,LANGUAGE)
            if query in normalized(f'{name} {chapter}:{verse} {mark["reference"]} {tr(COLORS[mark["color"]][1])}'):
                self.rows.append(mark)
        self.model.splice(0,self.model.get_n_items(),[MarkItem(mark) for mark in self.rows])
        self.status.set_text((tr('Highlights unavailable. The original file is preserved.')+'\n'+self.owner.highlights.error)
                             if self.owner.highlights.error else tr('No highlights yet.') if not self.rows else '')

    def activate(self,_,index):
        if index>=len(self.rows):return
        mark=self.rows[index];tab=self.owner.active_tab
        candidates=list(dict.fromkeys(([tab.state.resource] if tab else [])+[mark['resource']]+self.owner.library.installed('bible')))
        for name in candidates:
            if not name or name not in self.owner.library.installed('bible'):continue
            resource=self.owner.library.resource(name)
            if resource.versification==mark['system'] and self.owner.navigate_selection(name,mark['reference']):
                self.owner.present();self.close();return
        self.status.set_text(tr('No installed translation can open this highlight. The highlight is retained.'))

    def choose_file(self,restore):
        title=tr('Restore highlights') if restore else tr('Back up highlights')
        chooser=Gtk.FileChooserNative.new(title,self,Gtk.FileChooserAction.OPEN if restore else Gtk.FileChooserAction.SAVE,tr('Open') if restore else tr('Save'),tr('Cancel'))
        if not restore:chooser.set_current_name('Bible-highlights.json')
        self.choosers.append(chooser)
        def response(dialog,result):
            if result==Gtk.ResponseType.ACCEPT:
                path=dialog.get_file().get_path()
                def apply():
                    try:
                        if restore:self.owner.highlights.restore(path);self.owner.refresh_highlights();self.refresh()
                        else:self.owner.highlights.backup(path)
                        self.status.set_text(tr('Done'))
                    except (OSError,ValueError,TypeError) as error:self.status.set_text(str(error))
                if restore:message(self,'Restore highlights?','Merge the backup with existing highlights. Notes and translations are unchanged.',apply)
                else:apply()
            dialog.destroy();self.choosers.remove(dialog)
        chooser.connect('response',response);chooser.show()
