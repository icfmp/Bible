"""Native resource metadata, source attribution and detail actions."""

import unittest
from bible.resource_details import plain


class MetadataTests(unittest.TestCase):
    def test_non_sword_study_notice_remains_complete_without_optional_text_source(self):
        import tempfile
        from bible.study_resources import StudyResource
        from bible.resource_details import conditions_presentation
        from bible.i18n import tr

        resource = StudyResource()
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                conditions_presentation(resource, directory),
                (tr("Original source notice") + "\n" + resource.conditions, ()),
            )

    def test_legal_keys_are_labelled_only_after_exact_source_verification(self):
        import tempfile
        from pathlib import Path
        from dataclasses import replace
        from bible.library import config, resource_from_section
        from bible.resource_details import conditions_presentation
        from bible.i18n import tr

        data = (
            b"[Martin]\nDescription=Source\nCopyright=Philippe Lacombe\nCopyrightHolder=Philippe Lacombe\n"
            b"CopyrightNotes=Copying and sharing is allowed, as long as the original translation is unchanged, and https://example.org/source is credited.\n"
            b"CopyrightContactEmail=martin@example.org\nCopyrightUnknown=KEEP THIS UNKNOWN FIELD\nTextSource=https://example.org/source\n"
        )
        resource = resource_from_section("Martin", config(data)["Martin"])
        before = resource.conditions
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            conf = root / "Martin/mods.d"
            conf.mkdir(parents=True)
            (conf / "martin.conf").write_bytes(data)
            text, links = conditions_presentation(resource, root)
            self.assertIn(tr("Rights holder") + "\nPhilippe Lacombe", text)
            self.assertIn(
                "Copying and sharing is allowed, as long as the original translation is unchanged",
                text,
            )
            self.assertNotIn("copyrightholder:", text)
            self.assertNotIn("copyrightnotes:", text)
            self.assertIn(
                tr("Original source notice") + "\ncopyrightunknown: KEEP THIS UNKNOWN FIELD", text
            )
            self.assertIn(("martin@example.org", "mailto:martin@example.org"), links)
            self.assertIn(("https://example.org/source", "https://example.org/source"), links)
            altered = replace(
                resource, conditions="copyright: Prose which conflicts with the actual module"
            )
            self.assertEqual(
                conditions_presentation(altered, root),
                (tr("Original source notice") + "\n" + altered.conditions, ()),
            )
            self.assertEqual(resource.conditions, before)

    def test_only_structured_text_source_line_moves_to_link_without_mutating_terms(self):
        from bible.library import resource_from_section, config
        from bible.resource_details import visible_conditions, details

        resource = resource_from_section(
            "Test",
            config(
                b"[Test]\nDescription=Title\nTextSource=https://example.org/source\n"
                b"DistributionNotes=Keep this restriction.\nShortCopyright=Copyright retained.\n"
            )["Test"],
        )
        before = resource.conditions
        visible = visible_conditions(resource)
        self.assertIn("Keep this restriction.", visible)
        self.assertIn("Copyright retained.", visible)
        self.assertNotIn("textsource:", visible)
        self.assertEqual(resource.conditions, before)
        self.assertIn("https://example.org/source", details(resource))
        from dataclasses import replace

        mixed = replace(
            resource, conditions="A prose statement about textsource: https://example.org/source"
        )
        self.assertEqual(visible_conditions(mixed), mixed.conditions)

    def test_youversion_summary_does_not_claim_unfetched_conditions_are_absent(self):
        from bible.resource_details import details
        from bible.i18n import tr
        from bible.youversion_catalogue import resource_from_listing
        from tests.test_youversion_catalogue import listing

        text = details(resource_from_listing(listing(), "spa"))
        self.assertIn(tr("Loading edition details…"), text)
        self.assertNotIn(tr("No additional conditions supplied by the source."), text)

    def test_only_explicit_http_links_are_displayed(self):
        from bible.resource_details import linkable_url, first_link

        self.assertEqual(linkable_url("https://crosswire.org/"), "https://crosswire.org/")
        self.assertEqual(linkable_url("javascript:alert(1)"), "")
        self.assertEqual(linkable_url("https://evil.test@crosswire.org/"), "")
        self.assertEqual(linkable_url("https://crosswire.org/\n"), "https://crosswire.org/")
        self.assertEqual(
            first_link("CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)"),
            "https://creativecommons.org/licenses/by/4.0/",
        )
        self.assertEqual(first_link("No link supplied"), "")

    def test_legacy_paragraphs_keep_attribution_words(self):
        value = r"First paragraph. \\par\\parSource: Richard Lemay. \\parPermission retained."
        text = plain(value)
        self.assertNotIn("\\par", text)
        for attribution in ["First paragraph.", "Source: Richard Lemay.", "Permission retained."]:
            self.assertIn(attribution, text)
        self.assertIn("\n", text)
        self.assertEqual(plain(r"Keep \\parallel unknown text"), r"Keep \\parallel unknown text")

    def test_repeated_verified_public_domain_claims_deduplicate_without_losing_authored_terms(self):
        import tempfile
        from pathlib import Path
        from bible.library import config, resource_from_section
        from bible.resource_details import conditions_presentation

        data = (
            b"[Example]\nDescription=Source\nDistributionLicense=Public Domain\nCopyright=PUBLIC DOMAIN\n"
            b"ShortCopyright=PUBLIC DOMAIN\nCopyrightNotes=This complete original English notice must remain.\nCopyrightHolder=Different substantive attribution\n"
        )
        resource = resource_from_section("Example", config(data)["Example"])
        with tempfile.TemporaryDirectory() as directory:
            conf = Path(directory) / resource.id / "mods.d/example.conf"
            conf.parent.mkdir(parents=True)
            conf.write_bytes(data)
            text, _ = conditions_presentation(resource, directory)
            self.assertNotIn("PUBLIC DOMAIN", text)
            self.assertIn("This complete original English notice must remain.", text)
            self.assertIn("Different substantive attribution", text)
            self.assertIn("PUBLIC DOMAIN", resource.conditions)

    def test_approved_profile_uses_exact_cached_edition_independently_from_installed_version(self):
        import json
        import tempfile
        from dataclasses import replace
        from bible.resource_profile import approved_profile, profile_text
        from bible.curated_catalogue import catalogue
        from bible.catalogue_cache import CatalogueCache
        from bible.providers import BIBLE_RESOURCES, CROSSWIRE
        from tests.test_curated_catalogue import record, body, sword_metadata, CONF
        from unittest.mock import patch

        entry = record()
        entry["profiles"] = {
            "fr": dict(
                format="markdown",
                revision="editorial-test-2",
                approved_at="2026-11-23",
                approved_by="Test publisher",
                approval_url="https://example.org/approval",
                long_markdown="### Heading\n\n**Source words**\n- Original caveat\n<script>inert</script>",
            )
        }

        def fetch(url, out, **kw):
            out.write(
                body([entry]) if url.endswith(".json") else sword_metadata(CONF + b"Version=1.0\n")
            )

        with patch("bible.library.download", side_effect=fetch):
            current = catalogue()[0]
        old_entry = dict(entry, version="0.9")
        old_entry.pop("profiles")
        installed = replace(
            current,
            version="0.9",
            acquisition=json.dumps(
                dict(catalogue_url=BIBLE_RESOURCES.catalogue_url, entry=old_entry)
            ),
        )
        before = installed
        with tempfile.TemporaryDirectory() as directory:
            cache = CatalogueCache(directory)
            cache.write(BIBLE_RESOURCES, [current])
            saved = cache.read(BIBLE_RESOURCES)[0]
            self.assertEqual(approved_profile(installed, saved, "fr")[0], "fr")
            self.assertEqual(
                approved_profile(installed, saved, "en")[0], "fr"
            )  # honest source-language fallback
            self.assertIsNone(
                approved_profile(
                    installed,
                    [
                        replace(
                            current,
                            provider_id=CROSSWIRE.id,
                            source=CROSSWIRE.name,
                            source_url=CROSSWIRE.url,
                        )
                    ],
                    "fr",
                )
            )
            changed = dict(entry, canonical_edition_id="another-edition")
            other = replace(
                current,
                acquisition=json.dumps(
                    dict(catalogue_url=BIBLE_RESOURCES.catalogue_url, entry=changed)
                ),
            )
            self.assertIsNone(approved_profile(installed, [other], "fr"))
            unapproved = dict(entry, profiles={"fr": dict(entry["profiles"]["fr"], approved_by="")})
            draft = replace(
                current,
                acquisition=json.dumps(
                    dict(catalogue_url=BIBLE_RESOURCES.catalogue_url, entry=unapproved)
                ),
            )
            self.assertIsNone(approved_profile(installed, [draft], "fr"))
        text, spans = profile_text(entry["profiles"]["fr"]["long_markdown"])
        self.assertIn("• Original caveat", text)
        self.assertNotIn("###", text)
        self.assertIn("<script>inert</script>", text)  # native text, never HTML execution
        self.assertIn(("heading", 0, 7), spans)
        self.assertEqual(installed, before)
