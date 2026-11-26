"""Word/phrase normalization and exact source-offset highlighting."""

from __future__ import annotations

import re
import unicodedata
from .languages import canonical_language

LATIN_LANGUAGES = {"en", "fr", "de", "es", "pt", "it", "la", "nl", "ro", "ca"}
UNSEGMENTED_LANGUAGES = {"zh", "ja", "th", "lo", "km", "my"}


def normalized(value, language="und", offsets: bool = False):
    """Normalize language-aware search characters, optionally retaining original combining-cluster offsets.

    Fold accents only for supported Latin languages; keep combining marks
    for other scripts rather than treating them as ignorable content.
    """
    latin = canonical_language(language).split("-")[0] in LATIN_LANGUAGES
    characters = []
    positions = []
    clusters = []
    for index, char in enumerate(value):
        if unicodedata.combining(char) and clusters:
            clusters[-1][1] += char
        else:
            clusters.append([index, char])
    for index, cluster in clusters:
        for part in unicodedata.normalize("NFD", cluster.casefold()):
            if latin and unicodedata.combining(part):
                continue
            if part.isalnum() or unicodedata.combining(part):
                characters.append(part)
                positions.append(index)
            elif characters and characters[-1] != " ":
                characters.append(" ")
                positions.append(index)
    result = "".join(characters)
    return (result, positions) if offsets else result


def terms(query, language="und"):
    # Quoted phrases are contiguous; unquoted words are ANDed in any order.
    """Parse and deduplicate nonempty normalized words/quoted phrases, rejecting unmatched quotes."""
    if query.count('"') % 2:
        raise ValueError("Close the quoted phrase before searching.")
    parts = [phrase or word for phrase, word in re.findall(r'"([^"]*)"|([^\s"]+)', query)]
    result = [normalized(p, language).strip() for p in parts]
    result = [p for p in result if p]
    if not result:
        raise ValueError("Enter a word or phrase.")
    return tuple(dict.fromkeys(result))


def match_ranges(text, query, language="und"):
    """Map normalized word/phrase matches back to original text including trailing combining marks."""
    value, offsets = normalized(text, language, True)
    ranges = []
    for term in terms(query, language):
        pattern = re.escape(term)
        if canonical_language(language).split("-")[0] not in UNSEGMENTED_LANGUAGES:
            pattern = r"(?<!\w)" + pattern + r"(?!\w)"
        for match in re.finditer(pattern, value):
            if match.end():
                end = offsets[match.end() - 1] + 1
                while end < len(text) and unicodedata.combining(text[end]):
                    end += 1
                ranges.append((offsets[match.start()], end))
    return tuple(sorted(set(ranges)))
