"""Read private native waits and export only scalar aggregates, no raw payload."""
import json,os,re,signal,subprocess,sys,time,shutil
from pathlib import Path
def application_target(executable,args,expected_output):
    return (Path(executable).name=='python3.13' and args[1:3]==[b'-m',b'tools.check_scroll_waits']
            and str(expected_output).encode() in args)

output,version,repeat,perf=sys.argv[1:];output=Path(output);deadline=time.monotonic()+45;pid=None
while time.monotonic()<deadline and pid is None:
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            args=p.joinpath('cmdline').read_bytes().split(b'\0')
            if application_target(p.joinpath('exe').resolve(),args,output):
                pid=p.name;break
        except (OSError,RuntimeError):pass
    if pid is None:time.sleep(.05)
record=dict(version=version,repeat=int(repeat),syscall_traced=False,expected_process_role='application-python')
if pid is None:record['measurement_completed']=False;print(json.dumps(record));sys.exit()
record.update(runtime_python='python3.13',verified_entry_module='tools.check_scroll_waits')
# Keep ptrace out of import, SWORD discovery and initial GTK allocation.
# The independent input subprocess is launched only after the reader settles.
input_seen=False
while time.monotonic()<deadline and not input_seen:
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            args=p.joinpath('cmdline').read_bytes().split(b'\0')
            if b'tools.sustained_scroll_input' not in args or str(output.with_suffix('.input.json')).encode() not in args:continue
            fields=p.joinpath('stat').read_text().rsplit(')',1)[1].split()
            if fields[1]==pid:input_seen=True;break
        except (OSError,ValueError,IndexError):pass
    if not input_seen:time.sleep(.005)
record['input_process_observed']=input_seen
trace=output.with_suffix('.syscalls.private');log=output.with_suffix('.strace.private')
ticks=os.sysconf('SC_CLK_TCK');samples=[];measurement=None;cpu_error=None
perfdata=output.with_suffix('.perf.private');perflog=output.with_suffix('.perf-log.private')
perferr=perflog.open('w')
perfchild=subprocess.Popen([perf,'record','-e','cpu-clock:u','-F','199','--clockid','mono','--call-graph','dwarf,8192','-t',pid,'-o',str(perfdata)],stdout=perferr,stderr=perferr)
# Resolve only known application/runtime DSOs; keep their copies private.
symbols=output.parent/'native-symbols'
for line in (Path('/proc')/pid/'maps').read_text().splitlines():
    fields=line.split(maxsplit=5)
    if len(fields)<6 or not fields[5].startswith(('/usr/lib/','/app/lib/','/usr/bin/python')):continue
    name=fields[5];source=Path('/proc')/pid/'root'/name.lstrip('/');destination=symbols/name.lstrip('/')
    if destination.exists() or not source.is_file():continue
    destination.parent.mkdir(parents=True,exist_ok=True)
    try:shutil.copyfile(source,destination)
    except OSError:pass
def cpu(path):
    fields=path.read_text().rsplit(')',1)[1].split();return (int(fields[11])+int(fields[12]))/ticks
with log.open('w') as err:
    child=subprocess.Popen(['strace','-qq','-ttt','-T','-s','0','-e','trace=futex,poll,ppoll,select,pselect6,epoll_wait,read,write,recvmsg,sendmsg,recvfrom,sendto,openat,newfstatat,statx','-e','raw=read,write,recvmsg,sendmsg,recvfrom,sendto','-p',pid,'-o',str(trace)],stdout=err,stderr=err)
    while time.monotonic()<deadline:
        try:samples.append((time.monotonic(),cpu(Path('/proc')/pid/'task'/pid/'stat'),cpu(Path('/proc')/pid/'stat')))
        except (OSError,ValueError) as error:
            cpu_error=dict(kind=type(error).__name__,errno=getattr(error,'errno',None));break
        if output.exists():
            try:measurement=json.loads(output.read_text())
            except (OSError,json.JSONDecodeError):measurement=None
            if measurement and 'input' in measurement and 'heartbeat' in measurement:break
        time.sleep(.01)
    child.send_signal(signal.SIGINT)
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:child.kill();child.wait()
perfchild.send_signal(signal.SIGINT)
try:perfchild.wait(timeout=5)
except subprocess.TimeoutExpired:perfchild.kill();perfchild.wait()
perferr.close()
record.update(native_sampler_exit_code=perfchild.returncode)
record.update(trace_tool_exit_code=child.returncode,cpu_time_samples=len(samples),cpu_sampling_error=cpu_error,sampling_deadline_reached=time.monotonic()>=deadline)
if not measurement:
    record['trace_line_count']=len(trace.read_text(errors='replace').splitlines()) if trace.exists() else 0
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
# A fixed symbol/DSO/percentage schema only. No raw stacks, addresses or paths.
def symbol_aggregates(children=False):
    fields='overhead_children,symbol,dso' if children else 'overhead,symbol,dso'
    command=[perf,'report','-i',str(perfdata),'--symfs',str(symbols),'--stdio','--no-call-graph','--sort','symbol,dso','-F',fields,'-t','|','--percent-limit','0.1','--time',f'{gap[1]:.6f},{gap[2]:.6f}']
    command+=['--children'] if children else ['--no-children']
    result=subprocess.run(command,capture_output=True,text=True)
    record['native_inclusive_report_exit_code' if children else 'native_self_report_exit_code']=result.returncode
    entries=[];unresolved=0.0;matched=0
    for line in result.stdout.splitlines():
        parts=line.split('|')
        if len(parts)!=3:continue
        try:percentage=float(parts[0].strip().rstrip('%'))
        except ValueError:continue
        matched+=1
        symbol=re.sub(r'^\[[^]]+\]\s*','',parts[1].strip())
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_:.<>~@()+* ,\[\]-]{0,180}',symbol):
            unresolved+=percentage;continue
        entries.append(dict(percent=percentage,symbol=symbol,dso=Path(parts[2].strip()).name))
    record['native_inclusive_report_rows' if children else 'native_self_report_rows']=matched
    record['native_inclusive_unresolved_percent' if children else 'native_self_unresolved_percent']=unresolved
    return entries[:32]
record['longest_gap_native_cpu_symbols']=symbol_aggregates()
record['longest_gap_native_inclusive_symbols']=symbol_aggregates(True)
print(json.dumps(record))
