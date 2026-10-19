#!/usr/bin/env python3
"""Explicit online integration test: downloads one real public-domain translation."""
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


def main():
    resources = catalogue()
    assert resources, 'No public-domain Bible found in real CrossWire catalogue'
    print(f'Catalogue: {len(resources)} public-domain resources', flush=True)
    by_name = {r.name: r for r in resources}
    resource = next((by_name[name] for name in ['FreSegond', 'KJV'] if name in by_name), resources[0])
    print(f'Chosen: {resource.name} ({resource.language}); {resource.license}', flush=True)
    with tempfile.TemporaryDirectory() as directory:
        library = Library(directory)
        assert library.installed() == []
        library.install(resource)
        reader = Reader(Path(directory) / resource.name, resource.name)
        chapter = reader.chapter('Gen.1.1')
        assert any(text for _, text in chapter.verses), 'Downloaded chapter is empty'
        # Compare each displayed verse with SWORD's direct stripped source text.
        for reference, text in chapter.verses:
            reader.module.setKey(reader.key(reference))
            assert text == reader.module.stripText(), reference
        expected = chapter.verses
        del reader
        with patch('urllib.request.urlopen', side_effect=AssertionError('Network disabled')):
            restarted = Library(directory)
            assert restarted.installed() == [resource.name]
            reader = Reader(Path(directory) / resource.name, resource.name)
            assert reader.chapter('Gen.1.1').verses == expected
            following = reader.chapter(chapter.following)
            assert following.previous == 'Gen.1.1'
        command = shlex.split(os.environ.get('BIBLE_OFFLINE_PREFIX', ''))
        command += [sys.executable, '-m', 'tools.check_offline',
                    str(Path(directory) / resource.name), resource.name]
        offline = subprocess.run(command, check=True, capture_output=True, text=True)
        digest = hashlib.sha256(json.dumps(expected, ensure_ascii=False).encode()).hexdigest()
        assert offline.stdout.strip() == digest, 'Offline process text mismatch'
        print(f'PASS: real install, {len(expected)} verses read, SWORD fidelity, '
              'offline reopen and chapter navigation', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
