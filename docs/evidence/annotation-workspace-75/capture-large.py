import os,json,time
from pathlib import Path
from bible.ui import Application,Window,Library,Gtk,GLib
from tools.check_alpha_ui import X11Input
from tests.test_appearance import SystemStyleOverride
from PIL import ImageGrab
root=Path('/work/notes-75-96');phase=os.environ.get('CAPTURE_PHASE','after');app=Application();app.register();native=X11Input();profile=root/('profile-'+phase)
def spin(seconds=.35):
 end=time.monotonic()+seconds
 while time.monotonic()<end:GLib.MainContext.default().iteration(False);time.sleep(.003)
w=Window(app,Library(profile/'translations'));w.present();spin();settings=Gtk.Settings.get_default();dpi=settings.get_property('gtk-xft-dpi');report=[]
def shot(name):
 native.move_at(w,2,2);spin();name=phase+'-'+name+'.png';ImageGrab.grab().save(root/'captures'/name);report.append(name)
try:
 for mode,theme in [('day','light'),('night','dark')]:
  settings.set_property('gtk-xft-dpi',147456);w.appearance.update('mode',mode)
  for width,height,label in [(1280,800,'wide-large-text'),(360,800,'small-large-text'),(360,600,'small-short-large-text')]:
   w.set_default_size(width,height);s=w.open_notes();s.back_to_list();spin();shot(theme+'-'+label+'-list')
   s.open_note(w.notes_store.all()[0]);spin();shot(theme+'-'+label+'-detail')
   if phase=='after':
    s.editor.labels.entry.grab_focus();spin();shot(theme+'-'+label+'-labels')
    if width==360:
     s.back_to_list();s.filter_button.set_active(True);spin();shot(theme+'-'+label+'-filters');s.filter_button.set_active(False)
   if s.editor:s.editor.close()
   s.leave();spin()
 settings.set_property('gtk-xft-dpi',dpi)
 with SystemStyleOverride() as override:
  override.set(dark=False,high=True);w.appearance.update('mode','day');w.set_default_size(960,800);s=w.open_notes();s.open_note(w.notes_store.all()[0]);spin();shot('high-contrast-detail')
  if s.editor:s.editor.close()
finally:settings.set_property('gtk-xft-dpi',dpi);w.close();native.close()
(root/(phase+'-large-captures.json')).write_text(json.dumps(report,indent=2)+'\n');print('PASS',phase,len(report),'real GTK large-text and high-contrast captures')
