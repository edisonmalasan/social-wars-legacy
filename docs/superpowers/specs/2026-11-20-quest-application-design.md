# Authoritative Quest Application — Design

**Date:** 2026-11-20
**Spec:** `docs/ROADMAP.md` Group G4 (the "first chapter is completable" and "Quests... are functional" items) and the roadmap's *Unimplemented layers* blocker.

## Intent

The server currently refuses `end_quest` and has no case for `collect_mission`, `set_quest_var` or `admin_set_quest_rank`, so no quest reward is ever granted by server rule. The rules package already contains the full quest state machine (`packages/rules/src/quest.ts`). This work wires that state machine into the authoritative applier, following the same pattern used for darts, trade and offer packs: the client sends identifiers, the server owns the state, the win, the reward and the once-only guard.

## Two features, not one

The roadmap's two open quest items describe different machinery:

1. **Chapters / missions** (`set_quest_var`, `collect_mission`, `admin_set_quest_rank`) are a state machine on the player's own map. Chapter completion is a **state predicate**, not a combat result. This can be made authoritative with no battle data.
2. **Assault quests** (`end_quest`) are self-contained battles. The native command carries only `[questId, difficulty]` and the legacy form a client-claimed `win` flag. The server must hold a `QuestState`, advance it from validated events, and compute the win with `isQuestVictory` before calling `finishQuest`/`awardQuest`.

`start_quest` does not exist in the client. There is no server-side positional combat simulator and no complete map roster in the repository. Full authoritative combat (b-full) is therefore **out of scope** and remains a recorded dependency.

## Goals / non-goals / anti-goals

- **Goals:** server computes every quest and chapter reward from content; a replay pays once; a client cannot claim a win by sending a `win` flag or a reward delta; the chapter map advances from server-owned `questsRank`.
- **Non-goals:** rendering a quest battle in the web client; simulating unit movement or positioning; the legacy Flash client emitting new event commands.
- **Anti-goals:** adding commands to the 94-command protocol table (it is cross-checked against the report and the client); trusting the client's difficulty as the quest rank; treating `{0,0,0}` chapter objectives as a real completion gate without recording that the trust boundary is the client's event report.

## Constraints

- The server is authoritative; the rules engine is pure (no clock, unseeded randomness or I/O).
- No runtime dependency; Node's built-in test runner.
- The command catalogue check must still report 94 = 94 = 94.
- A refused command spends nothing. Quest commands are unpriced (they grant, not spend).
- Follow the existing applier/helper/test pattern from `apply.ts` and `apply.test.ts`.

## Approaches

1. **New quest-event commands** (e.g. `quest_element_killed`). Cleanest naming, but it changes `COMMAND_NAMES` from 94 entries, breaking the cross-checked catalogue against the report and the client until all three are regenerated. Rejected: high churn, no benefit to the player.
2. **Reuse `set_quest_var` (chosen).** Its whitelist already carries `killed`, `spawned`, `ended`, `activators`, `boss`, `treasure` and `id`. The server validates the value shapes, diffs new `killed` refs against the roster, advances a server-held `QuestState`, and lets `end_quest` resolve the win. No protocol change; the legacy shim already passes these args verbatim. Cost: the server still trusts the client's report that an element died — the same boundary as darts (client names a balloon, server owns the prize). This is documented, not hidden.
3. **Full authoritative combat.** Would need a positional simulator and a complete roster derived from decompiled AS3 that is not in the repository. Recorded as a remaining dependency, not attempted.

## Design (approach 2)

### Chapter path

- `setQuestVarCommand`: reject unknown keys, validate value shapes (`spawned/ended/visited` booleans; `activators/boss/treasure` numeric arrays; `killed` string arrays; `id` integer), ignore `idSimpleChapter` as upstream does, mirror `id` into `map.idCurrentMission`, and refuse `ended: true` unless the chapter was actually `spawned` and has a non-empty objective record.
- `collectMissionCommand`: parse `nextChapterId` with the upstream `> 99 → 1` wrap; require the completed chapter's status to be spawned and ended; grant `REWARDS_CHAPTERS[completedId]` from content once (new private-state award log); reset the map's quest vars and write `idCurrentMission`, `timestampLastChapter` from `deps.now()`.
- `adminSetQuestRankCommand`: accept as applied so the client flow does not stall, but **never** let the client difficulty overwrite the server's `questsRank` — ranks come from `awardQuest`.

### Assault-quest path

- New private-state key `activeQuest` holding a JSON-safe `QuestState`, added in migration v0→1 alongside `questProgress`.
- Build the roster from `QuestSpec.elements` plus content items (`type === 'u'` → unit, `type === 'b'` → building). Affiliation for scripted key elements is `enemy`; friendly elements come from the player's army count option.
- On the first validated `set_quest_var` `killed` write for a quest id, lazily initialise with `prepareQuest` → `startQuest` → `loadQuestMap`. Each newly reported ref is checked against the roster and fed to `killQuestElement`; the gold/xp it returns are accumulated in the server-held state.
- `endQuestCommand` ignores the client's claimed win/difficulty for the award: compute `win = isQuestVictory(state) || (voluntary end with partial reward policy)`, call `finishQuest(state, win, { expRequired })`, then `awardQuest(questProgress, outcome)` for the once-only rank/reward, add the outcome's reward rows to the wallet, persist progress and clear `activeQuest`.
- Accept both wire shapes: native `[questId, difficulty]` and legacy `[JSON blob]` (parse only the quest id and difficulty; ignore `win`, `units`, `loot`).

## Evidence that closes the items

- A shim-level test drives `set_quest_var` writes then `collect_mission` and asserts exactly one content-derived reward, unaffected by an injected client `res` delta.
- A test drives `killed` events for a scripted quest, then `end_quest`, and asserts the reward comes from `finishQuest`/`awardQuest`, a claimed `win: true` with no server events is refused, and a replay pays nothing.
- `check-roadmap`, report-sync, typecheck, lint and the full suite stay green; the command catalogue stays 94/94/94.
