# Commentary scrolling crash (#51)

Reproduced offline in the actual public Flatpak: source `08a00d2`, revision
39632604890-2, GTK 4.20.4, FreSegond1910 4.0 (Segond) and MHC 2.2 (KJV).
The client's exact module pair is still unconfirmed. This is a demonstrated
reproduction of the reported application-exit behavior, not a claim that their
unreported input details are known.

Wheel scrolling near the loaded chunk's bottom, then native scrollbar bottom
presses/wheel, repeatedly crosses progressive-loading boundaries in Genesis.
The process exits with status 133 (SIGTRAP), not a Python exception, SWORD fault
or demonstrated resource exhaustion. GTK reports `Byte index 2693 is off the
end of the line`. Python points to `StudyPanel.anchor()` / pixel hit-testing;
GDB identifies `iter_set_from_byte_offset`, `gtk_text_iter_set_visible_line_index`,
`line_display_index_to_iter` and `gtk_text_layout_get_iter_at_pixel`.
[Original traces](evidence/commentary-51-original-trace.txt).

Verified OSIS emphasis decorations were rendered with GtkTextTag.invisible.
In this runtime, hit-testing wrapped text around those invisible inline ranges
can produce an invalid visible byte index. A controlled run of the ORIGINAL
packaged code omitting only that attribute survives 100 native scrolling rounds;
ordinary deferral alone does not resolve the failure. The fix renders precisely
those verified source decorations at zero font scale instead. They have no ink
or advance, while buffer characters/offsets and original SWORD strings remain
unchanged. Document.copy still omits precisely the generated decorations; literal
source asterisks and unknown conversions are preserved. No word or attribution
is removed and no synchronization is disabled.

Scroll bookkeeping is coalesced outside adjustment notifications, pending load/
scroll sources are tracked and cancelled on replacement/hide/close, and loading
at the true resource boundary is a no-op. Buffers remain capped at 20 entries;
no content is dropped from the resource or made inaccessible. The existing
reference-driven study coordinator is unchanged.

Validation tools:

- `tests.test_commentary_format`: zero advance without invisible-index ranges,
  wrapped non-ASCII hit-testing and original-character Copy.
- `tests.test_reading_sync`: deferred/coalesced bookkeeping, cancellation and
  terminal loading without rebuilding the same document, plus existing linked
  ranges, reverse following, history, focus, selection and persistence cases.
- `tools/check_commentary_boundaries.py TEST_PROFILE`: real offline native wheel,
  reverse/keyboard/long scrollbar drag, multiple loads and capped retention,
  both sync directions, tab/source/hide changes, actual final MHC entry and
  repeated scrolling at the real end, saved note/session reopen. Use only a
  disposable profile containing FreSegond1910 and MHC. `--require-packaged`
  asserts /app imports for final-package evidence; candidate overlays are
  explicitly identified and never claimed to be published code.

Candidate runtime: the corrected rendering survived 100 native rounds across
multiple loads/evictions, where the original aborts around rounds 24–27. Seven targeted
unit checks pass. The complete real-module boundary probe passes in the Flatpak
runtime with candidate source explicitly imported from /src, including actual
final entry Rev.22.20–21 (5,506 indexed sections), no further load at the end,
and note/session reopen. Release regression and final /app public delivery
evidence must be recorded before announcing availability. Xvfb is not manual GNOME,
physical trackpad, Wayland or accessibility acceptance. Keep #51 open for the
client's real GNOME retest. Pending PRs remain unmerged; #26 and OpenBible feature
work remain excluded.
