"""Independent native wheel input and /proc sampling for installed-alpha A/B.

Never waits for the GTK main thread. CPU is process-wide across native threads,
100% means one logical CPU. PSS/RSS are host process memory, not GPU VRAM.
"""
import ctypes
import json
import os
from pathlib import Path
import sys
import time


def sample(pid):
    prefix=Path('/proc')/str(pid)
    raw=(prefix/'stat').read_text().rsplit(')',1)[1].split()
    data=dict(time=time.monotonic(),cpu_seconds=(int(raw[11])+int(raw[12]))/os.sysconf('SC_CLK_TCK'),
              rss_bytes=int(raw[21])*os.sysconf('SC_PAGE_SIZE'))
    for line in (prefix/'smaps_rollup').read_text().splitlines():
        key,_,value=line.partition(':')
        if key in ('Pss','Private_Clean','Private_Dirty','Anonymous','Swap'):
            data[key.lower()+'_bytes']=int(value.split()[0])*1024
    return data


def main():
    output=Path(sys.argv[1]);pid=int(sys.argv[2]);cycles=int(sys.argv[3])
    kind=sys.argv[4] if len(sys.argv)>4 else 'wheel'
    bar=json.loads(sys.argv[5]) if len(sys.argv)>5 else None
    x=ctypes.CDLL('libX11.so.6');xt=ctypes.CDLL('libXtst.so.6')
    x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p
    x.XFlush.argtypes=[ctypes.c_void_p]
    xt.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
    xt.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
    display=x.XOpenDisplay(os.environ['DISPLAY'].encode());assert display
    phases=[dict(name='startup_idle',duration=6)]
    for cycle in range(cycles):
        phases.extend([dict(name='scroll',cycle=cycle,duration=8),dict(name='after_scroll_idle',cycle=cycle,duration=6)])
    rows=[];events=[];transitions=[];began=time.monotonic();last_sample=0
    for phase in phases:
        start=time.monotonic();transitions.append(dict(phase,start=start));last_input=0
        if phase['name']=='scroll' and kind=='scrollbar':
            xt.XTestFakeMotionEvent(display,-1,bar['x'],bar['top'],0)
            xt.XTestFakeButtonEvent(display,1,True,0);x.XFlush(display)
            events.append([time.monotonic(),'press'])
        output.with_suffix('.phase.json').write_text(json.dumps(dict(phase,start=start)))
        while time.monotonic()-start<phase['duration']:
            now=time.monotonic()
            if now-last_sample>=.2:
                rows.append(dict(sample(pid),phase=phase['name'],cycle=phase.get('cycle')));last_sample=now
            if phase['name']=='scroll' and now-last_input>=.01:
                elapsed=now-start
                if kind=='scrollbar':
                    part=elapsed%4;fraction=part/2 if part<2 else (4-part)/2
                    y=round(bar['top']+fraction*(bar['bottom']-bar['top']))
                    xt.XTestFakeMotionEvent(display,-1,bar['x'],y,0);x.XFlush(display)
                    events.append([time.monotonic(),'motion',y])
                else:
                    button=5 if elapsed<3 else 4 if elapsed<6 else 5 if int((elapsed-6)/.5)%2==0 else 4
                    xt.XTestFakeButtonEvent(display,button,True,0);xt.XTestFakeButtonEvent(display,button,False,0)
                    x.XFlush(display);events.append([time.monotonic(),button])
                last_input=now
            time.sleep(.002)
        if phase['name']=='scroll' and kind=='scrollbar':
            xt.XTestFakeMotionEvent(display,-1,bar['x'],bar['top'],0)
            xt.XTestFakeButtonEvent(display,1,False,0);x.XFlush(display)
            events.append([time.monotonic(),'release'])
    output.write_text(json.dumps(dict(start=began,end=time.monotonic(),phases=transitions,samples=rows,events=events)))


if __name__=='__main__':main()
