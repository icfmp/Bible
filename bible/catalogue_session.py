"""Plain-data Library preparation shared across close/reopen, without GTK/SWORD."""
from dataclasses import dataclass,replace
from threading import RLock
import time
from weakref import WeakMethod
from .metadata_workers import MetadataExecutor
from .catalogue_cache import CatalogueCache
from .providers import PROVIDERS
from .languages import language_info,search_terms,available_languages
from .book_names import normalized
from .study_resources import StudyResources


@dataclass(frozen=True)
class CatalogueSnapshot:
    resources: tuple
    installed: dict
    study_installed: frozenset
    study_current: frozenset
    languages: dict
    search: dict
    timings: dict
    errors: dict
    refreshing: bool
    generation: int


class CatalogueSession:
    def __init__(self,library):
        self.library=library;self.cache=CatalogueCache(library.root.parent/'catalogue-cache')
        self.study=StudyResources(library.root.parent/'study-data')
        self.prepare=MetadataExecutor(thread_name_prefix='bible-library-metadata')
        self.network=MetadataExecutor(thread_name_prefix='bible-library-refresh')
        self.lock=RLock();self.closed=False;self.listeners=[];self.snapshot=None
        self.providers={};self.installed={};self.study_installed=frozenset();self.study_current=frozenset()
        self.language_records={};self.metrics={};self.errors={};self.refreshing=False
        self.language_inventory=frozenset()
        self.language_future=None
        self.refresh_future=None;self.installed_future=None;self.revision=0;self.generation=0
        self.bootstrap_future=self.schedule(self.bootstrap)

    def schedule(self,function,*args):
        future=self.prepare.submit(function,*args)
        future.add_done_callback(self.preparation_failed)
        return future

    def preparation_failed(self,future):
        if future.cancelled():return
        error=future.exception()
        if error is None:return
        with self.lock:
            if self.closed:return
            base=self.snapshot or CatalogueSnapshot((),{},frozenset(),frozenset(),{},{},{},{},False,self.generation)
            snapshot=replace(base,errors={**base.errors,'Library':str(error)},refreshing=False,generation=self.generation)
            self.snapshot=snapshot;listeners=[r() for r in self.listeners if r() is not None]
        for callback in listeners:callback(snapshot)

    def subscribe(self,callback):
        reference=WeakMethod(callback)
        with self.lock:self.listeners.append(reference);snapshot=self.snapshot
        if snapshot:callback(snapshot)

    def unsubscribe(self,callback):
        with self.lock:self.listeners=[r for r in self.listeners if r() is not None and r()!=callback]

    def scan_installed(self):
        start=time.monotonic();installed={};errors={}
        for name in self.library.installed():
            if self.closed:return
            try:installed[name]=self.library.resource(name)
            except Exception as error:errors[name]=str(error)
        study_installed=frozenset(self.study.installed())
        study_current=frozenset(name for name in study_installed if self.study.current(name))
        with self.lock:
            self.installed=installed;self.study_installed=study_installed;self.study_current=study_current
            self.metrics['installed_scan_seconds']=time.monotonic()-start
            if errors:self.metrics['installed_metadata_errors']=errors

    def bootstrap(self):
        start=time.monotonic();providers={}
        for provider in PROVIDERS:
            if self.closed:return
            value=self.cache.read(provider)
            if value is not None:providers[provider.id]=value[0]
        with self.lock:self.providers=providers;self.metrics['cache_read_seconds']=time.monotonic()-start
        self.scan_installed();self.publish()

    def load_languages(self):
        """Complete offline ISO choices on demand, independently of catalogue IO."""
        with self.lock:
            if self.closed or self.language_future:return self.language_future
            def prepare():
                self.language_inventory=available_languages();self.publish()
            self.language_future=self.schedule(prepare)
            return self.language_future

    def reload_installed(self):
        def work():
            self.scan_installed();self.publish()
        with self.lock:
            if self.closed:return None
            if self.installed_future and not self.installed_future.done():return self.installed_future
            self.installed_future=self.schedule(work)
            return self.installed_future

    def refresh(self,fetch,force,providers=PROVIDERS):
        with self.lock:
            if self.closed:return None
            if self.refresh_future and not self.refresh_future.done():return self.refresh_future
            if self.bootstrap_future.done() and self.bootstrap_future.exception() is not None:
                self.bootstrap_future=self.schedule(self.bootstrap)
            self.refreshing=True;self.errors={};self.generation+=1
            self.refresh_future=self.network.submit(self.fetch,fetch,force,tuple(providers))
            return self.refresh_future

    def fetch(self,fetch,force,providers):
        def provider_ready(provider,items,error,timings):
            with self.lock:
                if self.closed:return
                self.providers[provider.id]=tuple(items)
                if error:self.errors[provider.name]=str(error)
                self.metrics[provider.id]=dict(timings);self.revision+=1;revision=self.revision
            self.schedule(self.publish,revision)
        try:
            self.bootstrap_future.result()
            if self.closed:return
            result=fetch(providers=providers,on_provider=provider_ready,cache=self.cache,force=force)
            resources=getattr(result,'resources',result)
            with self.lock:
                if self.closed:return
                self.providers.update({p.id:tuple(r for r in resources if r.provider_id==p.id) for p in providers})
                self.errors=dict(getattr(result,'errors',{}))
        except Exception as error:
            with self.lock:self.errors={'Library':str(error)}
        finally:
            with self.lock:
                self.refreshing=False
                if not self.closed:self.schedule(self.publish)

    def publish(self,revision=None):
        with self.lock:
            if self.closed or revision is not None and revision!=self.revision:return
            resources=tuple(sorted((r for rows in self.providers.values() for r in rows),key=lambda r:(r.language,r.name,r.provider_id)))
            installed=dict(self.installed);study_installed=self.study_installed;study_current=self.study_current
            metrics=dict(self.metrics);errors=dict(self.errors);refreshing=self.refreshing;generation=self.generation
        start=time.monotonic();all_resources=(*resources,*installed.values(),*self.study.available())
        languages={r.language for r in all_resources}|self.language_inventory
        for code in languages:
            if self.closed:return
            if code not in self.language_records:
                name,native=language_info(code)
                display=name+((' — '+native) if native and native.casefold()!=name.casefold() else '')+f' ({code})'
                self.language_records[code]=(name,display,normalized(search_terms(code)))
        records={code:self.language_records[code] for code in languages}
        terms={r.id:normalized(' '.join((r.name,r.description,r.language,records[r.language][2]))) for r in all_resources}
        metrics['language_and_search_seconds']=time.monotonic()-start
        snapshot=CatalogueSnapshot(resources,installed,study_installed,study_current,records,terms,metrics,errors,refreshing,generation)
        with self.lock:
            if self.closed:return
            self.snapshot=snapshot;listeners=[ref() for ref in self.listeners if ref() is not None]
        for callback in listeners:callback(snapshot)

    def close(self):
        with self.lock:self.closed=True;self.listeners=[]
        self.prepare.shutdown(wait=False,cancel_futures=True);self.network.shutdown(wait=False,cancel_futures=True)
