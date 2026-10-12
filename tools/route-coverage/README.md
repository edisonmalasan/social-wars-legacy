# Legacy branch / modern route coverage census

Offline, read-only measurement of how many of the preserved legacy
dispatcher's named command branches are cited by a modern Compatibility API
`/v0` route. Python 3.9, standard library only, plus the repository's own
Flask (already a pinned dependency of `apps/compat-api/`, which this tool must
import). No new dependencies.

This is a **scoping instrument for milestone M13**, not a game rule and not a
behavioural claim. An uncovered branch is data.

## Executable and invocation

Verified interpreter: the pinned CPython 3.9.13 source runtime described in
`docs/legacy-baseline.md`; `python` in every command below is that
interpreter, never the PATH alias.

From the repository root:

```bash
python -B tools/route-coverage/verify_route_coverage.py
```

Exit 0 prints the deterministic JSON census on stdout and nothing else. The
tool never writes a file unless asked:

```bash
python -B tools/route-coverage/verify_route_coverage.py --out-path <path>
```

`--out-path` is optional and has **no default**: omitting it means the tool
writes nothing at all. `--repo-root` relocates the census (default: the current
directory).

The focused tests:

```bash
python -B -m unittest discover -s tools/route-coverage/tests -p "test_*.py" -v
```

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | The census was produced. **This is the normal exit even when branches are uncovered.** |
| 2 | Invalid input, unsupported source syntax, or a failed control: unreadable root, missing `command.py`, missing `do_command`, an unparseable branch set, a branch count other than 63, a planted control route the enumeration did not see, or an empty route enumeration. |

There is deliberately **no exit 1**, and that differs from
`tools/command-catalog/verify_commands.py`, which exits 1 on catalog drift.
The distinction is the point of this tool: coverage disagreement between the
legacy branch set and the modern route set is the *product*, and exiting
non-zero on it would make every uncovered branch a tool failure. A non-zero
exit here therefore means the instrument itself could not be trusted.

## What is measured

Current committed result (2026-10-12). **Every figure below is derived by the
tool from its inputs; none is hardcoded, and there is no expected-count
constant for any of them.**

**Conservative (the headline).** A branch is covered **only** when a resolved
`command.py:NNN` line span lands inside its span.

| Figure | Value |
| --- | --- |
| Legacy branches | 63 |
| `/v0` rules enumerated | 24 (24 distinct paths; 23 `POST`, 1 `GET`) |
| **Branches covered** | **24** |
| **Branches without a cited route** | **39** |
| Branches mentioned by name only (not covered) | 16 |
| Of those, mentions carrying a negation marker | 8 |
| Routes with no cited branch | 2 (`/v0/bootstrap`, `/v0/session`) |
| Branches cited by more than one route | 7 |
| Ambiguous citations (never ground a mapping) | 3 |
| Unresolved citations | 11 |

**Permissive (reported alongside, never the headline).** Counting a name-only
mention unless *every* mention of that branch is flagged: **37 covered / 26
uncovered.**

Both figures are emitted on every run, and both are internally checked by the
test suite against the citation lists they summarise. They are not two
estimates of one number — they are two different readings of the same
citations, and the gap between them is exactly the evidence a reader has to
adjudicate.

The 39 conservatively-uncovered branches are the 16 name-only branches above
plus the 23 that carry no resolved citation at all:

`add_inventory_item`, `add_xp_unit`, `admin_set_quest_rank`, `batch_remove`,
`buy_mana_new`, `buy_offer_pack`, `buy_powerups`, `buy_si_help`,
`collect_mission`, `finish_si`, `first_time_marketplace`, `flash_debug`,
`orient`, `ping`, `pop_unit`, `push_unit`, `remove_inventory_item`,
`rt_open_graph_unit`, `set_resource_allies`, `set_variables`,
`store_add_items`, `trade_resource`, `unit_collections_completed`.

## Reuse, not re-derivation (R1)

The legacy branch list is **imported** from
`tools/command-catalog/verify_commands.py`
(`extract_command_branches`, `_literal_command_name`), not re-extracted here.
The report records the reuse under `LEGACY_EXTRACTOR_SOURCE`. A second,
independently-written extractor would be a second thing that can silently
disagree with the catalog, and "63 branches" would then be a claim about this
directory rather than about the repository.

## Routes come from the live `url_map`, never from a source regex (R2)

Routes are enumerated from the booted Flask application's `url_map` via
`app.url_map.iter_rules()`. They are **not** found by searching
`compat_service.py` for decorator strings.

This is not a stylistic preference. A previous measurement of this same
question scanned the service source and matched a docstring that merely
*quoted* a decorator, reporting routes the application does not serve. The
live `url_map` cannot have that failure mode: it is the set of rules Flask
actually installed.

Enumeration is filtered by the `/v0` path prefix, and the report records the
prefix under `route_prefix_filter` so the filter is visible rather than
implicit.

