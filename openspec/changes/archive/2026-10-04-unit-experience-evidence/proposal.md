# Proposal

## Why

Seven delivered locations tell the reader that unit experience is out of scope **"because the
corpus cannot exercise it"** — five enumerated by the investigation and two more that only Apply
found. That reason is false. The legacy branch does mutate: `add_xp_unit`
(`command.py:322-343`) writes `attr["xp"]` on a placed row, and **22 executed-legacy
transactions** against an authentic committed village save — recorded in
`docs/legacy-unit-xp.md` and committed nowhere in a fixture — establish how. The field is not
absent from the repository's evidence either: it appears on **171 of 12,954** placed rows
across **all 31** committed save documents, in 5 of 31. The refusal itself is correct and stays
correct — **no trusted award exists**, and none is invented — but the *reason* recorded for it
is wrong, one of the wrong statements is a **user-facing string**, and the branch now has
behaviour with no committed fixture.

## What Changes

- **A committed executed-legacy fixture for `add_xp_unit`**, captured against
  `villages/AcidCaos.json` — the repository's first capture seeded from a village save rather
  than from `tests/saves/fresh-player.json`. It records the increment arm, the assign arm, the
  missing-row early return that still answers `success`, the absent clamp, the absent bound, the
  persisted float, the type-agnostic building row, the display-only third argument, and the
  two failing-type cases. Containment unchanged, loopback only, re-runnable.
- **One defaulted parameter on the shared capture harness**, `build_disposable(seed_path=
  FRESH_PLAYER_SAVE)`, so the new capture can pass a village save. All 17 existing call sites
  pass a single positional argument and are therefore unaffected.
- **A fail-closed refinement to the existing read-only projection**
  (`production_flow.gd::experience()`): the recorded value is reported verbatim *and* its kind is
  reported, so a bag poisoned by the legacy server's own string write (`{"xp": "5"}`, proven
  reachable) is **visible** rather than read as an integer.
- **Seven corrected stale statements** in `level_flow.gd` (its first doc line, two doc comments and
  the user-facing note string), in `town.gd`, and in `AGENTS.md` / `apps/client-godot/README.md`,
  each reframed from *"the corpus cannot exercise it"* to *"no trusted award exists"*, with the
  corpus figure retained and labelled as a corpus fact, the repository-wide figure added, and a
  pointer to this capability. A tree scan pinned to zero expected hits keeps a new one from
  appearing — the count grew from five to seven during Apply, which is the argument for the scan.
- **One wording-precision fix** where a hermetic assertion message says "NOT ONE **committed**
  row" while its scope is the 40-row fresh corpus — the assertion is true, the phrasing is
  broader than its scope.

Explicitly **not** in scope, and named here so a later reader does not infer otherwise:

- **No endpoint, no route, no client intent.** An endpoint would either repeat the
  untrusted-amount anti-pattern or exist only to refuse, and `godot-research` set the precedent
  that a write-only counter whose only writer is client-sent does not warrant one.
- **No award, no threshold, no unit level, no XP schedule.** `units[].xp` is refuted as the
  award by three independent arguments, and no committed per-unit level schedule exists.
- **No change to the level-reward refusal.** `reward_type`, `reward_amount`, and
  `level_ranking_reward` have committed information and zero legacy consumers; nothing is paid
  and nothing is invented.
- **No compatibility test expectation is changed.** The compat suite **grows**; the delivered
  refusal requirements are untouched.

## Capabilities

### New Capabilities

- `godot-unit-experience`: The executed-legacy evidence for the `add_xp_unit` branch — its
  committed fixture, the accepted-and-refused input shapes it establishes, the read-only
  fail-closed projection of a recorded row experience, and the preserved refusal to award
  experience from a client amount.

### Modified Capabilities

- `godot-unit-production`: its "no experience is awarded from a client amount" requirement
  currently records only the fresh corpus's absence of the field. It SHALL now record that
  absence as a **corpus fact distinct from the repository evidence**, and point to
  `godot-unit-experience` for the executed behaviour — the same amendment shape this capability
  already uses for `godot-unit-behaviors`.
- `godot-building-xp`: its XP-evidence requirement states unit experience and tutorial
  progression are "out of scope **because the corpus cannot exercise them**". The unit-experience
  reason SHALL become the untrusted-amount one (the corpus figure retained as a corpus fact), the
  tutorial half SHALL be dropped because `godot-tutorial` delivers it, and the requirement SHALL
  point to `godot-unit-experience`.

## Impact

- **Compatibility layer** (`apps/compat-api/`): one new `capture_*_fixture.py`, one new
  fixture-integrity test module, and **one added defaulted parameter** on
  `capture_legacy_fixtures.py`. **No envelope module**: an envelope in this project derives a
  request from a client intent for a route, and this line has no route, so adding one would
  invent a request shape. No route, no response field, no error code, no save-shape
  expectation. The suite grows from 2,130 tests; no existing expectation changes.
- **Client** (`apps/client-godot/`): a refinement to `production_flow.gd::experience()`, three
  corrected statements in `level_flow.gd`, one new hermetic suite, and one new entry in
  `verify-boot.ps1`. No new scene, no autoload, no rendered output.
- **Evidence**: a committed fixture under `tests/fixtures/`, a deterministic
  `unit-experience-report-v1` report under `apps/client-godot/evidence/unit-experience/`.
- **Preservation**: `villages/`, `tests/saves/`, committed fixtures, the content package, the
  conversion packages, and the legacy root remain byte-identical. No Flash, Ruffle,
  ActionScript, or browser executes. No non-loopback traffic.
- **No windowed capture** is claimed, because nothing is rendered.