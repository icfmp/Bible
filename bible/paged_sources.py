"""Bounded, on-demand chapter/entry sources for the native paginated reader."""
from collections import OrderedDict
from dataclasses import dataclass
from .pagination import Anchor,Document,PassageSpan,StyleSpan,paginate
from .book_names import display_name
from .i18n import LANGUAGE
from .verse_typography import first_word_length


class BiblePages:
    kind='bible'
    def __init__(self,reader,resource):self.reader=reader;self.resource=resource
    def key(self,reference):return self.reader.key(reference).getOSISRef().rsplit('.',1)[0]
    def document(self,key,preferences):
        chapter=self.reader.chapter(key+'.1');structured=self.reader.structured_chapter(chapter)
        native=self.reader.key(key+'.1')
        title=display_name(native.getOSISBookName(),native.getBookName(),LANGUAGE)
        if preferences.chapter_numbers:title+=' '+str(native.getChapter())
        pieces=[title+'\n\n'];styles=[StyleSpan('chapter',0,len(title))];spans=[];offset=len(pieces[0])
        for reference,plain in chapter.verses:
            start=offset if spans else 0
            segments=structured[reference]
            for segment in segments:
                if segment.kind=='heading' and segment.text.strip():
                    text=segment.text.strip()+'\n';pieces.append(text)
                    styles.append(StyleSpan('heading',offset,offset+len(text)));offset+=len(text)
            body=''.join(s.text for s in segments if s.kind!='heading')
            leading=body[:len(body)-len(body.lstrip())]
            if leading:pieces.append(leading);offset+=len(leading);body=body[len(leading):]
            number=reference.rsplit('.',1)[-1]+' ' if preferences.verse_numbers else ''
            if number:styles.append(StyleSpan('number',offset,offset+len(number)))
            pieces.append(number);offset+=len(number);body_start=offset
            pieces.append(body);offset+=len(body)
            if number:styles.append(StyleSpan('verse-start',body_start-len(number),body_start+first_word_length(body)))
            spans.append(PassageSpan(reference,start,body_start,offset))
            if not body.endswith('\n'):pieces.append(' ');offset+=1
        original=''.join(pieces)
        display=list(original)
        for style in styles:
            if style.kind=='verse-start':
                for index in range(style.start,style.end):
                    if display[index].isspace():display[index]='\u00a0'
        return Document(key,''.join(display),tuple(spans),tuple(styles),original)
    def neighbour(self,key,direction):
        before,after=self.reader.neighbours(key+'.1')
        reference=before if direction<0 else after
        return self.key(reference) if reference else None
    @property
    def rtl(self):return self.reader.rtl


class CommentaryPages:
    kind='commentary'
    def __init__(self,reader,resource):self.reader=reader;self.resource=resource
    def key(self,reference):return self.reader.index.locate(reference)
    def document(self,key,preferences):
        section=self.reader.index.sections[key]
        text=self.reader.index.text(key)
        reference=section.start if not section.introduction else '@'+str(section.index)
        return Document(key,text,(PassageSpan(reference,0,0,len(text)),))
    def neighbour(self,key,direction):return None  # Page navigation stops at entry boundaries.
    def entry_neighbour(self,key,direction):
        position=key+direction
        return position if 0<=position<len(self.reader.index.sections) else None
    @property
    def rtl(self):return self.reader.rtl


@dataclass(frozen=True)
class PageAddress:
    key: object
    index: int


class PagedStream:
    def __init__(self,widget,source,preferences):
        self.widget=widget;self.source=source;self.preferences=preferences
        self.width=400;self.height=500;self.cache=OrderedDict();self.partitions={};self.cursor=None

    def plan(self,key):
        if key not in self.cache:
            document=self.source.document(key,self.preferences)
            self.cache[key]=paginate(self.widget,document,self.preferences,self.width,self.height,self.partitions.get(key))
            while len(self.cache)>5:self.cache.popitem(last=False)
        self.cache.move_to_end(key)
        return self.cache[key]

    def configure(self,width,height,anchor,key):
        self.width=max(20,width);self.height=max(20,height);self.cache.clear();self.partitions.clear()
        self.partitions[key]=anchor
        plan=self.plan(key);self.cursor=PageAddress(key,plan.containing(plan.document.locate(anchor)))

    def step(self,address,direction):
        plan=self.plan(address.key);index=address.index+direction
        if 0<=index<len(plan.pages):return PageAddress(address.key,index)
        key=self.source.neighbour(address.key,direction)
        if key is None:return None
        return PageAddress(key,len(self.plan(key).pages)-1 if direction<0 else 0)

    def spread(self,count):
        addresses=[self.cursor]
        for _ in range(count-1):
            after=self.step(addresses[-1],1)
            if after is None:break
            addresses.append(after)
        return addresses

    def turn(self,direction,count):
        if direction<0:
            address=self.cursor
            for _ in range(count):
                before=self.step(address,-1)
                if before is None:break
                address=before
            if address==self.cursor:return False
        else:
            address=self.step(self.spread(count)[-1],1)
            if address is None:return False
        self.cursor=address;return True

    def anchor(self):
        plan=self.plan(self.cursor.key);page=plan.pages[self.cursor.index]
        return plan.document.anchor(page.start)
