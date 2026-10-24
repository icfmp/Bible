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
    window=Adw.PreferencesWindow(transient_for=owner,modal=True,title=tr('Preferences'),default_width=520,default_height=420)
    page=Adw.PreferencesPage()
    group=Adw.PreferencesGroup(title=tr('Library'),description=tr('Choose which resources appear first. Reading appearance remains in Aa.'))
    from .language_picker import LanguagePicker
    row=Adw.ActionRow(title=tr('Preferred resource language'))
    def changed():
        try:
            owner.application_settings.set('library_language',picker.codes[picker.get_selected()])
            dialog=owner.catalogue_window
            if dialog and not dialog.closed:
                dialog.language_choice=owner.application_settings.language;dialog.update_languages()
        except (OSError,ValueError) as error:owner.report_session_error(tr('Unable to save application preferences.'),error)
    picker=LanguagePicker(changed);picker.set_valign(Gtk.Align.CENTER)
    # Reuse worker-prepared catalogue names when available. The full ISO inventory
    # is populated asynchronously through the shared Library service.
    from .catalogue_session import CatalogueSession
    if not getattr(owner,'catalogue_session',None):owner.catalogue_session=CatalogueSession(owner.library)
    session=owner.catalogue_session
    picker.prepare_languages=session.load_languages
    picker.set_codes(['',owner.application_settings.language] if owner.application_settings.language else [''])
    picker.selected=1 if owner.application_settings.language else 0
    picker.set_label(picker.name(owner.application_settings.language))
    def apply(snapshot):
        from gi.repository import GLib
        def update():
            if not window.get_visible():return False
            from .languages import canonical_language
            current=canonical_language(owner.application_settings.language)
            codes=['']+sorted(({canonical_language(code) for code in snapshot.languages}|{'en','fr',current})-{''})
            picker.set_codes(codes,snapshot.languages)
            picker.selected=codes.index(current);picker.set_label(picker.name(current))
            return False
        GLib.idle_add(update)
    # WeakMethod subscriptions need a bound owner; retain it only for this dialog.
    class Listener:
        def ready(self,snapshot):apply(snapshot)
    listener=Listener();window._language_listener=listener;session.subscribe(listener.ready)
    window.connect('close-request',lambda *_:session.unsubscribe(listener.ready) or False)
    row.add_suffix(picker);group.add(row)
    auto=Adw.SwitchRow(title=tr('Refresh catalogues automatically'),subtitle=tr('Check metadata when Library opens. Resource texts download only on request.'),active=owner.application_settings.value['automatic_catalogue_refresh'])
    def toggled(widget,*_):
        try:owner.application_settings.set('automatic_catalogue_refresh',widget.get_active())
        except (OSError,ValueError) as error:owner.report_session_error(tr('Unable to save application preferences.'),error)
    auto.connect('notify::active',toggled);group.add(auto);page.add(group);window.add(page)
    window.present();owner.preferences_window=window
    return window


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