## Controls (R3)

Two controls gate the report, and either failing exits 2 without a census:

- **`planted_route`** — `/v0/__control_probe__` is planted on the live app
  with `app.add_url_rule` and re-enumerated. A prefix filter that is really
  something else, or an enumeration that cannot observe a newly added rule,
  fails here.
- **`branch_count`** — the reused extractor must still return exactly **63**
  branches, guarding against a silently different branch set.
- **`enumeration_non_empty`** — the route count must be non-zero, because a
  clean zero from an unvalidated instrument is not evidence.

A "non-`/v0` rules exist" control was deliberately **not** written: there are
zero such rules in the committed app, so a negative case would assert nothing
and would fail the moment anyone added a non-`/v0` rule for unrelated reasons.
The prefix filter is constrained by the planted probe instead.

## Grounding rule (R4)

A branch is **covered** when a route handler's own source cites it with a
`command.py:NNN` line span that resolves inside that branch's span. Every such
mapping carries the citing **file**, **line**, and the **exact matched text**,
plus the branch span it resolved into. Anything that does not resolve to
exactly one branch is reported `unresolved` and never counted.

A branch name in backticks in the docstring is **not** coverage. It is
reported in full under `branches_mentioned_by_name_only`, with its verbatim
citing line, and it never reaches the headline count. The reason is concrete
rather than theoretical: a handler naming a branch frequently names it in
order to distinguish itself *from* it.

Deliberately refused as evidence:

- A route name that resembles a branch name.
- An ambiguous line span (zero or more than one branch).
- A backticked line range with **no** `command.py:` prefix (e.g. `` `76-79` ``).
  These are reported with `resolution:
  "unresolved_bare_range_without_command_py_prefix"` and carry the branches
  their range *would* have hit. This is a deliberate undercount; guessing that
  a bare range means `command.py` would be an inference, not a citation.

Note also that `command.py:NNN` citations are scanned across the **whole
handler source**, not only its docstring, because several live in body
comments and string literals. Backticked-name matching is restricted to the
**docstring** only, matching the rule as written.

### The name-only tier requires human adjudication

The 16 name-only branches are **not** covered, and they are not close to
covered. Each is a mention in a sentence; determining whether the sentence
drives the route or merely contrasts it is a reading task, and this tool does
not perform it.

**3 of the 16 are explicitly negated by their own citing text** — the citation
says the opposite of coverage:

| Branch | Citing line | Verbatim context |
| --- | --- | --- |
| `soulmixer_speedup` | `/v0/queue` L5763 | ````soulmixer_speedup`` has no action here at all: the legacy branch needs`` |
| `push_queue_unit2` | `/v0/queue` L5761 | ````push_queue_unit2`` is not in the closed set because its unit id is a`` |
| `complete_goal` | `/v0/quests` L6524 | ````complete_goal`` is delivered as a no-op on purpose.`` |

A further 5 mentions are flagged but the branch has other unflagged mentions,
so the flag alone does not settle the branch:

- `fast_forward` — 3 mentions: `/v0/quests` L6509 *"``fast_forward`` key a
  client attaches is **ignored**"* and L6551 *"**no fast-forward operation is
  delivered**"* are flagged; L6900 `/v0/research` *"the fifth is
  ``fast_forward``"* is descriptive and unflagged. The branch is a fair
  example of why the conservative headline does not use this tier: the flag
  marks sentences, not branches.
- `buy_stored_item_cash`, `research_buy_step_cash` — one negated mention each,
  plus unflagged mentions elsewhere.

The remaining 8 branches have only unflagged mentions. That still does not
make them covered: an unflagged sentence is not an affirmative one.

### Negation flagging

Each citation carries **`negation_markers`**: the members of an explicit,
short marker list found in its verbatim citing line, matched case-insensitively.

Markers: `no `, `not `, `never`, `ignored`, `unlike`, `without`, `no-op`,
`none of`.

This is a **flag, never a filter**. A flagged citation is still reported in
full — nothing is dropped, and no branch is removed from any tier on the
strength of a marker. And an **empty list is not a claim of affirmation**; it
only means no listed marker appeared. The tool is deliberately mechanical here
and the reader adjudicates.

Two controls prove the detector is not inert, and both are recorded under
`controls.negation_detector`:

- a **crafted negated** sentence that must be flagged;
- a **crafted affirmative** sentence that must not be flagged.

If the detector cannot fire on the crafted negated input, or fires on the
affirmative one, the tool **refuses to report** (exit 2) instead of emitting a
report full of confident empty `negation_markers` lists. That failure mode is
the dangerous one, because an inert detector looks exactly like evidence of
affirmation.

## Line-span resolution

Branch spans are **flat**: each branch spans from its own `if`/`elif` line to
the line before the next branch, and the last branch (`set_variables`) spans
to the end of `do_command`.

AST `end_lineno` is useless here: because the branches form one `elif` chain,
every branch reports the same end line (956). Flat spans were measured
instead and have zero overlaps.

