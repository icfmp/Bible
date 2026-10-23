# Troubleshooting

Bible is alpha software. Thank you for helping improve it.

## Installation or update fails

Confirm Flatpak is installed and use the official [alpha installation link](https://icfmp.github.io/Bible/alpha/Bible.flatpakref). For upgrades from a standalone bundle, consult the [migration guide](https://github.com/icfmp/Bible/blob/main/docs/CANAL_ALPHA_FLATPAK.md).

## No Bible text appears

No translation is bundled. Open **Library** (`Ctrl+L`), choose a Bible and download it. Internet access is needed for the initial download.

## A commentary is missing for a passage

Commentaries have different coverage. Some references may not map cleanly across versification systems, especially in alpha.

## Report a bug

Open a [GitHub issue](https://github.com/icfmp/Bible/issues/new) and include:

- Your Linux distribution and desktop environment.
- What you expected and what happened.
- Steps to reproduce the problem.
- A screenshot if it helps (avoid exposing private notes).
- Your installed build, available with:

```sh
flatpak info io.github.icfmp.Bible//alpha
```

Please write public issues in English.
