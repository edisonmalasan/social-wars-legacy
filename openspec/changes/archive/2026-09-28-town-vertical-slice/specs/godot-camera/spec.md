# Spec Delta

## MODIFIED Requirements

### Requirement: Camera controls scaffold
The client SHALL provide a `Camera2D`-based camera-controls component (`scripts/camera_controls.gd`) with explicit committed view state: at creation the view SHALL sit at the default world position with zoom level 0 and factor 1.0, with world bounds unset; zoom SHALL be discrete levels 0 through 2 over the fixed factor table `1.0`, `2.0`, `4.0`, with the component's committed factor and the node's own zoom always in agreement; `zoom_in()` and `zoom_out()` SHALL return explicit `{ok, error}` results and SHALL fail closed with a named error that leaves position, level, factor, and node zoom unchanged when already at the maximum or minimum level; `pan_by(world_delta)` SHALL return an explicit `{ok, error}` result, SHALL reject the zero vector and any non-finite component with a named error that leaves the position unchanged, SHALL, when world bounds are committed, fail closed with a named error (position unchanged, no notification) whenever the requested delta would move the committed position outside those bounds, and SHALL otherwise commit exactly the requested world delta; world bounds SHALL be settable and clearable through explicit `{ok, error}` results that fail closed with a named error on a non-finite or empty rectangle leaving bounds and position unchanged, that clamp an out-of-bounds committed position to the nearest point inside the new bounds committing exactly one position correction (emitting exactly one pan notification carrying the correction delta) while a position already inside commits the bounds with no movement and no notification, and that when cleared restore the unbounded contract with no movement and no notification; bounds SHALL NOT affect zoom level, factor, or node zoom; getters SHALL reflect only committed state, including the committed bounds; and the component SHALL NOT read wall-clock or time services, perform transport or persistence, load content, reference legacy protocol or Flash-related primitives, or depend on any other script or autoload.

#### Scenario: Start at the default view
- **WHEN** the component is created and no control has been applied
- **THEN** the view reports the default world position with zoom level 0, factor 1.0, and the node's zoom exactly `(1, 1)`, and reports no world bounds

#### Scenario: Zoom one level at a time, fail closed at the bounds
- **WHEN** zoom-in is requested until the maximum level and zoom-out is then requested past both extremes
- **THEN** each valid request advances exactly one level with the table factor reflected in both the committed factor and the node's zoom, and each out-of-bounds request fails with an explicit error leaving level, factor, node zoom, and position unchanged

#### Scenario: Pan by a world delta
- **WHEN** `pan_by` receives a finite nonzero world delta
- **THEN** the request succeeds and the committed position moves by exactly the requested delta, verified cumulatively across consecutive pans

#### Scenario: Reject an invalid pan
- **WHEN** `pan_by` receives the zero vector, a NaN component, or an infinite component
- **THEN** each request fails with an explicit error and the committed position is unchanged

#### Scenario: Notify only on successful change
- **WHEN** a zoom or pan request succeeds, or a request is rejected or motion carries no movement
- **THEN** each success emits exactly one corresponding notification whose payload is the committed change (the new zoom level, or the requested world delta), and every rejection or no-op emits nothing

#### Scenario: Pans that would leave the world bounds fail closed
- **WHEN** world bounds are committed and `pan_by` receives a finite delta whose result would fall outside them
- **THEN** the request fails with an explicit named error, the committed position is unchanged, no notification is emitted, and a pan that stays inside the bounds still commits exactly the requested delta

#### Scenario: Setting bounds clamps an out-of-bounds position once
- **WHEN** `set_world_bounds` commits a rectangle that excludes the current position, and is then applied again with the position already inside
- **THEN** the first call commits exactly one position correction into the rectangle with exactly one pan notification carrying that correction delta, and the second call commits the bounds with no movement and no notification

#### Scenario: Clearing bounds restores unbounded panning
- **WHEN** bounds are cleared after a rejected out-of-bounds pan
- **THEN** the clear succeeds with no movement and no notification, and the same delta that was previously rejected now commits exactly

#### Scenario: Reject an invalid bounds request
- **WHEN** `set_world_bounds` receives a rectangle with a non-finite component or an empty extent
- **THEN** each request fails with an explicit named error and both the committed bounds and position are unchanged
