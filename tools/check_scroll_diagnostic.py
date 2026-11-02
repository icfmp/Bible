"""Diagnostic wrapper only; imports the installed application unchanged."""
import faulthandler,gc,json,sys,time
from pathlib import Path
from tools.check_sustained_scroll import main
output=Path(sys.argv[2]);events=[]
def record(phase,info):events.append(dict(time=time.monotonic(),phase=phase,**info))
with output.with_suffix('.stacks.txt').open('w') as stack:
    gc.callbacks.append(record)
    faulthandler.dump_traceback_later(.1,repeat=True,file=stack)
    try:main()
    finally:
        faulthandler.cancel_dump_traceback_later();gc.callbacks.remove(record)
        output.with_suffix('.gc.json').write_text(json.dumps(events,indent=2))
