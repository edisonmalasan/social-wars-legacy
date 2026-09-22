## Purpose

Provide a static inventory of SWF headers, tags, symbols, and embedded assets so conversion tooling can distinguish simple art from complex scripted content without executing anything.

## Requirements

### Requirement: Static SWF header and tag inventory
The tool SHALL parse every registry `.swf` entry with static byte reads, recording signature, version, declared and actual length, frame rect/size, frame rate, frame count, and a complete tag-code inventory with counts. Walks SHALL terminate at the End tag or fail explicitly.

#### Scenario: Inventory the measured corpus
- **WHEN** the inspector runs on the current registry
- **THEN** all 1176 SWFs report `CWS` signatures with versions 10/11/15/17, frame counts, and tag inventories, and reruns are byte-identical

#### Scenario: Reject a truncated file
- **WHEN** a tag walk overruns available bytes or never reaches End
- **THEN** validation fails identifying the file without writing outputs

### Requirement: Symbol and embedded-asset listing
The tool SHALL record SymbolClass/ExportAssets names verbatim, embedded bitmap/sound definition IDs, and ActionScript presence (DoABC/DoAction tags) with counts. Names and IDs SHALL never be interpreted behaviorally.

#### Scenario: Review a scripted file
- **WHEN** a maintainer reads an entry with DoABC tags
- **THEN** the presence flag and counts are identified, with no claim about script behavior

#### Scenario: Review symbol names
- **WHEN** a maintainer reads recorded symbol names
- **THEN** they are identified as verbatim export data for conversion scoping

### Requirement: Validation and round-trip evidence
The tool SHALL validate header well-formedness, walk termination, schema fields, and determinism. It SHALL report success with exit 0 and any validation failure with a non-zero exit, writing `inspection.json` only on success.

#### Scenario: Detect signature drift
- **WHEN** a corpus file carries a non-`CWS` signature
- **THEN** validation fails explicitly identifying the file and expected shape

#### Scenario: Prove outputs match inputs
- **WHEN** inspection outputs are re-derived in memory
- **THEN** headers, inventories, names, and counts are recomputed equal before any write

### Requirement: Preservation-safe inspection tooling
The tool SHALL NOT execute ActionScript, render, decode bitmaps/sounds to pixels/samples beyond tag-structure reads, convert, relocate, or modify any asset; SHALL NOT use Flash, browser, network, server, or subprocess execution; and SHALL write only `inspection.json` on success. Registry and coverage outputs SHALL remain untouched.

#### Scenario: Inspect without side effects
- **WHEN** the inspector succeeds or fails
- **THEN** every source asset and registry output remains byte-identical and only the inspection file is created or replaced
