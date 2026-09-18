# Legacy command catalog verifier

Offline, read-only verification that the reviewed legacy command catalog
(`docs/legacy-protocol/commands.json`) and its readable inventory
(`docs/legacy-protocol/commands.md`) still match the dispatcher branches in
`command.py`. Python 3.9 standard library only; no new dependencies.

## Executable and invocation

Verified executable: `C:\Users\Edison\AppData\Local\Temp\socialwars-runtime-740419ee065f46eab323c20a2d601e6b\verify-one\Scripts\python.exe`
(CPython 3.9.13, tags/v3.9.13:6de2ca5, May 17 2022, 16:36:42, MSC v.1929 64 bit (AMD64)),
from the pinned source runtime described in `docs/legacy-baseline.md`.
`sys.executable` reported exactly the path above and `python --version`
reported `Python 3.9.13` for the passing run. Any working Python 3.9+
standard-library interpreter should behave identically.

From the repository root:

```bash
python -B tools/command-catalog/verify_commands.py
```

Exit 0 prints a JSON report with `"result": "agreement"`. The report goes to
stdout only; the tool never writes files.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Catalog, inventory, and source agree |
| 1 | Catalog drift: branch coverage or inventory inconsistency detected; the report lists each problem |
| 2 | Invalid input or unsupported source syntax: missing/unreadable files, invalid catalog schema, unparseable source, a missing `do_command` dispatcher, or command comparisons outside the supported subset (literal `cmd == "<name>"` string-constant comparisons) |

## What is verified

- Inert AST analysis of `command.py`: every `cmd == "<name>"` branch inside
  `do_command` is resolved from string constants only. Nothing is imported
  or executed; any non-literal command comparison (dynamic names, membership
  tests, duplicate branches) fails with exit 2 instead of being silently
  skipped.
- Command coverage: the 63 handled command names in the catalog must exactly
  match the branches parsed from source. The catalog additionally carries one
  `fallthrough` entry for the unhandled `else` at `command.py:954-956`; the
  fallthrough is never counted as a branch.
- Count note: the approved proposal estimated 64 named branches, but the
  source contains 63 literal comparisons plus the fallthrough. The extra
  proposal-table row, `push_dead_unit`, is an engine helper called from the
  `sell` KILL path, not a dispatcher branch. The catalog records source truth
  and the verifier enforces it.
- Catalog schema: policy fields (including `branch_count`/`entry_count`
  cross-checked against the entries), the envelope contract (fields,
  per-command tuple shape, resource delta shape, pre-dispatch
  `apply_resources`, batch persistence, fallthrough), and per-entry fields
  (classification, domain, argument shapes, resource effects, state
  reads/writes, persistence effects, client-trust notes, security notes,
  source references with file and line bounds, observed fixtures, migration
  status). Every `source_references` entry must name a file under the
  repository root with `1 <= line <= end_line` within that file's actual line
  count.
- Inventory consistency: every catalog command name must appear verbatim in
  `commands.md`, with time-manipulation labeling, never-production labeling
  for debug and time paths, the alliance placeholder labeled as not
  implemented, and the pre-dispatch `apply_resources` contract present.

## Evidence classification

This tool establishes structural, source-grounded consistency between the
catalog, the readable inventory, and the current source. It is evidence of
reviewed documentation, not evidence of executed commands, gameplay parity, or
progressed-player coverage. Executed runtime evidence remains limited to the
four-command replay coverage documented in `tools/protocol-replay/` and the
guides it references; none is claimed by this verifier.

## Containment

- Reads only `command.py`, `docs/legacy-protocol/commands.json`, and
  `docs/legacy-protocol/commands.md` (plus optional `--repo-root` relocation
  of the same reads), plus the additional repository source files named by
  the catalog's `source_references` (`engine.py`, `sessions.py`,
  `get_game_config.py`), which are read to validate reference line bounds.
- Never imports or executes `command.py` or any legacy application module,
  never invokes command handlers, never reads runtime saves, never contacts a
  network, never starts a server, and never opens a browser or Flash content.
- Writes nothing: no report files, no bytecode (`-B` recommended), no caches,
  no temporary files in the repository. Repeated runs over unchanged inputs
  are byte-identical.
- The focused tests in `test_command_catalog.py` run the same way:

```bash
python -B -m unittest discover -s tools/command-catalog -p test_command_catalog.py -v
```
