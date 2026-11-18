"""Small durable request list; existing installers own transfer and validation."""
from dataclasses import asdict,dataclass
import hashlib,json
from pathlib import Path
from .library import Resource
from .study_resources import StudyResource
from .study_catalogue import atomic_write


class QueueConflict(ValueError):
    pass


@dataclass
class DownloadRequest:
    resource: object
    operation: str='install'
    permission: str|None=None
    state: str='queued'
    error: str=''

    @property
    def key(self):
        r=self.resource
        return (r.provider_id,r.id,getattr(r,'version',''),self.operation,
                hashlib.sha256(getattr(r,'acquisition',r.revision if r.kind=='study' else '').encode()).hexdigest())


class DownloadQueue:
    """Main-thread owned. Recovered requests wait for an explicit Resume click."""
    def __init__(self,path):
        self.path=Path(path);self.requests=[];self.error=None
        try:
            if self.path.is_symlink():raise ValueError('Queue file is a symbolic link')
            if not self.path.exists():return
            if self.path.stat().st_size>32*1024*1024:raise ValueError('Queue file is too large')
            data=json.loads(self.path.read_text())
            if not isinstance(data,dict) or data.get('format')!=1 or not isinstance(data.get('requests'),list):raise ValueError('Invalid queue format')
            for row in data['requests']:
                if not isinstance(row,dict) or not isinstance(row.get('resource'),dict):raise ValueError('Invalid queued resource')
                factory=StudyResource if row['kind']=='study' else Resource if row['kind']=='native' else None
                if factory is None:raise ValueError('Invalid queued resource type')
                if any(type(v) is not bool if k in ('locked','installable') else not isinstance(v,str)
                       for k,v in row['resource'].items()):raise ValueError('Invalid resource metadata')
                request=DownloadRequest(factory(**row['resource']),row['operation'],row.get('permission'),row['state'],row.get('error',''))
                if request.operation not in ('install','update') or request.state not in ('queued','active','paused','failed'):raise ValueError('Invalid queued operation')
                if request.permission is not None and (not isinstance(request.permission,str) or len(request.permission)!=64):raise ValueError('Invalid source acknowledgement')
                if not isinstance(request.error,str) or len(request.error)>4096:raise ValueError('Invalid queue diagnostic')
                if request.resource.kind=='study':
                    from .study_resources import REFERENCE_RESOURCE_ID,PLACE_RESOURCE_ID,TOPIC_RESOURCE_ID,STEP_RESOURCE_ID
                    if request.resource.id not in (REFERENCE_RESOURCE_ID,PLACE_RESOURCE_ID,TOPIC_RESOURCE_ID,STEP_RESOURCE_ID):raise ValueError('Unknown study resource')
                request.resource.id;request.key
                if request.state!='failed':request.state='paused'
                if self.find(request.resource.id):raise ValueError('Duplicate queue target')
                self.requests.append(request)
        except (OSError,ValueError,TypeError,KeyError,RecursionError) as error:
            self.requests=[];self.error=str(error)

    def save(self):
        if self.error:raise ValueError('Download queue could not be recovered: '+self.error)
        if self.path.is_symlink():raise ValueError('Queue file is a symbolic link')
        data=dict(format=1,requests=[dict(kind='study' if r.resource.kind=='study' else 'native',
            resource=asdict(r.resource),operation=r.operation,permission=r.permission,state=r.state,error=r.error) for r in self.requests])
        encoded=json.dumps(data).encode()
        if len(encoded)>32*1024*1024:raise ValueError('Download queue is too large')
        atomic_write(self.path,encoded)

    def find(self,identifier):
        return next((r for r in self.requests if r.resource.id==identifier),None)

    def enqueue(self,resource,permission=None,operation='install'):
        if self.error:raise ValueError('Download queue could not be recovered: '+self.error)
        existing=self.find(resource.id)
        request=DownloadRequest(resource,operation,permission)
        if existing and existing.state!='failed':
            if existing.key!=request.key:raise QueueConflict('A different edition or operation for this resource is already queued.')
            return existing
        if existing:position=self.requests.index(existing);self.requests[position]=request
        else:self.requests.append(request)
        try:self.save()
        except BaseException:
            if existing:self.requests[position]=existing
            else:self.requests.remove(request)
            raise
        return request

    def start(self):
        if any(r.state=='active' for r in self.requests):return None
        request=next((r for r in self.requests if r.state=='queued'),None)
        if request:
            request.state='active'
            try:self.save()
            except BaseException:request.state='queued';raise
        return request

    def finish(self,request):
        if request not in self.requests:return
        position=self.requests.index(request);self.requests.remove(request)
        try:self.save()
        except BaseException:self.requests.insert(position,request);raise

    def cancel(self,identifier):
        request=self.find(identifier)
        if request and request.state!='active':self.finish(request);return True
        return False

    def fail(self,request,error):
        request.state='failed';request.error=str(error)[:4096];self.save()

    def pause(self):
        for request in self.requests:
            if request.state!='failed':request.state='paused'
        self.save()

    def resume(self):
        for request in self.requests:
            if request.state=='paused':request.state='queued'
        self.save()
