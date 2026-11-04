"""Diagnostic only: measure native Button.can-shrink on the installed old candidate."""
from bible.ui import Window
original=Window.__init__
def probe(self,*args,**kwargs):
    original(self,*args,**kwargs)
    for button in (self.primary_version.download_more,self.compared_version.download_more,self.download_comparison):
        button.set_can_shrink(True)
Window.__init__=probe
from tools.check_translation_picker import main
main()
from pathlib import Path
import sys
p=Path(sys.argv[2])/'README.md'
p.write_text('DIAGNOSTIC ONLY: runtime Button.can-shrink=True probe; not delivery evidence.\n\n'+p.read_text())
