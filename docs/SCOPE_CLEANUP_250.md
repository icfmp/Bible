# PR250 scope cleanup and authorized application-only resumption

The client stopped feature development and publication on 8 November 2026, then reviewed the cleanup report and authorized resuming work **only in Bible**. The application cleanup is retained. Related issues and technical dependencies do not authorize work in other repositories. The resumption does not authorize merging or changing the separate Bible-Resources cleanup PR. Application review, successful checks and verified publication remain required under AGENTS.md.

## Cause

The agent interpreted #218's request for generic geographical coverage and its mention of a preferred Bible-Resources preparation process as permission to modify that repository. That interpretation was wrong. The resulting acquisition, collection and distribution changes in Bible-Resources PRs20 and21 exceeded the authorized repository scope.

## Bible-Resources

Draft PR22 proposes two ordinary, targeted revert commits, reverting PR21 then PR20. It removes their scripts, identity/source configuration, generated geographic dataset, manifests/snapshot, documentation/tests and build hooks. Its resulting tree equals the pre-change commit `751efabc54c1cf21a6351d4fd2f2b85d13a8de48`. Existing Segond, MHC, validation and resource-management work remains unchanged. No reset, rewritten history, moved tag or administrative change is used. **Do not merge without explicit client approval.**

## Bible PR250

Remove the generated geographic seed/origin, optional context resource registration and manifests, acquisition/distribution endpoints, context/photo renderer and associated tests/checks. Do not restore the old Jerusalem-only authored/translated sample. Previously downloaded profile files and photograph caches are left untouched and are no longer consumed by these paths.

Restore the pre-existing study catalogue, reference/topic installers and four Library study resources. Installed-version discovery remains read-only; its checker uses the catalogue URL documented by the pre-existing Bible-Resources build, not PR21's new committed snapshot. That endpoint returned HTTP404 on8November; on14November the same existing endpoint is reachable and publishes two module records. Consume/report its real state instead of creating another publication route. Cached metadata from the removed route is not reused.

## Independent improvements retained

- Shared note-editor layout, labels, linked passages, draft/save protection and existing persistence contract.
- Search/Aa/selection geometry and native dismissal fixes.
- References following the visible Bible anchor and transient Study context indication.
- Existing STEP word/gloss/occurrence data, exact installed Bible excerpts and verified reference mapping.
- One contextual dialog reusing those word and existing OpenBible map components.
- OpenBible's existing source IDs, names, proposed coordinates, uncertainty, bibliography and verse references; proposal headings may group an identical source modern ID without changing or deleting evidence.
- Read-only installed SWORD version/origin discovery. The complete intermittent selector lock and module installation/rollback are still unresolved/unimplemented.

## Unavailable dependencies

Historical descriptions and photographs require an existing approved external resource; none is integrated by this cleanup. Dictionary definitions and biblical-person records remain unavailable until legitimate data and explicit integration authorization exist. A reachable catalogue does not establish installed-edition identity or implement an update service. The initial optional provider installation belongs to unassigned #253, which is not started here. No atomic module installer or rollback is claimed.

## Repository boundary

Work only on explicitly assigned issues within explicitly authorized repositories. Consume existing identifiable resources; do not create datasets, curated collections, resource-generation pipelines or distribution infrastructure. Propose additional data providers for approval before integrating them. Missing source data remains missing. This rule applies to all study resources, not only geography.

Application work resumes within the assigned issue scope and the existing-data boundary. Cleanup checks are not client acceptance or a delivered alpha. Missing historical/photo/dictionary/person data must be reported as unavailable; catalogue connectivity must be reported from actual checks; no substitute dataset or distribution route is authorized.
