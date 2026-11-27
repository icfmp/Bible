"""Non-SWORD study data offered in the existing Library, kept out of translations."""

from __future__ import annotations

from collections.abc import Callable
from os import PathLike
from typing import TYPE_CHECKING, NoReturn, cast

if TYPE_CHECKING:
    from .place_data import PlaceData
    from .topic_data import TopicData
    from .step_data import StepData

from dataclasses import dataclass, replace
from .i18n import tr
from .reference_data import (
    ReferenceData,
    ReferenceDataError as ReferenceDataError,
    SOURCE_URL,
    LICENSE_URL,
    SOURCE_DATE,
    ARCHIVE_SHA256,
    NUMBERING,
    TRANSFORMATIONS,
)

REFERENCE_RESOURCE_ID = "openbible-cross-references"
PLACE_RESOURCE_ID = "openbible-places"
TOPIC_RESOURCE_ID = "openbible-topics"
STEP_RESOURCE_ID = "step-word-study"


@dataclass(frozen=True)
class StudyResource:
    """Library metadata for an existing optional study store, independent of Bible translations."""

    id: str = REFERENCE_RESOURCE_ID
    name: str = "OpenBible cross-references"
    description: str = "Bible cross-references"
    language: str = "mul"
    source: str = "OpenBible.info"
    source_url: str = SOURCE_URL
    license: str = "CC BY 4.0"
    author: str = "OpenBible.info; primarily Treasury of Scripture Knowledge"
    conditions: str = "OpenBible.info — " + SOURCE_URL + "\nCC BY 4.0 — " + LICENSE_URL
    about: str = SOURCE_DATE + "\nSHA-256: " + ARCHIVE_SHA256 + "\n" + TRANSFORMATIONS
    versification: str = NUMBERING
    provider_id: str = "openbible"
    kind: str = "study"
    locked: bool = False
    installable: bool = True
    revision: str = ""


