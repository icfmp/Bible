# Ready Library, selection and navigation — verified alpha.22 delivery

Published release: [0.1.0-alpha.22](https://github.com/icfmp/Bible/releases/tag/0.1.0-alpha.22). This is aggregate evidence only; original captures are supplied privately.


Selection actions follow completed native selections even when GTK starts a text COPY drag or stops recognizing the application's click gesture. Partial and multiverse selections, direct highlight colors, Copy, passage notes and Original text remain available. Escape and scrolling invalidate pending actions. No native copying feature is disabled.

Library installation success uses a brief native confirmation instead of a permanent footer. Progress is cleared after completion; confirmations are dismissed when changing resource details so they cannot cover the next action. Active downloads and other resources' failures retain their own status.

Study-resource updates use checked immutable archives and a current metadata catalogue, allowing the reference and topic indexes to evolve while retaining installed offline data on failed updates. Reviewed French/English topic names and synonyms are independently versioned data rather than application code. The current reviewed vocabulary covers 50 of 6,712 topics; other topics retain explicit English fallback rather than invented translations.

A dedicated header search button immediately before Study opens Text/Topics. Ctrl+F opens search; the central passage selector and Ctrl+G/Ctrl+K retain passage navigation. Both comparison translation buttons fill their own pane, with a centered name and right-aligned arrow.

Unsupported cross-system comparisons open the requested numbered chapter when that chapter actually exists instead of silently opening the first chapter. The interface accurately identifies independent reading, and resource-qualified independent positions survive refresh/restart. This does not assert exact verse equivalence where no verified mapping exists.

## Verified delivery

- Exact application source: `583b734a3f65385e7aedc469729753bbd5676e19` ([PR #174](https://github.com/icfmp/Bible/pull/174)); its complete tree matches tested candidate `9aeb2e796a2f6f2cf180058878ff58e6f76e65f5`.
- [Main source and Flatpak CI](https://github.com/icfmp/Bible/actions/runs/41979075066), [signed publication](https://github.com/icfmp/Bible/actions/runs/41981784257), and [actual retained-profile update from alpha.21](https://github.com/icfmp/Bible/actions/runs/41979116244) pass.
- Packaging revision `41981784257-1`; installed OSTree commit `3d75ababcea529b637a43e6cb3c6d478e2ee807eeccb5fb84bfd7b0892612a86`, updated from `31cc1433d9f9967c43ec5f36d981a0662f5a9ac0bd2edffa56a1b0501d192ecb` with the same `bible-alpha` origin and `app/io.github.icfmp.Bible/x86_64/alpha` ref.
- Stable signing identity: `47A17230403EA4953745E6E020EB9FFCCECAFD8F`. The publisher verifies the public update and GPG commit/summary, GTK startup and persistent sentinels.
- [Exact source archive](https://github.com/icfmp/Bible/releases/download/alpha-source-archives/Bible-583b734a3f65385e7aedc469729753bbd5676e19-sources.tar.gz), SHA-256 `953519826b9c3cb2e87b2bc679596836f949ea88709f355d0adfabfe52c7fcf8`. Matching verified build-bundle SHA-256: `4d4f977a4cd0fa1198fe7f01abc30a81d48250e48e9b5fdd7b671284ca2dc8fc`. Install through the signed channel below; no mismatched binary is attached.

## Checks and limitations

Installed GTK 4.20.4/GL checks pass [173 genuine selection cases](https://github.com/icfmp/Bible/actions/runs/41977388624), with zero missing toolbar, collapsed selection or wrong target; [12 BDS Mark 11:29–30 Original text cycles and 120 further pointer selections](https://github.com/icfmp/Bible/actions/runs/41977424310); [actual study updates and a separate network-unshared offline restart](https://github.com/icfmp/Bible/actions/runs/41977400378); and [six directional cases across three resource pairs, selector changes and offline position restoration](https://github.com/icfmp/Bible/actions/runs/41977412382). The reproduced selection baseline had 82 missing toolbars among 173 nonempty cases.

[French](https://github.com/icfmp/Bible/actions/runs/41978491000), [English](https://github.com/icfmp/Bible/actions/runs/41978503709) and [exact alpha.21 baseline](https://github.com/icfmp/Bible/actions/runs/41978517442) Library/search checks provide original before/after light/dark and narrow captures. Images were visually inspected; an earlier test-harness theme mismatch was corrected before these final captures. Captures remain in workflow artifacts and are supplied privately, rather than copied into a public evidence branch.

The full update retains one developer profile, six real translations/commentaries, four study datasets, 55 module-file digests, notes, highlights and reading preferences. It does not reset a client profile. Four combined scrollbar cycles and two wheel cycles each in single/comparison/study modes show no adjustment later than 500 ms after stop; the hidden selection backdrop is released and its placement tick stops.

In the same cloud worker's combined comparison, startup/final process RSS is 436.7/459.9 MiB on alpha.21 and 415.7/445.2 MiB after update. Scrolling CPU is 116.6–120.6% versus 118.2–124.4% of one logical core: no CPU improvement is claimed. First scroll/paint latency is 2.99/5.02 ms versus 2.36/3.89 ms. These short measurements use VulkanRenderer at scale 2 on a four-CPU worker; they neither establish long-session memory behavior nor reproduce the client's hardware rendering environment.

Automated native X11/Flatpak checks are separate from manual client GNOME/Wayland acceptance. No physical touch-device check is claimed. The word-study harness suppresses automatic Library loading during window construction; its reading/selection/word-study methods are the packaged implementation.

NFC's overlapping/interleaved Sirach structures (#153) remain under investigation and are not claimed delivered. NBS installation is client-confirmed, separately from full content acceptance. Unsupported exact Darby/NBS verse mapping remains unavailable; independent reading is identified explicitly. Physical touch-device and client-desktop acceptance are separate from automated X11 checks.

The BDS Mark 11:29–30 crash correction, Original text naming complement and cancelled notification-feature cleanup were delivered in alpha.21; they are retained here, not counted as new alpha.22 changes. Implementation issues remain OPEN for client validation.

## Install or update

Install [Bible.flatpakref](https://icfmp.github.io/Bible/alpha/Bible.flatpakref), or run `flatpak update io.github.icfmp.Bible//alpha`. The signed continuous channel can later serve a newer verified application; the source/tag receipt above identifies this numbered release exactly.

## Issue coverage

| Issue | Delivered scope and checked behavior |
| --- | --- |
| #150 | Integration verification of existing direct yellow/green/blue actions, repeated same-color application, retained native selection and absence of Compare in the selection toolbar. |
| #165 | Temporary native success, cleared footer/progress, correct installed row after reopen, and no completion toast intercepting the next resource action. |
| #166 | Real reference/topic updates from the retained old indexes to checked snapshots, correct generation/current state and exact usable offline restart; failed-update preservation is covered by focused validation tests. |
| #167 | Independent reviewed vocabulary/synonym data and index publication, with explicit partial coverage and English fallback. |
| #168 | Physical press/release and native text-drag completion retain actual selection/source context; no native gesture reset, copy disable, fabricated selection or polling. The prior touch path remains but was not tested with a physical touch device. |
| #169 | Native header search and Ctrl+F open Text/Topics; passage navigation remains separate. Narrow adaptive-menu dismissal restores focus/accelerators. |
| #171 | Common requested-chapter fallback and resource-qualified independent positions; six directional cases across three resource pairs, source changes and offline restart. Exact unsupported mappings remain unavailable. |
| #172 | Both selectors fill their own pane; caption centering and arrow placement checked in both themes, normal/narrow windows and study open/closed. |

The fresh Darby module declares and effectively uses German; this is not silently identified with the client's unspecified Luther build. The additional stale-heading variant was not reproduced in the fresh baseline. Corrected Darby/NBS opening shows Genesis 11 in both documents/headings, explicitly independent; moving the primary to Genesis 12 preserves the independent Genesis 11 comparison and its actual verse position across restart.

Implementation issues remain OPEN. Only the client marks Done. Project 5 access was rechecked and remains `Resource not accessible by integration`; the required manual status for these delivered scopes is In validation. NFC #153 remains In progress with no complete lossless-installation claim. The #151 crash correction, #152 naming complement and #28 cancellation cleanup were already delivered in alpha.21 and remain available.
