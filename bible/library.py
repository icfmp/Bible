"""Real CrossWire catalogue and bounded, atomic resource installation."""
import configparser
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from dataclasses import dataclass, replace
from functools import lru_cache
from concurrent.futures import as_completed
from .providers import CROSSWIRE, PROVIDERS, BY_ID, identity, module_name

BASE = 'https://www.crosswire.org/ftpmirror/pub/sword/'
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_UNPACKED = 256 * 1024 * 1024
BIBLE_DRIVERS = {'zText', 'RawText', 'RawText4', 'zText4'}
COMMENTARY_DRIVERS = {'RawCom', 'RawCom4', 'zCom', 'zCom4'}


@dataclass(frozen=True)
class Resource:
    name: str
    description: str
    language: str
    license: str
    about: str = ''
    conditions: str = ''
    locked: bool = False
    driver: str = 'RawText'
    source: str = 'CrossWire'
    source_url: str = BASE

    author: str = ''
    category: str = 'Biblical Texts'
    versification: str = 'KJV'
    provider_id: str = 'crosswire'
    acquisition: str = ''

    @property
    def id(self):
        return identity(self.provider_id, self.name)

    @property
    def kind(self):
        return 'commentary' if self.driver in COMMENTARY_DRIVERS or self.category == 'Commentaries' else 'bible'

    @property
    def installable(self):
        if self.provider_id=='youversion':
            try:
                if not (json.loads(self.acquisition).get('offline') or {}).get('url'):return False
            except (ValueError,TypeError,AttributeError):return False
        return (not self.locked and self.driver in BIBLE_DRIVERS | COMMENTARY_DRIVERS
                and self.category not in {'Images', 'Maps'})


def resource_from_section(name, section, provider=CROSSWIRE):
    # Keep provider statements, including unknown/restrictive licenses. Listing a
    # translation does not grant redistribution rights over its contents.
    conditions = '\n'.join(f'{key}: {value}' for key, value in section.items()
                           if value and (key.startswith('copyright') or key in {
                               'distributionnotes', 'shortcopyright', 'textsource'}))
    return Resource(name, section.get('Description') or name, section.get('Lang') or 'und',
                    section.get('DistributionLicense', '') or 'Unknown',
                    section.get('About') or '', conditions, 'cipherkey' in section,
                    section.get('ModDrv') or '', author=section.get('Author') or '',
                    category=section.get('Category') or 'Biblical Texts',
                    versification=section.get('Versification') or 'KJV',
                    provider_id=provider.id, source=provider.name, source_url=provider.url)


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
    try:parser.read_string('\n'.join(logical_lines))
    except configparser.Error as error:raise ValueError('Invalid resource configuration: '+str(error)) from error
    # Preserve repeated legal statements; ConfigParser normally keeps only the
    # final occurrence, whereas SWORD permits repeated configuration keys.
    legal, section = {}, None
    for line in logical_lines:
        if line.strip().startswith('[') and line.strip().endswith(']'):
            section = line.strip()[1:-1]
        elif section and '=' in line and not line.lstrip().startswith(('#', ';')):
            key, value = line.split('=', 1)
            key = key.strip().lower()
            if key.startswith('copyright') or key in {'distributionnotes', 'shortcopyright', 'about', 'textsource'}:
                legal.setdefault((section, key), []).append(value.strip())
    for (section, key), values in legal.items():
        if len(values) > 1:
            parser[section][key] = '\n'.join(values)
    return parser


def safe_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or '\x00' in name:
        raise ValueError('Unsafe archive path')
    return path


def compatible_notices(expected, actual, section):
    """Recognize Haiola's generated revision dates; keep raw legal notices."""
    fields=('license','conditions','about','author')
    if all(getattr(expected,key)==getattr(actual,key) for key in fields):return True
    if (expected.license,expected.author)!=(actual.license,actual.author):return False
    history=section.get('History_'+(section.get('Version') or ''),'') or ''
    if not (history.startswith('Automatically generated on ') and 'using Haiola (' in history):return False
    dates=[];bodies=[]
    for value in (expected.about,actual.about):
        match=re.fullmatch(r'(.*\S) +(\d{4}-\d{2}-\d{2})\s*',value,re.DOTALL)
        if not match:return False
        bodies.append(match[1]);dates.append(match[2])
    if bodies[0]!=bodies[1]:return False
    def conditions(value,date):
        # Only CopyrightNotes' terminal date may mirror About's revision date.
        # CopyrightDate, holders, licenses, restrictions and all prose stay exact.
        return re.sub(r'(?m)^(copyrightnotes:.*) +'+re.escape(date)+r'$',r'\1',value)
    return conditions(expected.conditions,dates[0])==conditions(actual.conditions,dates[1])


