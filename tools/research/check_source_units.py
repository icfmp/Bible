"""Independent source-DOM oracle for sparse native section/unit adapters.

No source text is emitted or retained outside the caller's private input. The
oracle groups DOM wrappers, not semantic converter nodes, and compares original
source identities, presentation order, text, headings and complete note bodies.
"""
from copy import deepcopy
from .check_yves_fidelity import suffix,remove,normalized,heading_text,HEADING_ROLES,canonical_unit


def audit(archive,edition,reader):
    from lxml import html
    from bible.youversion_source import archive_chapters
    from bible.youversion_content import native_chapter,project
    result=dict(chapters=0,introductions=0,physical_files=0,units=0,notes=0,headings=0,
                all_application_verses_verified=True,source_unit_order_verified=True,
                note_bodies_and_locators_verified=True,headings_verified=True)
    pending=None

    def check(value):
        reference=value['reference'];loaded=reader.chapter(reference)
        expected=value['units'];actual=loaded.display_units
        if len(expected)!=len(actual):raise AssertionError('Source unit count differs: '+reference)
        for (members,fragments),unit in zip(expected,actual,strict=True):
            if members!=unit.members:raise AssertionError('Source unit identities/order differ: '+reference)
            if normalized(' '.join(fragments))!=normalized(unit.text):
                raise AssertionError('Source unit body differs: '+reference)
        # Decode the actual physical index in order, independently of structured
        # rendering. Include unnumbered chapter prose/notes and spanning markup.
        native=reader._native_chapter(reader.addresses.native_chapter(reference)+'.1')
        key=reader.sword.VerseKey();key.setVersificationSystem(reader.versification)
        key.setIntros(True);key.setAutoNormalize(False)
        tree=native_chapter(reader.module,key,native.reference,[ref for ref,_ in native.unique_verses()])
        _,notes,titles=project(tree)
        if [(n.text,n.locator) for n in notes]!=value['notes']:
            raise AssertionError('Independent note bodies/locators differ: '+reference)
        if list(titles)!=value['headings']:raise AssertionError('Independent heading order/text differs: '+reference)
        result['chapters']+=1;result['units']+=len(actual);result['notes']+=len(notes);result['headings']+=len(titles)

    for source in archive_chapters(archive,edition,complete=True):
        result['physical_files']+=1;original=source['reference']
        dom=html.fromstring(source['source_html']).xpath('//div[@data-usfm=$r]',r=original)[0]
        if '.INTRO' in original:
            if pending:check(pending);pending=None
            from .check_yves_fidelity import canonical_chapter
            raw=reader.introduction(canonical_chapter(original.split('.')[0]+'.1').split('.')[0])
            def flow(node,source_html=False):
                name=node.tag.rsplit('}',1)[-1]
                if source_html and suffix(node)=='label':return ''
                content=node.text or ''
                for child in node:content+=flow(child,source_html)+(child.tail or '')
                return content+('\n' if name in {'div','p','title','l','item','table','tr','td','th','row','cell','br','lb'} else '')
            if raw is None or normalized(flow(dom,True))!=normalized(flow(raw)):
                raise AssertionError('Independent introduction differs: '+original)
            result['introductions']+=1;continue
        from .check_yves_fidelity import canonical_chapter
        public=reader.addresses.source_chapter(reader.addresses.native_chapter(canonical_chapter(original)))
        if pending and pending['reference']!=public:check(pending);pending=None
        if pending is None:pending=dict(reference=public,units=[],notes=[],headings=[])
        for node in dom.iter():
            if suffix(node)=='verse':
                # Public references are taken from the actual DOM, retaining
                # section IDs where that book has overlapping sections. Never
                # derive verse IDs from the adapter's native unit positions.
                source_members=canonical_unit(node.get('data-usfm')).split()
                members=tuple(public+'.'+ref.rsplit('.',1)[1] for ref in source_members)
                clean=deepcopy(node)
                for child in list(clean.iterdescendants()):
                    if suffix(child) in {'note','label'} and child.getparent() is not None:remove(child)
                body=''.join(clean.itertext())
                if not pending['units'] or pending['units'][-1][0]!=members:pending['units'].append((members,[]))
                pending['units'][-1][1].append(body)
            elif suffix(node)=='note':
                clean=deepcopy(node);locators=[child for child in node.iter() if suffix(child)=='fr']
                for child in list(clean.iterdescendants()):
                    if suffix(child) in {'label','fr'} and child.getparent() is not None:remove(child)
                if len(locators)>1:raise AssertionError('Multiple note locators: '+original)
                locator=normalized(''.join(locators[0].itertext())) if locators else ''
                pending['notes'].append((normalized(''.join(clean.itertext())),locator))
        source_titles=[node for node in dom if suffix(node) in HEADING_ROLES or
                       set(node.get('class','').split())&{'d','q','q1','q2','q3','q4','qc','qr'}
                       and not any(suffix(child)=='verse' for child in node.iter()) and normalized(''.join(node.itertext()))]
        pending['headings'].extend(heading_text(node,True) for node in source_titles)
    if pending:check(pending)
    return result
