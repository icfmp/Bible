from pathlib import Path
import inspect,json,time
from gi.repository import Gtk,GLib
from bible.ui import Application,Window
from bible.library import Library
from tools.check_alpha_ui import X11Input
def spin(until=lambda:True,duration=.1):
 loop=GLib.MainLoop();start=time.monotonic();failed=[]
 def poll():
  if time.monotonic()-start>20:failed.append('timeout');loop.quit();return False
  if time.monotonic()-start>=duration and until():loop.quit();return False
  return True
 GLib.timeout_add(10,poll);loop.run();assert not failed

from bible.sword_provider import Reader
root=Path('/validation/library78-native-download-final');lib=Library(root/'translations')
assert inspect.getfile(Window).startswith('/app/')
name='ebible~fraLSG1910eb';assert name not in lib.installed()
app=Application();app.register();w=Window(app,lib);w.present();d=w.open_library()
spin(lambda:not d.preparing and not d._building_rows,duration=.1)
assert len(d.resources)>1900
idx=d.languages.index('fr');d.language.set_selected(idx);d.search.set_text('fraLSG1910eb');spin(lambda:not d._building_rows,duration=.5)
assert len(d.filtered_resources)==1 and d.filtered_resources[0].id==name
assert '1910' in d.metadata.get_text() and d.download_button.get_sensitive()
d.open_details(None,0);native=X11Input();native.activate(d);native.click(d.download_button)
loop=GLib.MainLoop();deadline=time.monotonic()+100;ticks=[]
def poll():
 ticks.append(time.monotonic())
 if not d._transfer_busy or time.monotonic()>deadline:loop.quit();return False
 return True
GLib.timeout_add(20,poll);loop.run()
assert d._phase=='complete',d.status.get_text();spin(lambda:not d.preparing and not d._building_rows)
assert name in d.installed_ids() and d.installed_state.get_visible()
r=Reader(lib.root/name,name);text=dict(r.chapter('John.3.16').verses)['John.3.16'];r.module.setKey(r.key('John.3.16'));direct=r.module.stripText();direct=direct if isinstance(direct,str) else direct.c_str();assert text==direct and 'monde' in text.casefold()
spin(duration=.5)
from PIL import ImageGrab
ImageGrab.grab().save('/validation/library78-output/download-complete.png')
print(json.dumps(dict(status='PASS',app_import=inspect.getfile(Window),real_native_download=name,installed_state=True,language_filter='fr',terms_retained=True,exact_local_sword_reading='John.3.16',heartbeat_ticks=len(ticks),maximum_gap=max((b-a for a,b in zip(ticks,ticks[1:])),default=0))))
d.close();w.close();native.close()
