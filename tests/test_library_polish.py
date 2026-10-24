"""Approved Library/onboarding/global-menu contracts, including upgrade safety."""
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from dataclasses import replace
from bible.application_settings import ApplicationSettings
from bible.catalogue_session import CatalogueSession
from bible.library import Library, CatalogueResult
from bible.providers import CROSSWIRE, EXTRA
from bible.languages import canonical_language,search_terms
from tests.test_library import RESOURCE
from tests.test_ui import spin,installed_fixture,close_test_dialogs


class ApplicationSettingsTests(unittest.TestCase):
    def test_new_locale_defaults_explicit_choice_and_restart(self):
        for locale,expected in [('fr_FR','fr'),('en_US','en'),('C','en'),('de_DE','en')]:
            with self.subTest(locale=locale),tempfile.TemporaryDirectory() as directory,patch('bible.application_settings.LANGUAGE',locale):
                root=Path(directory);Library(root/'translations');settings=ApplicationSettings(root)
                self.assertTrue(settings.first_launch);self.assertEqual(settings.language,expected)
                settings.set('library_language','')
                restored=ApplicationSettings(root);self.assertFalse(restored.first_launch);self.assertEqual(restored.language,'')

    def test_upgrade_missing_marker_and_corrupt_settings_preserve_originals(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'notes.sqlite3').write_bytes(b'existing sentinel')
            settings=ApplicationSettings(root);self.assertFalse(settings.first_launch)
            self.assertEqual((root/'notes.sqlite3').read_bytes(),b'existing sentinel')
            settings.path.write_bytes(b'{corrupt original')
            corrupt=ApplicationSettings(root);self.assertFalse(corrupt.first_launch)
            with self.assertRaises(ValueError):corrupt.set('library_language','fr')
            self.assertEqual(settings.path.read_bytes(),b'{corrupt original')

    def test_saved_ui_language_is_loaded_at_next_process_start(self):
        import subprocess,sys
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'bible';root.mkdir()
            settings=ApplicationSettings(root);settings.set('ui_language','fr');settings.set('library_language','azb')
            env={**os.environ,'XDG_DATA_HOME':directory,'LANGUAGE':'en'}
            output=subprocess.check_output([sys.executable,'-c','from bible.i18n import LANGUAGE,tr;print(LANGUAGE,tr("Preferences"))'],env=env,text=True)
            self.assertEqual(output.strip(),'fr Paramètres')
            self.assertEqual(ApplicationSettings(root).language,'azb')

    def test_language_aliases_do_not_conflate_scripts_or_regions(self):
        self.assertEqual({canonical_language(x) for x in ['fr','fra','fre']},{'fr'})
        self.assertIn('fre',search_terms('fr'));self.assertIn('fra',search_terms('fr'))
        self.assertNotEqual(canonical_language('zh-Hans'),canonical_language('zh-Hant'))
        self.assertNotEqual(canonical_language('pt-BR'),canonical_language('pt-PT'))

    def test_scoped_refresh_keeps_other_providers_and_runs_only_selected_source(self):
        with tempfile.TemporaryDirectory() as directory:
            session=CatalogueSession(Library(Path(directory)/'translations'))
            try:
                session.bootstrap_future.result(10)
                extra=replace(RESOURCE,provider_id=EXTRA.id,source=EXTRA.name,source_url=EXTRA.url)
                session.providers[EXTRA.id]=(extra,)
                calls=[]
                def fetch(**kw):
                    calls.extend(kw['providers']);kw['on_provider'](CROSSWIRE,[RESOURCE],None,{})
                    return CatalogueResult((RESOURCE,),{})
                session.refresh(fetch,False,(CROSSWIRE,)).result(10)
                session.prepare.submit(lambda:None).result(10)
                self.assertEqual(calls,[CROSSWIRE]);self.assertEqual(session.providers[EXTRA.id],(extra,))
                self.assertEqual({r.id for r in session.snapshot.resources},{RESOURCE.id,extra.id})
            finally:session.close()


