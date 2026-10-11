# M13 opening investigation — where client authority enters the preserved server

This document tests an enumeration the roadmap already carried as M13's standing
instruction. That enumeration named six client-sent-delta refusals and called them
"Server v1's requirements written in the negative."

**The enumeration is incomplete and the framing is wrong in a way that changes what
M13's first line should be.** The client-sent resource delta is not six separate
places that six endpoints each had to handle. It is one call, made unconditionally,
before the dispatcher opens, for every command the preserved server accepts — and the
preserved server has no refusal channel at all, so no branch guard has ever been able
to decline anything on the client's behalf.

Status: investigation only. No production code, spec, test, or fixture was changed,
nothing here proposes a line, and no branch of the preserved server was executed.
Every figure comes from reading committed files, and every census was checked against
a planted control before its number was reported.

## 1. The enumeration the ledger carried, re-read

The roadmap named six. They are not six instances of one thing:

| named | what it actually is | a command? |
|---|---|---|
| `collect` | derivation — the service computes the payout | yes |
| `expand` | derivation — the service computes the debit | yes |
| `end_quest` | divergence — refuses to reproduce a client-dictated destruction count | yes |
| `add_xp_unit` | unvalidated client amount, written as-is | yes |
| `research_buy_step_cash` | discard — reads a client cash value and ignores it | yes |
| `used_syringe` | discard — reads `args[4]` and ignores it | **no** |

Three observations follow, and none of them is cosmetic.

1. **`used_syringe` is not a command.** It is the fourth argument of
   `resurrect_hero`. The list therefore mixed commands, an argument, and behaviours.
2. **Four mechanisms, not one.** Derivation, divergence, unvalidated write, and
   discard are different obligations on Server v1 and would produce different
   requirements. "Client-sent delta" was never the common shape; it was the label on
   a heterogeneous sample.
3. **The largest member of the family is absent from the list** — see section 2.

The sample was assembled one endpoint at a time, as each Compatibility API route was
built. That is the correct way to discover such things and it produced no false
entries. What it does not do is establish completeness, and the ledger read it as if
it did.

## 2. The structural property the enumeration missed

`command.py:30` runs `do_command` once per entry of the client-supplied batch.
`do_command` then applies the client's resource vector at **`command.py:40`**, and the
`if cmd ==` chain does not open until **`command.py:42`**:

```python
    do_command(USERID, map_id, cmd, args, resources_changed)
...
    apply_resources(save, map, resources_changed)

    if cmd == "buy":
```

`engine.py:251-271` is what that call does. It unpacks **eight** client-supplied slots,
reads slot 0 into `unknown` and never writes it, and writes the other seven as
`max(current + delta, 0)` — `xp`, `gold`, `wood`, `oil`, `steel` on the map, `cash` on
`playerInfo`, `mana` on `privateState`.

So the client-sent resource delta is not a property of six branches. **It is a property
of the dispatcher, and it applies to all of them.** The committed command catalogue
agrees with the source and was used as the population rather than a re-derivation:
`tools/command-catalog/verify_commands.py` reports `catalog_commands: 63`,
`command_branches: 63`, `result: "agreement"`, exit 0.

This is why the six behaviours above are not the whole job. They are what happens when
a route must decide a *particular* amount. The dispatcher-level fact is prior to all of
them: **the server applies the client's numbers before it knows which command is
coming.**

## 3. There is no refusal channel

`server.py:318-322`:

```python
        command(USERID, data)

        response = ({"result": "success"}, 200)
        observation.completed(response)
        return response
```

The success response is **unconditional**. It is not reached by a branch; it is
returned after `command()` returns, whatever happened inside it. The only other
`result` sites in `server.py` — `:208`, `:239`, `:268` — are commented out.

Every branch-level condition in the dispatcher therefore has exactly one way to decline:
print a server-side log line and `return`. `move` at `command.py:126-129` is
representative:

```python
        item = map_get_item(map, item_index)
        if not item:
            print("Error: item not found.")
            return
```

