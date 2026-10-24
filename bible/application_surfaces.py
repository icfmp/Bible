"""Shared global menu and native general preferences/help/about surfaces."""
from gi.repository import Adw, Gtk, Pango
from .i18n import tr


def application_menu():
    menu=Gtk.MenuButton(icon_name='open-menu-symbolic',tooltip_text=tr('Main menu'))
    menu.update_property([Gtk.AccessibleProperty.LABEL],[tr('Main menu')])
    popover=Gtk.Popover(halign=Gtk.Align.END)
    box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2,margin_top=6,margin_bottom=6,margin_start=6,margin_end=6)
    menu.global_actions=[]
    for label,action,icon,shortcut in [
        ('Library','translations','bible-library-symbolic','<Control>l'),
        ('Preferences','preferences','emblem-system-symbolic','<Control>comma'),
        ('Keyboard Shortcuts','shortcuts','preferences-desktop-keyboard-shortcuts-symbolic','<Control>question'),
        ('About Bible','about','help-about-symbolic','')]:
        if action=='about':box.append(Gtk.Separator(margin_top=6,margin_bottom=6))
        button=Gtk.Button(action_name='win.'+action)
        button.add_css_class('flat')
        row=Gtk.Box(spacing=12,margin_top=4,margin_bottom=4)
        row.append(Gtk.Image(icon_name=icon,pixel_size=16))
        row.append(Gtk.Label(label=tr(label),xalign=0,hexpand=True,wrap=True,wrap_mode=Pango.WrapMode.WORD_CHAR,width_chars=1,max_width_chars=20))
        if shortcut:
            key,modifiers=Gtk.accelerator_parse(shortcut)[-2:]
            hint=Gtk.Label(label=Gtk.accelerator_get_label(key,modifiers),halign=Gtk.Align.END)
            hint.add_css_class('caption');hint.add_css_class('dim-label');row.append(hint)
        button.set_child(row);button.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
        button.connect('clicked',lambda *_:popover.popdown())
        box.append(button);menu.global_actions.append(button)
    clamp=Adw.Clamp(maximum_size=320,tightening_threshold=320,unit=Adw.LengthUnit.PX);clamp.set_child(box)
    popover.set_child(clamp);menu.set_popover(popover)
    return menu


def show_preferences(owner):
    existing=getattr(owner,'preferences_window',None)
    if existing and existing.get_visible():
        existing.present(owner);return existing
    dialog=Adw.PreferencesDialog(title=tr('Preferences'),content_width=520,content_height=560,search_enabled=False)
    page=Adw.PreferencesPage()
    group=Adw.PreferencesGroup(title=tr('General'))
    status=Gtk.Label(wrap=True,xalign=0)
    settings=owner.application_settings
    def save(key,value):
        try:
            settings.set(key,value)
            if key=='interface_appearance':owner.reading_style.apply_mode()
            status.set_label(tr('Restart Bible to apply the application language.') if key=='ui_language' else '')
        except (OSError,ValueError) as error:status.set_label(tr('Unable to save application preferences.')+' '+str(error))
    def choice(title,key,values,description):
        row=Adw.PreferencesRow(title=tr(title),activatable=False)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=6,margin_top=12,margin_bottom=12,margin_start=12,margin_end=12)
        box.append(Gtk.Label(label=tr(title),xalign=0,wrap=True))
        hint=Gtk.Label(label=tr(description),xalign=0,wrap=True,max_width_chars=1)
        hint.set_max_width_chars(45);hint.add_css_class('dim-label');hint.add_css_class('caption');box.append(hint)
        control=Gtk.DropDown(model=Gtk.StringList.new([tr(label) for _,label in values]))
        control.update_property([Gtk.AccessibleProperty.LABEL],[tr(title)])
        control.set_selected([value for value,_ in values].index(settings.value[key]))
        control.connect('notify::selected',lambda widget,*_:save(key,values[widget.get_selected()][0]))
        box.append(control);row.set_child(box);group.add(row);return control
    dialog.language=choice('Application language','ui_language',[('system','System'),('fr','French'),('en','English')],
                          'Restart Bible to apply the application language.')
    dialog.appearance=choice('Interface appearance','interface_appearance',[('system','System'),('light','Light'),('dark','Dark')],
                            'Aa keeps its explicit reading palette; System follows this appearance.')
    row=Adw.SwitchRow(title=tr('Restore tabs at startup'),subtitle=tr('Applies at next launch. Your annotations and downloaded resources are kept.'),active=settings.value['restore_tabs'])
    row.connect('notify::active',lambda widget,*_:save('restore_tabs',widget.get_active()))
    dialog.restore_tabs=row;group.add(row);page.add(group)
    # Full annotation backup requires its own reviewed integration (#94).
    # Existing Notes backup routes remain available; do not mislabel their
    # note-only format as a complete personal-data backup.
    page.add(Adw.PreferencesGroup(description=tr('Reading appearance stays in Aa. Existing note backups remain available in My notes.')))
    feedback=Adw.PreferencesGroup();feedback.add(status);page.add(feedback)
    dialog.add(page);dialog.present(owner);owner.preferences_window=dialog
    return dialog