Citations resolve by **overlap**, not containment. Containment was tried first
and is wrong: `command.py:573-623` is not an empty range, it straddles four
branches. Overlap reports it as the ambiguous citation it actually is.

## Determinism (R5)

The report is byte-identical across runs: keys sorted, lists stably ordered,
no timestamps, no absolute paths, no host or commit values. Paths are
emitted `as_posix()`, so a Windows checkout produces the same document as a
POSIX one. JSON goes to stdout only; the Compatibility API boot's own stdout
chatter is redirected to stderr so stdout carries nothing but the report.

The tests assert byte-identity between two runs, sorted keys, and that no
forbidden key (timestamp, commit, generated-at, host, cwd) appears anywhere in
the document. That last check compares **keys as keys**, not as raw
substrings: `"date"` is a substring of the report's own `"validate"` control
key, and a substring test would forbid a field the tool legitimately reports.

## Containment (R6)

- The tool builds a **disposable corpus** with
  `compat_test_harness.build_test_corpus()` and removes it in a `finally`
  block, so an exception cannot leak it.
- **It never creates a working-tree `saves/` directory and never writes a save
  byte.** A test asserts no `saves/` appears in the repository root.
- It never executes a legacy command and never calls a route handler. Booting
  the app imports the legacy `command` module transitively, because
  `compat_legacy.initialize()` constructs the legacy boot; the census only
  reads that module's AST.
- It never opens a socket, starts a server, or opens a browser or Flash
  content.
- Without `--out-path` it writes nothing: no report, no bytecode (`-B`), no
  cache, no temporary file in the repository.

### "Corpus removed" vs "corpus contents removed"

`remove_corpus()` calls
`shutil.rmtree(corpus, ignore_errors=True)`. With `ignore_errors=True` the
directory's **contents** are removed but an **empty directory can remain**.
Those are two different claims and this README only makes the first one. The
tool does not assert that the corpus directory is gone; it asserts that no
corpus contents survive. `compat_legacy.initialize()` also `chdir`s into the
corpus and never restores the working directory, so the tool saves and
restores `os.getcwd()` itself in `finally` — otherwise the corpus would be
left deleted *and* current.

## Evidence classification

This tool establishes a **source-grounded census of citations**: which legacy
branches are explicitly named by which modern route handlers, with every
mapping traceable to a file, a line, and an exact matched text.

It establishes **no** executed command, **no** gameplay parity, **no**
request/response behaviour, **no** server-authoritative validation, and
**no** progressed-player coverage. A citation is a claim about *documentation
and source*, not about runtime: a route can cite a branch and still diverge
from it in behaviour.

Specifically, it does **not** claim:

- that an uncovered branch is unimplemented, unimplemented-in-the-client, or
  unimportant;
- that a covered branch is correctly or completely reproduced;
- that a name-only mention is positive rather than contrastive — which is
  exactly why it is excluded from the headline;
- that an unflagged citation is affirmative (see above);
- that the 39 uncovered branches are a defect count. Several, such as `ping`,
  `flash_debug`, and `set_variables`, are plausibly debug or plumbing
  branches; the tool cannot tell, and does not guess.

## Known limits of the measurement

- **Bare line ranges are an undercount.** Eight `bare_line_range` citations
  with no `command.py:` prefix are reported unresolved, so up to eight
  additional branch mappings may exist that this tool will not credit.
- **A docstring citation is weak evidence of intent.** The 16 name-only
  mentions are the number to treat with most caution, and the tool refuses to
  convert them into a coverage claim.
- **The negation list is a heuristic and is not exhaustive.** It is a short,
  explicit list of words a documentation author would use to deny a branch.
  It will miss hedging that uses none of them ("`soulmixer_speedup` sits
  outside this route's action set"), and it will occasionally flag a sentence
  that merely describes a limitation elsewhere. It flags; it never decides.
- **The permissive figure is weaker than it looks.** It counts a branch as
  mentioned unless *every* mention is flagged, so a branch cited once
  affirmatively and once with a hedge still counts. That is why it is not the
  headline.
- **Branch-count and route-count baselines are re-measured, not hard-coded
  into the mapping logic**, but `branch_count` *is* pinned at 63 by control.
  Adding a 64th legacy branch will fail the control and require the pin to be
  updated deliberately — which is the intended behaviour. No coverage or
  mention count is pinned anywhere.
- **Ambiguous citations are never resolved by heuristic.** If a handler cites
  a range covering several branches, the tool reports the candidate set and
  credits none of them. Three such citations exist today.
- **`/v0/bootstrap` and `/v0/session` have no cited branch.** That is a fact
  about citations, not proof that they exercise no legacy branch.
- **Coverage is a documentation claim, not a behavioural one.** A line span
  proves a handler author cited specific legacy lines. It does not prove the
  route reproduces that code, and it says nothing about the Flash client.