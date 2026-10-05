# Social Wars Modernization & Flash-Free Reconstruction Roadmap

**Project:** Social Wars Legacy Reconstruction  
**Primary Goal:** Reconstruct the existing Social Wars implementation into a modern, maintainable, Flash-free client/server game while preserving the behavior, content, saves, assets, and historical implementation contained in the current repository.

**Core Strategy:** Preservation-first reconstruction.

The existing repository will **not** be thrown away or treated merely as obsolete code.

It will serve as:

- Reference implementation
- Behavioral specification
- Protocol specification
- Preservation dataset
- Save-game corpus
- Content database
- Asset archive
- Regression oracle
- Migration source
- Historical documentation

The modern version will progressively replace Flash/SWF functionality with a Godot client while preserving the existing Python server until behavioral parity has been verified.

Only after the new client is substantially functional should the backend be modernized into an authoritative production architecture backed by PostgreSQL.

---

<!-- ORCHESTRATOR_STATUS_START -->

## Project Status

This section is maintained by the root Codex orchestrator.

It is a progress ledger, not the source of truth for specified behavior.

- **Current milestone:** **M10 — Missions and Combat — IN PROGRESS; lines 1 and 2 are DELIVERED and ARCHIVED, and two further deliver items were CLOSED by measurement rather than deferred.** The milestone opened with a committed investigation, **`docs/legacy-m10-missions.md`** (PR #283, merged `e4fc5e2`), and its verdict reframed the first objective before any code was written: **mission *state* was already delivered.** `collect_mission` (`command.py:430-442`) is the **only** mission-mutating command in the preserved server and is owned by `godot-quests`; `idCurrentMission` has **2** writes and **0** reads; `timestampLastChapter` has **2** writes and **0** reads, the second inside `fast_forward` as a client-supplied subtraction; **there is no mission-loading command**; and all **ten** committed save documents have `maps` of length **1** with `default_map` 0. So the first objective was **not** "mission loading" — that phrase does not mean a mission map, one of the four corrections the investigation records — and the only undelivered surface was **vocabulary**. **M9 — Progression remains CLOSED** with its exit criterion "Primary long-term progression systems work" **NOT MET**, a property of the **oracle** rather than of the modern client. **M8 — Units** is COMPLETE with its exit assessed MET, all eight lines delivered and archived; **M7 — Construction and Economy** remains complete with its exit assessed MET, as do M6 and the M0—M5 deliver lists.
- **Roadmap cursor:** **M10 — Missions and Combat**, advanced to its **second** objective in roadmap and dependency order: **combat actions**. Its deliver list is `mission loading`, `mission state`, `combat actions`, `damage`, `death`, `mission completion`, `rewards`, and its exit criterion is *"Primary combat loop works."* **Nothing in M10 beyond line 1 is pre-authorised.** The cursor moved because the investigation **closed** the first two deliver items rather than deferring them: `mission loading` has **no command in the preserved server**, and `mission state` was **already delivered** by `godot-quests`. That is the same reasoning that closed M9 — a milestone is not unfinished work when the behaviour being asked for has no oracle to reproduce — and it is recorded as a **measurement**, not a waiver: the absence of a mission-loading command is a finding about the preserved server, not a gap in the modern client. **The vocabulary that line 1 delivered is the reason the cursor is `combat actions` specifically.** The 64 `MISSION_*` declarations name the combat events the game once recognised — `MISSION_ATTACK_PLAYER` (37), `MISSION_ATTACK_FRIEND` (38), `MISSION_ASSAULTS_WON` (46), `MISSION_KILLED_ENEMY` (67), `MISSION_DEFEAT_ALL_TROLLS` (30), `MISSION_SACRIFICE_UNIT` (63), `MISSION_COORDINATED_ATTACK` (61), `MISSION_CAPTURED_SUBCATFUNC` (11) / `MISSION_CAPTURED_ID` (12) — so it is the only surviving statement of what the combat lines must resolve, and it resolves none of it. The next step is a **committed investigation for combat actions** on its own `docs/`-scoped branch and PR, establishing which combat branches exist, what each writes, what is server-derived versus client-sent, whether the corpus can genuinely exercise them, and whether any executed-legacy fixture can be captured **without fabricating player state**.

  **Per-line findings for M9 lines 1-3, carried forward verbatim** (the detail the previous
  cursor sentence accumulated; none of it is superseded by the assessment):

  Lines 1–3 established, each from committed source and executed probes rather than by pattern: **line 1 `research`**
  found a closed four-branch set over a three-counter, two-track vector whose counters are **WRITE-ONLY**
  (`researchStepNumber` **3** sites, `researchItemNumber` **2**, `timeStampDoResearch` **5** — the four branch writes
  plus **one read at `command.py:923` that is itself a write**, inside `fast_forward`, subtracting a
  **client-supplied** number of seconds clamped at zero), so **no research price is charged** and no readiness,
  completion, or unlock rule exists; **line 2 `quests`** found that **only TWO committed quest fields have any legacy
  consumer** (`id` **8**, `title` **2**, the latter being two `print` statements), that **`complete_goal` mutates
  nothing at all**, and that the `end_quest` destruction count is a **client-dictated** number that is therefore
  **refused** and recorded as a **measured divergence** — the legacy server destroyed a placed row, 40 → 39, while the
  modern endpoint leaves all 40 byte-identical; **line 3 `tutorial/progression`** found the **entire tutorial system**
  to be `command.py:60-66` — one branch, one local, one write — where `completed_tutorial` occurs **once** across the
  eleven legacy root modules on **one** line, that line being the **write**, with **zero readers**, making it the
  **tenth** committed field in this project with no legacy consumer; `tutorial_step` occurs **4** times over **3**
  lines and is a **local that is never persisted**, so there is **no stored step and no un-complete path**; the gate
  `tutorial_step >= 25 or tutorial_step == 15` has **no lower bound, no upper bound, and no type check**, and its
  **hole is exactly `16..24`**, nine values wide; and `config/main.json` plus every normalized package hold **zero**
  occurrences of `tutorial`, so there is no step list, no count, no gate definition, and no tutorial text to derive.
  **Line 3 is the first M9 line that is not a refusal line**, and the instruction to measure its own fields rather
  than assume the pattern repeated is what made that visible. **Line 1 also carried the cross-milestone correction**
  that `godot-unit-behaviors` claimed **three** doors into the dead-hero ledger where measurement makes it **four**:
  `map_lose_item` (`engine.py:215-228`) calls `push_dead_unit` at **223**, and its only **two** callers are
  `command.py:796` inside **`end_quest`** and `command.py:872` inside **`end_attack`**, so the fourth door is reached
  from the quest path and the attack path rather than the death path alone. **quest path and the attack path**, not
  the death path alone. **Line 2, `quests`, was the largest surface in M9** and it delivered the six branches
  `set_goals`, `complete_goal`, `set_quest_var`, `end_quest`, `admin_set_quest_rank`, and `collect_mission` against
  committed content normalized at **91** entries of a uniform ten-field shape and a corpus carrying real quest state
  (`goals` at **151** entries, **all `None`**; `questsRank` `{}`; `unlockedQuestIndex` `0`; `questTimes` `{}`;
  `currentQuestVars` **`None`**; `idCurrentMission` `0`). **Only TWO committed quest fields are read by anything**,
  measured as quoted occurrences so comments cannot contribute: `id` has **8** and `title` has **2**, the latter being
  the two `print` statements; every other committed field has **zero** consumers, and **`reward` has zero while being
  committed on all 91 entries and uniformly the value `10`**, so it carries no information even if it were read. There
  is therefore **no quest reward, cost, or price to derive**, and none is derived. **`complete_goal` mutates nothing
  at all** and the executed fixture proves it: the captured transaction changed **no** `privateState` key and **no**
  `maps[0]` key, so a goal completes by being narrated in a `print` statement and no completion state exists. **The
  `end_quest` destruction count is REFUSED, and the divergence is measured rather than asserted:** probe 4 sent
  `end_quest` with `units = [[26, 0, 1, 0]]` so the legacy branch's client-computed `lost = max(0, unit[2] - unit[3])`
  was **1**; the legacy server **destroyed a placed row, 40 -> 39**, while the modern endpoint derives `units: []`,
  destroys nothing, and leaves **all 40 rows byte-identical**. The manifest records that as a **divergence**, not as
  parity, and separately records that the *captured* transaction's rows were byte-identical because that step carried
  no lossy tuple. Reproducing a client-dictated destruction count would be exactly the anti-pattern `AGENTS.md` names
  as Bad. Three legacy type and shape facts are reproduced rather than normalized, each confirmed by the captured
  oracle: `collect_mission` wrote `idCurrentMission` as the **string** `'5'` against a corpus recording the
  **integer** `0`; `set_quest_var` self-healed `currentQuestVars` from the corpus's `None` to a dict; and `end_quest`
  wrote `questTimes` `{}` to `{'7': <instant>}`. **Three more probes establish the refusals with executed evidence:**
  `set_goals([500, "[0,0]"])` grew the list from **151 to 501** entries, **350** appended from one client-sent id with
  **no upper bound**, so the endpoint **reproduces** the unbounded growth rather than closing it;
  `set_quest_var(["idSimpleChapter", 5])` wrote **nothing** (the branch returns at `command.py:95` before any write)
  while an **invented key was accepted**, so exactly one key is refused and it is the one the legacy branch itself
  ignores; and `collect_mission([150])` **wrapped** to `1` at bound `99`, stored as a `str`. `unlockedQuestIndex` is
  reported and **never** written, having zero legacy sites, making it the **ninth** zero-consumer committed field in
  this project.
- **Line 1 selection:** the record recommends **research** as the first M9 line, and the reasoning is recorded rather than assumed. It is the only family that is (a) entirely undelivered, (b) a **closed four-branch set** with a single three-counter state vector, so one line can cover it without an open-ended surface, (c) **fully exercisable** by the committed corpus at its initial values, (d) the one with the clearest authority story, because the two counters advance on the client's word and the one price-taking branch **charges nothing** — which makes the refuse-the-cost / prove-unchanged pattern of M7 and M8 directly applicable — and (e) it requires no content package that has not already been normalized. Quests is the largest surface and is the natural **second** line; `quests.json` already holds **91** entries with a uniform ten-field shape, so its content side is ready when its turn comes.
- **Active OpenSpec change:** **NONE.** `openspec list` reports no active changes; `combat actions` is archived as `2026-10-05-combat-actions`. It added **one** new capability, **`godot-combat-actions`** (**ADDED**, **7 requirements**), and **modified** `godot-unit-behaviors` with **two** requirements. The spec sync (#291 `2081161`) is what carried the correction of `godot-unit-behaviors`' corpus premise into the main specs, which is why the correction is in the **spec** and not only in the prose: the merged record said "the committed corpus places only buildings and no unit row", which is true of `tests/saves/fresh-player.json` and **false of the repository**, which places **441** committed unit rows across **7** of the **10** committed save documents. The requirement that **no combat is resolved** was deliberately **not** modified, because this line resolves none either.
- **Lifecycle stage:** **ARCHIVED** for `combat actions`, on its own branch, as `2026-10-05-combat-actions`. Full lifecycle, each stage its own remote branch and merge-commit PR: investigation #288 `f21c111`, proposal #289 `6d9f2d0`, Apply #290 `d4e42a1`, Sync #291 `2081161`, and this archive. Every stage was pushed to `origin` before any edit, and no branch was reused across stages.
- **Change status:** **M10 lines 1 and 2 are delivered and archived**, and it is **M10's first deliver line**. The milestone's first two listed items — `mission loading` and `mission state` — are **resolved before implementation**, not delivered: the first has **no command in the preserved server** and the second was **already delivered** by `godot-quests`. What the line delivered instead is the **vocabulary** that the remaining combat items must eventually resolve, plus the **zero-consumer measurement** that makes the rest of M10's shape predictable. `openspec list` reports **no active changes**.
- **M8 exit assessment: MET** — exit criterion "Core unit gameplay works" is satisfied by committed evidence across all eight delivered lines, each
- **M7 exit assessment: MET** — (unchanged; see the detailed assessment above)
- **Current objective:** This orchestration run took **M10 line 2 — `combat actions`** through its **complete lifecycle**. The investigation inverted the line's expected shape by **disproving a merged record**: `godot-unit-behaviors` claimed no executed-legacy fixture was capturable because the corpus places no unit row, which is true of the fresh-player document alone and false of the repository, which places **441** unit rows across **7** of **10** committed save documents with **five** village documents carrying a non-empty ledger. So the line **is** capturable, against `villages/AcidCaos.json` and `villages/Neutral.json`. It is also **not** a refusal line, because `end_attack`, `kill`, `sell`, and `resurrect_hero` all mutate state. What it delivered is **one** server-derived destruction with the client-dictated count **refused**, and the legacy `max(0, sent - survived)` arithmetic recorded as a **divergence** rather than reproduced. Design D1 was load-bearing and was not widened.
- **Last completed change:** `mission vocabulary` — archived as `2026-10-05-mission-vocabulary` (#283 `e4fc5e2` investigation, #284 `dc4dbaf` proposal, #285 `d437ede` Apply, #286 `80c6cd9` Sync, and this archive). Before it: M9's `unit experience evidence` — `2026-10-04-unit-experience-evidence` (#276 `79d13ac`, #277 `8b51b16`, #278 `d0d70a3`, #279 `131a133`, and its archive). Before that: `stored item placement` — `2026-10-03-stored-item-placement` (#271 `6bb7a46`, #272 `dbf4491`, #273 `62e6328`, #274 `eab756b`).
- **Next eligible objective:** **Investigate M10's remaining open line — `damage`.** Nothing in M10 beyond line 2 was pre-authorised, so the next stage is a **committed investigation** on its own `docs/`-scoped branch and PR, establishing what damage rules the preserved server has at all. Two deliver items are already **closed by measurement** (`mission loading` has **no command** in the preserved server; `mission state` is **already delivered** by `godot-quests`), and the remaining open items are `damage`, `death`, `mission completion`, and `rewards`. `death` is partly delivered already — `godot-unit-behaviors` projects the ledger and `godot-unit-production` records that resurrection is unreachable from the delivered client — so the investigation should measure rather than assume. The **M10 exit criterion is "Primary combat loop works"**, and the 64 `MISSION_*` declarations are the only surviving statement of what the combat lines must resolve.
- **Last OpenSpec validation:** PASS — `combat-actions` **at Archive** (2026-10-05): `openspec validate --all --strict` reports **63 passed / 0 failed across 63 items**, exit `0` — the same 63 items as the pre-archive baseline, because the archived change stops counting as an item while its new capability becomes one; the count was **64** while the change was active. `openspec validate godot-combat-actions --strict` passes and emits only the repository's standing long-requirement INFO notices.
- **Last implementation verification:** Integration review over `mission-vocabulary`, with the batteries re-run in the final state by the root orchestrator — orchestrator-run, not an independent agent. Actually executed: `test_mission_vocabulary.gd` **208 checks** PASS (exit 0), the **41st** hermetic suite, and **211** with `--report`; `test_project_scope.gd` **1,832** (was **1,798**); `test_content_registry.gd` **87**, `test_game_api_fake.gd` **1,322**, `test_scene_build.gd` **36**, `test_quests.gd` **1,223**, `test_tutorial.gd` **639** — **all unchanged**, which is the evidence that the line adds no endpoint and no registry entry; `test_unit_experience.gd` **2,470** (was **2,430**); `verify.ps1` exit **0** with `PASS all checks succeeded`; `verify-boot.ps1` exit **0** with **41 hermetic suites** (up from 40) and **20 live phases** (**unchanged**), guard digest identical pre/post (`6978b959...ff348`), port 5056 released, no working-tree `saves/`, and **682** log files inspected with **zero** `[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines; compat **`Ran 2187 tests ... OK`**, exit **0** — **unchanged**, because the line touches `apps/compat-api/**` not at all; `validate_content.py` `result: valid`, 22 files / 21 schemas / 604 references; `hash_manifest.py verify` **3,258 entries**; and the report digest `1aeee8d2...b6f4b`, **13,850** bytes, byte-identical across **four** consecutive runs. **Eight anti-invention guards were proven by injection with a byte-identical restore**, none merely observed to pass: an invented dispatch helper (**5** failures), a helper named after a mission type (**5**), a suffixed absent helper caught by the substring check (**5**), a mission-state reference (**4**), a colliding mistranscribed value (**3**), a clean mistranscribed value (**3**), a mistranscribed name (**2**), and a removed entry (**3**). **Three defects in this line's own work were found by measurement and closed, and all three are recorded rather than shipped quietly.** (1) The projection **silently dropped entries**: the ordering pass used the *last entry in file order* as its `range()` bound, so one mistranscribed value shrank the projection **64 → 63** and surfaced as an entry-count mismatch rather than as the value mismatch it actually was — and a min/max fix was then **refused by the suite's own guard** for adding exactly two comparisons over a committed value, the final fix sorting the value keys instead. (2) The by-name guard was **case-sensitive**, so `mission_killed_enemy` would have slipped past it. (3) A **deliberate refusal test failed the battery**, because `JSON.parse_string` emits an engine `ERROR:` line for malformed input and `verify-boot.ps1` treats any `^ERROR:` as a script error, so non-object documents are now refused *before* the parser is invoked — same verdict, no engine error, coverage kept rather than dropped. **`evidence/boot/boot-report.json` was regenerated** because registering a suite invalidates its bytes, and the change was verified by comparing name **multisets**: assertions **204 → 206** and commands **67 → 68** with **nothing removed** in either, and no other top-level key differing except `environment.git_commit` and `generated_utc`. The ~100 `CHG` lines a naive diff shows are an **index shift** from inserting the suite at index 45, not a change to any existing assertion — the same obligation the `building-resources` line faced when a label correction invalidated its evidence. **A tooling note for the next run:** the shell's native-command capture intermittently dropped both stdout and `$LASTEXITCODE` for the Godot executable, returning **0 lines and an empty exit code**; every suite in this line was therefore run through `Start-Process -Wait -PassThru -RedirectStandardOutput`, which reported exit codes reliably. This is a **sixth** known flaky surface, in the harness rather than in the checks, and it is **recorded rather than fixed** because it is environmental.
- **Last verified commit:** `2081161` — the M10 line 2 spec-sync merge (`2081161`), behind the Apply merge `d4e42a1` on which the eight executed-legacy probes and the corpus inventory were measured. No implementation commit exists yet for `combat-actions`.
- **Last updated:** 2026-10-05 (**`combat actions` ARCHIVED** — M10 line 2, after M10 line 1 `mission vocabulary` ARCHIVED). New capability `godot-combat-actions`; `godot-unit-behaviors` **modified** with **two** requirements. **The finding: the milestone's second line is not a refusal line, because a delivered record said it was.** M8 recorded that no executed-legacy fixture could be captured since "the committed corpus places only buildings and no unit row, and its ledger is present and `{}`". Measured across all **11** committed save documents: **441** committed unit rows across **7 of 11**, **all** team one, **429** ledger-satisfying, and **five** village saves with a **non-empty** `deadHeroes` ledger. That is the **second** occurrence of this exact delivered-claim defect in the repository, M9's `unit-experience` line having corrected the identical claim for `attr["xp"]`. **It is contractual, not prose:** the premise sits in a merged requirement's SHALL text and a scenario, so the correction is carried as two `MODIFIED` requirements rather than deferred. **The eight probes make it a working line.** `end_attack` destroys **two** committed unit rows from one client tuple (319 → 317) and writes `{'1007': 2}`; `lost = 9999` destroys exactly 2 because the bound is **exhaustion, not a check**; the two absent-value failures sit on **opposite sides** of the write loop, which makes validation ordering load-bearing; `kill` never touches the ledger, `sell` behind the literal `"KILL"` is the second door, `kill_iid` mutates nothing, and `resurrect_hero` against `Neutral.json`'s committed 28-key ledger **directly disproves** the delivered claim. **Design D1:** the request addresses a lost unit **identity** and the service derives exactly one eligible row, because no combat rule exists to derive a count from; the difference from the legacy server is a recorded **divergence**, not parity. **Two harness failures recorded, not smoothed over:** a stdout result marker shared with the code under test lost a probe to the legacy loader's unterminated prints, and the first run leaked a temp directory by aborting before cleanup existed. **A second discrepancy is recorded, not corrected:** four of five M8 combat-field figures reproduce under no counting rule measured — this measurement finds zero for all four, strengthening M8's direction while leaving its figures unreproduced. `syringes` is carried on **all 429** units and **all 470** buildings and read by **nothing**.

### Resume point (updated after the `mission-vocabulary` archive, orchestrator)

**M8 — Units is COMPLETE, all eight lines delivered and archived, exit criterion "Core unit
gameplay works" assessed MET.** **M9 — Progression is CLOSED**: four lines delivered and
archived (`research`, `quests`, `tutorial/progression`, `stored item placement`), the
`unit-experience-evidence` correction line archived, and its exit criterion "Primary long-term
progression systems work" **NOT MET** — because nothing in the committed legacy server reads
progression state back to change what a player may do. That is a property of the **oracle**,
not of the modern client.

**M10 — Missions and Combat is IN PROGRESS, with line 1 of 8 deliver items delivered and
archived** as `2026-10-05-mission-vocabulary` (#283 `e4fc5e2`, #284 `dc4dbaf`, #285
`d437ede`, #286 `80c6cd9`, and its archive).

**M10 opened by measuring two of its own deliver items out of existence, which is the single
most important thing to know before starting line 2.** The milestone investigation
(`docs/legacy-m10-missions.md`) found that **mission state was already delivered**:
`collect_mission` at `command.py:430-442` is the **only** mission-mutating command in the
preserved server and is owned by `godot-quests`; `idCurrentMission` has **2** writes and **0**
reads; `timestampLastChapter` has **2** writes and **0** reads, the second inside `fast_forward`
as a **client-supplied** subtraction; **there is no mission-loading command at all**; and all
**ten** committed save documents have `maps` of length **1** with `default_map` 0. So the
roadmap's first listed objective, "mission loading", names something the legacy server does not
do — one of four corrections the investigation records, the sharpest being that **"mission
loading" does not mean a mission map**.

**The cursor is therefore `combat actions`, and nothing beyond it is authorised.**

**Why the vocabulary line came first, and why it precedes combat.** The 64 `MISSION_*`
declarations at `constants.py:984-1047` are the largest single block of unconsumed vocabulary in
the preserved server, and they are the **only surviving statement of what the combat lines must
resolve**: `MISSION_ATTACK_PLAYER` (37), `MISSION_ATTACK_FRIEND` (38), `MISSION_ASSAULTS_WON`
(46), `MISSION_KILLED_ENEMY` (67), `MISSION_DEFEAT_ALL_TROLLS` (30), `MISSION_SACRIFICE_UNIT`
(63), `MISSION_COORDINATED_ATTACK` (61), `MISSION_CAPTURED_SUBCATFUNC` (11) and
`MISSION_CAPTURED_ID` (12). They resolve none of it, and they are delivered before combat so
that the combat investigation starts from a named vocabulary rather than an inferred one.

**The finding is that the vocabulary exists and nothing ever read it.** A first classifier
reported three consumers at `constants.py:997`, `:998`, and `:1012`; **all three are substring
artifacts**. The suite re-measures the absence on every run across the **ten** other legacy
modules and requires **zero** `MISSION_` occurrences. Zero consumers is why the line adds **no
endpoint**, **no** executed-legacy fixture, and **no** live phase — a vocabulary with no consumer
has no transaction to capture — and the live-phase count holding at **20** while a new hermetic
suite registered is the evidence that this is measured rather than asserted.

**Four measurement lessons from this line, carried forward as instructions for line 2.**
1. **A substring is not a consumer.** `MISSION_DESTROYED` prefixes
   `MISSION_DESTROYED_SUBCATFUNC` and `MISSION_DESTROYED_ID`. Count occurrences per line,
   quote-aware, and record occurrence counts **separately** from distinct-line counts.
2. **Case is the same disguise as a suffix.** The by-name guard had to be strengthened to
   case-insensitive *after* measuring that the module was clean case-insensitively; strengthen
   the guard only once the clean measurement exists, or you are guessing.
3. **Opening a file in text mode silently translates CRLF to LF.** An earlier probe made a CRLF
   tree look LF-only. The byte-faithfulness guard therefore reads `constants.py` **as bytes**,
   and any byte-level claim in this repository should do the same.
4. **The suite's own guard can refuse your first fix.** The entry-dropping defect's min/max
   repair was rejected for adding two comparisons over a committed value; the repair that
   satisfied the constraint was a sort. When a guard refuses a fix, treat it as information
   about the contract rather than an obstacle to route around.

**Three defects in this line's own work were found by measurement, not by luck, and all three
are recorded rather than shipped quietly** — the entry-dropping defect whose min/max fix was
itself refused; the case-sensitive by-name guard; and a deliberate refusal test that failed the
battery because `JSON.parse_string` emits an engine `ERROR:` line that `verify-boot.ps1` treats
as a script error. **Eight guard injections were all detected** (5/5/5/4/3/3/2/3 failures), each
followed by a byte-identical restore.

**A sixth flaky surface is now recorded, and it is in the harness rather than in the checks:**
the shell's native-command capture intermittently dropped **both** stdout and `$LASTEXITCODE`
for the Godot executable, returning 0 lines and an empty exit code. Run Godot suites through
`Start-Process -Wait -PassThru -RedirectStandardOutput`, which reported exit codes reliably
throughout this line. The five pre-existing surfaces (the `^ERROR:` RID-leak guard, the
transient `0xC06D007F` module-load crash, the live-phase `%`-binding parse error, and
`verify.ps1`'s display-sensitive capture) remain open; two earlier ones were closed by fixing
the guard rather than re-running.

**M10 line 2's investigation is committed and merged (#288 `f21c111`, `docs/legacy-m10-combat.md`), and
it inverted the line's expected shape.** It found that **M8's `godot-unit-behaviors` recorded a false
premise**: that no executed-legacy fixture could be captured because "the committed corpus places only
buildings and no unit row, and its ledger is present and `{}`". That is false of the repository and
true of `tests/saves/fresh-player.json` alone. Measured across all **11** committed save documents
(**3,372** placed rows): **441** committed unit rows across **7 of 11** documents, **all** on team one,
**429** satisfying the `resurrectable` gate, and **five** village saves carrying a **non-empty** ledger
(`Neutral` 29 keys, `Kiriakos` 9, `Nerri` 9, `Scarlet` 2). **This is the second time the repository
has caught that exact delivered-claim defect** — M9's `unit-experience` line corrected the identical
claim for `attr["xp"]`. **The correction therefore cannot be deferred**: the false premise sits in a
**merged requirement's SHALL text and a scenario**, so a sibling capability capturing a combat fixture
would leave two merged specs contradicting each other.

**The eight executed probes make this a working line, not a refusal line.** `end_attack` with
`attacker_units=[[1007,1,3,1]]` destroys **two** committed unit rows (319 → 317) and writes
`deadHeroes {'1007': 2}`; `lost = 9999` destroys exactly **2**, because `map_lose_item` returns when no
row matches — the bound is **exhaustion, not a check**. **The ordering is the sharpest finding:**
omitting the loss list raises **before** the save is touched, while omitting the victim record raises
**after** two rows are gone and the ledger is incremented, so validation ordering is load-bearing.
`kill` deletes a row and **never** touches the ledger; `sell` behind the literal `"KILL"` is the second
ledger door (`KILL` is a string literal at `command.py:159`; the constant is never read by the
dispatcher); `kill_iid` **mutates nothing**; and `resurrect_hero` against `Neutral.json`'s committed
28-key ledger decrements one key and re-places a row at client-supplied cells — **directly disproving
the delivered claim**.

**Two harness failures are recorded rather than smoothed over**, both about trusting a guarantee
unearnedly: a result marker on **stdout** — shared with the code under test — lost one probe's outcome
to the legacy loader's unterminated `print(..., end='')`, so the marker moved to a file; and the first
run **leaked a temp directory** by aborting on Windows symlink elevation *before* cleanup existed. A
containment guarantee established by the happy path is not a guarantee.

**A second discrepancy is resolved, not deferred.** The four M8 combat-field figures deferred above
reproduce under **no** legacy-consumer counting rule — this measurement finds exactly **zero** for all
four, which **strengthens** M8's direction — but the line that owned those fields also established
*why* they were never reproduced, and it is not an error. Each reproduces **exactly** as the
`unit_distinct` column of `unit_behaviors.gd`'s own `ZERO_CONSUMER_FIELDS` table: the count of
**distinct committed values over the 429 committed unit definitions**. So `attack` 131, `defense` 1,
`life` 150, `min_level` 21, and `syringes` 6 are **all five of five** content-distribution counts,
not consumer counts. The record's numbers were correct and its **placement** misleads: it reads as a
consumer census and is a distribution census. **M8's conclusion is left intact and strengthened**,
and **no figure was silently replaced** — see the annotation in `AGENTS.md`. This change's own
proposal counted "four of five" and was itself off by one.

**This line is archived; the cursor advances to `damage`.** Design **D1** was load-bearing and was
**not widened**: the request addresses a **lost unit identity** and the service destroys **exactly
one** eligible row it derives itself, because no combat rule exists to derive a *count* from —
reproducing `max(0, sent - survived)` would be the `AGENTS.md` "Bad" pattern and the same
anti-pattern M9's `end_quest` refused. The resulting difference from the legacy server is recorded as
a **divergence**, never as parity. **Do not start damage, death, mission completion, or rewards**;
each is a separate later line, and each needs its own investigation before any proposal.

**Delivered and archived, M9 lines 1-3:**

| Line | Archive | PRs and merges |
| --- | --- | --- |
| `research` | `2026-10-02-research` | #251 `0b57e83` (cursor), #252 `3d44159` (measure), #253 `e630da3`, #254 `44d1fa9`, #255 `0efe16c`, #256 `49e96ce`, #257 `ece6246` |
| `quests` | `2026-10-03-quests` | #258 `0e886f2` (inv), #259 `049fa5a`, #260 `eefa6a0`, #261 `ae4c21f` (cursor), #262 `286152e`, #263 |
| `tutorial/progression` | `2026-10-03-tutorial` | #264 `2dbf715` (inv), #265 `960e143`, #266 `9f2325f`, #267 `2c69b33`, #268 `95c7f27` (guard follow-up), and this archive |

**M10 line status:**

| Line | Change | Stage reached |
| --- | --- | --- |
| **M10 line 2 — `combat actions`** | `2026-10-05-combat-actions` (**archived**) | investigation #288 `f21c111`, proposal #289 `6d9f2d0`, Apply #290 `d4e42a1`, Sync #291 `2081161`, and this archive |

| Line | Change | Stage reached |
| --- | --- | --- |
| **M10 line 1 — `mission vocabulary`** | `2026-10-05-mission-vocabulary` (**archived**) | investigation #283 `e4fc5e2`, proposal #284 `dc4dbaf`, Apply #285 `d437ede`, Sync #286 `80c6cd9`, and this archive |

| Line | Change | Stage reached |
| --- | --- | --- |
| `stored item placement` (closing the `collections` gap) | `2026-10-03-stored-item-placement` (**archived**) | investigation #271 `6bb7a46`, proposal #272 `dbf4491`, Apply #273 `62e6328`, Sync #274 `eab756b`, and this archive |

**Delivered and archived, M8 lines 1-8:**

| Line | Archive | PRs and merges |
| --- | --- | --- |
| `unit definitions` | `2026-10-01-unit-definitions` | #204 `cf13a5b`, #205 `72f87a3`, #206 `43b8ed4`, #207 `5e43bc0` |
| `unit instances` | `2026-10-01-unit-instances` | #208 `235b4d2` (inv), #209 `0710038` (**squash, disclosed**), #210 `02dbfa6`, #211 `84f7af9`, #212 `435db4e` |
| `queues` | `2026-10-01-unit-queues` | #213 `bbf4669` (inv), #214 `4b6a1eb`, #215 `69d49be`, #216 `a55fe41`, #217 `1420e2c` |
| `production` | `2026-10-01-unit-production` | #219 `58caf86` (inv), #220 `c442b3b`, #221 `eaa6f37`, #222 `65af7ee`, #223 `61f400a` |
| `collection` | `2026-10-01-unit-collection` | #224 `4cfc3fd` (inv), #225 `52e16b0`, #226 `22fdc2c`, #227 `20215fd`, #228 `c10de94` |
| `movement` | `2026-10-01-unit-movement` | #229 `5cd47a1` (inv), #231 `a958bef` (ledger reconcile), #232 `e5dc176`, #233 `da664a1`, #234 `ce29107`, #235 `018e030` |
| `animations` | `2026-10-02-unit-animations` | #237 `ff77e8f` (inv), #238 `3ccbf03` (cursor), #239 `e6f2f9c`, #240 `28e77df`, #241 `5bfdadd`, #242 `4915948` |
| `basic behaviors` | `2026-10-02-unit-behaviors` | #244 `2e98d55` (inv), #245 `8ca6778` (cursor), #246 `f5cdd30`, #247 `b473dc7`, #248 `db2c207` |

**Committed investigations, nine:** `docs/legacy-unit-instances.md`,
`docs/legacy-production-queues.md`, `docs/legacy-unit-production.md`,
`docs/legacy-unit-collection.md`, `docs/legacy-unit-movement.md`,
`docs/legacy-unit-animations.md`, and **`docs/legacy-unit-behaviors.md`** (PR #244, merged
`2e98d55`, and now carrying a corrections section), plus
**`docs/legacy-stored-unit-placement.md`** (PR #271, merged `6bb7a46`) — the first M9
investigation whose finding **contradicted the refusal pattern**, since 24 executed
probe transactions established that `place_stored_item` and `sell_stored_item` are
unguarded, type-agnostic, and charge nothing.

**Baselines in the final state (re-run by the orchestrator after line 8):** `verify.ps1` exit 0;
`verify-boot.ps1` exit 0 with **35 hermetic suites and 16 live phases** and the new `behavior-live`
phase proving a disposable corpus save mutated; compat **`Ran 1444 tests ... OK`** (up from 1352 by
**+92**); content validator `valid`, 21 schemas; hash manifest 3,258 entries; `openspec validate
--all --strict` **57/57** after the spec sync and **56/56** after the archive. Report digests, each
byte-identical across three runs: `f997eb2d...66d5`, `A02EEDC8...57BBA0`, `807477db...92090`,
`E56A470B...33CD6`, `81EFAD48...64C`, `785B0482...9165E`, `f06784cb...d8556`, and
**`0FE80C47...8F59`** (`unit-behaviors-report-v1`, 39,979 bytes).

**Committed M9 investigations, three:** **`docs/legacy-m9-progression.md`** (PR #250, merged `f74647c`,
the milestone-wide contract), extended by **PR #252** (merged `3d44159`, the research
measurements) and carrying a **corrections section** rather than quiet edits — `research` appears
in **two** normalized files (`buildings.json` **1**, `images.json` **6** from three popup rows),
not one; `config/main.json` **does** have **three** nested keys containing it, all in the `/images`
asset namespace, so "no key at any depth" was **false** though no top-level key contains it; and
the building's `legacy_id` is the **string** `"256"`, not an integer. The conclusion is unchanged
— every hit is an asset or display name, so there is still **no committed research cost, step
count, unlock requirement, or reward** — but the refusal now rests on a **correctly measured**
basis. And **`docs/legacy-m9-quests.md`** (PR #258, merged `0e886f2`), the line 2 contract. And
**`docs/legacy-m9-tutorial.md`** (PR #264, merged `2dbf715`), the line 3 contract — the **first M9 line
investigated on its own branch** rather than under the milestone-wide record, and recorded as
**40 executed-legacy probe transactions**. It found the entire tutorial system to be
`command.py:60-66`: one branch, one local, one write. `completed_tutorial` occurs **once**
across the eleven legacy root modules on **one** line, that line being
the **write**, with **zero readers** — the **tenth** committed field in this
project with no legacy consumer. `tutorial_step` occurs **4** times over **3** lines
and is a **local that is never persisted**, so there is **no stored step and no
un-complete path**. The gate `tutorial_step >= 25 or tutorial_step == 15` has **no
lower bound, no upper bound, and no type check**, and its hole is **exactly `16..24`**,
nine values wide. And `config/main.json` plus every normalized package hold **zero**
occurrences of `tutorial`: no step list, no count, no gate definition, no text.

**Baselines in the final state after M9 line 3 (re-run by the orchestrator):** `verify.ps1` exit 0;
`verify-boot.ps1` exit 0 with **38 hermetic suites and 19 live phases** (up from 37/18), the new
`tutorial-live` phase, and **264** log files inspected with **zero** `[test] FAIL`, `^ERROR:`,
or `SCRIPT ERROR` lines; compat **`Ran 1914 tests ... OK`** (1912 at the Apply merge, then **+2** from
the guard follow-up PR); content validator `valid`, 21 schemas; hash manifest
3,258 entries; `openspec validate --all --strict` **59/59** after the spec sync and **59/59**
after the archive. The line's own report digest is **`05f7b12d...c38b`**
(`tutorial-report-v1`, 10,634 bytes), byte-identical across three runs. The
prior M8 and M9 report digests remain as recorded above.

**Baselines in the final state after the `stored-item-placement` Apply (re-run by the
orchestrator):** `verify.ps1` exit 0; `verify-boot.ps1` exit 0 with **39 hermetic suites
and 20 live phases** (up from 38/19), the new `stored-placement-live` phase proving a
disposable corpus save mutated; compat **`Ran 2130 tests ... OK`** (up from 1914 by
**+216**, because the line adds two state-mutating routes, the envelope module, and three
test modules — the three new modules alone are **216** tests); content validator `valid`,
21 schemas; hash manifest 3,258 entries; `openspec validate --all --strict` **60/60** at
Apply, **61/61** after the Sync stage (the new capability was then both an active change
and a main spec), and **60/60** after the archive with `openspec list` reporting no
active changes. The line's own report digest is
**`c5bea9dd...8d18`** (`stored-placement-report-v1`, 13,618 bytes), byte-identical across
**four** runs. The prior M8 and M9 report digests remain as recorded above.

**The two anti-invention injections the orchestrator ran personally on this line**, both
restored byte-identically to `0b437e5d...0edbd`: `cell_is_free` into the delivered flow
module (**3** independent failures, exit 1) and `refund_for` (**1** failure). The second
is the line's finding: the by-name guard matched only the exact name `refund`, so a
helper wearing the same rule under a suffix slipped past it, and only the whole-inventory
pin caught it. A substring check was added — **2** failures for the same injection after
— and the finding is recorded in the suite rather than quietly fixed.

**Four cross-layer defects that the 544-check hermetic suite structurally could not
catch**, all four found only by `stored-placement-live`, which is the single strongest
argument in this milestone for keeping a live phase per state-mutating line: the
bootstrap payload is keyed `map` while the recorded fixture documents are keyed
`maps[0]`, so one storage assertion had been **passing for the wrong reason**;
`CollectionResult` has no `count_after`, so a bad field aborted the function before the
sale and both refusals ever ran; the service's and the client's copies of the recorded
geometry and quantity notes are deliberately **not** identical, so the suite had been
claiming "verbatim" — a claim **stronger than anything true** — and now asserts the
identifying **clauses**; and the sale's ledger append is **if-absent**, so a repeat
completion grants the prize again while the collection ledger **stands still**, the
opposite of what the first draft asserted and the fact that makes the sale reachable at
all.

**A sixth recorded flaky surface was found by this battery and FIXED rather than
re-run.** `verify-boot.ps1` failed `test_collection_endpoint.ContainmentTests` once on
`server_time` **1791066504** against **1791066505** with every other field identical,
while three immediate reruns passed. `/v0/session` stamps the current time on every
response, so a whole-document equality across two calls was **always** going to fail when
they straddled a second — the assertion was testing the clock, not the session list. The
first fix was then found wrong in the **other** direction by running that file alone,
because when both calls land inside one second the clock does *not* differ; so the
assertion is now that the differing-field set is a **subset** of the documented volatile
field, which is the only claim true in both cases and exactly as strict about every other
field as before. That guard was made to fail rather than trusted: injecting a real
session-list change produced `AssertionError: {'saves'} not less than or equal to
{'server_time'}`, and restoring the byte-identical file (`8efd62d8...7ab6`) returned it to
36 tests and `OK`. **This is the first recorded flaky surface in the project that was
closed rather than re-run**, and the reasoning generalises: a flaky guard is not a passing
guard.

**One cross-suite boundary had to be amended rather than deleted.** `test_unit_collection.gd`'s
`_check_boundary()` asserted that `place_stored_item` was absent from **every** client
source; that claim became **false** the moment this line landed, and it was measured
failing with **4** failures before being touched. The whole-tree absence was replaced by
an **ownership claim**, and — because two suites scanning one tree for one token with two
hand-maintained owner lists is drift waiting to happen — the owner list lives **only** in
this line's suite while the collection suite asserts that the hand-off's **recipient
exists and asserts it**. Its check count went **1,988 → 1,894** because the removed
tree-wide scan was 4 needles × ~93 sources.

**Archive-stage corrections, recorded rather than quietly fixed.** Three figures in this
change's own artifacts did not survive contact with measurement, and one of them was in
this ledger:

1. **The task list has 20 boxes, not 18.** This ledger, the client README, and the
   change's own proposal said "18 unticked tasks", written from memory at Propose and
   **never counted**. Measured: **20** — 1.1–1.4, 2.1–2.5, 3.1–3.4, 4.1–4.3, 5.1–5.4.
   Nothing about the delivered behaviour changes, but a ledger that miscounts its own
   tasks is not a ledger, so the correction is recorded here, in the archived
   `tasks.md`'s integration review, and in the README.
2. **Task 1.1's "exactly two leaves" was wrong, and the cause is in the fixture manifest.**
   Measured: **three** at whole-document scope (`maps[0].items.41`, `maps[0].store.1085`,
   `privateState.boughtUnits`) and **two** at map scope. The cause is not a defect — the
   committed investigation had seeded with `store_add_items`, which calls
   `bought_unit_add` in the **same** batch (`command.py:264`), so its ledger already held
   the id and the placement's own append-if-absent left it alone. Seeding instead with the
   content-derived `complete_collection` — which appends to `privateState["collections"]`
   and **never** to `boughtUnits` — makes that third write observable.
   `test_the_manifest_records_the_three_leaf_correction` pins the correction so it cannot
   be silently reverted to the predicted number.
3. **The capture is five chained steps, not four.** The sale needs a *second* seed,
   because the sale consumed the only stored unit and the ledger append is **if-absent** —
   so `login_post` → `complete_collection(1)` → `place_stored_item` →
   `complete_collection(1)` → `sell_stored_item`. Found by the live phase, after the
   offline suite was green.

**The Archive stage was run with `--skip-specs`, deliberately.** The Sync stage had
already applied and merged both deltas, so letting `archive` re-apply them would have
duplicated a whole requirement block. Both stages also repeat the same discipline in
opposite directions: Sync copies the delta's block **verbatim** into the main spec rather
than hand-editing it, and the earlier delta was generated **programmatically** from the
main spec rather than retyped — because a MODIFIED requirement replaces the **whole**
block, and a partial edit is exactly how a scenario silently disappears.

**The three injections the orchestrator ran personally on line 3**, each restored
byte-identically: `tutorial_total_steps` into the flow module (**3** independent failures,
exit 1, restored `9ea3ff1b...0d6`);
relocating `/v0/tutorial` after another route (**3** failures, exit 1, file still
compiling — because every delivered guard slices `def vN_x():` up to the next
`@app.<method>(...)` decorator, so a route inserted between two others lands inside
the *preceding* route's slice); and honouring a client-sent `completed_tutorial` in
the route (**1** failure across 1912 tests, then **2** once the sweep existed,
restored `D75BF31C...D6D0`).

**That third injection is the line's second substantive finding**, and it is the
sharpest instance yet of a discipline this repository keeps learning: the
delivered intent-only guard was **thinner than the claim it supported**. Three
narrow tests each sent one field name, and honouring a client-sent
`completed_tutorial` broke exactly **one** of them, because the other two sent
unrelated names and no envelope-side test could catch it at all — the envelope
never emits such a field. The requirement held, but it held by accident rather than
by proof. PR #268 closes the class with a sweep over **twenty** field names across
**both** a completing and a declining step, comparing the **whole response** minus a
named volatile-key list plus the persisted flag and every stored resource, with a
companion test asserting `server_time` is the **only** key that varies so the helper
cannot silently grow.

**A fifth recorded flaky surface** came from this line: the live phase's marker line
bound `%` to the last string of a concatenation and so produced a **parse error**
rather than a wrong count, which is exactly why `verify-boot/*.err.txt` is read
rather than the exit code trusted.

**Baselines in the final state after M9 line 2 (re-run by the orchestrator):** `verify.ps1` exit 0;
`verify-boot.ps1` exit 0 with **37 hermetic suites and 18 live phases** and **484** log files
inspected with **zero** `[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines; compat **`Ran 1751
tests ... OK`** (up from 1572 by **+179**); content validator `valid`, 21 schemas; hash manifest
3,258 entries; `openspec validate --all --strict` **59/59** after the spec sync and **58/58** after
the archive. The line's own report digest is **`412dd271...6019`** (`quests-report-v1`, 37,102
bytes), byte-identical across three runs. The prior M8 report digests remain as recorded above.

**The ASSESSMENT is COMPLETE, and it was a verdict rather than a line.**
`docs/legacy-m9-assessment.md` (PR #270, merged `7ab93c7`) assessed `XP`, `levels`, and
`collections` — the three M9 deliver items delivered by an earlier milestone and
deliberately narrowed there — against the question of whether M9's exit criterion
requires the omissions.

**M9's exit criterion — "Primary long-term progression systems work" — is NOT MET.**
The reason is uniform across all five M9 items: **the committed legacy server has no
progression _consumer_.** Every delivered M9 surface projects, records, or narrates,
and nothing in the legacy source reads any of it back to change what a player may do.
That is a finding about the oracle, not a defect in the modern client.

**Four measurements the assessment made that change the record:**

1. **The level curve's index base is now ESTABLISHED, not derived-provisional.**
   `building-xp` rested its one-based reading on **one** corpus data point. The eight
   committed **village** saves give **eight**, and the test is direct — one-based is
   **TIGHT on 7 of 8**, zero-based on **0 of 8**. `Scarlet.json` is the one genuine
   disagreement (recorded level 33 at `xp 107,694`, exactly one below the curve's tight
   level of 34), which is committed evidence that a stored level really can diverge —
   and confirmation that reporting rather than reconciling is right.
2. **Unit XP is not unreachable.** The recorded claim *"no unit XP; the corpus cannot
   exercise it"* is true of `tests/saves/fresh-player.json` (0 of 40 rows) and **false of
   the committed evidence**: `attr["xp"]` appears on **171 rows across 5 of 8** village
   saves, values 10 → 611,650.
3. **Committed level rewards exist and are not uniform** — **5** distinct
   `reward_type`/`reward_amount` pairs, not one — and a **second** unread table,
   `level_ranking_reward`, exists with **50** entries covering **1..50** with no gaps or
   duplicates, a `cash` field **uniformly 1**, and **exactly one** positional inversion
   (level 24 sits after level 19), so a positional consumer would be wrong for level 24
   and a field-keyed one would not.
4. **Both curve accessors are dead.** `get_xp_from_level` has **0** call sites and
   `get_level_from_xp` **0** callers; `exp_required` and `levels` each have **2**
   occurrences, both inside those two accessors. The auction level gate is dead too —
   `get_auctions(user_id, level)`'s only call site is commented out.

**All three assessed items have a real, bounded, evidence-backed gap**, and the
assessment proposed them as **separate** bounded lines while **authorising none of them**.
The deliver list is `XP`, `levels`, `quests`, `research`, `collections`, and
`tutorial/progression`, and the exit criterion is "Primary long-term progression systems
work."

- **`XP`** — the accumulation branch `add_xp_unit` (`command.py:322-343`) is undelivered.
  Its optional third argument is assigned to a local `level` and used **only in a print**.
- **`levels`** — a reward exists in committed content but its letters have **no**
  committed resource mapping, so paying one would invent both a schedule and a
  vocabulary. **Stays refused.**
- **`collections`** — the granted prize is never placed. **In flight** as
  `2026-10-03-stored-item-placement`.

**Two defects in the assessment's own probes were recorded rather than quietly fixed**,
and both are the reason one of its numbers changed: the first counter stripped **string
literals** — where every save field name lives — and reported `privateState` and
`collections` as **0** occurrences against the corrected **138/113** and **10/8**, which
would have supported a confident false claim about `command.py:517-518`; and the first
index-base probe printed its `one-b` and `zero-b` columns from the **same function**, so
the second column was meaningless and would have supported a confident claim about an
untested reading. Both were discarded and re-measured. Separately, a number the
assessment record initially carried for the defective probe — "93 occurrences" — could
not be reproduced, so it was replaced with the measured **0** rather than left as a
recollection.

**Current objective: none in flight, and M9 is CLOSED.** `stored-item-placement` and `unit-experience-evidence` are both archived, closing **both** authorised gaps the M9 assessment named. With them closed, **no evidence-supported M9 implementation gap remained**, so the milestone was closed by **`docs/legacy-m9-closure.md`** rather than left open: M9 is **implementation-complete to the extent the committed legacy oracle supports**, its exit criterion is **NOT MET**, and the cause is a **legacy-reference capability gap** — the preserved implementation being migrated contains **no progression consumer**. **`add_xp_unit` is no longer an unproposed candidate:** it was delivered and archived as `2026-10-04-unit-experience-evidence` (investigation PR #276 `79d13ac`, Apply PR #278 `d0d70a3`, Sync PR #279 `131a133`, fix PR #280 `dae7705`, Archive PR #281 `8d370a1`). The cursor has moved to **M10 — Missions and Combat**, first objective **mission loading / mission state**, which **requires its own committed investigation before any proposal**.

**Carried follow-ups, nearest first:**

1. **The stored-item round trip — DELIVERED and ARCHIVED** as
   `2026-10-03-stored-item-placement` (investigation `docs/legacy-stored-unit-placement.md`,
   PR #271 `6bb7a46`, proposal validating **60/60**), retained here as the resolved record
   rather than an open follow-up. It was the nearest undelivered step on a fully
   content-derived path, the collection line deliberately stopped there, and it closed the last
   place where **no acquired unit was ever placed on the map**. The committed investigation
   resolved the open questions with **24 executed-legacy probe transactions** in two contained
   runs, both reporting a byte-identical working-tree
   containment digest and a free port: the branch is **type-agnostic**, **no price exists**,
   the row is **server-derived in five of eight slots**, and **four behaviours the legacy server
   does not guard** were each confirmed by execution. It **corrects** the assessment's framing:
   **four of the ten collection prizes are buildings**, so the scope is written against the
   **prize** rather than the word "unit".
2. **`verify-boot.ps1`'s `^ERROR:` guard** is broad enough to fail on a benign engine shutdown
   RID-leak warning, on a single `0xC06D007F` Windows module-load crash of an untouched phase
   that had already passed nine times in the same run, and on a transient `0xC06D007F` of the
   same kind during the quests line; narrow it to `SCRIPT ERROR` or a fatal-error allowlist.
3. **Latent `%r` format bugs** in `game_api.gd:176`, `boot_data.gd:1282,1312`, and
   `fake_api.gd:2216,2237,2909,2910,2914` — Godot 4.7.2's `%` does **not** support `%r`, so
   each of those lines will raise if its branch is ever reached.
4. The friend-assist cluster, construction speedups, the upgrade row's seeded `{"nc": 0}`, the
   premium upgrade path, the legacy level gate and daily-upgrade limit, cap semantics for a
   non-zero `max_collects`, **the expansion tile-to-cell geometry** (new evidence, not a
   derivation), and the internal `TownState.Resources.coins` alias.
5. **No bound on the on-demand `goals` list and no membership test on `set_quest_var`** — both
   are Server v1 / M13 gaps the quests line deliberately left unfilled because the legacy branches
   have neither.
6. **Pin line endings for committed evidence.** Two separate defects in this project were
   byte-sensitive guards that pass on an LF checkout and fail on a CRLF one, and both were
   **fixed rather than re-run**: `test_collection_endpoint.py`'s whole-document comparison
   against a second `/v0/session` call, and the `stat().st_size` comparison in
   `test_unit_xp_fixture.py`. A measurement established that every prior fixture verifies by
   **sha256**, which is line-ending invariant, so those two were the only instances. The
   durable fix is `/tests/fixtures/** text eol=lf` (and the same for the
   `apps/client-godot/evidence/**` report JSONs) in `.gitattributes`, so committed evidence has
   exactly **one** byte form and this class of defect cannot recur. Relatedly, have the
   `test_project_scope.gd` source walk skip `__pycache__`.

**Discipline carried forward, with seven data points:** *measure every figure before asserting
it* — **eighteen of my own investigation figures** were asserted rather than measured or miscounted
across the eleven lines, and on this milestone's last line **five more were found and corrected**,
every one by someone else measuring it; *verify a worker's claim and reject it when wrong* — the
implementation worker on that line corrected my brief on **seven** points and was right on all
seven, which is the counter-example that keeps the habit honest in both directions; *prefer a public
accessor* over a private-state reach; *prefer a boundary assertion over a repository-wide absence*;
*inspect battery logs rather than exit codes*, which is what identified the two engine flakes as
flakes; and *test a guard rather than trusting it*. **Two process errors are disclosed above** — a
squash merge (#209) and one direct push to `main` (`41fc708`) — both from chaining git operations
into a block whose prerequisite step was not written out. Branch, commit, and push are now run as
separate verified steps. **A third, disclosed here:** my own `write_delta` helper wrote each delta
file *before* asserting its shape, so an early failing run left a corrupted `godot-building-sell`
delta in the tree; it was caught by reading the file rather than trusting the exit code, and
regenerated from the main spec. The helper was a temporary script, but the lesson is the standing
one — **assert before writing, and read the artifact, not the code.** The quests line added the
sharpest instance of it, so the lesson is now also enforced in the sync routine: **assert a delta's
shape before writing any of it**, and assert the target requirement counts **before and after**,
never after only.

**A fourth discipline point, earned on the quests line:** *know what a suite structurally cannot
detect.* 1223 hermetic checks passed while the live phase failed five separate times, because the
offline suite builds its own response envelope and therefore cannot see envelope or wire drift at
all. The suite now asserts that it builds no request body and records why, so the next line does
not have to rediscover the blind spot — **and the guard for that class is a live phase, which is a
single phase, so it is one failure away from being the only thing standing between the client and
the wire.**

**Known-flaky guard, five surfaces now:** `verify-boot.ps1` can fail on a `^ERROR:` line that is only an engine
shutdown RID-leak warning or a transient Windows module-load crash; re-run and inspect
`.godot/verify-boot/*.txt` before treating it as a regression. `verify.ps1` is also
display-sensitive through its windowed-capture step and returned **-1** on one of two runs and **0**
with `PASS all checks succeeded` on the second; re-run it too.

### Process disclosure (recorded 2026-10-01, orchestrator)

**PR #209, the `unit-instances` proposal, was squash-merged as `0710038` instead of with a
merge commit**, against the rule that OpenSpec and development PRs use merge commits only.
The cause was the orchestrator chaining a stray `gh pr merge --squash` into a command block it
intended to suppress.

**Impact, measured rather than assumed:** `0710038` has a single parent, so the merge commit
recording the PR is absent; its **tree is byte-identical** to the branch commit `dacda10`
(`918d3c`), the branch carried exactly **one** commit so no individual commit was destroyed,
and the branch was still on origin when measured. **No code, spec, or documentation was
lost.** What was lost is the branch topology in the history.

**Disposition:** the user chose to **record the deviation and continue** rather than rewrite
published `main` history, which would have required a force-push the project rules forbid
without explicit authorization. The squash stands on the permanent record, this disclosure
accompanies it, and **every subsequent PR used a merge commit** — #210 (`02dbfa6`) and #211
(`84f7af9`) are both proper merge commits.


### Process disclosure (second entry, recorded 2026-10-01, orchestrator)

**One commit was pushed directly to `main`, bypassing the branch-and-PR workflow.**
It was `docs: refresh the roadmap resume point for M8 line 5` (`41fc708`), a
documentation-only resume-point refresh, and it was the result of chaining a
`git push origin main` into the same command block that had just committed it — the branch
step was omitted by oversight rather than chosen.

**Impact:** the content is correct and was verified before pushing, and no code, spec, fixture,
or legacy byte was involved. But it is a **workflow violation** — every repository-mutating
stage is supposed to reach `main` through a remote branch and a merge-commit PR, so this one
commit has no PR and no merge commit.

**Disposition:** recorded here rather than papered over, and no force-push or history rewrite
was attempted. Every subsequent stage follows the workflow. This is the **second** process
error of this kind in this run — the first was the squash-merge recorded above — and both
were the same root cause: chaining a git operation into a command block where the
prerequisite step was not written out. The discipline that follows is to run branch, commit,
and push as **separate, explicitly verified** steps rather than one chained block.
## Stage A — Preserve the Current Implementation

```text
Flash Client
    │
    │ SWLoader.swf
    │ Basesec_*.swf
    │ FlashVars
    │ Legacy HTTP / form requests / AMF-era behavior
    ▼
Legacy Flask Server
    │
    ├── server.py
    ├── command.py
    ├── sessions.py
    ├── engine.py
    ├── get_player_info.py
    └── get_game_config.py
    │
    ▼
JSON Save Files
```

This implementation remains operational as the **behavioral oracle**.

Do not dismantle it during the first stages of development.

---

## Stage B — Flash-Free Compatibility Architecture

The first major target architecture should be:

```text
Godot Client
    │
    │ Modern JSON API
    ▼
Compatibility API v0
    │
    │ translates modern requests
    │ into legacy semantics
    ▼
Legacy Game Logic
    │
    ▼
JSON Save Files
```

At this stage:

- Flash Player is no longer required.
- The Godot client does not execute SWFs.
- The user can play through the modern client.
- Existing game behavior is preserved.
- Existing saves can still be loaded.
- Existing Python logic remains the behavioral reference.
- PostgreSQL is not yet required.
- Public account infrastructure is not yet required.

This should be achieved **before rewriting the backend**.

---

## Stage C — Production Architecture

The eventual production architecture becomes:

```text
Godot Client
    │
    │ HTTPS / JSON
    │ WebSocket only where justified
    ▼
Server API v1
    │
    ├── Authentication
    ├── Town Domain
    ├── Economy Domain
    ├── Buildings Domain
    ├── Units Domain
    ├── Inventory Domain
    ├── Research Domain
    ├── Quest Domain
    ├── Collections Domain
    ├── Missions Domain
    ├── Combat Domain
    └── Social Domain
    │
    ▼
PostgreSQL
    │
    ├── durable player state
    ├── transaction ledger
    ├── progression
    ├── missions
    ├── social state
    └── migration metadata
```

Optional infrastructure can later include:

```text
Redis
WebSockets
Admin tooling
Metrics
Job processing
CDN
```

These should only be introduced when they solve a demonstrated problem.

---

# 2. Non-Negotiable Engineering Principles

These rules should guide the entire reconstruction.

## 2.1 Preserve Before Replacing

Never remove or rewrite legacy behavior until its behavior has been:

1. observed,
2. documented,
3. recorded,
4. tested,
5. reproduced by the replacement.

---

## 2.2 Do Not Delete Original Data

Never destroy:

- SWFs
- JSON configuration
- existing saves
- images
- sounds
- XML files
- game configuration
- protocol examples
- legacy server code

Move them later into archival directories if necessary, but preserve their original versions.

---

## 2.3 Preserve Git History

When reorganizing files, use:

```bash
git mv
```

rather than deleting and recreating files whenever practical.

---

## 2.4 Do Not Redesign Gameplay During Parity Work

The reconstruction phase is not the time to rebalance the game.

Avoid changing:

- resource costs,
- XP rewards,
- building times,
- combat formulas,
- quest requirements,
- unit stats,
- progression pacing,
- unlock requirements.

First reproduce the existing game.

Improvements can happen later.

---

## 2.5 Never Rewrite Client and Server Semantics Simultaneously

A dangerous migration would be:

```text
Flash → Godot
Flask → completely different server
JSON saves → PostgreSQL
Legacy protocol → new protocol
```

all at once.

That would make behavioral regressions extremely difficult to diagnose.

Instead:

```text
Preserve server
    ↓
Replace client
    ↓
Verify parity
    ↓
Replace server internals
    ↓
Verify parity again
```

---

## 2.6 Every Migrated Feature Needs a Legacy Fixture

Before replacing a feature, capture examples of:

```text
request
before state
response
after state
```

These become golden-master tests.

---

## 2.7 Preserve Legacy IDs

Existing IDs used by:

- buildings,
- units,
- items,
- quests,
- research,
- collections,
- missions,
- effects,
- animations,
- assets

should remain stable.

The production database may use internal primary keys, but original IDs should be stored as:

```text
legacy_id
```

where appropriate.

---

## 2.8 Production Server Owns the Truth

The future server must be authoritative.

The client sends **intent**, not final state.

Bad:

```json
{
  "coins": 999999,
  "xp": 10000
}
```

Good:

```json
{
  "building_id": "barracks_01",
  "x": 24,
  "y": 17
}
```

The server determines:

```text
Is the building unlocked?
Does the player have enough resources?
Is placement valid?
What does it cost?
How much XP is awarded?
When does construction finish?
What state should be written?
```

---

## 2.9 SWF Files Become Archival References

The final runtime must not rely on:

- Adobe Flash Player
- Ruffle
- ActionScript runtime
- SWLoader.swf
- Basesec SWFs
- sprite SWFs
- FX SWFs
- AMF
- FlashVars

SWFs may remain inside:

```text
legacy/
```

for preservation and reference.

They must not be required by the final game runtime.

---

# 3. Legacy Component Classification

The existing repository should be classified before significant restructuring.

| Component | Strategy | Purpose |
|---|---|---|
| `server.py` | KEEP + FREEZE | Legacy HTTP behavior oracle |
| `sessions.py` | KEEP → REWRITE LATER | Save/session semantics |
| `command.py` | KEEP + DECOMPOSE | Primary game behavior specification |
| `engine.py` | AUDIT + EXTRACT | Reusable calculations where possible |
| `get_game_config.py` | KEEP + NORMALIZE | Content/configuration source |
| `get_player_info.py` | KEEP → REPLACE | Player bootstrap behavior |
| AMF/form protocol | LEGACY ONLY | Compatibility/reference |
| `templates/play.html` | ARCHIVE | Flash bootstrap |
| `SWLoader.swf` | ARCHIVE | Flash loader |
| `Basesec_*.swf` | ARCHIVE | Legacy client implementation |
| PNG/JPG assets | KEEP | Direct reusable content where legally permitted |
| MP3/audio assets | KEEP/CONVERT | Runtime audio source |
| SWF sprites | CONVERT | Godot-compatible assets |
| SWF effects | CONVERT/RECREATE | Godot effects |
| JSON game config | KEEP + VALIDATE | Canonical content source |
| JSON saves | KEEP + MIGRATE | Golden fixtures and migration source |

---

# 4. Target Repository Structure

Do not immediately restructure everything.

During early development the repository can gradually move toward:

```text
social-wars-legacy/
├── apps/
│   ├── client-godot/
│   ├── compat-v0/
│   └── server-v1/
│
├── packages/
│   └── game-content/
│       ├── raw/
│       ├── normalized/
│       ├── schemas/
│       └── generated/
│
├── tools/
│   ├── protocol-recorder/
│   ├── protocol-replay/
│   ├── state-diff/
│   ├── asset-pipeline/
│   ├── content-builder/
│   └── save-migrator/
│
├── tests/
│   ├── fixtures/
│   ├── golden/
│   ├── saves/
│   ├── integration/
│   ├── migration/
│   └── visual/
│
├── docs/
│   ├── architecture/
│   ├── legacy-protocol/
│   ├── game-systems/
│   ├── assets/
│   ├── migrations/
│   └── adr/
│
├── legacy/
│   ├── server/
│   ├── flash/
│   ├── assets/
│   └── saves/
│
└── README.md
```

Initially keep the existing structure intact.

Move legacy components only after the migration tooling and modern directories are established.

---

# 5. Phase 0 — Freeze and Preserve the Legacy Baseline

## Objective

Create a reproducible snapshot of the working legacy implementation before modifying architecture.

---

## Tasks

Create a Git tag:

```bash
git tag legacy-baseline
```

Document:

- Python version
- dependency versions
- operating system requirements
- startup procedure
- default ports
- required environment configuration
- directory expectations
- Flash client startup flow
- default player/save
- known bugs
- known broken features
- known incomplete features
- asset versions
- EXT_VERSION or equivalent content version
- expected URLs
- expected game bootstrap process

---

## Create Asset Hash Manifest

Generate SHA-256 hashes for:

```text
*.swf
*.json
*.xml
*.png
*.jpg
*.jpeg
*.mp3
*.wav
*.gif
```

Example:

```json
{
  "path": "assets/flash/SWLoader.swf",
  "sha256": "...",
  "size": 123456
}
```

This provides a permanent record of the original artifact set.

---

## Create Canonical Save Fixtures

Preserve multiple representative saves.

Recommended fixtures:

```text
tests/saves/fresh-player.json
tests/saves/early-game.json
tests/saves/mid-game.json
tests/saves/late-game.json
tests/saves/stress-town.json
```

Try to include:

### Fresh Player

- tutorial state
- starter buildings
- starter units
- starter currencies

### Early Game

- construction
- basic unit queues
- first quests

### Mid Game

- research
- collections
- larger inventory
- multiple zones

### Late Game

- advanced unlocks
- missions
- high-level buildings
- advanced units

### Stress Town

- dense town
- many buildings
- many units
- many queued operations
- large inventory

---

## Deliverables

```text
docs/legacy-baseline.md
docs/known-legacy-bugs.md
tests/saves/
tools/hash-manifest/
legacy-manifest.json
```

---

## Exit Criteria

The legacy game can be reproduced from a clean environment using documented instructions.

---

# 6. Phase 1 — Build the Legacy Protocol Recorder

This is one of the most important phases of the entire project.

## Objective

Turn the legacy implementation into an observable behavioral specification.

---

## Capture

For every request:

```text
timestamp
endpoint
HTTP method
request body
parsed command
player ID
session ID where appropriate
state before
response
state after
HTTP status
execution duration
```

---

## Important Rule

Instrumentation must not change behavior.

The recorder should observe the legacy system, not rewrite it.

---

## Golden Fixture Structure

Example:

```text
tests/golden/building-buy/
├── request.json
├── before.json
├── response.json
└── after.json
```

Other fixture examples:

```text
tests/golden/building-move/
tests/golden/unit-order/
tests/golden/collect-income/
tests/golden/start-research/
tests/golden/claim-quest/
tests/golden/mission-attack/
```

---

# 7. Build an Exhaustive Legacy Command Catalog

`command.py` is effectively a major portion of the existing game specification.

Create:

```text
docs/legacy-protocol/commands.md
```

or preferably a machine-readable catalog plus generated documentation.

Each command should include:

```text
Command name
Domain
Endpoint
Required parameters
Optional parameters
State read
State modified
Resources consumed
Rewards produced
Timers created
Dependencies
Client-trusted fields
Security concerns
Observed fixtures
Replacement API
Migration status
```

---

## Suggested Status Values

```text
UNOBSERVED
CAPTURED
DOCUMENTED
V0_SUPPORTED
V1_SUPPORTED
PARITY_VERIFIED
RETIRED
OUT_OF_SCOPE
```

---

## Example

```yaml
command: buy
domain: buildings
status: CAPTURED

inputs:
  - building_id
  - x
  - y

reads:
  - player.resources
  - player.level
  - town.objects
  - town.zones

writes:
  - player.resources
  - town.objects
  - player.xp

security:
  legacy_client_trust: high

replacement:
  endpoint: POST /v1/towns/me/buildings
```

---

# 8. Phase 2 — Define the Canonical Domain Model

Before building extensive modern code, define the conceptual game model.

Core domain objects should include:

```text
Player
Town
Map
Zone
TownObject
Building
Decoration
Unit
UnitInstance
Resource
InventoryItem
InventoryStack
ProductionQueue
Research
Quest
QuestObjective
Collection
Mission
Battle
Friend
Visit
Reward
Event
ContentDefinition
```

---

# 9. Separate Definitions From Player State

This distinction is extremely important.

## Definition Data

Shared static game content:

```text
Barracks
cost = 500 coins
build_time = 60
footprint = 3x3
required_level = 5
```

---

## Player Instance State

Player-owned object:

```text
instance_id = 8937
definition_id = barracks
x = 24
y = 17
level = 2
construction_ready_at = ...
```

Never merge these concepts.

Use patterns similar to:

```text
BuildingDefinition
BuildingInstance

UnitDefinition
UnitInstance

QuestDefinition
QuestProgress
```

---

# 10. Phase 3 — Build Canonical Game Content

Create a normalized content package.

```text
packages/game-content/
├── raw/
├── normalized/
│   ├── buildings.json
│   ├── units.json
│   ├── items.json
│   ├── quests.json
│   ├── research.json
│   ├── collections.json
│   └── missions.json
├── schemas/
│   ├── building.schema.json
│   ├── unit.schema.json
│   ├── quest.schema.json
│   └── ...
├── generated/
└── manifest.json
```

---

## Requirements

Every content definition should preserve:

```text
legacy_id
source
content version
asset references
dependencies
```

---

## Validate Content

The content builder should detect:

```text
duplicate IDs
unknown references
missing assets
invalid costs
invalid requirements
broken quest dependencies
broken research dependencies
missing unit references
missing building references
missing reward references
```

---

# 11. Phase 4 — Build the SWF Asset Migration Pipeline

Do not manually convert assets without tracking them.

Create a central asset registry.

---

## Asset Registry Fields

Each asset should track:

```text
source SWF
source hash
symbol/class name
legacy asset ID
category
dimensions
registration point
pivot
frame count
frame rate
frame labels
nested MovieClips
masks
blend modes
color transforms
filters
scale grids
ActionScript dependencies
output path
Godot resource
conversion status
notes
```

---

## Example

```yaml
legacy_id: building_barracks_01

source:
  file: assets/sprites/buildings.swf
  symbol: Barracks01

type: building

dimensions:
  width: 270
  height: 220

registration:
  x: 135
  y: 198

animation:
  frames: 12
  fps: 24

conversion:
  status: converted
  output: assets/runtime/buildings/barracks_01/
```

---

# 12. Preserve Important Flash Rendering Semantics

Asset conversion can easily become visually incorrect if these are ignored:

- registration points
- pivots
- nested MovieClips
- masks
- alpha
- color transforms
- blend modes
- shadows
- glow filters
- scale grids
- tween timing
- frame labels
- transform inheritance
- morph animations
- ActionScript-controlled states

These should be documented per asset where relevant.

---

# 13. Asset Conversion Mapping

Recommended mappings:

| Legacy Asset | Modern Replacement |
|---|---|
| Static bitmap | PNG / WebP |
| Vector icon | SVG or rasterized texture |
| Simple MovieClip | SpriteFrames |
| Complex animation | AnimationPlayer |
| Unit animation | AnimatedSprite2D / AnimationPlayer |
| UI panel | TextureRect / NinePatchRect |
| Flash scale-grid UI | NinePatchRect |
| MovieClip hierarchy | Godot scene |
| Flash particle effect | GPUParticles2D |
| Complex FX | Godot shader / scene animation |
| MP3 | OGG/WAV |
| Flash button | Godot Control/Button scene |

---

## Asset Directory Separation

Never overwrite original assets.

Use:

```text
assets/raw/
assets/converted/
assets/runtime/
```

or equivalent.

---

# 14. Asset Conversion Priorities

Do not attempt to convert every asset before the game runs.

Suggested order:

```text
1. Terrain
2. One building
3. One unit
4. Essential HUD
5. Selection indicators
6. Placement grid
7. Common buildings
8. Common units
9. Common UI
10. Combat effects
11. Missions
12. Rare content
13. Special events
```

---

# 15. Phase 5 — Initialize the Godot Client

Use a pinned stable Godot 4.x version.

Document it in:

```text
apps/client-godot/README.md
```

---

## Recommended Language

Use **GDScript initially** unless there is a strong reason to use C#.

Reasons:

- quickest Godot iteration
- excellent engine integration
- simpler deployment
- appropriate for UI-heavy and scene-heavy work
- easier contributor setup

C# can still be introduced later for specific systems if justified.

---

# 16. Suggested Godot Structure

```text
apps/client-godot/
├── project.godot
│
├── scenes/
│   ├── boot/
│   ├── town/
│   ├── buildings/
│   ├── units/
│   ├── missions/
│   └── ui/
│
├── scripts/
│   ├── core/
│   ├── networking/
│   ├── domain/
│   └── utils/
│
├── assets/
│
└── tests/
```

---

# 17. Godot Autoloads

Keep global singletons limited.

Potential autoloads:

```text
App
GameApi
Session
ContentRegistry
GameClock
Settings
AudioManager
```

Avoid creating a giant global `GameManager` containing every system.

---

# 18. Critical GameApi Abstraction

The Godot UI should never directly know about:

```text
command.php
AMF
FlashVars
form encoding
legacy URLs
legacy command names
```

Create an abstraction such as:

```gdscript
class_name GameApi
```

with operations similar to:

```text
get_bootstrap()
get_player()
get_town()

buy_building()
move_building()
sell_building()
upgrade_building()
collect_building()

order_unit()
cancel_unit_order()
collect_unit()

start_research()
cancel_research()
claim_research()

start_quest()
claim_quest()

start_mission()
attack_target()
```

---

## Initial Implementation

```text
LegacyV0Api
```

Later:

```text
ServerV1Api
```

The rest of Godot should not care which implementation is active.

---

# 19. Phase 5.5 — Compatibility API v0

Create a modern-facing API in front of the legacy server.

For example:

```http
POST /v0/buildings/buy
```

Request:

```json
{
  "building_id": "barracks",
  "x": 24,
  "y": 17
}
```

Internally:

```text
Compatibility API
    ↓
translate request
    ↓
legacy command semantics
    ↓
legacy response
    ↓
normalize
    ↓
Godot response
```

---

## Benefits

Godot never needs to implement:

```text
legacy form encoding
command.php specifics
Flash-oriented request structures
AMF
FlashVars
```

When Server v1 arrives, only the API implementation changes.

---

# 20. Phase 6 — First Flash-Free Vertical Slice

This is the first major development target.

Do not wait for full game parity.

---

## Required Flow

```text
Launch Godot
    ↓
Connect to compatibility server
    ↓
Load game configuration
    ↓
Load player
    ↓
Load town
    ↓
Render terrain
    ↓
Render buildings
    ↓
Render at least one unit
    ↓
Display HUD resources
    ↓
Allow camera movement
    ↓
Allow object selection
```

---

## Vertical Slice Requirements

### Bootstrap

Implement:

```text
configuration loading
player loading
town loading
content registry
session initialization
```

---

### Town Renderer

Implement:

```text
isometric grid
grid-to-screen conversion
screen-to-grid conversion
camera movement
zoom
town bounds
depth sorting
object footprint handling
selection
HUD
```

---

### First Building

Convert one real building.

Support:

```text
load
render
select
move
```

---

### First Unit

Convert one real unit.

Support:

```text
load
render
idle animation
select
```

---

# 21. First Major Gate

The following must work on a machine with:

```text
NO Adobe Flash
NO Ruffle
NO Flash plugin
NO ActionScript runtime
```

Godot should:

```text
launch
load an existing save
load game content
render town terrain
render buildings
render units
render HUD
pan camera
zoom camera
select objects
```

Once this works, the reconstruction has passed its first critical milestone.

---

# 22. Phase 7 — Building System Parity

Implement building functionality in dependency order.

```text
1. Load existing town objects
2. Select objects
3. Placement preview
4. Grid validation
5. Buy building
6. Construction
7. Move
8. Flip / rotate where applicable
9. Store
10. Restore
11. Upgrade
12. Sell
13. Remove
14. Unlock zones
15. Clear obstacles
16. Collect resources
```

---

# 23. Placement System Requirements

The town grid must properly understand:

```text
multi-tile footprints
town bounds
locked zones
occupied tiles
collision rules
placement previews
object pivots
base tile positions
selection hitboxes
orientation
depth sorting
```

Do not use texture dimensions as gameplay footprint dimensions.

A large image may occupy only a small number of logical tiles.

---

# 24. Isometric Coordinate Tests

Create automated tests for:

```text
grid → screen
screen → grid
negative coordinates
boundary coordinates
large coordinates
multi-tile footprints
camera transformations
zoom transformations
```

This logic will affect almost every town interaction.

---

# 25. Phase 8 — Economy and Timer Systems

Reconstruct:

```text
coins
resources
premium currency
XP
building income
production
construction
cooldowns
collections
rewards
```

---

# 26. Server-Based Timer Model

Never trust the client clock.

Server responses should include:

```json
{
  "server_time": 1789257600,
  "ready_at": 1789257900
}
```

The client computes a server offset.

---

## Persist Timers As State

Prefer:

```text
started_at
duration
ready_at
```

over creating one background worker for every timer.

---

# 27. Economy Invariants

Create tests such as:

```text
resource balances never become invalid
premium currency cannot be duplicated
purchases cannot execute without sufficient resources
rewards cannot be claimed twice
collect cannot execute before timer completion
client clocks cannot skip timers
```

---

# 28. Economy Ledger

For the production server, important currency mutations should create ledger entries.

Example fields:

```text
player_id
resource
amount
reason
related_entity
balance_before
balance_after
timestamp
request_id
```

This is especially important for:

```text
premium currency
quest rewards
mission rewards
admin grants
migration adjustments
purchases
```

---

# 29. Phase 9 — Inventory and Crafting

Implement:

```text
load inventory
add item
remove item
buy item
consume item
store item
activate item
deactivate item
craft
recycle
expiry
gift-related inventory behavior
```

---

## Inventory Invariants

```text
quantity >= 0
cannot consume missing item
cannot claim reward twice
crafting inputs removed atomically
crafting output added atomically
unknown definitions rejected or preserved during migration
```

---

# 30. Phase 10 — Unit Systems

Separate:

```text
UnitDefinition
UnitInstance
```

---

## Unit Definition

Contains shared data such as:

```text
unit type
health
damage
movement speed
animation references
production time
cost
unlock requirements
```

---

## Unit Instance

Contains:

```text
instance ID
definition ID
current health
position
state
energy
temporary effects
```

---

## Reconstruct

```text
unit loading
production
queues
queue cancellation
queue collection
town movement
idle animation
walking animation
attack animation
damage
death
energy
revive
healing
special behaviors
```

---

# 31. Phase 11 — Player Progression

Implement:

```text
XP
levels
level rewards
unlocks
tutorial state
objectives
challenges
progress flags
```

---

## Server Owns Unlock Logic

Do not simply trust:

```text
client says player reached level X
```

Server calculates progression.

---

# 32. Phase 12 — Quest System

Model quests explicitly.

Example:

```text
QuestDefinition
├── prerequisites
├── objectives
└── rewards

QuestProgress
├── state
├── objective progress
├── started_at
└── completed_at
```

---

## Objective Types

Potential objective types:

```text
build
upgrade
collect
produce
own
spend
earn
mission
combat
research
craft
visit
help
level
```

Do not hardcode every quest as custom logic if generic objective types can represent it.

---

# 33. Phase 13 — Research System

Implement:

```text
research definitions
requirements
prerequisites
research costs
research timers
start research
cancel research
complete research
unlock effects
```

Completed research must remain permanently recorded.

---

# 34. Phase 14 — Collection System

Model separately:

```text
CollectionDefinition
CollectionProgress
CollectionReward
```

Support:

```text
item acquisition
collection progress
collection completion
reward claim
```

Reward claiming must be transactional and one-time.

---

# 35. Phase 15 — Missions and Combat

Start by reproducing compatibility behavior.

Later transition combat to server authority.

---

## Bad Combat API

```json
{
  "target_hp": 0,
  "reward": 500
}
```

This trusts the client.

---

## Correct Combat Intent

```json
{
  "attacker_id": "unit-123",
  "target_id": "enemy-456",
  "action": "attack"
}
```

Server determines:

```text
attacker exists
target exists
mission active
attacker alive
target alive
range valid
cooldown valid
energy valid
damage amount
critical result
death result
reward result
```

---

# 36. Prefer Deterministic Action-Based Combat

Social Wars does not necessarily require MMO-style server simulation.

A simpler model:

```text
initial state
+
player action
+
game rules
=
result
+
state mutation
+
combat event
```

The Godot client animates the server result.

This makes:

```text
testing
replay
anti-cheat
debugging
migration
```

significantly easier.

---

# 37. Combat Event Log

Eventually record events such as:

```text
mission_id
action_number
attacker
target
action_type
damage
critical
status_effect
resulting_hp
timestamp
```

Useful for:

```text
debugging
replay
analytics
anti-cheat
support
```

---

# 38. Phase 16 — Social Systems

Reconstruct:

```text
friends
friend scores
visits
visit rewards
help mechanics
neighbor mechanics
leaderboards
social rewards
```

The production server must own social relationship state.

---

# 39. Phase 17 — Special and Rare Legacy Systems

`command.py` contains behavior outside the main town loop.

Examples that should be explicitly audited include:

```text
SOC/event systems
temporary events
rider mechanics
penguin mechanics
dive mechanics
superspy mechanics
rage mechanics
hero mechanics
special powers
temporary items
special crafting
special buildings
event progression
event-specific currencies
```

These should not block the first playable modern client.

However, each one must eventually receive one of:

```text
IMPLEMENTED
PARITY_VERIFIED
OUT_OF_SCOPE
RETIRED
```

Do not silently forget them.

---

# 40. Phase 18 — Begin Server API v1

Only begin this stage when the Godot client is substantially functional through Compatibility API v0.

---

# 41. Recommended Production Backend Stack

Because the existing game logic is Python, a practical target is:

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
PostgreSQL
Pytest
```

Optional later:

```text
Redis
background jobs
WebSockets
```

---

## Why Not Immediately Rewrite to NestJS?

A NestJS rewrite would simultaneously introduce:

```text
new language
new framework
new architecture
new persistence model
new game client
```

without materially helping the reconstruction.

Keeping Python initially allows legacy algorithms and knowledge to be migrated incrementally.

NestJS remains viable if there is a strong organizational reason to standardize on TypeScript.

---

# 42. Server v1 Domain Structure

Example:

```text
apps/server-v1/
├── api/
│   └── v1/
│
├── domain/
│   ├── players/
│   ├── towns/
│   ├── economy/
│   ├── buildings/
│   ├── units/
│   ├── inventory/
│   ├── research/
│   ├── quests/
│   ├── collections/
│   ├── missions/
│   ├── combat/
│   └── social/
│
├── services/
├── repositories/
├── infrastructure/
├── migrations/
└── tests/
```

---

# 43. Do Not Recreate `command.py`

The giant legacy command dispatcher should not become:

```text
/v1/command
```

forever.

Replace it with domain-oriented APIs.

Examples:

```http
GET /v1/bootstrap

GET /v1/towns/me

POST /v1/towns/me/buildings

POST /v1/towns/me/buildings/{id}/move

POST /v1/towns/me/buildings/{id}/upgrade

POST /v1/towns/me/buildings/{id}/collect

POST /v1/units/queues

DELETE /v1/units/queues/{id}

POST /v1/research/{id}/start

POST /v1/quests/{id}/claim

POST /v1/missions/{id}/start

POST /v1/missions/{id}/actions
```

---

# 44. Authoritative Server Rule

The legacy implementation may trust client-provided state changes.

The production implementation must not.

For example:

```text
Client:
"Build Barracks at tile 24,17"
```

Server:

```text
1. Load player state.
2. Load building definition.
3. Validate player level.
4. Validate unlock.
5. Validate prerequisites.
6. Validate town zone.
7. Validate placement.
8. Validate resource balance.
9. Calculate price.
10. Deduct resources.
11. Create building instance.
12. Calculate XP.
13. Start construction timer.
14. Increment state revision.
15. Commit transaction.
16. Return authoritative result.
```

---

# 45. PostgreSQL Data Model

Potential tables:

```text
accounts
players
towns
town_zones
town_objects
buildings
unit_instances
unit_queues
inventory_items
inventory_stacks
player_resources
economy_ledger
research_progress
quest_progress
objective_progress
collection_progress
missions
mission_sessions
combat_events
friendships
friend_visits
player_unlocks
content_versions
migration_runs
audit_events
```

Exact schema should follow discovered legacy behavior rather than being finalized prematurely.

---

# 46. Use JSONB Carefully

JSONB is useful for:

```text
unknown legacy fields
migration metadata
rare event payloads
temporary compatibility state
```

Do not simply move the entire old village JSON into one giant PostgreSQL JSONB column and call the migration complete.

Core production state should become structured.

---

# 47. Concurrency Protection

Use player or town revision numbers.

Example:

```json
{
  "expected_revision": 73
}
```

Server compares this against current revision.

If stale:

```http
409 Conflict
```

Client then resynchronizes.

---

# 48. Idempotency

Commands such as:

```text
purchase
collect
claim
craft
mission reward
premium transaction
```

must tolerate network retries.

Use:

```http
Idempotency-Key: UUID
```

If the same request is retried, the server should return the previous result instead of executing it twice.

---

# 49. Database Transactions

Operations that modify multiple pieces of state must be atomic.

Example building purchase:

```text
deduct coins
create building
award XP
update quest objective
write economy ledger
increase revision
```

All should succeed or fail together.

---

# 50. Phase 19 — Legacy Save Migration

Build a dedicated save migration CLI.

Example:

```bash
socialwars-migrate inspect old-save.json

socialwars-migrate validate old-save.json

socialwars-migrate import old-save.json

socialwars-migrate verify old-save.json
```

---

## Support Dry Runs

```bash
socialwars-migrate import old-save.json --dry-run
```

Dry-run output should show:

```text
player detected
resources detected
objects detected
units detected
inventory detected
quests detected
research detected
collections detected
unknown fields detected
validation errors
planned database mutations
```

---

# 51. Save Validation

Check:

```text
known object IDs
known unit IDs
known item IDs
known research IDs
known quests
known collections
resource validity
town positions
map bounds
object overlap
duplicate object IDs
duplicate unit IDs
queue state
timestamps
timer validity
unknown fields
```

---

# 52. Never Silently Drop Unknown Save Data

Unknown legacy fields should be retained somewhere like:

```text
legacy_extra
```

during migration.

This allows future investigation instead of destructive loss.

---

# 53. Migration Must Be Idempotent

Track:

```text
source save hash
migration version
player
import timestamp
migration status
```

Re-importing the same file should not duplicate objects or rewards.

---

# 54. Phase 20 — Authentication and Security

For local preservation mode, complex authentication may not be required.

For public hosting, implement proper account security.

---

## Required Production Measures

```text
no hardcoded secrets
environment-based secrets
HTTPS
secure password hashing where applicable
session expiry
refresh token rotation
request validation
rate limiting
payload limits
authorization checks
audit logging
server-side economy validation
server-side combat validation
server-side ownership validation
```

---

# 55. Local and Online Modes

The architecture could eventually support both.

## Preservation / Offline Mode

```text
Godot
    ↓
Local Compatibility Server
    ↓
Local Save
```

---

## Online Mode

```text
Godot
    ↓
Server API v1
    ↓
PostgreSQL
```

Because both use `GameApi`, the game client can avoid duplicating most gameplay/UI code.

---

# 56. Testing Strategy

Testing is essential because the goal is reconstruction rather than merely writing a similar game.

---

# 57. Golden-Master Tests

For each legacy operation compare:

```text
legacy before
legacy request
legacy response
legacy after
```

against the modern implementation.

Verify:

```text
resource mutations
object mutations
timers
XP
rewards
progression
queues
inventory
mission state
```

---

# 58. Replay Tests

Create gameplay sequences.

Example:

```text
load fresh player
buy building
move building
collect resource
order unit
collect unit
start research
claim research
complete quest
start mission
attack enemy
claim mission reward
```

Run the same sequence against:

```text
Legacy Server
Compatibility API v0
Server API v1
```

Compare state transitions.

---

# 59. Game Invariant Tests

Important invariants:

```text
resources remain valid
premium currency cannot duplicate
object IDs remain unique
unit IDs remain unique
buildings cannot overlap illegally
buildings cannot enter locked zones
queues respect capacity
rewards cannot be claimed twice
completed research remains completed
dead units cannot attack
unowned units cannot be controlled
client clock cannot complete timers early
```

---

# 60. Network Failure Tests

Test:

```text
request timeout
duplicate request
lost response
reconnect
server restart
database rollback
stale revision
request retry
out-of-order response
expired session
content version mismatch
client version mismatch
```

---

# 61. Visual Regression Tests

Maintain reference scenes for:

```text
town layout
building placement
unit animation
combat
HUD
missions
dialogs
```

Compare:

```text
position
scale
pivot
frame
orientation
depth
spacing
```

---

# 62. Performance Testing

Create stress scenarios for:

```text
large towns
hundreds of town objects
many animated units
many simultaneous FX
rapid pan/zoom
large inventory
large content catalog
network bootstrap
save imports
```

Measure before optimizing.

---

## Likely Optimization Areas

```text
off-screen animation throttling
visibility culling
sprite atlases
object pooling
resource caching
lazy UI loading
asset streaming
batching
```

---

# 63. CI Pipeline

The project should eventually run automated CI for:

```text
legacy regression tests
Python linting
Python type checking
Server v1 unit tests
PostgreSQL integration tests
content schema validation
save migration tests
asset manifest validation
Godot headless project import
Godot tests
Godot build
runtime dependency inspection
```

---

# 64. Flash-Free CI Gate

Production packaging should fail if the runtime artifact contains:

```text
*.swf
Flash Player runtime
Ruffle runtime
ActionScript runtime
legacy Flash loader
```

The final client should not depend on them.

---

# 65. Release Artifact Separation

Produce separate artifacts:

```text
legacy-reference
client
server
content
save-migrator
```

The production client must not accidentally package:

```text
legacy/
```

---

# 66. Observability

Production Server v1 should implement structured logging.

Include:

```text
request ID
player ID
action ID
domain
duration
result
revision
```

without exposing sensitive data.

---

## Useful Metrics

```text
request rates
error rates
database latency
slow actions
migration failures
economy anomalies
combat failures
queue failures
content mismatches
```

---

# 67. Admin and Support Tools

Eventually provide tools for:

```text
player lookup
town inspection
resource inspection
inventory inspection
action history
migration history
economy ledger
grant resource with reason
revoke resource with reason
restore snapshot
disable account
inspect content version
```

A CLI is sufficient initially.

A web dashboard can come later.

---

# 68. Content Versioning

Track:

```text
client version
protocol version
content version
server version
```

Bootstrap may return:

```json
{
  "server_version": "1.3.0",
  "protocol_version": 1,
  "content_version": "2026.09.01",
  "minimum_client_version": "0.8.0"
}
```

---

# 69. Server Owns Gameplay Rules

Critical values such as:

```text
building costs
unit costs
XP rewards
mission rewards
research requirements
timers
unlock rules
combat values
```

must be validated from server-controlled content.

Do not trust client copies of these values.

---

# 70. WebSocket Policy

Do not introduce WebSockets simply because the architecture is modern.

Use normal HTTPS requests for:

```text
town actions
building actions
inventory
quests
research
collections
mission commands
```

Use WebSockets later only when useful for:

```text
presence
real-time social events
live announcements
true live multiplayer
push notifications while connected
```

---

# 71. Legal and Provenance Workstream

This should not be ignored.

Create:

```text
PROVENANCE.md
```

and an asset registry containing:

```text
asset
source
original filename
modified status
creator where known
rights status
redistribution status
notes
```

---

## Important Distinction

The repository being GPL does **not automatically mean** every original Social Wars:

```text
art asset
music asset
sound asset
trademark
character
proprietary Flash client component
```

is automatically redistributable under GPL.

Before publicly redistributing reconstructed proprietary assets, obtain appropriate legal review.

---

# 72. Keep Implementations Distinguishable

Maintain separation between:

```text
legacy original material
decompiled reference
converted assets
clean modern implementation
```

This helps:

```text
maintenance
provenance
licensing review
debugging
preservation
```

---

# 73. Definition of Truly Flash-Free

The project is not genuinely Flash-free merely because Adobe Flash Player is gone.

For this project, Flash retirement means:

- Godot is the runtime client.
- No SWF executes during gameplay.
- No ActionScript executes.
- No Flash Player is required.
- No Ruffle runtime is required.
- `SWLoader.swf` is not packaged.
- `Basesec_*.swf` is not packaged.
- Sprite SWFs have been converted or recreated.
- FX SWFs have been converted or recreated.
- Flash UI assets have been converted or recreated.
- FlashVars are gone from the modern client.
- AMF is not required by the modern client.
- A clean machine can install and play the game without Flash-related software.
- CI verifies no Flash runtime dependency exists.

Archived SWFs may still exist in:

```text
legacy/
```

for preservation purposes.

---

# 74. Milestone Roadmap

## M0 — Preservation

Deliver:

```text
legacy baseline tag
environment documentation
dependency lock
asset hashes
canonical saves
known bug documentation
```

Exit:

Legacy implementation is reproducible.

---

## M1 — Protocol Discovery

Deliver:

```text
endpoint catalog
command catalog
legacy request examples
state mutation documentation
```

Exit:

Normal gameplay no longer contains major unknown commands.

---

## M2 — Behavioral Tooling

Deliver:

```text
protocol recorder
protocol replay
state diff
golden fixture format
```

Exit:

Legacy behavior can be automatically captured and compared.

---

## M3 — Content Normalization

Deliver:

```text
normalized game configuration
schemas
content validator
dependency validation
content manifest
```

Exit:

Godot can load validated game definitions without parsing arbitrary legacy structures.

---

## M4 — Asset Pipeline

Deliver:

```text
asset registry
SWF extraction workflow
conversion tooling
one converted building
one converted unit
```

Exit:

At least one authentic building and unit render correctly in Godot.

---

## M5 — Godot Foundation

Deliver:

```text
Godot project
GameApi
LegacyV0Api
ContentRegistry
Session
GameClock
camera
basic UI foundation
Settings
AudioManager
```

Exit:

Client boots and communicates with Compatibility API.

---

## M6 — Town Vertical Slice

Deliver:

```text
existing save loading
terrain
town objects
one building
one unit
camera
zoom
selection
HUD
```

Exit:

A player can launch and view a real legacy town without Flash.

This is the **first major project success target**.

---

## M7 — Construction and Economy

Deliver:

```text
placement
purchase
move
sell
store
upgrade
construction timers
collect income
town expansion
resources
XP basics
```

Exit:

Core town-building gameplay loop works.

---

## M8 — Units

Deliver:

```text
unit definitions
unit instances
queues
production
collection
movement
animations
basic behaviors
```

Exit:

Core unit gameplay works.

---

## M9 — Progression

Deliver:

```text
XP
levels
quests
research
collections
tutorial/progression
```

Exit:

Primary long-term progression systems work.

---

## M10 — Missions and Combat

Deliver:

```text
mission loading
mission state
combat actions
damage
death
mission completion
rewards
```

Exit:

Primary combat loop works.

---

## M11 — Social and Special Systems

Deliver:

```text
friends
visits
scores
social rewards
legacy event systems
special mechanics
```

Exit:

All relevant legacy game systems are classified and implemented or explicitly excluded.

---

## M12 — Asset Parity

Deliver:

```text
all runtime-required SWFs converted or recreated
UI assets converted
FX replaced
animation gaps resolved
```

Exit:

Godot no longer depends on runtime SWFs.

---

## M13 — Server API v1

Deliver:

```text
FastAPI architecture
domain services
authoritative validation
modern API
GameApi ServerV1 implementation
```

Exit:

Godot can operate against the modern server.

---

## M14 — PostgreSQL

Deliver:

```text
database schema
Alembic migrations
repositories
transactions
economy ledger
revisions
idempotency
```

Exit:

Production state no longer depends on filesystem JSON.

---

## M15 — Save Migration

Deliver:

```text
save validator
save importer
dry-run mode
migration report
verification
legacy_extra preservation
```

Exit:

Legacy saves can be migrated safely into PostgreSQL.

---

## M16 — Production Hardening

Deliver:

```text
authentication
authorization
rate limiting
secure secrets
HTTPS readiness
observability
admin tooling
network resilience
CI
deployment
```

Exit:

Server architecture is ready for controlled public deployment.

---

## M17 — Flash Retirement

Deliver:

```text
runtime Flash dependency scan
final package verification
legacy archival separation
documentation update
```

Exit:

The production game runs without:

```text
Flash Player
Ruffle
ActionScript
SWF execution
AMF
FlashVars
```

---

# 75. Exact Feature Migration Dependency Order

Use this order when migrating gameplay:

```text
BOOT
    ↓
CONTENT
    ↓
PLAYER
    ↓
TOWN RENDERING
    ↓
BUILDINGS
    ↓
ECONOMY
    ↓
INVENTORY
    ↓
CRAFTING
    ↓
UNITS
    ↓
XP / LEVELS
    ↓
QUESTS
    ↓
RESEARCH
    ↓
COLLECTIONS
    ↓
MISSIONS
    ↓
COMBAT
    ↓
SOCIAL
    ↓
SPECIAL EVENTS
```

Do not migrate systems randomly.

---

# 76. Initial Implementation Backlog

This is the recommended first concrete backlog.

## Preservation

### 1. Create legacy baseline Git tag

```text
chore: create legacy baseline tag
```

### 2. Document legacy environment

```text
docs: document legacy runtime and startup process
```

### 3. Lock Python dependencies

```text
chore: lock legacy Python dependencies
```

### 4. Build SHA-256 asset manifest

```text
tooling: add legacy asset hash manifest generator
```

### 5. Create canonical save fixtures

```text
test: add canonical legacy save fixtures
```

---

## Behavioral Tooling

### 6. Implement protocol recorder

```text
tooling: record legacy request and response behavior
```

### 7. Implement village state diff

```text
tooling: add before/after village state differ
```

### 8. Implement command replay

```text
tooling: add legacy command replay runner
```

### 9. Generate endpoint catalog

```text
docs: catalog legacy server endpoints
```

### 10. Generate command catalog

```text
docs: catalog legacy game commands and mutations
```

---

## Domain and Content

### 11. Define canonical game domain model

```text
docs: define canonical Social Wars domain model
```

### 12. Create game-content package

```text
feat: initialize normalized game content package
```

### 13. Add schemas

```text
feat: add schemas for normalized game content
```

### 14. Build content validator

```text
tooling: validate normalized game content
```

---

## Godot Foundation

### 15. Initialize Godot project

```text
feat: initialize Godot client
```

### 16. Implement GameApi abstraction

```text
feat: add GameApi abstraction
```

### 17. Implement Compatibility API v0

```text
feat: initialize compatibility API v0
```

### 18. Implement bootstrap loading

```text
feat: load player and game bootstrap data
```

### 19. Implement ContentRegistry

```text
feat: add canonical content registry
```

### 20. Implement asset ID registry

```text
feat: map legacy assets to modern runtime assets
```

---

## Town Renderer

### 21. Implement isometric grid-to-screen conversion

```text
feat: implement isometric coordinate conversion
```

### 22. Implement screen-to-grid conversion

```text
feat: implement inverse isometric coordinate conversion
```

### 23. Add coordinate tests

```text
test: verify isometric coordinate conversions
```

### 24. Implement town camera

```text
feat: add town camera pan and zoom
```

### 25. Implement town bounds

```text
feat: add town map boundaries
```

### 26. Render terrain

```text
feat: render legacy town terrain
```

### 27. Render static town objects

```text
feat: render town objects from existing save
```

### 28. Implement Y/depth sorting

```text
feat: implement isometric object depth sorting
```

### 29. Implement selection

```text
feat: add town object selection
```

### 30. Implement HUD resources

```text
feat: display authoritative player resource HUD
```

---

## First Asset Migration

### 31. Convert first building

```text
assets: convert first legacy building
```

### 32. Render first real building

```text
feat: render converted building in town
```

### 33. Convert first unit

```text
assets: convert first legacy unit
```

### 34. Render first real unit

```text
feat: render converted legacy unit
```

### 35. Add unit idle animation

```text
feat: play converted unit idle animation
```

---

## First Flash-Free Gate

### 36. Create no-Flash vertical-slice test

Verify:

```text
Godot launches
no Flash runtime installed
no Ruffle installed
existing legacy save loads
town renders
terrain renders
buildings render
unit renders
HUD renders
camera works
selection works
```

This is the first major milestone to target.

---

# 77. Second Implementation Backlog

After the Flash-free town works, implement:

```text
building placement preview
grid validation
building purchase
building movement
building flip/orientation
building storage
building restoration
building selling
construction timer
building collection
town expansion
obstacle clearing
inventory loading
unit queue
unit production
unit collection
unit movement
```

---

# 78. Do Not Build These Early

Avoid spending early development time on:

```text
Flask → NestJS rewrite
PostgreSQL migration before Godot works
Kubernetes
microservices
Redis everywhere
WebSockets everywhere
complete UI redesign
game rebalancing
mobile support
custom launcher/updater
public account infrastructure
new multiplayer functionality
```

The first problem to solve is:

Can the existing Social Wars game be faithfully reconstructed and played through a modern client with no Flash dependency?

Everything else follows from that.

---

# 79. Major Technical Risks

## Risk 1 — Important Logic Exists Only in Compiled SWFs

Mitigation:

```text
protocol recording
decompilation/reference analysis
behavioral observation
golden-master testing
state-diff testing
```

---

## Risk 2 — SWF Animations Are More Complex Than Expected

Mitigation:

```text
asset registry
conversion priority
automated extraction where practical
manual recreation for complex assets
visual regression testing
```

---

## Risk 3 — Hidden/Obscure Commands Are Missed

Mitigation:

```text
generated command catalog
coverage tracking
protocol recording
fixture requirements
migration status tracking
```

---

## Risk 4 — Legacy Saves Are Inconsistent

Mitigation:

```text
multiple fixtures
strict validator
raw source preservation
legacy_extra
migration reports
```

---

## Risk 5 — Server Rewrite Changes Behavior

Mitigation:

```text
replay tests
golden tests
legacy-vs-v1 comparison
state-diff tooling
```

---

## Risk 6 — Client Cheating

Mitigation:

```text
authoritative server
economy ledger
server-side rules
ownership validation
revision checking
idempotency
```

---

## Risk 7 — Duplicate Rewards Due to Network Retries

Mitigation:

```text
database transactions
idempotency keys
unique constraints
revision validation
reward claim records
```

---

## Risk 8 — Flash Dependency Survives in Rare UI/FX

Mitigation:

```text
asset dependency manifest
CI package scanning
conversion status tracking
final Flash-free gate
```

---

## Risk 9 — Original Asset Distribution Restrictions

Mitigation:

```text
provenance tracking
asset classification
distribution review
legal review before public release
```

---

# 80. Success Checkpoints

## Checkpoint A — Preservation

Successful when:

```text
legacy environment reproducible
asset hashes created
canonical saves preserved
protocol recorder operational
```

---

## Checkpoint B — First Modern Client

Successful when:

```text
Godot starts without Flash
existing player loads
existing town loads
terrain renders
buildings render
units render
camera works
HUD works
selection works
```

---

## Checkpoint C — Main Gameplay

Successful when Godot supports:

```text
build
move
collect
train units
research
quests
collections
missions
combat
```

---

## Checkpoint D — Legacy Parity

Successful when:

```text
all relevant command.py behavior classified
major replay tests pass
required assets converted
special systems classified
no unknown critical gameplay dependencies remain
```

---

## Checkpoint E — Production Server

Successful when:

```text
Server v1 authoritative
PostgreSQL active
legacy saves migrate
auth secure
economy protected
observability operational
CI operational
```

---

## Checkpoint F — Flash Retirement

Successful when the game can:

```text
install
launch
load player
load town
play normal game loop
save progress
close
restart
resume
```

without:

```text
Flash Player
SWF execution
ActionScript
Ruffle
AMF
FlashVars
```

---

# 81. Recommended Architecture Decision Record

Create:

```text
docs/adr/ADR-001-preservation-first-reconstruction.md
```

Suggested content:

# ADR-001 — Preservation-First Social Wars Reconstruction

## Status

Accepted

## Context

The current project contains a working or partially working reconstruction of Social Wars using a Flask server and the original Flash client architecture.

Although Flash is obsolete as a runtime platform, the existing repository contains valuable behavioral logic, game configuration, save data, server behavior, protocol behavior, images, sounds, and compiled client assets.

Replacing everything simultaneously would make regression detection difficult and risk losing undocumented gameplay behavior.

## Decision

The current Flask/Flash implementation will be treated as the reference implementation and preservation dataset.

The legacy implementation will be frozen while a new Godot client is built.

The first modern client will communicate through a compatibility API that preserves legacy game semantics.

Once client-side feature parity has been established, the backend will progressively migrate toward an authoritative FastAPI server backed by PostgreSQL.

Existing JSON saves will be treated as migration inputs and regression fixtures.

SWFs may remain under an archival legacy directory but must not be required by the final runtime or included in production client packages.

## Consequences

Positive:

- undocumented behavior remains discoverable
- migrations can be verified
- client and server rewrites are decoupled
- existing saves remain usable
- Flash removal can happen incrementally
- regressions become testable

Negative:

- legacy infrastructure remains temporarily
- compatibility code must be maintained during migration
- repository contains old and new implementations simultaneously

These costs are acceptable because they substantially reduce reconstruction risk.

---

# 82. End-State Repository

The eventual repository could look like:

```text
social-wars/
├── apps/
│   ├── client/
│   │   └── Godot
│   │
│   ├── server/
│   │   └── FastAPI
│   │
│   └── compat/
│       └── Legacy compatibility layer
│
├── packages/
│   └── game-content/
│
├── tools/
│   ├── asset-converter/
│   ├── protocol-recorder/
│   ├── protocol-replay/
│   ├── state-diff/
│   ├── save-migrator/
│   └── content-builder/
│
├── legacy/
│   ├── flask-server/
│   ├── flash-client/
│   ├── raw-assets/
│   └── saves/
│
├── tests/
│   ├── golden/
│   ├── integration/
│   ├── migration/
│   └── visual/
│
├── docs/
│   ├── architecture/
│   ├── legacy-protocol/
│   ├── game-systems/
│   ├── assets/
│   ├── migrations/
│   └── adr/
│
├── PROVENANCE.md
└── README.md
```

---

# 83. Immediate Priority Order

The immediate development sequence should be:

```text
FREEZE
    ↓
INSTRUMENT
    ↓
CATALOG
    ↓
REPLAY
    ↓
NORMALIZE CONTENT
    ↓
CREATE GODOT CLIENT
    ↓
BUILD COMPATIBILITY API
    ↓
RENDER ONE REAL TOWN
    ↓
BUILD MAIN GAMEPLAY LOOP
    ↓
REPLACE ALL RUNTIME SWFs
    ↓
BUILD AUTHORITATIVE SERVER
    ↓
MIGRATE TO POSTGRESQL
    ↓
HARDEN PRODUCTION
    ↓
RETIRE FLASH COMPLETELY
```

---

# 84. Most Important Near-Term Target

Do **not** make PostgreSQL or the backend rewrite the first visible result.

The first major target should be:

Launch the Godot client on a computer with no Flash runtime, load one real existing Social Wars save, and faithfully render the town, buildings, units, resources, camera, and basic selection using preserved legacy data.

Once that works, the project has proven that the Flash client can actually be replaced.

---

# 85. Core Architectural Thesis

The most important idea guiding the project is:

**The existing Social Wars repository is not obsolete code that should simply be replaced. It is the reference implementation, behavioral specification, protocol specification, preservation dataset, save corpus, content source, asset archive, and regression oracle for the reconstruction.**

The correct migration therefore is not:

```text
DELETE OLD GAME
    ↓
BUILD NEW GAME FROM MEMORY
```

It is:

```text
PRESERVE
    ↓
OBSERVE
    ↓
RECORD
    ↓
DOCUMENT
    ↓
REPRODUCE
    ↓
VERIFY
    ↓
REPLACE
    ↓
RETIRE
```

The existing Flask implementation should remain available until the Godot client and Server v1 can prove through recorded behavior, replay tests, golden fixtures, and state-diff tests that every required legacy system has a verified replacement.

That approach gives the project the best chance of achieving all four goals simultaneously:

1. **Preserve the original Social Wars behavior.**
2. **Remove the dependency on Flash/SWF completely.**
3. **Modernize the client/server architecture safely.**
4. **Create a maintainable foundation that can continue evolving after preservation parity is achieved.**

---

# 86. Recommended Development Workflow

For each major feature or migration unit:

```text
1. Explore legacy implementation.
2. Identify related commands/endpoints/assets/state.
3. Capture legacy fixtures.
4. Write/update OpenSpec change.
5. Define acceptance criteria.
6. Create feature branch.
7. Implement smallest complete vertical behavior.
8. Add automated tests.
9. Replay legacy fixtures.
10. Compare state.
11. Perform Godot/manual visual verification where applicable.
12. Update migration status.
13. Update documentation.
14. Review.
15. Merge.
16. Push.
```

---

# 87. Recommended Branch Strategy

Use branch-per-feature or branch-per-migration-unit.

Examples:

```text
feat/protocol-recorder
feat/state-diff
feat/content-normalization
feat/godot-bootstrap
feat/town-renderer
feat/building-placement
feat/unit-production
feat/quest-system
feat/server-v1-buildings
feat/save-migrator
```

Avoid creating enormous branches spanning several milestones.

---

# 88. OpenSpec Usage

Use OpenSpec for meaningful behavioral or architectural changes.

Each change should define:

```text
problem
scope
non-goals
existing behavior
target behavior
acceptance criteria
affected systems
migration concerns
testing requirements
```

For reconstruction work, include:

```text
Legacy reference:
- endpoint
- command
- source files
- fixtures

Parity requirements:
- expected state mutation
- expected response
- visual behavior where relevant
```

---

# 89. Definition of Done for a Migrated Feature

A migration feature is not complete merely because the new UI appears to work.

A migrated feature should normally satisfy:

```text
legacy behavior identified
legacy fixture captured
modern behavior implemented
automated test added
state mutation verified
error conditions tested
retry behavior considered
content IDs preserved
relevant assets migrated
documentation updated
migration status updated
no new Flash dependency introduced
```

For Server v1 features additionally require:

```text
server-authoritative validation
database transaction where needed
authorization
revision handling
idempotency where needed
economy ledger where needed
```

---

# 90. Final Project Definition of Done

The complete modernization is finished when:

```text
Godot is the only gameplay client.

Normal gameplay contains no SWF execution.

Normal gameplay contains no ActionScript execution.

Adobe Flash Player is unnecessary.

Ruffle is unnecessary.

The modern client does not know about command.php.

The modern client does not use FlashVars.

The modern client does not require AMF.

All gameplay-critical legacy commands are implemented,
retired, or explicitly declared out of scope.

All runtime-critical Flash assets have been converted
or recreated.

Existing supported legacy saves can be migrated.

Production player state lives in PostgreSQL.

Production game actions are server authoritative.

Important economy mutations are auditable.

Network retries cannot duplicate important rewards.

Client clock manipulation cannot bypass timers.

Authentication and authorization are production-safe.

Automated golden/replay tests verify important legacy parity.

Visual regression coverage exists for important scenes.

CI prevents accidental reintroduction of Flash dependencies.

Legacy files remain preserved separately for historical,
debugging, migration, and research purposes.

A clean machine can install the modern client,
connect to the server, load a player,
play the game, close it, reopen it,
and continue playing without installing
any Flash-related software.
```

---

# 91. Development Priority Summary

## Build Now

```text
legacy preservation
dependency locking
hash manifest
canonical saves
protocol recorder
state diff
command replay
endpoint catalog
command catalog
content normalization
Godot initialization
GameApi abstraction
Compatibility API v0
town bootstrap
isometric renderer
camera
terrain
town objects
first building
first unit
HUD
selection
no-Flash vertical slice
```

## Build Next

```text
building placement
economy
construction
collection
inventory
unit queues
unit movement
XP
quests
research
collections
missions
combat
social
special systems
asset parity
```

## Build After Parity Is Established

```text
Server API v1
authoritative game rules
PostgreSQL
save importer
authentication
rate limiting
observability
admin tools
production deployment
```

## Build Much Later If Needed

```text
Redis
WebSockets
mobile client
new multiplayer systems
major gameplay redesign
balance changes
microservices
advanced deployment infrastructure
```

---

# 92. The First Concrete Goal

The engineering team or coding agent should treat the following as the immediate mission:

**Preserve and instrument the legacy implementation, then build the smallest Godot vertical slice capable of loading and displaying a real Social Wars town from an existing save without executing Flash or SWF content.**

Everything before that target should directly support it.

Everything that does not directly support it should generally wait.

The first sequence therefore is:

M0 Preservation
    ↓
M1 Protocol Discovery
    ↓
M2 Recorder / Replay / State Diff
    ↓
M3 Content Normalization
    ↓
M4 Initial Asset Conversion
    ↓
M5 Godot Foundation
    ↓
M6 Flash-Free Town Vertical Slice

**M6 is the first major victory.**

Do not allow backend modernization, infrastructure work, or unrelated redesign to delay reaching it.

### The M8 entry position, recorded for the next run

M8's first deliver line is **unit definitions**, and the delivered work already constrains it
in three ways that the investigation must not re-derive:

- **The corpus contains no unit placements at all**, and 0 of its 40 placed rows carry
  `attr["xp"]`, which is why the XP line's unit XP (`add_xp_unit`) and the level curve's
  `reward_type`/`reward_amount` are out of scope there and recorded as such.
- **M4 established the unit asset truth**: `tools/asset-registry/convert_unit.py` produced one
  converted unit package — a per-sprite timeline inventory with shape/bitmap linkage, **no
  tessellation and no playback semantics** — and its README states it establishes "no animation
  correctness, rendering, visual fidelity, gameplay semantics, or Godot loading". So M8's
  `animations` and any rendering claim rest on that package plus the M6 slice evidence, which
  already proved authentic unit rendering through the Wild Elephant sprite in
  `apps/client-godot/evidence/town/` while recording that the fresh save has no unit placements.
- **The committed content already carries the unit definitions**: the items normalization
  committed **429 units** of the 900 `items` entries (470 buildings, 429 units, 1 documented
  special), each with schemas and round-trip evidence, so `unit definitions` is a content-delivery
  line over committed artifacts rather than a legacy-behaviour derivation.

The honest first questions for the M8 investigation are therefore: what does the legacy server
actually do with units (the command catalog's "Units and production queues" section is the place
to start, alongside `push_unit`, `pop_unit`, and `push_dead_unit`), what a unit instance looks
like in the save, and what the corpus can and cannot exercise — with every unobserved rule marked
derived-provisional exactly as M7's were.
