import os,json
from pathlib import Path
from bible.ui import Application,Window,Library,Gtk
from tests.test_ui import spin
from PIL import ImageGrab
from tools.check_alpha_ui import X11Input
phase=os.environ.get('CAPTURE_PHASE','after');root=Path('/work/passage-notes-90')
profile=root/('profile-'+phase);profile.mkdir(exist_ok=True)
if not (profile/'translations').exists():(profile/'translations').symlink_to('/work/visual-polish/profile/translations')
native=X11Input()
app=Application();app.register();w=Window(app,Library(profile/'translations'));w.set_default_size(1440,1000);w.present();spin();native.move_at(w,2,2)
try:
    assert w.active_tab.navigate('FreSegond1910','Acts.1.22');w.study_button.set_active(True);w.study.tools.set_visible_child_name('notes')
    if not w.notes_store.all():
        context=dict(versification='Segond',start='Acts.1.22',end='Acts.1.22',origin_translation='FreSegond1910',origin_language='fr')
        w.notes_store.save('Note de validation : le témoignage de la résurrection est central.',('Observation',),**context)
        w.notes_store.save('**Observation personnelle — validation**\n\nLire Jean 3:16 avant de revenir au rôle du témoin.\n\n*Questions de lecture*\n- Quel passage est visé ?\n- Qui prend la parole ?\n\n'+('Cette note de test longue permet de vérifier la lecture intégrale, la mise en forme et la conservation du brouillon.\n\n'*10),('À étudier',),**context)
        context.update(start='Acts.1.21')
        w.notes_store.save('Note de validation sur deux versets : relire le contexte de la sélection.',(),**context)
        w.highlights.set('Segond',['Acts.1.22'],'green','FreSegond1910')
    out=root/'captures';out.mkdir(exist_ok=True);report=[]
    for theme,mode in [('light','day'),('dark','night')]:
        w.appearance.update('mode',mode)
        for width,label in [(360,'narrow'),(430,'default'),(560,'wide')]:
            w.study_settings.width=width;w.study_divider.apply();w.study.notes.refresh(force=True);spin(duration=.4)
            path=out/f'{phase}-{theme}-{label}.png';ImageGrab.grab().save(path);report.append(dict(file=path.name,scale=w.get_scale_factor(),panel_width=w.study.get_width()))
        w.study_settings.width=430;w.study_divider.apply()
        settings=Gtk.Settings.get_default();dpi=settings.get_property('gtk-xft-dpi');settings.set_property('gtk-xft-dpi',147456);spin(duration=.4)
        ImageGrab.grab().save(out/f'{phase}-{theme}-large-text.png');settings.set_property('gtk-xft-dpi',dpi)
        w.set_default_size(360,700);spin(lambda:w.split.get_collapsed());w.split.set_show_sidebar(True);spin(duration=.3)
        ImageGrab.grab().save(out/f'{phase}-{theme}-small-window.png')
        settings.set_property('gtk-xft-dpi',147456);spin(duration=.3)
        ImageGrab.grab().save(out/f'{phase}-{theme}-small-large-text.png');settings.set_property('gtk-xft-dpi',dpi)
        w.set_default_size(1440,1000);spin(lambda:not w.split.get_collapsed());spin(duration=.3)
        if hasattr(w.study.notes,'cards'):
            notes=w.study.notes;long=next(n for n in notes.rows if len(n.body)>500)
            editor=notes.open_note(long);spin(duration=.3);ImageGrab.grab().save(out/f'{phase}-{theme}-inline-editor.png')
            w.set_default_size(360,700);spin(lambda:w.split.get_collapsed());w.split.set_show_sidebar(True);settings.set_property('gtk-xft-dpi',147456);spin(duration=.3)
            ImageGrab.grab().save(out/f'{phase}-{theme}-inline-small-large-text.png')
            settings.set_property('gtk-xft-dpi',dpi);w.set_default_size(1440,1000);spin(lambda:not w.split.get_collapsed())
            editor._discard=True;editor.close()
    from tests.test_appearance import SystemStyleOverride
    with SystemStyleOverride() as override:
        for theme,mode in [('light','day'),('dark','night')]:
            w.appearance.update('mode',mode);override.set(dark=theme=='dark',high=True);spin(duration=.4)
            assert w.reading_style.manager.get_high_contrast()
            if hasattr(w.study.notes,'cards'):assert w.study.notes.has_css_class('annotation-contrast')
            ImageGrab.grab().save(out/f'{phase}-{theme}-high-contrast.png')
    (root/(phase+'-capture-metrics.json')).write_text(json.dumps(report,indent=2))
    print('PASS actual GTK '+phase+' annotation captures',flush=True)
finally:w.close();native.close()
