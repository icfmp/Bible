# Recoverable offline changes

This backup preserves local commits fa2bfa0 and dd48c3f as format-patch mail and a cumulative patch inside Bible-reprise-patches.zip. BILAN.md records implementation, test evidence and remaining validation.

Exact base: 884591cd194bd7c07e3534a9b652c154a578dd34
Original head: dd48c3f56509079017c950582c49fc6cbe8304f6

Download the ZIP using GitHub's download button, extract it, and follow its README. The ZIP SHA-256 is ac998aa44bc191b55380e06e74d8ad93110d3ba7456192a2649bfdf2f6c909c2.

The cumulative.patch is also available separately and can be checked with git apply --check against the exact base. The original commit hashes are retained in the manifest; replaying patch mail may produce different committer metadata.

This backup branch contains recovery files over the original base. It is not the original feature branch and is not a published alpha. No signed channel, main branch, signing key or personal profile is modified. Source evidence remains 34 tests passed and five GTK/display skips. GTK and installed Flatpak validation remain pending.
