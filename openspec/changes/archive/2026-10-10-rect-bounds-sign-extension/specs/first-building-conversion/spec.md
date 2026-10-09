# Spec Delta

## Purpose

Decode `RECT` coordinate fields as the signed bit fields the format specifies, and refuse an inverted
rectangle instead of flooring its extent at zero.

## MODIFIED Requirements

### Requirement: Shape-style record parsing

The tool SHALL parse SHAPEWITHSTYLE bounds, fill/line style arrays with counts and types, bitmap-fill
character IDs, and raw matrices, failing closed on other shape versions or unexpected layouts. Edge
records SHALL be counted, never tessellated. `RECT` coordinate fields SHALL be decoded as the signed
bit fields the format specifies: a field whose sign bit within the declared `Nbits` is set SHALL be
sign-extended to its negative value rather than read as a large unsigned value. A decoded `RECT`
whose `xmax` is below its `xmin`, or whose `ymax` is below its `ymin`, SHALL fail closed as an
inverted rectangle, and SHALL NOT be reported as an extent of zero.

#### Scenario: Parse the measured shape

- **WHEN** the converter reads DefineShape id 2
- **THEN** bounds, one `0x41` bitmap fill referencing id 1, and line styles are recorded with the matrix preserved as raw bytes

#### Scenario: Sign-extend a coordinate field whose sign bit is set

- **WHEN** a shape's `RECT` declares `Nbits` and a coordinate field whose high bit within those `Nbits` is set
- **THEN** the field is decoded as a negative value and recorded verbatim in the shape's bounds
- **AND** the same bytes are not reinterpreted as a large unsigned coordinate

#### Scenario: Reject an inverted rectangle

- **WHEN** a decoded `RECT` has `xmax` below `xmin`, or `ymax` below `ymin`
- **THEN** validation fails identifying the file and tag
- **AND** no package is written and the extent is not floored at zero

#### Scenario: Reject an unexpected shape

- **WHEN** a shape version or style layout falls outside the parsed subset
- **THEN** validation fails identifying the file and tag without writing outputs

#### Scenario: Correct origins without moving sizes

- **WHEN** the committed elephant package is regenerated under the signed rule
- **THEN** 19 of its 28 shapes record a corrected `xmin` or `ymin`
- **AND** no shape's `width_px` or `height_px` changes