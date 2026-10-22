"""Prepare the signed, static alpha repository. Publication is a separate step."""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request

APP_ID = 'io.github.icfmp.Bible'
BRANCH = 'alpha'
REMOTE = 'bible-alpha'
REF = f'app/{APP_ID}/x86_64/{BRANCH}'
RUNTIME_REPO = 'https://dl.flathub.org/repo/flathub.flatpakrepo'
# Keep every published object and corresponding-source archive. This remains
# below GitHub Pages' 1 GiB site limit; exceeding it aborts before persistence.
MAX_SITE_BYTES = 768 * 1024 * 1024


def run(*args):
    return subprocess.check_output(list(map(str, args)), text=True).strip()


def restore_repository_layout(repo):
    """Recreate only empty directories lost by Git; preserve repository contents."""
    repo = Path(repo)
    assert not repo.is_symlink() and not (repo / 'config').is_symlink() and (repo / 'config').is_file(), 'Invalid saved OSTree repository'
    for name in ('objects', 'extensions', 'refs', 'refs/heads', 'refs/remotes',
                 'refs/mirrors', 'state', 'tmp', 'tmp/cache'):
        path = repo / name
        assert not path.is_symlink(), f'Unexpected link in OSTree repository: {name}'
        path.mkdir(exist_ok=True)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_archive(site, source):
    """Provide corresponding project and dependency sources, not just a Git link."""
    archive_path = site / 'alpha' / f'Bible-{source}-sources.tar.gz'
    if archive_path.exists():
        return archive_path
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / f'Bible-{source}-sources'
        root.mkdir()
        subprocess.run(['git', 'archive', '--format=tar', '-o', str(root / 'Bible-source.tar'), source], check=True)
        manifest = json.loads(run('git', 'show', f'{source}:packaging/{APP_ID}.json'))
        dependencies = root / 'dependencies'
        dependencies.mkdir()
        for module in manifest['modules']:
            for entry in module['sources']:
                if entry['type'] != 'archive':
                    continue
                path = dependencies / entry['url'].rsplit('/', 1)[-1]
                with urllib.request.urlopen(entry['url'], timeout=60) as response, path.open('wb') as output:
                    shutil.copyfileobj(response, output)
                assert digest(path) == entry['sha256'], f'Incorrect dependency source: {path.name}'
        (root / 'CONSTRUIRE.txt').write_text(
            f'Sources de Bible au commit {source}.\nExtraire Bible-source.tar dans un dossier vide.\n'
            'Installer Flatpak/flatpak-builder, ajouter Flathub et les runtime/SDK GNOME 49.\n'
            f'flatpak-builder --user --default-branch=alpha --repo=local-repo --force-clean build-dir packaging/{APP_ID}.json\n'
            'Archives originales des dépendances dans dependencies/ ; URL et SHA-256 dans le manifeste.\n'
            'Pour les utiliser localement, remplacer ces URL par des URL file:// absolues sans changer les sommes.\n'
            'Conserver le correctif SWORD. Voir LICENSE et THIRD_PARTY_NOTICES.md dans les sources.\n'
            'Runtime GNOME : sources et licences distribuées séparément par Flathub.\n')
        with tarfile.open(archive_path, 'w:gz') as archive:
            archive.add(root, arcname=root.name)
    return archive_path


