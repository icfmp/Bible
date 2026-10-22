#!/bin/sh
set -eu
export XDG_DATA_HOME=/validation/xdg-data
export XDG_CACHE_HOME=/validation/xdg-cache
mkdir -p /validation /evidence/flatpak
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user --noninteractive flathub org.gnome.Platform//49 org.gnome.Sdk//49
flatpak list --user --columns=ref,origin,active > /evidence/flatpak/runtimes.txt
cd /validation
flatpak-builder --user --jobs=4 --state-dir=/validation/builder-cache --repo=/validation/repo --default-branch=recovery-24 /validation/build /src/packaging/io.github.icfmp.Bible.json
flatpak build-bundle /validation/repo /evidence/flatpak/Bible-recovery-24.flatpak io.github.icfmp.Bible recovery-24
sha256sum /evidence/flatpak/Bible-recovery-24.flatpak > /evidence/flatpak/SHA256SUMS
flatpak install --user --noninteractive /evidence/flatpak/Bible-recovery-24.flatpak
flatpak info --user io.github.icfmp.Bible//recovery-24 > /evidence/flatpak/installed-info.txt
cd /tmp
flatpak run --user --unshare=network --env=PYTHONPATH=/app/lib/bible-python --command=python3 io.github.icfmp.Bible//recovery-24 -c 'import inspect, Sword; from bible.ui import Window; from bible.book_stream import BookStream; print(inspect.getfile(Window)); print(inspect.getfile(BookStream)); print(Sword.VerseKey("John.1.1").getOSISRef())'
