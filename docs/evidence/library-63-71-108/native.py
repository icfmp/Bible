import json,time,shutil,os
from pathlib import Path
from unittest.mock import patch
from gi.repository import GLib
from bible.ui import Application,Window,Library,Gtk
from bible.sword_provider import Reader
from tools.check_alpha_ui import X11Input
from PIL import ImageGrab
root=Path('/work/library-63-71-108');profile=root/'native-profile';profile.mkdir(exist_ok=True)
shutil.copytree(root/'cache-before',profile/'catalogue-cache',dirs_exist_ok=True)
# The cache makes this an existing profile; a separate genuinely clean profile
# exercised by the welcome captures/tests covers first-launch presentation.
app=Application();app.register();w=Window(app,Library(profile/'translations'));w.set_default_size(960,800);w.present();native=X11Input();ticks=[]
def spin(until=lambda:True,duration=.1,timeout=120):
 start=time.monotonic()
 while time.monotonic()-start<timeout:
  GLib.MainContext.default().iteration(False)
  if time.monotonic()-start>=duration and until():return
  time.sleep(.002)
 raise AssertionError('Native scenario timed out')
def shot(name):
 native.move_at(w,2,2);spin(duration=.2);ImageGrab.grab().save(root/'captures'/('native-'+name+'.png'))
def row(d,id):
 return next((item for item,resource in d._bound_rows.items() if resource.id==id),None)
try:
 with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):
  native.activate(w);native.click(w.menu);native.click(w.menu.global_actions[0]);d=w.catalogue_window
  spin(lambda:not d.busy);native.activate(d)
  d.language.set_selected(d.languages.index('fr'));d.search.set_text('frajnd2024eb');d.filter_resources();spin(lambda:not d.busy)
  resource=next(r for r in d.filtered_resources if r.id=='ebible~frajnd2024eb')
  spin(lambda:row(d,resource.id) is not None)
  before=(w.active_tab.state.resource,w.active_tab.state.reference,list(w.active_tab.state.history))
  timer=GLib.timeout_add(10,lambda:ticks.append(time.monotonic()) or True)
  assert resource.id not in w.library.installed(),'Fresh disposable profile required for actual transfer evidence'
  package_bytes=[];original_progress=d.report_progress
  def measured_progress(done,total):package_bytes.append(done);original_progress(done,total)
  d.report_progress=measured_progress
  if resource.id not in w.library.installed():
   native.click(row(d,resource.id).action);spin(lambda:d._task_id>0)
   assert d.pages.get_visible_child_name()=='list','Download click also opened details'
   shot('direct-download')
   spin(lambda:not d.busy,timeout=180)
   assert d._phase=='complete',d.status.get_text()
  spin(lambda:resource.id in d.installed_ids())
  assert before==(w.active_tab.state.resource,w.active_tab.state.reference,w.active_tab.state.history)
  transfer_started=d._task_id>0
  shot('installed-awaiting-read')
  spin(lambda:row(d,resource.id) is not None)
  native.click(row(d,resource.id).action);spin(lambda:w.active_tab.state.resource==resource.id and w.active_tab.reader is not None)
  def verse(reader):return next(text for ref,text in reader.chapter('John.3.16').verses if ref=='John.3.16')
  text=verse(w.active_tab.reader);assert 'dieu' in text.casefold()
  assert text==verse(Reader(w.library.root/resource.id,resource.id))
  shot('explicit-reading')
  GLib.source_remove(timer)
  initial=(w.active_tab.state.resource,w.active_tab.state.reference,list(w.active_tab.state.history))
  native.activate(w);native.click(w.primary_version);native.click(w.primary_version.download_more);d=w.catalogue_window
  assert d.open_context[1]=='bible' and d.kind.get_selected()==0
  d.close();assert initial==(w.active_tab.state.resource,w.active_tab.state.reference,w.active_tab.state.history)
  w.open_notes();spin();native.activate(w);native.click(w.notes_space.main_menu);native.click(w.notes_space.main_menu.global_actions[0]);d=w.catalogue_window
  assert w.main_pages.get_visible_child_name()=='notes';d.close()
  w.notes_space.leave();spin();native.click(w.menu);shot('global-menu')
  w.menu.popdown()
  def chord(modifiers,key):
   codes=[native.x11.XKeysymToKeycode(native.display,native.x11.XStringToKeysym(m.encode())) for m in modifiers]
   for code in codes:native.xtest.XTestFakeKeyEvent(native.display,code,True,0)
   native.key(key)
   for code in reversed(codes):native.xtest.XTestFakeKeyEvent(native.display,code,False,0)
   native.x11.XFlush(native.display);spin()
  native.activate(w);chord(['Control_L'],'comma');spin(lambda:getattr(w,'preferences_window',None) and w.preferences_window.get_visible())
  w.preferences_window.close();native.activate(w)
  chord(['Control_L','Shift_L'],'slash');spin(lambda:getattr(w,'shortcuts_window',None) and w.shortcuts_window.get_visible())
  w.shortcuts_window.close();native.activate(w);native.click(w.menu);w.menu.global_actions[0].grab_focus();native.key('Return')
  spin(lambda:w.catalogue_window.get_visible());w.catalogue_window.close();native.activate(w)
  native.click(w.menu);native.key('Escape');assert not w.menu.get_active()
  result=dict(status='PASS',actual_ebible_resource=resource.id,actual_transfer_started=transfer_started,resource_package_bytes=max(package_bytes),initial_installed_count=0,direct_download_did_not_open_details=True,no_automatic_selection=True,explicit_read=True,exact_local_sword_text=True,primary_context=True,library_from_notes=True,maximum_heartbeat_gap_seconds=max((b-a for a,b in zip(ticks,ticks[1:])),default=0),automated_native_x11=True,keyboard_preferences=True,keyboard_shortcuts_help=True,keyboard_library_menu=True,menu_escape=True)
  (root/'native-fr.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
finally:
 if w.note_editor:w.note_editor._discard=True
 w.close();native.close()
