"""Explicit offline passage relationships; body citations are never auto-linked."""
import re
from gi.repository import Gtk,Pango,GLib
from .i18n import tr
from .notes import PassageLink,validate_link,BOOK_ORDER
from .citations import grammar,fold


def parse_link(text,system):
    text=text.strip()
    canonical=re.fullmatch(r'([1-5]?[A-Za-z][A-Za-z0-9]*\.[0-9]+(?:_[0-9]+)?\.[0-9]+)(?:\s*[-–]\s*([1-5]?[A-Za-z][A-Za-z0-9]*\.[0-9]+(?:_[0-9]+)?\.[0-9]+))?',text)
    if canonical:start,end=canonical[1],canonical[2] or canonical[1]
    else:
        pattern,names=grammar();value=fold(text)[0];match=pattern.fullmatch(value)
        if not match:raise ValueError(tr('Enter a passage such as John 3:16–18.'))
        from .book_names import normalized
        book=names.get(normalized(match['name']))
        if not book:raise ValueError(tr('Enter a passage such as John 3:16–18.'))
        start=f'{book}.{match["chapter"]}.{match["verse"]}'
        end=f'{book}.{match["end_chapter"] or match["chapter"]}.{match["end_verse"] or match["verse"]}'
    link=validate_link(PassageLink(system,start,end))
    if start.split('.')[0] not in BOOK_ORDER:raise ValueError(tr('Unknown Bible book.'))
    return link


