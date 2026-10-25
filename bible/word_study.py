"""Deliberate lexical offers and temporary study details; no new permanent tab."""
from gi.repository import Gtk,GLib,Pango
from .i18n import tr
from .metadata_workers import MetadataExecutor
from .step_data import StepData
from .step_sources import CORPORA,NOTICE,DOWNLOAD_BYTES
from .word_metadata import selected_metadata
from .reference_resolution import resolve
from .reference_targets import Canon,local_excerpt
from .reference_preview import passage_title


class WordStudy(Gtk.Box):
    def __init__(self,owner):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.owner=owner;self.data=StepData(owner.library.root.parent/'study-data')
        self.executor=MetadataExecutor(thread_name_prefix='bible-word-study')
        self.generation=0;self.offer_generation=0;self.popover=None;self.context=None;self.pending=False
        row=Gtk.Box(spacing=8,margin_start=12,margin_end=12)
        self.back=Gtk.Button(icon_name='go-previous-symbolic',tooltip_text=tr('Back'))
        self.back.update_property([Gtk.AccessibleProperty.LABEL],[tr('Back')]);self.back.connect('clicked',lambda *_:self.leave())
        row.append(self.back);heading=Gtk.Label(label=tr('Word study'),hexpand=True,xalign=0);heading.add_css_class('heading');row.append(heading)
        self.append(row)
        self.content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10,margin_start=12,margin_end=12,margin_bottom=16)
        self.scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.scroll.set_child(self.content);self.append(self.scroll)

    def label(self,value,heading=False):
        label=Gtk.Label(label=value,xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,selectable=True)
        if heading:label.add_css_class('heading')
        return label

    def clear(self):
        while child:=self.content.get_first_child():self.content.remove(child)

    def button(self,label,callback,parent=None):
        button=Gtk.Button(child=Gtk.Label(label=label,wrap=True))
        button.connect('clicked',lambda *_:callback());(parent or self.content).append(button);return button

    def valid(self):
        if self.owner.closed or not self.context:return False
        target,tab,reference=self.context
        return (self.owner.active_tab is tab and tab.state.reference==reference
                and target.source.resource==(tab.state.comparison if target.source.side=='comparison' else tab.state.resource)
                and target.source.reader is (tab._comparison_reader if target.source.side=='comparison' else tab.reader))

    def dismiss_offer(self):
        self.offer_generation+=1
        if self.popover:self.popover.popdown()

    def offer(self,target,anchor):
        self.dismiss_offer()
        if not target or self.owner.closed:return
        metadata=selected_metadata(target)
        pop=Gtk.Popover(autohide=False);pop.set_parent(anchor);self.popover=pop
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
        label=Gtk.Label(label=tr('Explore the original words of this verse'),xalign=0,wrap=True,max_width_chars=36)
        box.append(label)
        action=Gtk.Button(child=Gtk.Label(label=tr('Study this word') if metadata else tr('Explore the original words of this verse'),wrap=True))
        action.connect('clicked',lambda *_:(pop.popdown(),self.open(target,metadata)))
        box.append(action)
        scroll=Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
            max_content_width=max(200,min(320,self.owner.get_width()-72)),propagate_natural_width=True,
            max_content_height=max(180,min(430,self.owner.get_height()-120)),propagate_natural_height=True)
        scroll.set_child(box);pop.set_child(scroll)
        from .popover_dismissal import fit_reader_popover
        pop.connect('show',lambda *_:fit_reader_popover(pop,self.owner))
        self.owner._reading_popovers.append(pop)
        def closed(*_):
            if self.popover is pop:self.popover=None
            if pop in self.owner._reading_popovers:self.owner._reading_popovers.remove(pop)
            GLib.idle_add(lambda:pop.unparent() or False)
        pop.connect('closed',closed);pop.popup()
        if metadata:
            label.set_text(tr('Strong lexical lookup. Exact STEP token or extended-sense alignment is not established.'))
            generation=self.offer_generation;tab=self.owner.active_tab
            def operation():
                return [entry for identifier in metadata['identifiers'] for entry in self.data.candidates(identifier)]
            future=self.executor.submit(operation)
            def complete():
                if self.owner.closed or generation!=self.offer_generation or self.popover is not pop or self.owner.active_tab is not tab:return False
                try:
                    entries=future.result()
                    if len(entries)==1:label.set_text(entries[0]['lemma']+' · '+entries[0]['gloss'][:240]+'\n'+tr('English lexical content')+'\n'+tr('Strong lexical lookup. Exact STEP token or extended-sense alignment is not established.'))
                except Exception:pass
                return False
            future.add_done_callback(lambda _:GLib.idle_add(complete))

    def open(self,target,metadata=None):
        if self.owner.closed or target.source.tab is not self.owner.active_tab:return
        if self.owner.immersion:self.owner.leave_immersion()
        self.generation+=1;self.pending=False
        study=self.owner.study
        if study.tool!='word':
            self.previous_tool=study.tool;self.previous_focus=self.owner.get_focus()
            if self.owner.passage_actions.contains(self.previous_focus):self.previous_focus=target.view
        self.target=target;self.lexical_metadata=metadata
        self.context=(target,self.owner.active_tab,self.owner.active_tab.state.reference)
        self.owner.passage_actions.dismiss()
        self.owner.study_button.set_active(True);study.content_pages.set_visible_child_name('word')
        self.clear();self.back.grab_focus();self.begin()

    def begin(self):
        self.clear()
        if self.data.revision is None:
            self.content.append(self.label(tr('Download study data once to use word lookup offline.')))
            self.button(tr('Download study data ({size} MB)').format(size=f'{DOWNLOAD_BYTES/1000000:.1f}'),self.download)
            return
        target=self.target
        if self.lexical_metadata:
            self.content.append(self.label(tr('Strong lexical lookup. Exact STEP token or extended-sense alignment is not established.')))
            identifiers=self.lexical_metadata['identifiers']
            self.request(lambda:[e for identifier in identifiers for e in self.data.candidates(identifier)],self.lexical_choices)
            self.button(tr('Explore the original words of this verse'),self.verse_choices)
        else:self.verse_choices()

    def download(self):
        from .study_resources import STEP_RESOURCE_ID
        window=self.owner.open_library('study')
        window.reveal_study_resource(STEP_RESOURCE_ID)

    def request(self,operation,complete):
        self.generation+=1;generation=self.generation;self.pending=True
        status=self.label(tr('Loading study data…'));self.content.append(status)
        future=self.executor.submit(operation)
        def finished():
            if generation!=self.generation or not self.valid() or self.owner.study.tool!='word':return False
            self.pending=False
            if status.get_parent() is self.content:self.content.remove(status)
            try:complete(future.result())
            except Exception as error:
                label=self.label(tr('Word study unavailable. Ordinary reading is unchanged.'));label.set_tooltip_text(str(error));self.content.append(label)
                self.button(tr('Download study data'),self.download)
            return False
        future.add_done_callback(lambda _:GLib.idle_add(finished))

    def lexical_choices(self,entries):
        unique={entry['id']:entry for entry in entries}
        if len(unique)==1:self.detail(next(iter(unique.values())));return
        self.content.append(self.label(tr('Choose a supplied lexical entry. Dictionary senses are not a claim about this passage.')))
        for entry in unique.values():
            self.button(entry['lemma']+' · '+entry['gloss'][:160],lambda e=entry:self.detail(e))
        if not unique:self.content.append(self.label(tr('No lexical entry supplied for these identifiers.')))

    def verse_choices(self):
        self.generation+=1;self.clear()
        self.content.append(self.label(tr('These are words of the identified source corpus, not a claimed translation of the selected word.')))
        if len(self.target.references)==1:self.explore(self.target.references[0]);return
        for ref in self.target.references:
            self.button(passage_title(ref,system=self.target.source.reader.versification),lambda r=ref:self.explore(r))

    def explore(self,reference):
        source=self.target.source
        try:
            mapped=resolve(reference,source.reader.versification,Canon('NRSV'),require_entry=False)
            # Split mappings are displayed explicitly, never reduced to one verse.
            from .reference_resolution import _span
            refs=_span(mapped.start,mapped.end,'NRSV')
        except ValueError:
            self.content.append(self.label(tr('No verified alignment for this passage.')));return
        self.clear();self.content.append(self.label(tr('These are words of the identified source corpus, not a claimed translation of the selected word.')))
        corpus='tagnt-na27' if source.reader.key(reference).getTestament() in (2,'\x02') else 'tahot-main'
        self.content.append(self.label(CORPORA[corpus]))
        def operation():return [(ref,self.data.verse(corpus,ref)) for ref in refs]
        def show(rows):
            found=False
            for ref,tokens in rows:
                self.content.append(self.label(passage_title(ref,system='NRSV'),True))
                for token in tokens:
                    found=True
                    button=self.button(token['form']+'\n'+token['transliteration']+' · '+token['gloss'],lambda t=token:self.token_detail(corpus,t))
                    if token['language'] in ('hbo','arc'):button.get_child().set_direction(Gtk.TextDirection.RTL)
            if not found:self.content.append(self.label(tr('No words supplied for this mapped source verse.')))
        self.request(operation,show)

    def token_detail(self,corpus,token):
        tags=[row[0] for row in token.get('lexical',[])] if corpus=='tahot-main' else token['tags']
        tags=list(dict.fromkeys(tags))
        self.clear();self.content.append(self.label(token['form'],True))
        self.content.append(self.label(token['transliteration']+' · '+token['gloss']))
        self.token=token;self.corpus=corpus
        self.request(lambda:[entry for tag in tags if (entry:=self.data.lookup(tag))],lambda entries:self.token_choices(entries,corpus,token))

    def token_choices(self,entries,corpus,token):
        if len(entries)==1:self.detail(entries[0],corpus,token)
        elif entries:
            for entry in entries:self.button(entry['lemma']+' · '+entry['gloss'][:160],lambda e=entry:self.detail(e,corpus,token))
        else:self.content.append(self.label(tr('No lexical entry supplied for these identifiers.')))

    def detail(self,entry,corpus=None,token=None):
        self.clear();self.entry=entry
        corpus=corpus or ('tagnt-na27' if entry['id'].startswith('G') else 'tahot-main')
        if token:
            self.content.append(self.label(token['form'],True))
            if token['transliteration']:self.content.append(self.label(token['transliteration']))
        self.content.append(self.label(entry['lemma'],True))
        if entry.get('transliteration'):self.content.append(self.label(entry['transliteration']))
        self.content.append(self.label(tr({'grc':'Greek','hbo':'Hebrew','arc':'Aramaic'}.get(token['language'] if token else entry['language'],'Hebrew'))+' · '+tr('English lexical content')))
        # Basic dictionary categories are defined by the TBESG file header.
        categories={'N':'Noun','V':'Verb','A':'Adjective','ADV':'Adverb','ART':'Article',
                    'PREP':'Preposition','CONJ':'Conjunction','PRT':'Particle'}
        code=entry.get('category','').split(':')[-1].split('-')[0].upper()
        if code in categories:self.content.append(self.label(tr(categories[code])))
        elif token and token['language'] in ('hbo','arc'):
            # TEHMC at the pinned STEP commit defines N/V at the start of
            # each Hebrew/Aramaic word-function segment; do not infer tense.
            functions=[part[:1] for part in token['morphology'][1:].split('/')]
            function=next((c for c in functions if c in ('N','V')),None)
            if function:self.content.append(self.label(tr(categories[function])))
        self.content.append(self.label(entry['gloss'][:800]))
        self.content.append(self.label(tr('Dictionary meanings describe possible senses, not all meanings intended in this passage.')))
        from .resource_details import plain
        self.content.append(self.label('STEPBible / Tyndale House · CC BY 4.0'))
        self.content.append(self.label(CORPORA[corpus]))
        counts=self.label(tr('Loading occurrences…'));self.content.append(counts)
        occurrence_rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        self.content.append(occurrence_rows)
        excluded=set()
        from .reference_resolution import _span
        for reference in self.target.references:
            try:
                mapped=resolve(reference,self.target.source.reader.versification,Canon('NRSV'),require_entry=False)
                excluded.update(_span(mapped.start,mapped.end,'NRSV'))
            except ValueError:pass
        def show(result):
            counts.set_text(tr('{tokens} source tokens · {verses} distinct verses').format(**result))
            for ref in [r for r in result['references'] if r not in excluded][:4]:
                try:
                    excerpt=local_excerpt(self.target.source.reader,ref,source_system='NRSV',limit=1)
                    caption=passage_title(excerpt.start,excerpt.end,self.target.source.reader.versification)+'\n'+excerpt.text
                except ValueError:caption=passage_title(ref,system='NRSV')+'\n'+tr('This passage is unavailable in the selected translation.')
                button=self.button(caption,lambda r=ref:self.preview(r),parent=occurrence_rows)
                button.add_css_class('flat')
                content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
                title,_,body=caption.partition('\n')
                title_label=self.label(title,True);title_label.set_selectable(False);title_label.add_css_class('accent');content.append(title_label)
                body_label=self.label(body);body_label.set_selectable(False);body_label.set_lines(2);body_label.set_ellipsize(Pango.EllipsizeMode.END)
                attributes=Pango.AttrList();attributes.insert(Pango.attr_weight_new(Pango.Weight.NORMAL));body_label.set_attributes(attributes)
                content.append(body_label);button.set_child(content)
                button._word_reference=ref
            self.button(tr('View all occurrences'),lambda:self.all_occurrences(corpus,entry),parent=occurrence_rows)
        self.request(lambda:self.data.occurrences(corpus,entry['id'],limit=min(200,4+len(excluded))),show)
        details=Gtk.Expander(label=tr('Details'))
        text=entry['id']+'\n'+(entry.get('category') or '')+'\n'+(token['morphology'] if token else '')
        if self.lexical_metadata:text+='\n'+self.lexical_metadata['source_lemma']+'\n'+self.lexical_metadata['source_morphology']
        text+='\n'+plain(entry.get('definition',''))+'\n'+NOTICE
        details.set_child(self.label(text));self.content.append(details)
        notices=Gtk.Expander(label=tr('Source notices'))
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8);notices.set_child(box)
        self.content.append(notices)
        def load_notices(expander,*_):
            if expander.get_expanded() and not box.get_first_child():
                try:
                    headers=self.data.metadata().get('headers',{})
                    for name,header in headers.items():
                        inner=Gtk.Expander(label=name);inner.set_child(self.label(header));box.append(inner)
                    if not headers:box.append(self.label(NOTICE))
                except (OSError,ValueError):box.append(self.label(NOTICE))
        notices.connect('notify::expanded',load_notices)
        self.button(tr('Explore the original words of this verse'),self.verse_choices)

    def preview(self,reference):
        source=self.target.source
        button=next((c for c in self.children() if getattr(c,'_word_reference',None)==reference),None)
        from .step_sources import SOURCE_URL
        if button:self.owner.reference_preview.show(button,source.resource,source.reader,reference,source_system='NRSV',
            provenance='STEPBible / Tyndale House · CC BY 4.0\n'+SOURCE_URL)

    def children(self):
        def walk(parent):
            child=parent.get_first_child()
            while child:
                yield child
                yield from walk(child)
                child=child.get_next_sibling()
        yield from walk(self.content)

    def all_occurrences(self,corpus,entry):
        navigation=self.owner.navigation
        self.owner.choose_passage();navigation.modes.set_visible_child_name('text')
        navigation.text_search.show_lemma(corpus,entry['id'],entry['lemma']+' · '+tr('Lemma occurrences'),self.target.source.resource)

    def leave(self):
        self.generation+=1;self.pending=False;self.owner.reference_preview.dismiss()
        self.owner.study.tools.set_visible_child_name(getattr(self,'previous_tool','notes'))
        self.owner.study.content_pages.set_visible_child_name('tools')
        focus=getattr(self,'previous_focus',None)
        if focus and focus.get_mapped():focus.grab_focus()
        self.context=None

    def refresh(self):
        if self.owner.study.tool=='word':
            if not self.valid():self.leave()

    def close(self):
        self.generation+=1;self.dismiss_offer();self.executor.shutdown(wait=False,cancel_futures=True)
