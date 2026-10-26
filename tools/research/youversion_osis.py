"""Experimental, local HTML -> semantic blocks -> OSIS proof for issue #26.

Not an application provider or a full-edition downloader. Requires lxml.
No generated scripture, credentials, modules or source HTML belong in Git.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from lxml import etree as E, html

NS = 'http://www.bibletechnologies.net/2003/OSIS/namespace'
BOOK_CODES = '''GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV'''.split()
OSIS_BOOKS = '''Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth Job Ps Prov Eccl Song Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal Matt Mark Luke John Acts Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev'''.split()
BOOKS = dict(zip(BOOK_CODES, OSIS_BOOKS, strict=True))
INLINE = {'content', 'verse', 'label', 'note', 'body', 'fr', 'ft', 'fqa',
          'ref', 'qt', 'wj', 'w', 'heading', 'it', 'bd', 'bdit', 'sc'}
BLOCK = {'p', 'ip', 'd', 'b', 'ie', 'imt', 's1', 'ms1', 'r', 'q1', 'q2', 'q3', 'q4'}


class Unsupported(ValueError):
    pass


def kind(element):
    classes = element.get('class', '').split()
    if len(classes) != 1:
        raise Unsupported(f'Expected one semantic class: {element.tag}, {classes}')
    return classes[0].rsplit('_', 1)[-1]


def osis_ref(source):
    """Only explicit single refs or explicit plus-joined refs; no guessed ranges."""
    out = []
    for item in source.split('+'):
        m = re.fullmatch(r'([A-Z0-9]{3})\.([1-9][0-9]*)(?:\.([1-9][0-9]*))?', item)
        if not m or m[1] not in BOOKS:
            raise Unsupported(f'Unsupported source reference: {source}')
        out.append('.'.join(x for x in (BOOKS[m[1]], m[2], m[3]) if x))
    return ' '.join(out)


@dataclass
class Node:
    kind: str
    attrs: dict[str, str]
    parts: list  # Ordered strings and Nodes, including child tails.


@dataclass
class Document:
    reference: str
    blocks: list[Node]
    source_sha256: str
    source_url: str
    attribution: str


def _node(el):
    k = kind(el)
    if k not in INLINE | BLOCK:
        raise Unsupported(f'Unsupported semantic element: {k}')
    if el.tag not in {'span', 'div'}:
        raise Unsupported(f'Unsupported tag: {el.tag}')
    unexpected = set(el.attrib) - {'class', 'data-usfm'}
    if unexpected:
        raise Unsupported(f'Unreviewed attributes: {sorted(unexpected)}')
    parts = [el.text] if el.text else []
    for child in el:
        parts.append(_node(child))
        if child.tail:
            parts.append(child.tail)
    return Node(k, dict(el.attrib), parts)


def read_document(raw: bytes, reference: str, *, source_url: str,
                  attribution: str) -> Document:
    if not attribution.strip():
        raise Unsupported('Explicit source attribution is required')
    if not re.fullmatch(r'[A-Z0-9]{3}\.(?:[1-9][0-9]*|INTRO1)', reference):
        raise Unsupported('Proof accepts one chapter or INTRO1 only')
    tree = html.fromstring(raw.decode('utf-8', errors='strict'))
    roots = tree.xpath('//div[@data-usfm=$ref]', ref=reference)
    if len(roots) != 1 or kind(roots[0]) != 'chapter':
        raise Unsupported('Expected one exact chapter container')
    root = roots[0]
    if root.text and root.text.strip():
        raise Unsupported('Unclassified text before first block')
    blocks = []
    for el in root:
        if el.tail and el.tail.strip():
            raise Unsupported('Unclassified text after block')
        if kind(el) == 'label':
            continue  # Generated chapter display number, not scripture text.
        if kind(el) not in BLOCK:
            raise Unsupported(f'Unsupported block: {kind(el)}')
        blocks.append(_node(el))
    return Document(reference, blocks, hashlib.sha256(raw).hexdigest(),
                    source_url, attribution)


def element(parent, tag, **attrs):
    return E.SubElement(parent, f'{{{NS}}}{tag}', {k: str(v) for k, v in attrs.items()})


def text(parent, value):
    if len(parent):
        parent[-1].tail = (parent[-1].tail or '') + value
    else:
        parent.text = (parent.text or '') + value


def plain(node):
    return ''.join(p if isinstance(p, str) else plain(p) for p in node.parts)


class Writer:
    def __init__(self, parent, chapter):
        self.chapter = parent
        self.source_chapter = chapter
        self.active = None
        self.seen = []
        self.fragments = Counter()
        self.note_count = 0

    def close(self, parent):
        if self.active:
            element(parent, 'verse', eID=self.active)
            self.active = None

    def parts(self, parts, parent, in_note=False):
        for part in parts:
            if isinstance(part, str):
                text(parent, part)
            else:
                self.inline(part, parent, in_note)

    def inline(self, node, parent, in_note=False):
        k = node.kind
        if k == 'label':
            return
        if k == 'verse':
            if in_note:
                raise Unsupported('Verse wrapper inside a footnote')
            source = node.attrs.get('data-usfm', '')
            if not re.fullmatch(re.escape(self.source_chapter) + r'\.[1-9][0-9]*', source):
                raise Unsupported(f'Unreviewed range/cross-chapter verse: {source}')
            ref = osis_ref(source)
            self.fragments[ref] += 1
            if self.active != ref:
                if ref in self.seen:
                    # Source includes empty continuation wrappers before headings.
                    if not plain(node).strip():
                        return
                    raise Unsupported(f'Non-contiguous verse fragments: {ref}')
                if self.seen and int(ref.rsplit('.', 1)[1]) <= int(self.seen[-1].rsplit('.', 1)[1]):
                    raise Unsupported('Out-of-order verse IDs')
                self.close(parent)
                element(parent, 'verse', osisID=ref, sID=ref, n=source.rsplit('.', 1)[1])
                self.active = ref
                self.seen.append(ref)
            self.parts(node.parts, parent)
            return
        if k == 'note':
            if in_note or not self.active:
                raise Unsupported('Nested or unanchored note')
            self.note_count += 1
            foot = element(parent, 'note', type='explanation', osisRef=self.active,
                           osisID=f'{self.active}!note{self.note_count}')
            self.parts(node.parts, foot, True)
            return
        if k == 'fr':
            if not in_note:
                raise Unsupported('Note reference outside a note')
            parent.set('n', plain(node).strip())
            # Keep the printed note locator separately, not in scripture/body text.
            return
        if k == 'ref':
            target = node.attrs.get('data-usfm')
            if not target:
                raise Unsupported('Reference without explicit target')
            self.parts(node.parts, element(parent, 'reference', osisRef=osis_ref(target)), in_note)
            return
        styles = {'fqa': 'italic', 'it': 'italic', 'bd': 'bold',
                  'bdit': 'x-bold-italic', 'sc': 'small-caps'}
        if k in styles:
            self.parts(node.parts, element(parent, 'hi', type=styles[k]), in_note)
        elif k == 'wj':
            self.parts(node.parts, element(parent, 'q', who='Jesus', marker=''), in_note)
        elif k == 'qt':
            self.parts(node.parts, element(parent, 'seg', type='x-source-quotation'), in_note)
        elif k == 'w':
            # Source w has no lemma/morphology in this sample. Never invent it.
            self.parts(node.parts, element(parent, 'seg', type='x-source-word'), in_note)
        elif k in {'content', 'body', 'ft', 'heading'}:
            self.parts(node.parts, parent, in_note)
        else:
            raise Unsupported(f'Unexpected inline kind: {k}')

    def blocks(self, blocks, parent):
        lg = None
        for block in blocks:
            k = block.kind
            if k not in {'q1', 'q2', 'q3', 'q4'}:
                lg = None
            if k in {'s1', 'ms1', 'imt'}:
                self.close(parent)
                target = element(parent, 'title', type='x-section',
                                 level='1' if k in {'ms1', 'imt'} else '2')
            elif k == 'r':
                self.close(parent)
                target = element(parent, 'title', type='parallel')
            elif k in {'p', 'ip'}:
                target = element(parent, 'p')
            elif k == 'd':
                # Psalm superscription includes an actual numbered verse here.
                target = element(parent, 'p', type='x-superscription')
            elif k in {'q1', 'q2', 'q3', 'q4'}:
                if lg is None:
                    lg = element(parent, 'lg')
                target = element(lg, 'l', level=k[1:])
            elif k in {'b', 'ie'}:
                if plain(block).strip():
                    raise Unsupported(f'Nonempty layout/end marker: {k}')
                if k == 'b':
                    element(parent, 'milestone', type='x-source-blank-line')
                continue
            else:
                raise Unsupported(f'Unsupported block kind: {k}')
            self.parts(block.parts, target)
            text(target, '\n')  # Explicit semantic block boundary, not pretty-print.
        self.close(parent)


def convert(doc: Document):
    root = E.Element(f'{{{NS}}}osis', nsmap={None: NS})
    body = element(root, 'osisText', osisIDWork='BDSProof', osisRefWork='Bible',
                   **{'{http://www.w3.org/XML/1998/namespace}lang': 'fr'})
    header = element(body, 'header')
    work = element(header, 'work', osisWork='BDSProof')
    element(work, 'title').text = 'BDS limited conversion research sample — not a complete Bible'
    element(work, 'identifier', type='URI').text = doc.source_url
    element(work, 'rights').text = doc.attribution
    element(work, 'refSystem').text = 'Bible'  # No unverified edition-wide versification claim.
    book = element(body, 'div', type='book', osisID=BOOKS[doc.reference.split('.')[0]])
    intro = doc.reference.endswith('.INTRO1')
    container = element(book, 'div', type='introduction') if intro else element(book, 'chapter', osisID=osis_ref(doc.reference))
    writer = Writer(container, doc.reference)
    writer.blocks(doc.blocks, container)
    if not intro and not writer.seen:
        raise Unsupported('Chapter contains no verses')
    report = dict(reference=doc.reference, source_url=doc.source_url,
                  source_sha256=doc.source_sha256, verse_ids=writer.seen,
                  verse_fragments=dict(writer.fragments), note_count=writer.note_count,
                  blocks=dict(Counter(b.kind for b in doc.blocks)),
                  scope='limited research sample; edition-wide versification unverified')
    return E.tostring(root, encoding='UTF-8', xml_declaration=True), report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('html', type=Path)
    p.add_argument('--reference', required=True)
    p.add_argument('--source-url', required=True)
    p.add_argument('--attribution-file', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    doc = read_document(args.html.read_bytes(), args.reference,
                        source_url=args.source_url,
                        attribution=args.attribution_file.read_text(encoding='utf-8'))
    xml, report = convert(doc)
    args.output.write_bytes(xml)
    args.output.with_suffix('.report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in {'verse_ids', 'verse_fragments'}}))


if __name__ == '__main__':
    main()
