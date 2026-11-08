"""Actual Library downloads and native NFC section/fragment reading validation.

Only a marked disposable developer profile is accepted. Screenshots remain
private artifacts; JSON reports contain aggregate checks, never a profile dump.
"""
import argparse,hashlib,inspect,json,time,traceback
from pathlib import Path
from unittest.mock import patch


def descendants(widget):
    yield widget
    child=widget.get_first_child()
    while child:
        yield from descendants(child);child=child.get_next_sibling()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--prepare',action='store_true');parser.add_argument('--offline',action='store_true')
    parser.add_argument('--baseline',action='store_true');parser.add_argument('--require-packaged',action='store_true')
    parser.add_argument('--compiler',default='/app/bin/osis2mod')
    args=parser.parse_args();marker=args.profile/'.nfc-test-profile'
    if args.prepare:
        assert not args.profile.exists() or marker.is_file(),'Refusing an unmarked profile'
        args.profile.mkdir(parents=True,exist_ok=True);marker.write_text('Disposable NFC section validation\n')
    assert marker.is_file()
    if args.offline:
        assert not args.prepare
        assert len(Path('/proc/net/route').read_text().splitlines())<=1,'Network routes remain available'
    from bible.library import Library,catalogue
    from bible.notes import NoteStore
    from bible.preferences import Preferences
    from bible.sword_provider import Reader
    library=Library(args.profile/'translations')
    if args.prepare and 'KJV' not in library.installed():library.install(next(r for r in catalogue() if r.id=='KJV'))
    store=NoteStore(args.profile/'notes.sqlite3')
    if not store.all():store.save('PRESERVED NFC VALIDATION NOTE',[],versification='KJV',start='Gen.1.1',origin_translation='KJV',origin_language='en')
    original_notes=store.all();store.close()
    preferences=Preferences(args.profile/'reading-preferences.json')
    if not preferences.path.exists():preferences.save()
    def hashes():return {str(p.relative_to(library.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in library.root.rglob('*') if p.is_file()}
    preserved=hashes()
    from bible.ui import Application,Window,Gtk
    from tests.test_ui import spin,close_test_dialogs
    from tests.test_appearance import SystemStyleOverride
    from tools.check_alpha_ui import X11Input
    from tools.check_client_feedback import Screen
    if args.require_packaged:
        assert inspect.getfile(Window).startswith('/app/') and inspect.getfile(Reader).startswith('/app/')
        assert args.compiler=='/app/bin/osis2mod'
    compiler_patch=None
    if args.compiler!='/app/bin/osis2mod':
        from bible.youversion_install import run_conversion
        def conversion(*values,**options):return run_conversion(*values,compiler=args.compiler,**options)
        compiler_patch=patch('bible.youversion_install.run_conversion',side_effect=conversion);compiler_patch.start()
    app=Application.get_default() or Application();app.register()
    window=Window(app,library);window.set_default_size(1200,900);window.present();spin()
    native=X11Input();native.activate(window);screen=Screen(native)
    args.output.mkdir(parents=True,exist_ok=True)
    report=dict(app_import=inspect.getfile(Window),ui_sha256=hashlib.sha256(Path(inspect.getfile(Window)).read_bytes()).hexdigest(),
                gtk=[Gtk.get_major_version(),Gtk.get_minor_version(),Gtk.get_micro_version()],
                renderer=type(window.get_renderer()).__name__,offline=args.offline,baseline=args.baseline,
                downloads=[],reading=[],captures=[],completed=False)
    if args.require_packaged:assert 'GL' in report['renderer']
    def save():(args.output/('nfc-offline.json' if args.offline else 'nfc.json')).write_text(json.dumps(report,indent=2)+'\n')
    def shot(name):
        native.move_at(window,2,2);spin(duration=.1);screen.grab(args.output/(name+'.png'))
        report['captures'].append(dict(file=name+'.png',width=window.get_width(),height=window.get_height()))
    def download(identifier):
        original_preferences=preferences.path.read_bytes()
        from bible.youversion_catalogue import editions
        resource=next(r for r in editions('fra') if r.name=='YV'+str(identifier))
        assert resource.id not in library.installed(),'A real fresh download is required'
        with patch('bible.catalogue_window.CatalogueWindow.auto_load',return_value=False):dialog=window.open_library('bible')
        spin(lambda:not dialog.preparing and not dialog._building_rows);dialog._catalogue_requested=True
        dialog.source_filter.set_selected(dialog.source_ids.index('youversion'))
        dialog.language.set_selected(dialog.language.codes.index('fr'));dialog.request_youversion_language(force=True)
        spin(lambda:not dialog.session.youversion_loading and not dialog._building_rows and any(r.id==resource.id for r in dialog.filtered_resources),timeout=120)
        index=next(i for i,r in enumerate(dialog.filtered_resources) if r.id==resource.id)
        dialog.open_details(None,index);spin(lambda:not dialog.busy and not dialog._building_rows,timeout=120)
        assert dialog.selected_resource().id==resource.id
        native.click(dialog.download_button);spin(duration=.3)
        def confirmation():return next((v for v in Gtk.Window.get_toplevels() if hasattr(v,'get_response_label') and v.get_mapped()),None)
        spin(lambda:confirmation() is not None,timeout=120)
        confirmation_dialog=confirmation();native.activate(confirmation_dialog)
        from bible.i18n import tr
        button=next(v for v in descendants(confirmation_dialog) if isinstance(v,Gtk.Button) and v.get_label()==tr('I have the required permission'))
        started=time.monotonic();native.click(button)
        spin(lambda:not dialog.busy and not dialog.preparing,duration=.4,timeout=600)
        installed=resource.id in library.installed()
        assert preferences.path.read_bytes()==original_preferences,'Installation changed reading preferences'
        report['downloads'].append(dict(edition=identifier,installed=installed,seconds=round(time.monotonic()-started,3),preferences_preserved=True,error=dialog.status.get_text() if not installed else None))
        with SystemStyleOverride() as style:
            for dark in (False,True):
                style.set(dark=dark,high=False);window.appearance.update('mode','night' if dark else 'day');spin()
                shot('library-'+str(identifier)+('-dark' if dark else '-light'))
        dialog.close();spin();native.activate(window)
        if identifier==2367 and args.baseline:
            assert not installed and 'SIR.1' in report['downloads'][-1]['error']
        else:assert installed,report['downloads'][-1]
    try:
        if args.prepare:
            download(104);download(2367)
            assert window.notes_store.all()==original_notes
            # Theme changes above are intentional developer capture actions;
            # installation itself must preserve every pre-existing module.
            assert all(hashes().get(path)==value for path,value in preserved.items())
            if args.baseline:report['completed']=True;save();return
        assert {'KJV','youversion~YV104','youversion~YV2367'}<=set(library.installed())
        root=library.root/'youversion~YV2367';reader=Reader(root,'youversion~YV2367')
        receipt=json.loads((root/'.verified.json').read_text());report['native_receipt']=receipt
        if not args.offline:
            from bible.youversion_source import read_edition
            from tools.research.check_source_units import audit
            edition=read_edition(json.loads(library.resource('youversion~YV2367').acquisition),2367)
            cache=args.profile/'cache/youversion'/(hashlib.sha256(edition.archive_url.encode()).hexdigest()+'.zip')
            report['independent_dom']=audit(cache,edition,reader)
        tab=window.active_tab
        with SystemStyleOverride() as style:
            for dark in (False,True):
                style.set(dark=dark,high=False);window.appearance.update('mode','night' if dark else 'day')
                for reference in ('Gen.1.1','Sir.1.1','Sir.1_1.1','Sir.43.17','Sir.44.23','Rev.22.21'):
                    tab.state.comparison='';tab.refresh_comparison();window.study_button.set_active(False)
                    assert tab.navigate('youversion~YV2367',reference);spin()
                    assert tab.reader.key(tab.state.reference).getOSISRef()==reference
                    assert tab._document.spans and tab.text.get_buffer().get_char_count()>100
                    if tab.current.units:assert tab.selected_passage()==(reference,reference)
                    record=dict(reference=reference,chapter=tab.current.reference,dark=dark,units=len(tab.current.display_units),labels=[s.number for s in tab._document.spans] if tab.current.units else None)
                    report['reading'].append(record)
                    if reference in ('Sir.1_1.1','Sir.43.17','Sir.44.23'):
                        for width in (1200,360):
                            window.set_default_size(width,850);spin(duration=.3)
                            shot(reference.replace('.','-')+'-'+str(width)+('-dark' if dark else '-light'))
                    window.set_default_size(1200,900)
                # NBS has no Sirach: first establish the real independent pane
                # on a chapter present in both resources, then retain it while
                # the primary opens the deuterocanonical source chapter.
                tab.navigate('youversion~YV2367','Gen.11.1');spin()
                tab.state.comparison='youversion~YV104';window.sync_comparison();spin()
                assert tab._comparison_reader and tab.comparison_text.get_buffer().get_char_count()>100
                assert not tab._comparison_aligned,'No NFC/NBS alignment has been verified'
                comparison=tab.comparison_visible_reference()
                assert comparison and comparison.startswith('Gen.11.')
                tab.show('Sir.43.17');spin()
                assert tab._comparison_reader and tab.comparison_visible_reference().startswith('Gen.11.')
                window.study_button.set_active(True);window.study.tools.set_visible_child_name('notes')
                spin()
                assert tab.reader.editorial_notes('Sir.43.17')
                assert not hasattr(window.study,'translation_notes')
                shot('parallel-study'+('-dark' if dark else '-light'))
                window.study_button.set_active(False)
                with patch.object(tab.reader,'editorial_notes',side_effect=AssertionError('Hidden source-note work')):
                    window.study.refresh(force=True)
        assert window.notes_store.all()==original_notes
        assert all(hashes().get(path)==value for path,value in preserved.items())
        report.update(completed=True,existing_modules_preserved=len(preserved),personal_notes_preserved=len(original_notes),provider_agreement_submitted=False)
        save()
    except BaseException:
        report['failure']=traceback.format_exc();save();raise
    finally:
        window.close();close_test_dialogs();spin();native.close()
        if compiler_patch:compiler_patch.stop()


if __name__=='__main__':main()
