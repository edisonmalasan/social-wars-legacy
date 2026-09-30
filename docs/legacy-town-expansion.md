# Legacy investigation: town expansion

Status: **investigation complete; the state effect is ESTABLISHED by an executed
probe, and four gameplay derivations remain OPEN, one of which (the expansion →
buildable-land mapping) is not resolvable from the repository at all.** This record
exists so the next bounded M7 change — *town expansion* — is proposed against real
evidence instead of a guess, and so every open question is visible before code is
written.

This is the ninth M7 deliver line's investigation. It follows the same
investigation-first pattern as upgrade (`docs/legacy-construction-timing.md` is the
construction record) and collect income (`docs/legacy-collect-income.md`).

## The command

The `command.py` dispatcher has exactly one expansion branch, and it is one line
of state change (`command.py:211-216`):

```python
elif cmd == "expand":
    expansion = args[0]
    map["expansions"] += [int(expansion)]
    print("Unlocked Expansion", expansion)
```

The committed command catalog records the same
(`docs/legacy-protocol/commands.md`, "Town expansion"): args[0] is an int-like
expansion id, the state change is `map[expansions] += [int(expansion)]`, and
persistence is the batch-level `save_session(USERID)` (`command.py:32`;
`sessions.py:248-255`) — the same persistence every other delivered line uses.

**Nothing else in the server reads, validates, prices, or deduplicates
`map["expansions"]`.** A repository-wide search finds exactly three references to
the word in the whole legacy server, all three inside the branch above. There is no
level gate, no requirement check, no "already expanded" check, no ordering rule,
and no link between an expansion id and any other state.

## The state effect: ESTABLISHED by executed probe

Probe: `expand(4)` with a **neutral** resource vector, then `expand(5)` with the
`expansion_prices[4]` vector, in one disposable copy of the real legacy server on
`127.0.0.1:5055` under the pinned interpreter.

```
before: expansions [35, 36, 45, 46] items 40 level 1 xp 4 gold 2000 wood 2000
        oil 2000 steel 2000 cash 5 mana 0 map_sizes [0]

expand(4) neutral -> {"result":"success"}
  after: expansions [35, 36, 45, 46, 4]      everything else identical

expand(5) priced  -> {"result":"success"}
  after: expansions [35, 36, 45, 46, 4, 5]   gold 2000 -> 0, cash 5 -> 0

changed top-level map keys: ['expansions', 'gold']
items identical: True   privateState identical: True
playerInfo identical (except cash): True
```

Established, in order of confidence:

1. **`expand(n)` appends `n` to `map["expansions"]` and changes nothing else** —
   not `items`, not `level`, not `map_sizes`, not `increasedPopulation`, not
   `privateState`, not the rest of `playerInfo`. The response is
   `{"result":"success"}`.
2. **Appends are not deduplicated and not ordered.** `[35, 36, 45, 46]` became
   `[35, 36, 45, 46, 4, 5]` — the corpus's own four ids plus the two sent. The
   legacy server accepts any int, including a repeat and an out-of-order value.
3. **The price is entirely client-sent and applied verbatim**, exactly as in every
   earlier delivered line: the server never prices an expansion. A `-2500` gold
   delta was applied as `-2500` gold.
4. **The per-resource clamp finally bit, for real.** The second batch asked for
   2500 gold against a balance of 2000, and `engine.py:251-271`'s
   `max(current + delta, 0)` drove the balance to **0** rather than to `-500`; the
   5 cash against 5 cash reached 0 exactly. This is the first executed evidence in
   the family that the clamp is reachable, and it is reachable exactly when a
   client-sent debit exceeds the balance. It confirms the earlier collect probe's
   note (where the clamp was deliberately not exercised because `-5` on `2000`
   stays positive) and it is the strongest available argument for a
   server-derived price: a client-sent debit is a client-trusted mint or burn.

## The content

Two unrelated price schedules exist, and nothing in the server connects either to
the `expand` branch:

| Key | Entries | Fields | Census |
| --- | --- | --- | --- |
| `expansion_prices` | 98 | `coins`, `cash`, `neighbors`, `inventory_qte` | "No stable ID; positional index" (`docs/game-content/census.md`); fully native numbers (`docs/game-content/field-types.md`) |
| `town_prices` | 4 | `coins`, `cash`, `level` | levels 15 / 25 / 35 / 45, coins 100 000 / 300 000 / 550 000 / 1 000 000, cash 20 |
| `map_prices` | 4 | `coins`, `cash`, `level` | **identical to `town_prices`** — normalized as a separate schedule and deliberately never deduplicated (`packages/game-content/README.md`, economy extension) |

