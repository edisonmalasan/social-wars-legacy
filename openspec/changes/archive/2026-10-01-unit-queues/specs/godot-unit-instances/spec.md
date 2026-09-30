# Spec Delta

## MODIFIED Requirements

### Requirement: The production-queue keys are reserved, not implemented

The client SHALL declare the production-queue attribute keys `nu`, `ts`, and `ui` as a
named reserved inventory with their established meanings and their established teardown
rule — the count, the start instant, the optional queued unit id, and the deletion of all
three together when the count reaches zero. That inventory is **fulfilled by the
`godot-unit-queues` capability**, which projects those three keys as a typed queue value
and records the three legacy commands' effects; the keys are therefore no longer merely
reserved, while this capability's own refusal of queue **behaviour** stands unchanged. Reading whether a row carries these keys is
permitted projection; this capability SHALL add **no** queue increment, no decrement, no
timestamp write, and no queue projection, and SHALL implement no training, production, or
queueing behaviour.

#### Scenario: The reserved inventory is named and typed

- **WHEN** the reserved attribute-key inventory is inspected
- **THEN** it names `nu`, `ts`, and `ui` with their established meanings and the teardown rule, and the meanings are recorded as established from committed source

#### Scenario: No queue behaviour is implemented

- **WHEN** this capability's client surface is inspected for queue mutation
- **THEN** it offers no increment, no decrement, no timestamp write, and no queue projection, and training, production, and queueing remain undelivered later deliver lines

#### Scenario: Presence is readable without behaviour

- **WHEN** a row is projected that carries the reserved keys
- **THEN** their presence and committed values may be reported as content, and no queue state is computed from them

#### Scenario: The reservation is fulfilled elsewhere, not abandoned
- **WHEN** the reserved-key inventory is read
- **THEN** it names `nu`, `ts`, and `ui` with their established meanings and the teardown rule,
  and points to the `godot-unit-queues` capability that projects them, while this capability
  still implements no queue mutation, no training, and no production
