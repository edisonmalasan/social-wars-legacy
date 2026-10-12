# Server v1 — the authoritative API

`apps/server-v1/` is the modern server. It is **not** a port of the legacy Flask
application: it is the first surface built around an authority boundary the
legacy server does not have.

The legacy server applies a client-sent resource vector before it dispatches
anything (`command.py:40`, an unconditional `apply_resources`) and answers
`{"result":"success"}` unconditionally (`server.py:320-322`). Every one of its 63
command branches inherits both properties. That is the defect this directory
exists to not reproduce, and it is why the first deliverable here is a
**boundary** rather than an endpoint.

The Compatibility API v0 (`apps/compat-api/`) stays in place and is v1's parity
oracle. It is 5,752,183 bytes across 122,022 lines and 24 routes, against
51,275 bytes and 1,572 lines for `command.py` + `engine.py` + `server.py`
together — more than a hundred times the legacy surface. v0 is not deleted; it
is retired per domain, later, once each domain has a verified v1 replacement.

## What exists today

Two routes.

| | `collect` | `collection` |
| --- | --- | --- |
| Route | `POST /v1/collect` | `POST /v1/collection` |
| Request | `{"player_id": <uuid>, "row": <int>}` — intent only | `{"player_id": <uuid>, "collection_id": <int>}` — intent only |
| Derives | a payout rung from committed `COLLECT_MINUTES` | a price, a requirement set and a prize from committed `collections` |
| Charges | nothing (a payout) | `cashPrice` (a **debit**) |
| Mutates | `maps/0/items/<row>/3` | `maps/0/store/<prize>`, `playerInfo/cash`, `privateState/collections` |
| Refusals | `409`, plus `400`/`404`/`500` | `409`, plus `400`/`404`/`500` |

Shared for both: a `200` carrying `result`, `action`, the derived figures, and
`protocol`; a gameplay refusal as `409` with `result: "refused"` and a `code`; a
structural refusal as `400`; an unknown player as `404`. Loopback
`127.0.0.1:5057`, no host option; protocol name `server-v1`.

`ROUTES` in `server_v1_app.py` is the inventory, `run.py`'s startup banner reads
that same mapping rather than transcribing it, and `tests/test_app.py` asserts the
set has exactly these two entries.

## Layering

```
run.py              process, port, exit codes, containment
server_v1_app.py    transport: parse intent -> call domain -> serialise outcome
server_v1_intent.py the boundary: refuses any client-dictated outcome field
server_v1_collect.py the first slice: decide, act, prove
server_v1_collection.py the second slice: a grant, not a payout
server_v1_economy.py the ONLY place a resource delta is derived
server_v1_outcomes.py typed success (requires a derivation) / typed refusal
server_v1_refusals.py the closed refusal vocabulary and its status table
server_v1_repository.py save access, preserving fields v1 does not model
server_v1_content.py committed content access, with provenance
server_v1_corpus.py disposable corpora and containment helpers
server_v1_settings.py protocol name, host, port, exit codes
```

Design **D2** is the load-bearing decision: the boundary is a domain service, not
route middleware. Middleware would have let a second route be added without
re-deciding who is allowed to move a balance. Here, adding a route means calling
`derive_collection_payout` or writing another derivation beside it, and the AST
invariant test in `tests/test_boundary_invariant.py` fails if a second
`ResourceDerivation` call site, or any `CollectionGrant` construction outside the
economy, appears anywhere in the directory.

## Verified commands

Run from the repository root, with the pinned CPython 3.9.13 on the path.

```bash
python -B -m pip install -r requirements.txt
python -B -m pip --isolated check
python -B -m unittest discover -s apps/server-v1/tests -p "test_*.py"
python -B apps/server-v1/run.py --fixed-now=1790705901
```

Observed on 2026-10-12, Windows x64, CPython 3.9.13:

| Command | Result |
| --- | --- |
| `pip install -r requirements.txt` | exit 0 |
| `pip --isolated check` | exit 0, `No broken requirements found.` |
| the unittest discovery above | **210 tests**, exit 0 |
| `run.py --fixed-now=…` | binds 5057, prints a JSON banner, serves, and on `CTRL_BREAK_EVENT` removes the corpus it built and exits 0 |

### Serving it by hand

```bash
python -B apps/server-v1/run.py --fixed-now=1790705901
```

It prints a JSON banner naming the protocol, host, port, corpus, content
provenance and routes, then serves. `Ctrl-C` in that console stops it cleanly.
`--fixed-now` pins the clock so a transaction can be compared against the
executed-legacy fixture's recorded capture instant; with no flag it reads the
real clock, which is its production behaviour. `SERVER_V1_CORPUS=<dir>` serves an
existing corpus instead of building one, and does not delete it.

Exit codes: `0` clean, `2` environment unusable, `3` the port is not free, `4`
the server exited with an error.

## What the boundary refuses, and why

A v1 request carries **intent**. It never carries an outcome. A body containing
`gold`, `wood`, `xp`, `resources_changed`, `hp`, `damage`, `result`, or a
`delta_`/`_delta`/`_amount`/`_value` variant of any of them is refused with
`400 client_supplied_delta`, and nothing is written.