`expansion_prices` is front-loaded with free entries: indexes 0–3 are all zero, and
the first non-zero costs are index 4 (`coins 2500`, `cash 5`, `neighbors 1`,
`inventory_qte 1`) and index 5 (`coins 5000`, `cash 8`, `neighbors 2`,
`inventory_qte 2`). From index 34 onward the price saturates at
`coins 100000`, `cash 20`, `neighbors 15`, `inventory_qte 30`.

The committed corpus is a **fresh player at map level 1** whose
`maps[0]["expansions"]` is **`[35, 36, 45, 46]`** — identical in the
pre-migration save, so it is part of the preserved corpus, not migration damage.

## The four open questions

**Q1 — which price table, indexed how?** The three candidate readings are
mutually inconsistent and the repository does not decide between them:

- the 98-entry `expansion_prices` indexed by the expansion id sent to `expand`;
- the 4-entry `town_prices` / `map_prices` indexed by the town level, whose
  `level` values (15/25/35/45) would be the expansion ids;
- the count of expansions already owned (`len(map["expansions"])`).

The one hard piece of evidence is the corpus itself: **`[35, 36, 45, 46]` is a
valid `expansion_prices` index (0–97) and is not a valid `town_prices` or
`map_prices` index (0–3), and it is not a plausible level value.** So the
`expansion_prices` reading is the best-supported — but it is a reading, not an
observation, and it has a consequence nobody has checked: the corpus already owns
expansions 35, 36, 45 and 46, which under that reading cost 100 000 coins and 20
cash each. A level-1 fresh player owning four saturated-price expansions is not a
coherent game state, which is a reason to distrust the reading rather than a
reason to accept it.

**Q2 — which resource does `coins` mean?** The eight-slot vector is
`[unknown, xp, gold, wood, oil, steel, cash, mana]`; `expansion_prices` names
`coins` and `cash`, and `cash` maps to slot 6 unambiguously. `coins` is the only
field with no exact counterpart among the seven named resources, and `gold` is the
plausible candidate. The collect line had the same question and resolved it from
`collect_type`; here nothing resolves it.

**Q3 — are the `neighbors` and `inventory_qte` requirements implemented, or
refused?** The server ignores both. A faithful line either enforces them (a
neighbor count and an inventory quantity, neither of which any delivered surface
can currently read) or refuses the expansion that needs them. The collect line's
precedent is to refuse rather than invent, and both requirements are outside the
delivered slice, so refusing is the likely answer — but it must be an explicit
decision, not an omission.

**Q4 — what does an expansion actually *do* for the player?** This is the
blocker. The server's only effect is an int in a list, and **nothing in the
repository maps an expansion id to buildable land, a grid size, a terrain extent,
or a placement bound.** The delivered placement line enforces grid bounds
client-side, and the M6 rendering evidence already records its projection
constants as derived-provisional because the legacy SWF's numeric iso constants
were never extracted. So a town-expansion line cannot yet "show the town get
bigger" — the client has no committed source for the bigger town's shape. The
deliverable that *is* supported by evidence is the **unlock ledger**: read the
committed price schedule, refuse what the requirements forbid, send one
`expand` intent, and prove the committed list grew by exactly the sent id — with
the land-shape effect recorded as a known, named gap rather than faked.

## What the next change should do

Recommended shape, subject to the Q1–Q4 decisions being made explicitly in its
design (the same treatment the collect line's D1–D6 received, each marked
derived-provisional):

- an executed-legacy `expand` fixture, one command, one disposable corpus — the
  corpus's `expansions` list gaining exactly one entry with `items`, the level,
  `map_sizes`, the private state, and the other six resources byte-identical;
- a loopback-only `POST /v0/expand` endpoint accepting only `{user_id,
  expansion_id}`, deriving the price from the chosen schedule, failing closed on a
  cap/requirement/level/duplicate that the committed evidence does not support,
  and proving the post-state — that is the shape of the collect endpoint, and its
  **value-level** post-state proof (every resource changed by exactly the derived
  debit) is directly reusable and would immediately prevent the client-trusted
  mint-or-burn the probe exposed;
- a typed `GameApi.expand_town()` on both implementations, an expansion readout on
  the selection-driven surface showing the committed schedule, the player's
  current list, and the next purchasable entry, and an `Expand` action as the
  seventh mutually exclusive mode that applies only the authoritative response;
- and an explicit recorded gap: **no buildable-land effect**, because no committed
  source maps an expansion id to land.

Non-goals: the neighbor/inventory requirement implementation, the town-versus-map
schedule disambiguation beyond what the corpus decides, `map_sizes`, terrain
growth, and server-authoritative validation (Server v1 / M13).

## Resolution, after the `building-expand` proposal (2026-09-30)

