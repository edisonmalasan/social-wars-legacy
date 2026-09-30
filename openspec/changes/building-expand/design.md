# Design

## Context

See `proposal.md` — Why, and the committed investigation record
`docs/legacy-town-expansion.md`. The `expand` branch's state effect is
**established**; four gameplay questions were open. Two of them are now settled
by committed evidence, one is settled by an executed probe plus a derivation, and
one is a **characterised evidence gap that bounds this change rather than blocking
it**.

### Established (unchanged from the investigation record, plus one new probe)

- `expand(n)` appends `n` to `map["expansions"]` and changes **nothing else** —
  not `items`, not `level`, not `map_sizes`, not `increasedPopulation`, not
  `privateState`, not the rest of `playerInfo` — and answers
  `{"result":"success"}` (`command.py:211-216`).
- The price is **entirely client-sent** and applied verbatim per resource as
  `max(current + delta, 0)` (`engine.py:251-271`).
- The per-resource clamp is **reachable, for the first time in this family**: a
  client-sent `-2500` gold debit against a `2000` balance landed on **`0`**, not
  `-500`. A non-int argument crashes the branch with an unhandled HTTP 500
  (`int("abc")`).
- **The server cannot arbitrate the id space at all** (new probe). Against the
  fresh corpus, in one disposable copy of the real server:
  `expand(999)` → success (`[35, 36, 45, 46, 999]`), a duplicate `expand(35)` →
  success, `expand(-1)` → success. No range check, no dedup, no level gate, no
  ordering rule, no requirement check.
- Content: `expansion_prices` (98 entries, positional, **no stable id**, fields
  `coins`/`cash`/`neighbors`/`inventory_qte`, indexes 0–3 all zero, 4 and 5
  cheapest non-zero, saturated at 100 000 coins / 20 cash / 15 neighbors / 30
  inventory from index 34); `town_prices` and `map_prices` (4 entries each,
  identical values, levels 15/25/35/45 — normalized as separate schedules and
  deliberately never deduplicated).
- Corpus: a level-1 fresh player whose `maps[0]["expansions"]` is
  **`[35, 36, 45, 46]`**, identical in the pre-migration save.

### New committed evidence (this is what settled two of the four questions)

The asset registry and the SWF static inventory — both committed, both
source-grounded, neither requiring execution — carry expansion vocabulary that
resolves two questions the config alone could not:

| Committed evidence | Resolves |
| --- | --- |
| `assets/images/en/expansion_gold.jpg` **and** `assets/images/en/expansion_cash.jpg` (registry, distinct sha256s) | **Q2**: the expansion price has exactly **two** components, and the client's own icon for one of them is named **`gold`** while the other is **`cash`**. So the config's `coins` field is the client's `gold`, and the server's slot 2 (`gold`, `engine.py:259-267`) is the target. Not a guess about which resource "coins" might be — a client-supplied asset name. |
| SWF symbols `PopupExpandMC` and `btnBuyExpandTileMC`, plus `assets/images/en/expansion.png` | **Q4, partially**: the client's model is a purchasable **expansion *tile*** bought through a popup. This is positive evidence that a tile is a real client concept. |
| `tools/asset-registry/README.md` scope statement — the inspection establishes *"no conversion, timeline semantics, script behavior, asset validity, gameplay parity, or Godot rendering"* | **Q4, the limit**: symbols and asset names are all the evidence carries. The **tile → cell geometry is not in the committed evidence**, so the size and position of a bought tile cannot be derived from anything preserved. |

A second, smaller correction of vocabulary: the config uses **two** resource
namings. `items[].costs` uses the *letter* set (`g` 279, `c` 375, `w` 128, `s`
110, `o` 69 occurrences), while the price schedules use the *word* set
(`coins`, `cash`). So a word-keyed price field is not a slip; it is a second naming
layer, and the bridge between the layers is the client's own asset name.

## The four questions, answered

