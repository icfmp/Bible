"""Validate actual public installation/update; never substitute a bundle test."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from tools.check_flatpak_channel import check, verify_data
from tools.flatpak_channel import APP_ID, run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['install','update'])
    parser.add_argument('--base-url',required=True)
    args = parser.parse_args()
    assert args.base_url.startswith('https://'), 'Public validation requires HTTPS'
    expected = json.loads(Path('public/alpha/provenance.json').read_text())
    url = args.base_url.rstrip('/') + '/alpha/provenance.json?revision=' + expected['flatpak_commit']
    for attempt in range(30):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'Cache-Control':'no-cache'}),timeout=20) as response:
                if json.load(response)['flatpak_commit'] == expected['flatpak_commit']:
                    break
        except Exception:
            if attempt == 29: raise
        time.sleep(10)
    else: raise RuntimeError('Public Pages metadata did not reach the expected revision')
    if args.action == 'install':
        result = check(args.base_url,expected,Path('public-install-check.json').resolve())
    else:
        old = json.loads(Path('public-install-check.json').read_text())
        for attempt in range(30):
            subprocess.run(['flatpak','update','--user','--noninteractive',APP_ID + '//alpha'],check=True)
            installed = run('flatpak','info','--user','--show-commit',APP_ID + '//alpha')
            if installed == expected['flatpak_commit']: break
            time.sleep(10)
        else: raise RuntimeError('flatpak update did not install the published revision')
        assert installed != old['install_commit'], 'The update must change the installed commit'
        verify_data(old['user_data_snapshot'])
        result = dict(old, user_data_preserved=True, update_commit=installed, public_update_success=True,
                      public_url=args.base_url + '/alpha/Bible.flatpakref')
        Path('public-update-check.json').write_text(json.dumps(result,indent=2) + '\n')
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as summary:
            summary.write('Installation et mise à jour publiques signées vérifiées.\n\n'
                          f'Installer : {result["public_url"]}\n\n'
                          f'Commit installé : `{installed}`\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__': main()
