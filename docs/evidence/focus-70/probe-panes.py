"""Native Alt+Tab through a real nested Mutter Wayland compositor.

Run on a disposable profile with a second application, MUTTER_XID and outer X11
input. Both GDK Wayland and XTest are intentional: Mutter owns inner activation.
This is distinct from the client's GNOME Shell session and deferred accessibility.
"""
import argparse,ctypes,json,os,time,inspect
from pathlib import Path
import gi
gi.require_version('Gtk','4.0');gi.require_version('Adw','1')
from gi.repository import Gtk,GLib,Gdk
from bible.ui import Application,Window,Library
from tools.check_alpha_ui import X11Input

def spin(until=lambda:True,duration=.15):
 loop=GLib.MainLoop();start=time.monotonic();failed=[]
 def poll():
  if time.monotonic()-start>15:failed.append('timeout');loop.quit();return False
  if time.monotonic()-start>=duration and until():loop.quit();return False
  return True
 GLib.timeout_add(15,poll);loop.run();assert not failed
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--legacy',action='store_true');parser.add_argument('--require-packaged',action='store_true')
    parser.add_argument('--extended',action='store_true');parser.add_argument('--offline',action='store_true')
    args=parser.parse_args()
    if args.offline:assert len(Path('/proc/net/route').read_text().splitlines())<=1
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    app=Application();app.register();w=Window(app,Library(args.profile/'translations'));w.maximize();w.present()
    w.appearance.update('mode','day');w.appearance.update('size',14);w.appearance.update('day_palette','white')
    w.active_tab.navigate('FreSegond1910','Gen.5.11');spin(lambda:not w.active_tab._restoring_scroll,duration=.7)
    view=w.active_tab.text;inputs=X11Input()
    outer=int(os.environ['MUTTER_XID'])
    root_x,root_y,child=ctypes.c_int(),ctypes.c_int(),ctypes.c_ulong()
    assert inputs.x11.XTranslateCoordinates(inputs.display,outer,inputs.x11.XDefaultRootWindow(inputs.display),0,0,ctypes.byref(root_x),ctypes.byref(root_y),ctypes.byref(child))
    # This only delivers keyboard input to the nested compositor. Mutter owns all
    # inner Wayland activation; no programmatic focus/reset is applied to Bible.
    inputs.x11.XSetInputFocus(inputs.display,outer,2,0);inputs.x11.XFlush(inputs.display)
    found,bounds=view.compute_bounds(w);assert found
    offset=w.active_tab._marker_ends['Gen.5.11']+6
    rect=view.get_iter_location(view.get_buffer().get_iter_at_offset(offset))
    cx,cy=view.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,rect.x+2,rect.y+rect.height//2)
    x=int(root_x.value+bounds.origin.x+cx);y=int(root_y.value+bounds.origin.y+cy)
    inputs.xtest.XTestFakeMotionEvent(inputs.display,-1,x,y,0)
    inputs.xtest.XTestFakeButtonEvent(inputs.display,1,True,0);inputs.xtest.XTestFakeButtonEvent(inputs.display,1,False,0);inputs.x11.XFlush(inputs.display);spin(duration=.4)
    from PIL import ImageGrab
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    report={'app_import':inspect.getfile(Window),'gtk_version':'.'.join(str(v) for v in (Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version())),'gdk_display':type(w.get_display()).__name__,'surface':type(w.get_surface()).__name__,'compositor':'Mutter 48.7 nested Wayland; XTest to outer compositor','offline':args.offline,'states':[],'css':w.reading_style.css,'accessibility':'Deferred; not tested','personal_gnome_desktop':'Not accessed; actual nested Mutter Wayland app switching'}
    def record(stage):
     r=dict(stage=stage,active=w.is_active(),window_focus_visible=w.get_focus_visible(),view_has_focus=view.has_focus(),view_visible_focus=view.has_visible_focus(),state_flags=int(view.get_state_flags()),reference=w.active_tab.state.reference,scroll=view.get_visible_rect().y,width=view.get_width(),height=view.get_height())
     report['states'].append(r);print(json.dumps(r),flush=True);ImageGrab.grab().save(out/(stage+'.png'))
    def chord(*names):
     codes=[inputs.x11.XKeysymToKeycode(inputs.display,inputs.x11.XStringToKeysym(n.encode())) for n in names]
     for code in codes:inputs.xtest.XTestFakeKeyEvent(inputs.display,code,True,0)
     for code in reversed(codes):inputs.xtest.XTestFakeKeyEvent(inputs.display,code,False,0)
     inputs.x11.XFlush(inputs.display);spin(duration=.6)
    record('pointer-before')
    assert w.is_active() and view.has_focus() and not view.has_visible_focus()
    before=(w.active_tab.state.reference,view.get_visible_rect().y,view.get_width(),view.get_height())
    chord('Alt_L','Tab');record('away');assert not w.is_active()
    chord('Alt_L','Tab');record('returned')
    assert w.is_active() and view.has_visible_focus() and w.get_focus_visible()
    assert before==(w.active_tab.state.reference,view.get_visible_rect().y,view.get_width(),view.get_height())
    # Actual rendered pixels distinguish a full rectangle from a visible leading mark.
    found,bounds=view.compute_bounds(w);assert found
    image=ImageGrab.grab().convert('RGB');scale=view.get_scale_factor()
    def pixel(px,py):return image.getpixel((round(root_x.value+(bounds.origin.x+px)*scale),round(root_y.value+(bounds.origin.y+py)*scale)))
    if args.legacy:
     assert pixel(1,view.get_height()/2)==(32,32,32)
     assert pixel(20,1)==(32,32,32)
    else:
     assert pixel(1,view.get_height()/2)==(0,63,135)
     for px,py in ((view.get_width()-2,view.get_height()/2),(20,1),(20,view.get_height()-2)):
      assert pixel(px,py)==(255,255,255),(px,py,pixel(px,py))
    report['actual_alt_tab_and_rendered_focus']='PASS'
    report['reference_scroll_allocation_preserved']=True
    chord('Tab');record('keyboard-tab');assert w.get_focus_visible() and not view.has_focus()
    chord('Shift_L','Tab');record('keyboard-back');assert view.has_visible_focus()
    if args.extended:
     chord('Shift_L','Right');buffer=view.get_buffer();selection=buffer.get_selection_bounds();assert selection
     selected=buffer.get_text(*selection,False);chord('Control_L','c');copied=[]
     def copied_text(clipboard,result):copied.append(clipboard.read_text_finish(result))
     view.get_clipboard().read_text_async(None,copied_text);spin(lambda:bool(copied));assert copied[0]==selected
     chord('Right');report['native_selection_copy']='PASS'
     original_study=w.study_button.get_active();chord('F9');assert w.study_button.get_active()!=original_study
     chord('F9');assert w.study_button.get_active()==original_study;report['native_F9']='PASS'
     chord('F11');spin(lambda:w.immersion and w.immersion.layout_ready)
     chord('F10');assert w.immersion.controls_focused();chord('F11');spin(lambda:w.immersion is None)
     report['native_F10_F11']='PASS'
     tabs=len(w.tabs());original=w.active_tab;chord('Control_L','t');assert len(w.tabs())==tabs+1
     chord('Control_L','w');assert len(w.tabs())==tabs and w.active_tab is original;report['native_tab_switch']='PASS'
     notes=w.notes_store.all();chord('Control_L','n');spin(lambda:w.note_editor and w.note_editor.get_mapped())
     chord('Alt_L','F4');spin(lambda:w.note_editor.closed);assert w.notes_store.all()==notes;report['native_note_open_close_preserved_data']='PASS'
    def switch_pane(target,name):
        nonlocal view
        view=target;spin(lambda:view.get_mapped(),duration=.4)
        found,bounds=view.compute_bounds(w);assert found
        px=int(root_x.value+bounds.origin.x+min(100,view.get_width()/2));py=int(root_y.value+bounds.origin.y+view.get_height()/2)
        inputs.xtest.XTestFakeMotionEvent(inputs.display,-1,px,py,0)
        inputs.xtest.XTestFakeButtonEvent(inputs.display,1,True,0);inputs.xtest.XTestFakeButtonEvent(inputs.display,1,False,0);inputs.x11.XFlush(inputs.display);spin(duration=.6)
        assert view.has_focus(),name
        before=(w.active_tab.state.reference,view.get_visible_rect().y,view.get_width(),view.get_height())
        chord('Alt_L','Tab');assert not w.is_active()
        chord('Alt_L','Tab');assert w.is_active() and view.has_visible_focus(),name
        assert before==(w.active_tab.state.reference,view.get_visible_rect().y,view.get_width(),view.get_height()),name
        found,bounds=view.compute_bounds(w);assert found
        im=ImageGrab.grab().convert('RGB');scale=view.get_scale_factor()
        p=(round(root_x.value+(bounds.origin.x+1)*scale),round(root_y.value+(bounds.origin.y+view.get_height()/2)*scale))
        shared=w.reading_style.scope in view.get_css_classes()
        if shared:assert im.getpixel(p)==(0,63,135),(name,p,im.getpixel(p))
        else:assert 'study-reader' in view.get_css_classes()
        record(name);report[name]='PASS: real Wayland Alt+Tab, native focus and preserved position'+('; visible leading mark' if shared else '; separate native commentary style retained')
    tab=w.active_tab;tab.state.comparison='KJV';w.sync_comparison()
    spin(lambda:tab.comparison_text.get_mapped() and tab._comparison_reader is not None,duration=.5)
    switch_pane(tab.comparison_text,'comparison')
    tab.state.commentary='MHC';w.study_button.set_active(True);w.study.tools.set_visible_child_name('commentaries');w.study.refresh()
    spin(lambda:w.study.text.get_mapped() and bool(w.study.text.get_buffer().props.text),duration=.5)
    switch_pane(w.study.text,'commentary-study-open')
    w.study_button.set_active(False);tab.state.comparison=None;w.sync_comparison();spin(duration=.5)
    chord('F11');spin(lambda:w.immersion and w.immersion.layout_ready)
    switch_pane(w.immersion.views[0],'immersion')
    chord('F11');spin(lambda:w.immersion is None)
    report['status']='PASS' 
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');w.close();inputs.close()


if __name__=='__main__':main()
