"""Compact EPUB-style reader settings; immediate, local and shared by tabs."""
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Pango, GLib, Adw
from .i18n import tr
from .preferences import ReadingPreferences


class AppearancePopover(Gtk.Popover):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self._syncing = False
        self._apply_id=0;self._pending_reflow=False
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                    max_content_height=620, propagate_natural_height=True,
                                    propagate_natural_width=True)
        self.scroll=scroll
        self.controls = box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                                     margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        self.width_clamp=Adw.Clamp(child=box,maximum_size=320,tightening_threshold=320,unit=Adw.LengthUnit.PX)
        scroll.set_child(self.width_clamp)
        title = Gtk.Label(label=tr('Reading appearance'),wrap=True,width_chars=1,wrap_mode=Pango.WrapMode.WORD_CHAR);title.add_css_class('heading');box.append(title)
        self.fonts = {}
        fonts = Gtk.Box(spacing=6, homogeneous=True)
        for style, label in [('book', 'Book'), ('simple', 'Simple')]:
            family=getattr(owner.preferences.value,'serif_font' if style=='book' else 'sans_font')
            button = Gtk.ToggleButton(tooltip_text=tr('Reading font')+': '+family)
            if self.fonts:button.set_group(next(iter(self.fonts.values())))
            preview = Gtk.Label(label=tr(label))
            attrs = Pango.AttrList();attrs.insert(Pango.attr_family_new(family));preview.set_attributes(attrs)
            button.set_child(preview)
            button.update_property([Gtk.AccessibleProperty.LABEL],[tr('Reading font')+': '+tr(label)])
            button.connect('clicked',lambda _, name=style:self.update('font_style',name))
            fonts.append(button);self.fonts[style]=button
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
        from .segmented_choice import SegmentedChoice
        self.mode=SegmentedChoice([tr(label) for label in ('System','Light','Dark')])
        self.mode.update_property([Gtk.AccessibleProperty.LABEL],[tr('Reading mode')])
        self.mode.connect('changed',lambda widget,*_:self.update('mode',('system','day','night')[widget.get_selected()]))
        box.append(self.mode)
        self.palettes={};self.palette_rows={}
        for group,label,options in [('day_palette','Day palettes',[('white','White'),('paper','Paper (sepia)')]),
                                    ('night_palette','Night palettes',[('dark','Dark grey'),('black','Black')])]:
            row=Gtk.Box(spacing=6,homogeneous=True)
            self.palette_rows[group]=row
            group_button=None
            for key,title in options:
                button=Gtk.ToggleButton(tooltip_text=tr(title))
                button.set_child(Gtk.Label(label=tr(title),wrap=True,width_chars=1,max_width_chars=12,wrap_mode=Pango.WrapMode.WORD_CHAR))
                if group_button:button.set_group(group_button)
                else:group_button=button
                button.add_css_class('palette-'+key)
                button.update_property([Gtk.AccessibleProperty.LABEL],[tr(title)+': '+tr(label)])
                button.connect('clicked',lambda _,attr=group,value=key:self.update(attr,value))
                self.palettes[key]=button;row.append(button)
            box.append(row)
        self.system_status=Gtk.Label(wrap=True,max_width_chars=28,xalign=0)
        box.append(self.system_status)
        box.append(Gtk.Separator())
        self.visible_elements=Gtk.Expander(label=tr('Visible elements'),expanded=owner.preferences.value.visible_elements_expanded)
        self.visible_elements.connect('notify::expanded',lambda widget,*_:self.update('visible_elements_expanded',widget.get_expanded()))
        visible_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.visible_elements.set_child(visible_box);box.append(self.visible_elements)
        for attr,label in [('chapter_numbers','Chapter headings'),('verse_numbers','Verse numbers'),('show_highlights','Show highlights'),
                           ('note_indicators','Show note indicators'),('place_markers','Show place markers')]:
            row=Gtk.Box(spacing=12)
            row.append(Gtk.Label(label=tr(label),xalign=0,hexpand=True,wrap=True,width_chars=1,wrap_mode=Pango.WrapMode.WORD_CHAR))
            button=Gtk.Switch(valign=Gtk.Align.CENTER)
            button.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
            button.connect('notify::active',lambda widget,_,key=attr:self.update(key,widget.get_active()))
            row.append(button);setattr(self,attr,button);visible_box.append(row)
        advanced=Gtk.Button(child=Gtk.Label(label=tr('More reading settings…'),wrap=True,
            width_chars=1,wrap_mode=Pango.WrapMode.WORD_CHAR))
        def open_settings(*_):
            self.popdown()
            from .application_surfaces import show_preferences
            dialog=show_preferences(owner);dialog.set_visible_page(dialog.reading_settings.page)
        advanced.add_css_class('flat');advanced.connect('clicked',open_settings);box.append(advanced)
        self.status=Gtk.Label(wrap=True,max_width_chars=28,xalign=0,label=owner.preferences.error)
        box.append(self.status)
        if not owner.preferences.writable:box.set_sensitive(False)
        self.set_child(scroll)
        def shown(*_):
            anchor=self.get_parent()
            found,bounds=anchor.compute_bounds(owner)
            below=owner.get_height()-(bounds.origin.y+bounds.size.height)-44 if found else owner.get_height()-100
            scroll.set_max_content_height(max(120,min(620,int(below))))
            width=max(180,min(320,owner.get_width()-40))
            self.width_clamp.set_maximum_size(width);self.width_clamp.set_tightening_threshold(width)
            scroll.set_min_content_width(-1);scroll.set_max_content_width(width);scroll.set_min_content_width(width)
            # Keep all three direct choices at large UI text sizes. Native
            # symbolic controls retain their localized labels and tooltips.
            modes=[('System','computer-symbolic'),('Light','weather-clear-symbolic'),('Dark','weather-clear-night-symbolic')]
            for button,(label,_) in zip(self.mode.buttons,modes):button.set_label(tr(label))
            if self.mode.measure(Gtk.Orientation.HORIZONTAL,-1)[0]>width-24:
                for button,(label,icon) in zip(self.mode.buttons,modes):
                    button.set_child(Gtk.Image(icon_name=icon,pixel_size=20));button.set_tooltip_text(tr(label))
                    button.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
            from .popover_dismissal import fit_reader_popover
            fit_reader_popover(self,owner)
        self.connect('show',shown)
        self.sync()

    def choice(self,parent,label,attribute,values):
        row=Gtk.Box(spacing=8)
        row.append(Gtk.Label(label=tr(label),xalign=0,hexpand=True,wrap=True))
        button=Gtk.DropDown(model=Gtk.StringList.new([tr(title) for _,title in values]))
        button._preset_titles=[tr(title) for _,title in values]
        button.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
        button.connect('notify::selected',lambda widget,*_:self.update(attribute,values[widget.get_selected()][0]) if widget.get_selected()<len(values) else None)
        row.append(button);parent.append(row);return button

    def step_size(self,delta):
        self.update('size',max(12,min(64,self.owner.preferences.value.size+delta)))

    def sync(self):
        self._syncing=True
        p=self.owner.preferences.value
        for style,button in self.fonts.items():
            family=p.serif_font if style=='book' else p.sans_font
            button.set_active(p.font_style==style);button.set_tooltip_text(tr('Reading font')+': '+family)
            attrs=Pango.AttrList();attrs.insert(Pango.attr_family_new(family));button.get_child().set_attributes(attrs)
        self.font_name.set_visible(False)
        self.visible_elements.set_expanded(p.visible_elements_expanded)
        self.size.set_text(f'{p.size} pt')
        self.size.update_property([Gtk.AccessibleProperty.LABEL],[f'{tr("Text size")}: {p.size} pt (12–64)'])
        self.smaller.set_sensitive(p.size>12);self.larger.set_sensitive(p.size<64)
        self.mode.set_selected(['system','day','night'].index(p.mode))
        for key,button in self.palettes.items():button.set_active(key in (p.day_palette,p.night_palette))
        self.chapter_numbers.set_active(p.chapter_numbers);self.verse_numbers.set_active(p.verse_numbers)
        self.show_highlights.set_active(p.show_highlights)
        self.note_indicators.set_active(p.note_indicators);self.place_markers.set_active(p.place_markers)
        self.sync_system();self._syncing=False
        dialog=getattr(self.owner,'preferences_window',None)
        if dialog and dialog.get_visible() and hasattr(dialog,'reading_settings'):dialog.reading_settings.sync()

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

    def update(self,key,value,*,defer=False):
        if self._syncing:return
        if key in {'mode','day_palette','night_palette'}:
            self.owner.reading_style.remember_tab_palettes()
        setattr(self.owner.preferences.value,key,value)
        p=self.owner.preferences.value
        if key=='font_style':p.font=p.serif_font if value=='book' else p.sans_font
        elif key in ('serif_font','sans_font'):
            if (key=='serif_font')==(p.font_style=='book'):p.font=value
        elif key=='font':
            # Preserve callers of the original reading-font preference.
            setattr(p,'serif_font' if p.font_style=='book' else 'sans_font',value)
        if key=='line_spacing':self.owner.preferences.value.line_spacing_px=None
        if key=='column_width':self.owner.preferences.value.text_width_px=None
        if key in {'mode','day_palette','night_palette'} and self.owner.active_tab:
            self.owner.active_tab.state.reading_palette=self.owner.reading_style.palette_settings()
        self.persist(reflow=key not in {'mode','day_palette','night_palette','show_highlights','study_font','study_size','visible_elements_expanded'},defer=defer)

    def cancel_pending(self):
        if self._apply_id:GLib.source_remove(self._apply_id)
        reflow=self._pending_reflow;self._apply_id=0;self._pending_reflow=False
        return reflow

    def apply_pending(self):
        reflow=self._pending_reflow;self._apply_id=0;self._pending_reflow=False
        if not self.owner.closed:self.owner.apply_appearance(reflow=reflow)
        return False

    def persist(self,reflow=True,*,defer=False):
        try:
            self.owner.preferences.save()
            if defer:
                self._pending_reflow|=reflow
                if not self._apply_id:self._apply_id=GLib.idle_add(self.apply_pending)
            else:self.owner.apply_appearance(reflow=self.cancel_pending() or reflow)
            self.status.set_text('')
        except (OSError,ValueError) as error:self.status.set_text(str(error))
        self.sync()
