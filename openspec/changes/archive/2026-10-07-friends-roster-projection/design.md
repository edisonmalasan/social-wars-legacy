# Design — friends roster projection

## Context

See `proposal.md` — Why. What this design must explain is *how*, given that the
binding investigation is `docs/legacy-m11-friends.md` and its §11 scope is
normative for this line.

Three measured facts drive every decision below. All three were re-measured in the
Propose stage rather than inherited:

1. **Transport is already delivered.** `/v0/bootstrap` embeds the real in-process
   `get_player_info(user_id)`, so the roster already rides the wire at
   `player_info.neighbors`. Measured live: 5 entries, 18 keys each, every entry
   leaf-identical to the committed executed oracle. The compat side is already
   proven against that oracle by `test_parity.py:129-138`.
2. **Ordering is not derivable.** `field-stability.json` records `neighbors /
   load_static_villages` as environment-dependent because iteration follows
   `os.listdir()`. It happened to agree between oracle and live in this run; that is
   coincidence and asserting it would be a latent flake.
3. **The two exclusion rules live in different scopes.** The two-pid literal pair
   applies to the static-village loop only; the self-exclusion applies to the saves
   loop only. So a static village that *is* your own pid is not excluded.

## Goals / Non-Goals

**Goals.** A typed projection that fails closed; a membership derivation that
follows the code rather than a file count; the two-channel disagreement surfaced
rather than resolved; and the relationship refusal carried as guards that fail.

**Non-goals (design-level).** No endpoint, no compat change, no fixture capture, no
visit payload, no FlashVar, no ordering claim, no relationship semantics. These are
scope boundaries the *implementation approach* creates, distinct from the
capability-level refusals in the spec.

## Decisions

### D1 — Add no endpoint, and do not touch `apps/compat-api/**`

The roster is already served. Measured: `player_info.neighbors`, 5 entries,
18 keys, leaf-identical to the oracle.

*Alternatives considered.* (a) A new `/v0/friends` route. Rejected: it would
duplicate bytes already on the wire, and it would need a route slot in a file where
placement is a pinned property — four delivered suites assert
`markers[-1] == '@app.post("/v0/level_up")'`, and `/v0/darts` already took the
only forward-safe slot after two rejected placements. Adding no route makes that
fragility **untouched by construction**, which is strictly safer than finding a
third safe slot. (b) A new route carrying only the roster, for a narrower payload.
Rejected for the same reason plus a second: it would present a roster as its own
endpoint, which reads as a social feature surface.

*Consequence.* The compat suite must stay at **3077**. A changed count would mean
this decision was not honoured, so it is a **verified** result, not a skipped check.

### D2 — A new pure projection module under `scripts/social/`, reading the opaque payload

`scripts/social/` already contains exactly one module, `social_state.gd`, so
`scripts/social/friends_roster.gd` follows the established one-domain-module
convention. It reads `PlayerInfoPayload.raw` — which `boot_data.gd:190` keeps as an
opaque `Dictionary` with only `player_name` typed — and projects from it.

*Alternative considered.* Widening `PlayerInfoPayload` to hold a typed roster.
Rejected: `boot_data.gd` is the transport-shaped typed boundary, its inner classes
are per-response shapes, and the roster is a domain projection. Putting it there
would also make the roster part of every bootstrap consumer's surface for no gain.
Reading the opaque payload keeps this line's footprint to one new module and one
new suite.

*Note on the false attraction.* A search for `neighbors` in the delivered client
returns `boot_data.gd:607 var neighbors := 0` — the expansion **requirement**,
owned and refused by `godot-building-expand` design D3. It is not the roster. The
suite must be able to tell the two apart, and the module is named `friends_roster`
rather than `neighbors` for exactly that reason.

### D3 — Report membership as an unordered set; never compare two positions

Every membership assertion is a **set** assertion. The projection exposes entry
lookup by pid and entry count; it exposes no index and no ordering.

