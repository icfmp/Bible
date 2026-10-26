"""CI-only native CPU sampling of the actual Python process, not Flatpak init."""
import argparse
from pathlib import Path
import shutil
import subprocess
import time


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('perf');p.add_argument('output',type=Path)
    p.add_argument('symbols',type=Path);args=p.parse_args()
    deadline=time.monotonic()+30;pid=None
    while time.monotonic()<deadline and pid is None:
        for proc in Path('/proc').iterdir():
            if not proc.name.isdecimal():continue
            try:
                if proc.joinpath('exe').resolve().name!='python3.13':continue
                command=proc.joinpath('cmdline').read_bytes().split(b'\0')
                if b'tools.profile_alpha_performance' in command and str(args.output).encode() in command:
                    pid=proc.name;break
            except (OSError,RuntimeError):continue
        if pid is None:time.sleep(.1)
    assert pid,'Actual packaged Python process not found'
    # Start once the independent input sampler has entered its initial idle phase.
    phase=args.output.with_suffix('.input.phase.json')
    while not phase.exists() and time.monotonic()<deadline:time.sleep(.1)
    assert phase.exists(),'Input sampler not started'
    stem=args.output.with_suffix('');data=stem.with_suffix('.perf.data')
    with stem.with_suffix('.perf.log').open('w') as log:
        subprocess.run([args.perf,'record','-e','cpu-clock:u','-F','99','--call-graph','dwarf',
                        '-p',pid,'-o',str(data),'--','sleep','20'],stdout=log,stderr=log,check=True)
    # Resolve the sandbox's DSOs while its process is still alive.
    proc=Path('/proc')/pid
    for line in proc.joinpath('maps').read_text().splitlines():
        parts=line.split(maxsplit=5)
        if len(parts)<6:continue
        name=parts[-1]
        if not name.startswith(('/usr/lib/','/app/lib/','/usr/bin/python')):continue
        source=proc/'root'/name.lstrip('/');target=args.symbols/name.lstrip('/')
        if target.exists() or not source.is_file():continue
        target.parent.mkdir(parents=True,exist_ok=True)
        try:shutil.copyfile(source,target)
        except OSError:pass
    with stem.with_suffix('.perf.txt').open('w') as report:
        subprocess.run([args.perf,'report','-i',str(data),'--symfs',str(args.symbols),
                        '--stdio','--no-children','--sort','comm,pid,dso,symbol'],
                       stdout=report,stderr=subprocess.STDOUT,check=True)
    text=stem.with_suffix('.perf.txt').read_text()
    assert 'python3' in text,'Report contains no application samples'
    print('Native CPU profile captured for actual Python PID',pid,flush=True)


if __name__=='__main__':main()
