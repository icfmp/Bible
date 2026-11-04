"""Diagnostic only: native button property and GTK minimum-width measurements."""
from bible.ui import Window,Gtk
from tools.check_client_feedback import Screen
original=Window.__init__;windows=[]
def probe(self,*args,**kwargs):
    original(self,*args,**kwargs);windows.append(self)
    for button in (self.primary_version.download_more,self.compared_version.download_more,self.download_comparison):
        button.set_can_shrink(True);button.get_child().set_max_width_chars(1)
Window.__init__=probe
original_grab=Screen.grab
def walk(widget):
    yield widget
    child=widget.get_first_child()
    while child:
        yield from walk(child);child=child.get_next_sibling()
def grab(self,path):
    if path.name=='large-text-360.png':
        w=windows[-1];c=w.primary_version
        print('DIAG window',w.get_width(),'popover child',c.popover.get_child().get_width(),'choices limits',c.choices.get_min_content_width(),c.choices.get_max_content_width(),'button can-shrink',c.download_more.get_can_shrink(),flush=True)
        for widget in walk(c.popover.get_child()):
            width=widget.get_width();m=widget.measure(Gtk.Orientation.HORIZONTAL,-1)
            if width>312 or m[0]>250:
                print('DIAG',type(widget).__name__,'allocated',width,'minimum',m[0],'natural',m[1],('text='+widget.get_text()) if isinstance(widget,Gtk.Label) else '',flush=True)
    return original_grab(self,path)
Screen.grab=grab
from tools.check_translation_picker import main
main()

from pathlib import Path
import sys
p=Path(sys.argv[2])/'README.md'
p.write_text('DIAGNOSTIC ONLY: runtime can-shrink and label natural-width cap; not delivery evidence.\n\n'+p.read_text())
