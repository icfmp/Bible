"""Real Library categories and optional actual download in a disposable profile."""
import argparse,inspect,json
from pathlib import Path
from unittest.mock import patch


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--ui-font');p.add_argument('--baseline',action='store_true');p.add_argument('--require-packaged',action='store_true');p.add_argument('--install',action='store_true');p.add_argument('--resource',default='openbible-places');a=p.parse_args()
    assert (a.profile/'.source-rendering-research').is_file();a.output.mkdir(parents=True,exist_ok=True)
    from bible.ui import Application,Window,Library,Gtk
    from tests.test_ui import spin
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    from bible.study_resources import REFERENCE_RESOURCE_ID
    if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    if a.ui_font:Gtk.init();Gtk.Settings.get_default().props.gtk_font_name=a.ui_font
    app=Application.get_default() or Application();app.register();records=[];transfer={}
    with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False),patch('bible.catalogue_session.CatalogueSession.load_youversion_language',return_value=None):
        w=Window(app,Library(a.profile/'translations'));w.present();d=w.open_library('study');spin(lambda:not d.busy)
        n=X11Input();n.activate(d);screen=Screen(n)
        try:
            if a.install:
                resource=d.study_resources.resource(a.resource)
                if resource.id not in d.installed_ids():
                    samples=[];original=d.report_progress
                    def progress(done,total):samples.append([done,total]);original(done,total)
                    with patch.object(d,'report_progress',side_effect=progress):
                        d.install(resource=resource)
                        spin(lambda:bool(samples) or not d._transfer_busy,timeout=90)
                        screen.grab(a.output/'actual-download.png')
                        task=d._task_id;d.kind.set_selected(0);d.kind.set_selected(2)
                        assert d._task_id==task
                        spin(lambda:not d.busy,timeout=180)
                    assert d._phase=='complete',(d._phase,d.status.get_text())
                    assert resource.id in d.installed_ids()
                    transfer=dict(actual_download=True,samples=samples,resource=resource.id,metadata=d.study_resources.stores[resource.id].metadata(),same_task_after_switch=True)
                else:transfer=dict(actual_download=False,already_installed=True)
            with SystemStyleOverride() as style:
                for dark in (False,True):
                    style.set(dark=dark,high=False);w.appearance.update('mode','night' if dark else 'day')
                    for category in range(3):
                        d.kind.set_selected(category);d.search.set_text('');d.filter_resources();spin(lambda:not d.busy)
                        for width in (560,360):
                            d.set_default_size(width,720);spin(duration=.3)
                            name=f'{"dark" if dark else "light"}-{category}-{width}'
                            screen.grab(a.output/(name+'.png'))
                            record=dict(case=name,width=d.get_width(),category=category,category_control_visible=d.type_tabs.get_visible(),resources=[r.id for r in d.filtered_resources])
                            if not a.baseline:
                                assert len(d.category_buttons)==3 and d.type_tabs.get_visible()
                                assert d.type_tabs.get_width()<=d.get_width()
                                for button in d.category_buttons:
                                    text=button.get_child()
                                    assert text.get_height()>=text.get_layout().get_pixel_size()[1],record
                                if category==2:
                                    assert len(d.filtered_resources)==4
                                    assert not d.language.get_visible() and not d.source_filter.get_visible()
                            records.append(record)
        finally:d.close();w.close();n.close()
    (a.output/'verification.json').write_text(json.dumps(dict(app_import=inspect.getfile(Window),baseline=a.baseline,gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],cases=records,transfer=transfer),ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
