"""Read private native waits and export only scalar aggregates, no raw payload."""
import json,os,re,signal,subprocess,sys,time
from pathlib import Path
output,version,repeat=sys.argv[1:];output=Path(output);deadline=time.monotonic()+45;pid=None
while time.monotonic()<deadline and pid is None:
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            args=p.joinpath('cmdline').read_bytes().split(b'\0')
            if b'tools.check_scroll_waits' in args and str(output).encode() in args and p.joinpath('exe').resolve().name.startswith('python3'):
                pid=p.name;break
        except (OSError,RuntimeError):pass
    if pid is None:time.sleep(.05)
record=dict(version=version,repeat=int(repeat),syscall_traced=False)
if pid is None:record['measurement_completed']=False;print(json.dumps(record));sys.exit()
trace=output.with_suffix('.syscalls.private');log=output.with_suffix('.strace.private')
ticks=os.sysconf('SC_CLK_TCK');samples=[];measurement=None
def cpu(path):
    fields=path.read_text().rsplit(')',1)[1].split();return (int(fields[11])+int(fields[12]))/ticks
with log.open('w') as err:
    child=subprocess.Popen(['strace','-qq','-ttt','-T','-s','0','-e','trace=futex,poll,ppoll,select,pselect6,epoll_wait,read,write,recvmsg,sendmsg,recvfrom,sendto,openat,newfstatat,statx','-e','raw=read,write,recvmsg,sendmsg,recvfrom,sendto','-p',pid,'-o',str(trace)],stdout=err,stderr=err)
    while time.monotonic()<deadline:
        try:samples.append((time.monotonic(),cpu(Path('/proc')/pid/'task'/pid/'stat'),cpu(Path('/proc')/pid/'stat')))
        except (OSError,ValueError):break
        if output.exists():
            try:measurement=json.loads(output.read_text())
            except (OSError,json.JSONDecodeError):measurement=None
            if measurement and 'input' in measurement and 'heartbeat' in measurement:break
        time.sleep(.01)
    child.send_signal(signal.SIGINT)
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:child.kill();child.wait()
record['trace_tool_exit_code']=child.returncode
if measurement is None:record['measurement_completed']=False;print(json.dumps(record));sys.exit()
x=measurement;offset=json.loads(output.with_suffix('.clock.json').read_text())['wall_offset']
start,end=x['input']['start'],x['input']['end'];rows=x['samples'];gap=max((b[0]-a[0],a[0],b[0]) for a,b in zip(rows,rows[1:]) if start<=a[0]<=end)
record.update(measurement_completed=True,main_loop_max_ms=x['heartbeat']['maximum']*1000,direction_max_ms=max((v or 0)*1000 for v in x['reversal_latency_seconds']),late_adjustments=x['changes_after_500ms'],longest_gap_start_ms=(gap[1]-start)*1000,longest_gap_ms=gap[0]*1000)
before=[v for v in samples if v[0]<=gap[1]];after=[v for v in samples if v[0]>=gap[2]]
if before and after:
    a,b=before[-1],after[0];record.update(main_cpu_ms_during_gap=(b[1]-a[1])*1000,process_cpu_ms_during_gap=(b[2]-a[2])*1000,cpu_sample_window_ms=(b[0]-a[0])*1000)
waits=[];pending=None;parsed=0;trace_lines=[]
if trace.exists():
    trace_lines=trace.read_text(errors='replace').splitlines()
    for line in trace_lines:
        m=re.search(r'(?:^|\s)(\d+\.\d+)\s+(\w+)\(',line)
        if m and '<unfinished ...>' in line:pending=(float(m[1]),m[2]);continue
        duration=re.search(r'<(\d+\.\d+)>\s*$',line)
        if not duration:continue
        elapsed=float(duration[1])
        if m:t,kind=float(m[1]),m[2]
        elif pending and 'resumed>' in line:t,kind=pending;pending=None
        else:continue
        parsed+=1
        t-=offset
        if t+elapsed<start or t>end:continue
        waits.append(dict(syscall=kind,duration_ms=elapsed*1000,start_after_input_ms=(t-start)*1000,overlaps_longest_gap=t<=gap[2] and t+elapsed>=gap[1]))
record.update(trace_line_count=len(trace_lines),parsed_timed_calls=parsed,syscall_traced=parsed>0,missing_direction_measurements=sum(v is None for v in x['reversal_latency_seconds']))
if not parsed:
    message=log.read_text(errors='replace') if log.exists() else ''
    record['trace_error_kind']='permission-denied' if 'Operation not permitted' in message or 'Permission denied' in message else 'missing-process' if 'No such process' in message else 'unclassified'
record['longest_native_waits']=sorted(waits,key=lambda v:v['duration_ms'],reverse=True)[:8]
record['longest_gap_native_waits']=[v for v in waits if v['overlaps_longest_gap'] and v['duration_ms']>5]
print(json.dumps(record))
