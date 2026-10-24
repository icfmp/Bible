"""Move exact corresponding sources off Pages and bound OSTree retention.

All work is staged. Persist/deploy is deliberately outside this module.
The data branch's ordinary Git history remains the recovery copy.
"""
import argparse
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import urllib.request

REPOSITORY = 'icfmp/Bible'
SOURCE_TAG = 'alpha-source-archives'
KEEP_COMMITS = 10


def command(*args):
    return subprocess.check_output(list(map(str, args)), text=True).strip()


def api(endpoint):
    return json.loads(command('gh', 'api', endpoint))


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def release():
    """Explicit technical storage prerelease; never a numbered application release."""
    return api(f'repos/{REPOSITORY}/releases/tags/{SOURCE_TAG}')


def verify_asset(asset, name, expected_sha, expected_size, *, download=True):
    assert asset['name'] == name and asset['state'] == 'uploaded'
    assert asset['size'] == expected_size
    assert asset.get('digest') == 'sha256:' + expected_sha, 'Release asset digest mismatch'
    url = f'https://github.com/{REPOSITORY}/releases/download/{SOURCE_TAG}/{name}'
    assert asset['browser_download_url'] == url
    if download:
        digest = hashlib.sha256()
        size = 0
        with urllib.request.urlopen(url, timeout=120) as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
                size += len(block)
        assert size == expected_size and digest.hexdigest() == expected_sha, 'Public source download mismatch'
    return url


def archive_sources(site):
    """Upload and publicly verify every source BEFORE deleting any staged copy.

    A failure leaves every local archive intact; no asset is overwritten.
    Existing catalogue entries are checked against GitHub's asset IDs/digests.
    """
    alpha = Path(site) / 'alpha'
    catalog_path = alpha / 'sources.json'
    catalog = json.loads(catalog_path.read_text()) if catalog_path.exists() else {'version': 1, 'archives': {}}
    assert catalog['version'] == 1
    remote = release()
    assert not remote['draft'] and remote['prerelease'], 'Source storage release must be public'
    assets = {a['name']: a for a in remote['assets']}
    for name, record in catalog['archives'].items():
        asset = assets[name]
        assert asset['id'] == record['asset_id'], 'Previously verified source asset was replaced'
        assert verify_asset(asset, name, record['sha256'], record['bytes'], download=False) == record['url']
    pending = sorted(alpha.glob('Bible-*-sources.tar.gz'))
    for path in pending:
        match = re.fullmatch(r'Bible-([0-9a-f]{40})-sources\.tar\.gz', path.name)
        assert match, f'Unexpected source archive: {path.name}'
        digest, size = sha256(path), path.stat().st_size
        asset = assets.get(path.name)
        if asset is None:
            subprocess.run(['gh', 'release', 'upload', SOURCE_TAG, str(path), '--repo', REPOSITORY], check=True)
            assets = {a['name']: a for a in release()['assets']}
            asset = assets[path.name]
        url = verify_asset(asset, path.name, digest, size)
        catalog['archives'][path.name] = dict(source_commit=match[1], sha256=digest,
                                             bytes=size, asset_id=asset['id'], url=url)
    # Only after every public download passed may staging discard originals.
    catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + '\n')
    provenance_path = alpha / 'provenance.json'
    if provenance_path.exists():
        provenance = json.loads(provenance_path.read_text())
        record = catalog['archives'][provenance['source_archive']]
        assert provenance['source_sha256'] == record['sha256']
        provenance['source_url'] = record['url']
        provenance_path.write_text(json.dumps(provenance, indent=2) + '\n')
    for path in pending:
        path.unlink()
    rows = ''.join(f'<li><a href="{html.escape(r["url"], quote=True)}">{html.escape(n)}</a>'
                   f' — SHA-256: <code>{r["sha256"]}</code></li>'
                   for n, r in sorted(catalog['archives'].items()))
    (alpha / 'sources.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<title>Bible corresponding sources</title><h1>Corresponding sources</h1>'
        '<p>Archives moved from Pages to GitHub Releases without changing their bytes. '
        'Old direct Pages archive URLs are replaced by the links below.</p><ul>' + rows + '</ul></html>\n')
    return catalog


def retain_repository(site, keep=KEEP_COMMITS):
    """Keep the current revision plus nine parents; retain every other ref tip.

    OSTree retains shared file objects needed by any retained tree. Old installed
    clients update via full objects when an incremental delta is unavailable.
    """
    assert keep >= 2
    from tools.flatpak_channel import REF, restore_repository_layout
    repo = Path(site) / 'alpha/repo'
    restore_repository_layout(repo)
    head = command('ostree', f'--repo={repo}', 'rev-parse', REF)
    before = sum(p.stat().st_size for p in repo.rglob('*') if p.is_file())
    # Remove derived static deltas before pruning: obsolete deltas otherwise grow
    # independently of commit retention. Flatpak can pull ordinary signed objects.
    deltas = repo / 'deltas'
    if deltas.exists():
        import shutil
        assert not deltas.is_symlink()
        shutil.rmtree(deltas)
    output = command('ostree', f'--repo={repo}', 'prune', '--refs-only', f'--depth={keep - 1}')
    command('ostree', f'--repo={repo}', 'fsck')
    assert command('ostree', f'--repo={repo}', 'rev-parse', REF) == head
    return dict(keep_commits=keep, flatpak_commit=head, before_bytes=before,
                after_bytes=sum(p.stat().st_size for p in repo.rglob('*') if p.is_file()), prune=output)