All four questions are now answered. The investigation text above is preserved
unchanged as the evidence base; this section records the resolutions, the two new
committed-evidence findings, the two additional probe results, and one correction
to a claim made above.

### Corrections to the investigation record

- **The saturation index above was imprecise.** It said the price "saturates at
  coins 100000, cash 20, neighbors 15, inventory_qte 30 from index 34". Computed
  per field from the real table, saturation begins much earlier: `cash` at index
  11, `coins` at 14, `neighbors` at 18, and `inventory_qte` at 33 — and the whole
  row reads `100000/20/15/30` from index 33 to 97. The committed capture manifest
  records the computed census rather than the hand-written number, and the `34`
  claim was not carried into any implementation or document.
- **`map_sizes` is not a map field.** The investigation listed it among
  `maps[0]`'s expansion-related fields; in the committed corpus `map_sizes` lives
  in `playerInfo` (`[0]`) and is **absent** from the map record entirely. The
  capture confirms it is absent before and after.

### Two new committed-evidence findings (no execution required)

- **Q2 settled — `coins` is the client's `gold`.** The asset registry carries
  `assets/images/en/expansion_gold.jpg` and `assets/images/en/expansion_cash.jpg`
  as two distinct committed images (sha256 `7918b5f6…` and `73daf476…`). They are
  the expansion popup's two price components, the server's slot 2 is `gold` and
  slot 6 is `cash`, and a row priced `coins C, cash K` derives
  `[0, 0, -C, 0, 0, 0, -K, 0]`. A smaller finding corrects the vocabulary:
  `items[].costs` uses the *letter* set (`g` 279, `c` 375, `w` 128, `s` 110,
  `o` 69), so the schedules' *word* vocabulary is a second naming layer, not a
  slip.
- **Q4 partially settled — an expansion is a purchasable *tile*.** The committed
  SWF symbols name `PopupExpandMC` and `btnBuyExpandTileMC`, and the registry
  carries `assets/images/en/expansion.png`. So the tile, the popup, and the two
  price components are all real client concepts.

### The two additional probe results

- **The server cannot arbitrate the id space at all.** Against the corpus,
  `expand(999)` → success (`[…, 999]`), a duplicate `expand(35)` → success, and
  `expand(-1)` → success. This is exactly the evidence for the delivered
  endpoint's two guards: the legacy server omits the range check and the
  duplicate check, so a client could otherwise "buy" expansion 999 for a price
  derived from a row that does not exist.
- **The clamp is reachable for the first time in this family.** The priced batch
  asked for 2500 gold against a 2000 balance and `engine.py:251-271`'s
  `max(current + delta, 0)` landed the balance on **0**, not `-500`; the 5 cash
  against 5 cash reached 0 exactly. The clamp is reachable precisely when a
  client-sent debit exceeds the balance, which is what makes a client-sent price
  a client-trusted mint or burn — and it is why the delivered endpoint derives the
  debit server-side and proves the resulting balances by value.

### The four resolutions

| # | Question | Resolution |
| --- | --- | --- |
| D1 | which schedule, which index space | `expansion_prices`, **indexed by the expansion id itself** — **derived**. The corpus's `[35, 36, 45, 46]` is valid only in the 98-entry table, invalid for the 4-entry schedules (0–3), and not a level set (levels 15/25/35/45; 36 and 46 are not levels). It must be derived because the probe shows the server offers no evidence to arbitrate. The claim is "the price the committed table assigns to that id", never "the price a coherent player pays" |
| D2 | which resource `coins` means | the client's `gold`, server slot 2 — **established by the committed client asset names**, with the letter-vs-word vocabulary note above |
| D3 | the `neighbors` / `inventory_qte` requirements | **refused, never invented** — **derived**. Nothing the delivered stack can read evaluates either. Consequence, recorded not worked around: **94 of 98 rows are unpurchasable, including all four ids the corpus owns**, so only the free indexes 0–3 can be bought and the delivered transaction is a zero-cost one |
| D4 | what an expansion does for the player | a **known evidence gap** — the vocabulary is established (tile, popup, two price components), the **tile → cell geometry is not**, because the committed inspection is symbols-and-tags only and its own scope statement disclaims timeline semantics, script behavior, and rendering. The delivered scope is the **unlock ledger**, with terrain, grid, buildable cells, and placement bounds explicitly **not** invented. Closing the gap needs new evidence, not a derivation |

Two further delivered decisions: **D5** the endpoint proves its post-state **twice**
— the owned list grew by exactly one appended id, *and* every stored resource
changed by exactly the derived debit — and **D6** an insufficient balance fails
closed `insufficient_resources` rather than reproducing the clamp, because the
debit is server-derived here, so a silent partial charge would make the
value-level proof ambiguous.

