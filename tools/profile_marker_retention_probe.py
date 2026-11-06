"""Lightweight lifetime observer; collection runs after all gesture samples."""
import gc,json,os,runpy,sys,weakref
from collections import Counter
from pathlib import Path
from bible.ui import Window,GLib
from bible.inline_markers import InlineMarkers
from tools.alpha_performance_input import sample
created=[];documents=[];windows=[];diagnostic={}
create=InlineMarkers.button;markers=InlineMarkers.markers;construct=Window.__init__;run=GLib.MainLoop.run
output=Path(sys.argv[2])
def track(self,view,reader,reference,kind,payload):
    button=create(self,view,reader,reference,kind,payload);created.append((kind,weakref.ref(button)));return button
def visit(self,reader,document):
    documents.append((reader.name,document.key));return markers(self,reader,document)
def remember(self,*args,**kwargs):
    construct(self,*args,**kwargs);windows.append(weakref.ref(self))
def observe(loop,*args,**kwargs):
    initial=len(created);first_document=len(documents);result=run(loop,*args,**kwargs)
    window=windows[-1]();tab=window.active_tab
    active={id(b) for view in (tab.text,tab.comparison_text) for b in getattr(view,'_inline_buttons',())}
    def alive(retired=False):return dict(Counter(kind for kind,ref in created if ref() is not None and (not retired or id(ref()) not in active)))
    diagnostic.update(created_before_gesture=initial,created_during_measurement=len(created)-initial,active=len(active),alive_before_gc=alive(),retired_before_gc=alive(True),documents_during_measurement=documents[first_document:],final_reference=tab.state.reference)
    diagnostic['memory_before_post_measurement_gc']=sample(os.getpid());diagnostic['gc_collected']=gc.collect()
    diagnostic['memory_after_post_measurement_gc']=sample(os.getpid());diagnostic['alive_after_gc']=alive();diagnostic['retired_after_gc']=alive(True)
    return result
InlineMarkers.button=track;InlineMarkers.markers=visit;Window.__init__=remember;GLib.MainLoop.run=observe
runpy.run_module('tools.profile_alpha_performance',run_name='__main__')
data=json.loads(output.read_text());data['diagnostic_marker_lifetime']=diagnostic;output.write_text(json.dumps(data,indent=2)+'\n')
