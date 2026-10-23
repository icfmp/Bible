"""Topics and literal text in the existing passage selector, with local previews."""
from concurrent.futures import ThreadPoolExecutor
from gi.repository import Gtk,GLib,Gio,GObject,Pango
from .i18n import tr
from .topic_vocabulary import VOCABULARY,suggestions,title
from .topic_data import TopicData,SOURCE_URL,LICENSE_URL
from .reference_data import Relationship
from .reference_targets import local_excerpt
from .reference_preview import passage_title
from .reference_resolution import VersificationMismatch


class SearchItem(GObject.Object):
    def __init__(self,value):super().__init__();self.value=value


class StudySearch(Gtk.Box):
    def __init__(self,navigation,mode):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.navigation=navigation;self.owner=navigation.owner;self.mode=mode
        self.data=TopicData(self.owner.library.root.parent/'study-data')
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='bible-search')
        self.generation=0;self.pending=False;self.context=None;self.topic=None;self.rows=[];self.future=None
        self.entry=Gtk.SearchEntry(placeholder_text=tr('Search topics' if mode=='topics' else 'Exact phrase in this translation'))
        self.entry.update_property([Gtk.AccessibleProperty.LABEL],[tr('Search topics' if mode=='topics' else 'Exact phrase in this translation')])
        self.entry.connect('search-changed',self.changed);self.append(self.entry)
        self.submit=Gtk.Button(label=tr('Search'));self.submit.connect('clicked',self.run_text)
        self.entry.connect('activate',self.run_text if mode=='text' else self.activate_first)
        self.submit.set_visible(mode=='text');self.append(self.submit)
        self.explanation=Gtk.Label(xalign=0,wrap=True,max_width_chars=55)
        self.explanation.add_css_class('caption');self.append(self.explanation)
        self.status=Gtk.Label(xalign=0,wrap=True,max_width_chars=55);self.append(self.status)
        self.download=Gtk.Button(label=tr('Download topic data'));self.download.connect('clicked',self.open_library);self.append(self.download)
        self.topic_model=Gio.ListStore.new(SearchItem)
        topic_factory=Gtk.SignalListItemFactory();topic_factory.connect('setup',self.topic_setup);topic_factory.connect('bind',self.topic_bind)
        self.topics=Gtk.ListView(model=Gtk.NoSelection(model=self.topic_model),factory=topic_factory)
        self.topic_scroll=Gtk.ScrolledWindow(min_content_height=80,max_content_height=160,propagate_natural_height=True,
                                            hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.topic_scroll.set_child(self.topics);self.topic_scroll.set_visible(mode=='topics');self.append(self.topic_scroll)
        self.heading=Gtk.Label(xalign=0,wrap=True);self.heading.add_css_class('heading');self.append(self.heading)
        self.model=Gio.ListStore.new(SearchItem)
        factory=Gtk.SignalListItemFactory();factory.connect('setup',self.result_setup);factory.connect('bind',self.result_bind)
        self.results=Gtk.ListView(model=Gtk.NoSelection(model=self.model),factory=factory)
        scroll=Gtk.ScrolledWindow(min_content_height=100,max_content_height=280,propagate_natural_height=True,
                                   hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_child(self.results);self.append(scroll)
        self.credit=Gtk.Label(label=tr('OpenBible.info · CC BY 4.0. Community suggestions; explore the context.'),xalign=0,wrap=True)
        self.credit.add_css_class('caption');self.credit.set_visible(mode=='topics');self.credit.set_tooltip_text(SOURCE_URL+'\n'+LICENSE_URL);self.append(self.credit)
        self.refresh()

    def close(self):self.generation+=1;self.executor.shutdown(wait=False,cancel_futures=True)

    def invalidate(self):
        if self.future:self.future.cancel();self.future=None
        self.generation+=1;self.pending=False;self.model.remove_all();self.rows=[];self.row_cache={};self.chapter_cache={}
        if hasattr(self.owner,'reference_preview'):self.owner.reference_preview.dismiss()
        self.heading.set_text('');self.status.set_tooltip_text(None)

    def refresh(self):
        self.invalidate()
        self.explanation.set_text(tr('Partial curated vocabulary: {count} topics in French and English. Suggestions are not doctrinal conclusions.').format(count=len(VOCABULARY)) if self.mode=='topics' else
                                  tr('Literal phrase, ignoring case, in the selected installed translation.'))
        self.download.set_visible(self.mode=='topics' and self.data.revision is None)
        if self.mode=='topics':self.changed()
        else:self.status.set_text(tr('Enter a phrase and press Enter.'))

    def changed(self,*_):
        self.invalidate()
        if self.mode=='text':self.status.set_text(tr('Enter a phrase and press Enter.'));return
        entries=suggestions(self.entry.get_text())
        self.topic_model.splice(0,self.topic_model.get_n_items(),[SearchItem(e) for e in entries])
        self.status.set_text(tr('Download topic data once to explore it offline.') if self.data.revision is None else
                             tr('Choose a topic.') if entries else tr('No topic in the supported vocabulary. Try a shorter word.'))
        self.download.set_visible(self.data.revision is None)

    def open_library(self,*_):
        from .study_resources import TOPIC_RESOURCE_ID
        self.navigation.popdown();library=self.owner.open_library('study')
        index=next(i for i,r in enumerate(library.filtered_resources) if r.id==TOPIC_RESOURCE_ID)
        library.open_details(None,index)

    def topic_setup(self,_,item):
        button=Gtk.Button();button.add_css_class('flat')
        label=Gtk.Label(xalign=0,wrap=True,width_chars=1);button.set_child(label)
        button.connect('clicked',lambda b:self.choose(b._topic));item.set_child(button)

    def topic_bind(self,_,item):
        button=item.get_child();button._topic=item.get_item().value;button.get_child().set_text(title(button._topic))
        button.set_tooltip_text('OpenBible.info · '+button._topic[0])

    def activate_first(self,*_):
        if self.topic_model.get_n_items():self.choose(self.topic_model.get_item(0).value)

    def capture_context(self):
        reader=self.navigation.reader;resource=self.navigation.selected_resource()
        if not reader or resource not in self.owner.library.installed('bible'):
            self.status.set_text(tr('Choose an installed translation.'));return False
        self.context=(resource,reader);return True

    def launch(self,operation,caption,source_system):
        self.invalidate()
        if not self.capture_context():return
        self.source_system=source_system;self.pending=True;self.status.set_text(tr('Searching…'));self.heading.set_text(caption)
        generation=self.generation;future=self.executor.submit(operation);self.future=future
        def complete():
            if self.owner.closed or generation!=self.generation:return False
            self.pending=False
            try:
                self.rows,total=future.result()
                self.model.splice(0,self.model.get_n_items(),[SearchItem((row,generation)) for row in self.rows])
                self.status.set_text(tr('Showing {count} of {total} results.').format(count=len(self.rows),total=total) if self.rows else tr('No matching passages.'))
            except Exception as error:
                self.status.set_text(tr('Search unavailable. Check the installed resource and try again.'));self.status.set_tooltip_text(str(error))
                self.download.set_visible(self.mode=='topics')
            return False
        future.add_done_callback(lambda _:GLib.idle_add(complete))

    def choose(self,entry):
        self.topic=entry
        if self.data.revision is None:self.status.set_text(tr('Download topic data once to explore it offline.'));return
        def operation():
            rows=self.data.query(entry[0]);return rows,len(rows)
        self.launch(operation,title(entry),'openbible')

    def run_text(self,*_):
        if self.mode!='text':return
        if not self.capture_context():return
        resource,reader=self.context;query=self.entry.get_text().strip()
        if not query or len(query)>200 or any(ord(c)<32 for c in query):
            self.invalidate();self.status.set_text(tr('Enter a phrase of 1–200 characters.'));return
        from .text_search import search
        root=self.owner.library.root
        def operation():
            value=search(root,resource,query)
            return [Relationship(ref,ref,0,1) for ref in value['references']],value['total']
        self.launch(operation,query,reader.versification)

    def result_setup(self,_,item):
        button=Gtk.Button();button.add_css_class('flat')
        content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        for _ in range(3):content.append(Gtk.Label(xalign=0,wrap=True,width_chars=1,wrap_mode=Pango.WrapMode.WORD_CHAR))
        heading=content.get_first_child();heading.add_css_class('heading');heading.add_css_class('accent')
        excerpt=heading.get_next_sibling();excerpt.set_lines(3);excerpt.set_ellipsize(Pango.EllipsizeMode.END)
        score=excerpt.get_next_sibling();score.add_css_class('caption')
        button.set_child(content);button.connect('clicked',self.preview);item.set_child(button)

    def result_bind(self,_,item):
        row,generation=item.get_item().value;button=item.get_child();button._result=(row,generation)
        resource,reader=self.context;key=(row.start,row.end)
        if key not in self.row_cache:
            try:
                excerpt=local_excerpt(reader,row.start,row.end,source_system=self.source_system,limit=1,chapter_cache=self.chapter_cache)
                result=(passage_title(excerpt.start,excerpt.end,reader.versification),excerpt.text)
            except (ValueError,OSError) as error:
                result=(passage_title(row.start,row.end),tr('No verified alignment for this passage.') if isinstance(error,VersificationMismatch) else
                        tr('This passage is unavailable in the selected translation.'))
            self.row_cache[key]=result
        caption,text=self.row_cache[key];heading=button.get_child().get_first_child();heading.set_text(caption)
        excerpt=heading.get_next_sibling();excerpt.set_text(text)
        excerpt.set_direction(Gtk.TextDirection.RTL if reader.rtl else Gtk.TextDirection.LTR);excerpt.set_xalign(1 if reader.rtl else 0)
        score=excerpt.get_next_sibling();score.set_visible(self.mode=='topics')
        score.set_text(tr('Source quality score: {score}').format(score=row.score))

    def preview(self,button):
        row,generation=button._result
        if generation!=self.generation:return
        resource,reader=self.context
        def navigate(action):
            self.navigation.popdown()
            if self.owner.main_pages.get_visible_child_name()=='notes':self.owner.notes_space.guard(action)
            else:action()
        self.owner.reference_preview.show(button,resource,reader,row.start,row.end,source_system=self.source_system,
            provenance='OpenBible.info · CC BY 4.0\n'+SOURCE_URL+'\n'+self.topic[0] if self.mode=='topics' else '',navigation_guard=navigate)