There are 28 bare `return`s in `command.py` in this shape. None reaches the client as
a refusal, because the route has already decided its answer.

**And a refusal would not undo the delta even if it could.** `apply_resources` runs at
`:40`; the `not item` test is at `:127`. A `move` whose address does not resolve has
*already* had the client's resource vector applied. Refusal in this protocol is
post-dispatch and, as written, invisible.

## 4. Census of the branch conditions — and a withdrawn term

Counting every `if` inside a branch body whose test does not mention `cmd` (inside
`do_command` the only conditions that test `cmd` are the dispatch chain, so any other
conditional is a condition on data):

- **63** branches
- **76** non-dispatch conditions
- **33** branches carry at least one; **30** carry none
- only **2 of 63** check argument count (`len(args) > 2` at `:326`, `len(args) > 4` at
  `:346`)

The 76 conditions classify by AST shape, mechanically and non-overlapping — the
top-level node type of the test decides the family, and a `Compare` is further split by
its operator set:

| family | count |
|---|---|
| membership (`'win' in response`, `str(magic_id) in magics`) | 28 |
| negation/absence (`not item`, `not building`) | 23 |
| ordering/bound (`n > 99`, `len(args) > 4`) | 9 |
| other/name (`win`, `won_extra`, `resurrectable`) | 9 |
| equality (`playerID == 1`, `reason == 'KILL'`) | 5 |
| boolean/comparison (`tutorial_step >= 25 or tutorial_step == 15`) | 1 |
| other/subscript (`data[6]`) | 1 |

**The term "guard" is withdrawn.** A first pass labelled these "validation guards" and
reported a 33/30 split. Reading all 76 tests falsified that label: membership is
overwhelmingly shape-checking a client-sent blob, and absence is overwhelmingly
addressability — *is there a row at that key* — which is not authority at all. The
two largest families are **51 of 76** and neither is an authority check.

One specific correction, because it is the kind of near-miss that becomes folklore: the
single equality test in `buy` at `command.py:52`, `if playerID == 1`, is **not** an
ownership gate. It selects whether to record the item in the bought-units list. The
purchase proceeds at `:55` regardless. There is no branch in the dispatcher that tests
whether the caller owns the thing it is acting on.

## 5. What already exists on the modern side

Measured over `apps/compat-api/`:

- **24** `/v0` routes
- **104** declared `ERROR_*`-family refusal constants
- **3** declared and referenced nowhere: `ERROR_INVALID_STEP`, `ERROR_MISSING_STEP`,
  `ERROR_NULL_STEP`

So the refusal channel Server v1 needs has already been built — per route, twenty-five
times, each route deriving its own vector and answering with its own codes. That is the
shape of the modern side, and it is also the cost: the derivation is not centralised,
because the protocol gave it nowhere to live.

## 6. What this changes for M13

The standing instruction said to convert six recorded divergences into enforced
invariants one at a time. That remains true work, and it is still the right order. But
it is the *per-route* half, and it is not where the authority boundary begins.

The prior half is structural and is now measured:

1. The client-sent resource vector is applied at dispatch, before the command is known,
   for all 63 branches.
2. There is no refusal channel; success is unconditional.
3. Refusal is post-dispatch and does not reverse the delta.

Together these say the preserved protocol has no way to say no and applies the client's
numbers before it can try. **Server v1's first job is therefore a dispatcher-level
refusal channel and a server-derived resource path**, not twenty-five per-route
derivations that each re-solve it. The six recorded divergences remain the correct
first *surface* to convert, but they are the tail of this, not the head.

**No line is proposed on this entry.**

## 7. Corrections and discarded instruments

Recorded rather than quietly fixed, per the repository's standing practice.

- **Withdrawn: the word "guard".** A first census reported per-branch "guard" counts.
  Reading the 76 tests falsified the term; section 4 replaces it with a measured AST
  classification. The underlying counts (63 branches, 76 conditions, 33/30) are
  unchanged and independently reproduced by two scripts.
- **Withdrawn: the completeness of the six-item enumeration.** See sections 1 and 2.
  The six entries themselves are accurate and none was removed.