**D1 — the price comes from `expansion_prices`, indexed by the expansion id
itself (derived).** Three readings were in competition: the 98-entry
`expansion_prices` indexed by the sent id; the 4-entry `town_prices` /
`map_prices` indexed by town level; or the count of expansions already owned. The
decisive evidence is the corpus's own value: **`[35, 36, 45, 46]` is a valid
`expansion_prices` index (0–97) and is not a valid `town_prices`/`map_prices`
index (0–3), and it is not a level set either** — the `level` values are 15, 25,
35, 45, and while 35 and 45 appear in the list, 36 and 46 do not, so the set as a
whole is not a level set. The owned list is therefore read as ids into the
positional table.

This is a **derivation**, and the new probe is exactly why: the server accepts
`999`, a duplicate, and `-1` alike, so it offers no evidence to arbitrate, and
the id space cannot be settled by observing the server. Two consequences are
carried explicitly. First, a level-1 fresh player owning four saturated-price
(`coins 100000`) expansions is not a coherent game state — that is recorded as a
reason to distrust the reading, and it is the reason the change's claim stops at
"the price the committed table assigns to the id", never at "the price a coherent
player would pay". Second, because the server does not range-check, **the endpoint
must**, or a client could buy expansion 999 for a price derived from a table that
has no entry 999.

**D2 — `coins` is the client's `gold`, and lands in server slot 2 (established by
committed asset evidence, with the slot mapping established by the server's own
ordering).** `expansion_gold.jpg` and `expansion_cash.jpg` are two distinct
committed images and the expansion popup is the one place both a gold and a cash
price appear together in this config. `cash` is unambiguous (slot 6,
`playerInfo.cash`); `coins` is the gold component. The derived vector for an
expansion priced `coins C, cash K` is `[0, 0, -C, 0, 0, 0, -K, 0]`, and a
zero-priced expansion derives the all-zero vector — legal, because the free
expansions 0–3 exist in the committed table.

**D3 — the `neighbors` and `inventory_qte` requirements are refused, never
invented (derived).** The server ignores both. Nothing any delivered surface can
currently read can evaluate either: no neighbor count and no inventory quantity is
exposed by the delivered bootstrap, the client's `GameApi`, or the corpus. The
collect line's precedent is to refuse rather than guess, and it applies unchanged:
an expansion whose committed `neighbors` or `inventory_qte` is greater than zero
fails closed with `expansion_requirements_unmet` (409).

This has a striking, honest consequence on the committed corpus that the tests
will assert rather than hide: **every id the corpus owns (`35, 36, 45, 46`) has
`neighbors 15` and `inventory_qte 30`, so none of them could have been bought
under this rule, and the only purchasable entries are the free ones — indexes
0–3, priced `0` coins and `0` cash.** The line therefore delivers a real
zero-cost expansion on this corpus and refuses the priced ones, which is the
correct outcome under the evidence and the wrong outcome for gameplay, and is
recorded as a claim limit rather than patched by lowering the bar.

**D4 — this change delivers the expansion **unlock ledger** and nothing about
land (established gap, explicitly bounded).** The server's only effect is an int in
a list, and the committed evidence establishes the *vocabulary* — an expansion is
a tile, bought through a popup, priced in gold and cash — but **not the
tile → cell geometry**, because the SWF inspection is symbols-and-tags only and
its own scope statement disclaims timeline semantics, script behavior, and
rendering. So this change will:

- **NOT** invent terrain growth, grid enlargement, new buildable cells, or any
  change to the placement bounds the delivered placement line enforces;
- **NOT** claim that a bought expansion makes any area of the town buildable;
- **WILL** deliver the full, evidence-supported unlock ledger: read the committed
  schedule, refuse what the evidence does not support, send one intent, and prove
  the committed list grew by exactly the sent id.

The gap is a **known evidence gap that bounds visual land growth**, and it is
named as such in the delta, the fixture README, both application READMEs, the
structural report's non-claims, and the roadmap ledger — so a later change can
close it with new evidence (an extracted geometry table, a rendered reference, or
an authoritative spec) instead of rediscovering that it is missing.

