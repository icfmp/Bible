# Reader polish delivery evidence — PR #91

[Download all 149 actual GTK captures, the before/after gallery and verification reports](reader-polish-delivery.zip?raw=true).
Unzip the archive and open `reader-polish-91/galerie.html`; read `report.md` for provenance.

Merged application source: `044d81ea09b0bbd4eaf1b0f4b88fa24d1f557691`.
[PR #91](https://github.com/icfmp/Bible/pull/91) ·
[Main CI](https://github.com/icfmp/Bible/actions/runs/39979270368) ·
[Signed alpha publication and update verification](https://github.com/icfmp/Bible/actions/runs/39980683771).

One application batch is available on the existing signed alpha. Numbered release
#87 remains paused; no numbered prerelease was created. #67 is icon-only;
the existing action order is retained and #71/#75 remain outside this batch.

The archive includes French/English, light/dark, 70 matched before/after pairs,
small windows, study on/off, immersion, HiDPI, 150% system text and emulated
System/high-contrast notifications. These are unretouched GTK/Xvfb captures,
not manual GNOME/Wayland or specialist accessibility acceptance.

This evidence-only branch does not publish another alpha or require installing
a candidate. Update the existing app with `flatpak update io.github.icfmp.Bible//alpha`.
