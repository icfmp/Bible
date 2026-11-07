# Ready batch #204–#214, #218–#228 and #230–#232

This is a candidate implementation and validation ledger, not a release report.
No issue is closed by this change. The last verified published application at
intake was alpha26, source `6faab9201d4fdf496ccb931c62b1cf9aa9e7f233`.
All 25 descriptions and then-current comments were read; all had zero comments.
At intake, the only pre-existing open PR was research PR #59. A subsequent refresh also found #242 (source attributions) and #245 (tab titles); both patches were read. They remain independent and are not merged or claimed by this batch.

| Issue | Candidate scope | Verification / outstanding acceptance |
| --- | --- | --- |
| #204 | Shared compact cards, pointer, focus and small primary arrow | Native passage card mouse/citation/Return/Space checks pass; final app-wide visual audit and packaged checks pending |
| #205 | Reference/theme/text/occurrence/place cards; note summaries prioritize passage and the user's note | Note storage/citation tests and actual pointer/keyboard checks pass; FR/EN narrow/contrast captures pending |
| #206 | Original passage → word → occurrences; actual form/transliteration, honest English meanings, collapsed linguistic details | Real STEP G2532 inspected; real BDS Mark7:4/G2532 and Genesis1:1 Hebrew keyboard passage/word/occurrence/preview/back flows pass in FR/EN light/dark; beginner acceptance remains client-owned |
| #207 | Requested dictionary-symbolic Library replacement | Exact upstream SVG imported with client approval after verifying its absence in GNOME49; pinned CC0 provenance; packaged resolution pending |
| #208 | Requested dictionary-symbolic / notebook-symbolic switcher and Notes icons | Client authorized official assets on 7 November; exact dictionary/notebook SVGs replace all custom usages; native tests pass, packaged proof pending |
| #209 | Native mark-location-symbolic at both former custom-place usages | Availability checked in development GTK and actual installed GTK49; screenshots pending |
| #210 | Remove obsolete filter SVG alongside #231's semantic sidebar-control cleanup | The former icon had one production use, opening a sidebar, not applying a filter; no obsolete filter operation retained |
| #211 | Pinned actual Roboto and Roboto Serif, OFL notices; defaults for new profiles, saved choices retained | Fontconfig resolves downloaded families in isolated native tests; actual offline packaged font resolution pending |
| #212 | Correct FR/EN AppStream component, desktop identity and manifest install | Missing metadata and generic local-bundle Software details reproduced on exact alpha26; semantic validator, final screenshots and candidate details page pending |
| #213 | Update existing Library rows in place when IDs/order are unchanged | 200-row Bible/commentary metadata refresh retains exact model objects, no splice, position within 2 px; real packaged install flow pending |
| #214 | First readable install opens the active reader immediately; invalid saved resource recovers deterministically | First install, restart, valid-reader preservation, Notes return and corrupt metadata/data preservation pass |
| #218 | Existing place names/evidence/bibliography plus separately licensed reviewed Jerusalem context and optional photo | Source licenses/identity/photo inspected; integrity/offline/explicit-download unit checks pass; real Jerusalem photo/full-size/offline reopening, Emmaus six disputed candidates and unidentified Nod checks pass; packaged cases pending |
| #219 | Remove standalone translation-notes page/action; preserve inline notes and exact locators | Native source-note mouse/keyboard and chapter-change tests pass; legacy tool falls back to a valid tab |
| #220 | Small raised native source-note icon with exact locator in accessible context/popover | Exact official talking SVG now bundled with client approval; locator preserved; native mouse/keyboard tests pass |
| #221 | Spinner inside submit button, compact native scope, inert previous results during pending search, no redundant topic instruction | Controlled asynchronous/stale-response/empty-query tests pass; final FR/EN layout captures pending |
| #222 | Remove commentary overflow; retain sparse previous/next and unique preface through native text context menu | Source preface fidelity/navigation tests pass; Library retains existing attribution/download route |
| #223 | Native view, quiet empty states, three underlined study tabs, one reference heading | Native three-tab checks pass; final theme/width screenshots pending |
| #224 | Aa Text/Appearance groups, collapsed default on fresh profiles, advanced action, two-column preference palettes | Independent fonts/preferences round trips pass with real Roboto available; final scale captures pending |
| #225 | One native separator within the existing 8 px resize target | Actual screenshot measured one visible pixel at scale1; native keyboard resizing passes; scale2 native drag/keyboard/width persistence/collapse pass in light/dark/high contrast; packaged check pending |
| #226 | Labeled book Introduction; supplied headings/emphasis/paragraphs in native selectable text | Existing introduction fidelity/navigation checks pass; nested source styles/paragraphs and actual BDS Jeremiah FR/EN wide/narrow end-of-document selection checks pass |
| #227 | Visible Original text label with native wrapping and correctly measured backdrop surface | Real mouse/keyboard Copy/highlight/notes/parallel/immersion checks pass; narrow bounds and hidden-backdrop work checks pending |
| #228 | Continuous commentary entries/chapters in ordinary and immersive reading; preserve GTK text marks during extension | Repeated synthetic native chapter forward/reverse checks pass; four real Segond/BDS × MHC/Wesley combinations pass eight forward/reverse cycles; measured results below; packaged checks pending |
| #230 | Coherent source context → My note → labels → links; bounded editor, contextual Bible action, visible confirmed deletion | Native citation/card/expansion/360px/150% editor checks pass; all four surfaces captured before/after in FR/EN, light/dark, wide/narrow; legacy/new backup/link round trips pass; installed checks pending |
| #231 | Remove wide Notes toolbar filter control; keep one semantic adaptive header sidebar toggle | Existing filters/state tests pass; actual wide/narrow screenshots pending |
| #232 | Remove redundant follow/all-annotations buttons; preserve APIs, drafts and main Notes navigation | Actual Bible wheel resumes following; manual note wheel suspends without navigating; captured draft and stable card tests pass |

