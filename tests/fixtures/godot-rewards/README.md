# `godot-rewards` — executed-legacy reward-cursor fixture

Executed-legacy evidence for the **two** preserved reward branches, recorded
against one disposable copy of one committed village document and **one** legacy
server:

| branch | preserved source | what it writes |
| --- | --- | --- |
| `weekly_reward` | `command.py:345-363` | `privateState.weeklyRewardIndex`, `privateState.timeStampMondayBonus` |
| `win_daily_bonus` | `command.py:444-463` | `privateState.bonusNextId`, `privateState.timestampLastBonus` |

Change: `2026-10-05-rewards`, task group 1 (fixture capture) and task group 2
(the Compatibility API envelope and `/v0/reward` route).

## Capture command and exit code

```bash
python -B apps/compat-api/capture_rewards_fixture.py
```

Observed exit code **0**, re-runnable, containment identical before and after on
every observed run. The capture stages the whole fixture **outside** the working
tree and publishes `steps/` and `capture-manifest.json` only after every check
has passed, so a failed run writes nothing into the repository. `README.md` is
hand-authored and is deliberately **not** replaced by a run: it carries the
measured inventory figures, the containment table, and the claim limits, none of
which any run can regenerate. (`capture_unit_xp_fixture.py` established that
scope; this capture's first draft replaced the whole directory and silently
deleted its own README, which is recorded here rather than quietly fixed.)

No Flash, Ruffle, ActionScript, or browser executes in the capture or in any
check over this fixture. The legacy server is started as a child process on
loopback to `127.0.0.1:5055`, and the capture refuses to start if that port is
already in use.

## Inventory

**48 capture-output files, 1,816,177 bytes** in LF-normalised form, **1,774 KB**.

The byte total is a **floor with a 512-byte ceiling**, not an exact figure, and
the bound is stated here because the branches stamp the wall clock
unconditionally: every recorded instant is a fresh ten-digit number, so the
serialized total drifts by a few tens of bytes between runs of an identical
capture — measured, 1,816,142 and 1,816,177 on two consecutive runs, 35 bytes
apart. The file count, by contrast, is exact.

