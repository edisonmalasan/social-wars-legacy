# Design

## Context

The contract is established in `docs/legacy-unit-xp.md` (merged, `79d13ac`). What shapes the
approach here is four facts about the *existing* repository, not about the branch:

1. **A projection already exists and is already correct in substance.**
   `production_flow.gd::experience()` (`:865-885`) already returns `recorded` verbatim with
   `recorded_is_absent`, a constant `awarded: false`, and `award_source`. Its header comment
   (`:67-74`) already states the sharp reason. So this line **refines** a delivered surface; it
   does not add one. Adding a second projection would create two sources of truth for the same
   field.

2. **The shared capture harness hardcodes its seed.** `FRESH_PLAYER_SAVE` is a module constant
   (`capture_legacy_fixtures.py:98`) read inside `build_disposable` (`:237-255`), and **all 17**
   capture scripts call `build_disposable` with exactly **one positional argument**. A
   village-seeded capture is therefore impossible today without either touching 17 files or
   duplicating ~20 lines of containment discipline.

3. **No capture script in the repository has ever been seeded from a village save.** All 17
   seed `tests/saves/fresh-player.json`. So the fixture-harness assumptions downstream of the
   seed (containment groups, `pid` extraction, save-file naming) are only *proven* for that one
   document, and this line is the first to exercise them on another.

4. **`playerInfo.pid` does not equal the filename stem for 3 of the 8 village saves**
   (`GM30.json` → `100000030`, `GM31.json` → `100000031`, `initial.json` → `None`). The harness
   already reads the pid from the document (`:246`), which is the correct behaviour and the
   reason the third case fails loudly rather than silently.

## Goals / Non-Goals

**Goals:**

- Make the executed behaviour of `add_xp_unit` permanent, replayable, and independently
  checkable without a running legacy server.
- Make a legacy-poisoned bag **visible** to the delivered projection rather than readable as a
  number, without changing what the projection already guarantees.
- Replace the false "the corpus cannot exercise it" reason at every recorded location without
  weakening a single refusal.

**Non-Goals:**

- No endpoint, route, envelope, or client intent. An envelope module derives a request from an
  intent for a route; with no route there is no request, so an envelope would be a fabricated
  artifact.
- No award, threshold, unit level, or schedule, and no adoption of the committed per-unit
  experience field as one.
- No change to the level-reward refusal.
- No change to any existing compat expectation, no new compat route, and no change to
  `compat_service.py` or `compat_legacy.py`.
- No change to the rendered client, so no windowed capture.

## Decisions

### D1 — Refine `experience()` rather than add a projection

**Decision.** Add one field, `recorded_kind`, classifying what the recorded value *is*, leaving
`recorded`, `recorded_is_absent`, `awarded`, `award_source`, `award_implemented`, `contract`,
and `corpus_note` exactly as they are.

**Rationale.** The executed evidence establishes that the legacy server will persist a
**string** on the assign arm (`{}` → `{"xp": "5"}`), after which every later increment against
that row raises. The delivered projection reports that value verbatim and correctly declines to
coerce it — but a consumer reading `recorded` alone cannot distinguish `{"xp": "5"}` from
`{"xp": 5}` without re-deriving the kind itself, and every consumer would do it differently.
Reporting the kind once, in the layer that owns the field, is the smallest change that makes the
defect visible.

**Alternative rejected — coerce or reject non-integers.** The projection would then either
refuse a value the legacy server accepts (contradicting the already-delivered contract that a
recorded value is reported as content) or normalise it (destroying the very fact the evidence
established). Both lose information.

**Alternative rejected — a separate "row integrity" projection.** Two projections over one
`attr` bag would drift, and the project already found this failure mode once: `test_unit_collection`
pinned a whole-tree absence that `godot-stored-item-placement` falsified, resolved by an
**ownership claim** rather than a second reader. Same resolution here: one owner.

### D2 — Classification vocabulary is a closed, named set

**Decision.** `recorded_kind` is one of `absent`, `int`, `float`, `string`, `bool`, or `other`,
computed by a single named helper, and the suite pins the inventory of that helper so a future
kind cannot be added silently.

