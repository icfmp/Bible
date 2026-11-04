"""Retained-client verification must distinguish live metadata and preserved data."""
from contextlib import redirect_stdout
import hashlib,io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools import validate_public_channel as channel


class PublicUpdateTests(unittest.TestCase):
    def setUp(self):
        self.directory=self.enterContext(tempfile.TemporaryDirectory())
        previous=Path.cwd();os.chdir(self.directory);self.addCleanup(os.chdir,previous)

    def test_snapshot_uses_live_public_revision_before_staging_is_published(self):
        previous=dict(flatpak_commit='old',source_commit='published-source')
        Path('public/alpha').mkdir(parents=True)
        Path('public/alpha/provenance.json').write_text(json.dumps(dict(flatpak_commit='not-published')))
        with patch.object(channel.urllib.request,'urlopen',return_value=io.BytesIO(json.dumps(previous).encode())),patch.object(channel,'check',return_value={'install_commit':'old'}) as check,patch('sys.argv',['test','snapshot','--base-url','https://example.invalid/Bible']),redirect_stdout(io.StringIO()):
            channel.main()
        self.assertEqual(check.call_args.args[1],previous)
        self.assertEqual(json.loads(Path('public-before-provenance.json').read_text()),previous)

    def update(self,*,damaged=False,unchanged=False):
        Path('public/alpha').mkdir(parents=True)
        expected=dict(flatpak_commit='next')
        Path('public/alpha/provenance.json').write_text(json.dumps(expected))
        note=Path('retained-note');note.write_text('Previously installed note')
        digest=hashlib.sha256(note.read_bytes()).hexdigest()
        if damaged:note.write_text('Changed unexpectedly')
        old=dict(install_commit='next' if unchanged else 'previous',user_data_snapshot={str(note.resolve()):digest})
        Path('public-install-check.json').write_text(json.dumps(old))
        requests=[];responses=iter([dict(flatpak_commit='stale'),expected])
        def receive(request,**_):
            requests.append(request.full_url)
            return io.BytesIO(json.dumps(next(responses)).encode())
        with patch.object(channel.urllib.request,'urlopen',side_effect=receive),patch.object(channel.time,'sleep'),patch.object(channel,'run',return_value='next'),patch.object(channel.subprocess,'run') as command,patch.object(channel,'verify_client') as verify,patch.dict(os.environ,{'GITHUB_STEP_SUMMARY':str(Path('summary').resolve())}),patch('sys.argv',['test','update','--base-url','https://example.invalid/Bible']),redirect_stdout(io.StringIO()):
            if damaged or unchanged:
                with self.assertRaises(AssertionError):channel.main()
                self.assertFalse(Path('public-update-check.json').exists())
                verify.assert_not_called()
            else:
                channel.main();verify.assert_called_once()
                command.assert_called_once_with(['flatpak','update','--user','--noninteractive','io.github.icfmp.Bible//alpha'],check=True)
                receipt=json.loads(Path('public-update-check.json').read_text())
                self.assertTrue(receipt['public_update_success']);self.assertTrue(receipt['user_data_preserved'])
                self.assertEqual(receipt['install_commit'],'previous');self.assertEqual(receipt['update_commit'],'next')
                self.assertEqual(note.read_text(),'Previously installed note')
        self.assertEqual(len(requests),2);self.assertNotEqual(requests[0],requests[1])

    def test_actual_update_waits_for_fresh_metadata_and_preserves_existing_note(self):self.update()

    def test_changed_user_data_cannot_produce_a_success_receipt(self):self.update(damaged=True)

    def test_same_installed_commit_is_not_reported_as_an_update(self):self.update(unchanged=True)
