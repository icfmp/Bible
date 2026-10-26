"""Bounded, on-demand chapter/entry sources for the native paginated reader."""
from collections import OrderedDict
from dataclasses import dataclass, replace
from .pagination import Anchor,Document,PassageSpan,StyleSpan,paginate
from .book_names import display_name
from .i18n import LANGUAGE
from .verse_typography import first_word_length
from .preparation import checkpoint


class BiblePages:
    kind='bible'
    def __init__(self,reader,resource):self.reader=reader;self.resource=resource
    def key(self,reference):return self.reader.key(reference).getOSISRef().rsplit('.',1)[0]
    def document(self,key,preferences,*,cancelled=None):
        checkpoint(cancelled)
        chapter=self.reader.chapter(key+'.1',cancelled=cancelled)
        structured=self.reader.structured_chapter(chapter,cancelled=cancelled)
        native=self.reader.key(key+'.1')
        title=display_name(native.getOSISBookName(),native.getBookName(),LANGUAGE)
        if preferences.chapter_numbers:title+=' '+str(native.getChapter())
        pieces=[title+'\n\n'];styles=[StyleSpan('chapter',0,len(title))];spans=[];offset=len(pieces[0])
        for reference,plain in chapter.unique_verses():
            checkpoint(cancelled)
            start=offset if spans else 0
            segments=structured[reference]
            for segment in segments:
                if segment.kind=='heading' and segment.text.strip():
                    text=segment.text.strip()+'\n';pieces.append(text)
                    styles.append(StyleSpan('heading',offset,offset+len(text)));offset+=len(text)
            body=''.join(s.text for s in segments if s.kind!='heading')
            leading=body[:len(body)-len(body.lstrip())]
            if leading:pieces.append(leading);offset+=len(leading);body=body[len(leading):]
            members=chapter.members(reference)
            label=chapter.label(reference) if len(members)>1 else None
            number=(label or reference.rsplit('.',1)[-1])+' ' if preferences.verse_numbers else ''
            if number:styles.append(StyleSpan('number',offset,offset+len(number)))
            pieces.append(number);offset+=len(number);body_start=offset
            pieces.append(body);offset+=len(body)
            if number:styles.append(StyleSpan('verse-start',body_start-len(number),body_start+first_word_length(body)))
            spans.append(PassageSpan(reference,start,body_start,offset,members[1:],label))
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


class BibleBookPages(BiblePages):
    """Load one actual book on demand; chapters share a continuous document."""
    book_pages=True

    def key(self,reference):return self.reader.key(reference).getOSISBookName()

    def clone(self):
        from .sword_provider import Reader
        return BibleBookPages(Reader(self.reader.root,self.reader.name),self.resource)

    def document(self,key,preferences,*,cancelled=None):
        checkpoint(cancelled)
        code=key.split('.')[0]
        if 'books' not in self.reader.__dict__:
            self.reader.__dict__['books']=self.reader.discover_books(cancelled)
        book=next((b for b in self.reader.books if b.code==code),None)
        if book is None:raise ValueError('Book unavailable: '+code)
        pieces=[];copies=[];spans=[];styles=[];offset=0
        for number in book.chapters:
            checkpoint(cancelled)
            doc=super().document(f'{code}.{number}',preferences,cancelled=cancelled)
            prefix=offset
            if pieces:pieces.append('\n\n');copies.append('\n\n');offset+=2
            pieces.append(doc.text)
            copies.append(doc.copy(0,len(doc.text)))
            for index,span in enumerate(doc.spans):
                spans.append(replace(span,start=prefix if index==0 else span.start+offset,
                                     body=span.body+offset,end=span.end+offset))
            styles.extend(replace(style,start=style.start+offset,end=style.end+offset) for style in doc.styles)
            offset+=len(doc.text)
        return Document(code,''.join(pieces),tuple(spans),tuple(styles),''.join(copies))

    def neighbour(self,key,direction):
        codes=[b.code for b in self.reader.books];position=codes.index(key)+direction
        return codes[position] if 0<=position<len(codes) else None


class CommentaryPages:
    kind='commentary'
    def __init__(self,reader,resource):self.reader=reader;self.resource=resource
    def key(self,reference):return self.reader.index.locate(reference)
    def document(self,key,preferences):
        section=self.reader.index.sections[key]
        text=self.reader.index.text(key)
        from .commentary_format import format_entry
        text,inline,titles=format_entry(self.reader.index.raw(key),text,str(self.reader.module.getConfigEntry('SourceType')))
        prefix=''.join(title+'\n' for title in titles)
        styles=([StyleSpan('heading',0,len(prefix))] if prefix else [])
        styles.extend(StyleSpan(kind,first+len(prefix),last+len(prefix)) for kind,first,last in inline)
        reference=section.start if not section.introduction else '@'+str(section.index)
        return Document(key,prefix+text,(PassageSpan(reference,0,len(prefix),len(prefix)+len(text)),),tuple(styles))
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
