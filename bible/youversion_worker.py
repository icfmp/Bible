"""Private, cancellable conversion/readback worker; never imports GTK."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as E

from .youversion_content import native_chapter, normalized, parse, project,semantic_roles
from .youversion_osis import NS, BOOKS, osis_ref
from .youversion_source import read_edition,archive_chapters,to_osis
from .youversion_editions import EDITIONS,module_id,storage_system


def emit(phase,done,total):
    print(json.dumps(dict(phase=phase,done=done,total=total)),flush=True)


def digest(value):
    from dataclasses import asdict,is_dataclass
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,
                   default=lambda obj:asdict(obj) if is_dataclass(obj) else obj)
    return hashlib.sha256(raw.encode()).hexdigest()


def source_canon(system):
    return json.loads((Path(__file__).parent/'versification_data'/(system+'.json')).read_text())['canon']


def build(archive,metadata,target,compiler,identifier=21):
    name=module_id(identifier);system=storage_system(identifier)
    edition=read_edition(json.loads(metadata.read_text()),identifier)
    known=identifier in EDITIONS
    if known and edition.language!=EDITIONS[identifier][2]:raise ValueError('Unexpected edition language')
    if known and edition.metadata.get('vrs')!=EDITIONS[identifier][0]:raise ValueError('Source numbering changed')
    target.mkdir(parents=True,exist_ok=False)
    canon=source_canon(system) if known else {};checks=[];seen=set();active_book=None;source_index=[];verse_order={}
    testaments={}
    if not known:
        for entry in edition.metadata['books']:
            if not entry['text']:continue
            book=BOOKS[entry['usfm']]
            role=entry.get('canon')
            if role not in ('ot','nt','dc','ap'):raise ValueError('Unknown source testament')
            numbers=[int(ref.rsplit('.',1)[1]) for ref in edition.chapters if ref.startswith(entry['usfm']+'.') and '.INTRO' not in ref]
            if not numbers or max(numbers)>255:raise ValueError('Invalid source chapter inventory')
            canon[book]=[0]*max(numbers);testaments[book]=2 if role=='nt' else 1
        # Keep the returned book order inside each native testament.
        canon={book:canon[book] for testament in (1,2) for book in canon if testaments[book]==testament}
    total=len(edition.chapters)
    osis=target.parent/'edition.osis.xml'
    with osis.open('wb') as output:
        for done,chapter in enumerate(archive_chapters(archive,edition,complete=True),1):
            ref=chapter['reference'];code,number=ref.split('.')
            source_index.append(dict(reference=ref,source_language=chapter['source_language'],encoded_sha256=chapter['encoded_sha256'],
                                     html_sha256=chapter['html_sha256']))
            book=BOOKS[code]
            xml,_=to_osis(chapter,edition);root=E.fromstring(xml)
            text=root.find('{'+NS+'}osisText');division=text.find('{'+NS+'}div')
            if done==1:
                header=text.find('{'+NS+'}header')
                output.write(('<?xml version="1.0" encoding="UTF-8"?><osis xmlns="'+NS+'"><osisText osisIDWork="YouVersion'+str(identifier)+'" osisRefWork="Bible" xml:lang="'+edition.language+'">').encode())
                output.write(E.tostring(header,encoding='utf-8'))
            if book!=active_book:
                if active_book:output.write(b'</div>')
                output.write(('<div type="book" osisID="'+book+'">').encode());active_book=book
            for item in division:output.write(E.tostring(item,encoding='utf-8'))
            if number.startswith('INTRO'):
                if number!='INTRO1':raise ValueError('Unsupported multiple book introductions')
                check=dict(ref=book+'.0.0',intro=True,
                           expected=digest((normalized(''.join(division.itertext())),
                                            project(division),semantic_roles(division))))
            else:
                chapter_ref=osis_ref(ref);seen.add(chapter_ref)
                units=[node.get('osisID').split() for node in division.iter()
                       if node.tag=='{'+NS+'}verse' and node.get('sID')]
                members=[item for unit in units for item in unit]
                maximum=max((int(item.rsplit('.',1)[1]) for item in members),default=0)
                if (not members or len(members)!=len(set(members)) or maximum>2000 or
                        known and maximum!=canon[book][int(number)-1]):
                    raise ValueError('Source chapter numbering changed')
                if not known:canon[book][int(number)-1]=maximum
                order=[int(item.rsplit('.',1)[1]) for item in members]
                if order!=sorted(order):verse_order[chapter_ref]=order
                check=dict(ref=chapter_ref,intro=False,units=units,
                           expected=digest((project(division,milestones=True,preverse=chapter_ref+'.0'),semantic_roles(division))))
            checks.append(check);emit('converting',done,total)
        output.write(b'</div></osisText></osis>')
    expected=({f'{book}.{number}' for book,chapters in canon.items() for number in range(1,len(chapters)+1)} if known else
              {osis_ref(ref) for ref in edition.chapters if '.INTRO' not in ref})
    if seen!=expected or sum(item['intro'] for item in checks)!=sum('.INTRO' in ref for ref in edition.chapters):
        raise ValueError('Incomplete source canon')
    relative='modules/texts/rawtext/'+name.lower()
    data=target/relative;data.mkdir(parents=True)
    emit('compiling',0,0)
    reference_index_sha256=None;index_options=[]
    if not known:
        from .source_versification import write_index,register_index
        index=target/'.source-versification'
        reference_index_sha256=write_index(index,system,canon,testaments)
        register_index(index,verified=False);index_options=['-V',str(index)]
    with (target.parent/'compiler.log').open('wb') as log:
        compiled=subprocess.run([compiler,str(data),str(osis),'-v',system,*index_options],stdout=log,stderr=subprocess.STDOUT,timeout=240)
    if compiled.returncode:raise ValueError('SWORD compilation failed')
    # Metadata cannot inject native module options or file paths.
    def line(value):return ' '.join(str(value).split()).replace('\\','/').replace('\x00','')
    abbreviation=edition.metadata.get('local_abbreviation') or edition.metadata.get('abbreviation') or name
    if not isinstance(abbreviation,str) or len(abbreviation)>40:abbreviation=name
    (target/'mods.d').mkdir()
    (target/'mods.d'/(name.lower()+'.conf')).write_text(
        f'[{name}]\nDataPath=./{relative}/\nModDrv=RawText\nSourceType=OSIS\nEncoding=UTF-8\n'
        f'Versification={system}\nBibleSource=YouVersion\nGlobalOptionFilter=OSISFootnotes\nGlobalOptionFilter=OSISHeadings\nGlobalOptionFilter=OSISRedLetterWords\n'
        f'Lang={line(edition.language)}\nDescription={line(edition.title)}\nAbbreviation={line(abbreviation)}\n'
        +('Direction=RtoL\n' if edition.metadata['language'].get('text_direction')=='rtl' else '')+
        f'Copyright={line(edition.attribution)}\nDistributionLicense=Source conditions apply\n'
        f'About=https://www.bible.com/versions/{identifier}\n',encoding='utf-8')
    import Sword
    manager=Sword.SWMgr(str(target));module=manager.getModule(name)
    if module is None:raise ValueError('Compiled resource missing')
    key=Sword.VerseKey();key.setVersificationSystem(system);key.setAutoNormalize(False);key.setIntros(True)
    if key.getVersificationSystem()!=system:raise ValueError('Packaged source numbering support is required')
    for done,check in enumerate(checks,1):
        if check['intro']:
            key.setText(check['ref']);module.setKey(key);raw=module.getRawEntry()
            raw=raw if isinstance(raw,str) else raw.c_str()
            native=parse('<root>'+raw+'</root>')
            actual=digest((normalized(''.join(native.itertext())),project(native),semantic_roles(native)))
        else:
            units=check['units'];references=[unit[0] for unit in units]
            key.setText(check['ref']+'.1')
            present=set()
            for verse in range(1,key.getVerseMax()+1):
                key.setVerse(verse)
                if module.hasEntry(key):present.add(key.getOSISRef())
            if present!={ref for unit in units for ref in unit}:raise ValueError('Compiled chapter inventory differs')
            for unit in units:
                key.setText(unit[0]);first=Sword.VerseKey(key)
                for alias in unit[1:]:
                    key.setText(alias)
                    if not module.isLinked(first,key):raise ValueError('Compiled verse bridge differs')
            native=native_chapter(module,key,check['ref'],references)
            actual=digest((project(native),semantic_roles(native)))
        if actual!=check['expected']:raise ValueError('Compiled text or editorial content differs: '+check['ref'])
        emit('verifying',done,total)
    order_sha256=None
    if verse_order:
        raw=json.dumps(verse_order,sort_keys=True,separators=(',',':')).encode()
        (target/'.source-verse-order.json').write_bytes(raw)
        order_sha256=hashlib.sha256(raw).hexdigest()
    (target/'.verified.json').write_text(json.dumps(dict(entries=len(checks),
        source_numbering=edition.metadata.get('vrs'),storage_numbering=system,
        reference_index_sha256=reference_index_sha256,
        source_verse_order_sha256=order_sha256,
        archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        all_text_notes_headings_verified=True)))
    (target/'.source-index.json').write_text(json.dumps(dict(parser_version=1,entries=source_index)))


if __name__=='__main__':
    build(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]),sys.argv[4],int(sys.argv[5]) if len(sys.argv)>5 else 21)
