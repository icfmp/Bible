"""Capture real X11 GTK surfaces and measure client feedback regressions.

Run only with a disposable profile. PNGs are unedited root-window captures,
including real native popups. Works inside the installed Flatpak without PIL.
"""
import argparse,ctypes,inspect,json,os,struct,time,zlib,subprocess,signal
from pathlib import Path
from bible.ui import Application,Window,Library,Gtk
from tests.test_ui import spin
from tests.test_appearance import SystemStyleOverride
from tools.check_alpha_ui import X11Input


class Screen:
    def __init__(self,native):
        self.n=native;x=native.x11;p=ctypes.c_void_p;i=ctypes.c_int;u=ctypes.c_ulong
        class Image(ctypes.Structure):
            _fields_=[('width',i),('height',i),('xoffset',i),('format',i),('data',p),('byte_order',i),('bitmap_unit',i),('bitmap_bit_order',i),('bitmap_pad',i),('depth',i),('stride',i),('bits',i)]
        self.Image=Image
        x.XDisplayWidth.argtypes=[p,i];x.XDisplayHeight.argtypes=[p,i]
        x.XGetImage.argtypes=[p,u,i,i,ctypes.c_uint,ctypes.c_uint,u,i];x.XGetImage.restype=p
        x.XDestroyImage.argtypes=[p]
        self.width=x.XDisplayWidth(native.display,0);self.height=x.XDisplayHeight(native.display,0)
    def point(self,widget,x,y):
        native=widget.get_native();found,bounds=widget.compute_bounds(native);assert found
        rx,ry,child=ctypes.c_int(),ctypes.c_int(),ctypes.c_ulong()
        assert self.n.x11.XTranslateCoordinates(self.n.display,native.get_surface().get_xid(),self.n.x11.XDefaultRootWindow(self.n.display),0,0,ctypes.byref(rx),ctypes.byref(ry),ctypes.byref(child))
        dx,dy=native.get_surface_transform()
        return round(rx.value+dx+bounds.origin.x+x),round(ry.value+dy+bounds.origin.y+y)
    def color(self,raw,stride,widget,x,y):
        px,py=self.point(widget,x,y);offset=py*stride+px*4
        return list(raw[offset:offset+3][::-1])
    def grab(self,path):
        x=self.n.x11;d=self.n.display
        ptr=x.XGetImage(d,x.XDefaultRootWindow(d),0,0,self.width,self.height,ctypes.c_ulong(-1),2)
        assert ptr
        try:
            im=ctypes.cast(ptr,ctypes.POINTER(self.Image)).contents
            assert im.bits==32 and im.byte_order==0
            raw=ctypes.string_at(im.data,im.stride*im.height)
            rows=[]
            for y in range(im.height):
                line=raw[y*im.stride:y*im.stride+im.width*4];rgb=bytearray(im.width*3)
                rgb[0::3]=line[2::4];rgb[1::3]=line[1::4];rgb[2::3]=line[0::4];rows.append(b'\0'+rgb)
            def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
            path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',im.width,im.height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b''))
            return raw,im.stride
        finally:x.XDestroyImage(ptr)


