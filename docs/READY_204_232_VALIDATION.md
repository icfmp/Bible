# Ready batch #204–#214, #218–#228 and #230–#232

This is a candidate implementation and validation ledger, not a release report.
No issue is closed by this change. The last verified published application at
intake was alpha26, source `6faab9201d4fdf496ccb931c62b1cf9aa9e7f233`.
All 25 descriptions and then-current comments were read; all had zero comments.
The only pre-existing open PR was the unrelated research PR #59, left untouched.

| Issue | Candidate scope | Verification / outstanding acceptance |
| --- | --- | --- |
| #204 | Shared compact cards, pointer, focus and small primary arrow | Native passage card mouse/citation/Return/Space checks pass; final app-wide visual audit and packaged checks pending |
| #205 | Reference/theme/text/occurrence/place cards; note summaries prioritize passage and the user's note | Note storage/citation tests and actual pointer/keyboard checks pass; FR/EN narrow/contrast captures pending |
| #206 | Original passage → word → occurrences; actual form/transliteration, honest English meanings, collapsed linguistic details | Real STEP G2532 inspected; latest real Greek/Hebrew walkthrough and beginner acceptance pending |
| #207 | Requested dictionary-symbolic Library replacement | Exact upstream SVG imported with client approval after verifying its absence in GNOME49; pinned CC0 provenance; packaged resolution pending |
| #208 | Requested dictionary-symbolic / notebook-symbolic switcher and Notes icons | Client authorized official assets on 7 November; exact dictionary/notebook SVGs replace all custom usages; native tests pass, packaged proof pending |
| #209 | Native mark-location-symbolic at both former custom-place usages | Availability checked in development GTK and actual installed GTK49; screenshots pending |
| #210 | Remove obsolete filter SVG alongside #231's semantic sidebar-control cleanup | The former icon had one production use, opening a sidebar, not applying a filter; no obsolete filter operation retained |
| #211 | Pinned actual Roboto and Roboto Serif, OFL notices; defaults for new profiles, saved choices retained | Fontconfig resolves downloaded families in isolated native tests; actual offline packaged font resolution pending |
| #212 | Correct FR/EN AppStream component, desktop identity and manifest install | Missing metadata and generic local-bundle Software details reproduced on exact alpha26; semantic validator, final screenshots and candidate details page pending |
| #213 | Update existing Library rows in place when IDs/order are unchanged | 200-row Bible/commentary metadata refresh retains exact model objects, no splice, position within 2 px; real packaged install flow pending |
| #214 | First readable install opens the active reader immediately; invalid saved resource recovers deterministically | First install, restart, valid-reader preservation, Notes return and corrupt metadata/data preservation pass |
| #218 | Existing place names/evidence/bibliography plus separately licensed reviewed Jerusalem context and optional photo | Source licenses/identity/photo inspected; integrity/offline/explicit-download unit checks pass; real photo UI and packaged cases pending |
| #219 | Remove standalone translation-notes page/action; preserve inline notes and exact locators | Native source-note mouse/keyboard and chapter-change tests pass; legacy tool falls back to a valid tab |
| #220 | Small raised native source-note icon with exact locator in accessible context/popover | Exact official talking SVG now bundled with client approval; locator preserved; native mouse/keyboard tests pass |
| #221 | Spinner inside submit button, compact native scope, inert previous results during pending search, no redundant topic instruction | Controlled asynchronous/stale-response/empty-query tests pass; final FR/EN layout captures pending |
| #222 | Remove commentary overflow; retain sparse previous/next and unique preface through native text context menu | Source preface fidelity/navigation tests pass; Library retains existing attribution/download route |
| #223 | Native view, quiet empty states, three underlined study tabs, one reference heading | Native three-tab checks pass; final theme/width screenshots pending |
| #224 | Aa Text/Appearance groups, collapsed default on fresh profiles, advanced action, two-column preference palettes | Independent fonts/preferences round trips pass with real Roboto available; final scale captures pending |
| #225 | One native separator within the existing 8 px resize target | Actual screenshot measured one visible pixel at scale1; native keyboard resizing passes; scale2/drag/persistence final check pending |
| #226 | Labeled book Introduction; supplied headings/emphasis/paragraphs in native selectable text | Existing introduction fidelity/navigation checks pass; expanded normalization/style and real Jeremiah cases pending |
| #227 | Visible Original text label with native wrapping and correctly measured backdrop surface | Real mouse/keyboard Copy/highlight/notes/parallel/immersion checks pass; narrow bounds and hidden-backdrop work checks pending |
| #228 | Continuous commentary entries/chapters in ordinary and immersive reading; preserve GTK text marks during extension | Repeated synthetic native chapter forward/reverse checks pass; real MHC/Wesley comparisons, timings and packaged checks pending |
| #230 | Coherent source context → My note → labels → links; bounded editor, contextual Bible action, visible confirmed deletion | Native citation/card/expansion/360px/150% editor checks pass; all four surfaces and backup/reopen final checks pending |
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
