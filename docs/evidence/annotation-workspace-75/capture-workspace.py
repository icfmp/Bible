import os,time,json,shutil
from pathlib import Path
from bible.ui import Application,Window,Library,Gtk,GLib
from tools.check_alpha_ui import X11Input
from PIL import ImageGrab
root=Path('/work/notes-75-96');phase=os.environ.get('CAPTURE_PHASE','before');profile=root/('profile-'+phase)
if not profile.exists():shutil.copytree('/work/library-63-71-108/preservation-profile',profile)
app=Application();app.register();native=X11Input();out=root/'captures';out.mkdir(exist_ok=True)
def spin(seconds=.4):
 until=time.monotonic()+seconds
 while time.monotonic()<until:GLib.MainContext.default().iteration(False);time.sleep(.003)
w=Window(app,Library(profile/'translations'));w.present();spin()
notes=w.notes_store.all()
if len(notes)<3:
 for start,body,labels in [('John.3.16','Comparer ce passage avec Jean 3:17. **Notes de lecture**, données de validation.', ['Étude']),('John.3.17','Une seconde note distincte, avec du texte à rechercher : espérance.', ['Espérance'])]:w.notes_store.save(body,labels,versification='Segond',start=start,end=start,origin_translation='FreSegond1910',origin_language='fr')
notes=w.notes_store.all();report=[]
try:
 for theme,mode in [('light','day'),('dark','night')]:
  w.appearance.update('mode',mode)
  for width,size in [(1280,'wide'),(360,'small')]:
   w.set_default_size(width,800);space=w.open_notes();space.back_to_list();spin();name=f'{phase}-{theme}-{size}-list.png';native.move_at(w,2,2);ImageGrab.grab().save(out/name);report.append(name)
   space.open_note(notes[0]);spin();name=f'{phase}-{theme}-{size}-detail.png';ImageGrab.grab().save(out/name);report.append(name)
   if space.editor:space.editor.close()
   space.leave();spin()
finally:w.close();native.close()
(root/(phase+'-captures.json')).write_text(json.dumps(report,indent=2)+'\n');print('PASS',phase,len(report),'native GTK workspace captures')
