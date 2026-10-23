"""Bounded FR/EN note citations; recognition never navigates or edits notes."""
from dataclasses import dataclass
from functools import lru_cache
from html.parser import HTMLParser
import re
import unicodedata
from .book_names import FRENCH, normalized

# UI/address metadata only, never Bible text. Deliberately bounded syntax;
# upstream's JavaScript parser is evaluated in the audit, not embedded/ported.
ENGLISH = dict(zip(list(FRENCH)[:66], [
    'Genesis','Exodus','Leviticus','Numbers','Deuteronomy','Joshua','Judges','Ruth',
    '1 Samuel','2 Samuel','1 Kings','2 Kings','1 Chronicles','2 Chronicles','Ezra',
    'Nehemiah','Esther','Job','Psalms','Proverbs','Ecclesiastes','Song of Songs',
    'Isaiah','Jeremiah','Lamentations','Ezekiel','Daniel','Hosea','Joel','Amos',
    'Obadiah','Jonah','Micah','Nahum','Habakkuk','Zephaniah','Haggai','Zechariah',
    'Malachi','Matthew','Mark','Luke','John','Acts','Romans','1 Corinthians',
    '2 Corinthians','Galatians','Ephesians','Philippians','Colossians',
    '1 Thessalonians','2 Thessalonians','1 Timothy','2 Timothy','Titus','Philemon',
    'Hebrews','James','1 Peter','2 Peter','1 John','2 John','3 John','Jude','Revelation']))
ABBREVIATIONS = {
    'Gn':'Gen','Ge':'Gen','Ex':'Exod','Lv':'Lev','Nb':'Num','Nu':'Num','Dt':'Deut',
    'Jos':'Josh','Jg':'Judg','Ps':'Ps','Psalm':'Ps','Psaume':'Ps','Pr':'Prov',
    'Ec':'Eccl','Ct':'Song','Song of Solomon':'Song','Cantique':'Song',
    'Es':'Isa','Ésa':'Isa','Jér':'Jer','Ez':'Ezek','Os':'Hos','Jon':'Jonah',
    'Mt':'Matt','Mc':'Mark','Mk':'Mark','Lc':'Luke','Lk':'Luke','Jn':'John',
    'Ac':'Acts','Rm':'Rom','Ro':'Rom','1 Co':'1Cor','2 Co':'2Cor','Ga':'Gal',
    'Ep':'Eph','1 Th':'1Thess','2 Th':'2Thess','1 Tm':'1Tim','2 Tm':'2Tim',
    'Phm':'Phlm','Héb':'Heb','Jc':'Jas','1 P':'1Pet','2 P':'2Pet',
    '1 Jn':'1John','2 Jn':'2John','3 Jn':'3John','Ap':'Rev'}
MAX_TEXT = 200000
MAX_CITATIONS = 200


@dataclass(frozen=True)
class Citation:
    begin: int
    finish: int
    start: str
    end: str
    system: str


def fold(text):
    result=[];positions=[]
    for offset,char in enumerate(text):
        for value in unicodedata.normalize('NFKD',char.casefold()):
            if not unicodedata.combining(value):result.append(value);positions.append(offset)
    return ''.join(result),positions


@lru_cache(maxsize=1)
def grammar():
    names={}
    for code,label in [*FRENCH.items(),*ENGLISH.items()]:
        names[normalized(label)]=code;names[normalized(code)]=code
    names.update({normalized(label):code for label,code in ABBREVIATIONS.items()})
    labels=set(FRENCH.values())|set(ENGLISH.values())|set(FRENCH)|set(ABBREVIATIONS)
    patterns=[]
    for label in sorted(labels,key=len,reverse=True):
        value=fold(label)[0]
        pattern=re.escape(value).replace(r'\ ',r'[ \t]+')
        if value[0].isdigit():pattern=value[0]+r'[ \t]*'+re.escape(value[1:].lstrip()).replace(r'\ ',r'[ \t]+')
        patterns.append(pattern)
    pattern=(r'(?<![\w/])(?P<name>'+ '|'.join(patterns)+r')\.?[ \t.]+'
        r'(?P<chapter>[1-9][0-9]{0,2})[.:](?P<verse>[1-9][0-9]{0,2})'
        r'(?:[ \t]*[–—-][ \t]*(?:(?P<end_chapter>[1-9][0-9]{0,2})[.:])?'
        r'(?P<end_verse>[1-9][0-9]{0,2}))?'
        r'(?![\w]|[.:][0-9]|[ \t]*[–—-])')
    return re.compile(pattern),names


