# Spec Delta

## MODIFIED Requirements

### Requirement: The nineteen measured social fields are delivered with their recorded storage location
The projection SHALL cover exactly the nineteen fields measured by the committed
investigation, each reported with the document or map it is stored in, and SHALL
NOT add a field that the investigation did not measure. Of those nineteen,
**seventeen** are social state; the remaining two — `timeStampEndPremium` and
`crossPromotionsFinished` — SHALL be reported as **foreign** to this capability and
named as owned by `godot-darts`, because the first records a paid purchase with a
server-derived value rather than a social fact, and the second records a
cross-promotion flag. The projection SHALL NOT present either as social state, and
SHALL NOT describe the field set as nineteen social fields.

#### Scenario: Review field coverage
- **WHEN** the projection is compared with the investigation's measured field list
- **THEN** all nineteen measured fields are present with their recorded storage location
- **AND** no unmeasured field is present

#### Scenario: Review the two foreign fields
- **WHEN** a maintainer reviews the field set
- **THEN** `timeStampEndPremium` and `crossPromotionsFinished` are reported as owned by another capability rather than as social state
- **AND** the delivered field set is described as seventeen social fields plus two foreign ones
- **AND** the named owning capability is verified to exist, so the hand-off is not an orphan

### Requirement: The one real social-state writer is recorded with its client-sent value and is not reproduced
`set_resource_allies` SHALL be reported as the only branch writing social state,
writing `resourceAlliesMarket` from a client-supplied argument, and as stamping the
addressed row's recorded instant. The capability SHALL NOT deliver an endpoint that
performs either write, and SHALL NOT derive meaning from the recorded instant stamp.
The premium-account branch SHALL NOT be reported as a client-sent social writer:
it is owned by `godot-darts`, and it writes its recorded instant **twice** in one
branch with a value derived server-side from the committed schedule, so this
capability's record of it SHALL carry neither a client-sent value nor a
single-write description.

#### Scenario: Review the recorded writer
- **WHEN** a maintainer reviews the only branch that writes social state
- **THEN** it is identified as writing the market resource from a client-supplied value
- **AND** the row instant stamp is reported with no semantics derived from it
- **AND** no delivered route performs either write

#### Scenario: Review the premium record's corrected description
- **WHEN** a maintainer reviews how the premium-account branch is recorded here
- **THEN** it is identified as owned by another capability rather than as a client-sent social writer
- **AND** this capability asserts neither that its value is client-sent nor that the branch performs a single write
