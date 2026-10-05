# godot-damage

## Purpose

Deliver the M10 `damage` line. The **refusal is the finding**: there is
nowhere in a save row to store damage. What the line delivers instead is the one
real combat-adjacent surface the preserved server actually writes -- the
`privateState.magics` ledger, moved by `buy_magic` and `use_magic` -- with the
counter transition derived server-side from a validated magic identity, a
client-sent count refused **by name** before dispatch, the recorded literal cap
applied without clamping a counter that already exceeds it, the absent effect
magnitudes named rather than synthesized, the zero-consumer damage vocabulary
reported and never used, and an executed-legacy fixture captured against the one
committed village document with a non-empty magics ledger, its seven recorded
divergences carried as divergences and never as parity.

## Requirements

### Requirement: A magic counter transition is derived server-side from a validated identity, and the delivered surface is a counter rather than damage

The compatibility service SHALL expose a magic-counter operation whose request
carries a **validated magic identity** and an action, and which derives the
resulting counter transition **from its own recorded state**. The service SHALL
NOT accept a client-supplied count, delta, or resulting value.

The delivered surface SHALL be the counter transition and **nothing else**. The
service SHALL NOT resolve, compute, apply, or store damage, and SHALL NOT apply
any magic effect to any unit, because the preserved server has no damage rule to
reproduce and no committed amount from which to derive one. The operation's
successful response SHALL carry the server-derived transition and SHALL NOT echo
any client-supplied value it ignored.

A client-supplied count, delta, or resulting value SHALL be refused with a named
code, an empty payload, and no change to the recorded state.

#### Scenario: The client sends an identity and an action only

- **WHEN** a magic-counter operation is requested
- **THEN** the request carries a magic identity and an action and no count, delta, or resulting value, and the service derives the before value, the after value, and the change from its own recorded state

#### Scenario: A client-dictated count is refused

- **WHEN** a magic-counter request carries a count, a delta, or a resulting value
- **THEN** the operation is refused with a named code, an empty payload, and no change to the recorded state

#### Scenario: No damage is resolved by any delivered code

- **WHEN** the delivered implementation is inspected
- **THEN** it contains no helper capable of computing a damage amount, a hit-point value, attack or defense arithmetic, a multiplier, a mitigation, or a combat outcome, and this absence is enforced by a guard that fails when such a helper is introduced

### Requirement: An identity outside the committed magic table is refused, and the legacy acceptance of arbitrary identities is recorded as a divergence

The operation SHALL validate the requested identity against the **committed
magic table** and SHALL refuse an identity absent from it with a named code, an
empty payload, and no change to the recorded state. Validation SHALL treat an
identity whose string form differs from the committed key as a **different**
identity rather than coercing it.

The preserved server performs no such validation: it accepts an identity outside
the committed table and creates a ledger entry for it, and it keys the ledger on
the identity's **string form**, so a numeric identity sent as a float produces a
**distinct** ledger key. The service SHALL record both differences as
**divergences**, and SHALL NOT report them as parity.

#### Scenario: An identity outside the committed table is refused

- **WHEN** a magic-counter request names an identity absent from the committed magic table
- **THEN** the operation is refused with a named code, an empty payload, and no ledger entry created

#### Scenario: A non-canonical identity form is not coerced into the committed key

- **WHEN** a magic-counter request names an identity whose string form differs from a committed key while denoting the same spell
- **THEN** the operation refuses it rather than resolving it to the committed key, and the difference from the preserved server is recorded as a divergence

### Requirement: The two legacy counter asymmetries are refused rather than reproduced, and recorded as divergences

The operation SHALL NOT reproduce either preserved-server counter asymmetry. It
SHALL NOT grow a counter without bound, and SHALL NOT reduce a counter that
already exceeds the cap.

The preserved server's two adjacent branches disagree: one **adds** a capped
amount and so is **unbounded**, while the other **assigns** a capped value and so
can **reduce** a counter, destroying owned charges on a command whose own
recorded message claims the opposite. Executed against a committed corpus, the
additive branch crossed the cap and continued climbing, and the assigning branch
turned a counter of 113 into 50.

