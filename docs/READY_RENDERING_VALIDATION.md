# Ready-batch renderer stabilization

Related to #185 and the reading/notes Ready delivery (#203). This is a native
GTK/GSK renderer selection, not a replacement text renderer or a data migration.

## Reproduction before the change

The signed application at `7fa4326fc5a51f722e7a38a190ac17ee22075949`
was compared with immutable alpha.24 on the same retained developer profile:
seven real installed resources, parallel reading and Study, Psalms 119:1,
1180 by 780 logical pixels, scale 2, GTK 4.20.4, composited X11. Each cycle
contains eight seconds of physical scrollbar input with direction changes,
followed by six seconds without input. The client profile was not accessed.

With the runner's default software Vulkan renderer, alpha.24 stayed around
461–463 MiB RSS after warm-up. The new version rose from 462 to 554 MiB across
12 cycles. PSS and anonymous memory also grew. The menu was hidden, its backdrop
released, and its placement callback stopped. No late position adjustments were
observed beyond 500 ms after input stopped.

Actual cProfile/tracemalloc samples showed roughly 19 MiB of live Python memory
in both versions. A separate lightweight weak-reference observer found 30 live
source-note buttons, zero retired buttons, zero buttons created during the
gesture, and no document rebuild during scrolling. Diagnostic collection after
measurement did not reduce RSS. Removing label attributes, rounded marker
clipping/shadows, or changing the Study background did not fix the growth.
These negative controls rule out those proposed application fixes; they do not
identify an exact line inside the Vulkan driver or GTK implementation.

## Paired renderer measurements

The same signed source, retained data, settings and input were then measured
with GTK/GSK OpenGL, without altering markers or their functionality. A matched
24-cycle run measured:

| RSS | alpha.24 OpenGL | Ready source OpenGL |
| --- | --- | --- |
| Startup | 358.84 MiB | 325.59 MiB |
| After cycle 1 | 422.32 MiB | 367.34 MiB |
| After cycle 12 | 427.46 MiB | 381.07 MiB |
| After cycle 24 | 432.20 MiB | 385.94 MiB |

The updated source's last eight cycles span 385.07–385.94 MiB. All 24 stops
had zero position adjustments later than 500 ms. Software OpenGL used about
97–99% of one logical CPU while scrolling, compared with about 120–121% for
software Vulkan in the 12-cycle sample. The renderer also painted fewer frames
on this runner; CPU percentages are not a claim of equal-throughput speedup.
This is evidence of bounded behavior in the observed interval, not a guarantee
of constant memory for arbitrary sessions or hardware.

Evidence: [Vulkan 12 cycles](https://github.com/icfmp/Bible/actions/runs/42268275894),
[allocation profile](https://github.com/icfmp/Bible/actions/runs/42270515359),
[widget-lifetime observer](https://github.com/icfmp/Bible/actions/runs/42276130078),
[OpenGL 24 cycles](https://github.com/icfmp/Bible/actions/runs/42277550193).

## Focused mitigation and limits

Select `GSK_RENDERER=gl` by default before GTK initialization on Linux. Preserve
an explicit environment override, including Vulkan or Cairo used for diagnostics.
Other operating systems retain GTK's normal selection. No user preference is
written; text, source notes, popovers, selection effects and stored data are
unchanged. GTK still owns rendering, cache lifetime and invalidation.

This avoids the measured Vulkan path rather than claiming an upstream Vulkan
memory bug has been repaired. The final exact-source signed package must pass
ordinary CI and a retained-profile update with the default renderer, prolonged
scrolling, parallel/Study checks and French/English native acceptance checks
before the numbered release. Those final receipts belong to the release report.
Client GNOME/Wayland and hardware GPUs remain separate acceptance limits.
