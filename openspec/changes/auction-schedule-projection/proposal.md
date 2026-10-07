# Proposal

## Why

The M11 deliver item `legacy event systems` names exactly one system in the
preserved source, and the measurement committed in
`docs/legacy-m11-event-systems.md` shows it is not merely switched off — it
cannot start. `auctions.py:32` guards on `FILE_AH_CONFIG` while `:33` reads
`FILE_AH_STATE`, so `AuctionHouse()` raises `FileNotFoundError` on any machine
holding the committed config and no leftover state. That is why `auctions/` is
absent from the repository.

The surface is therefore doubly unreachable: three fully-written routes and the
module import are all commented out, **and** the module cannot bootstrap even if
they were not. Neither fact is recorded anywhere in the specs, and the committed
content (`config/auctionhouse.json`, 3 auctions naming real endgame units) has
never been normalized, so it is invisible to the client by construction.

This change delivers the committed schedule and the measured module semantics as
a **read-only projection with explicit refusals**, so that a future line does not
rediscover the surface, mistake a dead declaration for a live one, or
reproduce the client-dictated price as if it were parity.

## What Changes

- Normalize `config/auctionhouse.json` into the committed content package as a
  new `auctions` section, with a schema, round-trip evidence and a manifest
  merge, following the existing `*-normalization` capability family.
- Add a client-side read-only projection of the committed auction schedule:
  the three auctions, their resolved unit names, the derived duration, and the
  recorded expiry semantics.
- Derive exactly one value — the auction duration — from committed content, via
  a single named minutes-to-seconds conversion, as `godot-building-collect` did
  for `COLLECT_MINUTES`.
- Record, and refuse to reproduce, the measured behaviours that constitute the
  "Bad" client-dictates-the-outcome pattern in `AGENTS.md`: the client-sent bid
  amount stored unvalidated, the client-sent `checkFinish` gating `betWinner`,
  and the discarded `count_expired`.
- Record the bootstrap defect as a **property of the oracle**, so a future
  implementation cannot silently "fix" it and claim parity.
- **No route, no `apps/compat-api/**` change, no live phase, and no executed
  legacy fixture.** The fixture is refused for a specific, measured reason rather
  than a missing corpus row — see the design's recorded decisions.

### Revision to the committed contract, recorded rather than drifted past

`docs/legacy-m11-event-systems.md` §12 listed "normalizing
`auctionhouse.json` into the content package" as **out of scope**, with the
caveat "unless a proposal says otherwise". This proposal is that case, and the
reason is a dependency rather than a preference: the Godot client reads committed
content **only** through the normalized registry (`godot-content-registry`), so a
client projection has nothing to read until the table is normalized. Delivering
the projection without it would introduce a second, parallel path into committed
content and contradict the architecture established since M4. The remaining
§12 exclusions — no route, no compat change, no live phase, no fixture — stand
unchanged.

## Capabilities

### New Capabilities
- `auction-schedule-normalization`: Normalize the committed `config/auctionhouse.json`
  into the content package as an `auctions` section, with a schema, a documented
  coercion ruleset, cross-domain reference resolution against the normalized
  items, exact round-trip evidence, and a manifest merge that leaves every prior
  section untouched.
- `godot-auction-schedule`: Project the committed auction schedule read-only
  through the normalized registry — entries, resolved units, the derived
  duration, and the recorded expiry semantics — reporting the measured refusals
  and never deriving a price, a round, or a winner.

### Modified Capabilities
<!-- None. No existing requirement changes: the auction surface is owned by no
     capability today, and `godot-social-state` / `godot-friends` /
     `godot-construction-assist` do not mention it. The endpoint catalog and
     command catalog already classify the disabled routes and the `buy_powerups`
     stub correctly and are not contradicted. -->

## Impact

- **New** `packages/game-content/tools/build_auctions.py`, its schema, its unit
  tests, and `packages/game-content/normalized/auctions.json` plus a new
  `auctions` section in the package manifest.
- **New** Godot client modules under `apps/client-godot/scripts/social/` (or a
  sibling path chosen in design) implementing the projection, plus the
  hermetic suite and the committed evidence report.
- **Extended** `packages/game-content/tools/validate_content.py` output count and
  `tools/hash-manifest` coverage, both of which are expected to move.
- **Unchanged**: all eleven legacy root modules, `config/auctionhouse.json`,
  every save and fixture, `apps/compat-api/**`, and the content of every
  existing normalized file.
- **No network, no Flash, no Ruffle, no ActionScript, and no browser** executes
  in any command of this change.