"""Independent XTest wheel input with repeated reversals and exact event timing."""
import ctypes,os,time,json,sys
from pathlib import Path
x=ctypes.CDLL('libX11.so.6');t=ctypes.CDLL('libXtst.so.6');x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p;x.XFlush.argtypes=[ctypes.c_void_p];t.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
d=x.XOpenDisplay(os.environ['DISPLAY'].encode());events=[];start=time.monotonic()
for duration,button in [(.5,5),(.5,4)]*7+[(.7,5),(.3,4)]:
 end=time.monotonic()+duration
 while time.monotonic()<end:
  t.XTestFakeButtonEvent(d,button,1,0);t.XTestFakeButtonEvent(d,button,0,0);x.XFlush(d);events.append([time.monotonic(),button]);time.sleep(.01)
Path(sys.argv[1]).write_text(json.dumps(dict(start=start,end=time.monotonic(),events=events)))
