# Troubleshooting

Bible is currently **alpha software**. Some features and installation details may change between releases. This guide covers common problems and how to report an issue when you need help.

## Installation fails

Bible's public alpha is distributed as a **Flatpak for Linux x86_64**. It is not yet available on Flathub as an application.

1. Confirm that [Flatpak is installed and configured](https://flatpak.org/setup/) on your system.
2. Use the [official Bible alpha installer](https://icfmp.github.io/Bible/alpha/Bible.flatpakref).
3. If the graphical installation fails, try the terminal:

```sh
flatpak install https://icfmp.github.io/Bible/alpha/Bible.flatpakref
```

Flatpak may need to install the GNOME runtime from Flathub. If an error appears, keep its exact text for your bug report.

See [Installation and updates](Installation) for the complete procedure.

## Bible does not start

Try launching it from a terminal:

```sh
flatpak run io.github.icfmp.Bible//alpha
```

If it fails, copy the relevant error messages. Avoid including personal notes, access tokens or other private information in a public report.

Check that you are running the expected alpha build:

```sh
flatpak info io.github.icfmp.Bible//alpha
```

## An update fails or the application seems outdated

Try:

```sh
flatpak update io.github.icfmp.Bible//alpha
```

If Flatpak reports a download, remote or signature error, do not delete the application's data or remove repositories at random. Save the exact message and report the problem.

**Coming from an older standalone Flatpak bundle?** Read the [alpha migration guide](https://github.com/icfmp/Bible/blob/main/docs/CANAL_ALPHA_FLATPAK.md) first. Older installations may use a different Flatpak branch, so the normal update command may not migrate them automatically.

## No Bible text appears

**Bible does not bundle Bible translations.** You must download at least one translation before reading.

1. Open **Library** with **`Ctrl+L`**.
2. In **Explore**, choose **Bible translations**.
3. Check your language and source filters.
4. Select a translation and download it.
5. Return to the reader and select the installed translation.

An internet connection is required for the initial download. Once installed, resources can be read offline.

If the catalogue appears empty, clear restrictive search terms or filters and try again. See [Downloading Bibles and commentaries](Downloading-Resources).

## A commentary is missing or does not follow the Bible

Make sure a commentary has been installed through **Library**, then open the study panel with **`F9`**, select **Commentaries**, and choose the installed resource.

Some commentaries do not cover every verse or chapter. Bible may also show **No verified alignment** or **Different versifications** when it cannot reliably match references across resources. This is preferable to showing commentary for the wrong passage.

Try another passage or commentary. See [Study panel and commentaries](Study-Panel).

## My notes or settings seem to have disappeared

Before changing installation methods, check whether you are running an older standalone bundle or the current alpha channel. Avoid launching multiple versions of Bible at the same time.

**Do not run `flatpak uninstall --delete-data` or delete application directories** when attempting to fix an issue. Such actions can permanently remove personal notes, highlights, settings and downloaded resources.

Bible's alpha does not yet offer a confirmed user-facing notes backup and restore workflow. Follow the [alpha migration guide](https://github.com/icfmp/Bible/blob/main/docs/CANAL_ALPHA_FLATPAK.md) and preserve existing application data before reinstalling or migrating.

## Report a bug or suggest an improvement

Open a [new GitHub issue](https://github.com/icfmp/Bible/issues/new) and provide:

- **System:** Linux distribution, version, and desktop environment (for example, GNOME).
- **Bible build:** the output of `flatpak info io.github.icfmp.Bible//alpha`.
- **Steps:** what you did, in the order you did it.
- **Expected / actual results:** what you expected and what happened instead.
- **Error text:** relevant terminal messages, if any.
- **Screenshot:** if it makes the issue easier to understand; remove any private notes or sensitive information.

Please write public issues **in English**, if possible, to help contributors investigate them.

---

**Related guides:** [Installation and updates](Installation) · [Downloading resources](Downloading-Resources) · [Notes and highlights](Notes-and-Highlights)
