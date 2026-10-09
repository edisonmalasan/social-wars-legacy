# Design

## Context

See `proposal.md` for motivation. The shape of the problem, and the measurements that constrain any
approach, are established in `docs/legacy-image-reference-resolution.md` (PR #348).

Four constraints shape this design:

1. **Two tools compute the same join and reconcile against each other.** `build_registry.py` writes
   `coverage.json` and computes the image tiers (`basename_single`, `basename_collision`) at
   `build_registry.py:312-341`. `build_asset_ids.py` re-derives the same join at
   `build_asset_ids.py:110-151` and then **reconciles** against coverage's recorded tier counts at
   `build_asset_ids.py:182-190`, appending a problem string and exiting 1 on a mismatch. A one-sided
   change therefore fails closed rather than producing inconsistent output — which is a property worth
   keeping, not a problem to route around.

2. **The rule is a declared contract, recorded in two places.** `RULES["images"]` in
   `build_asset_ids.py:51` and the `"rule"` string written into `coverage.json` both currently say
   `basename match (web-root-relative form preserved, never rewritten)`. Changing behaviour while
   leaving the recorded string would make the committed evidence lie about what the tool did.

3. **`ambiguous` is part of a closed six-status vocabulary that the client validates.**
   `content_registry.gd:45-49` declares the vocabulary and `:509-514` *enforces* that an entry with a
   status outside `["converted", "extracted", "passthrough"]` must not carry a runtime path. The status
   is not being removed; it is becoming unused for images, and must remain declarable.

4. **Three committed count pins assert today's figures.** `test_build_registry.py:219-220`,
   `test_build_asset_ids.py:171-172` and `test_asset_ids.gd:34`. All three are count pins this change's
   own verified behaviour invalidates, which is the established category for amendment in place.

## Goals / Non-Goals

**Goals:**

- Resolve every image reference that the corpus can truthfully identify, using the reference's own path.
- Make the fallback visible as recorded evidence rather than as silent behaviour.
- Leave the committed registry and coverage byte-deterministic on rerun.
- Keep every number in the committed output re-derivable from the corpus by the same rule.

**Non-Goals:**

- **No rendering, decoding, conversion, or display of any image.** Out of scope by measurement: no
  client code resolves image references today.
- **No authoring of the 32 missing images, and no editing of a content reference to make one resolve.**
- **No claim about what any image depicts**, nor about whether `chapters2` supersedes `chapters`. The
  path-first rule sidesteps that question by letting each reference name its own directory; resolving
  it would be a separate investigation.
- **No change to the `item_sprites`, `magic_sprites` or `sounds` joins.** Their rules are
  path-based already and are untouched.
- **No removal of `ambiguous` from the vocabulary.**

## Decisions

### D1 — Both tools move together, and the reconciliation check stays

`build_registry.py` and `build_asset_ids.py` each gain a path-first attempt ahead of the existing
basename match, and both record the fallback tier. Coverage's tier fields change shape:
`basename_single` / `basename_collision` become path-resolved / fallback-resolved counts plus the
missing count.

*Alternative considered:* change only `build_asset_ids.py`. Rejected — its reconciliation against
coverage would then fail, exiting 1 on every run. That is the check working, and routing around it
would mean weakening the check that makes the two tools trustworthy.

### D2 — The fallback is a distinct recorded tier, not a silent second chance

The two mis-pathed references (`/chapters/simple/arachnids_old.jpg`, `orcs_old.jpg`) resolve only
because their files happen to exist under `chapters2/simple/`. Recording them as ordinary
path-resolved would assert a directory agreement that does not exist; dropping them would regress two
entries that resolve today.

*Alternatives considered:* (a) drop the fallback and let them fall through to missing — rejected, it
converts two working resolutions into a content gap on the strength of a directory disagreement this
change is not asked to adjudicate; (b) record them as `ambiguous` — rejected, that would re-report as
a collision a reference that a single existing file does identify, which is less truthful than
naming the fallback.

### D3 — The rule string is rewritten, not appended

`RULES["images"]` becomes `path-first under assets/images/en, basename fallback recorded`. Leaving the
old string would make `coverage.json`'s own `rule` field misdescribe the tool that wrote it, and the
reconciliation reads that field's neighbours as facts.

### D4 — `ambiguous` stays in the vocabulary and in the client's validation

It remains declarable and the client's enforcement at `content_registry.gd:509-514` is untouched. A
future reference that neither its path nor a single basename match identifies must still be
reportable, and removing the status would make that reference unrepresentable rather than resolved.

### D5 — Count pins are amended in place; no assertion intent changes

The three suites move their pinned numbers to the new measured values. This is the established
category for a pin the incoming line legitimately moves, as distinct from an archived line's
behavioural assertion, which is never amended from an unrelated change. The new values are 575
resolved / 573 path / 2 fallback / 32 missing for coverage, and `{"missing_source": 32}` for the
client's images status map.

### D6 — The zero-disagreement property is asserted, not assumed

The new join must agree with the old one on every reference the old one resolved. That is the
property that makes this a refinement rather than a reinterpretation, and it is the check most worth
having in the suite because it is what would catch a regression into silent re-interpretation.

*Implementation note:* the committed evidence documents a lesson here. An earlier comparison written as
`runtime in (joined, source)` asks whether *runtime* equals either value, rather than whether *either
runtime or source* equals the join; it reported 9 false disagreements against a true zero. The new
assertion must compare each field against the join explicitly.

### D7 — No client source change beyond the three pinned numbers

The client's `resolve_asset` contract, the `ASSET_STATUS_WITH_RUNTIME` set and the fail-closed
behaviour are already correct and are untouched. The client will read a registry in which 50 entries
moved from a status that carries no runtime path to one that does — which is the improvement, and it
needs no client edit to take effect.

## Risks / Trade-offs

- **The 32 missing references stay missing, and the milestone may read as incomplete** → Stated
  explicitly in the proposal, the spec, and the evidence docs. No resolver work can close them: the
  files are absent under every extension. Treating this as a blocker would be inventing a content
  decision this repository cannot make.

- **A future reference could resolve to a file its author did not intend**, because path-first trusts
  the reference's directory → Mitigated by the corpus-wide bijection (573 refs → 573 files, zero
  unreferenced), which means the rule agrees with authorial intent across the entire corpus. If a
  future reference does not fit that bijection, it lands in the fallback tier or in missing, both of
  which are recorded rather than silently resolved.