## Native composition and interaction exceptions

Simple reference, theme, text and occurrence actions use the shared native
`GtkButton` card. A personal-note card can also contain genuine citation links;
it therefore uses the same shared visual content in a native composite. Its
reference header is a real primary button (Enter/Space), citation labels retain
native link activation, and otherwise unused card space opens the note. Pointer
and keyboard interaction were exercised together: a citation opens only its
preview; a note action opens only its editor. The original wrapping-button
candidate failed this real mouse test and was corrected rather than accepted
based on callback-only tests.

Highlight cards retain their genuine recolor/remove controls. Library download
rows retain installation/cancellation controls. Navigation tabs, source credits,
formatting buttons and menus remain their appropriate native controls instead
of being turned into competing passage cards. No new universal card framework
or storage format is introduced.

## Validation boundaries and publication gates

A development GTK4.18.6/X11/Cairo full-suite checkpoint ran 490 tests with six
failures and two skips. Three assertions described the superseded first-install
behavior; those were updated to #214's explicit immediate-opening behavior.
One missing startup diagnostic was corrected and retested. An immersive
selection check passes when the actual Roboto font is available rather than a
host fallback. One exact focus-pixel assertion fails identically on alpha26 and
the candidate in this local environment: `(17,76,143)` versus `(0,63,135)`.
That assertion was not weakened or skipped. Required CI and actual Flatpak
results must be recorded separately, and the final source rerun remains required.

Real before/draft-after GTK screenshots exist for French light/dark surfaces.
Draft captures exposed an overly short asynchronous word dialog and incorrect
wrapped-overlay measurement; both were corrected. Those defective intermediate
captures are not final validation evidence. Final FR/EN and narrow/large-text
captures must use the tested source. The store screenshot must be refreshed.

The GitHub Project5 query remains forbidden: `Resource not accessible by
integration`. No project status is invented or an issue closed as a workaround.
Applicable manual status transitions must be requested in the delivery report.

Merge, exact-source green CI, signed alpha deployment, actual retained-profile
update verification and one numbered alpha prerelease are outstanding. The
prospective alpha27 metadata is not a claim that alpha27 has been published.

## Official icon approval and compatibility follow-up

