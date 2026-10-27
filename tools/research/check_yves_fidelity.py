"""Independent DOM/readback oracle reused from PR #59 for local YVES samples.

Uses independent DOM extraction, not the converter's semantic model as its oracle.
Source markup is trusted only as data. Prints counts/hashes, never scripture text.
Run this optional research tool with lxml and SWORD Python bindings installed.
"""
from collections import defaultdict
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from lxml import etree as E, html


def normalized(s):
    # Compiler NFC plus semantic whitespace normalization only. No case/punctuation
    # folding, translation changes, dropped superscriptions or word substitutions.
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', s)).strip()


def suffix(el):
    classes=set(el.get('class','').split())
    return next((role for role in ('verse','note','label','fr',*HEADING_ROLES) if role in classes),'')


HEADING_ROLES=('s','s1','s2','s3','ms','ms1','ms2','r','mr','qa','imt','imt1','imt2','imt3','is1')


def remove(el):
    """Discard a subtree while retaining its following text."""
    parent = el.getparent()
    if el.tail:
        previous = el.getprevious()
        if previous is None:
            parent.text = (parent.text or '') + el.tail
        else:
            previous.tail = (previous.tail or '') + el.tail
    parent.remove(el)


def dom_verses(raw, reference):
    root = html.fromstring(raw.decode('utf-8')).xpath('//div[@data-usfm=$r]', r=reference)[0]
    result = defaultdict(list)
    for span in root.iter('span'):
        if suffix(span) != 'verse':
            continue
        cleaned = deepcopy(span)
        for child in list(cleaned.iterdescendants()):
            if suffix(child) in {'note', 'label'} and child.getparent() is not None:
                remove(child)
        # Separator is the semantic paragraph/poetry boundary between fragments;
        # converter writes explicit block whitespace rather than flattening words.
        result[span.get('data-usfm')].append(''.join(cleaned.itertext()))
    return {ref: normalized(' '.join(parts)) for ref, parts in result.items()}, root


def raw_body(raw):
    tree = E.fromstring(('<root>'+raw+'</root>').encode())
    for el in list(tree.xpath('.//note|.//title')):
        if el.getparent() is not None:
            remove(el)
    return normalized(''.join(tree.itertext()))


def xml_verses(xml):
    out = defaultdict(list)
    active = None
    active_sid = None
    def walk(el):
        nonlocal active,active_sid
        tag = E.QName(el).localname
        if tag == 'verse':
            if el.get('sID'):
                active = el.get('osisID')
                out.setdefault(active,[])
                active_sid = el.get('sID')
            elif el.get('eID'):
                if active_sid != el.get('eID'):
                    raise AssertionError('Unpaired verse milestones')
                active = None
                active_sid = None
            return
        if tag in {'note', 'title', 'header'}:
            return
        if active and el.text:
            out[active].append(el.text)
        for c in el:
            walk(c)
            if active and c.tail:
                out[active].append(c.tail)
    walk(E.fromstring(xml))
    if active:
        raise AssertionError('Unclosed verse')
    return {k: normalized(''.join(v)) for k, v in out.items()}


def canonical_chapter(reference):
    # Explicit standard identifiers, independent of the converter's document tree.
    usfm='GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV'.split()
    osis='Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth Job Ps Prov Eccl Song Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal Matt Mark Luke John Acts Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev'.split()
    books=dict(zip(usfm,osis,strict=True))
    code,number=reference.split('.')
    return books[code]+'.'+number


def canonical_unit(source_reference):
    return ' '.join(canonical_chapter(ref.rsplit('.',1)[0])+'.'+ref.rsplit('.',1)[1]
                    for ref in source_reference.split('+'))


def heading_text(node,source=False):
    clean=deepcopy(node)
    for child in list(clean.iterdescendants()):
        if (suffix(child)=='note' if source else E.QName(child).localname=='note') and child.getparent() is not None:
            remove(child)
    return normalized(''.join(clean.itertext()))


def compiled_chapter(entries):
    """Parse the complete native chapter, preserving entry boundaries with PIs.

    SWORD entries are fragments: list/item markup may start in one verse and end
    in another. Requiring every entry to be an XML document is not valid. Joining
    them in actual index order permits strict parsing without a recovery parser.
    """
    joined='<root>'+''.join('<?source-unit '+reference+'?>'+raw for reference,raw in entries)+'</root>'
    root=E.fromstring(joined.encode());bodies=defaultdict(list);notes=[];titles=[];active=None
    def visit(node):
        nonlocal active
        if isinstance(node,E._ProcessingInstruction):
            if node.target=='source-unit':active=node.text
            return
        if node.tag=='note':notes.append(node);return
        if node.tag=='title':
            titles.append(node);notes.extend(node.xpath('.//note'));return
        if active and node.text:bodies[active].append(node.text)
        for child in node:
            visit(child)
            if active and child.tail:bodies[active].append(child.tail)
    visit(root)
    return {ref:normalized(''.join(parts)) for ref,parts in bodies.items()},notes,titles


