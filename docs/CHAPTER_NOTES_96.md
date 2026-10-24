# Chapter annotations and semantic following (#96)

Study → Notes displays the current leading Bible chapter's complete annotation
collection in mapped Bible order. Independent note UUIDs and verse highlights
remain separate cards, including multiple records at one target. Notes that
actually overlap a chapter appear once. The heading names the chapter, and verse
changes within it reuse the same cards rather than refiltering to one verse.
Original references, readable previews, inline editing and highlight card actions
remain available. Clicking a card's reference deliberately navigates through the
existing verified resolver; clicking note text edits, and citations retain their
shared preview behavior.

Following uses the leading Bible's semantic reference. All overlapping records
are reachable from the first matching group. A gap chooses the next annotated
group, or the final preceding group if none follows. Only enough movement to
reveal the group's heading is applied; a visible group is left still. Automatic
following never navigates Scripture, adds history, changes focus or scrolls the
Bible from Notes. Existing comparison coordination maps its active source into
the leading Bible; a comparison gesture cancels a stale primary-side request.
Commentary coordination retains its established contract.

Wheel, scrollbar/key browsing, card interaction and inline editing suspend
recentering. One discreet Resume following action stays above the scrollable
cards, including after browsing away from the chapter heading. Deliberate Bible
input resumes following when no inline draft is active. Editing retains its
captured target and text through scroll, chapter/tab changes, delayed callbacks,
expansion and save/discard/cancel. A pending reveal is canceled on replacement
or close and verifies its tab, chapter generation and reference before moving.

The standalone Highlight creation dropdown above cards and the central
“Passage notes (N)” strip are removed, including the strip's reserved height.
Highlight/note creation remains in the existing contextual selection toolbar.
Card recoloring/removal, legacy standalone notes, actual highlights and
intentional inline markers remain. Clicking an inline marker reveals Study →
Notes without automatically entering an editor.

## Range and data compatibility

No schema, journal, new annotation model, identity migration or rewrite is used.
The existing `start`/`end` fields now accept ordered ranges across chapters of
one book. Previously they rejected every cross-chapter note. Membership and
`covers()` use the actual chapter/verse interval; reverse and cross-book ranges
remain rejected. Existing SQLite schema/version 1 and JSON backup/version 1 are
unchanged. Tests reopen and export/restore old and cross-chapter records together,
with exact identity/body/context retained. Older application versions that still
reject cross-chapter ranges cannot open such new notes: use the updated alpha to
restore these backups, rather than downgrading after creating a new range.

Read-only passage projection enumerates actual source verses, skips SWORD's
verse-zero chapter introductions, and maps each verse with the existing verified
resolver. It does not equate printed verse numbers or fill discontinuities. An
actual KJV Genesis 31:54–55 note appears in Luther chapters 31 and 32 without any
change to its stored range. Missing/unverified mappings remain conservative;
there is no fabricated alignment or Scripture. Unknown excerpts remain clearly
unavailable and annotations remain editable through the existing views.

## Verification

`tests.test_chapter_notes` checks ordered chapter membership, duplicate-target
records, highlight-only cards, gaps, forward/back following, stable card identity
and history, browsing suspension/resume, retained drafts across chapters/tabs,
actual differing versification and comparison, cross-chapter overlap once, and
205-card collections with cancellation of stale reveals. `tests.test_notes` adds
schema/identity/restart/backup round-trip checks for the expanded range boundary.
Existing card/selection tests preserve readability, contextual creation and
independent highlight removal. A Library heartbeat test now waits explicitly for
its five ticks under a half-second responsiveness bound rather than
assuming a fixed 120 ms interval always contains them.

`python3 -m tools.check_chapter_notes` performs actual X11 Bible wheel input in
both directions, manual Notes scrolling, native Resume, intentional marker
activation and keyboard typing while the Bible moves. The same checker and test
module run against application code imported from the installed Flatpak `/app`.
`tools.check_passage_note_cards` uses actual contextual creation after removal of
the duplicate dropdown. Before/after captures use real local French resources,
disposable saved annotations, light/dark, comparison, narrow and short windows.
See [native evidence](evidence/chapter-notes-96/README.md).

Developer Xvfb/installed-Flatpak checks do not replace client GNOME acceptance,
Wayland/touchpad testing or specialist accessibility validation. Complete chapter
collections are currently rendered with the existing compact card widgets; no
unmeasured arbitrary-scale performance claim is made.

## Client checks

1. In a chapter with several notes/highlights, scroll the Bible in both directions
   and confirm the chapter list stays complete and follows the relevant group.
2. Scroll Notes manually or edit a note, then use Resume or deliberately navigate
   the Bible; confirm browsing and the captured draft remain stable.
3. Check a small light/dark window and comparison: the central banner and duplicate
   Highlight dropdown are absent, while selection actions and existing data work.

Keep #96 open for client validation. Exact build/publication receipts belong in
the PR. Numbered prereleases remain paused by the client's instruction (#87).