After the runtime availability report, the client explicitly authorized the
official SVG additions on 7 November 2026, superseding #208's no-new-assets
constraint for these exact upstream assets. Four unmodified 16px icons by Jakub
Steiner are pinned to GNOME Icon Development Kit commit
`cf705cdad8b594295cabe84cac3b6efe4c0f7972`, with CC0 license, embedded creator
metadata, file hashes and installed notices. Dictionary and notebook replace
all former custom Library/Notes usages. Talking replaces the temporary allowed
information fallback. Filter is available without restoring #231's redundant
sidebar button. Native availability and existing action tests pass; actual
packaged resolution and light/dark rendering remain publication gates.

The first candidate CI validated AppStream, desktop identity and real host
Roboto resolution. It ran 494 tests with one failure: an older Adwaita fallback
adds a native FlowBoxChild around Copy, so a structural ordering assertion needed
to inspect that wrapper. A native compatibility test also exposed an extra
keyboard focus stop on those wrappers; only the actual toolbar controls now
participate in traversal. No failure was skipped or relabeled as a successful
Flatpak build; the packaging job did not run for that failed source.

## Real-resource commentary comparison (#228)

The exact alpha26 application tree was compared against the candidate application
tree through `f527cf1` (the subsequent `b9d4b2f` change only adjusts a host test).
Both used separate marked copies of the same retained test profile and identical
1280×900 geometry, saved DejaVu Serif14, Cairo/X11 GTK4.18.6, Genesis1 and actual
downloaded resources. Startup is a fresh process; OS/file/font caches were not
flushed. Timings end on an after-paint frame with usable text. These are local
development measurements, not installed-Flatpak or client-hardware measurements.

| Bible / commentary | Startup usable text, alpha26 → candidate (ms) | Immersion first / subsequent opens, alpha26 → candidate (ms) | Candidate RSS after cycles1 →8 (MiB) |
| --- | --- | --- | --- |
| BDS / MHC | 1029 →1144 | 220 /175,180 →243 /182,178 | 170.0 →175.2 |
| BDS / Wesley | 881 →791 | 157 /160,165 →252 /165,160 | 161.5 →161.9 |
| Segond / MHC | 1142 →1007 | 202 /182,181 →223 /181,179 | 164.9 →166.6 |
| Segond / Wesley | 954 →871 | 159 /164,165 →184 /164,165 | 159.6 →162.2 |

Alpha26 stops at the actual final Genesis1 entry in each ordinary-scroll case
and cannot turn beyond that chapter in commentary immersion. The candidate
crosses in both directions on all eight cycles of all four combinations, keeps
13–14 loaded entries in these cases, permits immersive continuation, and leaves
notes unchanged. RSS stabilizes instead of growing on every repeated cycle.
These timings do **not** establish a speed improvement: warmed immersion is
comparable, and the native wheel test includes input pacing. Earlier protocols
that seeded the end of the whole moving buffer were rejected: they changed the
tested passage each cycle and cannot support a before/after claim.

## Additional native validation checkpoint

- Four note surfaces have actual before/after FR/EN captures at1280 and560px in
  light/dark. No note changed in any capture run. A narrow Notes allocation warning
  occurs on both alpha26 and candidate in the local Adwaita environment; the actual
  editor remains within its viewport. Installed-GNOME49 validation is still required.
- The real BDS Mark7:4 Greek καὶ/G2532 entry provides the English gloss “and”; no
  French meaning is fabricated. Native keyboard passage →word →occurrences
  →preview →word →passage passes, as does Genesis1:1 Hebrew RTL. Reader history
  and notes remain unchanged. All supported introduction source tags survive
  nested paragraph cleanup; actual Jeremiah's last paragraph remains reachable.
- Scale2 screenshots contain one contiguous two-physical-pixel separator (one
  logical pixel), without an adjacent second edge, in light/dark/high contrast.
  Actual pointer drag, arrow resizing, saved width, reopening and collapse pass.
- A focused20-test run covers citations, source introductions, commentary text
  selection, note backup/restoration and linked passages, including legacy data.
  All pass. A direct-callback citation test now waits for the drawer's initial
  allocation/following to settle; the separate real pointer/keyboard checks remain.

