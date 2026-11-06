"""Process-only inline-marker clipping ablation, not a product preference."""
import json,runpy,sys
from pathlib import Path
from bible.ui import Window,Gtk
original=Window.__init__
def construct(self,*args,**kwargs):
    original(self,*args,**kwargs)
    provider=Gtk.CssProvider();provider.load_from_data(b'.source-note-marker { border-radius: 0; box-shadow: none; }')
    Gtk.StyleContext.add_provider_for_display(self.get_display(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION+1)
    self._diagnostic_marker_clip=provider
Window.__init__=construct
output=Path(sys.argv[2]);runpy.run_module('tools.profile_alpha_performance',run_name='__main__')
data=json.loads(output.read_text());data['diagnostic_square_source_markers']=True;output.write_text(json.dumps(data,indent=2)+'\n')
