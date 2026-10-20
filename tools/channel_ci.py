"""CI gates and data-branch persistence for the alpha channel."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from tools.flatpak_channel import digest, run, restore_repository_layout

REPO = 'icfmp/Bible'
DATA_BRANCH = 'flatpak-alpha-data'
BASELINE = 'c2792c14ec86b28767cd5bc9ec8509a576e9a52d'

def parent_state():
    return Path(os.environ['RUNNER_TEMP']) / 'bible-alpha-parent'


def api(endpoint):
    return json.loads(run('gh','api',endpoint))


def verify():
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    run_id = str(event.get('workflow_run',{}).get('id') or os.environ['INPUT_VERIFIED_RUN'])
    assert run_id.isdigit()
    execution = api(f'repos/{REPO}/actions/runs/{run_id}')
    assert execution['status'] == 'completed' and execution['conclusion'] == 'success', 'CI must be green'
    assert execution['head_branch'] == 'main' and execution['head_repository']['full_name'] == REPO
    assert execution['path'] == '.github/workflows/prerequisites.yml'
    source = execution['head_sha']
    assert re.fullmatch(r'[0-9a-f]{40}',source)
    subprocess.run(['git','merge-base','--is-ancestor',BASELINE,source],check=True)
    subprocess.run(['git','merge-base','--is-ancestor',source,'origin/main'],check=True)
    subprocess.run(['gh','run','download',run_id,'--repo',REPO,'--name','Bible-alpha-linux-x86_64','--dir','incoming'],check=True)
    info = json.loads(Path('incoming/build-info.json').read_text())
    assert info['commit'] == source and info['architecture'] == 'x86_64'
    assert info['prerequisites'] == 'success'
    assert info['ci'] == f'https://github.com/{REPO}/actions/runs/{run_id}'
    assert info['flatpak_ref'] == 'app/io.github.icfmp.Bible/x86_64/master'
    assert digest('incoming/Bible-alpha.flatpak') == info['sha256']
    Path('incoming/verified.json').write_text(json.dumps({'source':source,'ci_run':run_id},indent=2))
    return {'source':source,'ci_run':run_id}


def restore():
    site = Path('public')
    site.mkdir()
    heads = run('git','ls-remote','--heads','origin',f'refs/heads/{DATA_BRANCH}')
    parent_state().write_text(heads.split()[0] if heads else '')
    if not heads:
        return
    subprocess.run(['git','fetch','origin',f'refs/heads/{DATA_BRANCH}'],check=True)
    with tempfile.TemporaryDirectory() as temporary:
        worktree = Path(temporary) / 'data'
        subprocess.run(['git','worktree','add','--detach',str(worktree),'FETCH_HEAD'],check=True)
        try:
            for path in worktree.rglob('*'):
                assert not path.is_symlink(), 'Unexpected link in channel data'
            shutil.copytree(worktree,site,ignore=shutil.ignore_patterns('.git'),dirs_exist_ok=True)
            repo = site / 'alpha/repo'
            if repo.exists():
                restore_repository_layout(repo)
        finally:
            subprocess.run(['git','worktree','remove','--force',str(worktree)],check=True)


def persist():
    """Commit only the staged public site, never a signing key or runner files."""
    site = Path('public').resolve()
    assert (site / 'alpha/provenance.json').is_file()
    repository = Path(run('git','rev-parse','--absolute-git-dir'))
    heads = run('git','ls-remote','--heads','origin',f'refs/heads/{DATA_BRANCH}')
    parent = heads.split()[0] if heads else None
    assert parent_state().read_text() == (parent or ''), 'Channel changed while preparing; refusing to overwrite its objects'
    if parent:
        subprocess.run(['git','fetch','origin',f'refs/heads/{DATA_BRANCH}'],check=True)
    with tempfile.TemporaryDirectory() as temporary:
        env = dict(os.environ, GIT_DIR=str(repository), GIT_WORK_TREE=str(site),
                   GIT_INDEX_FILE=str(Path(temporary)/'index'),
                   GIT_AUTHOR_NAME='github-actions[bot]',GIT_AUTHOR_EMAIL='41898282+github-actions[bot]@users.noreply.github.com',
                   GIT_COMMITTER_NAME='github-actions[bot]',GIT_COMMITTER_EMAIL='41898282+github-actions[bot]@users.noreply.github.com')
        subprocess.run(['git','read-tree','--empty'],env=env,check=True)
        subprocess.run(['git','add','--all','.'],env=env,cwd=site,check=True)
        tree = subprocess.check_output(['git','write-tree'],env=env,text=True).strip()
        arguments = ['git','commit-tree',tree,'-m','Publish signed Flatpak alpha repository']
        if parent: arguments += ['-p',parent]
        commit = subprocess.check_output(arguments,env=env,text=True).strip()
        subprocess.run(['git','push','origin',f'{commit}:refs/heads/{DATA_BRANCH}'],check=True)
        parent_state().write_text(commit)


def import_signing_key():
    home = Path(os.environ['RUNNER_TEMP']) / 'alpha-signing-key'
    home.mkdir(mode=0o700)
    secret = os.environ.pop('BIBLE_FLATPAK_GPG_KEY')
    assert secret, 'Missing BIBLE_FLATPAK_GPG_KEY repository secret'
    fingerprint = os.environ['BIBLE_FLATPAK_GPG_FINGERPRINT']
    assert re.fullmatch(r'[0-9A-F]{40,64}',fingerprint), 'Missing signing fingerprint variable'
    subprocess.run(['gpg','--homedir',str(home),'--batch','--import'],input=secret.encode(),check=True)
    keys = run('gpg','--homedir',home,'--with-colons','--list-secret-keys')
    assert [line.split(':')[9] for line in keys.splitlines() if line.startswith('fpr:')] == [fingerprint], 'Signing secret/fingerprint mismatch'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action',choices=['verify','restore','persist','import-key'])
    action = parser.parse_args().action
    {'verify':verify,'restore':restore,'persist':persist,'import-key':import_signing_key}[action]()


if __name__ == '__main__': main()
