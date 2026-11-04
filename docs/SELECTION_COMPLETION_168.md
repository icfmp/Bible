# Native selection completion

Related to #168. Its current description and all comments were read. The client's recording is local to their computer and has not been attached to this session; these observations come from independent native-input reproduction.

## Measured causes

The unmodified installed Flatpak at application source `d7290ee50cb61c5e9e79b20d7a80f4768327272f` reproduced 82 missing toolbars among 173 genuine nonempty mouse selections (GTK 4.20.4, OpenGL, automated X11). Selection bounds remained present, while the application still considered the gesture active. No Python exceptions were recorded. Some replacement attempts actually start GTK's native text COPY drag and retain the preceding selection; they must not be described as newly selected replacement ranges.

GTK TextView starts its own GdkDrag when a press inside an existing selection crosses the drag threshold. Its native grab can replace the release expected by the application's GestureClick. Public drag cancellation/completion signals, observed passively through DropControllerMotion, establish this path without disabling native copying. GTK 4.20.4 source was consulted to corroborate the observed signals.

A separate local trace demonstrated a physical primary-button release reaching the window while the application's GestureClick emitted no corresponding release. The five-character native selection was complete and nonempty. Depending exclusively on GestureClick completion therefore misses ordinary selections too.

## Targeted correction

Observe physical primary-button release in the reading window without claiming the event. Also observe completion of a local native TextBuffer drag belonging to a pending reading gesture. Both paths invoke the existing source/document/generation-checked callback and its single idle capture of the actual native selection. Reset only the application's observer after completion, so a stopped observer cannot suppress the next gesture.

Escape, scrolling, another click, source/tab changes and closing invalidate pending captures and release drag handlers. Escape during an unfinished selection must not reopen the bar on a later release. Native COPY, partial/multiverse bounds, existing colors, Copy/Note/Original text and keyboard selection remain supported. No polling, fabricated selection, provider/passage exception or new rendering/cache infrastructure is introduced.

## Verification and delivery boundary

Local GTK 4.18.6/Cairo checks pass repeated native text drags, Escape cancellation with unchanged selected text, actual COPY into an editable GTK TextView with exact source text preserved, subsequent selection, scrolling dismissal and passage action targets. The broader local matrix reaches 168 mouse cases without a missing or collapsed selection; its remaining keyboard and tab-transition cases are still being investigated. This is not a completed installed-package acceptance claim.

The initial installed baseline and its original recording are retained privately. Final candidate Flatpak verification, required integrated CI, signed update verification and a matching numbered alpha are pending. No client GNOME/Wayland acceptance is claimed. Keep the issue open for client validation.
