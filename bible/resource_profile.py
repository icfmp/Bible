"""Display approved catalogue prose without changing the installed module."""

import re
from .resource_details import linkable_url


def approved_profile(resource, catalogue, locale):
    if resource.provider_id != "bible-resources":
        return None
    from .curated_catalogue import package_record

    try:
        installed = package_record(resource)
    except (ValueError, TypeError, KeyError):
        return None
    # Match edition provenance, never title similarity or another provider's ID.
    candidates = [
        r for r in catalogue if r.id == resource.id and r.provider_id == resource.provider_id
    ]
    candidates.append(resource)
    for candidate in candidates:
        try:
            entry = package_record(candidate)
        except (ValueError, TypeError, KeyError):
            continue
        identity = (
            "id",
            "canonical_edition_id",
            "edition",
            "sword_id",
            "category",
            "language",
            "versification",
        )
        if any(entry.get(key) != installed.get(key) for key in identity):
            continue
        profiles = entry.get("profiles", {})
        if not isinstance(profiles, dict):
            continue
        preferred = locale.split("_", 1)[0].split("-", 1)[0]
        for language in dict.fromkeys([preferred, "en", *sorted(profiles)]):
            profile = profiles.get(language)
            if (
                not isinstance(profile, dict)
                or profile.get("format") != "markdown"
                or not all(
                    isinstance(profile.get(k), str) and profile[k].strip()
                    for k in ("approved_at", "approved_by", "revision")
                )
                or not linkable_url(profile.get("approval_url", ""))
            ):
                continue
            from datetime import date

            try:
                date.fromisoformat(profile["approved_at"])
            except ValueError:
                continue
            text = profile.get("long_markdown") or profile.get("short_markdown")
            if isinstance(text, str) and text.strip():
                return language, text, profile
    return None


def profile_text(source):
    """Existing inert inline Markdown with native block heading styles."""
    from .markdown import render

    text = []
    spans = []
    offset = 0
    for line in source.splitlines(keepends=True):
        heading = re.match(r"^ {0,3}(#{1,6})\s+(.+?)(?:\s+#+)?(\n?)$", line)
        value, styles = render(heading[2] + heading[3] if heading else line)
        if heading:
            styles.append(("heading", 0, len(value.rstrip())))
        text.append(value)
        spans.extend((kind, a + offset, b + offset) for kind, a, b in styles)
        offset += len(value)
    return "".join(text), spans


def present_profile(label, source):
    from gi.repository import Pango

    text, spans = profile_text(source)
    label.set_text(text)
    attrs = Pango.AttrList()
    offsets = [0]
    for char in text:
        offsets.append(offsets[-1] + len(char.encode()))
    for kind, a, b in spans:
        styles = (
            [Pango.attr_weight_new(Pango.Weight.BOLD), Pango.attr_scale_new(1.12)]
            if kind == "heading"
            else [Pango.attr_weight_new(Pango.Weight.BOLD)]
            if kind == "bold"
            else [Pango.attr_style_new(Pango.Style.ITALIC)]
            if kind == "italic"
            else [Pango.attr_underline_new(Pango.Underline.SINGLE)]
        )
        for style in styles:
            style.start_index = offsets[a]
            style.end_index = offsets[b]
            attrs.insert(style)
    label.set_attributes(attrs)
