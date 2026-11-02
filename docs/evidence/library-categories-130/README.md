# Shared Library categories — issue 130

Bibles, Commentaries and Study tools share the same grouped category control,
window, cached metadata and installation services. Dataset downloads retain their
captured task when the category changes. Search text is remembered per category;
Bible/commentary language and provider filters are retained, while the local
multilingual study catalogue does not inherit those filters or provider errors.
Study progress/success uses the localized resource description, including STEP.
No new dataset, storage migration or content revision is included.

Local native tests cover category/search/filter restoration, contextual reveal
without installation, cancellation/failure/retry fixtures and retained transfer
identity. A real places/map download installed the five pinned files and indexed
1,342 places, 1,596 modern locations and 442 bibliographic sources while switching
categories. This is a real source GTK test; installed Flatpak validation remains
part of the batch delivery.

A separate live cross-reference download was safely rejected: the provider now
returns ZIP SHA-256 `045f1c5db8a331e3d2a185b44646b6ff220b72dd54669fd1976270a7351afcf4`
(1,983,632 bytes, archive timestamp 26 October 2026), while the reviewed source pin
is `5f61f4525156b7c7b8f7ae07e3a4225038cf4b60def39247df8b92916e14c56f`.
This is an upstream content-review limitation, not an installed-data migration.
The checksum check remains enabled and no installed index was overwritten.
The topics archive likewise currently differs from its reviewed pin: observed
SHA-256 `b20499362abe0c71c45bb18cca1dcf386b8caf50381e6246cc531fa7a69aa2cf`
(418,746 bytes), pinned
`47bc1cb1defe5b8f0f65ca9966cd99ff151b7f22cab18ef9c99eda6a244df7cc`.
Fresh reference/topic acquisitions remain blocked pending a separate source review.
The rendering checks reuse attributed, previously verified installed indices;
they do not substitute those fixtures into normal application downloads.
Do not describe either failed acquisition as a successful installation.

The issue remains open for client validation. Numbered release 87 remains paused.
