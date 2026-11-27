"""CLDR names (Babel) with maintained ISO 639-3 coverage, never merge source codes."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import NotRequired, TypedDict
from functools import lru_cache
import gettext
import json
from pathlib import Path
import re
from babel import Locale, UnknownLocaleError
from babel.core import get_global
from babel.localedata import locale_identifiers
from .i18n import LANGUAGE, tr as tr, collation_key


def language_order(
    codes: Iterable[str],
    available: Iterable[str],
    label: Callable[[str], str] | None = None,
) -> tuple[list[str], list[str]]:
    """A small shortcut policy, never an inventory or source-code merger."""
    names = label or language_name
    codes = set(codes) - {""}
    available = set(available) & codes
    interface = "fr" if LANGUAGE.startswith("fr") else "en"
    priority = [
        code
        for code in dict.fromkeys((interface, "fr", "en", "es", "pt", "de", "it"))
        if code in available
    ]
    remainder = sorted(codes - set(priority), key=lambda code: (collation_key(names(code)), code))
    return ["", *priority, *remainder], priority


@lru_cache(maxsize=4096)
def canonical_language(code: str) -> str:
    """Validated aliases only; retain script/region qualifiers exactly."""
    parts = code.replace("_", "-").split("-")
    base = parts[0].lower()
    base = get_global("language_aliases").get(base, base).replace("_", "-")
    return "-".join([base, *[p.title() if len(p) == 4 else p.upper() for p in parts[1:]]])


@lru_cache(maxsize=1)
def available_languages() -> frozenset[str]:
    """Return installed ISO identities plus the supported interface languages."""
    return frozenset(canonical_language(code) for code in iso_languages()) | {"en", "fr"}


class _IsoLanguage(TypedDict):
    """Fields consumed from the installed iso-codes 639-3 metadata."""

    name: str
    alpha_3: str
    alpha_2: NotRequired[str]


@lru_cache(maxsize=1)
def iso_languages() -> dict[str, _IsoLanguage]:
    """Cache installed ISO 639-3 metadata from the application or system share directory."""
    for root in [Path("/app/share"), Path("/usr/share")]:
        path = root / "iso-codes/json/iso_639-3.json"
        if path.is_file():
            values = json.loads(path.read_text())["639-3"]
            return {
                code: entry
                for entry in values
                for code in [entry["alpha_3"], entry.get("alpha_2")]
                if code
            }
    return {}


@lru_cache(maxsize=8)
def iso_translation(interface: str) -> gettext.NullTranslations:
    """Load installed language-name translations, falling back to source labels."""
    for root in ["/app/share/locale", "/usr/share/locale"]:
        try:
            return gettext.translation("iso_639-3", localedir=root, languages=[interface])
        except OSError:
            pass
    return gettext.NullTranslations()


@lru_cache(maxsize=4096)
def language_info(code: object, interface: str | None = None) -> tuple[str, str]:
    """Return localized and available native names while preserving unknown source codes explicitly.

    CLDR aliases affect presentation only; callers must retain the original
    provider code for resource identity and catalogue requests.
    """
    interface = (interface or LANGUAGE).split("_")[0].split("-")[0].split(":")[0]
    interface = "fr" if interface == "fr" else "en"
    if not isinstance(code, str) or not re.fullmatch(
        r"[A-Za-z]{2,3}(?:[-_][A-Za-z0-9]{2,8})*", code
    ):
        return (
            ("Langue non identifiée" if interface == "fr" else "Unidentified language")
            + f" ({code})",
            "",
        )
    parts = code.replace("_", "-").split("-")
    base = parts[0].lower()
    alias = get_global("language_aliases").get(base, base).split("_")[0]
    locale = Locale(interface)
    name = locale.languages.get(alias)
    if not name:
        entry = iso_languages().get(base)
        if entry:
            name = iso_translation(interface).gettext(entry["name"])
    if not name or base == "und":
        return (
            ("Langue non identifiée" if interface == "fr" else "Unidentified language")
            + f" ({code})",
            "",
        )
    qualifiers = []
    for part in parts[1:]:
        if len(part) == 4 and part.isalpha():
            qualifiers.append(locale.scripts.get(part.title(), part))
        elif len(part) in (2, 3):
            qualifiers.append(locale.territories.get(part.upper(), part))
        else:
            qualifiers.append(part)
    if qualifiers:
        name += " — " + ", ".join(qualifiers)
    native = ""
    # Babel's missing-locale fallback linearly normalizes its entire locale
    # inventory several times. Most ISO 639-3 catalogue languages have no CLDR
    # native locale at all: do not perform that expensive failed lookup.
    if alias in native_language_codes():
        try:
            own = Locale.parse(code.replace("-", "_"))
            native = own.get_display_name(own) or ""
        except (UnknownLocaleError, ValueError):
            pass
    return name, native


def language_name(code: str) -> str:
    """Return the interface-language label without changing the provider identity."""
    return language_info(code)[0]


@lru_cache(maxsize=1)
def native_language_codes() -> frozenset[str]:
    """Cache CLDR locale availability to avoid repeated failed native-name lookups."""
    return frozenset(identifier.split("_")[0] for identifier in locale_identifiers())


@lru_cache(maxsize=1)
def language_aliases() -> dict[str, list[str]]:
    """Index CLDR spelling aliases for search, never for merging source resources."""
    result: dict[str, list[str]] = {}
    for alias in get_global("language_aliases"):
        result.setdefault(canonical_language(alias), []).append(alias)
    return result


def search_terms(code: str) -> str:
    """Combine provider code, aliases and available localized names for filtering."""
    names = language_info(code)
    aliases = " ".join(language_aliases().get(canonical_language(code), ()))
    return " ".join(
        (code, aliases, *names, language_info(code, "fr")[0], language_info(code, "en")[0])
    )
