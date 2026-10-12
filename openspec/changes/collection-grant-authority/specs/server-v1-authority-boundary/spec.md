# Spec Delta

## Purpose

Amends the boundary capability that line 1 delivered, because this line's measurement
changes one of its claims. `server-v1-authority-boundary` specifies that the boundary is
demonstrated end to end by **one** transaction, `collect`, and that is no longer the
strongest true statement available: `complete_collection` has been measured to be a
**stronger** worked example in one specific respect, and the amendment records that
without discarding the first.

The change is a widening, not a correction. Every requirement line 1 specified stays
true; only the claim about how many worked examples exist is restated.

## MODIFIED Requirements

### Requirement: `collect` demonstrates the boundary end to end

The collection transaction SHALL be implemented on the v1 boundary as the first vertical
slice, deriving its payout server-side and refusing its documented invalid cases through
the typed channel. Its post-execution proof SHALL check both that the collection instant
moved forward **and** that every stored resource changed by exactly the derived amount,
so that a derivation which moved nothing could not pass as success.

`collect` is chosen because the Compatibility API's own collection is already proven
against a captured executed-legacy fixture, so v1's first slice is measured against an
existing oracle rather than a new one.

The boundary SHALL be demonstrated end to end by **at least two** transactions, and the
second SHALL exercise at least one rule the first does not.

`collect` remains the worked example of a **derived payout**: the server derives what a
`collect` *yields* from committed income content, and the client selects only which row
to collect.

`complete_collection` is the worked example of a **derived grant behind derived
preconditions**: the server derives what the collection *yields* from the committed
prize, whether the caller *may* claim it from the committed requirement list, what it
*costs* from the committed price, and whether it *has already* been claimed from the
recorded ledger. Each of those four is a rule `collect` does not exercise.

Both SHALL derive every resource movement from committed content, SHALL refuse a
client-supplied resource delta outright, and a refusal in either SHALL move nothing.

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

#### Scenario: A refused collection completion moves nothing

- **WHEN** a collection completion is refused for any reason
- **THEN** storage, the collection ledger, and every stored resource are byte-identical to before
- **AND** no partial grant survives the refusal