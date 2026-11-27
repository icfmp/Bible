"""Book-name UI metadata and French input aliases, never a list of module contents."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from functools import lru_cache
from threading import current_thread, main_thread
from typing import TYPE_CHECKING
import re

if TYPE_CHECKING:
    from .sword_provider import Book
import unicodedata

FRENCH = dict(
    zip(
        "Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth Job Ps Prov Eccl Song Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal Matt Mark Luke John Acts Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev".split(),
        [
            "Genèse",
            "Exode",
            "Lévitique",
            "Nombres",
            "Deutéronome",
            "Josué",
            "Juges",
            "Ruth",
            "1 Samuel",
            "2 Samuel",
            "1 Rois",
            "2 Rois",
            "1 Chroniques",
            "2 Chroniques",
            "Esdras",
            "Néhémie",
            "Esther",
            "Job",
            "Psaumes",
            "Proverbes",
            "Ecclésiaste",
            "Cantique des cantiques",
            "Ésaïe",
            "Jérémie",
            "Lamentations",
            "Ézéchiel",
            "Daniel",
            "Osée",
            "Joël",
            "Amos",
            "Abdias",
            "Jonas",
            "Michée",
            "Nahum",
            "Habacuc",
            "Sophonie",
            "Aggée",
            "Zacharie",
            "Malachie",
            "Matthieu",
            "Marc",
            "Luc",
            "Jean",
            "Actes",
            "Romains",
            "1 Corinthiens",
            "2 Corinthiens",
            "Galates",
            "Éphésiens",
            "Philippiens",
            "Colossiens",
            "1 Thessaloniciens",
            "2 Thessaloniciens",
            "1 Timothée",
            "2 Timothée",
            "Tite",
            "Philémon",
            "Hébreux",
            "Jacques",
            "1 Pierre",
            "2 Pierre",
            "1 Jean",
            "2 Jean",
            "3 Jean",
            "Jude",
            "Apocalypse",
        ],
    )
)
FRENCH.update(
    {
        "Tob": "Tobie",
        "Jdt": "Judith",
        "Wis": "Sagesse",
        "Sir": "Siracide",
        "Bar": "Baruch",
        "1Macc": "1 Maccabées",
        "2Macc": "2 Maccabées",
        "3Macc": "3 Maccabées",
        "4Macc": "4 Maccabées",
        "1Esd": "1 Esdras",
        "2Esd": "2 Esdras",
        "PrMan": "Prière de Manassé",
        "Ps151": "Psaume 151",
        "AddEsth": "Additions à Esther",
        "AddDan": "Additions à Daniel",
        "EpJer": "Lettre de Jérémie",
        "PrAzar": "Prière d’Azarias",
        "Sus": "Suzanne",
        "Bel": "Bel et le Dragon",
    }
)
FRENCH.update(
    {
        "EsthGr": "Esther (grec)",
        "DanGr": "Daniel (grec)",
        "Odes": "Odes",
        "PssSol": "Psaumes de Salomon",
        "EpLao": "Épître aux Laodicéens",
    }
)


def normalized(value: str) -> str:
    """Fold accents and punctuation for matching without changing displayed text."""
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(char) and char.isalnum()
    )


# Input aliases are static metadata; do not normalize the entire table for each verse.
_INPUT_ALIASES = {normalized(label): code for code, label in FRENCH.items()}
_INPUT_ALIASES.update(
    {
        normalized(label): code
        for label, code in (
            ("Psaume", "Ps"),
            ("Psaumes", "Ps"),
            ("Ps", "Ps"),
            ("Psalm", "Ps"),
            ("Psalms", "Ps"),
            ("Esaïe", "Isa"),
            ("Isaïe", "Isa"),
            ("Cantique", "Song"),
            ("Cantiques", "Song"),
        )
    }
)
_INPUT_ALIASES.update({normalized(code): code for code in FRENCH})


def canonical_input(reference: str) -> str:
    """Resolve full French names; let SWORD resolve its own names and abbreviations."""
    book = (
        _INPUT_ALIASES.get(normalized(reference)) if not any(c in reference for c in ".:") else None
    )
    if book:
        return book + ".1"
    match = re.fullmatch(
        r"(.+?)[ .]*([1-9][0-9]*(?:_[1-9][0-9]*)?(?:[.:][1-9][0-9]*)?)", reference.strip()
    )
    if match:
        name, numbers = match.groups()
        code = _INPUT_ALIASES.get(normalized(name))
        if code:
            return f"{code}.{numbers}"
    return reference.strip()


@lru_cache(maxsize=128)
def _native_french_name(code: str) -> str | None:
    """Read a native label with a dedicated, short-lived main-thread key."""
    from .reference_resolution import checked_verse_key

    try:
        key = checked_verse_key(code + ".1.1", "KJVA", locale="fr")
        if key.getOSISBookName() == code:
            return key.getBookName()
    except (ImportError, ValueError):
        pass
    return None


def display_name(code: str, fallback: str, language: str = "en") -> str:
    """Use matching native French names and preserve Bible's established wording."""
    if not language.startswith("fr"):
        return fallback
    preferred = FRENCH.get(code, fallback)
    # SWORD 1.9 also has a shared locale cache. Localized calls stay on the
    # main thread, with the GIL held by the packaged SWIG wrapper. Standalone
    # tools and worker-rendered documents retain the same offline label.
    if current_thread() is main_thread() and code in FRENCH:
        native = _native_french_name(code)
        if native == preferred:
            return native
    return preferred


