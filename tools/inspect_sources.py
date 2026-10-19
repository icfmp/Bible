"""Read public provider documentation and catalogue metadata, without Bible text."""
import io
import re
import tarfile
import urllib.request
from html.parser import HTMLParser
from bible.library import config, BASE


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag == 'a':
            url = dict(attrs).get('href', '')
            if any(word in url.lower() for word in ('api', 'doc', 'term', 'licen', 'offline')):
                self.links.append(url)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def notice(title, value):
    value = value.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
    print(f'::notice title={title}::{value}', flush=True)


def main():
    for title, url in [
        ('CrossWire repositories', BASE + 'masterRepoList.conf'),
        ('SWORD configuration', 'https://wiki.crosswire.org/DevTools:conf_Files'),
        ('YouVersion developers', 'https://developers.youversion.com/'),
        ('YouVersion API usage', 'https://developers.youversion.com/api-usage'),
        ('YouVersion Bible API', 'https://developers.youversion.com/api'),
    ]:
        try:
            data = urllib.request.urlopen(url, timeout=30).read(1024 * 1024).decode('utf-8', 'replace')
            parser = Text()
            parser.feed(data)
            text = '\n'.join(parser.parts) if '<html' in data.lower() else data
            if title == 'SWORD configuration':
                snippets = []
                for word in ('CipherKey', 'DistributionLicense', 'CopyrightNotes', 'DistributionNotes', 'DataPath'):
                    match = re.search(word, text, re.I)
                    if match:
                        snippets.append(text[max(0, match.start() - 80):match.start() + 650])
                text = '\n'.join(snippets)
            notice(title, url + '\n' + text[:11000] + '\nLinks: ' + str(sorted(set(parser.links))))
        except Exception as error:
            print(f'::warning title={title}::{error}', flush=True)
    with urllib.request.urlopen(BASE + 'raw/mods.d.tar.gz', timeout=30) as response:
        data = response.read(8 * 1024 * 1024)
    french = []
    matches = []
    counts = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        for entry in archive:
            if not entry.isfile() or not entry.name.endswith('.conf') or entry.size > 1024 * 1024:
                continue
            parser = config(archive.extractfile(entry).read())
            for name in parser.sections():
                section = parser[name]
                if section.get('ModDrv') not in {'zText', 'zText4', 'RawText', 'RawText4'}:
                    continue
                license = section.get('DistributionLicense', '(missing)')
                counts[license] = counts.get(license, 0) + 1
                if section.get('Lang', '').startswith('fr'):
                    french.append((name, {k: v for k, v in section.items() if k in {
                        'description', 'distributionlicense', 'copyright', 'copyrightnotes',
                        'distributionnotes', 'cipherkey', 'versification', 'minimumversion', 'textsource'}}))
                if re.search(r'\b(?:semeur|biblica|bds)\b', name + ' ' + str(dict(section)), re.I):
                    matches.append((name, section.get('Description'), license, 'cipherkey' in section))
    notice('CrossWire catalogue audit', 'Licenses: ' + str(counts) + '\nSemeur/Biblica candidates: ' + str(matches))
    notice('CrossWire French choices', '\n'.join(
        name + ': ' + str(metadata.get('description')) + '; ' + str(metadata.get('distributionlicense'))
        for name, metadata in french))
    for name, metadata in french:
        if name == 'FreBDM1707':
            notice('CrossWire French installation candidate', str(metadata))


if __name__ == '__main__':
    main()
