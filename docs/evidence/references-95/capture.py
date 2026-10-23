import os,json
from pathlib import Path
from bible.ui import Application,Window,Library,Gtk
from tests.test_ui import spin
from tools.check_alpha_ui import X11Input
from PIL import ImageGrab
phase=os.environ.get('CAPTURE_PHASE','after');root=Path('/work/references-95')
profile=root/('profile-'+phase);profile.mkdir(exist_ok=True)
for name,target in [('translations','/work/visual-polish/profile/translations'),('study-data','/work/references-95/data')]:
    if not (profile/name).exists():(profile/name).symlink_to(target)
app=Application();app.register();w=Window(app,Library(profile/'translations'));w.set_default_size(1440,1000);w.present();spin()
native=X11Input();native.move_at(w,2,2);Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
refs=w.study.references;out=root/'captures';out.mkdir(exist_ok=True);report=[]
def ready():spin(lambda:not refs.pending,duration=.35)
def capture(name):
    native.move_at(w,2,2);spin(duration=.3);ImageGrab.grab().save(out/(phase+'-'+name+'.png'))
    report.append(dict(file=phase+'-'+name+'.png',scale=w.get_scale_factor(),window=[w.get_width(),w.get_height()],panel_width=w.study.get_width(),source=refs.context[2:],total=len(refs.rows),shown=refs.model.get_n_items()))
try:
    for theme,mode in [('light','day'),('dark','night')]:
        w.appearance.update('mode',mode)
        for resource,reference,scenario in [('FreSegond1910','Acts.1.22','acts'),('KJV','Gen.1.1','genesis'),('FreSegond1910','John.1.5','john')]:
            w.active_tab.navigate(resource,reference);w.study_button.set_active(True);w.study.tools.set_visible_child_name('references');ready()
            for width,label in [(360,'narrow'),(430,'default'),(560,'wide')]:
                w.study_settings.width=width;w.study_divider.apply();ready();capture(f'{theme}-{scenario}-{label}')
            w.study_settings.width=430;w.study_divider.apply();settings=Gtk.Settings.get_default();dpi=settings.get_property('gtk-xft-dpi');settings.set_property('gtk-xft-dpi',147456);ready();capture(f'{theme}-{scenario}-large-text');settings.set_property('gtk-xft-dpi',dpi)
            refs.show_all();ready();capture(f'{theme}-{scenario}-expanded')
            if hasattr(refs,'show_initial'):refs.show_initial()
            else:refs.all_results=False;refs.populate()
        w.set_default_size(360,700);spin(lambda:w.split.get_collapsed());w.split.set_show_sidebar(True);ready();capture(f'{theme}-small-window')
        settings.set_property('gtk-xft-dpi',147456);ready();capture(f'{theme}-small-large-text');settings.set_property('gtk-xft-dpi',dpi)
        w.set_default_size(1440,1000);spin(lambda:not w.split.get_collapsed());w.split.set_show_sidebar(True);ready()
    from tests.test_appearance import SystemStyleOverride
    with SystemStyleOverride() as override:
        override.set(dark=False,high=True);w.appearance.update('mode','day');ready();capture('high-contrast')
    (root/(phase+'-capture-metrics.json')).write_text(json.dumps(report,indent=2)+'\n');print('PASS actual GTK '+phase+' reference captures',flush=True)
finally:w.close();native.close()
