"""Strict OSIS projections shared by installation checks and editorial views.

Native entries can contain markup spanning verse boundaries. Parse complete
chapters, with processing instructions retaining physical entry identities.
"""
from collections import defaultdict
from dataclasses import dataclass
import re
import unicodedata
from xml.etree import ElementTree as E


def normalized(value):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', value)).strip()


def tag(node):
    return node.tag.rsplit('}', 1)[-1] if isinstance(node.tag, str) else ''


def parse(raw):
    # No entities, external references or DTDs in the accepted OSIS subset.
    if '<!DOCTYPE' in raw or '<!ENTITY' in raw:
        raise ValueError('Unsupported OSIS declaration')
    parser = E.XMLParser(target=E.TreeBuilder(insert_pis=True))
    return E.fromstring(raw, parser=parser)


@dataclass(frozen=True)
class EditorialNote:
    reference: str
    locator: str
    kind: str
    text: str


def project(root, *, milestones=False, preverse=None, normalize=True, editorial=True):
    bodies = defaultdict(list)
    notes, titles = [], []
    active = preverse
    def visit(node):
        nonlocal active
        if node.tag is E.ProcessingInstruction:
            target, _, reference = (node.text or '').partition(' ')
            if target == 'source-unit':active = reference;bodies.setdefault(active,[])
            return
        name = tag(node)
        if name == 'header':return
        if name == 'verse' and milestones:
            if node.get('sID'):active = node.get('osisID', '').split()[0];bodies.setdefault(active,[])
            elif node.get('eID'):active = None
            return
        if name == 'note':
            if not editorial:return
            notes.append(EditorialNote(node.get('osisRef') or active or '',
                node.get('n', ''), node.get('type', ''), normalized(''.join(node.itertext()))))
            return
        if name == 'title':
            if not editorial:return
            # Preserve notes nested inside headings, without mixing them into
            # the heading or the biblical body.
            parts = []
            def heading(el):
                if tag(el) == 'note':visit(el);return
                if el.text:parts.append(el.text)
                for child in el:
                    heading(child)
                    if child.tail:parts.append(child.tail)
            heading(node);titles.append(normalized(''.join(parts)));return
        if active and node.text:bodies[active].append(node.text)
        for child in node:
            visit(child)
            if active and child.tail:bodies[active].append(child.tail)
    visit(root)
    projected={ref:(normalized(''.join(parts)) if normalize else ''.join(parts)) for ref,parts in bodies.items()}
    projected={ref:value for ref,value in projected.items() if value or not ref.endswith('.0')}
    return projected, tuple(notes), tuple(titles)


def semantic_roles(root):
    """Preserve explicit inline styling, quotation/reference and list levels."""
    accepted={'hi','divineName','transChange','catchWord','name','q','reference','foreign','l','item','table','row','cell'}
    result=[]
    for node in root.iter():
        name=tag(node)
        # osis2mod turns enclosing poetry/quote elements into start/end
        # milestones. An end marker does not introduce another semantic role.
        if node.get('eID'):continue
        if name in accepted or name=='seg' and node.get('type','').startswith(('x-source-','x-transliteration')):
            attrs=tuple(sorted((key,value) for key,value in node.attrib.items()
                               if key in ('type','who','marker','level','osisRef','role')))
            result.append((name,attrs))
    return result


def native_chapter(module, key, chapter, references):
    def entry(ref):
        key.setText(ref);module.setKey(key)
        value = module.getRawEntry()
        return value if isinstance(value,str) else value.c_str()
    entries = [(chapter+'.0', entry(chapter+'.0'))]
    entries.extend((ref,entry(ref)) for ref in references)
    return parse('<root>'+''.join('<?source-unit '+ref+'?>'+raw for ref,raw in entries)+'</root>')