Required CI has not yet produced a green candidate Flatpak. The latest complete
host run ran495 tests with one intermittent citation-preview failure; a20-repeat
local reproduction passed. This is recorded as an unresolved CI gate until the
exact revised source passes. No merge, signed alpha update or numbered release
is claimed by these native checks.

## Exact-source host and installed-candidate checkpoint

Source `a7b02d34be914fe52ce55e31b280b40759b15d35`, run42379203195:

- Host prerequisites passed:496 tests (26 skips),183 French tests (2 skips),
  native focus-pixel verification, all real X11 action/workspace/navigation
  checks, and actual CrossWire/commentary integration.
- The GNOME49 Flatpak was actually built and installed. Its263-test suite,
  13 immersive tests,7 selection/inline tests, actual YouVersion opening,
  real STEP/navigation/offline checks and sustained scrolling passed.
- The complete packaging job still failed: the blur diagnostic changed the
  radius but invalidated the controls, whose cached background is now a separate
  widget. It reported identical pixels because GTK correctly reused that cache.
  The diagnostic now invalidates `bar.background`; its assertions remain intact.
  A full local GLRenderer run passes, with24307 changed pixels and edge energy
  89078→12526. No production blur change or weakened assertion is involved.
- New place/word diagnostics were skipped after that failure. No verified
  distributable bundle or signed publication is claimed from this run.

Additional real GTK Library validation used a fresh, marked test profile, the
actual CrossWire catalogue, native wheel traversal and row-download clicks.
Geneva1669 opens immediately at Matthew1:1 as a real NT-only first install;
installing Wesley leaves that Bible open. The displayed279-row Bible and41-row
commentary models retain their exact objects, with zero `items-changed` events.
The same actually displayed surrounding row stays within3px for the Bible and
exactly in place for the commentary, after the final installation frame.
The numerical adjustment can change because GTK estimates offscreen row heights;
intermediate measurements while the footer resizes the viewport are not a final
scroll-position result. Experimental focus/anchor restorations were rejected
and removed. The product retains the simple in-place model update and GTK's
native anchoring, including user scrolling during transfers.

A separate native SQLite write-prohibition test confirms that installing the
first Bible cannot dismiss an unsavable note draft. Existing note identity,
passage and original-source context remain intact; the established guard saves
the draft and returns to reading once writes are allowed.

The actual narrow place check also found that an unwrapped alias disclosure
forced a533px dialog. Its native label now wraps; actual360px English/dark and
French/light wide checks pass with the real reviewed photo and unchanged source
names. Installed diagnostics now expose explicit theme/width options for that
verification. Obsolete research-script attempts to open the removed translation
notes page have been replaced with the real Notes tab and an absence check.

The revised exact source must pass the complete required CI, candidate Software
details verification and retained-profile signed update before merge/delivery
claims are upgraded.

## Test-isolation follow-up

The revised source `77a480f` passed the host checks, but its264-test installed
suite stopped on the synthetic commentary wheel test. Repeating the lifecycle
suite immediately before that wheel test reproduced eight failures in eight
cycles locally. The new write-prohibition test emitted the confirmation's Cancel
response directly but did not destroy its artificial dialog, retaining an input
grab for subsequent windows. Matching the established cleanup used by the other
native tests changes that same40-test sequence to40 passes, including all eight
native chapter-wheel cases. No commentary implementation, timeout, assertion or
wheel distance was changed to obtain that result. The full installed pipeline
must still pass on the revised exact source.

## Retained reference viewport during refresh

Source `abcd833` passed497 host tests and183 French tests, but the installed
264-test suite detected a7px adjustment change while reference data refreshed.
The existing same-passage list was retained, yet its temporary loading label
inserted a new row above it. A native geometry trace measured the viewport
shrinking by27px and the card's window position moving by27px during that state.
The refresh now keeps the existing cards without inserting that loading row;
new passages and empty states retain their loading feedback. The regression
also checks the unchanged viewport and absence of the extra status row, without
loosening its scroll-position assertion. Exact-source full CI is still required.
