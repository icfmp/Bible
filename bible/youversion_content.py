"""Strict OSIS projections shared by installation checks and editorial views.

Native entries can contain markup spanning verse boundaries. Parse complete
chapters, with processing instructions retaining physical entry identities.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import Sword
from dataclasses import dataclass
import re
import unicodedata
from xml.etree import ElementTree as E


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()


def tag(node: E.Element) -> str:
    return node.tag.rsplit("}", 1)[-1] if isinstance(node.tag, str) else ""


def parse(raw: str) -> E.Element:
    """Parse the supported OSIS subset without accepting DTD or entity declarations."""
    # No entities, external references or DTDs in the accepted OSIS subset.
    if "<!DOCTYPE" in raw or "<!ENTITY" in raw:
        raise ValueError("Unsupported OSIS declaration")
    parser = E.XMLParser(target=E.TreeBuilder(insert_pis=True))
    return E.fromstring(raw, parser=parser)


@dataclass(frozen=True)
class EditorialNote:
    """A source-supplied note with its actual reference, locator, type and text."""

    reference: str
    locator: str
    kind: str
    text: str


def project(
    root: E.Element,
    *,
    milestones: bool = False,
    preverse: str | None = None,
    normalize: bool = True,
    editorial: bool = True,
) -> tuple[dict[str, str], tuple[EditorialNote, ...], tuple[str, ...]]:
    """Project actual OSIS verse bodies, notes and titles with explicit milestone/storage boundaries.

    Normalization and editorial inclusion are caller-controlled; no content
    is synthesized for missing source references.
    """
    bodies: defaultdict[str, list[str]] = defaultdict(list)
    notes: list[EditorialNote] = []
    titles: list[str] = []
    active = preverse

    def visit(node: E.Element) -> None:
        nonlocal active
        if node.tag is E.ProcessingInstruction:
            target, _, reference = (node.text or "").partition(" ")
            if target == "source-unit":
                active = reference
                bodies.setdefault(active, [])
            return
        name = tag(node)
        if name == "header":
            return
        if name == "verse" and milestones:
            if node.get("sID"):
                active = node.get("osisID", "").split()[0]
                bodies.setdefault(active, [])
            elif node.get("eID"):
                active = None
            return
        if name == "note":
            if not editorial:
                return
            notes.append(
                EditorialNote(
                    node.get("osisRef") or active or "",
                    node.get("n", ""),
                    node.get("type", ""),
                    normalized("".join(node.itertext())),
                )
            )
            return
        if name == "title":
            if not editorial:
                return
            # Preserve notes nested inside headings, without mixing them into
            # the heading or the biblical body.
            parts = []

            def heading(el: E.Element) -> None:
                if tag(el) == "note":
                    visit(el)
                    return
                if el.text:
                    parts.append(el.text)
                for child in el:
                    heading(child)
                    if child.tail:
                        parts.append(child.tail)

            heading(node)
            titles.append(normalized("".join(parts)))
            return
        if active and node.text:
            bodies[active].append(node.text)
        for child in node:
            visit(child)
            if active and child.tail:
                bodies[active].append(child.tail)

    visit(root)
    projected = {
        ref: (normalized("".join(parts)) if normalize else "".join(parts))
        for ref, parts in bodies.items()
    }
    projected = {ref: value for ref, value in projected.items() if value or not ref.endswith(".0")}
    return projected, tuple(notes), tuple(titles)


def semantic_roles(root: E.Element) -> list[tuple[str, tuple[tuple[str, str], ...]]]:
    """Preserve explicit inline styling, quotation/reference and list levels."""
    accepted = {
        "hi",
        "divineName",
        "transChange",
        "catchWord",
        "name",
        "q",
        "reference",
        "foreign",
        "l",
        "item",
        "table",
        "row",
        "cell",
    }
    result = []
    for node in root.iter():
        name = tag(node)
        # osis2mod turns enclosing poetry/quote elements into start/end
        # milestones. An end marker does not introduce another semantic role.
        if node.get("eID"):
            continue
        if (
            name in accepted
            or name == "seg"
            and node.get("type", "").startswith(("x-source-", "x-transliteration"))
        ):
            attrs = tuple(
                sorted(
                    (key, value)
                    for key, value in node.attrib.items()
                    if key in ("type", "who", "marker", "level", "osisRef", "role")
                )
            )
            result.append((name, attrs))
    return result


def native_chapter(
    module: Sword.SWModule, key: Sword.VerseKey, chapter: str, references: Iterable[str]
) -> E.Element:
    """Parse native entries with physical identities so cross-entry markup stays intact.

    Mutates the supplied key and module; serialize access on their owning path.
    Supply native storage references, not public source section aliases.
    """

    def entry(ref: str) -> str:
        key.setText(ref)
        module.setKey(key)
        value = module.getRawEntry()
        return value if isinstance(value, str) else value.c_str()

    entries = [(chapter + ".0", entry(chapter + ".0"))]
    entries.extend((ref, entry(ref)) for ref in references)
    return parse(
        "<root>" + "".join("<?source-unit " + ref + "?>" + raw for ref, raw in entries) + "</root>"
    )
