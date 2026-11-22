# Content Replacement Strategy (v1)

> **Status: DESIGN — NOT IMPLEMENTED.** This document defines a strategy. It
> contains no content data, no code, no asset, no copied value and no cleared
> release gate. See [Honest status](#12-honest-status).
>
> **Version:** v1 of this strategy and of the neutral content specification it
> defines. A material change bumps the minor version with a note in
> [§ 13 Versioning](#13-versioning); a shape change to the bundle bumps the
> bundle's own `formatVersion` deliberately (see [§ 5](#5-requirement-1--schema-compatible-field-boundaries)).
>
> **Licence of this document:** CC0-1.0. To the extent possible under law, the
> contributors waive all copyright and related or neighbouring rights to this
> strategy document. It is not legal advice.
>
> **Licence required of all content authored under it:** CC0-1.0, with a
> per-source provenance record, exactly as the clean-room generator's output is
> dedicated in `assets/original/` (see `./adr/0021-clean-room-assets.md`).

---

## 1. Purpose and scope

This is the answer to the approved objective item that asks for a **versioned,
independently authored content replacement strategy**. It is a design document,
not an implementation. It says how the project would replace the proprietary
data that currently drives the shipped bundle with content the project authors
itself, without changing the protocol, the rules engine's determinism or the
server's authority, and without pretending the licensing gate is clear.

It owns exactly one file: `docs/CONTENT-REPLACEMENT.md`. It does not own
`docs/LICENSING.md`, `docs/ATTRIBUTION.md`, any source file or any asset. It
changes no roadmap checkbox and closes no gate.

The seven numbered requirements of the objective are addressed in §§ 5–11:

| # | Requirement | Section |
|---|---|---|
| 1 | Schema-compatible field boundaries | [§ 5](#5-requirement-1--schema-compatible-field-boundaries) |
| 2 | Fresh ID namespace and neutral category/art keys | [§ 6](#6-requirement-2--fresh-id-namespace-and-neutral-keys) |
| 3 | Authored names, costs, stats, formulas, quest principles | [§ 7](#7-requirement-3--authored-values-and-design-principles) |
| 4 | Reproducible build with hard source isolation | [§ 8](#8-requirement-4--reproducible-build-with-hard-source-isolation) |
| 5 | Protocol preservation | [§ 9](#9-requirement-5--protocol-preservation) |
| 6 | Deterministic rules and re-recorded golden corpus | [§ 10](#10-requirement-6--deterministic-rules-and-re-recorded-golden-corpus) |
| 7 | Ordered migration, acceptance tests, release gates | [§ 11](#11-requirement-7--ordered-migration-plan) |

---

## 2. Terms

- **Neutral content** — content authored for this project from design
  principles, dedicated CC0-1.0, with provenance a reviewer can check.
- **Authored** — a value that originates in the project's own spec sources and
  a recorded human decision. "Generated from an authored parameter" counts as
  authored; "generated from an upstream value" does not.
- **Upstream row / snapshot / constant** — any record or number in the vendored
  reference tree, the reverse-engineering tree or the decompiled client. These
  describe the *original* game. They are evidence about behaviour, never a
  source of shipped data.
- **Copy** — taking a value, name, id, relationship or number from such a
  record and putting it in the neutral spec.
- **Translate** — taking such a record and changing only its language,
  spelling, casing or presentation. Translation is copying.
- **Re-key** — taking such a record and changing only its identifier. Re-keying
  is copying. A neutral item must be designed, not renamed.
- **Shim alias** — a legacy numeric identifier accepted at a compatibility
  boundary so an untouched original client can still be served. It is a
  translation at the *wire edge*, never a definition of neutral content.

---

## 3. The problem this strategy addresses

The shipped bundle is currently **derived**. Its items, levels, goals,
globals, collections, offer data, quest rosters and quest event records all
come from the vendored reference configuration, its patch deltas, vendored
quest map snapshots and decompiled client constants. The frame manifest comes
from proprietary art. Tutorial strings come from decompiled literals, the font
scale from proprietary metrics, and the build id hashes those bytes.

The existing checks are honest about what they cover, and that is not enough
here: `check-licensing` and `check-no-flash` scan shipped *media and runtime
filenames* (and font usage), and the report-sync check compares counts between
the report set and the bundle. None of them inspects the JSON **values** for
proprietary data, and none asks where those values came from. A bundle whose
provenance fields were edited but whose rows were copied would pass them.

The gap is therefore not "add a licence string". It is **change the source of
the data** while leaving the behaviour contracts intact. That is what this
strategy specifies.

---

## 4. Invariants preserved by every phase

These are locked decisions; nothing in this strategy reopens them.

1. The decompiled client remains the **specification of behaviour**. This
   strategy changes content values, not the rules. Where a rule must be
   generalized to accept a neutral key, that is a reviewed code change, not a
   content change, and it keeps the same observable semantics.
2. The server remains **authoritative**: costs, outcomes, goal completion and
   rewards are computed server-side from server-owned data.
3. The rules engine remains **pure and deterministic**: no wall clock, no
   unseeded randomness, no I/O in simulation (ADR 0014).
4. The wire protocol is unchanged: **94 commands**, each with the same name,
   arity and result shape; `set_quest_var` stays **two-argument**; the locked
   resource-vector order (AGENTS.md non-negotiable 4, ADR 0011) is untouched.
5. No Flash anywhere in the shipped product; the original client is a test
   fixture only.
6. `upstream/` and `re/` remain **read-only references**. No shipped artefact
   may be built from them.
7. No authentication is inherited from the upstream; no `flash_debug`.
8. ADR 0019 (pure online) and ADR 0020 (social services server-only) keep their
   non-goals.
9. **Publication stays blocked** until I6 is closed by an explicit, authorized
   decision following a rights-holder request or equivalent. No rights-holder
   request exists at the time of writing. This document does not close I6.

---

## 5. Requirement 1 — Schema-compatible field boundaries

The neutral bundle stays shape-compatible with
`packages/content/src/schema.ts` so the runtime does not have to learn a second
content model. Compatibility is about **shape**, not about **source**: every
field below is either authored, derived from authored inputs, or removed. No
field is populated from a vendored record.

### 5.1 Authored item fields

Every field of `ContentItem` is owned by the neutral spec. Grouped by purpose:

| Group | Fields | Boundary rule |
|---|---|---|
| Identity | `id`, `name`, `type`, `category_id`, `subcategory_id`, `subcat_functional`, `img_name` | `id` allocated per § 6; `name` authored per § 7; category and functional values are neutral keys (§ 6); `img_name` holds neutral art keys (§ 6). |
| Combat | `attack`, `defense`, `life`, `attack_range`, `attack_interval`, `velocity`, `population` | Derived from authored role parameters and tier formulas (§ 7). `attack_interval` keeps its documented unit (frames at the client's tick rate); `velocity` keeps its documented unit (pixels per frame). Units are part of the schema contract, not copied numbers. |
| Economy | `cost`, `cost_type`, `costs`, `collect`, `collect_xp`, `max_collects`, `activation`, `collect_type` | Authored resource keys and authored cost/production curves. The legacy single-resource fields stay present and inert by the schema's own convention; the real cost is in `costs`. |
| Relationships | `trains_ids`, `upgrades_to`, `best_against`, `best_against_mult`, `inventory_ids`, `premium_upgrade_costs`, `unit_capacity`, `building_limit_same_id`, `building_limit_same_scf`, `volume`, `max_elem_vol` | All references resolve inside the neutral ID namespace; counter classes and their multipliers are authored, not inherited from any existing relationship table. |
| Build and presentation | `width`, `height`, `min_level`, `display_order`, `build_time`, `clicks_to_build`, `training_time`, `xp`, `group_type`, `race`, `in_store`, `giftable`, `gift_level`, `cost_unit_cash` | Authored from a declared balance and presentation model. Ordering and limits are design decisions with recorded rationale. |
| Property bag | `properties`, `properties_raw` | `properties` uses only keys from the authored neutral vocabulary. `properties_raw` is the canonical serialization of the authored `properties`, never a verbatim captured string. |
| Escape hatch | `extra` | **Empty in v1.** Any future entry needs a schema amendment and a review record; it is never a carrier for copied data. |

### 5.2 Authored container fields

`ContentBundle`'s collections are authored too: `levels`, `goals`, `globals`,
`collections`, `inventoryItems`, `offerPacks`, `socialItems`, `images`,
`sounds`, `dartsItems`, `unitCollectionCategories`, `magics`,
`expansionPrices`, `neighborAssists`, `townPrices`, `mapPrices`,
`findableItems`, `levelRankingReward`, `categories`, `questRosters` and
`questEvents`.

In particular `questRosters` and `questEvents`, which the current build
**extracts** from vendored map snapshots, become **authored declarations** in
the neutral spec: refs and counts are written from a designed quest, not read
out of a captured map.

### 5.3 Derived fields

`formatVersion`, `buildId`, `propertyKeys`, `subcatFunctionals`,
`clientOnlyItemIds` and `assetlessItemIds` are computed by the neutral build
from authored inputs. They are never typed by hand. In the neutral build
`clientOnlyItemIds` should be empty by construction (every referenced item is
in the spec) and `assetlessItemIds` should be empty once art coverage is
complete; a non-empty value is a warning that blocks release, not a fact to
ship quietly.

### 5.4 Provenance fields — replacement, not deletion

`upstreamCommit` and `patchesApplied` are **removed** from the neutral bundle.
They describe where the copied data came from and must not survive into a
product that claims no copied data. They are replaced by:

| Field | Type | Meaning |
|---|---|---|
| `specVersion` | string | The specification version, `v1` for this document. |
| `specRevision` | 64 lowercase hex | SHA-256 of the canonical concatenation of all authored spec inputs. Changes on any authored edit. |
| `authoringMethod` | string | `clean-room-authorship` — values designed from the project's own rules, with the method recorded in the spec. |
| `licence` | string | `CC0-1.0` for every authored source. |
| `artGenerator` | string | Generator identity and version from `@swl/art` (its own provenance constants). |
| `buildInputs` | array of `{ path, sha256 }` | The complete, closed list of neutral inputs, relative to the spec root. |
| `statement` | string | An explicit original-work statement in the same spirit as the generator's: no file from the reference trees, the decompiled client, an atlas or a proprietary font was read, traced or copied. |

Bumping `formatVersion` is a **deliberate migration step**, not a side effect of
this strategy; until that step is taken the current schema still declares the
old provenance fields and the neutral build must not be switched on (§ 11,
phase 7).

---

## 6. Requirement 2 — Fresh ID namespace and neutral keys

### 6.1 Canonical identity

An authored item's canonical identity is a **stable string slug**, not a
number. Slugs follow a project-owned convention such as
`<kind>.<role>.<variant>` (for example, a defensive structure or a ranged unit
gets a descriptive slug written by its author). Slugs are unique, human-readable
and survive renames of display names.

Numeric IDs remain on the wire because the protocol and the existing runtime
use them. They are **allocated**, not inherited:

- The spec owns an allocation table mapping slug → numeric id.
- IDs come from a fresh range chosen to be disjoint from the legacy identifier
  space; the exact range is a spec parameter fixed once and reviewed.
- Allocation is deterministic: adding an item appends to the table and cannot
  renumber an existing entry.
- **No id is carried over from an upstream record**, and no upstream row is
  "re-keyed" into the new table. Every entry must be traceable to an authored
  design record, not to a reference row.

### 6.2 Category and functional keys

All string vocabularies in authored fields are owned by neutral tables in the
spec:

- **Categories** — authored groupings such as civic, production, defence,
  offence, support and decoration. Names and boundaries are design choices.
- **Functional roles** — authored role keys used by `subcat_functional` and
  `group_type`; these describe what a thing *does* in the new design.
- **Factions** — authored faction keys for `race`; no captured token is reused.
- **Resource keys** — the locked protocol resource vector is preserved at the
  wire edge by reference (§ 9); authored content refers to it through the
  neutral resource table.

Where the rules engine is not yet generalized to a neutral key, a single
**reviewed key-map** translates neutral keys to the engine's internal keys. That
table is authored and reviewed like any other source; it is a compatibility
adapter inside the build, not a copy of an upstream vocabulary, and it is not a
place to park reference values. The long-term direction is to generalize the
engine and shrink the key-map to zero.

### 6.3 Art keys resolved through `@swl/art`

`img_name` holds one or more **neutral art keys**, separated as the schema
already allows. Each key resolves to an artefact produced by `@swl/art`, the
deterministic clean-room generator, whose manifest records path, byte size,
SHA-256, generator version, licence (`CC0-1.0`) and an original-work statement.
Examples of keys that already exist and are safe to reference are the Foundry
motif identifiers `foundry-anvil`, `foundry-turret`, `foundry-wagon`,
`foundry-shield`, `foundry-cog` and `foundry-flask`.

Resolution rules:

1. A key must resolve to a `@swl/art` artefact with a manifest entry. An
   unresolved key is a **build error**.
2. No key may name a proprietary asset, a SWF symbol, an atlas region or a font
   face from the reference trees.
3. Missing art is declared as a reviewed **pending placeholder**, with a slug,
   a reason and a gate that blocks release while it remains. A placeholder is
   never a reference to the original art.
4. The art set is extended by adding authored motifs to the generator, each with
   its own seed, so output does not depend on generation order or platform
   randomness (ADR 0021).

---

## 7. Requirement 3 — Authored values and design principles

This section defines **how values are authored**. It deliberately contains no
item names, costs, stats, multipliers, quest names, quest identifiers or roster
values from the original game. Parameter names below are symbolic; their
numbers are authored in the spec data file with a unit, a rationale and a
review record, and are tuned by playtesting rather than fitted to captured
data.

### 7.1 Names

- Names are written from a project-owned lexicon and theme consistent with the
  Foundry art family. A naming convention (length, casing, uniqueness,
  human-readability) is enforced by a lint step.
- No name is a copy, translation, transliteration, respelling or near-neighbour
  of a name in the reference configuration, the decompiled client or the
  reverse-engineering reports. A similarity scan against those sources is a
  build gate; a hit fails the build.
- Names are presentation, not identity: changing a name does not change a slug
  or an id.

### 7.2 Costs, stats and formulas

Values are derived from declared design models, each with authored parameters:

| Model | Formula shape (symbolic) | Design input |
|---|---|---|
| Build cost | `cost[r] = round(BASE[role][r] × TIER_FACTOR[r]^(tier−1))` | Resource curves, time-to-first-structure, economy pacing. |
| Combat | `attack = ROLE_ATTACK[role] × ATTACK_TIER^(tier−1)`; `life = ROLE_LIFE[role] × LIFE_TIER^(tier−1)` | Role envelope (front line, skirmisher, siege, support) and desired time-to-kill bands. |
| Cadence | `attack_interval` from an authored `CADENCE[role]` in the client's frame unit; `velocity` from authored movement bands | Readability of combat, not a captured timing. |
| Counters | `mult = COUNTER[attackerClass][targetClass]`, authored from a declared counter design | A small, designed counter graph; no inherited relationship table. |
| Production | `collect = BASE_COLLECT[role] × PERIOD_MULT[period] × WORKER_BONUS(workers)` | Authored period set and multipliers chosen for the new economy. |
| Population / capacity | authored per-role grants and ceilings | Declared progression curve. |

Rules for authored parameters:

- Every parameter has a name, a unit, a range and a written rationale.
- No parameter value is taken from, rounded from, scaled from or fitted to a
  captured constant. The acceptance scan checks provenance, not just equality.
- Changing a parameter changes `specRevision` and `buildId` and requires a
  balance-review record.
- Formulas are deterministic and integer-safe where the schema expects
  integers; rounding rules are part of the formula, not an afterthought.

### 7.3 Quest design principles

Quests are authored as state machines from a set of generic objective
archetypes — defend, destroy, collect, survive, escort and assemble — each
with declared spawn conditions, an objective, a win test, a fail test and a
reward drawn from the authored reward tables.

- Quest ids come from the neutral namespace (§ 6). No captured quest id, name,
  map filename or roster is reused.
- Enemy rosters are **designed**: an author chooses a composition theme and a
  tier, and the roster is generated from authored rules. It is not extracted
  from a captured map.
- Event channels (for example arrivals, eligible-defender kills or civilian
  evacuations) are authored event specifications with declared refs and
  counts, written as part of the quest design. No captured snapshot supplies
  them.
- Difficulty scales by an authored tier function; rewards come from authored
  tables. No captured play order or reward row is transcribed.
- Every quest passes an automated **solvability** check: the win condition is
  reachable under the authored spawn and timer rules, and no objective is
  unsatisfiable by construction. Quests that cannot be made solvable are
  dropped with a recorded reason, not shipped broken.
- Chapter and progress state uses the protocol's existing two-argument
  `set_quest_var` contract (§ 9); no new command is introduced.

---

## 8. Requirement 4 — Reproducible build with hard source isolation

### 8.1 Closed input set

The neutral build reads **only**:

- authored spec sources under a single neutral spec root (v1 sources), and
- `@swl/art` and its generated, manifested output.

It reads nothing from `upstream/`, nothing from `re/`, no decompiled output, no
captured traffic and no network. The current build's inputs (reference config,
patch deltas, quest snapshots, behaviour tables and asset tree) are all
prohibited.

### 8.2 The isolation guard

Source isolation must be enforced, not asserted:

1. A path allowlist resolves every input path (normalised, case-insensitive
   on Windows, symlink-resolved) and rejects any path under `upstream/` or
   `re/`, and any path outside the spec root or the art output root.
2. A CI check instruments filesystem reads during a build and fails on any
   prohibited access — the same technique the art package uses to prove it
   reads no upstream or reverse-engineering file.
3. A **planted-read test** deliberately attempts a prohibited read and proves
   the guard fires. A guard that has never been shown to fire is not a guard.
4. The generated bundle contains no absolute paths, no wall-clock values, no
   host locale, no environment values and no unseeded randomness. Time-based
   behaviour (such as rotating schedules) stays at runtime, as it does today.

### 8.3 Reproducibility

- Canonical serialization: sorted keys, fixed whitespace, stable array order.
- `buildId` = SHA-256 of the canonical bundle bytes; two clean builds produce
  identical bytes and identical ids.
- CLI modes mirror the existing content CLI: `build`, `--check` (validate only,
  for CI) and `--out <file>`. The summary prints the neutral provenance fields
  from § 5.4 and never the removed ones.

### 8.4 Build failures

The neutral build fails on any of:

- an unknown top-level section or unknown authored key;
- a duplicate id or a duplicate slug;
- a dangling reference (`trains_ids`, `upgrades_to`, inventory keys, quest
  refs) or a self-referential upgrade chain;
- an unresolved or prohibited art key;
- a non-canonical ordering or a non-neutral provenance field;
- any prohibited filesystem read;
- any leftover upstream or reverse-engineering provenance field in the output.

---

## 9. Requirement 5 — Protocol preservation

The content migration is a **data-source change only**. The protocol is frozen:

- **94 commands**, with unchanged names, arities, argument types and result
  shapes; `packages/protocol/src/commands.ts` and the catalogue check continue
  to pass unchanged.
- **`set_quest_var` remains two-argument**: `[key: string, value: JSON]`, with
  the same validation and the same behaviour. The neutral spec must not require
  a third argument (for example a quest id or a neutral slug); if quest state
  needs a richer key, that is encoded in the existing key string, never by
  changing the command's arity.
- The locked **resource-vector order** (AGENTS.md non-negotiable 4, ADR 0011) is
  unchanged. Neutral resource keys map to those slots at the wire edge.
- No new command is added for authoring, building or switching content.
  Authoring is a build-time activity and produces no wire traffic.
- `flash_debug` stays absent; server authority and the real authentication
  model are untouched.

### 9.1 Legacy numeric aliases (only if needed)

The untouched original client speaks legacy numeric item identifiers. If those
must still be served:

- All aliases live in **one reviewed shim table** at the compatibility edge,
  keyed by legacy numeric id → neutral slug. Nothing else in the product
  contains a legacy alias map.
- The table accepts only identifiers the client can actually emit; a test
  asserts it is a subset of that set. Unknown legacy ids are refused, never
  guessed.
- Every entry carries a review record: who approved it, why it is needed, and
  the neutral item's design record. An entry is **not** a re-keyed upstream row;
  it is a wire-edge translation to an independently designed item.
- The direction is legacy → neutral only. The neutral spec never exports legacy
  ids, and no neutral bundle field is populated from the table.
- The shim table is temporary by default: if the legacy client path can be
  retired, the table is deleted rather than maintained. Its continued existence
  is reviewed at each release gate.

---

## 10. Requirement 6 — Deterministic rules and re-recorded golden corpus

The rules engine is not changed by this strategy except where a neutral key
must be accepted through the reviewed key-map (§ 6.2). Its determinism
contract — seeded generator, integer operations, no clock, no I/O — stays
exactly as it is.

The golden corpus must be **re-recorded, not copied**:

1. Scenario **inputs** are re-authored against the neutral spec: neutral slugs
   and ids, authored rosters, authored cost and stat parameters. The fixed
   seeds used by the harness are kept — they are test fixtures, not content
   values, and keeping them makes the re-recording a like-for-like check of the
   new data.
2. Scenario **outputs** are computed by the rules engine from the neutral spec
   under those seeds and recorded into a **new, neutral corpus location** under
   the spec root. No recorded answer, delta or intermediate stage value is
   copied from the existing corpus.
3. A guard asserts the old corpus and the new one share no recorded output
   values; a coincidental match is investigated and documented, never assumed
   to be safe.
4. The harness gains a mode to select the neutral corpus and runs in CI. The
   perturbation test still holds: changing one recorded value is detected and
   reported.
5. Two clean builds produce a byte-identical corpus. The scenario count is
   tracked as a **floor** and may grow; it is not copied from the old count.

Because the neutral content has authored values, the recorded answers will
differ. That is the point: the corpus is evidence that the engine behaves
deterministically **on the new content**, not evidence that the new content
matches the old.

---

## 11. Requirement 7 — Ordered migration plan

Each phase has an acceptance test. A phase may not start until the previous
one's acceptance test passes. No phase closes I6.

### Phase 0 — Adopt the strategy

- **Work:** merge this document; record the decision in the project's normal
  channels.
- **Acceptance:** `node scripts/check-roadmap.mjs` still reports the same counts
  (401 items, 22 open at the time of writing); `node scripts/check-report-sync.mjs`
  still passes; no checkbox, blocker or ADR changed; I6 open.

### Phase 1 — Authoring charter and spec skeleton

- **Work:** create the neutral spec root, the CC0 notice, the provenance fields
  of § 5.4, the closed input list and the isolation guard of § 8.2.
- **Acceptance:** `build` and `--check` run against an empty authored set; the
  planted prohibited-read test fails the build as intended; no output contains
  `upstreamCommit` or `patchesApplied`.

### Phase 2 — Vocabulary, slugs and art keys

- **Work:** define categories, functional roles, factions, counter classes and
  the reviewed key-map; stand up the slug → id allocation table; prove art-key
  resolution through `@swl/art`.
- **Acceptance:** every key resolves; no duplicate slug or id; every art key has
  a manifest entry or a reviewed pending-placeholder record; a similarity scan
  finds no captured token in the neutral vocabularies.

### Phase 3 — Authored data

- **Work:** author names, cost/stat parameters, formulas, quest archetypes,
  rosters, event specifications and reward tables from the principles in § 7.
- **Acceptance:** the provenance scan finds no copied name, number, id or
  relationship; all solvability checks pass; every parameter has a unit, a
  range and a rationale; two independent reviewers sign the balance record.

### Phase 4 — Neutral bundle build

- **Work:** produce a shape-compatible bundle with neutral provenance; keep the
  old provenance fields absent; decide and record the deliberate
  `formatVersion` change with the schema amendment.
- **Acceptance:** schema validation reports zero errors; the bundle is
  byte-identical across two builds; every field boundary of § 5 holds; the
  legacy build is still the one the shipped tree consumes until phase 7.

### Phase 5 — Re-record the golden corpus

- **Work:** implement § 10.
- **Acceptance:** neutral corpus computes and passes with zero differences;
  perturbation detected; new corpus shares no recorded output with the old one;
  CI runs the new mode.

### Phase 6 — Legacy alias review

- **Work:** if, and only if, the untouched client still needs serving, build the
  single reviewed shim table of § 9.1; otherwise record the decision to retire
  that path.
- **Acceptance:** 94 commands unchanged; two-argument `set_quest_var` unchanged;
  the alias table is a reviewed subset of client-emittable ids and appears in
  exactly one place; no neutral field is populated from it.

### Phase 7 — Integration and removal

- **Work:** switch the shipped tree to the neutral bundle; integrate the neutral
  art; remove the proprietary-derived bundle from the shipped tree; re-point
  the report-sync item-count claim at **original-game evidence** rather than
  the shipped bundle, so the report set keeps describing the original game;
  re-run the media and runtime checks.
- **Acceptance:** `check-licensing` and `check-no-flash` pass on the shipped
  trees; `check-report-sync` passes with the re-pointed claim; no shipped JSON
  value is derived from a prohibited read; the shipped tree carries no
  reference-derived config, snapshot or atlas.

### Phase 8 — Gate review (not automatic)

- **Work:** present the evidence to the authorized decision-maker; record the
  rights-holder request or equivalent; keep the attribution and preservation
  notices current.
- **Acceptance:** I6 may be closed **only** by an explicit, authorized decision
  with that evidence. Until then the gate stays open and publication stays
  blocked. This phase is not completed by any code or document merge.

### 11.1 Release gates that always hold

- Publication is blocked until I6 is closed. No artefact is published on the
  strength of this strategy, a green test run or a clean licence scan.
- No rights-holder request exists at the time of writing; if one arrives, it is
  recorded under the project's corrections policy.
- `upstream/` stays byte-for-byte verified and read-only; no GPL data ships.
- ADR 0019 and ADR 0020 non-goals stay intact.
- No Flash, no proprietary font, no Zynga media and no reference-derived config
  in any shipped tree.

---

## 12. Honest status

- **Not implemented.** This is a strategy document. There is no neutral spec
  tree, no neutral build path, no authored content, no new shim table, no
  re-recorded corpus and no integrated art. Every phase in § 11 is future work.
- **No data, no code, no copied values.** This document contains no content
  rows, no numeric content parameters, no quest records and no asset data. The
  symbolic parameter names in § 7 are placeholders, not authored values.
- **I6 stays open.** This strategy does not clear the licensing gate, does not
  satisfy the configuration-recreation requirement, and does not authorize a
  release. No rights-holder request exists, and no publication is authorized.
- **Gates unchanged:** `node scripts/check-roadmap.mjs` still reports 401 items
  / 22 open; `node scripts/check-report-sync.mjs` still passes against the
  current (reference-derived) bundle; the ADR set, including 19/20/21, is
  untouched.
- **A plan is not evidence.** Nothing here may be cited as proof that the
  content is original, that the gate is clear, or that any screen, asset or
  release is complete.

---

## 13. Versioning

- `v1` — initial strategy: field boundaries, neutral namespace and keys,
  authoring principles, isolated reproducible build, protocol preservation,
  golden-corpus re-recording and the ordered migration plan.
- A change to a principle, a field boundary or a gate requires a minor bump and
  a dated note here, with the rationale and the review record.
- A change to the bundle's shape requires the deliberate `formatVersion`
  migration of § 5.4 and § 11 phase 4; it is never a silent consequence of an
  editorial change to this document.

---

## 14. References

- [Content schema](../packages/content/src/schema.ts) — the field boundaries this
  spec stays compatible with.
- [Content build](../packages/content/src/build.ts) — the current reference-derived
  build and the provenance fields being replaced.
- [`@swl/art` README](../packages/art/README.md) and
  [ADR 0021](./adr/0021-clean-room-assets.md) — the clean-room generator and
  its CC0 provenance model.
- [Licensing position](LICENSING.md) — the gate this strategy does not clear.
- [Roadmap](ROADMAP.md) — Group I and the I6 release gate.
- [ADR 0011](./adr/0011-the-resource-vector-order.md),
  [ADR 0014](./adr/0014-determinism-by-construction.md),
  [ADR 0019](./adr/0019-pure-online.md),
  [ADR 0020](./adr/0020-social-services-server-only.md) — preserved
  contracts and non-goals.
- [Protocol command table](../packages/protocol/src/commands.ts) — the frozen
  94-command catalogue and the two-argument `set_quest_var` contract.
