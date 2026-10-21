# Combined delivery: native highlight layout regression

The final installed signed alpha `1e7613d`, revision `39669216171-2`, passed
real MHC progressive-boundary/end, both synchronization directions and
notes/session reopen checks. The subsequent real-resource palette matrix
reproducibly aborted on GTK 4.20.4 with `gtk_text_view_validate_onscreen` /
`priv->onscreen_validated`. Delivery was held despite green CI/publication.

Faulthandler, attached GDB and paint callback stacks identify a distinct
highlight integration problem: while GTK validates the primary Bible's layout,
its adjustment notification refreshes navigation and rebuilds comparison.
That rebuild calls the shared highlight painter on both views. Unconditionally
resetting tag properties/removing tags invalidates the unchanged primary view
inside GTK's validation. An isolated diagnostic with personal painting omitted
passes the same matrix, confirming the repaint path; this was diagnostic only,
not the shipped fix and not a change to synchronization. Original evidence:
[evidence/highlight-layout-original-trace.txt](evidence/highlight-layout-original-trace.txt).

The fix makes personal painting idempotent for an unchanged buffer revision,
reference ranges, colors, visibility and palette. Actual text replacements
invalidate the state even if the characters are identical. Tag properties are
updated only when their style changes. New marks, hide/show, restored records,
new documents and high contrast still repaint normally. No data format, source
text, reference alignment, signed channel or key changes.

Review also found a stale `BiblePages` constructor in the immersive passage
navigation callback after the switch to `BibleBookPages`. Correcting it keeps
navigation on the continuous-book source; a focused navigation test covers it.

Five affected tests pass. The explicit source candidate in the same GNOME 49 /
GTK 4.20.4 Flatpak runtime passes all 16 surface states, including every palette,
emulated high contrast, study open/closed, resize, unavailable/restored content,
selection, equal widths and anchor retention. This source-overlay diagnostic
is not presented as a final installed-package check. All 159 full local tests pass. A new CI/publication/package verification follows
before availability is reported.

## Final installed-package confirmation

Source **6560dc4**, main CI **39673122687** and publication **39674239853** are
green. Revision **39674239853-2** is actually available and installed through the
existing signed channel. The exact previously failing /app pixel matrix passes
all 16 states; 28 affected packaged unit tests plus one isolated native click test
pass. Real highlights/backup, selection actions, continuous books, MHC true end,
both synchronization directions and notes/session reopen pass. Final public
provenance, bundle digest, actual profile preservation, GTK captures and limits
are recorded in [the delivery report](PENDING_DELIVERIES_2026_10_21.md).