def migrate(site):
    from tools.flatpak_channel import MAX_SITE_BYTES
    from tools.site_render import render
    site = Path(site)
    before = sum(p.stat().st_size for p in site.rglob('*') if p.is_file())
    alpha = site / 'alpha'
    original = json.loads((alpha / 'provenance.json').read_text())
    protected = {name: sha256(alpha / name) for name in
                 ['Bible.flatpakref', 'bible-alpha.flatpakrepo', 'bible-alpha.gpg', 'repo/summary', 'repo/summary.sig']}
    catalog = archive_sources(site)
    retention = retain_repository(site)
    provenance = json.loads((alpha / 'provenance.json').read_text())
    assert {k: provenance[k] for k in original} == original, 'Application provenance changed'
    assert all(sha256(alpha / name) == digest for name, digest in protected.items()), 'Signed channel identity changed'
    render(site, provenance)
    after = sum(p.stat().st_size for p in site.rglob('*') if p.is_file())
    assert after < MAX_SITE_BYTES
    report = dict(before_bytes=before, after_bytes=after, source_archives=len(catalog['archives']),
                  source_archive_bytes=sum(a['bytes'] for a in catalog['archives'].values()),
                  application_provenance_unchanged=True, signed_channel_files_unchanged=True,
                  retention=retention)
    Path('storage-plan.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def seed_client(site, base_url, old_commit):
    """Install while the unpruned public server is still live, then select #90."""
    import os
    from tools.check_flatpak_channel import check, verify_data
    from tools.flatpak_channel import APP_ID
    expected = json.loads((Path(site) / 'alpha/provenance.json').read_text())
    result = check(base_url, expected, Path('storage-client-before.json').resolve())
    assert re.fullmatch(r'[0-9a-f]{64}', old_commit)
    assert old_commit != expected['flatpak_commit']
    subprocess.run(['flatpak', 'update', '--user', '--noninteractive', f'--commit={old_commit}', APP_ID + '//alpha'], check=True)
    assert command('flatpak', 'info', '--user', '--show-commit', APP_ID + '//alpha') == old_commit
    verify_data(result['user_data_snapshot'])
    result.update(install_commit=old_commit, previous_current_commit=expected['flatpak_commit'],
                  client_dir=os.environ['FLATPAK_USER_DIR'])
    Path('storage-client-before.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def verify_clients(site, base_url):
    import os
    from tools.check_flatpak_channel import check, verify_data
    from tools.flatpak_channel import APP_ID
    before = json.loads(Path('storage-client-before.json').read_text())
    expected = json.loads((Path(site) / 'alpha/provenance.json').read_text())
    # Wait for the new source catalogue to propagate; the app commit is unchanged.
    import time
    for attempt in range(30):
        try:
            with urllib.request.urlopen(base_url + '/alpha/sources.json?storage=' + os.environ['GITHUB_RUN_ID'], timeout=30) as response:
                public = json.load(response)
            assert public == json.loads((Path(site) / 'alpha/sources.json').read_text())
            with urllib.request.urlopen(base_url + '/alpha/provenance.json?storage=' + os.environ['GITHUB_RUN_ID'], timeout=30) as response:
                assert json.load(response) == expected
            break
        except Exception:
            if attempt == 29: raise
            time.sleep(10)
    subprocess.run(['flatpak', 'update', '--user', '--noninteractive', APP_ID + '//alpha'], check=True)
    installed = command('flatpak', 'info', '--user', '--show-commit', APP_ID + '//alpha')
    assert installed == expected['flatpak_commit'] != before['install_commit']
    verify_data(before['user_data_snapshot'])
    old_dir = os.environ['FLATPAK_USER_DIR']
    try:
        os.environ['FLATPAK_USER_DIR'] = old_dir + '-fresh'
        fresh = check(base_url, expected, Path('storage-fresh-install.json').resolve())
    finally:
        os.environ['FLATPAK_USER_DIR'] = old_dir
    result = dict(old_commit=before['install_commit'], update_commit=installed,
                  old_client_update=True, user_data_preserved=True,
                  fresh_install=fresh['install_commit'] == installed,
                  gpg_commit=fresh['gpg_commit'], gpg_summary=fresh['gpg_summary'],
                  gtk_startup=fresh['gtk_startup'])
    Path('storage-check.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['archive', 'retain', 'migrate', 'seed-client', 'verify-clients'])
    parser.add_argument('--site', default='public')
    parser.add_argument('--base-url')
    parser.add_argument('--old-commit')
    args = parser.parse_args()
    if args.action == 'seed-client':
        result = seed_client(args.site, args.base_url, args.old_commit)
    elif args.action == 'verify-clients':
        result = verify_clients(args.site, args.base_url)
    else:
        result = {'archive': archive_sources, 'retain': retain_repository, 'migrate': migrate}[args.action](args.site)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
