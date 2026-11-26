# Python formatting and documentation

Use Python3.12 or newer and Ruff0.14.5, pinned in `requirements-dev.txt` and
`pyproject.toml`. Ruff is a development tool, never an application dependency.
GTK/SWORD development still uses the system Python described in the README.
Install tooling in an isolated environment, then run from the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install --no-deps -r requirements-gi-stubs.txt
.venv/bin/ruff format
.venv/bin/ruff check
.venv/bin/mypy
```

CI runs the same pinned `ruff format --check` and `ruff check`. The formatter
owns indentation, quotes, blank lines and wrapping with a100-character target.
Long literal strings/comments may exceed this target when wrapping changes their
meaning or makes them less clear. Do not add a second formatter. Editor
format-on-save can use the official Ruff extension with the project environment;
it is optional and must use the same configuration/version.

## Scope and safe linting

The configured scope is first-party Python in `bible`, `tools` and `tests`.
Third-party/vendored sources, resource corpora, generated build outputs and
virtual environments are excluded. Non-Python resource files are never formatted.
The initial lint set checks syntax, useful Pyflakes errors, imports and module
purpose docstrings. It also rejects mutable argument defaults, control flow that
suppresses exceptions in `finally`, discarded expressions and unretained asyncio
tasks. Property access that deliberately triggers identity validation should be
explicit (`_ = resource.id`), rather than removed as supposedly unused work.
It deliberately omits blanket style rules, import sorting
and mandatory docstrings for every callback/test/trivial helper. Existing public
exports must remain available; make genuine reexports explicit with `as` aliases.
Imports used to probe native dependency availability need explained narrow
exceptions. Do not remove an import merely because automatic linting calls it
unused: inspect callers and import side effects first. Never run unsafe fixes
indiscriminately.

`gi.require_version(...)` must precede the corresponding `gi.repository` imports,
and renderer setup must precede GTK initialization. The configuration lists only
the initialization modules needing E402 exceptions; preserve statement order.
`ui.py` also selects the default native GSK renderer before importing GI consumers.
Avoid broad package-wide exceptions or sorting around those constraints.

## Documentation conventions

Write comments and docstrings in English. Every first-party module needs a short
purpose docstring before imports, after any shebang/encoding line and before
future imports. Describe responsibilities and relevant constraints, not a list
of symbols. Document public APIs and complex internal behavior after reading
implementations, callers and relevant tests. Trivial callbacks/helpers and test
methods do not need repetitive boilerplate.

Use Google style. Start with a concise behavioral sentence; explain important
invariants, persistence and side effects, caller obligations and GTK main-loop
or worker-thread constraints. Use `Args`, `Returns`, `Raises` or `Yields` when
useful, without repeating obvious signatures or claiming guarantees the code
does not make. Add accurate type annotations where they clarify a contract;
avoid mass annotation changes as part of formatting.

Comments should explain why a compatibility workaround, validation or performance
constraint exists. Do not narrate assignments. Ruff checks selected docstring
layout, but cannot verify factual accuracy. Review documentation against the code.

## Review and validation

Keep formatter-only changes separate from documentation and meaningful lint
corrections. Compare Python ASTs for a mechanical formatting commit; do not
assume a large diff is semantically safe. Run existing tests for affected lint
corrections and preserve GTK startup/version initialization. Reuse unchanged
results and let normal CI run the broad regression suite once, as described in
[VALIDATION.md](VALIDATION.md). No implementation-mirroring tests are needed for
formatting or prose. Coordinate repository-wide formatting with active PRs before
editing their files; do not overwrite concurrent work.

## Progressive static typing

Run `.venv/bin/mypy` with the same pinned development dependency as CI. The
checked boundary is the explicit module list in `pyproject.toml`, including
provider/reference models, annotations, persistence and several GTK helpers.
Selected test and diagnostic modules are checked alongside the application code.
Imported modules are read silently, not presented as fully checked. Every function
in this boundary needs parameter/return annotations.
Expand this explicit list when an additional component has actually been typed.
Static GTK 4/GDK 4/Soup 3 declarations are pinned separately and installed with
`--no-deps`: the checker needs no native GTK runtime. SWORD declarations live in
`typings/Sword.pyi`. These are development inputs, never application dependencies.

Annotate public contracts, optional results and ambiguous/empty collections.
Prefer inferred local types when assignments are clear; Python needs no separate
variable declaration or redundant annotation for each literal. Use `PathLike`,
`Iterable`, immutable dataclasses and `TypedDict` according to real caller needs.
A `TypedDict` documents existing dictionary fields without changing serialized
keys, schemas or object representation. Keep external JSON dynamically typed at
the parsing boundary until existing validation proves a stronger contract.

Annotations never replace runtime validation, coerce imported data, create
missing values or justify changing persisted formats. Keep casts narrow and
explain their evidence; never add blanket ignores or annotate uncertain code as
`Any` merely to obtain a green check. Use platform guards understood by the checker for OS-specific bindings.
Preserve GI initialization and avoid importing GTK
solely for a type hint. Callbacks and the wider UI will be typed progressively,
not through a speculative application-wide rewrite.
