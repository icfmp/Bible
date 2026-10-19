"""One-time owner-side setup using gh authentication; never print the private key.

Run after review/merge, on a trusted workstation with gh and GnuPG. A stable key
is created only when no channel secret exists. Existing Pages sites are refused
unless they were explicitly marked as managed by this setup.
"""
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
from tools.channel_ci import REPO, api
from tools.flatpak_channel import run


def variable(name):
    result = subprocess.run(['gh','variable','get',name,'--repo',REPO],capture_output=True,text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def main():
    api(f'repos/{REPO}/contents/.github/workflows/alpha-channel.yml?ref=main')
    repository = api(f'repos/{REPO}')
    assert repository['permissions'].get('admin'), 'A repository administrator must run this setup with their own gh connection'
    if repository['has_pages']:
        assert variable('BIBLE_ALPHA_PAGES_MANAGED') == '1', 'An existing Pages site will not be overwritten'
    secrets = api(f'repos/{REPO}/actions/secrets')['secrets']
    if any(s['name']=='BIBLE_FLATPAK_GPG_KEY' for s in secrets):
        assert variable('BIBLE_FLATPAK_GPG_FINGERPRINT'), 'Existing signing key has no fingerprint; recover it rather than replacing it'
        print('Existing stable signing key retained.')
    else:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)/'gpg'
            home.mkdir(mode=0o700)
            try:
                subprocess.run(['gpg','--homedir',str(home),'--batch','--pinentry-mode','loopback','--passphrase','',
                                '--quick-generate-key','Bible alpha repository <icfmp@users.noreply.github.com>','rsa3072','sign','2y'],check=True)
                keys = run('gpg','--homedir',home,'--with-colons','--list-keys')
                fingerprint = next(line.split(':')[9] for line in keys.splitlines() if line.startswith('fpr:'))
                private = subprocess.check_output(['gpg','--homedir',str(home),'--armor','--export-secret-keys',fingerprint])
                backup = Path(os.environ.get('XDG_DATA_HOME', str(Path.home()/'.local/share'))) / 'bible-alpha-signing'
                backup.mkdir(parents=True, exist_ok=True, mode=0o700)
                backup.chmod(0o700)
                repository_root = Path(run('git','rev-parse','--show-toplevel')).resolve()
                assert not backup.resolve().is_relative_to(repository_root), 'Signing backup must stay outside Git'
                private_path = backup / f'{fingerprint}.asc'
                with private_path.open('xb') as output:
                    output.write(private)
                private_path.chmod(0o600)
                shutil.copy2(home/'openpgp-revocs.d'/f'{fingerprint}.rev', backup/f'{fingerprint}.rev')
                print(f'Sauvegarde privée à conserver hors ligne : {private_path}')
                subprocess.run(['gh','secret','set','BIBLE_FLATPAK_GPG_KEY','--repo',REPO],input=private,check=True)
                subprocess.run(['gh','variable','set','BIBLE_FLATPAK_GPG_FINGERPRINT','--repo',REPO,'--body',fingerprint],check=True)
            finally:
                subprocess.run(['gpgconf','--homedir',str(home),'--kill','all'],check=False)
    if not repository['has_pages']:
        subprocess.run(['gh','api','--method','POST',f'repos/{REPO}/pages','-f','build_type=workflow'],check=True)
    page = api(f'repos/{REPO}/pages')
    assert page['build_type'] == 'workflow'
    base_url = page['html_url'].rstrip('/')
    assert base_url.startswith('https://')
    for name,value in [('BIBLE_ALPHA_PAGES_BASE_URL',base_url),('BIBLE_ALPHA_PAGES_MANAGED','1')]:
        subprocess.run(['gh','variable','set',name,'--repo',REPO,'--body',value],check=True)
    runs = json.loads(run('gh','run','list','--repo',REPO,'--workflow','prerequisites.yml',
                          '--branch','main','--status','success','--limit','1','--json','databaseId'))
    assert runs, 'No successful main CI available; verify the prototype first'
    subprocess.run(['gh','workflow','run','alpha-channel.yml','--repo',REPO,'--ref','main',
                    '-f',f"verified_run={runs[0]['databaseId']}"],check=True)
    print('Configuration effectuée ; suivre la validation publique du workflow. Aucun lien d’installation n’est encore annoncé vérifié.')


if __name__ == '__main__': main()
