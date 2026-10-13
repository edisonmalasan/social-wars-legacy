# server-v1-authority-boundary

## Purpose

Defines where authority lives in Server v1: every resource movement is derived by the
server from player intent, refusal is a typed decision the domain makes and the client
receives, and transactions demonstrate both end to end. This is the boundary the legacy
branches still lacking modern authority will land in, so it is specified before any of
them are ported rather than after.

Three figures are corrected here rather than inherited, because a spec is the source of
truth and a known-falsified number in one is worse than an absent one. "One transaction"
was true when this capability was written and is true of neither end: `collect` and
`complete_collection` are now both specified below. "The 39 legacy branches with no
modern route" was `tools/route-coverage`'s **citation** count promoted into a coverage
claim. **The correction that replaced it was itself wrong by one.** It read **40** of the
63 named branches as dispatched by a v0 route and **23** as dispatched by none, on the
strength of `docs/legacy-m13-unrouted-branches.md`, whose route table listed
`buy_mana_new` under `/v0/magic`. **`buy_mana_new` is not dispatched.** `magic_envelope`
declares `MAGIC_COMMANDS` as the two-tuple `(buy_magic, use_magic)`, parks
`buy_mana_new` as `NO_OP_COMMAND` with the note that it is "**not** delivered", and its
only other occurrence sits inside `REPORTED_DAMAGE_VOCABULARY`, whose own rule field
states that "none of it is read to compute a value, gate an operation, or derive a limit";
`compat_service.py` contains no occurrence of the name at all. This is the identical
situation to `push_queue_unit2` at `queue_envelope`, which the same document caught and
excluded by hand; the caution was applied to one parked branch and missed on the other.
The split is therefore **39**
dispatched by a v0 route and **24** by none. **4** branches have authoritative v1 routes,
leaving **59** without one; that figure is independent of routing and is unchanged. It is
restated because an investigation accompanying this correction proposed raising it to
**62** by subtracting a single authoritative branch, which would have been arithmetically
wrong in the other direction: `complete_collection` is authoritative too.
`tools/route-coverage` answers the question it was built to answer and was not changed;
it had already filed `buy_mana_new` under `branches_mentioned_by_name_only` with a
negation marker.

