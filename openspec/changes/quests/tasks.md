# Tasks

## 1. The quest-state projection

- [x] 1.1 Implement `apps/client-godot/scripts/units/quest_flow.gd`: a typed read-only projection of the seven quest fields — `goals`, `questsRank`, `currentQuestVars`, `questTimes`, `idCurrentMission`, `timestampLastChapter`, `unlockedQuestIndex` — each reported **verbatim** with no value derived from another (D1) — verify: `test_quests.gd` covers every field and asserts that no completion state, remaining time, progress ratio, or reward is derived.
- [x] 1.2 Implement the **fail-closed** paths: an absent field, a wrong type, and a malformed element are each reported **unresolvable with their recorded state intact**, and a **null** `currentQuestVars` is reported as a recorded null rather than presented as an empty map (task 1.1's second half) — verify: the suite covers all four shapes, including the corpus's real `None`.
- [x] 1.3 Reproduce the two **type facts** rather than normalizing them: the stringified mission identifier written against a corpus recording an **integer**, and the quest-variable map self-healed from `None` to `{}` while being cleared (D8) — verify: both are asserted against the captured fixture bytes and the projection reports the corpus's `None` rather than assuming a dict.

## 2. The six-branch and content inventories

- [x] 2.1 Record the six-branch inventory with each branch's reads, writes, and whether it mutates anything, including that **`complete_goal` writes nothing at all** (D3) and that `set_goals` grows the list on demand through its engine helper with **no upper bound** (D4) — verify: the suite asserts all six branches, the no-op branch, and the branch count against the committed source.
- [x] 2.2 Assert the **no-completion-state absence structurally**: the suite fails if any completion flag, ledger, or completion accessor is added (D3) — verify: inject one, observe the failure, restore from a byte-identical copy, confirm the suite passes again; record both outcomes.
- [x] 2.3 Record the `set_quest_var` and `collect_mission` shapes: any client-invented key accepted against the eight the legacy comment enumerates, the one explicitly ignored key refused, and the out-of-range mission identifier **wrapping** rather than being rejected (D5) — verify: each fact is asserted, including that the accepted set is unbounded in the recorded direction.
- [x] 2.4 Record the **committed-content inventory** with its **measured** consumer counts, stating that only `id` and `title` are read and that `reward` has **zero** consumers and a **uniform** value on all 91 entries (D6) — verify: each consumer count is compared against the committed source and a discrepancy fails the suite.
- [x] 2.5 Assert that **no delivered code identifier or computation is named after the reward field**, making the "reported, never used" claim mechanical, and that `unlockedQuestIndex` is reported and **never written** (D6, D7) — verify: the suite asserts both, and no operation writes that index.

## 3. The intent-only compatibility surface

- [x] 3.1 Add `apps/compat-api/quest_envelope.py` with the legacy branches that legitimately mutate, each accepting **only** a player identifier and the branch's own addressing, deriving every stored value it writes and ignoring any client-supplied progress pair, key, value, rank, or outcome (D1) — verify: each route refuses extra fields and the response echoes no ignored value.
- [x] 3.2 **Refuse the `end_quest` destruction count** and prove the refusal: every placed row **byte-identical** before and after, compared over the **complete** placed-row set, with the refusal recorded as a **divergence** rather than as parity (D2) — verify: the proof covers the whole `items` dict, and a test proves a selected-subset comparison would be insufficient.
- [x] 3.3 Refuse an `end_quest` request with **no** recorded quest identifier with a named code, an **empty** payload, and **no** state change — verify: the refusal, its code, its empty payload, and the byte-identical before/after are asserted.
- [x] 3.4 Add the **resource-unchanged proof** to every quest action, comparing the **complete** stored resource set (D-none) — verify: each action's proof compares the full set rather than a subset.
- [x] 3.5 Add typed quest operations to **both** GameApi implementations and a client flow that sends **only** intent — verify: the fake and legacy-v0 implementations return the same typed shape, and the flow suite asserts the request body carries no derived value.

## 4. The refusals, timing, and the anti-invention guard

- [x] 4.1 Implement the **refusals as stated requirements**: no reward paid and no resource moved; no bounds on the on-demand goals list; no membership test on the quest-variable writer; no completion state (D3, D4, D5, D6) — verify: each refusal family is present with a non-empty reason, and the uniform reward value is asserted **not** to produce an amount.
- [x] 4.2 Record `fast_forward` as a **quest-state writer** naming both write sites — the quest-time map and the last-chapter instant — and assert that **no** fast-forward operation is delivered and no elapsed-time behaviour is derived (D9) — verify: the writer inventory contains the six branches plus fast-forward, and the delivered operation list has no fast-forward entry.
- [x] 4.3 Record the committed save-migration initialization of the quest-time map as a **migration path**, not gameplay (D9) — verify: the suite asserts the migration is recorded as such and not as a quest behaviour.
- [x] 4.4 Assert the **anti-invention guard** structurally: the module's whole static-function inventory is compared against a pinned list, so a `quest_reward`, `quest_progress_ratio`, `mark_goal_complete`, `is_goal_complete`, or `quest_remaining_time` helper fails the run wherever it is added — verify: **inject one, observe the failure, restore from a byte-identical copy, confirm the suite passes again**; record the exact injection and both outcomes.

## 5. Fixtures and the cross-milestone agreement

- [x] 5.1 Add `apps/compat-api/capture_quest_fixture.py` capturing each of the six branches against the committed corpus in a **disposable copy**, recording `request`, `before`, and `after` state and proving the committed corpus **byte-identical** (D11) — verify: the capture exits 0, is re-runnable, and its manifest records all six steps.
- [x] 5.2 Add executed-legacy **parity tests** replaying each captured step, and record **no** absence of a fixture — the corpus holds every quest field at its initial value, so a missing fixture would be a gap in the line, not a corpus limitation (D11) — verify: parity tests cover all six branches and the manifest asserts six steps.
- [x] 5.3 Name **`end_quest`** as one of `map_lose_item`'s two callers in `godot-unit-behaviors`, so the ledger owner and the quest owner describe the same reach consistently (D10) — verify: the suite asserts `end_quest` is recorded as a caller and that the ledger's door count remains **four**.

## 6. Boundary, evidence, and integration

- [x] 6.1 Register the hermetic suite in `verify-boot.ps1` and add a **`quests-live`** phase with `--expect-save-mutation` driving the mutating branches and the refused `end_quest` against a disposable corpus, asserting each typed response, each post-condition, that the refusal left every placed row byte-identical, and that the disposable save mutated — verify: `verify-boot.ps1` exits 0 end to end, the port is released, and no working-tree `saves/` is left behind.
- [x] 6.2 Write the deterministic `quests-report-v1` report into `apps/client-godot/evidence/quests/` via `--report=<path>`, bare `--report` defaulting there and the directory created first, recording the projection, the six-branch inventory, the content inventory, the refused destruction, the client-writable timing, and every non-claim (D12) — verify: the report is committed, carries every required field, and a rerun reproduces its committed bytes exactly.
- [x] 6.3 Document the slice in `apps/client-godot/README.md` and add the actually executed verification commands to `AGENTS.md`, stating the "no reward", "destruction refused", "no bounds", and "no completion state" limits wherever the slice is described — verify: each documented command matches one run successfully in this change.
- [x] 6.4 Run the full preservation battery in the final state and record the residual gaps: no reward paid and no resource moved; the destruction count refused as a divergence; no bound on the goals list and no membership test on the key writer; the unlocked-quest index reported and never written; no fast-forward operation delivered; no completion state; the committed content reported and never used; no pixel parity; no windowed capture — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, the compat suite is green and **grown**, `validate_content.py` exits 0, `hash_manifest.py verify` exits 0, the guard baseline reports identical digests before and after, and `git diff` shows no content-package, save, config, village, conversion-package, registry-manifest, or legacy-source byte changed.
- [x] 6.5 Perform the integration review: re-read the final diff against `proposal.md`, `design.md` D1–D12, `specs/`, and `docs/legacy-m9-quests.md`; run `openspec validate quests --strict` and both batteries once more; and record a requirement-to-evidence map — verify: strict validation exits 0 with **no** "Archive would refuse" warning, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.

---

# Review record

Recorded by the root orchestrator after the Apply stage. Every figure was **re-measured** by the root
rather than taken from the implementation worker's report.

## Requirement-to-evidence map

| Requirement | Evidence | Status |
| --- | --- | --- |
| The quest state is projected verbatim and fails closed | `quest_flow.gd`; 1223 checks cover all seven fields, four malformed shapes, and the corpus's real `currentQuestVars: None` reported as a recorded null | met |
| The six-branch command inventory records what each reads and writes | all six branches recorded; the no-op branch and the on-demand growth asserted | met |
| The `end_quest` destruction count is refused and recorded as a divergence | probe 4 **measured** it: legacy destroyed 1 row (40 -> 39); the endpoint leaves all 40 byte-identical, proved over the complete placed-row set | met |
| No quest reward is paid and no stored resource moves | every action's post-execution check compares the complete stored resource set; `reward`'s uniform value asserted not to produce an amount | met |
| The committed quest-content inventory is reported and never used | measured consumer counts recorded; no delivered identifier named after the reward field; `unlockedQuestIndex` never written | met |
| A quest action is a server-derived intent | request carries only a player identifier and the branch addressing; an invented key accepted; the one ignored key refused | met |
| Quest timing is recorded as client-writable and never delivered | both `fast_forward` write sites recorded; no fast-forward operation delivered; the migration recorded as migration | met |
| No executed-legacy behaviour fixture absence is claimed | six transactions + five probes captured and replayed; manifest asserts six steps | met |
| Quest evidence and claim limits | `evidence/quests/report.json`, digest `412dd271...6019`, 37,102 bytes, byte-identical across three runs | met |

## Measured in the final state, by the root

| Check | Result |
| --- | --- |
| `test_quests.gd` | exit 0, **1223 checks** |
| `test_quests.gd -- --report` x3 | digest `412dd271...6019` **identical** across all three |
| `test_research.gd` / `test_unit_behaviors.gd` | exit 0 -- **1024** / **573** |
| `test_project_scope.gd` / `test_game_api_fake.gd` | exit 0 -- **1713** / **1322** |
| `verify.ps1` | **-1** on run 1, then exit **0** with `PASS all checks succeeded` on run 2 |
| `verify-boot.ps1` | exit **0**, **37 hermetic suites, 18 live phases**; **484** log files with **zero** `[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines |
| compat discovery | **`Ran 1751 tests ... OK`**, exit 0 -- up from 1572 by **+179** |
| `validate_content.py` | exit 0, `result: valid`, 21 schemas |
| `hash_manifest.py verify` | 3,258 entries, exit 0 |

## The divergence was verified independently, and it is NOT in the transaction

The worker reported "legacy destroyed 1 row (40->39) on `end_quest`". Re-reading the captured fixture
found that the **captured transaction** shows placements **40 -> 40** with no removed map key -- correct,
because that step carried no lossy tuple. The destruction is in **probe 4**, which sends
`units = [[26, 0, 1, 0]]` so `lost = max(0, 0 - 0)` is **0**... and the root confirmed the probe records
`rows_before: 40`, `rows_after: 39`, `rows_destroyed_by_legacy: 1`, and
`recorded_end_quest_step_rows_byte_identical: true`. The worker distinguished the two rather than
letting the probe stand in for the transaction, which is exactly the honesty this project requires. The
root's own reading of the transaction is therefore recorded as **40 -> 40**, and the divergence rests on
probe 4.

## Legacy facts confirmed by the captured oracle, independently

| Fact | Root's measurement of the fixture |
| --- | --- |
| `complete_goal` mutates nothing | the captured step changed **no** `privateState` key and **no** `maps[0]` key |
| `collect_mission` stringifies | `idCurrentMission: 0 -> '5'` -- a **string** against a corpus **integer** |
| `set_quest_var` self-heals a null | `currentQuestVars: None -> dict len=1` |
| `set_goals` grows on demand | probe 1: goals **151 -> 501**, **350** appended from `set_goals([500, ...])` |
| the ignored key writes nothing | probe 2: `idSimpleChapter` produced **no** changed leaf; an invented key **was** accepted |
| the wrap | probe 3: `collect_mission([150])` -> **1**, stored type **str**, corpus type **int** |
| `reward` is unread and uniform | `{'10': 91}` over 91 entries; quoted `reward` **0**, `id` **8**, `title` **2**, everything else **0** |
| `unlockedQuestIndex` is dead | **0** legacy sites |
| `end_quest` writes quest times | `questTimes: {} -> {'7': <instant>}` |

## Both anti-invention guards were re-tested by the root, not trusted

1. copied `quest_flow.gd` to a byte-identical backup (SHA-256 `631a564d...fa12`)
2. injected `quest_reward` -> **exit 1**, **4 failures**
3. injected `mark_goal_complete` -> **exit 1**, **4 failures**
4. restored the byte-identical copy -> SHA-256 back to `631a564d...fa12`, **exit 0**, **1223 checks**

## Five cross-layer defects the hermetic suite could not catch -- the line's key finding

The offline suite builds its own response envelope, so **1223 hermetic checks passed while the live
phase failed five separate times**. Found only by `quests-live`: a fixed `addressing` wire key against
the service's per-action key; a missing `resolvable` flag that made **all six** live responses refuse
`bad_response`; `end_quest_blob` demanded unconditionally while the service sends `null` for the other
five; `int()` on a recorded null goal, a nonexistent Godot 4 constructor; and **Godot decoding every JSON
number as a `float`**. New guards were added for the class, and the suite now **asserts the double
builds no body at all**, recording *why* it could not catch any of the five. The root regards that last
guard as more valuable than the five fixes.

## Deviations and refused work

- **`game_api.gd` edited**, as permitted: all 18 live phases drive the `GameApi` facade.
- **Tasks 6.3 and the task tick were not the worker's**, since `AGENTS.md`, the README, and
  `openspec/**` were on its do-not-edit list; the root did both.
- **The root corrected one heading-level slip of its own** in the README: an appended `## Claim limits`
  was demoted to `###` to match the sibling sections.

## A third recorded flaky surface

`verify.ps1` returned **-1** on the first run and **0** with `PASS all checks succeeded` on the second,
because its windowed-capture step is display-sensitive. Together with the `verify-boot.ps1` `^ERROR:`
guard's RID-leak and `0xC06D007F` flakes, that is **three** surfaces on which a rerun is required before
treating a failure as a regression.

## Residual gaps

- **No quest reward is paid** and **no stored resource moves**; the uniform `10` is recorded as **not** a
  payout.
- **The `end_quest` destruction count is refused** as a divergence, not parity.
- **No bound** on the on-demand goals list and **no membership test** on the key writer -- both Server v1 /
  M13 gaps deliberately not filled, because closing them would make the modern service stricter than the
  legacy server.
- **No completion state exists**, and the suite asserts that absence structurally.
- `unlockedQuestIndex` reported, **never written**; **no fast-forward operation delivered**; the committed
  content **reported and never used**.
- The five **missing-key** refusals are **structurally unreachable through the typed client**, and the
  live phase proves that rather than asserting it.
- The hermetic suite **cannot** detect envelope or wire drift by construction; `quests-live` is the only
  guard for that class and is a **single** phase.
- **No pixel parity** and **no windowed capture**: nothing is rendered.
