"""Native selection-bar bounds and dismissal, including physical HiDPI input."""
import argparse,ctypes,inspect,json
from pathlib import Path
import gi
gi.require_version("Graphene","1.0")
from gi.repository import Graphene
from bible.ui import Application,Window,Library,Gtk
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input
from tools.check_client_feedback import Screen


class ScaledInput(X11Input):
    def move_at(self,widget,local_x,local_y):
        native=widget.get_native();found,point=widget.compute_point(native,Graphene.Point().init(local_x,local_y))
        assert found and widget.get_mapped()
        x,y,child=ctypes.c_int(),ctypes.c_int(),ctypes.c_ulong()
        assert self.x11.XTranslateCoordinates(self.display,native.get_surface().get_xid(),self.x11.XDefaultRootWindow(self.display),0,0,ctypes.byref(x),ctypes.byref(y),ctypes.byref(child))
        dx,dy=native.get_surface_transform();scale=widget.get_scale_factor()
        self.xtest.XTestFakeMotionEvent(self.display,-1,round(x.value+(point.x-dx)*scale),round(y.value+(point.y-dy)*scale),0)
        self.x11.XFlush(self.display)


def walk(widget):
    yield widget;child=widget.get_first_child()
    while child:yield from walk(child);child=child.get_next_sibling()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('output',type=Path);p.add_argument('--require-packaged',action='store_true');a=p.parse_args()
    assert (a.profile/'.ready-batch-test-profile').is_file()
    if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    a.output.mkdir(parents=True,exist_ok=True);app=Application();app.register();w=Window(app,Library(a.profile/'translations'))
    w.set_default_size(720,840);w.present();spin();n=ScaledInput();n.activate(w);screen=Screen(n)
    report=dict(complete=False,app_import=inspect.getfile(Window),scale=w.get_scale_factor(),cases=[])
    notes=w.notes_store.all();highlights=dict(w.highlights.entries)
    def capture(tab):
        buf=tab.text.get_buffer();first=tab._marker_ends['Gen.11.7'];last=tab._verse_ranges['Gen.11.9'][1]
        buf.select_range(buf.get_iter_at_offset(first),buf.get_iter_at_offset(last))
        actions=w.passage_actions;actions.capture(tab.text,lambda:actions.ordinary(tab),None)
        spin(lambda:actions.bar.get_mapped() and not actions.adapt_tick,duration=.3)
        return actions
    try:
        for width in (720,360):
            w.set_default_size(width,840);spin()
            tab=w.active_tab;tab.navigate('youversion~YV104','Gen.11.7');spin(lambda:not tab._restoring_scroll)
            w.study_button.set_active(False)
            for mode in ('day','night'):
                w.appearance.update('mode',mode);actions=capture(tab)
                assert not hasattr(actions,'close_button')
                assert actions.word_button.get_mapped() and actions.note_button.get_mapped() and actions.copy_button.get_mapped()
                assert all(button.get_mapped() for button,check in actions.highlight_buttons.values())
                assert actions.bar.get_width()<=actions.target.source.parent.get_width(),(width,actions.bar.get_width())
                visible_width=actions.bar.get_width();controls=[]
                for button in walk(actions.actions):
                    if isinstance(button,(Gtk.Button,Gtk.MenuButton)) and button.get_mapped():
                        ok,bounds=button.compute_bounds(actions.bar);assert ok
                        assert bounds.origin.x>=-1 and bounds.origin.x+bounds.size.width<=actions.bar.get_width()+1
                        assert bounds.origin.y>=-1 and bounds.origin.y+bounds.size.height<=actions.bar.get_height()+1
                        controls.append([round(bounds.origin.x),round(bounds.origin.y),round(bounds.size.width),round(bounds.size.height)])
                assert len(controls)>=6
                screen.grab(a.output/(str(width)+'-'+mode+'.png'))
                n.key('Escape');spin();assert not actions.bar.get_visible() and not actions.adapt_tick
                actions=capture(tab);n.wheel(tab.text,1);spin()
                assert not actions.bar.get_visible() and actions.bar.backdrop is None and not actions.adapt_tick
                actions=capture(tab)
                # A physical outside click, with coordinates scaled at the native boundary.
                n.click_at(tab.text,3,3);spin();assert not actions.bar.get_visible()
                report['cases'].append(dict(width=w.get_width(),mode=mode,toolbar_width=visible_width,buttons=len(controls),escape=True,first_wheel_hides=True,outside_pointer=True))
        assert w.notes_store.all()==notes and w.highlights.entries==highlights
        report.update(complete=True,personal_data_unchanged=True,limitation='Native X11 mouse/keyboard; physical touch and client Wayland/GPU are not tested.')
    finally:
        w.close();n.close();(a.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
