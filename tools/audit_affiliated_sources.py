"""Issue #11: reproducible read-only discovery, before changing provider policy.

Fetch official documentation and the standard repository list, and measure the
current CrossWire catalogue. No Bible/commentary text is downloaded or bundled.
"""
from datetime import datetime, timezone
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import tarfile
import urllib.parse
import urllib.request

from bible.library import BASE, BIBLE_DRIVERS, COMMENTARY_DRIVERS, config, download

DOCUMENTS = {
    'xiphos_manual': 'https://xiphos.org/manual/module-manager.html',
    'affiliated_repositories': 'https://wiki.crosswire.org/Official_and_Affiliated_Module_Repositories',
    'standard_repositories': BASE + 'masterRepoList.conf',
}


class Document(HTMLParser):
    def __init__(self, base):
        super().__init__()
        self.base, self.parts, self.links, self.hidden = base, [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}:
            self.hidden += 1
        if tag == 'a' and (href := dict(attrs).get('href')):
            url = urllib.parse.urljoin(self.base, href)
            if urllib.parse.urlsplit(url).scheme in {'https', 'http', 'ftp'}:
                self.links.append(url)

    def handle_endtag(self, tag):
        if tag in {'script', 'style'}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, text):
        if not self.hidden and text.strip():
            self.parts.append(text.strip())


def entries(payload):
    result = []
    expanded = 0
    with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
        for member in archive:
            if not member.isfile() or not member.name.endswith('.conf'):
                continue
            if member.size > 1024 * 1024:
                raise ValueError('Catalogue entry too large')
            expanded += member.size
            if expanded > 256 * 1024 * 1024:
                raise ValueError('Catalogue too large')
            parser = config(archive.extractfile(member).read())
            for name in parser.sections():
                section = parser[name]
                driver = section.get('ModDrv') or ''
                result.append({
                    'name': name, 'description': section.get('Description'),
                    'language': section.get('Lang'), 'driver': driver,
                    'category': section.get('Category'),
                    'license': section.get('DistributionLicense'),
                    'locked': 'cipherkey' in section,
                    'commentary': driver in COMMENTARY_DRIVERS or section.get('Category') == 'Commentaries',
                    'supported_driver': driver in BIBLE_DRIVERS | COMMENTARY_DRIVERS,
                    'missing_language': not section.get('Lang'),
                })
    return sorted(result, key=lambda r: r['name'])


def main():
    report = {'issue': 11, 'checked_at': datetime.now(timezone.utc).isoformat(),
              'documents': {}, 'catalogues': {}}
    for key, url in DOCUMENTS.items():
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                payload = response.read(2 * 1024 * 1024 + 1)
                if len(payload) > 2 * 1024 * 1024:
                    raise ValueError('Document too large')
                final_url = response.url
            text = payload.decode('utf-8', 'replace')
            parser = Document(final_url)
            parser.feed(text)
            report['documents'][key] = {'url': url, 'final_url': final_url,
                'text': '\n'.join(parser.parts) if '<html' in text.lower() else text,
                'links': sorted(set(parser.links))}
        except Exception as error:
            report['documents'][key] = {'url': url, 'error': str(error)}
    # Endpoints transcribed from AndBible repositories.txt and the standard list.
    urls = {
        'crosswire': BASE + 'raw/mods.d.tar.gz',
        'andbible-extra': 'https://andbible.github.io/andbible-extra/mods.d.tar.gz',
        'andbible': 'https://andbible.github.io/data/andbible/mods.d.tar.gz',
        'ebible': 'https://ebible.org/sword/mods.d.tar.gz',
        'step': 'https://public.modules.stepbible.org/catalog/mods.d.tar.gz',
        'xiphos-http': 'http://ftp.xiphos.org/pub/xiphos/mods.d.tar.gz',
        'xiphos-ftp': 'ftp://ftp.xiphos.org/pub/xiphos/mods.d.tar.gz',
    }
    def inspect(item):
        key, url = item
        try:
            with urllib.request.urlopen(url, timeout=25) as response:
                payload = response.read(8 * 1024 * 1024 + 1)
                if len(payload) > 8 * 1024 * 1024:
                    raise ValueError('Catalogue too large')
                final_url = response.url
            resources = entries(payload)
            return key, {'url': url, 'final_url': final_url, 'entries': len(resources),
                'commentaries': [r for r in resources if r['commentary']],
                'other_drivers': sorted({r['driver'] for r in resources if not r['commentary']})}
        except Exception as error:
            return key, {'url': url, 'error': str(error)}
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=7) as executor:
        report['catalogues'] = dict(executor.map(inspect, urls.items()))
    main_names = {r['name'] for r in report['catalogues']['crosswire'].get('commentaries', [])}
    for result in report['catalogues'].values():
        if 'commentaries' in result:
            result['additional_commentaries'] = [r for r in result['commentaries'] if r['name'] not in main_names]
    Path('affiliated-sources-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
