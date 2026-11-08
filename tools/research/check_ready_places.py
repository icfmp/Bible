"""Real native photo/cache/candidate-place validation, disposable profiles only."""
import argparse,inspect,json,hashlib
from pathlib import Path
from unittest.mock import patch
from bible.ui import Application,Window,Library,Gtk
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input
from tools.check_client_feedback import Screen
p=argparse.ArgumentParser();p.add_argument('profile',type=Path);p.add_argument('output',type=Path);p.add_argument('--prepare',action='store_true');p.add_argument('--require-packaged',action='store_true');p.add_argument('--resource',default='FreSegond1910');p.add_argument('--dark',action='store_true');p.add_argument('--narrow',action='store_true');a=p.parse_args()
root=a.profile;assert (root/'.ready-batch-test-profile').is_file() or root.name=='study-navigation-real','Disposable profile required'
if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
from bible.place_data import PlaceData
if a.prepare and PlaceData(root/'study-data').revision is None:PlaceData(root/'study-data').install()
out=a.output;out.mkdir(exist_ok=True,parents=True)
app=Application();app.register();w=Window(app,Library(root/'translations'));w.set_default_size(1280,900);w.present();spin();native=X11Input();screen=Screen(native)
w.appearance.update('mode','night' if a.dark else 'day')
report=dict(app_import=inspect.getfile(Window),complete=False,cases=[],dark=a.dark,narrow=a.narrow)
notes=w.notes_store.all()
def walk(widget):
 yield widget;child=widget.get_first_child()
 while child:yield from walk(child);child=child.get_next_sibling()
def open_case(ref,identity):
 tab=w.active_tab;tab.navigate(a.resource,ref);spin(lambda:not tab._restoring_scroll)
 host=w.open_passage_study(context=(tab.state.resource,tab.reader,ref,ref),mode="map");dialog=host.places
 if a.narrow:host.set_default_size(360,600)
 host.present();spin(lambda:not dialog.pending,timeout=30)
 if a.narrow:assert dialog.get_width()<=360,dialog.get_width()
 place=next(p for p in dialog.rows if p['id']==identity);dialog.open_place(place);spin(duration=.4);native.activate(dialog.host)
 return dialog,place
try:
 dialog,place=open_case('Mark.7.1','a15257a')
 button=next((x for x in walk(dialog) if isinstance(x,Gtk.Button) and x.get_visible() and x.get_label() and ('photograph' in x.get_label() or 'photographie' in x.get_label())),None)
 if button:
  native.click(button);spin(lambda:not button.get_visible(),timeout=35)
 hero=next(x for x in walk(dialog) if hasattr(x,'photo_path'))
 spin(lambda:hero.get_mapped() and hero.get_width()>100 and hero.get_child().get_width()>100 and hero.get_child().get_height()>=180,duration=.3)
 from bible.place_context import localized
 expected=dialog.contexts.entries(place)[0]['images'][0]
 digest=hashlib.sha256(hero.photo_path.read_bytes()).hexdigest();assert digest==expected['sha256']
 assert any(expected['author'] in x.get_text() and expected['license'] in x.get_text() for x in walk(dialog) if isinstance(x,Gtk.Label))
 screen.grab(out/'jerusalem-photo.png');report['hero_size']=[hero.get_child().get_width(),hero.get_child().get_height()];native.click(hero);spin()
 photo=next(x for x in Gtk.Window.list_toplevels() if x is not dialog.host and x is not w and x.get_visible() and x.get_transient_for() is dialog.host)
 assert photo.get_title()==localized(expected['caption']);photo.close();spin();dialog.close();spin()
 with patch('urllib.request.urlopen',side_effect=AssertionError('Offline verification')):
  dialog,place=open_case('Mark.7.1','a15257a')
  spin(lambda:any(hasattr(x,'photo_path') for x in walk(dialog)),timeout=10)
  assert not any(isinstance(x,Gtk.Button) and x.get_visible() and x.get_label() and ('photograph' in x.get_label() or 'photographie' in x.get_label()) for x in walk(dialog))
  report['cases'].append(dict(id=place['id'],photo_sha256=digest,offline_photo_reopen=True,source=place['source_url'],status=place['status']))
  dialog.close();spin()
 for ref,identity in [('Luke.24.13','ae7274b'),('Gen.4.16','a1ad8e1')]:
  dialog,place=open_case(ref,identity)
  assert not any(hasattr(x,'photo_path') for x in walk(dialog))
  if identity=='a1ad8e1':assert dialog.map_widget is None and place['status']=='unknown'
  else:assert len(place['candidates'])==6 and place['status']=='disputed'
  screen.grab(out/(identity+'.png'))
  report['cases'].append(dict(id=identity,candidates=len(place['candidates']),status=place['status'],no_photo=True))
  dialog.close();spin()
 assert w.notes_store.all()==notes
 report['complete']=True
finally:
 for dialog in list(Gtk.Window.list_toplevels()):
  if dialog is not w:dialog.close()
 w.close();native.close();(out/'result.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
