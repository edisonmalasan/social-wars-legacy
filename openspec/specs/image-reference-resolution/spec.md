## Purpose

Give the asset tooling a deterministic, evidence-bearing answer to which corpus file each content
image reference names, so that a reference is never left unresolved because the join discarded the
directory that already identified it.

## Requirements

### Requirement: Path-first image reference resolution
The image join SHALL resolve each content image reference by its own path first: the reference, with
its leading separator removed, appended to the committed web root `assets/images/en`, SHALL
identify the corpus file for that reference whenever a file exists at that path. Only when no file
exists at the reference's own path SHALL the join fall back to matching the reference's basename
against the corpus, and the reference SHALL then be recorded as fallback-resolved rather than as
path-resolved. The join SHALL report, per reference, whether the file was identified by the
reference's own path or by the fallback, so that the two are distinguishable in committed output.

A reference whose own path names no existing file and whose basename matches no corpus file SHALL be
reported as missing, never resolved to a substitute file and never left as a collision.

#### Scenario: Resolve a reference whose own path identifies the file
- **WHEN** an image reference is joined and a corpus file exists at `assets/images/en` plus that
  reference's path
- **THEN** the join records that exact file as the reference's source, records the resolution as
  path-based, and records no fallback

#### Scenario: Distinguish the three directory-sharing families
- **WHEN** the committed 607 image references are joined
- **THEN** the 12 chapter basenames shared between `chapters` and `chapters2`, the 3 shared between
  `chapters/simple` and `chapters2/simple`, and the 10 shared between `goals` and `packs` each
  resolve to the single file their own directory names, with no unresolved collision among them

#### Scenario: Report the two mis-pathed references as fallback-resolved
- **WHEN** `/chapters/simple/arachnids_old.jpg` and `/chapters/simple/orcs_old.jpg` are joined, whose
  files exist only under `chapters2/simple`
- **THEN** both resolve to their existing file, and both are recorded as fallback-resolved so the
  directory disagreement between reference and corpus stays visible in committed output

#### Scenario: Refuse a reference that names no file
- **WHEN** an image reference names no file at its own path and matches no corpus basename
- **THEN** the reference is reported as missing with no source, no runtime path, and no candidate
  list, and no other reference's file is substituted for it

#### Scenario: Agree with the previous rule wherever the previous rule resolved
- **WHEN** the new join's answer is compared with the previous basename-only join's answer for every
  image reference the previous rule resolved
- **THEN** the two agree on every one of them, so the change adds resolutions and alters none

### Requirement: Preservation-safe image resolution
The image join SHALL NOT create, rename, move, decode, convert, or modify any image file, and SHALL
NOT author a missing image or edit a content reference to make a reference resolve. A reference whose
file is absent from the corpus SHALL remain missing after the change, and the fact that it is absent
SHALL remain a recorded, inspectable fact rather than being worked around. The join SHALL NOT assert
that any image depicts any subject, that one directory supersedes another, or that a resolved
reference is displayed by any client.

#### Scenario: Resolve without touching any image
- **WHEN** the join runs to completion, whether it succeeds or fails
- **THEN** every image file under the corpus is byte-identical beforehand and afterward, and only
  the registry's own output files are written

#### Scenario: Keep absent images absent
- **WHEN** the join runs against the committed corpus
- **THEN** the 32 references whose files are absent under every extension remain reported missing,
  and no file, content reference or placeholder is created for any of them

#### Scenario: Make no claim about image content or display
- **WHEN** a reviewer reads the join's output and documentation
- **THEN** the output records paths, statuses and digests only, and no claim is made about what any
  image shows, which of two same-named images is current, or whether a client displays it
