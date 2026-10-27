"""Local semantic document → OSIS, shared with the #26 YVES research adapter.

Writer and explicit book map adapted from our draft PR #59, commit
3a535332f59fd5b4f45dc8f59ccd0f9e7de8d331. Uses only the standard library;
no website scraper, network acquisition or resource installation.
Unknown numbering/structures fail explicitly; no edition-wide alignment claim.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
import re
from xml.etree import ElementTree as E

NS = 'http://www.bibletechnologies.net/2003/OSIS/namespace'
E.register_namespace('', NS)
BOOK_CODES = '''GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV'''.split()
OSIS_BOOKS = '''Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth Job Ps Prov Eccl Song Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal Matt Mark Luke John Acts Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev'''.split()
BOOKS = dict(zip(BOOK_CODES, OSIS_BOOKS, strict=True))
INLINE = {'content', 'verse', 'label', 'note', 'body', 'fr', 'ft', 'fqa',
          'fq', 'fv', 'ord', 'tl', 'bk', 'em',
          'ref', 'qt', 'wj', 'w', 'heading', 'it', 'bd', 'bdit', 'sc', 'add', 'nd', 'br'}
INLINE |= {'qs','ior'}
BLOCK = {'p', 'm', 'ip', 'pm', 'nb', 'd', 'b', 'ib', 'ie', 'imt',
         'li1', 'li2', 'ili1', 'ili2',
         's1', 's2', 's3', 'ms1', 'r', 'q1', 'q2', 'q3', 'q4'}
BLOCK |= {'s','ms','ms2','mr','imt1','imt2','imt3','is1','ipi','io1','io2',
          'q','qa','qr','qc','pi','pi1','pc','lf','iex','table','row','cell'}


class Unsupported(ValueError):
    pass


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
    work_id: str = "YvesResearch"
    title: str = "Local conversion research; not a complete Bible"
    language: str = "und"

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
        self.active_sid = None
        self.active_source = None
        self.last_verse = 0
        self.seen = []
        self.fragments = Counter()
        self.note_count = 0
        self.note_context = (BOOKS[chapter.split('.')[0]] if '.INTRO' in chapter else None)

    def close(self, parent):
        if self.active:
            element(parent, 'verse', eID=self.active_sid)
            self.active = None
            self.active_sid = None
            self.active_source = None

    def verse_ids(self, source):
        # Plus-joined identifiers explicitly enumerate a source verse bridge.
        # Do not invent omitted verses, expand suffixes, or cross chapters.
        items = source.split('+')
        pattern = re.escape(self.source_chapter) + r'\.([1-9][0-9]*)'
        matches = [re.fullmatch(pattern, item) for item in items]
        if not all(matches):
            raise Unsupported(f'Unreviewed range/cross-chapter verse: {source}')
        numbers = [int(match[1]) for match in matches]
        if numbers != sorted(set(numbers)):
            raise Unsupported('Duplicate or out-of-order bridge identifiers')
        return osis_ref(source), numbers

    @staticmethod
    def first_verse(parts):
        def meaningful(node):
            if isinstance(node, str):return bool(node.strip())
            if node.kind == 'label':return False
            if node.kind == 'note':return True
            return any(meaningful(part) for part in node.parts)
        for node in parts:
            if isinstance(node, str):continue
            if node.kind == 'verse':
                if meaningful(node):return node.attrs.get('data-usfm', '')
            else:
                found=Writer.first_verse(node.parts)
                if found:return found
        return None

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
            ref,numbers = self.verse_ids(source)
            self.fragments[ref] += 1
            if self.active != ref:
                if ref in self.seen:
                    # Source includes empty continuation wrappers before headings.
                    if not plain(node).strip():
                        return
                    raise Unsupported(f'Non-contiguous verse fragments: {ref}')
                if numbers[0] <= self.last_verse:
                    raise Unsupported('Out-of-order verse IDs')
                self.close(parent)
                label=next((plain(part).strip() for part in node.parts
                            if isinstance(part,Node) and part.kind=='label'),None)
                self.active_sid=ref.split()[0]
                element(parent, 'verse', osisID=ref, sID=self.active_sid,
                        n=label or '+'.join(str(n) for n in numbers))
                self.active = ref
                self.active_source = source
                self.last_verse = numbers[-1]
                self.seen.append(ref)
            self.parts(node.parts, parent)
            return
        if k == 'note':
            anchor=self.note_context or self.active
            if in_note or not anchor:
                raise Unsupported('Nested or unanchored note')
            self.note_count += 1
            foot = element(parent, 'note', type=node.attrs.get('_note_type', 'explanation'), osisRef=anchor,
                           osisID=f'{anchor.split()[0]}!note{self.note_count}')
            self.parts(node.parts, foot, True)
            return
        if k == 'fr':
            if not in_note:
                raise Unsupported('Note reference outside a note')
            parent.set('n', plain(node).strip())
            # Keep the printed note locator separately, not in scripture/body text.
            return
        if k in {'fq','fv'}:
            if not in_note:raise Unsupported('Footnote-only content outside a note')
            target=(element(parent,'catchWord') if k=='fq'
                    else element(parent,'hi',type='super'))
            self.parts(node.parts,target,True)
            return
        if k == 'ref':
            target = node.attrs.get('data-usfm')
            if not target:
                raise Unsupported('Reference without explicit target')
            self.parts(node.parts, element(parent, 'reference', osisRef=osis_ref(target)), in_note)
            return
        if k == 'br':
            element(parent, 'lb')
            return
        if k in {'add', 'nd'}:
            target = element(parent, 'transChange', type='added') if k == 'add' else element(parent, 'divineName')
            self.parts(node.parts, target, in_note)
            return
        styles = {'fqa': 'italic', 'it': 'italic', 'bd': 'bold', 'em': 'emphasis', 'ord': 'super',
                  'bdit': 'x-bold-italic', 'sc': 'small-caps'}
        if k in styles:
            self.parts(node.parts, element(parent, 'hi', type=styles[k]), in_note)
        elif k == 'wj':
            self.parts(node.parts, element(parent, 'q', who='Jesus', marker=''), in_note)
        elif k == 'qt':
            self.parts(node.parts, element(parent, 'seg', type='x-source-quotation'), in_note)
        elif k == 'tl':
            # Source identifies foreign/transliterated words, but no language.
            self.parts(node.parts,element(parent,'seg',type='x-transliteration'),in_note)
        elif k == 'bk':
            self.parts(node.parts,element(parent,'name',type='x-book-title'),in_note)
        elif k == 'w':
            # Source w has no lemma/morphology in this sample. Never invent it.
            self.parts(node.parts, element(parent, 'seg', type='x-source-word'), in_note)
        elif k in {'qs','ior'}:
            self.parts(node.parts,element(parent,'seg',type='x-selah' if k=='qs' else 'x-introduction-outline-reference'),in_note)
        elif k in {'content', 'body', 'ft', 'heading'}:
            self.parts(node.parts, parent, in_note)
        else:
            raise Unsupported(f'Unexpected inline kind: {k}')

    def blocks(self, blocks, parent):
        lg = None
        source_list = None
        for index,block in enumerate(blocks):
            k = {'s':'s1','ms':'ms1','q':'q1','imt':'imt1','pi':'pi1'}.get(block.kind,block.kind)
            def contains_verse(node):
                return isinstance(node,Node) and (node.kind=='verse' or any(contains_verse(child) for child in node.parts))
            if ('.INTRO' not in self.source_chapter and k in {'d','q1','q2','q3','q4','qc','qr'}
                    and not contains_verse(block) and plain(block).strip()):
                # Keep unindexed source poetry/superscriptions distinct from
                # adjacent verses. In particular Psalm acrostic headings must
                # not become the end of verse 8 or an invented verse zero.
                k='unindexed-'+k
            note_context=self.note_context
            if k not in {'q1', 'q2', 'q3', 'q4','qr','qc'}:
                lg = None
            if k not in {'li1','li2','ili1','ili2','io1','io2'}:source_list=None
            if k in {'s1', 's2', 's3', 'ms1','ms2','imt1','imt2','imt3','is1','qa'} or k.startswith('unindexed-'):
                following=self.first_verse(blocks[index+1:])
                if following != self.active_source:self.close(parent)
                if following:self.note_context=self.verse_ids(following)[0]
                target = element(parent, 'title', type='x-source-'+k if k.startswith('unindexed-') else 'x-acrostic' if k=='qa' else 'x-section',
                                 level=k[-1] if k[-1].isdigit() else '1')
            elif k in {'r','mr'}:
                following=self.first_verse(blocks[index+1:])
                if following != self.active_source:self.close(parent)
                if following:self.note_context=self.verse_ids(following)[0]
                target = element(parent, 'title', type='parallel')
            elif k in {'p', 'm', 'ip'}:
                target = element(parent, 'p')
            elif k in {'pm','nb'}:
                target=element(parent,'p',type='x-embedded' if k=='pm' else 'x-no-break')
            elif k in {'pi1','ipi','pc','lf','iex'}:
                target=element(parent,'p',type={'pi1':'x-indent-1','ipi':'x-introduction-indented',
                    'pc':'x-centered','lf':'x-list-footer','iex':'x-explanatory'}[k])
            elif k in {'li1','li2','ili1','ili2','io1','io2'}:
                if source_list is None:source_list=element(parent,'list')
                # USFM states indentation level, not a parent/child relationship.
                # Keep that level without inventing empty list items or bullets.
                target=element(source_list,'item',type=f'x-introduction-outline-{k[-1]}' if k.startswith('io') else f'x-level-{k[-1]}')
            elif k == 'd':
                # Psalm superscription includes an actual numbered verse here.
                target = element(parent, 'p', type='x-superscription')
            elif k in {'q1', 'q2', 'q3', 'q4','qr','qc'}:
                if lg is None:
                    lg = element(parent, 'lg')
                target = element(lg, 'l', level=k[1:] if k[-1].isdigit() else '1',
                                 **({'type':'x-right-aligned' if k=='qr' else 'x-centered'} if k in {'qr','qc'} else {}))
            elif k=='table':
                target=element(parent,'table')
                for row in block.parts:
                    if isinstance(row,str) and not row.strip():continue
                    if not isinstance(row,Node) or row.kind!='row':raise Unsupported('Invalid source table row')
                    output_row=element(target,'row')
                    for cell in row.parts:
                        if isinstance(cell,str) and not cell.strip():continue
                        if not isinstance(cell,Node) or cell.kind!='cell':raise Unsupported('Invalid source table cell')
                        output_cell=element(output_row,'cell',**({'role':'label'} if cell.attrs.get('_cell_header')=='true' else {}));self.parts(cell.parts,output_cell)
                        text(output_cell,'\t')
                    text(output_row,'\n')
                continue
            elif k in {'b', 'ib', 'ie'}:
                if plain(block).strip():
                    raise Unsupported(f'Nonempty layout/end marker: {k}')
                if k in {'b','ib'}:
                    element(parent, 'milestone', type='x-source-blank-line')
                continue
            else:
                raise Unsupported(f'Unsupported block kind: {k}')
            self.parts(block.parts, target)
            self.note_context=note_context
            text(target, '\n')  # Explicit semantic block boundary, not pretty-print.
        self.close(parent)


def convert(doc: Document):
    if doc.reference.split('.')[0] not in BOOKS:
        raise Unsupported('Unreviewed USFM book code')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*', doc.work_id):
        raise Unsupported('Invalid research work identifier')
    root = E.Element(f'{{{NS}}}osis')
    body = element(root, 'osisText', osisIDWork=doc.work_id, osisRefWork='Bible',
                   **{'{http://www.w3.org/XML/1998/namespace}lang': doc.language})
    header = element(body, 'header')
    work = element(header, 'work', osisWork=doc.work_id)
    element(work, 'title').text = doc.title
    element(work, 'identifier', type='URI').text = doc.source_url
    element(work, 'rights').text = doc.attribution
    element(work, 'refSystem').text = 'Bible'  # No unverified edition-wide versification claim.
    book = element(body, 'div', type='book', osisID=BOOKS[doc.reference.split('.')[0]])
    intro = bool(re.search(r'\.INTRO[1-9][0-9]*$', doc.reference))
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
