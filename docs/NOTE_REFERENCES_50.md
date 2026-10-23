# Local Bible references in notes (#50)

Passage Notes and the existing My notes editor share the safe native Markdown
preview. Explicit French/English citations become underlined local actions:
click or Tab to the reference and press Enter/Space. Escape/outside dismissal
returns through the existing popup lifecycle. Previewing does not replace the
reading passage, append history, create a tab, or edit saved note text.

## Recognition and authored numbering

The initial grammar supports full French/English book names, existing OSIS names,
and the explicit abbreviation table in `bible/citations.py`. Examples include
`Romains 8.28–30`, `Romans 8:28–30`, `Ésaïe 9.2`, `1 Corinthiens 13.4–7`,
`1 Co 13.4`, `Rm. 8.28`, `John.3.16`, and same-book chapter-spanning ranges such
as `Romans 8:28–9:2`. Case, composed/decomposed accents and the normal dash forms
are supported. Canonical bounds and range order are validated separately from
installed-module availability. Dates, bare numbers, uncertain short aliases
such as `he`/`is`, chapter-only shorthand, implicit verse lists, Roman-numbered
books and cross-book ranges are not promoted to automatic links. This is a
bounded grammar, not universal natural-language understanding.

The note's **recorded versification** supplies the numbers' authored meaning,
not OpenBible's default convention or the currently displayed translation.
Activation resolves every source verse through the existing verified resolver
into the active installed Bible. For example, a Segond-authored `Psaumes 3:2`
previews actual KJV Psalm 3:1; Segond 3 John 15 resolves to KJV 14 through the
already verified split-verse tables. The popup identifies the actual translation
and target reference. Missing text/translation or unavailable mapping is explicit;
no silent translation substitution or online verse-text request occurs.

The preview is bounded to six exact local verses with a clear longer-passage
message and normal scroll/context-opening actions. Wrapped text gets a useful
minimum viewport; unavailable text hides that empty viewport. Explicit opening
uses the captured translation/target in the current or a new tab. A note's own
association/origin context is never retargeted by a citation mentioned in its body.

## Parser/dependency decision

[OpenBible's Bible-Passage-Reference-Parser](https://github.com/openbibleinfo/Bible-Passage-Reference-Parser/tree/15c9f0993267014d9d3aa81256b9ff5565e58856)
was evaluated at the audited commit `15c9f0993267014d9d3aa81256b9ff5565e58856`;
its upstream license is MIT and its grammar is substantially broader. Embedding
it would add a JavaScript runtime or require maintaining a port. The chosen
initial implementation instead extends existing book-name metadata and SWORD
canonical validation in Python. No upstream parser code/data is copied, no Node
or webview is added, and no new dependency/license is introduced. Ordinary book
names are address/UI metadata, not redistributed Bible text.

## Safety, editing and lifetime

Generated links are typed local citation objects, never executable URLs or HTML.
Recognition excludes fenced/inline code, existing Markdown links, raw HTML and
URL/scheme-like lines conservatively. Existing explicit links remain inert text.
Only safe rendered text/style spans are decorated; editable Markdown, backup
format, note IDs, labels, passage associations and original source metadata are
unchanged. Up to 200 citations are decorated in a note within the existing
200,000-character storage bound; display bounds do not truncate stored content.

Native drag-selection/double-click are preserved. Editing buffer cursor/selection
are separate from reference focus in the rendered preview. Typing and opening a
preview perform no navigation. Explicit navigation from either standalone or
embedded editor uses its existing save/discard/cancel guard; cancel preserves
the draft and current reader. Popup anchors are dismissed when their view unmaps
or is rebuilt. A real tab/translation change dismisses a stale preview; a benign
same-reader scroll notification does not close it.

## Verification and delivery

Before PR, 203 source tests and 68 affected tests in the GNOME 49 Flatpak passed.
The actual packaged application runs offline with real KJV/FreSegond resources:
inline pointer activation, native drag-selection, Tab/Enter/Space, Escape/focus
return, exact Romans range, mapped Psalm and split 3 John, My notes, actual draft
typing, cancel/discard guards, explicit new-tab opening and restart preserve the
original note. French narrow/light/dark/emulated-high-contrast checks are separate
from source fixtures. Receipts and package byte audit identify actual imports;
internal validation branches are not a separate client installation.

The PR records exact-head CI, review, merge and subsequent signed-alpha update
with controlled-profile preservation when complete. These are automated GTK/Xvfb
checks; client GNOME/Wayland and in-depth assistive-technology acceptance are
**not tested**. Accessibility remains deferred. Bible.com/BDS is excluded.

The final package audit matches all 74 application files and retains all 14
canonical mappings and their license notices. Compact receipts are under
`evidence/study-50/`; final package captures are `captures/note-50-*`. On the
source validation container, median render-plus-recognition time was 0.615 ms
for about 2,000 characters, 5.751 ms for 20,000 and 58.291 ms near the existing
200,000-character limit (8 samples each; the first cold parser load took
66.316 ms). These are observations, not latency guarantees.
