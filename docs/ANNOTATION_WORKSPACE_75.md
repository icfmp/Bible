# Notes and highlights workspace (#75)

The top-left Bible / Notes selector opens the same personal annotations used by
Study → Notes. The global workspace combines filters, a virtualized list and an
editable detail. Filters collapse below desktop width; list/detail become
forward/back navigation at narrow widths. At very small reader widths the single
passage chooser moves beside the tabs. The Library remains in the main menu.

Each note UUID is one list record. Each existing `(versification, verse)`
highlight is one separate record. Two notes and a highlight at the same passage
therefore count as three items in All, two in Notes and one in Highlights.
Nothing is merged or created by rendering. Highlights have no stored dates and
appear in Bible order after dated notes when sorting by modification time.
Search matches full Markdown text, references, original sources and labels.
Book, existing label, color and date-order controls filter actual records.

Detail shows original source independently from the chosen local excerpt
translation. Existing verified reference mapping handles numbering differences;
unavailable resources or invalid/unmapped references retain an editable note
and an explanation, never substitute invented Scripture. Related records use
verified canonical overlap. Open in Bible preserves unrelated reading tabs and
returns to a new or already matching passage; Notes retains its local context.
Passage Notes' footer reveals its actual saved record in the global collection.
Shared citation previews remain distinct from navigation and note ownership.

Global editing coalesces saves for 600 ms on the GTK owner thread through the
existing atomic SQLite write and revision check. Normal record/space changes
and closing flush the draft. Failed writes keep the draft and the existing
Save / Discard / Keep editing guard. Pending labels require Enter, or explicit
Save/leave commits them. Only a completed write reports Saved. Conflicting edits
from another view are not silently overwritten. Deletion requires confirmation,
cancels pending saves and cannot recreate a deleted note. The passage editor
retains its established explicit-save behavior.

No schema, note identity, highlight file, resolver or backup format changes.
Existing note JSON backups and separate highlight JSON backups remain available;
backup first flushes the active global draft and blocks on a write failure.
This is not the complete personal-data backup project (#94), a synchronization
journal, cloud integration or crash-recovery guarantee.

## Developer verification and evidence

`tests.test_annotation_workspace` covers distinct records/counts and full-text
filters, autosave/fast switching/restart, real optimistic conflicts, failed writes,
delete safety, missing resources, unchanged legacy backup merging, footer reveal,
pending labels, and actual Luther/KJV numbering differences. The full GTK suite
uses a real GLib main loop while waiting, with unchanged deadlines: processing
only one event every 5 ms starved idle completions behind layout/frame events.

`python3 -m tools.check_annotation_workspace` performs actual X11 keyboard input,
editing, a SQLite read-only write failure, canceled departure, recovered save,
confirmation/cancel/removal and unchanged installed-resource hashes. The same
check and regression module run from the installed Flatpak in CI, with an import
assertion proving application code comes from `/app`.

Native before/after captures are in
[evidence/annotation-workspace-75](evidence/annotation-workspace-75/README.md).
Fixtures are disposable developer profiles with actual installed SWORD resources
and saved notes/highlights; synthetic edge modules are identified as test data.
Light/dark, 360 px windows, short windows, 150% text and high contrast are included.
Automated Xvfb evidence does not replace client desktop or specialist accessibility
acceptance. Large collections use virtualized rows; no unmeasured performance
claim is made for arbitrarily large stores or long reference ranges.

## Client checks

1. Open Notes, search a phrase inside an existing note, then change its text/labels;
   return to Bible and reopen Notes to confirm the saved edit.
2. Open a highlight, recolor it and inspect its related notes; removing a highlight
   after confirmation must keep those notes.
3. Try a small light/dark window, citation preview and Open in Bible; confirm the
   original reading tab and your existing data remain available.

Keep #75 open for client validation. Publication receipts belong in the PR.
Numbered prereleases remain paused at the client's explicit request (#87).