def check(source: Path, xml: Path, root: Path, module_name: str, reference: str, *, module=None):
    import Sword
    raw=source if isinstance(source,bytes) else source.read_bytes()
    expected,dom=dom_verses(raw,reference);xml_result=xml_verses(xml if isinstance(xml,bytes) else xml.read_bytes())
    manager=None if module is not None else Sword.SWMgr(str(root))
    mod=module if module is not None else manager.getModule(module_name)
    if mod is None:raise AssertionError('SWORD cannot discover the compiled module')
    key=Sword.VerseKey();key.setVersificationSystem(mod.getConfigEntry('Versification'))
    key.setAutoNormalize(False);key.setIntros(True);chapter=canonical_chapter(reference)
    def entry(target):
        key.setText(target);mod.setKey(key);value=mod.getRawEntry()
        return value if isinstance(value,str) else value.c_str()
    entries=[(chapter+'.0',entry(chapter+'.0'))]
    for source_ref,content in expected.items():
        targets=canonical_unit(source_ref).split();target=targets[0]
        if xml_result.get(' '.join(targets))!=content:raise AssertionError('OSIS text mismatch: '+source_ref)
        key.setText(target)
        if key.popError()!='\x00' or not mod.hasEntry(key):raise AssertionError('Missing compiled verse: '+target)
        value=entry(target);entries.append((target,value));first_key=Sword.VerseKey(key)
        for alias in targets[1:]:
            key.setText(alias)
            if key.popError()!='\x00' or not mod.hasEntry(key) or not mod.isLinked(first_key,key):
                raise AssertionError('Bridge alias is absent or not linked: '+alias)
            if entry(alias)!=value:raise AssertionError('Bridge alias entry mismatch: '+alias)
    bodies,compiled_notes,compiled_titles=compiled_chapter(entries)
    for source_ref,content in expected.items():
        target=canonical_unit(source_ref).split()[0]
        if bodies.get(target,'')!=content:raise AssertionError('SWORD text mismatch: '+source_ref)
    source_notes=[node for node in dom.iter() if suffix(node)=='note']
    source_titles=[node for node in dom if suffix(node) in HEADING_ROLES or
                   set(node.get('class','').split())&{'d','q','q1','q2','q3','q4','qc','qr'}
                   and not any(suffix(child)=='verse' for child in node.iter()) and normalized(''.join(node.itertext()))]
    if len(compiled_notes)!=len(source_notes):raise AssertionError('Note count mismatch')
    for source_note,compiled_note in zip(source_notes,compiled_notes,strict=True):
        cleaned=deepcopy(source_note);locators=[node for node in source_note.iter() if suffix(node)=='fr']
        for child in list(cleaned.iterdescendants()):
            if suffix(child) in {'label','fr'} and child.getparent() is not None:remove(child)
        if normalized(''.join(cleaned.itertext()))!=normalized(''.join(compiled_note.itertext())):
            raise AssertionError('Note body mismatch')
        expected_locator=normalized(''.join(locators[0].itertext())) if len(locators)==1 else ''
        if len(locators)>1 or expected_locator!=normalized(compiled_note.get('n') or ''):
            raise AssertionError('Note locator mismatch: '+reference)
    if [heading_text(node,True) for node in source_titles]!=[heading_text(node) for node in compiled_titles]:
        raise AssertionError('Heading text/order mismatch')
    return dict(reference=reference,verses_compared=len(expected),notes_preserved=len(compiled_notes),
                bridge_units=sum('+' in ref for ref in expected),note_bodies_and_locators_verified=True,
                headings_preserved=len(compiled_titles),source_sha256=hashlib.sha256(raw).hexdigest(),
                comparison='NFC and whitespace normalized; punctuation/case/words unchanged',result='pass')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--osis', type=Path, required=True)
    p.add_argument('--module-root', type=Path, required=True)
    p.add_argument('--module-name', required=True)
    p.add_argument('--reference', required=True)
    args = p.parse_args()
    print(json.dumps(check(args.source, args.osis, args.module_root, args.module_name, args.reference), indent=2))


if __name__ == '__main__':
    main()
