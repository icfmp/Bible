"""Private diagnostic coordination; the installed application is unchanged."""
import json,sys,time,mmap,struct
from pathlib import Path
from tools.check_sustained_scroll import main
from bible.ui import GLib,Gtk
from gi.repository import Gdk
disable_overshoot='--diagnostic-no-overshoot' in sys.argv
if disable_overshoot:
    sys.argv.remove('--diagnostic-no-overshoot')
    Gtk.init()
    edge_provider=Gtk.CssProvider()
    edge_provider.load_from_string('scrolledwindow overshoot { background: none; box-shadow: none; }')
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),edge_provider,Gtk.STYLE_PROVIDER_PRIORITY_USER)
output=Path(sys.argv[2])
output.with_suffix('.clock.json').write_text(json.dumps(dict(wall_offset=time.time()-time.monotonic())))
heartbeat_file=output.with_suffix('.heartbeat.private').open('w+b')
heartbeat_file.truncate(8)
heartbeat=mmap.mmap(heartbeat_file.fileno(),8)
timeout_add=GLib.timeout_add
def observed_timeout(interval,callback,*args,**kwargs):
    if interval==10 and callback.__name__=='beat':
        original=callback
        def callback(*values):
            heartbeat[:]=struct.pack('d',time.monotonic())
            return original(*values)
    return timeout_add(interval,callback,*args,**kwargs)
GLib.timeout_add=observed_timeout
time.sleep(2)
try:main()
finally:time.sleep(3)
