# Topic list, first activation and attribution — issues 146/147

The effective UI language already respects the saved override. The topic-name
helper incorrectly tested equality with `fr`; system variants such as `fr_FR`
therefore displayed all English labels. It now recognizes regional French
variants and uses the reviewed labels (including Inquiétude, the existing French
name for anxiety). A missing individual French label falls back to English;
source IDs and relationships are unchanged. Sorting uses the existing normalized
localized names with process collation, and search retains actual FR/EN aliases.

The previous 160 px choices scroller and permanently reserved empty result area
are replaced by two pages sharing the available picker area: all themes, then
passages for the explicitly selected theme. The native Back action restores the
choices. The overall picker is bounded to the window; topics have one active
results scroller, with source information accessible below it. No new language
preference or taxonomy is introduced.

The first-passage failure was reproduced with actual native pointer activation:
a fast topic choice started a query, then SearchEntry's delayed unchanged
search notification invalidated the resulting model and detached its preview.
Before: generation 8→9/12→13, preview closed; after: 7→7/10→10, preview and verified
target retained. A different query still invalidates it. This is a timing/lifetime
fix, not a zero-index special case or an automatic navigation change.

The ordinary footer now offers a discreet OpenBible.info information button.
Its accessible popup retains the source link, CC BY 4.0 license link, community
qualification and original transformation notice; credit is not removed.

The fixture below is the previously validated, actually installed 19 October
OpenBible dataset, retained from a disposable research profile on 25 October.
It contains 6,712 source topics / 71,358 relationships; the existing reviewed
50-topic vocabulary remains the only exposed subset. It contains no Bible text,
notes or preferences and is used only for reproducible validation. It is **not**
automatically installed for application users.

- Source: https://www.openbible.info/topics/
- License: https://creativecommons.org/licenses/by/4.0/
- Original archive SHA-256: `47bc1cb1defe5b8f0f65ca9966cd99ff151b7f22cab18ef9c99eda6a244df7cc`
- Decompressed SQLite SHA-256: `90db0daa43b1981a82d66481dc07211e395eba5ab56c15a8ee57cdb06d1ec209`
- Changes: validated local relationship index, exact-range deduplication/ranking;
  reviewed FR/EN display names are supplied by the application, independently
  of source IDs. No Scripture quotations are imported.

Local source tests and native captures are distinct from installed candidate and
client desktop acceptance. Both issues remain open; release 87 remains paused.

The enlarged-UI checks also reproduced a shared reference-preview failure:
GTK closed an oversized native popup immediately after showing it, including in
the References panel. A native outer scroller now lets GTK constrain the complete
preview while keeping its existing text and navigation actions accessible. This
is separate from the delayed-search race and preserves popup ownership/targets.
