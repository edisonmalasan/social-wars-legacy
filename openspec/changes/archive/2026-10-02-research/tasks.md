# Tasks

## 1. The research counter projection

- [x] 1.1 Implement `apps/client-godot/scripts/units/research_flow.gd`: a typed read-only projection of the two-track research vector, reporting each track's `researchStepNumber`, `researchItemNumber`, and `timeStampDoResearch` **verbatim**, with no value derived from another (D1) — verify: `test_research.gd` covers both tracks and all six values, and asserts that no remaining time, ratio, fraction, or step count is derived.
- [x] 1.2 Implement the **fail-closed** paths: an absent vector, a non-list, a wrong length, a non-integer element, and a negative element are each reported **unresolvable with their recorded state intact**, never defaulted to a zero vector presented as resolved (task 1.1's second half) — verify: the suite covers all five malformed shapes.
- [x] 1.3 Record the **four branch effects as data**, including that the item branch resets the step counter **and** the research instant **together**, and that the cash branch reads a cash value, discards it, and charges nothing (D1) — verify: the suite asserts all four effects and the pairing, and that the branch count matches the committed source.
- [x] 1.4 Record the **two tracks** with their committed names and the committed building ids `ID_BUILDING_AREA_51 = 139` and `ID_BUILDING_ROBOTIC_CENTER = 86`, and record that `TYPE_AREA_51`/`TYPE_ROBOTIC` appear **only** in branch comments and are defined nowhere (D5) — verify: the suite asserts the mapping is reported and that **no delivered code identifier is named after either track constant**, making the "never used" claim mechanical.
- [x] 1.5 Record `fast_forward` as a **fourth writer** of the research instant, naming that it subtracts a **client-supplied** number of seconds clamped at zero, and assert that **no** fast-forward operation is delivered and no elapsed-time behaviour is derived (D7) — verify: the suite asserts the writer inventory contains five writers and that the delivered operation list has no fast-forward entry.

## 2. Executed-legacy fixtures

- [x] 2.1 Add `apps/compat-api/capture_research_fixture.py` capturing each of the four branches against the committed corpus's research counters in a **disposable copy**, recording `request`, `before`, and `after` state, and proving the capture left the committed corpus **byte-identical** (D9) — verify: the capture exits 0, is re-runnable, and its manifest records the counter transitions per branch and track.
- [x] 2.2 Capture **both tracks for every branch**, giving eight branch-track combinations, and assert in the suite that all eight are covered (task 2.1's verification) — verify: the fixture manifest lists eight captured steps and the suite asserts the count.
- [x] 2.3 Add executed-legacy **parity tests** replaying each captured step against the endpoint and asserting the post-state matches (task 2.2's verification) — verify: the compat suite includes parity tests for all four branches and both tracks.

## 3. The intent-only compatibility surface

- [x] 3.1 Add `apps/compat-api/research_envelope.py` with one operation per branch, each accepting **only** a player identifier and a track, deriving every counter value and research instant server-side and **ignoring** any client-supplied counter, timestamp, or cash value (D2) — verify: the endpoint refuses a request carrying extra fields and the response echoes no ignored value.
- [x] 3.2 Apply the recorded branch effects server-side, including the item branch's **paired** step-and-instant reset and the cash branch's **instant-only** zeroing (task 1.3's contract) — verify: each action's post-state matches the recorded effect exactly, for both tracks.
- [x] 3.3 Add the refusals with **named** codes, **empty** payloads, and **no** state change: a track that is not an integer, and a research state that is not resolvable (D6, structural validity only) — verify: both refusals are asserted with their codes, empty payloads, and a byte-identical vector before and after.
- [x] 3.4 Add the **resource-unchanged proof** to every action: **every** stored resource byte-identical before and after, comparing the **complete** stored resource set and not a selected subset (D3) — verify: each action's proof compares the full set, and a test proves a selected-subset comparison would be insufficient.
- [x] 3.5 Add typed research operations to **both** GameApi implementations and a client flow that sends **only** intent, never a derived value — verify: the fake and legacy-v0 implementations return the same typed shape, and the flow suite asserts the request body carries only the player identifier and the track.

## 4. The refusals and the anti-invention guard

- [x] 4.1 Implement the **refusals as stated requirements**: no price charged and no stored resource moved; no completion, readiness, remaining-time, or unlock semantics; no counter bound, membership rule, or clamp; no reward paid (D4, D6) — verify: each refusal family is present with a non-empty reason, and the committed content's **absence** of any research cost, step count, unlock requirement, or reward is asserted against the content itself rather than assumed.
- [x] 4.2 Assert that **no committed research content is invented**: no normalized package gains a research section and no config key contains `research`, while the `Research Lab` building name and the two committed building ids are reported as content (D4) — verify: the suite asserts the measured content findings, including that `research` appears in exactly one normalized file and only inside one `name`.
- [x] 4.3 Assert the **anti-invention guard** structurally: the module's whole static-function inventory is compared against a pinned list, so a `research_price`, `research_duration`, `is_research_complete`, `research_ready`, or `unlock_research` helper fails the run wherever it is added — verify: **inject one such helper, observe the failure, restore the file from a byte-identical copy, and confirm the suite passes again**; record the exact injection and both outcomes in the review.
- [x] 4.4 **Measure** every legacy and content figure in the same run rather than asserting it: the four branch line ranges, the three counters' occurrence counts and write-only property, the `fast_forward` writer, the corpus vector, the track names and committed building ids, and the content-absence findings (task 4.3's verification) — verify: each measurement is compared against its recorded constant and a discrepancy fails the suite rather than being averaged away.

## 5. The cross-milestone correction

- [x] 5.1 Correct `godot-unit-behaviors`' **three-door** claim to **four**, naming `map_lose_item` (`engine.py:215-228`) as the fourth door because it calls `push_dead_unit`, keeping the named-branch count separate from the door count, and recording the superseded heading label and the Archive constraint (D8) — verify: the suite asserts **four** doors, names the helper, and asserts the helper is not a dispatcher branch; and the delta's body carries the "MUST NOT be renamed" note.
- [x] 5.2 Assert in the suite that the research path **does** reach the ledger, distinguishing it from the death path, so a reader consulting `godot-unit-behaviors` alone cannot conclude the ledger is unreachable from quests (task 5.1's second half) — verify: the suite asserts the quest-path door is recorded and that the death-path doors are recorded separately.

## 6. Boundary, evidence, and integration

- [x] 6.1 Register the hermetic suite in `verify-boot.ps1` and add a **`research-live`** phase with `--expect-save-mutation` driving one full step → item → reset cycle against a disposable corpus, asserting each typed response, each post-condition, and that the disposable save mutated (task 3.5's verification) — verify: `verify-boot.ps1` exits 0 end to end, the port is released, and no working-tree `saves/` is left behind.
- [x] 6.2 Write the deterministic `research-report-v1` report into `apps/client-godot/evidence/research/` via `--report=<path>`, with the bare `--report` defaulting there and the destination directory created first, recording the counter vector, the four branch effects, both tracks with their committed ids, the `fast_forward` writer, the absent-content findings, and every non-claim (D10) — verify: the report is committed, carries every required field, and a rerun reproduces its committed bytes exactly.
- [x] 6.3 Document the slice in `apps/client-godot/README.md` and add the actually executed verification commands to `AGENTS.md`, stating the "no price", "no readiness", "no bounds", and "no in-game consumer" limits wherever the slice is described (task 6.2's companion) — verify: each documented command matches one run successfully in this change.
- [x] 6.4 Run the full preservation battery in the final state and record the residual gaps: no price charged and no resource moved; no completion/readiness/remaining-time/unlock semantics; no counter bound, membership rule, or clamp; no reward paid; no committed research content invented; the track-to-building mapping reported and never used; no fast-forward operation delivered; the counters have no in-game consumer; no executed-legacy fixture absence to record; no pixel parity; no windowed capture (task 6.3's verification) — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, the compat suite is green and **grown**, `validate_content.py` exits 0, `hash_manifest.py verify` exits 0, the guard baseline reports identical digests before and after, and `git diff` shows no content-package, save, config, village, conversion-package, registry-manifest, or legacy-source byte changed.
- [x] 6.5 Perform the integration review: re-read the final diff against `proposal.md`, `design.md` D1–D10, `specs/`, and `docs/legacy-m9-progression.md`; run `openspec validate research --strict` and both batteries once more; and record a requirement-to-evidence map — verify: strict validation exits 0 with **no** "Archive would refuse" warning, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.

---

# Review record

Recorded by the root orchestrator after the Apply stage. Every figure below was **re-measured** by the
root rather than taken from the implementation worker's report, and the worker's three corrections to the
root's own brief were **independently confirmed correct**.

## Requirement-to-evidence map

| Requirement | Evidence | Status |
| --- | --- | --- |
| The research counter vector is projected for both tracks, verbatim | `research_flow.gd` `project` / `TrackView` / `ResearchView`; 1024 checks cover both tracks and all six values and assert that no remaining time, ratio, fraction, or step count is derived | met |
| The four legacy branch effects are recorded as data | `branch_record`; all four effects asserted, the item branch's **paired** reset asserted, and the cash branch's charge-nothing effect asserted | met |
| Both tracks are named and their committed building ids reported but not used | `tracks`; asserts `ID_BUILDING_AREA_51 = 139` and `ID_BUILDING_ROBOTIC_CENTER = 86` are reported, that `TYPE_AREA_51`/`TYPE_ROBOTIC` appear **4** times each in `command.py` and **0** elsewhere, and that **no delivered identifier is named after either** | met |
| `fast_forward` is recorded as a fourth writer | `instant_writers`; five writers asserted and **no** fast-forward operation delivered | met |
| A research action is a server-derived intent | `POST /v0/research` in `research_envelope.py`; `intent_body` carries only a player identifier and a track; the response echoes no ignored value | met |
| No research price is charged and every stored resource is proven unchanged | every action's post-execution check compares the **complete** stored resource set | met |
| Executed-legacy behaviour fixtures are captured | `tests/fixtures/godot-research/` — `login_post` plus **eight** branch-track steps, re-runnable across three runs | met |
| Research evidence and claim limits | `evidence/research/report.json`, `research-report-v1`, digest `e62f2666…c86`, 32,607 bytes, byte-identical across **four** runs | met |

## Measured in the final state, by the root

| Check | Result |
| --- | --- |
| `test_research.gd` | exit 0, **1024 checks**, 0 `^ERROR`/`SCRIPT ERROR` |
| `test_research.gd -- --report` ×3 | digest `e62f2666…c86` **identical** across all three |
| `test_unit_queues.gd` / `test_project_scope.gd` / `test_game_api_fake.gd` | exit 0 — **411** / **1679** / **1322** |
| `verify.ps1` | exit **0** |
| `verify-boot.ps1` | exit **0**, **36 hermetic suites, 17 live phases**; **221** log files inspected with **zero** `^ERROR:` or `SCRIPT ERROR` |
| compat discovery | **`Ran 1572 tests … OK`**, exit 0 — up from 1444 by **+128** |
| `validate_content.py` | exit 0, `result: valid`, 21 schemas |
| `hash_manifest.py verify` | 3,258 entries, exit 0 |
| `openspec validate research --strict` | valid, with **no** "Archive would refuse" warning |

## The anti-invention guard was re-tested by the root, not trusted

1. copied `research_flow.gd` to a byte-identical backup (SHA-256 `fc7ba02a…`)
2. appended one invented `static func research_price(track: int, step: int) -> int`
3. the suite **exited 1** with `NOT-PASS … failures=4` — four independent failures: no delivered
   identifier named `research_price`, the whole function inventory differs from the pinned list, the
   module declares no `research_price` helper, and the module's code contains no `research_price(`
4. restored from the byte-identical copy — SHA-256 back to `fc7ba02a…`
5. the suite returned to exit **0** with **1024 checks**

The guard is therefore **structural** — a pinned whole static-function inventory plus a forbidden-name
list — and the single remaining occurrence of the string `research_price` in the module is the recorded
`{"helper": "research_price", "absent_because": …}` refusal entry, the same shape as `ABSENT_HELPERS` on
the M8 lines, which is a *record of absence* and not a helper.

## The worker's three corrections to the root's brief were all confirmed correct

The root's brief asserted that `research` appears in exactly **one** normalized file and only inside one
`name` value, and that `config/main.json` has **no** key containing `research` at any depth. Both were
false, and the root re-measured before accepting:

1. **`research` appears in TWO normalized files**: `buildings.json` **1** occurrence and `images.json`
   **6**, totalling **7**. The `images.json` occurrences come from **three** rows —
   `popupResearchCenter_buildingProcess.swf`, `_2.swf`, `_3.swf` — each contributing the word twice
   (`legacy_id` and `path`), so 3 rows yield 6.
2. **`config/main.json` DOES have three nested keys** containing it, all under `/images`
   (`/images/popupResearchCenter_buildingProcess{,_2,_3}.swf`), and exactly **one** string value
   (`/items/244/name = "Research Lab"`). The accurate claim is that **no top-level** key contains it.
3. **The building's `legacy_id` is the STRING `"256"`** — an integer comparison finds no such row, and
   **every** `legacy_id` in `buildings.json` is a string.

**The conclusion is unchanged**: every hit is an **asset name** or a **display name**, so there is still
no committed research cost, step count, unlock requirement, or reward. But the root's original
investigation **overstated** the absence, and `docs/legacy-m9-progression.md` now carries a corrections
section rather than quiet edits.

## Everything else the worker claimed measured correct

Re-verified by the root: the four branch line ranges `268–274`, `276–282`, `284–291`, `293–300`, each
confirmed **by content** rather than by line number; `TYPE_AREA_51` and `TYPE_ROBOTIC` at **4** and **0**;
`researchStepNumber` **3** sites (`271`, `288`, `297`), `researchItemNumber` **2** (`287`, `296`),
`timeStampDoResearch` **5** (`272`, `280`, `289`, `298`, `923`) — **all** in `command.py` and only in
`command.py`; `seconds = args[0]` at `906`, read at `923`, write at `927`; and the corpus at `[0, 0]`.

## Fixture containment, re-verified by the root

- the last step's `after.json` is **byte-identical** to the first research step's `before.json`
  (both `fd3aee7c…`), so the capture's own steps chain without a gap
- that first `before.json` is **parse-equal** to the committed corpus (it differs only in formatting)
- the manifest's recorded corpus digest `25df5b5a…` **matches** the live working-tree corpus
- `git status` shows exactly one path under `tests/fixtures/` — the **new** untracked directory — with
  **no** prior fixture modified and none deleted

## A measurement that STRENGTHENED the cross-milestone correction

`map_lose_item` is `engine.py:215-228` with `push_dead_unit` called at **223**, and the root measured its
only **two** callers: `command.py:796` inside **`end_quest`** and `command.py:872` inside
**`end_attack`**. The fourth dead-hero door is therefore reached from **two** branches — the quest path
*and* the attack path — not one. `godot-unit-behaviors` is corrected from three doors to four.

## A tool constraint measured rather than worked around

A MODIFIED delta resolves its header against the existing requirement name, and the tool warned that
Archive **would refuse** a renamed heading. No archived change uses `RENAMED Requirements` and
`openspec instructions specs` does not document the form, so a rename was not a verified path. The
`godot-unit-behaviors` requirement keeps its now-stale **"three-door"** heading as a documented
**superseded label**, with the four-door correction in its body and an explicit "MUST NOT be renamed"
note, so a future reader does not "fix" the heading and break Archive.

## Deviations, approved

1. **`/v0/research` placed before `v0_level_up`** rather than after. Two already-delivered suites slice
   `compat_service.py` from `def v0_level_up()` to the corpus constant and `ast.parse` the result;
   inserting a route between them broke that slice. The route was moved rather than two delivered tests
   edited, and both pass unchanged.
2. **`game_api.gd` edited** though it was outside the ownership list — all 17 live phases drive through the
   `GameApi` autoload facade, so the `research-live` phase would otherwise have instantiated
   `LegacyV0Api` directly. Additive: one preload, one counter, one forwarder in the shape of the 16
   existing ones. `test_game_api_fake` (1322 checks) still passes.
3. **The item branch's instant half is a recorded 0→0 transition.** Eight steps cover eight combinations
   with no room for a priming step, and the recorded order had already zeroed both instants. The branch's
   *step* half (1→0) and *item* half (0→1) are real transitions; the pairing is established by
   `command.py:288-289`. Recorded in the manifest and asserted rather than papered over.

## Defects found by measurement, and one latent class carried forward

The worker fixed **three** real defects by measurement rather than reading: the route reported
`derived.step: null` on the stamping branch though only the *instant* is non-derivable; `_parse_vector`
rejected the endpoint's flat `counters` field; and the fake double did not load boot fixtures first, so it
answered with an empty `game_version` and `server_time: 0` when reached before any boot read — caught only
by the live phase.

**Carried forward:** Godot 4.7.2's `%` operator does **not** support `%r`, and **pre-existing `%r` uses
remain latent bugs on error paths** in `game_api.gd:176`, `boot_data.gd:1282,1312`, and
`fake_api.gd:2216,2237,2909,2910,2914`. They are on paths the suites never take, which is why they went
unnoticed. Narrowing `verify-boot.ps1`'s `^ERROR:` guard remains the other carried follow-up.

## Residual gaps

- The delivered feature means **these counter transitions and nothing more**, because the counters have
  **no in-game consumer**.
- **No price is charged** and **no stored resource moves.**
- **No completion, readiness, remaining-time, or unlock semantics**; **no counter bound, membership rule,
  or clamp** is added, so a client could still send track `7` or `999` — a Server v1 / M13 gap.
- **No reward** is paid; **no committed research content is invented**, none existing.
- The **track-to-building mapping is derived-provisional**, reported and structurally unused.
- **No fast-forward operation is delivered**; the client-writable decrement is recorded only.
- Fixture parity covers **eight** transactions against the fresh-player corpus only.
- **No pixel parity** and **no windowed capture**: nothing is rendered and the corpus places neither
  research building.
