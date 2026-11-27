"""General application choices; never infer a new profile from a missing key."""

from __future__ import annotations

from os import PathLike
from typing import Literal, TypedDict, cast
import json
import os
from pathlib import Path
import tempfile
from .i18n import LANGUAGE


type SettingKey = Literal[
    "version",
    "welcome_seen",
    "library_language",
    "automatic_catalogue_refresh",
    "ui_language",
    "interface_appearance",
    "restore_tabs",
]


class ApplicationValues(TypedDict):
    """Existing application preferences, independent of content-reading typography."""

    version: int
    welcome_seen: bool
    library_language: str
    automatic_catalogue_refresh: bool
    ui_language: str
    interface_appearance: str
    restore_tabs: bool


class ApplicationSettings:
    """Keep general application choices separate from reading, notes and resource data."""

    def __init__(self, root: str | PathLike[str]) -> None:
        root = Path(root)
        self.path = root / "application-preferences.json"
        self.error = ""
        # Inspect before Window creates SQLite/preferences/session files. Empty
        # translations directories are created by Library even on first launch.
        existing = (
            any(p.name != "translations" or any(p.iterdir()) for p in root.iterdir())
            if root.exists()
            else False
        )
        self.first_launch = not existing
        self.value: ApplicationValues = dict(
            version=1,
            welcome_seen=True,
            library_language="fr" if LANGUAGE.startswith("fr") else "en",
            automatic_catalogue_refresh=True,
            ui_language="system",
            interface_appearance="system",
            restore_tabs=True,
        )
        try:
            data = self.path.read_bytes()
            if len(data) > 8192:
                raise ValueError("Application preferences too large")
            value = json.loads(data)
            if (
                not isinstance(value, dict)
                or value.get("version") != 1
                or type(value.get("welcome_seen")) is not bool
                or type(value.get("automatic_catalogue_refresh")) is not bool
                or not isinstance(value.get("library_language"), str)
            ):
                raise ValueError("Invalid application preferences")
            for key, choices in {
                "ui_language": ("system", "fr", "en"),
                "interface_appearance": ("system", "light", "dark"),
            }.items():
                if value.get(key, "system") not in choices:
                    raise ValueError("Invalid general preferences")
            if type(value.get("restore_tabs", True)) is not bool:
                raise ValueError("Invalid tab preference")
            # Validation above covers known fields; retain unknown keys on disk.
            cast("dict[str, object]", self.value).update(value)
            self.first_launch = False
        except FileNotFoundError:
            try:
                self.save()
            except OSError as error:
                self.error = str(error)
        except (OSError, ValueError, TypeError) as error:
            self.error = str(error)
            self.first_launch = False

    @property
    def language(self) -> str:
        """Return the saved Library filter independently of the interface language."""
        return self.value["library_language"]

    def set(self, key: SettingKey, value: str | bool | int) -> None:
        """Save a UI-selected setting, restoring the in-memory value if saving fails."""
        # Keep the original dictionary (including unknown future keys) intact.
        # The UI supplies the scalar value associated with the selected setting.
        record = cast("dict[str, object]", self.value)
        previous = record.get(key)
        record[key] = value
        try:
            self.save()
        except Exception:
            record[key] = previous
            raise

    def save(self) -> None:
        """Flush and atomically replace preferences, refusing to overwrite an originally unreadable file."""
        if self.error:
            raise ValueError("Original application preferences preserved")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                "w", dir=self.path.parent, prefix=".application-", delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump(self.value, stream, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
