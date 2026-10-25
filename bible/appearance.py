"""Compact EPUB-style reader settings; immediate, local and shared by tabs."""
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Pango
from .i18n import tr
from .preferences import ReadingPreferences


class AppearancePopover(Gtk.Popover):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self._syncing = False
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                    max_content_height=620, propagate_natural_height=True)
        self.controls = box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                                     margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        scroll.set_child(box)
        title = Gtk.Label(label=tr('Reading appearance'),wrap=True);title.add_css_class('heading');box.append(title)
        self.fonts = {}
        fonts = Gtk.Box(spacing=6, homogeneous=True)
        for family, label in [('DejaVu Serif', 'Book'), ('DejaVu Sans', 'Simple')]:
            button = Gtk.ToggleButton(tooltip_text=tr('Reading font')+': '+family)
            if self.fonts:button.set_group(next(iter(self.fonts.values())))
            preview = Gtk.Label(label=tr(label))
            attrs = Pango.AttrList();attrs.insert(Pango.attr_family_new(family));preview.set_attributes(attrs)
            button.set_child(preview)
            button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Reading font')+': '+tr(label)])
            button.connect('clicked',lambda _, name=family:self.update('font',name))
            fonts.append(button);self.fonts[family]=button
        box.append(fonts)
        self.font_name=Gtk.Label(wrap=True,max_width_chars=28,xalign=0)
        box.append(self.font_name)
        size_row=Gtk.Box(spacing=8)
        self.smaller=Gtk.Button(label='A−',tooltip_text=tr('Decrease text size'))
        self.larger=Gtk.Button(label='A+',tooltip_text=tr('Increase text size'))
        self.smaller.update_property([Gtk.AccessibleProperty.LABEL],[tr('Decrease text size')])
        self.larger.update_property([Gtk.AccessibleProperty.LABEL],[tr('Increase text size')])
        self.smaller.connect('clicked',lambda *_:self.step_size(-1))
        self.larger.connect('clicked',lambda *_:self.step_size(1))
        self.size=Gtk.Label(hexpand=True)
        self.size.update_property([Gtk.AccessibleProperty.LABEL],[tr('Text size')])
        for widget in [self.smaller,self.size,self.larger]:size_row.append(widget)
        box.append(size_row)
        self.mode=self.choice(box,'Reading mode','mode',[('system','System'),('day','Light'),('night','Dark')])
        self.palettes={};self.palette_rows={}
        for group,label,options in [('day_palette','Day palettes',[('white','White'),('paper','Paper (sepia)')]),
                                    ('night_palette','Night palettes',[('dark','Dark grey'),('black','Black')])]:
            row=Gtk.Box(spacing=6,homogeneous=True)
            self.palette_rows[group]=row
            group_button=None
            for key,title in options:
                button=Gtk.ToggleButton(tooltip_text=tr(title))
                button.set_child(Gtk.Label(label=tr(title),wrap=True,max_width_chars=12))
                if group_button:button.set_group(group_button)
                else:group_button=button
                button.add_css_class('palette-'+key)
                button.update_property([Gtk.AccessibleProperty.LABEL],[tr(title)+': '+tr(label)])
                button.connect('clicked',lambda _,attr=group,value=key:self.update(attr,value))
                self.palettes[key]=button;row.append(button)
            box.append(row)
        self.system_status=Gtk.Label(wrap=True,max_width_chars=28,xalign=0)
        box.append(self.system_status)
        layout_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6)
        box.append(Gtk.Separator());box.append(layout_box)
        self.line_spacing=self.choice(layout_box,'Line spacing','line_spacing',[('tight','Tight'),('normal','Normal'),('airy','Airy'),('very-airy','Very airy')])
        self.column_width=self.choice(layout_box,'Text width','column_width',[('narrow','Narrow'),('normal','Normal'),('wide','Wide')])
        box.append(Gtk.Separator())
        for attr,label in [('chapter_numbers','Chapter numbers'),('verse_numbers','Verse numbers'),('show_highlights','Show highlights'),
                           ('note_indicators','Show note indicators'),('place_markers','Show place markers')]:
            row=Gtk.Box(spacing=12)
            row.append(Gtk.Label(label=tr(label),xalign=0,hexpand=True,wrap=True))
            button=Gtk.Switch(valign=Gtk.Align.CENTER)
            button.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
            button.connect('notify::active',lambda widget,_,key=attr:self.update(key,widget.get_active()))
            row.append(button);setattr(self,attr,button);box.append(row)
        reset=Gtk.Button(child=Gtk.Label(label=tr('Reset reading settings'),wrap=True))
        reset.add_css_class('flat');reset.connect('clicked',lambda *_:self.reset());box.append(reset)
        self.status=Gtk.Label(wrap=True,max_width_chars=28,xalign=0,label=owner.preferences.error)
        box.append(self.status)
        if not owner.preferences.writable:box.set_sensitive(False)
        box.set_size_request(292,-1)
        self.set_child(scroll)
        def shown(*_):
            anchor=self.get_parent()
            found,bounds=anchor.compute_bounds(owner)
            below=owner.get_height()-(bounds.origin.y+bounds.size.height)-44 if found else owner.get_height()-100
            scroll.set_max_content_height(max(120,min(620,int(below))))
            from .popover_dismissal import fit_reader_popover
            fit_reader_popover(self,owner)
        self.connect('show',shown)
        self.sync()

    def choice(self,parent,label,attribute,values):
        row=Gtk.Box(spacing=8)
        row.append(Gtk.Label(label=tr(label),xalign=0,hexpand=True,wrap=True))
        button=Gtk.DropDown(model=Gtk.StringList.new([tr(title) for _,title in values]))
        button.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
        button.connect('notify::selected',lambda widget,*_:self.update(attribute,values[widget.get_selected()][0]) if widget.get_selected()<len(values) else None)
        row.append(button);parent.append(row);return button

    def step_size(self,delta):
        self.update('size',max(12,min(64,self.owner.preferences.value.size+delta)))

    def sync(self):
        self._syncing=True
        p=self.owner.preferences.value
        for family,button in self.fonts.items():button.set_active(p.font==family)
        self.font_name.set_text(p.font);self.font_name.set_visible(p.font not in self.fonts)
        self.size.set_text(f'{p.size} pt')
        self.size.update_property([Gtk.AccessibleProperty.LABEL],[f'{tr("Text size")}: {p.size} pt (12–64)'])
        self.smaller.set_sensitive(p.size>12);self.larger.set_sensitive(p.size<64)
        for attr,values in [('mode',['system','day','night']),('line_spacing',['tight','normal','airy','very-airy']),('column_width',['narrow','normal','wide'])]:
            getattr(self,attr).set_selected(values.index(getattr(p,attr)))
        for key,button in self.palettes.items():button.set_active(key in (p.day_palette,p.night_palette))
        self.chapter_numbers.set_active(p.chapter_numbers);self.verse_numbers.set_active(p.verse_numbers)
        self.show_highlights.set_active(p.show_highlights)
        self.note_indicators.set_active(p.note_indicators);self.place_markers.set_active(p.place_markers)
        self.sync_system();self._syncing=False

    def sync_system(self):
        high=self.owner.reading_style.manager.get_high_contrast()
        self.system_status.set_text(tr('Colors follow the system high contrast setting.') if high else '')
        self.system_status.set_visible(high)
        for button in self.palettes.values():button.set_sensitive(not high)
        dark=self.owner.reading_style.dark
        self.palette_rows['day_palette'].set_visible(not dark)
        self.palette_rows['night_palette'].set_visible(dark)

    def reset(self):
        if self._syncing:return
        self.owner.reading_style.remember_tab_palettes()
        # Retain the shared instance already held by all reading tabs.
        for key,value in vars(ReadingPreferences()).items():setattr(self.owner.preferences.value,key,value)
        if self.owner.active_tab:self.owner.active_tab.state.reading_palette=self.owner.reading_style.palette_settings()
        self.persist()

    def update(self,key,value):
        if self._syncing:return
        if key in {'mode','day_palette','night_palette'}:
            self.owner.reading_style.remember_tab_palettes()
        setattr(self.owner.preferences.value,key,value)
        if key in {'mode','day_palette','night_palette'} and self.owner.active_tab:
            self.owner.active_tab.state.reading_palette=self.owner.reading_style.palette_settings()
        self.persist(reflow=key not in {'mode','day_palette','night_palette','show_highlights'})

    def persist(self,reflow=True):
        try:
            self.owner.preferences.save();self.owner.apply_appearance(reflow=reflow);self.status.set_text('')
        except (OSError,ValueError) as error:self.status.set_text(str(error))
        self.sync()