**Rationale.** A closed vocabulary is assertable; a free-text type name is not. `bool` is a
separate member because the executed evidence shows the legacy server stores `True` for a
client-sent `true` — in Python `True + 5` is `6`, so a boolean reaches the field as a genuine
experience value, and a projection that reported it as `int` would be right by accident and
wrong by reason.

**Alternative rejected — reuse `typeof()`/`type_string()`.** GDScript's own type names are
engine-versioned vocabulary, not this contract's, and `test_unit_production` already records a
lesson about trusting a helper it did not test: a `_code_only()` scan was passed a path instead
of a body and became vacuously true.

### D3 — One defaulted parameter, and a structural pin that it stays defaulted

**Decision.** `build_disposable(tmp_parent, seed_path=FRESH_PLAYER_SAVE)`. The new capture
passes `villages/AcidCaos.json` by keyword. **No existing call site is edited.**

**Rationale.** All 17 existing call sites pass one positional argument, so a defaulted second
parameter is provably non-breaking *today*. But "provably non-breaking today" is exactly the
claim that decays, so the new test module carries a **structural pin**: it walks every
`build_disposable(` call site in `apps/compat-api/` and fails if any passes a second argument,
which would mean some other capture had begun depending on a non-fresh seed and the
corpus-wide assumptions of those fixtures needed rechecking. This converts a one-line refactor
from a silent risk into a loud one.

**Alternative rejected — monkeypatching `capture_legacy_fixtures.FRESH_PLAYER_SAVE`.** Zero
diff to the shared file, but it makes the seed of a 17-script family depend on import order and
would silently change the seed of whichever script imported first. A capture harness whose seed
is mutable global state is the same class of defect as the legacy server's in-memory corpus
cache that corrupted the investigation's first twelve probes.

**Alternative rejected — duplicating `build_disposable` in the new script.** Two containment
implementations means containment is verified twice, once of them never again.

### D4 — `PYTHONUNBUFFERED` is set by the new capture only, not in the shared harness

**Decision.** The new capture script sets `PYTHONUNBUFFERED=1` in its own child environment.

**Rationale.** The legacy server's `print` lines are load-bearing evidence here — specifically
the `+5xp` versus `+5xp BOUGHT LEVEL UP -> 9` difference that makes the third argument's
display-only nature visible, and the `Soldier +-1000xp` line that shows the unclamped negative.
Under block buffering those lines are lost when the harness terminates the child. But
`child_environment()` is **shared**, and changing it would change the stdout log of all 17
captures. Since the fixture's contract is the **state transition** — request, status, body,
before, after, leaf set — and the printed lines are already recorded verbatim in
`docs/legacy-unit-xp.md` §4d, the new capture records them **in addition to** the state and
touches nothing shared.

**Alternative rejected — adding it to `child_environment()`.** It is arguably the correct fix
and it is deferred, because it would alter every existing capture's log and no existing fixture
currently needs it. Recorded as a follow-up rather than smuggled in.

### D5 — The fixture is the deliverable; a self-verifying integrity module is the guard

**Decision.** No compat envelope, no compat endpoint. Instead one new test module that asserts
the committed fixture is internally consistent forever: that each recorded changed-leaf set
equals the leaf diff recomputed from its own before/after states; that each recorded after-state
moves **exactly** the leaves it claims and no stored resource; that the manifest's digests
match the fixture bytes; and that the census the manifest records still matches a fresh
measurement over the committed content.

**Rationale.** Every prior line's fixture has been replayed **against an endpoint**. With no
endpoint there is nothing to replay against, so the meaningful guard is different: the fixture is
the evidence, and an evidence artefact nobody re-checks is a claim, not evidence. Recomputing
its own diffs offline is the strongest available check and needs no server.

**Anti-invention guard, and it is structural.** The same module pins the whole
`static`-function inventory of `compat_service.py` and asserts that **no** route answers a
unit-experience path and that **no** delivered service identifier is named after an award
function. As on every prior line, this guard counts as proven only once it has been **made to
fail by injection** and the file restored from a byte-identical copy.

### D6 — Correction is textual and enumerates its own sites

