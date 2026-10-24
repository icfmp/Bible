import json,hashlib,os
from pathlib import Path
from bible.ui import Application,Window,Library
from tests.test_ui import spin
profile=Path('/work/library-63-71-108/preservation-profile');app=Application();app.register();w=Window(app,Library(profile/'translations'));w.present()
try:
    if os.environ['PRESERVATION_PHASE']=='after':assert w.main_pages.get_visible_child_name()!='welcome'
    if os.environ['PRESERVATION_PHASE']=='before':
        w.active_tab.navigate('FreSegond1910','John.3.16');w.active_tab.state.comparison='ebible~frajnd2024eb';w.sync_comparison()
        w.preferences.value.font='DejaVu Sans';w.preferences.value.size=19;w.preferences.value.mode='system';w.preferences.value.day_palette='paper';w.preferences.value.night_palette='black';w.preferences.value.line_spacing='airy';w.preferences.value.column_width='wide';w.preferences.save();w.apply_appearance()
        note=w.notes_store.save('Actual persistent Markdown **note**, test data only.',['Preservation'],versification='Segond',start='John.3.16',end='John.3.17',origin_translation='FreSegond1910',origin_language='fr')
        w.highlights.set('Segond',['John.3.16'],'green','FreSegond1910')
        (profile/'note-id').write_text(note.id)
    spin(lambda:not w.active_tab._restoring_scroll and not getattr(w.active_tab,'_comparison_positioning',False),duration=.3)
    note=w.notes_store.get((profile/'note-id').read_text())
    state=dict(note=vars(note),preferences=vars(w.preferences.value),highlights=sorted(w.highlights.entries.values(),key=lambda x:repr(x)),resource=w.active_tab.state.resource,reference=w.active_tab.state.reference,comparison=w.active_tab.state.comparison,resources={str(path.relative_to(profile/'translations')):hashlib.sha256(path.read_bytes()).hexdigest() for path in (profile/'translations').rglob('*') if path.is_file()})
    state=json.loads(json.dumps(state))
    if os.environ['PRESERVATION_PHASE']=='before':(profile/'expected.json').write_text(json.dumps(state,sort_keys=True))
    else:
        expected=json.loads((profile/'expected.json').read_text());assert state==expected,[(k,state[k],expected[k]) for k in state if state[k]!=expected[k]]
        Path('/work/library-63-71-108/profile-preservation.json').write_text(json.dumps(dict(status='PASS',actual_sqlite_note=True,labels=True,actual_highlight=True,explicit_reading_preferences=True,primary_and_comparison_session=True,resource_file_digests=len(state['resources']),before_source='f69de06e730445da634b5a3866084c3fce97171d',after_source='validated feature working tree; final CI records exact commit'),indent=2))
        print('PASS actual pre-existing SQLite note/labels, highlight, explicit preferences, primary/comparison session and all installed resource file digests preserved',flush=True)
finally:w.close()
