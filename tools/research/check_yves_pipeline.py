"""Exercise local synthetic YVES → OSIS → actual SWORD → offline GTK readback.

Never downloads Scripture or installs into an existing profile. This is tooling
validation, not the real-edition stage A required by #26 or a product provider.
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
import unicodedata
from xml.etree import ElementTree as E

from .semantic_osis import NS
from .test_yves_source import synthetic_archive
from .yves_source import archive_chapters, to_osis

EXPECTED = {
    'JHN.1.1': 'Premier fragment de test & ajout synthétique ; suite du test.',
    'JHN.1.3': 'NOM DE TEST — paroles synthétiques שָׁלוֹם. Fin du test.',
    'PSA.3.9': 'Numérotation de test uniquement.',
}
NOTE = 'Note de test, référence Ps 3:9.'
INTRO = 'Introduction de test Document synthétique, aucun texte biblique.'


def normalized(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text)).strip()


def value(sword_string):
    return sword_string if isinstance(sword_string, str) else sword_string.c_str()


def body(raw):
    tree = E.fromstring('<root>' + raw + '</root>')
    def text(node):
        if node.tag in {'note', 'title'}:
            return ''
        result = node.text or ''
        if node.tag in {'lb', 'l', 'p', 'div'}:
            result += ' '
        for child in node:
            result += text(child) + (child.tail or '')
        return result
    return normalized(text(tree)), tree


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='NEW disposable private directory')
    parser.add_argument('--compiler', type=Path, default=Path('/app/bin/osis2mod'))
    parser.add_argument('--gtk', action='store_true')
    parser.add_argument('--require-packaged', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    if args.require_packaged:
        assert str(args.compiler) == '/app/bin/osis2mod' and args.compiler.is_file()
    started = time.monotonic()
    archive = args.output/'synthetic.zip'
    edition = synthetic_archive(archive)
    chapters = list(archive_chapters(archive, edition, complete=True))
    trees = {}
    for chapter in chapters:
        raw, report = to_osis(chapter, edition)
        trees[chapter['reference']] = E.fromstring(raw)
        (args.output/(chapter['reference']+'.osis.xml')).write_bytes(raw)
    ns = {'o': NS}
    john = trees['JHN.1']
    john.find('.//o:div[@type="book"]', ns).insert(
        0, deepcopy(trees['JHN.INTRO1'].find('.//o:div[@type="introduction"]', ns)))
    (args.output/'john-with-intro.osis.xml').write_bytes(E.tostring(john, encoding='UTF-8', xml_declaration=True))
    from bible.sword_provider import Reader
    import Sword
    if args.require_packaged:
        assert inspect.getfile(Reader).startswith('/app/')
        assert inspect.getfile(Sword).startswith('/app/')
    profile = args.output/'profile'
    translations = profile/'translations'
    results = []
    for name, filename, reference, system in [
            ('YvesSyntheticJohn', 'john-with-intro.osis.xml', 'John.1', 'KJV'),
            ('YvesSyntheticPsalm', 'PSA.3.osis.xml', 'Ps.3', 'Segond')]:
        root = translations/name
        data = root/'modules/texts/rawtext'/name.lower()
        data.mkdir(parents=True)
        run = subprocess.run([str(args.compiler), str(data), str(args.output/filename), '-v', system],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30, check=True)
        log = run.stdout.decode('utf-8', errors='strict')
        (args.output/(name+'.compile.log')).write_text(log)
        assert not re.search(r'\b(?:ERROR|WARNING)\b', log), 'Review private compiler diagnostic'
        (root/'mods.d').mkdir()
        (root/'mods.d'/(name.lower()+'.conf')).write_text(
            f'[{name}]\nDataPath=./modules/texts/rawtext/{name.lower()}/\n'
            f'ModDrv=RawText\nSourceType=OSIS\nEncoding=UTF-8\nLang=fr\nVersification={system}\n'
            'Description=SYNTHETIC YVES TOOLING TEST — NOT SCRIPTURE\n'
            'DistributionLicense=Synthetic test material\n'
            'GlobalOptionFilter=OSISFootnotes\nGlobalOptionFilter=OSISHeadings\n'
            'GlobalOptionFilter=OSISRedLetterWords\n')
        (root/'.complete').write_text('synthetic local tooling test\n')
        reader = Reader(root, name)
        chapter = reader.chapter(reference)
        expected = {key: text for key, text in EXPECTED.items() if key.startswith('JHN.' if reference=='John.1' else 'PSA.')}
        target = {reference+'.'+key.rsplit('.',1)[1]: normalized(text) for key,text in expected.items()}
        actual = {key: normalized(text) for key,text in chapter.verses}
        assert actual == target, ('Exact application readback mismatch', reference, actual)
        notes, headings = [], []
        for key in [reference+'.0', *target]:
            vk = Sword.VerseKey();vk.setVersificationSystem(system);vk.setIntros(True);vk.setAutoNormalize(False);vk.setText(key)
            reader.module.setKey(vk)
            raw = value(reader.module.getRawEntry())
            if not raw:
                continue
            text, tree = body(raw)
            if key in target:
                assert text == target[key], ('Raw entry fidelity mismatch', key)
            notes.extend(tree.findall('.//note'))
            headings.extend(tree.findall('.//title'))
        if name == 'YvesSyntheticJohn':
            assert len(notes)==1 and normalized(''.join(notes[0].itertext()))==NOTE
            assert notes[0].get('n')=='1.1'
            assert notes[0].find('.//reference').get('osisRef')=='Ps.3.9'
            assert [normalized(''.join(node.itertext())) for node in headings]==['Titre synthétique']
            key=Sword.VerseKey();key.setIntros(True);key.setAutoNormalize(False);key.setText('John.0.0');reader.module.setKey(key)
            intro=E.fromstring('<root>'+value(reader.module.getRawEntry())+'</root>')
            assert normalized(' '.join(intro.itertext()))==INTRO
            assert 'John.1.2' not in actual, 'An absent verse was manufactured'
        segments = reader.structured_chapter(chapter)
        results.append(dict(module=name, scoped_versification=system, verses_compared=len(target),
                            all_text_matches=True, notes=len(notes), headings=len(headings),
                            structure_kinds=sorted({s.kind for v in segments.values() for s in v})))
    report = dict(status='PASS_SYNTHETIC_TOOLING_ONLY', real_edition_stage_a_complete=False,
                  source_import=inspect.getfile(Reader), sword_import=inspect.getfile(Sword),
                  compiler_sha256=hashlib.sha256(args.compiler.read_bytes()).hexdigest(),
                  source_chapters=len(chapters), results=results,
                  exact_text_comparison='NFC and semantic whitespace only; no word/case/punctuation folding',
                  acquisition_network_used=False, real_bds_content_downloaded=False,
                  publication_authorized=False, existing_profile_accessed=False)
    if args.gtk:
        from bible.ui import Application, Window, Library
        from tests.test_ui import spin
        if args.require_packaged:
            assert inspect.getfile(Window).startswith('/app/')
            assert len(Path('/proc/net/route').read_text().splitlines())<=1, 'Flatpak network isolation not applied'
        app=Application();app.register();window=Window(app,Library(translations));window.present();spin()
        try:
            tab=window.active_tab
            for name,reference in [('YvesSyntheticJohn','John.1.1'),('YvesSyntheticPsalm','Ps.3.9')]:
                tab.navigate(name,reference);spin(lambda:not tab._restoring_scroll)
                buffer=tab.text.get_buffer();visible=buffer.get_text(buffer.get_start_iter(),buffer.get_end_iter(),True)
                for ref,text in EXPECTED.items():
                    if ref.startswith('JHN.' if name.endswith('John') else 'PSA.'):
                        assert normalized(text).replace(' ','') in normalized(visible).replace(' ',''), 'GTK omitted source content'
            report['gtk_offline_readback']=True
            report['gtk_source_import']=inspect.getfile(Window)
            report['gtk_note_intro_limitation']='Current reader excludes editorial note bodies from main text and has no book-introduction navigation; preservation is checked at raw SWORD level, not an editorial-notes GUI feature.'
        finally:
            window.close()
    report['elapsed_seconds']=time.monotonic()-started
    (args.output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