*Consequence for guards.* The suite must assert the absence of ordering
arithmetic on roster values, in the same spirit as `godot-social-state`'s operator
guard — but **not** a blanket ban on all comparison, which that line's post-archive
review found would have condemned legitimate `typeof` discrimination. The guard is
arithmetic plus **ordering between committed values**, and nothing more.

### D4 — Ship the literal exclusion pair; record the rejected derivation

`"100000030"` / `"100000031"` are literals at `sessions.py:173-174` and `:196-197`.
The investigation establishes nothing in `config/` or the normalized package names
them; the committed comment `# general Mike` is the only statement of what they are.

*Alternative considered.* Deriving the exclusion from content — e.g. excluding
villages whose file name matches a pattern, or treating `initial.json` as the only
unloaded file and deriving 5 from the directory count. Rejected: the count
**follows from the code**, not from the **8** files in the directory
(`load_static_villages` skips `initial.json`, so `__villages` holds 7, minus 2
leaves 5). A derivation from a filename pattern or a file count would be an
invention that happens to agree.

*Consequence.* The pair is a pinned constant with a recorded reason, and the
rejected alternative is recorded beside it — the same shape as `godot-darts` D10's
refused invariants.

### D5 — Fail closed on shape, with distinct codes

Absent roster, non-list roster, and non-object entry each get their own refusal
code, matching the fail-closed convention every delivered projection uses.

*Instrument note carried from `godot-mission-vocabulary`.* `JSON.parse_string`
emits an engine `ERROR:` line for malformed input, and `verify-boot.ps1` treats any
`^ERROR:` as a script error. A refusal test that feeds the parser a document not
beginning with `{` will therefore fail the *battery* while the suite passes. The
refusal tests must discriminate shape **before** invoking the parser, with the
identical verdict and no engine error. Coverage is kept, not dropped.

### D6 — Report both channels; do not build a shared abstraction over them

`neighbors()` (18 fields, bootstrap JSON) and `fb_friends_str()` (2 fields,
`friendsInfo` FlashVar) are near-duplicates that were **not** derived from one
another. Measured: `friendsInfo`, `pic_square`, and `uid` occur nowhere in the live
v0 envelope; the FlashVar channel is client-only.

*Alternative considered.* One `RosterEntry` type parameterised by channel, or a
shared membership helper both channels call. Rejected: the investigation's §9.2
records that deduplicating them would assert a shared derivation the source does not
show, and the two channels genuinely disagree on per-entry content. Only
**membership** is common, and that is reported as a comparison, not factored into a
type.

### D7 — Carry the relationship refusal as guards proven by injection

Prose refusals cannot fail. The refusals become: a reserved-name inventory matched
case-insensitively **and by substring** (so a suffixed helper wearing one of the
names is caught), a whole-inventory pin over the module's static functions in both
directions, and the arithmetic/ordering guard from D3.

*Why substring and not exact match.* `godot-unit-instances`' review found a
by-name guard that matched only the exact name and missed a suffixed helper wearing
the same disguise. Substring matching is the belt; the whole-inventory pin is the
real gate.

