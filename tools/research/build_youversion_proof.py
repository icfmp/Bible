"""Build and verify ONLY three previously acquired local samples for issue #26.

No network fetching, full-Bible download or application installation. Run from
the repository root with lxml, SWORD bindings and osis2mod 1.9.0 available.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess

from lxml import etree as E, html

from tools.research.youversion_osis import NS, convert, read_document
from tools.research.check_youversion_osis import check, dom_verses, normalized


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def schema_at(directory):
    class Local(E.Resolver):
        def resolve(self, url, public, context):
            if url == 'http://www.w3.org/2001/xml.xsd':
                return self.resolve_filename(str(directory/'xml.xsd'), context)
    parser = E.XMLParser(no_network=True)
    parser.resolvers.add(Local())
    return E.XMLSchema(E.parse(str(directory/'osisCore.2.1.1.xsd'), parser))


def verify_intro(source, module_root):
    import Sword
    dom = html.fromstring(source.read_bytes().decode('utf-8'))
    root = dom.xpath('//div[@data-usfm="JHN.INTRO1"]')[0]
    expected = normalized(' '.join(''.join(x.itertext()) for x in root))
    manager = Sword.SWMgr(str(module_root))
    module = manager.getModule('ProofJohn')
    key = Sword.VerseKey()
    key.setIntros(True)
    key.setAutoNormalize(False)
    key.setText('John.0.0')
    if not module.hasEntry(key):
        raise AssertionError('Compiled book introduction is missing')
    module.setKey(key)
    content = E.fromstring(('<root>'+str(module.getRawEntry())+'</root>').encode())
    actual = normalized(' '.join(content.itertext()))
    if actual != expected:
        raise AssertionError(f'Introduction fidelity mismatch: {len(expected)}/{len(actual)} chars')
    return dict(reference='JHN.INTRO1', source_sha256=digest(source),
                full_intro_text_and_title_verified=True, result='pass')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--samples', type=Path, required=True,
                   help='JHN.1.html, PSA.3.html, JHN.INTRO1.html and attribution.txt')
    p.add_argument('--schema-dir', type=Path, required=True,
                   help='Official osisCore.2.1.1.xsd and W3C xml.xsd')
    p.add_argument('--osis2mod', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True,
                   help='NEW disposable directory outside the repository')
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    attribution = (a.samples/'attribution.txt').read_text(encoding='utf-8')
    schema = schema_at(a.schema_dir)
    ns = {'o': NS}
    roots = {}
    reports = {}
    for ref in ['JHN.1', 'PSA.3', 'JHN.INTRO1']:
        doc = read_document((a.samples/(ref+'.html')).read_bytes(), ref,
                            source_url='https://www.bible.com/fr/bible/21/'+ref+'.BDS',
                            attribution=attribution)
        xml, report = convert(doc)
        tree = E.fromstring(xml)
        schema.assertValid(tree)
        (a.output/(ref+'.xml')).write_bytes(xml)
        roots[ref], reports[ref] = tree, report
    john = roots['JHN.1']
    john.xpath('//o:div[@type="book"]', namespaces=ns)[0].insert(
        0, deepcopy(roots['JHN.INTRO1'].xpath('//o:div[@type="introduction"]', namespaces=ns)[0]))
    schema.assertValid(john)
    (a.output/'John-with-intro.xml').write_bytes(E.tostring(john, encoding='UTF-8', xml_declaration=True))
    results = []
    for name, filename, ref, system in [
            ('ProofJohn', 'John-with-intro.xml', 'JHN.1', 'KJV'),
            ('ProofPsalms', 'PSA.3.xml', 'PSA.3', 'Segond')]:
        module_root = a.output/name
        data = module_root/'modules'/'texts'/'rawtext'/name.lower()
        data.mkdir(parents=True)
        run = subprocess.run([str(a.osis2mod.resolve()), str(data.resolve()),
                              str((a.output/filename).resolve()), '-v', system],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             check=True)
        log = run.stdout.decode('utf-8', errors='replace')
        (a.output/(name+'.compile.log')).write_text(log, encoding='utf-8')
        if re.search(r'\b(?:ERROR|WARNING)\b', log):
            raise AssertionError('Compiler diagnostic requires review; see private log')
        (module_root/'mods.d').mkdir()
        (module_root/'mods.d'/(name.lower()+'.conf')).write_text(
            f'[{name}]\nDataPath=./modules/texts/rawtext/{name.lower()}/\n'
            f'ModDrv=RawText\nSourceType=OSIS\nEncoding=UTF-8\nLang=fr\n'
            f'Versification={system}\nDescription=Limited local BDS research sample\n'
            'GlobalOptionFilter=OSISFootnotes\nGlobalOptionFilter=OSISHeadings\n'
            'GlobalOptionFilter=OSISRedLetterWords\n'
            'DistributionLicense=Copyrighted; local research only; no redistribution\n'
            'Copyright='+attribution.replace('\n', ' ')+'\n', encoding='utf-8')
        results.append(check(a.samples/(ref+'.html'), a.output/(ref+'.xml'),
                             module_root, name, ref))
    results.append(verify_intro(a.samples/'JHN.INTRO1.html', a.output/'ProofJohn'))
    # Exercise the existing application's non-GUI reader, without editing it.
    from collections import Counter
    from bible.sword_provider import Reader
    app_results = []
    for name, ref, chapter in [('ProofJohn', 'JHN.1', 'John.1'),
                               ('ProofPsalms', 'PSA.3', 'Ps.3')]:
        reader = Reader(a.output/name, name)
        loaded = reader.chapter(chapter)
        expected, _ = dom_verses((a.samples/(ref+'.html')).read_bytes(), ref)
        actual = {key.rsplit('.', 1)[1]: normalized(value) for key, value in loaded.verses}
        for key, value in expected.items():
            if actual.get(key.rsplit('.', 1)[1]) != value:
                raise AssertionError(f'Application reader fidelity mismatch: {key}')
        structured = reader.structured_chapter(loaded)
        kinds = Counter(s.kind for parts in structured.values() for s in parts)
        app_results.append(dict(reference=ref, verses=len(loaded.verses),
                                segment_kinds=dict(kinds), result='pass'))
    summary = dict(
        status='limited local proof passed; not an app feature or complete edition',
        schema_validation='3 individual documents plus combined John introduction/chapter',
        schema_sha256=digest(a.schema_dir/'osisCore.2.1.1.xsd'),
        xml_namespace_schema_sha256=digest(a.schema_dir/'xml.xsd'),
        compiler_sha256=digest(a.osis2mod),
        tested_sword='1.9.0; Ubuntu 1.9.0+dfsg-6build2; not the application Flatpak build',
        versification_scope='KJV for John 1 only; Segond for Psalm 3 only; no edition-wide equivalence asserted',
        application_reader_results=app_results,
        documents=reports, results=results)
    (a.output/'verification.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'documents'}, indent=2))


if __name__ == '__main__':
    main()
