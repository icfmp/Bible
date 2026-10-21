"""Real offline book pagination and GTK responsiveness probe for #24."""
import argparse
from pathlib import Path
import time
from unittest.mock import patch


def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');parser.add_argument('--screenshot');args=parser.parse_args()
    from bible.ui import Application,Window,Gtk,GLib
    from bible.library import Library
    from bible.paged_sources import PageAddress
    from tests.test_ui import spin
    app=Application.get_default() or Application();app.register()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline verification')):
        window=Window(app,Library(Path(args.profile)/'translations'));window.set_default_size(1200,900);window.present()
        try:
            assert window.active_tab.navigate('FreSegond1910','Gen.1.1')
            spin(lambda:not window.active_tab._restoring_scroll)
            ticks=[];started=time.monotonic()
            timer=GLib.timeout_add(10,lambda:ticks.append(time.monotonic()) or True)
            try:
                assert window.enter_immersion()
                reading=window.immersion
                spin(lambda:reading.stream.cursor is not None and reading.layout_ready,duration=.3)
            finally:GLib.source_remove(timer)
            assert len(ticks)>2,'GTK main loop did not run during preparation'
            plan=reading.stream.plan('Gen');document=plan.document
            assert ''.join(document.text[p.start:p.end] for p in plan.pages)==document.text
            chapter_titles=[s for s in document.styles if s.kind=='chapter'][1:]
            joins=[(style,plan.containing(style.start)) for style in chapter_titles
                   if plan.pages[plan.containing(style.start)].start<style.start
                   and plan.pages[plan.containing(style.start)].end>style.end+1]
            assert joins,'No chapter was allowed to continue within a page'
            style,index=joins[0]
            reading.stream.cursor=PageAddress('Gen',index//reading.count*reading.count)
            reading.stream.requested_anchor=None;reading.render();spin(lambda:reading.layout_ready,duration=.3)
            if args.screenshot:
                from PIL import ImageGrab
                ImageGrab.grab().save(args.screenshot)
            largest_gap=max((b-a for a,b in zip([started]+ticks,ticks)),default=0)
            print(dict(book='Gen',pages=len(plan.pages),chapters_continuing_within_page=len(joins),
                       preparation_seconds=ticks[-1]-started,gtk_heartbeat_ticks=len(ticks),
                       largest_heartbeat_gap=largest_gap,exact_page_partition=True,offline=True),flush=True)
            # Reflow keeps the canonical in-verse anchor while the worker prepares.
            anchor=reading.stream.anchor()
            window.appearance.update('line_spacing','very-airy')
            spin(lambda:reading.stream.cursor is not None and reading.layout_ready,duration=.3)
            assert reading.stream.anchor()==anchor
            window.leave_immersion();spin(lambda:not window.active_tab._restoring_scroll)
        finally:window.close()


if __name__=='__main__':main()
