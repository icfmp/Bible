# Alpha 34 stability evidence

Application source: `8beb2b0fc4fe5c1a58568baeb8d53e2310fe9811`, PR [#316](https://github.com/icfmp/Bible/pull/316).

[Main checks](https://github.com/icfmp/Bible/actions/runs/44298089499) · [Signed publication](https://github.com/icfmp/Bible/actions/runs/44303259466) · [Installed update receipt](installed-update.json).

The installed commit is `8a3e0b238ce5c48d8d624013d5f7b39d2f5d8b5d7ad45ad3a8e39f3dbbc763a0`. All 116 installed Python files match that source. The update retained all 159 checked files across three existing validation profiles. Signature verification remained enabled, using the sole trusted alpha key `47A17230403EA4953745E6E020EB9FFCCECAFD8F`.

- #305: [the removed commentary is unavailable, with saved context retained](305-removed-fr.png). Actual installed MHCC removal followed by three Wesley/None cycles completed without a crash; the test note survived.
- #252: [eBible on the left](252-ebible-left-fr.png), [Preview on the left](252-preview-left-fr.png). Twelve installed GTK openings covered both pane orders across Ecclesiastes 11/12, Genesis 11/12 and John 2/3. These original ZIPs were accessed through an explicit read-only diagnostic adapter; this is not a claim that their upstream catalogue/package mismatch was accepted by the installer. Every indexed verse remained present, without false absence rows or an asserted equivalence.
- #267: [actual installed mouse-wheel evidence](267-installed-gestures.json) covers Bible → commentary and commentary → Bible for MHCC's disjoint Matthew 13:24–30 / 36–43 section. The intervening 31–35 section stays independent; the linked body renders once. Real module/testament introductions remain readable. Verified real BDS/KJV Bible pairs also retained shared alignment and wheel following in both directions.
- #308: [before](308-before-fr.png), [installed after](308-installed-fr.png). The before capture uses native GTK at commit `8b2d0fc` with the previous heading renderer; the after capture uses the actual updated installed application. The original source range label remains visible, and source/copy/body hashes of five checked real entries are unchanged.

The eBible archive exposes 14 native Ecclesiastes 12 entries; Preview exposes 16. The application cannot invent the missing authorial addresses. Native SWORD numbering declarations without edition-level evidence use independent Bible panes. Unrecognized or ambiguous source labels retain the generated context. These are cloud X11/software-GL checks, supplemented by FR/EN development and packaged CI; the client's desktop acceptance remains separate. Issues remain open.

This commit publishes documentation and captures only. It does not change, rebuild or republish the application or any resource package.
