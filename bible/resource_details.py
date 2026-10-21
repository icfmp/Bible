"""Plain, noninteractive presentation of untrusted provider metadata."""
from html.parser import HTMLParser
import re
from .i18n import tr


class PlainMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag in ('br', 'p', 'div'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain(value):
    parser = PlainMetadata()
    parser.feed(value)
    # About fields often contain SWORD's legacy RTF paragraph markers.
    value = ''.join(parser.parts)
    # Some catalogues double the backslash and omit the space before an
    # immediately following capital (e.g. \\par\\parSource:). Keep all words.
    value = re.sub(r'\\+par(?:d)?(?=$|[^a-z])\s*', '\n', value)
    return re.sub(r'\\+(?:qc|b0?|i0?)\b\s*', '', value).strip()


from .languages import language_name


def details(resource):
    availability = (tr('Access key required. Encrypted resources are not supported.') if resource.locked
                    else tr('Unsupported format.') if not resource.installable
                    else tr('Distributed by the source. Download is checked before installation.'))
    return '\n\n'.join([
        f'{plain(resource.description)} ({resource.name})',
        f'{tr("Resource type")}: {tr("Commentaries") if resource.kind == "commentary" else tr("Bibles")}',
        f'{tr("Author")}: {plain(resource.author)}' if resource.author else '',
        f'{tr("Language")}: {language_name(resource.language)}',
        f'{tr("Source")}: {resource.source}\n{resource.source_url}',
        f'{tr("License")}: {plain(resource.license)}',
        f'{tr("Verse numbering")}: {resource.versification}',
        availability,
        f'{tr("Conditions and attribution")}:\n' + (
            plain(resource.conditions) or tr('No additional conditions supplied by the source.')),
        plain(resource.about),
        tr('Check the source conditions before downloading. Availability does not grant redistribution rights.'),
    ])