The byte count is LF-normalised, not `st_size`. This repository sets
`core.autocrlf=true` with no `.gitattributes` entry for `tests/fixtures/**`, so a
CRLF checkout holds the same committed content in more bytes with nothing
changed; a guard measured with `st_size` would be a line-ending detector. That
defect was found and fixed once in this project (PR #280) and is not
reintroduced here — every figure below and in `test_rewards_parity.py` is
counted over CRLF-folded bytes.

`README.md` is itself a file in the directory it describes, which is the
fixed-point problem: **it cannot state its own byte count.** The inventory above
therefore excludes it, and `test_rewards_parity.py` asserts exactly that
convention — the capture-output file count, the capture-output byte total, and the
directory total, which must exceed the first by exactly one. So the directory
holds 49 files.

Sixteen of the 48 are state documents: a `before.json` and an `after.json` for
each of the seven transactions and for the one login step.

## Seed

`villages/Neutral.json`, digest `652cf19874f0b8d45cf35050192f2082ad361baaf7cb8244e8c7145cb213af22`
(committed blob form, CRLF folded). The pid is read from the save's own
`playerInfo.pid`, **never** from the filename stem: three of the eight committed
village saves disagree with their own stem (`General_Mike_30.json`,
`General_Mike_31.json`, `initial.json`), and for this particular seed the two do
happen to agree.

| property | value |
| --- | --- |
| placed rows | 549 |
| `boughtUnits` length | 135 |
| `maps[0].store` | `{}` — empty, which is the only reason a storage grant is visible at all |
| weekly cursor / instant | 3 / 1686569823 |
| daily cursor / instant | 2 / 1688653422 |
| stored resource slots | 8 (`xp`, `gold`, `wood`, `oil`, `steel`, `cash`, `mana`, `energy`) |

The seed's weekly cursor of 3 is the whole reason this document was chosen: its
successor lands on position **4**, which the three-entry weekly schedule cannot
answer. `villages/Nerri.json` at 2 would land on 3 — also unanswerable, but the
smaller demonstration.

**Nothing is written into the committed seed.** The capture reads it, copies it
verbatim into a disposable, asserts the copy's digest equals the source's, asserts
the source's digest is unchanged after the run, and contains itself entirely.
`test_rewards_parity.py` asserts there is no write-shaped call anywhere in the
capture whose first argument is the seed constant.

## One server, seven transactions, one interleaved sequence

`sessions.load_saves()` caches the corpus in a module global **at import time**,
so a running server never re-reads the seed file: restoring the seed between steps
leaves the in-memory corpus already mutated and silently produces different
results. So this capture runs **one** server and **one** disposable for the whole
sequence, and every step runs against its predecessor's recorded state.

One server per transaction was rejected rather than merely avoided. The recorded
cursors are the point of this fixture, and step 6's recorded before (4) is only
reachable if step 5 really advanced the cursor from 3.

| # | step | command | arguments sent | cursor after | leaves moved | parity |
| --- | --- | --- | --- | --- | --- | --- |
| — | `login_post` | — | — | — | **0** | neutral, asserted byte-identical |
| 1 | `txn_weekly_short_arm_grants_nothing` | `weekly_reward` | `[]` | 3 → 4 | 2 | parity |
| 2 | `txn_weekly_long_arm_appends_an_absent_unit` | `weekly_reward` | `[600, 1198, 58, 47, 1]` | 4 → 0 | 9 | **divergence** |
| 3 | `txn_weekly_long_arm_deduplicates_a_present_unit` | `weekly_reward` | `[601, 1055, 58, 47, 1]` | 0 → 1 | 8 | **divergence** |
| 4 | `txn_daily_short_arm_grants_nothing` | `win_daily_bonus` | `[0, 2]` | 2 → 3 | 2 | parity |
| 5 | `txn_daily_granting_arm_lands_in_storage` | `win_daily_bonus` | `[1198, 3]` | 3 → 4 | 3 | **divergence** |
| 6 | `txn_daily_oversized_next_id_moves_the_cursor_backwards` | `win_daily_bonus` | `[0, 99]` | 4 → **1** | 2 | **divergence** |
| 7 | `txn_daily_after_the_backwards_move` | `win_daily_bonus` | `[0, 1]` | 1 → 2 | 2 | parity |

Ladders, read off the recorded transitions rather than off the summary columns:
weekly **4 → 0 → 1**, daily **3 → 4 → 1 → 2**. The daily 4 → 1 is a **backwards**
move.

Every argument list above is **crafted and client-supplied**. The Flash client was
never executed. The weekly branch reads zero or five arguments and tests only the
*count*; the daily branch reads an item and a next id and validates neither.

## What the fixture establishes

1. **The short weekly arm grants nothing.** Zero arguments take the `else` arm:
   the branch prints `Won resources`, stamps the instant, and advances the cursor,
   while its whole-document leaf diff is **exactly two paths** — the cursor and
   the stamp. Nothing anywhere else in a 549-row save moved. This is the clean
   demonstration in this line.
2. **The weekly arm selects granting vs. not-granting on the client's argument
   count** (`command.py:346` tests `len(args) > 4`). The same command with five
   arguments places a row; with four it places nothing.
3. **The long weekly arm places a row** (549 → 550) with the client-sent item at
   the client-sent index, cell, and player team, and every pre-existing row
   byte-identical.
4. **Both halves of the deduplicating helper (`engine.bought_unit_add`,
   `engine.py:86-89`) are executed, not cited.** Step 2 appends to the unit list
   (135 → 136) because 1198 was absent from it; step 3 sends the *same* arm, the
   *same* arity, the *same* cell and team with 1055, which the list already
   carried, and the list **stands still** (136) while a row is still placed
   (550 → 551). The row half and the list half are shown to disagree under one
   request.
5. **An oversized client next id moves the recorded cursor BACKWARDS**, 4 → 1.
   `command.py:446` computes `next_id = args[1] + 1` from the client and `:451-452`
   overwrites anything above the literal `5` with `1`. Visible in the preserved
   source; executed here rather than argued.
6. **One grant lands in two places under two different rules.** Step 5 calls both
   helpers at once: the deduplicating unit-list one and the **accumulating**
   storage one (`engine.add_store_item`, `engine.py:70-75`). The seed's empty
   storage became exactly `{"1198": 1}` while the unit list stood still.
7. **No arm charges or credits anything.** All **eight** stored resource slots are
   byte-identical in all seven steps — non-tautologically, because the printed
   lines differ between the arms.
8. **The sixth weekly position names no schedule entry.** The derived weekly bound
   is **5**, derived from the committed schedule's *list-valued* entries, while
   the schedule holds **3** entries. Position 4 is therefore one the schedule
   cannot answer — and it is where step 1's recorded successor lands.
9. **Neither branch derives what to grant.** Both take the item id from the
   client, with no content lookup, no bound, and no eligibility test. The weekly
   schedule's only consumer returns an int (its length); the type letters `g` and
   `c` are decoded nowhere in any of the eleven preserved modules.

## Divergences — recorded, never called parity

**Four** transactions diverge from the delivered route, across **three**
divergence classes. The manifest records both counts under separate keys
(`transaction_count` and `class_count`), because two of the four share a class:
steps 2 and 3 are the same arm with the same five arguments and differ only in
whether the client-sent id was already in the unit list. An earlier draft of the
manifest carried one key named `count` beside a block named `three_divergences`,
so a reader comparing the two saw 3 against 4 with no explanation.

| class | transactions | what the oracle does |
| --- | --- | --- |
| `client_supplied_item` | 5 | takes the granted item from the client |
| `client_supplied_next_id` | 6 | advances a client-sent cursor, then clamps anything above 5 to 1 |
| `arity_selects_the_arm` | 2, 3 | the client's argument count picks granting vs. not granting |

Parity is claimed for exactly **three** transactions: steps 1, 4, and 7. All
three are non-granting arms whose whole-document leaf diff is exactly the cursor
and the instant, and the offline suite asserts that for each of them
individually — a parity claim could not survive a granting arm slipping into that
list.

**No price is claimed in either direction.** Nothing here charges or credits
anything, and the delivered route charges and credits nothing either.

## Volatile fields — why the verification recomputes

The whole-document state files are **necessarily volatile**, and this is measured
rather than assumed: both preserved branches write the wall clock
**unconditionally** (`command.py:361` and `command.py:454`), so every step's
`before.json` and `after.json` carries a different instant on every run. Two
consecutive runs were compared file by file with line endings normalised and
**37 of the 48 files differed** — every state document, every request record,
every transaction record, and the manifest.

An earlier draft of this capture claimed the opposite: that only the six response
`Date` headers moved. That claim was copied from a capture whose branch does not
stamp a wall clock, and it was **false here**.

**Consequence for verification:** a test must **recompute** each transaction's
state digest from the committed bytes rather than compare it to a fixed
constant. `test_rewards_parity.py` does exactly that — it reimplements the
capture's digest recipe independently and checks the recorded digest, the recorded
changed-leaf set, and the recorded leaf-diff payload all reproduce from the two
recorded documents.

The capture compensates for the same-second collision with `await_clock_past()`,
which waits out the wall clock past the instant each step is about to overwrite,
so the stamp change is observed rather than raced for. This is the eighth recorded
flaky surface in this project.

Also volatile and labelled as such: each record's `captured_at_utc`, each
response's own `Date` header (recorded verbatim — redacting a header the oracle
sent would narrow the record), and each transaction's own `instant_before` /
`instant_is_volatile`, which are compared by **shape** and never by value.

