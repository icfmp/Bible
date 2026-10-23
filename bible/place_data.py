"""Pinned OpenBible place evidence and real offline coastlines, never Bible text."""
from contextlib import closing
from datetime import datetime,timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile
from .reference_data import ReferenceDataError,reference_key

SOURCE_COMMIT='7eb18a5ee62f27b9b93bd6689ea272d76dd23b8f'
MAP_COMMIT='ca96624a56bd078437bca8184e78163e5039ad19'
SOURCE_URL='https://www.openbible.info/geo/'
LICENSE_URL='https://creativecommons.org/licenses/by/4.0/'
ODBL_URL='https://opendatacommons.org/licenses/odbl/1-0/'
MAP_SOURCE='https://www.naturalearthdata.com/'
BASE='https://raw.githubusercontent.com/openbibleinfo/Bible-Geocoding-Data/'+SOURCE_COMMIT+'/'
FILES={
 'ancient':(BASE+'data/ancient.jsonl','b8187aa4737e8517ccc090f765d2be11da4c548cd2a59d3cdcb62e952cb8c0f2',24*1024*1024),
 'modern':(BASE+'data/modern.jsonl','da731f6e110bac4ea66a9f037a0a31cfb11c4f1efc1206aa9e109092b2c60087',8*1024*1024),
 'sources':(BASE+'data/source.jsonl','b93709cfd947430a3befe3a02a82787ef589c3223c903f4f234adaa46727856a',1024*1024),
 'license':(BASE+'license.txt','f5b745ef98087f531e719ee8ca6a96809444573ecc7173c6fa68eaad39b3cc3f',64*1024),
 'coastline':('https://raw.githubusercontent.com/nvkelso/natural-earth-vector/'+MAP_COMMIT+'/geojson/ne_50m_coastline.geojson','271f1c4c1908312bac6b29d158ea1356544beafc129f260005300913aa5ea283',4*1024*1024),
}
REVISION=hashlib.sha256(json.dumps(FILES,sort_keys=True).encode()).hexdigest()
MAX_DATABASE=128*1024*1024
ROLES={'point','center','representative point','settlement'}
NOTICE=('OpenBible.info place data: CC BY 4.0. OpenStreetMap-derived components: ODbL 1.0; '
        '© OpenStreetMap contributors. Natural Earth 1:50m coastline: public domain. '
        'Transformed into a validated local index of supplied verse relationships, '
        'candidate coordinates/roles and source evidence; simplified coastline overview. '
        'No images, OSM polygons, Scripture quotations or historical boundaries imported.')


def text(value,limit=4096):
    if not isinstance(value,str) or len(value)>limit or '\x00' in value:raise ReferenceDataError('Invalid place text')
    return value


def identity(value,prefix):
    if not isinstance(value,str) or not re.fullmatch(prefix+r'[0-9a-f]{6}',value):raise ReferenceDataError('Invalid place identifier')
    return value


def records(path,prefix):
    result={}
    with Path(path).open(encoding='utf-8') as source:
        for line in source:
            if len(line)>1024*1024 or len(result)>=20000:raise ReferenceDataError('Place records exceed safe limits')
            item=json.loads(line);key=identity(item['id'],prefix)
            if key in result:raise ReferenceDataError('Duplicate place identifier')
            result[key]=item
    if not result:raise ReferenceDataError('Empty place data')
    return result


def coordinates(value):
    if isinstance(value,str):values=value.split(',')
    else:
        values=value
        if not isinstance(values,(list,tuple)) or any(type(x) not in (int,float) for x in values):raise ReferenceDataError('Invalid map coordinate types')
    if not isinstance(values,(list,tuple)) or len(values)!=2:raise ReferenceDataError('Invalid coordinate pair')
    try:lon,lat=map(float,values)
    except (TypeError,ValueError):raise ReferenceDataError('Invalid coordinates') from None
    if not math.isfinite(lon) or not math.isfinite(lat) or not -180<=lon<=180 or not -90<=lat<=90:
        raise ReferenceDataError('Coordinates outside the world')
    return lon,lat


def source_number(value):
    if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value) or abs(value)>1000000000:
        raise ReferenceDataError('Invalid place source score')
    return value


