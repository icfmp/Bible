"""Explicit offline passage relationships; body citations are never auto-linked."""
import re
from gi.repository import Gtk,Pango
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
    def __init__(self,context,values,changed):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        self.context=context;self.values=tuple(values);self.changed=changed
        self.primary=PassageLink(context['versification'],context['start'],context['end'])
        self.expander=Gtk.Expander(label=tr('Linked passages'))
        self.rows=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4);self.expander.set_child(self.rows)
        row=Gtk.Box(spacing=6);self.expander.set_hexpand(True);row.append(self.expander)
        self.add_button=Gtk.MenuButton(icon_name='list-add-symbolic',tooltip_text=tr('Add a linked passage'),valign=Gtk.Align.START)
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
        self.error=Gtk.Label(wrap=True,max_width_chars=32,xalign=0);box.append(self.error)
        pop.set_child(box);self.add_button.set_popover(pop);row.append(self.add_button);self.append(row)
        self.refresh()

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