The batch's `ts` is **pinned to a constant**, so it is not volatile: the
dispatcher parses it and never reads it.

## Containment

| check | result |
| --- | --- |
| combined working-tree digest before / after | `18e5e55ba85473bb…` — **identical** |
| committed seed digest before / after | `652cf198…3af22` — identical |
| working-tree `saves/` | absent |
| prior committed fixture directories | **20 prior committed fixture directories**, all unchanged |

The protected set is every committed `tests/fixtures/` directory except this one,
and `test_rewards_parity.py` asserts the set against the directories on disk — so
a new predecessor cannot be added without appearing in the capture's own pins
first. The count is 20; an earlier README said 19, because
`godot-unit-experience` joined the set after that sentence was written.

The capture is a **declared seeded capture**: `build_disposable()` gained a
defaulted seed parameter, and this capture is one of the four captures that
deliberately passes one (it needs the village corpus, not the fresh-player
corpus). `test_unit_xp_fixture.py` owns that exemption set and
`test_rewards_parity.py` asserts this capture's membership in it, so the
exemption cannot be removed silently.

## Claim limits

- **Nothing is claimed about what a reward is *worth*.** No price is charged and
  none is credited; there is no committed price schedule for either branch and the
  daily bound is a hardcoded literal, not a content-derived one.
- **The daily bound is not content-derived.** It is the literal `5` at
  `command.py:451`, in a branch with no reference to the five-entry schedule it
  happens to equal. The rejected derivation is retained in the manifest rather
  than dropped.
- **The weekly bound is derived from content, and it is not the schedule's
  cardinality** — 5 against 3, because it counts the schedule's list-valued
  entries. That is a derivation, not an observation.
- **Nothing is claimed about what the real Flash client sent.** Every payload here
  is crafted, and the weekly arm's arity in particular was chosen by this capture.
- **The captured item ids happen to be ones the weekly schedule names.** That is
  what makes the list append observable; it is **not** evidence that the schedule
  selects them, and the branch never reads it.
- **No eligibility, cooldown, window, or already-claimed rule is claimed or
  implemented.** The stamped instant has no reader anywhere in the preserved
  server, so there is nothing to reproduce. `fast_forward` makes both instants
  client-writable, and that is recorded rather than reproduced.
- **The two cursors are read by nothing.** Each is read only by the expression
  that overwrites it.
- **No type letter is mapped onto a resource.** `g`, `u`, and `c` are not decoded
  anywhere in the eleven preserved modules, so reading `g` as gold or `c` as cash
  would be an invention.
- **The derived index base is provisional.** The delivered envelope treats the
  cursor as a zero-based schedule index; nothing in the preserved source states a
  base, because nothing reads the cursor.
- **This is not pixel parity and there is no windowed capture.** Nothing is
  rendered by this line.
- **The parity claim covers these seven transactions against one fresh-ish village
  corpus.** No progressed-player save exists, and the corpus has **no** building
  or unit XP rows on any of its reward-relevant paths.

## Verification

```bash
python -B apps/compat-api/capture_rewards_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
python -B tools/hash-manifest/hash_manifest.py verify
openspec validate --all --strict
python -B packages/game-content/tools/validate_content.py
```

`test_rewards_parity.py` is the offline integrity guard for this fixture and
needs no server and no socket; it proves that by replacing `socket.socket` for
the duration of the whole recomputation and by asserting both service ports are
free. `test_rewards_endpoint.py` and `test_rewards_envelope.py` cover the
Compatibility API side.
