"""Actual X11 wheel and long scrollbar drags, without programmatic scrolling.

Synthetic SWORD fixtures; run on a dedicated dbus-run-session / Xvfb display.
A physical touchpad, Wayland and assistive technology still need manual checks.
"""
from pathlib import Path
import tempfile
from bible.ui import Application,Window,Library
from tests.test_ui import installed_fixture,spin
from tests.test_reading_sync import linked_commentary
from tools.check_alpha_ui import X11Input


def drag_scrollbar(native,scroll,observed):
    bar=scroll.get_vscrollbar();slider=bar.get_first_child()
    first,last=slider.get_slider_range()
    native.drag_at(bar,bar.get_width()/2,(first+last)/2,bar.get_height()-max(8,(last-first)/2),observed)


def main():
    app=Application();app.register();native=X11Input()
    with tempfile.TemporaryDirectory() as directory:
        installed_fixture(directory,entries=[(f'Gen.1.{i}',f'VERSE {i} SOURCE TEST '*90) for i in range(1,9)]+[('Gen.2.1','NEXT CHAPTER SOURCE TEST')])
        linked_commentary(directory)
        window=Window(app,Library(Path(directory)/'translations'));window.present();window.set_default_size(1180,780)
        try:
            tab=window.active_tab;study=window.study
            tab.state.commentary='Notes';window.study_button.set_active(True);study.refresh()
            # Keep tracks visible for reproducible pointer coordinates.
            tab.scroll.set_overlay_scrolling(False);study.scroll.set_overlay_scrolling(False)
            spin(lambda:not tab._restoring_scroll and not study._positioning,duration=.3)
            history=len(tab.state.history);study.text.grab_focus();focus=window.get_focus()
            initial_driver=window.reading_sync.driver
            native.move_at(study.text,20,20);spin()
            assert window.reading_sync.driver==initial_driver,'Hover changed the driver'
            before=tab.scroll.get_vadjustment().get_value()
            native.wheel(tab.text,8)
            spin(lambda:tab.state.reference==tab.visible_reference() and not study._positioning)
            assert tab.scroll.get_vadjustment().get_value()>before
            assert window.reading_sync.driver=='bible'
            assert window.get_focus() is focus,'Follower changed keyboard focus'
            followed=[]
            def bible_moved():
                reference=tab.visible_reference()
                spin(lambda:tab.state.reference==reference and not study._positioning)
                followed.append(reference)
            drag_scrollbar(native,tab.scroll,bible_moved)
            assert len(set(followed))>1,followed
            assert len(tab.state.history)==history
            # Restore a genuinely indexed section before manipulating its track.
            tab.select_verse('Gen.1.1');study.follow('Gen.1.1')
            spin(lambda:not study._positioning)
            before=study.scroll.get_vadjustment().get_value();native.wheel(study.text,3)
            spin(lambda:not study._positioning)
            assert study.scroll.get_vadjustment().get_value()>before
            assert window.reading_sync.driver=='commentary'
            sections=[]
            def commentary_moved():
                def aligned():
                    if study._positioning or tab._restoring_scroll:return False
                    position=study.visible_section();section=study.reader.index.sections[position]
                    return section.introduction or section.contains_index(tab.reader.key(tab.state.reference).getIndex())
                try:spin(aligned)
                except AssertionError as error:
                    position=study.visible_section();section=study.reader.index.sections[position]
                    raise AssertionError({'visible_section':section.start,'bible_reference':tab.state.reference,
                                          'driver':window.reading_sync.driver,'pending':window.reading_sync.pending,
                                          'needs_sync':window.reading_sync.needs_sync,'positioning':study._positioning}) from error
                section=study.reader.index.sections[study.visible_section()]
                if not section.introduction:sections.append(section.start)
            drag_scrollbar(native,study.scroll,commentary_moved)
            assert sections,sections
            assert len(tab.state.history)==history
            print('PASS: native wheel in both panes; two scrollbar drags >1.5 seconds; live passage following; focus and history preserved')
            print({'bible_references_during_drag':followed,'commentary_sections_during_drag':sections})
        finally:window.close();native.close()


if __name__=='__main__':main()