- **`coverage.json` and `asset_ids.json` are outside the Compatibility API guard baseline** (which
  covers `conversions.json`, `inspection.json`, `image_extraction.json`) → Both files' diffs are
  inspected explicitly rather than relied on to be caught, and the preservation manifest is verified
  separately so no unrelated input byte is implicated.

- **Regenerating committed generated output changes digests that some consumer may pin** →
  `verify.ps1` guards `asset_ids.json` for byte-identity *across* its own battery, which regeneration
  before the battery satisfies. Every pinning suite is enumerated and re-run.

- **The fallback tier could grow silently as new content arrives** → Mitigated by naming its members
  in the committed output and pinning its exact two current members in the suite.

## Migration Plan

Single mechanical pass across the two tools and three test suites, then regenerate the two committed
outputs and re-run the full battery. No data migration, no compatibility shim, no feature flag: the
registry has one producer and consumers read it whole. Rollback is reverting the commit; no preserved
input, save, config, village or content byte is touched by this change, so there is nothing to restore.

## Open Questions

None that would change the specs, the approach, or the task breakdown. The deferred items below are
real but each is independently answerable without disturbing this design, and each is explicitly
outside it:

- Whether `chapters2` supersedes `chapters` — a content-history question for a separate investigation.
- Whether the 32 absent images should be authored or their references retired — a product decision.
- Whether the 2 mis-pathed references or the corpus placement is the error — likewise a separate call.

## Corrections found during Apply

These were found by measurement while implementing, after this design was approved and merged. They are
recorded rather than quietly edited, and none of them changes the approach, the specs' requirements, or
the delivered behaviour — but one of them corrects a claim this document and the task list made, so it
is corrected in both places.