The service SHALL record both differences as **divergences**, SHALL record the
difference between the two preserved branches **separately** from the difference
between the service and the preserved server, and SHALL NOT report any of them as
parity.

A third divergence follows from the same reading and SHALL be recorded with them:
both preserved branches take their `else` arm for an identity with **no** recorded
entry and write that entry at **zero**, so the preserved server's own
"acquire a spell you hold none of" path increments **nothing** at all, while the
service reads an absent entry as zero charges and increments it. This was found
by tracing the live path rather than by reading the branches, and it is the
divergence a live phase against the fresh-player corpus reaches on its **first**
request, because that corpus's ledger is empty.

#### Scenario: The counter never grows past the cap

- **WHEN** a magic-counter operation is applied repeatedly to one identity
- **THEN** the counter rises to the cap and stops, and repeated application does not push it beyond the cap

#### Scenario: The counter is never reduced by an operation

- **WHEN** a magic-counter operation is applied to an identity whose counter already stands at the cap
- **THEN** the counter is unchanged, and it is never reduced below its prior value

#### Scenario: A recorded counter already above the cap is refused, not clamped and not left alone

- **WHEN** a magic-counter operation is applied to an identity whose recorded counter is **already greater** than the cap
- **THEN** the operation is refused with a named reason, the recorded state is reported rather than rewritten, and no stored resource moves

This is required because the obvious formula is wrong in the dangerous direction:
`min(cap, before + 1)` applied to a recorded counter of 113 **returns the cap**,
which is precisely the charge-destroying decrease this requirement exists to
refuse, wearing the service's own clothes. Clamping would reproduce the defect,
and leaving the value unchanged would answer success for an operation that did
nothing, so the recorded state is refused instead and the divergence is
recorded.

#### Scenario: The two divergences are recorded separately

- **WHEN** the recorded behaviour is compared against the executed preserved-server behaviour
- **THEN** the difference between the preserved server's two branches and the difference between the service and the preserved server are each recorded as divergences, and none is reported as matching parity

### Requirement: Every refusal resolves before any ledger write, so a refused request leaves the recorded state byte-identical

The operation SHALL complete **all** validation — structural, content, and
identity — **before** any ledger entry is created or modified, so that a refused
request provably leaves the whole recorded document byte-identical.

The preserved server's ordering cannot be reproduced because it performs no
validation at all; the ordering requirement therefore exists to make the
service's refusals safe rather than to match a recorded ordering.

#### Scenario: A refused request leaves the document byte-identical

- **WHEN** a magic-counter request is refused for any reason
- **THEN** the whole recorded document is byte-identical to its state before the request, including the ledger and every other key

#### Scenario: Validation ordering is asserted structurally

- **WHEN** the delivered implementation is inspected
- **THEN** every validation precedes the ledger write, and the delivered module's function inventory is pinned whole so a reordering fails the suite

### Requirement: No price is charged, and the two-part post-execution proof makes that non-tautological

The operation SHALL charge **no** resource. Every action SHALL carry a
two-part post-execution proof: the ledger's addressed counter moved by **exactly**
the amount the unchanged preserved branch writes, **and** **every** stored
resource is unchanged.

The second half SHALL compare the **complete** stored resource set the service
exposes, which is **eight** slots — the seven on the map plus the eighth stored
resource that lives in private state and that no branch writes — and SHALL NOT
compare a subset.

The first half SHALL **not** assert that the ledger equals the service's derived
transition. That assertion is impossible by construction, because the service is
required to refuse both preserved asymmetries while the preserved dispatcher is
left unchanged and therefore still writes its own numbers. The requirement
therefore pins what **actually executed**: the recorded value equals the
unchanged branch's own arithmetic, every unaddressed entry is byte-identical and
keeps its recorded position, and a created key is appended. The derived
transition SHALL be reported beside the recorded one, with an explicit statement
of whether they agree. **Verifying the preserved outcome is not reproducing it:**
the derived number is never written to a save.

