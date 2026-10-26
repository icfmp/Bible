#!/usr/bin/env python3
"""Read-only Linux sampler for a running Bible Flatpak. No profile/file contents.

Start Bible normally, then use its wheel/scrollbar and stop while this records.
The JSON contains version IDs, selected graphics environment settings, process
memory/CPU and thread CPU counters. No notes, preferences, translations, full
environment, command lines, host name or network requests are collected.
"""
import argparse
import configparser
import json
import os
from pathlib import Path
import platform
import time


def flatpak_processes():
    found=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdecimal():continue
        try:
            if proc.stat().st_uid!=os.getuid():continue
            command=proc.joinpath('cmdline').read_bytes().split(b'\0')
            if not any(command[i:i+2]==[b'-m',b'bible'] for i in range(len(command)-1)):continue
            info=configparser.ConfigParser(interpolation=None)
            info.read_string(proc.joinpath('root/.flatpak-info').read_text())
            if info.get('Application','name',fallback='')!='io.github.icfmp.Bible':continue
            instance=dict(info.items('Instance'))
            version={k:instance[k] for k in ('app-commit','runtime-commit','arch','branch') if k in instance}
            found.append((int(proc.name),version))
        except (OSError,configparser.Error):continue
    return found


def counters(proc):
    raw=proc.joinpath('stat').read_text().rsplit(')',1)[1].split()
    ticks=os.sysconf('SC_CLK_TCK')
    return dict(cpu_seconds=(int(raw[11])+int(raw[12]))/ticks,state=raw[0],
                age_seconds=time.clock_gettime(time.CLOCK_BOOTTIME)-int(raw[19])/ticks)


def snapshot(pid):
    proc=Path('/proc')/str(pid);result=dict(time=time.monotonic(),**counters(proc))
    wanted={'Rss','Pss','Pss_Anon','Pss_File','Pss_Shmem','Anonymous','Private_Clean','Private_Dirty','Swap'}
    for line in proc.joinpath('smaps_rollup').read_text().splitlines():
        key,_,value=line.partition(':')
        if key in wanted:result[key+'_bytes']=int(value.split()[0])*1024
    for line in proc.joinpath('status').read_text().splitlines():
        key,_,value=line.partition(':')
        if key in ('VmHWM','VmPeak'):result[key+'_bytes']=int(value.split()[0])*1024
    # Some desktop monitors account to the app's cgroup, including file cache.
    # Record it separately only when the scope explicitly belongs to Bible.
    for line in proc.joinpath('cgroup').read_text().splitlines():
        hierarchy,controllers,path=line.split(':',2)
        if hierarchy!='0' or 'io.github.icfmp.Bible' not in path:continue
        scope=Path('/sys/fs/cgroup')/path.lstrip('/')
        try:
            result['app_cgroup_memory_current_bytes']=int((scope/'memory.current').read_text())
            stats=dict(row.split() for row in (scope/'memory.stat').read_text().splitlines())
            result['app_cgroup_memory_stat']={k:int(stats[k]) for k in ('anon','file','shmem','file_mapped','kernel') if k in stats}
        except (OSError,ValueError):pass
    result['threads']={}
    for task in proc.joinpath('task').iterdir():
        try:result['threads'][task.name]=dict(name=task.joinpath('comm').read_text().strip(),**counters(task))
        except OSError:pass
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('output',type=Path);p.add_argument('--seconds',type=int,default=120)
    args=p.parse_args();assert 10<=args.seconds<=600
    if args.output.exists():p.error('Output exists; choose another file to preserve it.')
    found=flatpak_processes()
    if len(found)!=1:p.error(f'Expected exactly one running Bible Flatpak Python process; found {len(found)}.')
    pid,version=found[0]
    environment={}
    wanted={'GSK_RENDERER','GDK_BACKEND','GDK_SCALE','GDK_DPI_SCALE','LIBGL_ALWAYS_SOFTWARE'}
    for item in (Path('/proc')/str(pid)/'environ').read_bytes().split(b'\0'):
        key,_,value=item.partition(b'=')
        if key.decode(errors='replace') in wanted:environment[key.decode()]=value.decode(errors='replace')
    cards=[]
    for device in Path('/sys/class/drm').glob('card[0-9]*/device'):
        try:
            cards.append(dict(vendor=(device/'vendor').read_text().strip(),
                              device=(device/'device').read_text().strip(),driver=(device/'driver').resolve().name))
        except OSError:pass
    report=dict(pid=pid,version=version,graphics_environment=environment,gpu_devices=cards,
                kernel=platform.release(),architecture=platform.machine(),logical_cpus=os.cpu_count(),
                cpu_units='100 percent = one logical CPU; all native threads included',samples=[])
    print('Recording read-only process counters. Keep idle briefly, scroll/reverse, then stop.',flush=True)
    start=time.monotonic()
    try:
        while time.monotonic()-start<args.seconds:
            report['samples'].append(snapshot(pid));time.sleep(.25)
    except (KeyboardInterrupt,FileNotFoundError,ProcessLookupError):
        report['interrupted']=True
    finally:
        with args.output.open('x') as output:json.dump(report,output,indent=2)
        print(f'Saved {len(report["samples"])} samples to {args.output}',flush=True)


if __name__=='__main__':main()