class PassageLinks(Gtk.Box):
    def __init__(self,owner,context,values,changed):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        self.owner=owner;self.context=context;self.values=tuple(values);self.changed=changed
        self._suggestion_epoch=0;self._suggestion_future=None
        self.primary=PassageLink(context['versification'],context['start'],context['end'])
        self.expander=Gtk.Expander(label=tr('Linked passages'))
        self.rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);self.expander.set_child(self.rows)
        row=Gtk.Box(spacing=6);self.expander.set_hexpand(True);row.append(self.expander)
        self.add_button=Gtk.MenuButton(label=tr('Add'),tooltip_text=tr('Add a linked passage'),valign=Gtk.Align.START)
        self.add_button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Add a linked passage')])
        pop=Gtk.Popover();box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6,
            margin_start=12,margin_end=12,margin_top=12,margin_bottom=12)
        self.entry=Gtk.Entry(placeholder_text=tr('John 3:16–18'),width_chars=18)
        self.entry.update_property([Gtk.AccessibleProperty.LABEL],[tr('Linked passage')])
        self.entry.connect('activate',lambda *_:self.add());box.append(self.entry)
        hint=Gtk.Label(label=tr('Numbering follows the original passage. Availability is checked when opening.'),
            wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,max_width_chars=32,xalign=0)
        hint.add_css_class('caption');box.append(hint)
        add=Gtk.Button(label=tr('Add'));add.connect('clicked',lambda *_:self.add());box.append(add)
        self.suggestions=Gtk.Expander(label=tr('Suggested passages'),visible=False)
        self.suggestion_rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        suggestions_scroll=Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
            max_content_height=180,propagate_natural_height=True)
        suggestions_scroll.set_child(self.suggestion_rows);self.suggestions.set_child(suggestions_scroll);box.append(self.suggestions)
        self.error=Gtk.Label(wrap=True,max_width_chars=32,xalign=0);box.append(self.error)
        outer=Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
            max_content_height=max(160,min(420,owner.get_height()-100)),propagate_natural_height=True)
        outer.set_child(box);pop.set_child(outer);self.add_button.set_popover(pop);row.append(self.add_button);self.append(row)
        def shown(*_):
            root=self.get_root() or owner
            outer.set_max_content_height(max(120,min(420,root.get_height()-100)))
            outer.set_propagate_natural_width(True);outer.set_min_content_width(-1)
            outer.set_max_content_width(max(160,min(340,root.get_width()-64)))
            outer.set_min_content_width(max(160,min(280,root.get_width()-64)))
            self.load_suggestions(pop)
        pop.connect('show',shown)
        def hidden(*_):
            self._suggestion_epoch+=1
            if self._suggestion_future:self._suggestion_future.cancel();self._suggestion_future=None
        pop.connect('unmap',hidden)
        self.refresh()

    def load_suggestions(self,pop):
        """Optional existing reference data; manual entry never waits on it."""
        self._suggestion_epoch+=1;epoch=self._suggestion_epoch
        if self._suggestion_future:self._suggestion_future.cancel()
        self.suggestions.set_visible(False)
        while self.suggestion_rows.get_first_child():self.suggestion_rows.remove(self.suggestion_rows.get_first_child())
        panel=self.owner.study.references
        if panel.data.revision is None or self.context['origin_translation'] not in self.owner.library.installed('bible'):return
        try:
            from .sword_provider import Reader
            from .reference_targets import source_references
            reader=Reader(self.owner.library.root/self.context['origin_translation'],self.context['origin_translation'])
            if reader.versification!=self.context['versification']:return
            origins=source_references(reader,self.primary.start,self.primary.end)
        except (ValueError,OSError,RuntimeError):return
        future=panel.executor.submit(panel.data.query,origins);self._suggestion_future=future
        def complete():
            if self.owner.closed or epoch!=self._suggestion_epoch or not pop.get_visible():return False
            self._suggestion_future=None
            try:rows=future.result()
            except (ValueError,OSError,RuntimeError):return False
            from .reference_targets import local_target_ranges
            from .notes_window import passage_label
            choices=[]
            for result in rows:
                try:ranges=local_target_ranges(reader,result.start,result.end)
                except ValueError:continue
                for start,end in ranges:
                    link=PassageLink(reader.versification,start,end)
                    if link!=self.primary and link not in self.values and link not in choices:choices.append(link)
                if len(choices)>=8:break
            for link in choices[:8]:
                button=Gtk.Button(child=Gtk.Label(label=passage_label(link.start,link.end,link.versification),
                    xalign=0,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1))
                button.add_css_class('flat')
                def choose(*_,value=link):
                    self.entry.set_text(value.start+('–'+value.end if value.end!=value.start else ''));self.add()
                button.connect('clicked',choose);button._linked_passage=link;self.suggestion_rows.append(button)
            if choices:
                from .reference_data import SOURCE_URL,LICENSE_URL
                from .source_credit import source_credit
                self.suggestion_rows.append(source_credit('OpenBible.info · CC BY 4.0\n'+SOURCE_URL+'\n'+LICENSE_URL))
                self.suggestions.set_visible(True)
            return False
        future.add_done_callback(lambda _:GLib.idle_add(complete))

    def refresh(self):
        from .notes_window import passage_label
        while self.rows.get_first_child():self.rows.remove(self.rows.get_first_child())
        for link in self.values:
            row=Gtk.Box(spacing=6)
            label=Gtk.Label(label=passage_label(link.start,link.end,link.versification),xalign=0,
                wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,hexpand=True)
            row.append(label)
            remove=Gtk.Button(icon_name='list-remove-symbolic',tooltip_text=tr('Remove linked passage'))
            remove.add_css_class('flat');remove.update_property([Gtk.AccessibleProperty.LABEL],[tr('Remove linked passage')+': '+label.get_text()])
            remove.connect('clicked',lambda *_,value=link:self.remove(value));row.append(remove);self.rows.append(row)
        self.expander.set_label(tr('Linked passages')+(f' ({len(self.values)})' if self.values else ''))
        self.expander.set_sensitive(bool(self.values))

    def add(self):
        try:
            link=parse_link(self.entry.get_text(),self.context['versification'])
            if link==self.primary or link in self.values:
                self.error.set_text(tr('This passage is already linked.'));return False
            if len(self.values)>=200:raise ValueError(tr('Too many linked passages'))
            self.values=(*self.values,link);self.entry.set_text('');self.error.set_text('')
            self.refresh();self.expander.set_expanded(True);self.add_button.popdown();self.changed();return True
        except ValueError as error:self.error.set_text(tr(str(error)));return False

    def remove(self,link):
        self.values=tuple(value for value in self.values if value!=link);self.refresh();self.changed()
