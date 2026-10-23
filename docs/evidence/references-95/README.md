# Readable References (#95)

The right study panel keeps the same OpenBible data, score ordering, deduplication, resolver and shared preview. Rows now show complete mapped targets independently of excerpt limits, native separators and a three-line exact local Scripture preview. Scores are no longer displayed. A counted expansion action follows the initial five rows in the virtualized list, with a visible return action in expanded mode. Source/license links remain in the footer. No notes, highlights, settings or dataset format changes.

## Actual GTK evidence

Baseline: `1dc145882f9ba9e207315adc70147a2467c013fe`. French UI, same GTK scale 1, 1440 × 1000 Xvfb display, actual FreSegond1910/KJV resources and pinned OpenBible dataset. Preferred panel widths 360/430/560 px; system text enlargement emulates 150% via GTK DPI. Small windows are 360 × 700 px. Black outside a small window is the unchanged Xvfb desktop. High contrast uses the existing test-only libadwaita notification override, not a demonstrated GNOME portal connection.

| View | Before | After |
| --- | --- | --- |
| dark-acts-default | [PNG](before-dark-acts-default.png) | [PNG](after-dark-acts-default.png) |
| dark-acts-expanded | [PNG](before-dark-acts-expanded.png) | [PNG](after-dark-acts-expanded.png) |
| dark-acts-large-text | [PNG](before-dark-acts-large-text.png) | [PNG](after-dark-acts-large-text.png) |
| dark-acts-narrow | [PNG](before-dark-acts-narrow.png) | [PNG](after-dark-acts-narrow.png) |
| dark-acts-wide | [PNG](before-dark-acts-wide.png) | [PNG](after-dark-acts-wide.png) |
| dark-genesis-default | [PNG](before-dark-genesis-default.png) | [PNG](after-dark-genesis-default.png) |
| dark-genesis-expanded | [PNG](before-dark-genesis-expanded.png) | [PNG](after-dark-genesis-expanded.png) |
| dark-genesis-large-text | [PNG](before-dark-genesis-large-text.png) | [PNG](after-dark-genesis-large-text.png) |
| dark-genesis-narrow | [PNG](before-dark-genesis-narrow.png) | [PNG](after-dark-genesis-narrow.png) |
| dark-genesis-wide | [PNG](before-dark-genesis-wide.png) | [PNG](after-dark-genesis-wide.png) |
| dark-john-default | [PNG](before-dark-john-default.png) | [PNG](after-dark-john-default.png) |
| dark-john-expanded | [PNG](before-dark-john-expanded.png) | [PNG](after-dark-john-expanded.png) |
| dark-john-large-text | [PNG](before-dark-john-large-text.png) | [PNG](after-dark-john-large-text.png) |
| dark-john-narrow | [PNG](before-dark-john-narrow.png) | [PNG](after-dark-john-narrow.png) |
| dark-john-wide | [PNG](before-dark-john-wide.png) | [PNG](after-dark-john-wide.png) |
| dark-small-large-text | [PNG](before-dark-small-large-text.png) | [PNG](after-dark-small-large-text.png) |
| dark-small-window | [PNG](before-dark-small-window.png) | [PNG](after-dark-small-window.png) |
| high-contrast | [PNG](before-high-contrast.png) | [PNG](after-high-contrast.png) |
| light-acts-default | [PNG](before-light-acts-default.png) | [PNG](after-light-acts-default.png) |
| light-acts-expanded | [PNG](before-light-acts-expanded.png) | [PNG](after-light-acts-expanded.png) |
| light-acts-large-text | [PNG](before-light-acts-large-text.png) | [PNG](after-light-acts-large-text.png) |
| light-acts-narrow | [PNG](before-light-acts-narrow.png) | [PNG](after-light-acts-narrow.png) |
| light-acts-wide | [PNG](before-light-acts-wide.png) | [PNG](after-light-acts-wide.png) |
| light-genesis-default | [PNG](before-light-genesis-default.png) | [PNG](after-light-genesis-default.png) |
| light-genesis-expanded | [PNG](before-light-genesis-expanded.png) | [PNG](after-light-genesis-expanded.png) |
| light-genesis-large-text | [PNG](before-light-genesis-large-text.png) | [PNG](after-light-genesis-large-text.png) |
| light-genesis-narrow | [PNG](before-light-genesis-narrow.png) | [PNG](after-light-genesis-narrow.png) |
| light-genesis-wide | [PNG](before-light-genesis-wide.png) | [PNG](after-light-genesis-wide.png) |
| light-john-default | [PNG](before-light-john-default.png) | [PNG](after-light-john-default.png) |
| light-john-expanded | [PNG](before-light-john-expanded.png) | [PNG](after-light-john-expanded.png) |
| light-john-large-text | [PNG](before-light-john-large-text.png) | [PNG](after-light-john-large-text.png) |
| light-john-narrow | [PNG](before-light-john-narrow.png) | [PNG](after-light-john-narrow.png) |
| light-john-wide | [PNG](before-light-john-wide.png) | [PNG](after-light-john-wide.png) |
| light-small-large-text | [PNG](before-light-small-large-text.png) | [PNG](after-light-small-large-text.png) |
| light-small-window | [PNG](before-light-small-window.png) | [PNG](after-light-small-window.png) |

Acts 1:22 has 10 deduplicated targets, Genesis 1:1 has 62, and John 1:5 has 8. These counts come from the actual dataset. Screenshots show five initial rows and expanded lists, real single/multiple-verse targets, short/long book names, light/dark, narrow/wide and enlarged text. The source excerpt behavior already existed in #47; this delivery changes its presentation, not its provenance.

## Verification

- Native pointer/keyboard checks in French and English, including a container with networking disabled: preview without changing passage/history, Escape/outside dismissal, keyboard focus return, explicit current/new-tab actions, range aggregation, rapid source changes, exact FR/EN SWORD text, renumbered Psalms and split 3 John mappings, counted expansion/return, restart with the same offline index. Reports are included.
- Existing SQLite note, labels, highlight, explicit reading preferences, primary/comparison session and 36 installed-resource digests remain unchanged when opening the new References view.
- Regression cases cover complete range captions independently of truncated/missing text, real verse adjacency across chapter boundaries, exact count and source/history preservation during expansion/return. The whole application suite and installed Flatpak checks remain delivery gates.
- Validation is automated actual GTK/X11 under Xvfb; no manual client GNOME validation is claimed.

## Publication capacity

The new corresponding-source archive retains application sources, all compilation/install scripts, original icon sources, third-party sources, notices, tests and pinned dependency archives. Only historical GUI validation output is excluded from new archives. CI builds the installed Flatpak from this exact project tar layout. All existing source archives, their URLs/checksums and OSTree objects are retained unchanged. The entire prepared site must pass the bounded 999,000,000-byte guard, below the documented decimal 1 GB host limit. The measured source archive is 16,738,727 bytes before this implementation; the actual signed preparation is authoritative. This does not introduce an archival-retention policy; later batches still require the separate archival design documented in `CANAL_ALPHA_FLATPAK.md`.

Delivery uses the existing signed alpha after review, green CI and public installation/update verification. Numbered release #87 remains paused. No new numbered prerelease is authorized in this batch.
