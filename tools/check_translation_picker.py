"""Original GTK captures and native picker input on disposable real resources.

Never exports profile data, Scripture dumps or traces. Use --require-packaged
to prove application imports come from the installed Flatpak, not this checkout.
"""
import argparse,inspect
from pathlib import Path
from unittest.mock import patch


def prepare(root):
    marker=root/'.translation-picker-research'
    if root.exists() and not marker.exists():raise ValueError('Refusing an unmarked profile')
    root.mkdir(parents=True,exist_ok=True);marker.write_text('Disposable picker validation\n')
    from bible.library import Library,catalogue
    from bible.youversion_install import fetch_resource,acknowledgement
    library=Library(root/'translations');resources=catalogue()
    for name in ('KJV','FreSegond1910'):
        if name not in library.installed():library.install(next(r for r in resources if r.name==name))
    for identifier in (21,93):
        if 'youversion~YV'+str(identifier) not in library.installed():
            resource=fetch_resource(identifier);library.install(resource,permission=acknowledgement(resource))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--prepare',action='store_true');p.add_argument('--baseline',action='store_true');p.add_argument('--require-packaged',action='store_true');args=p.parse_args()
    if args.prepare:prepare(args.profile)
    assert (args.profile/'.translation-picker-research').is_file()
    args.output.mkdir(parents=True,exist_ok=True)
    from bible.ui import Application,Window,Library,Gtk
    from tests.test_ui import spin
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    if args.require_packaged:assert inspect.getfile(Window).startswith('/app/')
    app=Application.get_default() or Application();app.register();records=[];actions=[]
    with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):
        w=Window(app,Library(args.profile/'translations'));w.present();spin()
        renderer=type(w.get_renderer()).__name__;n=X11Input();n.activate(w);screen=Screen(n);settings=Gtk.Settings.get_default();font=settings.props.gtk_font_name
        try:
            w.study_button.set_active(False);t=w.active_tab;t.navigate('youversion~YV21','John.3.16')
            spin(lambda:not t._restoring_scroll)
            with SystemStyleOverride() as style:
                for dark in (False,True):
                    style.set(dark=dark,high=False)
                    for width in (1200,560,360):
                        w.set_default_size(width,820);spin(lambda:not w._controls_tick,duration=.4)
                        for kind in ('primary','compared','comparison'):
                            t.state.comparison=None if kind=='primary' else 'KJV';w.sync_comparison();spin(duration=.3)
                            chooser=w.primary_version if kind=='primary' else w.compared_version
                            button=w.comparison_button if kind=='comparison' else chooser
                            pop=w.comparison_popover if kind=='comparison' else chooser.popover
                            choices=w.comparison_choices if kind=='comparison' else chooser.choices
                            w.open_reading_popup(button);spin(lambda:pop.get_visible(),duration=.3)
                            name=f'{"dark" if dark else "light"}-{width}-{kind}'
                            n.move_at(w,2,2);screen.grab(args.output/(name+'.png'))
                            size=pop.get_child().get_width();records.append((name,w.get_width(),size))
                            if not args.baseline:
                                assert size<=w.get_width(),(name,size,w.get_width())
                                assert size>=480 if width==1200 else size>=240
                                assert choices.rows[choices.get_selected()].get_opacity()==1
                                selected=choices.list.get_selected_row()
                                found,bounds=selected.compute_bounds(choices)
                                assert found and bounds.get_y()>=-1 and bounds.get_y()+bounds.get_height()<=choices.get_height()+1,(name,bounds.get_y(),bounds.get_height(),choices.get_height(),choices.get_vadjustment().get_value())
                            n.key('Escape');spin();assert not pop.get_visible();w.dismiss_popovers();spin()
                    # Native keyboard activation and reselection preserve the close contract.
                    w.set_default_size(1200,820);t.state.comparison=None;w.sync_comparison();spin(duration=.3)
                    chooser=w.primary_version;n.click(chooser);spin(lambda:chooser.popover.get_mapped(),duration=.3)
                    row=chooser.choices.list.get_row_at_index(chooser.names.index('KJV'));row.grab_focus();n.key('Return')
                    spin(lambda:t.state.resource=='KJV' and not chooser.popover.get_visible())
                    n.click(chooser);spin();row=chooser.choices.list.get_selected_row();row.grab_focus();n.key('Down');n.key('Up');n.key('Return');spin()
                    assert not chooser.popover.get_visible() and t.state.resource=='KJV'
                    actions.append('keyboard selection and reselection '+('dark' if dark else 'light'))
                    n.click(chooser);spin(lambda:chooser.popover.get_mapped(),duration=.3)
                    screen.grab(args.output/('download-'+('dark' if dark else 'light')+'-before.png'))
                    n.click(chooser.download_more);spin(duration=.4)
                    screen.grab(args.output/('download-'+('dark' if dark else 'light')+'-after.png'))
                    assert w.catalogue_window and w.catalogue_window.get_visible()
                    assert w.catalogue_window.open_context[1]=='bible'
                    w.catalogue_window.close();spin();n.activate(w);actions.append('Download more opens contextual Library')
                    t.navigate('youversion~YV21','John.3.16');spin(lambda:not t._restoring_scroll)
                settings.props.gtk_font_name='Sans 18';w.set_default_size(360,820);spin(lambda:not w._controls_tick,duration=.4)
                n.click(w.primary_version);spin(duration=.3);n.key('Up');n.key('Down');screen.grab(args.output/'large-text-360.png')
                records.append(('large-text-360',w.get_width(),w.primary_version.popover.get_child().get_width()))
                if not args.baseline:assert w.primary_version.popover.get_child().get_width()<=w.get_width(), (w.primary_version.popover.get_child().get_width(),w.get_width(),w.primary_version.download_more.get_width())
                w.dismiss_popovers();spin()
        finally:settings.props.gtk_font_name=font;w.close();n.close()
    lines=['# Translation picker native verification','',f'- Application: `{inspect.getfile(Window)}`',f'- GTK: {Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}',f'- Renderer: {renderer}',f'- Baseline: {args.baseline}','- Resources: real CrossWire KJV, FreSegond1910; YouVersion BDS (21), LSG (93).','- Environment: Xvfb/X11; developer automation, not client GNOME acceptance.','','| Case | Window width | Popup content width |','| --- | ---: | ---: |']
    lines += [f'| {case} | {window} | {popup} |' for case,window,popup in records]
    lines += ['','Native input:']+['- '+action for action in actions]
    (args.output/'README.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':main()
