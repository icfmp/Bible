"""Non-SWORD study data offered in the existing Library, kept out of translations."""
from dataclasses import dataclass
from .i18n import tr
from .reference_data import (ReferenceData,ReferenceDataError,SOURCE_URL,LICENSE_URL,
                             SOURCE_DATE,ARCHIVE_SHA256,NUMBERING,TRANSFORMATIONS)

REFERENCE_RESOURCE_ID='openbible-cross-references'
PLACE_RESOURCE_ID='openbible-places'
TOPIC_RESOURCE_ID='openbible-topics'


@dataclass(frozen=True)
class StudyResource:
    id: str=REFERENCE_RESOURCE_ID
    name: str='OpenBible cross-references'
    description: str='Bible cross-references'
    language: str='mul'
    source: str='OpenBible.info'
    source_url: str=SOURCE_URL
    license: str='CC BY 4.0'
    author: str='OpenBible.info; primarily Treasury of Scripture Knowledge'
    conditions: str='OpenBible.info — '+SOURCE_URL+'\nCC BY 4.0 — '+LICENSE_URL
    about: str=SOURCE_DATE+'\nSHA-256: '+ARCHIVE_SHA256+'\n'+TRANSFORMATIONS
    versification: str=NUMBERING
    provider_id: str='openbible'
    kind: str='study'
    locked: bool=False
    installable: bool=True


class StudyResources:
    def __init__(self,root):
        from .place_data import PlaceData
        self.references=ReferenceData(root);self.places=PlaceData(root)
        from .topic_data import TopicData
        self.topics=TopicData(root)
        self.stores={REFERENCE_RESOURCE_ID:self.references,PLACE_RESOURCE_ID:self.places,TOPIC_RESOURCE_ID:self.topics}

    def available(self):
        from . import place_data as places
        from . import topic_data as topics
        return [StudyResource(description=tr('Bible cross-references')),
                StudyResource(id=PLACE_RESOURCE_ID,name='OpenBible places',description=tr('Biblical places and offline map'),
                    source_url=places.SOURCE_URL,license='CC BY 4.0; ODbL 1.0; public-domain coastlines',
                    author='OpenBible.info; OpenStreetMap contributors; Natural Earth contributors',
                    conditions='OpenBible.info — '+places.SOURCE_URL+'\nCC BY 4.0 — '+places.LICENSE_URL+
                        '\nOpenStreetMap — '+places.ODBL_URL+'\nNatural Earth — '+places.MAP_SOURCE+
                        '\nPublic-domain basemap terms — https://www.naturalearthdata.com/about/terms-of-use/',
                    about='OpenBible source: '+places.SOURCE_COMMIT+'\nNatural Earth source: '+places.MAP_COMMIT+
                        '\n'+places.NOTICE+'\n'+str({k:v[1] for k,v in places.FILES.items()})),
                StudyResource(id=TOPIC_RESOURCE_ID,name='OpenBible topics',description=tr('Curated French/English topics'),
                    source_url=topics.SOURCE_URL,author='OpenBible.info community contributors',
                    conditions='OpenBible.info — '+topics.SOURCE_URL+'\nCC BY 4.0 — '+topics.LICENSE_URL,
                    about=topics.SOURCE_DATE+'\nSHA-256: '+topics.ARCHIVE_SHA256+'\n'+topics.TRANSFORMATIONS)]

    def resource(self,name):
        return next((r for r in self.available() if r.id==name),None) or self.unknown()

    def unknown(self):raise ValueError('Unknown study resource')

    def installed(self):
        result=[]
        for name,store in self.stores.items():
            try:store.metadata();result.append(name)
            except (ReferenceDataError,OSError):pass
        return result

    def current(self,name):
        try:
            metadata=self.stores[name].metadata()
            if name==REFERENCE_RESOURCE_ID:return metadata['archive_sha256']==ARCHIVE_SHA256
            if name==TOPIC_RESOURCE_ID:
                from .topic_data import ARCHIVE_SHA256 as TOPIC_SHA
                return metadata['archive_sha256']==TOPIC_SHA
            from .place_data import REVISION
            return metadata['revision']==REVISION and self.places.has_map()
        except (ReferenceDataError,OSError,KeyError):return False

    def install(self,resource,progress,installing):
        if resource.id not in self.stores:raise ValueError('Unknown study resource')
        return self.stores[resource.id].install(progress,installing)
