"""Local real-edition #26 sample proof; input acquisition/rights are separate.

Source HTML/OSIS/modules/logs stay in the NEW private output directory. Publish
only verification.json (hashes/statistics), never the generated source corpus.
Uses the independent DOM/readback oracle from PR #59; requires research lxml.
"""
import argparse
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import re
import subprocess
import time
from xml.etree import ElementTree as E

from .check_yves_fidelity import check, normalized, dom_verses, canonical_unit
from .semantic_osis import NS
from .yves_source import archive_chapters, read_edition, to_osis


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path);parser.add_argument('--metadata',type=Path,required=True)
    parser.add_argument('--version',type=int,default=21);parser.add_argument('--compiler',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--extended',action='store_true',help='Also inspect bridges, heading notes, split verses and original numbering')
    parser.add_argument('--skip-application-check',action='store_true',help='Diagnostic raw SWORD check only, never an application pass')
    parser.add_argument('--require-packaged',action='store_true')
    parser.add_argument('--gtk',action='store_true',help='Check actual sample text in a disposable offline GTK window')
    args=parser.parse_args();started=time.monotonic()
    args.output.mkdir(parents=True,mode=0o700,exist_ok=False)
    edition=read_edition(json.loads(args.metadata.read_text()),args.version)
    selected={'JHN.1','JHN.INTRO1','PSA.3'};trees={};reports={};source_chapters=0
    cases=[('YvesBDS21ResearchJohn','john-with-intro.osis.xml','JHN.1','John.1','KJV'),
           ('YvesBDS21ResearchPsalms','PSA.3.osis.xml','PSA.3','Ps.3','Segond')]
    if args.extended:
        for label,ref,target in [('Bridge','EXO.27','Exod.27'),('HeadingNotes','EXO.36','Exod.36'),
                                 ('SplitVerse','GEN.35','Gen.35'),('OriginalJoel','JOL.4','Joel.4'),
                                 ('OriginalNumbers','NUM.17','Num.17'),('LongBridge','1CH.25','1Chr.25')]:
            selected.add(ref);cases.append(('YvesBDS21Research'+label,ref+'.osis.xml',ref,target,'German'))
    for chapter in archive_chapters(args.archive,edition,complete=True):
        source_chapters+=1
        if chapter['reference'] not in selected:continue
        ref=chapter['reference'];raw,report=to_osis(chapter,edition)
        (args.output/(ref+'.html')).write_text(chapter['source_html'])
        (args.output/(ref+'.osis.xml')).write_bytes(raw)
        trees[ref]=E.fromstring(raw);reports[ref]=report
    assert set(trees)==selected,'Required actual edition samples absent'
    ns={'o':NS};john=trees['JHN.1']
    john.find('.//o:div[@type="book"]',ns).insert(0,deepcopy(trees['JHN.INTRO1'].find('.//o:div[@type="introduction"]',ns)))
    (args.output/'john-with-intro.osis.xml').write_bytes(E.tostring(john,encoding='UTF-8',xml_declaration=True))
    from bible.sword_provider import Reader
    import Sword
    if args.require_packaged:
        assert inspect.getfile(Reader).startswith('/app/') and inspect.getfile(Sword).startswith('/app/')
        assert str(args.compiler)=='/app/bin/osis2mod' and args.compiler.is_file()
    results=[]
    for name,filename,ref,chapter,system in cases:
        root=args.output/'translations'/name;data=root/'modules/texts/rawtext'/name.lower();data.mkdir(parents=True)
        run=subprocess.run([str(args.compiler),str(data),str(args.output/filename),'-v',system],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30,check=True)
        log=run.stdout.decode();(args.output/(name+'.compile.log')).write_text(log)
        assert not re.search(r'\b(?:ERROR|WARNING)\b',log),'Review private compiler diagnostic'
        (root/'mods.d').mkdir();(root/'mods.d'/(name.lower()+'.conf')).write_text(
            f'[{name}]\nDataPath=./modules/texts/rawtext/{name.lower()}/\nModDrv=RawText\nSourceType=OSIS\nEncoding=UTF-8\nLang=fr\n'
            f'Versification={system}\nDescription=BDS 21 LOCAL PARTIAL RESEARCH SAMPLE\n'
            'DistributionLicense=Copyrighted; no redistribution\nGlobalOptionFilter=OSISFootnotes\nGlobalOptionFilter=OSISHeadings\n'
            'GlobalOptionFilter=OSISRedLetterWords\nCopyright='+edition.attribution.replace('\n',' ')+'\n')
        result=check(args.output/(ref+'.html'),args.output/(ref+'.osis.xml'),root,name,ref)
        reader=Reader(root,name)
        if not args.skip_application_check:
            loaded=reader.chapter(chapter)
            expected,_=dom_verses((args.output/(ref+'.html')).read_bytes(),ref)
            expected={canonical_unit(key).split()[0]:value for key,value in expected.items()}
            assert {key:normalized(text) for key,text in loaded.unique_verses()}==expected,'Application text readback mismatch'
            result['application_all_verses_match']=True
            result['application_structure_kinds']=sorted({s.kind for parts in reader.structured_chapter(loaded).values() for s in parts})
        result['module']=name;result['scoped_versification']=system
        if ref=='JHN.1':
            from lxml import etree as L,html
            raw=(args.output/'JHN.INTRO1.html').read_bytes();dom=html.fromstring(raw.decode('utf-8',errors='strict'))
            intro=dom.xpath('//div[@data-usfm="JHN.INTRO1"]')[0]
            expected_intro=normalized(' '.join(''.join(node.itertext()) for node in intro))
            key=Sword.VerseKey();key.setIntros(True);key.setAutoNormalize(False);key.setText('John.0.0');reader.module.setKey(key)
            value=reader.module.getRawEntry();value=value if isinstance(value,str) else value.c_str()
            tree=L.fromstring(('<root>'+value+'</root>').encode())
            assert normalized(' '.join(tree.itertext()))==expected_intro,'Introduction mismatch'
            result['complete_introduction_preserved']=True
        results.append(result)
        (root/'.complete').write_text('Local partial research fixture; not an installed complete edition\n')
    report=dict(status='PASS_REAL_RAW_SWORD_ONLY' if args.skip_application_check else 'PASS_REAL_LOCAL_SAMPLES_NOT_COMPLETE_EDITION',version=edition.identifier,
                application_checked=not args.skip_application_check,
                archive_bytes=args.archive.stat().st_size,archive_sha256=hashlib.sha256(args.archive.read_bytes()).hexdigest(),
                metadata_sha256=hashlib.sha256(args.metadata.read_bytes()).hexdigest(),indexed_chapters=len(edition.chapters),
                decoded_chapters=source_chapters,results=results,documents=reports,
                compiler_sha256=hashlib.sha256(args.compiler.read_bytes()).hexdigest(),source_import=inspect.getfile(Reader),
                elapsed_seconds=time.monotonic()-started,
                limitations=['Versification is scoped to these samples, not edition-wide mapping.',
                             'This local check is not an installed-Flatpak or client-GNOME validation.',
                             'Editorial-note and introduction GUI support and the in-app installer remain outstanding.',
                             'User is responsible for required permissions; no provider approval or agreement submission is asserted.'])
    if args.gtk:
        if args.skip_application_check:raise ValueError('GTK proof requires the application readback checks')
        from bible.ui import Application,Window,Library
        from tests.test_ui import spin
        if args.require_packaged:
            assert inspect.getfile(Window).startswith('/app/')
            assert len(Path('/proc/net/route').read_text().splitlines())<=1,'Flatpak proof requires network isolation'
        app=Application();app.register();window=Window(app,Library(args.output/'translations'));window.present();spin()
        visible_units=0
        try:
            for name,_,ref,target,_ in cases:
                expected,_=dom_verses((args.output/(ref+'.html')).read_bytes(),ref)
                first=canonical_unit(next(iter(expected))).split()[0]
                tab=window.active_tab
                assert tab.navigate(name,first),'Sample navigation failed'
                spin(lambda:not tab._restoring_scroll)
                buffer=tab.text.get_buffer()
                visible=normalized(buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),True)).replace(' ','')
                document=tab._document
                expected_units={canonical_unit(key).split()[0]:text for key,text in expected.items()}
                actual_units={s.reference:normalized(document.copy(s.body,s.end)) for s in document.spans}
                assert actual_units==expected_units,'GTK document unit count/text differs from the independent source'
                assert buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),True)==document.text,'GTK buffer differs from its source document'
                for text in expected.values():
                    assert normalized(text).replace(' ','') in visible,'GTK omitted source text'
                    visible_units+=1
            report['gtk_visible_units_checked']=visible_units
            report['gtk_offline_readback']=True
            report['gtk_exact_unit_text']=True
            report['gtk_source_import']=inspect.getfile(Window)
        finally:window.close()
        report['limitations']=[s for s in report['limitations'] if not s.startswith('This local check')]
        report['limitations'].append('Installed Flatpak is established only when require-packaged is used; client desktop acceptance remains separate.')
    (args.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='documents'},indent=2))


if __name__=='__main__':main()
