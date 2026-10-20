"""Download a real extra commentary; verify SWORD fidelity and GTK verse following offline."""
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
from bible.providers import CROSSWIRE, EXTRA
from bible.session import Session, SessionStore, TabState
from bible.sword_provider import CommentaryReader


def offline_snapshot(directory, commentary):
    from bible.ui import Application, Window, GLib
    library = Library(Path(directory) / 'translations')
    state = SessionStore(Path(directory) / 'session.json')
    state.save(Session([TabState('KJV', 'John.3.16', study_visible=True, commentary=commentary)]))
    app = Application()
    app.register()
    window = Window(app, library)
    window.present()
    result = []
    reader = CommentaryReader(library.root / commentary, commentary)
    references = []
    key = reader.key('John.1.1')
    while key.getOSISRef().startswith('John.'):
        reference = key.getOSISRef()
        if reader.entry(reference, reader.versification):
            references.append(reference)
            if len(references) == 2:
                break
        key.increment()
        if key.popError() != '\x00':
            break
    assert len(references) == 2, 'Need two genuinely indexed commentary entries'
    for reference in references:
        assert window.active_tab.navigate('KJV', reference)
        window.study.refresh(force=True)
        while GLib.MainContext.default().pending():
            GLib.MainContext.default().iteration(False)
        expected = reader.entry(reference, window.active_tab.reader.versification)
        assert expected and expected.strip(), reference
        buffer = window.study.text.get_buffer()
        actual = window.study.entry_text
        assert actual == expected, 'GTK commentary does not follow the active verse'
        reader.module.setKey(reader.key(reference))
        direct = reader.module.stripText()
        direct = direct if isinstance(direct, str) else direct.c_str()
        assert expected == direct, 'Commentary differs from native SWORD'
        result.append({'reference': reference, 'sha256': hashlib.sha256(actual.encode()).hexdigest()})
    # Kretzmann uses section entries. Never substitute a nearby section for an
    # exact absent verse or leave the previous commentary visible.
    missing = None
    for verse in range(1, 37):
        reference = f'John.3.{verse}'
        if reader.entry(reference, reader.versification) is None:
            assert window.active_tab.navigate('KJV', reference)
            window.study.refresh(force=True)
            buffer = window.study.text.get_buffer()
            assert not buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False)
            assert window.study.status.get_text()
            missing = reference
            break
    assert missing is not None, 'Expected sparse section commentary'
    resource = library.resource(commentary)
    assert resource.provider_id == EXTRA.id
    assert EXTRA.name in window.study.source.get_text()
    assert 'permission' in resource.license.lower()
    window.close()
    assert state.load().tabs[0].commentary == commentary
    return {'entries': result, 'absent_entry_clears_view': missing, 'provider': resource.provider_id, 'source': resource.source,
            'license': resource.license, 'conditions': resource.conditions}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--offline':
        with patch('urllib.request.urlopen', side_effect=AssertionError('Offline')):
            directory, commentary, output = sys.argv[2:]
            if os.environ.get('BIBLE_EXPECT_OFFLINE') == '1':
                assert len(Path('/proc/net/route').read_text().splitlines()) <= 1, 'Network routes remain available'
            Path(output).write_text(json.dumps(offline_snapshot(directory, commentary), ensure_ascii=False))
        return
    primary = {r.name for r in catalogue(CROSSWIRE) if r.kind == 'commentary'}
    extra = {r.name: r for r in catalogue(EXTRA) if r.kind == 'commentary'}
    resource = extra['Kretzmann']
    assert resource.name not in primary, 'Must test a genuinely additional commentary'
    bible = next(r for r in catalogue(CROSSWIRE) if r.name == 'KJV')
    with tempfile.TemporaryDirectory() as directory:
        library = Library(Path(directory) / 'translations')
        library.install(bible)
        library.install(resource)
        expected = offline_snapshot(directory, resource.id)
        command = shlex.split(os.environ.get('BIBLE_OFFLINE_PREFIX', ''))
        command += ['env', 'GSK_RENDERER=cairo', 'GTK_A11Y=none',
                    'BIBLE_EXPECT_OFFLINE=' + ('1' if command else '0'), 'dbus-run-session', '--', 'xvfb-run', '-a', sys.executable, '-m', 'tools.check_affiliated_commentary', '--offline', directory, resource.id, str(Path(directory) / 'offline-result.json')]
        actual = subprocess.run(command, check=True, capture_output=True, text=True)
        assert json.loads((Path(directory) / 'offline-result.json').read_text()) == expected, 'Offline reopen changed text or provenance'
        Path('affiliated-commentary-result.json').write_text(json.dumps({
            'result': 'success', 'commentary': resource.id, 'bible': bible.id,
            'driver': resource.driver, 'offline_process': command[:3],
            'checks': expected, 'commit': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
        }, ensure_ascii=False, indent=2) + '\n')
        print(f'PASS {resource.id}: real HTTPS install; SWORD fidelity; GTK follows two indexed entries and clears an absent verse; isolated offline reopen; attribution and session preserved')


if __name__ == '__main__':
    main()
