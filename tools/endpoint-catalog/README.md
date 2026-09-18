# Legacy endpoint catalog verifier

Offline, read-only verification that the reviewed legacy endpoint catalog
(`docs/legacy-protocol/endpoints.json`) and its readable inventory
(`docs/legacy-protocol/endpoints.md`) still match the route registrations in
`server.py`. Python 3.9 standard library only; no new dependencies.

## Executable and invocation

Verified executable: `C:\Users\Edison\AppData\Local\Temp\socialwars-runtime-740419ee065f46eab323c20a2d601e6b\verify-one\Scripts\python.exe`
(CPython 3.9.13, tags/v3.9.13:6de2ca5, May 17 2022, 16:36:42, MSC v.1929 64 bit (AMD64)),
from the pinned source runtime described in `docs/legacy-baseline.md`.
`sys.executable` reported exactly the path above and `python --version`
reported `Python 3.9.13` for the passing run. Any working Python 3.9+
standard-library interpreter should behave identically.

From the repository root:

```bash
python -B tools/endpoint-catalog/verify_endpoints.py
```

Exit 0 prints a JSON report with `"result": "agreement"`. The report goes to
stdout only; the tool never writes files.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Catalog, inventory, and source agree |
| 1 | Catalog drift: route coverage, method derivation, classification, or inventory inconsistency detected; the report lists each problem |
| 2 | Invalid input or unsupported source syntax: missing/unreadable files, invalid catalog schema, unparseable source, or route expressions outside the supported subset (string constants, string concatenation, top-level string-name bindings) |

## What is verified

- Inert AST analysis of `server.py`: every live `@app.route` registration is
  resolved from string constants, string concatenations, and module-level
  string-name bindings (`__STATIC_ROOT`, `__DYNAMIC_ROOT`). Nothing is imported
  or executed; unsupported expressions fail with exit 2 instead of being
  silently skipped.
- Route coverage: the 15 explicit active routes in the catalog must exactly
  match the registrations parsed from source, with declared and derived
  effective methods (omitted methods default to GET; GET implies HEAD; OPTIONS
  is automatic) matching per route.
- Classification: `explicit_active`, `framework_default`, and `disabled`
  entries; disabled declarations must have no effective methods, and no
  disabled route may appear as a live `@app.route` registration in source.
- Catalog schema: policy fields, required entry fields, input/response/effect
  lists, and source references with file and line bounds. Every
  `source_references` entry must name a file under the repository root with
  `1 <= line <= end_line` within that file's actual line count.
- Inventory consistency: every catalog route must appear verbatim in
  `endpoints.md`, with the disabled auction routes labeled as disabled, the
  framework static registration labeled as framework-provided, and the
  alliance placeholder labeled as not implemented.

## Evidence classification

This tool establishes structural, source-grounded consistency between the
catalog, the readable inventory, and the current source. It is evidence of
reviewed documentation, not evidence of executed endpoints, gameplay parity, or
complete command discovery. Executed runtime evidence remains limited to the
tools documented in `docs/legacy-baseline.md`, `tools/protocol-replay/`, and
related guides; none is claimed by this verifier.

## Containment

- Reads only `server.py`, `docs/legacy-protocol/endpoints.json`, and
  `docs/legacy-protocol/endpoints.md` (plus optional `--repo-root` relocation
  of the same reads), plus the additional repository source files named by
  the catalog's `source_references` (`sessions.py`, `bundle.py`,
  `get_game_config.py`, `get_player_info.py`, `command.py`,
  `legacy_command_recorder.py`), which are read to validate reference line
  bounds.
- Never imports or executes `server.py` or any legacy application module, never
  imports Flask, never invokes route handlers, never reads runtime saves,
  never contacts a network, never starts a server, and never opens a browser
  or Flash content.
- Writes nothing: no report files, no bytecode (`-B` recommended), no caches,
  no temporary files in the repository. Repeated runs over unchanged inputs
  are byte-identical.
- The focused tests in `test_endpoint_catalog.py` run the same way:

```bash
python -B -m unittest discover -s tools/endpoint-catalog -p test_endpoint_catalog.py -v
```
