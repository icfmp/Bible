"""Full native reading preferences, sharing the express Aa state and renderer."""
from gi.repository import Adw,GLib,Gtk,Pango
from .i18n import tr
from .reading_metrics import SPACING,WIDTHS,line_spacing,text_width,side_margin


class ReadingSettings:
    def __init__(self,owner,dialog):
        self.owner=owner;self.dialog=dialog;self.syncing=True
        self.page=Adw.PreferencesPage(title=tr('Reading'),name='reading',icon_name='format-text-symbolic')
        self.families={family.get_name().casefold():family
                       for family in self.page.get_pango_context().get_font_map().list_families()}
        font=Adw.PreferencesGroup(title=tr('Font'));self.page.add(font)
        self.font=self.family(font,'Reading font','font')
        self.size=self.number(font,'Text size (pt)','size',12,64)
        study=Adw.PreferencesGroup(title=tr('Study content font'),description=tr('Notes, references and commentaries. Interface controls keep the system font.'))
        self.page.add(study);self.study_font=self.family(study,'Font family','study_font')
        row=Adw.ActionRow(title=tr('Use the default study font'),activatable=True)
        row.add_suffix(Gtk.Image(icon_name='edit-clear-symbolic'));row.connect('activated',lambda *_:self.update('study_font','sans-serif'));study.add(row)
        layout=Adw.PreferencesGroup(title=tr('Layout'));self.page.add(layout)
        self.line_spacing_px=self.number(layout,'Extra line spacing (px)','line_spacing_px',0,48)
        self.text_width_px=self.number(layout,'Maximum text width (px)','text_width_px',280,1440,10,
            'The window may make the text column narrower.')
        self.side_margin_px=self.number(layout,'Minimum scrolling margin (px)','side_margin_px',48,160,2,
            'Space at each side. Small windows may reduce it.')
        self.alignment=self.choice(layout,'Text alignment','alignment',[('left','Start of line'),('justified','Justified')])
        self.immersion_columns=self.choice(layout,'Immersive columns','immersion_columns',[('automatic','Automatic'),('one','One column')])
        colors=Adw.PreferencesGroup(title=tr('Colors'));self.page.add(colors)
        self.mode=self.choice(colors,'Reading mode','mode',[('system','System'),('day','Light'),('night','Dark')])
        self.palettes={}
        for key,title,values in [('day_palette','Day palettes',[('white','White'),('paper','Paper (sepia)')]),
                                  ('night_palette','Night palettes',[('dark','Dark grey'),('black','Black')])]:
            row=Adw.ActionRow(title=tr(title));box=Gtk.Box(spacing=6,homogeneous=True)
            group=None
            for value,label in values:
                button=Gtk.ToggleButton(tooltip_text=tr(label));content=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
                sample=Gtk.Label(label='Aa');sample.add_css_class('palette-preview-'+value)
                content.append(sample);content.append(Gtk.Label(label=tr(label),wrap=True));button.set_child(content)
                button.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
                if group:button.set_group(group)
                else:group=button
                button.connect('clicked',lambda _,k=key,v=value:self.update(k,v))
                box.append(button);self.palettes[value]=button
            row.add_suffix(box);colors.add(row)
        row=Adw.ActionRow(title=tr('Reset reading settings'),activatable=True)
        row.add_suffix(Gtk.Image(icon_name='edit-undo-symbolic'));row.connect('activated',lambda *_:owner.appearance.reset())
        reset=Adw.PreferencesGroup();reset.add(row);self.page.add(reset)
        self.status=Gtk.Label(xalign=0,wrap=True);status=Adw.PreferencesGroup();status.add(self.status);self.page.add(status)
        self.page.set_sensitive(owner.preferences.writable)
        self.sync()

    def family(self,group,title,key):
        row=Adw.ActionRow(title=tr(title))
        preview=Gtk.Label(ellipsize=Pango.EllipsizeMode.END,max_width_chars=22)
        chooser=Gtk.Button(child=preview,valign=Gtk.Align.CENTER)
        chooser._family_row=row;chooser._family_preview=preview
        native=Gtk.FontDialog(title=tr(title))
        def choose(*_):
            saved=getattr(self.owner.preferences.value,key)
            alias={'sans-serif':'Sans','sans':'Sans','serif':'Serif','monospace':'Monospace'}.get(saved.casefold(),saved)
            initial=self.families.get(alias.casefold())
            def chosen(dialog,result):
                try:family=dialog.choose_family_finish(result)
                except GLib.Error as error:
                    if error.code not in (Gtk.DialogError.DISMISSED,Gtk.DialogError.CANCELLED):
                        self.status.set_text(tr('Unable to open the font chooser.'))
                    return
                if family and not self.owner.closed and self.dialog.get_visible():self.update(key,family.get_name())
            native.choose_family(self.dialog.get_native(),initial,None,chosen)
        chooser.connect('clicked',choose)
        row.add_suffix(chooser);row.set_activatable_widget(chooser);group.add(row);return chooser

    def number(self,group,title,key,low,high,step=1,hint=None):
        row=Adw.SpinRow.new_with_range(low,high,step);row.set_title(tr(title))
        if hint:row.set_subtitle(tr(hint))
        row.connect('notify::value',lambda widget,*_:self.update(key,int(widget.get_value())))
        group.add(row);return row

    def choice(self,group,title,key,values):
        row=Adw.ComboRow(title=tr(title),model=Gtk.StringList.new([tr(label) for _,label in values]))
        row._reading_values=[value for value,_ in values]
        row.connect('notify::selected',lambda widget,*_:self.update(key,values[widget.get_selected()][0]) if widget.get_selected()<len(values) else None)
        group.add(row);return row

    def update(self,key,value):
        if self.syncing:return
        if key=='line_spacing_px':
            preset=next((name for name,number in SPACING.items() if number==value),None)
            if preset:key,value='line_spacing',preset
        elif key=='text_width_px':
            preset=next((name for name,number in WIDTHS.items() if number==value),None)
            if preset:key,value='column_width',preset
        # Commit the shared state immediately; coalesce expensive reflow into
        # one main-loop idle when a native numeric control emits several changes.
        self.owner.appearance.update(key,value,defer=True)
        self.status.set_text(self.owner.appearance.status.get_text());self.sync()

    def sync(self):
        self.syncing=True;p=self.owner.preferences.value
        self.sync_family(self.font,p.font);self.sync_family(self.study_font,p.study_font)
        self.size.set_value(p.size);self.line_spacing_px.set_value(line_spacing(p))
        self.text_width_px.set_value(text_width(p));self.side_margin_px.set_value(side_margin(p,66))
        for key in ('alignment','immersion_columns','mode'):
            row=getattr(self,key);row.set_selected(row._reading_values.index(getattr(p,key)))
        high=self.owner.reading_style.manager.get_high_contrast()
        for value,button in self.palettes.items():
            button.set_active(value in (p.day_palette,p.night_palette));button.set_sensitive(not high)
        self.syncing=False

    def sync_family(self,control,saved):
        alias={'sans-serif':'Sans','sans':'Sans','serif':'Serif','monospace':'Monospace'}.get(saved.casefold(),saved)
        family=self.families.get(alias.casefold())
        control._family_row.set_subtitle('' if family else
            tr('Unavailable font: {family}. A fallback is used.').format(family=saved))
        control._family_preview.set_text(family.get_name() if family else saved)
        attrs=Pango.AttrList();attrs.insert(Pango.attr_family_new(saved))
        control._family_preview.set_attributes(attrs);control.set_tooltip_text(saved)