def candidates(place,modern):
    """Keep supplied resolutions/alternatives; never infer coordinates from names."""
    from .resource_details import plain
    result=[]
    for index,identification in enumerate(place['identifications']):
        if index>=100:raise ReferenceDataError('Too many place identifications')
        score=identification.get('score',{});tags=identification.get('votes',{}).get('tags',{})
        for name,count in tags.items():text(name,80);source_number(count)
        for number,resolution in enumerate(identification.get('resolutions',[])):
            if number>=500:raise ReferenceDataError('Too many place resolutions')
            modern_id=resolution.get('modern_basis_id');located='lonlat' in resolution
            if located:
                identity(modern_id,'m')
                if modern_id not in modern:raise ReferenceDataError('Unknown modern place')
                lon,lat=coordinates(resolution['lonlat']);role=resolution.get('lonlat_type')
                if role not in ROLES:raise ReferenceDataError('Unsupported coordinate role')
                name=text(modern[modern_id]['friendly_id'],300)
            else:
                lon=lat=None;role=None;name=text(resolution.get('special','unknown_place'),100)
            path_score=source_number(resolution.get('best_path_score',0))
            vote_total=source_number(score.get('vote_total',0));time_score=source_number(score.get('time_total',0))
            paths=resolution.get('paths',[])
            if not isinstance(paths,list) or len(paths)>1000:raise ReferenceDataError('Invalid place evidence paths')
            radius=resolution.get('geometry_radius_meters',identification.get('geometry_radius_meters'))
            if radius is not None and not 0<=source_number(radius)<=50000000:raise ReferenceDataError('Invalid uncertainty radius')
            result.append(dict(id=f'{index}:{number}',modern_id=modern_id,name=name,longitude=lon,latitude=lat,
                role=role,special=resolution.get('special'),description=plain(text(resolution.get('description',''))),
                modifier=text(identification.get('modifier',''),50),radius_meters=radius,path_score=path_score,
                vote_total=vote_total,time_score=time_score,vote_tags=tags,paths=paths,
                coordinate_source=modern[modern_id].get('coordinates_source',{}) if modern_id else {},
                geometry_credit=place.get('geometry_credit','')))
    return result


def status(values):
    """Conservative labels from supplied evidence, never invented certainty."""
    located=[v for v in values if v['longitude'] is not None]
    if not located:return 'unknown'
    credible=[v for v in located if v['path_score']>0 or v['vote_total']>0]
    if not credible:return 'disputed'
    if len({v['modern_id'] for v in credible})>1:return 'disputed'
    if max(v['path_score'] for v in credible)>=500:return 'known'
    if any(any(v['vote_tags'].get(k,0)>0 for k in ('confidence_yes','confidence_likely','confidence_mostlikely')) for v in credible):return 'probable'
    return 'disputed'


