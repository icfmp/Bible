"""Real short/long result geometry, native Aa and preference-palette checks."""
import argparse,json,inspect
from pathlib import Path
from bible.ui import Application,Window,Library,Gtk
from bible.topic_vocabulary import suggestions
from tests.test_ui import spin
from tests.test_appearance import SystemStyleOverride
from tools.check_alpha_ui import X11Input
from tools.check_client_feedback import Screen
p=argparse.ArgumentParser();p.add_argument('profile',type=Path);p.add_argument('output',type=Path);p.add_argument('--require-packaged',action='store_true');a=p.parse_args()
if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
assert (a.profile/'.ready-batch-test-profile').is_file();a.output.mkdir(parents=True,exist_ok=True)
app=Application();app.register();w=Window(app,Library(a.profile/'translations'));w.present();n=X11Input();n.activate(w);screen=Screen(n)
report=dict(complete=False,source=inspect.getfile(Window),cases=[],palettes=[])
def walk(widget):
 yield widget;c=widget.get_first_child()
 while c:yield from walk(c);c=c.get_next_sibling()
def shot(name):n.move_at(w,2,2);spin(duration=.2);screen.grab(a.output/(name+'.png'))
def scroll_state(widget):
 adj=widget.get_vadjustment();return dict(height=widget.get_height(),upper=adj.get_upper(),page=adj.get_page_size())
def geometry(panel,mode,query):
 pop=w.search_popover;spin(duration=.35)
 row=dict(mode=mode,query=query,popover=[pop.get_width(),pop.get_height()],content=[pop.content.get_width(),pop.content.get_height()],outer=scroll_state(pop.scroll),inner=scroll_state(panel.topic_scroll if mode=='topics' else panel.result_scroll),count=panel.topic_model.get_n_items() if mode=='topics' else panel.model.get_n_items(),total=panel.total)
 report['cases'].append(row);print(row,flush=True);return row
try:
 t=w.active_tab;t.navigate('youversion~YV104','John.14.6');spin(lambda:not t._restoring_scroll);w.study_button.set_active(False)
 with SystemStyleOverride() as style:
  for small,font in ((False,'Cantarell 11'),(True,'Cantarell 16')):
   Gtk.Settings.get_default().set_property('gtk-font-name',font)
   w.set_default_size(560 if small else 1280,750 if small else 900);spin()
   for mode in ('day','night'):
    style.set(dark=mode=='night',high=False);w.appearance.update('mode',mode)
    prefix=mode+('-small-largefont' if small else '-wide')
    for label,query in [('zero','zzready13nomatchingpassage'),('two','je suis le chemin'),('many','Dieu')]:
     w.show_search('text');spin();panel=w.search_popover.text_search
     panel.entry.set_text(query);panel.entry.grab_focus();n.key('Return');spin(lambda:not panel.pending and panel.result_query==query,timeout=100)
     result=geometry(panel,'text',query)
     if label=='two':
      assert result['total']==2,result
      assert result['inner']['upper']<=result['inner']['page']+2,result
     if label=='zero':assert result['total']==0,result
     if label=='many':assert result['total']>100,result
     if not small:assert result['outer']['upper']<=result['outer']['page']+2,result
     shot(prefix+'-text-'+label);w.search_popover.popdown();spin()
    w.show_search('topics');spin();panel=w.search_popover.topic_search
    for label,query in [('zero','zzready13nomatchingtheme'),('two','Forgiveness o'),('many','')]:
     panel.entry.set_text(query);spin(duration=.55)
     result=geometry(panel,'topics',query)
     if label=='two':
      assert result['count']==2,result
      assert panel.topic_pages.get_visible_child_name()=='topics' and panel.topic_scroll.get_mapped()
      assert len([b for b in walk(panel.topics) if isinstance(b,Gtk.Button) and getattr(b,'_topic',None)])==2
      assert result['inner']['upper']<=result['inner']['page']+2,result
     if label=='zero':assert result['count']==0,result
     if label=='many':assert result['count']>10,result
     shot(prefix+'-themes-'+label)
    w.search_popover.popdown();spin()
    w.appearance_button.popup();spin();pop=w.appearance
    pop.visible_elements.set_expanded(False);spin();collapsed=pop.get_width()
    widths=[b.get_width() for b in pop.mode.buttons];assert max(widths)-min(widths)<=1,widths
    shot(prefix+'-aa-collapsed')
    pop.visible_elements.grab_focus();n.key('Return');spin();assert pop.visible_elements.get_expanded()
    expanded=pop.get_width();assert abs(collapsed-expanded)<=1,(collapsed,expanded)
    shot(prefix+'-aa-expanded');w.appearance_button.popdown();spin()
    from bible.application_surfaces import show_preferences
    dialog=show_preferences(w);dialog.set_visible_page(dialog.reading_settings.page);spin()
    grid=dialog.reading_settings.palette_grid
    for scroll in [x for x in walk(dialog) if isinstance(x,Gtk.ScrolledWindow) and grid.is_ancestor(x)]:
     adj=scroll.get_vadjustment();adj.set_value(adj.get_upper()-adj.get_page_size())
    spin(duration=.3)
    sizes={key:[b.get_width(),b.get_height()] for key,b in dialog.reading_settings.palettes.items()}
    assert max(v[1] for v in sizes.values())-min(v[1] for v in sizes.values())<=1,sizes
    print('PALETTES',prefix,sizes,flush=True);report['palettes'].append(dict(mode=prefix,sizes=sizes))
    shot(prefix+'-preferences-colors');dialog.close();spin();w.preferences_window=None
 report['complete']=True
finally:
 (a.output/'result.json').write_text(json.dumps(report,indent=2)+'\n');w.close();n.close()
