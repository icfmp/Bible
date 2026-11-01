"""On-demand language/version metadata; never downloads Scripture on browsing."""
import io
import json
from pathlib import Path
import re
import time
from urllib.parse import quote

from .languages import canonical_language
from .youversion_editions import CONFIGURATION_URL,VERSIONS_URL,module_id,storage_system


def payload(value):
    if not isinstance(value,dict):raise ValueError('Invalid source catalogue')
    if 'response' in value:
        response=value['response']
        if not isinstance(response,dict) or response.get('code')!=200:raise ValueError('Source catalogue refused')
        value=response.get('data')
    if not isinstance(value,dict):raise ValueError('Invalid source catalogue data')
    return value


def language_tag(value):
    if not isinstance(value,str) or not re.fullmatch(r'[a-z]{2,3}(?:[_-][A-Za-z0-9]{2,8})*',value):
        raise ValueError('Invalid source language tag')
    return value


def read_languages(value):
    records=payload(value).get('default_versions')
    if not isinstance(records,list) or not 1<=len(records)<=15000:raise ValueError('Invalid source language inventory')
    result={}
    for record in records:
        if not isinstance(record,dict):raise ValueError('Invalid source language record')
        tag=language_tag(record.get('language_tag'))
        if tag in result:raise ValueError('Duplicate source language')
        iso=record.get('iso_639_3')
        if not isinstance(iso,str) or not re.fullmatch('[a-z]{3}',iso):raise ValueError('Invalid source language identity')
        if type(record.get('has_text')) is not bool:raise ValueError('Unknown source text availability')
        if record['has_text']:result[tag]=dict(record)
    return result


def cached(path):
    try:
        if path.stat().st_size>8*1024*1024:return None
        value=json.loads(path.read_text())
        if value.get('version')!=1 or not isinstance(value.get('updated'),(int,float)):return None
        if not 0<=time.time()-value['updated']:return None
        return value
    except (OSError,ValueError,TypeError,AttributeError):return None


def metadata(url,path=None,force=False):
    from .library import download
    saved=cached(path) if path else None
    if saved and saved.get('url')==url and not force and time.time()-saved['updated']<15*60:return saved['data'],False
    data=io.BytesIO();download(url,data,limit=8*1024*1024,same_origin=True)
    value=json.loads(data.getvalue());payload(value)
    # Callers validate before committing the cache, so malformed metadata never
    # replaces a previously usable catalogue.
    return value,True


def remember(path,url,value):
    if path:
        from .youversion_install import write_receipt
        path.parent.mkdir(parents=True,exist_ok=True)
        write_receipt(path,dict(version=1,url=url,updated=time.time(),data=value))


def languages(root=None,force=False):
    path=Path(root)/'languages.json' if root else None
    value,fetched=metadata(CONFIGURATION_URL,path,force);records=read_languages(value)
    if fetched:remember(path,CONFIGURATION_URL,value)
    return records


def saved_languages(root):
    value=cached(Path(root)/'languages.json')
    if not value or value.get('url')!=CONFIGURATION_URL:return {}
    try:return read_languages(value['data'])
    except (ValueError,KeyError):return {}


def resource_from_listing(value,tag):
    from .library import Resource
    from .providers import YOUVERSION
    from .youversion_source import offline_url
    if not isinstance(value,dict):raise ValueError('Invalid source edition')
    identifier=value.get('id');name=module_id(identifier)
    language=value.get('language')
    if not isinstance(language,dict) or language.get('language_tag')!=tag:raise ValueError('Source language mismatch')
    iso=language.get('iso_639_3')
    if not isinstance(iso,str) or not re.fullmatch('[a-z]{3}',iso):raise ValueError('Invalid edition language')
    title=value.get('local_title') or value.get('title')
    if not isinstance(title,str) or not title.strip() or len(title)>2000:raise ValueError('Invalid edition title')
    if type(value.get('text')) is not bool:raise ValueError('Unknown edition text availability')
    policy=value.get('offline');offline_url(policy,identifier)
    acquisition=dict(value,_catalogue_summary=True)
    return Resource(name,title,tag,'Source conditions apply',about='https://www.bible.com/versions/'+str(identifier),
        driver='RawText',source=YOUVERSION.name,source_url=YOUVERSION.url,provider_id=YOUVERSION.id,
        versification=storage_system(identifier),acquisition=json.dumps(acquisition,ensure_ascii=False,sort_keys=True,separators=(',',':')))


def editions(tag,root=None,force=False):
    tag=language_tag(tag);url=VERSIONS_URL.format(language=quote(tag,safe=''))
    path=Path(root)/(tag+'.json') if root else None
    value,fetched=metadata(url,path,force);items=payload(value).get('versions')
    if not isinstance(items,list) or len(items)>2000:raise ValueError('Invalid source edition inventory')
    resources=[];seen=set()
    for item in items:
        if not isinstance(item,dict) or type(item.get('text')) is not bool:raise ValueError('Invalid source edition record')
        if not item['text']:continue
        resource=resource_from_listing(item,tag)
        if resource.id in seen:raise ValueError('Duplicate source edition')
        seen.add(resource.id);resources.append(resource)
    if fetched:remember(path,url,value)
    return resources


def tags_for_language(choice,records):
    key=canonical_language(choice)
    # A base language includes its advertised regional/script editions; an
    # explicit qualified choice retains its source distinction.
    return [tag for tag in records if canonical_language(tag)==key or
            '-' not in key and canonical_language(tag).split('-')[0]==key]
