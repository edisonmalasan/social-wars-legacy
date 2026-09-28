# Spec Delta

## ADDED Requirements

### Requirement: Windowed boot-to-town transition

After the boot scene reaches its ready state with successfully validated typed bootstrap data, a windowed run SHALL hand that already-validated state to the town scene and replace the boot view with the town view — without issuing a second bootstrap request (the legacy bootstrap mutates `last_logged_in`, so exactly one request per launch is part of the contract) and without the raw transport payload reaching presentation code; a handoff that cannot build a valid town state SHALL surface an explicit error naming the failure in place of the view, never a blank window and never a partially rendered town; and a headless run SHALL never enter the town scene, keeping the existing headless marker, summary, error-state, and exit-code contract byte-for-byte unchanged.

#### Scenario: Exactly one bootstrap per launch into the town

- **WHEN** a windowed run completes bootstrap successfully against either GameApi implementation
- **THEN** exactly one bootstrap request was made, the boot view is replaced by the town view rendering that save's terrain, objects, and HUD, and the committed evidence capture records the view

#### Scenario: Headless boot behavior is unchanged

- **WHEN** the headless boot verification runs (success and unreachable-endpoint cases)
- **THEN** its markers, displayed summary, error states, and exit codes are exactly as before, and no town scene is instantiated

#### Scenario: Fail explicitly instead of a blank window

- **WHEN** the handed state cannot build a valid town state at transition time
- **THEN** an explicit error naming the failure replaces the view, and no partial town is shown
