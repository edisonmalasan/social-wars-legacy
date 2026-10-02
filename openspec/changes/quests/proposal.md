# Proposal

## Why

**M9 — Progression line 2, `quests`** — the largest M9 surface, with **six** undelivered branches. The
contract is established by measurement in `docs/legacy-m9-quests.md` (PR #258, merged `0e886f2`), on the
milestone-wide investigation `docs/legacy-m9-progression.md` (PR #250) extended by PR #252.

## The contract, measured

| Branch | `command.py` | Writes |
| --- | --- | --- |
| `set_goals(goal_id, json_progress)` | 68 | nothing directly — delegates to `engine.py:96` |
| `complete_goal(goal_id)` | 76 | **NOTHING AT ALL** |
| `set_quest_var(key, value)` | 87 | `idCurrentMission`, `currentQuestVars`, `currentQuestVars[key]` |
| `collect_mission(next_mission)` | 430 | `idCurrentMission` (stringified), `timestampLastChapter`, `currentQuestVars` (cleared) |
| `admin_set_quest_rank(quest_index, difficulty)` | 745 | `privateState["questsRank"][str(quest_index)]` |
| `end_quest(json_blob)` | 752 | `questTimes[str(quest_id)]`, and destroys rows via `map_lose_item` |

Three findings shape the line.

**1. Only TWO committed quest fields are read by anything.** Measured as *quoted* occurrences across the
seven modules: `id` has **8**, `title` has **2** — the two `print` statements — and **`reward` has ZERO**.
`hint`, `description`, `kind`, `legacy_id`, `source_file`, `source_layer`, `content_version` all have
**zero**. And `reward` is committed on all **91** entries, **uniformly the value `10`**, so it carries no
information even if it were read. **There is no quest reward, cost, or price to derive.**

**2. `complete_goal` mutates nothing.** It reads a goal id, resolves the committed title, prints it, and
returns. A goal "completes" by being narrated in a print statement.

**3. `end_quest` is the most client-sent branch in the project.** One client-authored JSON blob drives
`win`, `duration`, `units`, `map`, `difficulty`, `voluntary_end`, and `quest_id`; `difficulty` is the only
clamped value; and the branch destroys player state by a **client-computed** `lost = max(0, unit[2] -
unit[3])`.

## What Changes

- **A typed, read-only quest-state projection**: the `goals` list, `questsRank`, `currentQuestVars`,
  `questTimes`, `idCurrentMission`, `timestampLastChapter`, and `unlockedQuestIndex`, each reported
  **verbatim** and **failing closed** on a malformed shape rather than defaulting it. The corpus's
  **`currentQuestVars` is `None`**, which the projection must report as a recorded null rather than assume
  a dict.
- **The six-branch command inventory**, recording for each what it reads, what it writes, and — for
  `complete_goal` — that it writes **nothing**.
- **The committed-content inventory**, recording that only `id` and `title` are read, that `reward` is
  uniformly `10` with zero consumers, and that the other seven fields are read by nothing. **Reported as
  content, never used** to derive a reward, a cost, or a requirement.
- **An intent-only compatibility surface** for the branches that legitimately mutate, accepting **only** a
  player identifier and the branch's own addressing, with every value the service can derive derived
  server-side.
- **`end_quest`'s destruction count REFUSED**, not implemented, and recorded as a **divergence** — with a
  byte-identical before/after proof, the form M7 and M8 established.
- **Executed-legacy fixtures**, because the corpus can exercise all six branches from its initial state.
- **Tests and evidence**: a hermetic suite, a `quests-live` battery phase, and a deterministic
  `quests-report-v1` report.

### Explicitly not in this change

**No quest reward is paid and no stored resource moves** — `reward` has zero legacy reads and is uniformly
`10`, so paying it would invent an economy from a constant. **The `end_quest` destruction count is refused**,
because reproducing a client-dictated destruction is exactly the anti-pattern `AGENTS.md` names as "Bad";
the refusal is recorded as a divergence rather than as parity. **No bounds are added** to `set_goals`: a
client could send goal id `500` and the list would grow by 350 entries, and that absence is a Server v1 /
M13 gap, not something to silently close. **`unlockedQuestIndex` is reported as content and never
written** — it is the **ninth** zero-consumer committed field in this project. **No membership test is added**
to `set_quest_var`: the legacy branch accepts any client-invented key against the eight its own comment
enumerates, and inventing a closed set would be a parity break in the stricter direction. **No
fast-forward operation is delivered** — quest timing is client-writable and that is recorded, not
implemented. Legacy sources, configs, saves, the seventeen delivered fixture directories, conversion
packages, and registry manifests stay byte-identical. No Flash, Ruffle, ActionScript, or browser executes,
and every network call is loopback.

## Capabilities

### New Capabilities

- `godot-quests`: the six quest branches as a typed, server-authoritative surface — the quest-state
  projection, the branch inventory including the branch that mutates nothing, the committed-content
  inventory, the refused `end_quest` destruction count, and the nine committed-field consumers recorded
  as content.

### Modified Capabilities

- **`godot-unit-behaviors`**: its corrected **four**-door inventory is completed by naming `end_quest`
  explicitly as one of the two callers of `map_lose_item`, so the quest path's reach into the dead-hero
  ledger is visible from the capability that owns the ledger.
- **`godot-compatibility-boot`**: the new typed quest operations join its operation list.

## Impact

- **Compatibility API v0** — a new `quest_envelope.py`, routes for the mutating branches, and
  post-execution proofs. The compat suite will **grow**.
- **Godot client** — a new `scripts/units/quest_flow.gd`, a new hermetic `tests/test_quests.gd`, typed
  quest operations on both GameApi implementations, scope-test allow-list entries, and evidence under
  `apps/client-godot/evidence/quests/`.
- **Fixture capture** — a new `capture_quest_fixture.py` run against the committed corpus in a disposable
  copy.
- **Verification** — `verify-boot.ps1` gains the hermetic suite and a `quests-live` phase.
- **Documentation** — `AGENTS.md`, `apps/client-godot/README.md`, and the roadmap Project Status ledger.