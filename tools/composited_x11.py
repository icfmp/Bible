"""Run GUI evidence under a real X11 compositor (test environment only)."""
import ctypes,os,subprocess,sys,time


def main():
    x=ctypes.CDLL('libX11.so.6');pointer=ctypes.c_void_p;ulong=ctypes.c_ulong
    x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=pointer
    x.XInternAtom.argtypes=[pointer,ctypes.c_char_p,ctypes.c_int];x.XInternAtom.restype=ulong
    x.XGetSelectionOwner.argtypes=[pointer,ulong];x.XGetSelectionOwner.restype=ulong
    x.XCloseDisplay.argtypes=[pointer]
    display=x.XOpenDisplay(os.environ['DISPLAY'].encode());assert display
    atom=x.XInternAtom(display,b'_NET_WM_CM_S0',False)
    compositor=None
    try:
        if not x.XGetSelectionOwner(display,atom):
            compositor=subprocess.Popen(['xcompmgr','-n'])
            deadline=time.monotonic()+3
            while not x.XGetSelectionOwner(display,atom):
                assert compositor.poll() is None and time.monotonic()<deadline,'X11 compositor did not start'
                time.sleep(.05)
        return subprocess.run(sys.argv[1:]).returncode
    finally:
        x.XCloseDisplay(display)
        if compositor:compositor.terminate();compositor.wait(timeout=3)

if __name__=='__main__':raise SystemExit(main())
