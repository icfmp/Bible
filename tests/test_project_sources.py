"""Real Git archive retains preferred build inputs and excludes validation output."""
from pathlib import Path
import os
import subprocess
import tarfile
import tempfile
import unittest
from tools.project_sources import create_project_archive


class ProjectSourcesTests(unittest.TestCase):
    def test_build_inputs_original_assets_licenses_and_test_sources_survive(self):
        original=Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);repo=root/'repo';repo.mkdir()
            inputs={'bible/ui.py':b'APPLICATION SOURCE','packaging/io.github.icfmp.Bible.json':b'BUILD SCRIPT',
                    'packaging/icons/bible-source.png':b'ORIGINAL PREFERRED ICON SOURCE',
                    'third_party/source.tar.gz':b'ORIGINAL DEPENDENCY SOURCE','third_party/LICENSE':b'LICENSE',
                    'tools/build.py':b'BUILD CONTROL','tests/fixtures.py':b'TEST SOURCE','LICENSE':b'PROJECT LICENSE',
                    'docs/BUILD.md':b'BUILD INSTRUCTIONS'}
            evidence={'docs/evidence/old/capture.png':b'OLD GUI EVIDENCE','docs/captures/movie.webm':b'OLD MOVIE',
                      'wiki/images/old.png':b'OLD SCREENSHOT'}
            for name,content in (inputs|evidence).items():
                p=repo/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
            try:
                os.chdir(repo)
                subprocess.run(['git','init','-q'],check=True)
                subprocess.run(['git','add','.'],check=True)
                subprocess.run(['git','-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture'],check=True)
                source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
                result=create_project_archive(root/'source.tar',source)
                with tarfile.open(result) as archive:
                    files={m.name:archive.extractfile(m).read() for m in archive.getmembers() if m.isfile()}
                self.assertEqual(files,inputs)
                self.assertTrue(all((repo/name).read_bytes()==content for name,content in evidence.items()))
            finally:os.chdir(original)
