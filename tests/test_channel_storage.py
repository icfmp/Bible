"""Data branch round trip: retain objects and keep runner/private files out."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from tools.channel_ci import restore, persist
from tools.flatpak_channel import restore_repository_layout


class ChannelStorageTests(unittest.TestCase):
    def test_only_public_files_are_pushed_and_history_round_trips(self):
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root/'remote.git'
            work = root/'work';work.mkdir()
            subprocess.run(['git','init','--bare',str(remote)],check=True,capture_output=True)
            subprocess.run(['git','init','-b','main',str(work)],check=True,capture_output=True)
            os.chdir(work)
            try:
                subprocess.run(['git','remote','add','origin',str(remote)],check=True)
                (work/'source-code.py').write_text('source code must not enter published website')
                (work/'private.asc').write_text('SENTINEL PRIVATE TEST DATA; NEVER PUBLISH')
                subprocess.run(['git','add','source-code.py'],check=True)
                subprocess.run(['git','-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','source'],check=True,capture_output=True)
                subprocess.run(['git','push','origin','main'],check=True,capture_output=True)
                with patch.dict(os.environ,{'RUNNER_TEMP':str(root)}):
                    restore()
                    alpha = work/'public/alpha';alpha.mkdir()
                    (alpha/'provenance.json').write_text(json.dumps({'revision':1}))
                    (alpha/'objects').mkdir();(alpha/'objects/old').write_bytes(b'old object')
                    (work/'public/index.html').write_text('First revision')
                    persist()
                    first = subprocess.check_output(['git','--git-dir',str(remote),'rev-parse','flatpak-alpha-data'],text=True).strip()
                    (work/'public/index.html').write_text('Second revision')
                    (alpha/'objects/new').write_bytes(b'new object')
                    persist()
                    files = subprocess.check_output(['git','--git-dir',str(remote),'ls-tree','-r','--name-only','flatpak-alpha-data'],text=True).splitlines()
                    self.assertEqual(set(files),{'index.html','alpha/provenance.json','alpha/objects/old','alpha/objects/new'})
                    parent = subprocess.check_output(['git','--git-dir',str(remote),'rev-parse','flatpak-alpha-data^'],text=True).strip()
                    self.assertEqual(parent,first)
                    shutil.rmtree(work/'public')
                    restore()
                    self.assertEqual((work/'public/index.html').read_text(),'Second revision')
                    self.assertTrue((work/'public/alpha/objects/old').is_file())
                    self.assertFalse((work/'public/.git').exists())
            finally:
                os.chdir(original)


    @unittest.skipUnless(shutil.which('ostree'), 'OSTree CLI required')
    def test_second_publication_after_git_restore(self):
        original = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            work = root / 'work'
            work.mkdir()
            remote = root / 'remote.git'
            subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
            subprocess.run(['git', 'init', '-b', 'main', str(work)], check=True, capture_output=True)
            os.chdir(work)
            try:
                subprocess.run(['git', 'remote', 'add', 'origin', str(remote)], check=True)
                with patch.dict(os.environ, {'RUNNER_TEMP': str(root)}):
                    restore()
                    alpha = work / 'public/alpha'
                    alpha.mkdir()
                    repo = alpha / 'repo'
                    subprocess.run(['ostree', f'--repo={repo}', 'init', '--mode=archive-z2'], check=True)
                    content = root / 'content'
                    content.mkdir()
                    (content / 'file').write_text('first revision')
                    def commit():
                        return subprocess.check_output(['ostree', f'--repo={repo}', 'commit',
                            '--branch=app/test/x86_64/alpha', '--subject=test',
                            f'--tree=dir={content}'], text=True).strip()
                    first = commit()
                    config = (repo / 'config').read_bytes()
                    (alpha / 'provenance.json').write_text('{}')
                    persist()
                    files = subprocess.check_output(['git', '--git-dir', str(remote),
                        'ls-tree', '-r', '--name-only', 'flatpak-alpha-data'], text=True)
                    self.assertNotIn('refs/remotes/', files)
                    shutil.rmtree(work / 'public')
                    restore()
                    self.assertEqual((repo / 'config').read_bytes(), config)
                    self.assertTrue((repo / 'refs/remotes').is_dir())
                    subprocess.run(['ostree', f'--repo={repo}', 'refs'], check=True)
                    (content / 'file').write_text('second revision')
                    second = commit()
                    self.assertNotEqual(first, second)
                    subprocess.run(['ostree', f'--repo={repo}', 'summary', '--update'], check=True)
                    persist()
                    shutil.rmtree(work / 'public')
                    restore()
                    parent = subprocess.check_output(['ostree', f'--repo={repo}',
                        'rev-parse', second + '^'], text=True).strip()
                    self.assertEqual(parent, first)
                    subprocess.run(['ostree', f'--repo={repo}', 'fsck'], check=True)
            finally:
                os.chdir(original)


    def test_repository_restore_rejects_links_without_changing_config(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / 'repo'
            repo.mkdir()
            (repo / 'config').write_bytes(b'[core]\nrepo_version=1\nmode=archive-z2\n')
            original = (repo / 'config').read_bytes()
            outside = Path(directory) / 'outside'
            outside.mkdir()
            (repo / 'refs').symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(AssertionError, 'Unexpected link'):
                restore_repository_layout(repo)
            self.assertEqual((repo / 'config').read_bytes(), original)
            self.assertEqual(list(outside.iterdir()), [])
