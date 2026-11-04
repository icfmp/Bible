# Shared comparison context and verified alignment boundaries

Related to #171. Its current description and all comments were read; #129 and #137 and their comments were consulted for boundary/genericity coordination. This does not start either audit, claim independent review or expand their report-only authorization.

## Demonstrated causes and source facts

The unmodified application at `d7290ee50cb61c5e9e79b20d7a80f4768327272f` opens Genesis 1 when creating an unsupported cross-system comparison from Genesis 11. Actual Darby/NBS developer-profile probes reproduce this in both directions: primary `Gen.11.1`, comparison state/document/visible reference `Gen.1.1`/`Gen.1`/`Gen.1.1`. The common `ReadingTab.refresh_comparison` failure path used `reader.first_reference()` despite the requested numbered chapter being present in both target inventories. A structural synthetic regression fails before the correction with `Gen.1.1 != Gen.19.1`.

The freshly downloaded CrossWire FreJND (2024) declares **German**, and its effective native module key confirms German. The already fully verified NBS 104 module declares/effectively uses **YouVersion104**, registered from its digest-checked source index. Setting each module's native key to Genesis 11:1 retains that system and actual reference. The client's reported **Luther** may concern another installed module/version; the unknown client build is not silently equated with the fresh German resource.

German has an available verified supplementary mapping table; the exact source-specific NBS index has no verified cross-system mapping. Its provider `vrs=org` label and printed verse numbers do not establish identity correspondence. No such mapping is invented. In the current fresh reproduction, the wrong comparison chapter is headed Genesis 1 consistently; the client's additional stale Genesis 11 heading is not reproduced and is not falsely claimed measured.

## Targeted shared correction

An explicit comparison opening now reuses the same inventory-driven `available_chapter` rule as explicit source switching. It opens the requested printed chapter where that target actually contains entries, while retaining **Automatic following unavailable. Reading independently.** Exact verse following still requires the existing SWORD/verified-table resolver. A target without that chapter reports its absence and keeps the primary passage, rather than opening an unrelated first chapter.

Existing independent positions remain resource-qualified and are restored from an optional bounded `comparison_position` session field. Old version-1 sessions need no rewrite on load; existing fields, missing-resource identities and atomic save behavior remain. A stale position from a different resource cannot be applied to a newly selected comparison. Ending comparison clears only its owned position. Opening it again cannot reuse a hidden prior document as if it were still active.

The actual comparison reference already sampled during an input frame records the independent position; no new geometry query, polling, worker or timer is added. Engine diagnostics remain available in the banner tooltip. Source text, source indexes, canon/mapping tables, annotations and resource metadata are unchanged. Commentary following and reference-result navigation continue through the exact resolver; printed chapter availability is not substituted into those semantic mappings.

## Checks performed

Eighteen focused comparison/session/resolver tests pass. A broader 54-test local suite passes across commentary access, verified mapping/oracle cases, source-specific indexes, comparison rows/following, study-reference/search navigation, sessions and annotations. It includes split/merged/missing mapping behavior and the existing Psalm-numbering difference. These counts overlap and are not cumulative.

Actual local GTK 4.18.6/Cairo before/after probes with real Darby and the verified NBS module now show `Gen.11.1`, document `Gen.11` and rendered heading **Genèse 11** in both directions, with independent following explicitly retained. The NBS GUI fixture reuses its fully verified module; this is not a fresh in-UI NBS download claim. No module file is modified.

| Real source/target pair | Reference | Verified outcome |
| --- | --- | --- |
| BDS → LSG (YouVersion) | Genesis 11:3 | Exact Genesis 11:3 |
| LSG → BDS (YouVersion) | Genesis 11:3 | Exact Genesis 11:3 |
| KJV → Segond (CrossWire) | Psalm 3:1 | Exact Psalm 3:2 |
| Segond → KJV (CrossWire) | Psalm 3:2 | Exact Psalm 3:1 |
| Darby → NBS | Genesis 11:1 | Target chapter 11 available; exact verse alignment unsupported |
| NBS → Darby | Genesis 11:1 | Target chapter 11 available; exact verse alignment unsupported |

The synthetic shared-path checks cover source replacement, qualified independent-position restoration, ending/reopening comparison, unavailable chapters and unchanged primary reading. Diff inspection finds no new production condition keyed to translation/provider ID, language or example passage. The source/target names above belong to probes only.

## Remaining verification and limitations

Full CI, integrated source checks, installed Flatpak native mouse/following/source-switch/restored-tab/offline matrix, light/dark/narrow captures, signed delivery/update and numbered alpha remain pending. NBS exact cross-system following remains an explicit capability gap; no claim is made to establish a new mapping for it. The client's original stale-heading build and full video cadence are unavailable. Local X11/Cairo tests are separate from Flatpak/GL and client GNOME/Wayland acceptance. Keep #171 open for client validation.
