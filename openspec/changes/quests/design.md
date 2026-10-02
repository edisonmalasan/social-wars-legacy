# Design

## Context

From `docs/legacy-m9-quests.md`, restated compactly because every decision rests on it:

- **Six** dispatcher branches: `set_goals` 68, `complete_goal` 76, `set_quest_var` 87,
  `collect_mission` 430, `admin_set_quest_rank` 745, `end_quest` 752.
- **Only two** committed quest fields are read: `id` (8 quoted occurrences) and `title` (2, both `print`s).
  **`reward` has zero**, is committed on all 91 entries, and is **uniformly `10`**.
- `complete_goal` **writes nothing at all**.
- `end_quest` reads six keys from one client-authored JSON blob and destroys state by a **client-computed**
  `lost = max(0, unit[2] - unit[3])`; `difficulty` is the only clamped value.
- `set_goals` delegates to `engine.py:96-100`, which stores a client-sent `[visited, currentStep]` pair
  and **grows the list on demand** with no upper bound.
- `set_quest_var` accepts **any** client-invented key against the eight its own comment enumerates; `id`
  also aliases `idCurrentMission`; `idSimpleChapter` is explicitly ignored.
- `collect_mission` writes a **stringified** id against a corpus recording **integer** `0`, sets
  `timestampLastChapter`, **clears** `currentQuestVars`, and **wraps** above 99 rather than rejecting.
- `privateState["unlockedQuestIndex"]` has **zero** legacy sites.
- `fast_forward` writes `questTimes` (`command.py:942-944`) and `timestampLastChapter` (`911`) by a
  client-supplied subtraction. `version.py:38-44` initializes `questTimes` — a **migration**, not
  behaviour.
- Corpus: `goals` **151 entries all `None`**, `questsRank` `{}`, `questTimes` `{}`,
  `currentQuestVars` **`None`**, `idCurrentMission` `0`.
- Committed content: 91 entries, `kind` all `quest`, `id` **1..91**, indexed at import time in
  `get_game_config.py:142-146`, which is fail-closed for an unknown id but calls `int(id)` on the
  client value with no guard.
- `map_lose_item` calls `push_dead_unit`, and `end_quest` (`command.py:796`) is one of its two callers.

## Decisions

**D1 — deliver the state and the branch inventory; refuse the one destructive outcome (the scoping
decision).** Five of the six branches move state a client can legitimately be the source of intent for, and
the sixth destroys units by a client-computed count. Delivering the projection, the inventory, and the
five, while **refusing** the destruction, is the only split that neither invents authority nor discards
real behaviour. Refusing `end_quest` wholesale would discard the legitimate parts — the `quest_id`
timestamp, the recorded outcome, the difficulty clamp — and reproducing its destruction would be the
anti-pattern.

**D2 — the destruction count is refused, and the refusal is stated as a divergence (the authority
decision).** The legacy branch computes `lost = unit[2] - unit[3]` from a client blob and calls
`map_lose_item`. This line **does not implement that path**. The endpoint accepts the recorded outcome and
the quest id, derives what it legitimately can, and **leaves every placed row byte-identical**, proving it
with a before/after comparison over the whole `items` dict. Recording it as a *divergence* rather than
silently omitting it is what stops a later reader from believing parity was achieved.

**D3 — `complete_goal` is delivered as a no-op on purpose (the honesty decision).** It mutates nothing.
Writing a "completion" flag, a ledger, or a reward would invent a mechanic, and marking the branch
`complete` in any client state would be a lie. The line ships the branch's *recorded effect* — resolve the
committed title, mutate nothing — and the suite asserts the absence of any completion flag, so the claim is
mechanical rather than a promise.

**D4 — no bounds on `set_goals`, and the unbounded growth recorded (the parity decision).** A client-sent
goal id of `500` grows the list by 350 entries. The legacy server allows it. Adding a bound would make the
modern service *stricter* than the legacy server — a parity break in the unexamined direction — so the line
reproduces the absence and records it as a Server v1 / M13 gap, exactly as `building-move` and `expansion`
record their unvalidated surfaces.

**D5 — no membership test on `set_quest_var` (the parity decision, same reasoning).** The legacy branch
accepts any key; the source's own comment enumerates eight but enforces nothing. Inventing a closed set of
eight would reject keys the legacy server happily persisted. The line records the eight as **content** and
accepts what the client sends, while refusing the one key the legacy branch itself ignores
(`idSimpleChapter`) because that is a legacy behaviour, not an absence.

**D6 — the content inventory is reported and structurally unused (the non-invention decision).** Only `id`
and `title` are read; `reward` is uniformly `10` with zero consumers. A line that derived a quest reward
from `10` would fabricate a uniform payout that is not a payout at all. The line instead ships the measured
inventory and asserts **no delivered code identifier or computation is named after `reward`** — the same
mechanical "never used" pattern the research line used for `TYPE_AREA_51`.

**D7 — `unlockedQuestIndex` is reported, never written (the zero-consumer decision).** Zero legacy sites.
Following the `resurrectable` precedent, the field is projected as content and never consumed.

**D8 — the two type facts are reproduced rather than normalized (the fidelity decision).**
`collect_mission` writes a **string** where the corpus holds an **integer**, and `set_quest_var`
self-heals `currentQuestVars` from `None` to `{}`. Normalizing either would hide a real legacy shape
divergence; both are reproduced and asserted, and the projection **fails closed** on the corpus's `None`
rather than assuming a dict.

**D9 — `fast_forward` is recorded as a quest-state writer and never delivered (the cross-branch
decision).** Quest timing is client-writable for the same reason research timing is: nothing reads it. The
line records both write sites and delivers no fast-forward operation.

**D10 — `end_quest` completes the four-door correction (the cross-milestone decision).** Since
`end_quest` is one of `map_lose_item`'s two callers, delivering it means the quest path's reach into the
dead-hero ledger is a real, recorded relationship. The `godot-unit-behaviors` delta names it, so the ledger
capability and this one agree rather than describing the same subsystem differently.

**D11 — fixtures are captured (the evidence decision).** The corpus can exercise all six branches from
initial state, as it could for research. Unlike `unit-behaviors`, there is **no** corpus limitation to
record, so a missing fixture would be a gap in the line rather than a finding.

**D12 — evidence, claim limits, containment.** A deterministic `quests-report-v1` report recording the
projection, the six-branch inventory, the content inventory, the refused destruction, the client-writable
timing, and every non-claim, byte-identical across reruns. **No windowed capture**: nothing is rendered and
the corpus places no quest content. Containment: **loopback only**, both batteries plus the guard baseline,
the 3,258-entry hash manifest, and the content validator green in the final state.

## Risks / Trade-offs

- **The line is the most client-sent in the project, so most of its value is in the refusals.** Accepted and
  made explicit: a quest line that quietly reproduced a client-computed destruction count would be worse
  than no quest line at all.
- **Refusing `end_quest` means a player cannot lose units through the modern client.** That is the correct
  parity outcome for a v0 compatibility contract, and authoritative combat belongs to Server v1 / M13.
- **No reward means quest completion has no economic effect.** That is what the legacy server does.
- **`complete_goal` doing nothing may look like an unfinished feature.** D3 makes it a stated, asserted
  contract instead.
- **Six branches is a broad surface for one line.** Mitigated by the closed set: no seventh branch exists,
  and the content side needs no derivation.