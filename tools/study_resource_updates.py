"""Validate and publish independently versioned study resources on existing GitHub hosting."""
import argparse,base64,hashlib,json,subprocess,tempfile
from pathlib import Path
from bible.study_catalogue import BUNDLED,parse as parse_catalogue
from bible.reference_data import (DOWNLOAD_URL as REFERENCE_URL,MAX_ARCHIVE as REFERENCE_LIMIT,
                                 parse_archive as reference_rows,archive_generation,reference_header)
from bible.topic_data import DOWNLOAD_URL as TOPIC_URL,MAX_ARCHIVE as TOPIC_LIMIT,parse_archive as topic_rows,topic_header
from bible.topic_vocabulary import BUNDLED as VOCABULARY,parse as parse_vocabulary

REPO='icfmp/Bible'
BRANCH='data/study-resources'
TAG='study-resource-archives'
BASE='https://github.com/'+REPO+'/releases/download/'+TAG+'/'


def prepare(output,vocabulary,*,references=None,topics=None,previous=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    previous=BUNDLED.read_bytes() if previous is None else previous;records=parse_catalogue(previous)
    document=json.loads(previous);resources=document['resources'];assets=[];proof={}
    for identifier,path,name,member,header,rows,limit,format_name in (
        ('openbible-cross-references',references,'cross-references','cross_references.txt',reference_header,reference_rows,REFERENCE_LIMIT,'openbible-cross-references-v1'),
        ('openbible-topics',topics,'topic-scores','topic-scores.txt',topic_header,topic_rows,TOPIC_LIMIT,'openbible-topics-v1')):
        if path is None:continue
        path=Path(path)
        if path.is_symlink() or path.stat().st_size>limit:raise ValueError('Invalid input archive')
        generation=archive_generation(path,member,header);count=sum(1 for _ in rows(path))
        digest=hashlib.sha256(path.read_bytes()).hexdigest();filename=name+'-'+generation+'-'+digest[:12]+'.zip'
        target=output/filename;target.write_bytes(path.read_bytes());assets.append(target)
        resources[identifier]=dict(revision=generation,generation=generation,sha256=digest,size=target.stat().st_size,format=format_name,url=BASE+filename)
        proof[identifier]=dict(generation=generation,rows=count,sha256=digest,source=REFERENCE_URL if identifier=='openbible-cross-references' else TOPIC_URL)
    data=Path(vocabulary).read_bytes();value,entries=parse_vocabulary(data);digest=hashlib.sha256(data).hexdigest()
    old=records['topic-vocabulary']
    if old.sha256!=digest and old.revision==value['revision']:raise ValueError('Bump the vocabulary revision before publishing changed content')
    filename='topic-vocabulary-'+value['revision']+'-'+digest[:12]+'.json';target=output/filename;target.write_bytes(data);assets.append(target)
    resources['topic-vocabulary']=dict(revision=value['revision'],generation=value['revision'][:10],sha256=digest,size=len(data),format='bible-topic-vocabulary-v1',url=BASE+filename)
    document['resources']=resources
    catalogue=json.dumps(document,indent=2)+'\n';parse_catalogue(catalogue.encode())
    (output/'catalogue.json').write_text(catalogue)
    (output/'topic-vocabulary.json').write_bytes(data)
    proof['topic-vocabulary']=dict(revision=value['revision'],reviewed_names=len(entries),sha256=digest,source='Bible project reviewed vocabulary')
    (output/'provenance.json').write_text(json.dumps(proof,indent=2)+'\n')
    notices='''# Independently maintained study resources

The catalogue pins each immutable resource by size, SHA-256, compatible format
and actual generation date. Index updates and reviewed FR/EN vocabulary updates
are independent. These files contain relationships, source topic identifiers,
scores and reviewed names/synonyms; no Scripture quotations are bundled.

Cross-references: https://www.openbible.info/labs/cross-references/
Topics: https://www.openbible.info/topics/
Index attribution: OpenBible.info and its contributors, CC BY 4.0:
https://creativecommons.org/licenses/by/4.0/
Project vocabulary labels/synonyms: GPL-2.0-only; preferred source is the JSON
file in this branch. Original vocabulary source and authorship history:
https://github.com/icfmp/Bible/blob/e22dd2c605a6028e2329238034e92b14038734ce/bible/topic_vocabulary.py
The project history is preserved; the labels are not reattributed.

Maintain names/synonyms by reviewing `topic-vocabulary.json` in this data branch
and bumping its revision. Run the study-resource workflow in vocabulary-only
mode to deliver those changes without rebuilding the index or application.
Source identifiers join exactly; unmatched names are omitted from suggestions,
new source topics remain outside the curated list until reviewed, and missing
French names use the supplied English label. No automatic AI translation occurs.
A compatible source index missing a reviewed name remains installable.

The publisher validates complete compatible archives before archiving them,
never overwrites existing assets/tags, and updates this branch only after asset
verification. Failed validation retains prior published/installed resources.
Compatible applications refresh this small catalogue in Library > Study tools.
Offline applications keep their installed index/vocabulary and known catalogue.
'''
    (output/'README.md').write_text(notices)
    (output/'LICENSE').write_bytes((Path(__file__).resolve().parents[1]/'LICENSE').read_bytes())
    return assets,proof


def api(path,*,method='GET',data=None,missing=False):
    command=['gh','api','--method',method,'repos/'+REPO+'/'+path]
    if data is not None:command+=['--input','-']
    result=subprocess.run(command,input=json.dumps(data) if data is not None else None,text=True,capture_output=True)
    if result.returncode:
        if missing and '404' in result.stderr:return None
        raise RuntimeError(result.stderr.strip())
    return json.loads(result.stdout) if result.stdout.strip() else None


def remote_file(path,sha):
    value=api('contents/'+path+'?ref='+sha)
    if value.get('encoding')!='base64' or value.get('size',0)>1024*1024:raise ValueError('Unsupported data-branch file')
    return base64.b64decode(value['content'])


def publish(output,assets,expected_parent):
    output=Path(output)
    # A sibling maintainer edit must never be overwritten by a stale publisher.
    actual=api('git/ref/heads/'+BRANCH,missing=True)
    if (actual['object']['sha'] if actual else None)!=expected_parent:raise RuntimeError('Study resource branch changed; rerun against its new reviewed content')
    tree=[]
    for name in ('catalogue.json','topic-vocabulary.json','README.md','LICENSE'):
        blob=api('git/blobs',method='POST',data=dict(encoding='base64',content=base64.b64encode((output/name).read_bytes()).decode()))
        tree.append(dict(path=name,mode='100644',type='blob',sha=blob['sha']))
    parent_tree=api('git/commits/'+expected_parent)['tree']['sha'] if expected_parent else None
    tree_data=dict(tree=tree)
    if parent_tree:tree_data['base_tree']=parent_tree
    tree=api('git/trees',method='POST',data=tree_data)
    unchanged=bool(parent_tree==tree['sha'])
    commit={'sha':expected_parent} if unchanged else api('git/commits',method='POST',data=dict(message='Update verified study resource snapshots',tree=tree['sha'],parents=[expected_parent] if expected_parent else []))
    release=api('releases/tags/'+TAG,missing=True)
    if release is None:
        notes=output/'release-notes.md';notes.write_text('Verified OpenBible study-resource snapshots and independently maintained reviewed topic vocabulary. Current checked catalogue and attribution: https://github.com/icfmp/Bible/tree/data/study-resources . Applications retain their separate signed alpha releases and existing signing identity.\n')
        subprocess.run(['gh','release','create',TAG,'--repo',REPO,'--target',commit['sha'],'--prerelease','--latest=false','--title','Verified study resource archives','--notes-file',str(notes)],check=True)
    for asset in assets:
        release=api('releases/tags/'+TAG);existing=next((x for x in release['assets'] if x['name']==asset.name),None)
        digest='sha256:'+hashlib.sha256(asset.read_bytes()).hexdigest()
        if existing:
            if existing.get('digest')!=digest or existing['size']!=asset.stat().st_size:raise ValueError('Existing immutable study asset differs; it was not overwritten')
        else:
            subprocess.run(['gh','release','upload',TAG,str(asset),'--repo',REPO],check=True)
            release=api('releases/tags/'+TAG);existing=next(x for x in release['assets'] if x['name']==asset.name)
            if existing.get('digest')!=digest or existing['size']!=asset.stat().st_size:raise ValueError('Uploaded study asset failed digest verification')
    # GitHub enforces a non-forced fast-forward, including concurrent edits
    # arriving after the first parent check or during archive upload.
    latest=api('git/ref/heads/'+BRANCH,missing=True)
    if (latest['object']['sha'] if latest else None)!=expected_parent:raise RuntimeError('Data branch advanced during publication; its content was preserved')
    if unchanged:return expected_parent
    if expected_parent:api('git/refs/heads/'+BRANCH,method='PATCH',data=dict(sha=commit['sha'],force=False))
    else:api('git/refs',method='POST',data=dict(ref='refs/heads/'+BRANCH,sha=commit['sha']))
    return commit['sha']


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('output',type=Path)
    parser.add_argument('--vocabulary',type=Path);parser.add_argument('--references',type=Path);parser.add_argument('--topics',type=Path)
    parser.add_argument('--previous',type=Path);parser.add_argument('--vocabulary-only',action='store_true');parser.add_argument('--publish',action='store_true')
    args=parser.parse_args();parent=None;previous=args.previous.read_bytes() if args.previous else BUNDLED.read_bytes();vocabulary=args.vocabulary or VOCABULARY
    with tempfile.TemporaryDirectory(prefix='bible-study-update-') as temporary:
        temporary=Path(temporary)
        if args.publish:
            ref=api('git/ref/heads/'+BRANCH,missing=True);parent=ref['object']['sha'] if ref else None
            if args.vocabulary_only and parent is None:raise ValueError('Initialize checked indexes before a vocabulary-only update')
            if parent:
                previous=remote_file('catalogue.json',parent)
                if args.vocabulary is None:vocabulary=temporary/'vocabulary.json';vocabulary.write_bytes(remote_file('topic-vocabulary.json',parent))
        if not args.vocabulary_only:
            from bible.library import download
            for name,url,limit in [('references',REFERENCE_URL,REFERENCE_LIMIT),('topics',TOPIC_URL,TOPIC_LIMIT)]:
                if getattr(args,name) is None:
                    path=temporary/(name+'.zip')
                    with path.open('wb') as output:download(url,output,limit=limit)
                    setattr(args,name,path)
        assets,proof=prepare(args.output,vocabulary,references=None if args.vocabulary_only else args.references,topics=None if args.vocabulary_only else args.topics,previous=previous)
        if args.publish:print('Published data commit:',publish(args.output,assets,parent))
        print(json.dumps(proof,indent=2))
if __name__=='__main__':main()