def localized_input(reference: str, system: str, language: str) -> str:
    """Resolve a bounded French book alias while keeping the original numeric suffix."""
    fallback = canonical_input(reference)
    if not language.startswith("fr") or current_thread() is not main_thread():
        return fallback
    match = re.fullmatch(
        r"((?:[1-5]\s*)?[^\d.:]+?)[ .]+([1-9][0-9]*(?:_[1-9][0-9]*)?(?:[.:][1-9][0-9]*)?)",
        reference.strip(),
    )
    if not match or len(reference) > 256:
        return fallback
    from .reference_resolution import checked_verse_key

    name, numbers = match.groups()
    try:
        # Parse the book only. The selected reader retains authority over
        # chapter bounds, source subchapters and actual installed entries.
        key = checked_verse_key(name + " 1:1", system, locale="fr")
    except (ImportError, ValueError):
        return fallback
    code = key.getOSISBookName()
    if fallback != reference.strip():
        if fallback.split(".", 1)[0] != code:
            return fallback
    else:
        # Preserve accepted spellings even when they mean something different
        # in the French alias table. Native partial matches are not new aliases.
        try:
            previous = checked_verse_key(name + " 1:1", system)
        except ValueError:
            if normalized(name) not in {
                normalized(key.getBookName()),
                normalized(key.getBookAbbrev()),
            }:
                return fallback
        else:
            if previous.getOSISBookName() != code:
                return fallback
    return f"{code}.{numbers}"


def book_suggestions(
    text: str,
    books: Sequence[Book],
    language: str = "en",
    native_alias: Callable[[str], str | None] | None = None,
) -> tuple[tuple[str, str], ...]:
    """Optional book completion only; chapter/verse validation stays in Reader."""
    if len(text) > 256:
        return ()
    names = {book.code: display_name(book.code, book.name, language) for book in books}
    whole = next((name for name in names.values() if normalized(text) == normalized(name)), None)
    if whole:
        prefix, suffix = text.strip(), ""
    else:
        match = re.fullmatch(
            r"\s*((?:[1-4]\s*)?[^\d:]+?)(\s*\.?\s*[1-9]\d*(?:\s*[.:]\s*[1-9]\d*)?(?:\s*[-–]\s*[1-9]\d*)?)?\s*",
            text,
        )
        if not match:
            return ()
        prefix, suffix = match.group(1).strip(), match.group(2) or ""
    if not any(c.isalpha() for c in prefix):
        return ()
    query = normalized(prefix)
    native = None
    if native_alias and len(query) >= 2:
        try:
            native = native_alias(prefix)
        except (ValueError, RuntimeError):
            pass
    choices = []
    for index, book in enumerate(books):
        name = names[book.code]
        if normalized(name) == query and (suffix or text.endswith(" ")):
            continue
        aliases = {normalized(name), normalized(book.name), normalized(book.code)}
        aliases.update(alias for alias, code in _INPUT_ALIASES.items() if code == book.code)
        exact = query in aliases or native == book.code
        if exact or any(alias.startswith(query) for alias in aliases):
            ending = suffix.strip().lstrip(".").lstrip()
            choices.append(
                (
                    (not exact, not normalized(name).startswith(query), index),
                    name,
                    name + " " + ending,
                )
            )
    return tuple((name, value) for _, name, value in sorted(choices)[:5])