def main():
    p=argparse.ArgumentParser();p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--baseline',action='store_true');p.add_argument('--require-packaged',action='store_true');p.add_argument('--preferences-only',action='store_true');p.add_argument('--record',action='store_true');args=p.parse_args()
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    args.output.mkdir(parents=True,exist_ok=True)
    app=Application();app.register();w=Window(app,Library(args.profile/'translations'));w.set_default_size(1280,900);w.present();spin()
    n=X11Input();n.activate(w);screen=Screen(n)
    if args.require_packaged:assert 'GL' in type(w.get_renderer()).__name__,type(w.get_renderer()).__name__
    report=dict(source_import=inspect.getfile(Window),renderer=type(w.get_renderer()).__name__,gtk_version=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],scale=w.get_scale_factor(),language=os.environ.get('LANGUAGE'),baseline=args.baseline,captures=[],keys=[],geometry=[])
    def shot(name):
        n.move_at(w,2,2);spin(duration=.15);path=args.output/(name+'.png');result=screen.grab(path);report['captures'].append(path.name);return result
    def settled():spin(lambda:not w.active_tab._restoring_scroll,duration=.3)
    def menu(button,name):button.popup();spin(duration=.25);shot(name);button.popdown();spin(duration=.2)
    def walk(widget):
        yield widget;c=widget.get_first_child()
        while c:yield from walk(c);c=c.get_next_sibling()
    t=w.active_tab;t.state.comparison=None;w.sync_comparison();t.navigate('FreSegond1910','Ps.119.1');settled()
    try:
        with SystemStyleOverride() as style:
            for palette,mode in [('white','day'),('dark','night')]:
                style.set(dark=mode=='night',high=False);w.appearance.update('mode',mode);w.appearance.update('day_palette' if mode=='day' else 'night_palette',palette)
                for small in (False,True):
                    w.set_default_size(560 if small else 1280,700 if small else 900);spin()
                    settings=Gtk.Settings.get_default();old=settings.get_property('gtk-font-name')
                    if small:settings.set_property('gtk-font-name','Cantarell 16')
                    d=w.open_preferences() if hasattr(w,'open_preferences') else None
                    if not d:
                        from bible.application_surfaces import show_preferences
                        d=show_preferences(w)
                    spin();base='preferences-'+palette+('-small-large-type' if small else '-wide')
                    shot(base+'-top')
                    scrolls=[v for v in walk(d) if isinstance(v,Gtk.ScrolledWindow) and v.get_mapped() and v.get_vadjustment().get_upper()>v.get_vadjustment().get_page_size()]
                    if scrolls:
                        a=scrolls[0].get_vadjustment();a.set_value(a.get_upper()-a.get_page_size());spin();shot(base+'-bottom')
                    d.close();spin();settings.set_property('gtk-font-name',old)
            if args.preferences_only:return
            w.set_default_size(1280,900);spin();t=w.active_tab;w.appearance.update('size',24)
            for palette,mode,high in [('white','day',False),('dark','night',False),('paper','day',False),('black','night',False),('contrast-day','day',True),('contrast-night','night',True)]:
                style.set(dark=mode=='night',high=high);w.appearance.update('mode',mode)
                if not high:w.appearance.update('day_palette' if mode=='day' else 'night_palette',palette)
                settled();w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes');settled();raw,stride=shot(palette+'-study-notes')
                header=w.study.header
                header_colors=[screen.color(raw,stride,header,x,header.get_height()-3) for x in (8,header.get_width()/2,header.get_width()-8)]
                body_color=screen.color(raw,stride,w.study,8,min(300,w.study.get_height()-40))
                report.setdefault('study_colors',{})[palette]=dict(header=header_colors,body=body_color)
                if not args.baseline and not high:assert all(max(abs(a-b) for a,b in zip(c,body_color))<=1 for c in header_colors),(palette,header_colors,body_color)
                w.study.tools.set_visible_child_name('references');settled();shot(palette+'-study-references')
                w.study.tools.set_visible_child_name('commentaries');settled();shot(palette+'-study-commentary')
                menu(w.study.more,palette+'-study-actions');w.study.more.popup();spin();menu(w.study.info,palette+'-source-notices');w.study.more.popdown();spin()
                w.study_button.set_active(False);settled();shot(palette+'-reading')
                menu(w.menu,palette+'-main-menu')
                menu(w.passage_button,palette+'-passage-picker')
                menu(w.primary_version,palette+'-version-picker')
                menu(w.appearance_button,palette+'-appearance')
                b=t.text.get_buffer();start=t._marker_ends['Ps.119.1']+2;b.select_range(b.get_iter_at_offset(start),b.get_iter_at_offset(start+16))
                a=w.passage_actions;a.capture(t.text,lambda:a.ordinary(t),None);spin();shot(palette+'-selection')
                menu(getattr(a,'copy_button',None) or a.copy_options,palette+'-copy-menu')
                if a.highlight_button:menu(a.highlight_button,palette+'-annotation-menu')
                a.dismiss();b.place_cursor(b.get_iter_at_offset(start));t.text.grab_focus();n.key('Menu');spin();shot(palette+'-context-menu');n.key('Escape');spin()
            style.set(dark=False,high=False);w.appearance.update('mode','day');w.appearance.update('day_palette','white');w.appearance.update('size',24)
            t.navigate('FreSegond1910','Ps.119.1');settled();a=w.passage_actions;b=t.text.get_buffer();start=t._marker_ends['Ps.119.1'];b.select_range(b.get_iter_at_offset(start),b.get_iter_at_offset(start+20));a.capture(t.text,lambda:a.ordinary(t),None);spin()
            import bible.passage_actions as module
            original=module.BACKDROP_BLUR
            energies={}
            samples={};diagnostic={}
            for radius in (0,original):
                module.BACKDROP_BLUR=radius;a.bar.get_child().queue_draw();spin();raw,stride=shot('blur-diagnostic-'+str(radius))
                assert a.target and a.bar.get_mapped(),'Blur diagnostic requires the selection bar to be visibly open'
                x,y=screen.point(a.bar,16,12);width=a.bar.get_width()-32;height=a.bar.get_height()-24
                samples[radius]=[tuple(raw[(y+dy)*stride+(x+dx)*4:(y+dy)*stride+(x+dx)*4+3]) for dy in range(height) for dx in range(width)]
                pairs=[(samples[radius][dy*width+dx-1],samples[radius][dy*width+dx]) for dy in range(1,height-1) for dx in range(1,width-1)]
                # Exclude the sharp light foreground; inspect the actual dark
                # backdrop across the whole interior, not a font-dependent band.
                usable=[(p,q) for p,q in pairs if max(p)<100 and max(q)<100]
                energies[radius]=sum(abs(p[0]-q[0]) for p,q in usable)
                diagnostic[radius]=dict(mapped=a.bar.get_mapped(),bar_size=[a.bar.get_width(),a.bar.get_height()],high_contrast=w.reading_style.manager.get_high_contrast(),sample_origin=[x,y],usable_pairs=len(usable),paintable_size=[a.bar.backdrop.get_intrinsic_width(),a.bar.backdrop.get_intrinsic_height()] if a.bar.backdrop else None)
            report['blur_edge_energy']=energies
            report['blur_diagnostic']=diagnostic
            report['blur_changed_pixels']=sum(max(abs(a-b) for a,b in zip(p,q))>2 for p,q in zip(samples[0],samples[original]))
            print(json.dumps(dict(renderer=report['renderer'],blur_edge_energy=energies,blur_diagnostic=diagnostic,changed_pixels=report['blur_changed_pixels'])),flush=True)
            if not args.baseline:
                assert not diagnostic[original]['high_contrast'],diagnostic
                assert report['blur_changed_pixels']>len(samples[0])*.01,(energies,diagnostic)
                assert energies[original]<energies[0]*.85,(energies,diagnostic)
            module.BACKDROP_BLUR=original;a.bar.get_child().queue_draw();a.dismiss();b.place_cursor(b.get_iter_at_offset(start))
            # Use the client's actual source when available; never manufacture text.
            resource='FreBDM1707' if 'FreBDM1707' in w.library.installed() else 'FreSegond1910'
            t.navigate(resource,'Gen.6.1');settled();w.enter_immersion('bible');v=w.immersion;spin(lambda:v.layout_ready,timeout=30)
            n.move_at(v,300,400);spin();v.hide_controls();spin(duration=.5);shot('immersion-idle-start')
            video=None
            if args.record:
                video=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','x11grab','-framerate','10','-video_size',str(screen.width)+'x'+str(screen.height),'-i',os.environ['DISPLAY'],'-c:v','libx264','-preset','ultrafast','-crf','20','-pix_fmt','yuv420p',str(args.output/'immersion-idle-and-input.mp4')],stdin=subprocess.DEVNULL)
            initial=v.stream.anchor();geometry=v._geometry;start_time=time.monotonic()
            def sample(widget,clock):
                report['geometry'].append([round(time.monotonic()-start_time,3),str(v.stream.anchor()),list(v._geometry),list(getattr(v,'reading_box',()))]);return True
            tick=v.add_tick_callback(sample);spin(duration=15,timeout=20);v.remove_tick_callback(tick);shot('immersion-idle-end')
            assert v.stream.anchor()==initial and v._geometry==geometry
            for animation in (True,False):
                Gtk.Settings.get_default().set_property('gtk-enable-animations',animation)
                for key in ['Right','Right','Left','Left','Right','Left']:
                    before=v.stream.cursor;n.key(key);spin(duration=.3);after=v.stream.cursor
                    report['keys'].append(dict(key=key,animations=animation,before=str(before),after=str(after),turned=before!=after))
                    if not args.baseline:assert before!=after,(key,before,after)
            Gtk.Settings.get_default().set_property('gtk-enable-animations',True)
            # X11Input.key yields 150 ms: the next event arrives during the
            # existing 200 ms slide, including immediate direction reversals.
            for key in ['Right','Left','Right','Left']:
                before=v.stream.cursor;n.key(key);after=v.stream.cursor
                report['keys'].append(dict(key=key,animations=True,during_transition=True,before=str(before),after=str(after),turned=before!=after))
                if not args.baseline:assert before!=after,(key,before,after)
            spin(duration=.3)
            v.reveal_controls();spin(duration=.25);n.click(v.forward);spin(duration=.3);shot('immersion-pointer-next')
            if video:video.send_signal(signal.SIGINT);video.wait(timeout=10);assert video.returncode in (0,255)
            w.set_default_size(560,700);spin(lambda:v.layout_ready,duration=.5);shot('immersion-narrow')
            w.leave_immersion();spin();w.study_button.set_active(True);spin();shot('study-narrow')
    finally:
        (args.output/'report.json').write_text(json.dumps(report,indent=2));w.close();n.close()
    print(json.dumps({k:v for k,v in report.items() if k!='geometry'},indent=2))

if __name__=='__main__':main()
