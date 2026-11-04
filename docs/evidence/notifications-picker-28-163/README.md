# Translation picker and notification investigation (#163, #28)

These are original GTK screenshots from an installed Flatpak using real CrossWire KJV and FreSegond1910 resources and YouVersion editions BDS (21) and LSG (93). No profile, database, complete Scripture resource or raw trace is published here.

## Scope

The picker separates the full edition name, the smaller subdued provider line and an optional public metadata code. It omits a badge when no public code exists, rather than deriving one from an internal module ID. Native selection, keyboard navigation and the contextual Library action remain available in the primary, parallel-pane and comparison popups. The header caption introduced by #155 is unchanged.

Rows use GTK wrapping and native scrolled-window size limits. The requested width is at most 520 logical pixels and follows the owner window's available width; GTK measures wrapped row heights. Geometry work runs on opening and the existing bounded window-layout updates, with an immediate return for hidden popups. There is no new periodic worker or cache infrastructure.

## Notification investigation

See [the pinned source investigation](../../NOTIFICATION_INTEGRATION_28.md). The current Notification/Inhibit portals, freedesktop notification interface and GNOME presence setter do not establish the caller-owned, crash-safe global suppression lease required by #28. Existing manual Do Not Disturb guidance and sandbox permissions remain unchanged. GNOME Shell's primary-monitor fullscreen policy is documented separately; it is not runtime evidence of notification suppression by Bible.

No real GNOME notification-delivery, crash-restoration or multi-monitor claim is made. Immersive reading checks and the investigation of notification integration are separate.

## Before and after

Before: source `39449e0743c8e8b6fb03fbfc30a7d259046502f3`, ordinary build [41779503655](https://github.com/icfmp/Bible/actions/runs/41779503655), installed native check [41787780543](https://github.com/icfmp/Bible/actions/runs/41787780543).

After: application PR head `30465ec38ccbe95f00c67b534707b7b8f758c80b`. Ordinary source/Flatpak CI [41794196167](https://github.com/icfmp/Bible/actions/runs/41794196167) and the unmodified installed picker check [41797299836](https://github.com/icfmp/Bible/actions/runs/41797299836) passed. Main merge `fcfd908857c1c36e1ef0f371849e1a20a62fbeca` has the same Git tree as that candidate. The signed publication and retained-profile update have not completed; see the blocked delivery status below.

| Case | Before | After |
| --- | --- | --- |
| Wide, light | [Original PNG](before/light-1200-primary.png) | [Original PNG](after/light-1200-primary.png) |
| Wide, dark | [Original PNG](before/dark-1200-primary.png) | [Original PNG](after/dark-1200-primary.png) |
| Narrow, light | [Original PNG](before/light-360-primary.png) | [Original PNG](after/light-360-primary.png) |
| Narrow, dark | [Original PNG](before/dark-360-primary.png) | [Original PNG](after/dark-360-primary.png) |
| Enlarged UI text, narrow | [Original PNG](before/large-text-360.png) | [Original PNG](after/large-text-360.png) |

The full [before matrix](before/README.md) and [after matrix](after/README.md) record the measured content widths at 1200, 560 and 360 pixels, in both themes and all three popup locations. Extra original captures show the native contextual Download more action. The enlarged-text after capture includes native Up/Down navigation to reveal the current choice; list scroll offsets can differ.

## Limits

These are automated developer checks under Xvfb/X11 in a disposable cloud environment. They do not establish manual acceptance on the client's GNOME/Wayland desktop, hardware graphics driver or monitor arrangement. Test resources and saved annotations/preferences are retained across the signed update; the client's actual profile is not accessed or reset. #28 remains open. The closure of #163 by icfmp is preserved; distribution verification is still pending independently. Numbered release #87 remains paused.

## Verified candidate checks

- 413 source tests (10 skipped), 169 French UI tests, native mouse/keyboard and immersion checks.
- Installed GTK 4.20.4 with GLRenderer: 18 light/dark/location/size cases plus enlarged text, native selection/reselection and contextual Library actions.
- Content widths: 520 pixels at1200, 512 at560, 312 at360. Enlarged UI text also retains312 at360.
- Real resources, SWORD fidelity, offline reopening, retained note drafts/maps, and sustained scrolling with cold OpenGL shader caches passed ordinary CI.
- All46 PNG files are copied byte-for-byte from the successful installed before/after checks. No diagnostic runtime-property probe captures are included.

## Delivery status — blocked by GitHub service incident

As of 4 November 2026, 11:25 UTC, [GitHub Status](https://www.githubstatus.com/) reports an investigating incident affecting Git Operations, API requests, Pull Requests and Actions.

- PR [164](https://github.com/icfmp/Bible/pull/164) is merged. Main source/Flatpak CI [41813732631](https://github.com/icfmp/Bible/actions/runs/41813732631) is green for application source `fcfd908857c1c36e1ef0f371849e1a20a62fbeca`.
- Publication [41817346966](https://github.com/icfmp/Bible/actions/runs/41817346966) has a signed first revision available but fails public installation with HTTP 503. Earlier attempts also received GitHub Internal Server Error while pushing the second prepared repository revision. This is not a completed controlled publication.
- Distribution repair PR [170](https://github.com/icfmp/Bible/pull/170), merged as `e22dd2c605a6028e2329238034e92b14038734ce`, adds bounded same-commit server-error recovery, a self-contained Git pack fallback, parent/concurrent-change checks and per-attempt Pages artifact names. Its [real channel restoration/signature/update CI](https://github.com/icfmp/Bible/actions/runs/41818781106) passes. It changes no application or resource data.
- Retained-profile update check [41813577757](https://github.com/icfmp/Bible/actions/runs/41813577757) timed out waiting for a successful final publication; the update and after-update measurement were skipped. **No successful after-update data-preservation check is claimed.** The prepared old profile has not been reset to hide the blocker.
- The public source catalogue contains46 archives and all45 previous archive records are unchanged. The signing identity remains `47A17230403EA4953745E6E020EB9FFCCECAFD8F`. No source archive was deleted or replaced.
- Issue #163 was closed as completed by `icfmp` at11:16:35 UTC, with no closing commit or GitHub App recorded. That closure is preserved. The remaining signed-publication/update verification is recorded independently and is not claimed complete. Project access returns `Resource not accessible by integration`; no project status was changed by this work. #28 remains open. Numbered release #87 remains paused.

The final captures above are from the successful unmodified installed application candidate, with capture harness `536c179a7a8f02aa978852a1fb485c373178a50d` and `shrink_probe=false`. They are valid GUI evidence, not evidence of a completed signed-channel update.

Last observed public packaging revision: `41817346966-1`; OSTree commit `4e741fb5ffbc0d17f0776610b4fd8a0351acc260be7fe15d976260c0f4afeff9`. The controlled final revision and after-update preservation remain unverified.