class PlaceData:
    def __init__(self,root):
        self.root=Path(root);self.path=self.root/'openbible-places.sqlite3'
        self._metadata_revision=None;self._metadata=None

    @property
    def revision(self):
        try:info=self.path.stat();return info.st_ino,info.st_mtime_ns,info.st_size
        except FileNotFoundError:return None

    def connect(self):
        if not self.path.is_file() or self.path.stat().st_size>MAX_DATABASE:raise ReferenceDataError('Place data is unavailable')
        connection=sqlite3.connect(self.path.resolve().as_uri()+'?mode=ro',uri=True)
        connection.execute('PRAGMA query_only=ON');return connection

    def metadata(self):
        try:
            revision=self.revision
            if revision and revision==self._metadata_revision:return dict(self._metadata)
            with closing(self.connect()) as connection:
                value=json.loads(connection.execute('SELECT value FROM metadata WHERE key=?',('source',)).fetchone()[0])
                connection.execute('SELECT id,name,payload FROM places LIMIT 1').fetchone()
                connection.execute('SELECT osis,place FROM verses LIMIT 1').fetchone()
                if connection.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ReferenceDataError('Damaged place resource')
            if value['schema']!=1 or value['source_url']!=SOURCE_URL:raise ReferenceDataError('Unsupported place resource')
            self._metadata_revision,self._metadata=revision,value;return dict(value)
        except (sqlite3.Error,TypeError,KeyError,ValueError) as error:raise ReferenceDataError(str(error)) from error

    def install(self,progress=lambda done,total:None,installing=lambda:None):
        from .library import download
        self.root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.places-download-',dir=self.root) as temporary:
            files={};completed=0
            for name,(url,digest,limit) in FILES.items():
                path=Path(temporary)/name
                with path.open('wb') as output:download(url,output,lambda done,total:progress(completed+done,0),limit=limit)
                completed+=path.stat().st_size;files[name]=path
            installing();return self.install_files(files)

    def install_files(self,files):
        for name,(_,digest,limit) in FILES.items():
            path=Path(files[name])
            if path.stat().st_size>limit or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
                raise ReferenceDataError('Place source checksum mismatch; installed data was preserved')
        ancient=records(files['ancient'],'a');modern=records(files['modern'],'m');bibliography=records(files['sources'],'s')
        self.root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.places-index-',dir=self.root) as temporary:
            candidate=Path(temporary)/'index.sqlite3'
            with closing(sqlite3.connect(candidate)) as connection,connection:
                connection.executescript('''CREATE TABLE places(id TEXT PRIMARY KEY,name TEXT NOT NULL,payload TEXT NOT NULL);
                    CREATE TABLE verses(osis TEXT NOT NULL,place TEXT NOT NULL,PRIMARY KEY(osis,place));
                    CREATE INDEX verse_origin ON verses(osis);
                    CREATE TABLE coastlines(id INTEGER PRIMARY KEY,west REAL,south REAL,east REAL,north REAL,points TEXT);
                    CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);''')
                for key,place in ancient.items():
                    name=text(place['friendly_id'],300);values=candidates(place,modern)
                    aliases=place.get('translation_name_counts',{})
                    if not isinstance(aliases,dict) or len(aliases)>200:raise ReferenceDataError('Invalid place names')
                    for alias in aliases:text(alias,300)
                    sources=[]
                    for source_id,detail in place.get('identification_sources',{}).items():
                        identity(source_id,'s')
                        if source_id not in bibliography:raise ReferenceDataError('Missing place bibliography')
                        source=bibliography[source_id]
                        sources.append(dict(id=source_id,name=text(source['display_name']),year=source.get('year'),detail=detail))
                    payload=dict(id=key,name=name,aliases=list(aliases),status=status(values),candidates=values,sources=sources,
                                 references=[],source_url=SOURCE_URL+'ancient/'+key+'/'+text(place['url_slug'],300))
                    refs=set()
                    for verse in place.get('verses',[]):
                        ref=verse['osis'];reference_key(ref);refs.add(ref)
                    payload['references']=sorted(refs,key=reference_key)
                    connection.execute('INSERT INTO places VALUES(?,?,?)',(key,name,json.dumps(payload)))
                    connection.executemany('INSERT INTO verses VALUES(?,?)',((ref,key) for ref in refs))
                coast=json.loads(Path(files['coastline']).read_text())
                if coast['type']!='FeatureCollection' or len(coast['features'])>20000:raise ReferenceDataError('Invalid coastline data')
                total=0
                for feature in coast['features']:
                    geometry=feature['geometry'];kind=geometry['type'];parts=geometry['coordinates']
                    if kind=='LineString':parts=[parts]
                    elif kind!='MultiLineString':raise ReferenceDataError('Unsupported coastline geometry')
                    for part in parts:
                        if len(part)<2:raise ReferenceDataError('Empty coastline')
                        points=[coordinates(point) for point in part];total+=len(points)
                        if total>2000000:raise ReferenceDataError('Coastline exceeds safe limits')
                        longitude,latitude=zip(*points)
                        connection.execute('INSERT INTO coastlines(west,south,east,north,points) VALUES(?,?,?,?,?)',
                            (min(longitude),min(latitude),max(longitude),max(latitude),json.dumps(points)))
                metadata=dict(schema=1,source_url=SOURCE_URL,source_commit=SOURCE_COMMIT,map_commit=MAP_COMMIT,
                    revision=REVISION,license_url=LICENSE_URL,odbl_url=ODBL_URL,map_source=MAP_SOURCE,notice=NOTICE,
                    files={name:dict(url=value[0],sha256=value[1]) for name,value in FILES.items()},
                    places=len(ancient),modern_locations=len(modern),bibliographic_sources=len(bibliography),
                    installed_at=datetime.now(timezone.utc).isoformat())
                connection.execute('INSERT INTO metadata VALUES(?,?)',('source',json.dumps(metadata)))
                connection.execute('INSERT INTO metadata VALUES(?,?)',('publisher_license',Path(files['license']).read_text()))
                if connection.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ReferenceDataError('Invalid place index')
            if candidate.stat().st_size>MAX_DATABASE:raise ReferenceDataError('Place index is too large')
            with candidate.open('rb') as source:os.fsync(source.fileno())
            os.replace(candidate,self.path)
        return metadata

    def has_map(self):
        try:
            with closing(self.connect()) as connection:
                return bool(connection.execute('SELECT points FROM coastlines LIMIT 1').fetchone())
        except (sqlite3.Error,ReferenceDataError,OSError):return False

    def query(self,origins):
        origins=sorted(set(origins))
        if len(origins)>1000:raise ReferenceDataError('Select at most 1000 verses')
        for reference in origins:reference_key(reference)
        self.metadata()
        if not origins:return []
        parameters=','.join('?' for _ in origins)
        with closing(self.connect()) as connection:
            rows=connection.execute('SELECT p.payload,count(DISTINCT v.osis) FROM places p JOIN verses v ON p.id=v.place '
                f'WHERE v.osis IN ({parameters}) GROUP BY p.id ORDER BY p.name',origins).fetchall()
        return [dict(json.loads(payload),source_verse_count=count) for payload,count in rows]

    def coastlines(self,bounds):
        west,south,east,north=bounds
        if not all(math.isfinite(x) for x in bounds) or not -180<=west<east<=180 or not -90<=south<north<=90:
            raise ReferenceDataError('Invalid map extent')
        with closing(self.connect()) as connection:
            rows=connection.execute('SELECT points FROM coastlines WHERE west<=? AND east>=? AND south<=? AND north>=?',
                                    (east,west,north,south)).fetchall()
        return [json.loads(row[0]) for row in rows]