### C1 — The "bijection onto the corpus" holds over the path-resolved tier, not over all identified references

The Risks section above cites "the corpus-wide bijection (573 refs → 573 files, zero unreferenced)" as
the mitigation for path-first trusting a reference's directory. That figure is correct, and it was
measured again here — but it describes the **path-resolved** tier specifically, and this design, the
proposal and task 1.5 originally read it as covering every reference the join identifies.

Measured on the committed corpus: 573 path-resolved references → 573 distinct files, exactly the set
of files under `assets/images/en`, zero unreferenced. All **575** identified references → **573**
distinct files. The two references that break distinctness are precisely the two fallback members:

```
assets/images/en/chapters2/simple/arachnids_old.jpg
  <- /chapters2/simple/arachnids_old.jpg   (path-resolved)
  <- /chapters/simple/arachnids_old.jpg     (fallback-resolved)
assets/images/en/chapters2/simple/orcs_old.jpg
  <- /chapters2/simple/orcs_old.jpg        (path-resolved)
  <- /chapters/simple/orcs_old.jpg          (fallback-resolved)
```

This is not a defect and not a regression: the fallback exists precisely to resolve a reference whose
directory is wrong, and the only file available for that wrong directory is the one the correct
`chapters2` reference also names. Asserting distinctness over all 575 would have required asserting
something false, so the assertion is written over the path-resolved tier with the two shared targets
named explicitly — a stricter, more specific claim than the one originally written. Task 1.5 was
amended in place to match, with this correction cited.

### C2 — Two tools that compute the same join needed one shared implementation

The proposal treated `build_asset_ids.py` as re-deriving the join independently and reconciling against
`build_registry.py`'s recorded result. Implemented as written, that would be two copies of the rule,
with the reconciliation as the only thing standing between them — and a rule change made in one place
would show up as a coverage mismatch rather than as a wrong rule. `build_asset_ids.py` now calls
`build_registry.join_image_refs` directly and takes its `rule` string from `build_registry.IMAGE_RULE`,
so the two tools cannot record different rules for the same join. The reconciliation is **kept** — it
now additionally reconciles the two named member lists, and it remains the check that catches a
`coverage.json` that disagrees with a recomputation (probe P8 detects removing it). The check was
strengthened rather than routed around.

### C3 — The reconciliation needed a fourth tier field the spec does not name

The `asset-registry` spec delta names three tiers: path-resolved, fallback-resolved, missing. But a
reference can fail at its own path *and* match several files by basename — the case the
`godot-content-registry` spec delta explicitly keeps reachable by retaining `ambiguous` in the closed
vocabulary ("a reference that neither its path nor a single basename match identifies"). Recording only
three tiers would leave that reference in none of them: silently absent from `coverage.json`, and the
tier counts would no longer sum to the reference count. `coverage.json` therefore records
`fallback_ambiguous` and `fallback_ambiguous_refs` as well, both empty on the committed corpus and both
reconciled by the asset-ID tool. This is additive to the spec requirement, which specifies a minimum
("SHALL record …"), and it is the only way the requirement can hold for a reference that is neither
path-resolved, fallback-resolved, nor missing.

### C4 — `registry.json`'s line-ending form is load-bearing for `asset_ids.json`, and this is pre-existing

`asset_ids.json` records `registry.json`'s byte count and digest as an input. `build_registry.py` writes
LF; the committed `registry.json` is checked out CRLF (`core.autocrlf=true`, no `eol=lf` attribute), so
running `build_registry.py` changes that file's bytes and therefore changes `asset_ids.json`'s recorded
input digest. `test_rebuild_matches_committed_bytes` then fails until `registry.json` is restored to its
CRLF form. This was hit during this Apply, investigated, and **reproduced on stashed `main`** — it is
pre-existing, order-dependent, and unrelated to this change. It is not fixed here: the honest fix belongs
to the archived `asset-package-parameterisation` line that owns the `registry.json` worktree-form note in
`tools/asset-registry/README.md`, and reworking an archived line's containment assertion from an
unrelated change is how an unearned fix ships. Recorded as a known flaky surface.