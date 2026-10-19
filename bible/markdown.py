"""Small inert Markdown preview: native text and style spans, never HTML or URLs."""
import re

INLINE = re.compile(r'\*\*(.+?)\*\*|\*([^*\n]+)\*|\[([^\]\n]+)\]\(([^)\n]+)\)')


def render(source):
    output, spans, offset = [], [], 0
    for line in source.splitlines(keepends=True):
        line = re.sub(r'^\s*[-*] ', '• ', line)
        cursor = 0
        for match in INLINE.finditer(line):
            prefix = line[cursor:match.start()]
            output.append(prefix)
            offset += len(prefix)
            if match.group(1) is not None:
                value, kind = match.group(1), 'bold'
            elif match.group(2) is not None:
                value, kind = match.group(2), 'italic'
            else:
                # Links are displayed in full and remain inert, including unsafe schemes.
                value, kind = f'{match.group(3)} ({match.group(4)})', 'link'
            output.append(value)
            spans.append((kind, offset, offset + len(value)))
            offset += len(value)
            cursor = match.end()
        rest = line[cursor:]
        output.append(rest)
        offset += len(rest)
    return ''.join(output), spans
