# Notification cleanup and original-text crash stabilization

Related to #28, #151 and the naming complement in #152. Issues remain open for client validation.

Application source is `d7290ee50cb61c5e9e79b20d7a80f4768327272f` ([PR #173](https://github.com/icfmp/Bible/pull/173)). Its application tree exactly matches tested candidate `ba7bc0249fef9e38c2704fdf58cde3cbf6de1bad`. [Main source/Flatpak CI](https://github.com/icfmp/Bible/actions/runs/41871553894) passed. Signed publication and retained-profile update verification are tracked separately below; a merged PR alone is not a delivered alpha.

## Implemented and demonstrated

- #151: the unmodified previous installed build crashed with SIGSEGV (exit 139) during BDS Mark 11:29–30 original-word selection in [native reproduction](https://github.com/icfmp/Bible/actions/runs/41828429200). A separate [matching-SDK debugger run](https://github.com/icfmp/Bible/actions/runs/41829258086) locates the crashing main-thread path in `gtk_widget_is_ancestor → gtk_label_grab_focus → gtk_label_focus → gtk_window_focus → after_paint`. The focused selectable child was being unparented while GTK focus traversal retained it. The targeted correction moves focus to the stable Close button before removing a focused descendant; it retains selectable text, lexical content and async work.
- #152: the selection/context action and original-language surface now use **Texte original / Original text**. No change to word-source data or passage identity.
- #28: remove the cancelled manual Do Not Disturb banner, its exclusively owned helper/state and current research instructions. Startup retires only the obsolete `immersion-help.json`; unrelated preferences and data remain intact.

The [exact installed normal-runtime probe](https://github.com/icfmp/Bible/actions/runs/41862505462) used `/app/` imports, GTK 4.20.4 and GLRenderer without SDK/debugger. The harness suppresses automatic Library catalogue refresh during window construction; installed reading, selection and word-study implementations are unchanged. It completed 12 real BDS Mark 11:29–30 word-choice cycles (study panel alternately open/closed) and 40 mouse selections, with no crash or captured Python exception. Captured images show the actual lexical surface, not a mockup. This is developer automation, not client-desktop acceptance.

Local focused lifecycle/immersion tests pass. Native local GTK 4.18.6 previously produced repeated ancestry criticals in the same word flow; the fixed flow completes without those criticals. Local Cairo findings are separate from the installed Flatpak/GL result. A remaining nonfatal snapshot-allocation warning is not presented as a crash fix for every GTK warning.

## Original GTK before/after validation

The [baseline capture run](https://github.com/icfmp/Bible/actions/runs/41861406904) and [fixed probe](https://github.com/icfmp/Bible/actions/runs/41862505462) capture Bible/commentary immersion in light/dark at 1200 and 360 pixels. The original PNGs and bounded recordings remain in those workflow artifacts and are available privately to the client. No screenshots, video, JSON artifacts, profile or corpus are copied into this public evidence branch.

Both runs cover eight combinations: Bible/commentary × light/dark × 1200/360 pixels. The fixed run also records BDS Mark 11:29 and 11:30 original-language surfaces and native repeated selection. Workflow artifact retention limits apply; images have not been mirrored publicly.

The old hint appears only on the first baseline light/1200/Bible entry because that session then considers the hint seen. Later baseline frames already hide it; they are layout/readability controls, not eight separate visible-banner removals. The fixed version has no hint/banner widget in any case.

The first 40-selection protocol explicitly dismissed the old toolbar before each selection. A subsequent [baseline run](https://github.com/icfmp/Bible/actions/runs/41866643077) kept it between 120 genuine replacement drags in both directions: zero absent toolbars, collapsed selections or captured exceptions. This does **not** reproduce or close intermittent #168, and no selection-specific fix is claimed here.

## Publication state

The [signed publication 41909742241, attempt 2](https://github.com/icfmp/Bible/actions/runs/41909742241) and [full retained-profile update 41909748008, attempt 2](https://github.com/icfmp/Bible/actions/runs/41909748008) pass. Packaging revision is `41909742241-1`; actual installed OSTree commit is `31cc1433d9f9967c43ec5f36d981a0662f5a9ac0bd2edffa56a1b0501d192ecb`. Signing identity remains `47A17230403EA4953745E6E020EB9FFCCECAFD8F`, with the same `bible-alpha` remote and alpha ref. Source archive SHA-256 is `bdf9a84fcac405c67acf847d10fe7dd856ff335505043e03159d9ea001dc603a`; bundle SHA-256 is `98f73f1f4d49fe7826097a8f4995938ece40f419894e6242e992f3b1edb5f3bc`.

The update starts from actual signed alpha.20 (`63bee99a…`) and retains the same disposable profile throughout. Six real translations/commentaries, four study datasets, all 55 module-file digests, note/highlight and reading preferences are preserved; only the obsolete notification-hint state is retired. Four combined scrollbar cycles and two wheel cycles each in single/comparison/study modes report no adjustment later than 500 ms after stop. Hidden backdrop is released and placement tick is zero. This is update/data validation, not a new performance-regression fix.

On that cloud VulkanRenderer/scale-2 worker, combined startup/final RSS is 442.6/476.1 MiB before and 431.0/465.9 MiB after; scroll CPU is 116–119% versus 119–121% of one logical core. These short-run renderer-specific measurements do not establish a CPU improvement or long-session/client-hardware memory behavior. The first combined scroll/paint is 3.27/5.75 ms before and 2.97/4.96 ms after.

Earlier publication attempts `41876117598`/`41878801711` failed on Pages timeout/cancellation; `41906372662` failed because HTTPS never served its expected second revision. Reviewed [PR #176](https://github.com/icfmp/Bible/pull/176) replaces the duplicate deployment with one deployment and a retained public client; actual signed Git-restoration CI `41908868424` passes. The infrastructure merge `82e3a46…` reuses the exact verified application artifact/source above, with no application rebuild. Initial retry failures downloading STEP received HTTP 503/timeout; the successful attempt completes all preparation/update/data guards. Failed or cancelled attempts are not counted as update proof.

The matching numbered release is [alpha.21](https://github.com/icfmp/Bible/releases/tag/0.1.0-alpha.21). No published tag was moved. No client profile was accessed or reset. Client checks: open BDS Mark 11:29–30 and use Original text repeatedly; enter Bible/commentary immersion in a small light/dark window; check existing translations, annotations and reading preferences after updating. These checks do not claim #168 or NFC conversion fixed.

The original client video was referenced by filename without an accessible download URL. Tests reproduce the supplied concrete passage/action flow, not the exact unknown video cadence. Xvfb/X11 and software GL on a cloud runner do not establish GNOME/Wayland, hardware-driver, screen-reader or client-desktop acceptance.