## The remaining decisions of the change

**D5 — intent-only contract, content-derived debit, and a two-part post-state
proof that includes the money.** `POST /v0/expand` accepts only
`{user_id, expansion_id}`; no amount, resource, time, or price is accepted from
the client. The endpoint reads `map["expansions"]`, refuses out-of-range and
duplicate ids, reads the item's committed price, derives the debit, refuses
`expansion_requirements_unmet` and `insufficient_resources`, executes the
unchanged `command()` dispatcher, and then proves **both**: the list grew by
**exactly one** entry equal to the sent id **at the end**, and **every** stored
resource changed by **exactly** the derived debit. That second half is the direct
mitigation of the probe's finding: a client-sent debit is a client-trusted mint or
burn, and this is the first endpoint whose proof exists to catch exactly that.

**D6 — insufficient resources fail closed rather than reproduce the clamp.** Two
options were available. Reproducing the clamp is what every earlier line does,
because their prices were client-sent and there was nothing to compare against.
Here the debit is **server-derived**, so the endpoint can know whether the balance
covers it, and silently under-charging to the clamp would make the post-state
proof ambiguous (the balance moved by less than the derived debit, which is
indistinguishable from a bug). So an insufficient balance fails closed
`insufficient_resources` (409) before execution. **Derived**; the clamp
alternative is recorded as the rejected option, and the clamp's own reachability
(established by probe) is what makes this the safer choice rather than an
arbitrary one.

**D7 — validation split, and the client's readout.** The client owns what the
service cannot see: which entries are owned, which are unpurchased, and the
readout of the committed schedule and the derived cost; the endpoint owns
structural input validity, the content refusals, and the two-part proof.
Authoritative validation remains Server v1 (M13) work.

**D8 — evidence, claim limits, and containment.** A windowed fake-API capture of a
completed expansion plus a headless deterministic `expand-report-v1` report
(inputs and digests, the intent, the before/after lists, the derived debit, the
committed schedule row used, the request counts, the established-versus-derived
provenance split, and the explicit non-claims — including the land gap and the
"none of the corpus's owned ids could have been bought" consequence), byte-identical
across reruns. Execution and containment carry forward unchanged: unchanged legacy
`command()` in-process over a disposable corpus, loopback only, no new packages,
both batteries plus the guard baseline and the 3,258-entry hash manifest green in
the final state, and the orchestrator-run integration review as the fallback for
the unavailable dedicated verification workflow.

## Risks / Trade-offs

- **The id space is a derivation the server cannot confirm** → the boundary is
  drawn once, in D1, and carried verbatim into the envelope docstring, the fixture
  README, both application READMEs, the report's provenance section, and the
  ledger; the claim is "the price the committed positional table assigns to that
  id", never "the price a coherent player pays", and the incoherent-corpus
  observation is recorded rather than explained away.
- **A derivation would mint or burn resources if it were wrong** → this is the
  family's highest-stakes line for that failure, because the price is
  server-derived; it is mitigated by D5's value-level proof (any divergence is a
  fail-closed `internal_error`, not a reported success) and by D6's refusal rather
  than partial charge.
- **The requirements rule makes every priced expansion unpurchasable on this
  corpus** → accepted deliberately: refusing is the honest outcome under the
  evidence, the free expansions 0–3 still deliver a real end-to-end transaction,
  and the consequence is a named claim limit rather than a lowered bar.
- **The land effect is absent** → bounded explicitly in D4 with a written
  prohibition on inventing terrain, grid, cell, or placement-bound changes, and
  recorded as a known evidence gap everywhere the slice is described.
- **A seventh mode on one surface** → modes stay mutually exclusive, each keeps its
  own state, and all eight delivered suites must stay green, so a regression shows
  up in an existing suite rather than hiding behind the new one.
- **The corpus's incoherent expansion list** → the endpoint must tolerate the
  existing ids (they are not purchasable, but they are present) and must never
  rewrite or normalize them; the fixture and the parity tests assert the list is
  appended to, never reordered or deduplicated.
