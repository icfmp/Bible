"""Process-only source-label attribute ablation; never changes stored preferences."""
import importlib,json,runpy,sys
from pathlib import Path
try:module=importlib.import_module('bible.source_note_marker')
except ModuleNotFoundError as error:
    if error.name!='bible.source_note_marker':raise
    module=None
if module:
    original=module.source_note_marker
    def create(*args,**kwargs):
        button=original(*args,**kwargs);button.get_child().set_attributes(None);return button
    module.source_note_marker=create
output=Path(sys.argv[2]);runpy.run_module('tools.profile_alpha_performance',run_name='__main__')
data=json.loads(output.read_text());data['diagnostic_source_label_attributes_removed']=bool(module);output.write_text(json.dumps(data,indent=2)+'\n')
