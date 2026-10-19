"""Real CrossWire commentary integration, including an isolated offline process."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from unittest.mock import patch

from bible.library import Library, catalogue
from bible.sword_provider import CommentaryReader


def snapshot(library, name, reference):
    reader = CommentaryReader(library.root / name, name)
    text = reader.entry(reference, reader.versification)
    assert text and text.strip(), f'Empty real commentary: {name} {reference}'
    reader.module.setKey(reader.key(reference))
    direct = reader.module.stripText()
    if not isinstance(direct, str):
        direct = direct.c_str()
    assert text == direct, 'Commentary differs from direct SWORD text'
    resource = library.resource(name)
    assert resource.kind == 'commentary'
    return {'text_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'source': resource.source, 'license': resource.license,
            'conditions': resource.conditions}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--offline':
        directory, name, reference = sys.argv[2:]
        with patch('urllib.request.urlopen', side_effect=AssertionError('Offline')):
            print(json.dumps(snapshot(Library(directory), name, reference), ensure_ascii=False))
        return
    resources = {r.name: r for r in catalogue() if r.kind == 'commentary' and r.installable}
    with tempfile.TemporaryDirectory() as directory:
        library = Library(directory)
        for name in ('Clarke', 'MHCC'):
            resource = resources[name]
            assert resource.license == 'Public Domain'
            library.install(resource)
            reader = CommentaryReader(library.root / name, name)
            reference = 'John.3.16' if reader.has_reference('John.3.16') else reader.first_reference()
            expected = snapshot(library, name, reference)
            # Find a genuine absent entry when the source has one; fixtures also
            # check sparse and blank entries deterministically in the unit tests.
            key = reader.key('Gen.1.1')
            missing = None
            while True:
                if not reader.module.hasEntry(key):
                    missing = key.getOSISRef()
                    assert reader.entry(missing, reader.versification) is None
                    break
                key.increment()
                if key.popError() != '\x00':
                    break
            command = shlex.split(os.environ.get('BIBLE_OFFLINE_PREFIX', ''))
            command += [sys.executable, '-m', 'tools.check_commentary', '--offline', directory, name, reference]
            process = subprocess.run(command, check=True, capture_output=True, text=True)
            assert json.loads(process.stdout) == expected, 'Offline commentary or attribution mismatch'
            print(f'::notice title=Commentary integration {name}::PASS: real install; '
                  f'{resource.driver}; {reader.versification}; {reference}; exact SWORD text; '
                  f'offline reopen and attribution; absent entry={missing or "none in source"}', flush=True)
        assert library.installed('commentary') == ['Clarke', 'MHCC']
        assert library.installed('bible') == []


if __name__ == '__main__':
    main()
