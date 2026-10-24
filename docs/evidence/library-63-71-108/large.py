import os,json,time,shutil
from pathlib import Path
from unittest.mock import patch
from bible.ui import Application,Window,Library,Gtk,GLib
from tools.check_alpha_ui import X11Input
from tests.test_appearance import SystemStyleOverride
from PIL import ImageGrab
root=Path('/work/library-63-71-108');phase=os.environ.get('CAPTURE_PHASE','after');profile=root/('profile-'+phase)
def spin(until=lambda:True,duration=.1):
 start=time.monotonic()
 while time.monotonic()-start<30:
  GLib.MainContext.default().iteration(False)
  if time.monotonic()-start>=duration and until():return
  time.sleep(.003)
 raise AssertionError('Large text capture did not settle')
app=Application();app.register();native=X11Input();w=Window(app,Library(profile/'translations'));w.set_default_size(360,700);w.present();spin();report=[]
def shot(name,dialog=None):
 native.move_at(w,1,1);spin(duration=.3);name=phase+'-'+name+'.png';ImageGrab.grab().save(root/'captures'/name)
 report.append(dict(file=name,window=[w.get_width(),w.get_height()],dialog=[dialog.get_width(),dialog.get_height()] if dialog else None,dpi=Gtk.Settings.get_default().get_property('gtk-xft-dpi'),scale=w.get_scale_factor()))
settings=Gtk.Settings.get_default();dpi=settings.get_property('gtk-xft-dpi')
with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):
 try:
  for theme,mode in [('light','day'),('dark','night')]:
   settings.set_property('gtk-xft-dpi',147456);w.appearance.update('mode',mode);spin()
   d=w.open_library('bible');d.set_default_size(360,700);spin(lambda:not d.busy)
   if phase=='after':d.language.set_selected(d.languages.index('fr'));spin(lambda:not d.busy)
   shot(theme+'-library-large-text',d);d.close();w.menu.popup();shot(theme+'-menu-large-text');w.menu.popdown()
   emptyroot=root/(phase+'-large-empty-'+theme)
   if emptyroot.exists():shutil.rmtree(emptyroot)
   empty=Window(app,Library(emptyroot/'translations'));empty.set_default_size(360,700);empty.appearance.update('mode',mode);empty.present();spin();shot(theme+'-welcome-large-text');empty.close();w.present();spin()
   if phase=='after':w.open_notes();w.notes_space.main_menu.popup();shot(theme+'-notes-large-text');w.notes_space.main_menu.popdown();w.notes_space.leave()
  settings.set_property('gtk-xft-dpi',dpi)
  with SystemStyleOverride() as override:
   override.set(dark=False,high=True);w.appearance.update('mode','day');spin()
   w.menu.popup();shot('high-contrast-menu');w.menu.popdown()
   d=w.open_library('bible');d.set_default_size(360,700);spin(lambda:not d.busy);shot('high-contrast-library',d);d.close()
 finally:settings.set_property('gtk-xft-dpi',dpi);w.close();native.close()
(root/(phase+'-large-metrics.json')).write_text(json.dumps(report,indent=2)+'\n');print('GTK',phase,len(report),'large/contrast captures PASS',flush=True)
