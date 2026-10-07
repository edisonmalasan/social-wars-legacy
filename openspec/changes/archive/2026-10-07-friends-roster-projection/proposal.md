# friends roster projection

## Why

`docs/legacy-m11-social.md` §7 classified M11's `friends` deliver item as
**"State-only, no consumer … zero legacy occurrences"**, and `godot-social-state`
then *named its own capability around that classification* — its first requirement
declares that naming a capability `godot-friends` "would claim exactly what this
one measures to be absent."

**Both are now falsified by measurement.** The committed investigation
`docs/legacy-m11-friends.md` (PR #321) re-counted `friends` over all eleven
legacy modules under six rules and found **5** whole-file occurrences, **4** of
them code-only, all in `sessions.py`. A real server-side surface exists, it is
undelivered, and the standing refusal to name it can no longer rest on a premise
that has been disproved. Leaving a falsified premise in a main spec is the
failure mode this project records repeatedly: a delivered spec asserting something
false at the exact moment a later line disproves it.

This line delivers that surface, under the only name the evidence supports.

## What Changes

- **NEW capability `godot-friends`**, delivering the roster projection
  `neighbors(USERID)` (`sessions.py:191-221`) as a **typed, read-only, unordered
  projection**: every entry the 12 carried `playerInfo` keys plus the 6 derived
  from `maps[0]`, failing **closed** on a malformed entry, a non-list roster, or a
  non-object entry.
- **MODIFIED capability `godot-social-state`**: its first requirement's naming
  clause is amended, because its stated premise ("a capability named
  `godot-friends` would claim what this one measures to be absent") has been
  **measured false**. The amendment is a **hand-off**, not a deletion: the
  reservation was conditional on the roster being absent, and the roster is not
  absent.
- Membership is **derived from the literal pid pair**, not from content. The
  committed investigation establishes the pair is a hardcoded literal with nothing
  in `config/` or the normalized package behind it, so deriving it would be an
  invention.
- The **relationship vocabulary is refused**. What the server serves is a
  *directory listing*: membership is total and unconditional, with no direction,
  consent, or lifecycle. The capability is named `godot-friends` because that is
  the deliver item's committed name and because the correction must be visible —
  but no requirement, identifier, or field presents an entry as a friend, and the
  refusal is carried as **structural SHALL text with guards proven by injection**,
  in this project's established pattern.
- The **two-channel disagreement is reported, not resolved**: `neighbors` (18
  fields, bootstrap JSON) and `fb_friends_str` (2 fields, `friendsInfo` FlashVar)
  are near-duplicate functions serving different shapes over different transports.
- **No new endpoint, no Compatibility API change, and no new fixture capture.**
  `/v0/bootstrap` already carries the roster, measured this stage: it nests at
  `player_info.neighbors` (not top level), 5 entries of 18 keys, **leaf-identical
  to the committed executed oracle** on every entry. What is undelivered is the
  typed client projection and the explicit treatment of the rules — not transport.

### Non-goals, recorded so they are not read as gaps

- **No visit payload.** `get_neighbor_info` (`server.py:155-182`) is reached by
  three of four branches of one route, but **no committed fixture exercises a
  visit**; the captured route exercises the current-player branch only. The
  General Mike branch's discarded pid is recorded as a **divergence not
  reproduced**, and the `""`-with-HTTP-200 failure mode and the `privateState`
  exposure are recorded, not delivered.
- **No roster ordering claim.** Order is `os.listdir`-dependent and already
  recorded as environment-dependent in
  `tests/fixtures/godot-compatibility-boot/field-stability.json`.
- **No FlashVar delivery.** `friendsInfo` appears nowhere in the v0 envelope
  (measured); it is recorded as a client-only channel of the preserved Flash
  client, which is not a modern-runtime dependency.
- **No relationship reconciliation** against the three committed social tables,
  which have zero consumers and therefore cannot reconcile against anything.

## Capabilities

### New Capabilities

- `godot-friends` — the typed, read-only, unordered roster projection, its
  derived membership, its two reported channels, and its refused relationship
  vocabulary.

### Modified Capabilities

- `godot-social-state` — the first requirement's naming clause, whose premise this
  line falsifies, becomes an explicit ownership hand-off. **No other requirement
  is touched**: requirement 12 ("Visits and scores are reported as having no
  server-side surface") is *narrower than its title* — its body claims only that
  `world_id` and `worldChange` are carried-but-never-read and that no score
  arithmetic exists, and both remain true, so it is left alone rather than
  "corrected" on the strength of a title.

## Impact

- **New client module** `apps/client-godot/scripts/social/friends_roster.gd` and
  its hermetic suite `res://tests/test_friends.gd`, following the one-domain-module
  convention `scripts/social/social_state.gd` already establishes.
- **`apps/client-godot/tests/test_project_scope.gd`** allow-list grows by the new
  module, the new suite, and the new evidence report — the same three-path growth
  every prior line produced.
- **`apps/compat-api/**` is NOT touched**, so the compat suite is expected to stay
  at its **3077** baseline. That is a *required* result for this line, not a
  skipped check: the roster already rides `/v0/bootstrap`.
- **No route is added**, so the route-placement invariant (four delivered suites
  assert `markers[-1] == '@app.post("/v0/level_up")'`, and `/v0/darts` already took
  the only forward-safe slot) is **untouched by construction** rather than by
  luck. This is the first line in the project to add no route.
- **`docs/DEVELOPMENT_ROADMAP.md`** Project Status: the M11 cursor is corrected.
  It currently names `magics`/`mana` as the next unmeasured follow-up, though that
  surface shipped inside M10 line 3 (`godot-damage`) as the magic-counter ledger,
  and it still describes `friends` as "zero legacy occurrences", which §7 of this
  change corrects.
- **No preserved material changes**: no legacy source, config, village, save,
  content package, conversion package, or prior fixture byte is touched.

## Evidence basis

Measured in the Propose stage, not inherited:

| Property | Committed executed oracle | Live `/v0/bootstrap` | Agree |
|---|---|---|---|
| entry count | 5 | 5 | yes |
| keys per entry | 18 | 18 | yes |
| pids | `AcidCaos`, `Kiriakos`, `Nerri`, `Neutral`, `Scarlet` | same | yes |
| 12 carried keys present | yes | yes | yes |
| 6 derived keys present | yes | yes | yes |
| any `privateState` key in an entry | no | no | yes |
| every entry leaf-identical by pid | — | **yes** | yes |

Also measured: `friendsInfo`, `pic_square`, and `uid` occur **nowhere** in the live
v0 envelope, and the roster nests at `player_info.neighbors` rather than at the
envelope's top level — so `harness.by_pid`/`sort_neighbors`, which read a
top-level `neighbors`, apply to the **legacy fixture document** and not to the v0
envelope. Ordering happened to agree in this run and is **not** claimed.
