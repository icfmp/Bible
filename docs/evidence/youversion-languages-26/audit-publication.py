"""Read-only independent publication/source audit; never touches an application profile."""
import hashlib,io,json,re,subprocess,sys,tarfile,time,urllib.request
from pathlib import Path
root=Path('/workspace/work/youversion-language-26');expected=sys.argv[1]
assert re.fullmatch('[0-9a-f]{40}',expected)
out=root/'publication-audit';out.mkdir(exist_ok=True)
def request(url):return urllib.request.urlopen(urllib.request.Request(url,headers={'Cache-Control':'no-cache'}),timeout=45)
def remote(name):
 with request('https://icfmp.github.io/Bible/alpha/'+name+'.json?audit='+str(time.time_ns())) as r:value=json.load(r)
 (out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n');return value
before=json.loads((root/'provenance-before.json').read_text());p=remote('provenance');assert p['source_commit']==expected,p
for field in ('signing_fingerprint','remote','ref'):assert before[field]==p[field]
old=json.loads((root/'sources-before.json').read_text());catalogue=remote('sources')
for name,value in old['archives'].items():assert catalogue['archives'][name]==value,name
assert len(catalogue['archives'])==len(old['archives'])+1
record=catalogue['archives'][p['source_archive']];assert record['source_commit']==expected
assert record['sha256']==p['source_sha256'] and record['url']==p['source_url']
package=out/p['source_archive'];digest=hashlib.sha256();count=0
with request(record['url']) as response,package.open('wb') as f:
 while chunk:=response.read(1024*1024):
  count+=len(chunk);assert count<=128*1024*1024;digest.update(chunk);f.write(chunk)
assert count==record['bytes'] and digest.hexdigest()==record['sha256']
repo=root/'repo'
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args])
entries=git('ls-tree','-r','--name-only',expected).decode().splitlines()
expected_files={name:hashlib.sha256(git('show',expected+':'+name)).hexdigest() for name in entries if not any(name==skip or name.startswith(skip+'/') for skip in ('docs/captures','docs/evidence','wiki/images'))}
with tarfile.open(package,'r:gz') as outer:
 members=outer.getmembers();assert len(members)<10000
 project=next(m for m in members if m.isfile() and m.name.endswith('/Bible-source.tar'))
 raw=outer.extractfile(project).read();assert len(raw)<32*1024*1024
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as archive:
  files={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive.getmembers() if m.isfile()}
 assert files==expected_files,(sorted(set(expected_files)-set(files)),sorted(set(files)-set(expected_files)),[name for name in files if files.get(name)!=expected_files.get(name)])
 manifest=json.loads(git('show',expected+':packaging/io.github.icfmp.Bible.json'))
 dependencies=[]
 for module in manifest['modules']:
  for entry in module['sources']:
   if entry['type']!='archive':continue
   name=entry['url'].rsplit('/',1)[-1];member=next(m for m in members if m.isfile() and m.name.endswith('/dependencies/'+name))
   sha=hashlib.sha256(outer.extractfile(member).read()).hexdigest();assert sha==entry['sha256'],name
   dependencies.append(dict(name=name,sha256=sha))
tags=json.loads(subprocess.check_output(['gh','api','repos/icfmp/Bible/tags?per_page=100','--jq','[.[]|{name,sha:.commit.sha}]'],text=True))
oldtags=json.loads((root/'tags-before.json').read_text());numbered=lambda rows:sorted((r['name'],r['sha']) for r in rows if re.fullmatch(r'v?\d+\.\d+\.\d+-alpha\.\d+',r['name']))
assert numbered(tags)==numbered(oldtags)
report=dict(result='PASS',source_commit=expected,publication=p,project_files_verified=len(files),dependency_sources=dependencies,
 historical_source_records_unchanged=len(old['archives']),source_records_now=len(catalogue['archives']),
 numbered_tags_unchanged=numbered(tags),archive_sha256=digest.hexdigest(),archive_bytes=count,profile_accessed=False)
(out/'verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