def prepare(bundle, site, base_url, gpg_home, fingerprint, source, ci_run, revision, allow_loopback=False):
    assert re.fullmatch(r'[0-9a-f]{40}', source), 'Expected a full source commit'
    assert re.fullmatch(r'[0-9A-F]{40,64}', fingerprint), 'Expected the signing fingerprint'
    parsed = urllib.parse.urlsplit(base_url)
    assert parsed.scheme == 'https' or (allow_loopback and parsed.scheme == 'http' and parsed.hostname == '127.0.0.1')
    assert not parsed.query and not parsed.fragment and not parsed.username
    base_url = base_url.rstrip('/')
    site, gpg_home = Path(site), Path(gpg_home)
    alpha = site / 'alpha'
    alpha.mkdir(parents=True, exist_ok=True)
    old = alpha / 'provenance.json'
    if old.exists():
        previous = json.loads(old.read_text())
        assert previous['signing_fingerprint'] == fingerprint, 'Refusing an unreviewed signing key change'
        assert previous['source_commit'] == source or subprocess.run(
            ['git', 'merge-base', '--is-ancestor', previous['source_commit'], source]).returncode == 0, 'Refusing an alpha rollback'
    repo = alpha / 'repo'
    if not (repo / 'config').exists():
        subprocess.run(['ostree', f'--repo={repo}', 'init', '--mode=archive-z2'], check=True)
    restore_repository_layout(repo)
    with tempfile.TemporaryDirectory() as temporary:
        imported = Path(temporary) / 'imported'
        subprocess.run(['ostree', f'--repo={imported}', 'init', '--mode=archive-z2'], check=True)
        subprocess.run(['flatpak', 'build-import-bundle', str(imported), str(bundle)], check=True)
        refs = run('ostree', f'--repo={imported}', 'refs').splitlines()
        assert refs == [f'app/{APP_ID}/x86_64/master'], f'Unexpected bundle identity: {refs}'
        subprocess.run(['flatpak', 'build-commit-from', f'--src-repo={imported}', f'--src-ref={refs[0]}',
                        f'--gpg-sign={fingerprint}', f'--gpg-homedir={gpg_home}', '--force', '--no-update-summary',
                        f'--subject=Bible alpha {source[:12]} revision {revision}',
                        f'--body=Source {source}; verified CI {ci_run}; packaging revision {revision}', str(repo), REF], check=True)
    subprocess.run(['flatpak', 'build-update-repo', f'--gpg-sign={fingerprint}',
                    f'--gpg-homedir={gpg_home}', '--generate-static-deltas', str(repo)], check=True)
    assert (repo / 'summary.sig').is_file(), 'Unsigned repository summary'
    public_key = subprocess.check_output(['gpg', '--homedir', str(gpg_home), '--export', fingerprint])
    assert public_key
    (alpha / 'bible-alpha.gpg').write_bytes(public_key)
    encoded = base64.b64encode(public_key).decode('ascii')
    url = base_url + '/alpha/repo'
    (alpha / 'bible-alpha.flatpakrepo').write_text(
        f'[Flatpak Repo]\nTitle=Bible — canal alpha\nUrl={url}\nDefaultBranch={BRANCH}\nGPGKey={encoded}\n')
    (alpha / 'Bible.flatpakref').write_text(
        f'[Flatpak Ref]\nName={APP_ID}\nBranch={BRANCH}\nTitle=Bible — préversion alpha\n'
        f'Url={url}\nIsRuntime=false\nSuggestRemoteName={REMOTE}\nRuntimeRepo={RUNTIME_REPO}\nGPGKey={encoded}\n')
    sources = source_archive(site, source)
    commit = run('ostree', f'--repo={repo}', 'rev-parse', REF)
    provenance = {'source_commit': source, 'ci_run': str(ci_run), 'packaging_revision': str(revision),
                  'flatpak_commit': commit, 'ref': REF, 'remote': REMOTE,
                  'signing_fingerprint': fingerprint, 'source_archive': sources.name,
                  'source_sha256': digest(sources), 'bundle_sha256': digest(bundle)}
    old.write_text(json.dumps(provenance, indent=2) + '\n')
    (site / '.nojekyll').touch()
    from tools.site_render import render
    render(site, provenance)
    for path in site.rglob('*'):
        assert not path.is_symlink(), f'Pages cannot publish symlinks: {path}'
    assert sum(p.stat().st_size for p in site.rglob('*') if p.is_file()) < MAX_SITE_BYTES, 'Site exceeds the 768 MiB publishing limit; last deployment must be kept'
    return provenance


def main():
    parser = argparse.ArgumentParser()
    for name in ['bundle', 'site', 'base-url', 'gpg-home', 'fingerprint', 'source', 'ci-run', 'revision']:
        parser.add_argument('--' + name, required=True)
    args = vars(parser.parse_args())
    print(json.dumps(prepare(**args), indent=2))


if __name__ == '__main__':
    main()
