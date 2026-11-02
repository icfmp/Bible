"""Native reading/header evidence; requires a marked disposable research profile."""
import argparse,inspect,json
from pathlib import Path
from unittest.mock import patch


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--baseline',action='store_true');p.add_argument('--require-packaged',action='store_true');args=p.parse_args()
    assert (args.profile/'.source-rendering-research').is_file();args.output.mkdir(parents=True,exist_ok=True)
    from bible.ui import Application,Window,Library,Gtk
    from tests.test_ui import spin
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    app=Application.get_default() or Application();app.register();records=[]
    with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False),patch('bible.catalogue_session.CatalogueSession.load_youversion_language',return_value=None):
        w=Window(app,Library(args.profile/'translations'));w.present();n=X11Input();n.activate(w);screen=Screen(n)
        try:
            w.study_button.set_active(False);w.appearance.update('size',20)
            with SystemStyleOverride() as style:
                for palette,mode in [('white','day'),('dark','night')]:
                    style.set(dark=mode=='night',high=False);w.appearance.update('mode',mode);w.appearance.update('day_palette' if mode=='day' else 'night_palette',palette)
                    for comparison in (False,True):
                        t=w.active_tab;t.navigate('ebible~fraLSG1910eb','Gen.1.22');t.state.comparison='FreBDM1744' if comparison else None;w.sync_comparison()
                        for width in (1200,560,360):
                            w.set_default_size(width,820);spin(lambda:not t._restoring_scroll and not getattr(t,'_comparison_positioning',False),duration=.5)
                            name=f'{palette}-{"comparison" if comparison else "single"}-{width}'
                            screen.grab(args.output/(name+'.png'))
                            if not args.baseline:assert w.header.get_width()<=w.get_width()+4,(name,w.header.get_width(),w.get_width())
                            row=dict(case=name,width=w.get_width(),title=w.heading.get_title(),subtitle=w.heading.get_subtitle(),tab_title=t.title(),reference=t.state.reference,primary_title=w.primary_version.caption.get_text(),secondary_title=w.compared_version.caption.get_text() if comparison else None)
                            if not args.baseline:
                                assert ':' not in row['title'] and ':' not in row['tab_title'],row
                                assert row['subtitle']=='',row
                                assert row['reference']=='Gen.1.22',row
                                assert w.primary_version.caption.get_ellipsize()==0
                                assert w.primary_version.caption.get_text()==w.library.resource(t.state.resource).description
                                assert not hasattr(t,'primary_heading') and not hasattr(t,'comparison_heading')
                                assert w.reader_controls.get_parent() is w.header_tools
                                assert t.scroll.get_margin_top()==0
                                if comparison:
                                    assert w.primary_version.get_parent() is t.primary_controls
                                    assert w.compared_version.caption.get_text()==w.library.resource(t.state.comparison).description
                                    assert w.compared_version.caption.get_ellipsize()==0
                                else:
                                    assert w.primary_version.get_parent() is w.header_title
                                    assert w.primary_version.is_ancestor(w.compact_title if width<=760 else w.header)
                            if comparison and width<760:
                                h=t.comparison_horizontal.get_hadjustment();h.set_value(h.get_upper()-h.get_page_size());spin(duration=.2)
                                screen.grab(args.output/(name+'-right.png'));h.set_value(0);spin()
                            records.append(row)
                    w.set_default_size(1200,820);t.state.comparison=None;w.sync_comparison();spin(duration=.4)
                    n.click(w.primary_version);spin();assert w.primary_version.get_popover().get_visible();n.key('Escape');spin()
                    t.state.comparison='FreBDM1744';w.sync_comparison();spin(duration=.4)
                    n.click(w.compared_version);spin();assert w.compared_version.get_popover().get_visible();n.key('Escape');spin()
        finally:w.close();n.close()
    (args.output/'verification.json').write_text(json.dumps(dict(app_import=inspect.getfile(Window),baseline=args.baseline,gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],cases=records),ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
