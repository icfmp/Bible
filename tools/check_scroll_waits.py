"""Private diagnostic coordination; the installed application is unchanged."""
import json,sys,time
from pathlib import Path
from tools.check_sustained_scroll import main
output=Path(sys.argv[2])
output.with_suffix('.clock.json').write_text(json.dumps(dict(wall_offset=time.time()-time.monotonic())))
time.sleep(2)
try:main()
finally:time.sleep(3)
