import os,json,shutil
from pathlib import Path
from unittest.mock import patch
from bible.ui import Application,Window,Library,Gtk
import time
from gi.repository import GLib
def spin(until=lambda:True,duration=.1):
 start=time.monotonic()
 while time.monotonic()-start<25:
  GLib.MainContext.default().iteration(False)
  if time.monotonic()-start>=duration and until():return
  time.sleep(.005)
 raise AssertionError('Capture did not settle')
from tools.check_alpha_ui import X11Input
from PIL import ImageGrab
phase=os.environ.get('CAPTURE_PHASE','after');root=Path('/work/library-63-71-108');profile=root/('profile-'+phase)
profile.mkdir(exist_ok=True)
if not (profile/'translations').exists():(profile/'translations').symlink_to('/work/visual-polish/profile/translations')
shutil.copytree(root/'cache-before',profile/'catalogue-cache',dirs_exist_ok=True)
app=Application();app.register();native=X11Input();out=root/'captures';out.mkdir(exist_ok=True);report=[]
Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
def shot(name,window,dialog=None):
 native.move_at(window,2,2);spin(duration=.3);ImageGrab.grab().save(out/(phase+'-'+name+'.png'))
 report.append(dict(file=phase+'-'+name+'.png',scale=window.get_scale_factor(),window=[window.get_width(),window.get_height()],dialog=[dialog.get_width(),dialog.get_height()] if dialog else None))
with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):
 w=Window(app,Library(profile/'translations'));w.set_default_size(960,800);w.present();spin()
 for theme,mode in [('light','day'),('dark','night')]:
  for width,label in [(960,'normal'),(360,'small')]:
   w.set_default_size(width,800);w.appearance.update('mode',mode);w.active_tab.navigate('FreSegond1910','John.3.16');spin()
   d=w.open_library('bible');d.set_default_size(min(width,560),700);spin(lambda:not d.busy)
   if phase=='after':d.language.set_selected(d.languages.index('fr'));spin(lambda:not d.busy)
   shot(f'{theme}-{label}-bibles',w,d)
   d.kind.set_selected(1);spin(lambda:not d.busy);shot(f'{theme}-{label}-commentaries',w,d)
   d.language.set_selected(0);spin(lambda:not d.busy);shot(f'{theme}-{label}-all-commentaries',w,d)
   d.close();w.present();spin();w.menu.popup();shot(f'{theme}-{label}-menu',w);w.menu.popdown()
   w.primary_version.popup();shot(f'{theme}-{label}-version',w);w.primary_version.popdown()
  emptyroot=root/(phase+'-empty-'+theme)
  # Leave a new empty translations directory only: genuinely clean first use.
  if emptyroot.exists():shutil.rmtree(emptyroot)
  empty=Window(app,Library(emptyroot/'translations'));empty.set_default_size(960,800);empty.appearance.update('mode',mode);empty.present();spin();shot(f'{theme}-welcome',empty)
  empty.set_default_size(360,700);spin();shot(f'{theme}-welcome-small',empty)
  if hasattr(empty,'welcome_skip'):empty.welcome_skip.emit('clicked');shot(f'{theme}-skipped',empty)
  empty.close();w.present();spin()
 w.close();native.close()
(root/(phase+'-capture-metrics.json')).write_text(json.dumps(report,indent=2)+'\n')
print('GTK',phase,len(report),'captures PASS',flush=True)
