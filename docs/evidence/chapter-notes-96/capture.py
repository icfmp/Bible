import os,time,json,shutil
from pathlib import Path
from bible.ui import Application,Window,Library,Gtk,GLib
from tools.check_alpha_ui import X11Input
from PIL import ImageGrab
root=Path('/work/chapter-notes-96');phase=os.environ.get('CAPTURE_PHASE','before');profile=root/('profile-'+phase)
if not profile.exists():shutil.copytree('/work/notes-75-96/profile-before',profile)
app=Application();app.register();native=X11Input();out=root/'captures';out.mkdir(exist_ok=True)
def spin(seconds=.35):
 end=time.monotonic()+seconds
 while time.monotonic()<end:GLib.MainContext.default().iteration(False);time.sleep(.003)
w=Window(app,Library(profile/'translations'));w.present();spin();tab=w.active_tab;tab.navigate('FreSegond1910','Acts.1.8');spin()
if not any(n.start=='Acts.1.2' for n in w.notes_store.all()):
 for v in [2,8,8,15,25]:w.notes_store.save(f'Note de lecture sur Actes 1:{v}. **Observation personnelle** — données de validation, texte conservé.', ['Étude'],versification=tab.reader.versification,start=f'Acts.1.{v}',end=f'Acts.1.{v}',origin_translation='FreSegond1910',origin_language='fr')
 w.highlights.set(tab.reader.versification,['Acts.1.8'],'blue','FreSegond1910')
report=[]
def shot(label):
 native.move_at(w,2,2);spin();name=phase+'-'+label+'.png';ImageGrab.grab().save(out/name);report.append(name)
try:
 for theme,mode in [('light','day'),('dark','night')]:
  w.appearance.update('mode',mode)
  for width,size in [(1280,'wide'),(360,'small')]:
   w.set_default_size(width,800)
   for comparison,kind in [(None,'single'),('KJV','comparison')]:
    tab.state.comparison=comparison;w.sync_comparison();w.study_button.set_active(False);tab.update_notes(force=True);spin();shot(theme+'-'+size+'-'+kind+'-reader')
    w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes');w.study.notes.refresh(force=True);spin();shot(theme+'-'+size+'-'+kind+'-notes')
  tab.state.comparison=None;w.sync_comparison();w.set_default_size(360,600);Gtk.Settings.get_default().set_property('gtk-xft-dpi',147456);spin();shot(theme+'-small-short-large-text-notes')
  if phase=='after':
   w.study.notes.suspend_following();spin();shot(theme+'-small-short-large-text-paused');w.study.notes.resume_following()
  Gtk.Settings.get_default().set_property('gtk-xft-dpi',98304)
 if phase=='after':
  w.set_default_size(1280,800);w.appearance.update('mode','day');tab.state.comparison=None;w.sync_comparison();tab.navigate('FreSegond1910','Acts.1.1');w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes');spin(1)
  native.wheel(tab.text,14);spin(1);shot('native-bible-wheel-forward')
  forward=tab.state.reference;native.wheel(tab.text,-8);spin(1);shot('native-bible-wheel-back')
  assert tab.state.reference!=forward
finally:w.close();native.close()
(root/(phase+'-captures.json')).write_text(json.dumps(report,indent=2)+'\n');print('PASS',phase,len(report),'actual GTK captures')
