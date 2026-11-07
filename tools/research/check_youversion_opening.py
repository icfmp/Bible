"""Real #138 Library/selector opening, owned reference navigation and offline restore.

Uses a marked disposable profile, never a client's profile. Outputs counts and
hashes only; source archives and modules stay in the private working directory.
"""
import argparse
from functools import partial
import hashlib
import inspect
import json
from pathlib import Path
from unittest.mock import patch


def snapshot(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path);parser.add_argument('report',type=Path)
    parser.add_argument('--compiler',default='/app/bin/osis2mod')
    parser.add_argument('--require-packaged',action='store_true');args=parser.parse_args()
    from bible.library import Library
    from bible.youversion_install import fetch_resource,acknowledgement,run_conversion
    from bible.ui import Application,Window
    from bible.sword_provider import Reader
    from bible.reference_resolution import resolve,VersificationMismatch
    from bible.notes import NoteStore
    from bible.preferences import Preferences
    from bible.youversion_content import normalized
    from tests.test_ui import spin,close_test_dialogs
    if args.require_packaged:
        assert inspect.getfile(Window).startswith('/app/')
        assert args.compiler=='/app/bin/osis2mod'
    marker=args.profile/'.youversion-opening-proof'
    if args.profile.exists() and not marker.is_file():raise ValueError('Non-test profile refused')
    args.profile.mkdir(parents=True,exist_ok=True,mode=0o700);marker.write_text('Disposable issue 138 proof only\n')
    library=Library(args.profile/'translations')
    for identifier in (21,93):
        item=fetch_resource(identifier)
        if item.id not in library.installed():
            with patch('bible.youversion_install.run_conversion',partial(run_conversion,compiler=args.compiler)):
                library.install(item,permission=acknowledgement(item))
    source='youversion~YV21';target='youversion~YV93'
    notes=NoteStore(args.profile/'notes.sqlite3')
    if not notes.all():notes.save('PRESERVED SYNTHETIC OPENING NOTE',('preserve',),versification='Original',
        start='Gen.19.1',end='Gen.19.1',origin_translation=source,origin_language='fra')
    preferences=Preferences(args.profile/'reading-preferences.json')
    if not preferences.path.exists():preferences.save()
    original_notes=notes.all();original_preferences=preferences.path.read_bytes();files=snapshot(library.root)
    expected=Reader(library.root/target,target)
    assert resolve('Gen.11.3','Original',expected).start=='Gen.11.3'
    try:resolve('Gen.12.1','Original',expected)
    except VersificationMismatch:pass
    else:raise AssertionError('An unaudited verse unexpectedly gained a verified mapping')
    app=Application.get_default() or Application();app.register()
    window=Window(app,library);window.present();spin();opened=[]
    try:
        tab=window.active_tab;assert tab.navigate(source,'Gen.11.3');spin()
        with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):
            dialog=window.open_library();spin(lambda:not dialog.preparing)
        dialog.read_resource(library.resource(target));spin()
        assert dialog.closed and tab.state.resource==target
        assert tab.state.reference=='Gen.11.3' and not tab.status.get_visible()
        assert 'No verified alignment' not in tab.status.get_text()
        opened.append('Library Read')
        edge=expected.key('Mark.10.1').getVerseMax()
        references=['Gen.19.1','Gen.1.1','Ps.119.1',f'Mark.10.{edge}','Rev.22.21']
        for reference in references:
            assert tab.show(reference);spin()
            assert tab.current.unique_verses()==expected.chapter(reference).unique_verses()
            first=tab._document.spans[0]
            displayed=tab._document.copy(first.body,first.end).replace('\ufffc','')
            assert normalized(displayed)==normalized(expected.chapter(reference).unique_verses()[0][1])
        assert tab.show('Gen.12.1');spin()
        window.primary_version.sync()
        window.primary_version.choices.set_selected(window.primary_version.names.index(source));spin()
        assert tab.state.resource==source and tab.state.reference=='Gen.12.1'
        assert not window.primary_version.status.get_visible();opened.append('Primary selector')
        assert tab.show('Gen.11.3');window.new_tab();spin()
        assert window.open_installed_resource(target);spin();tab=window.active_tab
        assert tab.state.resource==target and tab.state.reference=='Gen.11.3';opened.append('New tab')
        tab.state.comparison=source;tab.refresh_comparison();spin()
        assert tab._comparison_reader and tab._comparison_aligned
        assert tab.comparison_text.get_buffer().get_char_count()>100
        assert tab.show('Gen.12.1');tab.refresh_comparison();spin()
        assert tab._comparison_reader and not tab._comparison_aligned
        assert not tab.status.get_visible()
        window.study_button.set_active(True);window.study.tools.set_visible_child_name('notes');spin()
        assert not hasattr(window.study,'translation_notes')
        assert tab.show('Gen.19.1');spin();window.save_session()
    finally:window.close();close_test_dialogs();spin()
    with (patch('urllib.request.urlopen',side_effect=AssertionError('Offline restore')),
            patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('Offline restore'))):
        window=Window(app,library);window.present();spin()
        try:
            assert window.active_tab.state.resource==target and window.active_tab.state.reference=='Gen.19.1'
            assert window.active_tab.current.unique_verses()==expected.chapter('Gen.19.1').unique_verses()
            opened.append('Offline session restore')
        finally:window.close();close_test_dialogs();spin()
    assert notes.all()==original_notes and preferences.path.read_bytes()==original_preferences
    assert snapshot(library.root)==files
    report=dict(result='PASS',app_import=inspect.getfile(Window),packaged=args.require_packaged,
        opening_routes=opened,verified_owned_references=references,verified_mapping_and_unaudited_verse_guard=True,
        independent_comparison=True,verified_comparison=True,study_panel=True,notes_preserved=len(original_notes),preferences_preserved=True,
        module_files_preserved=len(files),existing_client_profile_accessed=False)
    args.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
