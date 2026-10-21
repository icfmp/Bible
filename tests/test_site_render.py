"""Repeated page generation must preserve channel objects and current provenance."""
import json
from pathlib import Path
import tempfile
import unittest
from tools.site_render import render


class SiteRenderTests(unittest.TestCase):
    def test_regeneration_preserves_channel_and_escapes_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            alpha = site / 'alpha'
            alpha.mkdir()
            names = ['Bible.flatpakref', 'bible-alpha.flatpakrepo', 'bible-alpha.gpg',
                     'repo/objects/old', 'Bible-old-sources.tar.gz']
            for name in names:
                target = alpha / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b'preserve signed channel')
            provenance = dict(source_commit='a'*40, packaging_revision='build<1>',
                              source_archive='Bible-a-sources.tar.gz', flatpak_commit='b'*64,
                              source_sha256='c'*64, signing_fingerprint='d'*40)
            for revision in ['build<1>', 'build<2>']:
                provenance['packaging_revision'] = revision
                render(site, provenance)
                page = (site / 'index.html').read_text()
                self.assertIn(revision.replace('<', '&lt;').replace('>', '&gt;'), page)
                self.assertIn('alpha/Bible.flatpakref', page)
                self.assertNotIn('${', page)
                self.assertTrue((site / 'assets/style.css').is_file())
                self.assertTrue((site / 'assets/reading.png').is_file())
                for name in names:
                    self.assertEqual((alpha / name).read_bytes(), b'preserve signed channel')
