# Design

## Context

See `proposal.md` — Why, and the committed investigation record
`docs/legacy-xp-basics.md`. This is the **eleventh and final** M7 deliver line.

### Established (from the investigation record)

- `level_up(new_level)` (`command.py:81-85`) sets `map["level"] = new_level` with **no
  range check and no XP validation**, and answers `{"result":"success"}`.
- `add_xp_unit(item_index, xp_gain, level?)` creates or increments `attr["xp"]` on an
  item row; the optional third argument changes only a log line; **0 of the 40 placed
  corpus rows carry `attr["xp"]`**, and the fresh save has no unit placements.
- **Nothing in the legacy server reads the committed `levels` schedule** — zero
  references across `command.py`, `engine.py`, `sessions.py`, `server.py`,
  `constants.py`. The server neither derives a level from experience nor validates one
  against the curve.
- `maps[0].xp` is the player's experience (the 8-slot vector's **slot 1**, written by
  `engine.apply_resources`) and the only experience the server maintains;
  `maps[0].level` is written **only** by `level_up`. Corpus: `xp 4`, `level 1`.
- The curve: 100 entries, `exp_required` **strictly increasing** with no duplicates and
  no non-positive gap (`0, 40, 60, 100, 200, 350, 550, 800, …` to `2016089205`);
  `reward_type` in `{s, w, g, c}` — the same letter vocabulary as `items[].costs`, not
  the server's resource names — and **nothing consumes it**; `reward_amount` takes
  exactly three values (`1`, `50`, `250`) and is likewise unconsumed; `name` is **not**
  distinct (44 names across 100 entries), so it is a label, not an identifier.
- The readout already displays both `level` and `xp` as bare values, since the
  resources line placed them in the summary group.

## Decisions

**D1 — the curve is 1-based, the conversion lives in exactly one named place, and the
interpretation is derived-provisional (derived; the rejected alternative is actively
contradicted).** Stored level *n* is `levels[n - 1]`. The evidence: at the corpus's
`xp 4`, the 0-based reading implies level 0 while the save records level 1 — a direct
contradiction — whereas the 1-based reading maps level 1 to `levels[0]` (`"Slave"`,
`exp_required` 0) and `4 >= 0` holds. **Guessing 0-based would shift every level by one,
and the error would be invisible until a player saw the wrong level name**, which is why
this decision is written down rather than absorbed into an index expression. The
conversion is therefore a single documented function used by the client model, the
endpoint, the tests, and the report, with its boundary cases covered — `xp` below the
first threshold, exactly on a threshold, between thresholds, and above the last — plus
the corpus's own `xp 4 / level 1` pair as a regression fixture. The provenance section of
every artifact records this as derived-provisional **with the rejected 0-based reading
stated**, so a later change with better evidence revises one function rather than
auditing the codebase.

**D2 — the stored level is unverified, and disagreement is reported, never smoothed
(established asymmetry; reporting derived).** The server writes `level` from a
client-supplied integer with no validation, so the stored value is **not** evidence of
anything the curve implies. Two distinct facts therefore exist and must not be conflated:
the **derived** level, which is what the committed curve says the stored experience
implies, and the **stored** level, which is what the save records. When they agree, the
readout says so. When they disagree, the readout **states the disagreement explicitly**
— both values and the experience that separates them — rather than preferring one
silently or normalising the save. This is a deliberate departure from the "apply only the
authoritative response" rule of the other modes, and the reason is that here there is no
authoritative level to apply: the server has no opinion beyond echoing a client integer.

**D3 — the level-up target is derived server-side; the client never supplies it
(established intent-only discipline).** `POST /v0/level_up` accepts only
`{user_id}`. The endpoint reads the stored experience, derives the level the committed
curve implies, and refuses the request unless that is the only outcome consistent with
the stored experience. A client-supplied `level` key is **ignored**, exactly as the
collect and expand endpoints ignore client-supplied amounts and prices — this is the
line's core invariant, and a test asserts that sending one changes nothing. This
directly closes the legacy hole where any client could set level 99.

**D4 — refusals are fail-closed and precede the dispatcher.** The endpoint refuses with
`level_mismatch` when the stored level already equals the derived level (there is
nothing to do, and executing `level_up` would rewrite an identical value), and with
`xp_below_threshold` when the stored experience cannot reach the next level at all. Both
return **before** the dispatcher runs, so the corpus is byte-identical on every error
path — the same discipline as every delivered line.

**D5 — the post-state proof checks the level and the absence of resource movement.**
After execution the endpoint requires that the stored level equals the derived level and
that **every** stored resource is **unchanged**. The second half matters because
`level_up` is dispatched with a client-sent vector like every other command, and a
non-zero vector would silently move a balance: proving that *nothing* moved is what
distinguishes a correct level-up from a resource-minting exploit wearing its clothes.
Together with the collect line's and expand line's value-level proofs, this completes
the family's proof set: a value moved by exactly the derived delta, a value moved by
exactly the derived debit, and here a value proven **not** to move at all.

**D6 — an unaffordable next level is reported, never skipped.** The curve's levels
carry `reward_type`/`reward_amount` that nothing consumes, so no reward is paid and no
gate is invented; the readout shows the next level's requirement and the remaining
experience as information only.

**D7 — no tuning, no rewards, no unit XP, no tutorial.** The committed `exp_required`
values are preserved verbatim; `reward_type`/`reward_amount` are **refused rather than
invented**, exactly as the expansion `neighbors`/`inventory_qte` requirements were;
`add_xp_unit` is out of scope because the corpus cannot exercise it; and
`complete_tutorial` is a separate progression system.

**D8 — evidence, claim limits, and containment.** A windowed fake-API capture of the
level readout plus a headless deterministic `xp-report-v1` report recording the curve
facts used (entry count, the first thresholds, the corpus's own case), the derived and
stored levels, the disagreement state, the input digests, the request counts, the
provenance split naming D1 as derived-provisional with its rejected alternative, and the
non-claims — byte-identical across reruns. Containment carries forward unchanged: no new
packages, loopback only, both batteries plus the guard baseline and the 3,258-entry hash
manifest green in the final state, and the orchestrator-run integration review as the
fallback for the unavailable dedicated verification workflow.

## Risks / Trade-offs

- **A wrong index base would shift every level in the game** → mitigated by D1's single
  named conversion, its boundary coverage, the corpus regression fixture, and the
  contradiction recorded against the rejected alternative. This is the line's dominant
  risk and the reason the decision is documented rather than inlined.
- **Disagreement reporting is unusual next to the other modes' authoritative apply** →
  mitigated by D2's stated reason: with `level_up` echoing a client integer, there is no
  authoritative level to prefer, so hiding the conflict would be inventing authority.
- **A refused level-up could be mistaken for a bug** → mitigated by explicit refusal
  reasons naming both the derived and the stored level, so the failure explains itself.
- **The zero-resource-movement proof could be seen as over-strict** → it is the correct
  invariant: a level change moves no resource, and proving it is what forecloses a
  vector-smuggling exploit.
- **An eighth mode on one surface** → modes stay mutually exclusive, each keeps its own
  state, and all ten delivered suites must stay green, so a regression surfaces in an
  existing suite rather than hiding behind the new one.