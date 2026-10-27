"""Current-passage OpenBible suggestions, with stale-result and focus guards."""
from concurrent.futures import ThreadPoolExecutor
from gi.repository import Gtk,GLib,Gio,GObject,Pango
from .i18n import tr
from .reference_data import ReferenceData,SOURCE_URL,LICENSE_URL
from .reference_targets import source_references,local_excerpt,local_target_ranges
from .reference_preview import passage_title
from .reference_resolution import VersificationMismatch


class ReferenceItem(GObject.Object):
    def __init__(self,relationship,context,generation):
        super().__init__();self.relationship=relationship;self.context=context;self.generation=generation


class StudyReferences(Gtk.Box):
    def __init__(self,owner):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=8,
                         margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
        self.owner=owner;self.data=ReferenceData(owner.library.root.parent/'study-data')
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='bible-references')
        self.generation=0;self.stamp=None;self.context=None;self.rows=[];self.pending=False
        self.all_results=False;self.chapter_cache={};self.row_cache={}
        context=Gtk.Label(label=tr('Passage studied'),xalign=0);context.add_css_class('caption');self.append(context)
        self.heading=Gtk.Label(xalign=0,wrap=True);self.heading.add_css_class('heading');self.append(self.heading)
        self.status=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR)
        self.append(self.status)
        self.download=Gtk.Button(label=tr('Download reference data'))
        self.download.connect('clicked',lambda *_:owner.open_library('study'));self.append(self.download)
        self.model=Gio.ListStore.new(ReferenceItem)
        self.return_results=Gtk.Button(label=tr('Back to first references'),halign=Gtk.Align.START,visible=False)
        self.return_results.add_css_class('flat');self.return_results.connect('clicked',self.show_initial);self.append(self.return_results)
        # A footer item shares the virtualized list's normal content flow.
        # The data model remains only actual relationships, with unchanged ordering.
        footer_model=Gio.ListStore.new(ReferenceItem);footer_model.append(ReferenceItem(None,None,None))
        sections=Gio.ListStore.new(Gio.ListModel);sections.append(self.model);sections.append(footer_model)
        combined=Gtk.FlattenListModel(model=sections)
        factory=Gtk.SignalListItemFactory();factory.connect('bind',self.bind)
        factory.connect('unbind',lambda _,item:item.set_child(None))
        self.list=Gtk.ListView(model=Gtk.NoSelection(model=combined),factory=factory,vexpand=True,show_separators=True)
        self.list.add_css_class('navigation-sidebar')
        scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_child(self.list);self.append(scroll);self.scroll=scroll
        self.footer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,margin_top=8,margin_bottom=12,margin_start=8,margin_end=8)
        self.view_all=Gtk.Button(label=tr('View all'),halign=Gtk.Align.START,visible=False);self.view_all.connect('clicked',self.show_all);self.footer.append(self.view_all)
        credit=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1)
        credit.set_markup('<a href="'+SOURCE_URL+'">OpenBible.info</a> · <a href="'+LICENSE_URL+'">CC BY 4.0</a>\n'+
                          GLib.markup_escape_text(tr('Community-ranked suggestions; explore the context.')))
        credit.add_css_class('caption');credit.set_tooltip_text(SOURCE_URL+'\n'+LICENSE_URL);self.footer.append(credit)
        self.teaser=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        header=Gtk.Box(spacing=6)
        title=Gtk.Label(label=tr('Cross-references'),xalign=0,hexpand=True);title.add_css_class('heading');header.append(title)
        see_all=Gtk.Button(label=tr('View all'));see_all.add_css_class('flat')
        see_all.connect('clicked',lambda *_:owner.study.tools.set_visible_child_name('references'));header.append(see_all)
        self.teaser.append(header)
        self.teaser_rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);self.teaser.append(self.teaser_rows)
        self.teaser_status=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR)
        self.teaser_status.add_css_class('dim-label');self.teaser.append(self.teaser_status)
        self.teaser_download=Gtk.Button(label=tr('Download reference data'))
        self.teaser_download.connect('clicked',lambda *_:owner.open_library('study'));self.teaser.append(self.teaser_download)
        self.message(tr('Open a Bible passage to see its references.'))

    def close(self):
        self.generation+=1;self.executor.shutdown(wait=False,cancel_futures=True)

    def invalidate(self):
        self.stamp=None;self.refresh()

    def message(self,text,download=False):
        self.status.set_tooltip_text(None)
        self.status.set_text(text);self.status.set_visible(bool(text))
        self.teaser_status.set_text(text);self.teaser_status.set_visible(bool(text))
        self.download.set_visible(download);self.teaser_download.set_visible(download)

    def clear_rows(self):
        self.owner.reference_preview.dismiss()
        self.model.remove_all()
        while self.teaser_rows.get_first_child():self.teaser_rows.remove(self.teaser_rows.get_first_child())
        self.view_all.set_visible(False)
        self.return_results.set_visible(False)

    def refresh(self,force=False):
        if self.owner.closed or self.owner.study.tool not in ('notes','references'):return
        tab=self.owner.active_tab
        if not tab or not tab.reader:
            self.generation+=1;self.context=None;self.stamp=None;self.pending=False;self.clear_rows()
            self.rows=[];self.row_cache={};self.chapter_cache={};self.all_results=False
            self.heading.set_text(tr('References'))
            self.message(tr('Open a Bible passage to see its references.'));return
        start,end=tab.selected_passage();reader=tab.reader
        stamp=(id(tab),id(reader),tab.state.resource,start,end,self.data.revision)
        if not force and stamp==self.stamp:return
        self.stamp=stamp;self.generation+=1;generation=self.generation
        self.context=(tab.state.resource,reader,start,end)
        self.rows=[];self.chapter_cache={};self.row_cache={};self.all_results=False;self.pending=False
        self.clear_rows();self.heading.set_text(passage_title(start,end,reader.versification))
        if self.data.revision is None:
            self.message(tr('Download OpenBible reference data once to use it offline.'),download=True);return
        try:origins=source_references(reader,start,end)
        except ValueError as error:
            self.message(tr('No verified alignment for this passage.'));self.status.set_tooltip_text(str(error));return
        self.pending=True;self.message(tr('Loading references…'))
        revision=self.data.revision
        future=self.executor.submit(self.data.query,origins)
        def complete():
            if self.owner.closed or generation!=self.generation:return False
            self.pending=False
            if revision!=self.data.revision:self.invalidate();return False
            try:self.rows=future.result()
            except Exception as error:
                self.message(tr('Reference data is unavailable. Download it again from Library.'),download=True)
                self.status.set_tooltip_text(str(error));return False
            self.message(tr('No cross-references for this passage.') if not self.rows else '')
            self.populate();return False
        future.add_done_callback(lambda _:GLib.idle_add(complete))

    def bind(self,_,item):
        if item.get_item().relationship is None:item.set_child(self.footer)
        else:
            button=self.button();self.fill(button,item.get_item());item.set_child(button)

    def button(self):
        button=Gtk.Button();button.add_css_class('flat')
        content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,margin_start=4,margin_end=4,margin_top=6,margin_bottom=6)
        title=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1)
        title.add_css_class('heading');title.add_css_class('accent');title.add_css_class('study-content');content.append(title)
        text=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,ellipsize=Pango.EllipsizeMode.END,lines=3,width_chars=1)
        text.add_css_class('reference-excerpt');text.add_css_class('study-content')
        content.append(text)
        button.set_child(content);button._reference_labels=(title,text)
        button.connect('clicked',self.preview)
        return button

    def fill(self,button,item):
        button._reference_item=item
        row=item.relationship;resource,reader,_,_=item.context;title,text=button._reference_labels
        text.set_direction(Gtk.TextDirection.RTL if reader.rtl else Gtk.TextDirection.LTR)
        text.set_xalign(1 if reader.rtl else 0)
        key=(row.start,row.end)
        if key not in self.row_cache:
            caption=passage_title(row.start,row.end)
            try:
                targets=local_target_ranges(reader,row.start,row.end)
                caption='; '.join(passage_title(first,last,reader.versification) for first,last in targets)
                excerpt=local_excerpt(reader,row.start,row.end,chapter_cache=self.chapter_cache)
                result=(caption,' '.join(excerpt.text.split())+(' …' if excerpt.more else ''))
            except (ValueError,OSError) as error:
                result=(caption,tr('No verified alignment for this passage.') if isinstance(error,VersificationMismatch)
                        else tr('This passage is unavailable in the selected translation.'))
            self.row_cache[key]=result
        caption,body=self.row_cache[key];title.set_text(caption);text.set_text(body)
        button.set_tooltip_text(tr('OpenBible target: {reference}').format(reference=passage_title(row.start,row.end))+'\n'+
                               tr('Related to {count} selected verses.').format(count=row.source_count))

    def preview(self,button):
        item=button._reference_item
        if item.generation!=self.generation:return
        row=item.relationship;resource,reader,_,_=item.context
        self.owner.reference_preview.show(button,resource,reader,row.start,row.end,
            provenance='OpenBible.info · CC BY 4.0\n'+SOURCE_URL)

    def populate(self):
        items=[ReferenceItem(row,self.context,self.generation) for row in (self.rows if self.all_results else self.rows[:5])]
        self.model.splice(0,self.model.get_n_items(),items)
        self.view_all.set_visible(not self.all_results and len(self.rows)>5)
        self.view_all.set_label(tr('See all {count} references').format(count=len(self.rows)))
        self.return_results.set_visible(self.all_results and len(self.rows)>5)
        while self.teaser_rows.get_first_child():self.teaser_rows.remove(self.teaser_rows.get_first_child())
        for item in items[:3]:
            button=self.button();self.fill(button,item);self.teaser_rows.append(button)

    def show_all(self,*_):
        self.all_results=True;self.populate()

    def show_initial(self,*_):
        self.all_results=False;self.populate();self.scroll.get_vadjustment().set_value(0)
