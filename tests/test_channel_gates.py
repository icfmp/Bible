"""Publication gates must reject an unverified source, changed artifact or key."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import channel_ci
from tools.flatpak_channel import prepare, digest


class ChannelGateTests(unittest.TestCase):
    def verification(self, *, conclusion='success', repository='icfmp/Bible', corrupt=False):
        previous = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            os.chdir(directory)
            try:
                Path('event.json').write_text(json.dumps({'workflow_run':{'id':123}}))
                execution = {'status':'completed','conclusion':conclusion,'head_branch':'main',
                    'head_repository':{'full_name':repository},'path':'.github/workflows/prerequisites.yml',
                    'head_sha':channel_ci.BASELINE}
                def command(args, **kwargs):
                    if args[:3] == ['gh','run','download']:
                        incoming = Path('incoming'); incoming.mkdir()
                        bundle = incoming/'Bible-alpha.flatpak'; bundle.write_bytes(b'test artifact')
                        (incoming/'build-info.json').write_text(json.dumps({
                            'commit':channel_ci.BASELINE, 'architecture':'x86_64', 'prerequisites':'success',
                            'ci':'https://github.com/icfmp/Bible/actions/runs/123',
                            'flatpak_ref':'app/io.github.icfmp.Bible/x86_64/master',
                            'sha256': '0'*64 if corrupt else digest(bundle)}))
                env = {'GITHUB_EVENT_PATH':str(Path('event.json').resolve())}
                with patch.dict(os.environ,env), patch.object(channel_ci,'api',return_value=execution), patch.object(channel_ci.subprocess,'run',side_effect=command):
                    return channel_ci.verify()
            finally:
                os.chdir(previous)

    def test_green_main_artifact_is_identified(self):
        self.assertEqual(self.verification(),{'source':channel_ci.BASELINE,'ci_run':'123'})

    def test_failed_ci_cannot_publish(self):
        with self.assertRaisesRegex(AssertionError,'CI must be green'):
            self.verification(conclusion='failure')

    def test_fork_run_cannot_publish(self):
        with self.assertRaises(AssertionError):
            self.verification(repository='untrusted/Bible')

    def test_changed_artifact_cannot_publish(self):
        with self.assertRaises(AssertionError):
            self.verification(corrupt=True)

    def test_signing_key_change_preserves_previous_site(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)/'site'
            alpha = site/'alpha';alpha.mkdir(parents=True)
            old = {'source_commit':'a'*40,'signing_fingerprint':'A'*40}
            metadata = alpha/'provenance.json';metadata.write_text(json.dumps(old))
            with self.assertRaisesRegex(AssertionError,'signing key change'):
                prepare('unused',site,'https://example.invalid/Bible','unused','B'*40,'a'*40,'1','1')
            self.assertEqual(json.loads(metadata.read_text()),old)

    def test_rollback_preserves_previous_site(self):
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)/'site'
            alpha = site/'alpha';alpha.mkdir(parents=True)
            old = {'source_commit':'a'*40,'signing_fingerprint':'A'*40}
            metadata = alpha/'provenance.json';metadata.write_text(json.dumps(old))
            import subprocess
            with patch('tools.flatpak_channel.subprocess.run',return_value=subprocess.CompletedProcess([],1)):
                with self.assertRaisesRegex(AssertionError,'alpha rollback'):
                    prepare('unused',site,'https://example.invalid/Bible','unused','A'*40,'b'*40,'1','1')
            self.assertEqual(json.loads(metadata.read_text()),old)

    def test_non_https_repository_is_not_public(self):
        with self.assertRaises(AssertionError):
            prepare('unused','unused','http://example.invalid/Bible','unused','A'*40,'a'*40,'1','1')
