"""On-demand pilot edition: returned metadata/ZIP, isolated conversion, atomic commit.

No application key, account impersonation or remote agreement submission. The
user's acknowledgement is local and is bound to the exact displayed metadata.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime,timezone

from .providers import YOUVERSION
from .youversion_source import read_edition
from .youversion_editions import EDITIONS,METADATA_URL,module_id,edition_id
from .i18n import tr

MAX_ZIP = 32 * 1024 * 1024


def serialized(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def write_receipt(path,value):
    temporary=None
    try:
        with tempfile.NamedTemporaryFile('w',dir=path.parent,prefix='.receipt-',delete=False) as output:
            temporary=Path(output.name);output.write(serialized(value));output.flush();os.fsync(output.fileno())
        os.replace(temporary,path)
    finally:
        if temporary:temporary.unlink(missing_ok=True)


def resource_from_metadata(value,expected_id=21):
    from .library import Resource
    name=module_id(expected_id)
    edition = read_edition(value,expected_id)
    if edition.language!=EDITIONS[expected_id][2]:raise ValueError('Unexpected edition language')
    policy = edition.metadata.get('offline') or {}
    # Pilot only. New editions or numbering systems require separate fidelity
    # and numbering validation, rather than being silently treated as KJV.
    if edition.metadata.get('vrs') != EDITIONS[expected_id][0]:
        raise ValueError('Unsupported source numbering')
    notices=[edition.attribution]
    for notice_key in ('copyright_long','reader_footer'):
        notice=edition.metadata.get(notice_key)
        if isinstance(notice,dict) and isinstance(notice.get('text'),str) and notice['text'] not in notices:notices.append(notice['text'])
    conditions = '\n\n'.join(notices)+'\n\n'+serialized(policy)
    return Resource(name,edition.title,edition.language,'Source conditions apply',
        about='https://www.bible.com/versions/'+str(expected_id), conditions=conditions,
        driver='RawText',
        source=YOUVERSION.name,source_url=YOUVERSION.url,
        versification=EDITIONS[expected_id][1],provider_id=YOUVERSION.id,
        acquisition=serialized(edition.metadata))


def acknowledgement(resource):
    return hashlib.sha256(resource.acquisition.encode()).hexdigest()


def catalogue(timings=None):
    """Fetch only the seven reviewed metadata records, with bounded concurrency."""
    from concurrent.futures import as_completed
    from .metadata_workers import MetadataExecutor
    from .library import download
    def fetch(identifier):
        data=io.BytesIO();download(METADATA_URL.format(edition=identifier),data,
                                  limit=2*1024*1024,same_origin=True)
        return resource_from_metadata(json.loads(data.getvalue()),identifier),data.tell()
    resources=[];errors={};size=0;start=time.monotonic()
    with MetadataExecutor(max_workers=2,thread_name_prefix='bible-edition-metadata') as executor:
        pending={executor.submit(fetch,identifier):identifier for identifier in EDITIONS}
        for future in as_completed(pending):
            identifier=pending[future]
            try:
                item,received=future.result();resources.append(item);size+=received
            except Exception as error:errors[str(identifier)]=str(error)
    if timings is not None:timings.update(requests=len(EDITIONS),metadata_bytes=size,
        network_seconds=time.monotonic()-start,edition_errors=errors,validators={})
    if not resources:raise OSError('; '.join(f'{key}: {value}' for key,value in errors.items()))
    return sorted(resources,key=lambda item:(item.language,item.description))


def checkpoint(cancelled):
    if cancelled():raise OSError(tr('Download cancelled.'))


def open_response(opener,request,cancelled):
    from email.utils import parsedate_to_datetime
    for attempt in range(3):
        checkpoint(cancelled)
        try:return opener(request,timeout=30)
        except urllib.error.HTTPError as error:
            if error.code not in (429,502,503,504) or attempt==2:raise
            raw=error.headers.get('Retry-After','')
            try:delay=float(raw)
            except ValueError:
                try:delay=parsedate_to_datetime(raw).timestamp()-time.time()
                except (TypeError,ValueError,OverflowError):delay=2**attempt
            # Honour long provider delays by ending the attempt, rather than
            # retrying earlier than requested or blocking cancellation.
            if delay>30:raise
            deadline=time.monotonic()+max(0,delay)
            while time.monotonic()<deadline:
                checkpoint(cancelled);time.sleep(min(.1,max(0,deadline-time.monotonic())))


class SourceRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        from urllib.parse import urlsplit
        old,new=urlsplit(request.full_url),urlsplit(newurl)
        if new.scheme!='https' or new.netloc!=old.netloc:
            raise ValueError('Unexpected source redirect')
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def cached_download(url, cache, progress, cancelled, *, opener=None):
    """Resume only this exact returned URL, with a strong server validator.

    Incomplete bytes are never compiled. Completed packages are retained for
    retrying conversion without requesting a redownload from the provider.
    """
    opener=opener or urllib.request.build_opener(SourceRedirect()).open
    cache.mkdir(parents=True,exist_ok=True,mode=0o700)
    key=hashlib.sha256(url.encode()).hexdigest()
    path=cache/(key+'.zip');receipt=cache/(key+'.json')
    if path.is_symlink() or receipt.is_symlink():raise ValueError('Unsafe cache path')
    state={}
    try:
        if receipt.stat().st_size<4096:state=json.loads(receipt.read_text())
    except (OSError,ValueError):pass
    if not isinstance(state,dict):state={}
    if path.is_file() and state.get('complete') and state.get('url')==url:
        if path.stat().st_size<=MAX_ZIP and hashlib.sha256(path.read_bytes()).hexdigest()==state.get('sha256'):
            progress(path.stat().st_size,path.stat().st_size);checkpoint(cancelled);return path
        # A damaged completed cache is not a valid resumable prefix. Restart
        # this derived package only, leaving installed resources untouched.
        state={}
    start=path.stat().st_size if path.is_file() and state.get('url')==url and state.get('etag') else 0
    if start>MAX_ZIP:raise ValueError('Download too large')
    headers={'User-Agent':'Bible/0.1'}
    if start:headers.update(Range=f'bytes={start}-',**{'If-Range':state['etag']})
    request=urllib.request.Request(url,headers=headers)
    checkpoint(cancelled)
    with open_response(opener,request,cancelled) as response:
        if response.url!=url:raise ValueError('Unexpected source response URL')
        status=response.status
        if status==206:
            import re
            match=re.fullmatch(r'bytes ([0-9]+)-([0-9]+)/([0-9]+)',response.headers.get('Content-Range',''))
            if not start or not match or int(match[1])!=start or int(match[2])+1!=int(match[3]):
                raise ValueError('Invalid resumed response')
            total=int(match[3])
            if response.headers.get('ETag')!=state.get('etag'):raise ValueError('Source changed during resume')
        elif status==200:
            start=0;total=int(response.headers.get('Content-Length',0))
        else:raise ValueError('Unexpected source HTTP status')
        if total<0 or total>MAX_ZIP:raise ValueError('Download too large')
        etag=response.headers.get('ETag','')
        import re
        if len(etag)>512 or not re.fullmatch(r'"[\x21\x23-\x7e\x80-\xff]*"',etag):etag=''
        state={'url':url,'etag':etag,'complete':False}
        write_receipt(receipt,state)
        done=start;deadline=time.monotonic()+180
        with path.open('ab' if start else 'wb') as output:
            progress(done,total)
            read=getattr(response,'read1',response.read)
            while True:
                checkpoint(cancelled)
                chunk=read(64*1024)
                if not chunk:break
                done+=len(chunk)
                if done>MAX_ZIP or time.monotonic()>deadline:raise ValueError('Download limit exceeded')
                output.write(chunk);progress(done,total)
            output.flush();os.fsync(output.fileno())
        if total and done!=total:raise ValueError('Incomplete download')
        checkpoint(cancelled)
        state.update(complete=True,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                     acquired_at=datetime.now(timezone.utc).isoformat())
        write_receipt(receipt,state)
        return path


def run_conversion(archive,metadata,target,phase,cancelled,*,compiler='/app/bin/osis2mod',edition=21):
    """A separate process owns all temporary Python/native conversion heaps."""
    module_id(edition)
    command=[sys.executable,'-m','bible.youversion_worker',str(archive),str(metadata),str(target),compiler,str(edition)]
    with tempfile.TemporaryFile() as errors:
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=errors,start_new_session=True)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout,selectors.EVENT_READ)
                pending=b''
                while selector.get_map():
                    checkpoint(cancelled)
                    for selected,_ in selector.select(.1):
                        chunk=os.read(selected.fileobj.fileno(),8192)
                        if not chunk:selector.unregister(selected.fileobj);break
                        pending+=chunk
                        if len(pending)>65536:raise ValueError('Invalid conversion progress')
                        while b'\n' in pending:
                            line,pending=pending.split(b'\n',1)
                            value=json.loads(line)
                            phase(value['phase'],value['done'],value['total'])
            if process.wait()!=0:
                # Compiler/source bodies stay private; no corpus in UI or logs.
                raise ValueError(tr('Translation conversion or verification failed. No resource was installed.'))
        finally:
            if process.poll() is None:
                os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=3)
                except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait()
            process.stdout.close()


def install(library,resource,progress,installing,cancelled,phase,permission):
    from .library import download
    identifier=edition_id(resource.name)
    if permission!=acknowledgement(resource):
        raise ValueError(tr('Confirm the source conditions before downloading.'))
    checkpoint(cancelled)
    current=io.BytesIO();download(METADATA_URL.format(edition=identifier),current,limit=2*1024*1024,same_origin=True)
    actual=resource_from_metadata(json.loads(current.getvalue()),identifier)
    if actual.acquisition!=resource.acquisition:
        raise ValueError(tr('Source conditions or edition changed. Refresh the catalogue and review them again.'))
    edition=read_edition(json.loads(actual.acquisition),identifier)
    if not edition.archive_url:raise ValueError('No offline package supplied by the source')
    archive=cached_download(edition.archive_url,library.root.parent/'cache/youversion',progress,cancelled)
    with tempfile.TemporaryDirectory(prefix='.install-',dir=library.root) as temporary:
        stage=Path(temporary);metadata=stage/'metadata.json';metadata.write_text(actual.acquisition)
        target=stage/'content'
        run_conversion(archive,metadata,target,phase,cancelled,edition=identifier)
        checkpoint(cancelled)
        installing()  # Only the short atomic commit becomes non-cancellable.
        source={'provider_id':YOUVERSION.id,'module_name':resource.name,
                'source':YOUVERSION.name,'url':YOUVERSION.url,'acquisition':actual.acquisition,
                'source_versification':edition.metadata['vrs'],'storage_versification':actual.versification,
                'local_permission_acknowledgement':permission,
                'provider_agreement_submitted':False}
        source.update(parser_version=1,installed_at=datetime.now(timezone.utc).isoformat())
        (target/'.source.json').write_text(serialized(source),encoding='utf-8')
        (target/'.complete').write_text(resource.id,encoding='utf-8')
        destination=library.root/resource.id
        if destination.exists():raise ValueError('Resource directory already exists')
        os.rename(target,destination)
