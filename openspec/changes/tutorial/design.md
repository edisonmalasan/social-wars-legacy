# Design

## Context

The legacy tutorial is one branch. `command.py:60-66` reads `args[0]` into a local,
prints it, and on `tutorial_step >= 25 or tutorial_step == 15` writes
`save["playerInfo"]["completed_tutorial"] = 1`. Nothing else in any of the eleven
root modules names the tutorial. See `docs/legacy-m9-tutorial.md` (PR #264) for
the measurements; this document records only the choices they force.

Four constraints shape every decision below:

1. **`completed_tutorial` is write-only.** One occurrence in the whole server, the
   write. Zero readers. So nothing in the legacy server behaves differently once
   the flag is `1`, and there is no legacy evidence for any *other* tutorial
   behaviour to reproduce.
2. **`tutorial_step` is never persisted.** A tutorial position is therefore
   unrepresentable in the legacy save shape. This is the single hardest boundary
   in the line, because "tutorial progress" is exactly the kind of feature a
   reader would expect to exist.
3. **The command is a resource-minting vector.** `apply_resources` runs at
   `command.py:40`, *before* dispatch, so every tutorial command applies a
   client-sent 8-slot vector. One captured request moved all seven stored
   resources *and* the flag.
4. **The gate is arithmetic on a client-sent value with a nine-value hole**, and
   three input shapes are answered with an unhandled 500.

The compatibility layer's established shape (from `research` and `quests`) is:
a standalone envelope module holding the derivation, an endpoint in
`compat_service.py` that slices nothing out of context, executed-legacy parity
tests over a captured fixture, a typed Godot projection with a hermetic suite, and
a live phase as the only guard against wire drift.

## Goals / Non-Goals

**Goals:**

- Deliver the one executed transition the corpus can reach, with a captured
  fixture, and refuse everything the legacy server cannot answer.
- Make the gate a single named value per layer, so the client and the service
  cannot disagree about what "step 16" means.
- Keep the proof honest: every action proves no stored resource moved, and that
  proof is anchored to a transaction where every resource *did* move.

**Non-Goals:**

- Any tutorial content, schedule, step list, dialogue, or reward. Zero is
  committed; inventing any would be invention, not reconstruction.
- Any stored step, resume position, progress ratio, or remaining time.
- An un-complete path, and any reader of the flag.
- Closing the gate's missing bounds. That is Server v1 / M13's decision.
- Displaying tutorial progress. Nothing is rendered in this line, so no windowed
  capture and no pixel parity are claimed.

## Decisions

### 1. The three 500-raising shapes are refused, not reproduced

`"15"`, a missing step, and `null` each raise inside the legacy branch and escape
as an unhandled Flask 500. Three options:

- **Reproduce the 500.** Rejected: it is a crash, not a behaviour, and it would
  make the endpoint's contract untestable.
- **Silently coerce** (treat a non-numeric step as `0`, so it declines). Rejected:
  it invents a value the client never sent and hides the malformed request.
- **Refuse with a named code, an empty payload, and no state change.** Chosen.

The divergence is confined to *response shape* and recorded as such. For every
step the legacy server **accepts**, the state transition is identical, which is
the claim that actually matters for parity. Note the one case where the two
readings could differ: legacy treats a JSON `true` as `True`, which satisfies
neither arm, so it declines. Refusing `true` as a non-integer also leaves state
unchanged, so the state outcomes agree and only the response differs — the same
confinement as above.

Executed evidence supports refusing rather than emulating: a raising step was
measured to change **zero** leaves even with a full client ladder attached, so
the legacy crash discards the already-applied vector rather than persisting it.
Emulating a crash that is already safe would add a failure mode, not parity.

### 2. The client sends a step; the server derives completion

The step is legitimate *intent* — "I reached step N" — so it is accepted. What is
refused is any client-supplied **outcome**, stored flag, or resource vector. The
alternative designs were both rejected:

- **Have the client compute completion and send a boolean.** Rejected outright:
  that is the anti-pattern `AGENTS.md` names as "Bad", and it would make the gate
  client-controlled.
- **Reject the step entirely and let the server track progress.** Impossible: the
  legacy save has no step, so the server has nothing to track. Inventing a stored
  step would change the save shape, which is out of scope and unevidenced.

### 3. The gate lives in exactly one named function per layer

The level-curve precedent set by `godot-building-xp` is followed directly: a named
gate predicate with a named inverse in the envelope module, and a named mirror in
the Godot flow module, with the hermetic suite asserting both agree across the
whole input table — rather than `town.gd` re-deriving an index.

The boundary table itself is already pinned by
`tools/protocol-replay/test_protocol_replay.py:173-179`, which covers steps 14,
15, 24, 25, 26, and -1. That test runs against a **stub oracle inside the replay
harness**, so it is not an executed-legacy oracle. The new work therefore
*references* it and adds the executed fixture rather than claiming the boundary
table as new, and the tutorial suite is pointed at it explicitly so the two
cannot drift into disagreeing.

### 4. The no-resource-moved proof is anchored to a captured minting transaction

The research and quests lines both arrived at this proof form independently. The
tutorial line has the strongest anchor of the three, because a captured legacy
transaction exists in which one tutorial request moved **all seven** stored
resources alongside the flag. So the endpoint's post-execution check — that every
stored resource is unchanged — is non-tautological in a way that can be *pointed
at*.

The fixture records the minting transaction as a second captured case, so the
suite can assert both directions: that the endpoint moves nothing, and that the
legacy server could move everything on the same command.

### 5. The hermetic suite asserts it builds no request body

The quests line learned this the hard way: 1223 hermetic checks passed while the
live phase failed five separate times, because an offline suite that builds its
own envelope cannot see wire drift. The tutorial hermetic suite therefore asserts
it constructs no request body at all, and records why. The guard for that class
is the live phase — which is a single phase, and is recorded as such.

### 6. The flag is read from `playerInfo`, and the projection reports no map field

The legacy flag lives in the save-level `playerInfo` record, which `maps[0]` does
not contain at all. Every earlier delivered line's shape was a map-scoped record,
so this is the first write delivered on a previous line to target a save-level
field. The projection reads it from `playerInfo` and explicitly reports **no**
`playerInfo` field as belonging to a map, so the structural difference is visible
in the report rather than implied.

`get_player_info.py:15` hands the whole `playerInfo` dict to the client, so the
flag does reach the client — by wholesale inclusion, not by any server-side naming
of it. The projection's fail-closed path is therefore an absent or wrongly-typed
`playerInfo` object, not a missing map key.

## Risks / Trade-offs

- **The refusal set diverges from the legacy response on three inputs.** → The
  divergence is written into the capability spec, confined to failure handling,
  and the state outcomes are shown to agree. Accepted deliberately.
- **The gate is reproduced with its missing bounds, so a client can send any
  integer.** → Recorded as a Server v1 / M13 gap and named in the spec, rather
  than silently closed; closing it would invent a bound with no evidence.
- **Wire drift can only be caught by one live phase.** → The hermetic suite
  asserts it builds no body and records why; the single-phase guard is stated in
  the spec's claim limits rather than presented as comprehensive.
- **A projection with one field could drift toward becoming a progress display.**
  → The absence requirements forbid any step, ratio, remaining time, or
  completion, and the anti-invention guard pins the module's whole static-function
  inventory so a new helper cannot be added unnoticed.
- **Parity rests on one transaction against one corpus.** → Stated as the claim
  limit; no progressed-player save exists with the flag at any other value, and
  none can (see Context, constraint 2).

## Migration Plan

None. This line adds an endpoint, a projection module, a fixture, and a spec. It
changes no legacy file, no save shape, no content package, and no existing
endpoint's behaviour, so there is nothing to migrate and nothing to roll back
beyond reverting the commit.

## Open Questions

None. Every unknown that would change the specs, the approach, or the task
breakdown was resolved by the committed investigation before this document was
written, and the ones that remain — what the Flash client counts as a step, how
it renders progress, what the gate bounds *should* be — are recorded claim limits
and Server v1 / M13 questions rather than deferrable design decisions.