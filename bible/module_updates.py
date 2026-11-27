"""Read-only installed/curated version discovery; never replaces a SWORD root."""

from __future__ import annotations

from collections.abc import Iterable
from contextlib import AbstractContextManager
from os import PathLike
from typing import TYPE_CHECKING, Literal, Protocol, TypedDict, cast
from dataclasses import dataclass

if TYPE_CHECKING:
    from .library import Resource
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import urllib.request
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlunsplit
from .library import config
from .study_catalogue import atomic_write
from .providers import BIBLE_RESOURCES

CATALOGUE_URL = BIBLE_RESOURCES.catalogue_url
MAX_CATALOGUE = 2 * 1024 * 1024


@dataclass(frozen=True)
class InstalledModule:
    """Read-only installed module identity, source context, version and local location."""

    name: str
    version: str
    source: str
    root: Path
    versification: str
    title: str


def public_source(value: str) -> str:
    """Never display credentials from an InstallSource URL."""
    try:
        parts = urlsplit(value)
        if parts.scheme and parts.hostname:
            return urlunsplit(
                (
                    parts.scheme,
                    parts.hostname + (":" + str(parts.port) if parts.port else ""),
                    parts.path,
                    "",
                    "",
                )
            )
    except ValueError:
        return ""
    return value[:128] if re.fullmatch(r"[\w .()/-]{0,128}", value) else ""


def installed_modules(
    library_root: str | PathLike[str],
    extra_roots: Iterable[str | PathLike[str]] = (),
) -> tuple[tuple[InstalledModule, ...], tuple[tuple[str, str], ...]]:
    """Inspect app/system/user SWORD configurations without taking ownership of external roots.

    Returns:
        Deduplicated module records and per-location errors; invalid metadata
        does not authorize destructive management or invented source attribution.
    """
    library_root = Path(library_root)
    roots = (
        [p for p in library_root.iterdir() if p.is_dir() and (p / ".complete").is_file()]
        if library_root.exists()
        else []
    )
    roots.extend(
        Path(p).expanduser()
        for p in (
            *os.environ.get("SWORD_PATH", "").split(os.pathsep),
            str(Path.home() / ".sword"),
            "/usr/share/sword",
            "/usr/local/share/sword",
            *map(str, extra_roots),
        )
        if p
    )
    result = []
    errors = []
    seen = set()
    for root in roots:
        try:
            for file in (root / "mods.d").glob("*.conf"):
                identity = file.resolve()
                if identity in seen:
                    continue
                seen.add(identity)
                if file.stat().st_size > 65536:
                    raise ValueError("Module configuration exceeds safe limits")
                parser = config(file.read_bytes())
                for name in parser.sections():
                    section = parser[name]
                    source = section.get("InstallSource", "")
                    if not source and (root / ".source.json").is_file():
                        try:
                            if (root / ".source.json").stat().st_size > 4 * 1024 * 1024:
                                raise ValueError("Source metadata exceeds safe limits")
                            metadata = json.loads((root / ".source.json").read_text())
                            if not isinstance(metadata, dict):
                                raise ValueError("Invalid source receipt")
                            raw_source = metadata.get("url", metadata.get("source_url", ""))
                            if not isinstance(raw_source, str):
                                raise ValueError("Invalid source origin")
                            source = raw_source
                        except (OSError, ValueError, TypeError) as error:
                            errors.append((str(root), str(error)))
                            source = ""
                    result.append(
                        InstalledModule(
                            name,
                            section.get("Version", ""),
                            public_source(source),
                            root,
                            section.get("Versification", "KJV"),
                            section.get("Description", name),
                        )
                    )
        except (OSError, ValueError, TypeError) as error:
            errors.append((str(root), str(error)))
    return tuple(result), tuple(errors)


class _Download(TypedDict):
    sha256: str
    size_bytes: int
    url: str


class _CatalogueModule(TypedDict):
    id: str
    sword_id: str
    version: str
    edition: str
    download: _Download


