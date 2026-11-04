# Immersion cleanup and native original-text focus stability

Related to #28, #151 and #152. The current descriptions and every comment were read before implementation; the client's cancellation and naming decisions supersede earlier guidance. This is implementation/review evidence, not yet a completed application delivery.

## Demonstrated crash and focused correction

The unmodified installed Flatpak at application source `fcfd908857c1c36e1ef0f371849e1a20a62fbeca` segfaulted in [native probe41828429200](https://github.com/icfmp/Bible/actions/runs/41828429200): real mouse selection of BDS Mark11:29–30, the word-study action, a passage choice, then an original-word button. Local GTK4.18.6/Cairo survived the extended flow but emitted widget ancestry criticals. Local success alone did not establish a fix.

A second installed run [41829258086](https://github.com/icfmp/Bible/actions/runs/41829258086), using the matching SDK debugger only to collect a stack, located the main-thread fault in `gtk_widget_is_ancestor → gtk_label_grab_focus → gtk_label_focus → gtk_widget_focus_move → gtk_window_focus → after_paint`. The simultaneous occurrence-query worker was not the crashing thread. [GTK4.20.4's gtk_label_grab_focus](https://github.com/GNOME/gtk/blob/4.20.4/gtk/gtklabel.c) retains a raw previous-focus pointer across the parent focus transfer before checking ancestry. Replacing dynamic selectable content after its focus widget was unparented exposes that lifetime boundary.

The shared WordStudy content-removal path now moves focus to the stable Close button BEFORE unparenting the focused child or one of its ancestors. Both whole-content replacement and async loading-status removal use it. This covers passage choices, original words, lexical details and further lookups through the same lifecycle. It preserves selectable/copyable text and metadata; it adds no polling, delayed content retention, renderer change or blanket exception suppression. Close/reopen generation guards and worker cancellation remain intact. Other place/reference surfaces do not use this dynamic-content container and are not changed speculatively.

The visible selection action, context actions, dialog heading/title, tooltip/accessibility name and unavailable state use **Original text / Texte original**. Existing verified lexical data, passage choices and honest unaligned/missing-data explanations remain available. The entry point is not a claim of translated-word alignment.

The current issue/comments describe the client's video by filename without a downloadable attachment URL. Tests exercise the supplied concrete passage/action sequence; inspection of the original recording at full cadence remains unavailable in this environment.

## Abandoned notification feature

The immersion banner, its callbacks/session flag, preference helper, unused localized strings and dedicated investigation document are removed. On load only the exclusively owned legacy `immersion-help.json` is retired; an unreadable/read-only legacy entry does not prevent startup. No other profile path is removed or reset. Bible/commentary immersion and their native controls remain.

Current requirements/roadmap/guide and handoff references reflect cancellation. Historical reports retain their original evidence with an explicit superseding cancellation note. A shallow read of the current project wiki found no feature references. The final source scan distinguishes unrelated GTK property notifications and Shumate's load-notification patch; no abandoned notification probe/dependency or extra sandbox permission existed to remove.

## Verification state

- Local GTK:16 immersion/pagination tests and8 word-study/metadata tests passed, including restarting an old profile, resource digests, notes, highlight and typography, and focus relocation before nested selectable content is unparented.
- Exact packaged native regression rerun, full required CI, before/after captures, signed deployment and retained-profile update remain required before publication. No completed delivery or client GNOME/Wayland acceptance is claimed here.
- #150 and #168's repeated real selection checks are coordinated through the native probe but are not declared fixed by this focus change.
