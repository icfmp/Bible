"""Exact capability-based bridge through KJVA; no missing-table identity guess.

Expanded JSword data retains verse parts and absent sections. The native SWORD
canon must match the pinned data before its implicit identities can be used.
Existing native-to-native resolution remains in reference_resolution.
"""
from functools import lru_cache
import json
from pathlib import Path


@lru_cache(maxsize=None)
def table(system):
    import Sword
    # Registry comes from packaged tables, never resource/provider names.
    path = next((p for p in Path(__file__).with_name('versification_data').glob('*.json')
                 if p.stem == system), None)
    if path is None:
        return None
    data = json.loads(path.read_text())
    key = Sword.VerseKey()
    key.setVersificationSystem(system)
    if key.getVersificationSystem() != system:
        return None
    canon = {}
    for testament in (1, 2):
        key.setTestament(testament)
        for book in range(1, key.getBookMax() + 1):
            key.setBook(book)
            name = key.getOSISBookName()
            chapters = []
            for chapter in range(1, key.getChapterMax() + 1):
                key.setChapter(chapter)
                chapters.append(key.getVerseMax())
            canon[name] = chapters
    if canon != data['canon']:
        return None
    return data


def valid(reference, data):
    try:
        book, chapter, verse = reference.split('.')
        chapter, verse = int(chapter), int(verse)
        sizes = data['canon'][book]
        return 1 <= chapter <= len(sizes) and 0 <= verse <= sizes[chapter - 1]
    except (ValueError, KeyError):
        return False


def to_base(reference, system):
    """Return qualified KJVA references, or None if capability is unavailable."""
    data = table(system)
    base = table('KJVA')
    if data is None or base is None:
        return None
    if reference in data.get('forward', {}):
        result = data['forward'][reference]
        # The pinned upstream cannot unmap a qualified multi-verse range
        # (it casts it to Verse). Do not truncate it at the first '!'.
        if any('!' in ref and '-' in ref for ref in result):
            return []
        return result
    return [reference] if valid(reference, base) else []


def from_base(qualified, system):
    data = table(system)
    if data is None:
        return None
    reverse = data.get('reverse', {})
    if qualified in reverse:
        return reverse[qualified]
    whole = qualified.split('!', 1)[0]
    if whole in reverse:
        return reverse[whole]
    if qualified.startswith('?') or whole in data.get('absent', ()):
        return []
    return [whole] if valid(whole, data) else []
