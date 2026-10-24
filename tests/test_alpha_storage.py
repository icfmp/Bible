"""Archive migration is fail-closed and retention preserves complete trees."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from tools import alpha_storage as storage


class AlphaStorageTests(unittest.TestCase):
    def asset(self, name, data):
        return dict(id=123, name=name, state='uploaded', size=len(data),
                    digest='sha256:' + hashlib.sha256(data).hexdigest(),
                    browser_download_url=f'https://github.com/icfmp/Bible/releases/download/{storage.SOURCE_TAG}/{name}')

    def test_all_public_bytes_verified_before_any_local_archive_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory); alpha = site / 'alpha'; alpha.mkdir()
            paths = [alpha / f'Bible-{c * 40}-sources.tar.gz' for c in 'ab']
            for p in paths: p.write_bytes(p.name.encode())
            assets = [self.asset(p.name, p.read_bytes()) for p in paths]
            remote = dict(draft=False, prerelease=True, assets=assets)
            with patch.object(storage, 'release', return_value=remote), patch.object(storage, 'verify_asset', side_effect=['https://example.invalid/a', AssertionError('Public source download mismatch')]):
                with self.assertRaisesRegex(AssertionError, 'download mismatch'):
                    storage.archive_sources(site)
            self.assertTrue(all(p.exists() for p in paths))
            self.assertFalse((alpha / 'sources.json').exists())

    def test_verified_migration_preserves_digest_and_updates_source_link(self):
        import io
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory); alpha = site / 'alpha'; alpha.mkdir()
            name = f'Bible-{"a" * 40}-sources.tar.gz'; data = b'exact original archive bytes'
            (alpha / name).write_bytes(data)
            asset = self.asset(name, data)
            provenance = dict(source_archive=name, source_sha256=asset['digest'][7:], flatpak_commit='b' * 64)
            (alpha / 'provenance.json').write_text(json.dumps(provenance))
            with patch.object(storage, 'release', return_value=dict(draft=False, prerelease=True, assets=[asset])), patch.object(storage.urllib.request, 'urlopen', return_value=io.BytesIO(data)):
                catalog = storage.archive_sources(site)
            self.assertFalse((alpha / name).exists())
            self.assertEqual(catalog['archives'][name]['sha256'], provenance['source_sha256'])
            updated = json.loads((alpha / 'provenance.json').read_text())
            self.assertEqual(updated['flatpak_commit'], provenance['flatpak_commit'])
            self.assertEqual(updated['source_url'], asset['browser_download_url'])
            self.assertIn(name, (alpha / 'sources.html').read_text())
            # Replacement of a previously verified asset is refused on later runs.
            replacement = dict(asset, id=124)
            with patch.object(storage, 'release', return_value=dict(draft=False, prerelease=True, assets=[replacement])):
                with self.assertRaisesRegex(AssertionError, 'replaced'):
                    storage.archive_sources(site)

    def test_corrupt_remote_digest_is_rejected(self):
        asset = self.asset('archive', b'original')
        with self.assertRaisesRegex(AssertionError, 'digest mismatch'):
            storage.verify_asset(asset, 'archive', '0' * 64, len(b'original'))

    def test_public_bytes_are_checked_independently_of_asset_metadata(self):
        import io
        name = f'Bible-{"a" * 40}-sources.tar.gz'
        asset = self.asset(name, b'original')
        with patch.object(storage.urllib.request, 'urlopen', return_value=io.BytesIO(b'tampered')):
            with self.assertRaisesRegex(AssertionError, 'download mismatch'):
                storage.verify_asset(asset, name, asset['digest'][7:], asset['size'])

    @unittest.skipUnless(shutil.which('ostree'), 'OSTree CLI required')
    def test_prune_keeps_ten_complete_revisions_and_current_ref(self):
        from tools.flatpak_channel import REF
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory); repo = site / 'alpha/repo'; content = site / 'content'; content.mkdir()
            storage.command('ostree', f'--repo={repo}', 'init', '--mode=archive-z2')
            commits = []
            for n in range(14):
                (content / 'shared').write_text('unchanged shared content')
                (content / 'changed').write_text(str(n))
                commits.append(storage.command('ostree', f'--repo={repo}', 'commit', f'--branch={REF}', f'--subject={n}', f'--tree=dir={content}'))
            result = storage.retain_repository(site)
            self.assertEqual(result['flatpak_commit'], commits[-1])
            for commit in commits[-10:]:
                self.assertEqual(storage.command('ostree', f'--repo={repo}', 'cat', commit, '/shared'), 'unchanged shared content')
            self.assertLess(result['after_bytes'], result['before_bytes'])
            self.assertFalse((repo / 'objects' / commits[0][:2] / (commits[0][2:] + '.commit')).exists())
