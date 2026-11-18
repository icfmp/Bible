# Proportionate validation and delivery

Keep source fidelity, user data, signatures, provenance and client acceptance as
hard requirements. Reduce duplicated work rather than bypassing those checks.
These rules apply to work in `icfmp/Bible` only.

## Choose the smallest useful validation before editing

Record the affected behavior, likely shared consumers and a short check list in
the task update. Use the assigned issue and current comments as the acceptance
criteria. Do not create a new planning document for each small change.

| Change | Developer validation | Delivery |
| --- | --- | --- |
| Documentation, agent instructions or workflow configuration | Review the relevant text; validate workflow syntax and event/job gates when affected. | Push/merge the verified change. No application rebuild, installed-app campaign or numbered alpha. |
| Small visual fix | Focused native regression if meaningful, the client's reproduction, and a representative actual GTK before/after comparison. Check FR/EN, narrow windows and themes where that surface is affected or explicitly requested. Usually 1–3 useful screenshot pairs suffice. | Normal application CI, one signed deployment, actual installed update and one numbered alpha for the batch. |
| Shared functional mechanism | Focused regression plus other affected consumers; real existing resources where provider behavior matters. Test both directions for synchronization/mapping. | Same application delivery gates; report any unavailable source dependency. |
| Persistence, source conversion, packaging or distribution | Review through a PR. Test the relevant migration/restore, fidelity/offline or signature/provenance failure boundaries. For packaging-risk PRs, explicitly dispatch the full application workflow on the branch before merge. | Green checks for the exact merged application source; publish only after required installed-update verification. Reuse the verified artifact for distribution-only repairs. |

Expand coverage when a failure, shared mechanism, migration or explicit client
request justifies it. Do not multiply every language, Bible, font, renderer,
theme and window size by default. A localization-neutral pixel change does not
require downloading more editions just to increase the test count. Keep any
broader coverage specifically requested by the client.

## CI responsibilities

- `prerequisites.yml`: application PRs run the host regression checks. Main runs
  the same checks and builds/tests the exact merged Flatpak once. Existing
  native-input, real-resource/offline, scrolling and packaged regression suites
  remain in place. Live host resource downloads run on main/manual dispatch,
  avoiding the same network downloads on the PR and its merge. The French replay uses localized UI smoke tests normally;
  localization changes, missing history and manual dispatch keep the full French
  replay. Non-UI parsers/backups still run in the full functional suites. A manual dispatch can still build a branch when needed.
- Test/diagnostic-only maintenance is reviewed through PR host checks and the
  lightweight policy suite, without repackaging unchanged application code on
  main. When needed, exercise a changed native test against the existing installed
  build. Do not use a direct unverified main push to bypass PR test checks.
- Extra visual/word/contextual/Library campaigns use `tools/ci_campaigns.py` and
  the changed files. Shared components select related consumers. Unknown runtime
  files, packaging changes or unavailable Git history keep all campaigns; manual
  workflow dispatch also keeps full coverage. The core offline/scrolling and
  packaged suites are never conditional on this selector. A failed selector
  fails CI rather than silently omitting coverage. Explicit client requests for
  broader validation still apply.
- Numeric blur pixel-energy thresholds are diagnostic report values, not release
  gates. Font checks require the expected bundled family, not a particular font
  subdirectory; animation checks require respecting the user's animation setting,
  not a fixed duration. Hidden-work and first-input performance guards remain.
- Workflow policy tests validate declarative boundaries and driver commands, not
  a homemade interpreter for GitHub expressions/globs. Confirm actual PR/main
  job states in GitHub when changing those conditions.
- Documentation, Wiki, agent instructions, workflow-only changes and
  distribution-only maintenance do not trigger an application build. Mixed
  changes containing application/build code still do. Wiki publication keeps
  its own existing workflow.
- `workflow-checks.yml`: lightweight YAML and event/job-policy checks cover
  workflow edits. They do not build, install or publish an application.
- `channel-restore-checks.yml`: PRs run the native channel/storage/gate tests;
  main and explicit dispatch additionally exercise the real signed installation
  and update. This main check remains required before delivering a distribution
  change. Signature, provenance and retained-data rejection tests remain intact.
- `audit-affiliated-sources.yml`: explicit source/documentation audit. Routine
  application CI no longer rediscovers GNOME guidance, available SWORD packages
  or documentation endpoint availability. Actual resource integration checks
  remain in application CI.
- Historical profiling, YouVersion fidelity and signed-feedback campaigns are
  explicit manual workflows, not extra jobs on old feature/performance branches.
  Enter the current verified run/previous source for a manual publication or
  comparison; historical default identifiers are not reusable evidence.
- Publication still accepts only a green main application build and matching
  artifact. Keep stable signing identity, exact source/tag and actual public
  installation/update checks. No change here relaxes publication verification.

Run focused local checks once. Let CI run the broad regression suites; do not
repeat them locally in full for unchanged code. Wait for the relevant CI result
before starting a second campaign. Reuse existing screenshots/results only when
their code, artifact, environment and tested behavior still apply. Do not report
omitted checks as passed or branch tests as a tested merged package.

## Bound failures and investigations

After two identical failures without new evidence, stop retrying and identify
the failing operation. After 30 minutes of active investigation outside the
assigned fix, report the blocker, established facts and the next bounded step;
passive CI wait is not active investigation. Continue independent authorized
work. A larger ancillary repair needs a concrete plan and client approval before
scope expands. Never turn a dependency outage into an unrequested redesign.

For CI, read the failed step and a short relevant log excerpt first. Rerun only
the failed job when a transient cause is established; reuse a successful build.
Do not regenerate packages to retry publication or create release notes. Do not
repeatedly probe denied authentication/project permissions without a change in
access. Preserve a concise source/check/artifact/next-action receipt across
environment restarts, instead of reconstructing or repeating completed work.

## Preservation and remaining limits

Snapshot persistent content, references, note links and preferences before the
operation. Use logical comparisons where serialization, timestamps or caches
legitimately change. If session state is rewritten, verify the stored passages,
tabs, history and preferences separately from volatile viewport fields. Record
any position drift as a limitation; do not silently discard the whole session
from preservation checks. Never reset the profile or overwrite a baseline to
hide a discrepancy.

When the agreed change and relevant checks pass, finish the batch. If the
reported symptom cannot be reproduced, describe exactly what the change proves
and what still needs client validation. Repeating similar captures cannot turn
an unreproduced symptom into a proven correction. Keep implementation, tested
behavior, publication and client acceptance distinct.
