"""Display saved canonical passage references independently of the GTK surfaces."""

from .book_names import display_name
from .i18n import LANGUAGE
from .notes import parts


def passage_label(start: str, end: str | None = None, versification: str | None = None) -> str:
    """Format a canonical saved range for display without requiring the original module to be installed."""
    code, chapter, verse = parts(start)
    name = code
    try:
        import Sword

        key = Sword.VerseKey()
        key.setVersificationSystem(versification or "KJV")
        key.setAutoNormalize(False)
        key.setText(start)
        if key.popError() == "\x00" and key.getOSISBookName() == code:
            name = key.getBookName()
    except Exception:
        pass
    result = f"{display_name(code, name, LANGUAGE)} {chapter}:{verse}"
    if end and end != start:
        final = parts(end)
        result += "–" + (
            str(final[2])
            if final[:2] == (code, chapter)
            else f"{final[1]}:{final[2]}"
            if final[0] == code
            else passage_label(end, versification=versification)
        )
    return result
