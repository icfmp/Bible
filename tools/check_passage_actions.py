"""Native real-resource selection actions; use a disposable TEST profile only."""
import argparse
from pathlib import Path
from unittest.mock import patch
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input
from bible.ui import Application,Window,Library,Gtk


def point(view,offset):
    rect=view.get_iter_location(view.get_buffer().get_iter_at_offset(offset))
    x,y=view.buffer_to_window_coords(Gtk.TextWindowType.WIDGET,rect.x,rect.y)
    return x+max(1,rect.width/3),y+rect.height/2


def hold(native,key,down):
    code=native.x11.XKeysymToKeycode(native.display,native.x11.XStringToKeysym(key.encode()))
    native.xtest.XTestFakeKeyEvent(native.display,code,down,0);native.x11.XFlush(native.display);spin(duration=.06)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');parser.add_argument('prefix');parser.add_argument('--synthetic',action='store_true');parser.add_argument('--no-screenshots',action='store_true');args=parser.parse_args()
    def capture(path):
        if not args.no_screenshots:
            from PIL import ImageGrab
            ImageGrab.grab().save(path)
    primary,secondary,system='FreSegond1910','FreLSN1872','Calvin'
    if args.synthetic:
        profile=Path(args.profile)
        if profile.exists():parser.error('--synthetic requires a new disposable profile')
        from tests.test_ui import installed_fixture
        primary,secondary,system='Test','Other','Segond'
        for name,v11n in [(primary,'KJV'),(secondary,system)]:
            installed_fixture(profile,name,entries=[(f'Gen.1.{i}',f'SENTINEL {name} verse {i}; TEST DATA ONLY. '*12) for i in range(1,5)],versification=v11n)
        print('SYNTHETIC native fixtures: sentinel data only, not scripture',flush=True)
    app=Application();app.register();native=X11Input()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline test')):
        window=Window(app,Library(Path(args.profile)/'translations'));window.set_default_size(1440,900);window.present()
        try:
            window.appearance.reset();window.appearance.update('mode','day')
            window.study_button.set_active(False)
            tab=window.active_tab;tab.navigate(primary,'Gen.1.1');tab.state.comparison=None;tab.refresh_comparison()
            spin(lambda:not tab._restoring_scroll)
            actions=window.passage_actions;view=tab.text;buffer=view.get_buffer();body=tab._marker_ends['Gen.1.1']
            assert not actions.bar.get_visible()
            native.click_at(view,*point(view,body+4));spin(lambda:actions.target is not None)
            assert actions.target.references==('Gen.1.1',) and actions.target.source.resource==primary
            capture(args.prefix+'-single.png')
            # Complete a real pointer selection; do not show the bar mid-drag.
            first,last=point(view,body+3),point(view,body+18)
            native.move_at(view,*first);native.xtest.XTestFakeButtonEvent(native.display,1,True,0);native.x11.XFlush(native.display)
            spin(duration=.1)
            for i in range(1,9):
                native.move_at(view,first[0]+(last[0]-first[0])*i/8,first[1]+(last[1]-first[1])*i/8)
                spin(duration=.04);assert not actions.bar.get_visible()
            native.xtest.XTestFakeButtonEvent(native.display,1,False,0);native.x11.XFlush(native.display)
            spin(lambda:actions.target is not None)
            assert actions.target.native_selection
            bounds=tuple(i.get_offset() for i in buffer.get_selection_bounds());expected=actions.target.text
            native.click(actions.copy_button);copied=[]
            window.get_clipboard().read_text_async(None,lambda clipboard,result:copied.append(clipboard.read_text_finish(result)))
            spin(lambda:bool(copied));assert copied[0]==expected
            assert tuple(i.get_offset() for i in buffer.get_selection_bounds())==bounds
            capture(args.prefix+'-partial.png')
            native.click(actions.copy_options);native.key('Escape');assert actions.bar.get_visible()
            native.click(actions.copy_options);native.click_at(view,view.get_width()-8,100)
            spin();assert not actions.bar.get_visible() and not actions.copy_popover.get_visible()
            assert tuple(i.get_offset() for i in buffer.get_selection_bounds())==bounds
            view.grab_focus();buffer.place_cursor(buffer.get_iter_at_offset(body+4))
            hold(native,'Shift_L',True)
            for _ in range(5):native.key('Right')
            hold(native,'Shift_L',False);spin(lambda:actions.target is not None)
            assert window.get_focus() is view and actions.target.native_selection
            native.key('Escape');assert not actions.bar.get_visible()
            tab.state.comparison=secondary;window.sync_comparison()
            spin(lambda:not getattr(tab,'_comparison_positioning',False) and not tab._restoring_scroll)
            other=tab.comparison_text;offset=tab._comparison_markers['Gen.1.2']
            native.click_at(other,*point(other,offset+4));spin(lambda:actions.target is not None)
            assert actions.target.source.resource==secondary
            assert actions.target.source.reader.versification==system
            if actions.highlight_button:
                saved=actions.target
                native.click(actions.highlight_button)
                native.click(actions.highlight_popover.get_child().get_first_child())
                for reference in saved.references:
                    mark=window.highlights.entries[(system,reference)]
                    assert mark['resource']==secondary and mark['color']=='yellow'
                assert actions.target==saved and actions.valid()
                capture(args.prefix+'-highlight-candidate.png')
            native.click(actions.note_button);editor=window.note_editor
            assert editor.context['origin_translation']==secondary and editor.context['versification']==system
            editor.close();spin()
            capture(args.prefix+'-comparison.png')
            native.click(actions.compare_button)
            assert tab.state.resource==primary and tab.state.reference=='Gen.1.2'
            assert window.compared_version.popover.get_visible();native.key('Escape')
            actions.dismiss();tab.state.comparison=None;tab.refresh_comparison()
            tab.navigate(primary,'Gen.1.1');spin(lambda:not tab._restoring_scroll)
            assert window.enter_immersion('bible');spin(lambda:window.immersion.layout_ready)
            reading=window.immersion;page=reading.views[0];document,base,end=page._study_page
            span=next(s for s in document.spans if base<=s.body<end)
            native.click_at(page,*point(page,span.body-base+3));spin(lambda:actions.target is not None)
            assert actions.target.source.side=='immersion' and actions.bar.get_parent() is reading
            cursor=reading.stream.cursor
            hold(native,'Shift_L',True);native.key('Right');hold(native,'Shift_L',False)
            spin(lambda:actions.target is not None and actions.target.native_selection)
            assert reading.stream.cursor==cursor
            capture(args.prefix+'-immersion.png')
            native.key('Escape');assert window.immersion is reading and not actions.bar.get_visible()
            native.key('Escape');assert window.immersion is None
            print('PASS: native single verse, completed drag, exact partial Copy, retained selection, '
                  'keyboard extension without focus theft, nested Escape, comparison note source/versification, '
                  'mapped Compare and immersive action/close lifecycle',flush=True)
        finally:window.close();native.close()


if __name__=='__main__':main()
