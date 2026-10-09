# Spec Delta

## MODIFIED Requirements

### Requirement: Content cross-reference coverage
The tool SHALL extract asset references from the committed normalized package (item `img_name` parts, magic `img_name`, sound `file`, images paths), join them with the documented per-domain rules, and SHALL write coverage with per-domain resolved/missing counts, missing-name lists, unreferenced-file counts, and corpus totals. The image domain's join SHALL resolve each reference by its own path under the committed web root before falling back to a basename match, and SHALL record the image tiers as path-resolved, fallback-resolved, and missing counts together with the rule text describing that order, replacing the previous basename-only single/collision tiering.

#### Scenario: Review measured joins
- **WHEN** the coverage report is compared with direct reads
- **THEN** sprites resolve 862/872 with the 10 missing names listed, magic 10/10, sounds 138/138 file ids, and the 607 image references resolve 573 by their own path, 2 by the recorded basename fallback, and 32 remain listed as missing

#### Scenario: Surface gaps for prioritization
- **WHEN** a maintainer reads the coverage report
- **THEN** referenced-but-missing names and present-but-unreferenced counts are identified per domain without any asset being modified

#### Scenario: Record the fallback rather than hide it
- **WHEN** the image tiers are written
- **THEN** the fallback-resolved count is recorded separately from the path-resolved count and names
  its members, so a reference whose directory disagrees with the corpus is distinguishable from one
  whose path identified its file directly