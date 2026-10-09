# Spec Delta

## Purpose

Apply the shared style parser's signed `RECT` rule to unit packages, and record that the rule moves
origins in the committed elephant package while leaving every pixel size untouched.

## MODIFIED Requirements

### Requirement: Shape records with byte-aligned style arrays

The tool SHALL parse SHAPEWITHSTYLE bounds, fill/line style arrays with counts and types, bitmap-fill
character IDs, and raw matrices for every shape in the source, failing closed on other shape versions
or unexpected layouts. Edge records SHALL be counted, never tessellated. The shared style parser SHALL
align to a byte boundary after the fill-style array so files whose fill arrays end mid-byte parse, and
existing package outputs SHALL be re-verified byte-identical under the fix. `RECT` coordinate fields
SHALL be decoded as the signed bit fields the format specifies: a field whose sign bit within the
declared `Nbits` is set SHALL be sign-extended to its negative value rather than read as a large
unsigned value. A decoded `RECT` whose `xmax` is below its `xmin`, or whose `ymax` is below its
`ymin`, SHALL fail closed as an inverted rectangle, and SHALL NOT be reported as an extent of zero.

#### Scenario: Parse the measured shapes under the alignment fix

- **WHEN** the converter reads the elephant's 28 shapes (whose fill arrays end mid-byte and fail under the previous byte-strict read)
- **THEN** all 28 parse with bounds, line styles, and edge counts recorded, and each referenced bitmap fill recorded with the matrix preserved as raw bytes

#### Scenario: Prove the fix does not drift existing output

- **WHEN** the house package is regenerated with the shared parser change
- **THEN** its `package_sha256` and bitmap digests are byte-identical to the committed values

#### Scenario: Correct origins without moving sizes

- **WHEN** the committed elephant package is regenerated under the signed rule
- **THEN** 19 of its 28 shapes record a corrected `xmin` or `ymin`
- **AND** `width_px` and `height_px` are unchanged on all 28 shapes and every non-shape package field is unchanged

#### Scenario: Reject an inverted rectangle

- **WHEN** a decoded `RECT` has `xmax` below `xmin`, or `ymax` below `ymin`
- **THEN** validation fails with a non-zero exit and no writes
- **AND** the extent is not floored at zero

#### Scenario: Reject an unexpected shape

- **WHEN** a shape version or style layout falls outside the parsed subset
- **THEN** validation fails with a non-zero exit and no writes