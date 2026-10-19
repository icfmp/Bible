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
