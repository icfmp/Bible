# Installation and updates

Bible currently offers an **alpha release for Linux x86_64** through Flatpak. It is not yet published on Flathub.

## Install

1. [Set up Flatpak](https://flatpak.org/setup/) if needed.
2. Open the [Bible alpha installer](https://icfmp.github.io/Bible/alpha/Bible.flatpakref) with your software manager.

Alternatively, in a terminal:

```sh
flatpak install https://icfmp.github.io/Bible/alpha/Bible.flatpakref
flatpak run io.github.icfmp.Bible//alpha
```

The alpha comes from the project's signed repository on GitHub Pages. The GNOME runtime is provided through Flathub.

**Bible translations are downloaded separately.** The application does not include Bible texts by default. After installation, open Library to choose and download the translations and study resources you want.

## Update

Use your software manager, or run:

```sh
flatpak update io.github.icfmp.Bible//alpha
```

Automatic updates depend on your software manager settings.

## Uninstall

You can remove the alpha installation through your software manager or by running:

```sh
flatpak uninstall io.github.icfmp.Bible//alpha
```

A normal uninstall does not deliberately remove Bible's application data. **Do not use `--delete-data`** if you want to preserve your notes, settings and downloaded resources. Back up important personal notes before making major installation changes.

## Upgrading from an older bundle

Read the [alpha channel migration guide](https://github.com/icfmp/Bible/blob/main/docs/CANAL_ALPHA_FLATPAK.md) before replacing an earlier standalone build. Preserve your existing notes and downloaded resources.

If installation fails, see [Troubleshooting](Troubleshooting).
