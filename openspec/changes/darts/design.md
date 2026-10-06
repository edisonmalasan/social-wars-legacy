# Design

## Context

See `proposal.md` — Why. The measured facts this design has to satisfy are in
`docs/legacy-m11-darts.md` (PR #315), and the behaviour contract is in
`specs/godot-darts/spec.md` and `specs/godot-social-state/spec.md`. What follows is
only the shape of the implementation and the choices that were genuinely open.

Three constraints from the established house pattern shape everything:

- **A refusal that is only prose cannot fail.** Every prior M8–M11 line carries its
  refusals as structural guards proven by injection, and two of those lines
  (`godot-mission-vocabulary`, `godot-social-state`) learned that a guard which never
  fires is decoration.
- **The census is re-derived on every run.** `godot-social-state`'s design D2
  re-derives its census each run, and that guard earned its keep on the first real
  legacy edit it met — it is what caught the 13→12 error.
- **The instrument must be shown to measure what it claims.** Nine instrument faults
  were found and fixed across the two previous lines, every one by a self-check
  rather than by inspection.

## Goals / Non-Goals

**Goals**

- Deliver the six darts fields, the three darts transitions, the server-derived
  premium duration with its clamp and both arms, and the week-reset predicate.
- Prove "nothing is charged" non-tautologically, by comparing the **complete**
  stored resource set on every successful action.
- Correct the two mis-filed fields in `godot-social-state` and hand them off
  without orphaning them.
- Re-measure every figure this line depends on on each run, so a legacy edit fails
  the suite instead of silently contradicting it.

**Non-Goals**

- No rendering, no darts UI, no premium purchase screen, no countdown, no
  eligibility window, no cooldown, and no "the free shot is available again"
  affordance.
- No claim about the Flash client. Whether it presented darts or a premium flow is
  unverifiable from the preserved oracle.
- No normalization work: `darts_items` and `PREMIUM_ACCOUNTS` are read, never
  transformed.
- No work on `reset_stuff`'s day-boundary `numTradesDone` reset, which shares the
  function but is not darts state. It is named in the investigation so a later line
  does not assume the function touches darts alone.
- **No schema validation and no eligibility gate on the premium purchase.** The
  preserved server has none, and adding one would be a Server v1 / M13 concern.

## Decisions

### D1 — One capability, two surfaces, because they share the committed-content read path but nothing else

`godot-darts` covers darts state *and* premium purchase rather than two
capabilities. The two surfaces share the only thing that makes either derivable: a
read of a committed normalization output through the registry. Splitting them would
mean two modules reading the same registry for the same reason, and would split the
one requirement that carries this line's headline finding — that a committed price
has zero consumers — away from the code that proves it.

**Alternative rejected:** a separate `godot-premium` capability. Rejected because the
finding spans both halves: premium's duration is server-derived *because* the darts
half established that this is the one M11 surface where the server computes a value.

### D2 — Split the module into domain files rather than one flat script

`godot-social-state` is a single flat script with top-level consts and one inner
class. This line has more moving parts — a projection, a purchase derivation, a week
predicate, and three separate refusal families — so it uses a directory with one
small script per concern, matching the M7/M9 flow-module convention.

**The trap recorded from the previous line, and the reason for this decision:** an
inner class named identically to the preloaded script makes every static call resolve
to the inner class, and `Projection` is a built-in Godot type. So this line uses
flat scripts with distinct names, no inner class shadowing a preload, and no
built-in type as a class name.

### D3 — Deliver the shot index, refuse the shot outcome

The recorded shoot transition reads two client arguments: `index` and `won_extra`.
They are not the same kind of thing, and treating them alike would be wrong in both
directions.

`index` is **intent** — which target the player aimed at. The preserved server
accepts it, records it, and derives nothing about it. Delivering it reproduces the
recorded transition without asserting an outcome.

`won_extra` is an **asserted result**. The preserved server trusts a client
truthiness to set the got-extra flag, and verifies no win: nothing in the eleven
modules checks whether the target existed, was hittable, or was won. Reproducing that
is the `apply_client_state` pattern `AGENTS.md` names as Bad.

So the got-extra flag is **refused**, the refusal is recorded as a **divergence**
rather than as parity, and the refusal is visible in the response rather than silent.
**Alternative rejected:** deliver both and mark the outcome unverified. Rejected
because it would make the flag's presence in a save indistinguishable from a
server-verified win, which is exactly the untrusted-delta shape this project
refuses everywhere else.

### D10 — Resolving the contract's "refusing to trust the shot index": accepted as intent, trusted about nothing

`docs/legacy-m11-darts.md` §8 recommends refusing to *trust* "the seed, the shot
index, `won_extra`, the unbounded list, and the committed price". That phrase admits
two readings and the choice is consequential, so it is resolved here explicitly
rather than by preference.

- **Reading A — refuse the shot outright:** deliver only reset, free-grant, and
  premium; accept no shot at all.
- **Reading B — accept the shot but trust nothing about it:** record the index as
  client-sent intent, derive nothing from it, bound nothing with it, and refuse the
  outcome.

**Reading B is chosen.** The precedent is `godot-building-move`, which delivered a
`move` taking client-sent `x`/`y` with no occupancy, bounds, or terrain check, and
recorded those absences as Server v1 / M13 gaps rather than refusing the command.
`AGENTS.md`'s own "Good" example is `buy_building(player_id, building_id, x, y)` —
client coordinates, unvalidated. The shot index is the same kind of value: *which
thing the player acted on*. What `AGENTS.md` forbids is trusting a client's
**deltas and outcomes** — resource, XP, HP, result — and `won_extra` is exactly that
while the index is not.

Reading A would also make the line's own recorded corpus facts untestable: a corpus
document records `[18, 17]` and another records the out-of-schedule `[0]`, and
"refuse the shot" leaves those documents with nothing to reproduce.

**The seed is the opposite case and is refused in full.** `darts_reset` writes a
client `seed` into the save and no preserved branch ever reads it back, so there is
no intent to reconstruct — only a value to store. It is delivered as a recorded
client-sent write with no semantics derived, and the delivered code derives nothing
from it, which is a stronger and separately-guarded claim than the index's.

### D4 — Refuse to grow the balloon list without a recorded bound, and refuse to invent one

The recorded branch appends whenever the index is absent, with no length bound and no
membership test against the committed 27-entry schedule. A corpus document even
records a shot index of `0`, which is absent from the schedule (`1..27`), and the
preserved server accepted it.

Two rules could be invented here — a maximum shot count, and a schedule-membership
test — and **both would be inventions**: neither exists in the preserved server, and
the corpus proves the absent check is not merely unimplemented but *not enforced*
against an out-of-schedule value. So neither is delivered. The out-of-schedule corpus
shot is **reported**, because it is the evidence that makes the absence real rather
than assumed.

**Alternative rejected:** clamp the list to the schedule size. Rejected: the preserved
server does not, and a clamp would silently drop a shot the legacy server recorded.

### D5 — Deliver the week-reset as a predicate, never as a mutation the player triggers

`reset_stuff` is reached from the player-info path, not a command, and writes the
instant to `0` rather than to the server clock. So it is delivered as a pure
predicate over (recorded instant, server clock, recorded constants) plus its
recorded existence guard, with no route that performs the write. The source's own
intent comment — that the offset exists because timestamp zero is a Thursday and the
reset should land on Monday — is reported **as a comment**, not as a derived weekday
rule.

**Alternative rejected:** implement the reset as an action. Rejected: it is not an
action in the preserved server, and routing it as one would create a player-triggered
reset the legacy never had.

### D6 — The two-part proof for premium is "instant moved by the derived duration AND every stored resource unchanged"

Because the committed price has zero consumers, "nothing is charged" is the line's
central claim and must not be vacuous. Comparing the complete stored resource set —
all seven slots, not a subset — on every successful purchase makes the claim
non-tautological, exactly as `godot-rewards`'s four-part proof does for its own
no-grant claim. The derived duration is checked against the derived value, not
against a recorded snapshot, so a wrong derivation cannot pass.

**That proof establishes a refusal, not parity, and the distinction is recorded
rather than blurred.** `engine.apply_resources` (`engine.py:251-271`) applies a
**client-sent** eight-slot vector through `max(current + delta, 0)` *before* the
dispatcher runs, so a legacy client could pair a debit with a premium purchase and
the branch itself would still charge nothing from committed content. The preserved
server's own comment at `:252` says as much — it reads the negative results as
cheat detection. So "nothing is charged" is true of the **committed price** and
false as a statement about every legacy path; the modern endpoint ignores any
client-sent vector outright, which is the untrusted-delta refusal this project has
applied since M7, and the divergence is recorded rather than reproduced.

The clamp is also why the seven-slot comparison must be **complete**: the resource
vocabulary the service exposes is seven (`xp, gold, wood, oil, steel, cash, mana`),
while the vector is eight (it carries an `unknown` slot `resource[0]` that is read
and discarded). Comparing a subset would leave room to smuggle a delta through the
uncompared slots.

### D7 — Derive the duration from the **normalized** package through the registry, never from `config/main.json`

`get_game_config.py:181-189` reads `__game_config["globals"]["PREMIUM_ACCOUNTS"]`
from the served config. The modern client must not read legacy config, so the
derivation reads the normalized `globals` output through the registry's public
`get_entry(domain, legacy_id)` accessor — verified to resolve, since the normalized
entry carries `legacy_id: "PREMIUM_ACCOUNTS"` and a `value` of six
`{time, price}` objects. **This is a content-ownership boundary, not a
convenience:** the schedule stays owned by `globals-tuning-normalization` and
`darts-schedule-normalization`, and the ownership is asserted so a rename cannot
orphan it.

The committed durations are `360, 180, 30, 7, 3, 1` and the branch multiplies by
`86400`, so `time` is in **days** and the record is preserved in that unit rather
than converted to seconds at the content boundary. The prices beside them are
`800, 450, 80, 40, 20, 8` — descending with duration, which is what makes the
zero-consumer finding cost something rather than nothing: the schedule is
well-formed and was obviously meant to be charged.

**Alternative rejected:** hardcode the six durations in the client. Rejected: it
would fork the content package and make the "derived from committed content" claim
unfalsifiable.

### D8 — Correct `godot-social-state` rather than leaving a known-wrong record

`social_state.gd` currently records `timeStampEndPremium` as `written_by:
["buy_premium_account"]` with the note *"a single instant write"*. Both halves are
wrong: the branch writes the instant **twice** (`:619` and `:622`, one per arm), and
its value is **server-derived** from the committed schedule, not client-sent — which
matters because the capability's own requirement is titled *"The one real social-state
writer is recorded with its **client-sent value**"*.

Leaving it would ship a delivered spec asserting something the measurement
contradicts, which is the defect class this project keeps finding. So the record is
corrected and both fields are declared foreign to that capability.

**The hand-off is verified, not asserted.** `godot-social-state` will check that the
named owning capability exists and really projects those fields, so this is a
hand-off rather than an orphan — the same treatment `godot-unit-collection` received
when it handed the stored-item placement step over.

### D9 — Re-derive every dependent figure on each run

The premium schedule's entry count, the durations, the presence of a price beside
each duration, the darts field sites, the week constants, and the corpus counts are
all re-derived per run. The measurement in the investigation found that a whole-file
occurrence count credits a **commented-out** line as a writer — `command.py:917` is
exactly that — so the census must distinguish comments from code, and must **preserve
string contents**, because every persistence field is reached through a dict
subscript and blanking strings reports zero everywhere.

That last point is a hazard for every committed census in this project. The
delivered `godot-social-state` suite was checked against it and is **sound** — it
runs its quoted-count over raw source by design, with a comment naming the hazard —
and that check is recorded in the investigation rather than left as reassurance.

## Risks / Trade-offs

- **[The refusal to set the got-extra flag diverges from the preserved server]** →
  Mitigated by recording it as a divergence in the response, the report, and the
  claim limits, never as parity. A replay test asserts the flag does not move.
- **[Refusing the list bound means a client can still grow the list]** → That is the
  preserved behavior and it is recorded as a Server v1 / M13 gap. The absence is
  reported with the corpus's out-of-schedule shot as evidence that no check exists.
- **[A committed price with zero consumers is the kind of fact that gets "fixed"]
  later by someone who reads it as an oversight]** → The spec requires the price be
  reported with its zero-consumer measurement, and requires that no capability name,
  identifier, or response field imply a payment was made.
- **[Modifying a delivered capability risks breaking its 361-check suite]** → The
  correction is additive to the requirement text and the field record; the foreign
  fields stay present with corrected descriptions rather than being deleted, so the
  suite's coverage of all nineteen measured fields is preserved.
- **[The extend arm has no corpus coverage]** → Recorded as crafted input in the
  spec, the report, and the claim limits; no fixture claims to have exercised it.
- **[A re-derivation guard could fail on an unrelated legacy edit]** → Accepted as the
  intended behaviour: a silent contradiction is worse than a failing suite.
