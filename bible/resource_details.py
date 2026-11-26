"""Plain, noninteractive presentation of untrusted provider metadata."""

from html.parser import HTMLParser
from urllib.parse import urlsplit
import re
from .i18n import tr


class PlainMetadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        if tag in ("br", "p", "div"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def plain(value):
    parser = PlainMetadata()
    parser.feed(value)
    # About fields often contain SWORD's legacy RTF paragraph markers.
    value = "".join(parser.parts)
    # Some catalogues double the backslash and omit the space before an
    # immediately following capital (e.g. \\par\\parSource:). Keep all words.
    value = re.sub(r"\\+par(?:d)?(?=$|[^a-z])\s*", "\n", value)
    return re.sub(r"\\+(?:qc|b0?|i0?)\b\s*", "", value).strip()


def linkable_url(value):
    """Expose only explicit, valid HTTP(S) provider URLs as clickable links."""
    if not isinstance(value, str) or len(value) > 2048:
        return ""
    candidate = value.strip()
    if not candidate or any(ord(ch) < 33 or ord(ch) == 127 for ch in candidate):
        return ""
    try:
        parsed = urlsplit(candidate)
    except ValueError:
        return ""
    return (
        candidate
        if parsed.scheme in ("http", "https")
        and parsed.hostname
        and not parsed.username
        and not parsed.password
        else ""
    )


def first_link(value):
    """Find an explicitly supplied license link; never synthesize one."""
    if not isinstance(value, str):
        return ""
    for match in re.finditer(r'https?://[^\s<>"]+', value):
        result = linkable_url(match.group().rstrip(").,;"))
        if result:
            return result
    return ""


def visible_conditions(resource):
    """Move only the parser's explicit TextSource line to its own link row.

    Keep the complete original conditions in the model/technical disclosure.
    No prose, copyright, restrictions or mixed About field is classified here.
    """
    text_source = getattr(resource, "text_source", "")
    if resource.provider_id != "youversion" and linkable_url(text_source):
        return plain(
            "\n".join(
                line
                for line in resource.conditions.splitlines()
                if line != "textsource: " + text_source
            )
        )
    return plain(resource.conditions)


def conditions_presentation(resource, root):
    """Human labels only for fields verified against the actual SWORD conf.

    Mixed, conflicting or unknown source notices remain literal text. Neither
    source values nor the Resource model are rewritten for presentation.
    """
    from pathlib import Path
    from .library import config, resource_from_section

    labels = {
        "copyright": "Copyright",
        "copyrightholder": "Rights holder",
        "copyrightnotes": "Conditions",
        "copyrightcontactemail": "Contact",
        "copyrightcontactname": "Contact name",
        "copyrightcontactaddress": "Contact address",
        "copyrightdate": "Copyright date",
        "shortcopyright": "Copyright notice",
        "distributionnotes": "Distribution conditions",
    }
    text_source = getattr(resource, "text_source", "")
    original = "\n".join(
        line
        for line in resource.conditions.splitlines()
        if not (linkable_url(text_source) and line == "textsource: " + text_source)
    )
    if not original:
        return "", ()
    try:
        files = list((Path(root) / resource.id / "mods.d").glob("*.conf"))
        if len(files) != 1 or files[0].stat().st_size > 2 * 1024 * 1024:
            raise ValueError("Unverified source metadata")
        parser = config(files[0].read_bytes())
        if len(parser.sections()) != 1:
            raise ValueError("Ambiguous source metadata")
        section = parser[parser.sections()[0]]
        if resource_from_section(resource.name, section).conditions != resource.conditions:
            raise ValueError("Mixed catalogue and source notice")
    except (OSError, ValueError):
        return tr("Original source notice") + "\n" + original, ()
    blocks = []
    unknown = []
    links = []

    # Deduplicate only exact, verified short public-domain declarations.
    # Distinct authored conditions (including complete sentences) stay intact.
    def public_domain(value):
        return bool(re.fullmatch(r"public[ _-]+domain", value.strip(), re.I))

    public_domain_seen = public_domain(resource.license)
    for key, value in section.items():
        if not value:
            continue
        if key in labels:
            if public_domain(value):
                if public_domain_seen:
                    continue
                public_domain_seen = True
            blocks.append(tr(labels[key]) + "\n" + value)
            for match in re.finditer(r'https?://[^\s<>"]+', value):
                url = linkable_url(match.group().rstrip(").,;"))
                if url and (url, url) not in links:
                    links.append((url, url))
            if key == "copyrightcontactemail" and re.fullmatch(
                r"[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+", value
            ):
                from urllib.parse import quote

                links.append((value, "mailto:" + quote(value, safe="@.+-_")))
        elif (
            key.startswith("copyright")
            or key == "textsource"
            and not (linkable_url(value) and value == text_source)
        ):
            unknown.append(key + ": " + value)
    if unknown:
        blocks.append(tr("Original source notice") + "\n" + "\n".join(unknown))
    return "\n\n".join(blocks), tuple(links)


from .languages import language_name


def details(resource):
    import json

    try:
        pending = resource.provider_id == "youversion" and json.loads(resource.acquisition).get(
            "_catalogue_summary"
        )
    except (ValueError, AttributeError):
        pending = False
    availability = (
        tr("Access key required. Encrypted resources are not supported.")
        if resource.locked
        else tr("Unsupported format.")
        if not resource.installable
        else tr("Distributed by the source. Download is checked before installation.")
    )
    if resource.provider_id == "youversion" and not resource.installable:
        availability = tr("No offline package supplied by the source.")
    numbering = resource.versification
    if resource.provider_id == "youversion" and numbering.startswith("YouVersion"):
        numbering = tr("Numbering supplied by this edition")
        availability += "\n" + tr(
            "Automatic verse alignment with other editions is unavailable. Independent parallel reading remains available."
        )
    provenance = ""
    if resource.provider_id == "bible-resources":
        from .curated_catalogue import package_record

        try:
            entry = package_record(resource)
        except (ValueError, TypeError, KeyError):
            entry = None
        provenance = (
            tr("Source edition") + ": " + entry["canonical_edition_id"] + " / " + entry["edition"]
            if entry
            else tr("Source edition metadata could not be verified.")
        )
        # Report publisher-supplied approval metadata, never turn a draft's
        # prose into application-authored claims or silently translate it.
        profiles = entry.get("profiles", {}) if entry else {}
        if isinstance(profiles, dict):
            for language, profile in profiles.items():
                if not isinstance(profile, dict):
                    continue
                if all(
                    isinstance(profile.get(key), str) and profile[key]
                    for key in ("approved_at", "approved_by", "approval_url")
                ):
                    provenance += (
                        "\n"
                        + tr("Profile approval reported by the source")
                        + " ("
                        + str(language)
                        + "): "
                        + profile["approved_at"]
                        + "\n"
                        + profile["approval_url"]
                    )
    return "\n\n".join(
        [
            f"{plain(resource.description)} ({resource.name})",
            f"{tr('Resource type')}: "
            + tr(
                {
                    "commentary": "Commentaries",
                    "study": "Study resources",
                    "dictionary": "Dictionary or lexicon",
                    "general": "General book",
                }.get(resource.kind, "Bibles")
            ),
            f"{tr('Author')}: {plain(resource.author)}" if resource.author else "",
            f"{tr('Language')}: {language_name(resource.language)}",
            f"{tr('Source')}: {resource.source}\n{resource.source_url}",
            f"{tr('Text source')}: {resource.text_source}"
            if getattr(resource, "text_source", "")
            else "",
            f"{tr('Version')}: {resource.version}" if getattr(resource, "version", "") else "",
            tr("Version notes (source)") + ":\n" + plain(resource.release_notes)
            if getattr(resource, "release_notes", "")
            else "",
            provenance,
            f"{tr('License')}: {plain(resource.license)}",
            f"{tr('Verse numbering')}: {numbering}"
            if resource.kind in ("bible", "commentary", "study")
            else "",
            availability,
            f"{tr('Conditions and attribution')}:\n"
            + (
                tr("Loading edition details…")
                if pending
                else plain(resource.conditions)
                or tr("No additional conditions supplied by the source.")
            ),
            plain(resource.about),
            tr(
                "Check the source conditions before downloading. Availability does not grant redistribution rights."
            ),
        ]
    )
