"""Lightweight marker observer; diagnostics run only after normal measurements."""
import ctypes,gc,json,os,runpy,sys,weakref
from collections import Counter
from pathlib import Path
from bible.ui import Window
from bible.inline_markers import InlineMarkers
from tools.alpha_performance_input import sample
created=[];documents=[];create=InlineMarkers.button;markers=InlineMarkers.markers;close=Window.close
output=Path(sys.argv[2])
def track(self,view,reader,reference,kind,payload):
    button=create(self,view,reader,reference,kind,payload);created.append((kind,weakref.ref(button)));return button
def visit(self,reader,document):
    documents.append((reader.name,document.key));return markers(self,reader,document)
def finish(self,*args,**kwargs):
    if output.exists():
        data=json.loads(output.read_text());active={id(b) for view in (self.active_tab.text,self.active_tab.comparison_text) for b in getattr(view,'_inline_buttons',())}
        def alive(retired=False):return dict(Counter(kind for kind,ref in created if ref() is not None and (not retired or id(ref()) not in active)))
        data['diagnostic_marker_lifetime']=dict(created=len(created),active=len(active),alive_before_gc=alive(),retired_before_gc=alive(True),documents=documents,final_reference=self.active_tab.state.reference)
        data['diagnostic_post_measurement_gc_before']=sample(os.getpid());data['diagnostic_gc_collected']=gc.collect()
        data['diagnostic_post_measurement_gc_after']=sample(os.getpid());data['diagnostic_marker_lifetime']['alive_after_gc']=alive();data['diagnostic_marker_lifetime']['retired_after_gc']=alive(True)
        output.write_text(json.dumps(data,indent=2)+'\n')
    return close(self,*args,**kwargs)
InlineMarkers.button=track;InlineMarkers.markers=visit;Window.close=finish
runpy.run_module('tools.profile_alpha_performance',run_name='__main__')
