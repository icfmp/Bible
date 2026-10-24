# Instructions for development agents

## Product and sources of truth
Build **Bible**, a free/open-source desktop Bible reading and study application.
Read these before implementation:
1. docs/CAHIER_DES_CHARGES.md — confirmed product requirements and open questions.
2. docs/FEUILLE_DE_ROUTE.md — proposed sequencing, first task and acceptance checks.

The user is the client. Communicate with the client in French. Keep implementation identifiers clear and interface strings translatable. Do not assume access to the conversation that produced these documents.

## Public project language
- Use English for all public GitHub content: issue titles, descriptions and comments; pull requests and reviews; commit messages; release notes; README and contributor-facing documentation.
- Keep direct conversations with the client in French. Explain decisions and next steps in French privately, and in English on GitHub.
- Keep the application available in French and English. This policy does not change UI localization or the language of downloaded resources.
- Exact localized UI labels and error messages may be quoted when needed, with an English explanation.
- Preserve historical contributions and authorship. Translate existing project documentation progressively when it is revised; do not rewrite Git history to change its language.

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
- For routine, reversible changes, work on the current `main`, run relevant checks, commit and push the result directly when repository access permits. Refresh from the latest `main` before editing and do not force-push.
- For changes that warrant review (data migrations, licensing or content-source policy, secrets, release/distribution, or major architecture), use a feature branch and a pull request. Explain the decision and next action in the appropriate language defined above.
- If the environment cannot push or merge, report the exact permission/error and leave a reviewable commit or pull request; do not ask the client to perform routine Git operations without first diagnosing the access issue.
- Run relevant tests and report actual results. Test data persistence, references, offline behavior and text fidelity where affected.
- Distinguish automated checks from manual GUI validation and actual OS-specific checks.
- Cloud execution does not prove the GUI works on the client's GNOME desktop.
- Do not claim Flathub acceptance, a successful build, an available artifact or a working integration unless verified.
- Do not add fabricated progress, placeholder translations presented as real, or silent requirement reductions.
- Do not publish releases, submit to Flathub, spend money or change repository administration without the corresponding task authorization.


## Numbered prereleases until the first stable release
- Standing client authorization (23 October 2026): every completed application delivery batch published to the signed alpha channel must also receive a numbered GitHub prerelease, until the first official stable release. Do not require the client to request this again. This authorization does not cover a stable release, Flathub submission, spending or repository administration.
- Continue sequential numbering from `0.1.0-alpha.3` to `0.1.0-alpha.4`, etc. Use one prerelease per delivered batch, not per intermediate commit, CI retry, packaging verification revision or documentation/website-only change.
- Publish only after the relevant review, green CI, successful signed deployment and actual update verification. Failed or incomplete deployments are not releases.
- Tag the exact verified application source commit and never move published tags. Record matching source/build/publication provenance; preserve the signed channel identity and user data.
- Include English release notes describing all delivered features, changes and fixes since the previous numbered prerelease, plus installation/update instructions and material known limitations. Exclude planned or unshipped issues. Attach only matching verified packages/sources/checksums, or link clearly to the signed installation channel.
- A delivery report must include the public GitHub prerelease URL. If publication is blocked, report the exact blocker and explicitly state that the delivery is not yet fully published.
- Keep continuous Flatpak updates. Do not rebuild or republish the application solely to create release notes for an already verified snapshot.


## Milestones, project status and client acceptance
Standing client workflow decision (24 October 2026). Use the Bible project at https://github.com/users/icfmp/projects/5 with this lifecycle:
**Backlog -> Ready -> In progress -> In review -> In validation -> Done**.

- A milestone groups an outcome; assigning an issue to one does not authorize starting it. When the client explicitly requests work on a milestone, read its current issues and comments, check dependencies and existing work, and move its eligible not-started issues to Ready. Preserve In progress, In review, In validation and Done items; do not reset them. Keep already-Ready client priorities and active assignments unless the client changes them. Do not silently expand the selected milestone's scope.
- Move an issue to In progress only when actively working on it. Work through dependencies in focused increments, respect project work-in-progress limits, and coordinate overlapping changes. Ready is a queue, not a claim that all issues are running.
- Use In review while applicable code review, CI, packaging or publication verification remains outstanding. A merged PR alone is not a completed delivery.
- Move an application issue to In validation only when its agreed scope is implemented, relevant review/checks pass, the signed alpha and matching numbered prerelease are actually published, and the update has been verified under the delivery rules above. Partial work or failed/blocked publication stays out of In validation; record the exact remaining work/blocker without inventing a status.
- For documentation-only or project-configuration work, In validation requires the actual published change and relevant verification; do not rebuild/release the application for those changes.
- Provide each issue in validation with concise English evidence: implemented scope, checks actually performed, exact source/build and release link for application work, material limitations, and up to three simple client test steps. Distinguish developer validation from the client's desktop acceptance.
- ONLY THE CLIENT moves issues to Done. Agents must not set Done, close completed implementation issues or close milestones merely because code merged or an alpha shipped. Leave issues OPEN during In validation. This supersedes older issue instructions to close on delivery.
- Do not use automatic issue-closing keywords (Closes/Fixes/Resolves #...) in commits or PR descriptions, or development links that auto-close issues on merge. Use non-closing references such as Related to #... and inspect existing PR closing links before merging.
- Project workflows that send merged PRs or closed items directly to Done are disabled. The Done -> close issue workflow remains enabled so the client's manual acceptance also closes the issue. Do not re-enable completion shortcuts. If project permissions prevent a status update, report the precise limitation; do not close an issue as a substitute.
- Client-reported failed acceptance returns the affected issue to In progress when work resumes, retaining the report, drafts/data and release evidence. Do not reopen/rework unrelated accepted issues.
- A milestone is accepted only when all in-scope issues are client-validated Done and actually closed; the client controls its final closure. A milestone may be delivered in several verified alpha batches; do not wait for client acceptance to publish the already-authorized next batch or count In validation as accepted completion.
- Creating milestones or configuring this workflow does not start implementation. Preserve the current Ready tasks (#75 and #96 at setup) and current project item order/status unless explicitly instructed otherwise.