The recognition is a closed vocabulary — `DELTA_KEYS` and `DELTA_MODIFIERS` —
checked in both orders, so `gold`, `wood_delta`, `delta_wood` and `gold_value`
are all caught. It is refused, never clamped, coerced, or ignored: clamping would
invent a rule the legacy server does not have, and ignoring would tell the
client its request succeeded.

Two further guards are refused rather than implemented, because the legacy
server has neither and inventing one would be fabrication:

- a non-zero committed `max_collects` is refused (`capped_collection`);
- a recorded collection instant in the future is refused (`unreadable_state`).

## The two-part post-execution proof

`server_v1_collect._prove` runs after the write and raises
`PostConditionViolation` if either half fails:

1. **the collection instant moved strictly forward** — not merely "changed", so
   an instant that moved backwards fails;
2. **every stored resource changed by exactly the derived delta** — over the
   *complete* stored set, so a resource absent from the derivation must be
   unchanged and a store that quietly also moved gold fails.

Half two is what makes the pair non-tautological: a derivation that moved
nothing cannot satisfy half one, and a derivation that moved the wrong amount
cannot satisfy half two. Both halves were proven sensitive by injection, not
trusted; see the correction notes in `tests/test_parity_v0_collect.py` and
`tests/test_collect.py`.

## The collection grant: four derived rules

`server_v1_collection` replaces a fourteen-line branch (`command.py:504-523`) that
grants a committed prize **unconditionally** and appends to the ledger only if the
id is absent. v1 adds three rules the branch does not have, each in a recorded
fixed order — alias/unresolvable id, content readability, already claimed,
eligibility, affordability — so every refusal is independently reachable:

| Rule | Source | Status |
| --- | --- | --- |
| alias (id `< 1` clamps to collection 1 through `max(0, id-1)`) | the branch's own index | **derived** (design D3) |
| eligibility (`hold every committed item_ids`) | committed `collections.item_ids`, **zero legacy consumers** | **derived** (design D4) |
| price (`cashPrice`) | committed `collections.cashPrice`, **zero legacy consumers** | **derived** (design D5) |
| once-only (`privateState.collections`) | the branch's conditional append | **derived** (design D6) |

Because none of the four was observed from the Flash client, each is a
**divergence** from the preserved branch and never parity. `CollectionGrant` is a
separate derivation type rather than a `ResourceDerivation` with a negative delta:
`ResourceDerivation` forbids negative deltas by construction, and a collection has
no ladder, no rung and no elapsed time.

Its post-execution proof has **four** halves — granted quantity, no unexpected
storage key besides the granted one, every stored resource moved by exactly the
derived delta, and the ledger exactly one longer — each proven sensitive by
injection in `tests/test_collection.py`, and each rolled back on failure.

**A recorded limit:** the proof does **not** catch a stored key that *vanishes*.
`server_v1_collection._prove` says so in its own docstring, and
`tests/test_collection.py` asserts the behaviour rather than quoting the claim,
so the day the gap is closed the test fails and the docstring must move with it.

## Evidence

| Path | What it is |
| --- | --- |
| `docs/legacy-m13-authority.md` | the committed investigation the whole milestone is scoped by |
| `docs/legacy-m13-collect-v1.md` | which collection rules are **established** and which are **derived**, with the rejected alternative for each derived rule |
| `docs/legacy-baseline.md`, "Server v1 additions" | the pinned versions and their verification evidence |
| `tests/fixtures/godot-building-collect/` | the executed-legacy oracle: one `collect` transaction |
| `apps/server-v1/tests/test_parity_v0_collect.py` | the comparison against those **captured bytes**, not a re-capture |
| `tools/route-coverage/` | 24 of 63 legacy branches covered by a v0 route; **39 uncovered** |

## Claim limits

- **One route, one transaction, one corpus.** The parity comparison covers a
  single recorded `collect` against the fresh-player corpus. No
  progressed-player save exists and no other row has been compared.
- **No payout figure is a parity claim.** The payout grows in four committed
  rungs derived from committed income fields; it is never a claim about any
  specific amount the legacy client paid.
- **No price, cost, or fee is charged**, and `mana` can never be paid by this
  derivation.
- **No cap semantics, level gate, quest tie-in, or permission check** exists,
  because the legacy server has none to reproduce.
- **The save shape is not migrated.** SQLAlchemy and Alembic are deferred to M14
  by design D4; access is through a repository seam over the committed document.
- **No client transport is delivered for v1 yet** beyond what registers
  `ServerV1Api` behind the `GameApi` facade.
- **The other 39 uncited legacy branches are not covered by this line**, and no
  claim here touches them.
- **`tests/test_live_server.py` is the only module that binds a socket.** It is
  also the fifth recorded flaky surface in this repository: a `TIME_WAIT` entry
  left by a recently killed v1 process can stop it binding `5057`, which is why
  its release assertions use a connect probe rather than a bind probe. Re-run
  before treating a failure there as a regression.

## No Flash

Nothing in this directory, and no command documented above, executes Flash,
Ruffle, ActionScript, a SWF, or a browser. The only network traffic is loopback.