*Verification contract.* Every guard is proven by **injection with a
byte-identical restore**, and the report records each probe's failure count and the
restored SHA-256, so the proof is checkable from the report rather than remembered.
This is the established pattern from `godot-darts` (10 injections) and
`godot-social-state` (6, one of which borrowed no reserved word at all and was
caught only by the arithmetic/ordering guard — the reason D3's guard is separate).

*Three defects found in a guard-proof harness while building this change's own
proposal verification, recorded because each would have produced a false "all
guards proven" record.* They are verification-tooling defects, not
delivered-behaviour defects, and they constrain how the Apply stage must write
its injection harness.

1. **A vacuous restore assertion.** The harness asserted
   `sha256(file_after) == sha256(file_after)` — a self-comparison that is true
   whatever the file contains, and that would have certified as "byte-identical
   restore" a file that had in fact been left corrupted. The digest must be
   captured **before** the probe's write and compared against it afterwards.
2. **An inverted expectation that reported passing guards as failures.** Probes
   declared "any non-zero exit" set their result true and then hit a branch that
   set it false, so three probes that fired *correctly* were reported as
   undetected. Two further probes were mis-targeted: one replaced text in an entry
   the guard does not read, and two named an expected message belonging to a
   *different* check than the one that fires. A probe that cannot reach the text
   under test is a mis-targeted probe, not evidence the guard is dead.
3. **Real tracked-file corruption, and a misleading diff.** The harness appended
   **two NUL bytes** at end-of-file and destroyed the file's final newline. Git
   then treated the file as **binary** and reported the *entire* file as changed
   — 4,908 insertions against 4,901 deletions for what was really a 9-line edit.
   The obvious reading, "this CRLF-versus-LF churn is the checkout's normal form
   because `core.autocrlf=true`", was **wrong**: the line endings were normal and
   the NUL bytes were not. `git diff --ignore-cr-at-eol` agreed with the default
   reading only *after* the repair, which is what made the difference visible.

   Consequences the Apply stage must honour: a restore assertion checks the **NUL
   count and the final newline**, not only a digest; and a "did I change more than
   I meant to?" review of a tracked file must compare against
   `git diff --numstat --ignore-cr-at-eol` **and** confirm the file is not
   classified as binary. This is the same class as the recorded fixture-integrity
   defect fixed in PR #280, which compared a recorded byte count that passed on an
   LF checkout and failed on a CRLF one — there the checkout form broke a byte
   comparison, here a probe's write broke the diff.

### D8 — No live phase

The projection runs over an already-fetched bootstrap payload; the roster is
non-mutating and the client already retrieves this surface. `godot-darts` set the
precedent of a state-mutating endpoint with no live phase, and
`godot-social-state` of a delivered capability whose whole finding is absence.

*Consequence.* `verify-boot.ps1` live phases stay at **23**, and the hermetic suite
count rises by one. `boot-report.json` is regenerated and its diff **inspected**,
which should contain only `generated_utc`, the advanced `git_commit`, and the one
added suite entry.

### D9 — Re-verify the committed oracles; fabricate no capture

Both channels are backed by committed executed-legacy captures. The suite compares
the projection against them leaf-by-leaf rather than re-deriving the corpus.

*Recorded coverage limit.* The saves-loop half of either channel has **no** executed
evidence, because the committed captures ran with no `saves/` directory. The suite
asserts this limit rather than papering over it, and exercises the saves half over
crafted in-memory input only — recorded as **crafted**, never as executed parity.

## Risks / Trade-offs

- **A future route breaks the pinned placement invariant** → this line adds no
  route, so it cannot. The invariant's owner (`test_tutorial_endpoint.
  RoutePlacementTests`) is untouched and still passes.
- **The projection is read from an opaque payload, so a service-side rename would
  silently yield an empty roster** → the fail-closed codes make an absent or
  renamed roster a visible refusal, not a silent empty list, and the suite pins the
  key name against the committed capture.
- **Adding a client source raises `test_project_scope.gd`'s count**, and its
  allow-list is hand-maintained → the list is amended in the same change, as every
  prior line did, and the suite's count is re-measured rather than quoted.
- **A refactor could reintroduce relationship vocabulary under a name the reserved
  inventory does not contain** → the whole-inventory pin plus substring matching
  plus the arithmetic/ordering guard are three independent nets; the injections
  prove all three fire. Residual risk is accepted and recorded rather than claimed
  away.
- **The harness's `by_pid`/`sort_neighbors` read a *top-level* `neighbors`**, which
  is the legacy fixture document's shape, not the v0 envelope's
  `player_info.neighbors` → the suite must not reuse them against the envelope
  without descending first. Recorded here because it is a live trap: measured this
  stage, and the delivered bootstrap nests the roster.

## Migration Plan

None. No persistence, no schema, no route, no compatibility surface. The change is
additive: one new client module and one new suite, plus a spec amendment.

## Open Questions

None. Every choice above is forced by a measurement or by the committed
investigation's §11 scope; each was resolved here rather than deferred, because
deferring any of them would change the specs, the approach, or the task breakdown.
