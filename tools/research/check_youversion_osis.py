"""Compare local public-page samples against OSIS and a locally built SWORD module.

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
import socket
import unicodedata

from lxml import etree as E, html


def normalized(s):
    # Compiler NFC plus semantic whitespace normalization only. No case/punctuation
    # folding, translation changes, dropped superscriptions or word substitutions.
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', s)).strip()


def suffix(el):
    return el.get('class', '').rsplit('_', 1)[-1]


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
    def walk(el):
        nonlocal active
        tag = E.QName(el).localname
        if tag == 'verse':
            if el.get('sID'):
                active = el.get('sID')
            elif el.get('eID'):
                if active != el.get('eID'):
                    raise AssertionError('Unpaired verse milestones')
                active = None
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


def check(source: Path, xml: Path, root: Path, module_name: str, reference: str):
    import Sword
    # Make network use fail in this validation process; reading uses local SWMgr.
    def offline(*args, **kwargs):
        raise AssertionError('Unexpected network access in local validation')
    socket.create_connection = offline
    raw = source.read_bytes()
    expected, dom = dom_verses(raw, reference)
    xml_result = xml_verses(xml.read_bytes())
    manager = Sword.SWMgr(str(root))
    mod = manager.getModule(module_name)
    if mod is None:
        raise AssertionError('SWORD cannot discover the compiled module')
    key = Sword.VerseKey()
    key.setVersificationSystem(mod.getConfigEntry('Versification'))
    key.setAutoNormalize(False)
    key.setIntros(True)
    chapter = 'John.1' if reference == 'JHN.1' else 'Ps.3'
    compiled_notes, compiled_titles = [], []
    for source_ref, content in expected.items():
        target = chapter+'.'+source_ref.rsplit('.', 1)[1]
        if xml_result.get(target) != content:
            raise AssertionError(f'OSIS text mismatch: {source_ref}')
        key.setText(target)
        if key.popError() != '\x00' or not mod.hasEntry(key):
            raise AssertionError(f'Missing compiled verse: {target}')
        mod.setKey(key)
        entry = str(mod.getRawEntry())
        if raw_body(entry) != content:
            raise AssertionError(f'SWORD text mismatch: {source_ref}; expected length {len(content)}, got {len(raw_body(entry))}')
        parsed = E.fromstring(('<root>'+entry+'</root>').encode())
        compiled_notes.extend(parsed.xpath('.//note'))
        compiled_titles.extend(parsed.xpath('.//title'))
    # Include chapter pre-verse headings, where the compiler indexes initial titles.
    key.setText(chapter+'.0')
    mod.setKey(key)
    extra = str(mod.getRawEntry())
    if extra:
        compiled_titles = E.fromstring(('<root>'+extra+'</root>').encode()).xpath('.//title') + compiled_titles
    source_notes = [x for x in dom.iter() if suffix(x) == 'note']
    source_titles = [x for x in dom if suffix(x) in {'s1', 'ms1', 'r'}]
    if len(compiled_notes) != len(source_notes):
        raise AssertionError('Note count mismatch')
    for source_note, compiled_note in zip(source_notes, compiled_notes, strict=True):
        cleaned = deepcopy(source_note)
        locators = [x for x in source_note.iter() if suffix(x) == 'fr']
        for child in list(cleaned.iterdescendants()):
            if suffix(child) in {'label', 'fr'} and child.getparent() is not None:
                remove(child)
        if normalized(''.join(cleaned.itertext())) != normalized(''.join(compiled_note.itertext())):
            raise AssertionError('Note body mismatch')
        if len(locators) != 1 or normalized(''.join(locators[0].itertext())) != compiled_note.get('n'):
            raise AssertionError('Note locator mismatch')
    if [normalized(''.join(x.itertext())) for x in source_titles] != [normalized(''.join(x.itertext())) for x in compiled_titles]:
        raise AssertionError('Heading text/order mismatch')
    return dict(reference=reference, verses_compared=len(expected), notes_preserved=len(compiled_notes),
                note_bodies_and_locators_verified=True,
                headings_preserved=len(compiled_titles), source_sha256=hashlib.sha256(raw).hexdigest(),
                comparison='NFC and whitespace normalized; punctuation/case/words unchanged',
                result='pass')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--osis', type=Path, required=True)
    p.add_argument('--module-root', type=Path, required=True)
    p.add_argument('--module-name', required=True)
    p.add_argument('--reference', choices=['JHN.1', 'PSA.3'], required=True)
    args = p.parse_args()
    print(json.dumps(check(args.source, args.osis, args.module_root, args.module_name, args.reference), indent=2))


if __name__ == '__main__':
    main()
