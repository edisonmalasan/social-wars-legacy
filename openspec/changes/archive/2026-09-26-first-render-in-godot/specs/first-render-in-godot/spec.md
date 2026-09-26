# Spec Delta

## Purpose

Render the first converted building and unit packages in Godot as authentic frame-1 output with captured, programmatically compared screenshot evidence so the M4 exit criterion can be assessed without executing Flash or adding any game system.

## ADDED Requirements

### Requirement: Minimal render-verification Godot project
The system SHALL provide a Godot project under `apps/client-godot/` configured for the pinned Godot 4.7.2.stable engine, containing only render-verification content: no `GameApi`, `LegacyV0Api`, `ContentRegistry`, `Session`, `GameClock`, camera controls, UI foundation, network access, or backend integration. The project SHALL document the pinned engine version.

#### Scenario: Boot with the pinned engine
- **WHEN** the project is started with Godot 4.7.2.stable
- **THEN** it loads without version or configuration errors and exposes only the render-verification scene and scripts

#### Scenario: Remain within the verification scope
- **WHEN** the project configuration and scene tree are inspected
- **THEN** no M5 game-system autoload, scene, or script is present

### Requirement: Read-only conversion-v1 package loading
The system SHALL load `assets/converted/buildings/0001_house_1_m/package.json` and `assets/converted/units/10033_wild_elephant/package.json` read-only through their `conversion-v1` envelope, honoring `kind`, `legacy_id`, `content_version`, frame data, symbols, shapes, fills, and bitmaps, and SHALL fail with an explicit error on an envelope or field it cannot recognize rather than rendering partial or guessed output. Package files SHALL remain byte-identical before and after any run.

#### Scenario: Load the building package
- **WHEN** the loader reads the house package
- **THEN** it reports `converted_building` with `legacy_id` `0001_house_1_m` and resolves its shape, fill, and two bitmap files, and the package bytes are unchanged

#### Scenario: Load the unit package
- **WHEN** the loader reads the elephant package
- **THEN** it reports `converted_unit` with `legacy_id` `10033_wild_elephant`, inventories all 7 sprite timelines and 28 shapes, and the package bytes are unchanged

#### Scenario: Reject an unrecognized envelope
- **WHEN** a package's envelope, `kind`, or required fields are missing or foreign
- **THEN** loading fails with an error naming the package and no render output is produced from it

### Requirement: Frame-1 placement resolution
The system SHALL resolve frame-1 renderable content by walking `main` placements into sprite timelines and their frame-1 placements down to shapes, SHALL select fills through `fill_refs` where the package provides it and SHALL never select an unreferenced `65535` placeholder fill, and SHALL fail with an explicit error when a placement references a character the package does not contain. Transforms SHALL be applied as the package expresses them; where placements carry no transform fields, identity is used.

#### Scenario: Resolve the house
- **WHEN** frame-1 resolution runs on the building package
- **THEN** its single shape at bounds 216×144 px with its referenced bitmap fill is selected

#### Scenario: Resolve the elephant
- **WHEN** frame-1 resolution runs on the unit package via `main` → sprite 63
- **THEN** the frame-1 shape chain is selected using referenced fills only, with every `65535` placeholder fill excluded

#### Scenario: Fail on a broken placement chain
- **WHEN** a placement names a `character_id` absent from the package
- **THEN** resolution fails with an error naming the package, sprite, and character id, and nothing is rendered for it

### Requirement: Authentic bitmap rendering
The system SHALL render each resolved shape as its package bounds textured by the referenced bitmap, with the raw SWF fill matrix decoded so the bitmap maps onto the shape bounds, and with JPEG color and alpha PNG composited into straight-alpha pixels. Both the house and the elephant frame-1 output SHALL be drawn side by side on a neutral background at their authentic pixel dimensions.

#### Scenario: Render the house faithfully
- **WHEN** the verification scene renders the house
- **THEN** its 216×144 px texture with correct alpha edges appears at its shape bounds over the neutral background

#### Scenario: Map the fill matrix exactly
- **WHEN** the decoded fill matrix is applied to a shape's bounds
- **THEN** the mapped rectangle equals the referenced bitmap's pixel dimensions within one pixel, verified against the house (4320×2880 twips ↔ 216×144 px)

#### Scenario: Render the elephant faithfully
- **WHEN** the verification scene renders the resolved elephant frame-1 shapes
- **THEN** each shape appears at its bounds with its composited bitmap alpha and authentic dimensions

### Requirement: Captured verification evidence
The verification run SHALL capture the rendered viewport to a PNG, build a reference composite independently from the same source bitmaps, compare capture against reference at 1:1 pixel dimensions using a documented tolerance, write a report recording pass/fail plus per-channel and alpha deviation metrics, and exit 0 only when every metric is within tolerance. The comparison logic SHALL also be self-testable without a display: a deliberately perturbed reference MUST yield a non-zero exit and a report identifying the deviation.

#### Scenario: Pass on faithful output
- **WHEN** the verification command runs against the current packages
- **THEN** it exits 0, the report records all metrics within the documented tolerance, and the screenshot evidence is written to the documented evidence path

#### Scenario: Fail on a real deviation
- **WHEN** the captured render deviates from the reference beyond tolerance
- **THEN** the run exits non-zero and the report records the failing metrics and affected pixel counts

#### Scenario: Prove the comparator detects errors
- **WHEN** the self-test runs the comparator against a deliberately perturbed reference
- **THEN** it reports a deviation and returns non-zero, without needing a display for the comparison itself

### Requirement: Preservation and containment
The verification workflow SHALL execute no Flash, Ruffle, ActionScript, browser, network, or server; SHALL leave legacy sources, extracted bitmaps, conversion packages, and all prior manifests byte-identical; and SHALL commit only the documented evidence outputs, never Godot's generated cache. Rerunning verification on the same machine and engine SHALL reproduce a passing report.

#### Scenario: Verify without side effects
- **WHEN** a verification run completes or fails
- **THEN** every source, package, and prior manifest hash is unchanged and no Flash-related runtime was invoked

#### Scenario: Reproduce the result
- **WHEN** verification runs twice with the same packages and engine
- **THEN** both runs pass with metrics inside the documented tolerance

### Requirement: Documented commands and assessment record
The repository SHALL document the exact Godot commands actually executed for import-free rendering and verification, the evidence locations, the pinned engine version, and the limits of the correctness claim (source-bitmap fidelity, not live-Flash pixel parity), and the roadmap Project Status ledger SHALL record the M4 exit assessment result.

#### Scenario: Record the executed commands
- **WHEN** verification has been run successfully
- **THEN** `AGENTS.md` and `apps/client-godot/README.md` describe the exact commands, evidence paths, tolerance rationale, and scope boundaries that were actually used

#### Scenario: Record the exit assessment
- **WHEN** the M4 exit assessment concludes
- **THEN** the roadmap Project Status ledger states the result with pointers to the committed evidence