**A further correction, from the magic authority line.** `buy_magic` and `use_magic` are now
authoritative, which is what moves the pair **2**/**61** to **4**/**59**. The routed/unrouted split
of **39**/**24** is unchanged and is not restated as a new claim; `buy_mana_new` remains dispatched
by no v0 route, and `POST /v1/magic` cannot reach it either, because that route's operation
vocabulary is closed to two values. The change here is a **widening**: every requirement already
specified stays true, and the requirement below gains a third worked transaction covering the
case the capability never had - a transaction that moves **no** stored resource at all, whose
absence of a cost is itself proven rather than assumed.

## Requirements

### Requirement: Resource movement is server-derived from intent

A Server v1 request SHALL express **what the player wants to happen** and SHALL NOT
express **what it costs or what it yields**. No v1 request schema SHALL carry a
resource, experience, health, damage, or result delta, and the economy authority SHALL
derive every balance change from committed content and recorded state.

A request that attempts to carry such a delta SHALL be refused as a structural input
error, and SHALL NOT be clamped, coerced, or partially honoured. This is deliberately
stricter than the preserved server, which applies a client-supplied eight-slot resource
vector at dispatch for every command and clamps each slot at zero; the clamp is
recorded as the behaviour being replaced, not reproduced.

#### Scenario: An intent-only collection moves resources by the derived amount

- **WHEN** a player sends a collection intent naming an addressable placed row
- **THEN** the server derives the payout from committed content and recorded state
- **AND** every stored resource changes by exactly the derived amount
- **AND** the response reports the derivation rather than echoing a client figure

#### Scenario: A request carrying a resource delta is refused

- **WHEN** a collection intent additionally carries a resource delta
- **THEN** the server refuses it as a structural input error
- **AND** every stored resource is unchanged
- **AND** no partial amount is applied

### Requirement: Refusal is a typed domain decision with a channel to the client

Refusal SHALL be a value the domain layer produces and the transport translates, not a
status code each route invents. A v1 route SHALL NOT be able to answer success for an
action the domain refused, and SHALL NOT be able to report a refusal the domain did not
produce.

The preserved server has no such channel: `server.py` returns `{"result": "success"}`
unconditionally after dispatch, so a branch's only way to decline is to print a log line
and return, invisibly to the client. v1 SHALL NOT reproduce that shape.

#### Scenario: A refused action is reported to the client

- **WHEN** the domain refuses an action for a named reason
- **THEN** the client receives a structured refusal naming that reason
- **AND** the client can distinguish it from a transport failure

#### Scenario: The transport cannot override a domain refusal

- **WHEN** the domain refuses an action
- **THEN** the route reports the refusal
- **AND** no success response is emitted for the same request

### Requirement: A refused action moves nothing

The server SHALL decide before it mutates. A refused action SHALL leave every stored
resource, every stored instant, and every stored placement byte-identical, and SHALL
NOT apply any part of the requested effect before deciding.

This inverts the preserved ordering, where `apply_resources` runs at `command.py:40`
and the first branch condition is tested at `:42` or later, so a command that is
subsequently declined has already had the client's vector applied.

#### Scenario: A refusal is byte-identical on the store

- **WHEN** an action is refused
- **THEN** the stored save document is byte-identical to its pre-request bytes
- **AND** no stored instant, placement, or balance moved

#### Scenario: Decision precedes mutation

- **WHEN** an action is refused for a content or state reason
- **THEN** the refusal was determined before any balance was written
- **AND** the response carries no partial result

### Requirement: `collect` demonstrates the boundary end to end

The collection transaction SHALL be implemented on the v1 boundary as the first vertical
slice, deriving its payout server-side and refusing its documented invalid cases through
the typed channel. Its post-execution proof SHALL check both that the collection instant
moved forward **and** that every stored resource changed by exactly the derived amount,
so that a derivation which moved nothing could not pass as success.

`collect` is chosen because the Compatibility API's own collection is already proven
against a captured executed-legacy fixture, so v1's first slice is measured against an
existing oracle rather than a new one.

The boundary SHALL be demonstrated end to end by **at least three** transactions, and
the second and third SHALL each exercise at least one rule the first does not.

`collect` remains the worked example of a **derived payout**: the server derives what a
`collect` *yields* from committed income content, and the client selects only which row
to collect.

`complete_collection` is the worked example of a **derived grant behind derived
preconditions**: the server derives what the collection *yields* from the committed
prize, whether the caller *may* claim it from the committed requirement list, what it
*costs* from the committed price, and whether it *has already* been claimed from the
recorded ledger. Each of those four is a rule `collect` does not exercise.

The magic counter transition is the worked example of a **derived state transition
that moves no stored resource**: the server derives the identity's new counter value
from its own recorded state and from a bound recorded in the preserved source, the
client selects only which committed magic the identity names, and no committed
price, mana cost, or effect magnitude is read to produce it. It demonstrates the
boundary's refusal half on a transaction whose preserved-server counterpart charged
nothing, because the only mechanism by which a legacy client could have paid was a
resource vector applied before the dispatcher opened.

All three SHALL derive every resource movement they make from committed content,
SHALL refuse a client-supplied resource delta outright, and a refusal in any of them
SHALL move nothing.

#### Scenario: A collected row advances its instant and pays exactly the derived amount

- **WHEN** a collection succeeds on an addressable row that has reached a committed rung
- **THEN** the row's recorded collection instant advances
- **AND** each stored resource changed by exactly the derived amount for the reached rung
- **AND** the response reports the rung the payout came from

#### Scenario: A collection below the first committed rung is refused

- **WHEN** a collection is requested on a row that has not reached a committed rung
- **THEN** the domain refuses it with a named reason
- **AND** the stored save document is byte-identical to its pre-request bytes

#### Scenario: A collection on a row under construction is refused in the service

- **WHEN** a collection is requested on a row carrying construction state
- **THEN** the domain refuses it with a named reason
- **AND** the row's construction instants are unchanged

#### Scenario: The boundary has two worked transactions, not one

- **WHEN** the boundary is exercised
- **THEN** both `collect` and `complete_collection` are specified end to end
- **AND** each derives every resource movement from committed content
- **AND** each refuses a client-supplied delta outright rather than clamping it

#### Scenario: The boundary has a third worked transaction that moves no resource at all

- **WHEN** the boundary is exercised
- **THEN** `collect`, `complete_collection`, and the magic counter transition are all specified end to end
- **AND** each derives every resource movement it makes from committed content
- **AND** the magic counter transition derives no cost, and the absence of that cost is itself proven rather than assumed
- **AND** each refuses a client-supplied delta outright rather than clamping it

#### Scenario: A refused collection completion moves nothing

- **WHEN** a collection completion is refused for any reason
- **THEN** storage, the collection ledger, and every stored resource are byte-identical to before
- **AND** no partial grant survives the refusal

#### Scenario: A transaction that derives no cost is still on the boundary

- **WHEN** a worked transaction charges nothing because the preserved server charged nothing and no committed content establishes a price
- **THEN** the absence of the charge is a specified property with a proof that asserts every stored resource is byte-identical
- **AND** a charge of any size on any stored resource fails that proof

### Requirement: v1 coexists with v0 and changes no v0 behaviour

The Server v1 surface SHALL be added alongside the Compatibility API. This change SHALL
NOT modify any v0 route's behaviour, SHALL NOT modify any v0 test's expectation, and
SHALL NOT re-point any delivered client capability from v0 to v1.

v0 is retired per domain, in later lines, only after v1 has demonstrated parity for that
domain against the existing executed-legacy fixtures.

#### Scenario: The Compatibility API is unchanged by this capability

- **WHEN** the v0 test suite runs against this capability's final state
- **THEN** every v0 route behaves and answers exactly as it did before
- **AND** no v0 route, envelope module, or fixture was edited

#### Scenario: The two surfaces are separately addressable

- **WHEN** a client is configured for v0 and one for v1
- **THEN** each reaches only its own surface
- **AND** neither surface reads the other's response shape

### Requirement: Server v1 is reachable only through the GameApi facade

The client SHALL reach v1 through the same facade every other delivered capability uses,
and v1 SHALL NOT require any client code outside that facade. A client SHALL NOT depend
on the legacy transport, and v1 SHALL NOT be reachable by any path that bypasses the
facade.

Registering v1 closes a recorded gap: the facade currently declares only a fake
implementation and the legacy v0 implementation, so no switch selects a v1 surface
because none exists yet.

#### Scenario: v1 is selectable through the facade

- **WHEN** the client is started with the v1 implementation selected
- **THEN** its requests reach the v1 surface through the facade
- **AND** no gameplay code required modification to route them

#### Scenario: The v0 and fake implementations are unaffected

- **WHEN** the client is started with the fake or the v0 implementation selected
- **THEN** its behaviour is exactly as before this capability

### Requirement: Unknown save fields survive the round trip

Server v1 SHALL preserve every field it does not understand when it reads and writes a
save document, and SHALL NOT silently drop, rename, or normalise an unrecognised field.
Preservation is required of the same committed save corpus the Compatibility API and
the preserved server read, so that a v1 transaction does not destroy evidence that
later migration analysis depends on.

#### Scenario: An unknown field survives a v1 write

- **WHEN** a v1 transaction writes a save document containing a field v1 does not model
- **THEN** that field is present with its original value after the write
- **AND** no other field was altered to accommodate it

### Requirement: Evidence distinguishes established behaviour from derived authority

Every v1 claim SHALL be labelled as **established** — observed in committed legacy
source or executed-legacy evidence — or **derived** — chosen by this design and never
observed from the Flash client. No v1 requirement SHALL assert a legacy amount, price,
or rule as observed when it is in fact derived, and the preserved server's
client-supplied behaviour SHALL be recorded as the thing being replaced rather than
reproduced.

#### Scenario: Derived authority is labelled as derived

- **WHEN** a v1 transaction derives a payout, price, or clamp
- **THEN** the committed record labels it derived and names the alternative rejected
- **AND** no document presents it as an observed legacy behaviour

#### Scenario: No legacy process executes to produce this evidence

- **WHEN** this capability's evidence is produced
- **THEN** no Flash, Ruffle, ActionScript, or browser runtime executed
- **AND** every network call was loopback
