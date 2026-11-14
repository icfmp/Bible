"""Actual Library lifecycle controls over existing public resource packages."""
import argparse,hashlib,inspect,json,os
from dataclasses import asdict
from pathlib import Path
from bible.ui import Application,Window,Library,Gtk
from gi.repository import Adw
from bible.library import source_fingerprints
from bible.i18n import tr
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input
from tools.check_client_feedback import Screen

p=argparse.ArgumentParser();p.add_argument('profile',type=Path);p.add_argument('output',type=Path);p.add_argument('--require-packaged',action='store_true');a=p.parse_args()
assert (a.profile/'.ready-batch-test-profile').is_file()
if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
a.output.mkdir(parents=True,exist_ok=True);library=Library(a.profile/'translations')
expected={'bible-resources~BRLSG1910','bible-resources~BRMHCC','Easton'}
assert expected<=set(library.installed())
before={identifier:source_fingerprints(library.root/identifier) for identifier in expected}
app=Application();app.register();w=Window(app,library);w.set_default_size(1280,900);w.present();spin()
w.application_settings.set('automatic_catalogue_refresh',False)
native=X11Input();native.activate(w);screen=Screen(native)
report=dict(complete=False,app_import=inspect.getfile(Window),language=os.environ.get('LANGUAGE'),cases=[],captures=[])
def shot(name):
 native.move_at(w,2,2);spin(duration=.2);screen.grab(a.output/(name+'.png'));report['captures'].append(name+'.png')
def choose(dialog,identifier):
 dialog.back_to_list();dialog.source_filter.set_selected(0);dialog.language_choice=''
 item=library.resource(identifier) if identifier in library.installed() else next(r for r in dialog.resources if r.id==identifier);dialog.kind.set_selected({'bible':0,'commentary':1}.get(item.kind,2));dialog.update_languages()
 spin(lambda:not dialog._building_rows)
 index=next(i for i,r in enumerate(dialog.filtered_resources) if r.id==identifier)
 dialog.open_details(None,index);spin();assert dialog.modules.actions.get_visible()==(identifier in library.installed())
def confirmation():return next(x for x in Gtk.Window.get_toplevels() if isinstance(x,Adw.MessageDialog))
try:
 tab=w.active_tab;tab.navigate('bible-resources~BRLSG1910','Gen.1.1');spin(lambda:not tab._restoring_scroll)
 w.study_button.set_active(True);w.study.tools.set_visible_child_name('commentaries');w.study.choices.set_selected(w.study.names.index('bible-resources~BRMHCC'));w.study.refresh(force=True);spin()
 note=w.notes_store.save('**Synthetic personal lifecycle note**',('Keep',),versification=tab.reader.versification,start='Gen.1.1',end='Gen.1.1',origin_translation=tab.state.resource,origin_language='fr')
 w.highlights.set(tab.reader.versification,['Gen.1.1'],'yellow',tab.state.resource)
 notes=[asdict(x) for x in w.notes_store.all()];highlights=dict(w.highlights.entries)
 dialog=w.open_library();spin(lambda:not dialog.preparing);native.activate(dialog)
 dialog.modules.check();spin(lambda:not dialog.busy,timeout=90);assert dialog._phase=='complete',dialog.status.get_text()
 report['checks']={key:dict(state=value['state'],available_version=value['available'].version if value.get('available') else None) for key,value in dialog.modules.reports.items()}
 for mode in ('day','night'):
  w.appearance.update('mode',mode)
  for identifier in sorted(expected):
   choose(dialog,identifier);shot(mode+'-details-'+identifier)
  dialog.set_default_size(360,620);spin();choose(dialog,'Easton');assert dialog.get_width()<=360,dialog.get_width();shot(mode+'-narrow-tool');dialog.set_default_size(560,640);spin()
 for identifier in ('Easton','bible-resources~BRMHCC','bible-resources~BRLSG1910'):
  item=library.resource(identifier);choose(dialog,identifier)
  native.activate(dialog);dialog.modules.remove_button.grab_focus();native.key('space');spin();prompt=confirmation();shot('confirm-'+identifier)
  prompt.response('cancel');prompt.destroy();spin();assert source_fingerprints(library.root/identifier)==before[identifier]
  dialog.modules.remove_button.emit('clicked');spin();prompt=confirmation();prompt.response('confirm');prompt.destroy()
  spin(lambda:not dialog.busy,timeout=30);assert dialog._phase=='complete',dialog.status.get_text()
  assert identifier not in library.installed()
  assert [asdict(x) for x in w.notes_store.all()]==notes and w.highlights.entries==highlights
  for other in expected-{identifier}:assert source_fingerprints(library.root/other)==before[other]
  if item.kind=='bible':assert tab.reader is None and tab.state.resource==identifier and tab.state.reference=='Gen.1.1'
  if item.kind=='commentary':assert w.study.reader is None and tab.state.commentary==identifier
  shot('removed-'+identifier)
  # Explicit reinstall of the same real provider package, no silent replacement.
  choose(dialog,identifier);assert dialog.download_button.get_visible() and dialog.download_button.get_sensitive()
  native.activate(dialog);dialog.download_button.grab_focus();native.key('space')
  spin(lambda:not dialog.busy,timeout=90);assert dialog._phase=='complete',dialog.status.get_text()
  assert identifier in dialog._installed_metadata and source_fingerprints(library.root/identifier)==before[identifier]
  report['cases'].append(dict(resource=identifier,remove_cancel_preserved_files=True,removed=True,reinstalled_exact=True,notes_highlights_preserved=True))
 report['source_files_unchanged_after_reinstall']=all(source_fingerprints(library.root/i)==before[i] for i in expected);assert report['source_files_unchanged_after_reinstall']
 report['complete']=True
finally:
 if getattr(w,'catalogue_window',None):w.catalogue_window.close()
 w.close();native.close();(a.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