def excluded_ranges(text, style_spans=()):
    """Conservatively exclude code, existing links, URLs and raw HTML."""
    ranges=[(a,b) for kind,a,b in style_spans if kind=='link']
    fence=None;start=0;offset=0
    for line in text.splitlines(keepends=True):
        match=re.match(r'^[ \t]{0,3}(`{3,}|~{3,})',line)
        if match:
            marker=match[1]
            if fence is None:fence=marker;start=offset
            elif marker[0]==fence[0] and len(marker)>=len(fence) and not line[match.end():].strip():
                ranges.append((start,offset+len(line)));fence=None
        offset+=len(line)
    if fence:ranges.append((start,len(text)))
    runs=list(re.finditer(r'`+',text));index=0
    while index<len(runs):
        opening=runs[index]
        if any(a<=opening.start()<b for a,b in ranges):index+=1;continue
        closing=next((i for i in range(index+1,len(runs)) if runs[i][0]==opening[0]),None)
        if closing is not None:ranges.append((opening.start(),runs[closing].end()));index=closing+1
        else:
            end=text.find('\n',opening.end())
            ranges.append((opening.start(),end if end>=0 else len(text)));index+=1
    for pattern in (
        r'\b(?:https?|ftp|file|javascript|data|mailto|bible|shell|exec):[^\n]*',
        r'<[^>\n]*(?:>|$)',
    ):
        ranges.extend(m.span() for m in re.finditer(pattern,text,re.IGNORECASE|re.MULTILINE))
    html=InertHTML(text);html.feed(text);html.close()
    ranges.extend(html.ranges)
    if html.stack:ranges.append((html.stack[0][1],len(text)))
    return ranges


class InertHTML(HTMLParser):
    """Locate inert HTML regions only; never render tags, URLs or scripts."""
    def __init__(self,text):
        super().__init__(convert_charrefs=False)
        self.stack=[];self.ranges=[];self.lines=[0]
        self.lines.extend(match.end() for match in re.finditer('\n',text))

    def position(self):
        line,column=self.getpos();return self.lines[line-1]+column

    def handle_starttag(self,tag,attrs):
        start=self.position();end=start+len(self.get_starttag_text())
        self.ranges.append((start,end))
        if tag not in {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}:
            self.stack.append((tag,start))

    def handle_startendtag(self,tag,attrs):self.ranges.append((self.position(),self.position()+len(self.get_starttag_text())))

    def handle_endtag(self,tag):
        index=next((i for i in range(len(self.stack)-1,-1,-1) if self.stack[i][0]==tag),None)
        if index is not None:
            self.ranges.append((self.stack[index][1],self.position()+len(tag)+3));del self.stack[index:]

    def handle_comment(self,data):self.ranges.append((self.position(),self.position()+len(data)+7))


def citations(text, system, style_spans=()):
    """Recognize explicit citations in their note's recorded numbering system.

    Installed-module existence/mapping are deliberately checked by the shared
    preview later. Invalid/ambiguous references remain ordinary inert text.
    """
    from .reference_targets import Canon
    if len(text)>MAX_TEXT:return []
    pattern,names=grammar();value,positions=fold(text)
    excluded=excluded_ranges(text,style_spans);result=[];canon=Canon(system)
    for match in pattern.finditer(value):
        begin,finish=positions[match.start()],positions[match.end()-1]+1
        if any(begin<b and finish>a for a,b in excluded):continue
        if re.search(r'\b(?:[0-9]+|i{1,3})[ \t]+$',value[max(0,match.start()-8):match.start()]):continue
        if re.search(r'[0-9][ \t]*[–—-][ \t]*$',value[max(0,match.start()-8):match.start()]):continue
        book=names.get(normalized(match['name']))
        if not book:continue
        start=f'{book}.{match["chapter"]}.{match["verse"]}'
        end=f'{book}.{match["end_chapter"] or match["chapter"]}.{match["end_verse"] or match["verse"]}'
        try:
            if canon.key(start).getIndex()>canon.key(end).getIndex():continue
        except ValueError:continue
        result.append(Citation(begin,finish,start,end,system))
        if len(result)>=MAX_CITATIONS:break
    return result