class ModuleCatalogueData(TypedDict):
    """Consumed identity/integrity fields in the existing provider catalogue."""

    schema_version: Literal[1]
    repository: str
    repository_url: str
    modules: list[_CatalogueModule]


class _SavedCatalogue(TypedDict):
    source_url: str
    body: str
    etag: str
    last_modified: str
    checked: str


class CatalogueCheck(TypedDict):
    """Checked catalogue and explicit freshness; cached results keep their error."""

    catalogue: ModuleCatalogueData
    cached: bool
    checked: str
    error: str


class _Headers(Protocol):
    def get(self, name: str, default: str) -> str: ...


class _Response(Protocol):
    @property
    def headers(self) -> _Headers: ...
    def read(self, size: int) -> bytes: ...


class _Opener(Protocol):
    def __call__(
        self, request: urllib.request.Request, *, timeout: int
    ) -> AbstractContextManager[_Response]: ...


def parse_catalogue(data: bytes) -> ModuleCatalogueData:
    """Validate bounded existing Bible Resources catalogue identity, download origin and integrity fields."""
    if len(data) > MAX_CATALOGUE:
        raise ValueError("Module catalogue exceeds safe limits")
    value = json.loads(data)
    if (
        not isinstance(value, dict)
        or type(value.get("schema_version")) is not int
        or value.get("schema_version") != 1
        or value.get("repository") != "Bible Resources"
        or value.get("repository_url") != "https://icfmp.github.io/Bible-Resources/"
        or not isinstance(value.get("modules"), list)
        or len(value["modules"]) > 10000
    ):
        raise ValueError("Unsupported Bible Resources catalogue")
    for entry in value["modules"]:
        if not isinstance(entry, dict):
            raise ValueError("Invalid curated module")
        for field in ("id", "sword_id", "version", "edition"):
            if not isinstance(entry.get(field), str) or not 0 < len(entry[field]) <= 128:
                raise ValueError("Invalid curated module identity")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", entry["sword_id"]):
            raise ValueError("Invalid SWORD identifier")
        download = entry.get("download", {})
        if (
            not isinstance(download, dict)
            or not isinstance(download.get("sha256"), str)
            or not re.fullmatch("[0-9a-f]{64}", download["sha256"])
            or type(download.get("size_bytes")) is not int
            or download["size_bytes"] <= 0
        ):
            raise ValueError("Invalid curated module integrity metadata")
        if not download.get("url", "").startswith(
            "https://icfmp.github.io/Bible-Resources/sword/packages/"
        ):
            raise ValueError("Unsupported curated module origin")
    # Preserve every source field; narrow only after the existing identity
    # and package-integrity checks above. No provider data is rewritten.
    return cast("ModuleCatalogueData", value)


