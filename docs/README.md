# Documentation map

This directory contains **developer and maintainer documentation**, not a second user manual. For end-user instructions, use the project's [GitHub wiki](https://github.com/icfmp/Bible/wiki). For current priorities and delivery status, consult [GitHub issues](https://github.com/icfmp/Bible/issues) rather than dated handoff reports.

## Start here

- [Repository README](../README.md) — install the alpha, run from source, run tests and contribute.
- [Agent and contributor rules](../AGENTS.md) — conventions, source fidelity, validation and delivery.
- [Product requirements](CAHIER_DES_CHARGES.md) — original approved product scope (historical French source of truth; do not mistake its proposed phases for current progress).
- [Original roadmap](FEUILLE_DE_ROUTE.md) — initial sequencing, **not** the current project board.

## Maintained technical references

- [Notes data format](NOTES_DATA_FORMAT.md) — persisted note identity and linked-passage contract.
- [Source section storage](SOURCE_SECTION_STORAGE.md) — source structure and storage decisions.
- [Wiki publishing](WIKI_PUBLISHING.md) — publishing user help without duplicating it here.
- [Alpha Flatpak channel](CANAL_ALPHA_FLATPAK.md) — channel design, recovery caveats and historical operational evidence; use the current release/workflow for live status.
- [Single alpha deployment](ALPHA_SINGLE_DEPLOYMENT.md) — delivery procedure and constraints.
- [Provider sources](SOURCES_AFFILIEES_11.md) — source integration background; verify against current code before making changes.

## Historical material and evidence

The many issue-numbered implementation reviews, delivery handoffs and screenshots currently under `docs/` are **historical evidence, not live instructions**. Do not infer current product behavior or release state from them. The long-term cleanup in [issue #86](https://github.com/icfmp/Bible/issues/86) will curate and relocate them only after checking inbound references from tests, scripts, workflows and other documents.

- `docs/captures/` — historical UI captures; not necessarily current UI.
- `docs/evidence/` — prior validation output and diagnostic material; not a substitute for current CI.
- `docs/validation/` — individual validation notes and fixtures.

**When in doubt:** inspect current source code, current workflows, and the relevant open issue before relying on an older report.