**Decision.** The five stale locations are corrected in place with the corpus figure retained and
labelled as a corpus fact, plus the `godot-unit-production` and `godot-building-xp` requirement
deltas. The hermetic suite carries a **tree scan** asserting that no client source states the
corpus-cannot-exercise reason for unit experience — so the sixth location cannot be added later
without the suite failing.

**Rationale.** The supersession of this claim already happened **once** and propagated only as
far as a code comment: `production_flow.gd:67-74` carries the sharp reason while
`AGENTS.md:704-705` and `README.md:2115-2116` still carry the old sentence, and the user-facing
note at `level_flow.gd:846-848` holds a *corrected* tutorial half beside a *stale* unit-XP half.
A one-time edit does not prevent a recurrence; a scan does.

**Alternative rejected — reword only the comment.** Leaves a reader-facing string and two prose
files asserting something false.

**Alternative rejected — delete the stale sentences.** They carry the *true* clause (the fresh
corpus really has zero such rows) inside the false conclusion. Deleting loses a true fact;
rewording keeps it labelled.

### D7 — The third argument's accepted-and-ignored rule is recorded, not implemented

**Decision.** The fixture records that the two-argument and three-argument forms produce
identical post-states and identical leaf sets while their printed output differs. **No consumer
is implemented**, because this line has no consumer.

**Rationale.** The spec requirement states what a *future* consumer of the contract must do
(accept and ignore, do not refuse), with the reason: refusing would reject a request the legacy
server accepts whose stored effect is nil. Recording the rule now costs one requirement and
avoids a later line re-deriving whether to refuse. Implementing it now would require an
endpoint, which D5 excludes.

## Risks / Trade-offs

- **A village-seeded capture is the first of its kind, so a downstream harness assumption
  could break in a way the fresh corpus never exposed.** → Mitigated by running the capture
  **at least three times consecutively** and requiring identical output, by asserting the
  containment digest before and after, and by recording the seed's digest in the manifest. If a
  later discovery invalidates the fixture, it is one committed directory to regenerate.

- **The classification helper could be made vacuously true by a bad test scan.** This exact
  defect occurred twice on this line's predecessor (`test_unit_production`'s
  `_code_only()` receiving a path, and desynchronising on an apostrophe). → Mitigated by
  asserting the scan finds the helper's own definition by name before asserting anything about
  its body, and by **injecting** a violation to confirm the guard fails.

- **Editing `AGENTS.md` and `README.md` risks touching unrelated lines in two very long
  documents.** → Mitigated by a targeted replacement of the exact stale sentence, verified by
  re-reading the surrounding block afterwards and by `git diff` showing a bounded hunk.

- **The tree scan for the stale reason could false-positive on the *new* correct text**, which
  legitimately mentions the corpus figure. → Mitigated by scanning for the **reason
  construction** ("because … cannot exercise"), not for the corpus figure, and by pinning the
  scan's expected hit count to zero so a change in either direction fails.

- **A committed fixture for a branch the client will never call could be read as an implicit
  promise to implement it.** → Mitigated by naming the refusal in the fixture README, in the
  report, in both modified capabilities, and in the new capability's Purpose, and by the
  compat-side structural guard asserting no route and no award helper exists.

## Migration Plan

Not applicable — no data migration, no route, no save-shape change, and nothing to roll back
beyond reverting the commit. The change is additive on the compat side and textual on the
documentation side.

## Open Questions

None that would change the specs, the approach, or the task breakdown. Two facts are recorded
as **derived-provisional** and are not deferred questions, because both are already decided by
measurement:

- **The choice of `AcidCaos.json` as the disposable seed.** Derived from three measurements
  rather than preference: it is the smallest of the five committed saves carrying the field by
  placed-row count (319 against 569 / 367 / 549 / 576), it carries 36 rows **with** the field —
  ample for a fixture — and 283 without it, including 12 unit rows with an empty bag and 271
  building rows, so both arms and both row kinds are exercisable from one document. Any other of
  the five would also work; the choice is recorded so a rerun reproduces the committed bytes.
- **The report shape.** The census tables are generated from the projection module's own data
  and from the fixture's own recorded manifest, following the precedent set by
  `resources-report-v1`, so they cannot drift from the code they document.