# Proposal

## Why

M11's deliver list ends at **special mechanics**, and its exit criterion is
unusual for this project: *"All relevant legacy game systems are classified and
implemented or explicitly excluded."* That is a **classification** criterion, so
classification is the deliverable.

The committed investigation **`docs/legacy-m11-social.md`** (PR #309, merged
`0cccdde`, corrected `fe63b85`) measured the six M11 items and produced a
classification that is largely **negative but not empty** — and the negative part
is precise rather than assumed.

**Three findings, each measured rather than inferred.**

**1. Social content is committed and read by nothing.** Three normalized tables —
`social_items` (26), `findable_items` (10), `neighbor_assists` (5) — exist with
schemas, round-trip evidence and manifest entries. Across all 11 legacy modules,
under **six counting rules**, all three return **zero** consumers, for both
normalized and raw `config/main.json` key names. That is **41 entries of committed
social content with no server-side behaviour**, joining the established class of
committed fields with no legacy consumer.

**2. Social state is persisted in every document and never written.** This is the
finding that makes M11 a surface rather than a closure, and it is the same shape
that made `godot-rewards` real. Of 19 measured social state fields, **12 have zero
occurrences of any kind** - no read, no write, no mention:

`friendsHelpedCoveredItem`, `neighborAssists`, `receivedAssists`,
`firstTimeAlliance`, `helpMap`, `attacksSent`, `attacksReceived`, `attacksPack`,
`spyings`, `spyingsPack`, `questsRank`, `resourcesTraded`,
`crossPromotionsFinished`

The six that *are* written are written by branches whose subject is not the social
system they name, and the only genuine one,
`set_resource_allies` (`command.py:637`), writes
`map["resourceAlliesMarket"] = resource` from **client-sent `args[0]`**.

**3. Every write-less field is uniformly empty across the whole corpus.** Across
all **33** documents, each of the 12 holds exactly **one** value — `null`, `{}`,
`[]`, or `0`, in **33/33** cases. The corpus contains **no example of a populated
social field.**

**Visits and scores have no surface at all.** `world_id` and `worldChange` are map
keys present in all 33 documents and appear **zero** times in the legacy source.
There is **zero** arithmetic on any score-like value in `command.py`. Two apparent
positives were checked and **rejected**: `lost` is a local unit-loss counter
(`command.py:792`, `:868`) and `won` is an auction-bet result
(`auctions.py:164`).

## What this proposal delivers

A **`godot-social-state` refusal line**: a typed, read-only projection of the
persisted social state, reporting the measured fields, their recorded uniform
corpus values, and the recorded zero-consumer census — while **refusing** to
decode `neighbor_assists` rewards, charge `findable_items` coins, select
`social_items` workers, or treat an absent field as an empty one.

This is the shape of the delivered refusal lines (`godot-unit-animations`,
`godot-unit-movement`, `godot-unit-production`): **content and state reported,
mechanism refused, and the absence recorded as a property** rather than read as
permission to invent a rule.

## Why a refusal line rather than an implementation

Implementing "friends" here would mean inventing a social system. The legacy
server has no friend command, no friend state writer, no visit surface, and no
score arithmetic. Any rule this project delivered would be **fabricated** — and
`AGENTS.md` is explicit that client-dictated state is the *Bad* pattern and that
observed legacy behaviour is the only parity evidence.

There is a real risk this line is misread as "M11 has nothing left." It does not.
It records **where the boundary is**, so the next line can be chosen from evidence
instead of from a name on a roadmap.

## Scope

**In scope**
- A typed read-only projection of the 19 measured social state fields.
- The recorded uniform corpus values, and the recorded zero-consumer census.
- Fail-closed handling of absent fields, distinguished from committed empties.
- The `set_resource_allies` client-sent write, recorded verbatim, not reproduced.

**Out of scope**
- Any Compatibility API endpoint or executed-legacy fixture. There is no social
  behaviour to capture, and the corpus holds no populated social field.
- `world_id` / `worldChange` semantics.
- Darts, premium, magic, mana — a separate line; darts alone has four branches
  across six fields.
- Decoding any `neighbor_assists` reward, `findable_items` coin value, or
  `social_items` worker cost.

## Non-goals

- **No friends, visits, or scores feature.** Not deferred — refused, with the
  measurement attached.
- **No parity claim.** Nothing here executes against the legacy server.
- **No roadmap change.** M11's classification advances; M11's exit criterion is a
  separate judgement that this proposal does not assert is met.

## Claim limits

Absence of a token is not absence of a feature: the Flash client may have held
friends and scores entirely client-side, which would leave no server branch ever
to exist. That is **unverifiable from the preserved oracle** — the same limitation
that made M10's exit criterion unsatisfiable. The uniform-empty finding is a
**corpus** fact about 33 documents, not a claim about all players.
