# Design

## Context

See `proposal.md` — Why, and `docs/legacy-m11-social-rewards.md` for every
measured figure. Only the constraints that shaped the approach are restated here.

The assist key already reaches the client: `town_state.gd` reads the row
attribute bag from map-row slot 6 and carries `attr["si"]` through verbatim, so
`/v0/bootstrap` serves it. Two capabilities already touch its neighbourhood —
`godot-stored-item-placement` derives the key at placement from the committed
`friend_assistable` flag, and `godot-social-state` records the
`set_resource_allies` instant stamp. Neither owns the lifecycle.

Three constraints bind the implementation shape:

1. `test_project_scope.gd`'s `FORBIDDEN` table is a **raw-substring** scan over
   project sources and `test_town_gate.gd` holds a second one. A deliverable
   cannot quote a forbidden literal even to document that it avoids it, so module
   prose describes the transport and cites `templates/play.html:99` and
   `server.py:91` instead. `godot-friends` discovered this by failing the
   battery on it.
2. A MODIFIED delta replaces a requirement **in full**, so every delta line was
   diffed against a wrap-normalised copy of the original to prove no sentence was
   weakened.
3. Every committed figure must be **re-derived per run**, not pinned, or a legacy
   edit silently contradicts the suite.

## Goals / Non-Goals

**Goals**

- A typed, read-only, fail-closed projection of one recorded attribute-bag key.
- A dispatcher table quoting the three branches' effects with `reproduced: false`.
- A corpus measurement re-derived per run against an explicit document allow-list.
- Ownership links **asserted** (recipient capability exists, delivered module
  names the same committed field) rather than assumed.
- Every refusal enforced by a guard **proven to fail** by injection.

**Non-Goals** — all carried in the specs rather than restated: no route, no
compatibility change, no reward decoding, no element decoding, no ordinal
position for the gift fields, no windowed capture (nothing is rendered).

## Decisions

**D1 — No route, and `apps/compat-api/**` is untouched.**

`attr["si"]` already arrives on `/v0/bootstrap`, so a projection needs no new
transport. The compatibility suite therefore holds at its **3077** baseline as a
*verified* figure — re-run, not skipped — which is what makes the absence of a
compatibility change evidence rather than an omission.

*Rejected:* a `/v0/assist` route. It would give the client a way to write a key
whose only appended value is a sentinel meaning *"buying instead of hiring
friends"*, granting nothing and charging nothing. A client affordance for a
transaction with no consequence is the surface this capability exists to refuse,
and `godot-darts` set the precedent of a state-mutating capability shipping no
live phase for exactly this reason.

**D2 — No executed-legacy fixture, recorded as a decision.**

`buy_si_help` creates the key when absent, so a capture **is** reachable — unlike
the M8 refusal lines, where absence was a corpus fact. The reason not to is
scope: the transaction grants nothing, charges nothing, appends a fixed sentinel,
and needs no fixture to establish any of that. The requirement records both halves
so the absence cannot later be misread as unreachable.

**D3 — Two modules, not one.**

`construction_assist_state.gd` holds the typed record and the fail-closed
projection; `assist_transitions.gd` holds the recorded dispatcher table as data.
Split because the table is a **census of source text** and the projection is a
**projection of payload** — a single module would invite the first to be mistaken
for behaviour, which is the exact confusion the naming discipline exists to
prevent.

*Rejected:* one module. Simpler, and it would have let the dispatcher's quoted
`[0]` append sit beside live projection code where a reader could mistake the
former for something the client does.

**D4 — Element types are reported, never refused.**

A recorded element of an unexpected type is passed through with its type
intact. Refusing it would invent a type rule the oracle does not have — and the
corpus's only recorded element is an `int`, so a type guard could only ever fire
on data this oracle cannot produce. The three refusals are exactly the shapes
whose *meaning* is unreadable: absent bag, non-object bag, non-list value.

**D5 — A missing key is distinct from an empty list.**