def show_shortcuts(owner):
    window=Gtk.ShortcutsWindow(transient_for=owner,modal=True,title=tr('Keyboard Shortcuts'))
    section=Gtk.ShortcutsSection(section_name='application',title=tr('Bible'))
    group=Gtk.ShortcutsGroup(title=tr('Reading and application'))
    for label,action in [
        ('Library','translations'),('Preferences','preferences'),('Keyboard Shortcuts','shortcuts'),
        ('New tab','new-tab'),('Close tab','close-tab'),('Choose a passage','choose-passage'),
        ('Reference','reference'),('Previous chapter','previous-chapter'),('Next chapter','next-chapter'),
        ('Previous verse','previous-verse'),('Next verse','next-verse'),
        ('History back','history-back'),('History forward','history-forward'),
        ('Study','study'),('Passage note','note'),('My notes','notes'),('Immersive mode','immersive')]:
        accelerators=owner.get_application().get_accels_for_action('win.'+action)
        if accelerators:group.add_shortcut(Gtk.ShortcutsShortcut(title=tr(label),accelerator=' '.join(accelerators)))
    section.add_group(group);window.add_section(section);window.present();owner.shortcuts_window=window
    return window


def show_about(owner):
    window=Adw.AboutWindow(transient_for=owner,modal=True,application_name='Bible',
        application_icon='io.github.icfmp.Bible',version='0.1.0-alpha',developer_name='Bible contributors',
        developers=['icfmp'],website='https://github.com/icfmp/Bible',
        issue_url='https://github.com/icfmp/Bible/issues',license_type=Gtk.License.GPL_2_0_ONLY,
        comments=tr('Read and study the Bible. Downloaded resources keep their own licenses.'))
    window.add_link(tr('Third-party notices'),'https://github.com/icfmp/Bible/blob/main/THIRD_PARTY_NOTICES.md')
    window.present();owner.about_window=window
    return window


def welcome_page(owner):
    view=Adw.ToolbarView();header=Adw.HeaderBar();owner.welcome_menu=application_menu();header.pack_end(owner.welcome_menu);view.add_top_bar(header)
    page=Adw.StatusPage(title=tr('Welcome to Bible'),description=tr('Choose a Bible to start reading and studying.'),icon_name='io.github.icfmp.Bible')
    box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=12,halign=Gtk.Align.CENTER)
    box.append(Gtk.Label(label=tr('Your downloaded texts stay available offline.'),wrap=True,max_width_chars=34,justify=Gtk.Justification.CENTER))
    choose=Gtk.Button(label=tr('Choose my Bible'));choose.add_css_class('suggested-action');choose.add_css_class('pill')
    choose.connect('clicked',lambda *_:owner.open_library('bible'))
    skip=Gtk.Button(label=tr('Later'));skip.add_css_class('flat');skip.connect('clicked',lambda *_:owner.main_pages.set_visible_child_name('reading'))
    box.append(choose);box.append(skip);page.set_child(box);view.set_content(page)
    owner.welcome_choose=choose;owner.welcome_skip=skip
    return view
