"""Passage annotation cards and an inline host for the existing safe note editor."""
from gi.repository import Gtk, Pango, GLib, Gdk
from .i18n import tr
from .highlights import COLORS
from .notes import parts
from .notes_window import NoteEditor, passage_label, readable_date
from .passage_annotations import PassageAnnotations
from .annotation_card import AnnotationPreview


class PassageNotes(Gtk.Box):
    def __init__(self, owner):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=10,
                         margin_start=12,margin_end=12,margin_top=12,margin_bottom=16)
        self.owner=owner;self.annotations=PassageAnnotations()
        self.context=None;self._stamp=None;self.rows=[];self.marks=[];self.cards=[];self.editor=None
        self.heading=Gtk.Label(xalign=0,wrap=True);self.heading.add_css_class('heading');self.append(self.heading)
        self.following=True;self._follow_idle=0;self._follow_serial=0;self._card_targets=[]
        self.resume=Gtk.Button(label=tr('Resume following'),halign=Gtk.Align.START,visible=False)
        self.resume.add_css_class('flat');self.resume.connect('clicked',lambda *_:self.resume_following())
        self.status=Gtk.Label(xalign=0,wrap=True,visible=False)
        self.status.add_css_class('dim-label')
        self.status.connect('notify::label',lambda *_:self.status.set_visible(bool(self.status.get_text())))
        self.append(self.status)
        self.editor_panel=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,visible=False)
        self.editor_panel.add_css_class('annotation-card');self.editor_panel.add_css_class('card')
        self.append(self.editor_panel)
        self.list=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);self.append(self.list)
        self.footer=Gtk.Button(label=tr('All my annotations'),halign=Gtk.Align.START)
        self.footer.connect('clicked',lambda *_:self.open_collection())
        self.footer.add_css_class('flat');self.append(self.footer)
        css=Gtk.CssProvider()
        css.load_from_data(b'.annotation-card { padding: 12px; border: 1px solid alpha(currentColor,0.16); border-radius: 12px; } '
                           b'.annotation-card.highlight-yellow { border-left: 3px solid #aa8000; background-color: alpha(#c9a900,0.07); } '
                           b'.annotation-card.highlight-green { border-left: 3px solid #338044; background-color: alpha(#338044,0.07); } '
                           b'.annotation-card.highlight-blue { border-left: 3px solid #427bb7; background-color: alpha(#427bb7,0.07); } '
                           b'.annotation-contrast .annotation-card { background-color: @window_bg_color; border-color: currentColor; }')
        self.css=css
        Gtk.StyleContext.add_provider_for_display(owner.get_display(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.contrast_handler=owner.reading_style.manager.connect('notify::high-contrast',lambda *_:self.style_changed())
        self.style_changed()

    def style_changed(self):
        if self.owner.reading_style.manager.get_high_contrast():self.add_css_class('annotation-contrast')
        else:self.remove_css_class('annotation-contrast')

    def close(self):
        self.cancel_follow()
        self.owner.reading_style.manager.disconnect(self.contrast_handler)
        Gtk.StyleContext.remove_provider_for_display(self.owner.get_display(),self.css)

    def open_collection(self):
        source_editor=self.editor
        tab=self.owner.active_tab;reader=tab.reader if tab else None
        start,end=tab.selected_passage() if reader else (None,None)
        notes=sorted(self.annotations.notes(reader,start,end,self.owner.notes_store),key=lambda note:(note.created,note.id)) if reader and self.owner.notes_store else []
        marks=self.annotations.highlights(reader,start,end,self.owner.highlights) if reader else []
        fallback=(('note',notes[0].id) if notes else ('highlight',marks[0]['system'],marks[0]['reference']) if marks else None)
        def shown(space):
            key=('note',source_editor.note.id) if source_editor and source_editor.note else fallback
            if key:space.reveal(key)
        return self.owner.open_notes(on_open=shown)

    def clear(self,box):
        while box.get_first_child():box.remove(box.get_first_child())

    def bind_scroll(self,scroll):
        self.scroll=scroll
        from .scroll_motion import ScrollMotion
        self.motion=ScrollMotion(scroll)
        wheel=Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
        wheel.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        wheel.connect('scroll',lambda *_:self.suspend_following() or False);scroll.add_controller(wheel)
        keys=Gtk.EventControllerKey();keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        def key(_,value,*args):
            if value in (Gdk.KEY_Up,Gdk.KEY_Down,Gdk.KEY_Page_Up,Gdk.KEY_Page_Down,Gdk.KEY_Home,Gdk.KEY_End,Gdk.KEY_space):self.suspend_following()
            return False
        keys.connect('key-pressed',key);scroll.add_controller(keys)
        click=Gtk.GestureClick(button=1);click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click.connect('pressed',lambda *_:self.suspend_following());scroll.add_controller(click)

    def cancel_follow(self):
        self._follow_serial+=1
        if self._follow_idle:GLib.source_remove(self._follow_idle);self._follow_idle=0

    def suspend_following(self):
        if hasattr(self,'motion'):self.motion.cancel()
        self.following=False;self.resume.set_visible(True);self.cancel_follow()

    def resume_following(self):
        # Reading intent must never move an active draft out of view.
        if self.editor and not self.editor.closed:
            self.suspend_following();return
        self.following=True;self.resume.set_visible(False)
        tab=self.owner.active_tab
        if tab:self.queue_follow(tab.state.reference)

    def refresh(self,force=False):
        if self.owner.closed:return
        tab=self.owner.active_tab;reader=tab.reader if tab else None;store=self.owner.notes_store
        start,end=tab.selected_passage() if reader else (tab.state.reference,tab.state.reference) if tab else (None,None)
        self.context=(dict(versification=reader.versification,start=start,end=end,origin_translation=tab.state.resource,
                          origin_language=self.owner.library.resource(tab.state.resource).language) if reader else None)
        chapter=parts(tab.state.reference)[:2] if tab else None
        stamp=(id(tab),id(reader),chapter,store.generation if store else -1,
               tuple(tuple(m.values()) for m in self.owner.highlights.entries.values()))
        if not force and stamp==self._stamp:
            if tab:self.queue_follow(tab.state.reference)
            return
        self.cancel_follow();self._stamp=stamp
        self.heading.set_text(tr('Notes on')+' '+passage_label(f'{chapter[0]}.{chapter[1]}.1',versification=reader.versification if reader else None).rsplit(' ',1)[0]+f' {chapter[1]}' if chapter else tr('Passage notes'))
        if reader:
            key=reader.key(tab.state.reference)
            first=f'{chapter[0]}.{chapter[1]}.1';last=f'{chapter[0]}.{chapter[1]}.{key.getVerseMax()}'
            self.rows=self.annotations.notes(reader,first,last,store) if store else []
            self.marks=self.annotations.highlights(reader,first,last,self.owner.highlights)
        else:
            def original_match(resource,first,last):
                from .notes import BOOK_ORDER
                def order(ref):
                    b,c,v=parts(ref);return BOOK_ORDER.get(b,10000),b,c,v
                low=f'{chapter[0]}.{chapter[1]}.1';high=f'{chapter[0]}.{chapter[1]}.999'
                return bool(tab and resource==tab.state.resource and order(first)<=order(high) and order(last)>=order(low))
            self.rows=[n for n in store.all() if original_match(n.origin_translation,n.start,n.end)] if store and chapter else []
            self.marks=[m for m in self.owner.highlights.entries.values() if original_match(m['resource'],m['reference'],m['reference'])] if chapter else []
        self.status.set_text(tr('Notes unavailable. The original file has been preserved.') if not store else
                             tr('No annotations in this chapter.') if not self.rows and not self.marks else '')
        from .annotation_collection import records,bible_order
        entries=records(self.rows,self.marks)
        def targets(a):
            return self.annotations.positions(reader,a.system,a.start,a.end) if reader else ()
        mapped={a.key:targets(a) for a in entries}
        def order(a):
            spans=mapped[a.key]
            return (min((left for left,right,_,_ in spans if right>=reader.key(first).getIndex() and left<=reader.key(last).getIndex()),default=0) if reader else 0,bible_order(a))
        entries.sort(key=order)
        self.rows=[a.note for a in entries if a.note];self.marks=[a.mark for a in entries if a.mark]
        self.clear(self.list);self.cards=[];self._card_targets=[];self._chapter_texts={}
        for a in entries:
            if a.note:self.note_card(a.note,reader)
            else:self.highlight_card(a.mark,reader)
            card=self.cards[-1];card.annotation_key=a.key
            self._card_targets.append((card,mapped[a.key]))
        if tab:self.queue_follow(tab.state.reference)

    def queue_follow(self,reference):
        self.cancel_follow()
        if not self.following or self.editor or not hasattr(self,'scroll') or not self.owner.split.get_show_sidebar():return
        tab=self.owner.active_tab;reader=tab.reader if tab else None
        if not reader or not self._card_targets:return
        serial=self._follow_serial;stamp=self._stamp;attempts=0
        def reveal():
            nonlocal attempts
            self._follow_idle=0
            if (self.owner.closed or serial!=self._follow_serial or stamp!=self._stamp or not self.following
                    or self.editor or self.owner.active_tab is not tab or tab.state.reference!=reference
                    or self.owner.study.tool!='notes'):return False
            if not self.get_mapped() or any(card.get_height()==0 for card,_ in self._card_targets):
                attempts+=1
                if attempts<30:self._follow_idle=GLib.timeout_add(16,reveal)
                return False
            position=reader.key(reference).getIndex()
            candidates=[(card,spans) for card,spans in self._card_targets if spans]
            matching=[(card,spans) for card,spans in candidates if any(low<=position<=high for low,high,_,_ in spans)]
            if matching:card=matching[0][0]
            else:
                following=[(card,spans) for card,spans in candidates if min(low for low,_,_,_ in spans)>position]
                if following:card=following[0][0]
                elif candidates:
                    last_start=min(low for low,_,_,_ in candidates[-1][1])
                    card=next(c for c,spans in candidates if min(low for low,_,_,_ in spans)==last_start)
                else:return False
            # Keep the group header visible; a tall card remains freely scrollable.
            found,bounds=card.compute_bounds(self.scroll)
            if not found:return False
            adjustment=self.scroll.get_vadjustment();top=bounds.get_y();bottom=top+min(bounds.get_height(),80)
            height=self.scroll.get_height()
            target = adjustment.get_value()+top if top<0 else adjustment.get_value()+bottom-height if bottom>height else None
            if target is not None:
                self.motion.move(target, valid=lambda: not self.owner.closed and stamp==self._stamp
                                 and self.owner.active_tab is tab and self.following and not self.editor
                                 and self.owner.study.tool=='notes' and tab.state.reference==reference)
            return False
        self._follow_idle=GLib.idle_add(reveal)

    def card(self,system,start,end,kind):
        card=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        card.add_css_class('card');card.add_css_class('annotation-card')
        header=Gtk.Box(spacing=6)
        reference=Gtk.Label(label=passage_label(start,end,system),xalign=0,hexpand=True,wrap=True,
                            wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1)
        reference.add_css_class('caption')
        jump=Gtk.Button(child=reference,hexpand=True,tooltip_text=tr('Open in Bible'));jump.add_css_class('flat')
        jump.update_property([Gtk.AccessibleProperty.LABEL],[tr('Open in Bible')+': '+passage_label(start,end,system)])
        jump.connect('clicked',lambda *_:self.navigate_annotation(system,start));header.append(jump)
        menu=Gtk.MenuButton(icon_name='view-more-symbolic',tooltip_text=tr(kind))
        menu.add_css_class('flat');menu.update_property([Gtk.AccessibleProperty.LABEL],[tr(kind)])
        header.append(menu);card.append(header)
        card.actions=menu;self.list.append(card);self.cards.append(card)
        return card

    def navigate_annotation(self,system,start):
        tab=self.owner.active_tab;reader=tab.reader if tab else None
        if not reader:return
        try:
            from .reference_resolution import resolve
            mapped=resolve(start,system,reader)
            self.owner.navigate_selection(tab.state.resource,mapped.start)
        except (OSError,ValueError) as error:self.status.set_text(str(error))

    def excerpt(self,card,reader,system,start,end):
        texts=[];source=''
        if reader:
            try:
                refs=[]
                for _,_,first,last in self.annotations.positions(reader,system,start,end):
                    chapter=first.rsplit('.',1)[0]
                    if chapter not in self._chapter_texts:self._chapter_texts[chapter]=reader.chapter(first)
                    if len(self._chapter_texts)>64:self._chapter_texts.pop(next(iter(self._chapter_texts)))
                    for reference,text in self._chapter_texts[chapter].verses:
                        if reader.key(first).getIndex()<=reader.key(reference).getIndex()<=reader.key(last).getIndex() and text.strip():
                            refs.append(reference)
                from .sword_provider import passage_verses
                texts=list(passage_verses(reader,refs,self._chapter_texts))
                source=self.owner.library.resource(reader.name).description
            except (ValueError,OSError):texts=[]
        preview=Gtk.Label(label=' '.join(' '.join(text.split()) for _,text in texts) or tr('Bible excerpt unavailable.'),
                          xalign=0,yalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,lines=2,
                          ellipsize=Pango.EllipsizeMode.END,width_chars=1)
        preview.add_css_class('study-content')
        card.append(preview);card.excerpt=preview
        if texts:
            caption=Gtk.Label(label=source,xalign=0,ellipsize=Pango.EllipsizeMode.END,width_chars=1)
            caption.add_css_class('caption');caption.add_css_class('dim-label')
            caption.set_tooltip_text(source+' · '+passage_label(texts[0][0],texts[-1][0],reader.versification))
            card.append(caption)

    def note_card(self,note,reader):
        card=self.card(note.versification,note.start,note.end,'Note actions');card.note_id=note.id
        self.excerpt(card,reader,note.versification,note.start,note.end)
        card.append(Gtk.Separator())
        row=Gtk.Box(spacing=6);row.append(Gtk.Image(icon_name='bible-notes-symbolic',valign=Gtk.Align.START,pixel_size=16))
        preview=AnnotationPreview(self.owner,note,lambda:self.open_note(note));preview.set_hexpand(True)
        row.append(preview)
        open_button=Gtk.Button(icon_name='go-next-symbolic',tooltip_text=tr('Open note'),valign=Gtk.Align.START)
        open_button.add_css_class('flat');open_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Open note')])
        open_button.connect('clicked',lambda *_:self.open_note(note));row.append(open_button)
        card.append(row);card.preview=preview;card.open_button=open_button
        date,exact=readable_date(note.modified)
        meta=Gtk.Label(label=tr('Modified')+': '+date+((' · '+' · '.join(note.labels)) if note.labels else ''),xalign=0,wrap=True)
        meta.add_css_class('caption');meta.set_tooltip_text(exact);card.append(meta)
        pop=Gtk.Popover();actions=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,margin_top=8,margin_bottom=8,margin_start=8,margin_end=8)
        edit=Gtk.Button(label=tr('Expand note'))
        def expand(*_):pop.popdown();self.open_note(note,expand=True)
        edit.connect('clicked',expand);actions.append(edit)
        delete=Gtk.Button(label=tr('Delete note…'));delete.connect('clicked',lambda *_:self.delete_note(note,pop));actions.append(delete)
        pop.set_child(actions);card.actions.set_popover(pop)

    def highlight_card(self,mark,reader):
        card=self.card(mark['system'],mark['reference'],mark['reference'],'Highlight actions')
        card.highlight_key=(mark['system'],mark['reference']);card.add_css_class('highlight-'+mark['color'])
        kind=Gtk.Label(label=tr('Highlight')+' · '+tr(COLORS[mark['color']][1]),xalign=0,wrap=True)
        kind.add_css_class('caption');card.append(kind)
        self.excerpt(card,reader,mark['system'],mark['reference'],mark['reference'])
        self.colors(card.actions,mark=dict(mark))

    def open_note(self,note=None,context=None,expand=False):
        self.suspend_following()
        existing=self.owner.note_editor
        if existing and not existing.closed:
            if note and existing.note and existing.note.id==note.id:
                if expand and existing is self.editor and existing.embedded:self.expand_editor()
                else:existing.present();existing.body.grab_focus()
                return existing
            existing.after_close=lambda:self.open_note(note,context,expand)
            existing.close();return existing
        editor=NoteEditor(self.owner,note=note,context=context,embedded=True,compact=True)
        editor.embedded_host=self;self.editor=editor;self.owner.note_editor=editor
        self.clear(self.editor_panel)
        self.editor_panel.set_visible(True);self.editor_panel.append(editor.embedded_content)
        commands=Gtk.Box(spacing=6)
        save=Gtk.Button(label=tr('Save'));save.connect('clicked',lambda *_:editor.save());commands.append(save)
        cancel=Gtk.Button(icon_name='window-close-symbolic',tooltip_text=tr('Cancel'))
        cancel.update_property([Gtk.AccessibleProperty.LABEL],[tr('Cancel')])
        cancel.connect('clicked',lambda *_:editor.close());commands.append(cancel)
        expand_button=Gtk.Button(icon_name='view-fullscreen-symbolic',tooltip_text=tr('Expand note'))
        expand_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Expand note')])
        expand_button.connect('clicked',lambda *_:self.expand_editor());commands.append(expand_button)
        self.editor_commands=commands;self.editor_panel.prepend(commands)
        editor.body.grab_focus()
        if expand:self.expand_editor()
        return editor

    def add_note(self,*_):
        if self.context:return self.open_note(context=dict(self.context))

    def expand_editor(self):
        # Finish the activating key event before moving focus to a new window;
        # otherwise Space can also be inserted into the editor's buffer.
        GLib.idle_add(self._expand_editor,self.editor)

    def _expand_editor(self,editor):
        if not editor or self.editor is not editor or editor.closed or not editor.embedded:return
        self.editor_panel.remove(editor.embedded_content);self.editor_panel.set_visible(False)
        editor.stack.set_vexpand(True);editor.body_scroll.set_min_content_height(0)
        editor.body_scroll.set_max_content_height(-1);editor.body_scroll.set_propagate_natural_height(False);editor.body_scroll.set_vexpand(True)
        editor.embedded=False;editor.dialog_parent=editor
        editor.header.set_visible(True);editor.set_content(editor.embedded_content);editor.present()

    def editor_closed(self,editor):
        if editor.embedded_content.get_parent() is self.editor_panel:self.editor_panel.remove(editor.embedded_content)
        if self.editor is editor:
            self.editor=None;self.clear(self.editor_panel);self.editor_panel.set_visible(False)
        if not self.owner.closed:self.refresh(force=True)

    def delete_note(self,note,popover=None):
        if popover:popover.popdown()
        current=self.owner.note_editor
        if current and not current.closed and (not current.note or current.note.id!=note.id):
            current.after_close=lambda:self.delete_note(note);current.close();return
        editor=self.open_note(note)
        if editor.note and editor.note.id==note.id:editor.ask_delete()

    def colors(self,menu,*,mark=None,context=None,reader=None,annotate=False):
        popover=Gtk.Popover();box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4,
            margin_start=8,margin_end=8,margin_top=8,margin_bottom=8)
        if context:
            box.append(Gtk.Label(label=passage_label(context['start'],context['end'],context['versification']),wrap=True))
        for color in [*COLORS,None] if mark else COLORS:
            button=Gtk.Button(label=tr(COLORS[color][1] if color else 'Remove highlight'))
            def choose(_,value=color,snapshot=dict(mark) if mark else dict(context)):
                try:
                    if mark:system,refs,resource=snapshot['system'],[snapshot['reference']],snapshot['resource']
                    else:
                        system,resource=snapshot['versification'],snapshot['origin_translation']
                        key=reader.key(snapshot['start']);last=reader.key(snapshot['end']).getIndex();refs=[]
                        while key.getIndex()<=last:
                            if reader.has_reference(key.getOSISRef()):refs.append(key.getOSISRef())
                            if len(refs)>1000:raise ValueError('Select at most 1000 verses')
                            key.increment()
                            if key.popError()!='\x00':break
                    self.owner.highlights.set(system,refs,value,resource)
                    popover.popdown();self.owner.refresh_highlights()
                    if annotate:self.open_note(context=snapshot)
                except (OSError,ValueError) as error:self.status.set_text(str(error))
            button.connect('clicked',choose);box.append(button)
        popover.set_child(box);menu.set_popover(popover)
