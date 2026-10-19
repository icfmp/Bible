import importlib.util,json,os,tempfile,unittest,hashlib,shutil
from pathlib import Path
from unittest.mock import patch
from tools import publish_prerelease as m
class Publication(unittest.TestCase):
 def exercise(self,corrupt=False):
  previous=Path.cwd()
  with tempfile.TemporaryDirectory() as d:
   os.chdir(d)
   try:
    Path('release-artifacts').mkdir(); Path('release-artifacts/Bible-alpha.flatpak').write_bytes(b'fixture-bundle')
    Path('LICENSE').write_text('fixture'); Path('packaging').mkdir(); Path('docs/releases').mkdir(parents=True)
    Path('docs/releases/0.1.0-alpha.2.md').write_text('fixture notes')
    source=Path('dependency.tar'); source.write_bytes(b'fixture-source')
    Path('packaging/io.github.icfmp.Bible.json').write_text(json.dumps({'modules':[{'sources':[{'type':'archive','url':source.resolve().as_uri(),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()}]}]}))
    info={'commit':m.SOURCE_COMMIT,'architecture':'x86_64','prerequisites':'success','ci':f'https://github.com/{m.REPO}/actions/runs/{m.SOURCE_RUN}','flatpak_ref':'app/io.github.icfmp.Bible/x86_64/master','sha256':m.digest(Path('release-artifacts/Bible-alpha.flatpak'))}
    Path('release-artifacts/build-info.json').write_text(json.dumps(info))
    Path('release-artifacts/SHA256SUMS').write_text(info['sha256']+'  Bible-alpha.flatpak\n')
    release={'id':1,'draft':True,'prerelease':True,'tag_name':m.VERSION,'assets':[], 'html_url':'https://github.com/icfmp/Bible/releases/tag/'+m.VERSION}
    uploaded={}; edits=[]
    def query(*args):
     if args[0]=='git': return m.SOURCE_COMMIT
     if args[:2]==('gh','api'):
      if '/actions/runs/' in args[2]: return json.dumps({'head_sha':m.SOURCE_COMMIT,'status':'completed','conclusion':'success'})
      if args[2].endswith('/tags/0.1.0-alpha.1'): return json.dumps({'id':417477427,'draft':False,'assets':[]})
      if args[2].endswith('?per_page=100'): return json.dumps([release] if uploaded else [])
      return json.dumps(release)
     raise AssertionError(args)
    def execute(args,**kw):
     if args[:2]==['git','archive']:
      Path(args[args.index('-o')+1]).write_bytes(b'fixture git archive'); return
     if args[:3]==['gh','release','create']:
      for p in Path('release-artifacts').iterdir(): uploaded[p.name]=p.read_bytes()
      release['assets']=[{'name':n,'browser_download_url':'https://example.org/'+n} for n in uploaded]; return
     if args[:3]==['gh','release','download']:
      dest=Path(args[args.index('--dir')+1])
      for n,data in uploaded.items(): (dest/n).write_bytes(data)
      if corrupt: (dest/next(iter(uploaded))).write_bytes(b'corruption')
      return
     if args[:3]==['gh','release','edit']:
      edits.append(args); release['draft']=False; return
     raise AssertionError(args)
    env={'GITHUB_REF':'refs/heads/release/'+m.VERSION,'GITHUB_REPOSITORY':m.REPO,'GITHUB_SHA':'b'*40,'GITHUB_RUN_ID':'fixture','GITHUB_STEP_SUMMARY':str(Path('summary').resolve())}
    with patch.dict(os.environ,env),patch.object(m,'run',query),patch.object(m.subprocess,'run',execute):
     if corrupt:
      with self.assertRaises(AssertionError): m.main()
      self.assertFalse(edits); self.assertTrue(release['draft'])
     else:
      m.main(); self.assertEqual(len(edits),1); self.assertFalse(release['draft']); self.assertTrue(release['prerelease'])
      self.assertEqual(json.loads(uploaded['provenance.json'])['commit'],m.SOURCE_COMMIT)
   finally: os.chdir(previous)
 def test_corrupt_uploaded_asset_keeps_draft(self): self.exercise(True)
 def test_verified_assets_publish_prerelease(self): self.exercise(False)
if __name__ == '__main__':
 unittest.main()
