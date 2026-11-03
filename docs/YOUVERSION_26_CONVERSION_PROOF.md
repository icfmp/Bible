# BDS → OSIS → SWORD: limited conversion proof

Research for #26, 22 October 2026. **Not an application feature, full translation,
published resource, or authorization to redistribute BDS.** The client requested
this independent proof while the development team stabilizes the alpha.

## Result

The public chapter HTML is technically sufficient for faithful conversion of
the samples below. No browser automation, mobile-package extraction, private
API, App Key, account or authentication bypass was used.

| Sample | Actual results |
| --- | --- |
| [John 1](https://www.bible.com/fr/bible/21/JHN.1.BDS) | 51 verse IDs in 86 verse fragments; all 51 verses match after compilation/readback; 14 note bodies/locators and 6 headings retained |
| [Psalm 3](https://www.bible.com/fr/bible/21/PSA.3.BDS) | 9 verse IDs in 29 fragments; all 9 verses match; 2 note bodies/locators and 1 heading retained; poetry and numbered superscription retained |
| [John introduction](https://www.bible.com/fr/bible/21/JHN.INTRO1.BDS) | Entire introduction body/title match the SWORD book-introduction entry when compiled together with John 1 |

Four XML documents validate against official OSIS 2.1.1: three individual
documents plus combined John introduction/chapter. Twelve synthetic regression
tests pass. `osis2mod` 1.9.0 compiles the two limited modules without warnings.
Direct local SWORD readback and the existing application's non-GUI `Reader`
both return the same 60 source verses. The application structure extractor
recognizes headings, paragraph breaks and poetry. This is **not** a GTK or
Flatpak validation; note/introduction presentation in the UI remains separate.

Fidelity comparison permits NFC normalization and whitespace normalization only.
It does not fold case/punctuation, substitute words, remove superscriptions or
paraphrase. Notes are compared independently, not counted as scripture text.
The committed [verification record](research/youversion-26-verification.json)
contains hashes and counts, **no scripture or note bodies**.

Test runtime: Ubuntu package `1.9.0+dfsg-6build2` / SWORD 1.9.0, locally extracted
with Python bindings. The app pins the same upstream version but builds it
separately in Flatpak; that precise binary has not been tested by this proof.

## Conversion rules actually exercised

1. Parse exactly the requested `div[data-usfm]`, ignoring surrounding site UI.
   Match semantic class suffixes rather than the generated CSS prefix.
2. Read source content as ordered blocks and inline nodes. A repeated verse ID
   is a continuation, not a duplicate to discard. Reject non-contiguous returns
   to an earlier nonempty verse rather than overwriting content.
3. Map book codes explicitly (`JHN` → `John`, `PSA` → `Ps`, `2SA` → `2Sam`).
   Do not parse localized printed labels to establish verse identity.
4. Emit OSIS verse milestone pairs, preserving paragraphs that cross verses and
   verses that cross paragraphs. Keep mixed-content tails: introduction
   references can be bare text between spans. Never pretty-print mixed XML.
5. Preserve `p`/`ip` paragraphs, `qN` poetry lines/indentation, source headings,
   explicit references and numbered Psalm superscriptions. Retain the source
   poetry separator character; do not reinterpret it without evidence.
6. Separate editorial notes from the scripture stream. Preserve the source note
   locator, ordered note content and references. Note reference spans are not
   scripture verse spans even when they also have `data-usfm` attributes.
7. Preserve explicit italics and words-of-Jesus semantics without adding quote
   punctuation. An unannotated source `w` does not justify invented lemmas,
   morphology or Strong's numbers. Retain conservative quotation/word segments.
8. Keep the exact source attribution in OSIS and module metadata. Source URLs,
   raw-page hashes and converter scope accompany the proof. Do not import site
   fonts, scripts, styles or account data.
9. Reject unknown semantic elements, unexpected attributes, unsupported verse
   ranges and unclassified nonempty block text. This deliberately limited
   adapter must not silently discard content it has not been taught to handle.

Source model and converter: `tools/research/youversion_osis.py`.
Independent DOM/readback oracle: `tools/research/check_youversion_osis.py`.
Local schema/build/readback harness: `tools/research/build_youversion_proof.py`.
Synthetic tests: `tools/research/test_youversion_osis.py`.

## Versification: scoped success, not edition-wide compatibility

John 1 was compiled under KJV and Psalm 3 under Segond **for these samples only**.
The nine source verses of Psalm 3 do not fit KJV's eight-verse inventory by
identity. This is exactly why a blanket `Versification=KJV` would be wrong.
No complete-edition KJV/Segond equivalence, canonical mapping table or comparison
with other resources is established. Do not install these experimental modules
as a complete BDS or use them to claim cross-version alignment works.

An introduction-only OSIS compiled without a following chapter produced no
indexed text in this SWORD build despite exit status zero. Compiling that
introduction **with its actual following chapter** preserves it at `John.0.0`.
Always validate indexed content rather than trusting compiler exit status.

## Public HTML versus official API

The sampled public pages returned HTTP 200 and included content server-side.
That demonstrates sample accessibility, not long-term availability, download
speed, complete-edition access or a stable markup contract.

The official [API usage guide](https://developers.youversion.com/api-usage) and
[detailed Bibles API](https://developers.youversion.com/api/bibles) describe an
App Key and version-dependent access. The passage endpoint can return HTML
with headings and notes; plain text omits those elements. Book/chapter metadata
endpoints enumerate structure, not complete book text. The detailed reference
is more precise on that distinction than the quick-reference wording.

The [display guide](https://developers.youversion.com/guides/display-bible-html)
also distinguishes raw API HTML from SDK-transformed HTML. Do not assume the
public-page parser can consume either unchanged. Use separate adapters feeding
the same semantic model.

API access to BDS, permanent offline storage/export scope, credentials suitable
for an open-source desktop application and full-edition download availability
were **not** tested. This proof does not resolve them. The public source shows
Biblica's edition attribution and reserved-rights notice; preserve those notices
and verify source access conditions before product integration.

## Reproduce without committing source content

Use a private disposable directory outside the Git checkout. Acquire only the
three explicitly listed sample URLs there as `JHN.1.html`, `PSA.3.html` and
`JHN.INTRO1.html`. Copy the complete publisher attribution block from the source
footer into `attribution.txt`, preserving its three paragraphs. The research
tools do not fetch content or crawl a Bible themselves.

Provide the official schema files in a local schema directory:

- https://www.crosswire.org/osis/osisCore.2.1.1.xsd
- https://www.w3.org/2001/xml.xsd

The resolver uses only the supplied local W3C schema; validation does not access
the network. Install/provide `lxml`, SWORD Python bindings and `osis2mod` 1.9.0
in the research environment, not as new application dependencies.

From the repository root:

```sh
python -m unittest tools.research.test_youversion_osis -v
python -m tools.research.build_youversion_proof \
  --samples /absolute/private/sample-directory \
  --schema-dir /absolute/private/schema-directory \
  --osis2mod /absolute/path/to/osis2mod \
  --output /absolute/private/NEW-proof-directory
```

The output directory must not already exist. Generated HTML/OSIS/modules and
full logs remain private research artifacts. The JSON verification record is
safe to review separately. No operation touches the user's Bible data or the
signed alpha channel.

## Required next batch — Sol high

1. Resolve the provider access route and offline-storage contract, independently
   of this format proof. No mobile DRM or account workaround is required here.
2. Enumerate the actual edition's canon, chapters and introductions from metadata;
   validate its complete verse inventory and mapping instead of guessing it.
3. Extend the adapter with representative long verses, ranges/omissions,
   chapter-boundary structures and additional markup. Use explicit rejection
   until each class has fidelity tests. The limited proof does not implement
   multi-chapter joining or prove an entire edition.
4. Test compiled content in the app's exact pinned Flatpak runtime and actual
   GTK note/introduction handling. Existing structured reading works in the
   non-GUI check; full editorial typography is not established.
5. Plan compiler packaging: the current Flatpak sets `SWORD_BUILD_UTILS=No` and
   does not ship `osis2mod`. User-side SWORD conversion cannot simply invoke an
   absent system utility from the sandbox. Review a compatible build-tool or
   library-based import path; do not substitute a dedicated server.
6. Only then build the product provider: cancellation/retry/backoff, resumable
   manifests, honest progress, metadata provenance and atomic registration after
   content validation. No automatic full-Bible crawling is in this research PR.

Official format references:
[CrossWire OSIS Bibles](https://wiki.crosswire.org/OSIS_Bibles),
[OSIS schema](https://www.crosswire.org/osis/osisCore.2.1.1.xsd).
