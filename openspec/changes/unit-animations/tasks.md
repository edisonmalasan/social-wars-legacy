# Tasks

## 1. The linkage projection

- [x] 1.1 Implement `apps/client-godot/scripts/units/unit_animations.gd`: a typed read-only projection carrying the recorded animation labels, each label's recorded frame position, the per-sprite recorded frame counts, and the recorded frame rate, each reported **verbatim**, with no value derived from another (D1) — verify: `test_unit_animations.gd` covers every label and position verbatim and asserts that no duration is computed from a frame count and a rate, no loop, transition, or playback order is derived, and no intermediate frame is produced.
- [x] 1.2 Implement the **fail-closed** path: an asset that is absent, unreadable, or carries **no labels** is reported **unresolvable with its recorded state intact**, never defaulted to an empty, nominal, or single-frame animation (task 1.1's second half) — verify: the suite covers an absent package, an unreadable package, a label-less package, and a malformed label entry, each refusing rather than defaulting.
- [x] 1.3 Resolve the committed asset through the **committed converted package** for the one unit that has one, and record the projection's **coverage** explicitly so a later conversion is a visible addition rather than an assumption (D5) — verify: the suite asserts the resolved package's identity, and the report records the one-package coverage with the count of converted unit packages present.

## 2. Content-only reporting and the `max_frame` non-equivalence

- [x] 2.1 Report the committed `max_frame`, `img_name`, `attack`, `attack_interval`, `attack_range`, and `velocity` plus the `animal` `properties` flag as **content only**, with the **zero-consumer** fact stated in the module's own `##` documentation and the committed distributions recorded (D2) — verify: the suite asserts the values are reported, that the zero-consumer statement is present, and that the recorded distributions match the committed package measured in the same run.
- [x] 2.2 Record the **`max_frame` non-equivalence** as a first-class fact: the committed `max_frame` beside the asset's parsed root frame count and the labelled sprite's frame count, with `max_frame` adopted **nowhere** as a frame count, duration, or loop bound, and with **no claim** about what `max_frame` means because the measurement is one data point (D2) — verify: the suite asserts all three measured numbers, asserts `max_frame` appears in no frame-count or duration role, and asserts the one-data-point statement is present.
- [x] 2.3 Record the **animation-command inventory** naming the 63 dispatcher branches, the five vocabulary matches, and the reason each is a substring artifact, with the animation-command count stated as **zero** (D4) — verify: the suite measures the branch count from the committed dispatcher, asserts each recorded match's reason, and asserts no animation command exists.

## 3. The refusals and the anti-invention guard

- [x] 3.1 Implement the **refusal set as stated requirements** in the module's own documentation and data: no frame duration, loop count, state machine, transition rule, priority, interrupt, playback order, per-state timing, animation trigger, or event-to-state mapping, each with its reason — verify: the suite asserts each refusal family is present with a non-empty reason.
- [x] 3.2 Assert the **anti-invention guard** (D3): the suite fails if any duration, loop, state-machine, transition, priority, interrupt, timing, trigger, or playback helper is added to the module — verify: inject one such helper, observe the failure, restore the file, and confirm the suite passes again; record the result in the review.
- [x] 3.3 Measure every legacy and content figure **in the same run** rather than taking any on trust — the six zero-consumer counts across the seven modules, the branch inventory, the `max_frame` distribution over units and buildings, and the asset's own frame records — verify: each measurement is compared against the recorded constant, and a discrepancy fails the suite rather than being averaged away.

## 4. Boundary, battery registration, and evidence

- [x] 4.1 Assert the **no-endpoint boundary**: no compatibility route, response field, or error code was added, no animate intent is issued, and `apps/compat-api/**` is untouched — verify: the boundary assertions run headless and the compatibility suite is green **unchanged**.
- [x] 4.2 Update the project-scope allow-list for the new script, suite, and evidence files; register `test_unit_animations` in the hermetic list (**34** hermetic) and update the header sentence listing the hermetic suites (no new live phase) — verify: `powershell -File apps/client-godot/verify-boot.ps1` exits 0 end to end with the new suite in its documented count.
- [x] 4.3 Write the deterministic `unit-animations-report-v1` report into `apps/client-godot/evidence/unit-animations/` (written by the suite itself via `--report=<path>`, bare `--report` defaulting there) recording the labels and frame positions verbatim, the per-sprite frame counts, the recorded rate, the six-field inventory with its zero-consumer statements, the `max_frame` distribution and its measured non-equivalence, the one-package coverage, the established-versus-derived split, and every non-claim from the delta — verify: the report is committed, carries every required field, and a rerun reproduces its committed bytes exactly.

## 5. Documentation and integration review

- [x] 5.1 Document the slice in `apps/client-godot/README.md` and add the actually executed verification commands to `AGENTS.md` — verify: each documented command matches one run successfully in this change, and the "no legacy branch selects an animation" limit is stated wherever the slice is described.
- [x] 5.2 Run the full preservation battery in the final state and record the residual gaps (no frame duration, loop count, state machine, transition, priority, interrupt, playback order, per-state timing, animation trigger, or event-to-state mapping; the committed animation fields read by no legacy branch; `max_frame` not adopted as a frame count and its meaning not claimed; no legacy branch selecting an animation; no animation played, animated, or rendered; the converted package establishing linkage only; no claim for any unit other than the one committed converted package; no executed-legacy fixture and the reason being the absence of behaviour rather than only the corpus; no pixel parity and no windowed capture) — verify: `verify.ps1` and `verify-boot.ps1` both exit 0, `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` is green **unchanged**, `python -B packages/game-content/tools/validate_content.py` exits 0, `python -B tools/hash-manifest/hash_manifest.py verify` exits 0, the guard baseline reports identical digests before and after, and `git diff` shows no content-package, conversion-package, registry-manifest, or legacy-source byte changed.
- [x] 5.3 Perform the integration review: re-read the final diff against `proposal.md`, `design.md` D1–D7, `specs/`, and `docs/legacy-unit-animations.md`; run `openspec validate unit-animations --strict` and both batteries once more; and record a requirement-to-evidence map — verify: strict validation exits 0, both batteries exit 0, and every spec requirement maps to a passing check or a recorded claim limit.

---

## Review record (task 5.3)

Every requirement in `specs/godot-unit-animations/spec.md` maps to a check in
`apps/client-godot/tests/test_unit_animations.gd` (**628 checks**, 629 with `--report`) or to a recorded
claim limit carried in `apps/client-godot/evidence/unit-animations/report.json` (digest
`f06784cb...d8556`, 46,703 bytes, byte-identical across three runs).

| Requirement | Evidence |
| --- | --- |
| An animation asset is projected as linkage, never as behaviour | the five labels and their recorded frame positions reported verbatim in committed order; the recorded rate reported and never multiplied; **zero** multiplication or division lines in the module, asserted by a code scan with comments and string literals removed, so the no-derivation claim is mechanically true rather than asserted |
| Committed animation fields are content with no legacy consumer | the six fields plus `animal`, each with its measured **zero** count across the seven legacy modules, its committed distribution, and the near-constant `max_frame`; `max_frame` named as the seventh zero-consumer committed field in this project |
| The committed `max_frame` is not the asset's frame count | all three measured numbers recorded — committed **2**, parsed root **1**, labelled sprite **29**; `max_frame` adopted in no frame-count, duration, or loop role; **and** the suite asserts no code identifier is named after the field, which is what forced the accessor to be named `non_equivalence_record()` |
| No legacy branch selects an animation, and no state machine is derived | the 63-branch inventory measured from the committed dispatcher, each vocabulary match's reason recorded, the five matches split into three whole-`_`-token and two pure-substring, animation-command count asserted **zero**, plus a negative measurement that `frame`/`play`/`loop`/`state`/`clip`/`sprite`/`idle`/`walk`/`death` match no branch at all |
| Animation is content, not a server operation | the boundary assertions run headless; `apps/compat-api/**` untouched and the suite green **unchanged** at `Ran 1352 tests ... OK` |
| No executed-legacy animation fixture is claimed | `captured` false; the reason stated as the **absence of animation behaviour** in the legacy server, not a corpus limitation; no conversion or extraction output regenerated, and the conversion package and registry manifests stay byte-identical |
| Unit-animation evidence and claim limits | `unit-animations-report-v1` carrying every required field and non-claim |

### Three corrections the implementation stage made to the investigation and to my brief

1. **Sprite 63 records 11 placements, not the 5 my brief stated**, and 7 removes. Measured across all
   seven sprites the total is **39** placements. My brief's figure was wrong; the package is right.
2. **`max_frame` over the 470 buildings is `2` on 446 and `1` on 24** — a figure the investigation
   left as only "`1` or `2`".
3. **The `animal` flag is set on exactly 2 of the 429 units and 0 of the 470 buildings** — recorded
   nowhere in the investigation.

The investigation's loose phrase "five substring artifacts" was also sharpened: **three** are
whole-`_`-token matches (`move`, `orient`, `end_attack`) and only **two** are pure substring artifacts.

### Two defects in my own prior work, found while verifying

1. **`test_project_scope.gd` listed `tests/test_unit_movement.gd` and
   `evidence/unit-movement/report.json` twice in `ALLOWED`.** I introduced these on the movement
   line by appending without first checking whether the interrupted worker had already added them.
   The scope test is a permissive allow-list and did not catch it, so it would have shipped silently.
   Both duplicates are removed. The four `scenes/*.tscn` duplicates are **intentional** and left
   alone: `ALLOWED` lists them and `EXPECTED_SCENES` checks them separately.
2. **`AGENTS.md` recorded the collection suite at 1793 checks where the unmodified suite measures
   1845** (1857 with `--report`). The recorded figure was stale; corrected in place with the
   correction noted.

### Guard tested, not trusted (task 3.2)

Injecting one deliberately invented

```gdscript
static func frame_duration(frame_count: Variant, rate: Variant) -> float:
	return float(frame_count) / float(rate)
```

produced **two independent failures** — the per-helper absence check
(`the module does NOT provide the recorded absent helper 'frame_duration'`) and the pinned-inventory
check (`expected [], got ["frame_duration"]`) — and restoring the file from a byte-identical copy
returned the suite to **628 checks, exit 0**.

### Verification actually run (2026-10-02)

| Check | Result |
| --- | --- |
| `test_unit_animations.gd` | **628 checks**, exit 0 |
| `test_unit_animations.gd -- --report` x3 | `f06784cb...d8556` identical, 46,703 bytes |
| `test_unit_movement.gd` / `test_unit_collection.gd` / `test_project_scope.gd` | 245 / 1845 / 1594, all exit 0, **zero** `ERROR:` or `SCRIPT ERROR` lines each |
| guard injection + restore | 2 failures injected, restored to a passing state |
| `verify.ps1` | exit 0 |
| `verify-boot.ps1` | exit 0 — **34 hermetic suites**, 15 live phases, no new live phase |
| compat unittest discovery | `Ran 1352 tests ... OK`, exit 0, **unchanged** |
| `validate_content.py` | exit 0, `result: valid`, 21 schemas |
| `hash_manifest.py verify` | exit 0, 3,258 entries |
| `git status` on content/conversion/registry/fixture/legacy/compat paths | **no byte changed** |

**The exit code alone was not trusted.** On the previous line the battery's `^ERROR:` guard caught two
**real** defects that a grep for `FAIL` had missed, so the battery logs were inspected directly: the
animations suite's `.err.txt` is **0 bytes**, and a scan of every battery log for `^ERROR:` or
`SCRIPT ERROR` returned nothing. The only non-empty error log is the compat unittests', holding
pre-existing CPython `ResourceWarning`s from legacy `get_game_config.py` unclosed files, unrelated to
this change.

### Residual risks

- The `max_frame` non-equivalence is **one data point** over the one committed converted package.
  Nothing says what `max_frame` means, and no claim is made for any other unit. Closing the gap needs
  a new conversion, not a derivation.
- Coverage is **1 of 429** units; every other path is exercised over crafted in-memory packages.
- The five label names are reported verbatim and **deliberately not translated**; a later line wanting
  those readings must re-derive them, because nothing in the evidence selects a state for a
  translation to name.
- Pinning **all 63** branch names makes the suite sensitive to any future legacy dispatcher edit.
  Intended, but worth knowing.
- The `--report` check count is not perfectly stable (628 plain, 629 with `--report`, 630 the first
  time the evidence directory is created) because `_write_report` adds checks conditionally. This is
  inherited verbatim from `test_unit_movement.gd`'s identical writer, so it is a pre-existing pattern
  rather than new behaviour, and the documented figure is the plain-run count.
