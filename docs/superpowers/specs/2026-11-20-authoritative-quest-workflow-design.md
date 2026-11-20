# Authoritative Quest Workflow — Design

**Date:** 2026-11-20
**Spec source:** user decision on the two-argument `set_quest_var` approach with architectural safeguards; `docs/ROADMAP.md` Group G4.

## Intent

Close the last open quest item by making the whole quest loop server-authoritative without changing the locked 94-command catalogue or the two-argument `set_quest_var` contract. The client must be able to enter a quest, report kills and quest-specific events, and have the server decide completion and rewards — with forged, duplicate, off-roster, wrong-quest and invalid-state events rejected.

## Decisions from the user

1. Preserve the 94-command catalogue and the two-argument `set_quest_var` contract. No undocumented third argument.
2. `end_quest` stays the completion/reward command only — it must not implicitly start a quest.
3. Add persistent, server-owned active-quest initialization. If an explicit start is needed, use a native API operation that does not change the legacy command catalogue.
4. Roster membership alone is not proof of a kill. Validate events against authoritative server gameplay state.
5. Initialize quest-specific counters from server-owned quest data.
6. Add validated truck-arrival (Q03), eligible-enemy (Q10/Q14) and civilian-evacuation (Q11) events.
7. Add a client per-kill request builder using two arguments.
8. Rewards remain server-authoritative, idempotent and replay-protected.
9. Chapter progress and existing quest compatibility are preserved.
10. Update the roadmap only after all acceptance criteria are verified.

## Goals / non-goals / anti-goals

- **Goals:** an explicit server-owned quest start; authoritative element state; validated event channels for all remaining quest win conditions; a client that can drive the workflow through existing commands plus native operations; once-only rewards.
- **Non-goals:** a positional combat simulator; changing the legacy command names or arity; rendering quest battles in the web client.
- **Anti-goals:** accepting a `killed` ref merely because it appears in a roster; using `end_quest` to seed state; marking G4 complete from protocol changes alone.

## Constraints

- The rules engine stays pure: no clock, unseeded randomness or I/O.
- The server owns the clock, the seed, the state and the reward.
- Every new state field must be JSON-safe and migrated for older saves.
- No runtime dependency on `upstream/`.
- All existing checks stay green: protocol, rules, server, client, integration and the content/asset pipeline.

## Approaches (to be finalised after recon)

1. **Native quest API operations** (preferred): `POST /api/quest/start` and `POST /api/quest/action` operate on the authenticated player's save inside the existing transaction layer. They create and advance a server-owned `activeQuest` state (element HP, counters, event flags). The legacy `set_quest_var('killed',[ref])` remains the client's reporting channel but is accepted only when the authoritative state already says the element is dead.
2. **Repurpose an existing command as a start signal** — rejected: it would make `end_quest` or `set_quest_var` do double duty and blur completion vs. start.
3. **Add a third `set_quest_var` argument** — rejected by the user; the catalogue and 2-arg contract are locked.

## What must be proved

- A start operation creates persistent active-quest state that survives a restart.
- A kill is accepted only when server state marks the element dead; roster membership alone is insufficient.
- Q03 trucks, Q10/Q14 eligible enemies and Q11 civilians each have validated event paths and counters seeded from server data.
- Forged, duplicate, off-roster, wrong-quest and invalid-state events are refused with unchanged save.
- Rewards pay exactly once; replay pays nothing; chapter state is unchanged.
- A real client-server end-to-end test completes the remaining quests.
