"""Consume the existing curated catalogue and its standard SWORD metadata.

No resource content is authored here. JSON supplies edition/package identity;
the publisher's SWORD configuration supplies driver, attribution and rights.
"""
from dataclasses import replace
import hashlib
import io
import json
import re
import time
from .module_updates import parse_catalogue
from .providers import BIBLE_RESOURCES


def entries(data):
    value=parse_catalogue(data);seen=set();editions=set();modules=set()
    for entry in value['modules']:
        canonical=entry.get('canonical_edition_id')
        if (not isinstance(canonical,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,199}',canonical)
                or not isinstance(entry.get('language'),str) or not entry['language']
                or entry.get('category') not in ('bible','commentary','dictionary')
                or entry['category']!='dictionary' and (
                    not isinstance(entry.get('versification'),str) or not entry['versification'])
                or not isinstance(entry.get('title'),dict)
                or not all(isinstance(k,str) and isinstance(v,str) and 0<len(v)<=500 for k,v in entry['title'].items())
                or not entry['title']):raise ValueError('Incomplete curated edition metadata')
        if (entry['download']['url']!=BIBLE_RESOURCES.packages_url+entry['sword_id']+'.zip'
                or entry['download']['size_bytes']>64*1024*1024):
            raise ValueError('Unsupported curated package path or size')
        edition=(canonical,entry['edition'])
        if entry['id'] in seen or edition in editions or entry['sword_id'] in modules:
            raise ValueError('Duplicate curated edition or SWORD identity')
        seen.add(entry['id']);editions.add(edition);modules.add(entry['sword_id'])
    # This adapter exposes verse-keyed resources only. Existing dictionary
    # records must not block them, but remain unavailable until their separate
    # integration is developed. Validate shared identity/integrity above even
    # for ignored records; never invent a dictionary versification.
    return [entry for entry in value['modules'] if entry['category']!='dictionary']


def catalogue(provider=BIBLE_RESOURCES,timings=None,validators=None):
    from .library import download,parse_sword_catalogue
    started=time.monotonic();data=io.BytesIO();headers={}
    for key,name in (('ETag','If-None-Match'),('Last-Modified','If-Modified-Since')):
        if validators and key in validators:headers[name]=validators[key]
    received={}
    download(provider.catalogue_url,data,limit=2*1024*1024,headers=headers,response_headers=received)
    records=entries(data.getvalue())
    if not records:
        if timings is not None:timings.update(requests=1,metadata_bytes=data.tell(),validators=received,http_status=200)
        return []
    metadata=io.BytesIO()
    download(provider.url+'sword/mods.d.tar.gz',metadata,limit=8*1024*1024)
    resources=parse_sword_catalogue(metadata.getvalue(),provider)
    configs={}
    for resource in resources:
        if resource.name in configs:raise ValueError('Duplicate SWORD catalogue configuration')
        configs[resource.name]=resource
    result=[]
    for entry in records:
        resource=configs.get(entry['sword_id'])
        if resource is None or (resource.version,resource.versification,resource.kind,resource.language)!=(
                entry['version'],entry['versification'],entry['category'],entry['language']):
            raise ValueError('Curated and SWORD catalogues disagree; reload when the publisher finishes updating')
        result.append(replace(resource,acquisition=json.dumps(dict(catalogue_url=provider.catalogue_url,entry=entry))))
    if timings is not None:timings.update(requests=2,metadata_bytes=data.tell()+metadata.tell(),validators=received,
                                        http_status=200,network_seconds=time.monotonic()-started)
    return result


def package_record(resource):
    value=json.loads(resource.acquisition)
    if not isinstance(value,dict) or value.get('catalogue_url')!=BIBLE_RESOURCES.catalogue_url:
        raise ValueError('Curated package provenance is missing')
    entry=value.get('entry')
    # Reuse the same metadata validation for downloaded receipts/cached entries.
    records=entries(json.dumps(dict(schema_version=1,repository='Bible Resources',
        repository_url=BIBLE_RESOURCES.url,modules=[entry])).encode())
    if not records:raise ValueError('Unsupported curated resource type')
    entry=records[0]
    if (entry['sword_id'],entry['version'],entry['category'],entry['versification'])!=(
            resource.name,resource.version,resource.kind,resource.versification):
        raise ValueError('Curated edition identity mismatch')
    return entry


def verify_package(path,entry):
    if path.stat().st_size!=entry['download']['size_bytes']:
        raise ValueError('Curated package size does not match its catalogue')
    with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
    if digest!=entry['download']['sha256']:raise ValueError('Curated package checksum verification failed')
