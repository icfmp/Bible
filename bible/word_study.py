"""Deliberate lexical offers and temporary study details; no new permanent tab."""
from gi.repository import Adw,Gtk,Gdk,GLib,Pango
from .i18n import tr
from .metadata_workers import MetadataExecutor
from .step_data import StepData
from .step_sources import DOWNLOAD_BYTES
from .word_metadata import selected_metadata,source_verse_references
from .reference_targets import local_excerpt
from .reference_preview import passage_title


class WordStudy(Gtk.Box):
    def __init__(self,owner):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.owner=owner;self.data=StepData(owner.library.root.parent/'study-data')
        self.executor=MetadataExecutor(thread_name_prefix='bible-word-study')
        self.generation=0;self.offer_generation=0;self.popover=None;self.context=None;self.pending=False
        self.dialog=None;self.futures=set()
        row=Adw.HeaderBar(show_end_title_buttons=False)
        self.back=Gtk.Button(icon_name='window-close-symbolic',tooltip_text=tr('Close'))
        self.back.update_property([Gtk.AccessibleProperty.LABEL],[tr('Close')]);self.back.connect('clicked',lambda *_:self.leave())
        row.pack_end(self.back);self.heading=Gtk.Label(label=tr("Explore the verse's words"),wrap=True)
        self.heading.add_css_class('heading');row.set_title_widget(self.heading)
        self.go_back=Gtk.Button(icon_name='go-previous-symbolic',tooltip_text=tr('Back'),visible=False)
        self.go_back.update_property([Gtk.AccessibleProperty.LABEL],[tr('Back')])
        self.go_back.connect('clicked',self.previous);row.pack_start(self.go_back)
        self.append(row)
        self.context_label=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,
            margin_start=16,margin_end=16,margin_top=8,margin_bottom=8)
        self.context_label.add_css_class('dim-label');self.append(self.context_label)
        self.selection_label=Gtk.Label(xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,
            lines=2,ellipsize=Pango.EllipsizeMode.END,margin_start=16,margin_end=16,margin_bottom=8)
        self.append(self.selection_label)
        self.content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10,margin_start=12,margin_end=12,margin_bottom=16)
        self.scroll=Gtk.ScrolledWindow(vexpand=True,hscrollbar_policy=Gtk.PolicyType.NEVER,
            propagate_natural_height=False,min_content_height=160,max_content_height=420)
        self.scroll.set_child(self.content);self.append(self.scroll)
        from .source_credit import source_credit
        from .step_sources import SOURCE_URL
        credit=source_credit('STEPBible / Tyndale House · CC BY 4.0\n'+SOURCE_URL)
        credit.set_margin_start(16);credit.set_margin_end(16);credit.set_margin_bottom(12);self.append(credit)

    def label(self,value,heading=False):
        label=Gtk.Label(label=value,xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,selectable=True)
        if heading:label.add_css_class('heading')
        return label

    def script_label(self,value,language):
        label=self.label(value,True)
        if language in ('hbo','arc'):
            label.set_direction(Gtk.TextDirection.RTL);label.set_xalign(1)
        return label

    def remove_content(self,child):
        # Keep focus in a live, parented widget before replacing dynamic content.
        # GTK's label focus transfer may inspect its previous focus after the
        # root releases it; an already-unparented label can then be destroyed.
        root=self.get_root();focus=root.get_focus() if root else None
        if focus and (focus is child or focus.is_ancestor(child)):
            self.back.grab_focus()
        self.content.remove(child)

    def clear(self):
        while child:=self.content.get_first_child():self.remove_content(child)

    def button(self,label,callback,parent=None):
        button=Gtk.Button(child=Gtk.Label(label=label,wrap=True))
        button.connect('clicked',lambda *_:callback());(parent or self.content).append(button);return button

    def valid(self):
        if self.owner.closed or not self.context or self.dialog is None:return False
        target,tab,reference=self.context
        return (self.owner.active_tab is tab and tab.state.reference==reference
                and target.source.resource==(tab.state.comparison if target.source.side=='comparison' else tab.state.resource)
                and target.source.reader is (tab._comparison_reader if target.source.side=='comparison' else tab.reader))

    def dismiss_offer(self):
        self.offer_generation+=1
        if self.popover:self.popover.popdown()

    def offer(self,target,anchor=None):
        if not target or self.owner.closed:return
        self.offer_generation+=1;generation=self.offer_generation
        metadata=selected_metadata(target)
        def present():
            if self.owner.closed or generation!=self.offer_generation:return False
            current=target.factory()
            if (current and self.owner.active_tab is target.source.tab
                    and current.reader is target.source.reader and current.document.key==target.source.document.key):
                self.open(target,metadata)
            return False
        # Finish the native activation before hiding its toolbar/menu anchor.
        GLib.idle_add(present)

    def open(self,target,metadata=None):
        if self.owner.closed or target.source.tab is not self.owner.active_tab:return
        previous=self.dialog;self.leave(restore_focus=False)
        if previous:previous.set_content(None)
        self.restore_focus=True
        self.generation+=1;self.pending=False;self.previous_focus=target.view
        self.target=target;self.lexical_metadata=metadata
        self.context=(target,self.owner.active_tab,self.owner.active_tab.state.reference)
        resource=self.owner.library.resource(target.source.resource)
        self.context_label.set_text(passage_title(target.references[0],target.references[-1],target.source.reader.versification)+' — '+resource.description)
        # This is a compact context excerpt, not the original-word display.
        # Explicit translation line breaks otherwise each get their own line
        # limit and can consume the entire small dialog before any source word.
        self.selection_label.set_text(' '.join(target.text.split()))
        self.selection_label.set_visible(bool(target.text))
        self.owner.passage_actions.dismiss()
        self.dialog=Adw.Window(title=tr('Original text'),transient_for=self.owner,modal=True,
            destroy_with_parent=True,default_width=min(640,max(320,self.owner.get_width()-48)),
            default_height=min(600,max(360,self.owner.get_height()-96)))
        self.scroll.set_max_content_height(max(160,min(420,self.owner.get_height()-250)))
        self.dialog.add_css_class(self.owner.reading_style.scope+'-window')
        self.dialog.set_content(self)
        self.dialog.connect('close-request',self.dialog_closed)
        keys=Gtk.EventControllerKey()
        keys.connect('key-pressed',lambda _,key,*args:(self.leave() or True) if key==Gdk.KEY_Escape else False)
        self.dialog.add_controller(keys)
        self.begin();self.dialog.present();self.back.grab_focus()

    def dialog_closed(self,*_):
        dialog=self.dialog;self.dialog=None;self.generation+=1;self.pending=False;self.context=None
        for future in self.futures:future.cancel()
        self.futures.clear();self.owner.reference_preview.dismiss()
        focus=getattr(self,'previous_focus',None)
        restore=self.restore_focus
        def detached():
            if dialog and dialog.get_content() is self:dialog.set_content(None)
            if restore and not self.dialog and not self.owner.closed and focus and focus.get_mapped():focus.grab_focus()
            return False
        GLib.idle_add(detached)
        return False

    def begin(self):
        self.clear()
        self.stage='passage';self.go_back.set_visible(False)
        if self.data.revision is None:
            self.content.append(self.label(tr('Download study data once to use word lookup offline.')))
            self.button(tr('Download study data ({size} MB)').format(size=f'{DOWNLOAD_BYTES/1000000:.1f}'),self.download)
            return
        self.verse_choices()

    def download(self):
        from .study_resources import STEP_RESOURCE_ID
        self.leave(restore_focus=False)
        window=self.owner.open_library('study')
        window.reveal_study_resource(STEP_RESOURCE_ID)

    def request(self,operation,complete):
        self.generation+=1;generation=self.generation;self.pending=True
        status=self.label(tr('Loading study data…'));self.content.append(status)
        future=self.executor.submit(operation);self.futures.add(future)
        def finished():
            self.futures.discard(future)
            if generation!=self.generation or not self.valid():return False
            self.pending=False
            if status.get_parent() is self.content:self.remove_content(status)
            try:complete(future.result())
            except Exception as error:
                label=self.label(tr('Original text unavailable. Ordinary reading is unchanged.'));label.set_tooltip_text(str(error));self.content.append(label)
                self.button(tr('Download study data'),self.download)
            return False
        future.add_done_callback(lambda _:GLib.idle_add(finished) if self.context and generation==self.generation else None)

    def lexical_choices(self,entries):
        unique={entry['id']:entry for entry in entries}
        if len(unique)==1:self.detail(next(iter(unique.values())));return
        self.content.append(self.label(tr('Choose a supplied lexical entry. Dictionary senses are not a claim about this passage.')))
        for entry in unique.values():
            self.button(entry['lemma']+' · '+entry['gloss'][:160],lambda e=entry:self.detail(e))
        if not unique:self.content.append(self.label(tr('No lexical entry supplied for these identifiers.')))

    def verse_choices(self):
        self.generation+=1;self.clear()
        self.stage='passage';self.go_back.set_visible(False)
        self.heading.set_text(tr("Explore the verse's words"))
        if self.dialog:self.dialog.set_title(self.heading.get_text())
        self.content.append(self.label(tr('Select a word to discover its meaning.')))
        references=self.target.references
        self._verse_offset=0
        self.passage_words(references)

    def explore(self,reference):
        self.generation+=1;self.clear();self.stage='passage';self.go_back.set_visible(False)
        self._verse_offset=0;self.passage_words((reference,))

    def passage_words(self,references):
        source=self.target.source;batch=references[self._verse_offset:self._verse_offset+5]
        def operation():
            rows=[]
            for reference in batch:
                try:refs=source_verse_references(reference,source.reader)
                except ValueError:rows.append((reference,None,()));continue
                corpus='tagnt-na27' if source.reader.key(reference).getTestament() in (2,'\x02') else 'tahot-main'
                rows.append((reference,corpus,tuple((ref,self.data.verse(corpus,ref)) for ref in refs)))
            return rows
        def show(rows):
            for reference,corpus,verses in rows:
                self.content.append(self.label(passage_title(reference,system=source.reader.versification),True))
                if corpus is None:
                    self.content.append(self.label(tr('No verified alignment for this passage.')));continue
                self.content.append(self.label(tr('Greek text' if corpus=='tagnt-na27' else 'Hebrew / Aramaic text'),True))
                found=False
                for ref,tokens in verses:
                    if len(verses)>1 or ref!=reference:
                        self.content.append(self.label(tr('Source reference: {reference}').format(reference=passage_title(ref,system='NRSV'))))
                    flow=Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE,min_children_per_line=1,
                                     max_children_per_line=30,column_spacing=6,row_spacing=6)
                    if corpus=='tahot-main':flow.set_direction(Gtk.TextDirection.RTL)
                    self.content.append(flow)
                    for token in tokens:
                        found=True
                        button=Gtk.Button(child=Gtk.Label(label=token['form'],wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR))
                        button.set_cursor_from_name('pointer')
                        button._source_token=token;button._source_corpus=corpus
                        button.connect('clicked',lambda _,c=corpus,t=token:self.token_detail(c,t))
                        flow.append(button)
                        if token['source_key']==getattr(self,'passage_anchor',None):button.grab_focus()
                if not found:self.content.append(self.label(tr('No words supplied for this mapped source verse.')))
                note=self.label(tr('Original words do not necessarily match translation words one for one.'))
                note.add_css_class('caption');note.add_css_class('dim-label');self.content.append(note)
            self._verse_offset+=len(batch)
            if self._verse_offset<len(references):
                more=self.button(tr('More verses'),lambda:more_clicked())
                def more_clicked():
                    self.remove_content(more);self.passage_words(references)
            if self.lexical_metadata:
                self.button(tr('Lexical entries for the selected translation word'),self.selected_lexemes)
        self.request(operation,show)

    def selected_lexemes(self):
        self.clear();self.stage='word';self.go_back.set_visible(True)
        self.content.append(self.label(tr('Strong lexical lookup. Exact STEP token or extended-sense alignment is not established.')))
        identifiers=self.lexical_metadata['identifiers']
        self.request(lambda:[e for identifier in identifiers for e in self.data.candidates(identifier)],self.lexical_choices)

    def previous(self,*_):
        if self.stage=='occurrences':self.detail(self.entry,self.corpus,getattr(self,'token',None))
        else:self.verse_choices()

    def token_detail(self,corpus,token):
        tags=[row[0] for row in token.get('lexical',[])] if corpus=='tahot-main' else token['tags']
        tags=list(dict.fromkeys(tags))
        self.passage_anchor=token['source_key']
        self.clear();self.stage='word';self.go_back.set_visible(True);self.content.append(self.script_label(token['form'],token['language']))
        self.content.append(self.label(token['transliteration']+' · '+token['gloss']))
        self.content.append(self.label(tr('English lexical content')))
        self.token=token;self.corpus=corpus
        self.request(lambda:[entry for tag in tags if (entry:=self.data.lookup(tag))],lambda entries:self.token_choices(entries,corpus,token))

    def token_choices(self,entries,corpus,token):
        if len(entries)==1:self.detail(entries[0],corpus,token)
        elif entries:
            for entry in entries:self.button(entry['lemma']+' · '+entry['gloss'][:160],lambda e=entry:self.detail(e,corpus,token))
        else:self.content.append(self.label(tr('No lexical entry supplied for these identifiers.')))

    def detail(self,entry,corpus=None,token=None):
        self.clear();self.stage='word';self.go_back.set_visible(True);self.entry=entry;self.token=token
        corpus=corpus or ('tagnt-na27' if entry['id'].startswith('G') else 'tahot-main')
        self.corpus=corpus
        language=token['language'] if token else entry['language']
        self.heading.set_text(tr('Understand a Greek word' if language=='grc' else 'Understand a Hebrew word' if language=='hbo' else 'Understand an Aramaic word'))
        if self.dialog:self.dialog.set_title(self.heading.get_text())
        form=token['form'] if token else entry['lemma'] or entry['id']
        surface=self.script_label(form,language);surface.add_css_class('title-1');self.content.append(surface)
        transliteration=(token.get('transliteration') if token else '') or entry.get('transliteration')
        if transliteration:self.content.append(self.label(transliteration))
        self.content.append(self.label(tr('Common meanings'),True))
        self.content.append(self.label(entry['gloss'] or tr('No meaning supplied by the installed lexicon.')))
        source=self.label(tr('The installed STEP lexicon provides English meanings.'))
        source.add_css_class('caption');self.content.append(source)
        # Basic dictionary categories are defined by the TBESG file header.
        categories={'N':'Noun','V':'Verb','A':'Adjective','ADV':'Adverb','ART':'Article',
                    'PREP':'Preposition','CONJ':'Conjunction','PRT':'Particle'}
        code=entry.get('category','').split(':')[-1].split('-')[0].upper()
        category=tr(categories[code]) if code in categories else ''
        if not category and token and token['language'] in ('hbo','arc'):
            # TEHMC at the pinned STEP commit defines N/V at the start of
            # each Hebrew/Aramaic word-function segment; do not infer tense.
            functions=[part[:1] for part in token['morphology'][1:].split('/')]
            function=next((c for c in functions if c in ('N','V')),None)
            if function:category=tr(categories[function])
        hint=self.label(tr('Dictionary meanings describe possible senses, not all meanings intended in this passage.'))
        hint.add_css_class('caption');hint.add_css_class('dim-label');self.content.append(hint)
        from .resource_details import plain
        self.button(tr('See other occurrences'),lambda:self.all_occurrences(corpus,entry))
        details=Gtk.Expander(label=tr('Linguistic details'))
        text=tr('Dictionary headword')+': '+(entry['lemma'] or entry['id'])+'\n'+entry['id']
        if entry.get('transliteration'):text+='\n'+entry['transliteration']
        if category:text+='\n'+category
        text+='\n'+(entry.get('category') or '')+'\n'+(token['morphology'] if token else '')
        if self.lexical_metadata:text+='\n'+self.lexical_metadata['source_lemma']+'\n'+self.lexical_metadata['source_morphology']
        text+='\n'+plain(entry.get('definition',''))
        details.set_child(self.label(text));self.content.append(details)

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
        self.clear();self.stage='occurrences';self.go_back.set_visible(True)
        self.heading.set_text(tr('Other occurrences'))
        if self.dialog:self.dialog.set_title(self.heading.get_text())
        self.content.append(self.label((entry['lemma'] or entry['id'])+' — '+tr('Lemma occurrences'),True))
        self.content.append(self.label(tr('Counts refer to this source corpus; a word can have different meanings in context.')))
        self.occurrence_offset=0
        self.occurrence_rows(corpus,entry)

    def occurrence_rows(self,corpus,entry):
        def show(result):
            if not self.occurrence_offset:
                self.content.append(self.label(tr('{tokens} source tokens · {verses} distinct verses').format(**result)))
            from .passage_card import passage_card
            for ref in result['references']:
                button=passage_card();heading,body=button._reference_labels
                try:
                    excerpt=local_excerpt(self.target.source.reader,ref,source_system='NRSV',limit=1)
                    heading.set_text(passage_title(excerpt.start,excerpt.end,self.target.source.reader.versification));body.set_text(excerpt.text)
                except ValueError:
                    heading.set_text(passage_title(ref,system='NRSV'));body.set_text(tr('This passage is unavailable in the selected translation.'))
                button._word_reference=ref;button.connect('clicked',lambda _,r=ref:self.preview(r));self.content.append(button)
            self.occurrence_offset+=len(result['references'])
            if self.occurrence_offset<result['addresses']:
                more=self.button(tr('More results'),lambda:more_clicked())
                def more_clicked():
                    self.remove_content(more);self.occurrence_rows(corpus,entry)
        self.request(lambda:self.data.occurrences(corpus,entry['id'],offset=self.occurrence_offset,limit=30),show)

    def leave(self,restore_focus=True):
        if self.dialog:self.restore_focus=restore_focus;self.dialog.close()

    def refresh(self):
        if self.dialog and not self.valid():self.leave(restore_focus=False)

    def close(self):
        self.leave();self.generation+=1;self.dismiss_offer();self.executor.shutdown(wait=False,cancel_futures=True)