- **Discarded instrument — dead refusal codes.** A regex assuming inline string
  literals in `error_response(...)` calls returned **zero** matches, because the codes
  are named constants. A clean zero from a broken instrument; discarded, not reported.
- **Discarded instrument — the corrected dead-code search.** The replacement grep was
  non-recursive (`apps/compat-api/*.py`) and never entered `apps/compat-api/tests/`,
  so it reported **5** unreferenced codes. Re-run recursively, the true figure is
  **3**. The two codes it did find genuinely dead were among the five, which is why
  the wrong number was not obviously wrong.
- **A control refused a measurement, correctly.** The family classifier's fourth
  planted control was expected to yield `boolean(Or)` and yielded
  `boolean(Compare)`. The expectation was wrong, not the classifier; the instrument
  refused to report until the control was corrected. Recorded because a control that
  never fires is not a control.
- **Route count corrected twice, and the second correction discards the instrument
  that produced the first.** An early truncated read reported 26 routes. A
  path-recursive regex over `apps/compat-api/**/*.py` then reported **25** — and
  that figure was wrong for a reason the regex could not see: the match set
  includes `tests/test_unit_xp_fixture.py:412`, whose **docstring contains the
  literal `@app.post("/v0/...")`** while describing the registration pattern.
  A recursive text search cannot distinguish prose that quotes a decorator from
  the decorator. The route table itself was then asked directly —
  `app.url_map.iter_rules()`, filtered to `/v0`, built from a disposable corpus
  exactly as the test harness does — and reports **24 rules, 24 distinct paths**,
  every one `POST` except `/v0/session` (`GET`). A planted `add_url_rule` probe
  was visible to the same enumeration, so the count is able to see a route it has
  no other reason to find. **The 25 in the previous revision of this document is
  withdrawn; 24 is measured against the registration itself.**
- **A bad control, recorded because it looked like a passing one.** The route
  enumeration's second control asserted that non-`/v0` rules exist, so that the
  `/v0` filter could be shown to discriminate rather than match everything. There
  are **zero** non-`/v0` rules — every registered rule is `/v0` — so the control
  failed while the measurement it guarded was correct. The control's premise was
  unestablished; it was removed rather than weakened, and the plant is the control
  that actually constrains the result.
- **Containment note.** The harness's `remove_corpus` calls
  `shutil.rmtree(..., ignore_errors=True)`, which removed every file but left
  three **empty** directories under the temp root. No working-tree `saves/` was
  created and no save byte was written; the empty directories were removed
  directly. Recorded because "the corpus was removed" and "the corpus's contents
  were removed" are different claims.

## 8. Verification actually run for this document

- `tools/command-catalog/verify_commands.py` — `catalog_commands: 63`,
  `command_branches: 63`, `result: "agreement"`, `problems: []`, exit 0.
- The route table asked directly — `create_app(boot).url_map.iter_rules()` over a
  disposable corpus built by `compat_test_harness.build_test_corpus()` and removed
  after — reporting **24** `/v0` rules with a planted rule visible to the same
  enumeration. This is the measurement behind the correction in section 7, and it
  supersedes the textual count.
- Three instruments re-run from committed sources, each refusing to report until its
  planted controls classified as planted; the two census scripts agree on 63 branches,
  76 conditions and 30 bare branches.
- `openspec validate --all --strict` — **75 passed / 0 failed** (75 items), exit 0, the
  unchanged baseline; no spec was touched by this stage.
- `hash_manifest.py verify` — **3,258 entries, 758,423,699 bytes**, commit
  `e8c98a03c902eba70323538dc5d4eaba2f2927a1`, exit 0. Unmoved, as expected: the
  manifest does not cover `docs/`.

**Not run, and why:** no application, client, or Conversion-API suite was executed.
This change alters two files under `docs/`, and `hash_manifest.py` does not cover
`docs/`; the references to `docs/` in the Godot suites and the census tools are all to
specific named files, and no suite scans the directory. Re-running a battery that
cannot observe the change would be theatre, and recording it as though it had run would
be a false claim.
