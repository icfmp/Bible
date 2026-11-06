"""Small inert Markdown preview: native text and style spans, never HTML or URLs."""
import re

FORMATTING=re.compile(r'\*\*\*(.*?)\*\*\*|\*\*(.*?)\*\*|\*([^*\n]*?)\*|\[([^\]\n]+)\]\(([^)\n]+)\)')


def markup_regions(text,offset=0,depth=0):
    """Source ranges for native editing; delimiter tags never change data."""
    if depth>4:return
    for match in FORMATTING.finditer(text):
        first,last=offset+match.start(),offset+match.end()
        group=next(index for index in range(1,6) if match.group(index) is not None)
        if group==4:
            yield 'hidden',first,first+1
            close=offset+match.start(4)+len(match[4]);yield 'hidden',close,close+1
            yield 'link',first,last
        else:
            width={1:3,2:2,3:1}[group]
            yield 'hidden',first,first+width;yield 'hidden',last-width,last
            for kind in (('bold','italic') if group==1 else ('bold',) if group==2 else ('italic',)):
                yield kind,first+width,last-width
            yield from markup_regions(match[group],first+width,depth+1)


def inline(text,depth=0):
    if depth>4:return text,[]
    output=[];spans=[];cursor=0;offset=0
    for match in FORMATTING.finditer(text):
        prefix=text[cursor:match.start()];output.append(prefix);offset+=len(prefix)
        group=next(index for index in range(1,6) if match.group(index) is not None)
        if group==4:value,children=f'{match[4]} ({match[5]})',[];kinds=('link',)
        else:
            value,children=inline(match[group],depth+1)
            kinds=('bold','italic') if group==1 else ('bold',) if group==2 else ('italic',)
        output.append(value)
        spans.extend((kind,offset,offset+len(value)) for kind in kinds)
        spans.extend((kind,offset+first,offset+last) for kind,first,last in children)
        offset+=len(value);cursor=match.end()
    output.append(text[cursor:]);return ''.join(output),spans


def render(source):
    output, spans, offset = [], [], 0
    for line in source.splitlines(keepends=True):
        line = re.sub(r'^\s*[-*] ', '• ', line)
        value,styles=inline(line);output.append(value)
        spans.extend((kind,first+offset,last+offset) for kind,first,last in styles)
        offset+=len(value)
    return ''.join(output), spans
