# Spec Delta

## MODIFIED Requirements

### Requirement: Minimal render-verification Godot project
The system SHALL provide a Godot project under `apps/client-godot/` configured for the pinned Godot 4.7.2.stable engine, its contents governed by an enforced allow-list scope test: the render-verification content (first-render scene, conversion-v1 package loader, comparator, and their tests) SHALL remain present and passing; the cross-cutting foundation systems introduced by the compatibility boot, content-registry, and session work (`GameApi` autoload with its `LegacyV0Api`/`FakeApi` implementations, boot data types, the `ContentRegistry` autoload with its content and asset-resolution script and tests, the `Session` autoload with its scaffold script and tests, and the boot scene) SHALL be allow-listed explicitly; and every other game system (`GameClock`, camera controls, UI foundation) SHALL remain absent until its own change adds it. No Flash-related runtime and no legacy protocol token (`command.php`, AMF, FlashVars, legacy form encoding) SHALL appear in project scripts. The project SHALL document the pinned engine version.

#### Scenario: Boot with the pinned engine
- **WHEN** the project is started with Godot 4.7.2.stable
- **THEN** it loads without version or configuration errors, starts the boot scene as the main scene, and keeps the render-verification scene runnable as its own scene

#### Scenario: Remain within the verification scope
- **WHEN** the project configuration and scene tree are inspected
- **THEN** only allow-listed foundation and verification files are present, exactly the three allow-listed autoloads (`GameApi`, `ContentRegistry`, and `Session`) are registered, no system outside the allow-list (camera, UI foundation, clock) exists, no legacy protocol token appears, and the first-render verification scene and tests remain intact
