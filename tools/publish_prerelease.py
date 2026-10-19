"""Publish only the explicitly requested alpha, after the tag's full CI succeeds."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

VERSION = '0.1.0-alpha.2'
SOURCE_COMMIT = 'c2792c14ec86b28767cd5bc9ec8509a576e9a52d'
SOURCE_RUN = '39315036866'
REPO = 'icfmp/Bible'


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True).strip()


def api(endpoint: str) -> dict:
    return json.loads(run('gh', 'api', endpoint))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    assert os.environ['GITHUB_REF'] == f'refs/heads/release/{VERSION}'
    assert os.environ['GITHUB_REPOSITORY'] == REPO
    commit = run('git', 'rev-parse', 'HEAD')
    assert commit == SOURCE_COMMIT
    assert run('git', 'rev-parse', f'{VERSION}^{{commit}}') == commit
    ci_run = api(f'repos/{REPO}/actions/runs/{SOURCE_RUN}')
    assert ci_run['head_sha'] == commit
    assert ci_run['status'] == 'completed' and ci_run['conclusion'] == 'success'
    old_release = api(f'repos/{REPO}/releases/tags/0.1.0-alpha.1')
    assert old_release['id'] == 417477427 and not old_release['draft']
    old_assets = [(a['id'], a['name'], a.get('digest')) for a in old_release['assets']]
    info = json.loads(Path('release-artifacts/build-info.json').read_text())
    assert info['commit'] == commit and info['architecture'] == 'x86_64'
    assert info['prerequisites'] == 'success'
    assert info['ci'] == f'https://github.com/{REPO}/actions/runs/{SOURCE_RUN}'
    assert info['flatpak_ref'].split('/')[2] == 'x86_64'
    original = Path('release-artifacts/Bible-alpha.flatpak')
    assert digest(original) == info['sha256']
    assert Path('release-artifacts/SHA256SUMS').read_text().strip() == f"{info['sha256']}  Bible-alpha.flatpak"
    # Keep the release asset directory separate from the downloaded CI metadata.
    Path('release-artifacts/SHA256SUMS').unlink()
    Path('release-artifacts/build-info.json').unlink()
    assert Path('LICENSE').is_file(), 'La licence du projet doit être choisie avant distribution'
    out = Path('release-artifacts')
    bundle = out / f'Bible-{VERSION}-linux-x86_64.flatpak'
    (out / 'Bible-alpha.flatpak').rename(bundle)
    assert bundle.stat().st_size > 0
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary) / f'Bible-{VERSION}-sources'
        root.mkdir()
        # Preserve the complete source snapshot and scripts of this exact commit.
        subprocess.run(['git', 'archive', '--format=tar', '-o', str(root / 'Bible-source.tar'), commit], check=True)
        vendors = root / 'dependencies'
        vendors.mkdir()
        manifest = json.loads(Path('packaging/io.github.icfmp.Bible.json').read_text())
        for module in manifest['modules']:
            for source in module['sources']:
                if source['type'] != 'archive':
                    continue
                path = vendors / source['url'].rsplit('/', 1)[-1]
                with urllib.request.urlopen(source['url'], timeout=120) as response, path.open('wb') as target:
                    shutil.copyfileobj(response, target)
                assert digest(path) == source['sha256'], f'Source incorrecte : {path.name}'
        (root / 'CONSTRUIRE.txt').write_text(
            f'Bible {VERSION}\nCommit : {commit}\n\n'
            'Extraire Bible-source.tar dans un dossier vide. Installer flatpak et flatpak-builder,\n'
            'ajouter Flathub, puis installer org.gnome.Platform//49 et org.gnome.Sdk//49.\n'
            'Depuis les sources du projet :\n'
            'flatpak-builder --user --repo=local-repo --force-clean build-dir packaging/io.github.icfmp.Bible.json\n'
            f'flatpak build-bundle local-repo Bible-{VERSION}-linux-x86_64.flatpak io.github.icfmp.Bible --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo\n\n'
            'Les archives originales SWIG et SWORD sont dans dependencies/ ; leurs sommes\n'
            'sont épinglées dans le manifeste. Pour les réutiliser sans retéléchargement,\n'
            'remplacer les URL correspondantes du manifeste par leurs URL file:// absolues,\n'
            'en conservant les sommes et le correctif SWORD. Ne pas modifier le code de Bible.\n'
            'Les licences des dépendances sont dans leurs archives respectives ; voir aussi\n'
            'THIRD_PARTY_NOTICES.md dans les sources du projet. Le runtime GNOME est distribué\n'
            'séparément par Flathub, avec ses licences et ses sources correspondantes.\n'
            'Les traductions et commentaires sont téléchargés séparément, sous leurs propres licences.\n'
        )
        archive = out / f'Bible-{VERSION}-sources.tar.gz'
        with tarfile.open(archive, 'w:gz') as tar:
            tar.add(root, arcname=root.name)
    provenance = {
        'version': VERSION, 'commit': commit, 'architecture': 'x86_64',
        'ci': f'https://github.com/{REPO}/actions/runs/{SOURCE_RUN}',
        'build_info': info,
        'publication_ci': f'https://github.com/{REPO}/actions/runs/{os.environ["GITHUB_RUN_ID"]}',
        'publisher_commit': os.environ['GITHUB_SHA'],
        'flatpak': bundle.name, 'sha256': digest(bundle),
    }
    (out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    assets = sorted(out.iterdir())
    sums = out / 'SHA256SUMS'
    sums.write_text(''.join(f'{digest(path)}  {path.name}\n' for path in assets))
    assets.append(sums)
    notes = Path(tempfile.gettempdir()) / 'bible-release-notes.md'
    notes.write_text(Path(os.environ.get('BIBLE_RELEASE_NOTES', f'docs/releases/{VERSION}.md')).read_text() +
                     f'\nCommit : `{commit}`\n\n[CI de ce commit]({provenance["ci"]})\n\n'
                     f'SHA-256 de `{bundle.name}` :\n```text\n{provenance["sha256"]}\n```\n')
    # Drafts must be fetched by ID: the tag endpoint only finds published releases.
    matching = [r for r in api(f'repos/{REPO}/releases?per_page=100')
                if r['tag_name'] == VERSION]
    assert len(matching) <= 1, 'Plusieurs releases correspondent à cette étiquette'
    if matching:
        assert matching[0]['draft'], 'Refus de remplacer une release déjà publique'
        subprocess.run(['gh', 'release', 'upload', VERSION, '--repo', REPO,
                        '--clobber', *map(str, assets)], check=True)
        subprocess.run(['gh', 'release', 'edit', VERSION, '--repo', REPO,
                        '--title', VERSION, '--notes-file', str(notes), '--prerelease'], check=True)
    else:
        subprocess.run(['gh', 'release', 'create', VERSION, '--repo', REPO, '--verify-tag',
                        '--draft', '--prerelease', '--title', VERSION,
                        '--notes-file', str(notes), *map(str, assets)], check=True)
        matching = [r for r in api(f'repos/{REPO}/releases?per_page=100')
                    if r['tag_name'] == VERSION]
    assert len(matching) == 1
    release_id = matching[0]['id']
    release = api(f'repos/{REPO}/releases/{release_id}')
    assert release['draft'] and release['prerelease']
    assert release['tag_name'] == VERSION
    assert {a['name'] for a in release['assets']} == {p.name for p in assets}
    with tempfile.TemporaryDirectory() as temporary:
        subprocess.run(['gh', 'release', 'download', VERSION, '--repo', REPO, '--dir', temporary], check=True)
        for path in assets:
            assert digest(Path(temporary) / path.name) == digest(path), path.name
    subprocess.run(['gh', 'release', 'edit', VERSION, '--repo', REPO, '--draft=false', '--prerelease'], check=True)
    release = api(f'repos/{REPO}/releases/{release_id}')
    assert not release['draft'] and release['prerelease']
    preserved = api(f'repos/{REPO}/releases/tags/0.1.0-alpha.1')
    assert [(a['id'], a['name'], a.get('digest')) for a in preserved['assets']] == old_assets
    print(json.dumps({'release': release['html_url'], 'commit': commit,
                      'assets': [a['browser_download_url'] for a in release['assets']],
                      'sha256': provenance['sha256']}, indent=2))
    with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a') as summary:
        summary.write(f'Publication vérifiée : {release["html_url"]}\n\nCommit : `{commit}`\n\nSHA-256 : `{provenance["sha256"]}`\n')


if __name__ == '__main__':
    main()
