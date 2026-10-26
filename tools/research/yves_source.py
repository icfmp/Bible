"""Bounded, local ZIP/YVES source adapter for #26 research.

No network, installer, HTML execution or permission inference. The byte transform
and ordered-tree contract follow the independently verified prototype in #26.
Raw HTML and unknown nodes remain source data; OSIS conversion is stricter.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
import hashlib
from html import entities
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
import stat
from urllib.parse import urljoin, urlsplit
import zipfile

from .semantic_osis import BLOCK, INLINE, Document, Node, Unsupported, convert


@dataclass(frozen=True)
class Edition:
    metadata: dict
    identifier: int
    title: str
    language: str
    attribution: str
    chapters: tuple[str, ...]
    archive_url: str | None


def _string(value, name):
    if not isinstance(value, str) or not value.strip():
        raise Unsupported(f'Missing {name}')
    return value


def read_edition(data, expected_id):
    """Read the returned index, including introductions, in source order.

    Agreement, redownload, publisher, build and vrs fields remain in metadata.
    `vrs` is a source identifier, never silently mapped to a SWORD system.
    """
    if type(expected_id) is not int or expected_id < 1 or not isinstance(data, dict):
        raise Unsupported('Invalid expected edition identity')
    if 'response' in data:
        response = data['response']
        if not isinstance(response, dict) or not isinstance(response.get('data'), dict):
            raise Unsupported('Unexpected metadata envelope')
        data = response['data']
    if type(data.get('id')) is not int or data['id'] != expected_id:
        raise Unsupported('Metadata edition identity mismatch')
    title = _string(data.get('local_title'), 'edition title')
    language = data.get('language')
    if not isinstance(language, dict):
        raise Unsupported('Missing language metadata')
    language = _string(language.get('iso_639_3'), 'language')
    if not re.fullmatch(r'[a-z]{3}', language):
        raise Unsupported('Unsupported language identifier')
    copyright = data.get('copyright_short')
    if not isinstance(copyright, dict):
        raise Unsupported('Missing edition attribution')
    attribution = _string(copyright.get('text'), 'edition attribution')
    books = data.get('books')
    if not isinstance(books, list) or not books or len(books) > 200:
        raise Unsupported('Invalid book inventory')
    chapters, seen_books = [], set()
    for book in books:
        if not isinstance(book, dict) or not re.fullmatch(r'[A-Z0-9]{3}', str(book.get('usfm', ''))):
            raise Unsupported('Invalid indexed book')
        code = book['usfm']
        if code in seen_books:
            raise Unsupported('Duplicate indexed book')
        seen_books.add(code)
        if type(book.get('text')) is not bool:
            raise Unsupported('Unknown book text availability')
        if not book['text']:
            continue
        inventory = book.get('chapters')
        if not isinstance(inventory, list) or not inventory:
            raise Unsupported('Missing text chapter inventory')
        for chapter in inventory:
            ref = chapter.get('usfm') if isinstance(chapter, dict) else None
            if not isinstance(ref, str) or not re.fullmatch(code + r'\.(?:[1-9][0-9]*|INTRO[1-9][0-9]*)', ref):
                raise Unsupported('Unexpected indexed chapter')
            canonical = chapter.get('canonical')
            if type(canonical) is not bool or canonical == ('.INTRO' in ref):
                raise Unsupported('Inconsistent chapter/introduction role')
            chapters.append(ref)
    if not chapters or len(chapters) > 10000 or len(set(chapters)) != len(chapters):
        raise Unsupported('Invalid or duplicate chapter inventory')
    offline = data.get('offline')
    archive_url = None
    if offline is not None:
        if not isinstance(offline, dict):
            raise Unsupported('Invalid offline metadata')
        raw = offline.get('url')
        if raw:
            raw = _string(raw, 'offline URL')
            archive_url = urljoin('https://nodejs.bible.com', raw)
            parsed = urlsplit(archive_url)
            if (parsed.scheme != 'https' or parsed.hostname != 'offline-bibles-cdn.youversionapi.com'
                    or parsed.netloc != parsed.hostname or parsed.fragment
                    or not re.fullmatch(fr'/bible/text/offline/{expected_id}-[0-9]+\.zip', parsed.path)):
                raise Unsupported('Unreviewed offline URL or mismatching edition')
    return Edition(data, expected_id, title, language, attribution, tuple(chapters), archive_url)


def decode_bytes(data):
    """Rotate left three, swap adjacent pairs; retain the rotated odd tail."""
    result = bytearray(((value << 3) | (value >> 5)) & 255 for value in data)
    for index in range(0, len(result) - 1, 2):
        result[index], result[index + 1] = result[index + 1], result[index]
    return bytes(result)


class TreeParser(HTMLParser):
    def __init__(self, *, max_nodes=100000, max_depth=128):
        super().__init__(convert_charrefs=False)
        self.root = {'tag': '#document', 'attrs': [], 'children': []}
        self.stack = [self.root]
        self.remaining = max_nodes
        self.max_depth = max_depth

    def append(self, node):
        self.remaining -= 1
        if self.remaining < 0:
            raise Unsupported('Chapter node limit exceeded')
        self.stack[-1]['children'].append(node)

    def handle_starttag(self, tag, attrs):
        if len({k for k, v in attrs}) != len(attrs):
            raise Unsupported('Duplicate HTML attributes')
        node = {'tag': tag, 'attrs': attrs, 'children': []}
        self.append(node)
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}:
            if len(self.stack) >= self.max_depth:
                raise Unsupported('Chapter nesting limit exceeded')
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        before = len(self.stack)
        self.handle_starttag(tag, attrs)
        if len(self.stack) != before:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if len(self.stack) == 1 or self.stack[-1]['tag'] != tag:
            raise Unsupported('Unbalanced chapter markup')
        self.stack.pop()

    def handle_data(self, value):
        self.append(value)

    def handle_comment(self, text):
        self.append({'tag': '#comment', 'text': text})

    def handle_decl(self, text):
        self.append({'tag': '#declaration', 'text': text})

    def handle_pi(self, text):
        self.append({'tag': '#pi', 'text': text})

    def handle_entityref(self, name):
        if name + ';' not in entities.html5:
            raise Unsupported('Unknown HTML entity')
        self.handle_data(entities.html5[name + ';'])

    def handle_charref(self, name):
        try:
            value = int(name[1:], 16) if name.lower().startswith('x') else int(name)
        except ValueError as error:
            raise Unsupported('Invalid HTML character reference') from error
        if value not in (9, 10, 13) and not (32 <= value <= 0xD7FF or 0xE000 <= value <= 0xFFFD or 0x10000 <= value <= 0x10FFFF):
            raise Unsupported('Invalid XML character in source')
        self.handle_data(chr(value))

    def parse(self, source):
        self.feed(source)
        self.close()
        if len(self.stack) != 1:
            raise Unsupported('Unclosed chapter markup')
        return self.root


def attributes(node):
    return dict(node.get('attrs', []))


def roles(node):
    return set((attributes(node).get('class') or '').split())


def walk(node, path=()):
    if isinstance(node, dict):
        yield node, path
        for index, child in enumerate(node.get('children', [])):
            yield from walk(child, path + (index,))


def projected_text(node):
    """Convenience projection only. The ordered tree/raw HTML are authoritative."""
    if isinstance(node, str):
        return node
    if node['tag'].startswith('#') or roles(node) & {'label', 'note', 'footnote', 'crossreference', 'cross-reference'}:
        return ''
    if node['tag'] == 'br':
        return '\n'
    return ''.join(projected_text(child) for child in node.get('children', []))


def parse_chapter(encoded, reference, edition):
    source = decode_bytes(encoded).decode('utf-8', errors='strict')
    tree = TreeParser().parse(source)
    nodes = list(walk(tree))
    versions = [(n, p) for n, p in nodes if 'version' in roles(n)]
    container_role = 'intro' if '.INTRO' in reference else 'chapter'
    chapters = [(n, p) for n, p in nodes if container_role in roles(n)]
    if len(versions) != 1 or len(chapters) != 1:
        raise Unsupported('Expected one version and chapter container')
    version, version_path = versions[0]
    chapter, chapter_path = chapters[0]
    if (attributes(version).get('data-vid') != str(edition.identifier)
            or attributes(version).get('data-iso6393') != edition.language
            or attributes(chapter).get('data-usfm') != reference
            or reference not in edition.chapters
            or chapter_path[:len(version_path)] != version_path):
        raise Unsupported('Archive content/metadata identity mismatch')
    verses = OrderedDict()
    for node, path in walk(chapter):
        if 'verse' not in roles(node):
            continue
        ref = attributes(node).get('data-usfm')
        # Preserve bridges/suffixes verbatim; a converter must review them.
        if not isinstance(ref, str) or not ref.startswith(reference + '.') or not ref[len(reference)+1:]:
            raise Unsupported('Missing or mismatching verse identity')
        entry = verses.setdefault(ref, {'reference': ref, 'fragments': []})
        entry['fragments'].append({'tree_path': list(chapter_path + path), 'text': projected_text(node)})
    for entry in verses.values():
        entry['text'] = ''.join(fragment['text'] for fragment in entry['fragments'])
    if '.INTRO' not in reference and not verses:
        raise Unsupported('Chapter contains no indexed verses')
    return dict(reference=reference, encoded_sha256=hashlib.sha256(encoded).hexdigest(),
                html_sha256=hashlib.sha256(source.encode()).hexdigest(), source_html=source,
                tree=tree, chapter_path=list(chapter_path), verses=list(verses.values()))


def archive_chapters(path, edition, *, complete=False, max_member=8*1024*1024,
                     max_total=256*1024*1024, max_entries=10000):
    """Never extract. Check all names/bounds first, then CRC-read in index order."""
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > max_entries:
            raise Unsupported('Archive entry limit exceeded')
        names, found, total = set(), {}, 0
        for info in infos:
            name = info.orig_filename
            parts = name.rstrip('/').split('/')
            mode = info.external_attr >> 16
            if (not name or name.startswith('/') or '\\' in name or '\x00' in name
                    or any(part in ('', '.', '..') or ':' in part for part in parts)
                    or name.casefold() in names or info.flag_bits & 1
                    or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise Unsupported('Unsafe, duplicate or encrypted archive member')
            names.add(name.casefold())
            total += info.file_size
            if info.file_size > max_member or total > max_total:
                raise Unsupported('Archive byte limit exceeded')
            if info.is_dir() or not name.lower().endswith('.yves'):
                continue
            member = PurePosixPath(name)
            ref = member.parent.name + '.' + member.stem
            if ref not in edition.chapters or ref in found:
                raise Unsupported('Unknown or duplicate indexed chapter')
            found[ref] = info
        if not found or complete and set(found) != set(edition.chapters):
            raise Unsupported('Empty or incomplete chapter inventory')
        for ref in edition.chapters:
            if ref in found:
                info = found[ref]
                data = archive.read(info)  # zipfile checks CRC; no filesystem extraction.
                if len(data) != info.file_size:
                    raise Unsupported('Truncated chapter')
                result = parse_chapter(data, ref, edition)
                result['member'] = info.filename
                yield result


def _semantic(node):
    if isinstance(node, str):
        return node
    if node['tag'] == '#comment':
        return None
    attrs = attributes(node)
    kinds = roles(node)
    if node['tag'] == 'br' and not attrs:
        kind = 'br'
    elif len(semantic := kinds & (BLOCK | INLINE)) == 1:
        kind = next(iter(semantic))
        extra = kinds - {kind}
        # Observed offline markup adds verse-number/note-kind CSS classes.
        allowed = {c for c in extra if kind == 'verse' and re.fullmatch(r'v[1-9][0-9]*', c)}
        if kind == 'note':
            allowed |= extra & {'f', 'x'}
        if extra != allowed:
            raise Unsupported('Unreviewed semantic classes')
        if kind == 'note' and 'x' in extra:
            attrs['_note_type'] = 'crossReference'
    else:
        raise Unsupported('Unreviewed semantic classes')
    if node['tag'] not in {'div', 'span', 'br'} or kind not in BLOCK | INLINE:
        raise Unsupported('Unreviewed source semantic structure')
    if set(attrs) - {'class', 'data-usfm', 'id', '_note_type'}:
        raise Unsupported('Unreviewed source attributes')
    parts = [part for child in node.get('children', []) if (part := _semantic(child)) is not None]
    return Node(kind, attrs, parts)


def to_osis(chapter, edition):
    """Strict semantic conversion; unknown raw source stays intact on failure."""
    node = chapter['tree']
    for index in chapter['chapter_path']:
        node = node['children'][index]
    blocks = []
    for child in node.get('children', []):
        if isinstance(child, str):
            if child.strip():
                raise Unsupported('Unclassified chapter text')
            continue
        block = _semantic(child)
        if block is None or block.kind == 'label':
            continue
        if block.kind not in BLOCK:
            raise Unsupported('Unreviewed chapter block')
        blocks.append(block)
    document = Document(chapter['reference'], blocks, chapter['encoded_sha256'],
                        edition.archive_url or 'urn:local:authorized-yves', edition.attribution,
                        work_id=f'YouVersion{edition.identifier}Research', title=edition.title,
                        language=edition.language)
    return convert(document)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--version', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    edition = read_edition(json.loads(args.metadata.read_text()), args.version)
    # Private output only; publish statistics/hashes separately, never this corpus.
    args.output.mkdir(parents=True, exist_ok=False, mode=0o700)
    try:
        count = 0
        for chapter in archive_chapters(args.archive, edition, complete=args.require_complete):
            xml, report = to_osis(chapter, edition)
            name = chapter['reference']
            (args.output/(name+'.json')).write_text(json.dumps(chapter, ensure_ascii=False))
            (args.output/(name+'.osis.xml')).write_bytes(xml)
            count += 1
        (args.output/'source-metadata.json').write_text(json.dumps(edition.metadata, ensure_ascii=False))
    except BaseException:
        import shutil
        shutil.rmtree(args.output)
        raise
    print(json.dumps(dict(chapters=count, expected=len(edition.chapters), complete=count==len(edition.chapters),
                         scope='local research output; not an installed resource or proof of permitted use')))


if __name__ == '__main__':
    main()
