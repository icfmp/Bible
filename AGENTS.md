# Instructions for development agents

## Product and sources of truth
Build **Bible**, a free/open-source desktop Bible reading and study application.
Read these before implementation:
1. docs/CAHIER_DES_CHARGES.md — confirmed product requirements and open questions.
2. docs/FEUILLE_DE_ROUTE.md — proposed sequencing, first task and acceptance checks.

The user is the client. Communicate with the client in French. Keep implementation identifiers clear and interface strings translatable. Do not assume access to the conversation that produced these documents.

## Technical direction
- Native GNOME first: Python + PyGObject + GTK 4 + libadwaita is the proposed baseline.
- Use a real Header Bar and current stable GNOME patterns. Do not substitute a web mockup, Electron shell, or website.
- Prove SWORD Python bindings and Flatpak packaging early. Do not invent binding methods or module capabilities.
- Separate domain/reference models, content providers, persistence, AI adapters, and UI.
- Desktop targets are Linux, Windows and macOS; GNOME is the priority. Flag portability risks before expanding dependencies.
- Verify current official documentation and pin compatible stable dependencies. Explain major stack changes before implementing them.
- No dedicated server or mandatory Bible account. AI costs belong to users through their own provider configuration.

## Content and data
- Download resources on user request; ship no complete Bible translation.
- CrossWire is the initial functional source. YouVersion/full offline Semeur availability remains to be validated.
- Preserve text structure, canonical references, source attribution and versification. Account for different canons and missing verses.
- Notes belong to passages across translations/languages, recording the original translation only as context.
- Persist and migrate user data safely. Notes must survive resource uninstall/update.
- Never generate or silently paraphrase Bible text.
- Treat downloaded markup, Markdown and AI output as untrusted data.
- Keep credentials out of Git, logs and ordinary backups. Use appropriate credential storage.
- Do not imply that owning a print/digital Bible grants every external download permission. Document provider access conditions and unknowns honestly.
- Do not bypass authentication, DRM or other access controls.

## UX and scope
- Keep reading clean; study tools are optional and collapsible.
- Prioritize useful defaults and plain-language controls, not technical setup screens.
- French and English UI from the first release; full keyboard access and comfortable text sizing.
- Never squeeze comparisons into unreadably narrow columns.
- No prayer list, task management, habit tracking, mobile app, manual file import or initial sync.
- Reading plans and AI theological explanations are future exploration.
- No mandatory AI for ordinary reading, exact search, navigation, copying or note-taking.

## Delivery discipline
- Work in focused increments; first prove a real downloaded module and installable GTK application.
- Use a feature branch and a reviewable pull request for implementation.
- Run relevant tests and report actual results. Test data persistence, references, offline behavior and text fidelity where affected.
- Distinguish automated checks from manual GUI validation and actual OS-specific checks.
- Cloud execution does not prove the GUI works on the client's GNOME desktop.
- Do not claim Flathub acceptance, a successful build, an available artifact or a working integration unless verified.
- Do not add fabricated progress, placeholder translations presented as real, or silent requirement reductions.
- Do not publish releases, submit to Flathub, spend money or change repository administration without the corresponding task authorization.

