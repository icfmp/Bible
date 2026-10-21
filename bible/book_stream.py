"""Bounded background SWORD/Pango preparation; GTK stays on its owning thread."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import gi
gi.require_version('PangoCairo','1.0')
from gi.repository import Pango,PangoCairo
from .paged_sources import PagedStream,PageAddress
from .pagination import paginate


class LayoutContext:
    """A private worker font map, never a Gtk widget shared across threads."""
    def __init__(self,resolution,language):
        self.font_map=PangoCairo.FontMap.new()
        self.font_map.set_resolution(resolution if resolution>0 else 96)
        self.context=self.font_map.create_context()
        self.context.set_language(Pango.Language.from_string(language))

    def create_pango_layout(self,text):
        layout=Pango.Layout.new(self.context);layout.set_text(text,-1);return layout

    def get_pango_context(self):return self.context


class BookStream(PagedStream):
    def __init__(self,widget,source,preferences):
        super().__init__(widget,source,preferences)
        context=widget.get_pango_context()
        self.resolution=PangoCairo.context_get_resolution(context)
        self.language=context.get_language().to_string()
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='bible-pages')
        self.futures={};self.errors={};self.error=None;self.pending=None
        self.requested_anchor=None;self.spread_count=2;self.closed=False

    def build(self,key,preferences,width,height,anchor):
        source=self.source.clone()  # Its own SWMgr/VerseKey, not the visible reader.
        document=source.document(key,preferences)
        layout=LayoutContext(self.resolution,self.language)
        return paginate(layout,document,preferences,width,height,anchor)

    def request(self,key):
        if key not in self.cache and key not in self.futures and key not in self.errors:
            self.futures[key]=self.executor.submit(self.build,key,replace(self.preferences),
                                                   self.width,self.height,self.partitions.get(key))

    def plan(self,key):
        self.request(key)
        return self.cache.get(key)

    def configure(self,width,height,anchor,key):
        for future in self.futures.values():future.cancel()
        self.futures={};self.errors={};self.error=None
        self.width=max(20,width);self.height=max(20,height)
        self.cache.clear();self.partitions={key:anchor};self.cursor=None
        self.pending=key;self.requested_anchor=anchor;self.request(key)

    def poll(self):
        if self.closed:return None
        changed=None
        for key,future in list(self.futures.items()):
            if not future.done():continue
            del self.futures[key]
            try:self.cache[key]=future.result()
            except Exception as error:
                self.errors[key]=str(error)
                if key==self.pending:self.error=str(error);self.pending=None;changed='current'
                continue
            if key==self.pending:
                plan=self.cache[key];index=plan.containing(plan.document.locate(self.requested_anchor))
                if self.spread_count==2:index=index//2*2
                self.cursor=PageAddress(key,index);self.pending=None;changed='current'
                # Only adjacent books are prepared, never the whole translation.
                for direction in (1,-1):
                    neighbour=self.source.neighbour(key,direction)
                    if neighbour is not None:self.request(neighbour)
            elif changed is None:changed='controls'
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
        self.requested_anchor=None;return True

    def anchor(self):
        return self.requested_anchor or super().anchor()

    def close(self):
        self.closed=True
        # Join before a disposable profile can remove SWORD's backing files.
        self.executor.shutdown(wait=True,cancel_futures=True)
