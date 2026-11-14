"""Clean first-run, real index/install and native selectors without restart."""
import argparse,inspect,json,sys
from pathlib import Path
from bible.ui import Application,Window,Library,Gtk
from bible.providers import PROVIDERS,YOUVERSION
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input
from tools.check_client_feedback import Screen
from bible.youversion_install import fetch_resource,acknowledgement
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--require-packaged',action='store_true');parser.add_argument('--compiler',type=Path);a=parser.parse_args()
if a.require_packaged:assert inspect.getfile(Window).startswith('/app/') and a.compiler is None
p=a.profile;assert not p.exists();p.mkdir();(p/'.ready-batch-test-profile').touch()
out=a.output;out.mkdir(parents=True,exist_ok=True)
app=Application();app.register();w=Window(app,Library(p/'translations'));w.application_settings.set('library_language','en');w.present()
d=w.open_library();d.set_default_size(360,640);d.source_filter.set_selected(1+PROVIDERS.index(YOUVERSION))
n=X11Input();screen=Screen(n);records=[]
def walk(widget):
 yield widget;c=widget.get_first_child()
 while c:yield from walk(c);c=c.get_next_sibling()
def state(phase):
 item=dict(phase=phase,resources=len(d.resources),native_languages=d.language.strings.get_n_items(),language=d.language_choice,rows=len(d.filtered_resources),sensitive=d.language.get_sensitive(),busy=d.busy,preparing=d.preparing,errors=d._catalogue_errors)
 records.append(item);print(item,flush=True)
try:
 n.activate(d);state('clean-no-index');n.click(d.language);n.key('Escape')
 d.load_catalogue();spin(lambda:not d.busy and any(r.provider_id=='youversion' for r in d.resources),timeout=150,duration=.4)
 state('first-index-without-restart');screen.grab(out/'first-index.png')
 if d.language.get_popover().get_visible():n.key('Escape')
 assert not d.language.get_popover().get_visible(),'Escape from the search field must dismiss the native popup'
 for code in ('fr','en','fr','en'):
  n.click(d.language);assert d.language.get_popover().get_visible()
  d.language.search.set_text(d.language.name(code));d.language.filter(force=True);spin(duration=.4)
  index=next(i for i in range(d.language.strings.get_n_items()) if d.language._label_codes.get(d.language.strings.get_string(i))==code)
  caption=d.language.strings.get_string(index);label=next(v for v in walk(d.language.list) if isinstance(v,Gtk.Label) and v.get_mapped() and v.get_text()==caption)
  n.click(label);spin(lambda:not d.busy,timeout=120,duration=.3);assert d.language_choice==code;state('native-language-'+code)
 from contextlib import nullcontext
 from unittest.mock import patch
 from functools import partial
 from bible.youversion_install import run_conversion
 resource=fetch_resource(1)
 with (patch('bible.youversion_install.run_conversion',partial(run_conversion,compiler=str(a.compiler))) if a.compiler else nullcontext()):
  d.install(resource=resource,permission=acknowledgement(resource))
  spin(lambda:not d._transfer_busy,timeout=180,duration=.4)
 spin(lambda:not d._transfer_busy,timeout=180,duration=.4);assert resource.id in w.library.installed(),d.status.get_text()
 d.close();spin();n.activate(w)
 for i in range(12):
  n.click(w.primary_version);assert w.primary_version.popover.get_visible();assert resource.id in w.primary_version.names
  n.key('Escape');assert not w.primary_version.popover.get_visible()
 report=dict(app_import=inspect.getfile(Window),local_compiler_override=str(a.compiler) if a.compiler else None,complete=True,no_restart=True,clean_first_run=True,native_header_cycles=12,installed=resource.id,states=records,limitation='Successful diagnostic, not an identified intermittent failure mechanism.')
finally:
 (out/'result.json').write_text(json.dumps(locals().get('report',dict(complete=False,states=records)),indent=2));w.close();n.close()