`buy_si_help` creates `[0]` lazily and `finish_si` deletes it, so absent and
empty are produced by different branches and are different recorded states.
Collapsing them would report a deleted key as a resolved empty one.

**D6 — The corpus allow-list is an explicit list, not a directory walk.**

The canonical corpus is 10 named documents. A naive walk would sweep fixture step
documents and build caches into the counts and produce a number that is right by
accident. The allow-list is a named constant so a new committed save document
cannot silently change the denominator.

**D7 — Guards are proven by injection, and the harness is hardened.**

The refusals are prose, and prose cannot fail. Each is therefore backed by a
guard proven to fail against a **byte-identical** copy, with the restored file's
SHA-256 recorded in the report. The guard set is a **whole-function inventory
pin** (the real gate) plus a **case-insensitive substring** reserved-name match
(the belt) — the belt earns its place because `godot-friends` found suffixed
helpers (`roster_order_by_xp`) that an exact-name check passes. The inventory is
compared as a sorted unique set with the declaration count pinned separately,
because five of `godot-friends`' declarations appear twice and a positional
comparison fails against the delivered module itself.

*Rejected:* trusting the guard. Never shown failing is not a guard.

**D8 — Harness defects found by the friends line are designed against, not
rediscovered.** Every restore asserts zero NUL bytes and a final newline, aborts
loudly when an injection anchor is absent, and `git diff --numstat
--ignore-cr-at-eol` plus `git status --short` must equal their pre-probe values.

**D9 — The gift fields get no ordinal.**

Four earlier lines named successive zero-consumer discoveries "the sixth",
"the seventh", "the ninth", "the tenth" — each over a **different scope**, with no
reconciled census in the repository. `godot-unit-behaviors` was itself corrected
for exactly this. So this capability reports the measured fact and lists its
overlap, and adds `giftable` — in no census at all — as a recorded row while
completing that capability's units-only `gift_level` row.

**D10 — Reports are deterministic and written in LF.**

Godot writes LF; the working tree is CRLF under `core.autocrlf=true`. Evidence
digests are taken over the **committed Git blob** form, and byte counts are stated
"in LF form", as prior lines recorded.

## Risks / Trade-offs

**[The spec search instrument under-counts on hyphen-wrapped terms]** → A raw
substring search reported a term absent that was present as `friend-` + newline +
`assistable`, and collapsing whitespace does not fix a hyphenated split. Any
future line searching the specs must unwrap the line, not collapse it. Recorded
here because it nearly caused this change to amend a requirement for a reason that
does not exist in it.

**[A vacuous comparison can print as a finding]** → The first re-measurement
matched 0 ids and then reported `low+3000 == high set: True` over two empty
lists. Every comparison this suite reports is asserted non-vacuous — a count of
zero over an empty input fails rather than passes — because that is the same
tautology class `godot-friends` closed.

**[The recorded `0` sentinel invites a decoded meaning]** → Guarded by a
reserved-name list covering assist, reward, friend, gift and decode vocabulary,
matched case-insensitively and by substring, and by asserting no delivered
identifier is named after a refused behaviour.

**[Adding client sources raises sibling suites that walk the source tree]** →
Expected and accepted: `test_project_scope.gd`'s allow-list grows, and
`test_unit_collection.gd`-style tree walks increase in count. Both are recorded
with before/after numbers rather than treated as failures.

**[Two capabilities can drift on the same key's creation]** → Prevented by D1's
ownership assertion: this capability checks the owning capability's spec exists
and that the delivered derivation names the same committed field, so a rename on
either side fails rather than orphaning the link.

**[The three unflagged `si` carriers tempt a flag guard]** → Recorded, not
enforced. Enforcing `friend_assistable` client-side would refuse two committed
corpus rows, and the legacy branch has no such check, so the divergence is
recorded rather than closed.

**[`/v0/bootstrap` is a state-mutating-looking surface for a granted nothing]** →
Not applicable: no client affordance is delivered, and nothing in the delivered
client can write the key.