class ModuleCatalogue:
    """Conditional metadata retrieval with a validated saved catalogue for offline discovery."""

    def __init__(self, root: str | PathLike[str]) -> None:
        self.path = Path(root) / "module-catalogue.json"

    def saved(self) -> _SavedCatalogue:
        """Read and validate the saved catalogue envelope/body without modifying it."""
        if self.path.is_symlink() or self.path.stat().st_size > MAX_CATALOGUE * 2:
            raise ValueError("Invalid saved module catalogue")
        record = json.loads(self.path.read_text())
        if (
            not isinstance(record, dict)
            or record.get("source_url") != CATALOGUE_URL
            or not isinstance(record.get("body"), str)
        ):
            raise ValueError("Invalid saved module catalogue")
        parse_catalogue(record["body"].encode())
        return cast("_SavedCatalogue", record)

    def check(self, opener: _Opener | None = None) -> CatalogueCheck:
        """Refresh conditional metadata and retain a validated cache when the source is unavailable.

        A cached result carries its previous checked time and the current error;
        it does not claim a fresh successful source check.
        """
        try:
            saved = self.saved()
        except (OSError, ValueError, TypeError, KeyError):
            saved = None
        headers = {"User-Agent": "Bible module update check"}
        if saved:
            if saved.get("etag"):
                headers["If-None-Match"] = saved["etag"]
            if saved.get("last_modified"):
                headers["If-Modified-Since"] = saved["last_modified"]
        request = urllib.request.Request(CATALOGUE_URL, headers=headers)
        checked = datetime.now(timezone.utc).isoformat()
        try:
            try:
                with (opener or urllib.request.urlopen)(request, timeout=20) as response:
                    data = response.read(MAX_CATALOGUE + 1)
                    parse_catalogue(data)
                    saved = _SavedCatalogue(
                        source_url=CATALOGUE_URL,
                        body=data.decode(),
                        etag=response.headers.get("ETag", ""),
                        last_modified=response.headers.get("Last-Modified", ""),
                        checked=checked,
                    )
            except HTTPError as error:
                if error.code != 304 or not saved:
                    raise
                saved = _SavedCatalogue(**{**saved, "checked": checked})
            atomic_write(self.path, json.dumps(saved).encode())
            return dict(
                catalogue=parse_catalogue(saved["body"].encode()),
                cached=False,
                checked=checked,
                error="",
            )
        except (OSError, ValueError, TypeError) as error:
            if not saved:
                raise
            return dict(
                catalogue=parse_catalogue(saved["body"].encode()),
                cached=True,
                checked=saved["checked"],
                error=str(error),
            )


def assessment(installed: InstalledModule, catalogue: ModuleCatalogueData) -> str:
    """An ID/title/Version coincidence is never sufficient edition evidence."""
    candidates = [entry for entry in catalogue["modules"] if entry["sword_id"] == installed.name]
    return "identity-unverified" if candidates else "no-curated-edition"


def version_key(value: object) -> tuple[int, ...] | None:
    """Compare bounded numeric versions, treating insignificant trailing zeros equally."""
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,8}(?:\.[0-9]{1,8}){0,7}", value):
        return None
    parts = list(map(int, value.split(".")))
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def applicable_update(installed: Resource, available: Resource) -> str:
    """Same declared edition and receipt, never a coincidental SWORD ID/title."""
    if (
        installed.id,
        installed.source_url,
        installed.source,
        installed.driver,
        installed.versification,
        installed.language,
        installed.locked,
    ) != (
        available.id,
        available.source_url,
        available.source,
        available.driver,
        available.versification,
        available.language,
        available.locked,
    ):
        return "identity-changed"
    if installed.locked:
        return "encrypted-unavailable"
    if (installed.author, installed.license) != (available.author, available.license):
        return "edition-changed"
    if installed.provider_id == "bible-resources":
        from .curated_catalogue import package_record

        try:
            old = package_record(installed)
            new = package_record(available)
        except (ValueError, TypeError, KeyError):
            return "identity-unverified"
        if (old["id"], old["canonical_edition_id"], old["edition"]) != (
            new["id"],
            new["canonical_edition_id"],
            new["edition"],
        ):
            return "edition-changed"
        if installed.text_source != available.text_source:
            return "edition-changed"
        if (
            installed.version == available.version
            and old["download"]["sha256"] != new["download"]["sha256"]
        ):
            return "same-version-content-changed"
    else:
        # This contract is extended only to the explicitly assigned providers.
        # A missing original TextSource is uncertainty, not an update offer.
        if installed.provider_id not in ("crosswire", "ebible", "andbible-extra"):
            return "provider-unavailable"
        if not installed.text_source or not available.text_source:
            return "edition-unverified"
        if installed.text_source != available.text_source:
            return "edition-changed"
        if (installed.description, installed.author, installed.license) != (
            available.description,
            available.author,
            available.license,
        ):
            return "edition-changed"
    old_version = version_key(installed.version)
    new_version = version_key(available.version)
    if old_version is None or new_version is None:
        return "version-unavailable"
    if new_version < old_version:
        return "older-catalogue"
    return "available" if new_version > old_version else "current"
