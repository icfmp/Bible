import json,time,shutil
from pathlib import Path
from gi.repository import GLib
from bible.ui import Application,Window,Library,Gtk
from PIL import ImageGrab
root=Path('/work/library-63-71-108');assert len(Path('/proc/net/route').read_text().splitlines())<=1
app=Application();app.register();out=root/'captures'
def spin(until=lambda:True,duration=.1):
 start=time.monotonic()
 while time.monotonic()-start<30:
  GLib.MainContext.default().iteration(False)
  if time.monotonic()-start>=duration and until():return
  time.sleep(.003)
 raise AssertionError('Offline UI did not settle')
def shot(name):spin(duration=.25);ImageGrab.grab().save(out/('offline-en-'+name+'.png'))
fresh=root/'offline-first'
if fresh.exists():shutil.rmtree(fresh)
w=Window(app,Library(fresh/'translations'));w.set_default_size(360,700);w.present();spin()
assert w.main_pages.get_visible_child_name()=='welcome'
for theme,mode in [('light','day'),('dark','night')]:
 w.appearance.update('mode',mode);shot(theme+'-welcome')
w.welcome_skip.emit('clicked');d=w.open_library('bible');d.source_filter.set_selected(5);d.load_catalogue(force=False);spin(lambda:not d.busy)
assert not d.resources and not w.library.installed() and 'eBible' in d.refresh_status.get_text()
shot('first-use-unavailable');d.close();w.close();w=Window(app,Library(fresh/'translations'));w.present();spin()
assert w.main_pages.get_visible_child_name()=='reading' and w.active_tab.download_bible.get_visible();w.close()
profile=root/'offline-existing'
if profile.exists():shutil.rmtree(profile)
profile.mkdir();(profile/'translations').symlink_to(root/'native-profile/translations');shutil.copytree(root/'cache-after',profile/'catalogue-cache')
w=Window(app,Library(profile/'translations'));w.set_default_size(960,800);w.present();spin()
assert w.main_pages.get_visible_child_name()=='reading' and w.active_tab.reader
w.active_tab.navigate('ebible~frajnd2024eb','John.3.16')
before=(w.active_tab.state.resource,w.active_tab.state.reference,list(w.active_tab.state.history))
d=w.open_library('bible');spin(lambda:not d.busy);d.language.set_selected(d.languages.index('fr'));spin(lambda:not d.busy)
assert 'ebible~frajnd2024eb' in [r.id for r in d.filtered_resources]
for theme,mode in [('light','day'),('dark','night')]:
 w.appearance.update('mode',mode);shot(theme+'-installed-library')
d.close();assert before==(w.active_tab.state.resource,w.active_tab.state.reference,w.active_tab.state.history)
w.open_notes();w.notes_space.main_menu.popup();shot('notes-global-menu');w.notes_space.main_menu.popdown();w.notes_space.leave()
w.lookup_action('preferences').activate(None);shot('preferences');w.preferences_window.close()
w.lookup_action('shortcuts').activate(None);shot('shortcuts');w.shortcuts_window.close()
w.lookup_action('about').activate(None);shot('about');w.about_window.close();w.close()
w=Window(app,Library(profile/'translations'));w.present();spin()
assert (w.active_tab.state.resource,w.active_tab.state.reference,w.active_tab.state.history)==before
assert w.application_settings.language=='fr';w.close()
result=dict(status='PASS',network_disabled=True,english_welcome_light_dark=True,first_use_failure_settles=True,skip_not_replayed_on_restart=True,existing_readable_resource_precedes_welcome=True,offline_installed_metadata=True,explicit_language_restart=True,notes_global_menu=True,preferences_shortcuts_about=True,session_and_history_preserved=True)
(root/'native-offline-en.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
