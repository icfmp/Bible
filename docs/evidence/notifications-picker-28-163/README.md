# Translation picker and notification investigation (#163, #28)

These are original GTK screenshots from an installed Flatpak using real CrossWire KJV and FreSegond1910 resources and YouVersion editions BDS (21) and LSG (93). No profile, database, complete Scripture resource or raw trace is published here.

## Scope

The picker separates the full edition name, the smaller subdued provider line and an optional public metadata code. It omits a badge when no public code exists, rather than deriving one from an internal module ID. Native selection, keyboard navigation and the contextual Library action remain available in the primary, parallel-pane and comparison popups. The header caption introduced by #155 is unchanged.

Rows use GTK wrapping and native scrolled-window size limits. The requested width is at most 520 logical pixels and follows the owner window's available width; GTK measures wrapped row heights. Geometry work runs on opening and the existing bounded window-layout updates, with an immediate return for hidden popups. There is no new periodic worker or cache infrastructure.

## Notification investigation

See [the pinned source investigation](../../NOTIFICATION_INTEGRATION_28.md). The current Notification/Inhibit portals, freedesktop notification interface and GNOME presence setter do not establish the caller-owned, crash-safe global suppression lease required by #28. This investigation predates the client's cancellation decision. The current #28 scope removes the manual Do Not Disturb guidance and its exclusively owned code; that cleanup is pending in the Ready queue. GNOME Shell's primary-monitor fullscreen policy is documented separately; it is not runtime evidence of notification suppression by Bible.

No real GNOME notification-delivery, crash-restoration or multi-monitor claim is made. Immersive reading checks and the investigation of notification integration are separate.

## Before and after

