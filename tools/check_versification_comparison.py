"""Real-resource GTK comparison matrix; disposable TEST profile only.

Run once with --install-darby, then again with the network disabled. Packaged
runs must set --require-packaged and import the app from /app before this tool.
No full resource text is written to the report.
"""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import re

from tests.test_ui import spin

NAMES = ['FreSegond1910', 'KJV', 'FreLSN1872', 'ebible~frajnd2024eb',
         'ebible~fraLSG1910eb', 'ebible~frasbl2022eb', 'GerBoLut']


def direct(reader, reference):
    import Sword
    from bible.providers import module_name
    manager = Sword.SWMgr(str(reader.root))
    module = manager.getModule(module_name(reader.name))
    key = Sword.VerseKey(); key.setVersificationSystem(reader.versification)
    key.setAutoNormalize(False); key.setText(reference)
    assert key.popError() == '\x00'
    module.setKey(key); value = module.stripText()
    return value if isinstance(value, str) else value.c_str()


def fidelity(reader, document):
    digest = hashlib.sha256(); exact = 0
    for span in document.spans:
        source = direct(reader, span.reference)
        copied = document.copy(span.body, span.end)
        # Structured paragraph separators differ from SWORD's plain filter;
        # every source word/punctuation must survive, in order.
        assert re.sub(r'\s+', ' ', copied).strip() == re.sub(r'\s+', ' ', source).strip(), (reader.name, span.reference)
        exact += copied == source
        digest.update(span.reference.encode()+b'\0'+source.encode()+b'\0')
    return dict(verses=len(document.spans), byte_identical=exact, direct_sword_sha256=digest.hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', type=Path); parser.add_argument('output', type=Path)
    parser.add_argument('--require-packaged', action='store_true')
    parser.add_argument('--install-darby', action='store_true')
    parser.add_argument('--screenshot', type=Path)
    args = parser.parse_args()
    from bible.ui import Application, Window, Gtk
    from bible.library import Library, catalogue
    from bible.providers import EBIBLE
    from tools.check_alpha_ui import X11Input
    from tools.check_resource_installation import wait
    import bible
    if args.require_packaged: assert bible.__file__.startswith('/app/'), bible.__file__
    library = Library(args.profile/'translations')
    app = Application(); app.register(); native = X11Input()
    Gtk.Settings.get_default().set_property('gtk-enable-animations', False)
    window = Window(app, library); window.set_default_size(1440, 1000); window.present()
    report = dict(app_import=inspect.getfile(Window), resources={}, matrix=[], boundaries=[], input=[],
                  accessibility='Deferred; not tested', fresh_install=False)
    def settled():
        spin(lambda: not tab._restoring_scroll and not getattr(tab, '_comparison_positioning', False), duration=.15)
        assert not tab._restoring_scroll and not getattr(tab, '_comparison_positioning', False)
    def open_pair(primary, comparison, reference):
        assert tab.navigate(primary, reference), (primary, reference, tab.status.get_text())
        tab.state.comparison = comparison; window.sync_comparison(); settled()
        assert not tab.comparison_status.get_text(), (primary, comparison, reference, tab.comparison_status.get_text())
        assert abs(tab.reading_overlay.get_width()-tab.comparison_box.get_width()) <= 1
        print('CHECK', primary, comparison, reference, flush=True)
        return dict(primary=primary, comparison=comparison, reference=reference,
                    primary_fidelity=fidelity(tab.reader, tab._document),
                    comparison_fidelity=fidelity(tab._comparison_reader, tab._comparison_document))
    tab = window.active_tab
    try:
        window.appearance.reset(); window.study_button.set_active(False)
        if args.install_darby:
            assert 'ebible~frajnd2024eb' not in library.installed()
            resource = next(r for r in catalogue(EBIBLE) if r.id == 'ebible~frajnd2024eb')
            dialog = window.open_library(); dialog._catalogue_requested = True
            dialog.resources = [resource]; dialog.update_languages(); dialog.open_details(None, 0)
            dialog.install(); wait(lambda: not dialog.busy)
            assert resource.id in library.installed(), dialog.status.get_text()
            assert dialog.installed_state.get_visible() and not dialog.download_button.get_visible()
            dialog.close()
            report['immediate_install_comparison'] = open_pair(resource.id, 'FreSegond1910', 'John.3.16')
            report['fresh_install'] = True
        from bible.sword_provider import Reader
        for name in NAMES:
            reader = Reader(library.root/name, name)
            report['resources'][name] = dict(system=reader.versification, driver=reader.module.getConfigEntry('ModDrv'),
                                             version=reader.module.getConfigEntry('Version'))
        for primary in NAMES:
            for comparison in NAMES:
                report['matrix'].append(open_pair(primary, comparison, 'John.3.16'))
        # Independent expected references: original pinned tables/native data,
        # including a part which cannot be resolved more narrowly than a range.
        boundaries = [
            ('ebible~frajnd2024eb', 'KJV', 'Gen.32.1', 'Gen.31.55', 'Gen.31.55'),
            ('KJV', 'ebible~frajnd2024eb', 'Gen.31.55', 'Gen.32.1', 'Gen.32.1'),
            ('ebible~frajnd2024eb', 'KJV', 'Ps.3.2', 'Ps.3.1', 'Ps.3.1'),
            ('KJV', 'ebible~frajnd2024eb', 'Ps.3.1', 'Ps.3.2', 'Ps.3.2'),
            ('FreSegond1910', 'ebible~frajnd2024eb', 'Ps.3.2', 'Ps.3.2', 'Ps.3.2'),
            ('ebible~frajnd2024eb', 'FreSegond1910', 'Ps.3.2', 'Ps.3.2', 'Ps.3.2'),
            ('ebible~frajnd2024eb', 'KJV', 'Acts.19.40', 'Acts.19.40', 'Acts.19.41'),
            ('KJV', 'ebible~frajnd2024eb', 'Acts.19.41', 'Acts.19.40', 'Acts.19.40'),
            ('GerBoLut', 'ebible~frajnd2024eb', 'Acts.19.40', 'Acts.19.40', 'Acts.19.40'),
            ('FreSegond1910', 'ebible~frajnd2024eb', 'Ps.51.3', 'Ps.51.2', 'Ps.51.3'),
            ('ebible~frasbl2022eb', 'KJV', '3John.1.14', '3John.1.14', '3John.1.14'),
        ]
        for primary, comparison, ref, start, end in boundaries:
            row = open_pair(primary, comparison, ref)
            expected = start+('–'+end if end != start else '')
            assert tab.comparison_heading.get_text().endswith(expected), (row, tab.comparison_heading.get_text())
            row['expected_target'] = expected; report['boundaries'].append(row)
        # Ordinary John 3 has identical verified numbering in these systems.
        for primary, comparison in [('FreSegond1910','ebible~frajnd2024eb'),
                                    ('ebible~frajnd2024eb','KJV'),('FreLSN1872','ebible~frajnd2024eb'),
                                    ('ebible~frasbl2022eb','FreSegond1910'),('GerBoLut','KJV')]:
            open_pair(primary, comparison, 'John.3.1')
            history = list(tab.state.history)
            for side in ('primary', 'comparison', 'primary', 'comparison'):
                view = tab.text if side == 'primary' else tab.comparison_text
                native.wheel(view, 3)
                spin(lambda: not tab.comparison_sync.pending and not getattr(tab,'_comparison_positioning',False), duration=.25)
                if side == 'primary':
                    assert tab.comparison_visible_reference() == tab.visible_reference(), (primary, comparison, side, tab.visible_reference(), tab.comparison_visible_reference())
                else:
                    assert tab.state.reference == tab.comparison_visible_reference(), (primary, comparison, side, tab.state.reference, tab.comparison_visible_reference())
                assert not tab.comparison_status.get_text()
            assert tab.state.history == history
            buffer = tab.comparison_text.get_buffer(); span = tab._comparison_document.spans[2]
            buffer.select_range(buffer.get_iter_at_offset(span.body+2), buffer.get_iter_at_offset(min(span.end,span.body+19)))
            selected = tab._comparison_document.copy(*(i.get_offset() for i in buffer.get_selection_bounds()))
            assert selected and selected in direct(tab._comparison_reader, span.reference)
            tab.comparison_text.emit('copy-clipboard'); clipboard = []
            tab.comparison_text.get_clipboard().read_text_async(None, lambda clip,res:clipboard.append(clip.read_text_finish(res)))
            spin(lambda:bool(clipboard)); assert clipboard == [selected]
            reference = tab.state.reference
            window.appearance.update('size', 18); settled()
            copied = tab._comparison_document.copy(*(i.get_offset() for i in buffer.get_selection_bounds()))
            assert copied == selected and tab.state.reference == reference
            window.appearance.update('size', 14); settled(); buffer.place_cursor(buffer.get_start_iter())
            report['input'].append(dict(primary=primary,comparison=comparison,bidirectional_native_wheel=True,
                                        exact_partial_clipboard=True,selection_reflow=True,history_unchanged=True))
        # A real heading verse has no normal target verse; keep independently
        # readable target text, clearly labelled, and resume on a supported verse.
        assert tab.navigate('ebible~frajnd2024eb','Ps.3.1')
        tab.state.comparison='KJV';window.sync_comparison();settled()
        assert tab.comparison_status.get_text() and 'Independent reading' in tab.comparison_heading.get_text()
        assert tab.comparison_text.get_buffer().get_char_count()>0
        limitation=tab.comparison_status.get_text()
        heading=tab.comparison_heading.get_text()
        tab.comparison_sync.intent('comparison');tab.comparison_sync.synchronize()
        # It may recover at its explicitly displayed independent reference only
        # if a subsequent real user gesture has a verified mapping.
        report['unsupported_heading']=dict(status_before_deliberate_input=limitation,heading=heading,readable=True,
                                           status_after_verified_input=tab.comparison_status.get_text())
        open_pair('ebible~frajnd2024eb','KJV','Ps.3.2')
        # New tab and return must rebuild source-qualified comparison state.
        old=tab; window.new_tab()
        tab=window.active_tab;open_pair('GerBoLut','ebible~frajnd2024eb','Gen.1.1')
        window.view.set_selected_page(window.view.get_page(old));tab=window.active_tab;settled()
        assert tab is old and tab.state.comparison=='KJV'
        open_pair('FreSegond1910','ebible~frajnd2024eb','Ps.3.2')
        if args.screenshot:
            from PIL import ImageGrab
            spin(duration=.2);ImageGrab.grab().save(args.screenshot)
        report['status']='PASS'; report['tab_switch']=True
    finally:
        window.close();native.close()
        report.setdefault('status','INCOMPLETE')
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('matrix','boundaries','resources')},ensure_ascii=False))


if __name__=='__main__':main()
