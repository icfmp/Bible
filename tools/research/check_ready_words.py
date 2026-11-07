"""Real native original-word walkthrough; use only disposable validation profiles."""
import argparse,inspect,json
from pathlib import Path
from gi.repository import Gtk,Graphene
from bible.ui import Application,Window,Library
from bible.i18n import tr
from tests.test_ui import spin
from tests.test_appearance import SystemStyleOverride
from tools.check_alpha_ui import X11Input
from tools.check_client_feedback import Screen
p=argparse.ArgumentParser();p.add_argument('profile',type=Path);p.add_argument('output',type=Path);p.add_argument('--resource',default='FreSegond1910');p.add_argument('--require-packaged',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
root=a.profile
assert (root/'.ready-batch-test-profile').is_file() or root.name=='study-navigation-real','Disposable test profile required'
if a.require_packaged:assert inspect.getfile(Window).startswith('/app/')
app=Application();app.register();w=Window(app,Library(root/'translations'));w.set_default_size(1280,900);w.present();spin();n=X11Input();screen=Screen(n);notes=w.notes_store.all()
report=dict(source=inspect.getfile(Window),cases=[],complete=False)
from gi.repository import Gdk
theme=Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
report['icons']={name:theme.has_icon(name) for name in ('dictionary-symbolic','notebook-symbolic','filter-symbolic','talking-symbolic','mark-location-symbolic')}
assert all(report['icons'].values()),report['icons']
if a.require_packaged:
 import subprocess
 report['fonts']={}
 for family in ('Roboto','Roboto Serif'):
  path=subprocess.check_output(['fc-match','-f','%{file}',family],text=True)
  assert path.startswith('/app/share/fonts/roboto/'),(family,path)
  report['fonts'][family]=path
def shot(name):n.move_at(w,2,2);spin(duration=.25);screen.grab(a.output/(name+'.png'))
def walk(widget):
 yield widget;c=widget.get_first_child()
 while c:yield from walk(c);c=c.get_next_sibling()
try:
 with SystemStyleOverride() as style:
  for dark in (False,True):
   style.set(dark=dark,high=False);w.appearance.update('mode','night' if dark else 'day');prefix='night' if dark else 'day'
   for ref,language in [('Mark.7.4','grc'),('Gen.1.1','hbo')]:
    t=w.active_tab;t.navigate(a.resource,ref);spin(lambda:not t._restoring_scroll)
    history=list(t.state.history);b=t.text.get_buffer();first=t._marker_ends[ref];last=t._verse_ranges[ref][1];b.select_range(b.get_iter_at_offset(first),b.get_iter_at_offset(last))
    actions=w.passage_actions;actions.capture(t.text,lambda:actions.ordinary(t),None);spin()
    n.activate(w);actions.word_button.grab_focus();n.key('Return')
    words=w.study.words;spin(lambda:words.dialog is not None and not words.pending,timeout=40);n.activate(words.dialog)
    tokens=[x for x in words.children() if hasattr(x,'_source_token')];assert tokens
    if language=='grc':token=next(x for x in tokens if 'G2532' in x._source_token.get('tags',[]))
    else:token=next(x for x in tokens if len(x._source_token.get('lexical',[]))==1 and words.data.lookup(x._source_token['lexical'][0][0]))
    if language=='hbo':assert token.get_parent().get_parent().get_direction()==Gtk.TextDirection.RTL
    shot(prefix+'-'+language+'-passage')
    expected=token._source_token['form'];token.grab_focus();n.key('Return');spin(lambda:not words.pending,timeout=40)
    assert words.stage=='word' and words.token['form']==expected
    labels=[x for x in words.children() if isinstance(x,Gtk.Label)];assert any(x.get_text()==expected for x in labels)
    assert any(x.get_text()==tr('Common meanings') for x in labels)
    if language=='grc':assert words.entry['id']=='G2532' and words.entry['gloss']=='and'
    if language=='hbo':assert next(x for x in labels if x.get_text()==expected).get_direction()==Gtk.TextDirection.RTL
    assert all(not x.get_expanded() for x in words.children() if isinstance(x,Gtk.Expander));shot(prefix+'-'+language+'-word')
    more=next(x for x in words.children() if isinstance(x,Gtk.Button) and isinstance(x.get_child(),Gtk.Label) and x.get_child().get_text()==tr('See other occurrences'))
    more.grab_focus();n.key('Return');spin(lambda:not words.pending,timeout=40)
    assert words.stage=='occurrences';cards=[x for x in words.children() if hasattr(x,'_word_reference')];assert cards
    shot(prefix+'-'+language+'-occurrences');cards[0].grab_focus();n.key('Return');spin()
    assert w.reference_preview.popover and w.reference_preview.popover.get_visible();w.reference_preview.dismiss();spin()
    words.go_back.grab_focus();n.key('Return');assert words.stage=='word'
    words.go_back.grab_focus();n.key('Return');spin(lambda:not words.pending);assert words.stage=='passage'
    assert t.state.reference==ref and t.state.history==history
    words.leave();spin();report['cases'].append(dict(reference=ref,language=language,native_keyboard_flow=True,preview=True,back_chain=True,reading_position_preserved=True))
   t.navigate(a.resource,'Jer.1.1');spin(lambda:not t._restoring_scroll)
   from bible.editorial_view import show_introduction,introduction_text
   if t.reader.introduction('Jer') is None:
    report['jeremiah_introduction']='Not supplied by this edition; BDS real-source coverage recorded separately'
    continue
   intro=show_introduction(w,t.reader,'Jer');spin();text=intro.text.get_buffer().props.text
   assert text==introduction_text(intro.source_document);assert intro.text.get_editable() is False
   shot(prefix+'-jeremiah-introduction-wide')
   intro.set_default_size(340,560);spin();adj=next(x for x in walk(intro) if isinstance(x,Gtk.ScrolledWindow)).get_vadjustment();adj.set_value(adj.get_upper()-adj.get_page_size());spin();shot(prefix+'-jeremiah-introduction-narrow-end')
   rect=intro.text.get_visible_rect();last=intro.text.get_iter_location(intro.text.get_buffer().get_end_iter());assert last.y+last.height<=rect.y+rect.height+2,(last,rect)
   intro.text.get_buffer().select_range(*intro.text.get_buffer().get_bounds());assert intro.text.get_buffer().get_selection_bounds();intro.close();spin()
 assert w.notes_store.all()==notes
 report['notes_unchanged']=True;report['complete']=True
finally:
 w.close();n.close();(a.output/'result.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