def download(url, destination, progress=lambda done, total: None, limit=MAX_ARCHIVE, headers=None, response_headers=None, same_origin=False):
    deadline=time.monotonic()+120
    request = urllib.request.Request(url, headers={'User-Agent': 'Bible-prototype/0.1',**(headers or {})})
    opener=urllib.request.urlopen
    if same_origin:
        from .youversion_install import SourceRedirect
        opener=urllib.request.build_opener(SourceRedirect()).open
    with opener(request, timeout=30) as response:
        if not response.url.startswith('https://'):
            raise ValueError('HTTPS required')
        if response_headers is not None:
            response_headers.update({key:response.headers[key] for key in ('ETag','Last-Modified') if response.headers.get(key)})
        try:
            total = max(0, int(response.headers.get('Content-Length', 0)))
        except (TypeError, ValueError):
            total = 0
        if response.headers.get('Transfer-Encoding'):
            total = 0
        if total > limit:
            raise ValueError('Download too large')
        done = 0
        progress(0, total)
        # read() waits for a full block (or EOF); read1() reports bytes already
        # received even for small/slow responses. Never invent a percentage.
        read = getattr(response, "read1", response.read)
        while chunk := read(64 * 1024):
            if time.monotonic()>deadline:raise TimeoutError('Download exceeded its time limit')
            done += len(chunk)
            if done > limit:
                raise ValueError('Download too large')
            destination.write(chunk)
            progress(done, total)
        if total and done != total:
            raise ValueError('Incomplete download')


def catalogue(provider=CROSSWIRE, timings=None, validators=None):
    started=time.monotonic()
    data = io.BytesIO()
    if provider not in PROVIDERS:
        raise ValueError('Unsupported resource source')
    response_headers={}
    headers={name:validators[key] for key,name in [('ETag','If-None-Match'),('Last-Modified','If-Modified-Since')]
             if validators and key in validators}
    if timings is not None:timings.update(requests=1,metadata_bytes=0)
    try:
        options={'same_origin':True} if provider.id=='youversion' else {}
        download(provider.catalogue_url, data, limit=8 * 1024 * 1024,headers=headers,response_headers=response_headers,**options)
    finally:
        if timings is not None:timings.update(metadata_bytes=data.tell(),network_seconds=time.monotonic()-started)
    received=time.monotonic()
    if provider.id == 'youversion':
        from .youversion_install import resource_from_metadata
        resources = [resource_from_metadata(json.loads(data.getvalue()))]
        if timings is not None:timings.update(parse_seconds=time.monotonic()-received,
                http_status=200,validators=response_headers)
        return resources
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
                if (re.fullmatch(r'[A-Za-z0-9_-]+', name)
                        and (section.get('ModDrv') in BIBLE_DRIVERS | COMMENTARY_DRIVERS
                             or section.get('Category') in {'Biblical Texts', 'Commentaries'})):
                    resources.append(resource_from_section(name, section, provider))
    if timings is not None:timings.update(network_seconds=received-started,parse_seconds=time.monotonic()-received,
                                        metadata_bytes=len(data.getvalue()),http_status=200,validators=response_headers)
    return sorted(resources, key=lambda r: (r.language, r.name))


@dataclass(frozen=True)
class CatalogueResult:
    resources: tuple
    errors: dict


def catalogues(providers=PROVIDERS, on_provider=None, cache=None, force=True):
    """One unavailable provider must not discard successful catalogues."""
    def load(provider):
        started=time.monotonic()
        timings={};cached=cache.read(provider) if cache else None
        if cached and not force and time.time()-cached[1]<15*60:
            return cached[0],None,{'cached':True,'updated':cached[1],'requests':0,'metadata_bytes':0}
        try:
            validators=cache.validators.get(provider.id,{}) if cache and cached else {}
            items=catalogue(provider,timings=timings,**({'validators':validators} if validators else {}))
            if cache:
                try:cache.write(provider,items,validators=timings.get('validators'))
                except OSError as error:timings['cache_error']=str(error)
            return items,None,timings
        except Exception as error:
            import urllib.error
            if isinstance(error,urllib.error.HTTPError) and error.code==304 and cached and error.geturl().startswith('https://'):
                try:cache.write(provider,cached[0],validators=cache.validators.get(provider.id))
                except OSError as write_error:timings['cache_error']=str(write_error)
                timings.update(http_status=304,requests=1,metadata_bytes=0,network_seconds=time.monotonic()-started)
                return cached[0],None,timings
            return cached[0] if cached else [],str(error),timings
    resources, errors = [], {}
    from .metadata_workers import MetadataExecutor
    with MetadataExecutor(max_workers=4, thread_name_prefix='bible-catalogue') as executor:
        futures={executor.submit(load,provider):provider for provider in providers}
        for future in as_completed(futures):
            provider=futures[future];items,error,timings=future.result()
            if error is not None:
                errors[provider.name] = error
            resources.extend(items)
            if on_provider:on_provider(provider,items,error,timings)
    # Retain duplicates with distinct IDs and explicit provenance, never pick an
    # arbitrary provider based on network completion order.
    return CatalogueResult(tuple(sorted(resources, key=lambda r: (r.language, r.name, r.provider_id))), errors)


