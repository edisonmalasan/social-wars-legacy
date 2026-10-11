# Design — asset package mass conversion

Binding measurements: `proposal.md` §§1–5. Binding predecessor records:
`docs/legacy-m12-scope-classes.md` (PR #372), `docs/legacy-m12-byte-alignment.md` (PR #371).

---

## D1 — Conversion output references the shared extracted tree; it does not copy

**Decision.** Each converter emits `package.json` only. Every `bitmaps[].file` records the
**extraction output path** (`assets/converted/images/<sprite>/<name>`) rather than a
package-relative copy, retaining `sha256` and `bytes`.

**Why.** The bytes already exist, extracted, under a gitignored tree (`convert_building.py:725-727`
reads them from `root / output["file"]` and writes a *second* copy under the package directory).
Measured cost of the copies: **63,853,466 bytes** across **8,515** files — 88% of the 72.9 MB
total — in a `.git` already at **690 MB**. Cross-package duplication is only **1.11×**, so this is
not a deduplication problem that a content-addressed store would also solve; it is the copy.

**Consequence accepted.** A converted package is no longer self-contained. It becomes a manifest
over shared extracted assets. That is a real change of contract and is recorded as one rather than
presented as repackaging.

**Rejected — commit the 72.9 MB as measured.** Irreversible without a history rewrite, which
preservation rules forbid, and it duplicates already-ignored material.

**Rejected — deduplicate by content hash.** Measured factor is 1.11×; at best it reclaims ~6.5 MB
of 63.9 MB while adding a store, an index, and a resolution rule. Not worth the complexity.

**Rejected — commit manifests and force-add bitmaps via a `.gitignore` exception.** Same 63.9 MB in
history; adds a rule that exists only to be overridden.

## D2 — The reference is verified, not merely recorded

**Decision.** The digest comparison at `convert_building.py:736-738` is **retained**. Every
referenced path must resolve, and its bytes must hash to the extraction manifest's recorded
`sha256`.

**Why.** Without the copy there is no second artifact to compare, so the check that proves *the
package points at the intended bytes* becomes the **only** thing tying the manifest to real
content. Dropping it would make `bitmaps[].sha256` an unverified transcription.

**This is the strongest argument for D1 surviving review.** The reference is not a weaker copy; it
is a copy replaced by a *checked* pointer.

## D3 — `output_bytes` semantics are corrected, not reinterpreted

**Decision.** With no copied bytes, `conversions.json`'s `output_bytes` becomes the `package.json`
byte total. The schema description at `conversion.schema.json:72-74` — currently *"Package.json
bytes plus **copied** bitmap bytes"* — is amended **in the same change**.

**Why.** A schema whose description contradicts its data is a defect that survives every test,
because nothing validates prose. Both existing package entries are re-derived under the corrected
meaning; their recorded values move, and that movement is expected rather than a regression.

## D4 — Client path resolution is **measured before it is changed**

**Decision.** Apply task 1.1 measures how `package_loader.gd:481` / `package_paths.gd:33-38`
resolve `bitmaps[].file` today, and the design branches on the result. **The proposal deliberately
does not assume the cheap answer.**

- If `file` is joined onto the package directory, resolution becomes repository-relative and
  `package_paths.gd` gains one accessor.
- If `file` is already repository-relative, **no client change is required at all** — which would
  make this a tooling-only change.

**Why measure first.** `package_paths.gd:33-38` exposes `package_dir()`/`package_json()` but no
bitmap accessor, and `package_loader.gd:481` iterates entries without showing how `file` is used.
Reading it costs one reading; guessing wrong costs a wrong client contract in a preservation-first
project, and this project has repeatedly recorded that a plausible reading was false.

## D5 — Both committed packages are re-derived under D1–D3

**Decision.** `0001_house_1_m` and `10033_wild_elephant` are re-converted, and their
`package_sha256`, `output_bytes`, and `bitmaps[].file` values change. `test_package_loader.gd`'s
`HOUSE_CONTENT_VERSION` / `ELEPHANT_CONTENT_VERSION` and the pinned digests in
`evidence/first-render/report.json` and `verify.ps1` are updated **in the same change**.

**Why.** Two packages that keep copies while 290 reference the shared tree would leave two
resolution conventions in one corpus — the exact "two owners of one surface" failure this project
records repeatedly.

## D6 — The MATRIX anomaly is recorded at line level and no field is invented

**Decision.** Captured MATRIX hex is preserved **verbatim**. The anomaly (`HasScale = 1`,
`NScaleBits = 22` against a cap of 11, in **2,869 / 2,869** resolvable bitmap fills) is recorded in
the change's artifacts as carried-forward and unresolved. **No per-package anomaly field is added.**

**Why.** Its meaning is **not established**. Objective 2 recorded that a coherent stream across
4,616 fills argues against a simple mis-decode, and that `parse_matrix` (`:296-308`) validates
nothing. A field asserting the anomaly would encode an unestablished claim into 290 committed
artifacts. Recording it once, at line level, is the honest form.

**User-confirmed.** Proceed with mass conversion; do not open a MATRIX investigation line. The
standing investigate-only instruction on the desync family is unchanged.

## D7 — The preservation manifest is untouched, and the claim is withdrawn

**Decision.** No manifest change. The prior line's *"preservation-manifest regeneration"* non-goal
is **withdrawn as false**, with the mechanism recorded.

**Why.** `hash_manifest.py:180-184` builds from `git ls-tree -r <commit>` against the **pinned**
`source.commit`. New blobs cannot enter it. Measured: **3,258** entries, **0** under
`assets/converted`, despite two converted packages already being committed.

**Why this is recorded rather than dropped.** `PROTECTED` includes `assets` (`:16-17`), so the
claim looks true on inspection. Protection governs what the manifest *would* hash **if the pinned
commit contained those blobs** — not what a later commit adds. A reader checking `PROTECTED` would
"confirm" the false claim, which is exactly why it must be corrected in place.

## D8 — Scope is the committed census, re-verified, never a hand-copied list

**Decision.** The 290 targets come from `target_census.json`'s `verdict == "converted"`, filtered at
run time. No stem is transcribed into any source file, manifest, or task.

**Why.** The census is the measured authority and the spec already requires the candidate set be
derived, never transcribed. A transcribed list of 290 stems is exactly the kind of input that
silently rots when content changes.

**Known staleness, carried forward.** Objective 2 recorded the committed census at `84B11BEE…`
against the current tree's `84B7D954…`, differing on 109 targets with one verdict change, and
recording no input digests. Apply task 1.2 re-measures the census and records the delta rather than
assuming the committed document is current.

## D9 — Determinism is asserted across reruns, and the rerun oracle is three consecutive runs

**Decision.** Conversion output must be byte-identical across repeated runs, checked over
**three** consecutive full runs, not two.

**Why.** `.gitattributes` already pins the package manifests LF precisely because they are compared
byte-for-byte. Two runs can agree while a third differs on a dict-ordering or timestamp path; three
is the project's established bar for a regenerated evidence artefact.

## D10 — Containment and blast radius

**Decision.** Conversion runs into a contained root; the repository is read-only input. No legacy
Python touching `auctions/` is ever run with the repository root as CWD. No Flash, Ruffle,
ActionScript, or browser executes; no network is used.

**Blast radius if this line is wrong.** 290 committed manifests plus 2 re-derived, and up to five
client/verification digest pins. Reversible by reverting the merge; **no history rewrite is ever
proposed**, which is what made D1's alternative unacceptable rather than merely unattractive.

---

## Verification obligations

Every one below is a claim this design makes that a script reporting success would not establish.

| # | Obligation | Falsified by |
|---|---|---|
| V1 | Referenced bitmaps resolve and match `sha256` | a reference that does not hash to the extraction manifest |
| V2 | Packages contain no copied bitmap bytes | any non-`package.json` file under a package dir |
| V3 | Output identical across 3 runs | any byte difference |
| V4 | 290 targets, 0 disagreements with census | a target whose verdict moved |
| V5 | Preserved inputs byte-identical | any change to sprites/manifests/content/saves |
| V6 | `openspec validate --all --strict` passes | any strict failure |
| V7 | Preservation manifest still verifies at 3,258 | any movement (it must not move) |

**V4 and V7 are the two that catch a *plausible* wrong implementation.** V4 catches a converter that
silently succeeds on the wrong input — the exact defect that produced the withdrawn 365/365 unit
figure in the predecessor line. V7 catches a line that "helpfully" regenerated a manifest that
cannot be regenerated.