@unittest.skipUnless(os.environ.get('DISPLAY'),'Requires GTK')
class LibraryPolishTests(unittest.TestCase):
    def setUp(self):
        from bible.ui import Application,Window
        self.root=Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.app=Application.get_default() or Application();self.app.register()
        self.enterContext(patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False))
        self.window=Window(self.app,Library(self.root/'translations'));self.window.present()

    def tearDown(self):
        close_test_dialogs();self.window.close()

    def test_welcome_skip_restart_and_later_empty_download_route(self):
        w=self.window
        self.assertEqual(w.main_pages.get_visible_child_name(),'welcome')
        self.assertEqual(w.library.installed(),[])
        w.welcome_skip.emit('clicked');self.assertEqual(w.main_pages.get_visible_child_name(),'reading')
        self.assertTrue(w.active_tab.download_bible.get_visible())
        w.close()
        from bible.ui import Window
        self.window=w=Window(self.app,w.library);w.present()
        self.assertEqual(w.main_pages.get_visible_child_name(),'reading')
        w.active_tab.download_bible.emit('clicked');self.assertEqual(w.catalogue_window.kind.get_selected(),0)

    def test_narrow_reader_keeps_mouse_routes_after_menu_cleanup(self):
        w=self.window;w.welcome_skip.emit('clicked');w.set_default_size(360,700);spin()
        for button in [w.tab_new_button,w.space_selector,w.study_button]:
            self.assertTrue(button.get_visible());self.assertTrue(button.get_mapped())
        self.assertFalse(w.new_tab_button.get_visible())
        before=w.view.get_n_pages();w.tab_new_button.emit('clicked');self.assertEqual(w.view.get_n_pages(),before+1)
        w.space_selector.set_selected(1);self.assertEqual(w.main_pages.get_visible_child_name(),'notes')

    def test_global_menu_preferences_shortcuts_about_and_notes_share_routes(self):
        w=self.window
        self.assertFalse(hasattr(w,'library_button'))
        self.assertEqual([b.get_action_name() for b in w.menu.global_actions],['win.translations','win.preferences','win.shortcuts','win.about'])
        w.lookup_action('preferences').activate(None);self.assertTrue(w.preferences_window.get_visible());w.preferences_window.close()
        w.lookup_action('shortcuts').activate(None);self.assertTrue(w.shortcuts_window.get_visible());w.shortcuts_window.close()
        w.lookup_action('about').activate(None)
        self.assertEqual(w.about_window.get_application_name(),'Bible');self.assertEqual(w.about_window.get_version(),'0.1.0-alpha');w.about_window.close()
        notes=w.open_notes();self.assertEqual(len(notes.main_menu.global_actions),4)
        w.lookup_action('translations').activate(None);self.assertTrue(w.catalogue_window.get_visible())
        self.assertEqual(w.main_pages.get_visible_child_name(),'notes')

    def test_general_preferences_reuse_persist_and_do_not_change_library_or_reader(self):
        from bible.application_surfaces import show_preferences
        from bible.ui import Adw,Window
        w=self.window;settings=w.application_settings
        settings.set('library_language','azb')
        p=show_preferences(w)
        self.assertIsInstance(p,Adw.PreferencesDialog)
        self.assertIs(show_preferences(w),p)
        p.language.set_selected(1);p.appearance.set_selected(2)
        self.assertEqual(settings.language,'azb')
        self.assertEqual(w.preferences.value.mode,'system')
        self.assertTrue(w.reading_style.manager.get_dark())
        w.preferences.value.mode='day';w.apply_appearance(reflow=False)
        self.assertFalse(w.reading_style.manager.get_dark())
        p.restore_tabs.set_active(False)
        count=w.view.get_n_pages();self.assertEqual(w.view.get_n_pages(),count)
        restored=ApplicationSettings(self.root)
        self.assertEqual(restored.value['ui_language'],'fr')
        self.assertFalse(restored.value['restore_tabs'])
        self.assertEqual(restored.language,'azb')
        p.close();w.new_tab();w.save_session();w.close()
        self.window=w=Window(self.app,w.library);w.present()
        self.assertEqual(w.view.get_n_pages(),1)
        w.preferences.value.mode='system';settings.set('interface_appearance','system');w.reading_style.apply_mode()

    def test_cold_offline_language_inventory_remains_searchable_and_empty_is_truthful(self):
        w=self.window;d=w.open_library();spin(lambda:not d.busy)
        d.language.prepare_languages()
        spin(lambda:'azb' in d.languages and len(d.languages)>1000,timeout=30)
        self.assertIsNone(d.session.language_future.exception())
        d.language.search.set_text('azb');d.language.filter()
        spin(lambda:d.language.strings.get_n_items()==2)
        d.language.activate(None,1)
        self.assertEqual(d.language_choice,'azb');self.assertFalse(d.filtered_resources)
        self.assertTrue(d.empty.get_visible())
        d.kind.set_selected(1);self.assertEqual(d.language_choice,'azb')
        d.close();d=w.open_library();self.assertEqual(d.language_choice,'azb')

    def test_filter_change_during_refresh_rejects_stale_type_and_language_rows(self):
        w=self.window;w.application_settings.set('library_language','en')
        d=w.open_library();spin(lambda:not d.busy)
        french=replace(RESOURCE,name='FrenchCommentary',language='fra',driver='RawCom',category='Commentaries')
        resources=(RESOURCE,french,replace(RESOURCE,name='OtherEnglish'))
        release=threading.Event();self.addCleanup(release.set)
        def fetch(**kwargs):
            kwargs['on_provider'](CROSSWIRE,resources,None,{})
            release.wait(3);return CatalogueResult(resources,{})
        before=(w.active_tab.state.resource,w.active_tab.state.reference,list(w.active_tab.state.history))
        with patch('bible.catalogue_window.catalogue',side_effect=fetch):
            d.load_catalogue();spin(lambda:bool(d.resources))
            d.kind.set_selected(1);d.language.set_selected(d.languages.index('fr'))
            d.source_filter.set_selected(d.source_ids.index(EXTRA.id));self.assertFalse(d.filtered_resources)
            d.source_filter.set_selected(d.source_ids.index(CROSSWIRE.id));release.set()
            spin(lambda:not d.busy)
        self.assertEqual(d.filtered_resources,[french]);self.assertEqual(d.choice_model.get_n_items(),1)
        self.assertEqual(d.choice_model.get_item(0).resource,french)
        self.assertEqual(before,(w.active_tab.state.resource,w.active_tab.state.reference,w.active_tab.state.history))

    def test_language_choice_empty_alias_and_type_persistence_without_fetch(self):
        w=self.window;w.application_settings.set('library_language','fr')
        d=w.open_library();spin(lambda:not d.busy)
        d.resources=[replace(RESOURCE,name='French',language='fra'),replace(RESOURCE,name='English'),replace(RESOURCE,name='Study',driver='RawCom',category='Commentaries',language='fre')]
        d.update_languages();spin(lambda:not d.busy)
        self.assertEqual([r.name for r in d.filtered_resources],['French'])
        d.kind.set_selected(1);spin(lambda:not d.busy)
        self.assertEqual([r.name for r in d.filtered_resources],['Study'])
        d.language.set_selected(d.languages.index('en'));spin(lambda:not d.busy)
        self.assertEqual(d.filtered_resources,[]);self.assertTrue(d.empty.get_visible())
        d.kind.set_selected(0);spin(lambda:not d.busy);self.assertEqual([r.name for r in d.filtered_resources],['English'])
        d.close();d=w.open_library();self.assertEqual(d.language_choice,'en')
        d.language.set_selected(0);self.assertEqual(w.application_settings.language,'')

    def test_install_refresh_never_selects_resource_explicit_read_targets_intended_tab(self):
        w=self.window;w.welcome_skip.emit('clicked');initial=w.active_tab
        from bible.session import TabState
        second=w.append_tab(TabState()).get_child()
        context=w.library_context(initial,'bible')
        installed_fixture(self.root,'Test')
        w.view.set_selected_page(w.view.get_page(second));w.resource_installed('Test')
        self.assertIsNone(initial.state.resource);self.assertIsNone(second.state.resource)
        self.assertTrue(w.open_installed_resource('Test',context))
        self.assertIs(w.active_tab,initial);self.assertEqual(initial.state.resource,'Test')
        self.assertIsNone(second.state.resource)
        w.view.close_page(w.view.get_page(initial));spin()
        before=(w.active_tab.state.resource,w.active_tab.state.reference)
        self.assertFalse(w.open_installed_resource('Test',context));self.assertEqual(before,(w.active_tab.state.resource,w.active_tab.state.reference))

    def test_contextual_downloads_preserve_passage_and_installed_selection(self):
        w=self.window;installed_fixture(self.root,'Test');w.open_installed_resource('Test')
        before=(w.active_tab.state.resource,w.active_tab.state.reference,list(w.active_tab.state.history))
        for chooser,kind,destination in [(w.primary_version,0,'bible'),(w.compared_version,0,'comparison')]:
            chooser.download_more.emit('clicked');d=w.catalogue_window
            self.assertEqual(d.kind.get_selected(),kind);self.assertEqual(d.open_context[1],destination);d.close()
            self.assertEqual(before,(w.active_tab.state.resource,w.active_tab.state.reference,w.active_tab.state.history))
        w.contextual_library('commentary','commentary');self.assertEqual(w.catalogue_window.kind.get_selected(),1)
        self.assertEqual(before,(w.active_tab.state.resource,w.active_tab.state.reference,w.active_tab.state.history))

    def test_library_install_and_explicit_read_keep_unsaved_note_guard(self):
        w=self.window
        installed_fixture(self.root,'Test');installed_fixture(self.root,'Other')
        w.open_installed_resource('Test');space=w.open_notes();space.create_note();editor=space.editor
        editor.body.get_buffer().set_text('Actual unsaved draft — keep this text')
        original=w.active_tab.state.resource
        w.resource_installed('Other')
        self.assertEqual(w.main_pages.get_visible_child_name(),'notes')
        self.assertEqual(editor.body.get_buffer().props.text,'Actual unsaved draft — keep this text')
        with patch.object(w.notes_store,'save',side_effect=OSError('Test write failure')):
            w.open_installed_resource('Other')
        self.assertEqual(w.active_tab.state.resource,original)
        self.assertTrue(editor._confirmation.get_visible())
        editor._confirmation.response('cancel')
        self.assertEqual(w.active_tab.state.resource,original)
        self.assertEqual(editor.body.get_buffer().props.text,'Actual unsaved draft — keep this text')
        editor._discard=True;editor.close()
