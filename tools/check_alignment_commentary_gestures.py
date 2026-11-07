"""Additional native bidirectional Study gestures; marked developer profile only."""
import argparse,hashlib,inspect,json
from pathlib import Path
from unittest.mock import patch
from bible.ui import Application,Window,Library,Gtk
from bible.reference_resolution import resolve
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input
from tools.check_client_feedback import Screen


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--require-packaged',action='store_true');a=p.parse_args()
    assert (a.profile/'.alignment-test-profile').is_file();a.output.mkdir(parents=True,exist_ok=True)
    if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    app=Application.get_default() or Application();app.register();w=Window(app,Library(a.profile/'translations'))
    Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
    w.set_default_size(1440,960);w.present();spin()
    n=X11Input();n.activate(w);screen=Screen(n)
    report=dict(app_import=inspect.getfile(Window),renderer=type(w.get_renderer()).__name__,
        network_isolated=len(Path('/proc/net/route').read_text().splitlines())<=1,checks=[],complete=False)
    success=False
    def settled():
        spin(lambda:not w.active_tab._restoring_scroll and not w.study._positioning and not w.reading_sync.pending,duration=.4,timeout=30)
    try:
        with patch('urllib.request.urlopen',side_effect=AssertionError('Offline reading path')):
            for name in ('FreSegond1910','KJV','youversion~YV133','youversion~YV152','youversion~YV2367'):
                w.end_comparison();t=w.active_tab;assert t.navigate(name,'Gen.1.1')
                w.study_button.set_active(True);w.study.tools.set_visible_child_name('commentaries')
                t.state.commentary='MHC';w.study.refresh(force=True);settled()
                assert w.study.entry_text
                for iteration in range(3):
                    previous=t.scroll.get_vadjustment().get_value();n.wheel(t.text,12 if iteration!=1 else -8);settled()
                    assert abs(t.scroll.get_vadjustment().get_value()-previous)>1
                    visible=t.visible_reference();expected=resolve(visible,t.reader.versification,w.study.reader,require_entry=False)
                    assert w.study.current_position==w.study.reader.index.locate(expected.start),(name,visible,w.study.status.get_text())
                    report['checks'].append(dict(source=name,driver='bible',round=iteration,visible=visible,commentary=expected.start))
                    previous=w.study.scroll.get_vadjustment().get_value();n.wheel(w.study.text,12 if iteration!=1 else -6);settled()
                    assert abs(w.study.scroll.get_vadjustment().get_value()-previous)>1
                    position=w.study.visible_section();assert position is not None
                    section=w.study.reader.index.sections[position]
                    if section.introduction:
                        assert w.study.current_position==position
                        report['checks'].append(dict(source=name,driver='commentary',round=iteration,introduction=True))
                    else:
                        first=resolve(section.start,w.study.reader.versification,t.reader).start
                        last=resolve(section.end,w.study.reader.versification,t.reader).end
                        current=t.reader.key(t.state.reference).getIndex()
                        assert t.reader.key(first).getIndex()<=current<=t.reader.key(last).getIndex(),(name,section.start,section.end,t.state.reference)
                        assert w.study.current_position==position
                        report['checks'].append(dict(source=name,driver='commentary',round=iteration,range=[first,last],current=t.state.reference))
                n.move_at(w,2,2);screen.grab(a.output/(name.replace('~','-')+'-following.png'))
            # Leave the shared profile in the same source-qualified session
            # expected by the subsequent independent offline restart check.
            t=w.active_tab;assert t.navigate('youversion~YV133','Gen.11.3')
            t.state.comparison='youversion~YV2367';w.sync_comparison();settled()
            t.state.commentary='MHC';w.study.refresh(force=True);settled();assert w.study.entry_text
            success=True
    finally:
        report['complete']=success;w.close();n.close()
        (a.output/'commentary-gestures.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
