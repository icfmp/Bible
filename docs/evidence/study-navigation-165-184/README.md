# Bible alpha.24 — study and parallel navigation

Published release: https://github.com/icfmp/Bible/releases/tag/0.1.0-alpha.24

## Changes since alpha.23

- Library uses the approved separate active download footer: resource name, one progress indication and right-hand Cancel. Success clears the footer and leaves a brief confirmation plus the installed row; failure/retry remains actionable (#165).
- Shared parallel following uses declared, verified reference conventions and compatible native indexes, without renaming modules or guessing verse equivalence. Darby/NBS and Semeur/NBS are covered together; unsupported locations remain local (#171, duplicate #184).
- Reference previews fit their content and available window space, keep both navigation actions, and retain discreet accessible attribution (#179).
- New or recovered reference lists start at the first card; unchanged-passage refreshes and tool switches retain manual scrolling (#180).
- Theme passages share References cards, a single navigation/title/count row and an unobscured final card (#181).
- Original text follows passage → original word → paginated occurrences. Hebrew/Greek ordering, source references, transliteration and explicit English possible meanings are retained; raw STEP documentation stays out of lexical results (#182).
- Comparison chooses a translation when off and exits immediately when on, using a correctly rendered crossed-panel symbolic icon. The secondary selector remains available (#183).

## Verification

[Exact main CI](https://github.com/icfmp/Bible/actions/runs/42107442188) is green. The reviewed candidate also passes 456 general tests (20 native-dependency skips in the distro step), 178 French UI tests, and 231 + 13 + 7 installed Flatpak tests. Dedicated [French](https://github.com/icfmp/Bible/actions/runs/42105990450) and [English](https://github.com/icfmp/Bible/actions/runs/42106026491) checks each run 25 packaged tests without skips, actual STEP transfer/cancel/retry, controlled failure recovery, ten directional real-resource comparison cases, native card actions, small windows and a network-unshared offline restart.

[Signed publication](https://github.com/icfmp/Bible/actions/runs/42111331193) and the [actual alpha.23 upgrade](https://github.com/icfmp/Bible/actions/runs/42107565702) pass. The same profile retains notes, highlights, reading preferences, study data and 65 resource-file digests, with unchanged remote/ref/signing identity. Original captures are supplied privately.

## Known limits

Cloud native X11 checks do not establish client GNOME/Wayland, screen-reader or long-session hardware acceptance. Some OpenGL captures retain minor glyph repaint artifacts after one second; local Cairo does not show them and their cause is not isolated. Unknown/incompatible reference structures and unresolved verse parts remain explicit. English lexical possibilities are not French translations or asserted word-for-word alignments. Translation-note styling is recorded separately in #185 and is outside this release. Implementation issues remain OPEN for client validation.

## Install or update

Install using [Bible.flatpakref](https://icfmp.github.io/Bible/alpha/Bible.flatpakref), or update with:

    flatpak update --user io.github.icfmp.Bible//alpha

Keep the existing profile. The continuous signed channel may later offer a newer verified source; this immutable numbered tag identifies this batch exactly.

## Provenance

Source: 6d260ff5e788653e6ee79c719dfcba71ed034fa9 (PR #186); main CI 42107442188; signed revision 42111331193-1.

OSTree: b69b230c39958e81c574c8bf7e714789693027d5e96a9e2f1e4b6b857259f32e. Signing fingerprint: 47A17230403EA4953745E6E020EB9FFCCECAFD8F.

[Matching immutable source archive](https://github.com/icfmp/Bible/releases/download/alpha-source-archives/Bible-6d260ff5e788653e6ee79c719dfcba71ed034fa9-sources.tar.gz), SHA-256 e4551a0116054eb14aa6b090990d542ec0abdeda58db60c91f732d8d8e1103b3. Verified build-bundle SHA-256: 6db13dc2cb034acce133c718bd403c6d33ca7c5261858d6306139a26d39beff1. Install through the signed channel above; no different binary is attached.

## Measured behavior and test boundaries

The installed alpha.23 baseline opens the reference list at 335/335 px. The final candidate opens at 0/201 px (nine rows); unchanged-list manual scrolling is retained. Delayed data refresh and recovery after a failed query have focused native regressions. The current baseline already opens Genesis 11 correctly; its missing following capability is distinct from the earlier first-chapter defect fixed in alpha.22.

Each language runs ten directional cases and 60 native wheel gestures online, then repeats with networking unshared: Darby/NBS Genesis 11; Semeur/NBS Psalm 33; KJV/Segond Psalm 3:1 ↔ 3:2; KJV/NBS Genesis 31:55 ↔ 32:1; BDS/LSG Genesis 11:3. Mapped body/group anchors differ by zero pixels in these checks. A merged title/body group can have different printed first-visible iterators; that is not treated as identical verse numbering.

In the same four-CPU worker, four combined scrollbar cycles measure alpha.23 startup/final RSS 445.9/463.3 MiB and alpha.24 430.1/449.3 MiB. Scrolling remains about 112–115% of one logical CPU; no CPU optimization is claimed. First scroll/paint latency is 2.65/4.75 ms before and 2.59/4.4 ms after. Two further wheel cycles each in single, comparison and study modes show no adjustment later than 500 ms after stop; the hidden backdrop is released and its placement tick stops. The study-only sample has one 120.2 ms main-loop delay. These short VulkanRenderer/scale-2 measurements do not establish long-session memory behavior or client hardware performance.

Captures: 22 original installed alpha.23 images and 65 final candidate images per language, light/dark, normal/narrow, online/offline. The captured candidate is ef3d78fb4c926cc1b36551bd71f6242409d9ed3e; its entire tree equals the verified merge/source 6d260ff5e788653e6ee79c719dfcba71ed034fa9 (tree 6abfcceecde561e26b18d3a83a1ed332df7a23fb). Both use GTK 4.20.4/GLRenderer and installed /app imports. The actual signed upgrade separately confirms the final application UI hash and preserved data. The icon defect found during visual review was corrected before final captures.

The initial publication attempt uploaded its Pages artifact but failed to find its metadata immediately; the next attempt could not fetch the github-pages environment before starting. Verified retry 3 succeeds with no app, workflow or repository-policy changes. The first retained-update attempt expired waiting for that failed publication; attempt 2 is the successful actual upgrade referenced above. Failed attempts are not counted as releases.

Project 5 access remains refused with Resource not accessible by integration. Required manual status: In validation for #165, #171, #179, #180, #181, #182 and #183; leave them OPEN. #184 remains the client-closed duplicate. Only the client marks Done.
