"""Bounded background SWORD/Pango preparation; GTK stays on its owning thread."""
from collections import OrderedDict
from concurrent.futures import CancelledError, ThreadPoolExecutor
from dataclasses import replace
from threading import Event, Lock
import gi
gi.require_version('Pango','1.0')
gi.require_version('PangoCairo','1.0')
from gi.repository import Pango,PangoCairo
from .paged_sources import PagedStream,PageAddress
from .pagination import paginate
from .preparation import checkpoint


class LayoutContext:
    """A private worker font map, never a Gtk widget shared across threads."""
    def __init__(self,resolution,language,*,round_positions=True,font_options=None):
        self.font_map=PangoCairo.FontMap.new()
        self.font_map.set_resolution(resolution if resolution>0 else 96)
        self.context=self.font_map.create_context()
        self.context.set_language(Pango.Language.from_string(language))
        self.context.set_round_glyph_positions(round_positions)
        if font_options is not None:PangoCairo.context_set_font_options(self.context,font_options)

    def create_pango_layout(self,text):
        layout=Pango.Layout.new(self.context);layout.set_text(text,-1);return layout

    def get_pango_context(self):return self.context


class BookStream(PagedStream):
    def __init__(self,widget,source,preferences):
        super().__init__(widget,source,preferences)
        context=widget.get_pango_context()
        self.resolution=PangoCairo.context_get_resolution(context)
        self.language=context.get_language().to_string()
        self.round_positions=context.get_round_glyph_positions()
        options=PangoCairo.context_get_font_options(context)
        # An independent immutable snapshot, never a GTK context in the worker.
        self.font_options=options.copy() if options is not None else None
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='bible-pages')
        self.futures={};self.errors={};self.error=None;self.pending=None
        self.requested_anchor=None;self.spread_count=2;self.closed=False
        self.cancellations={}
        # Caches belong to this resource/stream, never to a persisted profile.
        # Documents depend only on number visibility; plans additionally depend
        # on geometry, typography and the canonical reflow partition.
        self.documents=OrderedDict();self.plans=OrderedDict();self._cache_lock=Lock()
        self._worker_source=None;self._worker_layout=None
        self._configuration=None

    @staticmethod
    def document_signature(key,preferences):
        return key,preferences.chapter_numbers,preferences.verse_numbers

    def _remember(self,cache,key,value,cancelled=None):
        with self._cache_lock:
            checkpoint(cancelled)
            cache[key]=value;cache.move_to_end(key)
            while len(cache)>3:cache.popitem(last=False)

    def build(self,key,preferences,width,height,anchor,cancelled=None):
        checkpoint(cancelled)
        signature=self.document_signature(key,preferences)
        plan_key=(signature,preferences.font,preferences.size,preferences.line_spacing,
                  width,height,anchor)
        with self._cache_lock:
            plan=self.plans.get(plan_key)
            if plan is not None:
                self.plans.move_to_end(plan_key);return plan
            document=self.documents.get(signature)
            if document is not None:self.documents.move_to_end(signature)
        if document is None:
            if self._worker_source is None:self._worker_source=self.source.clone()
            checkpoint(cancelled)
            document=self._worker_source.document(key,preferences,cancelled=cancelled)
            checkpoint(cancelled)
            self._remember(self.documents,signature,document,cancelled)
        if self._worker_layout is None:
            self._worker_layout=LayoutContext(self.resolution,self.language,
                round_positions=self.round_positions,font_options=self.font_options)
        # The requested anchor chooses the containing spread, not an artificial
        # page break. Keep it separately for exact reflow/exit restoration.
        plan=paginate(self._worker_layout,document,preferences,width,height,None,cancelled=cancelled)
        checkpoint(cancelled)
        self._remember(self.plans,plan_key,plan,cancelled)
        return plan

    def request(self,key):
        if self.closed:return
        if key not in self.cache and key not in self.futures and key not in self.errors:
            event=Event();self.cancellations[key]=event
            self.futures[key]=self.executor.submit(self.build,key,replace(self.preferences),
                                                   self.width,self.height,self.partitions.get(key),event.is_set)

    def plan(self,key):
        self.request(key)
        return self.cache.get(key)

    def _cancel(self,key):
        self.cancellations.pop(key).set()
        self.futures.pop(key).cancel()

    def cancel_pending(self):
        for key in list(self.futures):self._cancel(key)
        self.pending=None

    def configure(self,width,height,anchor,key):
        if self.closed:return
        width,height=max(20,width),max(20,height)
        p=self.preferences
        configuration=(key,width,height,anchor,p.font,p.size,p.line_spacing,p.chapter_numbers,p.verse_numbers)
        if configuration==self._configuration and (self.pending==key or
                (self.cursor and self.cursor.key==key and self.requested_anchor==anchor)):return
        self._configuration=configuration
        self.cancel_pending()
        self.errors={};self.error=None
        self.width=width;self.height=height
        self.cache.clear();self.partitions={key:anchor};self.cursor=None
        self._retain_books(key)
        self.pending=key;self.requested_anchor=anchor;self.request(key)

    def _retain_books(self,key):
        neighbours=[self.source.neighbour(key,direction) for direction in (1,-1)]
        retained={key,*(n for n in neighbours if n is not None)}
        for old in list(self.futures):
            if old not in retained:self._cancel(old)
        for old in list(self.cache):
            if old not in retained:del self.cache[old]
        with self._cache_lock:
            for old in list(self.documents):
                if old[0] not in retained:del self.documents[old]
            for old in list(self.plans):
                if old[0][0] not in retained:del self.plans[old]
        return neighbours

    def _prefetch(self,key):
        neighbours=self._retain_books(key)
        for neighbour in neighbours:
            if neighbour is not None:self.request(neighbour)

    def poll(self):
        if self.closed:return None
        changed=None
        for key,future in list(self.futures.items()):
            if not future.done():continue
            del self.futures[key];self.cancellations.pop(key)
            try:self.cache[key]=future.result()
            except CancelledError:continue
            except Exception as error:
                self.errors[key]=str(error)
                if key==self.pending:self.error=str(error);self.pending=None;changed='current'
                continue
            if key==self.pending:
                plan=self.cache[key];index=plan.page_for_anchor(self.requested_anchor)
                if self.spread_count==2:index=index//2*2
                self.cursor=PageAddress(key,index);self.pending=None;changed='current'
                # Prefetch after collecting this batch: pruning may otherwise
                # invalidate the futures snapshot currently being iterated.
            elif changed is None:changed='controls'
        if changed=='current' and self.cursor:self._prefetch(self.cursor.key)
        while len(self.cache)>3:
            key=next(iter(self.cache))
            if self.cursor and key==self.cursor.key:self.cache.move_to_end(key);continue
            self.cache.pop(key)
        return changed

    def step(self,address,direction):
        plan=self.plan(address.key)
        if plan is None:return None
        index=address.index+direction
        if 0<=index<len(plan.pages):return PageAddress(address.key,index)
        key=self.source.neighbour(address.key,direction)
        if key is None:return None
        plan=self.plan(key)
        if plan is None:return None
        return PageAddress(key,len(plan.pages)-1 if direction<0 else 0)

    def spread(self,count):
        if not self.cursor:return []
        result=[self.cursor]
        for _ in range(count-1):
            after=self.step(result[-1],1)
            if after is None or after.key!=self.cursor.key:break
            result.append(after)
        return result

    def turn(self,direction,count):
        if not self.cursor:return False
        if direction<0 and count==2 and self.cursor.index<2:
            before=self.step(PageAddress(self.cursor.key,0),-1)
            if self.cursor.index==1:before=PageAddress(self.cursor.key,0)
            elif before:before=PageAddress(before.key,before.index//2*2)
            if before is None:return False
            self.cursor=before
        elif not super().turn(direction,count):return False
        self.requested_anchor=None;self._prefetch(self.cursor.key);return True

    def anchor(self):
        return self.requested_anchor or super().anchor()

    def close(self):
        self.closed=True
        self.cancel_pending()
        # Cooperative cancellation stops at the next native-operation boundary;
        # join before a disposable profile can remove SWORD's backing files.
        self.executor.shutdown(wait=True,cancel_futures=True)
        self.pending=None;self.cache.clear()
        with self._cache_lock:self.documents.clear();self.plans.clear()
        self._worker_source=None;self._worker_layout=None
