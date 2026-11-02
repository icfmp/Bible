"""Export scalar research measurements, never raw traces or profile contents."""
import json,sys
from pathlib import Path
path,commit,repeat,status=sys.argv[1:]
record=dict(diagnostic_source_commit=commit,repeat=int(repeat),exit_status=int(status),
            mounted_python_source=True,installed_package_proof=False)
p=Path(path)
if p.exists():
    x=json.loads(p.read_text())
    record.update(main_loop_max_ms=x['heartbeat']['maximum']*1000,
        main_loop_over_100ms=x['heartbeat']['over_100ms'],
        direction_max_ms=max((v or 0)*1000 for v in x['reversal_latency_seconds']),
        missing_direction_measurements=sum(v is None for v in x['reversal_latency_seconds']),
        late_adjustments=x['changes_after_500ms'],first_motion_ms=(x['first_scroll_latency_seconds'] or 0)*1000,
        first_paint_ms=(x['first_gtk_paint_latency_seconds'] or 0)*1000)
else:record['measurement_completed']=False
print(json.dumps(record))
