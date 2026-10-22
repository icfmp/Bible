import inspect
import json
from pathlib import Path
from bible.ui import Application, Window, Gtk
from bible.library import Library
from tests.test_ui import spin

assert inspect.getfile(Window).startswith('/src/bible/')
app=Application(); app.register()
Gtk.Settings.get_default().set_property('gtk-enable-animations',False)
window=Window(app,Library(Path('/validation/issue57-source-ui-profile/translations')))
window.set_default_size(1200,900); window.present()
results=[]
try:
    for primary,comparison in (('FreSegond1910','ebible~frajnd2024eb'),
                                ('ebible~frajnd2024eb','FreSegond1910'),
                                ('FreLSN1872','FreSegond1910'),
                                ('FreSegond1910','FreLSN1872'),
                                ('ebible~frasbl2022eb','FreSegond1910'),
                                ('GerBoLut','FreSegond1910')):
        tab=window.active_tab
        assert tab.navigate(primary,'John.3.16')
        tab.state.comparison=comparison; window.sync_comparison()
        spin(lambda:not tab._restoring_scroll and not getattr(tab,'_comparison_positioning',False),duration=.3)
        result=dict(primary=primary,comparison=comparison,reference=tab.state.reference,
                    primary_characters=tab.text.get_buffer().get_char_count(),
                    comparison_characters=tab.comparison_text.get_buffer().get_char_count(),
                    status=tab.comparison_status.get_text())
        assert result['primary_characters']>0
        results.append(result)
finally:window.close()
print(json.dumps({'code':'source-candidate','window_import':inspect.getfile(Window),
                  'base_source_commit':'87b9803eebf56fbd3acaa1e3c6b9cfd8f5d60d0b',
                  'network':'unshare --net','checks':results,
                  'status':'Reproduces open #57; not correction acceptance'},ensure_ascii=False,indent=2))
