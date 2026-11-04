"""Validate actual public installation/update; never substitute a bundle test."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
from tools.check_flatpak_channel import check, verify_data, verify_client
from tools.flatpak_channel import APP_ID, run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['snapshot','install','update'])
    parser.add_argument('--base-url',required=True)
    args = parser.parse_args()
    assert args.base_url.startswith('https://'), 'Public validation requires HTTPS'
    metadata_url = args.base_url.rstrip('/') + '/alpha/provenance.json'
    if args.action == 'snapshot':
        with urllib.request.urlopen(urllib.request.Request(metadata_url+'?before='+str(time.time_ns()),headers={'Cache-Control':'no-cache'}),timeout=20) as response:
            previous=json.load(response)
        Path('public-before-provenance.json').write_text(json.dumps(previous,indent=2)+'\n')
        print(json.dumps(check(args.base_url,previous,Path('public-install-check.json').resolve()),indent=2))
        return
    expected = json.loads(Path('public/alpha/provenance.json').read_text())
    url = metadata_url + '?revision=' + expected['flatpak_commit']
    for attempt in range(30):
        try:
            with urllib.request.urlopen(urllib.request.Request(url+'&check='+str(time.time_ns()),headers={'Cache-Control':'no-cache'}),timeout=20) as response:
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
        verify_client()
        result = dict(old, user_data_preserved=True, update_commit=installed, public_update_success=True,
                      public_url=args.base_url + '/alpha/Bible.flatpakref')
        Path('public-update-check.json').write_text(json.dumps(result,indent=2) + '\n')
        with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as summary:
            summary.write('Installation et mise à jour publiques signées vérifiées.\n\n'
                          f'Installer : {result["public_url"]}\n\n'
                          f'Commit installé : `{installed}`\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__': main()
