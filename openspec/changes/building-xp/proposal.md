# Proposal

## Why

M7's first ten deliver lines are delivered and archived. With placement, purchase,
move, sell, store, upgrade, construction, collect income, town expansion, and
resources in place, a player can build, upgrade, watch a build finish, collect
income, and expand the town — and can see their resources, which the resources line
made true for the first time. What the loop does not yet express is **why** the player
is doing it: the town carries `maps[0].xp` and `maps[0].level`, the readout shows both
as bare numbers, and nothing anywhere connects experience to a level. XP basics closes
that, and it is the last of the eleven M7 deliver lines.

The contract was established by investigation and is committed as
`docs/legacy-xp-basics.md` (PR #198). The finding that shapes the change is that **the
legacy server is almost entirely absent from this area, and the content that does exist
is complete and unused**:

- **`level_up(new_level)`** (`command.py:81-85`) is one line of state change —
  `map["level"] = new_level` — with **no range check and no XP validation**. A client
  can set any level, including 99, and the server answers `{"result":"success"}`.
- **`add_xp_unit`** is *unit* experience on an item's attribute bag, and **of the 40
  placed corpus rows, 0 carry `attr["xp"]`** — the fresh save has no unit placements at
  all, so the path cannot be exercised.
- **Nothing in the legacy server reads the committed `levels` schedule.** Zero
  references across `command.py`, `engine.py`, `sessions.py`, `server.py`, and
  `constants.py`. The level curve is content the **client** owns entirely: the server
  neither derives a level from experience nor validates one against the curve.

That absence is precisely what makes this line's guard possible. The collect and expand
lines could only refuse what the evidence did not support; here the evidence *does*
support a guard, because the curve that constrains the level is committed content and
the corpus proves its index base.

## The one consequential decision: the index base

The curve's 100 entries have `exp_required` **strictly increasing** with no duplicates
and no non-positive gap (`0, 40, 60, 100, 200, 350, 550, 800, …` to `2016089205`). Two
readings of its index are possible and they disagree by one level — `map["level"]` as
the index (0-based), or stored level *n* being `levels[n - 1]` (1-based).

**The committed corpus decides between them, and 0-based is contradicted:**

```
corpus xp = 4 | stored level = 1 | level the 0-based curve implies = 0
```

Under 0-based, a player with 4 experience is recorded as level 1 while the curve says
level 1 begins at 40 experience. Under **1-based**, stored level 1 is `levels[0]` —
`"Slave"`, `exp_required` 0 — and `4 >= 0` holds, so the corpus is self-consistent.

This is the most consequential decision in the line: guessing 0-based would shift
**every** level in the game by one, and the error would stay invisible until a player
noticed the wrong level name. The evidence is one data point in a hand-built corpus, so
the resolution is **derived-provisional** — but it is derived from the only evidence
there is, and the rejected 0-based alternative is **actively contradicted** rather than
merely unsupported. Both facts are recorded in the provenance and the claim limits, and
the conversion lives in **exactly one named place** so a later change can revisit it
with better evidence by editing one function.

## What Changes

- **A committed-curve level model** — a pure client-side module reading the normalized
  `levels` schedule with the 1-based conversion in one named function, exposing the
  player's derived level, its name, the next threshold, and the progress toward it.
- **A level and progress readout** — the current level, its name, experience, the next
  level's requirement and how much remains, so the loop's progression is legible.
- **Explicit disagreement reporting** — the stored `level` is treated as **unverified
  against the curve**, not authoritative. When the stored level and the level derived
  from the stored experience disagree, the readout **says so** rather than smoothing it
  over or silently trusting either value.
- **A guarded level-up endpoint** — `POST /v0/level_up` on Compatibility API v0
  accepting only the intent `{user_id}`, **deriving** the allowed target level
  server-side from the stored experience and the committed curve. A client-supplied
  level outcome is never trusted; any attempt to send one is ignored, exactly as the
  collect and expand endpoints ignore client-supplied amounts. A request for anything
  but the derived level fails closed with a structured error and a byte-identical
  corpus, and success requires that the stored level moved to exactly the derived value
  while every stored resource is unchanged.
- **A typed GameApi operation** — `GameApi.level_up_town()` on both implementations
  (`FakeApi` as the deterministic double, `LegacyV0Api` over loopback JSON), with a
  typed result carrying the derived level, the stored level before and after, the curve
  facts used, and the resources.
- **Client flow, tests, live verification, and evidence** — an eighth mutually
  exclusive client mode, a hermetic suite, a `level-up-live` battery phase proving a
  disposable corpus save mutates, and a windowed capture plus a deterministic
  `xp-report-v1` report whose provenance section names the index base as
  derived-provisional with its rejected alternative.

### Explicitly not in this change

**Level rewards.** `reward_type` and `reward_amount` are committed on every curve
entry, and **no legacy branch reads either**. Paying them would invent an economy, so
they are refused rather than implemented — the same discipline the expansion
`neighbors`/`inventory_qte` requirements received.

**Unit XP behavior.** `add_xp_unit` cannot be exercised: the committed corpus has no
unit placements and 0 of 40 placed rows carry `attr["xp"]`.

**Tutorial progression.** `complete_tutorial` is a separate progression system with its
own semantics and no bearing on the town-building loop.

**XP rebalancing.** The committed `exp_required` values are preserved verbatim; no
tuning is proposed or performed. Also out of scope: `name` treated as an identifier
(it is not — 44 distinct names across 100 entries), server-authoritative validation
beyond this one guard (Server v1 / M13), and any change to the ten delivered lines'
behaviour. Legacy sources, configs, saves, villages, committed fixtures, conversion
packages, registry manifests, and every delivered slice's evidence stay byte-identical
(existing SHA-256 guards plus the hash manifest). No Flash, Ruffle, ActionScript, or
browser executes, and no external network is used.

## Capabilities

### New Capabilities

- `godot-building-xp`: the player's progression through the committed level curve — a
  curve model with the 1-based conversion in one named place, a level and progress
  readout, **explicit stored-versus-derived disagreement reporting**, a
  `POST /v0/level_up` endpoint that derives the allowed level server-side from the
  stored experience and refuses any client-dictated outcome, a typed
  `GameApi.level_up_town()` operation, an eighth mutually exclusive client mode, and
  the evidence, containment, provenance, and claim limits — including the index base
  as derived-provisional with its **actively contradicted** 0-based alternative.

### Modified Capabilities

- `godot-compatibility-boot`: the bootstrap-service requirement names all ten
  state-mutating gameplay capabilities (`godot-building-xp` added), and the `GameApi`
  abstraction requirement gains the typed `level_up_town()` operation with an "Level up
  through either implementation" scenario and the rule that the client never supplies a
  level outcome.

## Impact

- **Compatibility API v0** — a new `apps/compat-api/level_envelope.py` deriving the
  `level_up` batch envelope from the committed curve and the stored experience, content
  accessors in `compat_legacy.py` for the curve and its entry count (mirroring the
  delivered `item_upgrade_to` / `expansion_price` patterns), a `POST /v0/level_up`
  route in `compat_service.py`, a new `apps/compat-api/capture_level_fixture.py`, and
  new compat tests (envelope, endpoint, executed-legacy replay).
- **Legacy** — unchanged and read only: `command.py`, `engine.py`, `constants.py`,
  `sessions.py`, `config/`, `villages/`, `tests/saves/`, and every committed fixture.
- **Godot client** — a new `scripts/town/level_flow.gd` pure helper, an eighth mode and
  a readout in `scripts/town/town.gd`, `scripts/gameapi/{boot_data,game_api,fake_api,legacy_v0_api}.gd`,
  a new `tests/test_town_xp.gd`, scope-test allow-list entries, and the new evidence.
- **Verification** — `verify-boot.ps1` gains the hermetic XP suite and the
  `level-up-live` phase; the guard baseline, the hash manifest, and both batteries must
  stay green with no new packages and no non-loopback traffic.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`,
  `apps/compat-api/README.md`, the updated `docs/legacy-xp-basics.md`, the new fixture
  README, and the roadmap Project Status ledger.