# Design

## Context

See `proposal.md` — Why. This is the sixth change in the same family and the
first one whose contract had to be *established* rather than chosen. The
investigation is recorded here in full so the provenance of every value is
traceable, and so a later change does not have to repeat it.

### Established from committed legacy source

| Fact | Evidence |
| --- | --- |
| There is no upgrade command | 63 named `command.py` dispatcher branches (`docs/legacy-protocol/commands.json`); none named `upgrade`, and the only branch consuming a second argument as a reason is `sell` (`command.py:149-168`) |
| The upgrade sell reason is `"UPGR"` | `constants.py:970` `SELL_REASON_UPGRADE = "UPGR"`, committed legacy server source |
| A purchase can reuse an exact map key and cell | `command.py:42-58`: `buy` takes `[item_index, item_id, x, y, playerID, orientation, unknown, reason]` and writes `map_add_item(map, item_index, item_id, x, y, orientation=…, player=…)` — the **key** and cell are client-supplied |
| A purchase writes a *fresh* row | `engine.py:10-34`: `map_add_item` defaults `timestamp` to `timestamp_now()`, `store` to `[]`, and, when `player == 1` and the item's config has `clicks_to_build > 0`, seeds `attr["nc"] = 0` (the click-to-build counter) |
| A purchase records the new tier | `command.py:52-53`: `buy` with `playerID == 1` calls `bought_unit_add(save, item_id)` |
| The target tier is in the config | every item carries `upgrades_to`; the normalized package documents `-1`/`0` as "none" and resolves other values against the item set (`packages/game-content/tools/build_items.py:547-550`); Wall I (23) → Wall II (24) |
| No upgrade price exists | item `cost` is `"0"` and `cost_type` is `null` across all 778 items (dead fields), `costs` prices the *purchase* only, and the 139 `premium_upgrade_costs` entries (`{"c":20}`, mostly unique decorations such as "Nice fountain", "Orange Tree", "Chickens") belong to the premium path, whose relationship to the normal upgrade is unproven |
| The client gates upgrades | static SWF inventory (no execution): `CmdUpgrade`, `PopupUpgradeBuilding`, `btnUpgrade`, `btnUpgradeCash`, `upgradeinfo`, `getUpgradeBuilding`, `upgrades_to`, `premium_upgrade`, `premium_upgrade_costs`, `numUpgradesToday`, `lastUpgrades/`, `upgradeDateString`, `"No space to upgrade"`, `"You need to be level #0# to upgrade this building."`, `"Upgrade instantly for"` (matching the `UPGRADE_SPEEDUP_PRICING` global), plus tutorial copy ("Let's upgrade our CC!", "UPGRADE TO WALL III") |

### Established by executing the real legacy server

Both probes ran the real `server.py` on `127.0.0.1:5055` inside a disposable copy
under the system temp root (seeded from `tests/saves/fresh-player.json`), wrote
nothing into the repository, and removed the copy on exit. They are throwaway
scripts, not committed tools; the committed capture tool re-records the same
transaction as the parity oracle.

1. **Sell-then-buy, same key and cell** — batch
   `[[0,"sell",[12,"UPGR"],[0,0,0,0,0,0,0,0]],[0,"buy",[12,24,45,49,1,0,0,""],[0,0,0,0,0,0,0,0]]]`
   → HTTP 200 `{"result":"success"}`; slot 12 `[23,45,49,0,0,[],{},1]` becomes
   `[24,45,49,<timestamp>,0,[],{"nc":0},1]`; `boughtUnits` `[]` → `[24]`; the
   placement count stays 40; every other row is byte-identical; `store` stays
   `{}`; the rest of `privateState` and all of `playerInfo` are byte-identical;
   `xp 4`, `gold/wood/oil/steel 2000`, `cash 5` unchanged.
2. **Buy-then-sell (reverse order)** → HTTP 200 `{"result":"success"}` **and the
   key is absent afterwards** (40 → 39 placements, `boughtUnits` still `[24]`).

Probe 2 is the decisive design constraint: legacy answers `success` for a batch
that *destroys* the building, so the order is forced (sell first) and a
success-status check is not evidence of an upgrade. Every artifact of this change
therefore carries a post-execution proof of the derived post-state.