class Library:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def installed(self, kind=None):
        names = sorted(p.name for p in self.root.iterdir()
                      if p.is_dir() and not p.name.startswith('.')
                      and (p / '.complete').is_file())
        if kind is None:
            return names
        matching=[];self.discovery_errors={}
        for name in names:
            try:
                if self.resource(name).kind==kind:matching.append(name)
            except (OSError,ValueError) as error:self.discovery_errors[name]=str(error)
        return matching

    def resource(self, name):
        """Read installed attribution offline, also for pre-existing installations."""
        if name not in self.installed():
            raise ValueError('Translation is not installed')
        files = list((self.root / name / 'mods.d').glob('*.conf'))
        if len(files) != 1:
            raise ValueError('Expected one resource configuration')
        metadata_path = self.root / name / '.source.json'
        def revision(path):
            try:info=path.stat()
            except FileNotFoundError:return None
            return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns
        return self._read_resource(name,files[0],metadata_path,
                                   (revision(files[0]),revision(metadata_path)))

    @staticmethod
    @lru_cache(maxsize=128)
    def _read_resource(name,configuration,metadata_path,revision):
        # Cache immutable attribution only, never Readers or library instances.
        # Native file revisions invalidate both configuration and provenance;
        # installation checks above still reject missing/removed resources.
        parser = config(configuration.read_bytes())
        metadata = json.loads(metadata_path.read_text()) if metadata_path.is_file() else {}
        provider_id = metadata.get('provider_id', 'crosswire')
        provider = BY_ID.get(provider_id)
        internal = module_name(name)
        if (provider is None or identity(provider_id, internal) != name
                or metadata.get('module_name', internal) != internal):
            raise ValueError('Installed source identity mismatch')
        if internal not in parser:raise ValueError('Installed module configuration is missing')
        resource = resource_from_section(internal, parser[internal], provider)
        # Read the recorded attribution, not today's registry URL, offline.
        return replace(resource, source=metadata.get('source', resource.source),
                       source_url=metadata.get('url', resource.source_url),
                       acquisition=metadata.get('acquisition', ''))

    def install(self, resource, progress=lambda done, total: None, installing=lambda: None,
                *, cancelled=lambda: False, phase=lambda name,done,total: None,
                permission=None):
        provider = BY_ID.get(resource.provider_id)
        if provider is None or resource.source_url != provider.url or resource.source != provider.name:
            raise ValueError('Unsupported resource source')
        if not resource.installable:
            raise ValueError('Encrypted or unsupported resource')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', resource.name):
            raise ValueError('Invalid resource name')
        if resource.id in self.installed():
            return
        if resource.provider_id == 'youversion':
            from .youversion_install import install
            return install(self,resource,progress,installing,cancelled,phase,permission)
        with tempfile.TemporaryDirectory(prefix='.install-', dir=self.root) as temporary:
            stage = Path(temporary)
            archive_path = stage / 'download.zip'
            with archive_path.open('wb') as output:
                download(provider.packages_url + f'{resource.name}.zip', output, progress)
            installing()
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
                raise ValueError(f'Resource identity mismatch: expected {resource.name}, got {parser.sections()}')
            section = parser[resource.name]
            actual = resource_from_section(resource.name, section, provider)
            if (actual.kind, actual.driver, actual.versification) != (
                    resource.kind, resource.driver, resource.versification):
                raise ValueError('Resource type changed. Reload the catalogue before downloading.')
            if not actual.installable:
                raise ValueError('Encrypted or unsupported resource')
            if not compatible_notices(resource,actual,section):
                raise ValueError('Resource conditions changed. Reload the catalogue before downloading.')
            data_path = safe_path(section.get('DataPath', ''))
            if not data_path.parts or data_path.parts[0] != 'modules':
                raise ValueError('Unsafe resource DataPath')
            # Do not let SWORD load arbitrary file references from untrusted metadata.
            for key in section:
                if key.lower().endswith('path') and key.lower() != 'datapath':
                    raise ValueError('Unsupported resource path')
            from .sword_provider import Reader, CommentaryReader
            reader = (CommentaryReader if actual.kind == 'commentary' else Reader)(target, resource.name)
            first = reader.first_reference()
            if actual.kind == 'commentary':
                if not reader.entry(first, reader.versification):
                    raise ValueError('No readable commentary entry in resource')
            elif not any(text.strip() for _, text in reader.chapter(first).verses):
                raise ValueError('No readable chapter in resource')
            del reader
            (target / '.source.json').write_text(json.dumps({
                'provider_id': provider.id, 'module_name': resource.name,
                'source': resource.source, 'url': resource.source_url,
                'catalogue_notices': {key:getattr(resource,key) for key in ('license','conditions','about','author')},
                'updated_notice_fields': [key for key in ('license','conditions','about','author')
                                         if getattr(resource,key)!=getattr(actual,key)],
            }), encoding='utf-8')
            (target / '.complete').write_text(resource.id, encoding='utf-8')
            destination = self.root / resource.id
            # Existing complete installations are never replaced by failed downloads.
            if destination.exists():
                raise ValueError('Resource directory already exists')
            os.rename(target, destination)
