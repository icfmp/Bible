# GNOME Software packaging diagnosis (#212)

The verified alpha26 is source `6faab9201d4fdf496ccb931c62b1cf9aa9e7f233`,
CI run `42337813257`, signed deployment `42339636693`. The installed alpha ref
was `d2f999a4bb057de100984fe96ffbb36aeac07c308554b8084b2d96dac6932d0b`.
Its desktop launcher and actual application icons existed, but `/app/share/metainfo`
and `/app/share/appdata` were empty. No application AppStream component was shipped.

A disposable Ubuntu 24.04 runner installed this exact signed alpha using the
standard user Flatpak installation and GNOME Software 46.0. A second comparison
opened its exact CI bundle, artifact `13561440844`, whose ZIP SHA-256 was verified
as `ca304eb97fd3e08dfae861a44f32f321916c0dac47e223e0df531ee621e261d0`.
Diagnostic workflow `42355958206` (source `ce7edc90d5b0318847829036247f6a2162a59ad9`)
completed successfully, artifact `13566954231`, ZIP SHA-256
`2e7fc6fa3301660710d1b09c57d26f90ec5cc010155e597286e81051f168a194`.

Observed behavior, not merely XML inspection:

- Requests for either application ID or desktop ID left Software on Explore;
  no Bible details page could be resolved from the remote's missing component.
- Opening the actual local bundle produced a details page named
  `io.github.icfmp.Bible`, with the generic gear icon, no screenshots, and
  “A flatpak application”. Software logged **“no appstream metadata in file”**.
- The local-file page offers Install even with the alpha branch installed;
  that master-branch bundle is a distinct installation source. No install button
  was activated during this comparison and no existing application was replaced.

The candidate adds a native AppStream component matching the desktop ID, GPL
license, FR/EN summary/description, developer, source/help links, development
release history and a publicly hosted real-application screenshot. The existing
manifest installs it under `/app/share/metainfo`. The existing Flatpak export and
signed repository updater can then produce AppStream data; their actual output
and Software's details page must still be checked with the candidate build.

The candidate alpha27 metadata is prospective until its exact source passes CI,
signed deployment, retained-profile update verification and numbered publication.
The screenshots must be refreshed to the final tested native interface before
release. A source-file check, a green screenshot step, or Software's Explore page
does not prove that the final application's details page works.