The preserved server charges nothing, measured across twelve executed
transactions in which **no** resource slot moved and the mana value held steady
across a use command, so any price would be invented.

#### Scenario: The counter moved by exactly what the preserved branch writes

- **WHEN** a magic-counter operation succeeds
- **THEN** the ledger value for the addressed identity equals the unchanged preserved branch's own result for the recorded prior value, every unaddressed entry is byte-identical and in its recorded position, and the response reports the derived value beside the recorded one together with an explicit statement of whether they agree

#### Scenario: The derived and recorded values disagree, and that is reported rather than hidden

- **WHEN** the derived transition deliberately disagrees with the preserved branch — which it does for every `buy` and for every absent identity
- **THEN** the operation still succeeds, the response states the disagreement plainly, and the disagreement is recorded as a divergence rather than presented as parity

#### Scenario: Every stored resource is unchanged

- **WHEN** a magic-counter operation succeeds
- **THEN** all eight stored resource slots are byte-identical to their values before the request, including the mana and private-state energy slots

### Requirement: The counter cap is the recorded literal it is, and the rejected content derivation is retained rather than silently chosen

The operation SHALL apply the cap as the **hardcoded literal recorded in the
preserved source**, and SHALL NOT derive it from committed content.

That literal's value also occurs among the committed magic values, which is a
coincidence of the value distribution and **not** its provenance; the preserved
source contains no reference to any content when it applies the cap. The design
retains the rejected content-derivation alternative explicitly, so that a later
reader cannot mistake the coincidence for a derivation.

#### Scenario: The cap is the recorded literal

- **WHEN** the delivered implementation applies the cap
- **THEN** it uses the literal recorded in the preserved source, and no committed magic value is read to obtain it

#### Scenario: The rejected derivation is retained in the record

- **WHEN** the design is read
- **THEN** it names the content-derivation alternative it rejected and why, rather than leaving only the chosen option

### Requirement: The committed magic content is reported verbatim, and the absent effect magnitude is named rather than synthesized

The operation SHALL report the committed magic content **verbatim**, carrying
each entry's recorded cost, level, and target fields exactly as normalized, and
SHALL derive **no** value from it.

Where a committed description promises an effect whose magnitude is **not
committed**, the absence SHALL be named explicitly and no magnitude SHALL be
synthesized. At least one committed entry's description promises to increase
attack and life while committing **no** multiplier, no factor, and no amount; the
suite SHALL assert that no delivered code produces one.

#### Scenario: Committed content is reported verbatim

- **WHEN** the committed magic content is projected
- **THEN** every entry's recorded fields are reported exactly as normalized, with no value computed from them and none substituted

#### Scenario: An absent effect magnitude is named, not synthesized

- **WHEN** the committed entry whose description promises an attack and life increase is projected
- **THEN** the absence of any committed magnitude is reported, and no delivered code computes a multiplier, factor, or amount for it

### Requirement: The damage vocabulary that does exist is reported and never used

The operation SHALL report the damage vocabulary the preserved server retains —
the self-damage and enemy-damage cost tokens, the attack-reset and
spy-reset private-state instants, the branch whose entire body is a recorded
message, and the combat-named mission types — and SHALL **not** use any of them
to compute a value, gate an operation, or derive a limit.

The attack-reset instant has exactly **one** occurrence in the whole preserved
server and that occurrence is a write; it has **no** reader, so no attack
allowance, limit, window, or reset rule exists to reproduce, and none SHALL be
invented.

#### Scenario: The vocabulary is reported and never consumed

- **WHEN** the operation is implemented
- **THEN** the cost tokens, the two reset instants, the no-op branch, and the combat-named mission types appear only as reported content, and none of them is read to compute a value, gate an operation, or derive a limit

#### Scenario: No attack allowance is invented

- **WHEN** the attack-reset instant is projected
- **THEN** it is reported as an instant with a single write site and no reader, and no allowance, limit, window, or reset rule is derived from its name
