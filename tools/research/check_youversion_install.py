"""Whole-edition in-app download, independent fidelity and offline GTK proof.

Only NEW disposable outputs are accepted. Optional sibling-profile reuse proves
that adding an edition preserves earlier resources, real notes and preferences.
Receipts contain counts/hashes only; source and modules remain private.
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


def file_hash(path):
    with path.open('rb') as source:return hashlib.file_digest(source,'sha256').hexdigest()


def snapshot(root):
    return {str(path.relative_to(root)):file_hash(path) for path in root.rglob('*') if path.is_file()}


def independent_check(archive,edition,root,reader):
    """Source DOM versus compiler, independent of the semantic writer's tree."""
    from bible.youversion_source import archive_chapters,to_osis
    from .check_yves_fidelity import check,normalized,canonical_chapter,canonical_unit,dom_verses,suffix
    from lxml import html
    checked=intros=units=notes=0
    for source in archive_chapters(archive,edition,complete=True):
        ref=source['reference']
        if '.INTRO' in ref:
            dom=html.fromstring(source['source_html']).xpath('//div[@data-usfm=$r]',r=ref)[0]
            def flow(node,source_html=False):
                name=node.tag.rsplit('}',1)[-1]
                if source_html and suffix(node)=='label':return ''
                result=node.text or ''
                for child in node:result+=flow(child,source_html)+(child.tail or '')
                return result+('\n' if name in {'div','p','title','l','item','table','tr','td','th','row','cell','br','lb'} else '')
            raw=reader.introduction(canonical_chapter(ref.split('.')[0]+'.1').split('.')[0])
            if raw is None or normalized(flow(dom,True))!=normalized(flow(raw)):
                raise AssertionError('Independent introduction mismatch: '+ref)
            intros+=1
        else:
            xml,_=to_osis(source,edition)
            result=check(source['source_html'].encode(),xml,root,reader.name.split('~')[-1],ref,module=reader.module)
            expected,_=dom_verses(source['source_html'].encode(),ref)
            expected={canonical_unit(key).split()[0]:value for key,value in expected.items()}
            loaded=reader.chapter(canonical_chapter(ref)+'.1')
            actual={key:normalized(value) for key,value in loaded.unique_verses()}
            if actual!=expected:raise AssertionError('Application verse text mismatch: '+ref)
            checked+=1;units+=result['verses_compared'];notes+=result['notes_preserved']
    return dict(chapters=checked,introductions=intros,units=units,notes=notes,all_application_verses_verified=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path,nargs='?')
    parser.add_argument('--metadata',type=Path)
    parser.add_argument('--version',type=int,default=21)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--compiler',default='/app/bin/osis2mod')
    parser.add_argument('--offline-metadata',action='store_true')
    parser.add_argument('--require-packaged',action='store_true')
    parser.add_argument('--gtk',action='store_true')
    parser.add_argument('--independent',action='store_true')
    parser.add_argument('--shared-profile',action='store_true')
    parser.add_argument('--verify-only',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False,mode=0o700)
    from bible.library import Library,download
    from bible.youversion_install import acknowledgement,resource_from_metadata,run_conversion
    from bible.youversion_editions import module_id,METADATA_URL
    from bible.youversion_source import read_edition
    from bible.sword_provider import Reader
    from bible.providers import identity
    import Sword
    name=module_id(args.version);identifier=identity('youversion',name)
    if args.require_packaged:
        assert inspect.getfile(Reader).startswith('/app/') and inspect.getfile(Sword).startswith('/app/')
        assert args.compiler=='/app/bin/osis2mod'
    profile=args.output.parent/'shared-proof-profile' if args.shared_profile else args.output/'profile'
    marker=profile/'.youversion-proof-profile'
    if profile.exists() and not marker.is_file():raise ValueError('Existing non-test profile refused')
    profile.mkdir(parents=True,exist_ok=True,mode=0o700);marker.write_text('Disposable issue 26 proof only\n')
    library=Library(profile/'translations')
    url=METADATA_URL.format(edition=args.version)
    if args.verify_only:data=json.loads(library.resource(identifier).acquisition)
    elif args.metadata:data=json.loads(args.metadata.read_text())
    else:
        import io
        received=io.BytesIO();download(url,received,limit=2*1024*1024,same_origin=True)
        data=json.loads(received.getvalue())
    edition=read_edition(data,args.version);item=resource_from_metadata(data,args.version)
    cache=profile/'cache/youversion';cache.mkdir(parents=True,exist_ok=True,mode=0o700)
    key=hashlib.sha256(edition.archive_url.encode()).hexdigest();retained=cache/(key+'.zip')
    if args.archive:
        shutil.copyfile(args.archive,retained)
        (cache/(key+'.json')).write_text(json.dumps(dict(url=edition.archive_url,complete=True,sha256=file_hash(retained))))
    from bible.notes import NoteStore
    from bible.preferences import Preferences
    store=NoteStore(profile/'notes.sqlite3')
    if not store.all():store.save('PRESERVED SYNTHETIC PERSONAL NOTE',('Preserved',),
        versification='KJV',start='Gen.1.1',end='Gen.1.1',origin_translation='PreviousResource',origin_language='en')
    original_notes=store.all()
    preferences=Preferences(profile/'reading-preferences.json')
    if not preferences.path.exists():preferences.save()
    original_preferences=preferences.path.read_bytes()
    existing=snapshot(library.root);previous=library.installed();phases={};start=time.monotonic()
    transfer={'bytes':0,'total':0,'first':None,'last':None}
    cached=False
    try:
        receipt=json.loads((cache/(key+'.json')).read_text())
        cached=receipt.get('complete') is True and receipt.get('sha256')==file_hash(retained)
    except (OSError,ValueError):pass
    def progress(done,total):
        now=time.monotonic()
        if transfer['first'] is None:transfer['first']=now
        transfer.update(bytes=done,total=total,last=now)
    def phase(stage,done,total):phases[stage]=(done,total)
    def compiler(archive,metadata,target,phase,cancelled,**options):
        return run_conversion(archive,metadata,target,phase,cancelled,compiler=args.compiler,**options)
    def metadata_response(request_url,out,**kwargs):
        assert request_url==url
        out.write(json.dumps(data).encode())
    if not args.verify_only:
        with patch('bible.youversion_install.run_conversion',side_effect=compiler),(
                patch('bible.library.download',side_effect=metadata_response) if args.offline_metadata else nullcontext()):
            library.install(item,progress,phase=phase,permission=acknowledgement(item))
    elapsed=time.monotonic()-start
    assert library.installed()==sorted(set(previous+[item.id]))
    assert all(file_hash(library.root/path)==value for path,value in existing.items())
    assert store.all()==original_notes and preferences.path.read_bytes()==original_preferences
    root=library.root/item.id
    assert json.loads((root/'.verified.json').read_text())['all_text_notes_headings_verified']
    actual=library.resource(item.id)
    assert actual.acquisition==item.acquisition and actual.conditions==item.conditions
    reader=Reader(root,item.id);assert reader.versification==item.versification
    assert len(reader.books)==66
    oracle=independent_check(retained,edition,root,reader) if args.independent else None
    gtk=False;parallel=None
    with patch('urllib.request.urlopen',side_effect=AssertionError('Offline')),patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('Offline')):
        for ref in ('Gen.1.1','Ps.3.1','John.1.1','Rev.22.21'):assert reader.chapter(ref).verses
        if args.version==21:
            assert ('Exod.27.15','Exod.27.14') in reader.chapter('Exod.27.14').links
            assert len(reader.editorial_notes('John.1.1'))==14
            assert reader.introduction('John') is not None
        library.install(item)
        if args.gtk:
            from bible.ui import Application,Window
            from tests.test_ui import spin,close_test_dialogs
            app=Application.get_default() or Application();app.register()
            window=Window(app,library);window.present();spin()
            try:
                tab=window.active_tab;tab.navigate(item.id,'John.1.1');spin()
                assert tab._document.spans and len(tab.text.get_buffer().props.text)>100
                if args.version==21:
                    tab.navigate(item.id,'Exod.27.14');spin()
                    assert tab.text._verse_labels['Exod.27.15']=='14–15'
                    tab.navigate(item.id,'John.1.1')
                counterpart=next((resource for resource in library.installed() if resource!=item.id),None)
                if counterpart:
                    tab.state.comparison=counterpart;tab.refresh_comparison();spin()
                    assert tab._comparison_reader is not None
                    assert len(tab.comparison_text.get_buffer().props.text)>20
                    parallel=True
                window.study_button.set_active(True);window.study.tools.set_visible_child_name('translation-notes')
                try:spin(lambda:window.study.translation_notes.stamp==(id(tab.reader),'John.1'))
                except AssertionError as error:
                    raise AssertionError(dict(expected_reader=id(tab.reader),stamp=window.study.translation_notes.stamp,
                        reference=tab.state.reference,resource=tab.state.resource,tool=window.study.tool,
                        sidebar=window.split.get_show_sidebar(),mapped=window.study.translation_notes.get_mapped(),
                        size=(window.get_width(),window.get_height()))) from error
                assert window.study.translation_notes.stamp==(id(tab.reader),'John.1')
                assert window.study.translation_notes.text.get_buffer().get_char_count()>0
                for width in (1100,360):window.set_default_size(width,600);spin()
                window.study_button.set_active(False);spin()
                with patch.object(tab.reader,'editorial_notes',side_effect=AssertionError('Hidden work')):
                    window.study.translation_notes.refresh(force=True)
                assert window.notes_store.all()==original_notes
                gtk=True
            finally:window.close();close_test_dialogs();spin()
    assert store.all()==original_notes and preferences.path.read_bytes()==original_preferences
    assert all(file_hash(library.root/path)==value for path,value in existing.items())
    report=dict(result='PASS',edition=args.version,title=edition.title,
        installed_entries=json.loads((root/'.verified.json').read_text())['entries'],
        all_native_text_notes_headings_verified=True,independent_dom=oracle,
        source_numbering=edition.metadata['vrs'],native_numbering=reader.versification,
        archive_sha256=file_hash(retained),source_import=inspect.getfile(Reader),sword_import=inspect.getfile(Sword),
        elapsed_seconds=elapsed,conversion_child_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        phases=phases,gtk=gtk,offline_reopen=True,parallel_gtk=parallel,
        existing_resources_preserved=len(previous),existing_personal_notes_preserved=len(original_notes),
        existing_preferences_preserved=True,live_metadata_revalidated=not args.verify_only and not args.offline_metadata,
        actual_archive_download_in_application=not args.verify_only and item.id not in previous and not cached,
        transfer=dict(bytes=transfer['bytes'],total=transfer['total'],
            seconds=(transfer['last']-transfer['first']) if transfer['first'] is not None else 0),
        offline_verification_only=args.verify_only,provider_agreement_submitted=False,source_distribution=False)
    (args.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
