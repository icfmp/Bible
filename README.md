# Bible

<img src="packaging/icons/128x128/io.github.icfmp.Bible.png" alt="Bible application icon" width="128" height="128">

Read and study the Bible with a native GNOME application built with Python, GTK 4 and libadwaita.

- Download Bibles and commentaries from SWORD catalogues and read them offline.
- Open passages in separate tabs.
- Write passage notes with labels and search your notes.
- Customize typography, colors and fullscreen reading.
- Available in English and French.

**Alpha software:** expect bugs and interface changes. Linux x86_64 is currently supported. No Bible translation is bundled; each resource has its own terms of use.

## Install the alpha

With [Flatpak](https://flatpak.org/setup/) installed, open [**Install Bible**](https://icfmp.github.io/Bible/alpha/Bible.flatpakref) in your software manager, or run:

```sh
flatpak install https://icfmp.github.io/Bible/alpha/Bible.flatpakref
flatpak run io.github.icfmp.Bible//alpha
```

The alpha comes from the project's signed repository hosted on GitHub Pages. Bible is not currently published on Flathub; its GNOME runtime is supplied through Flathub.

### Update

Use your software manager or:

```sh
flatpak update io.github.icfmp.Bible//alpha
```

Automatic updates depend on your software manager's settings. If you previously installed a standalone bundle, see the [alpha channel guide](docs/CANAL_ALPHA_FLATPAK.md#passage-depuis-un-ancien-bundle).

## Try it

1. Open **Library** (`Ctrl+L`), choose a Bible, review its terms and download it. KJV is a useful first test.
2. Click the passage title in the Header Bar to choose a book and chapter.
3. Open another tab with `Ctrl+T`, or enter fullscreen reading with `F11`.
4. Download a commentary such as Clarke or MHCC, then press `F9` to show the study panel. Some combinations with different versification systems are still being fixed.
5. Create a passage note with `Ctrl+N`; find it again in **My notes** (`Ctrl+Shift+N`).
6. Disconnect from the network and restart Bible to check offline reading.

[Report a bug](https://github.com/icfmp/Bible/issues/new) with the steps to reproduce it, your Linux distribution, a screenshot if useful, and the installed build:

```sh
flatpak info io.github.icfmp.Bible//alpha
```

## Run from source

On Debian 13 or Ubuntu 24.04:

```sh
sudo apt install git python3 python3-gi python3-sword python3-babel iso-codes fonts-dejavu-core fonts-dejavu-extra gir1.2-gtk-4.0 gir1.2-adw-1
git clone https://github.com/icfmp/Bible.git
cd Bible
/usr/bin/python3 -m bible
```

Use the system Python so that the distribution's GTK and SWORD bindings are available. The interface follows the system language; use `LANGUAGE=fr /usr/bin/python3 -m bible` to select French.

### Run tests

```sh
/usr/bin/python3 tools/check_environment.py
/usr/bin/python3 -m unittest discover -v
```

GUI tests need a graphical session. For a headless Linux environment, install `xvfb` and `dbus-x11`, then run:

```sh
dbus-run-session -- xvfb-run -a /usr/bin/python3 -m unittest discover -v
```

To test an actual download and local reading (requires network access):

```sh
/usr/bin/python3 -m tools.check_crosswire
```

## Contributing

Bug reports, testing, translations and code contributions are welcome. Please use **English** for issues, pull requests, commit messages and contributor documentation. Read [AGENTS.md](AGENTS.md) before making changes and check the [open issues](https://github.com/icfmp/Bible/issues).

## License

See [LICENSE](LICENSE) (GNU GPL version 2) and [third-party notices](THIRD_PARTY_NOTICES.md). Downloaded Bibles and commentaries remain subject to their respective licenses.
