"""Real CrossWire catalogue and bounded, atomic resource installation."""
import configparser
import io
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass

BASE = 'https://www.crosswire.org/ftpmirror/pub/sword/'
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_UNPACKED = 256 * 1024 * 1024


@dataclass(frozen=True)
class Resource:
    name: str
    description: str
    language: str
    license: str


def config(data):
    # SWORD FileMgr::getLine joins physical lines ending in backslash.
    # Its configuration also permits bare keys and repeated entries.
    parser = configparser.ConfigParser(interpolation=None, strict=False,
                                       allow_no_value=True, delimiters=('=',))
    logical_lines = []
    pending = ''
    for line in data.decode('utf-8-sig', errors='replace').splitlines():
        line = line.rstrip()
        if line.endswith('\\'):
            pending += line[:-1]
        else:
            logical_lines.append(pending + line)
            pending = ''
    if pending:
        logical_lines.append(pending)
    parser.read_string('\n'.join(logical_lines))
    return parser


def safe_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or '\x00' in name:
        raise ValueError('Unsafe archive path')
    return path


def download(url, destination, progress=lambda done, total: None, limit=MAX_ARCHIVE):
    request = urllib.request.Request(url, headers={'User-Agent': 'Bible-prototype/0.1'})
    with urllib.request.urlopen(request, timeout=30) as response:
        if not response.url.startswith('https://'):
            raise ValueError('HTTPS required')
        total = int(response.headers.get('Content-Length', 0))
        if total > limit:
            raise ValueError('Download too large')
        done = 0
        while chunk := response.read(64 * 1024):
            done += len(chunk)
            if done > limit:
                raise ValueError('Download too large')
            destination.write(chunk)
            progress(done, total)
        if total and done != total:
            raise ValueError('Incomplete download')


def catalogue():
    data = io.BytesIO()
    download(BASE + 'raw/mods.d.tar.gz', data, limit=8 * 1024 * 1024)
    resources = []
    expanded = 0
    with tarfile.open(fileobj=io.BytesIO(data.getvalue()), mode='r:gz') as archive:
        for member in archive:
            if not member.isfile() or not member.name.endswith('.conf'):
                continue
            if member.size > 1024 * 1024:
                raise ValueError('Catalogue entry too large')
            expanded += member.size
            if expanded > MAX_UNPACKED:
                raise ValueError('Catalogue too large')
            parser = config(archive.extractfile(member).read())
            for name in parser.sections():
                section = parser[name]
                # Minimal catalogue: only resources explicitly declared public domain.
                if (re.fullmatch(r'[A-Za-z0-9_-]+', name)
                        and section.get('ModDrv') in {'zText', 'RawText', 'RawText4', 'zText4'}
                        and section.get('DistributionLicense', '').lower() == 'public domain'
                        and not section.get('CipherKey')):
                    resources.append(Resource(name, section.get('Description', name),
                                              section.get('Lang', ''),
                                              section['DistributionLicense']))
    return sorted(resources, key=lambda r: (r.language, r.name))


class Library:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def installed(self):
        return sorted(p.name for p in self.root.iterdir()
                      if p.is_dir() and not p.name.startswith('.')
                      and (p / '.complete').is_file())

    def install(self, resource, progress=lambda done, total: None):
        if not re.fullmatch(r'[A-Za-z0-9_-]+', resource.name):
            raise ValueError('Invalid resource name')
        if resource.name in self.installed():
            return
        with tempfile.TemporaryDirectory(prefix='.install-', dir=self.root) as temporary:
            stage = Path(temporary)
            archive_path = stage / 'download.zip'
            with archive_path.open('wb') as output:
                download(BASE + f'packages/rawzip/{resource.name}.zip', output, progress)
            target = stage / 'content'
            target.mkdir()
            with zipfile.ZipFile(archive_path) as archive:
                if len(archive.infolist()) > 20000:
                    raise ValueError('Too many archive entries')
                expanded = 0
                seen = set()
                for entry in archive.infolist():
                    path = safe_path(entry.filename)
                    if not path.parts or path.parts[0] not in {'mods.d', 'modules'}:
                        raise ValueError('Unexpected archive layout')
                    if path in seen:
                        raise ValueError('Duplicate archive entry')
                    seen.add(path)
                    if stat.S_ISLNK(entry.external_attr >> 16):
                        raise ValueError('Archive symlink refused')
                    expanded += entry.file_size
                    if expanded > MAX_UNPACKED:
                        raise ValueError('Unpacked resource too large')
                    destination = target.joinpath(*path.parts)
                    if entry.is_dir():
                        destination.mkdir(parents=True, exist_ok=True)
                    else:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(entry) as source, destination.open('xb') as output:
                            shutil.copyfileobj(source, output)
            configs = list((target / 'mods.d').glob('*.conf'))
            if len(configs) != 1:
                raise ValueError('Expected one resource configuration')
            parser = config(configs[0].read_bytes())
            if parser.sections() != [resource.name]:
                raise ValueError('Resource identity mismatch')
            section = parser[resource.name]
            if (section.get('DistributionLicense', '').lower() != 'public domain'
                    or section.get('ModDrv') not in {'zText', 'RawText', 'RawText4', 'zText4'}
                    or section.get('CipherKey')):
                raise ValueError('Unsupported resource')
            data_path = safe_path(section.get('DataPath', ''))
            if not data_path.parts or data_path.parts[0] != 'modules':
                raise ValueError('Unsafe resource DataPath')
            # Do not let SWORD load arbitrary file references from untrusted metadata.
            for key in section:
                if key.lower().endswith('path') and key.lower() != 'datapath':
                    raise ValueError('Unsupported resource path')
            from .sword_provider import Reader
            reader = Reader(target, resource.name)
            chapter = reader.chapter()
            if not any(text.strip() for _, text in chapter.verses):
                raise ValueError('No readable Genesis chapter in resource')
            del reader
            (target / '.complete').write_text(resource.name, encoding='utf-8')
            destination = self.root / resource.name
            # Existing complete installations are never replaced by failed downloads.
            if destination.exists():
                raise ValueError('Resource directory already exists')
            os.rename(target, destination)
