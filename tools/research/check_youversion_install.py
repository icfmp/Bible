"""Whole-edition installer/offline GTK proof in a NEW disposable profile.

Uses the already acquired returned-URL archive, without a second provider ZIP
request. Outputs counts/hashes only; all source/compiled content stays private.
"""
import argparse
from contextlib import nullcontext
import hashlib
import inspect
import json
from pathlib import Path
import resource
import shutil
import time
from unittest.mock import patch


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--compiler',default='/app/bin/osis2mod')
    parser.add_argument('--offline-metadata',action='store_true')
    parser.add_argument('--require-packaged',action='store_true')
    parser.add_argument('--gtk',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    from bible.library import Library
    from bible.youversion_install import acknowledgement,resource_from_metadata,run_conversion
    from bible.youversion_source import read_edition
    from bible.sword_provider import Reader
    import Sword
    if args.require_packaged:
        assert inspect.getfile(Reader).startswith('/app/') and inspect.getfile(Sword).startswith('/app/')
        assert args.compiler=='/app/bin/osis2mod'
    data=json.loads(args.metadata.read_text());edition=read_edition(data,21)
    item=resource_from_metadata(data)
    profile=args.output/'profile';library=Library(profile/'translations')
    # Seed the legitimate first acquisition into the same immutable URL cache.
    # Range/cancel/cache acquisition is tested independently with synthetic data.
    cache=profile/'cache/youversion';cache.mkdir(parents=True,mode=0o700)
    key=hashlib.sha256(edition.archive_url.encode()).hexdigest()
    shutil.copyfile(args.archive,cache/(key+'.zip'))
    sha=hashlib.sha256(args.archive.read_bytes()).hexdigest()
    (cache/(key+'.json')).write_text(json.dumps(dict(url=edition.archive_url,complete=True,sha256=sha)))
    preserved=profile/'preserved-preferences.json';preserved.write_bytes(b'{"existing":"unchanged"}')
    phases={};start=time.monotonic()
    def phase(name,done,total):phases[name]=(done,total)
    def compiler(archive,metadata,target,phase,cancelled):
        return run_conversion(archive,metadata,target,phase,cancelled,compiler=args.compiler)
    def metadata_response(url,out,**kwargs):
        assert url=='https://nodejs.bible.com/api/bible/version/3.3?id=21'
        out.write(args.metadata.read_bytes())
    with patch('bible.youversion_install.run_conversion',side_effect=compiler),(
            patch('bible.library.download',side_effect=metadata_response) if args.offline_metadata else nullcontext()):
        library.install(item,phase=phase,permission=acknowledgement(item))
    elapsed=time.monotonic()-start
    assert library.installed()==[item.id]
    root=library.root/item.id
    assert json.loads((root/'.verified.json').read_text())['all_text_notes_headings_verified']
    assert library.resource(item.id).acquisition==item.acquisition
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline')):
        reader=Reader(root,item.id);assert reader.versification=='Original'
        assert len(reader.books)==66
        chapter=reader.chapter('Exod.27.14')
        assert ('Exod.27.15','Exod.27.14') in chapter.links
        assert len(reader.chapter('John.1.1').unique_verses())==51
        assert len(reader.editorial_notes('John.1.1'))==14
        assert reader.introduction('John') is not None
        library.install(item)  # Installed resources never redownload.
        gtk=False
        if args.gtk:
            from bible.ui import Application,Window
            from tests.test_ui import spin,close_test_dialogs
            app=Application.get_default() or Application();app.register()
            window=Window(app,library);window.present();spin()
            try:
                tab=window.active_tab;tab.navigate(item.id,'Exod.27.14');spin()
                assert sum('Exod.27.14' in s.members for s in tab._document.spans)==1
                assert tab.text._verse_labels['Exod.27.15']=='14–15'
                before=window.notes_store.all()
                tab.navigate(item.id,'John.1.1');window.study_button.set_active(True)
                window.study.tools.set_visible_child_name('translation-notes');spin()
                assert window.study.translation_notes.stamp==(id(tab.reader),'John.1')
                assert window.study.translation_notes.text.get_buffer().get_char_count()>100
                for width in (1100,360):
                    window.set_default_size(width,600);spin()
                window.study_button.set_active(False);spin()
                with patch.object(tab.reader,'editorial_notes',side_effect=AssertionError('Hidden work')):
                    window.study.translation_notes.refresh(force=True)
                assert window.notes_store.all()==before
                gtk=True
            finally:window.close();close_test_dialogs();spin()
    assert preserved.read_bytes()==b'{"existing":"unchanged"}'
    report=dict(result='PASS',installed_entries=json.loads((root/'.verified.json').read_text())['entries'],
                all_native_text_notes_headings_verified=True,source_numbering='org',native_numbering='Original',
                archive_sha256=sha,source_import=inspect.getfile(Reader),sword_import=inspect.getfile(Sword),
                elapsed_seconds=elapsed,conversion_child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                phases=phases,offline_gtk=gtk,offline_reopen=True,existing_preferences_preserved=True,
                live_metadata_revalidated=not args.offline_metadata,provider_agreement_submitted=False,
                source_distribution=False)
    (args.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
