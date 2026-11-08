"""Topics and literal text in the dedicated search popover, with local previews."""
from .metadata_workers import MetadataExecutor
from gi.repository import Adw,Gtk,GLib,Gio,GObject,Pango
from .i18n import tr,LANGUAGE
from .topic_vocabulary import TopicVocabulary,suggestions,title
from .topic_data import TopicData,SOURCE_URL,LICENSE_URL,TRANSFORMATIONS
from .reference_data import Relationship
from .reference_targets import local_excerpt
from .reference_preview import passage_title
from .reference_resolution import VersificationMismatch
from .passage_card import passage_card


class SearchItem(GObject.Object):
    def __init__(self,value):super().__init__();self.value=value


class StudySearch(Gtk.Box):
    def __init__(self,navigation,mode):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.navigation=navigation;self.owner=navigation.owner;self.mode=mode
        self.data=TopicData(self.owner.library.root.parent/'study-data')
        self.vocabulary=TopicVocabulary(self.data.root);self._vocabulary_entries=()
        self.executor=MetadataExecutor(max_workers=1,thread_name_prefix='bible-search')
        self.epoch=0;self._refresh_stamp=None;self.search_names=[];self.search_reader=None;self.total=0;self.lemma_query=None
        self.generation=0;self.pending=False;self.context=None;self.topic=None;self.rows=[];self.future=None;self.result_query=''
        self.entry=Gtk.SearchEntry(placeholder_text=tr('Search for a theme…' if mode=='topics' else 'A word or phrase…'))
        # GtkSearchEntry's default delegated minimum can widen the horizontal
        # fallback on older libadwaita. Let the entry expand into the remaining
        # row width rather than impose its desktop-sized default on both modes.
        self.entry.get_delegate().set_width_chars(8)
        self.entry.update_property([Gtk.AccessibleProperty.LABEL],[tr('Search for a theme…' if mode=='topics' else 'A word or phrase…')])
        self.entry.connect('search-changed',self.changed)
        query=(Adw.WrapBox(child_spacing=6,line_spacing=6,natural_line_length=480)
               if hasattr(Adw,'WrapBox') else Gtk.Box(spacing=6))
        self.entry.set_hexpand(True);self.entry.set_size_request(110,-1);query.append(self.entry);self.append(query)
        self.source=Gtk.DropDown(enable_search=True)
        from .version_chooser import bounded_choices
        bounded_choices(self.source);self.source.set_enable_search(True)
        self.source.update_property([Gtk.AccessibleProperty.LABEL],[tr('Search translation')])
        self.source.connect('notify::selected',self.source_changed)
        # Retained as an internal source model for lexical occurrence searches.
        # Ordinary text searches always use the active reading translation.
        self.source.set_visible(False)
        self.scope=Gtk.DropDown();self.scope_names=['all']
        self.scope.connect('notify::selected',lambda *_:self.changed())
        self.scope.update_property([Gtk.AccessibleProperty.LABEL],[tr('Search scope')])
        self.scope.set_visible(mode=='text')
        bounded_choices(self.scope);self.scope.add_css_class('flat');query.append(self.scope)
        self.submit=Gtk.Button(icon_name='system-search-symbolic',tooltip_text=tr('Search'))
        self.submit.update_property([Gtk.AccessibleProperty.LABEL],[tr('Search')]);self.submit.connect('clicked',self.run_text)
        self.entry.connect('activate',self.run_text if mode=='text' else self.activate_first)
        self.submit.set_visible(mode=='text');query.append(self.submit)
        self.spinner=Gtk.Spinner()
        self.spinner.update_property([Gtk.AccessibleProperty.LABEL],[tr('Searching…')])
        self.submit_display=Gtk.Stack()
        self.submit_display.add_named(Gtk.Image(icon_name='system-search-symbolic'),'search')
        self.submit_display.add_named(self.spinner,'busy');self.submit.set_child(self.submit_display)
        self.explanation=Gtk.Label(xalign=0,wrap=True,max_width_chars=55)
        self.explanation.add_css_class('caption')
        self.explanation.set_margin_start(12);self.explanation.set_margin_end(12);self.explanation.set_margin_top(12);self.explanation.set_margin_bottom(12)
        help_button=Gtk.MenuButton(icon_name='help-about-symbolic',tooltip_text=tr('Search syntax'))
        help_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Search syntax')])
        help_button.add_css_class('flat');help_button.set_visible(mode=='text')
        help_pop=Gtk.Popover();help_pop.set_child(self.explanation);help_button.set_popover(help_pop);query.append(help_button)
        self.status=Gtk.Label(xalign=0,wrap=True,max_width_chars=55,visible=False);self.append(self.status)
        self.status.connect('notify::label',lambda *_:self.status.set_visible(bool(self.status.get_text())))
        self.download=Gtk.Button(label=tr('Download topic data'));self.download.connect('clicked',self.open_library);self.append(self.download)
        self.topic_model=Gio.ListStore.new(SearchItem)
        topic_factory=Gtk.SignalListItemFactory();topic_factory.connect('setup',self.topic_setup);topic_factory.connect('bind',self.topic_bind)
        self.topics=Gtk.ListView(model=Gtk.NoSelection(model=self.topic_model),factory=topic_factory)
        self.topic_scroll=Gtk.ScrolledWindow(min_content_height=80,max_content_height=160,propagate_natural_height=True,
                                            hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.topic_scroll.set_child(self.topics);self.topic_scroll.set_visible(mode=='topics')
        if mode!='topics':self.append(self.topic_scroll)
        self.back_topics=Gtk.Button(icon_name='go-previous-symbolic',tooltip_text=tr('All themes'),halign=Gtk.Align.START,visible=False)
        self.back_topics.update_property([Gtk.AccessibleProperty.LABEL],[tr('All themes')])
        self.back_topics.add_css_class('flat');self.back_topics.connect('clicked',self.show_topics)
        self.heading=Gtk.Label(xalign=0,wrap=True,width_chars=1,hexpand=True);self.heading.add_css_class('heading');self.heading.set_visible(mode!='topics')
        self.topic_count=Gtk.Label(xalign=1);self.topic_count.add_css_class('dim-label')
        if mode=='topics':self.heading.set_wrap(False);self.heading.set_ellipsize(Pango.EllipsizeMode.END)
        self.topic_header=Gtk.Box(spacing=8,visible=mode!='topics')
        self.topic_header.append(self.back_topics);self.topic_header.append(self.heading)
        if mode=='topics':self.topic_header.append(self.topic_count)
        self.append(self.topic_header)
        self.model=Gio.ListStore.new(SearchItem)
        factory=Gtk.SignalListItemFactory();factory.connect('setup',self.result_setup);factory.connect('bind',self.result_bind)
        self.results=Gtk.ListView(model=Gtk.NoSelection(model=self.model),factory=factory)
        scroll=Gtk.ScrolledWindow(min_content_height=100,max_content_height=280,propagate_natural_height=True,
                                   hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_child(self.results);self.result_scroll=scroll
        self.set_vexpand(False)
        scroll.set_min_content_height(0);scroll.set_propagate_natural_height(True)
        if mode=='topics':
            self.topic_scroll.set_min_content_height(0)
            self.topic_scroll.set_propagate_natural_height(True)
            self.topic_pages=Gtk.Stack(hhomogeneous=False,vhomogeneous=False)
            self.topic_pages.add_named(self.topic_scroll,'topics');self.topic_pages.add_named(scroll,'results')
            self.append(self.topic_pages)
        else:self.append(scroll)
        self.more=Gtk.Button(label=tr('More results'),visible=False)
        self.more.connect('clicked',lambda *_:self.run_lemma(append=True) if self.lemma_query else self.run_text(append=True));self.append(self.more)
        self.credit=Gtk.MenuButton(child=Gtk.Label(label='OpenBible.info',xalign=0),halign=Gtk.Align.START)
        self.credit.add_css_class('flat');self.credit.add_css_class('caption');self.credit.add_css_class('source-attribution');self.credit.set_visible(mode=='topics')
        self.credit.update_property([Gtk.AccessibleProperty.LABEL],[tr('Source and license')])
        information=Gtk.Popover()
        notice=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,max_width_chars=36,
            margin_start=12,margin_end=12,margin_top=12,margin_bottom=12,selectable=True)
        notice.add_css_class('source-attribution')
        notice.set_markup('<a href="'+SOURCE_URL+'">OpenBible.info</a> · <a href="'+LICENSE_URL+'">CC BY 4.0</a>\n'+
            GLib.markup_escape_text(tr('Community suggestions; explore the context.'))+'\n\n'+GLib.markup_escape_text(TRANSFORMATIONS))
        notice_scroll=Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
            propagate_natural_height=True,propagate_natural_width=True,
            min_content_width=220,max_content_width=360,max_content_height=350)
        notice_scroll.set_child(notice);information.set_child(notice_scroll)
        self.credit.set_popover(information);self.append(self.credit)
        self.refresh()

    def close(self):self.generation+=1;self.executor.shutdown(wait=False,cancel_futures=True)

    def pause(self):
        self.epoch+=1
        if self.pending:
            self.invalidate()
            self.status.set_text('' if self.mode=='topics' else tr('Enter a phrase and press Enter.'))
            if self.mode=='topics':self.show_topics()
        elif self.future:self.future.cancel()
        self.pending=False;self.busy(False)

    def busy(self,value):
        self.spinner.set_spinning(value);self.submit_display.set_visible_child_name('busy' if value else 'search')

    def invalidate(self,keep_results=False):
        if hasattr(self,'more'):self.more.set_visible(False)
        if self.future:self.future.cancel();self.future=None
        self._submitted_query=None
        self.generation+=1;self.pending=False;self.busy(False)
        self.results.set_sensitive(False)
        if not keep_results:self.model.remove_all();self.rows=[];self.row_cache={};self.chapter_cache={}
        if hasattr(self.owner,'reference_preview'):self.owner.reference_preview.dismiss()
        self.heading.set_text('');self.status.set_text('');self.status.set_tooltip_text(None)

    def refresh(self):
        names=self.owner.library.installed('bible')
        revision=self.data.revision if self.mode=='topics' else None
        active=self.owner.active_tab if hasattr(self.owner,'view') else None
        vocabulary=self.vocabulary.read() if self.mode=='topics' else None
        stamp=(tuple(names),revision,bool(active),self.navigation.selected_resource(),LANGUAGE,vocabulary[2] if vocabulary else None)
        if stamp==self._refresh_stamp:return
        self._refresh_stamp=stamp
        if vocabulary:
            self._vocabulary_entries=vocabulary[1]
            if revision:
                try:identifiers=self.data.identifiers()
                except (OSError,ValueError):identifiers=frozenset()
                self._vocabulary_entries=tuple(e for e in self._vocabulary_entries if e[0] in identifiers)
        self.invalidate()
        self.explanation.set_text(tr('{count} reviewed themes').format(count=len(self._vocabulary_entries)) if self.mode=='topics' else
                                  tr('All words first, then strong close matches. Quoted phrases stay exact. Supported Latin accents are ignored.'))
        if self.mode=='text':
            previous=self.search_names[self.source.get_selected()] if self.source.get_selected()<len(self.search_names) else None
            self.search_names=names
            self._source_syncing=True
            self.source.set_model(Gtk.StringList.new([self.owner.library.resource(n).description for n in names]))
            if active and not self.lemma_query:previous=self.navigation.selected_resource()
            self._had_active_context=bool(active)
            selected=previous if previous in names else active.state.resource if active and active.state.resource in names else names[0] if names else None
            self.source.set_selected(names.index(selected) if selected in names else Gtk.INVALID_LIST_POSITION)
            self._source_syncing=False;self.source_changed()
        self.download.set_visible(self.mode=='topics' and self.data.revision is None)
        if self.mode=='topics':self._topic_filter=None;self.changed()
        else:self.status.set_text('');self.status.set_visible(False)

    def source_changed(self,*_):
        if self.mode!='text' or getattr(self,'_source_syncing',False):return
        self.invalidate();self.search_reader=None
        index=self.source.get_selected()
        if index>=len(self.search_names):return
        from .sword_provider import Reader
        name=self.search_names[index]
        try:
            self.search_reader=Reader(self.owner.library.root/name,name)
            old_scope=self.scope_names[self.scope.get_selected()] if self.scope.get_selected()<len(self.scope_names) else 'all'
            testaments=set()
            for book in self.search_reader.books:
                chapter=next(iter(book.chapters));verse=book.chapters[chapter][0]
                value=self.search_reader.key(f'{book.code}.{chapter}.{verse}').getTestament()
                testaments.add(ord(value) if isinstance(value,str) else int(value))
            self.scope_names=['all']
            if {1,2}<=testaments:self.scope_names+=['ot','nt']
            reference=self.navigation.current_reference()
            code=reference.split('.')[0] if reference else None
            if code in {b.code for b in self.search_reader.books}:self.scope_names.append('book')
            labels={'all':'Whole Bible','ot':'Old Testament','nt':'New Testament','book':'Current Book'}
            self.scope.set_model(Gtk.StringList.new([tr(labels[s]) for s in self.scope_names]))
            self.scope.set_selected(self.scope_names.index(old_scope) if old_scope in self.scope_names else 0)
            if self.lemma_query:self.run_lemma()
        except (OSError,ValueError) as error:self.status.set_text(str(error))

    def changed(self,*_):
        if getattr(self,'_setting_lemma',False):return
        if self.mode=='text' and _ and _[0] is self.entry and self.entry.get_text()==getattr(self,'_submitted_query',None):return
        if self.mode=='topics':
            query=self.entry.get_text()
            if query==getattr(self,'_topic_filter',None):return
            self._topic_filter=query
        if self.mode=='text' and self.lemma_query and self.entry.get_text()==getattr(self,'_lemma_caption',None):return
        self.lemma_query=None
        if self.mode=='text':self.scope.set_visible(True)
        self.invalidate(keep_results=self.mode=='text' and bool(self.rows))
        if self.mode=='text':
            self.status.set_text('');self.status.set_visible(False)
            # GtkEditable.set_text deletes then inserts; its intermediate empty
            # notification must not clear the last completed result list.
            generation=self.generation
            if not self.entry.get_text().strip():
                def clear_empty():
                    if not self.owner.closed and generation==self.generation and not self.entry.get_text().strip():self.invalidate()
                    return False
                GLib.idle_add(clear_empty)
            return
        if self.mode=='topics':self.show_topics()
        entries=suggestions(self.entry.get_text(),entries=self._vocabulary_entries)
        self.topic_model.splice(0,self.topic_model.get_n_items(),[SearchItem(e) for e in entries])
        self.status.set_text(tr('Download topic data once to explore it offline.') if self.data.revision is None else
                             '' if entries else tr('No topic in the supported vocabulary. Try a shorter word.'))
        self.download.set_visible(self.data.revision is None)

    def show_topics(self,*_):
        if self.mode!='topics':return
        self.topic_pages.set_visible_child_name('topics');self.back_topics.set_visible(False);self.heading.set_visible(False);self.topic_header.set_visible(False)
        if _:self._topic_filter=None;self.changed()

    def open_library(self,*_):
        from .study_resources import TOPIC_RESOURCE_ID
        self.navigation.popdown();library=self.owner.open_library('study')
        index=next(i for i,r in enumerate(library.filtered_resources) if r.id==TOPIC_RESOURCE_ID)
        library.open_details(None,index)

    def topic_setup(self,_,item):
        button=passage_card();button._reference_labels[1].set_visible(False)
        button.connect('clicked',lambda b:self.choose(b._topic));item.set_child(button)

    def topic_bind(self,_,item):
        button=item.get_child();button._topic=item.get_item().value;button._reference_labels[0].set_text(title(button._topic))
        button.update_property([Gtk.AccessibleProperty.LABEL],[title(button._topic)])

    def activate_first(self,*_):
        if self.topic_model.get_n_items():self.choose(self.topic_model.get_item(0).value)

    def capture_context(self):
        if self.mode=='text':
            if not self.lemma_query:self.navigation.sync()
            index=self.source.get_selected()
            resource=self.search_names[index] if index<len(self.search_names) else None
            reader=self.search_reader
        else:reader=self.navigation.reader;resource=self.navigation.selected_resource()
        if not reader or resource not in self.owner.library.installed('bible'):
            self.status.set_text(tr('Choose an installed translation.'));return False
        self.context=(resource,reader);return True

    def launch(self,operation,caption,source_system,append=False):
        previous_context=self.context
        if not append:self.invalidate(keep_results=self.mode=='text' and bool(self.rows))
        if not self.capture_context():return
        if previous_context!=self.context:
            self.model.remove_all();self.rows=[];self.row_cache={};self.chapter_cache={}
        display_query=self.entry.get_text()
        if self.mode=='text':self._submitted_query=display_query
        self.source_system=source_system;self.pending=True;self.busy(True);self.status.set_text('');self.heading.set_text(caption if self.mode=='topics' else '')
        generation=self.generation;epoch=self.epoch;future=self.executor.submit(operation);self.future=future
        def complete():
            if self.owner.closed or generation!=self.generation or epoch!=self.epoch:return False
            self.pending=False;self.busy(False)
            try:
                rows,total=future.result();self.total=total;self.result_query=display_query
                self.results.set_sensitive(True)
                if append:
                    self.rows.extend(rows)
                    self.model.splice(self.model.get_n_items(),0,[SearchItem((row,generation)) for row in rows])
                else:
                    self.rows=rows
                    self.model.splice(0,self.model.get_n_items(),[SearchItem((row,generation)) for row in self.rows])
                self.more.set_visible(self.mode=='text' and len(self.rows)<total)
                count=tr('{count} passage' if total==1 else '{count} passages').format(count=total) if self.mode=='topics' else tr('{count} result' if total==1 else '{count} results').format(count=total)
                self.heading.set_text(caption if self.mode=='topics' else count)
                if self.mode=='topics':self.heading.set_tooltip_text(caption)
                if self.mode=='topics':
                    self.topic_count.set_text(count)
                    self.results.scroll_to(0,Gtk.ListScrollFlags.NONE,None)
                self.status.set_text(tr('No matching passages.') if not self.rows else '')
                self.status.set_visible(not self.rows)
            except Exception as error:
                self.status.set_visible(True);self.status.set_text(tr('Search unavailable. Check the installed resource and try again.'));self.status.set_tooltip_text(str(error))
                self.download.set_visible(self.mode=='topics')
            return False
        future.add_done_callback(lambda _:GLib.idle_add(complete))

    def choose(self,entry):
        # An explicit choice wins over the SearchEntry's delayed notification.
        self._topic_filter=self.entry.get_text()
        self.topic=entry
        if self.data.revision is None:self.status.set_text(tr('Download topic data once to explore it offline.'));return
        def operation():
            rows=self.data.query(entry[0]);return rows,len(rows)
        self.topic_pages.set_visible_child_name('results');self.back_topics.set_visible(True);self.heading.set_visible(True);self.topic_header.set_visible(True);self.topic_count.set_text('')
        self.launch(operation,title(entry),'openbible')

    def run_text(self,*_,append=False):
        if self.mode!='text':return
        if self.lemma_query:return self.run_lemma(append=append)
        if not self.capture_context():return
        resource,reader=self.context;query=self.entry.get_text().strip()
        if not query or len(query)>200 or any(ord(c)<32 for c in query):
            self.invalidate();self.status.set_text(tr('Enter a phrase of 1–200 characters.'));return
        from .text_search import search,TextMatch
        from .search_terms import terms
        try:terms(query,self.owner.library.resource(resource).language)
        except ValueError as error:self.status.set_text(tr(str(error)));return
        root=self.owner.library.root
        scope=self.scope_names[self.scope.get_selected()] if self.scope.get_selected()<len(self.scope_names) else 'all'
        reference=self.navigation.current_reference();book=reference.split('.')[0] if reference else None
        offset=len(self.rows) if append else 0
        def operation():
            value=search(root,resource,query,scope,book,offset)
            return [TextMatch(item['reference'],item['reference'],item['kind']) for item in value['matches']],value['total']
        self.launch(operation,query,reader.versification,append=append)
        self._submitted_query=self.entry.get_text()

    def show_lemma(self,corpus,identifier,caption,resource):
        if resource in self.search_names:self.source.set_selected(self.search_names.index(resource))
        self._setting_lemma=True
        self.lemma_query=(corpus,identifier);self._lemma_caption=caption
        self.entry.set_text(caption);self._setting_lemma=False
        self.scope.set_visible(False)
        self.run_lemma()

    def run_lemma(self,append=False):
        if not self.lemma_query:return
        corpus,identifier=self.lemma_query
        from .step_data import StepData
        from .step_sources import CORPORA
        data=StepData(self.owner.library.root.parent/'study-data')
        offset=len(self.rows) if append else 0
        def operation():
            result=data.occurrences(corpus,identifier,offset=offset)
            return [Relationship(ref,ref,0,1) for ref in result['references']],result['addresses']
        self.explanation.set_text(tr('Lemma occurrences in')+' '+CORPORA[corpus]+' · '+tr('English lexical content'))
        self.launch(operation,self._lemma_caption,'NRSV',append=append)

    def result_setup(self,_,item):
        button=passage_card();content=button.get_child()
        score=Gtk.Label(xalign=0,wrap=True);score.add_css_class('caption');content.append(score)
        button._result_score=score
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
        caption,text=self.row_cache[key];heading,excerpt=button._reference_labels;heading.set_text(caption)
        excerpt.set_text(text)
        attributes=Pango.AttrList();attributes.insert(Pango.attr_weight_new(Pango.Weight.NORMAL))
        excerpt.set_attributes(attributes)
        if self.mode=='text' and not self.lemma_query:
            from .search_terms import match_ranges
            try:
                query=self.result_query
                if getattr(row,'kind','strict')=='close':
                    from .search_terms import normalized
                    query=' '.join(normalized(query,self.owner.library.resource(resource).language).split())
                ranges=match_ranges(text,query,self.owner.library.resource(resource).language)
            except ValueError:ranges=()
            for start,end in ranges:
                attribute=Pango.attr_weight_new(Pango.Weight.BOLD)
                attribute.start_index=len(text[:start].encode());attribute.end_index=len(text[:end].encode());attributes.change(attribute)
            excerpt.set_attributes(attributes)
        excerpt.set_direction(Gtk.TextDirection.RTL if reader.rtl else Gtk.TextDirection.LTR);excerpt.set_xalign(1 if reader.rtl else 0)
        score=button._result_score
        close=self.mode=='text' and not self.lemma_query and getattr(row,'kind','strict')=='close'
        score.set_visible(close);score.set_text(tr('Close match') if close else '')

    def preview(self,button):
        row,generation=button._result
        if generation!=self.generation:return
        resource,reader=self.context
        def navigate(action):
            self.navigation.popdown()
            if self.owner.main_pages.get_visible_child_name()=='notes':self.owner.notes_space.guard(action)
            else:action()
        self.owner.reference_preview.show(button,resource,reader,row.start,row.end,source_system=self.source_system,
            provenance='OpenBible.info · '+title(self.topic) if self.mode=='topics' else '',navigation_guard=navigate)
