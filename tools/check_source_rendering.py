"""Real source/rendering evidence on an explicitly disposable research profile."""
import argparse,hashlib,inspect,json,os
from pathlib import Path
from unittest.mock import patch


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--prepare',action='store_true');p.add_argument('--baseline',action='store_true')
    p.add_argument('--require-packaged',action='store_true');p.add_argument('--runtime-probe',action='store_true')
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    from bible.ui import Application,Window,Library,Gtk
    from bible.library import catalogue
    from bible.providers import PROVIDERS
    from bible.sword_provider import Reader,CommentaryReader
    from tests.test_ui import spin
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    marker=args.profile/'.source-rendering-research'
    if args.prepare:
        if args.profile.exists() and any(args.profile.iterdir()) and not marker.exists():raise RuntimeError('Unmarked nonempty profile')
        args.profile.mkdir(parents=True,exist_ok=True);marker.touch()
    assert marker.is_file(),'Use a marked disposable research profile only'
    library=Library(args.profile/'translations')
    names=['MHC','FreAug','FreChry','FreBDM1744','FreJND','ebible~fraLSG1910eb','ebible~frasbl2022eb','FreSegond1910']
    if args.prepare:
        resources=[r for provider in PROVIDERS if provider.id in {'crosswire','ebible'} for r in catalogue(provider)]
        for name in names:
            if name not in library.installed():library.install(next(r for r in resources if r.id==name or r.name==name))
    def hashes():return {str(f.relative_to(library.root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in library.root.rglob('*') if f.is_file()}
    before=hashes();report=dict(app_import=inspect.getfile(Window),baseline=args.baseline,development_source_with_installed_runtime=args.runtime_probe,gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],cases=[],resources=[])
    if args.require_packaged:assert report['app_import'].startswith('/app/')
    for name in names:
        resource=library.resource(name);reader=(CommentaryReader if resource.kind=='commentary' else Reader)(library.root/name,name)
        report['resources'].append(dict(id=name,title=resource.description,system=reader.versification,version=str(reader.module.getConfigEntry('Version')),source_type=str(reader.module.getConfigEntry('SourceType'))))
    app=Application.get_default() or Application();app.register()
    Gtk.Settings.get_default().set_property('gtk-enable-animations',True)
    with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False),patch('bible.catalogue_session.CatalogueSession.load_youversion_language',return_value=None):
        w=Window(app,library);w.present();n=X11Input();n.activate(w);screen=Screen(n)
        try:
            w.appearance.update('size',20);w.appearance.update('line_spacing','normal')
            with SystemStyleOverride() as style:
                for palette,mode in [('white','day'),('dark','night')]:
                    style.set(dark=mode=='night',high=False);w.appearance.update('mode',mode);w.appearance.update('day_palette' if mode=='day' else 'night_palette',palette)
                    for name,reference,comment in [('ebible~fraLSG1910eb','Ps.13.1',None),('ebible~frasbl2022eb','Ps.13.1',None),('ebible~fraLSG1910eb','Gen.2.1',None),('FreJND','Gen.2.1',None),('FreBDM1744','Gen.1.1',None),('FreSegond1910','Gen.1.1','MHC'),('FreSegond1910','Gen.2.4','MHC'),('FreSegond1910','Ps.13.1','FreAug'),('FreSegond1910','Ps.13.1','FreChry')]:
                        for width in ([1200,620] if comment or reference=='Ps.13.1' else [1200]):
                            t=w.active_tab;t.state.commentary_positions={};t.state.comparison=None;w.sync_comparison()
                            w.set_default_size(width,820);t.navigate(name,reference);spin(lambda:not t._restoring_scroll,duration=.3,timeout=30)
                            w.study_button.set_active(bool(comment))
                            if comment:
                                s=w.study;s.tools.set_visible_child_name('commentaries');s.refresh(force=True);s.choices.set_selected(s.names.index(comment));spin(lambda:not s._loading and not s._positioning and not s._adapt_tick,duration=.4,timeout=30)
                            spin(duration=.3);case=f'{name}-{reference}-{comment or "reader"}-{palette}-{width}'
                            row=dict(case=case,reference=t.state.reference,width=w.get_width(),source_sha256=None)
                            if comment:
                                position=s.current_position;assert position is not None,(case,s.status.get_text())
                                raw=s.reader.index.raw(position);row['source_sha256']=hashlib.sha256(raw.encode()).hexdigest()
                                if hasattr(s,'_source_focus'):
                                    focus=s.text.get_iter_location(s.text.get_buffer().get_iter_at_offset(s._source_focus[position]));row['focus_delta_pixels']=focus.y-s.text.get_visible_rect().y
                            n.move_at(w,2,2);screen.grab(args.output/(case+'.png'));report['cases'].append(row)
        finally:w.close()
    report['module_files_preserved']=before==hashes();assert report['module_files_preserved']
    bad=[r for r in report['cases'] if abs(r.get('focus_delta_pixels',0))>32]
    report['unexpected_context_positions']=[r['case'] for r in bad]
    (args.output/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if not args.baseline:assert not bad,report['unexpected_context_positions']


if __name__=='__main__':main()
