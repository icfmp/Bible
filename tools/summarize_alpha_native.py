"""Summarize high-water and end-of-process live native allocations without data."""
import json
from pathlib import Path
import sys
import memray

reader=memray.FileReader(sys.argv[1])
def summarize(records):
    result=[]
    for record in sorted(records,key=lambda r:r.size,reverse=True)[:30]:
        try:stack=list(record.hybrid_stack_trace())[-35:]
        except (NotImplementedError,RuntimeError):stack=list(record.stack_trace())[-35:]
        result.append(dict(bytes=record.size,allocations=record.n_allocations,thread=record.thread_name,stack=stack))
    return result
report=dict(peak=summarize(reader.get_high_watermark_allocation_records()),
            retained_at_tracker_end=summarize(reader.get_leaked_allocation_records()),
            limitation='Tracker/end-of-process retained allocations include intentional caches and tracer overhead; this is not by itself a leak verdict.')
Path(sys.argv[2]).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(peak_groups=len(report['peak']),retained_groups=len(report['retained_at_tracker_end']))))