class StudyResources:
    """Discover and install the existing reference, topic, place and STEP stores through their checked adapters."""

    def __init__(self, root: str | PathLike[str]) -> None:
        from .place_data import PlaceData

        self.references = ReferenceData(root)
        self.places = PlaceData(root)
        self.catalogue = self.references.catalogue
        from .topic_data import TopicData

        self.topics = TopicData(root)
        from .step_data import StepData

        self.step = StepData(root)
        self.stores: dict[str, ReferenceData | PlaceData | TopicData | StepData] = {
            REFERENCE_RESOURCE_ID: self.references,
            PLACE_RESOURCE_ID: self.places,
            TOPIC_RESOURCE_ID: self.topics,
            STEP_RESOURCE_ID: self.step,
        }

    def available(self) -> list[StudyResource]:
        """List existing study store choices using checked catalogue revisions and pinned provider metadata."""
        from . import place_data as places
        from . import topic_data as topics
        from . import step_sources as step

        revisions = self.catalogue.load()
        reference = revisions[REFERENCE_RESOURCE_ID]
        topic = revisions[TOPIC_RESOURCE_ID]
        words = revisions["topic-vocabulary"]
        return [
            StudyResource(
                description=tr("Bible cross-references"),
                revision=reference.sha256,
                about=reference.generation
                + "\nSHA-256: "
                + reference.sha256
                + "\n"
                + TRANSFORMATIONS,
            ),
            StudyResource(
                id=PLACE_RESOURCE_ID,
                name="OpenBible places",
                description=tr("Biblical places and offline map"),
                revision=places.REVISION,
                source_url=places.SOURCE_URL,
                license="CC BY 4.0; ODbL 1.0; public-domain coastlines",
                author="OpenBible.info; OpenStreetMap contributors; Natural Earth contributors",
                conditions="OpenBible.info — "
                + places.SOURCE_URL
                + "\nCC BY 4.0 — "
                + places.LICENSE_URL
                + "\nOpenStreetMap — "
                + places.ODBL_URL
                + "\nNatural Earth — "
                + places.MAP_SOURCE
                + "\nPublic-domain basemap terms — https://www.naturalearthdata.com/about/terms-of-use/",
                about="OpenBible source: "
                + places.SOURCE_COMMIT
                + "\nNatural Earth source: "
                + places.MAP_COMMIT
                + "\n"
                + places.NOTICE
                + "\n"
                + str({k: v[1] for k, v in places.FILES.items()}),
            ),
            StudyResource(
                id=TOPIC_RESOURCE_ID,
                name="OpenBible topics",
                description=tr("Curated French/English topics"),
                revision=topic.sha256 + ":" + words.sha256,
                source_url=topics.SOURCE_URL,
                author="OpenBible.info community contributors; Bible project vocabulary contributors",
                license="CC BY 4.0; GPL-2.0-only (project vocabulary)",
                conditions="OpenBible.info — "
                + topics.SOURCE_URL
                + "\nCC BY 4.0 — "
                + topics.LICENSE_URL
                + "\nBible project vocabulary — GPL-2.0-only — https://github.com/icfmp/Bible/blob/data/study-resources/LICENSE",
                about=topic.generation
                + "\nSHA-256: "
                + topic.sha256
                + "\n"
                + tr("Reviewed topic names: {revision}").format(revision=words.revision)
                + "\n"
                + topics.TRANSFORMATIONS,
            ),
            StudyResource(
                id=STEP_RESOURCE_ID,
                name="STEP word study",
                description=tr("Greek and Hebrew word study"),
                revision=step.COMMIT,
                source="STEPBible / Tyndale House",
                source_url=step.SOURCE_URL,
                author="STEPBible / Tyndale House, Cambridge",
                language="mul",
                provider_id="stepbible",
                license="CC BY 4.0",
                conditions=step.NOTICE + "\n" + step.LICENSE_URL,
                about=tr(
                    "Download: {size} MB. Local index: about 275 MB; additional temporary update space is required."
                ).format(size=f"{step.DOWNLOAD_BYTES / 1000000:.1f}")
                + "\n"
                + str({name: values[1] for name, values in step.FILES.items()}),
                versification="NRSV (supplied STEP reference convention)",
            ),
        ]

    def resource(self, name: str) -> StudyResource:
        """Resolve an existing study choice, rejecting unknown resource identifiers."""
        return next((r for r in self.available() if r.id == name), None) or self.unknown()

    def installed_resource(self, name: str) -> StudyResource:
        """Describe an installed store using its actual revision rather than the latest advertised revision."""
        resource = self.resource(name)
        metadata = self.stores[name].metadata()
        if name not in (REFERENCE_RESOURCE_ID, TOPIC_RESOURCE_ID):
            return replace(
                resource,
                revision=str(metadata["commit" if name == STEP_RESOURCE_ID else "revision"]),
            )
        revision = str(metadata.get("archive_sha256", ""))
        transformations = metadata.get("transformations", "")
        if not isinstance(transformations, str):
            raise ValueError("Invalid study resource attribution")
        about = (
            str(metadata.get("source_date", "—"))
            + "\nSHA-256: "
            + str(metadata.get("archive_sha256", "—"))
            + "\n"
            + transformations
        )
        if name == TOPIC_RESOURCE_ID:
            from .topic_vocabulary import TopicVocabulary

            vocabulary, _, vocabulary_sha = TopicVocabulary(self.topics.root).read()
            revision += ":" + vocabulary_sha
            about += "\n" + tr("Reviewed topic names: {revision}").format(
                revision=vocabulary["revision"]
            )
        return replace(resource, about=about, revision=revision)

    def unknown(self) -> NoReturn:
        """Keep unknown study choices unavailable instead of synthesizing metadata."""
        raise ValueError("Unknown study resource")

    def installed(self) -> list[str]:
        """List only study stores whose installed metadata can be validated."""
        result = []
        for name, store in self.stores.items():
            try:
                store.metadata()
                result.append(name)
            except (ValueError, OSError):
                pass
        return result

    def current(self, name: str) -> bool:
        """Compare actual installed components with checked expected revisions, including vocabulary and maps."""
        try:
            metadata = self.stores[name].metadata()
            if name == STEP_RESOURCE_ID:
                from .step_sources import COMMIT

                return metadata["commit"] == COMMIT
            if name == REFERENCE_RESOURCE_ID:
                return metadata["archive_sha256"] == self.catalogue.load()[name].sha256
            if name == TOPIC_RESOURCE_ID:
                from .topic_vocabulary import TopicVocabulary

                revisions = self.catalogue.load()
                return metadata["archive_sha256"] == revisions[name].sha256 and TopicVocabulary(
                    self.topics.root
                ).current(revisions["topic-vocabulary"])
            from .place_data import REVISION

            return metadata["revision"] == REVISION and self.places.has_map()
        except (ValueError, OSError, KeyError):
            return False

    def install(
        self,
        resource: StudyResource,
        progress: Callable[[int, int], object],
        installing: Callable[[], object],
        cancelled: Callable[[], bool] | None = None,
    ) -> object:
        """Dispatch an existing store installation with the selected revision and supported cancellation."""
        if resource.id not in self.stores:
            raise ValueError("Unknown study resource")
        if resource.id == STEP_RESOURCE_ID:
            return self.step.install(progress, installing, cancelled)
        if resource.id in (REFERENCE_RESOURCE_ID, TOPIC_RESOURCE_ID):
            return cast("ReferenceData | TopicData", self.stores[resource.id]).install(
                progress, installing, expected_revision=resource.revision
            )
        return cast("PlaceData", self.stores[resource.id]).install(progress, installing)