Before: source `39449e0743c8e8b6fb03fbfc30a7d259046502f3`, ordinary build [41779503655](https://github.com/icfmp/Bible/actions/runs/41779503655), installed native check [41787780543](https://github.com/icfmp/Bible/actions/runs/41787780543).

After: application PR head `30465ec38ccbe95f00c67b534707b7b8f758c80b`. Ordinary source/Flatpak CI [41794196167](https://github.com/icfmp/Bible/actions/runs/41794196167) and the unmodified installed picker check [41797299836](https://github.com/icfmp/Bible/actions/runs/41797299836) passed. Main merge `fcfd908857c1c36e1ef0f371849e1a20a62fbeca` has the same Git tree as that candidate. The signed publication and retained-profile upgrade are now verified; see delivery evidence below.

| Case | Before | After |
| --- | --- | --- |
| Wide, light | [Original PNG](before/light-1200-primary.png) | [Original PNG](after/light-1200-primary.png) |
| Wide, dark | [Original PNG](before/dark-1200-primary.png) | [Original PNG](after/dark-1200-primary.png) |
| Narrow, light | [Original PNG](before/light-360-primary.png) | [Original PNG](after/light-360-primary.png) |
| Narrow, dark | [Original PNG](before/dark-360-primary.png) | [Original PNG](after/dark-360-primary.png) |
| Enlarged UI text, narrow | [Original PNG](before/large-text-360.png) | [Original PNG](after/large-text-360.png) |

The full [before matrix](before/README.md) and [after matrix](after/README.md) record the measured content widths at 1200, 560 and 360 pixels, in both themes and all three popup locations. Extra original captures show the native contextual Download more action. The enlarged-text after capture includes native Up/Down navigation to reveal the current choice; list scroll offsets can differ.

## Limits

These are automated developer checks under Xvfb/X11 in a disposable cloud environment. They do not establish manual acceptance on the client's GNOME/Wayland desktop, hardware graphics driver or monitor arrangement. Test resources and saved annotations/preferences are retained across the signed update; the client's actual profile is not accessed or reset. #28 remains open. The closure of #163 by icfmp is preserved; distribution verification is complete independently. The client has withdrawn the mistaken #87 pause instruction; the standing numbered-alpha rule applies.

## Verified candidate checks

- 413 source tests (10 skipped), 169 French UI tests, native mouse/keyboard and immersion checks.
- Installed GTK 4.20.4 with GLRenderer: 18 light/dark/location/size cases plus enlarged text, native selection/reselection and contextual Library actions.
- Content widths: 520 pixels at1200, 512 at560, 312 at360. Enlarged UI text also retains312 at360.
- Real resources, SWORD fidelity, offline reopening, retained note drafts/maps, and sustained scrolling with cold OpenGL shader caches passed ordinary CI.
- All46 PNG files are copied byte-for-byte from the successful installed before/after checks. No diagnostic runtime-property probe captures are included.

## Signed delivery and verified update — 4 November 2026

[Numbered prerelease 0.1.0-alpha.20](https://github.com/icfmp/Bible/releases/tag/0.1.0-alpha.20) tags the exact application source `fcfd908857c1c36e1ef0f371849e1a20a62fbeca`. Source/main CI [41813732631](https://github.com/icfmp/Bible/actions/runs/41813732631), final [signed publication 41826448325](https://github.com/icfmp/Bible/actions/runs/41826448325), and [actual retained-profile upgrade 41827533843](https://github.com/icfmp/Bible/actions/runs/41827533843) passed.

Packaging revision `41826448325-2`, installed OSTree `63bee99a9021161a949173617cfc97ad74ade3c8b7f811a9019c23615cb05272`. Source archive SHA-256 `9773f4b173bbf2cc16db4d3b9a139bfaab6d43dfbb51c1bde2d9434ef899cfb6`; bundle SHA-256 `49e0f0c444a012f562d18adf0f0f6c1a9a1ea762ac67efc85861bed7be5733bc`. The stable signing identity, remote/ref and all previous source archives remain unchanged. [Install the signed alpha](https://icfmp.github.io/Bible/alpha/Bible.flatpakref) or run `flatpak update io.github.icfmp.Bible//alpha`.

The actual signed upgrade began with the immutable previous alpha.19 commit `cc68b9d2eb9d79ba7dafe7f544247a19dea9f64c2387352364196a2d125fdd28`. Its signature and application UI hash were checked before seeding the marked disposable profile once. The same profile was retained across before measurements, the real upgrade and after measurements: all55 resource files, six translations/commentaries, four study datasets, the note/highlight and preferences remained identical. The client's profile was not accessed/reset. Curated receipt artifact `13320347273` matches GitHub SHA-256 `cc7112de9ee5b49fdc2aae664c8e4ef698ec6c966f7e91758e0cbd8cf73dd59d`.

The upgrade check used VulkanRenderer, scale2, four combined scrollbar cycles and two wheel cycles each in single/comparison/study modes. No adjustment arrived later than500ms after stopping in these checks. The hidden selection toolbar released its backdrop and had no placement tick. These results do not establish client hardware-driver performance or fix the separately reported word-study crash.

Earlier publication attempts failed during GitHub's service incident (HTTP500/503), and the original retained-profile worker expired without updating. A later worker was cancelled because GitHub's commit-to-PR API omitted the known merged head; the corrected verifier checks PR164 directly. Neither incomplete attempt is counted as update evidence. The successful final worker above independently revalidated the immutable old signed application and retained its new isolated test profile throughout the upgrade.

Distribution-only [PR170](https://github.com/icfmp/Bible/pull/170), source `e22dd2c605a6028e2329238034e92b14038734ce`, adds bounded same-commit transport recovery and retry-safe Pages artifact names; no application/resource data changed. Issue163 was closed by the client; that closure is preserved. Issue28's subsequently approved cleanup remains separate and open. Project updates are refused with `Resource not accessible by integration`; no Done/status change was invented.

The original46 before/after captures use the successful unmodified installed candidate, harness `536c179a7a8f02aa978852a1fb485c373178a50d`, `shrink_probe=false`. Later diagnostic probes are not substituted for those captures.

| Same-profile combined test | Startup RSS (MiB) | Peak RSS (MiB) | Scroll CPU (% of one core) | First adjustment / paint (ms) |
| --- | --- | --- | --- | --- |
| current-signed-combined | 443.3 | 470.4 | 116.1–120.1 | 3.12 / 5.57 |
| candidate-signed-combined | 429.2 | 454.9 | 118.2–119.7 | 3.08 / 5.19 |

CPU is process usage on a4-CPU software-rendered worker, not total-machine percentage; samples remain specific to this bounded developer upgrade check. There is no claim that the picker change is a performance fix.
