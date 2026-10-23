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

## Update

Use your software manager, or run:

```sh
flatpak update io.github.icfmp.Bible//alpha
```

Automatic updates depend on your software manager settings.

## Upgrading from an older bundle

Read the [alpha channel migration guide](https://github.com/icfmp/Bible/blob/main/docs/CANAL_ALPHA_FLATPAK.md) before replacing an earlier standalone build. Preserve your existing notes and downloaded resources.

If installation fails, see [Troubleshooting](Troubleshooting).
