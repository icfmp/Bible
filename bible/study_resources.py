"""Non-SWORD study data offered in the existing Library, kept out of translations."""
from dataclasses import dataclass
from .i18n import tr
from .reference_data import (ReferenceData,ReferenceDataError,SOURCE_URL,LICENSE_URL,
                             SOURCE_DATE,ARCHIVE_SHA256,NUMBERING,TRANSFORMATIONS)

REFERENCE_RESOURCE_ID='openbible-cross-references'


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
    def __init__(self,root):self.references=ReferenceData(root)

    def available(self):return [StudyResource(description=tr('Bible cross-references'))]

    def resource(self,name):
        if name!=REFERENCE_RESOURCE_ID:raise ValueError('Unknown study resource')
        return self.available()[0]

    def installed(self):
        try:self.references.metadata();return [REFERENCE_RESOURCE_ID]
        except (ReferenceDataError,OSError):return []

    def current(self,name):
        if name!=REFERENCE_RESOURCE_ID:return False
        try:return self.references.metadata()['archive_sha256']==ARCHIVE_SHA256
        except (ReferenceDataError,OSError,KeyError):return False

    def install(self,resource,progress,installing):
        if resource.id!=REFERENCE_RESOURCE_ID:raise ValueError('Unknown study resource')
        return self.references.install(progress,installing)