## Goals / Non-Goals

**Goals:**

- One executed-legacy two-command upgrade transaction captured from the real
  legacy server, committed with full before/after state, manifest, and README.
- One intent-only v0 endpoint that derives both legacy commands, executes the
  unchanged dispatcher in-process over the service corpus, and answers with an
  authoritative superset naming both sides of the replacement.
- A post-execution proof strong enough to reject the reverse-order outcome that
  legacy itself reports as a success.
- One typed `GameApi.upgrade_building()` operation with the fake/live
  implementations interchangeable behind it.
- An upgrade confirm on the delivered selection-driven surface with exactly one
  intent, cancellation with no state change, and an authoritative apply that rolls
  back completely on any failure.
- Evidence, provenance, claim limits, documentation, and battery integration
  matching the delivered lines.

**Non-Goals:**

- **The construction timer.** The buy half seeds `attr = {"nc": 0}` for items with
  `clicks_to_build > 0` and stamps a fresh `timestamp`; consuming either is the
  `activate` / `add_click` / `activate_item_click` / `buy_si_help` / `finish_si`
  family, which the roadmap's next M7 line (construction timers) owns. This line
  shows the upgraded building as immediately present with no timer.
- **The premium upgrade path** (`premium_upgrade_costs`, `btnUpgradeCash`,
  `CmdPremiumUpgrade`): a distinct price class with no recorded relationship to
  the normal upgrade.
- **The client's level gate and daily-upgrade limit** — see D6.
- The storage round trip, `orient`, `collect`, town expansion, resources, XP, and
  any server-authoritative validation (Server v1 / M13).

## Decisions

**D1 — The contract is one legacy batch with two commands, in this order: `sell` then `buy`.**
`sell` carries the committed upgrade reason `"UPGR"`; `buy` carries the target
tier id, the row's own key and cell, the row's orientation and player, and the
documented placeholders. Alternatives: a single `upgrade` command — it does not
exist in the dispatcher, so it would hit the unhandled fallthrough and change
nothing; `store_item` + `place_stored_item` (a storage round trip) — that changes
the map key, the timestamp, and the bought-units list differently, and the storage
round trip is a separate deferred candidate; a client-side transformation with no
command at all — that cannot change the save, so the server would never learn about
the new tier. What remains **derived-provisional** is that the Flash client sends
exactly this pair (never observed); what is *established* is that this is the only
shape the committed server can implement an upgrade with, and that it executes
correctly.

**D2 — Intent-only contract `{user_id, item_index}`; the endpoint derives everything else.**
The target tier comes from the committed configuration's `upgrades_to` (resolved,
with `-1`/`0` and unresolvable values meaning "no path"); the reason comes from
`constants.py`; the cell, orientation, and player come from the row being
replaced. The client therefore cannot name a target tier, a reason, a cell, a
price, or a quantity. The buy's `unknown` and `reason` arguments are the same
documented placeholders the placement line already uses (`0` and `""`).

**D3 — Fail closed on a missing upgrade path, and prove the post-state.**
A placement whose item has no resolvable next tier answers a structured
`no_upgrade_path` error (400) before the dispatcher runs — a row that cannot be
upgraded must never become a bare sale. After execution the endpoint requires all
three facts: the key still exists, its item id equals the derived target tier, and
its cell equals the pre-execution cell. Any other outcome is a 500
`internal_error` fail-closed, which is exactly what catches the reverse-order
outcome legacy would have reported as a success.

**D4 — Neutral price vector; no upgrade cost is claimed.**
The derived `resources_changed` is the all-zero vector for both commands, the same
boundary the move, sell, and store lines took: the server computes no price, no
config field prices an upgrade, and a client-sent delta would let any client mint
resources. The change therefore claims neither that upgrading costs the target
tier's `costs`, nor the difference between tiers, nor anything about
`premium_upgrade_costs`.

