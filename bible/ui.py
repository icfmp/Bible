"""Native tabbed GNOME reader; downloads live in a dedicated window."""
from pathlib import Path

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gio, GLib, Gtk, Pango  # noqa: E402

from .catalogue_window import CatalogueWindow
from .providers import module_name
from .i18n import tr
from .library import Library
from .reading_tab import ReadingTab
from .study_panel import StudyPanel
from .navigation import PassagePopover
from .notes import NoteStore
from .preferences import Preferences
from .appearance import AppearancePopover
from .reading_style import ReadingStyle
from .reading_sync import ReadingSync
from .immersion import Immersion
from .immersion_hints import ImmersionHints
from .pagination import Anchor
from .paged_sources import BibleBookPages, CommentaryPages
from .highlights import HighlightStore,COLORS
from .notes_window import NoteEditor, NotesWindow, NotesSpace
from .session import Session, SessionError, SessionStore, TabState


class Window(Adw.ApplicationWindow):
    def __init__(self, app, library, session_path=None):
        super().__init__(application=app, title='Bible', default_width=960, default_height=700)
        self.set_size_request(360, 320)
        self.library = library
        from .application_settings import ApplicationSettings
        if not hasattr(app,'_application_settings'):app._application_settings={}
        key=library.root.parent.resolve()
        if key not in app._application_settings:app._application_settings[key]=ApplicationSettings(key)
        self.application_settings=app._application_settings[key]
        self.application_settings.first_launch=False
        self.store = SessionStore(session_path or library.root.parent / 'session.json')
        self.preferences = Preferences(library.root.parent / 'reading-preferences.json')
        from .study_settings import StudySettings
        self.study_settings = StudySettings(library.root.parent / 'study-preferences.json')
        self._study_resizing = False
        from weakref import WeakValueDictionary
        if not hasattr(app,'_highlight_stores'):app._highlight_stores=WeakValueDictionary()
        path=(library.root.parent/'highlights.json').resolve()
        self.highlights=app._highlight_stores.get(path)
        if self.highlights is None:
            self.highlights=HighlightStore(path);app._highlight_stores[path]=self.highlights
        self.highlights_window=None
        self.reading_style = ReadingStyle(self)
        self.closed = False
        self.immersion=None;self._immersion_help_seen=False
        self.immersion_hints=ImmersionHints(library.root.parent/'immersion-help.json')
        self._initializing = True
        self._syncing_study = False
        self._save_id = 0
        self._session_writable = True
        self.catalogue_window = None
        self.notes_window = None
        self.notes_space = None
        self.note_editor = None
        self.notes_error = ''
        try:
            self.notes_store = NoteStore(library.root.parent / 'notes.sqlite3')
            from .personal_backup import recover
            recover(self.notes_store,self.highlights)
        except Exception as error:
            if getattr(self,'notes_store',None):self.notes_store.close()
            self.notes_store = None
            self.notes_error = str(error)
        self.connect('close-request', self.on_close)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        header = Adw.HeaderBar()
        header.set_centering_policy(Adw.CenteringPolicy.LOOSE)
        self.heading = Adw.WindowTitle(title=tr('Choose a passage'))
        # Bound both title and version even with long affiliated module IDs.
        def constrain_labels(widget,maximum=18):
            if isinstance(widget,Gtk.Label):
                widget.set_max_width_chars(maximum);widget.set_width_chars(1);widget.set_ellipsize(Pango.EllipsizeMode.END)
            child=widget.get_first_child()
            while child:
                constrain_labels(child,maximum);child=child.get_next_sibling()
        constrain_labels(self.heading)
        heading_box = Gtk.Box(spacing=4)
        heading_box.append(self.heading)
        heading_box.append(Gtk.Image(icon_name='pan-down-symbolic'))
        self.passage_button = Gtk.MenuButton(child=heading_box, tooltip_text=tr('Choose a passage'))
        self.passage_button.add_css_class('flat')
        self.navigation = PassagePopover(self)
        self.passage_button.set_popover(self.navigation)
        header.set_title_widget(self.passage_button)
        from .workspace_selector import WorkspaceSelector
        self.space_selector=WorkspaceSelector(self);header.pack_start(self.space_selector)
        new = Gtk.Button(icon_name='tab-new-symbolic', tooltip_text=tr('New tab'),
                         action_name='win.new-tab')
        self.new_tab_button=new
        header.pack_start(new)
        from .application_surfaces import application_menu
        self.menu=application_menu()
        self.study_button=Gtk.ToggleButton(icon_name='sidebar-show-right-symbolic',tooltip_text=tr('Study'))
        self.study_button.connect('toggled',self.toggle_study)
        self.immersive_button=Gtk.ToggleButton(icon_name='view-fullscreen-symbolic',tooltip_text=tr('Immersive mode'))
        self.immersive_button.connect('clicked',lambda *_:self.toggle_immersion())
        self.appearance_button=Gtk.MenuButton(child=Gtk.Label(label='Aa'),tooltip_text=tr('Reading appearance'))
        self.appearance=AppearancePopover(self);self.appearance_button.set_popover(self.appearance)
        self.comparison_button=Gtk.MenuButton(icon_name='view-dual-symbolic',tooltip_text=tr('Compare translations'))
        self.comparison_popover=Gtk.Popover()
        from .version_chooser import DirectChoices
        self.comparison_choices=DirectChoices()
        self.comparison_choices.connect('notify::selected',self.comparison_selected)
        self.comparison_choices.connect('reselected',lambda *_:self.comparison_popover.popdown())
        comparison_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8,margin_top=8,margin_bottom=8,margin_start=8,margin_end=8)
        comparison_box.append(self.comparison_choices)
        self.stop_comparison=Gtk.Button(label=tr('Stop comparison'))
        self.stop_comparison.connect('clicked',lambda *_:self.end_comparison())
        self.stop_comparison.set_visible(False)
        self.download_comparison=Gtk.Button(label=tr('Download more…'))
        self.download_comparison.connect('clicked',lambda *_:self.contextual_library('bible','comparison'))
        comparison_box.append(self.download_comparison)
        self.comparison_popover.set_child(comparison_box)
        self.comparison_button.set_popover(self.comparison_popover)
        from .popover_dismissal import install, fit_reader_popover
        self._reading_popovers = [self.navigation, self.appearance, self.comparison_popover]
        self._popover_dismissal = install(self, self._reading_popovers)
        self.comparison_popover.connect('show',lambda *_:fit_reader_popover(self.comparison_popover,self))
        self._comparison_syncing=False
        # Notes has a working application-space selector at the top left.
        for widget,label in [(self.menu,'Main menu'),
                             (self.study_button,'Study')]:
            widget.add_css_class('flat')
            widget.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
            header.pack_end(widget)
        # Explicit native symbolic size leaves Header Bar hit targets untouched.
        for button in (self.study_button,):
            image=Gtk.Image(icon_name=button.get_icon_name(),pixel_size=16)
            button.set_child(image)
        from .version_chooser import VersionChooser
        self.primary_version=VersionChooser(self)
        self.compared_version=VersionChooser(self,comparison=True)
        self.reader_controls=Gtk.Box(spacing=6,halign=Gtk.Align.END,valign=Gtk.Align.START,
                                    margin_top=12,margin_end=12)
        self.reader_controls.append(self.primary_version)
        for widget,label in [(self.comparison_button,'Compare translations'),(self.appearance_button,'Reading appearance'),(self.immersive_button,'Immersive mode')]:
            widget.add_css_class('circular');widget.add_css_class('reader-action')
            widget.update_property([Gtk.AccessibleProperty.LABEL],[tr(label)])
            self.reader_controls.append(widget)
        self.reader_controls.add_tick_callback(self.fit_reader_controls)
        layout.append(header)
        self.session_status = Gtk.Label(wrap=True, xalign=0, visible=False,
                                        margin_start=12, margin_end=12)
        layout.append(self.session_status)
        self.notes_status = Gtk.Label(wrap=True, xalign=0, visible=bool(self.notes_error),
                                       margin_start=12, margin_end=12,
                                       label=(tr('Notes unavailable. The original file has been preserved.') + '\n' + self.notes_error) if self.notes_error else '')
        layout.append(self.notes_status)
        self.view = Adw.TabView(vexpand=True)
        self.bar = Adw.TabBar(view=self.view, autohide=False)
        self.tab_new_button=Gtk.Button(icon_name='tab-new-symbolic',tooltip_text=tr('New tab'),action_name='win.new-tab',visible=False)
        self.tab_new_button.add_css_class('flat');self.bar.set_end_action_widget(self.tab_new_button)
        layout.append(self.bar)
        layout.append(self.view)
        self.header = header
        self.split = Adw.OverlaySplitView(content=layout, show_sidebar=False,
                                          min_sidebar_width=360, max_sidebar_width=560,
                                          sidebar_width_fraction=.38,
                                          sidebar_position=Gtk.PackType.END)
        from .reference_preview import ReferencePreview
        self.reference_preview=ReferencePreview(self)
        self.study = StudyPanel(self)
        self.header_height_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.VERTICAL)
        self.header_height_group.add_widget(header)
        self.header_height_group.add_widget(self.study.header)
        self.reading_sync=ReadingSync(self)
        from .study_resize import StudyDivider
        sidebar = Gtk.Box()
        self.study_divider = StudyDivider(self, self.study_settings)
        sidebar.append(self.study_divider); sidebar.append(self.study)
        self.study.set_hexpand(True)
        self.split.set_sidebar(sidebar)
        self.split.connect('notify::show-sidebar', lambda *_:self.sync_header_controls())
        self.split.connect('notify::show-sidebar', self.sidebar_changed)
        self.main_pages=Gtk.Stack(hhomogeneous=False,vhomogeneous=False)
        self.main_pages.connect('notify::visible-child-name',lambda *_:self.space_selector.sync())
        self.main_pages.add_named(self.split,'reading')
        self.set_content(self.main_pages)
        breakpoint = Adw.Breakpoint.new(Adw.BreakpointCondition.parse('max-width: 860px'))
        breakpoint.add_setter(self.split, 'collapsed', True)
        self.add_breakpoint(breakpoint)
        tiny_header = Adw.Breakpoint.new(Adw.BreakpointCondition.parse('max-width: 420px'))
        tiny_header.add_setter(self.split, 'collapsed', True)
        # Adw breakpoints do not stack: the tiny layout also needs the drawer's
        # adaptive sizing and its single visible set of native window controls.
        # Removing Library frees room for the existing mouse routes; the new
        # global menu no longer duplicates these reading/workspace commands.
        tiny_header.add_setter(new,'visible',True)
        tiny_header.add_setter(self.tab_new_button,'visible',False)
        # The real passage chooser stays reachable beside the tabs when the
        # top-left space selector needs room. There is still one chooser.
        compact_title=Gtk.Box()
        def compact(*_):
            self.space_selector.add_css_class('compact-space')
            header.set_title_widget(compact_title)
            layout.insert_child_after(self.passage_button,header)
            constrain_labels(self.heading,8)
        def expanded(*_):
            self.space_selector.remove_css_class('compact-space')
            if self.passage_button.get_parent() is layout:layout.remove(self.passage_button)
            header.set_title_widget(self.passage_button)
            constrain_labels(self.heading)
        tiny_header.connect('apply',compact);tiny_header.connect('unapply',expanded)
        self.add_breakpoint(tiny_header)
        icons = Gtk.IconTheme.get_for_display(self.get_display())
        icons.add_search_path(str(Path(__file__).parent / 'icons'))
        css = Gtk.CssProvider()
        css.load_from_data(b'textview.reading { } '
                           b'dropdown.compact-space > button { padding-left: 6px; padding-right: 6px; } '
                           b'.study-drawer textview, .study-drawer textview text { background-color: transparent; color: @sidebar_fg_color; } '
                           b'.study-drawer listview { background-color: transparent; } '
                           b'.study-tools button { min-width: 0; } '
                           b'.reference-excerpt { font-weight: normal; } '
                           b'.study-divider:focus-visible { outline: 2px solid @accent_color; outline-offset: -2px; } '
                           b'button.chapter-navigation { min-width: 40px; min-height: 40px; '
                           b'padding: 0; border-radius: 9999px; } '
                           b'.reader-action { min-width: 34px; min-height: 34px; padding: 0; border-radius: 9999px; } '
                           b'.version-pill > button { border-radius: 9999px; } '
                           b'box.navigation-books { background-color: alpha(currentColor, 0.04); '
                           b'padding: 8px; border-radius: 12px; } '
                           b'popover.passage-selector > contents { border-radius: 18px; }')
        Gtk.StyleContext.add_provider_for_display(self.get_display(), css,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.view.connect('notify::selected-page', self.selected_changed)
        self.view.connect('page-detached', self.page_detached)
        self.view.connect('notify::n-pages',lambda *_:self.bar.set_visible(self.view.get_n_pages()>1))
        self.bar.set_visible(False)
        self.view.connect('page-reordered', lambda *_: self.schedule_save())
        self.add_action_callback('new-tab', lambda *_: self.new_tab())
        self.add_action_callback('close-tab', lambda *_: self.close_tab())
        self.add_action_callback('translations', lambda *_: self.open_library())
        from .application_surfaces import show_preferences,show_shortcuts,show_about
        self.add_action_callback('preferences',lambda *_:show_preferences(self))
        self.add_action_callback('shortcuts',lambda *_:show_shortcuts(self))
        self.add_action_callback('about',lambda *_:show_about(self))
        app.set_accels_for_action('win.preferences',['<Control>comma'])
        app.set_accels_for_action('win.shortcuts',['<Control>question'])
        self.add_action_callback('choose-passage', lambda *_: self.choose_passage())
        self.add_action_callback('reference', lambda *_: self.choose_passage(direct=True))
        self.add_action_callback('previous-chapter', lambda *_: self.step_chapter(-1))
        self.add_action_callback('next-chapter', lambda *_: self.step_chapter(1))
        self.add_action_callback('previous-verse', lambda *_: self.active_tab.step_verse(-1))
        self.add_action_callback('next-verse', lambda *_: self.active_tab.step_verse(1))
        self.add_action_callback('appearance',lambda *_:self.show_appearance())
        self.add_action_callback('compare',lambda *_:self.show_comparison())
        self.add_action_callback('immersive',lambda *_:self.toggle_immersion())
        self.add_action_callback('previous-commentary-entry',lambda *_:self.immersion.change_entry(-1) if self.immersion and self.immersion.kind=='commentary' else self.study.step_entry(-1))
        self.add_action_callback('next-commentary-entry',lambda *_:self.immersion.change_entry(1) if self.immersion and self.immersion.kind=='commentary' else self.study.step_entry(1))
        self.add_action_callback('immersive-open-bible',lambda *_:self.immersion.open_in_bible() if self.immersion and self.immersion.kind=='commentary' else None)
        self.add_action_callback('history-back',lambda *_:self.active_tab.travel(self.active_tab.state.history_index-1))
        self.add_action_callback('history-forward',lambda *_:self.active_tab.travel(self.active_tab.state.history_index+1))
        self.add_action_callback('copy-passage',lambda *_:self.copy_passage())
        self.add_action_callback('copy-with-reference',lambda *_:self.copy_passage(True))
        self.add_action_callback('copy-reference',lambda *_:self.copy_passage(reference_only=True))
        self.add_action_callback('note', lambda *_: self.new_note())
        self.add_action_callback('notes', lambda *_: self.open_notes())
        self.add_action_callback('highlights',lambda *_:self.open_highlights())
        for color in COLORS:self.add_action_callback('highlight-'+color,lambda *_,value=color:self.mark_highlight(value))
        self.add_action_callback('highlight-remove',lambda *_:self.mark_highlight(None))
        self.lookup_action('note').set_enabled(self.notes_store is not None)
        self.lookup_action('notes').set_enabled(self.notes_store is not None)
        self.add_action_callback('study', lambda *_: self.study_button.set_active(not self.study_button.get_active()))
        app.set_accels_for_action('win.immersive',['F11'])
        app.set_accels_for_action('win.new-tab', ['<Control>t'])
        app.set_accels_for_action('win.close-tab', ['<Control>w'])
        app.set_accels_for_action('win.translations', ['<Control>l'])
        app.set_accels_for_action('win.study', ['F9'])
        app.set_accels_for_action('win.note', ['<Control>n'])
        app.set_accels_for_action('win.notes', ['<Control><Shift>n'])
        app.set_accels_for_action('win.previous-verse', ['<Alt>Up'])
        app.set_accels_for_action('win.next-verse', ['<Alt>Down'])
        app.set_accels_for_action('win.choose-passage', ['<Control>g'])
        app.set_accels_for_action('win.reference', ['<Control>k'])
        app.set_accels_for_action('win.previous-chapter', ['<Alt>Page_Up'])
        app.set_accels_for_action('win.history-back',['<Alt>Left'])
        app.set_accels_for_action('win.next-chapter', ['<Alt>Page_Down'])
        app.set_accels_for_action('win.history-forward',['<Alt>Right'])
        try:
            session = self.store.load() if self.application_settings.value["restore_tabs"] else Session()
        except (OSError, SessionError) as error:
            self._session_writable = False
            self.report_session_error(tr('Unable to restore the session. The original file has been preserved.') + '\n' + tr('Session saving is disabled to preserve the original file.'), error)
            session = Session()
        if not session.tabs:
            names = self.library.installed('bible')
            session.tabs = [TabState(resource=names[0] if names else None)]
        from .passage_actions import PassageActions
        self.passage_actions=PassageActions(self)
        for state in session.tabs:
            self.append_tab(state)
        self.view.set_selected_page(self.view.get_nth_page(session.selected))
        self._initializing = False
        self.selected_changed()
        self.study_divider.apply()
        from .application_surfaces import welcome_page
        self.welcome=welcome_page(self);self.main_pages.add_named(self.welcome,'welcome')
        self.startup_resource_error=''
        readable=False
        for name in self.library.installed():
            try:
                if self.library.resource(name).kind=='bible':
                    from .sword_provider import Reader
                    reader=Reader(self.library.root/name,name);first=reader.first_reference()
                    if not any(text.strip() for _,text in reader.chapter(first).verses):raise ValueError('No readable text in installed Bible')
                    readable=True;break
            except (OSError,ValueError) as error:self.startup_resource_error=str(error)
        if not readable:
            self.main_pages.set_visible_child_name('welcome')
            if self.startup_resource_error:self.welcome_status.set_description(GLib.markup_escape_text(tr('Some installed Bibles could not be read. They are preserved. Retry from Library.')+' '+self.startup_resource_error))
        if self.application_settings.error:self.report_session_error(tr('Unable to load application preferences. Original file preserved.'),self.application_settings.error)

    def fit_reader_controls(self,*_):
        tab=self.active_tab
        if not tab or self.primary_version.get_parent() is not self.reader_controls:return True
        available=tab.reading_overlay.get_width()-24
        if available<=0:return True
        others=[];child=self.reader_controls.get_first_child()
        while child:
            if child is not self.primary_version and child.get_visible():others.append(child)
            child=child.get_next_sibling()
        widths=tuple(widget.measure(Gtk.Orientation.HORIZONTAL,-1)[1] for widget in others)
        caption=self.primary_version.caption
        stamp=(available,widths,caption.get_text(),caption.get_pango_context().get_serial())
        if stamp==getattr(self,'_reader_controls_geometry',None):return True
        self._reader_controls_geometry=stamp
        width=sum(widths)
        padding=self.primary_version.measure(Gtk.Orientation.HORIZONTAL,-1)[1]-caption.measure(Gtk.Orientation.HORIZONTAL,-1)[1]
        em=max(1,caption.create_pango_layout('M').get_pixel_size()[0])
        chars=max(4,min(16,int((available-width-padding-6*len(others))/em)))
        if caption.get_max_width_chars()!=chars:caption.set_max_width_chars(chars)
        return True

    def copy_passage(self,with_reference=False,reference_only=False):
        from .notes_window import passage_label
        tab=self.active_tab
        if not tab or not tab.reader:return
        if self.immersion:
            if self.immersion.kind!='bible':return
            first,last=self.immersion.selected_passage();reader=self.immersion.source.reader
            version=self.immersion.source.resource.name
        else:first,last=tab.selected_passage();reader=tab.reader;version=module_name(tab.state.resource)
        label=passage_label(first,last,reader.versification)+' — '+version
        if reference_only:value=label
        else:
            start,end=reader.key(first).getIndex(),reader.key(last).getIndex()
            chapter=reader.chapter(first)
            value='\n'.join(text for ref,text in chapter.verses if start<=reader.key(ref).getIndex()<=end)
            if with_reference:value=label+'\n'+value
        self.get_clipboard().set(value)

    def show_appearance(self):
        if self.immersion:self.immersion.reveal_controls();self.immersion.aa.popup()
        else:self.appearance_button.popup()

    def show_comparison(self):
        if self.immersion:self.leave_immersion()
        if self.active_tab and self.active_tab.state.comparison:self.compared_version.popup()
        else:self.comparison_button.popup()

    def toggle_immersion(self):
        if self.immersion:self.leave_immersion()
        else:self.enter_immersion('bible')

    def enter_immersion(self,kind='bible'):
        if hasattr(self,'passage_actions'):self.passage_actions.dismiss()
        if self.immersion:self.leave_immersion()
        tab=self.active_tab
        if not tab or not tab.reader:return False
        if kind=='commentary':
            study=self.study
            if not study.reader or study.current_position is None:return False
            source=CommentaryPages(study.reader,self.library.resource(tab.state.commentary))
            key=study.current_position
            doc=source.document(key,self.preferences.value);anchor=doc.anchor(0)
            saved=tab.state.commentary_positions.get(tab.state.commentary)
            if saved and saved.get('immersive'):
                positions=[i for i,section in enumerate(source.reader.index.sections) if section.index==saved['index']]
                if positions:
                    key=positions[0];doc=source.document(key,self.preferences.value)
                    anchor=Anchor(doc.spans[0].reference,saved['offset'],True)
            else:
                current=study.anchor()
                if current:
                    key,offset=current;doc=source.document(key,self.preferences.value)
                    anchor=doc.anchor(doc.spans[0].body+offset if offset else 0)
        else:
            source=BibleBookPages(tab.reader,self.library.resource(tab.state.resource))
            anchor=Anchor(tab.state.reference)
            if tab.text.get_mapped() and not tab._restoring_scroll:
                rect=tab.text.get_visible_rect();_,iterator=tab.text.get_iter_at_location(rect.x,rect.y)
                position=tab.position_anchor(iterator.get_offset())
                if position:
                    reference,offset=position;buffer=tab.text.get_buffer();first=tab._marker_ends[reference]
                    text=buffer.get_text(buffer.get_iter_at_offset(first),buffer.get_iter_at_offset(first+offset),False)
                    anchor=Anchor(reference,sum(not c.isspace() for c in text),iterator.get_offset()>=first)
            key=source.key(anchor.reference)
        for popover in self._reading_popovers:popover.popdown()
        self.reading_sync.driver=None
        immersion=Immersion(self,source,key,anchor);self.immersion=immersion
        self.main_pages.add_named(immersion,'immersive');self.main_pages.set_visible_child_name('immersive')
        self.immersive_button.set_active(True);self.lookup_action('note').set_enabled(kind=='bible' and self.notes_store is not None)
        self.fullscreen();return True

    def leave_immersion(self):
        if hasattr(self,'passage_actions'):self.passage_actions.dismiss()
        immersion=self.immersion
        if not immersion:return
        anchor,key=immersion.finish();tab=immersion.tab;self.immersion=None
        self.main_pages.set_visible_child_name('reading');self.main_pages.remove(immersion)
        if not immersion.was_fullscreen:self.unfullscreen()
        self.immersive_button.set_active(False);self.lookup_action('note').set_enabled(self.notes_store is not None)
        self.reading_sync.driver=None
        if immersion.kind=='bible' and tab.reader:
            tab._travelling=True
            try:tab.show(anchor.reference)
            finally:tab._travelling=False
            if anchor.reference in tab._verse_ranges:
                first,last=tab._verse_ranges[anchor.reference];body=tab._marker_ends[anchor.reference]
                buffer=tab.text.get_buffer();text=buffer.get_text(buffer.get_iter_at_offset(body),buffer.get_iter_at_offset(last),False)
                remaining=anchor.offset;offset=0
                for offset,char in enumerate(text):
                    if not char.isspace():
                        if remaining<=0:break
                        remaining-=1
                tab._appearance_anchor=(anchor.reference,offset) if anchor.at_body else None
                tab._jump_reference=None if anchor.at_body else anchor.reference;tab.schedule_scroll_restore()
        elif immersion.kind=='commentary':
            section=immersion.source.reader.index.sections[key]
            tab.state.commentary_positions[tab.state.commentary]=dict(reference=section.start,index=section.index,offset=anchor.offset,canonical=True,immersive=True)
            if tab is self.active_tab:self.study.resume(key,anchor)
        self.update_navigation() if immersion.kind=='bible' else None
        self.schedule_save()

    def add_action_callback(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect('activate', callback)
        self.add_action(action)

    @property
    def active_tab(self):
        page = self.view.get_selected_page()
        return page.get_child() if page else None

    @property
    def previous(self):
        return self.active_tab.previous

    @property
    def following(self):
        return self.active_tab.following

    def tabs(self):
        return [self.view.get_nth_page(index).get_child() for index in range(self.view.get_n_pages())]

    def append_tab(self, state, jump_to_reference=False):
        if not state.reading_palette:
            state.reading_palette=dict(self.reading_style.initial_palette if self._initializing else self.reading_style.palette_settings())
        tab = ReadingTab(self.library, state, self.tab_changed, jump_to_reference,
                         self.notes_store, self.reveal_passage_annotations, self.preferences.value)
        self.reading_sync.bind(tab.scroll,tab.text,'bible',tab)
        self.reading_style.decorate(tab.text)
        # The viewport, headers, gutters and empty comparison space belong to
        # the same reading palette as the text, not the native window surface.
        for surface in (tab.reading_layout,tab.reading_overlay,tab.scroll,
                        tab.comparison_box,tab.comparison_overlay,tab.comparison_scroll):
            surface.add_css_class(self.reading_style.scope+'-surface')
        self.reading_style.decorate(tab.comparison_text)
        from .comparison_sync import ComparisonSync
        tab.comparison_sync = ComparisonSync(self, tab)
        tab._highlight_store=self.highlights
        tab.update_highlights(self.reading_style.manager.get_high_contrast(),self.reading_style.palette)
        self.passage_actions.bind(tab.text,lambda:self.passage_actions.ordinary(tab))
        self.passage_actions.bind(tab.comparison_text,lambda:self.passage_actions.ordinary(tab,True))
        tab.download_bible=Gtk.Button(label=tr('Download a Bible'),halign=Gtk.Align.CENTER,visible=tab.reader is None)
        tab.download_bible.connect('clicked',lambda *_:self.open_library('bible',context=self.library_context(tab,'bible')))
        tab.insert_child_after(tab.download_bible,tab.status)
        page = self.view.append(tab)
        def selection_changed(*_):
            if self.active_tab is tab and self.study.tool in ('notes','references'):
                if not getattr(self.study,'_notes_idle',0):
                    def refresh():
                        self.study._notes_idle=0
                        if not self.closed:
                            if self.study.tool=='notes':self.study.notes.refresh()
                            self.study.references.refresh()
                        return False
                    self.study._notes_idle=GLib.idle_add(refresh)
        tab.text.get_buffer().connect('mark-set',selection_changed)
        page.set_title(tab.title())
        return page

    def return_to_reading(self):
        readable=any(tab.reader is not None and tab.current is not None for tab in self.tabs())
        self.main_pages.set_visible_child_name('reading' if readable else 'welcome')

    def new_tab(self):
        if self.immersion:self.leave_immersion()
        current = self.active_tab
        names = self.library.installed('bible')
        state = TabState(current.state.resource, current.state.reference, current.state.scroll,
                         commentary=current.state.commentary) if current else TabState(
            resource=names[0] if names else None)
        if current:state.reading_palette=self.reading_style.palette_settings()
        page = self.append_tab(state)
        self.view.set_selected_page(page)
        self.schedule_save()
        page.get_child().text.grab_focus()
        return page.get_child()

    def navigate_selection(self, resource, reference, new_tab=False):
        if hasattr(self,'passage_actions'):self.passage_actions.dismiss()
        try:
            if new_tab:
                from .sword_provider import Reader
                reader = Reader(self.library.root / resource, resource)
                if not reader.has_reference(reference):
                    raise ValueError(tr('This passage is not available in this translation.'))
                page = self.append_tab(TabState(resource, reader.key(reference).getOSISRef(),
                                                commentary=self.active_tab.state.commentary if self.active_tab else None),
                                       jump_to_reference=True)
                self.view.set_selected_page(page)
                self.schedule_save()
                return True
            return bool(self.active_tab and self.active_tab.navigate(resource, reference))
        except Exception as error:
            if self.active_tab:
                self.active_tab.status.set_text(f'{tr("Unable to read this passage.")} {error}')
                self.active_tab.status.set_visible(True)
            return False

    def choose_passage(self, direct=False):
        if self.immersion and self.immersion.kind=='commentary':self.leave_immersion()
        self.navigation.modes.set_visible_child_name('passage')
        button=self.immersion.passage_button if self.immersion else self.passage_button
        if self.immersion:self.immersion.reveal_controls()
        button.set_active(True)
        self.navigation.sync(force=True)
        (self.navigation.direct if direct else self.navigation.search).grab_focus()

    def step_chapter(self, direction):
        tab = self.active_tab
        if tab and tab.reader:
            previous, following = tab.reader.neighbours(tab.state.reference)
            reference = previous if direction < 0 else following
            if reference:
                tab.show(reference)

    def update_navigation(self):
        tab = self.active_tab
        if not tab:
            return
        for color in [*COLORS,'remove']:
            self.lookup_action('highlight-'+color).set_enabled(tab.reader is not None and not (self.immersion and self.immersion.kind=='commentary'))
        parent=self.reader_controls.get_parent()
        if parent is not tab.reading_overlay:
            if parent:parent.remove_overlay(self.reader_controls)
            tab.reading_overlay.add_overlay(self.reader_controls)
        right_parent=self.compared_version.get_parent()
        if right_parent is not tab.comparison_controls:
            if right_parent:right_parent.remove(self.compared_version)
            tab.comparison_controls.append(self.compared_version)
        self.primary_version.sync();self.compared_version.sync()
        self.immersive_button.set_visible(not bool(tab.state.comparison))
        self.immersive_button.set_sensitive(tab.reader is not None)
        self.lookup_action('immersive').set_enabled(tab.reader is not None)
        for name in ['copy-passage','copy-with-reference','copy-reference']:
            self.lookup_action(name).set_enabled(tab.reader is not None and not (self.immersion and self.immersion.kind=='commentary'))
        self.heading.set_title(tab.passage_title())
        subtitle = module_name(tab.state.resource) if tab.state.resource else tr('Choose a translation')
        if tab.state.resource and tab.state.resource not in self.library.installed():
            subtitle += f' ({tr("Missing translation")})'
        self.heading.set_subtitle(subtitle)
        self.passage_button.set_tooltip_text(f'{tab.passage_title()} — {subtitle}\n{tr("Choose a passage")} (Ctrl+G)')
        self.passage_button.update_property([Gtk.AccessibleProperty.LABEL],
                                             [f'{tr("Choose a passage")}: {tab.passage_title()} — {subtitle}'])
        previous, following = tab.reader.neighbours(tab.state.reference) if tab.reader else (None, None)
        self.lookup_action('previous-chapter').set_enabled(previous is not None)
        self.lookup_action('next-chapter').set_enabled(following is not None)
        self.navigation.sync()
        self.sync_comparison()
        self.lookup_action('history-back').set_enabled(tab.state.history_index>0)
        self.lookup_action('history-forward').set_enabled(tab.state.history_index+1<len(tab.state.history))
        self.study.refresh()
        tab.update_notes()

    def apply_appearance(self,reflow=True):
        self.reading_style.apply_mode()
        self.appearance.sync()
        if not reflow:return
        for tab in self.tabs():tab.apply_appearance()
        if self.active_tab:self.active_tab.refresh_comparison()
        if self.immersion:self.immersion.reflow()

    def sync_comparison(self):
        tab=self.active_tab
        self._comparison_syncing=True
        self._comparison_names=[None]+[name for name in self.library.installed('bible') if name!=tab.state.resource]
        labels=[tr('No comparison')]+[self.library.resource(name).description for name in self._comparison_names[1:]]
        # Synchronization must not emit another selection for an unchanged row.
        if getattr(self,'_comparison_labels',None)!=labels:
            self.comparison_choices.set_model(Gtk.StringList.new(labels));self._comparison_labels=labels
        self.comparison_choices.set_selected(self._comparison_names.index(tab.state.comparison) if tab.state.comparison in self._comparison_names else 0)
        self.comparison_choices.update_property([Gtk.AccessibleProperty.LABEL],[tr('Compare translations')])
        self._comparison_syncing=False
        self.comparison_choices.set_visible(True)
        self.stop_comparison.set_visible(False)
        label=tr('Stop comparison') if tab.state.comparison else tr('Compare translations')
        self.comparison_button.set_tooltip_text(label)
        self.comparison_button.update_property([Gtk.AccessibleProperty.LABEL],[label])
        tab.refresh_comparison()
        self.primary_version.sync();self.compared_version.sync()
        self.immersive_button.set_visible(not bool(tab.state.comparison))

    def end_comparison(self):
        self.active_tab.state.comparison=None
        self.sync_comparison();self.schedule_save();self.comparison_popover.popdown()

    def comparison_selected(self,widget,*_):
        if self._comparison_syncing or not self.active_tab:return
        index=widget.get_selected()
        self.active_tab.state.comparison=self._comparison_names[index] if index<len(self._comparison_names) else None
        self.sync_comparison()
        self.schedule_save()
        # Finish native row activation before dismissing its parent.
        GLib.idle_add(lambda: self.comparison_popover.popdown() or False)

    def close_tab(self):
        if self.immersion:self.leave_immersion()
        page = self.view.get_selected_page()
        if page:
            self.view.close_page(page)

    def page_detached(self, *_):
        if self.closed:
            return
        if self.view.get_n_pages() == 0:
            self.append_tab(TabState())
        self.schedule_save()

    def tab_changed(self, tab):
        if hasattr(tab,'download_bible'):tab.download_bible.set_visible(tab.reader is None)
        active=self.active_tab
        context=(id(active),id(active.reader),active.state.resource) if active else None
        if context!=getattr(self,'_reference_context',None):
            self.reference_preview.dismiss();self._reference_context=context
        if self.immersion and self.immersion.kind=='bible' and tab is self.immersion.tab:
            current=self.immersion.stream.anchor() if self.immersion.stream.cursor else self.immersion.initial_anchor
            if current.reference!=tab.state.reference or self.immersion.source.reader is not tab.reader:
                source=BibleBookPages(tab.reader,self.library.resource(tab.state.resource))
                self.immersion.source=source;self.immersion.stream.source=source
                self.immersion.go_to_reference(tab.state.reference)
        if self._initializing:
            return
        for index in range(self.view.get_n_pages()):
            page = self.view.get_nth_page(index)
            if page.get_child() is tab:
                page.set_title(tab.title())
                break
        if tab is self.active_tab:
            self.update_navigation()
        self.schedule_save()

    def selected_changed(self, *_):
        if self.immersion:self.leave_immersion()
        self.reading_sync.driver=None
        tab = self.active_tab
        if tab is None:
            return
        if hasattr(self,'appearance'):self.reading_style.activate_tab(tab)
        self._syncing_study = True
        self.study_button.set_active(tab.state.study_visible)
        self.split.set_show_sidebar(tab.state.study_visible)
        self._syncing_study = False
        self.update_navigation()
        self.schedule_save()

    def toggle_study(self, *_):
        if not self._syncing_study:
            self.split.set_show_sidebar(self.study_button.get_active())

    def sync_header_controls(self):
        visible=self.split.get_show_sidebar()
        self.header.set_show_end_title_buttons(not visible)
        self.study.header.set_show_end_title_buttons(visible)

    def sidebar_changed(self, *_):
        if not self.split.get_show_sidebar():self.study.cancel_scroll()
        if self._syncing_study:
            return
        visible = self.split.get_show_sidebar()
        if not visible:
            for popover in self.study.popovers:popover.popdown()
        self._syncing_study = True
        self.study_button.set_active(visible)
        if self.active_tab:
            self.active_tab.state.study_visible = visible
            if visible:self.study.update_indicator()
            else:self.active_tab.mark_commentary_range(None,None)
        self._syncing_study = False
        self.schedule_save()

    def open_places(self):
        if getattr(self,'place_dialog',None) is None or self.place_dialog.closed:
            from .place_cards import PlaceCards
            self.place_dialog=PlaceCards(self)
        self.place_dialog.present(self)
        return self.place_dialog

    def library_context(self,tab,destination):
        import weakref
        return (weakref.ref(tab),destination)

    def contextual_library(self,kind,destination):
        self.dismiss_popovers()
        return self.open_library(kind,context=self.library_context(self.active_tab,destination))

    def dismiss_popovers(self):
        for popover in self._reading_popovers:popover.popdown()
        for popover in self.study.popovers:popover.popdown()

    def open_library(self, kind=None, context=None):
        if self.catalogue_window is None or self.catalogue_window.closed:
            self.catalogue_window = CatalogueWindow(self, self.library, self.resource_installed)
        if kind is not None:
            self.catalogue_window.kind.set_selected({'commentary':1,'study':2}.get(kind,0))
        elif self.catalogue_window.kind.get_selected()==2:self.catalogue_window.kind.set_selected(0)
        self.catalogue_window.open_context=context
        self.catalogue_window.present()
        return self.catalogue_window

    def resource_installed(self, name):
        if self.closed:
            return
        from .study_resources import REFERENCE_RESOURCE_ID,PLACE_RESOURCE_ID,TOPIC_RESOURCE_ID
        if name in (REFERENCE_RESOURCE_ID,PLACE_RESOURCE_ID,TOPIC_RESOURCE_ID):
            for window in self.get_application().get_windows():
                if isinstance(window,Window) and not window.closed and window.library.root==self.library.root:
                    if name==REFERENCE_RESOURCE_ID:window.study.references.invalidate()
                    elif name==TOPIC_RESOURCE_ID:window.navigation.topic_search.refresh()
                    elif getattr(window,'place_dialog',None) and not window.place_dialog.closed:window.place_dialog.refresh()
            return
        # Installation refreshes choices, never the user's selected resource.
        for window in self.get_application().get_windows():
            if not isinstance(window,Window) or window.closed or window.library.root!=self.library.root:continue
            if getattr(window,'catalogue_session',None):window.catalogue_session.reload_installed()
            for tab in window.tabs():
                if tab.state.resource==name:tab.load_resource();window.tab_changed(tab)
            window.study._readers.pop(name,None)
            window.study.refresh(force=True)
            window.primary_version.sync();window.compared_version.sync();window.sync_comparison()
            if window.notes_space:
                window.notes_space._reader_cache.pop(name,None);window.notes_space._excerpt_cache.clear()
                window.notes_space.refresh()
                if window.notes_space.selected_annotation:window.notes_space.update_context(window.notes_space.selected_annotation)

    def open_installed_resource(self,name,context=None):
        tab=context[0]() if context else self.active_tab
        destination=context[1] if context else 'bible'
        if tab not in self.tabs():return False
        resource=self.library.resource(name)
        def open_now():
            if self.closed or tab not in self.tabs():return
            if self.immersion:self.leave_immersion()
            self.view.set_selected_page(self.view.get_page(tab))
            if resource.kind=='commentary':
                tab.state.commentary=name;self.study.tools.set_visible_child_name('commentaries')
                self.study_button.set_active(True);self.study.refresh(force=True)
            elif destination=='comparison':
                tab.state.comparison=name;self.sync_comparison()
            else:
                from .sword_provider import Reader
                from .reference_resolution import resolve
                reader=Reader(self.library.root/name,name)
                reference=resolve(tab.state.reference,tab.reader.versification,reader).start if tab.reader else reader.first_reference()
                if not self.navigate_selection(name,reference):return
            self.main_pages.set_visible_child_name('reading');self.schedule_save()
        if self.main_pages.get_visible_child_name()=='notes':
            def guarded_open():
                try:open_now()
                except (OSError,ValueError) as error:self.report_session_error(tr('Unable to read this passage.'),error)
            self.notes_space.guard(guarded_open)
        else:open_now()
        return True

    def notes_changed(self):
        for window in self.get_application().get_windows():
            if not isinstance(window,Window) or window.closed or window.library.root!=self.library.root or not window.notes_store:continue
            if window is not self:window.notes_store.generation+=1
            for tab in window.tabs():tab.update_notes(force=True)
            if window.notes_window and not window.notes_window.closed:
                window.notes_window.labels.set_suggestions(window.notes_store.labels());window.notes_window.refresh()
            if window.study.tool=='notes':window.study.notes.refresh()

    def refresh_highlights(self):
        for window in self.get_application().get_windows():
            if (isinstance(window,Window) and not getattr(window,'closed',True)
                    and hasattr(window,'view') and window.highlights is self.highlights):
                window.paint_highlights()

    def paint_highlights(self):
        for tab in self.tabs():tab.update_highlights(self.reading_style.manager.get_high_contrast(),self.reading_style.palette)
        if self.immersion:
            self.immersion.capture_selection();self.immersion.render()
        if self.highlights_window and not self.highlights_window.closed:self.highlights_window.refresh()
        if self.notes_space and not self.notes_space.closed:self.notes_space.refresh()
        if self.study.tool=='notes':self.study.notes.refresh()

    def mark_highlight(self,color):
        tab=self.active_tab
        if not tab or not tab.reader or (self.immersion and self.immersion.kind!='bible'):return
        try:
            start,end=self.immersion.selected_passage() if self.immersion else tab.selected_passage()
            key=tab.reader.key(start);last=tab.reader.key(end).getIndex();references=[]
            while key.getIndex()<=last:
                reference=key.getOSISRef()
                if tab.reader.has_reference(reference):references.append(reference)
                if len(references)>1000:raise ValueError('Select at most 1000 verses')
                key.increment()
                if key.popError()!='\x00':break
            self.highlights.set(tab.reader.versification,references,color,tab.state.resource)
            self.refresh_highlights()
        except (ValueError,OSError,TypeError) as error:
            tab.status.set_text(str(error));tab.status.set_visible(True)

    def open_highlights(self):
        def shown(space):space.set_category('highlights');space.split.set_show_sidebar(True)
        return self.open_notes(on_open=shown)

    def open_notes(self,on_open=None):
        if self.immersion:self.leave_immersion()
        if self.notes_store is None:return
        editor=self.note_editor
        if editor and not editor.closed and editor.embedded_host is not self.notes_space:
            editor.after_close=lambda:self.open_notes(on_open=on_open);editor.close();return
        if self.notes_space is None:
            self.notes_space=NotesSpace(self)
            self.notes_window=self.notes_space
            self.main_pages.add_named(self.notes_space,'notes')
        self.notes_space.refresh();self.notes_space.present()
        if on_open:on_open(self.notes_space)
        return self.notes_space

    def new_note(self, force_new=False):
        override=self.immersion.selected_passage() if self.immersion and self.immersion.kind=='bible' else None
        if self.immersion:self.leave_immersion()
        tab = self.active_tab
        if not self.notes_store or tab is None or tab.reader is None:
            self.notes_status.set_text(tr('Open a Bible passage before creating a note.'))
            self.notes_status.set_visible(True)
            return
        start, end = override or tab.selected_passage()
        matching = self.notes_store.passage(tab.reader.versification, start, end)
        if matching and not force_new:
            return self.open_passage_notes((start,end))
        context = dict(versification=tab.reader.versification, start=start, end=end,
                       origin_translation=tab.state.resource,
                       origin_language=self.library.resource(tab.state.resource).language)
        return self.edit_note(context=context)

    def reveal_passage_annotations(self):
        # Intentional inline markers reveal the chapter list, never enter edit.
        self.study_button.set_active(True);self.study.tools.set_visible_child_name('notes')
        self.study.notes.refresh();self.study.notes.resume_following()

    def open_passage_notes(self, passage=None, *, resource=None, reader=None):
        tab = self.active_tab
        reader=reader or (tab.reader if tab else None)
        resource=resource or (tab.state.resource if tab else None)
        if not self.notes_store or not tab or not reader:
            return
        start, end = passage or tab.selected_passage()
        notes = self.notes_store.passage(reader.versification, start, end)
        if len(notes) == 1:
            return self.edit_note(note=notes[0])
        if not notes:
            context=dict(versification=reader.versification,start=start,end=end,
                         origin_translation=resource,origin_language=self.library.resource(resource).language)
            return self.edit_note(context=context)
        def shown(window):
            window.search.set_text('');window.labels.set_values([])
            window.passage_filter=(reader.versification,start,end);window.set_category('all')
        return self.open_notes(on_open=shown)

    def edit_note(self, note=None, context=None, explanation=''):
        if self.note_editor and not self.note_editor.closed:
            self.note_editor.status.set_text(tr('Save or close the current note before opening another.'))
            self.note_editor.present()
            return self.note_editor
        self.notes_status.set_visible(False)
        self.note_editor = NoteEditor(self, note=note, context=context, explanation=explanation)
        self.note_editor.present()
        return self.note_editor

    def open_saved_note(self, note, edit=True):
        note = self.notes_store.get(note.id)
        if note is None:
            return
        if edit and self.main_pages.get_visible_child_name()=='notes':
            return self.notes_space.open_note(note)
        from .sword_provider import Reader
        tab = self.active_tab
        candidates = list(dict.fromkeys([tab.state.resource if tab else None,
                                         note.origin_translation, *self.library.installed('bible')]))
        explanation = tr('No compatible translation installed. The note remains available.')
        for name in candidates:
            if name not in self.library.installed('bible'):
                continue
            try:
                reader = tab.reader if tab and tab.state.resource == name and tab.reader else Reader(self.library.root / name, name)
                if (reader.versification == note.versification and reader.has_reference(note.start)
                        and reader.has_reference(note.end)):
                    if self.navigate_selection(name, note.start):
                        explanation = ''
                        break
            except Exception:
                continue
        if explanation:
            explanation += f' [{note.versification}]'
        return self.edit_note(note=note, explanation=explanation) if edit else not explanation

    def schedule_save(self):
        if self._initializing or self.closed or not self._session_writable:
            return
        if self._save_id:
            GLib.source_remove(self._save_id)
        self._save_id = GLib.timeout_add(300, self.save_session)

    def save_session(self):
        self._save_id = 0
        if not self._session_writable:
            return False
        pages = self.tabs()
        if not pages:
            return False
        selected = pages.index(self.active_tab) if self.active_tab in pages else 0
        try:
            self.store.save(Session([tab.state for tab in pages], selected))
            self.session_status.set_visible(False)
        except OSError as error:
            self.report_session_error(tr('Unable to save the session.'), error)
        return False

    def report_session_error(self, message, error):
        self.session_status.set_text(f'{message}\n{error}')
        self.session_status.set_visible(True)

    def on_close(self, *_):
        if self.immersion:self.leave_immersion()
        if self.note_editor and not self.note_editor.closed:
            def close_later():
                if not self.closed:self.close()
                return False
            self.note_editor.after_close = lambda:GLib.idle_add(close_later)
            self.note_editor.close()
            # Synchronous autosave/clean close can finish inside close-request.
            # Continue this request; a nested Gtk.Window.close is ignored.
            if not self.note_editor.closed:return True
        if self._save_id:
            GLib.source_remove(self._save_id)
            self._save_id = 0
        self.save_session()
        self.closed = True
        self.reference_preview.dismiss()
        self.study.references.close()
        self.study.notes.close()
        self.navigation.close()
        self.study.cancel_reveal()
        self.study.cancel_scroll()
        self.reading_style.close()
        if self.notes_space:self.notes_space.closed=True
        if self.notes_store:
            self.notes_store.close()
        if self.catalogue_window is not None and not self.catalogue_window.closed:
            self.catalogue_window.close()
        if getattr(self,'catalogue_session',None):self.catalogue_session.close()
        return False


class Application(Adw.Application):
    def __init__(self):
        super().__init__(application_id='io.github.icfmp.Bible')

    def do_activate(self):
        if not self.get_active_window():
            root = Path(GLib.get_user_data_dir()) / 'bible' / 'translations'
            Window(self, Library(root)).present()
        else:
            self.get_active_window().present()


def main():
    return Application().run()
