#!/usr/bin/env python3
"""Explicit integration: real French and English downloads, fidelity and offline use."""
from pathlib import Path
import hashlib
import json
import os
import shlex
import subprocess
import sys
import tempfile
from unittest.mock import patch

from bible.library import Library, catalogue
from bible.sword_provider import Reader


def check_resource(resource):
    with tempfile.TemporaryDirectory() as directory:
        library = Library(directory)
        assert library.installed() == []
        library.install(resource)
        assert library.resource(resource.name).license == resource.license
        assert library.resource(resource.name).conditions == resource.conditions
        reader = Reader(Path(directory) / resource.name, resource.name)
        assert reader.has_reference('John.3.16'), 'John 3:16 missing from real resource'
        john = next(book for book in reader.books if book.code == 'John')
        assert 16 in john.chapters[3]
        first = reader.first_reference()
        chapter = reader.chapter(first)
        assert any(text for _, text in chapter.verses), 'Downloaded chapter is empty'
        for reference, text in chapter.verses:
            reader.module.setKey(reader.key(reference))
            assert text == reader.module.stripText(), reference
        expected = chapter.verses
        following = reader.neighbours(first)[1]
        del reader
        with patch('urllib.request.urlopen', side_effect=AssertionError('Network disabled')):
            restarted = Library(directory)
            assert restarted.installed() == [resource.name]
            assert restarted.resource(resource.name).source == 'CrossWire'
            reader = Reader(Path(directory) / resource.name, resource.name)
            assert reader.chapter(first).verses == expected
            if following:
                assert reader.neighbours(following)[0] == first
                assert reader.chapter(following).verses
        command = shlex.split(os.environ.get('BIBLE_OFFLINE_PREFIX', ''))
        command += [sys.executable, '-m', 'tools.check_offline',
                    str(Path(directory) / resource.name), resource.name]
        offline = subprocess.run(command, check=True, capture_output=True, text=True)
        digest = hashlib.sha256(json.dumps(expected, ensure_ascii=False).encode()).hexdigest()
        assert offline.stdout.strip() == digest, 'Offline process text mismatch'
        print(f'::notice title=CrossWire integration {resource.name}::PASS: '
              f'{resource.language}; {resource.license}; first passage {first}; '
              f'{len(expected)} verses; actual install; SWORD fidelity; offline attribution; '
              'offline reopen; chapter navigation', flush=True)


def main():
    resources = catalogue()
    print(f'Catalogue: {len(resources)} Bible resources; '
          f'{sum(r.installable for r in resources)} supported and not encrypted', flush=True)
    by_name = {r.name: r for r in resources if r.installable}
    french = next((by_name[name] for name in ('FreBDM1707', 'FreBA') if name in by_name), None)
    assert french is not None, 'No expected French translation available from CrossWire'
    assert french.language == 'fr'
    for name in (french.name, 'KJV'):
        check_resource(by_name[name])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