**D5 — The new row's semantics are documented, not "fixed".**
The buy half writes a fresh row: a new `timestamp` (wall-clock, the documented
time-dependent field in the fixture), `store: []`, and `attr` seeded with
`{"nc": 0}` when the target's config has `clicks_to_build > 0` — which is Wall II's
case — plus `boughtUnits` gaining the target tier. The replaced row's timestamp,
attr, and store are **not** carried over. Reproducing that exactly is the point:
the upgraded building is present and unfinished, and the timer line will consume
`nc`. The client displays the tier change and the timer seed, and claims nothing
about how long a build takes.

**D6 — Three legacy-client rules are deliberately not implemented here, and that
is a recorded gap, not an oversight.**
The static evidence names them: a level gate ("You need to be level #0# to upgrade
this building."), a daily limit (`numUpgradesToday`, `lastUpgrades/`), and a space
check ("No space to upgrade"). None is enforced by the legacy server, and none can
be reproduced from the repository: the gate's semantics (which level field, and
whether it is the target's `min_level`) are unobserved. The level gate is also
*inexercisable on the committed corpus*: the fresh save's `maps[0].level` is 1 and
**no** item's next tier has `min_level ≤ 1` (the lowest is 5, Turret II), so
enforcing the gate would make the whole deliver line unreachable on the corpus the
project preserves. The space check is vacuous for this contract, since the same
key and cell are reused. Each rule is named in the delta's non-claims with its
evidence, and the level gate is listed as an explicit follow-up.

**D7 — Validation split carried forward.** The client owns the gameplay rules
legacy never enforced — an upgrade is offered only for a selected addressable
placement that has an upgrade path, and the confirm is the only way to reach the
intent — while the endpoint keeps structural fail-closed validation (resolvable
save, integer index present in the save, a resolvable upgrade path) plus the
post-execution proof. Authoritative validation remains Server v1 (M13) work.

**D8 — One shared envelope derivation, one more mode on the selection-driven
surface.** `upgrade_envelope.py` imports the shared helpers from
`placement_envelope` and adds only `build_envelope(item_index, target_item_id, x,
y, player, orientation, reason="UPGR", unknown=0, ts=None)` producing the two
commands. The `Upgrade` action joins `Move`, `Sell`, and `Store` on the delivered
surface with a confirm naming both tiers; the four modes stay mutually exclusive
and every delivered mode's behavior is unchanged.

**D9 — Evidence, claim limits, and containment.** A windowed fake-API capture
driving the same flow a player uses (select, upgrade, confirm) plus a headless
deterministic `upgrade-report-v1` report (inputs and digests, the intent, both
rows and both tiers, the bought-units change, counts and resources before/after,
request counts, the projection-constants pointer, and explicit non-claims),
byte-identical across reruns. Execution and containment carry forward unchanged:
unchanged legacy `command()` in-process over a disposable corpus, loopback only,
no new packages, both batteries plus the guard baseline and the 3,258-entry hash
manifest green in the final state, and the orchestrator-run integration review as
the fallback for the unavailable dedicated verification workflow.

## Risks / Trade-offs

- **The composition is derived, not observed** → the boundary is drawn exactly
  where the evidence stops: the server-side shape, the `UPGR` reason, the
  key/cell reuse, the ordering, and the resulting state are established by
  committed source plus two executed probes; only the fact that the Flash client
  sends this pair is unobserved, and every artifact says so.
- **Legacy reports success for a destructive batch** → D3's three-part
  post-execution proof closes it, and the endpoint tests cover a stubbed
  reverse-order outcome that must fail closed, so the guard is exercised rather
  than merely described.
- **Upgrading appears to work at the wrong level** → D6 records the gap with the
  corpus evidence (level 1 vs lowest next-tier level 5) and names the rule for a
  follow-up, rather than shipping a gate that would make the line dead on the
  preserved corpus or inventing a level the save does not have.
- **The upgraded building's `nc` seed is unconsumed** → documented as belonging to
  the construction-timers line (D5), with the evidence that `map_add_item` sets it
  and that `activate` / `add_click` consume it.
- **`boughtUnits` grows on every upgrade** → that is legacy's own behavior for
  `buy` with `playerID == 1`; the fixture proves it and the client mirrors the
  response, never computing the list itself.
- **A fourth mode on one surface** → modes stay mutually exclusive, each keeps its
  own state, and the four delivered suites must stay green, so a regression shows
  up in an existing suite instead of hiding behind the new one.
