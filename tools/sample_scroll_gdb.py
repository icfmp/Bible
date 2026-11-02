"""Capture native function names on a live diagnostic heartbeat pause only."""
import json,mmap,re,struct,subprocess,sys,time
from pathlib import Path
output,version,repeat=sys.argv[1:];output=Path(output)
record=dict(version=version,repeat=int(repeat),diagnostic_only=True,performance_gate=False,triggered=False)
deadline=time.monotonic()+55;pid=None;mapping=None
while time.monotonic()<deadline:
    if pid is None:
        for proc in Path('/proc').iterdir():
            if not proc.name.isdecimal():continue
            try:
                args=proc.joinpath('cmdline').read_bytes().split(b'\0')
                if proc.joinpath('exe').resolve().name=='python3.13' and args[1:3]==[b'-m',b'tools.check_scroll_waits'] and str(output).encode() in args:
                    pid=proc.name;break
            except (OSError,RuntimeError):pass
    if mapping is None and output.with_suffix('.heartbeat.private').exists():
        try:
            file=output.with_suffix('.heartbeat.private').open('rb');mapping=mmap.mmap(file.fileno(),8,access=mmap.ACCESS_READ)
        except (ValueError,OSError):pass
    if pid and mapping:
        beat=struct.unpack('d',mapping[:])[0]
        if beat and time.monotonic()-beat>.1:
            record.update(triggered=True,trigger_age_ms=(time.monotonic()-beat)*1000)
            try:
                stat=(Path('/proc')/pid/'task'/pid/'stat').read_text().rsplit(')',1)[1].split()
                record['trigger_state']=stat[0]
            except OSError:pass
            result=subprocess.run(['gdb','-nx','-batch','-iex','set debuginfod enabled off','-iex','set auto-load off','-iex',f'set sysroot /proc/{pid}/root','-p',pid,'-ex','set pagination off','-ex','set print frame-arguments none','-ex','thread 1','-ex','bt 48','-ex','detach'],capture_output=True,text=True,timeout=20)
            output.with_suffix('.native-stack.private').write_text(result.stdout+'\n'+result.stderr)
            record['debugger_exit_code']=result.returncode;functions=[]
            for line in result.stdout.splitlines():
                match=re.match(r'^#\d+\s+(?:0x[0-9a-f]+\s+in\s+)?([A-Za-z_][A-Za-z0-9_:.<>~@]+)\s*\(',line)
                if match:functions.append(match[1])
            record['native_functions']=functions
            record['native_total_frames']=sum(bool(re.match(r'^#\d+\s',line)) for line in result.stdout.splitlines())
            record['native_unresolved_frames']=sum(bool(re.match(r'^#\d+\s+(?:0x[0-9a-f]+\s+in\s+)?\?\?',line)) for line in result.stdout.splitlines())
            break
    if output.exists():
        try:
            measurement=json.loads(output.read_text())
            if 'heartbeat' in measurement:
                record['uninterrupted_max_main_loop_ms']=measurement['heartbeat']['maximum']*1000;break
        except (OSError,json.JSONDecodeError):pass
    time.sleep(.005)
print(json.dumps(record))
