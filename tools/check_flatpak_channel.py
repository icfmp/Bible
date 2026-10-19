"""Real signed repository installation and update between two packaging revisions.

The test key is ephemeral and MUST NOT be used for a public channel. Public HTTPS
validation is a separate mandatory step after deployment with the stable key.
"""
import contextlib
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
from threading import Thread
import urllib.request

from tools.flatpak_channel import APP_ID, REF, REMOTE, prepare, run

SOURCE = 'c2792c14ec86b28767cd5bc9ec8509a576e9a52d'
BUNDLE_SHA = 'b1d0db01e1b824d6b761f3af22849f7a05fb00601d74c31ee558737962754297'


def check(base_url, expected, report_path, *, test_revision=None):
    """Clean client; GPG verification remains enabled throughout."""
    from tools.flatpak_channel import digest
    with urllib.request.urlopen(base_url + '/alpha/Bible.flatpakref', timeout=30) as response:
        descriptor = response.read()
    assert b'GPGKey=' in descriptor and b'Branch=alpha' in descriptor
    descriptor_path = report_path.parent / 'Bible.flatpakref'
    descriptor_path.write_bytes(descriptor)
    subprocess.run(['flatpak','remote-add','--user','--if-not-exists','flathub',
                    'https://dl.flathub.org/repo/flathub.flatpakrepo'], check=True)
    subprocess.run(['flatpak','install','--user','--noninteractive', str(descriptor_path)], check=True)
    installed = run('flatpak','info','--user','--show-commit', APP_ID + '//alpha')
    assert installed == expected['flatpak_commit']
    assert run('flatpak','info','--user','--show-ref', APP_ID + '//alpha') == REF
    assert run('flatpak','info','--user','--show-origin', APP_ID + '//alpha') == REMOTE
    user_repo = Path(os.environ['FLATPAK_USER_DIR']) / 'repo'
    assert run('ostree',f'--repo={user_repo}','config','get', f'remote "{REMOTE}".gpg-verify') == 'true'
    assert run('ostree',f'--repo={user_repo}','config','get', f'remote "{REMOTE}".gpg-verify-summary') == 'true'
    # Verify the installed code, launcher, icons, and actual GTK startup in the sandbox.
    command = '''import gi
from pathlib import Path
gi.require_version('Gtk', '4.0')
from gi.repository import GLib
from bible.ui import Application
assert Path('/app/share/applications/io.github.icfmp.Bible.desktop').is_file()
assert Path('/app/share/icons/hicolor/256x256/apps/io.github.icfmp.Bible.png').is_file()
app = Application()
GLib.timeout_add(900, lambda: app.quit() or False)
app.run([])
print('Bible GTK startup OK')'''
    subprocess.run(['dbus-run-session','--','xvfb-run','-a','flatpak','run','--user',
                    '--env=PYTHONPATH=/app/lib/bible-python','--env=GSK_RENDERER=cairo',
                    '--command=python3',APP_ID + '//alpha','-c',command], check=True)
    result = {'install_commit': installed, 'ref': REF, 'origin': REMOTE,
              'gpg_commit': True, 'gpg_summary': True, 'gtk_startup': True}
    if test_revision:
        updated = test_revision()
        subprocess.run(['flatpak','update','--user','--noninteractive', APP_ID + '//alpha'], check=True)
        current = run('flatpak','info','--user','--show-commit',APP_ID + '//alpha')
        assert current == updated['flatpak_commit'] and current != installed
        result.update(update_commit=current, update_success=True)
    report_path.write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        gpg = root / 'gpg'
        gpg.mkdir(mode=0o700)
        subprocess.run(['gpg','--homedir',str(gpg),'--batch','--pinentry-mode','loopback','--passphrase','',
                        '--quick-generate-key','Bible CI test only <test@example.invalid>','rsa3072','sign','1d'],check=True)
        keys = run('gpg','--homedir',gpg,'--with-colons','--list-keys')
        fingerprint = next(line.split(':')[9] for line in keys.splitlines() if line.startswith('fpr:'))
        bundle = root / 'Bible.flatpak'
        with urllib.request.urlopen(f'https://github.com/icfmp/Bible/releases/download/0.1.0-alpha.2/Bible-0.1.0-alpha.2-linux-x86_64.flatpak',timeout=60) as response:
            bundle.write_bytes(response.read())
        from tools.flatpak_channel import digest
        assert digest(bundle) == BUNDLE_SHA
        site = root / 'site'
        site.mkdir()
        server = ThreadingHTTPServer(('127.0.0.1',0),functools.partial(SimpleHTTPRequestHandler,directory=str(site)))
        thread = Thread(target=server.serve_forever,daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            first = prepare(bundle,site,base,gpg,fingerprint,SOURCE,'39315036866','test-1',allow_loopback=True)
            os.environ['FLATPAK_USER_DIR'] = str(root / 'client-installation')
            second = lambda: prepare(bundle,site,base,gpg,fingerprint,SOURCE,'39315036866','test-2',allow_loopback=True)
            result = check(base,first,Path('flatpak-channel-test.json').resolve(),test_revision=second)
            # A mismatching summary must be rejected by a clean client with GPG enabled.
            summary = site / 'alpha/repo/summary'
            original = summary.read_bytes()
            summary.write_bytes(original + b'corrupt')
            corrupt_env = dict(os.environ, FLATPAK_USER_DIR=str(root/'tampered-client'))
            added = subprocess.run(['flatpak','remote-add','--user','--from',REMOTE,
                                    str(site/'alpha/bible-alpha.flatpakrepo')],env=corrupt_env,capture_output=True,text=True)
            failure = subprocess.run(['flatpak','remote-ls','--user',REMOTE],env=corrupt_env,capture_output=True,text=True)
            assert failure.returncode != 0, 'Corrupt signed summary was accepted'
            result['corrupt_summary_rejected'] = True
            summary.write_bytes(original)
            Path('flatpak-channel-test.json').write_text(json.dumps(result,indent=2) + '\n')
            print(json.dumps(result,indent=2))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
            subprocess.run(['gpgconf','--homedir',str(gpg),'--kill','all'],check=False)


if __name__ == '__main__':
    main()
