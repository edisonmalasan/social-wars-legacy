# Social Wars Modernization & Flash-Free Reconstruction Roadmap

**Project:** Social Wars Legacy Reconstruction  
**Primary Goal:** Reconstruct the existing Social Wars implementation into a modern, maintainable, Flash-free client/server game while preserving the behavior, content, saves, assets, and historical implementation contained in the current repository.

**Core Strategy:** Preservation-first reconstruction.

The existing repository will **not** be thrown away or treated merely as obsolete code.

It will serve as:

- Reference implementation
- Behavioral specification
- Protocol specification
- Preservation dataset
- Save-game corpus
- Content database
- Asset archive
- Regression oracle
- Migration source
- Historical documentation

The modern version will progressively replace Flash/SWF functionality with a Godot client while preserving the existing Python server until behavioral parity has been verified.

Only after the new client is substantially functional should the backend be modernized into an authoritative production architecture backed by PostgreSQL.

---

<!-- ORCHESTRATOR_STATUS_START -->

## Project Status

This section is maintained by the root Codex orchestrator.

It is a progress ledger, not the source of truth for specified behavior.

- **Current milestone:** **M12 - Asset Parity - line 3 `rect-bounds-sign-extension` DELIVERED, VERIFIED, SYNCED and ARCHIVED.** Archived as `openspec/changes/archive/2026-10-10-rect-bounds-sign-extension/`. It **modifies two capabilities and creates none**: `first-building-conversion` (*Requirement: Shape-style record parsing*) and `first-unit-conversion` (*Requirement: Shape records with byte-aligned style arrays*, which already governs unit targets through "the shared style parser"). **Lifecycle, each stage on its own remote branch from updated `main`, merged as a merge commit, no branch reused:** the correction plus newly located defect investigation `docs/legacy-m12-signed-rect.md` (PR #357, merge `ef93fdb`), proposal PR #358 merge `a5b4bd3`, Apply PR #359 merge `6696ccd`, Sync PR #360 merge `ad7b196`, this archive. **What shipped**: `RECT` coordinate fields are **sign-extended per field** rather than read unsigned, and a decoded rectangle whose `xmax` is below its `xmin` (or `ymax` below `ymin`) **fails closed instead of being floored to a zero extent**. **Measured on the full population of 290 converted targets, routed per domain through `CONVERTER_BY_DOMAIN`:** all **290** parse, **4347 shapes**, **0 inverted remain** (from **2445 across 74 targets**), **0 refusals by the new guard**, **0 negative sizes**. Per-field moves: `xmin` 1987, `ymin` 1597, `xmax` 10, `ymax` 22, `width_px` 10, `height_px` 22. **Two shipped decisions, one corrected in flight**: D1 (sign extension) shipped as specified, and **D3's original design text said the extents would be kept unclamped, which was WRONG** - `xmin=-118, xmax=-71` is correctly ordered yet floors to `-4`, so deleting the `max(0, ...)` clamp would have emitted **negative pixel sizes**. The clamp is **retained**, the inversion guard is not, and the correction is visible in `design.md` section D3 rather than quietly applied. **The fixture repair is a spec-conformance fix, not an expectation change**: the test helper `rect_bytes` read `Nbits` bits where the format specifies `max_bit_length + 1`, and **no expected value was edited**. **The decisive A/B evidence, one process per variant:** baseline **81 run, 0 failures, 0 errors**; sign extension alone **70 run, 9 failures, 2 errors**; sign extension plus the one-bit-wider fixture **81 run, 0 failures, 0 errors** - which is what separated a real defect from a broken instrument after **variants in one process leaked state** (70 vs 81) and were discarded. **No mass conversion**: only `assets/converted/units/10033_wild_elephant/package.json` was regenerated, **19 of its 28 shapes moved** (`xmin` 9, `ymin` 17), with `xmax` / `ymax` / `width_px` / `height_px` **unchanged on all 28** and **no non-shape field changed**, while the house package is **byte-identical and never rewritten**. **A dependency the proposal's Impact originally omitted:** `build_asset_ids.py` records `conversions.json` as an input, so `asset_ids.json` **must** be regenerated whenever `conversions.json` changes - found because the full unittest discovery failed, and recorded as an amendment to `proposal.md` rather than worked around. **D2 remains deferred and separable** (3452 of 4347 shapes, 76 of 290 targets), with the interaction recorded: all 32 size fields moving across 13 targets move **non-zero to 0**. **Verification actually run:** asset-registry discovery **221 tests OK**, exit 0; `hash_manifest.py verify` **3258 entries / 758,423,699 bytes**, exit 0; `validate_content.py` `result: valid`, 23 files / 22 schemas / 604 references, exit 0; `openspec validate --all --strict` **75 passed / 0 failed**, exit 0; and the population re-measure reproduced the proposal table **exactly**. **The desync family still carries no line**, and the thirteen recorded flaky surfaces remain open.
- **Current milestone, before this entry, retained in full:** **M12 - Asset Parity - a RECT sign-extension defect is LOCATED and FULLY IDENTIFIED, it repairs 74 of the 290 converted targets, and the converter is shown to FAIL OPEN.** This entry opens by recording **corrections to the merged desync-origin record** (`docs/legacy-m12-desync-origin.md`, PR #356), because that record's own error is what hid the defect below. Investigation: `docs/legacy-m12-signed-rect.md` (this branch). **FIVE claims from the predecessor are corrected or withdrawn, and the cause is an instrument fault rather than a wrong theory**: the end-to-end probe called `convert_building.build_package` for all 272 desync targets, but the set splits **77 building / 195 unit**, so every unit target failed the *building* content lookup with `content ref not unique ... : 0` **before any parsing happened**. 195 of the 272 therefore never reached the parser and every parser-phase figure for them was vacuous. The census avoids this by routing through `CONVERTER_BY_DOMAIN` (`census_targets.py:160-166`); the probe did not. **The tell was available and unused**: the class appears in the *unpatched* run with the identical 195 targets, and a monkeypatch cannot create a refusal the unpatched run already has. Withdrawn: section 7's class table, which **covers 77 of 272** and never says so; section 8's downstream blocker, which was arithmetically derived from the 195; and correction C5's attribution of that class to the patch's return key - the return-shape mismatch was real and is retained, but fixing it did not remove the class, which **rose** from 173 to 195. Corrected: "0 of 272 convert" is **2** under correct routing, and across **all 817** candidates the located layout gains **3** and loses **3**, **net 0**, with all six **stable across 3 repeats in each phase**. **The three losses are corrections, not regressions**: each emits geometry that cannot be drawn (`1005_special_spy_m` and `1421_cyberInquisitorDrone` both at **-288.6 px**, and `0127_enemy_harbour_m` at 1087.7 px on a 1000 px frame), so refusing them is right and the predecessor's "regressions refute the layout" reading is dissolved. **THE NEW FINDING - the converter FAILS OPEN.** `parse_rect_bits` (`convert_building.py:257-267`) reads the four RECT fields with `read_bits`, but the spec says they are **SB** (signed), and `BitReader.read_bits` (`:229-238`) is a correct **unsigned** MSB-first reader. Measured over the 290 converted targets: **74 of 290** emit at least one shape with a **negative extent** and **2445 of 4347** shapes do, so **56%** of all emitted geometry is impossible - and it is invisible in every count reported so far. **Attribution is causally closed**: sign extension **alone**, with nothing else changed, removes **2445 of 2445** negative shapes and repairs **74 of 74** targets with **0 failures**. A second, **independent** defect is held fixed during that measurement and does **not** move - `width_px`/`height_px` are computed from `xmax`/`ymax` instead of the extent, which disagrees with the shape's own bounds in **3452 of 4347** shapes across **76 of 290** targets - so the two causes are separated rather than confounded. **`max(0, ...)` at `:267` clamps a negative to zero instead of failing closed**, which is why a bad RECT passes silently. Negative extents **do not cluster on one tag** (DefineShape 2311, DefineShape2 126, DefineShape3 8), so this is the shared RECT decode and not one tag's payload layout. **Blast radius on committed bytes is one file**: only two conversion packages are committed, `0001_house_1_m` is clean, and `assets/converted/units/10033_wild_elephant/package.json` carries **19** negative and **22** wrong-size shapes; `legacy-manifest.json` does not cover `assets/converted`, so the 3,258-entry preservation manifest is unaffected. **Three test sites pin the affected output** and an owning line would amend them: `test_convert_building.py:240-241`, `:464-465`, `test_convert_unit.py:268-269`. **Why this warrants a line where the desync family does not**: the family needed a layout **underdetermined in 5 of 6 parameters** and converted net zero with no monotonicity test separating a partial fix from a wrong one, while this is **one function**, **fully identified** (sign extension is what `SB` means, not a free parameter), **causally closed**, **large**, and **checked against a fixed corpus of two committed packages**. **FIVE instrument faults of my own are committed with this entry rather than fixed in place**, because the most dangerous measurement is a clean-looking zero from a broken instrument: the end-to-end routing fault; a plausibility probe that read shapes from the conversion manifest instead of the package and then **re-committed the same routing error**; and a D2 measurement that was vacuous **twice over** - it compared `width_px` against `max(0, xmax // 20)`, **the exact expression the code uses**, and then read `width_px` off the shape when it lives inside the nested `bounds`, so its reported "0 of 290" could not have failed. **A reasoning error of mine is recorded because it is the reason the defect went unexamined for a whole stage**: I ruled sign extension out before testing it, arguing that unsigned reading applies "a uniform shift" that "preserves order". Sign extension is **not** a uniform shift - it subtracts `2**nbits` only for fields whose sign bit is set, moving them below the non-negative ones and therefore **changing** their order. The cheapest available test would have found the defect immediately.
- **Current milestone, before this entry, retained in full:** **M12 - Asset Parity - the 272-target desync family's origin PARTIALLY LOCATED, and NO LINE IS PROPOSED because the located defect converts nothing.** The investigation is committed as `docs/legacy-m12-desync-origin.md` (this branch). It is a **measurement, not a line**, and it implements nothing - no conversion, extraction, client, tool, or spec change. **The precondition is settled**: all 272 payload slices are correct (the UI16 ShapeID matches the walk's shape id 272 of 272), every tag is style-bearing (22x tag 2, 141x tag 22, 109x tag 32), no morph tag is present, and no payload is too short to carry an id - so the defect is in what the parser reads, not in the bytes. **One real defect is located and sharply bounded**: `parse_fill_style` reads the solid branch's colour as `4 if rgba else 3`, but a solid fill colour in an RGBA-tagged shape is **3 bytes**; correcting that single expression makes **138 of 272** payloads parse exactly where the committed rule resolves **9**, a 15x gap and the only sharply constrained parameter in the whole layout. It reaches `unknown fill style` 109 of 137 and `shape bit overrun` 15 of 20, but `shape byte overrun` - the largest single class - only **10 of 104**. **And it converts 0 of 272 end to end**, measured through the real `build_package` against a harness calibrated to report 10 of 10 known-converted targets as converted and an audited parser return shape; refusals only relocate, with two previously MASKED classes (`unresolvable bitmap fill` 0 -> 8, `unsupported shape tag` 0 -> 2) surfacing once the earlier refusal no longer hides them. **This is the PR #355 3.2 pattern, not an exception to it.** Five candidate origins are now falsified: inter-fill alignment (11 of 272), a wrong start offset (177 of 272 have no witness at any offset), the gradient layout (216 variants, at most 14), the edge-record grammar (16 grammars x 3 gradient layouts, at most 6 - a genuine four-way specification deviation at `count_shape_records:381-393` that is real and simply not the origin), and the conditional LINESTYLE miter pair that `parse_line_style:313-317` omits (131 targets either way, so the omission is exercisable but harmless here). **The blocker**: at least one further defect lies **downstream of the parse**, on the content-reference and asset-resolution path - the 130 targets that now parse land in refusals that are not parse failures at all.
- **Current milestone, before this entry, retained in full:** **M12 - Asset Parity - the 8 refusal classes INVESTIGATED; the second of the three open decisions is now answered and the previous recommendation is WITHDRAWN on measurement.** The investigation is committed as `docs/legacy-m12-refusal-classes.md` (this branch, `3fa6040`), answering the refusal-class question that `docs/legacy-m12-asset-parity.md` §6 item 3 raised and that the FX / animation re-scope deliberately left open. It is a **decision, not a line**, and it implements nothing - no conversion, extraction, client, tool, or spec change. **The classes are not eight.** `unknown fill style` (137) + `shape byte overrun` (104) + `shape bit overrun` (20) + `shape byte misaligned` (11) are **one shared cause** - a bit-position desync - totalling **272 targets / 194 labelled**, so the largest group in the census is a *family* and a line aimed at any single member would have addressed 104 of 272 and left 168 behind. **The predecessor's recommendation is WITHDRAWN.** `docs/legacy-m12-fx-animation-rescope.md` recommended lifting `shape byte overrun` (104 targets, 89 labelled, `68 -> 157` convertible labelled sprites) on the strength of a real defect in the gradient FILLSTYLE parse at `convert_building.py:285-310`, which reads an 8-bit header where the specification has a MATRIX followed by a 12-bit header. **Correcting that defect converts 0 of 104 and relocates 66 failures**; and on the 37 shapes readable under both parses the `0xFFFF` sentinel count **rises 6 -> 12** (seven targets enter it, five leave), so the correction **moves the fault rather than removing it**. **The supporting link is strong and is recorded**: **91 of the 99** failing shapes declare a gradient fill, the exact mis-parsed structure. **Two classes are documented scope decisions, not parser limits**: `unsupported shape tag` is code **83 DefineShape4 on all 64**, refused by `TAG_REFUSED_SHAPE = (83,)` - a one-member constant, making DefineShape4 the only shape tag the converter declines at all - and `unsupported timeline tag` is code **70 PlaceObject3 on all 57** from `convert_unit.py:71-77`, whose semantics this oracle cannot recover. **Recorded, not queued.** **`unresolvable bitmap fill` has no general rule**: `0xFFFF` occurs **1,138** times, but **0 of 133** targets are all-`0xFFFF` and **127** mix it with real ids, so "ignore null bitmap fills" is contradicted by the corpus rather than supported by it. `unsupported tag in timeline` is **1 target** and is not worth a line. **The deliverable is a recommendation, not an authorisation**: one line aimed at the desync **family**, and only after its cause is located. **Nine corrections are recorded rather than quietly fixed and none changes the decision**; C1-C8 are mis-scoped probes, a broken tool call, and a prediction measurement falsified (C6 withdrew the recommendation), while **C9 is five further defects found by reading the finished draft** - a class no probe could catch because none of them is a number - one of which *strengthened* a finding by checking a citation against committed source and discovering `TAG_REFUSED_SHAPE` has a single member. **The standing lesson re-earned**: §3.2 is a concrete demonstration that a plausible-looking fix can convert nothing, so a proposal written before the remaining desync is located would be guessing at a parsing rule - the exact failure this project has declined repeatedly.

- **Current milestone, before this entry, retained in full:** **M12 - Asset Parity - the FX / animation re-scope DECIDED; one of the three open decisions is closed and the milestone's ordering has changed.** The decision is committed as `docs/legacy-m12-fx-animation-rescope.md` (PR #353, merge `5061bb5`). It is a **decision, not a line**, exactly as `docs/legacy-m12-asset-parity.md` §6 item 3 framed it, and it was required before any proposal could be written for either deliver item. **It implements nothing** - no conversion, no extraction, no client, tool, or spec change - and every figure comes from committed artifacts read by a script, with four distinct matching rules applied wherever a stem is searched for (`whole_file`, `code_only`, `token`, `quoted`), because a substring match and a whole-token match answer different questions. **"FX replaced" is CLOSED BY MEASUREMENT as unsatisfiable from this oracle, and the absence is structural rather than a failed search:** 205 FX SWFs, 205 distinct stems, **205 of 205 dotted**, against **0 of 862** dotted sprite stems, so no content-facing vocabulary can name an FX asset even in principle; **0** names under four rules across 16 normalized files, the raw config, and all **1,627** `asset_ids` references; **0** collisions with sprite, magic or image stems; each file's own exported symbol equals its own stem (**205 of 205**, **0** unexplained occurrences), so there is no cross-reference; **205 of 205** carry ActionScript but the committed tooling records **presence, never contents**, so the candidate explanation the original investigation declined to record is not merely unrecorded but **unreadable here**; and FX is **not a census domain**, so it cannot acquire a verdict without a content row. **The substantive new measurement is that the FX bitmaps already exist: 86 of 205 are extracted, 639 bitmaps on disk**, each figure confirmed by two independent measures that agree, and **all 119 unextracted files carry zero `bitmap_ids`**, so nothing is stranded and extraction is **complete, not partial**. **"Animation gaps resolved" is the opposite verdict - feasible, and its prerequisite is refusal-class work, not FX work.** It is measurable for the first time because line 1 closed the tooling gap: of **422** labelled sprite files, **68** are converted, **313** refused and **41** are not candidates, so **animation is blocked behind the census refusal classes**. **`frame_count` is not the animation measure** - only **5 of 817** targets exceed 1 frame while **68** carry labels, so the root header value understates the surface by roughly 68 to 1 - and the label vocabulary is **10** distinct strings reported verbatim and deliberately **not** translated, because nothing selects a state for a translation to name. **The largest single lever is `shape byte overrun`**, **104** targets of which **89** are labelled, which alone would move convertible animation sprites from **68 to 157**; the eight classes sum exactly to the recorded **527** because `refused_targets_in_several_classes` is **0**. **Two independent blockers exist and neither alone reaches the population**: **313** behind converter refusals and **41** behind a content-side gap, the latter reproducing the census derivation exactly (**5** clause-(a) + **10** zero-row + **30** multi-row -> **817**) read from `census_targets.py:113-143`, with the **30** multi-row cases being genuine **content ambiguity** (`1001_worker_m` claimed by Worker II, III and IV) that would otherwise be misreported as a convertibility refusal. **`max_frame` is generalised as wrong**, disagreeing with recorded `frame_count` on **276 of 290** convertible targets, which strengthens rather than relaxes the refusal `godot-unit-animations` recorded from one data point. **CONSEQUENCE: M12's ordering changes - the 8 refusal classes move from one of three open decisions to the critical path for TWO deliver items** ("all runtime-required SWFs converted or recreated", **290 of 817** convertible, and "animation gaps resolved", **68 of 422** labelled). **"UI assets converted" was re-measured after line 2** and now reads **566** passthrough, **9** extracted, **0** ambiguous, **32** missing of **607**; the 32 stay absent **by decision, not oversight**. **Six instrument defects are recorded in a corrections section rather than quietly fixed**, and two of them are **printed conclusions their own data falsifies** - "animation is NOT blocked behind a refusal" printed twenty lines above a measurement of **313 of 422** refused, and "a file no content row names is not a candidate" printed against a measurement showing **all 41** are named - so both are marked **withdrawn** and replaced with measured statements; a third, an early **92**-stem FX figure, was a substring artifact corrected to **86** with all six containment stems named. **A process deviation is recorded rather than hidden: this ledger entry landed in its own docs-only PR instead of travelling with the investigation as PR #348 did for line 2, because the investigation was committed without it.** No correction changes a conclusion; C1 and C2 changed figures, C4 and C5 withdrew asserted sentences, C6 fixed a sum, and the decision stands on the corrected numbers. Checks run on the investigation branch: `openspec validate --all --strict` **74 passed / 0 failed**, `hash_manifest.py verify` **3,258 entries / 758,423,699 bytes / commit e8c98a03**, both exit **0**.

- **Current milestone, before this entry, retained in full:** **M12 - Asset Parity - line 2 DELIVERED, VERIFIED, SYNCED and ARCHIVED.** `image-reference-resolution` is archived as `openspec/changes/archive/2026-10-09-image-reference-resolution/`. It **creates one capability, `image-reference-resolution`** (**2 requirements**, **8 scenarios**), and **modifies two**: `asset-registry`'s `Content cross-reference coverage` and `godot-content-registry`'s `Deterministic asset ID registry`. **Lifecycle, each stage on its own remote branch from updated `main`, merged as a merge commit, no branch reused:** investigation `docs/legacy-image-reference-resolution.md` (PR #348, merge `0902326`), proposal PR #349 `08eb31f`, Apply PR #350 `42807bf`, Sync PR #351 `915a656`, this archive. **The proposal was scoped as a mechanism line and the split was deliberate**: authoring or retiring the 32 absent images is a **content decision this repository cannot make from preserved evidence**, and a proposal claiming to close them would promise something the oracle cannot deliver. **What shipped**: the join resolves each image reference by **its own path** under the committed web root `assets/images/en` first, and only when no corpus file sits there does a basename match apply - recorded as a distinct `fallback_resolved` tier **with its members named**, never applied silently. Measured on the committed corpus: **573 path-resolved, 2 fallback-resolved, 0 fallback-ambiguous, 32 missing = 607**, unchanged in total, and **exactly 50** image entries moved `ambiguous` -> `passthrough` with real `source` / `runtime` / `source_sha256` (30 `.jpg` + 20 `.png`), the entry total holding at **1,627**. **`ambiguous` was NOT removed**: it stays in the closed status vocabulary and stays declarable, unused for the committed images. **The zero-disagreement property was built, not asserted**: `build_kind_entries` is called **twice through the same classifier**, once with old basename-only candidates and once with path-first ones, and compared field by field - because the shape `runtime in (joined, source)` asks whether *runtime* equals either value rather than whether *either* equals the join, and that shape passed vacuously on two nulls. **Two tools, one implementation**: `build_asset_ids.py` calls `build_registry.join_image_refs` and takes its rule string from `build_registry.IMAGE_RULE`, so they cannot record different rules for the same join; the reconciliation was **kept and strengthened** (it now reconciles the three tier counts *and* the two named member lists), not routed around. **A claim of this change's own artifacts was falsified by measurement and corrected, not shipped**: the \"corpus bijection\" holds over the **path-resolved** tier (573 refs -> 573 distinct files, exactly the files under the web root, zero unreferenced) and **not** over all 575 identified references, whose only two shared targets are the mis-pathed fallback references aliasing their `chapters2` counterparts. Task 1.5 was amended in place and the correction recorded in `design.md` as C1 - the assertion written is **stricter and more specific** than the one originally proposed, so the correction narrowed a false claim rather than excusing a limit. **A fourth tier field the spec did not name was found necessary**: a reference can miss at its own path *and* match several files by basename, and recording only three tiers would leave it in none of them with the counts no longer summing to the reference count (C3). **11 injection probes against the final bytes, all detected**, measured failure lines `4,4,1,1,5,5,2,2,1,6,1` = **32**, every restore byte-identical by SHA-256. **Three defects in my own harness were found and fixed by measurement before any probe counted**: it detected with the *Godot* suite's `^[test] FAIL` format so every Python probe read as unproven; it patched by *inserting* after a single-line anchor, which duplicates the statement and yields a parse error - and **a parse-error detection proves nothing about a guard**, so parse-only failures are now reported separately and never counted; and it used `write_text(newline=...)`, which **does not exist on the pinned CPython 3.9.13**. The baseline suites are also run clean first and the run aborts otherwise. **One pre-existing flaky surface was found, reproduced on stashed `main`, and deliberately NOT fixed**: running `build_registry.py` rewrites `registry.json` in LF form, flipping the input digest `asset_ids.json` records and failing `test_rebuild_matches_committed_bytes` until it is restored - order-dependent, pre-existing, and the honest fix belongs to the archived `asset-package-parameterisation` line that owns the worktree-form note. **No client contract changed**: `content_registry.gd`'s closed vocabulary and runtime-path enforcement are untouched; only the three pinned numbers in `test_asset_ids.gd` moved.

- **Current milestone, before this entry, retained in full:** **M12 - Asset Parity - line 1 ARCHIVED; line 2 opened as an INVESTIGATION** on `docs/legacy-image-reference-resolution.md` (this branch). **The question it had to answer before any proposal could be written: is the 50 `ambiguous` + 32 `missing_source` image-reference population a resolution failure a better rule would fix, or a content gap no rule can fix?** The two answers imply entirely different lines, and the answer turned out to be **both** - which is why this investigation is worth more than a status count. **A mechanism exists, and it is not an invention.** The registry's own declared images rule is `basename match (web-root-relative form preserved, never rewritten)`, but each reference **already carries the disambiguating directory** (`/goals/1.png` vs `/packs/1.png`), and the rule discards exactly the component that settles the question. Joining the reference's own path onto `assets/images/en` resolves **50 of 50** ambiguous entries to a single existing file, **agrees with today's answer on 523 of 523** entries where both rules work (**zero** disagreements), and is a **perfect bijection onto the corpus**: **573** references -> **573** distinct files -> **573** files in `assets/images/en` -> **0** unreferenced. Every image file is named by exactly one reference at exactly the path that reference spells out, which is what distinguishes an authored rule from a fitted one. **The ambiguity is real, not cosmetic: 17 of the 25 candidate pairs are byte-differing (34 of the 50 entries), and all ten `goals`/`packs` pairs differ by an order of magnitude** (3,210 B against 65,092 B for `1.png`) - icon against card art. **A content gap also exists, and no rule closes it.** All 32 `missing_source` are **29** chapter `_m`/`_w`/`_old` variants, **2** prison images, and **1** stray, and a corpus-wide search under every extension finds **nothing anywhere** - absent, not mis-pathed. **Two figures I was following are corrected:** the "32 `missing_source`" is the **images kind only** and the repository-wide total is **42** (32 + 10 `item_sprites`, named and scoped out rather than dropped); and **three of my own instruments were wrong**, recorded in the investigation's section 10 - a path join that omitted the separator made the rule look like it broke **147** passing entries when it breaks **2**, `os.listdir` handed back a directory that was then hashed, and, the one that mattered most, **the appendix script shipped a logic error and running it printed 514/9 against the document's 523/0**. Had the appendix been shipped unrun, the document would have carried two contradictory numbers with nothing to adjudicate between them. **No client code resolves image references today** (`/chapters/`, `/goals/`, `/packs/` return **0** client files; `town.gd`'s three `images/en` hits are prose evidence strings), so this is **not a live user-facing defect** - it is a known ambiguity removed *before* something depends on it, and claiming otherwise would overstate the value.

- **Current milestone, before this entry, retained in full:** **M12 - Asset Parity - line 1 APPLIED, VERIFIED, SYNCED and ARCHIVED.** `asset-package-parameterisation` is archived as `openspec/changes/archive/2026-10-09-asset-package-parameterisation/`. It **creates one capability, `asset-package-census`** (**3 requirements**, **10 scenarios**), and **modifies two**: `first-building-conversion` and `first-unit-conversion` each have their assembly requirement replaced and **two** requirements added. **Lifecycle, each stage on its own remote branch from updated `main`, merged as a merge commit:** investigation `docs/legacy-m12-asset-parity.md` (`f7f9861`), proposal PR #344 `2e42640`, Apply PR #345 `9886cf6`, Sync PR #346 `850fc4a`, this archive. **An independent verifier ran before Archive and returned PASS WITH FINDINGS** - 3 MINOR and 1 INFORMATIONAL, none blocking - which is the correct order, because Archive is the stage that declares the change complete and must not be the first reader of its own diff. **Two of its findings were fixed here rather than deferred**, because both live in a file this change already owns and a later archive session is unlikely to see them: a **dead `import importlib`** in `census_targets.py` (line 33, used nowhere), and a **containment guard that was equality where the requirement says containment** - it refused `--out-root <repo>` but accepted `<repo>/anything`, and `evaluate()` builds `<out_root>/<domain>/<stem>`, so an out-root one level down would have written the whole census tree into the working copy. The guard now resolves both paths and refuses `repo_root in out_root.parents`, **decided before the `mkdir`** so a refused root is not left behind either. **Proven by reverting the guard, not by assertion: 2 measured failures**, both `AssertionError: 0 != 2` - the old code did not merely fail to refuse, it **ran the census into the repository and exited 0** - and the restore was sha256-verified (`6684d8a9...b70c1e`) with the baseline green before and after. A **third** test asserts the opposite direction, that a **sibling** directory whose name merely starts with the repository's is accepted, so the guard cannot be "fixed" into a string-prefix comparison. **The archived artifacts are six of seven pure renames at 100%**; the census delta is **79%** because this stage amended it, and the spec was amended identically in `openspec/specs/asset-package-census/spec.md` - recorded rather than described as a pure rename. **Verification could not run everything and says so**: `verify.ps1`, `verify-boot.ps1`, the 3,077-test compat discovery, `validate_content.py`, and the 11 injection probes were **not** re-run by the verifier, so their Apply-stage figures stand unverified by it. `openspec validate --all --strict` reports **73 passed / 0 failed** after the archive, against Sync's **74 = 73 main specs plus 1 change** - Archive removes the change and the total falls by exactly one, so **the composition is what distinguishes the stages, never the total**.

- **Current milestone, before this entry, retained in full:** **M12 - Asset Parity - line 1 APPLIED and VERIFIED on `docs/legacy-m12-asset-parity.md` (merged `f7f9861`): the tooling that makes a second package possible, plus the measurement of how many there are.** **The investigation's unit verdict was false and the Apply stage caught it.** The Propose-stage instrument reassigned `TARGET_STEM`/`TARGET_LEGACY_ID` but not `SOURCE = "assets/sprites/" + TARGET_STEM + ".swf"`, which is **computed at import time** and never moved, so all **365** unit targets were parsed from the same elephant SWF; it did not error because that elephant's bitmap `character_id`s happen to sit in most unit sprites' extraction directories. Driving the converters through their **CLI entry points** (D5) rather than by reassigning module constants is what turned a silent wrong answer into a failing one. **Corrected, measured: 817 candidates, 290 converted, 527 refused, 8 classes, 0 targets in several classes; buildings 222/452 (five classes, 133/61/20/14+2) and units 68/365 (seven classes over 297 targets, 90/76/57/44/18/11/1).** **D1 vindicated** - a required target is exactly what stops a batch run silently re-deriving one. **No refusal class fixed, no mass conversion** (D7/D8): the 290 packages are ~15,000 files, recorded as a follow-up. **D3 is load-bearing**: both packages change in one field (`content_version` `ddeca799...`->`c4e76e6d...`, `9d8ad3b3...`->`a0c3861f...`), `conversions.json` and `asset_ids.json` cascade by two lines each, and **two client pins moved with the artifact** (`test_package_loader.gd`), which **falsified this change's own scope guard** - recorded in `tasks.md`, not discovered from a failing battery. **11 of 11 probes detected** with measured counts (a=1 b=2 c=2 d=2 e=1 f=1 g=1 h=1 i=3 j=1 k=1), restores sha256-verified, baseline green before and after. **Two defects in my own guards were found by injection**: probe (g) first detected nothing, exposing a **tautology** (argparse's usage line lists every option name, required or not); and the committed-report timestamp guard **cannot see a tool mutation**, so a fresh-report guard was added - a *constant* fake timestamp is invisible to the determinism guard. **Three harness defects** were corrected, each of which would have misreported rather than failed, the sharpest being that it counted `[test] FAIL` - the **Godot** marker - in `unittest` suites, so probe (a) read 0 failures while the guard was firing. **An ordering lesson, because it produced a false green**: `guard-baseline.json` was regenerated before `verify.ps1` rewrote `first-render/report.json`, and `verify` cannot catch that. **Three groups moved, not two** - `m4_evidence` is regenerated evidence. **A second false claim was made and then falsified in the same task, and is recorded here because a green PR is exactly where a wrong claim survives unnoticed**: I read `guard_baseline.py` as hashing **raw working-tree bytes**, measured a CRLF checkout against a recorded digest, got a mismatch, and concluded - then committed - that the baseline **fails on a fresh default Windows checkout**, a **pre-existing** defect, with a `.gitattributes` pin to match. **It was wrong in my instrument, not the repository**: `guarded_bytes()` decodes UTF-8, passes binary through, and **normalises CRLF to LF before hashing**, so all **91** recorded digests reproduce on either checkout form and no pin was ever needed for that reason. I had already been told this line's fingerprint fix "generalises the guard's existing line-ending-invariant precedent" - the precedent was named in the task text and I built a claim on the assumption that contradicted it. **The pin is kept**, for the honest and weaker reason that this is regenerated evidence whose recorded digests should stay comparable across checkout forms. The transferable lesson is not the tally but the check: **a mismatch is only evidence once the expected value's own algorithm has been read.** **Final-state checks:** asset-registry **206 tests OK, 0 skips** (was 205-with-3-skips); `hash_manifest` **3,258 entries / 758,423,699 bytes**; compat **3,077 tests OK** (baseline reproduced, not skipped); validator `valid` **23/22/604**; guard baseline OK; `openspec validate --all --strict` **73 = 72 specs + 1 change**, correcting this change's own "71 + 1" text; `verify.ps1` exit 0. **The census is byte-identical across three runs** (`84b11bee...`, 354,636 bytes), after killing and re-running the set because two of my own process defects would have faked it - an out-root deleted before its digest was captured, and probes mutating files mid-run.

- **Current milestone, before this entry, retained in full:** **M11 - Social and Special Systems - line 6 of 6 APPLIED, VERIFIED and SYNCED. All six deliver items are now accounted for, and M11's exit criterion can be assessed.** Line 6 delivers `special mechanics` as the read-only **market / trade counters**, on the binding investigation `docs/legacy-m11-special-mechanics.md` (PR #337, merge `1c8786b`); proposal PR #338 `9094dbe`; Apply PR #339 merged `ab886f8`. **The promoted surface displaced the investigation's own rank #1**: the atom-fusion queue is already owned by `godot-unit-queues` under that line's archived decision D6, and promoting it twice would have produced two owners of one surface - a boundary nobody enforces. The displacement is recorded rather than silently resolved. **No route, no live phase, no executed-legacy fixture, and no `apps/compat-api/**` change** - all four decisions with measured reasons, and `DELIVERED_ROUTES`, `DELIVERED_ACTIONS`, `DELIVERED_REQUESTS` are empty arrays. **The corpus measurement shapes every claim limit: 8 of 10** committed save documents record `timestampLastTrade == 0`, for which the day-reset predicate `now // 86400 != last_trade // 86400` is **unconditionally true** and the count is cleared on every load, so the cap is reachable in the committed corpus in **`Nerri.json` only**. That is why the neutral-instant inference is *proved* rather than assumed: `command.py:471` is the only site that can raise the instant (`command.py:913` subtracts a **client-supplied** `seconds` and floors at zero), so a non-zero instant proves a trade actually ran. **The cap is the branch literal `20` at `command.py:470`, never derived from `MARKET_MAX_NUM_TRADES`**, and their equality is recorded as a **coincidence** because that committed constant has zero consumers. **The unclamped print is reproduced, not corrected**: the branch stores the count clamped while printing remaining-trades unclamped, so the figure goes negative from the 21st trade onward, delivered as a separately labelled field so the divergence at `command.py:473` is visible rather than silent. The reset predicate is **reported, never performed**, and `engine.reset_stuff` is referenced as its owner. **No enforcement**, because `numTradesDone`'s only reader is its own increment at `command.py:469`; no price, period, percentage, or increment bound; and no resource movement. **All nine injection probes were re-measured against the FINAL delivered state** - after the two corrections below - because a later edit can silently restore or remove guard coverage: measured `6, 4, 7, 27, 8, 2, 2, 3, 4` against the recorded **63**, **no count moved**, every restore byte-identical, git state unchanged. **Sync created one new main spec and amended none.**

- **Current milestone, before this entry, retained in full:** **M11 - Social and Special Systems - line 5 of 6 ARCHIVED, five delivered, and **one of the six deliver items still partial** (`special mechanics`).** `auction-schedule-projection` is archived as `2026-10-08-auction-schedule-projection`; investigation PR #331 `cd9db76`, proposal PR #332 `b908608`, Apply PR #333 `b2bafdd`, Sync PR #334 `dca93c7`, and the Archive PR carrying this entry. The two capabilities it delivered, `auction-schedule-normalization` (6 requirements) and `godot-auction-schedule` (7 requirements), are in the main specs. **The Archive stage was NOT purely archival, and it found three things worth more than the archive itself.** First, **a required check the Apply stage never ran**: task 2.2 requires the builder's own `test_build_auctions.py`, and section 5 ran `validate_content.py` and not it, so I reported Apply verified on a check I had never executed. Running it at the gate produced `Ran 86 tests ... FAILED (failures=1)`, and the failing test was **a guard that could only ever pass once**: it compared the working manifest against `git show HEAD:` and required the difference to be exactly `['auctions']`, which holds only while the section is uncommitted. Measured, `auctions` is absent at `af63a77~1` and present from `af63a77` on, so the test was green on the Apply branch and permanently red from the moment the Apply PR merged - **including on `main`**. Fixed on its own branch `fix/auction-manifest-section-guard` (PR #335 `c553c6a`) in a state-independent form, and re-proven by three injection probes with byte-identical restores rather than trusted, since loosening an assertion is exactly the change that silently stops guarding. One of those three is recorded rather than tidied: removing the builder's own section also trips the no-removal assertion, so the added presence assertion is **unreachable in the committed state** and is a belt for the pre-commit window only - the no-removal assertion is the real gate. Second, **the detection gap is larger than the defect**: `packages/game-content` appears in `verify.ps1` exactly once, at line 197, inside the SHA-256 pre/post **byte** guard, so **none of the twelve** `packages/game-content/tests/test_*.py` suites runs in any battery. That is why task 2.2 was missed and why the time bomb merged, and it is the **same class** as the stale-evidence-report gap recorded for the earlier lines: a committed artifact with no automated check comparing it against the code that produces it. **Two instances, one instrument, neither caught by `verify.ps1` or `verify-boot.ps1`.** Third, **all 48 task boxes were unchecked** at the gate, which combined with the first finding made blanket-ticking unacceptable. Every task was therefore re-derived from the implementation before ticking, and **the verifier's first run reported 11 FAILs of which all 11 were its own defects** - including a Python `def` regex applied to GDScript's `func`, a literal-`60` search that could not distinguish prose from a conversion (and so reported **the opposite of the truth**), a dict read as a list that made a comparison **vacuous**, and three forbidden-token scans over **raw source** that counted the prose documenting each token's absence as the token's presence - the precise inversion those claims are about. The fix was the two-state lexer `godot-construction-assist` had already been forced to build, not weaker checks; that lexer then had **two more defects of its own**, found by the verifier disagreeing with code already read: stripping string payloads removed exactly the dictionary keys task 3.2 checks, because GDScript dictionary keys **are** string literals, and a `"""` docstring was unrecognised so the lone quote in `auction["interval"]` falsely closed it. The verifier was then probed, because one that has only ever reported success is indistinguishable from one that does nothing: **twelve probes, all twelve detected, every restore byte-identical**. Those last three probed the **builder source** rather than the committed output and went **undetected**, exposing a uniform gap - the verifier checked the artifact without the code that produces it, the third instance of that class - closed by an added check that rebuilds into a **temporary work tree** with `--out-root` and compares produced bytes to committed bytes (identical, 1542 bytes, sha256 `8e9c1d958010b24a...`). That temporary work tree was itself non-obvious: an empty `--out-root` fails with `FileNotFoundError` on `manifest.json`, because the builder merges into an existing manifest and reads the normalized units package for its reference edge. **Fourth, the probe harness damaged two delivered files and this is the third recorded instance of one defect class**: it read with universal newlines and wrote text back, converting `auction_schedule.gd` and `auction_oracle.gd` from CRLF to LF, so all ten restores honestly reported `restored byte-identical: False`. Recovered with `git checkout --` and confirmed via `git cat-file` that the committed blobs still hash to `c04b416d8ef1c891...` and `6db9d6e6d1ec0558...` at **19627** and **20744** bytes with **zero** CRLF, so no damage reached the repository - and the honest signal is what caught it. Prior instances: the byte-count guard fixed in PR #280, and a `git show > file` redirection writing **UTF-16LE** earlier in this stage. **Three instances, one root cause: tooling that rewrites bytes without asserting that the bytes it read are the bytes it wrote back.** The scratch verifier and its probe were **deleted, not committed** - honest instruments that found four real defects, but single-use Archive scaffolding wired into no battery and guarded by nothing, which would repeat the very gap the stage recorded. **Verification actually run at the final state**: `test_build_auctions.py` **Ran 86 tests OK**; the full `packages/game-content` discovery **Ran 559 tests OK**; `validate_content.py` `valid` at 23 files, 22 schemas, 604 references; `hash_manifest.py verify` **3258 entries / 758,423,699 bytes**, unchanged; `openspec validate --all --strict` **72** after Sync and **71** after Archive, matching the corrected table in the change's own section 6.0; and `git status` clean apart from the intended files. **Zero preservation paths changed.**
- **Current milestone:** **M11 - Social and Special Systems - line 5 of 6 APPLIED, VERIFIED and SYNCED, five delivered, and **one of the six deliver items still partial** (`special mechanics`).** Line 5 delivers `legacy event systems` as two capabilities, `auction-schedule-normalization` and `godot-auction-schedule`, on the investigation contract `docs/legacy-m11-event-systems.md` (PR #331, `cd9db76`); proposal PR #332 `b908608`; Apply PR #333 merged `b2bafdd`, two commits `af63a77` (normalization) and `9749d51` (projection). **The target surface was chosen by measurement rather than by name**: the deliver item says "event systems", and `interval` and `expire` have **zero** occurrences outside `auctions.py` across all **eleven** legacy root modules, making the auction house the only interval- and expiry-driven system in the preserved server. **The headline finding is a bootstrap defect that is recorded and never repaired**: `auctions.py:32` guards on `FILE_AH_CONFIG` while `:33` reads `FILE_AH_STATE`, so `AuctionHouse()` raises `FileNotFoundError`. That is *why* no runtime `auctions/` directory exists in the repository, and repairing it would invent behaviour the original never had. **No executed-legacy fixture was captured, and the reason is stronger than a missing corpus row**: the behaviour has **no request path at all**, because all three routes and the module import are commented out. Obtaining a fixture would mean enabling them, which is the one thing the project forbids. **Exactly one derived value**: the duration in seconds, `interval * 60`, in one named function with a named inverse and a round trip, following the `COLLECT_MINUTES` precedent. **Preserved encodings, not normalized away**: `legacy_id` stays the committed **string** `uuid` (because `auctions.py:106` keys state by it), and `interval` stays in **minutes** with `interval_unit` recorded and no conversion in the builder. **The committed `betPrice` is carried and marked `bet_price_consumed: false`**, citing its zero-consumer measurement, and **no ordinal is claimed** for it, since no reconciled census of zero-consumer fields exists. **Normalization turned out to be a hard dependency**, amending committed §12: the client reads committed content only through `ContentRegistry`, so the projection could not have been delivered from `config/auctionhouse.json` directly. **Three corrections and one amendment are recorded rather than tidied away.** First, the requirement **"no `apps/compat-api/**` file is modified" was falsified by applying it**: adding any normalized output forces one pinned count inside an existing compat-API content-absence guard to move (`test_no_normalized_package_carries_a_research_section`, 22 to 23), so the spec, design D5 and the proposal were amended to the narrower claim that is true - no route, endpoint, envelope, dispatcher or save shape - with the cause recorded in each; the guard's meaning is intact and it now also scans the new file. Second, a **false correction** in the first draft of the report was found and reverted: it declared the committed `resource_tokens_substring.mana = 0` wrong by one, having counted raw occurrences **case-folded** while `build_auctions.py` counts them **case-sensitively**, so two measurements taken under different rules were compared and the mismatch called a correction; under the builder's own rule `mana` is genuinely 0 and only `xp` disagrees, and the case-folded view is still reported as the separately-labelled measurement it is. Third, my own §6.0 prediction of the `openspec` item count was wrong by one because it assumed one new main spec where this change declares **two**; the measured sequence is **70 to 72 to 71**. **A stale committed report from an earlier line was exposed and regenerated**: investigating the largest regenerated diff showed `evidence/unit-production/report.json` was already stale, because the M9 `unit-experience` line amended `production_flow.gd` and its suite without regenerating that report, and **nothing catches it** since `verify-boot.ps1` runs every suite **without** `--report=`. The gap is recorded: **no automated check compares any committed evidence report against the suite that writes it.** **Two tooling defects of the orchestrator's own** are recorded because both nearly produced a false conclusion: PowerShell here-strings consume backticks (one became a literal carriage return and broke parsing), and `git show > file` writes **UTF-16LE**, which under-matched and briefly led me to a wrong conclusion about `HEAD`. **Module placement was corrected in review**: the implementation placed both modules under `scripts/social/`, and they were moved to `scripts/events/` because `social/` holds only genuinely social modules, the closest precedent (`premium_purchase.gd`) lives in `scripts/darts/`, and the auction house has no friend, neighbor or assist concept - the same misleading-name defect `godot-friends` corrected. **Verification actually run** at the final state: the suite at **1218 checks** and `test_project_scope.gd` at **2223**, both exit 0; `verify.ps1` exit 0; `verify-boot.ps1` exit 0 with guard digest `6978b959...ff348` **identical before and after**; **1092** log files inspected for `[test] FAIL`, `^ERROR:` **and** `SCRIPT ERROR` with **zero** hits on all three (the first attempt at that grep matched zero files, because the logs are `.txt` and the filter said `.log` - the zeros were vacuous and were re-measured); the compat suite **3077 OK, unchanged**; the content validator `valid` at 23 files, 22 schemas and 604 references; the preservation manifest unchanged at **3,258 entries / 758,423,699 bytes**; `openspec validate --all --strict` **70** at Apply and **72** after Sync; and the report **36,636 bytes**, sha256 `495d29abd4e38ae01be36222...`, LF form, **byte-identical across three consecutive runs** and re-verified through `git cat-file` so the digest describes the committed blob rather than a checkout form. **Five injection probes were re-run independently rather than taken on the worker's word**, with measured failure counts: **4** for a helper borrowing no reserved word (which proves the declared-function inventory pin is the real gate and the reserved-name guard is the belt), **7** for a **suffixed** reserved stem that an exact-name check would have passed, **6** for arithmetic in a non-permitted function, and **1** each for the forbidden words `dead` and `unused`, the latter in the **oracle** module so the wording guard is proved to cover both. All five produced real `[test] FAIL` lines with no parse error - a parse-error detection proves nothing about a guard - every restore was byte-identical by sha256, and the post-probe suite returned to exit 0. **No preservation material changed**, and no runtime `auctions/` directory was created.
- **Current milestone:** **M11 - Social and Special Systems - line 4 of 6 ARCHIVED, four delivered, and **two of the six deliver items still partial** (`legacy event systems`, `special mechanics`).** Line 4, `godot-construction-assist`, is the `social rewards` deliver item, and the line's shape was fixed by the committed measurement rather than chosen: `attr["si"]` is already carried on `/v0/bootstrap`, so **no route was proposed and `apps/compat-api/**` is untouched** — the compat suite's **3077** baseline was **re-run and reported as a verified figure** (`Ran 3077 tests ... OK`, exit 0), not skipped. **The finding is a paid substitute for a friend, and the friend arm has no writer**: the list records **who filled each assist slot** and the only value any writer appends is the integer `0`, fixed by the author's own comment at `engine.py:142`; the committed corpus holds **53** `si` rows, **3** non-empty, **7** elements, **one** distinct value. **Three branches** reach the key and one is **not named for it** (`set_resource_allies` → `finish_si` at `command.py:644`), so the DELETE path has **two** dispatchers. **Three decisions, recorded rather than assumed**: **no route** (D1, `/v0/assist` rejected — a client affordance for a transaction that grants nothing is the surface this capability exists to refuse); **no executed-legacy fixture, a decision and not a limitation**, since `buy_si_help` *creates* the key when absent (`engine.py:139-140`) and so made a capture reachable; and **no ordinal claimed** for either gift field, because no reconciled census of zero-consumer fields exists and four earlier lines each numbered over a different scope. **Two figure corrections were made by measurement and recorded rather than tidied**: the `RECONCILIATION` table read `{"count": 4, "ids": [4, 12]}`, mixing a **row** count with an **id** count, and is now **four per-unit facts**; and a note calling ids 61/75 the corpus's *only* non-empty lists was **false** (gated id **9** carries `[0,0,0]`) and is now corrected **and asserted**. Missing key is **not** conflated with the empty list — three writers write three different values — and the absent `friend_assistable` check is **recorded, not enforced**, because enforcing it would refuse **2** committed corpus rows. **Four defects of this line's own work were found by measurement, all four in the suite's instrument rather than its modules**: the reserved-name guard scanned raw source and tripped on `ABSENT_HELPERS`' own text (now a declared-name, case-folded, bidirectional substring comparison); the ordinal guard had the **same** shape because the module's rationale for *refusing* an ordinal names four earlier figures in a comment (now a two-state lexer, with the rationale's presence **asserted** so the guard cannot be simplified back); the crafted-input assertions **assumed JSON decoding** where a GDScript literal is a real `int` (both paths now asserted separately); and the transport-token guard was **removed rather than duplicated**, because `test_project_scope.gd` forbids those tokens in every allow-listed file so a guard naming them can only exist in a form its owner rejects — the third instance of that shape in this project, handled by **delegating** the claim to the owner. **The eight injections were all detected with byte-identical restores, and their failure counts are measured: 6, 5, 5, 4, 1, 2, 2, 1**, summing to **26**. The draft's `3, 3, 3, 2, 1, 1` was an estimate of the guards rather than a count of them — the inventory pin is enforced by **four** independent checks — and probe 6 was raised from 1 to 2 by widening the probe itself. **Probes 7 and 8 were added to close task 4.1, and probe 8 found a real defect in the guard it was written to prove**: renaming the bag key `si` to `s1` in the owning module **exited 0 on its first run**, because the check matched `si` as a **bare two-character substring** and `si` occurs inside "assist", "position" and "using" throughout that module, so the check **could never fail**. All three ownership names are now matched as the **quoted literal** a GDScript source carries, and the suite additionally asserts the bare form is *still present* after a rename, so the reason the quoted form is required cannot be unlearned. Probe 7 fires **2** of the 3 ownership guards and that is the **correct** result — the third names the bag key the rename does not touch — which is recorded on the probe row rather than left to read as an undercount. **A harness fault nearly produced six fake passes and is recorded because of it**: the first run reported `failures=0` with **53** engine error lines per function probe because the harness wrote `\r\r\n` on every pre-existing line, so the module stopped **parsing** and the suite exited 1, which a "did it exit non-zero?" gate records as a *detection*; the harness now normalises to LF before mutating **and aborts when a probe fails with no `[test] FAIL` line**. **A fourth harness defect is a task deviation, recorded rather than satisfied**: the final-newline rule was a universal *content* rule — every probed file ends with a newline — which is true of the two modules this change authored and **false of `stored_item_flow.gd`**, a pre-existing delivered file that legitimately ends with `return out` and no newline. So it was not detecting truncation, which is what it was written for; it was asserting a style property and it aborted the probe set. The replacement pins the restored file's **final byte to the baseline** and *reports* each file's newline state rather than guarding it. A tautological check written during that fix, testing that a file both lacks and ends with a newline, was **deleted before it shipped**. Probe 4 borrows no reserved word, so only the inventory pin and the two count pins see it, which is what makes the pin the real gate and the reserved-name guard the belt. **This line COMPLETES the `godot-unit-behaviors` gift census rather than duplicating it**: `gift_level` was already there units-only and now carries its buildings side (8 and 11), `giftable` was in **no** census and is **added** (2 and 2), `legacy_reads: 0` for both is **measured** over all seven legacy modules, and the correction chain is retained in full — investigation **20**, measured **21**, **amended 22** — with the `building_distinct` column deliberately **partial** and its size pinned to 2. Two candidate amendments were **rejected**: `godot-stored-item-placement` (this line moves no state) and `social-tables-normalization`, whose motivating claim was **falsified** because all 26 `social_items` ids are distinct. Observed: assist suite **495** checks exit 0 (the **48th** hermetic suite), amended census suite **598**, amended scope suite **2138**, `verify.ps1` exit 0, `verify-boot.ps1` exit 0 with **48** hermetic suites (was 47), **23** live phases **unchanged** (none delivered), **226** assertions (was 224), guard digest `6978b959...ff348` identical pre/post, **1040** log files with zero `FAIL`/`ERROR`/`SCRIPT ERROR` lines, content validator `valid` (22 outputs, 21 schemas, 604 refs), preservation manifest **3,258** entries / 758,423,699 bytes, and `openspec validate --all --strict` **69 passed / 0 failed**. The report is **21,384** bytes, sha256 `776aa8c7...10e94`, byte-identical across three runs and written in **LF form** — the committed Git blob form, re-verified at Sync time through `git cat-file` as **21,384** bytes with **zero** CRLF — so its raw and LF byte counts are equal and its digest needs no form qualifier, and the qualifier is load-bearing rather than decorative, because a CRLF working-tree checkout of the same content measures **21,981** bytes. It now also records the **sha256 of both delivered modules as they sit on disk**, because every probe's credibility rests on a byte-identical restore; the record names its own form and asserts `comparable_to_lf_normalised_digest: false`. Two task-verification gaps were closed in the process, and both are measurements rather than assertions: the corpus walker is extracted into `_measure_corpus(allow)` so an **empty allow-list is a second real call** that must return zero documents, zero rows and zero assist rows — without it, a walker ignoring its argument would reproduce every figure and every comparison would still agree; and **both directions of the reconciliation are now re-derived every run** from the content gate and the corpus carriers, asserted **disjoint**, because a table compared only against itself is not evidence. A **tenth recorded flaky surface** was found here, **diagnosed**, and **NOT fixed**: the compat discovery failed once on `test_collection_endpoint.ContainmentTests.test_session_stays_byte_identical_and_bootstrap_changes_only_its_own_targets` with `playerInfo.last_logged_in` 1791375563 against 1791375562 and every other field identical; the file then passed **five consecutive times** alone and the full discovery passed at **3077**, so it is the recorded **sixth** surface firing again — but the investigation found the earlier record got the fix wrong. That surface was previously *fixed* by exempting a volatile field, and **the fix was applied at the wrong depth and never took effect**: the guard iterates the top-level *sections* of `player_info` and tests each section name against `VOLATILE_PLAYER_INFO_FIELDS = {"last_logged_in"}`, but the wall-clock stamp lives one level deeper at `player_info.playerInfo.last_logged_in`. No top-level section is ever named `last_logged_in`, so the exemption is **dead code** and the nested field walks straight through to the per-section equality. That it *is* a clock and not state is settled by `test_compat_v0.py:333`, which asserts `player_info["playerInfo"]["last_logged_in"] == player_info["timestamp"]`. **Not fixed here**, established by `git diff --name-only` returning no `apps/compat-api/**` path and excluded by design D1: the honest fix belongs to the capability that owns `/v0/session`, and reworking an already-archived line's containment assertion from an unrelated change is how an unearned fix ships. An earlier, unrelated flake in the same line — `verify-boot.ps1` on the untouched `test_town_xp`, which PASSED **767** checks with only the recorded RID-leak shutdown line as an error — was re-run rather than fixed. Three parse and typo faults in this line's own suite are recorded rather than hidden, and the third is instructive: a **misspelled dictionary key** (`of_these` for `of_those`) aborted `_check_reconcile` mid-function while the suite **exited 0 and printed `SCRIPT ERROR`**, because `test_base.gd` records a function abort as a pass — so that recorded defect has now caught a real fault in this line **twice**. **Sync**: `openspec validate --all --strict` **70 passed / 0 failed** (was 69; the new capability is exactly one added item), and the new main spec `openspec/specs/godot-construction-assist/spec.md` was created with **9** requirements and **21** scenarios, while three `godot-social-state` requirements were replaced wholesale with their MODIFIED deltas — which is safe only because each delta block is a *complete* requirement, body plus every surviving scenario; the script located blocks by exact heading and aborted rather than guessing, and the neighbouring requirements were confirmed untouched. **Sync found one of its own false claims, and the finding is recorded here rather than tidied away**: the change's own delta asserted that ids 61 and 75 "are the corpus's **only** non-empty lists, at `[0, 0]` each", and the corpus holds **3** totalling **7** elements — the third is the **gated** item **9** at `[0, 0, 0]`. This was re-measured from scratch over the canonical 10-document allow-list rather than taken from the evidence report, and it is the **second** instance of the defect, because the *sibling* `godot-social-state` requirement in the **same change** already carried the correct count — so two specs of one change disagreed and the corpus settled it. The clause was corrected in **both** the delta and the new main spec, with the superseded wording still visible. A follow-up defect of my own was caught by reading the output: the first insertion landed *inside* the three-fact bullet list, orphaning bullets two and three after a paragraph with no blank line, so the correction was moved below the complete list. Two claims about the evidence report were also checked rather than repeated: its `teams: [1.0]` is scoped to **`si`-carrying** rows, so the `[1, 3]` an independent walk produced over *all* placed rows is a **different measurement, not a discrepancy** — and the delta's `content_version` claim **holds**, every carrier recording `null`. One figure in four documents was found claiming a form it does not hold in all forms: "written in **LF form**, so its raw and LF byte counts are equal" is true of the committed Git blob — re-verified through `git cat-file` as **21,384** bytes with **zero** CRLF — and **false of a CRLF working-tree checkout**, which measures **21,981** bytes for the same content. The figure and digest are therefore both **blob-form** figures, now stated as such and aligned to the wording the friends line had already got right. This is the **second** instance of the byte-form defect class here; the first was PR #280. The assist suite (**495**) and the scope suite (**2,138**) were re-run unchanged after the spec writes, because both read spec files for their ownership assertions. **Archived** on branch `chore/archive-construction-assist` as `openspec/changes/archive/2026-10-07-social-rewards-assist-projection/`, the fourth merged PR of the lifecycle and the fifth stage: investigation #326 `5ad1cdf`, proposal #327 `95e5909`, Apply #328 `5d4ce3d`, Sync #329 `2fcd651`, and this archive - each stage on its own remote branch, each merged as a **merge commit**, no branch reused across stages. **The archive moved all six change artifacts by `git mv` and every one was recorded by git as a pure rename**, including `.openspec.yaml` - so nothing was rewritten on the way in. **The pre-archive sync state was verified rather than assumed**, which the archive workflow requires before it will move a change: all **9** `godot-construction-assist` requirements are present in the main spec with **identical** bodies, and all **3** modified `godot-social-state` requirements are present with identical bodies and their scenario counts **grown** 2 to 3, 2 to 3 and 1 to 2 with **zero lost**, checked against the pre-sync spec read from git rather than from memory. `openspec validate --all --strict` then read **69 passed / 0 failed**, back to the Apply-stage baseline: the `change/` item disappears on archiving while `spec/godot-construction-assist` remains, so 69 at Apply, 70 while the change was still active at Sync, 69 again once archived. **Figure correction, made by measurement rather than tidied**: this change's own two Project Status entries called M11 "**line 4 of 4**", and read `social rewards` as its last deliver item. Both are wrong. M11's milestone block lists **six** deliver items - `friends`, `visits`, `scores`, `social rewards`, `legacy event systems`, `special mechanics` - and the ledger's own entries for lines 1 through 3 all say "of **6**". Only the **live** entry was corrected, because the superseded bullet is retained in full as the historical record; note that the **live cursor bullet already had this right**, saying every one of the six items is now delivered or closed by measurement with the two partial items as the remaining work, so the two entries disagreed with each other and not only with the milestone block. **The correct reading is that line 4 closed the last *unexamined* item** - `visits` and `scores` were already checked and rejected on their own merits - and that M11 is **bounded but open**, with `legacy event systems` and `special mechanics` still partial. **The next eligible objective is `legacy event systems`**, and each of the two needs its own committed investigation before any proposal; neither may be proposed from this cursor's evidence. **No further change is begun here**: per the ledger's own rule the cursor is advanced, not acted on.

- **Current milestone, before this entry, retained in full:** **M11 - Social and Special Systems - line 4 of 4 INVESTIGATED, before proposed, three delivered and archived.** The investigation contract `docs/legacy-m11-social-rewards.md` is committed (this branch) for the last unexamined deliver item, `social rewards`. **It falsifies the standing classification of that item**, and the correction is the point of the entry: `docs/legacy-m11-social.md` §3/§7 and the roadmap's own `Next eligible objective` bullet classified `social rewards` as *content committed, behaviour absent* on the strength of three tables with zero consumers. That measurement is **reproduced** - `neighbor_assists`, `findable_items`, `social_items` and `workers` all measure **0 / 0 / 0 / 0 / 0 / 0** across all 11 legacy modules under six rules, and the raw `config/main.json` citations `:44946` / `:45047` / `:47262` are confirmed, not corrected - and it is **false of the deliver item**, because the preserved server holds a social-assistance state machine that is persisted, written, dispatched from **three** branches, and recorded in the committed corpus, and none of it lives in those tables. **`attr["si"]` is "Socially In Construction" and the expansion is not inferred**: `engine.py:19` states it verbatim and adds *"because the game expects it"*, an admission that it is a client-display concession. The token is unmeasurable raw - **150** whole-file occurrences over **126** lines across **8** modules, because it sits inside `using`, `version`, `signature`, `sessionid` and `buy_si_help` itself - so the word-boundary rule gives **6** occurrences on **6** distinct lines, **all** in `engine.py` (`:24`, `:139`, `:140`, `:142`, `:146`, `:147`), across three functions. **The finding is the second of the two author comments**: `engine.py:142` reads `attr["si"].append(0) # 0 is for buying instead of hiring friends`, so the list records **who filled each assist slot** and the **only writer ever fills it with the paid arm**. **The friend arm has no writer anywhere**, and the corpus proves it rather than assuming it: over the canonical **10**-document allow-list (`magic_flow.gd:554-566`) and **3,372** placed rows - figures that reproduce `magic_flow.gd:588` exactly - **53** rows carry `si`, **3** are non-empty, and there are **7** elements totalling **one distinct element value, the integer `0`**, with no non-zero, float, string, `null` or non-list value anywhere. All 53 are on player team 1, matching the `if player == 1:` guard at `engine.py:15`. `del attr["si"]` has **two** dispatchers, not one: `buy_si_help` (`command.py:549`) and `finish_si` (`:561`) name them, but **`set_resource_allies` (`:637`) calls `finish_si` at `:644`** while also stamping `item[3]` and writing a client-sent `resourceAlliesMarket` - an effect `godot-social-state` already records at `social_state.gd:275-279` with `reproduced: false`, so the **effect is owned and the mechanism is not**. Both dedicated branches require only that `map_get_item` return non-`None`: there is **no `friend_assistable` check, no type check and no team check**, so a client can open an assist list on any row. **Nothing is charged and nothing is granted** - `buy_si_help` makes no `apply_resources` call and no `bought_unit_add`. **Three facts are recorded as gaps rather than explained**, because two of them falsify any claim that `si` implies the flag: **2 of 53** `si` rows sit on ids **61** ("Allies Building") and **75** ("Recon center") that do **not** carry `friend_assistable`, and those are the corpus's **only** non-empty lists at `[0, 0]` each, while their `content_version` matches a genuine carrier's, so the flag was not added later; **2** flagged ids are placed with **no** `si`; and **8 of 26** flagged ids are never placed. `buy_si_help`'s absent flag check would produce exactly `[0, 0]` after two appends and `map_add_item_from_item` (`engine.py:33-34`) bypasses the gate entirely - both are **candidates, not measurements**. **The committed reward schedule is uniform**: `neighbor_assists.reward` is `{"cash": 0, "coins": 50, "xp": 15}` on **all 5** entries - **one distinct object of 5**, all three keys `int` - so even a reader would have exactly one number to give; `findable_items.coins` is `100` on all **10**; `social_items.worker_cost` is `int` over `{1,2,3}` with `workers` a display `str` on all **26**, and `social_items.legacy_id` is an **item id** while the other two tables' ids are table-local, so intersecting those two with building ids would be a category error and is not done. **Two more committed fields have zero legacy consumers**: `giftable` (`int`, on all 470 buildings + 429 units + 1 special, `1` on 20 buildings and 10 units) and `gift_level` (`int`, all three, buildings `0..10`, units `0..40`) both measure **0 / 0 / 0 / 0 / 0 / 0** over the 11 modules, and **no ordinal position is claimed for either**, because no reconciled census of zero-consumer committed fields exists in this repository and the earlier "sixth"/"seventh"/"ninth"/"tenth" labels were each taken over a different scope. **`gift_level` is already recorded, for units only** (`unit_behaviors.gd:355`), and **`giftable` is in no delivered census at all** - recorded here as a gap in a delivered artifact, not as a fact about the legacy server. **The recommended shape is a read-only line with no route and no `apps/compat-api/**` change**, because `attr["si"]` is already carried on `/v0/bootstrap` (read at `town_state.gd:333` straight off row slot 6), which would leave the compat suite at its **3077** baseline as a *verified* figure as `godot-friends` did; a `/v0/assist` route is recorded as the **rejected alternative** because both branches mutate a row while granting nothing and charging nothing, and `set_resource_allies` must be settled first. **An executed-legacy fixture IS reachable** - unlike the refusal lines - because `buy_si_help` creates the key when absent, even though `fresh-player.json`, `fresh-player-pre-migration.json` and `initial.json` each carry **0** of 40 rows with `si`. **Three of this investigation's own instrument faults are committed with it** rather than fixed in place: a string-vs-int comparison reported **0** overlaps because the normalized package stores `properties` flags as **strings** (the identical trap `godot-unit-movement` recorded); a `repr`-keyed counter cannot distinguish `1` from `'1'`, since `repr(1)` is the *string* `'1'`; and the first corpus scan walked a glob rather than the canonical allow-list, so its **row** figure survived at 3,372 while its **document** denominator was wrong.

- **Current milestone, before this entry, retained in full:** **M11 - Social and Special Systems - line 3 of 6 APPLIED AND VERIFIED, two delivered and archived.** Line 3, `godot-friends`, is the **first line in this project that adds no route and touches no Compatibility API file at all**: `/v0/bootstrap` was measured to already carry the roster at `player_info.neighbors` (5 entries, 18 keys, leaf-identical to the committed executed oracle on every entry), so `apps/compat-api/**` is untouched and the compat suite **stayed at its 3077 baseline** - a *verified* result for this line rather than a skipped check. **The deliver item's name is the opposite of what the preserved server has.** `neighbors()` (`sessions.py:191-221`) returns **every other loaded village, unconditionally**, with no add, no remove, no accept, no decline, no consent and no direction anywhere in the preserved source, so the line delivers a **roster** and refuses the relationship vocabulary. Membership derives from **code, never from a file count**: every `villages/*.json` except `initial.json` (skipped at `sessions.py:78`) is 7 loaded villages, minus the two-pid literal pair is **5** members; both pids ship as literals because `sessions.py:173-174` and `:196-197` hardcode them and nothing in `config/` or the normalized content package names them, so there is nothing to derive them *from*, and deriving the exclusion from content is recorded as the **rejected alternative**. **The committed classification of `friends` was falsified before this line was proposed** - `docs/legacy-m11-social.md` §7 called it *zero legacy occurrences*; re-counted over all eleven modules under six rules it has **5** whole-file and **4** code-only occurrences, all four code-only ones in `sessions.py`. That is why `godot-social-state`'s requirement 1 was **amended as an ownership hand-off** rather than left standing: its recorded premise was measured false, and the hand-off moves **zero** state fields because a roster entry is not private state. **M11's exit criterion is NOT MET and remains unfinished rather than unsatisfiable**: `social rewards` is the only deliver item not yet examined.

- **Current milestone, before this entry, retained in full:** **M11 - Social and Special Systems - line 2 of 6 DELIVERED and ARCHIVED.** The milestone opened on 2026-10-06 with the committed investigation `docs/legacy-m11-social.md`; line 1, `godot-social-state`, closed out that same day, and line 2, `godot-darts` (darts plus premium accounts), closed out on 2026-10-07. **Line 2's finding is a committed price with zero consumers**: `get_premium_days` returns the committed **duration** and never reads the amount recorded beside it (`get_game_config.py:181-189`), so **no price is charged** and all **seven** stored resource slots must be byte-identical. That is a **refusal, not parity**, because `engine.apply_resources` (`engine.py:251-271`) unpacks **eight** slots (slot 0 read into `unknown` and never written; **seven** real write targets, each `max(current + delta, 0)`) and `command.py:40` applies that **client-sent** vector *before* the `if cmd ==` chain opens at `:42`, so a legacy client could pair a debit with this purchase. It is deliberately **not** the same mechanism as `research_buy_step_cash`, where the server *discards* a client-sent price; here it *ignores* a committed one. **Two invariants were invented and refused**, each with a corpus fact behind it: the shot list stays **unbounded** and the shot index is **never** tested against the committed `darts_items` schedule, because `villages/Nerri.json` records shot index `0`, which is absent from the committed `1..27` ids - a membership test would contradict the corpus rather than reproduce the branch. The client-dictated **won-shot** outcome is refused too, and the difference from the preserved branch is recorded as a **divergence**, never as parity. **Two corrections to committed figures were made by the Apply stage and are recorded rather than silently edited**: **C3**, the corpus denominator is **33** canonical documents and not the 231 the investigation reported, because 200+ of those are generated `tests/fixtures/**` `before.json`/`after.json` pairs; and **C4**, `dartsGotExtra` is `false` in **33 of 33** documents, which is exactly why the client-dictated `won_extra` refusal has **no corpus evidence at all**. **M11's exit criterion is NOT MET and is still unfinished rather than unsatisfiable**: line 2 advanced the **`legacy event systems`** and **`special mechanics`** deliver items - darts is the one special system with genuine multi-branch state, four branches across six fields - while **`friends`** and **`social rewards`** remain the unexamined items and `visits` and `scores` were already rejected by measurement.

- **Current milestone, before this entry, retained in full:** **M11 — Social and Special Systems — line 1 of 6 DELIVERED and ARCHIVED, 5 of 6 deliver items still unexamined.** The milestone opened on 2026-10-06 with the committed investigation `docs/legacy-m11-social.md` and its first line, `godot-social-state`, which is a **refusal line established by measurement rather than by assumption**. **The finding: social CONTENT has zero consumers and social STATE exists but is never written.** All three committed social tables — `social_items` 26, `findable_items` 10, `neighbor_assists` 5, **41 entries** — have **zero** consumers under six counting rules over the eleven legacy modules; of **19** measured social state fields, **12** have zero occurrences and **12** are write-less; and exactly **one** real social writer exists, `set_resource_allies` (`command.py:637`), which sets `map["resourceAlliesMarket"]` from a **client-sent** `args[0]` — recorded verbatim and **not reproduced**, with no endpoint delivered. **M11's exit criterion is NOT MET and cannot yet be assessed**, because 5 of its 6 deliver items have not been examined at all; unlike M10 this is **unfinished rather than unsatisfiable**, and the two must not be conflated. **Prior milestone, whose ledger follows unchanged:** **M10 — Missions and Combat — DELIVER LIST COMPLETE, 7 of 7 accounted for:** `mission vocabulary`, `combat actions`, `damage`, and `rewards` are DELIVERED and ARCHIVED, while `mission loading`, `mission state`, `death`, and `mission completion` were each CLOSED BY MEASUREMENT with no undelivered surface rather than deferred. **M10 opened by measuring two of its own deliver items out of existence and closed by measuring four of seven that way, leaving three delivered.** The milestone does not advance on that accounting alone, because its **exit criterion is NOT MET** — and that verdict is now recorded as **unsatisfiable from this oracle** rather than unfinished, which is a different statement and is stated as one.  **`rewards`, the last deliver item, was investigated, delivered, and ARCHIVED on 2026-10-06**, so **M10's deliver list is now COMPLETE — all seven items accounted for — while the exit criterion remains NOT MET.** That verdict is now recorded as **unsatisfiable from this oracle** rather than unfinished: the preserved server has no combat rule to reproduce and nowhere to store one, so there is no combat loop to make work (re-measured below). The `rewards` investigation on `docs/legacy-m10-rewards.md` had first established that `rewards` was a **real, undelivered surface** — the preserved server records that a reward was taken and nothing about what it was — so the item was neither a closure nor invented. The milestone opened with a committed investigation, **`docs/legacy-m10-missions.md`** (PR #283, merged `e4fc5e2`), and its verdict reframed the first objective before any code was written: **mission *state* was already delivered.** `collect_mission` (`command.py:430-442`) is the only **dedicated** mission command in the preserved server — `set_quest_var` (`command.py:111`) is a **second writer** of the mission pointer, from unvalidated client input, one correction the M10 mission-completion investigation records — and is owned by `godot-quests`; `idCurrentMission` has **2** writes and **0** reads; `timestampLastChapter` has **2** writes and **0** reads, the second inside `fast_forward` as a client-supplied subtraction; **there is no mission-loading command**; and all **ten** committed save documents have `maps` of length **1** with `default_map` 0. So the first objective was **not** "mission loading" — that phrase does not mean a mission map, one of the four corrections the investigation records — and the only undelivered surface was **vocabulary**. **Line 2 (`combat actions`) was the first combat line that was NOT a refusal**, because `end_attack`, `kill`, `sell`, and `resurrect_hero` all mutate state; it delivered one server-derived destruction with the client-dictated count **refused**, and recorded the legacy `max(0, sent - survived)` arithmetic as a **divergence** rather than reproducing it. **Line 3 (`damage`) was DELIVERED and ARCHIVED, and it was NOT a pure refusal**: the refusal is primary and is stronger than any recorded so far -- not merely "no code was found" but "there is nowhere to store damage" -- but the same investigation surfaced a real, state-mutating, capturable surface no delivered line owned, the `privateState.magics` ledger, so the line delivered that counter instead.** **M9 — Progression remains CLOSED** with its exit criterion "Primary long-term progression systems work" **NOT MET**, a property of the **oracle** rather than of the modern client. **M8 — Units** is COMPLETE with its exit assessed MET, all eight lines delivered and archived; **M7 — Construction and Economy** remains complete with its exit assessed MET, as do M6 and the M0—M5 deliver lists.
- **Roadmap cursor:** **M12 - Asset Parity, deliver lines 1, 2 and 3 delivered, verified, synced and archived; the desync family's downstream measured; the untouched 118 partitioned by where they diverge; and the `FILL_GRADIENTS` branch now MEASURED at the offsets it actually reads, which is the objective the previous stage named. No line is proposed and none may be.** The measurement is committed as `docs/legacy-m12-fill-gradient-measurement.md`. Its findings, in order of how much they constrain later work: **(1) after a gradient `FILLSTYLE` the reader resumes at an offset from which the following line count cannot be satisfied inside the shape tag it was read from, in 86 of 87 cases**, measured against the tag extent, which comes from the SWF tag header and is never shown to the parser; the same measurement at the identical failure stage over the 5 shapes that stop through a **solid** `FILLSTYLE` finds **1**, and that one is a mid-stream `NewStyles` case the previous stage had already recorded as not the shape's own array, so the groups do not even compare like with like; the divergence is therefore bracketed to the inside of the gradient record, after the type byte - **(2) across the whole 817-target population there are 129 gradient blocks in 124 targets and NOT ONE is in any of the 290 targets that convert**, so the branch has no successful instance in the committed corpus and cannot be calibrated by one; **(3) the obvious reading is REFUTED** - the gradient block does **not** overrun or consume its own tag, its span is smaller than the bytes remaining in **87 of 87** cases by 2 to 314 bytes, so it stops in the wrong place rather than running off the end of anything; **(4) leaving the reader mid-byte is NOT a defect**, 62 of 87 exit unaligned because `parse_matrix` is bit-oriented and legitimately ends mid-byte, and this looked like a signal and is not one; **(5) the `0x13` focal branch is UNMEASURED, not clean**, no `0x13` type byte is read anywhere in the population, so the branch that reads two focal bytes on the fill type rather than on a flag bit is entirely unexercised and silence about it is not a result; **(6) five controls pass** - a **planted** 18-byte payload reporting **22 of 22** offsets known in advance *before* any population figure was read, **inertness at 817 of 817** identical verdicts and refusal classes, **817 of 817** agreement with the committed census, a tag-extent oracle over **4347** parsed shapes with all eight padding buckets populated and none outside, which independently reproduces the previous stage's shipped shape count, and a discrimination check at **10** distinct entry bytes and **42** distinct spans. **The SWF format specification was deliberately not consulted**: this is a measurement, and naming what the record should have contained would be a diagnosis. The next eligible objective is bounded and named: compare the measured layout against the documented SWF gradient layout, one field at a time. **The two open decisions are unchanged and still not pre-authorised** - mass-converting the 290 available packages, and revisiting the three scope-decision classes - and neither was advanced by this stage, which changed no production code.
- **Roadmap cursor, before this entry, retained in full:** **M12 - Asset Parity, deliver lines 1, 2 and 3 delivered, verified, synced and archived; the desync family's downstream measured; and the untouched 118 now PARTITIONED BY WHERE THEY DIVERGE, which turns "not one defect" from a statement about one defect's reach into a routed population. No line is proposed and none may be.** The trace is committed as `docs/legacy-m12-shape-trace.md`. Its findings, in order of how much they constrain later work: **(1)** the **118 untouched** are **three groups, not one** - **87** declare a **gradient** fill type as read (`0x12` radial **57**, `0x10` linear **30**; 78 unit / 9 building) and stop in the LineStyleArray, **5** declare `0x00` solid, **25** stop inside the FillStyleArray across **four different classes**, and **1** fails on an inline read; **(2)** the located defect is a **solid** fill colour width confined to the `FILL_SOLID` branch, so it **structurally cannot reach the 87** - which is why the patch moved 2 and not more; **(3)** in those 87 the walk reaches the line count with the reader at the wrong offset: the declared FILL count is **1** for **91** of 92 and the declared LINE count takes **46 distinct** values including **65535**, exceeding the styles actually entered for **89 of 92**; **(4)** **four controls all pass** - calibration over all **290** converted targets with **4347** shapes and no fabricated failure, which independently reproduces the shipped shape count; **inertness at 272 of 272** identical refusal classes; **4 distinct** leaf stages so the partition is not one bucket; and the own-versus-mid-stream detector returning **both** values in one process. **No cause is established for the 87 and none is claimed.** The `FILL_GRADIENTS` branch contains an expression of the **same textual form** as the one located as defective, recorded as the **next place to measure** and explicitly **not** as a diagnosis or a fix. **Six instrument faults are committed with it**, and the third is the standing lesson re-earned: the own-versus-mid-stream detector tested `depth > 1` when the shape's own `parse_fill_style` is already at depth 2, so it returned a clean, uniform, confident **True for all 118** and separated nothing - the same defect class as `docs/legacy-m12-signed-rect.md` C-4's 1,154 "failing shapes", where a check with no discriminating power returned a tidy aggregate that would have supported a conclusion. **The next eligible objective is a measurement of the `FILL_GRADIENTS` branch**, recording per-ratio offsets and the offset the reader believes it is at on return to the shape's own byte stream - **not** a line, and **not** another grammar enumeration. **Two decisions remain open and are not pre-authorised:** mass-converting the 290 available packages, and revisiting the three scope-decision classes.
- **Roadmap cursor, before this entry, retained in full:** **M12 - Asset Parity, deliver lines 1, 2 and 3 delivered, verified, synced and archived; and the desync family's downstream now MEASURED for the first time, which closes the question the signed-RECT record left open and leaves the family unproposed for a sharper reason than before.** The narrowing experiment is committed as `docs/legacy-m12-desync-downstream.md`. Its findings, in order of how much they constrain later work: **(1)** the committed `tools/asset-registry/target_census.json` is **measured current** - all **817** targets return identical verdicts and identical refusal classes under the shipped parser, so the family's recorded baseline stands and needs no re-baselining; **(2)** the downstream picture, which `docs/legacy-m12-signed-rect.md` C-4 recorded as **never measured**, now exists - correcting the located defect moves `unknown fill style` 137 -> 26 but moves `shape byte overrun` 104 -> **187**, because **84** targets flow directly from the former into the latter, so the family **cascades deeper into the parser rather than exiting it**, and only **8** ever reach asset resolution; **(3)** the family is **not one defect** - **118 of 272** targets are **byte-identically untouched** by the located layout, which is a *negative* result bounding its reach and nothing more; **(4)** only **2** convert, `1076_robo_soldier_m` and `1155_dwarf_soldier`, independently reproducing C-3. **No line is proposed and none may be.** The next eligible objective is **not** another grammar enumeration and **not** a line: it is a **per-shape trace** recording where inside a shape the walk first diverges, because **all 272 targets record `problem_count` exactly 1** and the census therefore carries no positional information at all. **Two decisions remain open and are not pre-authorised:** mass-converting the 290 available packages, and revisiting the three scope-decision classes - which this measurement newly sizes at **286 of 527** refused targets (**54%**), and shows are **domain-split**: `unresolvable bitmap fill` is **100% building** (141 of 141) and PlaceObject# is **100% unit** (70 of 70), so the bitmap-fill policy cannot be a symmetric decision.
- **Roadmap cursor, before this entry, retained in full:** **M12 - Asset Parity, deliver lines 1, 2 and 3 delivered, verified, synced and archived; the FX / animation re-scope decided; the RECT sign-extension defect fixed; and the desync family still carries NO proposed line.** Line 3 `rect-bounds-sign-extension` is archived as `openspec/changes/archive/2026-10-10-rect-bounds-sign-extension/`, having **repaired 74 of the 290 converted targets and left 0 inverted rectangles across 4347 shapes**. The milestone's **remaining** work is the desync family, which is underdetermined in 5 of 6 parameters and converts **net 0** across all 817 candidates, so the next objective is a **narrowing experiment**, not another delivery line. **Two decisions remain open and are not pre-authorised:** mass-converting the 290 available packages, and revisiting the three scope-decision classes (DefineShape4, PlaceObject3, bitmap-fill policy).
- **Roadmap cursor, before this entry, retained in full:** **M12 - Asset Parity, deliver lines 1 and 2 delivered, verified, synced and archived, the FX / animation re-scope decided, and the eight refusal classes investigated; the desync family's origin is PARTIALLY LOCATED with its end-to-end result now CORRECTED, and a separate RECT defect is LOCATED, FULLY IDENTIFIED and ready for a `fix/` line.** **The cursor does not advance to a line**, because the ledger's rule is that the cursor is advanced, not acted on, and the correction has to land first. **The next eligible objective is a `fix/` line owning `parse_rect_bits`**: add sign extension to the four RECT fields (D1), replace `max(0, ...)` with a fail-closed refusal (D3), amend the **three** pinned test sites, and regenerate the **one** affected committed package. **D2 (`width_px` from the far edge rather than the extent) is separable** and may ride the same line or a second one; it is reported separately precisely so its attribution is not confounded with D1's. **Do not propose a desync-family line**: it is net 0 across all 817 candidates and remains underdetermined, and its previously recorded end-to-end figure of "0 of 272" is corrected to 2 here rather than quietly replaced. **The content-reference / asset-resolution path is NOT the next objective**: that plan was built on the withdrawn section 8, which derived its 130 targets from the 195 that never reached the parser, so that surface has never actually been measured and must not be planned from this entry. **Still open and not pre-authorised:** whether to mass-convert the 290 available packages (~15,000 files plus preservation-manifest regeneration, its own line with its own measured diff), and whether the three documented scope-decision classes (DefineShape4, PlaceObject3, and the bitmap-fill policy) are ever revisited. **Start here:** read `docs/legacy-m12-signed-rect.md` before proposing the fix line, and read its sections 2 and 6 before trusting any figure from the predecessor - five instrument faults and five withdrawn claims are recorded there, and one of the faults produced a favourable aggregate that would have supported exactly the recommendation it invalidates.
- **Roadmap cursor, before this entry, retained in full:** **M12 - Asset Parity, deliver lines 1 and 2 delivered, verified, synced and archived; the FX / animation re-scope and the eight refusal classes are both now investigated and both are DECISIONS rather than lines; the desync family's origin is PARTIALLY LOCATED and deliberately left at a recorded blocker.** M12's own exit criterion was already met before any of the three investigations. **The cursor does not advance**, because the next step is not a line: `docs/legacy-m12-desync-origin.md` establishes that the one located defect converts 0 of 272, so the eligible next objective is **an investigation of the content-reference and asset-resolution path** that receives the targets which now parse - which needs new evidence, not another grammar enumeration, the grammar having now been searched exhaustively. **Still open and not pre-authorised:** whether to mass-convert the 290 available packages (~15,000 files plus preservation-manifest regeneration, its own line with its own measured diff), and whether the three documented scope-decision classes (DefineShape4, PlaceObject3, and the bitmap-fill policy) are ever revisited.
- **Roadmap cursor, before this entry, retained in full:** **M12 - Asset Parity, deliver lines 1 and 2 delivered, verified, synced and archived, the FX / animation re-scope decided, and the refusal classes now investigated; nothing is active and no next line is pre-authorised.** **Of the three open decisions, one is now closed and it changes the line boundary rather than opening a line.** The refusal-class decision does not authorise work; it rules one route out and regroups the problem. **The next eligible objective is therefore not a deliver line at all - it is locating the remaining desync** in the 272-target family, because a proposal cannot be written from a class name and §3.2 is the standing proof that a plausible fix here can convert nothing. **Do not propose a `shape byte overrun` line**: that recommendation is withdrawn. **Do not propose an FX line**: closed by measurement, and its absence is structural rather than a failed search. **Two of the three open decisions remain open and neither is pre-authorised**: (1) whether to **mass-convert the 290 available packages** - roughly **15,000** files plus a preservation-manifest regeneration, therefore its own line with its own measured diff; and (2) whether the three **scope-decision** classes (DefineShape4, PlaceObject3, and the per-target bitmap-fill ambiguity) are ever revisited, which this investigation argues against but does not authorise closing. **The three classes that are closed by measurement must not be re-litigated without new evidence**: DefineShape4 and PlaceObject3 are refused by named tables on purpose, and `unresolvable bitmap fill` has no general rule to implement. **M12's exit criterion was already MET before either line** (the client loads no runtime SWF), so the milestone's remaining value is entirely in its deliver items, and its deliverables and exit criterion are **different kinds of statement** - do not plan from the exit criterion. **Start here:** read `docs/legacy-m12-refusal-classes.md` §2, §3 and §9 before proposing anything, and read its §7 before trusting any of its figures without re-measuring: nine of its own instrument and draft defects are recorded there, and one of them (C4's 1,154 "failing shapes") had already produced a favourable aggregate that would have supported the recommendation this document withdraws.

- **Roadmap cursor, before this entry, retained in full:** **M12 - Asset Parity, deliver lines 1 and 2 delivered, verified, synced and archived, and the FX / animation re-scope decided; nothing is active and no next line is pre-authorised.** Line 1 (`asset-package-parameterisation`) delivered the enabling tooling and the census that bounded what is convertible. Line 2 (`image-reference-resolution`) delivered the **mechanism** half of the 50 `ambiguous` + 32 `missing_source` population. The re-scope decision (`docs/legacy-m12-fx-animation-rescope.md`, PR #353) settled the third open decision. **The two halves of the image population are in different states and must not be read as one item**: the 50 are **closed**, and the 32 are **explicitly not closed** - absent under every extension repository-wide, so no resolver rule reaches them and **authoring or retiring them is a content decision this repository does not make**. M12's **exit criterion was already MET before either line** (the client loads no runtime SWF), so the milestone's remaining value is entirely in its deliver items, and its own deliverables and exit criterion are **different kinds of statement** - do not plan from the exit criterion. **Of the three decisions that were open, one is now closed and it reorders the milestone.** **"FX replaced" is CLOSED BY MEASUREMENT as unsatisfiable from this oracle**, and structurally so rather than for want of a search: 205 of 205 FX stems are dotted against 0 of 862 sprite stems, so no committed content can name one; 205 of 205 files carry ActionScript the tooling cannot read; 86 of 205 are already extracted with 639 bitmaps on disk and all 119 unextracted carrying zero bitmaps, so the work that could be done is already done. **Do not propose an FX line.** **"animation gaps resolved" is feasible and is gated on the refusal classes, not on FX**: 68 of 422 labelled sprites convert today, 313 are refused and 41 are content-side gaps, and lifting `shape byte overrun` alone (104 targets, 89 labelled) would take that 68 to 157. **Two decisions remain open and neither is pre-authorised**: whether the **8 refusal class-domains** get investigation lines of their own or are recorded as permanently refused (**527 targets, 290 packages**) - and the animation measurement is now a concrete argument that at least `shape byte overrun` deserves investigation rather than a permanent-refusal record; and whether to **mass-convert the 290 available packages**, which is ~**15,000** files plus a preservation-manifest regeneration and is therefore its own line with its own measured diff. **Start here:** read `docs/legacy-m12-asset-parity.md`, `docs/legacy-image-reference-resolution.md`, and `docs/legacy-m12-fx-animation-rescope.md` before proposing anything; the next line's investigation is committed on its own branch from updated `main`, which is not relaxed by three closures, and the re-scope decision explicitly recommends rather than authorises a refusal-class line.

- **Roadmap cursor, before this entry, retained in full:** **M12 - Asset Parity, deliver lines 1 and 2 delivered, verified, synced and archived; nothing is active and no next line is pre-authorised.** Line 1 (`asset-package-parameterisation`) delivered the enabling tooling and the census that bounded what is convertible. Line 2 (`image-reference-resolution`) delivered the **mechanism** half of the 50 `ambiguous` + 32 `missing_source` population. **The two halves of that population are now in different states and must not be read as one item**: the 50 are **closed**, and the 32 are **explicitly not closed** - they are absent under every extension repository-wide, so no resolver rule reaches them and **authoring or retiring them is a content decision this repository does not make**. M12's **exit criterion was already MET before either line** (the client loads no runtime SWF), so the milestone's remaining value is entirely in its deliver items, and its own deliverables and exit criterion are **different kinds of statement** - do not plan from the exit criterion. **Three decisions remain open and none is pre-authorised**: whether the **FX / animation** items are re-scoped or dropped (the 205 FX SWFs are named by no committed content); whether the **8 refusal class-domains** the census found get investigation lines of their own, or are recorded as permanently refused (**527 targets, 290 packages**); and whether to **mass-convert the 290 available packages**, which is ~**15,000** files plus a preservation-manifest regeneration and is therefore its own line with its own measured diff. **Start here:** read `docs/legacy-m12-asset-parity.md` and `docs/legacy-image-reference-resolution.md` before proposing anything; the next line's investigation is committed on its own branch from updated `main`, which is not relaxed by two closures.

- **Roadmap cursor, before this entry, retained in full:** **M12 - Asset Parity, deliver line 1 applied and verified; Sync and Archive remain, and M12's three remaining deliver items (all runtime-required SWFs converted, UI assets converted, FX replaced, animation gaps resolved) are untouched and unstarted.** This line delivers the *enabling* tooling and the census, and deliberately converts no additional package, so the exit criterion "Godot no longer depends on runtime SWFs" is **not** met and must not be read as met.

- **Roadmap cursor, before this entry, retained in full:** **M11 - Social and Special Systems, six deliver lines delivered, verified and synced, and its exit criterion assessable.** The deliver list was `friends`, `visits`, `scores`, `social rewards`, `legacy event systems`, `special mechanics`. **`friends`, `social rewards`, `legacy event systems` and `special mechanics` were each delivered** across lines 3-6; **`visits` and `scores` were checked and REJECTED for any server-side surface on their own merits** - the `world_id` map key and the `worldChange` `privateState` key are carried in 33 of 33 documents with **zero** legacy occurrences, there is **zero** score arithmetic, and both candidate readings were measured and rejected. **No deliver item remains unexamined or partial**, which is what makes M11's exit criterion ("All relevant legacy game systems are classified and implemented or explicitly excluded") assessable rather than merely closer. The assessment itself is recorded in the Change status entry below and is **not** the same statement as M10's, which was closed *unsatisfiable from this oracle*; M11 is *bounded-but-open*, with its undelivered surfaces recorded rather than invented. **Carry-forwards that survive the milestone**, all recorded rather than fixed: `crossPromotionsFinished` and `unlockedSkins` are inert and `specials.json` holds exactly one entry (`legacy_id` `"925"`); the atom-fusion **powerup purchase** is a `# TODO` with a committed six-row ladder and zero consumers; `first_time_marketplace` is a 2-statement unowned branch; `rt_open_graph_unit`; and the **24-declaration** `SPELL_*`/`TECH_*` gap beside `godot-mission-vocabulary`. **M10 and every earlier M11 line follow in full and are unchanged.**

- **Roadmap cursor, before this entry, retained in full:** **M11 - Social and Special Systems**, **four deliver lines delivered and archived** (`godot-social-state`, `godot-darts`, `godot-friends`, `godot-construction-assist`), with `social rewards` archived on 2026-10-07 as `2026-10-07-social-rewards-assist-projection`. **M11's exit criterion ("All relevant legacy game systems are classified and implemented or explicitly excluded") is closer but still NOT MET**, and the reason has not moved in this line: `visits` and `scores` were **checked and rejected** for any server-side surface on their own merits, and the two items keeping the criterion open are **`legacy event systems`** and **`special mechanics`**, both still **partial**. This line therefore **closes the last unexamined deliver item**, which converts M11 from *unfinished* to *bounded-but-open*: every one of its six items is now either delivered or closed by measurement, and the remaining work is the two partial items rather than an unexamined surface. **`social rewards` is no longer an exclusion candidate.** It was classified *content committed, behaviour absent* on the strength of three tables with zero consumers; that classification is **reproduced for the tables and falsified for the item**, and what replaces it is narrower than the item's name suggests — a **read-only projection** of `attr["si"]` plus a **dispatch census**, with no reward, no charge, no decoded element, no friend count, and no gifting interface. The next eligible objective is **`legacy event systems`**, and the one after it **`special mechanics`**; both need their own committed investigation before any proposal, and neither may be proposed from this cursor's evidence. **M10, past its final objective, follows in full and is unchanged.**

- **Roadmap cursor, before this entry, retained in full:** **M11 - Social and Special Systems**, **three deliver lines delivered and archived** (`godot-social-state`, `godot-darts`, `godot-friends`), and the **fourth and last deliver item, `social rewards`, PROPOSED** as change `social-rewards-assist-projection`, which delivers capability **`godot-construction-assist`**. **The capability is deliberately not named `godot-social-rewards`**, on the same recorded reason that withheld `godot-friends`: the deliver item's name is the *inverse* of what the preserved server holds. The line's shape is fixed by the committed measurement rather than chosen: `attr["si"]` is already carried on `/v0/bootstrap` and its only transaction grants nothing and charges nothing, so **no route is proposed** and `apps/compat-api/**` is untouched - the compat suite's **3077** baseline must therefore be re-run and reported as a **verified** figure for this line, not skipped. **Exactly three requirements in the repository are modified, all on `godot-social-state`** (req 1's standing refusal becomes an ownership hand-off without weakening the prohibition it carries; req 7 names the `finish_si` call at `command.py:644` it omitted; req 11's *"no social command exists"* reason is corrected, since three exist), because those are the only three whose text this change falsifies or leaves materially incomplete. **Two candidate amendments were examined and rejected as not warranted**: `godot-stored-item-placement`'s attribute-bag scenario is scoped to placement and nothing contradicts it, and `social-tables-normalization` turned out to be **literally correct**. `visits` and `scores` remain **checked and rejected** for any server-side surface; `legacy event systems` and `special mechanics` remain **partial**. **M11's exit criterion ("All relevant legacy game systems are classified and implemented or explicitly excluded") is closer but NOT MET**, because those two items are still partial. **M10, past its final objective, follows in full and is unchanged.**
- **Roadmap cursor, before this entry, retained in full:** **M11 - Social and Special Systems**, **three deliver lines delivered and archived** (`godot-social-state`, `godot-darts`, `godot-friends`), and the **fourth and last unexamined item, `social rewards`, now investigated** on its contract `docs/legacy-m11-social-rewards.md` and **not yet proposed**. **The cursor is an elimination with one item left in it.** `visits` and `scores` were **checked and rejected** for any server-side surface; `legacy event systems` and `special mechanics` are **partial**; and `social rewards`, which every earlier entry called *content committed, behaviour absent*, is now measured to contain a **real, unowned social-assistance state machine** in `attr["si"]` - "Socially In Construction" per `engine.py:19` - persisted on **53 of 3,372** placed rows, written by three functions in `engine.py`, dispatched from **three** branches including one that is not named for it (`set_resource_allies`, `command.py:644`), with the friend arm's single append value fixed to the **paid** sentinel `0` by the author's own comment at `engine.py:142` and corroborated by a corpus holding **7** elements and **one** distinct element value. **That is M11's fourth line by elimination, and it is a read-only one**: the state is already carried on `/v0/bootstrap` and the transaction grants nothing, so no route is recommended. **`social rewards` is therefore no longer a candidate to close by measurement** the way `visits` and `scores` were - it has an undelivered surface. **M11's exit criterion ("All relevant legacy game systems are classified and implemented or explicitly excluded") is closer but NOT MET**, because `legacy event systems` and `special mechanics` remain partial and only one line of six deliver items has ever been closed by measurement. **M10, past its final objective, follows in full and is unchanged.**

- **Roadmap cursor, before this entry, retained in full:** **M11 - Social and Special Systems**, **two deliver lines delivered and archived, and line 3 (`godot-friends`) proposed** on its investigation contract `docs/legacy-m11-friends.md`. **Two corrections to this cursor are recorded here rather than edited into the earlier entries they supersede.** **First, `friends` is NOT "state-only with no consumer", and the committed classification is wrong**: `docs/legacy-m11-social.md` §7 called it **zero legacy occurrences**, but re-counted over all **eleven** legacy modules under **six** rules the token has **5** whole-file occurrences and **4** code-only ones, all in `sessions.py` (`:169`, `:179`, `:188`, `:189`), with the fifth a comment at `engine.py:142`. A real server-side roster surface exists and is undelivered. **Second, the `magics`/`mana` follow-up this cursor previously named as the next unmeasured item is ALREADY DELIVERED** - it shipped inside M10 line 3 (`godot-damage`) as the magic-counter ledger (commit `ccab116`, spec `godot-damage`), so nominating it as unmeasured was stale. `visits` and `scores` remain **checked and rejected** for any server-side surface: `world_id` and `worldChange` are carried in **33 of 33** documents with **zero** legacy occurrences, there is **zero** score arithmetic, and the two candidate readings - `lost` at `command.py:792`/`:868` and `won` at `auctions.py:164` - were measured and **rejected** as scores. `social rewards` remains **content committed, behaviour absent** (three tables, **41** entries, zero consumers, `neighborAssists` and `receivedAssists` uniformly `{}` - though the placement correction stands: `receivedAssists` and `resourcesTraded` are `maps[0]` keys, not `privateState`), while `legacy event systems` and `special mechanics` are **partial**, which line 2 advanced. **M10, past its final objective, follows in full and is unchanged.**

  **Roadmap cursor, before these two corrections, retained in full:** **M11 - Social and Special Systems**, **two deliver lines delivered and archived, four deliver items still to advance.** After two lines the cursor is an elimination rather than a preference. `visits` and `scores` were **checked and rejected** for any server-side surface: `world_id` and `worldChange` are carried in **33 of 33** documents with **zero** legacy occurrences, there is **zero** score arithmetic, and the two candidate readings - `lost` at `command.py:792`/`:868` and `won` at `auctions.py:164` - were measured and **rejected** as scores. `friends` is **state-only with no consumer** (persisted in **33/33** documents, **zero** legacy occurrences, uniformly empty) and `social rewards` is **content committed, behaviour absent** (three tables, **41** entries, zero consumers, `neighborAssists` and `receivedAssists` uniformly `{}`), while `legacy event systems` and `special mechanics` are **partial**, which line 2 advanced. **M10, past its final objective, follows in full and is unchanged.**

- **Roadmap cursor, before this entry, retained in full:** **M10 — Missions and Combat**, **past its final objective.** All seven deliver items are accounted for: **three delivered and archived** (`combat actions`, `damage`, `rewards`) and **four closed by measurement** rather than deferred (`mission loading` has no command; `mission state` was already delivered by `godot-quests`; `death` and `mission completion` have no undelivered surface). **`mission completion` was CLOSED BY MEASUREMENT** on the committed investigation `docs/legacy-m10-mission-completion.md` (PR #300, merged `d4bad71`) — it has **no undelivered surface**, on four independently sufficient grounds. **First, no vocabulary consumer**: the 64 `MISSION_*` declarations have **zero** occurrences outside `constants.py`, re-measured across all **eleven** top-level legacy modules rather than the **seven** earlier probes walked, and owned by `godot-mission-vocabulary`. **Second, no reader of the mission pointer**: `idCurrentMission` has **2** writers (`command.py:111`, `:438`) and **0** readers, `timestampLastChapter` **2** writers (`:439`, and `:911` as a client-supplied subtraction inside `fast_forward`) and **0** readers, both owned by `godot-quests`. **Third, no mechanism**: `complete_goal` (`command.py:76-79`) — the branch the deliver item is *named* for — mutates nothing and narrates a title in a `print`, `end_attack` and `kill` touch no mission state at all, and only **5 of 63** branches touch any. **Fourth, no content**: no mission or chapter table among the **20** committed top-level keys, and the **91** `goals` entries never mention a chapter. **The corpus finding runs the other way and is recorded as such**: **39 of 39** documents carry both fields, and the **5** non-zero pointers are **exactly** the 5 string-valued ones — the fingerprint of `collect_mission`'s `str(next_mission)` — so the pointer is real, populated and progressed, and is still read by nothing. **Five measurement defects were found and recorded rather than quietly fixed**, and the class recurred: a column-zero pattern found **0** declarations and so made the zero-consumer re-measurement vacuous (its subject list was empty); the same failure mode then recurred in the verification script as a **rebound variable** that made a check run against the wrong subjects and return a clean, plausible `False`. A second defect inverted the corpus finding in the direction that makes a closure *easier* — the mission fields live on `maps[0]`, not `privateState`, and a `privateState` probe reported a confident absence where **39 of 39** documents carry them. A third made the `elif` chain's nested AST spans run to the end of the function, reporting **61 of 63** branches against a true **5 of 63**. A fourth **under-counted** the ledger scan, missing `darts_shoot_balloon` because it appends through a **local alias**, and an under-count is the tidier closure. The fifth is `docs/legacy-m10-death.md` §6.2 recurring **inside this very document**: a literal ownership grep reported the mission globals **unowned** because `godot-mission-vocabulary` names them by **role** — *"the active mission count, the permission pack unit list, and the permission cost table"* — and never by key name, so **grepping prose specs for a source identifier is wrong for the wrong reason, twice now.** **All 78 mechanically checkable claims verify** with **0** failures and **3** judgement calls recorded as *not* mechanically checkable rather than counted as passing, and `openspec validate --all --strict` is unchanged at **64 passed / 0 failed** because no code, spec, or artifact changed. **`rewards` was then investigated** on its own branch and is **a REAL surface, not a closure** — committed as `docs/legacy-m10-rewards.md`. `weekly_reward` (`command.py:345-363`) and `win_daily_bonus` (`command.py:444-463`) both mutate state and both grant a **client-sent** item id, and **nothing owned any of it**: no `godot-*` capability names `weeklyRewardIndex`, `bonusNextId`, `timeStampMondayBonus`, `timestampLastBonus`, either branch, or either schedule (`level_ranking_reward` is owned **as normalized content** and undelivered **as gameplay**, which are different states and are not collapsed here). **Two cursors are write-only**: `weeklyRewardIndex` has one site and `bonusNextId` has one, and both are the write itself, so each records *that* a reward was taken and never *what it should be* — the shape `godot-research` delivered for the research counters. **The one reward schedule that is read is read for its LENGTH only.** `get_weekly_reward_length` (`get_game_config.py:195-204`) returns an `int`, and the committed `MONDAY_BONUS_REWARDS` has **three rungs** against a derived rotation length of **five** — the length is `max(len(value))` over rungs whose `value` is a **list**, and only the unit rung qualifies, so counting the rungs gives **3** and the answer is **5**. **A grant is therefore representable but NOT derivable**: all five committed unit ids (`1055`, `1033`, `1046`, `1063`, `1198`) resolve against committed items, yet no code path returns a rung, an item or an amount. **Ten of the eleven committed reward schedules have ZERO consumers** across all **eleven** legacy modules, and the schedule's own type letters `g`, `u` and `c` are **undecoded** — six independent searches for a decoder all return **0**, so reading `g` as gold and `c` as cash would be an invention. **Seven `privateState` fields are save-only** — `attacksSent`, `attacksPack`, `attacksReceived`, `bestUnit`, `betWin`, `spyings`, `strategy` — present in **39 of 39** committed documents and in **zero** source lines. **Neither arm charges anything.** And unlike most M10 lines this one is **not blocked by a fresh-player corpus**: **seven** documents carry `weeklyRewardIndex > 0` (`Nerri.json` at 2, `Neutral.json` at 3, five at 1) and **twenty-six** carry a non-zero `timestampLastBonus`. **A delivered line would be neither a pure refusal nor a routine feature** — it would deliver the cursors and the derived length of **5**, refuse to derive the grant, refuse to decode `g`/`c`, and record the client-sent grant as a **divergence** in the `damage` line's manner. **Three measurement defects were recorded rather than quietly fixed**, and the first is the *third* instance of one class: a reader/writer census inverted by a quote-on-one-side-only pattern, which reported `timeStampMondayBonus`, `bonusNextId`, `questsRank` and `collections` as **read** when they are written. The second stopped the probe with a `KeyError` rather than reporting wrong — `legacy_id` is the *normalized* package's field name and the raw config uses **`id`** — which is recorded because the same mistake inside a `try/except` would have shipped an empty resolution table reading as "none of these ids resolve". The third records a false attraction: the daily wrap bound `> 5` is a **hardcoded literal**, not derived from `DAILY_GOLD_REWARDS` merely because that schedule also has five entries. **All 113 mechanically checkable claims verify** with **0** failures and **5** judgement calls recorded as *not* mechanically checkable rather than counted as passing, and `openspec validate --all --strict` is unchanged at **64 passed / 0 failed** because no code, spec, or artifact changed. **`death` was CLOSED BY MEASUREMENT** on the committed investigation `docs/legacy-m10-death.md` — it has **no undelivered surface**. The words the deliver item is named for (`dead`, `death`, `die`, `resurrect`, `revive`, `syringe`) have **zero** token-exact occurrences across the seven legacy root modules; the mechanism is a ledger called `deadHeroes` reachable through **four** doors, and **all four are owned** by delivered capabilities — `sell`+`KILL` and `kill` by `godot-unit-behaviors`, the `map_lose_item` caller on the quest path by `godot-quests`, and the same helper on the combat path by `godot-combat-actions`. `godot-unit-behaviors` additionally owns the door accounting and names both reaching capabilities so the owners cannot describe the same reach differently. **Two measurement defects were found and recorded rather than quietly fixed**, and the second is the important one: the first ownership probe demanded the literal string `end_attack` inside `godot-combat-actions`' spec, reported the door as **UNOWNED**, and would have blocked the closure — because that capability describes the behaviour by **role** ("a combat resolution") and never uses the branch's source name. **A closure-by-measurement claim is only as strong as its ownership test, and grepping prose specs for a source identifier is exactly the test that is wrong for the wrong reason.** The first defect was an identifier-class error matching `command ==` when the dispatcher compares `cmd ==`, which voided the enclosing-branch column of the entire door inventory — the **third** such census failure in this project after the `push_queue_unit2` regex, twice. **All 37 mechanically checkable claims in the investigation verify**, and `openspec validate --all --strict` is unchanged at **64 passed / 0 failed** because no code, spec, or artifact changed. Line 3 (`damage`) closed at Apply PR #296, Sync PR #297, and Archive PR #298; its capability `godot-damage` is in the main specs at **65 items** under `openspec validate --all --strict`. **Nothing in M10 beyond line 3 is pre-authorised**, and the cursor reached `death` only because line 3 is archived. Its deliver list is `mission loading`, `mission state`, `combat actions`, `damage`, `death`, `mission completion`, `rewards`, and its exit criterion is *"Primary combat loop works."* **Nothing in M10 beyond line 2 is pre-authorised.** The cursor reached `damage` because the committed investigation **`docs/legacy-m10-damage.md`** (PR #294, merged `bf56c62`) established it rather than because the milestone moved on. Two findings decide this line. **First, the preserved server resolves no damage**: all seven committed damage-shaping fields (`attack`, `defense`, `life`, `attack_interval`, `attack_range`, `best_against`, `best_against_mult`) have **zero** legacy consumers under six counting rules, and the apparently-conflicting counts are substring artifacts — `damage` shows 2 code-only occurrences and **0** tokens because both sit inside `COST_DAMAGE_SELF` and `COST_DAMAGE_ENEMY`, and `attack` shows 42 whole-file occurrences and **0** tokens because every one sits inside `end_attack`, `attacker`, `flash_reload_attack`, or `ANIMATION_ATTACKING`. **Second, and decisively, there is nowhere to STORE damage**: across all **10** canonical save documents and **3,372** placed rows **every row is exactly 8 slots** with a fixed type per slot, the complete `attr` bag union is `cp=28, nu=1, si=53, ts=1, ui=1, xp=171`, and **zero** damage-shaped keys exist in any `privateState`. That makes the refusal a statement about the shape of the data, and it is stronger than any recorded previously. **But the same investigation found the line is not a pure refusal**, because it surfaced a real, state-mutating, **capturable** combat-effect surface no delivered line owns: the **`privateState.magics` ledger**, written by `buy_magic` and `use_magic` at `command.py:652-674` and **read by nothing**. Twelve executed transactions against `villages/Neutral.json` — the only committed corpus with a non-empty ledger — confirmed the two adjacent branches are **not** interchangeable: `buy_magic` uses `+=` and is **unbounded** (`2 → 3 → 7 → 15 → 31 → 63 → 113`, crossing 50 and still climbing), while `use_magic` uses `=` and **destroys charges** (**`113 → 50`**, 63 owned spells deleted by a command whose recorded message claims the opposite). **No price is charged** — all **8** stored resource slots were compared before and after twelve requests and **none moved**, with `mana` steady at 15 through a `use_magic` — and **no committed magics field can be consumed at all**, because the ledger has zero readers. **Line 3 is now DELIVERED and ARCHIVED.** Apply PR #296, Sync PR #297, Archive PR #298; capability `godot-damage`, eight requirements. **Seven divergences are recorded and none is reproduced as parity**, and the above-cap case is **REFUSED rather than clamped** -- a **modern-only** authority, because `min(cap, before + 1)` applied to the recorded `113` returns the cap, which is the exact charge-destroying decrease being refused wearing the service's own clothes. The recorded `50` cap ships as a **literal**, with the rejected content derivation (`AirStrike.cash = 50`, `Shortcircuit.level = 50`) retained in design D6 and in both delivered modules rather than silently chosen. **A specification requirement was CORRECTED during Apply rather than silently narrowed**: the post-execution proof originally demanded the ledger equal the *derived* value, which is impossible by construction because the service must refuse both preserved asymmetries while the preserved dispatcher is left unchanged and still writes its own numbers, so it fails on five of seven successful steps. It now pins what actually executed and requires the derived value to be **reported beside** the recorded one with an explicit `matches_derived` flag -- **verifying the preserved outcome is not reproducing it.** **Three instances of ONE defect class were found and CLOSED rather than re-run** -- whole-document equality over a wall-clock-stamped response -- in `test_collection_endpoint.py` (`/v0/session` `server_time`, then `/v0/bootstrap` `server_time` **plus nested `player_info.last_logged_in`**) and then in `test_research_endpoint.py`, the last as a **real** battery failure (`server_time` 1791185085 against 1791185086). The class was then **measured** rather than patched a fourth time: **15** whole-document equalities exist, **12** are determinism checks, **2** compare save *file hashes* and are correct precisely because file bytes never move, and **zero remain at risk**. Battery baseline after this line: **43 hermetic suites, 22 live phases**, compat `Ran 2662 tests ... OK`, `test_project_scope.gd` 1900, `test_damage_magic.gd` 618/621, manifest **3,258** entries, `openspec validate --all --strict` **65 passed / 0 failed**. **Four corrections to the committed investigation and one false claim of my own** are recorded in `docs/legacy-m10-damage.md` §7.1-7.2 rather than quiet edits -- including that I claimed the legacy `use` arm and the derived transition "agree only at zero" when they are literally the same formula `min(cap, x + 1)` and agree at **every** counter 0..50 -- and the branch-count correction **recurred** in the implementation for the same reason as the first time, which is the finding worth keeping: **recording a correction is not the same as preventing the class.** **The next objective was `death`, was closed by measurement, and is now `rewards`**, and per AGENTS.md this cursor is updated but the next change is **not** begun until the current orchestration request allows it.

  **Per-line findings for M9 lines 1-3, carried forward verbatim** (the detail the previous
  cursor sentence accumulated; none of it is superseded by the assessment):

  Lines 1–3 established, each from committed source and executed probes rather than by pattern: **line 1 `research`**
  found a closed four-branch set over a three-counter, two-track vector whose counters are **WRITE-ONLY**
  (`researchStepNumber` **3** sites, `researchItemNumber` **2**, `timeStampDoResearch` **5** — the four branch writes
  plus **one read at `command.py:923` that is itself a write**, inside `fast_forward`, subtracting a
  **client-supplied** number of seconds clamped at zero), so **no research price is charged** and no readiness,
  completion, or unlock rule exists; **line 2 `quests`** found that **only TWO committed quest fields have any legacy
  consumer** (`id` **8**, `title` **2**, the latter being two `print` statements), that **`complete_goal` mutates
  nothing at all**, and that the `end_quest` destruction count is a **client-dictated** number that is therefore
  **refused** and recorded as a **measured divergence** — the legacy server destroyed a placed row, 40 → 39, while the
  modern endpoint leaves all 40 byte-identical; **line 3 `tutorial/progression`** found the **entire tutorial system**
  to be `command.py:60-66` — one branch, one local, one write — where `completed_tutorial` occurs **once** across the
  eleven legacy root modules on **one** line, that line being the **write**, with **zero readers**, making it the
  **tenth** committed field in this project with no legacy consumer; `tutorial_step` occurs **4** times over **3**
  lines and is a **local that is never persisted**, so there is **no stored step and no un-complete path**; the gate
  `tutorial_step >= 25 or tutorial_step == 15` has **no lower bound, no upper bound, and no type check**, and its
  **hole is exactly `16..24`**, nine values wide; and `config/main.json` plus every normalized package hold **zero**
  occurrences of `tutorial`, so there is no step list, no count, no gate definition, and no tutorial text to derive.
  **Line 3 is the first M9 line that is not a refusal line**, and the instruction to measure its own fields rather
  than assume the pattern repeated is what made that visible. **Line 1 also carried the cross-milestone correction**
  that `godot-unit-behaviors` claimed **three** doors into the dead-hero ledger where measurement makes it **four**:
  `map_lose_item` (`engine.py:215-228`) calls `push_dead_unit` at **223**, and its only **two** callers are
  `command.py:796` inside **`end_quest`** and `command.py:872` inside **`end_attack`**, so the fourth door is reached
  from the quest path and the attack path rather than the death path alone. **quest path and the attack path**, not
  the death path alone. **Line 2, `quests`, was the largest surface in M9** and it delivered the six branches
  `set_goals`, `complete_goal`, `set_quest_var`, `end_quest`, `admin_set_quest_rank`, and `collect_mission` against
  committed content normalized at **91** entries of a uniform ten-field shape and a corpus carrying real quest state
  (`goals` at **151** entries, **all `None`**; `questsRank` `{}`; `unlockedQuestIndex` `0`; `questTimes` `{}`;
  `currentQuestVars` **`None`**; `idCurrentMission` `0`). **Only TWO committed quest fields are read by anything**,
  measured as quoted occurrences so comments cannot contribute: `id` has **8** and `title` has **2**, the latter being
  the two `print` statements; every other committed field has **zero** consumers, and **`reward` has zero while being
  committed on all 91 entries and uniformly the value `10`**, so it carries no information even if it were read. There
  is therefore **no quest reward, cost, or price to derive**, and none is derived. **`complete_goal` mutates nothing
  at all** and the executed fixture proves it: the captured transaction changed **no** `privateState` key and **no**
  `maps[0]` key, so a goal completes by being narrated in a `print` statement and no completion state exists. **The
  `end_quest` destruction count is REFUSED, and the divergence is measured rather than asserted:** probe 4 sent
  `end_quest` with `units = [[26, 0, 1, 0]]` so the legacy branch's client-computed `lost = max(0, unit[2] - unit[3])`
  was **1**; the legacy server **destroyed a placed row, 40 -> 39**, while the modern endpoint derives `units: []`,
  destroys nothing, and leaves **all 40 rows byte-identical**. The manifest records that as a **divergence**, not as
  parity, and separately records that the *captured* transaction's rows were byte-identical because that step carried
  no lossy tuple. Reproducing a client-dictated destruction count would be exactly the anti-pattern `AGENTS.md` names
  as Bad. Three legacy type and shape facts are reproduced rather than normalized, each confirmed by the captured
  oracle: `collect_mission` wrote `idCurrentMission` as the **string** `'5'` against a corpus recording the
  **integer** `0`; `set_quest_var` self-healed `currentQuestVars` from the corpus's `None` to a dict; and `end_quest`
  wrote `questTimes` `{}` to `{'7': <instant>}`. **Three more probes establish the refusals with executed evidence:**
  `set_goals([500, "[0,0]"])` grew the list from **151 to 501** entries, **350** appended from one client-sent id with
  **no upper bound**, so the endpoint **reproduces** the unbounded growth rather than closing it;
  `set_quest_var(["idSimpleChapter", 5])` wrote **nothing** (the branch returns at `command.py:95` before any write)
  while an **invented key was accepted**, so exactly one key is refused and it is the one the legacy branch itself
  ignores; and `collect_mission([150])` **wrapped** to `1` at bound `99`, stored as a `str`. `unlockedQuestIndex` is
  reported and **never** written, having zero legacy sites, making it the **ninth** zero-consumer committed field in
  this project.
- **Line 1 selection:** the record recommends **research** as the first M9 line, and the reasoning is recorded rather than assumed. It is the only family that is (a) entirely undelivered, (b) a **closed four-branch set** with a single three-counter state vector, so one line can cover it without an open-ended surface, (c) **fully exercisable** by the committed corpus at its initial values, (d) the one with the clearest authority story, because the two counters advance on the client's word and the one price-taking branch **charges nothing** — which makes the refuse-the-cost / prove-unchanged pattern of M7 and M8 directly applicable — and (e) it requires no content package that has not already been normalized. Quests is the largest surface and is the natural **second** line; `quests.json` already holds **91** entries with a uniform ten-field shape, so its content side is ready when its turn comes.
- **Active OpenSpec change:** **none.** `image-reference-resolution` completed its full lifecycle on 2026-10-09 and is **ARCHIVED** as `openspec/changes/archive/2026-10-09-image-reference-resolution/`, archived with `--skip-specs` because Sync had already applied all three deltas. **All seven artifacts are `R100` pure renames**, verified with git's own rename detection rather than assumed. **The ledger was the stale artifact again, for the fourth recorded time, and the gap is named:** it read *line 2 opened as an INVESTIGATION* across the **proposal, Apply and Sync** stages, so a session resuming at Archive would have started from a stage already passed. `openspec validate --all --strict` reports **75 passed / 0 failed** as a composition of **74 main specs + 1 change** during the change, and **74 passed / 0 failed = 74 main specs + 0 changes** after Archive - Archive removes the change and the total falls by exactly one, so the total alone never distinguishes the stages, which is why every entry here states the composition.

- **Active OpenSpec change, before this entry, retained in full:** **none.** M12's second deliver line has opened with an **INVESTIGATION** rather than a proposal: `docs/legacy-image-reference-resolution.md`, committed on branch `docs/legacy-image-reference-resolution`. Exploration is read-only by rule, so **no change directory exists yet and none should until the investigation's recommendation is accepted** - it splits the objective into a **mechanism** (`godot-image-reference-resolution`: resolve image references by their own path, keeping the basename rule as an explicit fallback so the two mis-pathed entries stay visible rather than silently dropped) and a **content decision that is not proposed here** (whether the 32 absent images are authored or their references retired - a product decision this repository cannot make from preserved evidence).

- **Active OpenSpec change, before this entry, retained in full:** **none.** `asset-package-parameterisation` completed its full lifecycle on 2026-10-09 and is **ARCHIVED** as `openspec/changes/archive/2026-10-09-asset-package-parameterisation/`. **Sync created the new capability and modified two existing ones, measured rather than assumed:** `asset-package-census` was created at `openspec/specs/asset-package-census/spec.md` with **3 requirements / 8 scenarios**, its `## Purpose` copied **verbatim** from the delta so no `TBD` placeholder was left to fill by hand, and **zero** delta operation headers survived into any main spec. `first-building-conversion` went to **6 requirements / 14 scenarios** and `first-unit-conversion` to **9 / 22**, each keeping **every** scenario it already held. **One placement decision is worth recording because the mechanical choice was worse:** the unit delta's placeholder-scoping requirement went **after** `Bitmap-fill resolution with recorded placeholders` - the requirement it constrains - rather than appended at the end of the file, where it reads as an unrelated trailing clause. **One thing was lost and is named rather than silently accepted:** both MODIFIED blocks dropped a trailing `and reruns are byte-identical` clause from their measured-assembly scenario. It was not restored, because the delta is authoritative for the requirements it rewrites and the guarantee survives elsewhere - the building spec's `Validation and conversion manifest` and the unit spec's `Validation and manifest-grade determinism` both still assert byte-identical reruns. **Sync therefore created the exact state that makes the next validation noisy:** `openspec validate --all --strict` reports **74 passed / 0 failed = 73 main specs plus 1 change**, and also prints two `[INFO]` lines saying archive *would refuse* the deltas because their ADDED headers now exist in the main specs. That is the **established post-Sync shape here, not a failure** - the archived `2026-10-08-market-trade-counters-projection` retains a delta whose 7 ADDED headers are byte-identical to its 7 main-spec headers and archived successfully - so Archive ran with **`--skip-specs`**, which is what the flag is for.

- **Active OpenSpec change, before this entry, retained in full:** **`asset-package-parameterisation`** - M12's first deliver line, at the **APPLIED / VERIFIED** stage on the Apply branch. Proposal merged; Apply in progress against `tasks.md` 0.x-2.x with every task recorded with its observed result, and 3.x (follow-ups this change records but does not perform) left unchecked by design. The binding investigation is `docs/legacy-m12-asset-parity.md`; the design carries D1-D10, with **D1 vindicated by measurement** and **D7 extended to seven unit refusal classes**.

- **Active OpenSpec change, before this entry, retained in full:** **`asset-package-parameterisation`** - M12's first deliver line, at the **PROPOSED** stage, on branch `docs/asset-package-parameterisation-proposal` branched from updated `main` `f7f9861`, bounded by the committed investigation `docs/legacy-m12-asset-parity.md`. Artifacts: `proposal.md`, `design.md` (**D1-D10**), `tasks.md`, a MODIFIED+ADDED delta for `first-building-conversion`, a MODIFIED+ADDED delta for `first-unit-conversion`, and an ADDED delta creating the new capability **`asset-package-census`**. `openspec validate asset-package-parameterisation --strict` exits **0**; `openspec validate --all --strict` reports **73 passed / 0 failed = 72 main specs plus 1 change**, against the pre-change baseline of **72 = 72 plus 0**. **No code was written in this stage and no suite was run, because none was changed** - the figures below come from running the **committed** converters into a temporary output root, and that is recorded rather than presented as a green battery. **Proposing it required measuring feasibility first, and the measurement changed the change twice.** The investigation had recommended this line on the grounds that both converters are one-shot by construction (`convert_building.py:36`, `convert_unit.py:38-40` hardcode `TARGET_STEM`, `TARGET_LEGACY_ID` and a derived `SOURCE` as module constants, used at **10** sites each, with only `--repo-root`/`--out-root` as CLI arguments) while `package_paths.gd` pins exactly two packages. *The tooling is half the story.* Over **every** candidate - **452** buildings and **365** units, defined as a sprite whose bitmaps are already `extracted` and whose `img_name` resolves to exactly one normalized row - the **unit converter converts 365 of 365 (100%)** and the **building converter 222 of 452 (49.1%)**. The unit converter decodes timeline records and never touches fills; the building converter does not. The **230** building refusals are **four disjoint classes with exactly one class per failing target** (230 class mentions across 230 targets, so these are four separate root causes and not one): **`unresolvable bitmap fill -> 65535` 133**, **`unknown fill style` 61**, **`unsupported shape tag: 83` 20**, **`shape byte/bit overrun` 16**. **587** packages are therefore available immediately. *Two plausible fixes were tried and both refuted.* The dominant 133-target class looked like a missing port of the rule `first-unit-conversion` already specifies (unreferenced `65535` placeholder fills recorded verbatim, referenced ones refused), since the building converter validates **every** fill in **every** style array; porting it into a temporary copy converted **0** additional targets and regressed **0**, and a separate 40-target probe **disagrees** with that (697 unreferenced and 14 referenced `65535` fills, with neither found in **27 of 40**), so the class is recorded **unestablished** and **no fix is proposed for it** - the two contradictory measurements are both committed rather than one of them chosen. And reading `merge_conversion_document` suggested a single-target merge that would clobber the other tool's entry in a batch; measurement refutes it, since either converter alone emits a **two**-package manifest with `counts.packages = 2`, and `build_asset_ids.py:208` already rejects a repeated `legacy_id`, so **D4 introduces no merge threading and no ordering requirement**. **The change also surfaces a fourth instance of the LF-defect class, and it is sharper than the first three because it lands on a provenance field rather than on a comparison**: `fingerprint_inputs` (`convert_building.py:517-525`) digests **raw working-tree bytes** of `buildings.json`, `inspection.json` and `image_extraction.json`, and the latter two are **unpinned** in `.gitattributes` while carrying **170,096** and **1,219,378** CRLF on disk, so the committed `content_version` values are digests of exactly one checkout form - `ddeca799…` and `9d8ad3b3…` reproduce over raw disk bytes and become `c4e76e6d…` and `a0c3861f…` once LF-normalised, and on an LF checkout both committed packages stop reproducing. **D3 fixes the cause rather than the configuration**, normalising inside `fingerprint_inputs` and pinning the paths, on the precedent `apps/compat-api/guard_baseline.py` already set ("text digests are line-ending invariant, so the baseline holds across checkout forms"); the **accepted consequence is recorded in the design rather than discovered during Apply**, namely that both packages' `content_version` and `conversions.json`'s `package_sha256` change **once** and that `tests/fixtures/godot-compatibility-boot/guard-baseline.json` is regenerated in the same change because the guard hashes both package directories and three registry manifests. **The oracle was confirmed before the change was designed**: both committed packages reproduce their recorded `package_sha256` (`7de262e9…366b92a7`, `c40b754c…05d1c7`) and `conversions.json` and `statuses.json` reproduce byte-identically, all **LF-normalised** - and **the working-tree/committed-blob CRLF deltas are recorded separately** (`statuses.json` +1,054, `conversions.json` +35, unit `package.json` +1,790) so that no claim in the change depends on a checkout form. **D8 keeps the 587 available packages out of this change**: committing them is roughly 30,000 files, regenerates the preservation manifest, and delivers **no** client-visible progress while `package_paths.gd` pins two, so it is a separate line with its own measured diff. **D9 records, and does not fix,** the defect that both packages' `legacy_id` field carries the sprite stem rather than the content id the unit converter separately resolves. **D5/D6 make the census a tool beside the converters that writes a deterministic `tools/asset-registry/target_census.json`, requires `--out-root` with no default, records a refused target as data and continues, and exits non-zero only on a genuine tool failure** - containment was verified rather than assumed, since `write_outputs` writes the package directory, bitmap payloads, `conversions.json` and `statuses.json` **only** beneath `out_root` (`convert_building.py:718-733`). **No M12 line beyond this one is pre-authorised**: the **50 `ambiguous`** plus **32 `missing_source`** image references and the **FX / animation re-scope decision** remain unproposed, and the FX item is recorded as a **decision rather than a line** because it has no committed content to work from.

- **Active OpenSpec change, before this entry, retained in full:** **none.** **M12 has opened with an INVESTIGATION**, `docs/legacy-m12-asset-parity.md`, committed on branch `docs/legacy-m12-asset-parity`. **No M12 change exists and none is pre-authorised.** **The headline finding is a mismatch between M12's deliverables and its exit criterion, and it was measured rather than argued.** The exit criterion - *"Godot no longer depends on runtime SWFs"* - is **ALREADY MET**: the client's `.swf` occurrences resolve to **five files, all non-loads** (one rationale string naming committed filenames, one **forbidden-token list** guarding *against* SWF references, one sibling test, two evidence reports), there is no `load()`/`preload()`/resource path to any `.swf`, and the standing no-Flash gates are already green. **The deliverables are close to untouched, and that mismatch is the finding.** Measured from committed artifacts: **1,627** asset references over **1,176** SWFs, and the status vocabulary separates **`converted` (2)** from **`extracted` (872)** - bitmaps exist without geometry or timeline, so **extraction is not conversion**. **"All runtime-required SWFs converted or recreated" is not convertible for the part that matters and is 0.2% complete for the part that is feasible:** the corpus is **1,175 of 1,176** SWFs carrying an ABC block with **0** legacy actions, and `abc_count` is a **counter only** (`inspect_swf.py:267,303,319`) - **this repository has no ABC parser or decompiler**, so converting the game means translating ActionScript 3 with no tooling and no licence to execute it. **Recreation** is the only path, and that is what M6-M11 have been doing line by line. The runtime-required set narrows to a **server-pinned pair**: `templates/play.html:85` loads `SWLoader.swf?swftoload=.../{{GAMEVERSION}}`, `server.py:96` pins `Basesec_1.5.4.swf`, and that build measures **4,542,821 bytes, 1 ABC block, 1,224 DefineSprite, 10,002 PlaceObject2, 419 exports, 420 symbols**. Of `flash/`'s **60** SWFs, **57** versioned builds are superseded, and `Debug_1.5.4.swf` is recorded **separately** because it is a **same-version debug build**, not a superseded one - identical structural fingerprint, **4,585,198** bytes - and nothing in the preserved server selects between the release and the debug build. **The trap this had to avoid is named explicitly:** **0 of 60** `flash/` stems appear in normalized content, and that is *not* evidence the game SWFs are unneeded - they are loaded by the loader and by client-side ActionScript, so **any M12 work classifying assets by content reference alone would have declared the game itself unused**. **Per deliver item:** *UI assets* are **516 of 607 (85%)** already runtime-loadable passthrough, and the residue is **evidence gap, not conversion** - **50 `ambiguous`** (each exactly **2** candidates, all inside three colliding directory pairs) and **32 `missing_source`**. *FX replaced* has **205** fx SWFs and **0 of 205** stems in content: **no committed FX specification exists to replace**, and "FX is referenced from the game SWF's ActionScript" is a **candidate, not a conclusion**. *Animation gaps* sits downstream of conversion and already carries a **measured contradiction** - `max_frame` is **2** where the parsed root has **1** frame and the labelled sprite has **29**. **The one unambiguously feasible item is the tooling:** both converters are **one-shot by construction** - `convert_building.py:36` and `convert_unit.py:38-40` hardcode `TARGET_STEM` as module constants and the only CLI arguments are `--repo-root` and `--out-root` - while `package_paths.gd` pins **exactly two** packages. **Generalising target selection is the recommended first M12 line**, and it has an existing oracle: the two committed M4 packages. **One hypothesis of mine was tested and rejected** and is recorded in the investigation's §2.5: I expected `0 of 26` for `characters_2/` to be a limitation of the `assets/sprites/<stem>.swf` join rule, and direct search over all **23** normalized files disproved it. **M12's exit criterion is MET and is deliberately *not* M10's "unsatisfiable from this oracle" verdict** - that was about a missing rule and a missing hit point, and it does not apply to a criterion that is a statement about the client.

- **Active OpenSpec change, before this entry, retained in full:** **none.** **`2026-10-08-market-trade-counters-projection`** - M11's sixth and final deliver line - completed the full lifecycle on 2026-10-08 and is **ARCHIVED** as `openspec/changes/archive/2026-10-08-market-trade-counters-projection/`. It added **one** new capability, **`godot-market-trade-counters`** (**ADDED**, **7 requirements**, **20 scenarios**), and **modified none** - the single existing mention, `godot-building-resources/spec.md`'s out-of-scope note, is a limitation this capability **satisfies** rather than a requirement it revises. Full lifecycle, each stage on its own remote branch from updated `main`, merged as a **merge commit**: investigation PR #337 `1c8786b`, proposal PR #338 `9094dbe`, Apply PR #339 `ab886f8`, Sync PR #340 `fccb9c5`, a post-Sync LF defect fix PR #341 `4b214dc`, and this archive. **Ordering was deliberate at the defect fix:** PR #341 was merged **before** Archive began, because Archive moves the change's artifacts out of `openspec/changes/` and a defect belonging to that change belongs ahead of it rather than inside its archive commit - folding it in would have put a red-to-green change to the suite inside a stage whose diff should be a pure rename plus ledger text. All five artifacts moved with `git mv` and `git status` records every one as a **pure rename** (`R`, no content modification), so the archived bytes are the merged bytes. `openspec validate --all --strict` reports **72 passed / 0 failed = 72 main specs plus 0 changes**, against Sync's **73 = 72 plus 1**; Archive removes the change and the total falls by exactly one, so **the composition is what distinguishes the stages, never the total**. **With this, M11's six deliver lines are all closed**, four delivered and projected, two closed by measurement, and its exit criterion is assessed MET below.

- **Active OpenSpec change, before this entry, retained in full:** **`2026-10-08-market-trade-counters-projection`** - M11's sixth and final deliver line, at the **SYNCED** stage, on branch `docs/market-trade-counters-spec-sync` branched from the Apply merge `ab886f8`. **What Sync changed, measured rather than assumed:** `godot-market-trade-counters` is **created** as a main spec at `openspec/specs/godot-market-trade-counters/spec.md` - **7 requirements, 20 scenarios** - and its requirement-and-scenario body is **byte-identical** to the delta's, verified by comparing from the first `### Requirement:` heading onward. **No existing spec is amended**: the single existing mention, `godot-building-resources/spec.md`'s out-of-scope note, is a limitation this capability **satisfies** rather than a requirement it revises, and the fact is recorded in the new spec's `## Purpose`. **One edit goes beyond the delta, and it is deliberate:** the measured findings that shape every requirement - the 8-of-10 corpus figure, the branch literal and the coincidence, and the clamped-store/unclamped-print asymmetry - are added to the new `## Purpose`, because a delta's Purpose is a proposal artefact and those figures are what a later reader needs to judge the requirements. **One defect of this stage's own work was found and recorded rather than tidied:** converting the delta by dropping its `## ADDED Requirements` wrapper also dropped the `## Requirements` header the main-spec schema **requires**, so `openspec validate godot-market-trade-counters --strict` failed with *"Spec must have a Requirements section"*. A delta and a main spec are not the same shape, and the difference is exactly the kind of thing a mechanical conversion loses. `openspec validate --all --strict` now reports **73 passed / 0 failed (73 items)** = **72 main specs plus 1 change**; during the change it was **72** = 71 plus 1, so **the total alone never says which stage is done** - record the composition. **Archive remains**, on its own branch from updated `main`.

- **Active OpenSpec change, before this entry, retained in full:** **`social-rewards-assist-projection`** - M11's fourth deliver line, at the **PROPOSED** stage, bounded by the committed investigation contract `docs/legacy-m11-social-rewards.md`. Artifacts: `proposal.md`, `design.md`, `tasks.md`, an ADDED delta for the new capability `godot-construction-assist`, and a MODIFIED delta for `godot-social-state` carrying the three amended requirements. `openspec validate --all --strict` reports **69 passed / 0 failed (69 items)**, against the pre-change baseline of **68**; `openspec validate social-rewards-assist-projection --strict` exits **0**. **No live phase is proposed, so the count stays at 23**, and **no executed-legacy fixture is proposed** - and that absence is a **decision, not a limitation**: `buy_si_help` creates the key when absent, so a capture *was* reachable, unlike the M8 refusal lines where the corpus made it unreachable. The transaction grants nothing, charges nothing, and appends a fixed sentinel, and no fixture would establish anything further.
- **Active OpenSpec change, before this entry, retained in full:** **none.** `friends-roster-projection` - M11's third deliver line - completed the full lifecycle on 2026-10-07 and is **ARCHIVED** as `openspec/changes/archive/2026-10-07-friends-roster-projection/`. The lifecycle was four merged PRs, each on its own fresh branch from updated `main` and each merged as a **merge commit**: investigation #321 `3df888a` (content `82b6df9`), proposal #322 `f7cc36b`, Apply #323 `4b210dc`, Sync #324 `fd258ce`. **The archive moved all six change artifacts by `git mv`, and every one was recorded by git as a pure rename** - `.openspec.yaml`, `design.md`, `proposal.md`, `tasks.md` and both delta specs - so nothing was rewritten on the way into the archive. **The pre-archive sync state was verified rather than assumed**: every one of the eight `godot-friends` requirements and the one modified `godot-social-state` requirement was compared against its main spec, and for each the delta body is present **verbatim** with every delta scenario present and **no** scenario missing, while neither main spec carries a delta operation header and neither carries a `TBD` placeholder. The Archive therefore had nothing left to sync. **M11's exit criterion is still NOT MET and remains unfinished rather than unsatisfiable**: `social rewards` is the only deliver item not yet examined.

- **Active OpenSpec change, before this entry, retained in full:** **`friends-roster-projection`** - M11's third deliver line, at the **SYNCED** stage: the Apply PR **#323** merged as a **merge commit** `4b210dc` on 2026-10-07, and this Sync ran on branch `docs/friends-projection-spec-sync` branched from that updated `main`. **What Sync changed, measured rather than assumed:** `godot-friends` is **created** as a main spec at `openspec/specs/godot-friends/spec.md` - **8 requirements, 14 scenarios**, its `## Purpose` copied **verbatim** from the delta so no `TBD` placeholder is left to fill in by hand, and **zero** delta operation headers survive into the main spec. `godot-social-state` is **modified** in place: requirement 1 is replaced by the delta's complete block, taking the file from **16** scenarios to **17**, while the requirement count stays at **12** and **every requirement title is byte-identical**, which is what makes the merge auditable rather than a rewrite. **One edit goes beyond the delta, and it is deliberate:** the existing capability's `## Purpose` still quoted the now-falsified premise "a capability named `godot-friends` would claim exactly what this one measures to be absent" as a *standing reason* for withholding the name. A delta may not carry a `## Purpose` for an existing capability, so leaving it would have left a measured-false premise asserted as current fact in the main specs. It is therefore amended directly and the falsification is **recorded in place** rather than quietly deleted, with the narrower reason that now stands. `openspec validate --specs --strict` **68 passed / 0 failed**, `openspec validate --all --strict` **69 passed / 0 failed** (was 68; the delta set is unchanged and the count moved by the one new main spec). **Archive remains.**

- **Active OpenSpec change, before this entry, retained in full:** **`friends-roster-projection`** - M11's third deliver line, at the **APPLIED and ORCHESTRATOR-VERIFIED** stage, awaiting Sync. It adds **one** new capability, **`godot-friends`** (**ADDED**, **8 requirements**, **14 scenarios**), and modifies one: `godot-social-state`'s **first** requirement, amended as an **ownership hand-off** because its recorded premise was measured false. **The delivered surface is one read-only module** (`scripts/social/friends_roster.gd`, **29 distinct function names across 34 declarations**) **and one hermetic suite** at **570 checks** - the **47th** registered. **`social_state.gd` is untouched at 405 checks**, which is the required result for an ownership hand-off that moves zero fields, and the compat suite is untouched at **3077**, which is the required result for a line that adds no endpoint. **Two refusals are carried structurally, not in prose**, because prose cannot fail: a **26-name reserved inventory** matched case-insensitively *and by substring* in both directions, and a **whole-inventory pin** over the module's function declarations, with the declaration **count** pinned separately because five names are declared twice and a positional list comparison would fail against the delivered module itself. **Seven injections, all detected and all byte-identically restored, run twice - once during implementation and once against the final delivered state**, because a later edit can silently restore a guard's coverage; the failure counts are **3, 3, 4, 3, 3, 34, 1** and every probe exited 1. The reserved-name guard earned its place: probes 2 and 4 were **suffixed** helpers wearing a reserved name as a **prefix** (`roster_order_by_xp`, `assist_neighbor_reward`), which an exact-name check would have passed. **Three false attractions were recorded rather than followed**: `neighbors` has two meanings (the bootstrap roster and the `expansion_prices` requirement at `boot_data.gd:607`), `"100000"` is a routing prefix rather than an identity test, and `pic_square` is a dictionary key rather than a Facebook API call. **A tautology was found and closed**: the privateState intersection reads each entry's **real** key names through a new `all_key_names()` rather than against the projection's own declared 18, because a widened key table is exactly the edit the guard exists to catch; the recording player's `privateState` has **47** keys and the intersection is empty by measurement. **Two literal tokens had to be reworded rather than relaxed**, because both no-Flash gates are **raw substring** scans: `USERID` and the Flash variable name are in `test_project_scope.gd`'s `FORBIDDEN` table and the Flash variable name is also in `test_town_gate.gd`'s `RUNTIME_NEEDLES`, so the module's prose **describes** the transport and cites `templates/play.html:99` and `server.py:91` instead of quoting it, with the reason recorded at the site. **The first `verify-boot.ps1` run of this line failed on exactly this**, and the failure is recorded rather than hidden.

- **Active OpenSpec change, before this entry, retained in full:** **`friends-roster-projection`** - M11's third deliver line, at the **PROPOSED** stage. It adds **one** new capability, **`godot-friends`** (**ADDED**, **8 requirements**, **14 scenarios**), and **modifies one**: `godot-social-state`'s **first** requirement is amended, because its recorded premise - that a capability named `godot-friends` "would claim exactly what this one measures to be absent" - has been **measured false**, so the amendment is an **ownership hand-off** and not a deletion. **No other requirement of that capability is touched**: requirement 12 ("Visits and scores are reported as having no server-side surface") is **narrower than its title** - its body claims only that `world_id` and `worldChange` are carried-but-never-read and that no score arithmetic exists, both of which remain true - so it is left alone rather than "corrected" on the strength of a title. **Two properties make this the first line in the project to add NO route and NO Compatibility API change**: `/v0/bootstrap` was **measured** in the Propose stage to already carry the roster at `player_info.neighbors` (5 entries, 18 keys, **leaf-identical to the committed executed oracle** on every entry), and `apps/compat-api/**` is therefore untouched, so the compat suite must remain at its **3077** baseline - a *verified* result for this line rather than a skipped check. Adding no route also leaves the pinned route-placement invariant **untouched by construction**, which is strictly safer than finding a third forward-safe slot after `/v0/darts` took the only one.

- **Active OpenSpec change, before this entry, retained in full:** **none.** `2026-10-07-darts` - M11's second deliver line - completed the full lifecycle on 2026-10-07 and is **ARCHIVED** as `openspec/changes/archive/2026-10-07-darts/`. It added **one** new capability, **`godot-darts`** (**ADDED**, **12 requirements**, **18 scenarios**), and **modified one**: `godot-social-state`'s two requirements were replaced **in place by title** at Sync, so the nineteen measured fields are now described as **seventeen social plus two foreign** owned by `godot-darts`, and the premium-account branch is recorded as owned elsewhere rather than as a client-sent social writer with a single write.

- **Active OpenSpec change, before this entry, retained in full:** **none.** `2026-10-06-social-state` — M11's first deliver line — completed the full lifecycle on 2026-10-06 and is **ARCHIVED** as `openspec/changes/archive/2026-10-06-social-state/`. It added **one** new capability, **`godot-social-state`** (**ADDED**, **12 requirements**), and modified **none**. The delta carries its refusals as **structural SHALL text** with **three guards proven by injection**, not as prose: a whole-inventory pin over the module's static functions, a folded-plus-substring reserved-name guard, and an **operator guard** asserting the module contains no arithmetic on, and no ordering comparison between, committed social values. **The operator guard is not redundant**, and that was measured rather than argued: one of the six injections, `normalize(first, second)`, borrowed **no reserved word at all** and was caught **only** by the arithmetic and ordering guards. **Before it:** **none.** `2026-10-05-rewards` — M10's seventh and last deliver item — completed the full lifecycle on 2026-10-06 and is **ARCHIVED** as `openspec/changes/archive/2026-10-05-rewards/`. It added **one** new capability, **`godot-rewards`** (**ADDED**, **9 requirements**), and modified **none**. The delta carries its refusals as **structural SHALL text**: a requirement asserts the delivered code contains no helper capable of selecting a schedule entry from a cursor value, indexing a schedule by a cursor, mapping a cursor position to a type letter or an amount, deriving an eligibility rule from the stamped instant, or decoding a type letter onto a resource slot — and that each absence is **enforced by a guard that fails when such a helper is introduced**, because a prose refusal cannot fail and a guard can.
- **Lifecycle stage:** **M12 - INVESTIGATION**, `asset-package-parameterisation` closed on its own archive PR #347 (`959e7c4`) and M12's next line opened with `docs/legacy-image-reference-resolution.md`. **Investigation-before-proposal is the established order for every line in this milestone**, and this one is deliberately **read-only**: it changes no tool, no client, and no registry entry, and it commits no measurement script - the reproducible appendix lives inside the document because a script shipped unexecuted is a liability, and the first draft of this very appendix **was** one. **Nothing about the archived line was reopened.** The four open M12 decisions recorded at the previous archive stand unchanged and are restated so they are not lost: `godot-image-reference-resolution` (**now investigated, awaiting a proposal**), the FX/animation re-scope, whether the eight refusal class-domains get investigation lines, and whether to mass-convert the 290 available packages (~15,000 files).

- **Lifecycle stage, before this entry, retained in full:** **M12 - ARCHIVED**, change **`asset-package-parameterisation`**: investigation `f7f9861`, proposal PR #344 `2e42640`, Apply PR #345 `9886cf6`, Sync PR #346 `850fc4a`, this archive. **Sync and Archive both ran on their own branches from updated `main` and were merged as merge commits; the proposal branch was not reused for any later stage.** **An independent verification pass ran before Archive, not after** - it returned **PASS WITH FINDINGS** (3 MINOR, 1 INFORMATIONAL, nothing blocking), and two of its three MINOR findings were fixed **here** (a dead `import importlib`; a containment guard that was equality rather than containment, now covering the whole subtree and decided before any `mkdir`). **One finding was about this ledger itself** - that it still read APPLIED after Sync had merged - and it is corrected in this same entry. The M11 ARCHIVED entries above were **not** overwritten: each prior bullet is retained in full and relabelled rather than replaced.

- **Lifecycle stage, before this entry, retained in full:** **M12 - APPLIED**, change **`asset-package-parameterisation`**: proposal merged (PR #344, `2e42640`); Apply implemented and verified on its own branch; **Sync and Archive not started.** The M11 ARCHIVED entries above were **not** overwritten - each prior bullet is retained in full and relabelled rather than replaced.

- **Lifecycle stage, before this entry, retained in full:** **M12 - PROPOSED**, change **`asset-package-parameterisation`** on branch `docs/asset-package-parameterisation-proposal`, bounded by the committed investigation `docs/legacy-m12-asset-parity.md` (merged `f7f9861`). M11 is CLOSED: all six deliver lines archived, its exit criterion assessed MET. **M11's lifecycle, each stage on its own remote branch from updated `main` and merged as a merge commit:** investigation PR #337 `1c8786b`, proposal PR #338 `9094dbe`, Apply PR #339 `ab886f8`, Sync PR #340 `fccb9c5`, post-Sync LF defect fix PR #341 `4b214dc`, archive PR #342 `10e5f59`. `openspec validate --all --strict` reports **73 passed / 0 failed = 72 main specs plus 1 change**, and `openspec validate asset-package-parameterisation --strict` exits **0**. **The investigation recommended this line as "generalise target selection", and measuring it changed the shape twice before a word was proposed.** *First*, the tooling is only half the story: the committed converters were run over **every** candidate rather than a sample, and **units convert 365 of 365 (100%)** while **buildings convert 222 of 452 (49.1%)** — the unit converter generalises cleanly because it never touches fills, and the building converter does not. The **230** building refusals fall into **four disjoint classes, one per failing target, 230 class mentions across 230 targets**: **`65535` unresolvable bitmap fill 133**, **`unknown fill style` 61**, **`unsupported shape tag: 83` 20**, **`shape byte/bit overrun` 16**. So **587** packages are available immediately and 230 buildings are blocked by unresolved format questions. *Second*, two plausible fixes were tried and **both refuted**: porting `first-unit-conversion`'s already-specified referenced-only `65535` placeholder rule into the building converter converted **0** additional targets and regressed **0**, and a separate 40-target probe **disagrees** with that result (697 unreferenced and 14 referenced `65535` fills, neither found in **27 of 40**) — so the largest class is recorded **unestablished** and **no fix is proposed for it**; and reading `merge_conversion_document` suggested a single-target merge that would clobber the other tool's entry, which measurement refutes, since either converter alone emits a **two**-package manifest with `counts.packages = 2`. **The proposal is therefore tooling, determinism, and a census — not mass conversion** (D8), and it surfaces a **fourth instance of the LF-defect class that is sharper than the first three**: `fingerprint_inputs` (`convert_building.py:517-525`) digests **raw working-tree bytes** of `buildings.json`, `inspection.json`, and `image_extraction.json`, the latter two **unpinned** in `.gitattributes` and carrying **170,096** and **1,219,378** CRLF on disk, so the committed `content_version` values are digests of one checkout form — `ddeca799…`/`9d8ad3b3…` reproduce on raw disk bytes and become `c4e76e6d…`/`a0c3861f…` LF-normalised. Unlike the previous three instances this lands on a **provenance field** rather than on a comparison, and the fix generalises a precedent the project already set in `apps/compat-api/guard_baseline.py` ("text digests are line-ending invariant"). Its accepted consequence is recorded rather than discovered later: both committed packages' `content_version` and `conversions.json`'s `package_sha256` change **once**, and the compatibility guard baseline is regenerated in the same change. **D9 records, and does not fix, the defect that both packages' `legacy_id` field carries the sprite stem rather than the content id.** **No M12 line beyond this one is pre-authorised**, and the other two recommended items — the **50 `ambiguous`** plus **32 `missing_source`** image references, and the **FX/animation re-scope decision** — remain unproposed; the FX item is a **decision, not a line**, because neither has committed content to work from.

- **Lifecycle stage, before this entry, retained in full:** **M12 - INVESTIGATION** (`docs/legacy-m12-asset-parity.md`, branch `docs/legacy-m12-asset-parity`). M11 is CLOSED: all six deliver lines archived, its exit criterion assessed MET. **M11's lifecycle, each stage on its own remote branch from updated `main` and merged as a merge commit:** investigation PR #337 `1c8786b`, proposal PR #338 `9094dbe`, Apply PR #339 `ab886f8`, Sync PR #340 `fccb9c5`, post-Sync LF defect fix PR #341 `4b214dc`, archive PR #342 `10e5f59`. **No M12 OpenSpec change exists yet**, so the next stage is **Propose**, on its own fresh branch from updated `main`, and it is **not pre-authorised**.

- **Lifecycle stage, before this entry, retained in full:** **ARCHIVED** for `2026-10-08-market-trade-counters-projection`, on its own branch `chore/archive-market-trade-counters`. **M11 is CLOSED**: all six deliver lines are archived, and there is no active OpenSpec change. Full lifecycle, each stage on its own remote branch from updated `main` and merged as a **merge commit**: investigation PR #337 `1c8786b`, proposal PR #338 `9094dbe`, Apply PR #339 `ab886f8`, Sync PR #340 `fccb9c5`, post-Sync LF defect fix PR #341 `4b214dc`, archive PR #342 `10e5f59`.

- **Lifecycle stage, before this entry, retained in full:** **SYNCED** for `2026-10-08-market-trade-counters-projection`, on its own branch `docs/market-trade-counters-spec-sync`. Full lifecycle so far, each stage on its own remote branch from updated `main` and merged as a **merge commit**: investigation PR #337 `1c8786b`, proposal PR #338 `9094dbe`, Apply PR #339 `ab886f8`. **Archive is the only remaining stage.**

- **Lifecycle stage, before this entry, retained in full:** **ARCHIVED** for `darts`, on its own branch `chore/archive-darts`. Full lifecycle, each stage its own remote branch and merge-commit PR, no branch reused across stages: investigation #315 `7964523`, proposal #316 `7340c33`, Apply #317 `f9af80d` (merge commit over content `129d98d`, which followed the two committed Apply-stage corrections `e75b52c` and `cfdd25c`), Sync #318 `5240bb6` (content `e7cc383`), and this archive. The archive ran with `--skip-specs` because Sync had already seeded both main specs, and **both SHA-256 digests were captured before and after and are unchanged** (`godot-darts` `7281fbb5...d3e`, `godot-social-state` `d40d1bd7...3b7`) - the same correct refusal recorded for `social-state` and `rewards`, which without the flag aborts with *"ADDED failed ... already exists"*. **Two task texts were found contradicted by the delivered code and two task-mandated injections were found never to have been run; all four were corrected or performed rather than ticked** - see the `Post-Archive task check` entry below.

- **Lifecycle stage, before this entry, retained in full:** **ARCHIVED** for `social-state`, on its own branch `chore/archive-social-state`. Full lifecycle, each stage its own remote branch and merge-commit PR, no branch reused across stages: investigation #309 `0cccdde` (correction `fe63b85`), proposal #310 `6763a23`, Apply #311 `60d29c5`, Sync #312 `114ae44`, and this archive #313 `bdbbf8f`. The archive ran with `--skip-specs` because Sync had already seeded the main spec; without it the tool aborts with *"ADDED failed … already exists"*, the same correct refusal recorded for `rewards`. **A task was found NOT done at Archive and implemented rather than ticked** — see the `Post-Archive` finding below. **Before it:** **ARCHIVED** for `rewards`, on its own branch `chore/archive-rewards`. Full lifecycle, each stage its own remote branch and merge-commit PR, no branch reused across stages: investigation #302 `50b2700`, proposal #303 `ebbca3d`, Apply #304 `bade634` (server half `bc4f8f8`, client half `2ec8a08`), the orchestrator's review-fix PR #305 `2b19d73`, Sync #306 `aed98ee`, and this archive. The archive ran with `--skip-specs` because the Sync stage had already added the capability, and the main spec's SHA-256 was confirmed **unchanged** by the archive step.
- **Change status:** **M11's deliver list is COMPLETE - all six items accounted for, and the exit criterion is assessed below rather than left open.** Four were delivered as read-only projections and two were closed by measurement: `visits` and `scores` have **no server-side surface** to implement, which the exit criterion's *"or explicitly excluded"* clause covers. **M11's exit criterion ("All relevant legacy game systems are classified and implemented or explicitly excluded") is MET**, and the honest reading of it is narrower than "the game works": every relevant system this oracle can see is now **classified**, four are **projected**, and the rest are **refused with the reason measured**. That is a different verdict from M10's, which was closed **unsatisfiable from this oracle** because there is no combat loop in the preserved server to make work - and the two must not be conflated. **No line in M11 delivered a round trip.** Six lines, six read-only projections, zero routes, zero executed-legacy fixtures: every legacy branch M11 touched had either no request path, an unvalidated client-sent grant, or content that nothing anywhere reads. **That is the milestone's actual finding, and it is not a shortfall of effort** - the social and special systems of this game lived almost entirely in the Flash client, which absence of a server rule says nothing about. **The recorded open carry-forwards are unchanged** and travel past the milestone boundary: the **ten** recorded flaky surfaces, five sibling suites lacking `--report=` absolute-path resolution, none of the twelve `packages/game-content/tests/` suites running in any battery, committed reports not regenerated by `verify-boot.ps1`, and the `godot-combat-actions` README section gap deliberately left un-backfilled.

- **Change status, before this entry, retained in full:** **M11's deliver list is INCOMPLETE - two lines delivered and archived, and four of the six deliver items are still to advance.** `godot-social-state` established that social **content** has zero consumers and social **state** exists but is never written, and `godot-darts` advanced **`legacy event systems`** and **`special mechanics`**, delivering the darts state machine over six recorded fields and the one surface in M11 where the preserved server derives a value from committed content and computes it authoritatively - the premium account **duration** - beside a committed **price that nothing anywhere reads**. **Nothing is granted, charged, priced, bounded, resolved for a win, or displayed**, and no capability name, identifier, or response field presents a shot, a target, a win, or a premium entitlement as obtainable or active. Every successful action carries a **two-part post-execution proof** - the premium instant moved by exactly the derived duration **and** the **complete** seven-slot stored resource set byte-identical - with each half **made to fail on purpose** so the proof is shown non-tautologous rather than asserted to be. **No executed-legacy fixture exists and none is claimed**, because `tests/saves/fresh-player.json` carries every darts field at its initial value and a zero premium instant, and **no committed document records a future premium instant**, so the extend arm is exercisable only over crafted input - a stronger statement than the usual corpus limitation. **M11's exit criterion is NOT MET and remains unfinished rather than unsatisfiable.**

- **Change status, before this entry, retained in full:** **M10's deliver list is COMPLETE — all seven items accounted for — and the milestone exit criterion is NOT MET.** Three items were delivered and archived (`combat actions`, `damage`, `rewards`); **four were closed by measurement** rather than deferred (`mission loading` has no command in the preserved server; `mission state` was **already delivered** by `godot-quests`; `death` and `mission completion` have **no undelivered surface** on four independently sufficient grounds each). What `rewards` delivered is the two reward cursors as **server-derived transitions** from recorded state, each derived bound beside its schedule's cardinality and **the difference in both directions**, the stamped instant, and the surrounding unread and undecoded surface reported rather than invented. **Its primary finding is that neither cursor can address the whole of the schedule it would address, for two DIFFERENT reasons**, which is exactly why one figure would hide half of it: weekly's derived bound is **5 against 3** rungs, so positions **3 and 4** name no rung; daily's bound is **5 against 5** entries — **no exceedance at all** — and the defect is a one-based vs zero-based offset, leaving position **5** unreachable *and* position **0** unreachable. **Nothing is granted, selected, priced, credited, charged, or displayed**, and no capability name, identifier, or response field implies a payout was paid. Every successful action carries a **four-part post-execution proof** — no map row, no bought-units entry, no storage entry, and every stored resource byte-identical compared as a **complete set** rather than a subset — which is what makes the no-grant claim non-tautologous. **Three divergences** are recorded and **none** is reproduced as parity: the **client-sent item**, the **client-sent next id** (which the preserved branch advances and then overwrites when oversized, moving the recorded cursor **backwards**), and **arity-selected arm choice**. **M10 exit assessment: NOT MET** — "Primary combat loop works" cannot be satisfied from this oracle, because there is no combat loop in the preserved server to make work; see the re-measurement below.
- **M8 exit assessment: MET** — exit criterion "Core unit gameplay works" is satisfied by committed evidence across all eight delivered lines, each
- **M7 exit assessment: MET** — (unchanged; see the detailed assessment above)
- **Current objective:** This orchestration run **closed out M11's sixth and final deliver line, `special mechanics`, through Apply and Sync**, each stage on its own fresh branch from updated `main` and merged as a merge commit. **What the run established:** M11 has no transaction to deliver. Six lines, six read-only projections, zero routes, zero executed-legacy fixtures - and every one of those absences was a decision with a measured reason rather than an omission. **The most important thing it found was in the orchestrator's own process, twice, and both are recorded rather than tidied.** First, **a hard-coded evidence flag that was simply wrong**: the report's `comparable_to_lf_normalised_digest` read `false`, justified by a true statement about the *checkout* attached to a field named for the *files* - and both delivered modules are pure LF, so each raw digest **is** its LF-normalised digest. Three sibling reports carry the same field as `false` and there it is correct, so copying a field *and its value* across file forms is how a guard becomes a lie. Second, **two defects in my own instruments**: `String(PackedByteArray)` does not exist on this engine, so the first fix was a **parse** error surfacing as an unparseable suite rather than as a failing check; and the purity test compared `sha(bytes)` against un-hashed bytes, so `all(...)` printed `False` on two files that are pure LF and pointed straight at a correct file. **A third correction was a disclosure rather than a fix**: `_injection_record()` was presenting a transcribed table of a prior session's external harness run as though it were live evidence, and an earlier review of this change read it exactly that way. `INJECTION_PROVENANCE` now states the suite cannot execute a probe and distinguishes what the block asserts in run from what it does not - asserted, so an edit that leaves the table intact cannot drop it. **And the nine probes were then re-measured against the final delivered bytes**, because a later edit can silently restore guard coverage; measured `6, 4, 7, 27, 8, 2, 2, 3, 4` against the recorded `63`, **no count moved**. The verification then re-ran **every battery at the true final tree** rather than relying on an argument that the two documentation-only edits could not affect.

- **Current objective, before this entry, retained in full:** This orchestration run **closed out M11's second line, `godot-darts`, through all four stages** - investigation, proposal, Apply, Sync, Archive - with each stage on its own fresh branch from updated `main` and merged as a merge commit, and then **recorded the milestone in the status block rather than declaring M11 done**. **What this run actually established:** the first server-derived value M11 derives from a committed schedule, beside a committed price with **zero** consumers, so nothing is charged - a **refusal**, and explicitly **not** parity, because `engine.apply_resources` applies a **client-sent** vector before the dispatcher chain opens. **The most important thing it found was in the orchestrator's own process.** At Archive all four artifacts reported `done` and the task list reported `Complete`, and checking the **31** boxes against the implementation surfaced **two task texts the delivered code contradicted** - task 2.1 named a verification command for `res://tests/test_darts_state.gd`, **a suite that does not exist**, the delivered suite being the single `res://tests/test_darts.gd`; and task 6.3 asked to "verify the manifest states" the absence of an executed-legacy fixture when **there is no manifest and no fixture** - plus **two task-mandated injections that had never been run**: task 1.3's misspelled owner name and task 2.2's temporarily changed recorded corpus number. **All four were corrected or performed rather than ticked.** The two injections produced **2 independent failures each** with byte-identical restores (`b7d28e8b...7c37a` and `0d825fa5...7453`), and the suites returned to **405** and **610** checks at exit 0. The contradictions are recorded as **C5** and **C6** in the archived `tasks.md` rather than edited away. **A cross-line defect was fixed at the source rather than patched over:** adding `/v0/darts` broke **eight** guards owned by **four** earlier delivered lines, because every family slices a route's source from its `def` to *some* end marker and two suites reach forward across every route declared between them. Two placements were tried and rejected before the route was declared **second** - the only slot no delivered span reaches - which left the four `markers[-1]` invariants **untouched**, and the placement is now a **pinned property**, proven by injection with **four independent detections** and a byte-identical restore. **A `darts-live` phase was deliberately not delivered**, and that narrowing is recorded in `tasks.md`, `AGENTS.md`, and the client README rather than omitted: a client able to fire `darts_shoot_balloon` is precisely the surface this line exists to refuse.

- **Current objective, before this entry, retained in full:** This orchestration run **closed out M11's first line, `godot-social-state`, through all four stages** — investigation, proposal, Apply, Sync, Archive — with each stage on its own fresh branch from updated `main` and merged as a merge commit, and then **recorded the milestone in the status block rather than declaring M11 done**. **What this run actually established:** social CONTENT has **zero** consumers across all three committed tables and 41 entries, and social STATE exists but is never written — **12 of 19** fields have zero occurrences, 12 are write-less, and the single real writer, `set_resource_allies`, takes its value from a **client** argument, which is why it is recorded and **not reproduced**. **The most important thing it found was in the orchestrator's own process:** at Archive, all four artifacts reported `done` while **all 43 task boxes were unchecked**, and checking them against the implementation surfaced **four problems** — three task descriptions the delivered code **contradicted** (a read-without-written field that is read *and* written, a blanket comparison ban that would have condemned legitimate `typeof` discrimination, and a hardcoded suite count that does not exist), and one task that was **simply not done** (the injection evidence was missing from the report). All four were **implemented or corrected**, not ticked. **Two further corrections** to figures already committed to `docs/legacy-m11-social.md` and the proposal are recorded rather than quietly edited: the zero-occurrence group is **12**, not 13, because `questsRank` is read and written, and D9's title was wrong for the same reason. **This run also ran the batteries it had every reason to skip**, because the recorded `rewards` post-Sync regression was exactly that failure; both passed, and the `boot-report.json` diff was inspected rather than assumed and contained only the timestamp and the advanced commit. **Prior run, retained in full:** this orchestration run **reviewed and accepted the `rewards` Apply work rather than inheriting it**, then closed the line out. The client agent had merged its own Apply PR without the review gate, which produced the correct end state but skipped a check the workflow requires — and **the gate then earned its keep**, because the review found **three defects in that line's own delivered client half**, all three instances of the recorded *a check that fires on its own prose* class, and none of them in the underlying data: (1) the suite reported a `godot-combat-actions` README section **present while no such section exists**, because the search was the bare substring and the **only** occurrence in the file was this capability's own prose **recording the gap** — and the line was an `info()` call asserting nothing, while its own comment stated the opposite intent; (2) two prose sites claimed **both** derived bounds exceed their schedule's cardinality, which is **false for the daily cursor**, while the delivered data honestly reported `exceeds_cardinality_by: 0` and the suite already stated why a single exceedance figure is the wrong shape; (3) a census comment read *"all 34 walked documents that carry a `privateState`"* immediately beside constants of 34 walked and 33 carrying. All three were fixed in follow-up PR #305 with the first **proven by injection** rather than trusted. **Two figures were re-measured independently** rather than quoted, and one **requirement was reconciled at Sync** because the contract itself asserted an exceedance the implementation had to contradict. The run then recorded the completion with only checks the orchestrator actually ran, **named what it did NOT independently re-proven**, **re-measured M10's exit basis from source** (finding **7 of 7** combat fields with zero code-only consumers and **58,336** placed rows that are **every one exactly 8 slots**), and fixed **two instrument faults of its own** while doing so. **The standing lesson is unchanged and re-earned twice more: a counting script must be shown to count what it claims, and a check must be shown to fail when it should.**
- **Last defect fix:** **`market-trade-counters-projection` - post-Sync LF defect, on `fix/market-trade-lf-digest-check`**, its own branch and PR per the `fix/auction-manifest-section-guard` precedent, because a defect found after Apply or Sync gets its own branch rather than being folded into the next stage's diff. **The defect reproduced on `main`, and the committed evidence already proved it:** `_check_evidence_record()` required both delivered modules to be pure LF, but `core.autocrlf=true` with no `.gitattributes` rule for those paths means a default Windows checkout delivers **CRLF**, so `_modules_are_pure_lf()` correctly measured `false` and the suite failed. The artifact that shipped said so - the committed `evidence/boot/boot-report.json` records `"pass": false`, `failures: ["test_market_trade exits 0 (got 1)", "test_market_trade reports PASS"]` and that command's `exit_code: 1` - while the Apply-stage battery had passed on the authoring checkout. **This is the same defect class as the hard-coded `false` corrected during Apply, in the opposite direction:** both mistake a property of **how the file arrived** for a property of **what was delivered**, and a checkout form is never a delivery guarantee. It is the **third** recorded instance of that class, after Apply's `comparable_to_lf_normalised_digest` constant and the byte-count guard `godot-unit-experience` fixed. **The fix is two things because they fix different failures:** each module now records a second `sha256_lf_normalised` beside its raw digest, and the check asserts **only checkout-independent facts** - both digests present, the flag equal to a **fresh** measurement, raw equal to LF-normalised **iff** the flag is true, both modules taking one of the two branches, and **never neither** - with the equality check made **non-tautological** by computing the two digests through independent routes (`FileAccess.get_sha256` vs `HashingContext`); and `.gitattributes` pins the three paths to LF (**+12 lines**, `git check-attr` verified `eol: lf` under `core.autocrlf=true`), which is what makes the **committed report's digests reproduce on any checkout**. The first half alone would pass the suite everywhere while leaving the evidence report checkout-dependent. **Proof: 1005 checks and exit 0 on a pure-LF tree, and 1005 checks and exit 0 on a tree with all three files rewritten to CRLF** - the second run is precisely the case that failed on `main` - restored afterwards to zero CRLF pairs. Report regenerated: **40,006 bytes**, zero CRLF, sha256 **`b2e2c9c6…5348e`**, byte-identical across **three** runs including a different output path, **1007** checks with `--report`, and the **raw** digests unchanged (`1f8d8dcf…`, `d8e1d852…`), so the report diff is only the two added fields and corrected prose. Injection probes re-run after the suite edit: still `6, 4, 7, 27, 8, 2, 2, 3, 4` = **63**, **no count moved**, second re-measurement against this final state. Batteries re-run green: `verify-boot.ps1` exit `0` with **230/230** assertions, **80** commands, **zero** non-zero exits, guard digest `6978b959…ff348` identical pre/post, and **1,144** logs with zero `[test] FAIL`/`^ERROR:`/`SCRIPT ERROR`; `verify.ps1` exit `0`; compat **3077 OK** unchanged; validator **23 / 22 / 604**; manifest **3,258 / 758,423,699**; `openspec validate --all --strict` **73 passed / 0 failed** (72 main specs + 1 change). The `boot-report.json` diff was inspected rather than assumed and **is** the fix's evidence: `exit_code` `1 → 0`, two assertions `false → true`, `failures` emptied, `pass: false → true`, 8 insertions / 9 deletions and **no** `log` renumbering. **Two recorded flaky surfaces fired on this branch, both on suites the fix does not touch:** a `test_town_upgrade` access violation `0xC0000005`, and `test_game_api_live.gd` reporting *"the live reference instant is not older than the instant it stamped"* - a second-boundary clock race of the same family as the recorded `server_time` surfaces. The third run passed. Recorded as the **eleventh** and **twelfth** surfaces, both still open.

- **Last completed change, before this entry, retained in full:** **`market-trade-counters-projection`** - Apply merged as `ab886f8` (PR #339), Sync merged as `fccb9c5` (PR #340). Investigation PR #337 `1c8786b`, proposal PR #338 `9094dbe`. Before it: M11's `auction-schedule-projection` - `2026-10-08-auction-schedule-projection`. Before that: `social-rewards-assist-projection`, `friends-roster-projection`, `2026-10-07-darts`, `2026-10-06-social-state`.

- **Last completed change, before this entry, retained in full:** this entry was left stale at `darts` when M11 line 3 closed, and it is corrected here rather than left to mislead. **`friends-roster-projection` is the last completed change** — archived as `2026-10-07-friends-roster-projection` (#321 `3df888a` investigation, #322 `f7cc36b` proposal, #323 `4b210dc` Apply merge, #324 `fd258ce` Sync merge, #325 `6ad36c3` archive merge). Before it: M11's `darts` - `2026-10-07-darts` (#315 `7964523`, #316 `7340c33`, #317 `f9af80d`, #318 `5240bb6`, #319 `216ccb5`, plus #320 `32a26b5` for the archive ledger). Before that: M11's `social-state` - `2026-10-06-social-state`.

- **Last completed change, before this correction, retained in full:** `darts` - archived as `2026-10-07-darts` (#315 `7964523` investigation, #316 `7340c33` proposal, #317 `f9af80d` Apply merge, #318 `5240bb6` Sync merge, and this archive). Before it: M11's `social-state` - `2026-10-06-social-state`.

- **Last completed change, before this entry, retained in full:** `social-state` — archived as `2026-10-06-social-state` (#309 `0cccdde` investigation, #310 `6763a23` proposal, #311 `60d29c5` Apply, #312 `114ae44` Sync, #313 `bdbbf8f` archive). Before it: M10's `rewards` — `2026-10-05-rewards`. Before that: M10's `damage` — `2026-10-05-damage`. Before that: `combat actions` — `2026-10-05-combat-actions`. Before that: `mission vocabulary` — `2026-10-05-mission-vocabulary`.
- **Next eligible objective:** **Sync then Archive `asset-package-parameterisation`**, each on its own branch and PR. Beyond that, M12 needs **two decisions before any further line is proposed**, and both are recorded rather than assumed: whether the **refusal classes get their own investigation lines** (now **twelve** class-domains: five building, seven unit, two spanning both), and whether the **mass conversion** of the **290** available packages (~15,000 files, plus a preservation-manifest regeneration) is worth doing before **FX replacement** and **animation gaps** - the census is the measurement that makes that question answerable, and it was the point of the line. Also carried forward unproposed: **`godot-image-reference-resolution`** (**50** `ambiguous` + **32** `missing_source`) and the **FX/animation re-scope decision**.

- **Next eligible objective, before this entry, retained in full:** **`2026-10-08-market-trade-counters-projection` Archive, then a decision on M12** - neither is pre-authorised. Archive runs on its own branch `chore/archive-market-trade-counters` from updated `main`, as a **merge commit**, with the branch deleted afterwards. **M11 needs no further deliver line**: all six items are accounted for and the exit criterion is assessed as met above. **The next phase must not begin from this cursor's evidence** - every M11 line needed its own committed `docs/legacy-*.md` investigation before any proposal, and that rule is not relaxed by a milestone closing. **Recorded open carry-forwards**, none of which is a reason to invent a surface: the **twelve** recorded flaky surfaces, the newest two found on `fix/market-trade-lf-digest-check` and recorded in full above - a `test_town_upgrade` access violation `0xC0000005` and a `test_game_api_live.gd` second-boundary clock race, both on suites that fix does not touch and both cleared by a re-run, which is exactly the disposition the rule prescribes; five sibling suites lacking `--report=` absolute-path resolution; none of the twelve `packages/game-content/tests/` suites running in any battery; committed evidence reports not regenerated by `verify-boot.ps1`; the `godot-combat-actions` README section gap; and the six surfaces this milestone named and declined - the atom-fusion **powerup purchase** (`buy_powerups` is a `# TODO` with a committed six-row ladder and zero consumers), `first_time_marketplace`, `rt_open_graph_unit`, the **24-declaration** `SPELL_*`/`TECH_*` gap, and the inert `crossPromotionsFinished`/`unlockedSkins` pair beside a **one-entry** `specials.json`.

- **Next eligible objective, before this entry, retained in full:** **`godot-construction-assist` - PROPOSED, awaiting Apply.** Its binding investigation is `docs/legacy-m11-social-rewards.md`. Apply must begin by re-running the suites this line touches and reporting before/after counts, because adding client sources measurably raises every suite that walks the source tree. The **structural guards are the part that must not be trusted**: the whole-function inventory pin and the case-insensitive substring reserved-name guard each have to be proven by **injection against a byte-identical copy**, with the restored SHA-256 recorded in the evidence report, including one probe that borrows **no** reserved word so the belt is shown necessary rather than redundant. **No route, no `apps/compat-api/**` change, no windowed capture** (nothing is rendered) and **no live phase** are in scope, and the compatibility suite's **3077** baseline is asserted rather than assumed. Two recorded absences must survive Apply unchanged: the absent `friend_assistable` check is **recorded, not enforced**, because enforcing it would refuse two committed corpus rows; and the `0` sentinel's meaning stays a **quoted source comment**, never a decode.
- **Next eligible objective, before this entry, retained in full:** **`social rewards` (M11 line 4) - INVESTIGATED, propose next on its own fresh branch from updated `main`.** Its binding contract `docs/legacy-m11-social-rewards.md` is committed on branch `docs/legacy-m11-social-rewards`; no OpenSpec change exists for it yet and **none is pre-authorised**. **What the investigation established, and why this line is neither a refusal line nor a transaction:** the standing classification of `social rewards` is **falsified** - the three tables' zero-consumer census is **reproduced** and **true**, but it does not describe the deliver item, because the preserved server holds a social-assistance state machine the tables never mention. `attr["si"]` is **"Socially In Construction"** by the author's own comment at `engine.py:19`, gated by the committed `properties.friend_assistable` string `'1'` on **26 of 470 buildings** and **0 of 429 units** with **exactly one** consumer site, and persisted on **53 of 3,372** placed rows across the canonical 10-document corpus with **7** elements totalling **one** distinct value, the integer `0`. **The friend arm has no writer anywhere**, and the sentinel's meaning is fixed by `engine.py:142`'s comment *"0 is for buying instead of hiring friends"* - so the surface records **a paid substitute for a friend**, the inverse of the deliver item's name. **Nothing is charged and nothing is granted**, so the recommended shape is a **read-only projection plus an absence record with no route**, leaving the compat suite at its **3077** baseline as a *verified* figure; a `/v0/assist` route is the **rejected alternative**, and `set_resource_allies` must be settled first because it is the branch with the real write. **Three corpus facts are recorded as gaps, not explanations**: `si` does **not** imply `friend_assistable` in either direction. **`giftable` and `gift_level`** are measured as two more committed fields with zero legacy consumers (over all 11 modules and six rules, `0 / 0 / 0 / 0 / 0 / 0` each), with **no ordinal position claimed for either** because no reconciled census of zero-consumer committed fields exists in this repository and the earlier "sixth"/"seventh"/"ninth"/"tenth" labels were each taken over a different scope, and `giftable`'s absence from `godot-unit-behaviors`' census is recorded as a gap in a delivered artifact. **The proposed line should also carry a forward reference to the standing fragile surface**: the delivered-suite end marker still resolves through an **unanchored** `route.index('@app.post("/v0/level_up")')`, recorded by M11 line 2. The recorded open carry-forwards remain the `godot-combat-actions` README section gap, deliberately left un-backfilled, and the **eight** still-open recorded flaky surfaces, the eighth being `test_collect_endpoint`'s sub-second clock budget.

- **Next eligible objective, before this entry, retained in full:** **`friends-roster-projection` Sync, then Archive, on their own fresh branches from updated `main`.** Neither is pre-authorised as automatic: Sync is skipped only if there is genuinely nothing to synchronize, and Archive runs only after Apply and any required Sync are merged. **The one remaining M11 deliver item is `social rewards`, and it remains unexamined** - three committed tables, **41** entries, zero consumers, `neighborAssists` and `receivedAssists` uniformly `{}` in **33 of 33** documents - so it should be closed by measurement or advanced, following the four-item precedent M10 set, on a `docs/legacy-m11-social-rewards.md` investigation of its own. **M11's exit criterion is NOT MET and remains unfinished rather than unsatisfiable**, which is a different statement from M10's unsatisfiable verdict and must not be conflated with it. `crossPromotionsFinished` and `unlockedSkins` are inert and `specials.json` holds exactly **1** entry, `legacy_id` `"925"`. **No line beyond Sync/Archive is pre-authorised and no investigation exists for it**; the next stage opens with a `docs/legacy-*.md` on its own fresh branch. The recorded open carry-forwards are the `godot-combat-actions` README section gap, deliberately left un-backfilled, the **eight** still-open recorded flaky surfaces - the eighth being `test_collect_endpoint`'s sub-second clock budget, found by this line - and the delivered-suite fragility recorded by M11 line 2, a resolved end marker using an **unanchored** `route.index('@app.post("/v0/level_up")')`.

- **Next eligible objective, before this entry, retained in full:** **`godot-friends` - PROPOSED, awaiting Apply.** Its binding investigation `docs/legacy-m11-friends.md` is committed (PR #321, merge `3df888a`, content `82b6df9`) and the proposal is active as the OpenSpec change `friends-roster-projection`. **What the investigation established, and why this line is not a refusal line:** `friends` is **not** state-only with no consumer - the committed classification is falsified (see the Roadmap cursor entry) - and the surface it names is a **roster projection** (`neighbors()`, `sessions.py:191-221`) with real executed parity evidence already committed, so this is the **first M11 line that needs no new fixture capture**. The finding is decisive in the opposite direction from the deliver item's name: **membership is total and unconditional**, with no direction, consent, or lifecycle, so the line delivers a **roster** and refuses the relationship vocabulary. **The `social rewards` item remains unexamined** and is the next candidate after this line: three tables, **41** entries, zero consumers, `neighborAssists` and `receivedAssists` uniformly `{}` in **33 of 33** documents, and it should be closed by measurement or advanced, following the four-item precedent M10 set. `crossPromotionsFinished` and `unlockedSkins` are inert and `specials.json` holds exactly **1** entry, `legacy_id` `"925"`. **No line beyond this one is pre-authorised and no investigation exists for it**; the next stage opens with a `docs/legacy-*.md` on its own fresh branch. The recorded open carry-forwards remain the `godot-combat-actions` README section gap, deliberately left un-backfilled, the **seven** still-open recorded flaky surfaces, and the delivered-suite fragility recorded by line 2 - a resolved end marker using an **unanchored** `route.index('@app.post("/v0/level_up")')`.

  **Next eligible objective, before this entry, retained in full:** **within M11, one deliver item, investigated before proposed.** After two lines the cursor is an elimination over what remains: **`friends`** is *state-only with no consumer* (persisted in **33/33** documents, **zero** legacy occurrences, uniformly empty) and **`social rewards`** is *content committed, behaviour absent* (three tables, **41** entries, zero consumers, `neighborAssists` and `receivedAssists` uniformly `{}`), while `visits` and `scores` are already rejected. **`legacy event systems` and `special mechanics` are partial**, and the committed investigation flagged one specific follow-up measurement it declined to take: **`magics` and `mana` are read without any writer in `command.py`**, which inverts the usual read/write shape and is worth measuring rather than concluding; `crossPromotionsFinished` and `unlockedSkins` are inert, and `specials.json` holds exactly **1** entry, `legacy_id` `"925"`. **No line is pre-authorised and no investigation exists for any of them**; the next stage opens with a `docs/legacy-*.md` on its own fresh branch. The recorded open carry-forwards remain the `godot-combat-actions` README section gap, deliberately left un-backfilled, the **seven** still-open recorded flaky surfaces, and the **new** fragility this line recorded: a delivered suite resolves its end marker with an **unanchored** `route.index('@app.post("/v0/level_up")')`, so a span meant to reach one route can silently reach another that merely mentions the literal.

- **Next eligible objective, before this entry, retained in full:** **within M11, one deliver item, investigated before proposed.** M11's deliver list is `friends`, `visits`, `scores`, `social rewards`, `legacy event systems`, `special mechanics`, and **five of the six remain unexamined**. The measured result of line 1 makes the **next selection a real elimination rather than a guess**: `visits` and `scores` were already **checked and rejected** as having any server-side surface — the `world_id` map key and the `worldChange` `privateState` key are carried in **33 of 33** documents with **zero** legacy occurrences, there is **zero** score arithmetic, and the two candidate readings (`lost` at `command.py:792`/`:868` and `won` at `auctions.py:164`) were measured and **rejected** as scores. `friends` is therefore the next candidate by elimination, and **`legacy event systems` / `special mechanics` are the two the classification-shaped exit criterion turns on.** **No line is pre-authorised and no investigation exists for any of them**; the next stage opens with a `docs/legacy-*.md` on its own fresh branch. The recorded open carry-forwards remain the `godot-combat-actions` README section gap, deliberately left un-backfilled, and the **seven** still-open recorded flaky surfaces.
- **M10 OpenSpec validation, superseded by the entry above but retained in full:** PASS — `rewards` **at Archive** (2026-10-06): `openspec validate --all --strict` reports **65 passed / 0 failed across 65 items**, exit `0`. The item count is only explicable as a pair, so both figures are recorded: **65** while the change was still active, **66** at Sync once the new `godot-rewards` capability spec was added, and **65** again at Archive once the change stopped counting as an item while its capability spec remained. The archive ran with `--skip-specs` because Sync had already added the capability — without it the tool aborts with *"ADDED failed ... already exists"*, which is the correct refusal and not a defect. `openspec validate godot-rewards --strict` passes and emits only the repository's standing long-requirement INFO notices.
- **M10 implementation verification, superseded by the entry above but retained in full:** Integration review of `rewards` by the root orchestrator, with both batteries re-run in the final state by the orchestrator itself — **orchestrator-run, not an independent agent**. Actually executed: `capture_rewards_fixture.py` **exit 0** on two consecutive runs with containment `18e5e55ba85473bb` **identical before and after** both; `test_rewards.gd` **419 checks** PASS, exit 0 (**417** before the review fixes, **422** with `--report`); `verify.ps1` exit **0** with `PASS all checks succeeded`; `verify-boot.ps1` exit **0** with **44 hermetic suites** (up from 43), every one `exit=0`, **218 assertions** all ok, **0 failures**, guard digest `6978b959…ff348` **identical before and after**, port 5056 released and no working-tree `saves/`; compat **`Ran 2921 tests … OK`**, exit **0** against a 2662 baseline, **+259** = 134 envelope + 74 endpoint + 51 parity; `validate_content.py` `result: valid`; `hash_manifest.py verify` **3,258 entries**; `openspec validate --all --strict` **66 passed / 0 failed**; and the evidence report **byte-identical across three consecutive runs**, 45,135 bytes LF, sha256 `A86E3443308F9496B348EE23…`, normalised to CRLF at 46,304 bytes. **832** battery log files inspected with **zero** `[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines. **`git status` over `command.py`, `engine.py`, `config/`, `villages/`, `tests/saves/`, `packages/`, `tools/`, `tests/fixtures/`, and `docs/` was clean** — no preservation material changed by either Apply half. **Three defects the review found in this line's own client half were fixed in a follow-up PR rather than merged unexamined**, all three instances of the recorded *a check that fires on its own prose* class: the suite reported a `godot-combat-actions` README section **present while none exists**, because the search was the bare substring and the only occurrence was this capability's **own prose recording the gap** — and it was an `info()` line asserting nothing; two prose sites claimed **both** bounds exceed their cardinality, false for daily, while the data said `exceeds_cardinality_by: 0`; and a census comment read *"all 34 walked documents that carry a `privateState`"* beside pins of 34 walked and 33 carrying. The first was **proven by injection** — a fake heading produced 1 failure and exit 1, restore byte-identical. **One requirement was reconciled at Sync rather than inherited**: requirement 2 asserted an exceedance for **both** cursors, which is false for daily, so the requirement was corrected and the code was not. **One claim was tightened rather than repeated**: re-running the capture rewrites **129** fixture leaves and **every one** was classified as a wall clock or a digest over one, so the fixture is **semantically reproducible** and deliberately **not** byte-deterministic, consistent with the manifest's own `instant_is_volatile: true`. **Two figures were re-measured independently**: the save-document census is **34** walked / **33** carrying / **zero** missing any of the 7 save-only fields (the investigation's earlier `39/39` was a different scope, counting fixture step files), and `exceeds_cardinality_by` is **2** for weekly and **0** for daily. **Recorded as NOT independently re-proven**, so a later reader cannot mistake it for orchestrator-verified: the **seven server-half structural injection guards** and the **sibling suites'** per-suite check counts.

- **Post-Archive task check, found by inspecting the implementation instead of trusting the boxes (2026-10-06).** All four artifacts reported `done`, yet **all 43 task boxes were unchecked**. Checking each box against the implementation found **three task descriptions the delivered code contradicted**, which were **corrected rather than ticked**: 1.5 said `questsRank` was read-without-written and that **six** fields are written — it is read **and** written, and **seven** are written; 4.6 demanded a blanket ban on comparing committed social values, which would have condemned the `typeof` discrimination the projection legitimately uses, so the delivered guard is arithmetic plus **ordering**; and 8.1 described a hardcoded suite count in `verify-boot.ps1` that **does not exist**, the array being the only registration. **A fourth task was genuinely not done**: 5.7 required the injection results and the pre/post SHA-256 of the restored file to appear in the **evidence report**, and the report recorded the guards but not the proof that they fire. It was **implemented**, not ticked: the record is carried as data and the suite asserts it is complete and internally consistent, including that all six probes carry the **same** restored digest as the delivered module, which makes the byte-identical restore checkable from the report rather than remembered. The standing lesson re-earned: *a checked task box is not evidence.*
- **Last implementation verification (orchestrator-run, 2026-10-08):** `godot-market-trade-counters`, run by the root orchestrator on the **final** state and actually executed, not inherited. `verify-boot.ps1` exit **0**, `PASS all checks succeeded`, 80 commands, **230/230** assertions ok, **0** failures, hermetic suites **50** (was 49), live phases **23 unchanged**, guard digest `6978b959…ff348` **identical before and after**, and **1,144** log files inspected carrying **zero** `[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines. `verify.ps1` exit **0**. Compat suite `Ran 3077 tests … OK` exit **0** - a *verified re-run baseline*, since the line adds no endpoint and touches `apps/compat-api/**` not at all. Validator **23 files / 22 schemas / 604 references**, `result: valid`, exit **0**. Manifest **3,258 entries / 758,423,699 bytes**, exit **0**. `auctions/` and `saves/` both absent. **A worker-reported baseline of "22 files / 21 schemas" was WRONG**; measured **23 / 22 / 604**. It appeared only in that worker's chat report - the repository was never wrong, and it is recorded because a wrong figure in a report is precisely what a later reader re-measures and re-litigates. **`boot-report.json` was regenerated and its diff inspected rather than assumed:** 79 -> 80 entries, exactly one added, nothing removed, order preserved, and on the **25** retained entries **only the `log` field changed**. **One predicted figure was wrong:** a verifier predicted **26** log renumberings and the measurement is **25** - off by one, no effect on the conclusion, and recorded because a predicted number that differs from the measured one was never a measurement.

- **Last implementation verification (orchestrator-run, 2026-10-07), before this entry, retained in full:** `godot-friends`, run by the root orchestrator on the **final** state. Actually executed: `test_friends.gd` **570 checks** PASS, exit 0 - the **47th** registered hermetic suite; the evidence report `friends-report-v1` **29,220 bytes**, sha256 `6318c9b5...81f4`, byte-identical across **three** consecutive runs; the **seven injections** run twice and re-run against the final delivered state, every probe exit 1 with failure counts **3, 3, 4, 3, 3, 34, 1**, every restore byte-identical to a digest captured **before** the probe, zero NUL bytes and a final newline asserted on each, the module digest after all seven equal to the digest before the first (`ed4d88a8...b9dd`, 32,470 bytes), and `git diff --numstat --ignore-cr-at-eol` plus `git status --short` equal to their pre-probe values after each; the sibling suites `test_social_state.gd` **405** (unchanged - the required result for a hand-off moving zero fields), `test_project_scope.gd` **2,087** (was 2,053; the allow-list grew by exactly three paths), `test_content_registry.gd` **87**, `test_game_api_fake.gd` **1,322**, `test_scene_build.gd` **36** and `test_darts.gd` **610**, all unchanged; compat **`Ran 3077 tests in 52.428s`** then **OK**, exit 0 - **unchanged**, the required result for a line that adds no endpoint; `verify.ps1` `PASS all checks succeeded`, exit 0; `verify-boot.ps1` `PASS all checks succeeded`, exit 0, **47 hermetic suites** (was 46), **23 live phases UNCHANGED** because no live phase was delivered, **224 assertions** (was 222), guard digest `6978b959...ff348` **identical before and after**, port 5056 released and no working-tree `saves/`; **988** battery log files inspected with **zero** `[test] FAIL`, `^ERROR:` or `SCRIPT ERROR` lines; `validate_content.py` `result: valid`, 22 outputs, 21 schemas, 604 references, exit 0; `hash_manifest.py verify` **3,258 entries**, 758,423,699 bytes, exit 0; `openspec validate --all --strict` **68 passed / 0 failed** (68 items). `git status` confirmed **no** content-package, fixture, save, config, village, conversion-package, registry-manifest, or legacy-source byte changed - the diff is three client-side files and three new client-side paths. **`boot-report.json` was regenerated and its diff inspected rather than assumed**: it contained only `generated_utc`, the advanced `git_commit` (`5240bb6` -> `f7cc36b`), the one added `test_friends` command, and **25** `log`-field index renumberings - each of the 25 confirmed to be the `log` field and nothing else, because a rename and a content change are easy to confuse inside a 51-insertion diff. **Two honest failures were recorded rather than hidden**: the first `verify-boot.ps1` run failed `test_town_gate` because the module quoted the Flash variable name in prose, which that gate's raw substring needle forbids - fixed by **describing** the transport and citing `templates/play.html:99` and `server.py:91`, **not** by relaxing either no-Flash gate; and the same run failed one compat test, `test_collect_endpoint`'s `test_a_recent_instant_is_too_early`, whose **sub-second** time budget was exhausted by machine load - now recorded as the **eighth** recorded flaky surface in `AGENTS.md`, established as pre-existing and unrelated by `git diff --name-only` returning no `apps/compat-api/**` path, with the file passing **five consecutive times** alone afterwards and the full discovery passing at 3077. **Not fixed here**: the honest fix belongs to `godot-building-collect`, which owns the collect refusal.

- **Last implementation verification (orchestrator-run, 2026-10-06), before this entry, retained in full:** `godot-darts`, run by the root orchestrator on the **final** state, plus the two task-mandated injections run at Archive. Actually executed: `test_darts.gd` **610 checks** PASS, exit 0 - the **46th** registered hermetic suite; `test_social_state.gd` **405 checks** (was **361**); `test_project_scope.gd` **2,053** (was 1,832 - the allow-list grew by the four darts scripts, the suite, and the report); `test_content_registry.gd` **87**, `test_game_api_fake.gd` **1,322**, and `test_scene_build.gd` **36**, all **unchanged**; darts envelope **82 tests** and darts endpoint **73 tests**, both OK; compat **`Ran 3077 tests ... OK`**, exit **0** against the 2921 baseline, **+156** = 82 + 73 + 1 new tutorial test - the growth being required, because this line adds a state-mutating route; `verify.ps1` `PASS all checks succeeded`, exit **0**; `verify-boot.ps1` `PASS all checks succeeded`, exit **0**, **46 hermetic suites** (was 45), **23 live phases UNCHANGED** because no live phase was delivered, guard digest `6978b959...ff348` **identical before and after**, port 5056 released and no working-tree `saves/`; **976** battery log files inspected with **zero** `[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines; `validate_content.py` `result: valid`, 22 outputs, 21 schemas, 604 references, exit **0**; `hash_manifest.py verify` **3,258 entries**, 758,423,699 bytes, exit **0**; `openspec validate --all --strict` **67 / 0** at Apply, **68 / 0** at Sync, **67 / 0** at Archive. The evidence report digest `e4859928...2a044`, **28,484 bytes**, byte-identical across **three** consecutive runs. `git status` confirmed **no** content-package, fixture, save, config, village, conversion-package, registry-manifest, or legacy-source byte changed, and `boot-report.json` was regenerated and its diff **inspected rather than assumed** - it contained only `generated_utc`, the advanced `git_commit`, the one added `test_darts` entry, and the log-index renumbering that follows. **The two Archive injections:** misspelling the foreign owner `godot-darts` to `godot-dartz` in `social_state.gd` (2 replacements) produced **2 independent failures** naming both foreign fields; changing the pinned distinct-value count of `timeStampDartsReset` from `15` to `16` on line 111 of `darts_state.gd`, **one number and nothing else**, produced **2 independent failures**. Both restores byte-identical, and both suites returned to their passing counts at exit 0.

- **Last implementation verification (orchestrator-run, 2026-10-06), before this entry, retained in full:** `godot-social-state`, run by the root orchestrator on the **final** state. `test_social_state.gd` **361 checks** PASS, exit 0 (**328** before the injection record was added, which is what proves the record is load-bearing rather than decorative); `test_project_scope.gd` **1,968** (was 1,934 — the allow-list grew by three paths); `test_content_registry.gd` **87** and `test_scene_build.gd` **36**, both **unchanged**; `verify.ps1` `PASS all checks succeeded`, exit **0**; `verify-boot.ps1` `PASS all checks succeeded`, exit **0**, **45 hermetic suites** (44 + this one), **220 assertions**, **0** failures, guard digest `6978b959…ff348` **identical before and after**, port 5056 released and no working-tree `saves/`; **884** battery log files inspected with **zero** `[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines. Compat suite **unchanged** at `Ran 2921 tests … OK`, exit 0, which is the required result for a line that adds no endpoint and does not touch `apps/compat-api/**` at all. `validate_content.py` `result: valid`, 21 schemas, exit 0. `hash_manifest.py verify` **3,258 entries**, 758,423,699 bytes, exit 0. The evidence report digest `703ce9ef…c894`, **17,605 bytes**, byte-identical across **three** consecutive runs, and **re-verified against the committed Git blob** — which is LF, no BOM — rather than against the working tree, so the figure cannot be a CRLF artefact. `openspec validate --all --strict` **67 passed / 0 failed** after Sync and **66 / 0** after Archive. `git status` confirmed **no** content-package, fixture, save, config, village, conversion-package, registry-manifest, or legacy-source byte changed. **The `boot-report.json` diff was inspected rather than assumed**: it contained only `generated_utc` and the advanced `git_commit`, which is correct because this line adds no live phase.
- **Post-Archive task check, found by inspecting the implementation instead of trusting the boxes (2026-10-07).** The archive reported `Task status: Complete`, yet checking the **31** boxes against the delivered code found **two task texts the implementation contradicts**. **C5**: task 2.1 said to verify with `res://tests/test_darts_state.gd`, and **no such suite exists** - four modules were delivered but as **one** suite, `res://tests/test_darts.gd`, at **610 checks**. The projection requirement is satisfied; the **command as written cannot be run**, so it is corrected in the archived `tasks.md` rather than left as a verification step that would fail anyone following it. **C6**: task 6.3 said to "verify the manifest states" that no executed-legacy fixture is claimed, and **there is no manifest and no fixture**, because the committed investigation established that no darts transaction is executable against the corpus. The absence is recorded in **four** places, none of them a manifest: the committed investigation, the task itself, the `AGENTS.md` section, and the evidence report's `claim_limits` (10 entries) and `not_delivered` (6), which carry corrections C3 and C4 verbatim. Asserting a manifest exists would be inventing evidence. **Two further tasks mandated injections that had never been run**, and both were **performed rather than ticked on the strength of the mechanism existing**: task 1.3's misspelled owner name (**2** independent failures, restore `b7d28e8b...7c37a`, suite back to **405**) and task 2.2's temporarily changed recorded corpus number (**2** independent failures, restore `0d825fa5...7453`, suite back to **610**). Together with the **ten** module injections already in the report - **10 detected, 0 missed, every restore byte-identical** - the corpus measurement is now shown to be re-derived rather than asserted, and the hand-off is shown not to be an orphan. The standing lesson re-earned for the fourth time in this project: *a checked task box is not evidence, and neither is a guard whose injection was never run.*

- **Last OpenSpec validation:** PASS - `asset-package-parameterisation` **at Archive** (2026-10-09): `openspec validate --all --strict` reports **73 passed, 0 failed**, composition re-measured as **73 main specs + 0 changes**, against Sync's **74 = 73 plus 1**. Archive ran with **`--skip-specs`** because Sync had already applied all three deltas; running it without that flag would have refused the two `ADDED` provenance-digest requirements as already existing, which is the normal post-Sync shape and not a defect. **The census spec was then amended in this same stage** (containment rather than a bare "not the repository root"), so **73 is 73 specs including that amendment**, and the change's delta carries the identical text.

- **Last OpenSpec validation, before this entry, retained in full:** PASS - `asset-package-parameterisation` **at Apply** (2026-10-09): `openspec validate --all --strict` reported **73 passed, 0 failed**, composition re-measured as **72 main specs + 1 active change**. The composition is recorded because the bare total alone never says which stage is done, and this change's own task 2.11 predicted "71 main specs + 1 change" - corrected there and here rather than left as a reproduced figure.

- **Last OpenSpec validation, before this entry, retained in full:** PASS - `2026-10-08-market-trade-counters-projection` **at Sync** (2026-10-08): `openspec validate --all --strict` reports **73 passed / 0 failed across 73 items**, and `openspec validate godot-market-trade-counters --strict` reports **valid**. **The composition is the claim, not the total**: **72 main specs plus 1 change** now, against **71 plus 1** during the change, and **72 plus 0** after the change is archived. Sync converts a change into a main spec, so the total moves by one at Sync and the change then leaves at Archive - **the number alone never says which stage is done.**

- **Last OpenSpec validation, before this entry, retained in full:** PASS - `darts` **at Archive** (2026-10-07): `openspec validate --all --strict` reports **67 passed / 0 failed across 67 items**, exit `0`. The count is explicable as a triple, so all three figures are recorded: **67** while the change was active at Apply, **68** at Sync once the new `godot-darts` capability spec was seeded, and **67** again at Archive once the change stopped counting as an item while its capability spec remained. `openspec validate godot-darts --strict` passes and emits only the repository's standing long-requirement INFO notices. Both main specs' SHA-256 digests were captured **before** the archive step and are **unchanged** after it, which is what proves `--skip-specs` did what it claims rather than being taken on trust.

- **Last OpenSpec validation, before this entry, retained in full:** PASS — `social-state` **at Archive** (2026-10-06): `openspec validate --all --strict` reports **66 passed / 0 failed across 66 items**, exit `0`. The count is explicable as a pair, so both figures are recorded: **67** after Sync once the new `godot-social-state` capability spec was seeded, and **66** at Archive once the change stopped counting as an item while its capability spec remained. All twelve requirements are present, the delta headers did not leak into the main spec, the Purpose is written rather than a placeholder, and the change never had a `.openspec.yaml`, so the archive moved all four artifacts and lost nothing.
- **Nine instrument faults were found and fixed in `godot-social-state`, all by self-checks or by the suite's own re-derivation rather than by inspection**, and the count is itself a finding: design **D2's** re-derivation guard earned its keep on the first real legacy edit it met. (1) `world_id` is a **map** key while `worldChange` is a **`privateState`** key, and the corpus search was map-only, so it reported one of the two. (2) A `bool` parameter is passed **by value** in GDScript, so a recursive search assigned `true` and the caller never saw it — both world keys measured as absent. (3) The comment/string-stripping lexer erases string literals, so every branch-**name** assertion was vacuous: `cmd == "set_resource_allies"` reads as `cmd == ""`. (4) The module's inner class was named the same as the preloaded script, so every static call resolved to the inner class. (5) `Projection` is a **built-in Godot type**. (6) An inner class cannot resolve an outer script's static by bare name. (7) `%` binds tighter than `+`, so a message split across two string literals formats only the second and one message raised *"not all arguments converted"* with its text lost silently. (8) `_has_arithmetic` iterated the `<`/`>` operator offsets — it scanned for *ordering* while looking for arithmetic, so it could never fire and its emptiness assertion was vacuously true. (9) `_field_table` read five columns through a three-column accessor, so the report could not be written. **Two corrections to committed figures are recorded rather than silently edited**: the zero-occurrence group is **12**, not the 13 the investigation and proposal claimed, because `questsRank` is read **and** written and the original census matched only the literal `privateState["x"]` form, missing an aliased-local write; the census now counts identifier tokens **and** quoted subscripts as two forms and sums them. D9's title was also wrong ("a reader and no writer") and was corrected.
- **Last verified commit:** `ab886f8` - the Apply merge for PR #339, over content `50912f4` and `aea262f`. The batteries above were run in the final state of that content, after which only `docs/DEVELOPMENT_ROADMAP.md` and the new main spec changed - both outside every battery's read surface, which is an **argument** and was therefore followed by re-running the full battery rather than being relied on.

- **Last verified commit, before this entry, retained in full:** `216ccb5` - the archive merge, over content `f95f069`. The batteries above were run in the final state on `5240bb6`, the Sync merge, which is the last state at which the implementation is byte-identical to `f9af80d` (the Apply merge); the archive changes no implementation, and the Sync hash is named here rather than this one only because a commit cannot record its own hash.

- **Last verified commit, before this entry, retained in full:** `bdbbf8f` — the archive merge. The batteries above were re-run in the final state on `aac3b39`/`bcdde95` (`488fee7` archive content), and the implementation-verification figures above are from that run.
- **Post-Sync regression, found by running the battery rather than assuming it still passed, and fixed in `fix/rewards-boundary-guard` (#308).** The entry above claims `verify-boot.ps1 exit 0`. That was true of the **pre-Sync** state; **the Sync stage itself broke it**, and nothing re-ran the battery afterwards, so the claim sat there asserting a pass the battery contradicted. Running it: `Ran 2921 tests … FAILED (failures=1)`, `verify-boot` exit **1**, failing its `compat unittest discovery exits 0` check. Root cause is **two** defects, one introduced by Sync and one pre-existing in the guard that caught it. **(a) Sync carried forbidden prose into a main spec:** `openspec/specs/godot-rewards/spec.md` said "a **weekly reward** operation succeeds", a role phrase rather than a key name, **inherited verbatim from the change's spec delta**, which carries the identical phrase. The reason it reached a main spec unchecked is itself a guard gap: **the guard scans `openspec/specs/` only**, so a delta may carry forbidden prose indefinitely without ever being inspected — the phrase is the recorded defect class exactly, prose describing behaviour by role and never by key name, which "has now failed twice". Fixed by naming the key the scenario is actually about (`the weekly operation on `weeklyRewardIndex` succeeds`), which is legitimate in the owning spec and is precisely what the guard's exemption exists to permit. **(b) The guard's owner exemption was dead code:** it skipped `capability == "rewards"`, but the delivered capability directory is `godot-rewards` and `openspec/specs/rewards` **does not exist**, so the exemption never fired. The guard was therefore not doing what its docstring said — it forbade the **owning** capability from naming its own cursor, instant, or command, while its message describes a *rival* claim; any rewards spec legitimately naming `weeklyRewardIndex` or `win_daily_bonus` would have been reported as another capability stealing the line. This never fired **because the file it was written to police did not exist yet**: this is the first line whose owner spec was created while the guard was already in the tree, so the guard had been **passing vacuously against its own target**. Fixed by deriving the exemption from a checked directory rather than a guessed name, so renaming the capability **fails the test** instead of silently disarming it. **Both properties then proven by injection**, not trusted: injecting the owner's own cursor key, stamp key, command name, and role phrase into the **owner's** spec leaves the guard **PASSING** (the exemption is live), while injecting the same text into **`godot-damage`** makes it **FAIL** naming `godot-damage` with three hits (the guard still fires, and was not over-broadened into neutering). Each injection asserted its text had actually landed before any result was read, and each restored byte-identically (`ABFC7FB267625F01D43D8CE5CA884E9D` and `CE6842C7E92A6974651358A45925BB58` either side). **Post-fix, actually re-run:** `verify-boot.ps1` **PASS**, exit **0**; **74** commands, **every one** `exit_code` **0**; **44** hermetic suites, **all** exit 0; **218** assertions all ok; guard digest `6978b9594f52b3f87ebe043b…` **identical pre and post**; **832** battery log files (416 `.out.txt` + 416 `.err.txt`) with **0** `^ERROR:`, **0** `SCRIPT ERROR`, **0** `[test] FAIL`; compat **`Ran 2921 tests … OK`**; `openspec validate --all --strict` **65 passed / 0 failed**; validator `valid`; hash manifest **3,258 entries**. **Five instrument faults of mine surfaced while diagnosing this**, all the standing *a counting script must be shown to count what it claims* lesson, and all recorded rather than quietly fixed: an injection that **never ran** (an inline `python -c` line-continuation error) after which I read the guard's **PASS** as if it had — a passing guard after an injection that did not happen is worse than no result, because it looks like evidence; a `git checkout --` restore, which restores from **HEAD** and silently discarded the **uncommitted** prose fix while leaving the guard fix intact; a report check that read key `exit` when the field is `exit_code`, making "0 commands failed" **vacuously true**; a type-sensitive `exit_code == '0'` compare against **int** codes, which reported 44 failures that did not exist; and a log sweep filtered on `*.out.txt` that covered **416 of 832** files, so the first "0 errors" claim covered **half the logs**.
- **M10 last verified commit, superseded by the entry above:** `2b19d73` — the review-fix merge, and the commit on which the batteries above were re-run in the final state. The lifecycle then continued through the Sync merge `aed98ee` and this archive, neither of which changes implementation.
- **M10 exit re-measurement (orchestrator-run, 2026-10-06, for the exit verdict above):** over the **eleven** top-level legacy modules, counting **whole-identifier tokens with comments and string literals stripped** — not substrings, because `end_attack`, `attacker`, `attacker_units` and `flash_reload_attack` all contain *attack* without being the committed field — **all 7 of 7** combat fields have **zero** code-only consumers: `attack`, `defense`, `life`, `attack_interval`, `attack_range`, `best_against`, `best_against_mult`. (`attack`'s **12** whole-file hits are every one inside a longer identifier, and the other six have **no** occurrence in any view.) And there is **nowhere to store a hit point**: across **231** map documents and **58,336** placed rows, the placed-row length is **exactly 8 in every single case**, and **zero** of the **47** distinct `privateState` keys contains a whole `hp`/`hit`/`health`/`damage`/`wound`/`life`/`armor` segment. So the exit criterion "Primary combat loop works" is **NOT MET and is not satisfiable from this oracle** — a combat loop needs a rule to reproduce and somewhere to keep a remaining hit point, and the preserved server has **neither**. **Two instrument faults of mine were found and fixed while measuring this, and both are the standing lesson re-earned**: my corpus walk assumed `items` was a list, but it is a **dict keyed by the row key as a string**, so iterating it yielded key *strings* and the probe reported a confident **"0 placed rows"** — the identical failure mode the `damage` line recorded, in a different shape; and my first hit-point search was a case-insensitive substring, which matched researc**hIt**emNumber. Both were fixed before the numbers above were recorded, and the figures above are from the **corrected** probe.
- **Last updated:** 2026-10-10 (**M12 `FILL_GRADIENTS` measurement, committed on `docs/m12-fill-gradient-measurement`** - investigation only, **no line proposed**, no conversion attempted, **no production code changed**). The objective the per-shape trace named as next eligible is now measured: per-ratio offsets, and the offset the reader believes it is at when the fill style returns to the shape's own byte stream. The reading it found is that after a gradient `FILLSTYLE` the reader resumes where the following line count is unsatisfiable inside the tag in **86 of 87** cases against **1 of 5** for solid at the same stage, and that **no gradient fill in the entire committed corpus ever parses** - 129 blocks across 124 targets, none in the 290 that convert. It also **refuted** the tempting reading that the block overruns its tag: it is 2 to 314 bytes short of that in every case. The specification was not consulted on purpose. Five controls pass, including a planted payload checked before any population figure was read and a tag-extent oracle that independently reproduces the previous stage's **4347** shapes. Five instrument faults are committed with it, the first being a reduction that selected each target's first shape instead of its failing one and produced a clean-looking but wrong split, and a sixth being a roadmap edit here that split on a delimiter the label does not contain and silently dropped the head of both entries it meant to retain. Neither open decision moved.
- **Last updated, before this entry, retained in full:** 2026-10-10 (**M12 per-shape trace of the desync family, committed on `docs/m12-shape-trace`** - investigation only, **no line proposed**, no production code touched). It does the one thing `docs/legacy-m12-desync-downstream.md` named as the next eligible objective: it partitions the **118 untouched** targets by **where inside a shape the walk first diverges**, which `target_census.json` cannot support because every family target records `problem_count` exactly 1. The **118 are three groups**: **87** declare a **gradient** fill type as read and stop in the LineStyleArray, **5** are solid, **25** stop inside the FillStyleArray across four classes, **1** fails inline. The located defect is a **solid** colour width confined to the `FILL_SOLID` branch and therefore **cannot reach the 87**. In those 87 the reader reaches the line count at the wrong offset: declared FILL count **1** for 91 of 92, declared LINE count over **46 distinct** values including **65535**, exceeding the styles entered for **89 of 92**. **Four controls pass** - **290 of 290** converted targets calibrated with **4347** shapes and no fabricated failure (independently reproducing the shipped shape count), **inertness 272 of 272**, **4 distinct** leaf stages, and the own-versus-mid-stream detector returning **both** values. **No cause is claimed for the 87**; a same-shaped expression in the `FILL_GRADIENTS` branch is recorded as the next place to **measure**, not as a fix. **Six instrument faults are committed with it**, including a vacuous detector that reported a clean uniform `True` for all 118 - the same class as C-4's favourable aggregate. **Two decisions remain open and are not pre-authorised:** mass-converting the 290 available packages, and revisiting the three scope-decision classes.
- **Last updated, before this entry, retained in full:** 2026-10-10 (**M12 desync-family downstream narrowing experiment, committed on `docs/m12-desync-narrowing`** - investigation only, **no line proposed**, no production code touched). It measures what `docs/legacy-m12-signed-rect.md` C-4 recorded as never measured, because the predecessor's probe routed all **272** family targets through the **building** converter and the **195** unit targets died at the content lookup before parsing. With routing delegated to the committed `census_targets.evaluate`, the located defect is shown to **cascade rather than exit**: `unknown fill style` 137 -> 26 while `shape byte overrun` 104 -> **187**, with **84** targets flowing straight from one into the other. Only **2** convert, reproducing C-3 by name, and **118 of 272** are **byte-identically untouched** by the patch - a negative result that bounds the defect's reach without locating another. A separate **null** result: the committed census is **current** over all **817** targets, though it records **no input digests** and so cannot prove that - the same dependency class as `asset_ids.json` hashing `conversions.json`, recorded as a gap and not fixed. **Four instrument faults are committed with it**: the reconciliation identity omitted the two converted targets' outflow (caught by a self-check, off by exactly 2); the flow table lacked an inequality filter, so hand-summing it gave **188** against the run's **187** and every aggregate was moved off the printout onto the records; the return-shape probe was one byte short so **both** parsers overran and the control **rejected** it rather than passing it; and a background run left a 0-byte stream, so the foreground run was used and two runs had to agree before either was believed. **The scope-decision classes are newly sized at 286 of 527** refused targets, and are domain-split, so the bitmap-fill policy cannot be symmetric.
- **Last updated, before this entry, retained in full:** 2026-10-10 (**M12 line 3 `rect-bounds-sign-extension` ARCHIVED** - the signed-`RECT` fix, delivered, verified, synced and archived through PRs #357, #358, #359, #360). Two capabilities modified and none created; **290 of 290** converted targets parse with **0 inverted rectangles** remaining from **2445 across 74 targets**; **D3's clamp was corrected in flight and retained**; the `rect_bytes` fixture repair is a spec-conformance fix with **no expected value edited**; `asset_ids.json` was regenerated because `build_asset_ids.py` records `conversions.json` as an input; and the Sync stage's own spacing census was **discarded as a defective instrument** - it `lstrip()`ed the newlines it was testing for and returned a clean 0/451 and 0/524 - then redone behind a planted control, which falsified the repo-convention assumption behind it. Thirteen recorded flaky surfaces remain open; the desync family still has no line; and mass conversion plus the three scope-decision classes remain **not pre-authorised**.
- **Last updated, before this entry, retained in full:** 2026-10-10 (**M12 RECT sign-extension defect LOCATED and FULLY IDENTIFIED - converter shown to fail OPEN, 74 of 290 converted targets and 2445 of 4347 shapes emitting negative extents, and the predecessor's end-to-end result CORRECTED from "0 of 272" to net 0 across all 817** - investigation `docs/legacy-m12-signed-rect.md`; five claims from `docs/legacy-m12-desync-origin.md` corrected or withdrawn after its end-to-end probe routed **195 unit** targets through the **building** converter, so they failed the content lookup before parsing; three test sites and one committed package would be affected by a fix, and no line is proposed on this entry).
- **Last updated, before this entry, retained in full:** 2026-10-09 (**M12 desync family origin PARTIALLY LOCATED, no line proposed** - investigation `docs/legacy-m12-desync-origin.md`; the family's precondition is verified clean at 272 of 272; one real defect located and sharply bounded (the solid fill colour is 3 bytes, not `4 if rgba else 3`, worth 138 of 272 against the committed rule's 9); **it converts 0 of 272** through a calibrated harness, so no line is proposed; five candidate origins falsified; an oracle defect corrected - the strict form ignored the byte-alignment padding after the 6-bit EndShapeRecord and reported 42 witnesses where the corrected form reports 95 - with eight recorded corrections C1-C8, three of them to my own instruments)
- **Last updated, before this entry, retained in full:** 2026-10-09 (**M12 refusal classes INVESTIGATED** - investigation `docs/legacy-m12-refusal-classes.md`, commit `3fa6040`; docs-only, and it lands on the **same PR** as the investigation, correcting the deviation recorded in the entry below). **Nine corrections, and the one that matters is a withdrawn recommendation.** The predecessor's `shape byte overrun` line is withdrawn on measurement: the real gradient FILLSTYLE defect converts **0 of 104** and relocates 66, and the `0xFFFF` sentinel count rises **6 -> 12**, so the fix moves the fault rather than removing it. **The withdrawal is recorded as such, not as a softened claim.** Two of the nine corrections were instrument faults that had already produced figures about the wrong population: C1 walked the tag stream from offset 0 and located 2 of 104 failures, and C4 counted every overrunning shape (**1,154**) instead of the first, so every denominator built on it was wrong. **A favourable aggregate from the wrong population would have supported the recommendation this document withdraws** - which is the finding worth carrying forward, larger than any single number in it. The other recorded classes: C5 omitted a path filter (**494** against the recorded **422**, the 72 extras being `assets/flash/Basesec_*.swf` UI builds), C7 named the label-vocabulary scope (**61** over the sprite scope against the predecessor's unqualified **10**, which is the labelled-**converted** scope - both correct, both now named), and C8 replaced a derived figure presented as a measured one. **C9 is a class the project has not seen before**: five defects found by *reading the finished draft*, which no probe could catch because none of them is a number - a mis-pointed cross-reference, a placeholder that survived into the prose, an **80** where the measured distinct count is **76**, a missing source-line citation, and one case where **verifying a citation strengthened the finding**: `TAG_REFUSED_SHAPE` was called "a named set" when it has exactly one member, making DefineShape4 the only shape tag the converter declines at all.

- **Last updated, before this entry, retained in full:** 2026-10-09 (**M12 FX / animation RE-SCOPE DECIDED** - investigation `docs/legacy-m12-fx-animation-rescope.md`, PR #353, merge `5061bb5`; docs-only, and it lands in its own PR rather than with the investigation, which is a deviation from the established pattern and is recorded below).

- **Last updated, before this entry, retained in full:** 2026-10-09 (**M12 line 2 `image-reference-resolution` ARCHIVED**; line 1 `asset-package-parameterisation` remains ARCHIVED). **What changed in the deliverable versus what the investigation predicted.** The investigation predicted a mechanism line, and that is what shipped, but three things it stated as settled were measured differently during Apply. **First, the corpus bijection does not hold over what the proposal implied.** `docs/legacy-image-reference-resolution.md` and the Risks section of the approved design both cited "573 refs -> 573 files, zero unreferenced" as the mitigation for path-first trusting a reference's directory, read as covering *every* reference the join identifies. Measured, it describes the **path-resolved tier specifically**: all **575** identified references name **573** files, because the 2 fallback references alias the `chapters2` files their correct-path counterparts already name. That is not a defect - the fallback exists to resolve a reference whose directory is wrong, and the only file for that wrong directory is the one already claimed - but it did mean the assertion as written would have asserted something false, so it was rewritten over the path-resolved tier with the 2 shared targets named. **The correction narrowed a claim rather than excusing a limit, and it is recorded in the change's own `design.md` as C1 with task 1.5 amended in place.** **Second, the rule needed three tiers and the spec needed four.** A reference can fail at its own path *and* match several files by basename; recording only path-resolved / fallback-resolved / missing would leave it in none of them and the tier counts would stop summing to the reference count, so `fallback_ambiguous` and `fallback_ambiguous_refs` are recorded too - both empty on the committed corpus, and additive to a requirement that specifies a minimum. **Third, one claim the delta itself made was wrong before it was synced**: the `godot-content-registry` scenario read "566 `passthrough` from a file identified by the reference's own path", which is wrong - 566 is **564 path-identified plus 2 fallback-identified**. A main spec is durable, so the delta was corrected in place before being applied rather than carried into the durable record. **The transferable lesson is about the harness, not the code.** All **11** injection probes were *initially* reported as "unproven", and none of them was: the harness detected failures with the **Godot** suite's line format so every Python probe read as unproven, it patched by **inserting** after a single-line anchor which duplicates the statement into a **parse error**, and it used a `pathlib` keyword that **does not exist on the pinned 3.9.13**. The parse-error point is the one worth keeping: **a probe whose only effect is that the file stops compiling has proved nothing about the guard it was written to test**, and a harness that counts a non-zero exit as a detection would have reported 11 confident false positives with a clean-looking restore table. **Next:** nothing is pre-authorised. The three open decisions are the FX/animation re-scope, whether the 8 refusal class-domains get their own investigations, and whether to mass-convert the 290 available packages.

- **Last updated, before this entry, retained in full:** 2026-10-09 (**M12 line 2 INVESTIGATION committed** - `docs/legacy-image-reference-resolution.md`; line 1 `asset-package-parameterisation` remains ARCHIVED). **What the line found, in one line: the 50 `ambiguous` references are a broken rule and the 32 `missing_source` references are a content gap, and conflating them would have produced the wrong deliverable.** The registry resolves image references by **basename**, throwing away the directory that the reference already carries, so `/goals/1.png` and `/packs/1.png` are reported as interchangeable when their files differ by an order of magnitude; joining the reference's own path resolves all 50 with zero disagreement against the 523 entries that already work and maps the corpus **bijectively**, 573 refs to 573 files with none unreferenced. The 32 are absent outright - a corpus-wide search under every extension finds nothing - so no amount of resolver work will ever close them, and a proposal that claimed to would be promising something the oracle cannot deliver. **The transferable lesson is the shape of the second correction.** The appendix script shipped a comparison written as `runtime in (joined, source)`, which asks whether *runtime* equals either value rather than whether *either runtime or source* equals the join; run verbatim it printed **514/9** against the document's **523/0**. The finding was right and the *test* was wrong, and nothing but executing it distinguished the two. **A reproducibility appendix that has never been run is a second source of truth, not a safeguard** - and this project has now produced that failure twice in three investigations, the other being a path join missing its separator. **Next:** propose `godot-image-reference-resolution` as a mechanism line with an explicit basename fallback, and leave the 32 absent images to a product decision rather than an OpenSpec change.

- **Last updated, before this entry, retained in full:** 2026-10-09 (**`asset-package-parameterisation` ARCHIVED**, M12's first deliver line). New capability `asset-package-census` (**3 requirements**, **10 scenarios**), **two modified**: `first-building-conversion` (**6 / 14**) and `first-unit-conversion` (**9 / 22**). **What this line actually established:** the tooling was only half of M12's problem. Parameterising both converters made it possible to ask how much of the corpus is convertible at all, and the answer is **290 of 817** - **290 packages exist today and 527 targets are refused over 8 disjoint classes**. **That measurement was worth more than the parameterisation**, because the refused majority is now a named, re-runnable measurement instead of an assumption that a tool generalised because it ran without error once. **No refusal class was fixed and no mass conversion was performed**, both recorded as follow-ups; the 290 available packages are roughly 15,000 files and a preservation-manifest regeneration, which is a separate line with its own measured diff. **M12's exit criterion was already MET when this line opened** - the client has no runtime SWF dependency - so the milestone's remaining value is entirely in the deliver items, and this line closed one of them. **The verification finding worth carrying forward is the shape of the check, not the bug:** the containment guard was `out_root == repo_root` where the requirement said "beneath", and the gap was invisible because proving it requires writing into the repository - which is exactly what a read-only verification pass must not do. **Naming a guard by the property it enforces is not the same as enforcing it**, and this line had already been bitten by a claim of the same kind (`guard_baseline.py` read as hashing raw bytes when it normalises line endings). **Next:** `godot-image-reference-resolution` (50 `ambiguous` + 32 `missing_source` asset references), the FX/animation re-scope decision, and the two open M12 decisions - whether the eight refusal class-domains get investigation lines, and whether to mass-convert the 290 available packages.

- **Last updated, before this entry, retained in full:** 2026-10-08 (**`market-trade-counters-projection` ARCHIVED - M11 CLOSED**, and its post-Sync LF defect fixed in between). New capability `godot-market-trade-counters` (**7 requirements**, **20 scenarios**), **none modified**. **M11 is complete: six deliver lines, all archived, exit criterion assessed MET**, and there is no active OpenSpec change. **What the milestone found, and it is the thing not to lose:** six lines, six read-only projections, **zero routes and zero executed-legacy fixtures**. Every legacy branch M11 touched had either no request path, an unvalidated client-sent grant, or committed content nothing anywhere reads - the social and special systems lived almost entirely in the **Flash client**, and **absence of a server rule says nothing about what that client displayed**, so being projection-only is a measurement and not a shortfall. **A defect was found after Sync and fixed on its own branch before Archive,** which is the correct order and is recorded as such: the suite required both delivered modules to be pure LF, but `core.autocrlf=true` with no `.gitattributes` rule means a default Windows checkout delivers CRLF - and **the committed `boot-report.json` on `main` already recorded the red run** (`"pass": false`, `test_market_trade exits 0 (got 1)`), so the artifact shipped was reporting a failure nobody had read. **That is the third recorded instance of the same defect class** - a property of **how a file arrived** mistaken for a property of **what was delivered** - and **a checkout form is never a delivery guarantee**. Two changes fixed it, because they fix different failures: the check now records an LF-normalised digest per module and asserts **only checkout-independent facts**, with the equality made non-tautological by two independent computations; and `.gitattributes` pins the three paths to LF so the **committed report's digests reproduce on any checkout**. Proof: **1005 checks and exit 0 on an LF tree and on a CRLF tree**, the second being precisely the case that failed on `main`. **Also recorded: two more flaky surfaces** (a `test_town_upgrade` access violation and a `test_game_api_live.gd` second-boundary clock race), both on suites the fix does not touch and both cleared by a re-run. **Before this entry:** 2026-10-08 (`market-trade-counters-projection` APPLIED, VERIFIED and SYNCED - M11's sixth and fi

- **Last updated, before this entry, retained in full:** **`market-trade-counters-projection` APPLIED, VERIFIED and SYNCED** - M11's sixth and final deliver line, `special mechanics`). New capability `godot-market-trade-counters` (**7 requirements**, **20 scenarios**), and **no existing spec amended**. **The promoted surface displaced the investigation's own rank #1**, because the atom-fusion queue is already owned by `godot-unit-queues` under its archived decision D6 and two owners of one surface is a boundary nobody enforces. **No route, no live phase, no executed-legacy fixture, no compat-API change** - four decisions with measured reasons. **The finding: M11 has no transaction to deliver.** The cap is the branch literal `20` and is **stored but never enforced**, since `numTradesDone`'s only reader is its own increment; the branch **stores the count clamped while printing remaining-trades unclamped**, so that figure is negative from the 21st trade onward and is **reproduced rather than corrected**; and **8 of 10** committed documents record a zero last-trade instant, making the day-reset predicate unconditionally true and the cap reachable in the corpus in `Nerri.json` only. **Three corrections to this line's own work**, each recorded with its cause: a hard-coded evidence flag that was wrong because it described the checkout rather than the files it was named for; `String(PackedByteArray)`, which does not exist on this engine and so failed at *parse* time rather than as a check; and a purity test comparing a hex digest against un-hashed bytes, which pointed at a correct file. Plus one **disclosure**: the injection block was a transcribed record of an external harness run presented as live evidence, and an earlier review read it that way. **All nine probes were then re-measured against the final bytes** - `6, 4, 7, 27, 8, 2, 2, 3, 4` against the recorded **63**, no count moved. **Sync found one defect of its own**: dropping the delta's `## ADDED Requirements` wrapper also dropped the `## Requirements` header a main spec requires, caught by strict validation rather than by reading. **M11's exit criterion is assessed MET**, with the honest reading stated: every relevant system this oracle can see is classified, four are projected, and the rest are refused with the reason measured.

- **Last updated, before this entry, retained in full:** 2026-10-07 (**`darts` ARCHIVED** - M11's second deliver line, on a milestone opened the previous day). New capability `godot-darts` (**12 requirements**, **18 scenarios**), and `godot-social-state` **modified** by two requirements replaced in place. **The finding: a committed price with zero consumers** - `get_premium_days` returns the duration and never reads the amount beside it (`get_game_config.py:181-189`), so nothing is charged, and that is a **refusal, not parity**, because `engine.apply_resources` (`engine.py:251-271`) applies a **client-sent** eight-slot vector before the dispatcher chain opens at `command.py:42`. Two invented rules were **refused**, each with a corpus fact behind it: the shot list stays **unbounded** and the shot index is never schedule-tested, because `villages/Nerri.json` records shot index `0`, absent from the committed `1..27` ids. **No executed-legacy fixture exists and none is claimed**, which is stronger than the usual corpus limitation: the corpus carries every darts field at its initial value and **no committed document records a future premium instant**, so the extend arm is exercisable only over crafted input. Also recorded: **two committed-figure corrections** made by the Apply stage (**C3**, the corpus denominator is **33** canonical documents, not the 231 the investigation reported, because 200+ of those are generated `tests/fixtures/**` `before.json`/`after.json` pairs; **C4**, `dartsGotExtra` is `false` in **33 of 33**, which is why the client-dictated `won_extra` refusal has no corpus evidence at all); **two task-box problems** found at Archive and corrected rather than ticked (**C5**, a verification command for a suite that does not exist; **C6**, a "manifest" that does not exist because there is no fixture); **two task-mandated injections run rather than ticked**, two failures each with byte-identical restores; **a cross-line route-placement fragility found and fixed at the source**, which broke eight guards across four earlier lines and is now a pinned property proven by injection with four independent detections, leaving the four `markers[-1]` invariants untouched; **ten module injections, ten detected, none missed**, one of which borrowed **no reserved word at all** and was caught only by the whole-inventory pin, which is what makes the pin the gate and the reserved-name guard the belt; and **no `darts-live` phase**, recorded as the finding rather than omitted, because a client able to fire `darts_shoot_balloon` is precisely the surface this line exists to refuse. M11's exit criterion is **NOT MET** and remains **unfinished**: `visits` and `scores` are rejected by measurement, `friends` and `social rewards` are unexamined, and `legacy event systems` / `special mechanics` are partial. **Before this entry:** 2026-10-06 (**`social-state` ARCHIVED** — M11's first deliver line, on a milestone opened the same day). New capability `godot-social-state` (**12 requirements**). **The finding: social content has zero consumers and social state exists but is never written**, and **one** branch — `set_resource_allies` (`command.py:637`) — is the only real social writer, taking its value from a client-sent argument; it is recorded verbatim and **not reproduced**, and **no endpoint was delivered**. M11's exit criterion is **NOT MET**, and unlike M10's this is **unfinished rather than unsatisfiable**: **5 of 6** deliver items have not been examined at all. `visits` and `scores` were already checked and **rejected** by measurement, so the next line is selected by elimination. Also recorded: **nine instrument faults** in this line's own suite, all caught by self-checks rather than inspection; **four task-box problems** found by checking the boxes against the code instead of trusting them; and **six injections**, one of which borrowed no reserved word and was caught **only** by the operator guards, which is what makes those guards non-redundant rather than decorative. **Before this entry:** 2026-10-06 (`rewards` ARCHIVED — M10's seventh and last deliver item, which **completes M10's deliver list**). New capability `godot-rewards` (**9 requirements**). **The finding: both reward branches are real granting surfaces rather than closures, and neither cursor can address the whole of the schedule it would address — for two different reasons.** M10 opened by measuring two of its own deliver items out of existence and closed by measuring **four** of seven that way, leaving **three** delivered and archived. **The exit criterion is NOT MET and cannot be**, which is a different statement from unfinished and is the honest verdict: there is no combat loop in the preserved server to make work. Also recorded: **the client agent merged its own Apply PR without the review gate**, which produced the correct end state but skipped a check the workflow requires — the review then found **three defects in that line's own delivered client half**, all in the recorded *check fires on its own prose* class, so the gate demonstrably earns its keep rather than being ceremonial.

- **Last updated, before this entry, retained in full:** 2026-10-06 (**`social-state` ARCHIVED** — M11's first deliver line, on a milestone opened the same day). New capability `godot-social-state` (**12 requirements**). **The finding: social content has zero consumers and social state exists but is never written**, and **one** branch — `set_resource_allies` (`command.py:637`) — is the only real social writer, taking its value from a client-sent argument; it is recorded verbatim and **not reproduced**, and **no endpoint was delivered**. M11's exit criterion is **NOT MET**, and unlike M10's this is **unfinished rather than unsatisfiable**: **5 of 6** deliver items have not been examined at all. `visits` and `scores` were already checked and **rejected** by measurement, so the next line is selected by elimination. Also recorded: **nine instrument faults** in this line's own suite, all caught by self-checks rather than inspection; **four task-box problems** found by checking the boxes against the code instead of trusting them; and **six injections**, one of which borrowed no reserved word and was caught **only** by the operator guards, which is what makes those guards non-redundant rather than decorative. **Before this entry:** 2026-10-06 (`rewards` ARCHIVED — M10's seventh and last deliver item, which **completes M10's deliver list**). New capability `godot-rewards` (**9 requirements**). **The finding: both reward branches are real granting surfaces rather than closures, and neither cursor can address the whole of the schedule it would address — for two different reasons.** M10 opened by measuring two of its own deliver items out of existence and closed by measuring **four** of seven that way, leaving **three** delivered and archived. **The exit criterion is NOT MET and cannot be**, which is a different statement from unfinished and is the honest verdict: there is no combat loop in the preserved server to make work. Also recorded: **the client agent merged its own Apply PR without the review gate**, which produced the correct end state but skipped a check the workflow requires — the review then found **three defects in that line's own delivered client half**, all in the recorded *check fires on its own prose* class, so the gate demonstrably earns its keep rather than being ceremonial.
### Resume point (updated after the FILL_GRADIENTS branch was measured at the offsets it reads, orchestrator)

The measurement landed, and it bracketed the divergence without explaining it.

1. **Read `docs/legacy-m12-fill-gradient-measurement.md` first, and its section 10 before trusting any instrument claim in it.** Five faults are recorded there; the first is the one to carry forward.
2. **The finding: after a gradient `FILLSTYLE` the reader resumes where the line count is unsatisfiable inside its own tag, 86 of 87.** The test needs no format reading - a line style is at least five bytes and the tag extent comes from the SWF tag header, which the parser never sees.
3. **The control group is the solid fills, not an opinion about the format.** The same measurement at the identical failure stage over the 5 solid cases finds 1, and that one is a mid-stream `NewStyles` block the predecessor had already recorded as not the shape's own array.
4. **The obvious reading is REFUTED and must not be carried forward.** The gradient block does not overrun or consume its tag: its span is smaller than the bytes remaining in **87 of 87** cases, by 2 to 314 bytes. It stops in the wrong place, not off the end of anything.
5. **Leaving the reader mid-byte is not a defect.** 62 of 87 exit unaligned, because `parse_matrix` is bit-oriented and legitimately ends mid-byte. This looked like a signal and is not one.
6. **No gradient fill anywhere in the committed corpus ever parses.** 129 blocks in 124 targets, every one the first fill in its shape, and none in any of the 290 targets that convert. The branch therefore has no successful instance and cannot be calibrated by one.
7. **The `0x13` focal branch is UNMEASURED, not clean.** No `0x13` type byte is read anywhere in the population, so the branch that reads two focal bytes on the fill type rather than on a flag bit is entirely unexercised. Do not read the silence as a result.
8. **The next eligible objective is bounded and named: compare the measured layout against the documented SWF `FILLSTYLE` gradient layout, one field at a time, and record which field the measured offsets contradict.** That is a diagnosis step and was deliberately not begun. No proposal may be written from this measurement alone.
9. **Do not propose a desync-family line.** Unchanged: 2 of 272 convert, net 0 across all 817. Repairing the gradient branch would reach the 124 targets that read one, and whether that converts anything is untested and is not estimated.
10. **The census still records no input digests, and still cannot prove it is current.** Unchanged by this stage, which touched no production code.
11. **Two decisions remain open and are NOT pre-authorised:** mass-converting the 290 available packages, and revisiting the three scope-decision classes.
12. **The lesson that re-earned itself here is about shape selection.** The first reduction took each target's first shape rather than its failing one and produced a confident, tidy, wrong split of 1 gradient / 18 solid / 73 other. Every figure in the committed document comes from the corrected reduction, and the wrong run was discarded rather than reported. A tidy aggregate from a check pointed at the wrong unit is the same defect class as the vacuous detector.
13. **The second lesson is that a script reporting success is not a verification.** This roadmap's own edit split its retained entries on a delimiter the label does not contain, and then produced a doubled entry, and each time the script's own check passed. Both were caught by reading the diff. Verify the artefact, not the edit that made it.
14. **Two harness events interrupted the population runs** - a tool timeout and a server restart - and neither produced a partial file, because the instrument writes its document only at the end. Both were restarted and both exited 0.
15. **Thirteen recorded flaky surfaces remain open**, and nothing in this investigation fixed any of them. Two stale M11 `Current milestone` entries remain pre-existing and out of scope.


### Resume point (updated after the untouched 118 were partitioned by where they diverge, orchestrator)

The trace landed and it gave "not one defect" a measured shape.

1. **Read `docs/legacy-m12-shape-trace.md` first, and its section 9 before trusting any instrument claim in it.** Six faults of its own are recorded there; the third is the one to carry forward.
2. **The 118 untouched are three groups, not one.** **87** declare a **gradient** fill type as read (`0x12` radial 57, `0x10` linear 30) and stop in the LineStyleArray; **5** are `0x00` solid; **25** stop inside the FillStyleArray across four different classes; **1** fails on an inline read. Identity 92 + 25 + 1 = 118, and 106 unit / 12 building reproduces exactly.
3. **The located defect cannot reach the 87, and that is structural rather than incidental.** It is a *solid* colour width in the `FILL_SOLID` branch; the gradients are in the `FILL_GRADIENTS` branch. The 2 converts were never going to be more.
4. **In the 87 the reader is at the wrong offset when it reads the line count.** Declared FILL count is **1** for 91 of 92; declared LINE count takes **46 distinct** values including **65535** and exceeds the styles actually entered for **89 of 92**; a LINESTYLE is at least 5 bytes, so 65535 was never satisfiable.
5. **Do not read the same-shaped expression as a fix.** The `FILL_GRADIENTS` branch contains `reader.read_bytes(4 if rgba else 3, label)` in its per-ratio loop — textually the form located as defective in the solid branch. It is recorded as the **next place to measure** and nothing more. The located defect converts 2 of 272 and net 0 across all 817; that is the standing precedent.
6. **The next eligible objective is a measurement of the `FILL_GRADIENTS` branch** — per-ratio offsets, and the offset the reader believes it is at on return to the shape's own byte stream. **Not** a line, and **not** another grammar enumeration. No proposal may be written from a same-shaped expression.
7. **Do not propose a desync-family line.** Unchanged: 2 of 272 convert, net 0 across all 817.
8. **The census still records no input digests, and still cannot prove it is current.** Unchanged by this stage, which added a trace beside the census and touched neither it nor any production code.
9. **Two decisions remain open and are NOT pre-authorised:** mass-converting the 290 available packages, and revisiting the three scope-decision classes.
10. **The lesson that re-earned itself here is about a vacuous check.** The own-versus-mid-stream detector tested `depth > 1` while the shape's own `parse_fill_style` is already at depth 2, so it returned a clean, uniform, confident **True for all 118** and separated nothing. A tidy aggregate from a check that cannot discriminate is worse than a failure, because it looks like a finding — and this is now the **second** recorded instance of that class, after C-4's 1,154 "failing shapes". The instrument was only accepted after a planted control showed both values occur.
11. **Thirteen recorded flaky surfaces remain open**, and nothing in this investigation fixed any of them. Two stale M11 `Current milestone` entries remain pre-existing and out of scope.

### Resume point, before this entry, retained in full (updated after the desync family's downstream was measured, orchestrator)

The narrowing experiment landed and it changed the **kind** of next step rather than opening a line.

1. **Read `docs/legacy-m12-desync-downstream.md` first, and its section 8 before trusting any figure from its predecessors.** It measures what `docs/legacy-m12-signed-rect.md` C-4 recorded as never measured, and it commits four instrument faults of its own.
2. **The committed census is current — measured, not assumed.** `tools/asset-registry/target_census.json` was last written at `2d51b61`, and both `convert_building.py` and its recorded input `asset_ids.json` changed afterwards at `8961f8c`, so it describes a parser no longer in the tree. Re-measuring all **817** targets with the shipped parser returns **identical** verdicts and **identical** refusal classes: **0** moves in either direction, calibration **290 of 290**, family still **272** (77 building / 195 unit). The whole family's recorded baseline stands and needs no re-baselining.
3. **But the census cannot prove that, and this is a recorded gap.** It stores **no input digests** and no tool revision — its keys are `counts`, `policy`, `refusal_class_totals`, `refused_targets_in_several_classes`, `result`, `schema_version`, `targets`. It is current by luck, because the signed-RECT fix changed recorded *values* for targets that already converted and never moved a verdict. A parser change that shifted one target across the boundary would leave it silently wrong with nothing to detect it. **Recorded, not fixed here** — this investigation owns no production code. It is the same dependency class as `asset_ids.json` hashing `conversions.json`.
4. **The located defect cascades; it does not exit.** Under correct per-domain routing the corrected layout moves `unknown fill style` **137 → 26** but moves `shape byte overrun` **104 → 187**, with **84** targets flowing directly from the first into the second. Only **8** of 272 ever reach asset resolution. **Do not plan from "the blocker lies downstream of the parse"** — that reading was already withdrawn by C-4, and this measurement contradicts it for the dominant mass.
5. **The family is not one defect, and this is the result that constrains everything later.** **118 of 272** targets are **byte-identically untouched** by the located layout — same refusal class *and* same recorded `problems` list, which for this family is its whole verdict. Of the **239** still inside the four-class family, **118 do not move and 121 do**. Any attempt aimed at the 118 cannot reuse the located defect, and "not one defect" is a statement about that defect's *reach*, not a claim that there are exactly two causes.
6. **Do not propose a desync-family line.** It converts **2 of 272** (`1076_robo_soldier_m` and `1155_dwarf_soldier`, both unit targets — an independent reproduction of C-3, not a discovery) and **net 0** across all **817** candidates.
7. **The next eligible objective is a per-shape trace — not a line, and not another grammar enumeration.** **All 272 family targets record `problem_count` exactly 1.** The census captures a target's first refusal and stops, so it carries no information about how far the walk got, where inside the shape the parse diverged, or how many bytes were left unconsumed. Some non-family targets *do* record several (one building records 5), so the field is meaningful and the family's uniform 1 is itself the finding. What a next step needs is a trace recording the **entry bit position** of the first divergence, so the untouched 118 can be partitioned by *where* they desync rather than lumped into one class.
8. **The scope-decision classes are newly sized, and they are domain-split.** The three classes govern **286 of 527** refused targets (**54%**) once the located defect is corrected: **31** inside the family that were previously masked behind its earlier refusal, plus **255** outside it. `unresolvable bitmap fill` is **100% building** (141 of 141) and PlaceObject# is **100% unit** (70 of 70), so the bitmap-fill policy can only ever affect buildings and cannot be a symmetric decision. These are **inputs** to the open decisions, **not** a recommendation, and nothing here pre-authorises any of the three.
9. **Two decisions remain open and are NOT pre-authorised:** mass-converting the 290 available packages (roughly 15,000 files plus preservation-manifest regeneration, its own line with its own measured diff), and revisiting the three scope-decision classes (DefineShape4, PlaceObject3, bitmap-fill policy).
10. **Two habits this stage extended, and the second is about an instrument.** A reconciliation identity that counts only target pairs refused in *both* runs is wrong by exactly the number that **convert** — count the escape as an outflow from its baseline class, and write the check before you believe the table. And a control that compares two parsers on a payload **both** of them reject has measured nothing: this stage's return-shape probe was one byte short, made both parsers overrun, and the control **rejected** it rather than passing it — which is precisely why it was worth writing.
11. **Thirteen recorded flaky surfaces remain open**, and nothing in this investigation fixed any of them — it changed no production code and converted no target. Two stale M11 `Current milestone` entries remain pre-existing and out of scope.

### Resume point, before this entry, retained in full (updated after M12 line 3 was archived, orchestrator)

The signed-`RECT` line is closed. What it established is narrower than the class it repaired, so the next move is a narrowing experiment rather than another delivery.

1. **Read `docs/legacy-m12-signed-rect.md` section 10, "As landed", first.** It records what shipped against what was proposed, including the **D3 correction**: the clamp is **retained** because `xmin=-118, xmax=-71` is correctly ordered yet floors to `-4`, so unclamping would emit negative pixel sizes. Do not "fix" the clamp.
2. **The population figures are re-runnable, not remembered.** `C:\Users\Edison\AppData\Local\Temp\opencode\verify_shipped.py` imports the shipped parser as committed and routes per domain: **290 of 290 targets, 4347 shapes, 0 inverted (from 2445 across 74 targets), 0 new-guard refusals, 0 negative sizes**, with per-field moves `xmin` 1987, `ymin` 1597, `xmax` 10, `ymax` 22, `width_px` 10, `height_px` 22. Re-run it before quoting any of them.
3. **`conversions.json` has a dependent artifact.** `build_asset_ids.py` records it as an input, so **any** change to `conversions.json` requires regenerating `asset_ids.json` or the full unittest discovery fails. This was omitted from the proposal's Impact and was found by the failure rather than by review.
4. **The desync family still carries no line.** It is underdetermined in 5 of 6 parameters and converts **net 0** across all 817 candidates (3 gains, 3 losses). The next eligible objective is a **narrowing experiment** that constrains a parameter, not another investigation of the same class.
5. **Two decisions remain open and are NOT pre-authorised:** mass-converting the 290 available packages (roughly 15,000 files plus preservation-manifest regeneration), and revisiting the three scope-decision classes (DefineShape4, PlaceObject3, bitmap-fill policy). Both need an explicit go-ahead.
6. **Two habits this milestone paid for, and one of them is about an instrument.** A refusal class present identically in the patched and unpatched runs cannot have been caused by the patch - that single check would have caught this stage's first `ab_tests.py`, whose "baseline" always installed the signed parser. And a census that returns a clean zero is suspect until it has seen a file where it must return non-zero: the Sync stage's spacing census `lstrip()`ed the very newlines it was testing for and reported 0/451 and 0/524, and a planted control then failed a **second** time because the regex stopped before end-of-line. Both were **discarded, not reported as findings**. The third fault worth naming is variants-in-one-process leaking state (70 against 81 for the same code), which is why the A/B was finally run with **one process per variant**.
7. **Thirteen recorded flaky surfaces remain open**, and nothing in this line fixed any of them. Two stale M11 `Current milestone` entries at roadmap lines 54-55 are pre-existing and out of scope.
### Resume point, before this entry, retained in full (updated after M12's RECT defect was located, orchestrator)

The desync-family investigation landed and then had to be corrected, and the correction found something better than what it replaced.

1. **Read `docs/legacy-m12-signed-rect.md` first.** Its section 2 withdraws five claims from `docs/legacy-m12-desync-origin.md`. The cause is an instrument fault, not a wrong theory: the end-to-end probe called the **building** converter for all **272** desync targets, but the set splits **77 building / 195 unit**, so the unit targets failed the building content lookup with `content ref not unique ... : 0` **before parsing**. With correct per-domain routing the located layout converts **2 of 272**, and across **all 817** candidates it is **net 0** (3 gained, 3 lost, all six stable across 3 repeats in each phase). The three losses are **wrongly-passing targets**, not regressions - they emit negative-width geometry today.
2. **The desync family stays open and unproposed.** It is underdetermined in 5 of 6 parameters and converts net zero. Do not re-derive a layout from the class name; section 3.2 of the refusal-class document is the standing proof that a plausible fix here can convert nothing.
3. **The real finding is that the converter FAILS OPEN.** `parse_rect_bits` reads the four RECT fields as unsigned where the spec says **SB**. **74 of 290** converted targets and **2445 of 4347** shapes emit negative extents, and sign extension **alone** repairs **2445 of 2445** with **0 failures** while the independent D2 defect is held fixed. Nothing that reported counts ever saw this, because the failures are in the output, not in the verdict.
4. **The next eligible objective is a `fix/` line on `parse_rect_bits`**, not another investigation. Its scope: sign extension (D1), fail closed instead of `max(0, ...)` (D3), amend `test_convert_building.py:240-241`, `:464-465` and `test_convert_unit.py:268-269`, and regenerate `assets/converted/units/10033_wild_elephant/package.json` - the only committed package affected. D2 (`width_px` from the far edge, **3452 of 4347** shapes) is separable.
5. **Two habits this stage paid for.** A class present identically in the patched and unpatched runs cannot have been caused by the patch - that single check would have caught the routing fault immediately. And a reported zero from a broken instrument is the most dangerous shape a measurement can take: two D2 attempts were vacuous at once, one comparing the recorded value against **the very expression the code uses**.
6. **Not pre-authorised:** mass-converting the 290 available packages, and revisiting the three scope-decision classes (DefineShape4, PlaceObject3, bitmap-fill policy). **The content-reference / asset-resolution path must not be planned from the current ledger** - that plan rested on the withdrawn section 8 and has never been measured.
### Resume point, before this entry, retained in full (updated after M12's desync-family origin was partially located, orchestrator)

Read `docs/legacy-m12-desync-origin.md` before starting anything on M12. It
answers the question PR #355 left open - where the 272-target desync family
begins - and the answer is deliberately partial.

**What is settled.** The family's inputs are clean: payload slices, tags and
declared lengths all verify 272 of 272, so nothing is wrong with the bytes. One
real defect is located in `parse_fill_style`: the solid branch's colour width.
It is a single expression and it is worth 138 of 272 payloads parsing exactly
against the committed rule's 9.

**What is not settled, and why it blocks.** That defect converts **0 of 272**
end to end. Measured through the real `build_package`, with a harness proved
able to report a success (10 of 10 known-converted targets) and a parser return
shape audited against the committed key set. Refusals relocate; the total does
not move. **So there is no deliver line here, and proposing one would be a
line that changes no outcome.**

**The next investigation, when it is authorised.** At least one defect remains
**downstream of the parse**, on the content-reference and asset-resolution
path. The evidence for it is already in hand: after the located fix, 130
targets stop refusing with `unknown fill style` and land in refusals that are
not parse failures, and two classes that were previously hidden surface on
their own (`unresolvable bitmap fill` 0 -> 8, `unsupported shape tag` 0 -> 2).
Start from those 130 and from the downstream path they now reach. Do **not**
start from the grammar: it has now been searched exhaustively and five
candidate origins are falsified against a corrected oracle.

**Standing instructions for whoever picks this up.**

1. **Exact consumption is necessary, nowhere near sufficient.** PR #355
   established this with the gradient field order (a correct fix that converted
   0 of 104) and this stage established it again from the other direction (a
   parse that consumes 138 of 272 exactly and converts 0). Always measure the
   real conversion path, never the parse.
2. **Calibrate every harness against a known success before trusting a zero.**
   The first end-to-end run here reported a brand-new refusal class for 173
   targets; that class was the probe's own wrong return key, and the zero it
   produced would have been reported as a finding.
3. **A payload ends with a 6-bit `EndShapeRecord` plus byte-alignment padding.**
   An oracle demanding an exact landing at `payload_len * 8` rejects the
   correct parses. This cost 53 of 95 witnesses and invalidated four
   falsifications made against it.
4. **Underdetermined is not identified.** The located layout is free in its
   focal-point width (138 at 0, 2 and 10 bytes) and weak in four others. A
   layout the data cannot pin down is not a result, however well it scores.
5. **A measurement whose instrument is defective is discarded, not reported.**
   Three instruments were defective here: the oracle, the gradient count nibble
   (`header & 0x0F`, not `>> 8`), and a shared colour-width override that made
   a solid-fill finding read as a gradient finding. All three are corrections
   C1, C2 and C4.
6. **No committed source, save, config, content package or conversion output was
   modified.** Every probe ran as a monkeypatch in a separate process and wrote
   only to a disposable temp directory.

**Also still open, unchanged, and not pre-authorised:** mass-converting the 290
available packages (~15,000 files plus preservation-manifest regeneration, its
own line with its own measured diff), and whether the three documented
scope-decision classes are ever revisited.

---


### Resume point, before this entry, retained in full (updated after M12's refusal classes were investigated, orchestrator)

**The second of M12's three open decisions is closed, and it closed by ruling a
route OUT rather than by authorising a line.** Read
`docs/legacy-m12-refusal-classes.md` (commit `3fa6040`) as the current answer to
the refusal-class question; `docs/legacy-m12-fx-animation-rescope.md` (PR #353)
remains current for the FX and animation questions, and its §3.3/§3.6 partitions
are reproduced exactly in the new document's §6.1.

**Do not propose a `shape byte overrun` line. That recommendation is WITHDRAWN.**
The predecessor recommended it on a real defect, and the defect is real: the
committed gradient FILLSTYLE parse at `convert_building.py:285-310` reads an 8-bit
header where the SWF specification has a MATRIX followed by a 12-bit header
(SpreadMode 2, InterpolationMode 2, StartRatio 4, NumGradients 4). The committed
parse takes `NumGradients` from the low nibble of `StartRatio`, and because a
MATRIX is bit-aligned, reading it last instead of first desynchronises every
subsequent bit position. **That is precisely the mechanism the census measures** -
all 104 failing shapes read absurd declared `line_count` values from a byte-aligned
position, **64 of 99** above 64, only **5 of 99** fitting the bytes available, and
**91 of 99** sitting on a gradient-filled shape. **Fixing it converts 0 of 104.**

**And the fix is worse than useless, which is why this matters.** On the 37 shapes
readable under both parses, absurd counts do fall 64 -> 19 - but the `0xFFFF`
sentinel count **rises 6 -> 12**, with seven targets entering the sentinel against
five leaving it. `0xFFFF` is no more a plausible style count than 36716 is, so a
correction that produces more of them has **moved the fault, not removed it**. The
original figure supporting the fix ("absurd counts fall 735 -> 22") came from a
probe keyed to every overrunning shape rather than the first, and reporting only
the row that improved is what hid this.

**The largest group in the census is a family, not a class.** `unknown fill style`
(137), `shape byte overrun` (104), `shape bit overrun` (20) and `shape byte
misaligned` (11) are one shared desync cause - **272 targets, 194 labelled** - and
`unknown fill style`'s 137 targets read **76** distinct `fill_type` values of which
**not one** is a defined fill type, which is the same reader at the wrong offset
sampled at different places. **A line aimed at any single member would have
addressed 104 of 272 and left 168 behind.**

**Three classes are now closed by measurement and must not be re-proposed without
new evidence.** `unsupported shape tag` is code **83 DefineShape4 on all 64**,
refused by `TAG_REFUSED_SHAPE = (83,)` - one member, so it is the only shape tag
the converter declines at all. `unsupported timeline tag` is code **70
PlaceObject3 on all 57**, from the named table at `convert_unit.py:71-77`, and
what PlaceObject3 *means* here is a converter-design decision the oracle cannot
recover. `unresolvable bitmap fill` (133, all buildings) has **no general rule**:
`0xFFFF` occurs **1,138** times but **0 of 133** targets are all-`0xFFFF` and
**127** mix it with real ids. `unsupported tag in timeline` is **1 target**.

**The next eligible objective is a measurement, not a line: locate the remaining
desync** in the 272-target family. A proposal cannot honestly be written until
that is in hand, and §3.2 is the standing demonstration of why - a real, specified,
plausible fix converted nothing.

**One decision remains genuinely open and un-pre-authorised**, beyond the two
above: whether to **mass-convert the 290 available packages**, roughly **15,000**
files plus a preservation-manifest regeneration, which is its own line with its own
measured diff.

**Standing lesson from this investigation, larger than its numbers.** C4 counted
every overrunning shape (**1,154**) rather than the first, and the resulting
aggregate was **favourable** - it would have supported the recommendation this
document withdraws. A census that records one verdict per target because the
converter raises on the first, measured with a probe that records every failure,
does not produce a small error. It produces a confident wrong answer, and in this
case the wrong answer pointed directly at the work.

### Resume point, before this entry, retained in full (updated after M12's FX / animation re-scope was decided, orchestrator)

**One of M12's three open decisions is now closed, and closing it reordered the milestone.**
The binding investigation `docs/legacy-m12-asset-parity.md` §6 item 3 asked for a
**decision**, not a line, and that decision is committed as
`docs/legacy-m12-fx-animation-rescope.md` (PR #353, merge `5061bb5`).

**"FX replaced" is CLOSED BY MEASUREMENT as unsatisfiable from this oracle.** It is not
merely unmeasured. The **205** FX SWFs are unnameable by committed content **structurally**:
**205 of 205** stems are dotted and **0 of 862** sprite stems are, so no content-facing
vocabulary can name an FX asset even in principle. Zero names appear under **four** rules
across the 16 normalized files, the raw config, and all **1,627** `asset_ids` references.
Each file's own exported symbol equals its own stem (**205 of 205**, **0** unexplained
occurrences), so there is no cross-reference; and while **205 of 205** files carry
ActionScript, the committed tooling records its **presence and never its contents**, so the
likely naming source is genuinely unreadable here. **FX is not a census domain** and cannot
become one without a content row.

**New evidence the earlier pass missed: the FX bitmaps already exist.** **86 of 205** are
extracted, **639** bitmaps on disk, each figure confirmed by two independent measures. All
**119** unextracted files carry **zero** bitmaps, so nothing is stranded and extraction is
**complete, not partial** - there is no un-run job here.

**"Animation gaps resolved" is FEASIBLE, and its prerequisite is refusal-class work, not FX.**
Measured for the first time now that line 1 produced the census. Of **422** labelled sprite
files: **68** converted, **313** refused, **41** not candidates. **Animation is blocked
behind the refusal classes.** The largest single lever is **`shape byte overrun`** - **104**
targets, **89** of them labelled - which alone would move convertible animation sprites from
**68 to 157**. Two independent blockers exist and neither alone reaches the population:
**313** behind converter refusals, **41** behind a content-side gap (**10** zero-row,
**30** multi-row, plus 5 not-`extracted`), the multi-row cases being genuine content
ambiguity (`1001_worker_m` is claimed by Worker II, III **and** IV).

**Consequence for ordering.** The **8 refusal classes** move from one of three open
decisions to the **critical path for two deliver items** - "all runtime-required SWFs
converted" (**290 of 817** convertible) and "animation gaps resolved" (**68 of 422**
labelled). That is the strongest reason yet to treat them as M12 line 3.

**Two decisions remain open**, and neither is pre-authorised. (1) Whether the **8 refusal
class-domains** get investigation lines of their own, or are recorded as permanently
refused - **527** refused, and the animation measurement above is the argument for
investigating at least `shape byte overrun` rather than recording it. (2) Whether to
**mass-convert the 290** available packages - roughly **15,000** files plus a
preservation-manifest regeneration, which is its own line with its own measured diff.

**Start here.** Read `docs/legacy-m12-fx-animation-rescope.md` alongside
`docs/legacy-m12-asset-parity.md` before proposing anything. Do **not** propose an FX line:
the deliver item is closed. Do not read the **32** `missing_source` images as fixed.

**Six instrument defects were recorded rather than quietly fixed**, including two printed
conclusions their own data falsifies - "animation is NOT blocked behind a refusal" against
**313 of 422** refused, and "a file no content row names is not a candidate" against all
**41** being named. Read §6 before trusting any figure in that document without re-measuring
it.

### Resume point, before this entry, retained in full (updated after M12 line 2 was archived, orchestrator)

**M11 is CLOSED** and **M12 has two delivered, verified, synced, archived lines**:
`asset-package-parameterisation` (line 1) and `image-reference-resolution` (line 2). **There is
no active OpenSpec change** and no remaining stage on either.

**Start here — nothing is queued, and no next line is pre-authorised.** Read
`docs/legacy-m12-asset-parity.md` and `docs/legacy-image-reference-resolution.md` before proposing
anything. Line 2 closed the **mechanism** half of the image-reference population: 50 references the
old basename-only rule could not resolve are now resolved by their own path and recorded as
`passthrough` with a real source and runtime. **The other half is deliberately still open** — the
**32** `missing_source` references are absent under every extension, so no resolver rule reaches
them, and **authoring or retiring them is a content decision this repository does not make**. Do not
read them as fixed.

**Three decisions remain open, and each is a decision rather than a queued line.** (1) Whether the
**FX and animation** deliverables are re-scoped or dropped — the **205** FX SWFs are named by no
committed content. (2) Whether the **8 refusal class-domains** the line-1 census found get
investigation lines of their own, or are recorded as permanently refused — **527 targets** refused,
**290** packages available. (3) Whether to **mass-convert the 290**: roughly **15,000** files plus a
preservation-manifest regeneration, which is its own line with its own measured diff.

**Do not start M12 from its exit criterion.** The client already loads no runtime SWF, so "Godot no
longer depends on runtime SWFs" was met before either line ran. The milestone's remaining value is
entirely in its deliver items, and its deliver list and its exit criterion are **different kinds of
statement**.

### Resume point, before this entry, retained in full (updated after M12's investigation was committed, orchestrator)

**M11 - Social and Special Systems is CLOSED.** All **six** of its six deliver lines are
delivered, verified, synced and **ARCHIVED**, and its exit criterion is assessed **MET**.
**M12 - Asset Parity has OPENED with an INVESTIGATION and has no change.**

**Start here.** Read `docs/legacy-m12-asset-parity.md` before proposing anything. It measures
that **M12's exit criterion is already met** (the Godot client loads no SWF) while its four
deliverables are close to untouched, and it establishes the shape of the gap: **2 of 872** sprite
SWFs converted against **857** merely extracted, **516 of 607** UI images already runtime-loadable,
**205** FX SWFs named by no committed content, and both converters hardcoding a single
`TARGET_STEM` so no batch mechanism exists. The recommended first line is
**`godot-asset-package-parameterisation`**, because it is the only item on M12's list that is
unambiguously feasible, it has an oracle in the two committed M4 packages, and it unblocks
everything downstream. **Propose** runs next, on its own fresh branch from updated `main`, and it
is **not pre-authorised**.

**Do not start M12 from the roadmap's deliver list.** It is the first milestone whose deliver list
and exit criterion are different kinds of statement, and taking the list at face value would have
produced a plan to convert 870 sprite SWFs while missing that the game itself is one 4.5 MB
ActionScript file this project cannot decompile.

### Resume point, before this entry, retained in full (updated after the `market-trade-counters-projection` archive, orchestrator)

**M11 - Social and Special Systems is CLOSED.** All **six** of its six deliver lines are
delivered, verified, synced and **ARCHIVED**, and its exit criterion is assessed **MET**.
There is **no active OpenSpec change** and **no remaining M11 stage**.

**Start here — nothing is queued.** `2026-10-08-market-trade-counters-projection` is
archived as `openspec/changes/archive/2026-10-08-market-trade-counters-projection/`:
Apply merged `ab886f8` (PR #339), Sync merged `fccb9c5` (PR #340), the post-Sync LF defect
fix merged `4b214dc` (PR #341), archive merged (PR #342). **A decision on M12 is required
and is not pre-authorised**: the next milestone's first line opens with a committed
`docs/legacy-*.md` investigation on its own fresh branch from updated `main`, and that rule
is not relaxed by M11 closing. **Every M11 line followed it - eleven lines, eleven committed
investigations, zero proposals written from a cursor.**

**The one lesson from the defect fix that is not specific to it:** three separate times
this project has turned a property of **how a file arrived** into a required property of
**what was delivered** - the hard-coded `comparable_to_lf_normalised_digest: false`, the
byte-count guard `godot-unit-experience` fixed, and now the pure-LF requirement - and each
time the artifact that caught it was a committed digest or report rather than a reading of
the code. **A checkout form is never a delivery guarantee.** Checks over recorded digests
must assert only checkout-independent facts, and any path whose bytes are hashed into
committed evidence needs an explicit `.gitattributes` LF pin so those digests reproduce
wherever the repository is cloned.

**M11's actual finding, which is the thing not to lose:** six lines, six read-only
projections, **zero routes and zero executed-legacy fixtures**. Every legacy branch this
milestone touched had either no request path, an unvalidated client-sent grant, or
committed content that nothing anywhere reads. The social and special systems of this game
lived almost entirely in the **Flash client**, and **absence of a server rule says nothing
about what that client displayed** - so M11 being projection-only is a measurement, not a
shortfall.

**The next phase must not begin from this cursor's evidence.** Every M11 line needed its
own committed `docs/legacy-*.md` investigation before any proposal was written, and a
milestone closing does not relax that. **Recorded open carry-forwards**, none of which is
a reason to invent a surface: the **twelve** recorded flaky surfaces, the newest two
found on `fix/market-trade-lf-digest-check` (a `test_town_upgrade` access violation
`0xC0000005`, and a `test_game_api_live.gd` second-boundary clock race) on suites that fix
does not touch, both cleared by a re-run - the disposition the rule prescribes; five sibling
suites lacking `--report=` absolute-path resolution; none of the twelve
`packages/game-content/tests/` suites running in any battery; committed evidence reports
not regenerated by `verify-boot.ps1`; the `godot-combat-actions` README section gap; and
the six surfaces this milestone named and declined - the atom-fusion **powerup purchase**
(`buy_powerups` is a `# TODO` with a committed six-row ladder and zero consumers),
`first_time_marketplace`, `rt_open_graph_unit`, the **24-declaration** `SPELL_*`/`TECH_*`
gap beside `godot-mission-vocabulary`, and the inert `crossPromotionsFinished`/
`unlockedSkins` pair beside a **one-entry** `specials.json`.

**M10 and every earlier M11 line follow in full and are unchanged.**

### Resume point, before this entry, retained in full (updated after the LF defect fix, orchestrator)

**M11 - Social and Special Systems has SIX of its six deliver lines delivered, verified and
synced, and its exit criterion is assessed MET.** `market-trade-counters-projection` is
synced and its post-Sync LF defect is fixed on `fix/market-trade-lf-digest-check`;
**only its Archive stage remains.** The LF defect fix had to be **merged before Archive
began**, because Archive moves the change's artifacts out of `openspec/changes/` and a
defect belonging to that change belongs ahead of it, not inside it. Archive then ran on
`chore/archive-market-trade-counters` from updated `main`, as a **merge commit**, with the
branch deleted afterwards. **No further M11 deliver line exists** - all six are accounted
for, four delivered and two closed by measurement. **The lesson from that defect, which is
not specific to it:** three separate times this project has turned a property of **how a
file arrived** into a required property of **what was delivered** - the hard-coded
`comparable_to_lf_normalised_digest: false`, the byte-count guard `godot-unit-experience`
fixed, and now the pure-LF requirement - and each time the artifact that caught it was a
committed digest or report rather than a reading of the code. **A checkout form is never a
delivery guarantee.** Checks over recorded digests must assert only checkout-independent
facts, and any path whose bytes are hashed into committed evidence needs an explicit
`.gitattributes` LF pin so those digests reproduce wherever the repository is cloned.
**The carry-forwards above read `ten` recorded flaky surfaces at this point** and are
corrected to **twelve** in the current entry.

### Resume point, before this entry, retained in full (updated after the `auction-schedule-projection` archive, orchestrator)

**M11 - Social and Special Systems has FIVE of its six deliver lines ARCHIVED.**
`auction-schedule-projection` is archived as
`2026-10-08-auction-schedule-projection`, and both capabilities
(`auction-schedule-normalization`, `godot-auction-schedule`) are in the main
specs. `openspec validate --all --strict` reads **71**.

**The next and final eligible objective is `special mechanics`, and it needs
its own committed `docs/legacy-*.md` investigation before any proposal.** It
may not be proposed from this cursor's evidence, for the same reason
`legacy event systems` was not proposed from the `social rewards` cursor: every
M11 deliver item has turned out to be the **opposite of what its name suggests**
once measured. `friends` was a directory listing rather than a relationship,
`social rewards` a paid substitute whose friend arm has no writer,
`legacy event systems` a module that **cannot construct itself**.

**The pattern to carry into the last line is that the name is not the surface.**
Each line found its real behaviour where the deliver item's name did not point,
by counting occurrences across all **eleven** legacy modules under **six** rules.
`special mechanics` should be measured the same way first.

**Two standing lessons from this line's Archive stage, both cost real effort.**
First, **an unchecked verification list is not a safe one**: task 2.2 was
reported verified and had never been run, and it was hiding a guard that could
only pass pre-commit. Run every command the task list names, including the ones
whose output looks redundant. Second, **tooling that rewrites bytes must assert
that the bytes it read are the bytes it wrote back** - a newline translation
silently rewrote two committed modules, and this is the **third** recorded
instance of that class in this project.

**M11's exit criterion ("All relevant legacy game systems are classified and
implemented or explicitly excluded") is close but still NOT MET**, and the
remaining reason is a single deliver item rather than an unexamined surface.

**M8, M9, M10 and the earlier M11 lines follow in full and are unchanged.** The
full prior cursor, including every retained entry, is above.


### Resume point (updated after the `auction-schedule-projection` Sync, orchestrator)

**M11 - Social and Special Systems has FIVE of its six deliver lines delivered,
applied, verified and synced**, with **one** remaining. This Sync is the
`auction-schedule-projection` stage; the change is **not yet archived**, and the
next step is the Archive stage, which moves `openspec validate --all --strict`
from **72** to **71**.

**The next eligible objective is `special mechanics`, and it needs its own
committed investigation before any proposal.** It may not be proposed from this
cursor's evidence, for the same reason `legacy event systems` was not proposed
from the `social rewards` cursor: each deliver item of this milestone has turned
out to be the *opposite* of what its name suggests once measured. `friends`
turned out to be a directory listing rather than a relationship, `social rewards`
turned out to be a paid substitute whose friend arm has no writer, and
`legacy event systems` turned out to be a module that **cannot construct itself**.

**The pattern worth carrying into the last line is that the name is not the
surface.** Each M11 line so far has found its real behaviour in a place its
deliver item's name does not point at, and each found it by counting occurrences
across all **eleven** legacy modules under **six** rules rather than the seven
earlier probes some lines used. `special mechanics` should be measured the same
way before anything is proposed about it.

**M11's exit criterion ("All relevant legacy game systems are classified and
implemented or explicitly excluded") is closer but still NOT MET**, and the
remaining reason is a single deliver item rather than an unexamined surface.

**M8, M9, M10 and the earlier M11 lines follow in full and are unchanged.** The
full prior cursor, including every retained entry, is above.


### Resume point (updated after the `mission-vocabulary` archive, orchestrator)

**M8 — Units is COMPLETE, all eight lines delivered and archived, exit criterion "Core unit
gameplay works" assessed MET.** **M9 — Progression is CLOSED**: four lines delivered and
archived (`research`, `quests`, `tutorial/progression`, `stored item placement`), the
`unit-experience-evidence` correction line archived, and its exit criterion "Primary long-term
progression systems work" **NOT MET** — because nothing in the committed legacy server reads
progression state back to change what a player may do. That is a property of the **oracle**,
not of the modern client.

**M10 — Missions and Combat is IN PROGRESS, with line 1 of 8 deliver items delivered and
archived** as `2026-10-05-mission-vocabulary` (#283 `e4fc5e2`, #284 `dc4dbaf`, #285
`d437ede`, #286 `80c6cd9`, and its archive).

**M10 opened by measuring two of its own deliver items out of existence, which is the single
most important thing to know before starting line 2.** The milestone investigation
(`docs/legacy-m10-missions.md`) found that **mission state was already delivered**:
`collect_mission` at `command.py:430-442` is the **only** mission-mutating command in the
preserved server and is owned by `godot-quests`; `idCurrentMission` has **2** writes and **0**
reads; `timestampLastChapter` has **2** writes and **0** reads, the second inside `fast_forward`
as a **client-supplied** subtraction; **there is no mission-loading command at all**; and all
**ten** committed save documents have `maps` of length **1** with `default_map` 0. So the
roadmap's first listed objective, "mission loading", names something the legacy server does not
do — one of four corrections the investigation records, the sharpest being that **"mission
loading" does not mean a mission map**.

**The cursor is therefore `combat actions`, and nothing beyond it is authorised.**

**Why the vocabulary line came first, and why it precedes combat.** The 64 `MISSION_*`
declarations at `constants.py:984-1047` are the largest single block of unconsumed vocabulary in
the preserved server, and they are the **only surviving statement of what the combat lines must
resolve**: `MISSION_ATTACK_PLAYER` (37), `MISSION_ATTACK_FRIEND` (38), `MISSION_ASSAULTS_WON`
(46), `MISSION_KILLED_ENEMY` (67), `MISSION_DEFEAT_ALL_TROLLS` (30), `MISSION_SACRIFICE_UNIT`
(63), `MISSION_COORDINATED_ATTACK` (61), `MISSION_CAPTURED_SUBCATFUNC` (11) and
`MISSION_CAPTURED_ID` (12). They resolve none of it, and they are delivered before combat so
that the combat investigation starts from a named vocabulary rather than an inferred one.

**The finding is that the vocabulary exists and nothing ever read it.** A first classifier
reported three consumers at `constants.py:997`, `:998`, and `:1012`; **all three are substring
artifacts**. The suite re-measures the absence on every run across the **ten** other legacy
modules and requires **zero** `MISSION_` occurrences. Zero consumers is why the line adds **no
endpoint**, **no** executed-legacy fixture, and **no** live phase — a vocabulary with no consumer
has no transaction to capture — and the live-phase count holding at **20** while a new hermetic
suite registered is the evidence that this is measured rather than asserted.

**Four measurement lessons from this line, carried forward as instructions for line 2.**
1. **A substring is not a consumer.** `MISSION_DESTROYED` prefixes
   `MISSION_DESTROYED_SUBCATFUNC` and `MISSION_DESTROYED_ID`. Count occurrences per line,
   quote-aware, and record occurrence counts **separately** from distinct-line counts.
2. **Case is the same disguise as a suffix.** The by-name guard had to be strengthened to
   case-insensitive *after* measuring that the module was clean case-insensitively; strengthen
   the guard only once the clean measurement exists, or you are guessing.
3. **Opening a file in text mode silently translates CRLF to LF.** An earlier probe made a CRLF
   tree look LF-only. The byte-faithfulness guard therefore reads `constants.py` **as bytes**,
   and any byte-level claim in this repository should do the same.
4. **The suite's own guard can refuse your first fix.** The entry-dropping defect's min/max
   repair was rejected for adding two comparisons over a committed value; the repair that
   satisfied the constraint was a sort. When a guard refuses a fix, treat it as information
   about the contract rather than an obstacle to route around.

**Three defects in this line's own work were found by measurement, not by luck, and all three
are recorded rather than shipped quietly** — the entry-dropping defect whose min/max fix was
itself refused; the case-sensitive by-name guard; and a deliberate refusal test that failed the
battery because `JSON.parse_string` emits an engine `ERROR:` line that `verify-boot.ps1` treats
as a script error. **Eight guard injections were all detected** (5/5/5/4/3/3/2/3 failures), each
followed by a byte-identical restore.

**A sixth flaky surface is now recorded, and it is in the harness rather than in the checks:**
the shell's native-command capture intermittently dropped **both** stdout and `$LASTEXITCODE`
for the Godot executable, returning 0 lines and an empty exit code. Run Godot suites through
`Start-Process -Wait -PassThru -RedirectStandardOutput`, which reported exit codes reliably
throughout this line. The five pre-existing surfaces (the `^ERROR:` RID-leak guard, the
transient `0xC06D007F` module-load crash, the live-phase `%`-binding parse error, and
`verify.ps1`'s display-sensitive capture) remain open; two earlier ones were closed by fixing
the guard rather than re-running.

**M10 line 2's investigation is committed and merged (#288 `f21c111`, `docs/legacy-m10-combat.md`), and
it inverted the line's expected shape.** It found that **M8's `godot-unit-behaviors` recorded a false
premise**: that no executed-legacy fixture could be captured because "the committed corpus places only
buildings and no unit row, and its ledger is present and `{}`". That is false of the repository and
true of `tests/saves/fresh-player.json` alone. Measured across all **11** committed save documents
(**3,372** placed rows): **441** committed unit rows across **7 of 11** documents, **all** on team one,
**429** satisfying the `resurrectable` gate, and **five** village saves carrying a **non-empty** ledger
(`Neutral` 29 keys, `Kiriakos` 9, `Nerri` 9, `Scarlet` 2). **This is the second time the repository
has caught that exact delivered-claim defect** — M9's `unit-experience` line corrected the identical
claim for `attr["xp"]`. **The correction therefore cannot be deferred**: the false premise sits in a
**merged requirement's SHALL text and a scenario**, so a sibling capability capturing a combat fixture
would leave two merged specs contradicting each other.

**The eight executed probes make this a working line, not a refusal line.** `end_attack` with
`attacker_units=[[1007,1,3,1]]` destroys **two** committed unit rows (319 → 317) and writes
`deadHeroes {'1007': 2}`; `lost = 9999` destroys exactly **2**, because `map_lose_item` returns when no
row matches — the bound is **exhaustion, not a check**. **The ordering is the sharpest finding:**
omitting the loss list raises **before** the save is touched, while omitting the victim record raises
**after** two rows are gone and the ledger is incremented, so validation ordering is load-bearing.
`kill` deletes a row and **never** touches the ledger; `sell` behind the literal `"KILL"` is the second
ledger door (`KILL` is a string literal at `command.py:159`; the constant is never read by the
dispatcher); `kill_iid` **mutates nothing**; and `resurrect_hero` against `Neutral.json`'s committed
28-key ledger decrements one key and re-places a row at client-supplied cells — **directly disproving
the delivered claim**.

**Two harness failures are recorded rather than smoothed over**, both about trusting a guarantee
unearnedly: a result marker on **stdout** — shared with the code under test — lost one probe's outcome
to the legacy loader's unterminated `print(..., end='')`, so the marker moved to a file; and the first
run **leaked a temp directory** by aborting on Windows symlink elevation *before* cleanup existed. A
containment guarantee established by the happy path is not a guarantee.

**A second discrepancy is resolved, not deferred.** The four M8 combat-field figures deferred above
reproduce under **no** legacy-consumer counting rule — this measurement finds exactly **zero** for all
four, which **strengthens** M8's direction — but the line that owned those fields also established
*why* they were never reproduced, and it is not an error. Each reproduces **exactly** as the
`unit_distinct` column of `unit_behaviors.gd`'s own `ZERO_CONSUMER_FIELDS` table: the count of
**distinct committed values over the 429 committed unit definitions**. So `attack` 131, `defense` 1,
`life` 150, `min_level` 21, and `syringes` 6 are **all five of five** content-distribution counts,
not consumer counts. The record's numbers were correct and its **placement** misleads: it reads as a
consumer census and is a distribution census. **M8's conclusion is left intact and strengthened**,
and **no figure was silently replaced** — see the annotation in `AGENTS.md`. This change's own
proposal counted "four of five" and was itself off by one.

**This line is archived; the cursor advances to `damage`.** Design **D1** was load-bearing and was
**not widened**: the request addresses a **lost unit identity** and the service destroys **exactly
one** eligible row it derives itself, because no combat rule exists to derive a *count* from —
reproducing `max(0, sent - survived)` would be the `AGENTS.md` "Bad" pattern and the same
anti-pattern M9's `end_quest` refused. The resulting difference from the legacy server is recorded as
a **divergence**, never as parity. **Do not start damage, death, mission completion, or rewards**;
each is a separate later line, and each needs its own investigation before any proposal.

**Delivered and archived, M9 lines 1-3:**

| Line | Archive | PRs and merges |
| --- | --- | --- |
| `research` | `2026-10-02-research` | #251 `0b57e83` (cursor), #252 `3d44159` (measure), #253 `e630da3`, #254 `44d1fa9`, #255 `0efe16c`, #256 `49e96ce`, #257 `ece6246` |
| `quests` | `2026-10-03-quests` | #258 `0e886f2` (inv), #259 `049fa5a`, #260 `eefa6a0`, #261 `ae4c21f` (cursor), #262 `286152e`, #263 |
| `tutorial/progression` | `2026-10-03-tutorial` | #264 `2dbf715` (inv), #265 `960e143`, #266 `9f2325f`, #267 `2c69b33`, #268 `95c7f27` (guard follow-up), and this archive |

**M10 line status:**

| Line | Change | Stage reached |
| --- | --- | --- |
| **M10 line 2 — `combat actions`** | `2026-10-05-combat-actions` (**archived**) | investigation #288 `f21c111`, proposal #289 `6d9f2d0`, Apply #290 `d4e42a1`, Sync #291 `2081161`, and this archive |

| Line | Change | Stage reached |
| --- | --- | --- |
| **M10 line 1 — `mission vocabulary`** | `2026-10-05-mission-vocabulary` (**archived**) | investigation #283 `e4fc5e2`, proposal #284 `dc4dbaf`, Apply #285 `d437ede`, Sync #286 `80c6cd9`, and this archive |

| Line | Change | Stage reached |
| --- | --- | --- |
| `stored item placement` (closing the `collections` gap) | `2026-10-03-stored-item-placement` (**archived**) | investigation #271 `6bb7a46`, proposal #272 `dbf4491`, Apply #273 `62e6328`, Sync #274 `eab756b`, and this archive |

**Delivered and archived, M8 lines 1-8:**

| Line | Archive | PRs and merges |
| --- | --- | --- |
| `unit definitions` | `2026-10-01-unit-definitions` | #204 `cf13a5b`, #205 `72f87a3`, #206 `43b8ed4`, #207 `5e43bc0` |
| `unit instances` | `2026-10-01-unit-instances` | #208 `235b4d2` (inv), #209 `0710038` (**squash, disclosed**), #210 `02dbfa6`, #211 `84f7af9`, #212 `435db4e` |
| `queues` | `2026-10-01-unit-queues` | #213 `bbf4669` (inv), #214 `4b6a1eb`, #215 `69d49be`, #216 `a55fe41`, #217 `1420e2c` |
| `production` | `2026-10-01-unit-production` | #219 `58caf86` (inv), #220 `c442b3b`, #221 `eaa6f37`, #222 `65af7ee`, #223 `61f400a` |
| `collection` | `2026-10-01-unit-collection` | #224 `4cfc3fd` (inv), #225 `52e16b0`, #226 `22fdc2c`, #227 `20215fd`, #228 `c10de94` |
| `movement` | `2026-10-01-unit-movement` | #229 `5cd47a1` (inv), #231 `a958bef` (ledger reconcile), #232 `e5dc176`, #233 `da664a1`, #234 `ce29107`, #235 `018e030` |
| `animations` | `2026-10-02-unit-animations` | #237 `ff77e8f` (inv), #238 `3ccbf03` (cursor), #239 `e6f2f9c`, #240 `28e77df`, #241 `5bfdadd`, #242 `4915948` |
| `basic behaviors` | `2026-10-02-unit-behaviors` | #244 `2e98d55` (inv), #245 `8ca6778` (cursor), #246 `f5cdd30`, #247 `b473dc7`, #248 `db2c207` |

**Committed investigations, nine:** `docs/legacy-unit-instances.md`,
`docs/legacy-production-queues.md`, `docs/legacy-unit-production.md`,
`docs/legacy-unit-collection.md`, `docs/legacy-unit-movement.md`,
`docs/legacy-unit-animations.md`, and **`docs/legacy-unit-behaviors.md`** (PR #244, merged
`2e98d55`, and now carrying a corrections section), plus
**`docs/legacy-stored-unit-placement.md`** (PR #271, merged `6bb7a46`) — the first M9
investigation whose finding **contradicted the refusal pattern**, since 24 executed
probe transactions established that `place_stored_item` and `sell_stored_item` are
unguarded, type-agnostic, and charge nothing.

**Baselines in the final state (re-run by the orchestrator after line 8):** `verify.ps1` exit 0;
`verify-boot.ps1` exit 0 with **35 hermetic suites and 16 live phases** and the new `behavior-live`
phase proving a disposable corpus save mutated; compat **`Ran 1444 tests ... OK`** (up from 1352 by
**+92**); content validator `valid`, 21 schemas; hash manifest 3,258 entries; `openspec validate
--all --strict` **57/57** after the spec sync and **56/56** after the archive. Report digests, each
byte-identical across three runs: `f997eb2d...66d5`, `A02EEDC8...57BBA0`, `807477db...92090`,
`E56A470B...33CD6`, `81EFAD48...64C`, `785B0482...9165E`, `f06784cb...d8556`, and
**`0FE80C47...8F59`** (`unit-behaviors-report-v1`, 39,979 bytes).

**Committed M9 investigations, three:** **`docs/legacy-m9-progression.md`** (PR #250, merged `f74647c`,
the milestone-wide contract), extended by **PR #252** (merged `3d44159`, the research
measurements) and carrying a **corrections section** rather than quiet edits — `research` appears
in **two** normalized files (`buildings.json` **1**, `images.json` **6** from three popup rows),
not one; `config/main.json` **does** have **three** nested keys containing it, all in the `/images`
asset namespace, so "no key at any depth" was **false** though no top-level key contains it; and
the building's `legacy_id` is the **string** `"256"`, not an integer. The conclusion is unchanged
— every hit is an asset or display name, so there is still **no committed research cost, step
count, unlock requirement, or reward** — but the refusal now rests on a **correctly measured**
basis. And **`docs/legacy-m9-quests.md`** (PR #258, merged `0e886f2`), the line 2 contract. And
**`docs/legacy-m9-tutorial.md`** (PR #264, merged `2dbf715`), the line 3 contract — the **first M9 line
investigated on its own branch** rather than under the milestone-wide record, and recorded as
**40 executed-legacy probe transactions**. It found the entire tutorial system to be
`command.py:60-66`: one branch, one local, one write. `completed_tutorial` occurs **once**
across the eleven legacy root modules on **one** line, that line being
the **write**, with **zero readers** — the **tenth** committed field in this
project with no legacy consumer. `tutorial_step` occurs **4** times over **3** lines
and is a **local that is never persisted**, so there is **no stored step and no
un-complete path**. The gate `tutorial_step >= 25 or tutorial_step == 15` has **no
lower bound, no upper bound, and no type check**, and its hole is **exactly `16..24`**,
nine values wide. And `config/main.json` plus every normalized package hold **zero**
occurrences of `tutorial`: no step list, no count, no gate definition, no text.

**Baselines in the final state after M9 line 3 (re-run by the orchestrator):** `verify.ps1` exit 0;
`verify-boot.ps1` exit 0 with **38 hermetic suites and 19 live phases** (up from 37/18), the new
`tutorial-live` phase, and **264** log files inspected with **zero** `[test] FAIL`, `^ERROR:`,
or `SCRIPT ERROR` lines; compat **`Ran 1914 tests ... OK`** (1912 at the Apply merge, then **+2** from
the guard follow-up PR); content validator `valid`, 21 schemas; hash manifest
3,258 entries; `openspec validate --all --strict` **59/59** after the spec sync and **59/59**
after the archive. The line's own report digest is **`05f7b12d...c38b`**
(`tutorial-report-v1`, 10,634 bytes), byte-identical across three runs. The
prior M8 and M9 report digests remain as recorded above.

**Baselines in the final state after the `stored-item-placement` Apply (re-run by the
orchestrator):** `verify.ps1` exit 0; `verify-boot.ps1` exit 0 with **39 hermetic suites
and 20 live phases** (up from 38/19), the new `stored-placement-live` phase proving a
disposable corpus save mutated; compat **`Ran 2130 tests ... OK`** (up from 1914 by
**+216**, because the line adds two state-mutating routes, the envelope module, and three
test modules — the three new modules alone are **216** tests); content validator `valid`,
21 schemas; hash manifest 3,258 entries; `openspec validate --all --strict` **60/60** at
Apply, **61/61** after the Sync stage (the new capability was then both an active change
and a main spec), and **60/60** after the archive with `openspec list` reporting no
active changes. The line's own report digest is
**`c5bea9dd...8d18`** (`stored-placement-report-v1`, 13,618 bytes), byte-identical across
**four** runs. The prior M8 and M9 report digests remain as recorded above.

**The two anti-invention injections the orchestrator ran personally on this line**, both
restored byte-identically to `0b437e5d...0edbd`: `cell_is_free` into the delivered flow
module (**3** independent failures, exit 1) and `refund_for` (**1** failure). The second
is the line's finding: the by-name guard matched only the exact name `refund`, so a
helper wearing the same rule under a suffix slipped past it, and only the whole-inventory
pin caught it. A substring check was added — **2** failures for the same injection after
— and the finding is recorded in the suite rather than quietly fixed.

**Four cross-layer defects that the 544-check hermetic suite structurally could not
catch**, all four found only by `stored-placement-live`, which is the single strongest
argument in this milestone for keeping a live phase per state-mutating line: the
bootstrap payload is keyed `map` while the recorded fixture documents are keyed
`maps[0]`, so one storage assertion had been **passing for the wrong reason**;
`CollectionResult` has no `count_after`, so a bad field aborted the function before the
sale and both refusals ever ran; the service's and the client's copies of the recorded
geometry and quantity notes are deliberately **not** identical, so the suite had been
claiming "verbatim" — a claim **stronger than anything true** — and now asserts the
identifying **clauses**; and the sale's ledger append is **if-absent**, so a repeat
completion grants the prize again while the collection ledger **stands still**, the
opposite of what the first draft asserted and the fact that makes the sale reachable at
all.

**A sixth recorded flaky surface was found by this battery and FIXED rather than
re-run.** `verify-boot.ps1` failed `test_collection_endpoint.ContainmentTests` once on
`server_time` **1791066504** against **1791066505** with every other field identical,
while three immediate reruns passed. `/v0/session` stamps the current time on every
response, so a whole-document equality across two calls was **always** going to fail when
they straddled a second — the assertion was testing the clock, not the session list. The
first fix was then found wrong in the **other** direction by running that file alone,
because when both calls land inside one second the clock does *not* differ; so the
assertion is now that the differing-field set is a **subset** of the documented volatile
field, which is the only claim true in both cases and exactly as strict about every other
field as before. That guard was made to fail rather than trusted: injecting a real
session-list change produced `AssertionError: {'saves'} not less than or equal to
{'server_time'}`, and restoring the byte-identical file (`8efd62d8...7ab6`) returned it to
36 tests and `OK`. **This is the first recorded flaky surface in the project that was
closed rather than re-run**, and the reasoning generalises: a flaky guard is not a passing
guard.

**One cross-suite boundary had to be amended rather than deleted.** `test_unit_collection.gd`'s
`_check_boundary()` asserted that `place_stored_item` was absent from **every** client
source; that claim became **false** the moment this line landed, and it was measured
failing with **4** failures before being touched. The whole-tree absence was replaced by
an **ownership claim**, and — because two suites scanning one tree for one token with two
hand-maintained owner lists is drift waiting to happen — the owner list lives **only** in
this line's suite while the collection suite asserts that the hand-off's **recipient
exists and asserts it**. Its check count went **1,988 → 1,894** because the removed
tree-wide scan was 4 needles × ~93 sources.

**Archive-stage corrections, recorded rather than quietly fixed.** Three figures in this
change's own artifacts did not survive contact with measurement, and one of them was in
this ledger:

1. **The task list has 20 boxes, not 18.** This ledger, the client README, and the
   change's own proposal said "18 unticked tasks", written from memory at Propose and
   **never counted**. Measured: **20** — 1.1–1.4, 2.1–2.5, 3.1–3.4, 4.1–4.3, 5.1–5.4.
   Nothing about the delivered behaviour changes, but a ledger that miscounts its own
   tasks is not a ledger, so the correction is recorded here, in the archived
   `tasks.md`'s integration review, and in the README.
2. **Task 1.1's "exactly two leaves" was wrong, and the cause is in the fixture manifest.**
   Measured: **three** at whole-document scope (`maps[0].items.41`, `maps[0].store.1085`,
   `privateState.boughtUnits`) and **two** at map scope. The cause is not a defect — the
   committed investigation had seeded with `store_add_items`, which calls
   `bought_unit_add` in the **same** batch (`command.py:264`), so its ledger already held
   the id and the placement's own append-if-absent left it alone. Seeding instead with the
   content-derived `complete_collection` — which appends to `privateState["collections"]`
   and **never** to `boughtUnits` — makes that third write observable.
   `test_the_manifest_records_the_three_leaf_correction` pins the correction so it cannot
   be silently reverted to the predicted number.
3. **The capture is five chained steps, not four.** The sale needs a *second* seed,
   because the sale consumed the only stored unit and the ledger append is **if-absent** —
   so `login_post` → `complete_collection(1)` → `place_stored_item` →
   `complete_collection(1)` → `sell_stored_item`. Found by the live phase, after the
   offline suite was green.

**The Archive stage was run with `--skip-specs`, deliberately.** The Sync stage had
already applied and merged both deltas, so letting `archive` re-apply them would have
duplicated a whole requirement block. Both stages also repeat the same discipline in
opposite directions: Sync copies the delta's block **verbatim** into the main spec rather
than hand-editing it, and the earlier delta was generated **programmatically** from the
main spec rather than retyped — because a MODIFIED requirement replaces the **whole**
block, and a partial edit is exactly how a scenario silently disappears.

**The three injections the orchestrator ran personally on line 3**, each restored
byte-identically: `tutorial_total_steps` into the flow module (**3** independent failures,
exit 1, restored `9ea3ff1b...0d6`);
relocating `/v0/tutorial` after another route (**3** failures, exit 1, file still
compiling — because every delivered guard slices `def vN_x():` up to the next
`@app.<method>(...)` decorator, so a route inserted between two others lands inside
the *preceding* route's slice); and honouring a client-sent `completed_tutorial` in
the route (**1** failure across 1912 tests, then **2** once the sweep existed,
restored `D75BF31C...D6D0`).

**That third injection is the line's second substantive finding**, and it is the
sharpest instance yet of a discipline this repository keeps learning: the
delivered intent-only guard was **thinner than the claim it supported**. Three
narrow tests each sent one field name, and honouring a client-sent
`completed_tutorial` broke exactly **one** of them, because the other two sent
unrelated names and no envelope-side test could catch it at all — the envelope
never emits such a field. The requirement held, but it held by accident rather than
by proof. PR #268 closes the class with a sweep over **twenty** field names across
**both** a completing and a declining step, comparing the **whole response** minus a
named volatile-key list plus the persisted flag and every stored resource, with a
companion test asserting `server_time` is the **only** key that varies so the helper
cannot silently grow.

**A fifth recorded flaky surface** came from this line: the live phase's marker line
bound `%` to the last string of a concatenation and so produced a **parse error**
rather than a wrong count, which is exactly why `verify-boot/*.err.txt` is read
rather than the exit code trusted.

**Baselines in the final state after M9 line 2 (re-run by the orchestrator):** `verify.ps1` exit 0;
`verify-boot.ps1` exit 0 with **37 hermetic suites and 18 live phases** and **484** log files
inspected with **zero** `[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines; compat **`Ran 1751
tests ... OK`** (up from 1572 by **+179**); content validator `valid`, 21 schemas; hash manifest
3,258 entries; `openspec validate --all --strict` **59/59** after the spec sync and **58/58** after
the archive. The line's own report digest is **`412dd271...6019`** (`quests-report-v1`, 37,102
bytes), byte-identical across three runs. The prior M8 report digests remain as recorded above.

**The ASSESSMENT is COMPLETE, and it was a verdict rather than a line.**
`docs/legacy-m9-assessment.md` (PR #270, merged `7ab93c7`) assessed `XP`, `levels`, and
`collections` — the three M9 deliver items delivered by an earlier milestone and
deliberately narrowed there — against the question of whether M9's exit criterion
requires the omissions.

**M9's exit criterion — "Primary long-term progression systems work" — is NOT MET.**
The reason is uniform across all five M9 items: **the committed legacy server has no
progression _consumer_.** Every delivered M9 surface projects, records, or narrates,
and nothing in the legacy source reads any of it back to change what a player may do.
That is a finding about the oracle, not a defect in the modern client.

**Four measurements the assessment made that change the record:**

1. **The level curve's index base is now ESTABLISHED, not derived-provisional.**
   `building-xp` rested its one-based reading on **one** corpus data point. The eight
   committed **village** saves give **eight**, and the test is direct — one-based is
   **TIGHT on 7 of 8**, zero-based on **0 of 8**. `Scarlet.json` is the one genuine
   disagreement (recorded level 33 at `xp 107,694`, exactly one below the curve's tight
   level of 34), which is committed evidence that a stored level really can diverge —
   and confirmation that reporting rather than reconciling is right.
2. **Unit XP is not unreachable.** The recorded claim *"no unit XP; the corpus cannot
   exercise it"* is true of `tests/saves/fresh-player.json` (0 of 40 rows) and **false of
   the committed evidence**: `attr["xp"]` appears on **171 rows across 5 of 8** village
   saves, values 10 → 611,650.
3. **Committed level rewards exist and are not uniform** — **5** distinct
   `reward_type`/`reward_amount` pairs, not one — and a **second** unread table,
   `level_ranking_reward`, exists with **50** entries covering **1..50** with no gaps or
   duplicates, a `cash` field **uniformly 1**, and **exactly one** positional inversion
   (level 24 sits after level 19), so a positional consumer would be wrong for level 24
   and a field-keyed one would not.
4. **Both curve accessors are dead.** `get_xp_from_level` has **0** call sites and
   `get_level_from_xp` **0** callers; `exp_required` and `levels` each have **2**
   occurrences, both inside those two accessors. The auction level gate is dead too —
   `get_auctions(user_id, level)`'s only call site is commented out.

**All three assessed items have a real, bounded, evidence-backed gap**, and the
assessment proposed them as **separate** bounded lines while **authorising none of them**.
The deliver list is `XP`, `levels`, `quests`, `research`, `collections`, and
`tutorial/progression`, and the exit criterion is "Primary long-term progression systems
work."

- **`XP`** — the accumulation branch `add_xp_unit` (`command.py:322-343`) is undelivered.
  Its optional third argument is assigned to a local `level` and used **only in a print**.
- **`levels`** — a reward exists in committed content but its letters have **no**
  committed resource mapping, so paying one would invent both a schedule and a
  vocabulary. **Stays refused.**
- **`collections`** — the granted prize is never placed. **In flight** as
  `2026-10-03-stored-item-placement`.

**Two defects in the assessment's own probes were recorded rather than quietly fixed**,
and both are the reason one of its numbers changed: the first counter stripped **string
literals** — where every save field name lives — and reported `privateState` and
`collections` as **0** occurrences against the corrected **138/113** and **10/8**, which
would have supported a confident false claim about `command.py:517-518`; and the first
index-base probe printed its `one-b` and `zero-b` columns from the **same function**, so
the second column was meaningless and would have supported a confident claim about an
untested reading. Both were discarded and re-measured. Separately, a number the
assessment record initially carried for the defective probe — "93 occurrences" — could
not be reproduced, so it was replaced with the measured **0** rather than left as a
recollection.

**Current objective: none in flight, and M9 is CLOSED.** `stored-item-placement` and `unit-experience-evidence` are both archived, closing **both** authorised gaps the M9 assessment named. With them closed, **no evidence-supported M9 implementation gap remained**, so the milestone was closed by **`docs/legacy-m9-closure.md`** rather than left open: M9 is **implementation-complete to the extent the committed legacy oracle supports**, its exit criterion is **NOT MET**, and the cause is a **legacy-reference capability gap** — the preserved implementation being migrated contains **no progression consumer**. **`add_xp_unit` is no longer an unproposed candidate:** it was delivered and archived as `2026-10-04-unit-experience-evidence` (investigation PR #276 `79d13ac`, Apply PR #278 `d0d70a3`, Sync PR #279 `131a133`, fix PR #280 `dae7705`, Archive PR #281 `8d370a1`). The cursor has moved to **M10 — Missions and Combat**, first objective **mission loading / mission state**, which **requires its own committed investigation before any proposal**.

**Carried follow-ups, nearest first:**

1. **The stored-item round trip — DELIVERED and ARCHIVED** as
   `2026-10-03-stored-item-placement` (investigation `docs/legacy-stored-unit-placement.md`,
   PR #271 `6bb7a46`, proposal validating **60/60**), retained here as the resolved record
   rather than an open follow-up. It was the nearest undelivered step on a fully
   content-derived path, the collection line deliberately stopped there, and it closed the last
   place where **no acquired unit was ever placed on the map**. The committed investigation
   resolved the open questions with **24 executed-legacy probe transactions** in two contained
   runs, both reporting a byte-identical working-tree
   containment digest and a free port: the branch is **type-agnostic**, **no price exists**,
   the row is **server-derived in five of eight slots**, and **four behaviours the legacy server
   does not guard** were each confirmed by execution. It **corrects** the assessment's framing:
   **four of the ten collection prizes are buildings**, so the scope is written against the
   **prize** rather than the word "unit".
2. **`verify-boot.ps1`'s `^ERROR:` guard** is broad enough to fail on a benign engine shutdown
   RID-leak warning, on a single `0xC06D007F` Windows module-load crash of an untouched phase
   that had already passed nine times in the same run, and on a transient `0xC06D007F` of the
   same kind during the quests line; narrow it to `SCRIPT ERROR` or a fatal-error allowlist.
3. **Latent `%r` format bugs** in `game_api.gd:176`, `boot_data.gd:1282,1312`, and
   `fake_api.gd:2216,2237,2909,2910,2914` — Godot 4.7.2's `%` does **not** support `%r`, so
   each of those lines will raise if its branch is ever reached.
4. The friend-assist cluster, construction speedups, the upgrade row's seeded `{"nc": 0}`, the
   premium upgrade path, the legacy level gate and daily-upgrade limit, cap semantics for a
   non-zero `max_collects`, **the expansion tile-to-cell geometry** (new evidence, not a
   derivation), and the internal `TownState.Resources.coins` alias.
5. **No bound on the on-demand `goals` list and no membership test on `set_quest_var`** — both
   are Server v1 / M13 gaps the quests line deliberately left unfilled because the legacy branches
   have neither.
6. **Pin line endings for committed evidence.** Two separate defects in this project were
   byte-sensitive guards that pass on an LF checkout and fail on a CRLF one, and both were
   **fixed rather than re-run**: `test_collection_endpoint.py`'s whole-document comparison
   against a second `/v0/session` call, and the `stat().st_size` comparison in
   `test_unit_xp_fixture.py`. A measurement established that every prior fixture verifies by
   **sha256**, which is line-ending invariant, so those two were the only instances. The
   durable fix is `/tests/fixtures/** text eol=lf` (and the same for the
   `apps/client-godot/evidence/**` report JSONs) in `.gitattributes`, so committed evidence has
   exactly **one** byte form and this class of defect cannot recur. Relatedly, have the
   `test_project_scope.gd` source walk skip `__pycache__`.

**Discipline carried forward, with seven data points:** *measure every figure before asserting
it* — **eighteen of my own investigation figures** were asserted rather than measured or miscounted
across the eleven lines, and on this milestone's last line **five more were found and corrected**,
every one by someone else measuring it; *verify a worker's claim and reject it when wrong* — the
implementation worker on that line corrected my brief on **seven** points and was right on all
seven, which is the counter-example that keeps the habit honest in both directions; *prefer a public
accessor* over a private-state reach; *prefer a boundary assertion over a repository-wide absence*;
*inspect battery logs rather than exit codes*, which is what identified the two engine flakes as
flakes; and *test a guard rather than trusting it*. **Two process errors are disclosed above** — a
squash merge (#209) and one direct push to `main` (`41fc708`) — both from chaining git operations
into a block whose prerequisite step was not written out. Branch, commit, and push are now run as
separate verified steps. **A third, disclosed here:** my own `write_delta` helper wrote each delta
file *before* asserting its shape, so an early failing run left a corrupted `godot-building-sell`
delta in the tree; it was caught by reading the file rather than trusting the exit code, and
regenerated from the main spec. The helper was a temporary script, but the lesson is the standing
one — **assert before writing, and read the artifact, not the code.** The quests line added the
sharpest instance of it, so the lesson is now also enforced in the sync routine: **assert a delta's
shape before writing any of it**, and assert the target requirement counts **before and after**,
never after only.

**A fourth discipline point, earned on the quests line:** *know what a suite structurally cannot
detect.* 1223 hermetic checks passed while the live phase failed five separate times, because the
offline suite builds its own response envelope and therefore cannot see envelope or wire drift at
all. The suite now asserts that it builds no request body and records why, so the next line does
not have to rediscover the blind spot — **and the guard for that class is a live phase, which is a
single phase, so it is one failure away from being the only thing standing between the client and
the wire.**

**Known-flaky guard, five surfaces now:** `verify-boot.ps1` can fail on a `^ERROR:` line that is only an engine
shutdown RID-leak warning or a transient Windows module-load crash; re-run and inspect
`.godot/verify-boot/*.txt` before treating it as a regression. `verify.ps1` is also
display-sensitive through its windowed-capture step and returned **-1** on one of two runs and **0**
with `PASS all checks succeeded` on the second; re-run it too.

### Process disclosure (recorded 2026-10-01, orchestrator)

**PR #209, the `unit-instances` proposal, was squash-merged as `0710038` instead of with a
merge commit**, against the rule that OpenSpec and development PRs use merge commits only.
The cause was the orchestrator chaining a stray `gh pr merge --squash` into a command block it
intended to suppress.

**Impact, measured rather than assumed:** `0710038` has a single parent, so the merge commit
recording the PR is absent; its **tree is byte-identical** to the branch commit `dacda10`
(`918d3c`), the branch carried exactly **one** commit so no individual commit was destroyed,
and the branch was still on origin when measured. **No code, spec, or documentation was
lost.** What was lost is the branch topology in the history.

**Disposition:** the user chose to **record the deviation and continue** rather than rewrite
published `main` history, which would have required a force-push the project rules forbid
without explicit authorization. The squash stands on the permanent record, this disclosure
accompanies it, and **every subsequent PR used a merge commit** — #210 (`02dbfa6`) and #211
(`84f7af9`) are both proper merge commits.


### Process disclosure (second entry, recorded 2026-10-01, orchestrator)

**One commit was pushed directly to `main`, bypassing the branch-and-PR workflow.**
It was `docs: refresh the roadmap resume point for M8 line 5` (`41fc708`), a
documentation-only resume-point refresh, and it was the result of chaining a
`git push origin main` into the same command block that had just committed it — the branch
step was omitted by oversight rather than chosen.

**Impact:** the content is correct and was verified before pushing, and no code, spec, fixture,
or legacy byte was involved. But it is a **workflow violation** — every repository-mutating
stage is supposed to reach `main` through a remote branch and a merge-commit PR, so this one
commit has no PR and no merge commit.

**Disposition:** recorded here rather than papered over, and no force-push or history rewrite
was attempted. Every subsequent stage follows the workflow. This is the **second** process
error of this kind in this run — the first was the squash-merge recorded above — and both
were the same root cause: chaining a git operation into a command block where the
prerequisite step was not written out. The discipline that follows is to run branch, commit,
and push as **separate, explicitly verified** steps rather than one chained block.
## Stage A — Preserve the Current Implementation

```text
Flash Client
    │
    │ SWLoader.swf
    │ Basesec_*.swf
    │ FlashVars
    │ Legacy HTTP / form requests / AMF-era behavior
    ▼
Legacy Flask Server
    │
    ├── server.py
    ├── command.py
    ├── sessions.py
    ├── engine.py
    ├── get_player_info.py
    └── get_game_config.py
    │
    ▼
JSON Save Files
```

This implementation remains operational as the **behavioral oracle**.

Do not dismantle it during the first stages of development.

---

## Stage B — Flash-Free Compatibility Architecture

The first major target architecture should be:

```text
Godot Client
    │
    │ Modern JSON API
    ▼
Compatibility API v0
    │
    │ translates modern requests
    │ into legacy semantics
    ▼
Legacy Game Logic
    │
    ▼
JSON Save Files
```

At this stage:

- Flash Player is no longer required.
- The Godot client does not execute SWFs.
- The user can play through the modern client.
- Existing game behavior is preserved.
- Existing saves can still be loaded.
- Existing Python logic remains the behavioral reference.
- PostgreSQL is not yet required.
- Public account infrastructure is not yet required.

This should be achieved **before rewriting the backend**.

---

## Stage C — Production Architecture

The eventual production architecture becomes:

```text
Godot Client
    │
    │ HTTPS / JSON
    │ WebSocket only where justified
    ▼
Server API v1
    │
    ├── Authentication
    ├── Town Domain
    ├── Economy Domain
    ├── Buildings Domain
    ├── Units Domain
    ├── Inventory Domain
    ├── Research Domain
    ├── Quest Domain
    ├── Collections Domain
    ├── Missions Domain
    ├── Combat Domain
    └── Social Domain
    │
    ▼
PostgreSQL
    │
    ├── durable player state
    ├── transaction ledger
    ├── progression
    ├── missions
    ├── social state
    └── migration metadata
```

Optional infrastructure can later include:

```text
Redis
WebSockets
Admin tooling
Metrics
Job processing
CDN
```

These should only be introduced when they solve a demonstrated problem.

---

# 2. Non-Negotiable Engineering Principles

These rules should guide the entire reconstruction.

## 2.1 Preserve Before Replacing

Never remove or rewrite legacy behavior until its behavior has been:

1. observed,
2. documented,
3. recorded,
4. tested,
5. reproduced by the replacement.

---

## 2.2 Do Not Delete Original Data

Never destroy:

- SWFs
- JSON configuration
- existing saves
- images
- sounds
- XML files
- game configuration
- protocol examples
- legacy server code

Move them later into archival directories if necessary, but preserve their original versions.

---

## 2.3 Preserve Git History

When reorganizing files, use:

```bash
git mv
```

rather than deleting and recreating files whenever practical.

---

## 2.4 Do Not Redesign Gameplay During Parity Work

The reconstruction phase is not the time to rebalance the game.

Avoid changing:

- resource costs,
- XP rewards,
- building times,
- combat formulas,
- quest requirements,
- unit stats,
- progression pacing,
- unlock requirements.

First reproduce the existing game.

Improvements can happen later.

---

## 2.5 Never Rewrite Client and Server Semantics Simultaneously

A dangerous migration would be:

```text
Flash → Godot
Flask → completely different server
JSON saves → PostgreSQL
Legacy protocol → new protocol
```

all at once.

That would make behavioral regressions extremely difficult to diagnose.

Instead:

```text
Preserve server
    ↓
Replace client
    ↓
Verify parity
    ↓
Replace server internals
    ↓
Verify parity again
```

---

## 2.6 Every Migrated Feature Needs a Legacy Fixture

Before replacing a feature, capture examples of:

```text
request
before state
response
after state
```

These become golden-master tests.

---

## 2.7 Preserve Legacy IDs

Existing IDs used by:

- buildings,
- units,
- items,
- quests,
- research,
- collections,
- missions,
- effects,
- animations,
- assets

should remain stable.

The production database may use internal primary keys, but original IDs should be stored as:

```text
legacy_id
```

where appropriate.

---

## 2.8 Production Server Owns the Truth

The future server must be authoritative.

The client sends **intent**, not final state.

Bad:

```json
{
  "coins": 999999,
  "xp": 10000
}
```

Good:

```json
{
  "building_id": "barracks_01",
  "x": 24,
  "y": 17
}
```

The server determines:

```text
Is the building unlocked?
Does the player have enough resources?
Is placement valid?
What does it cost?
How much XP is awarded?
When does construction finish?
What state should be written?
```

---

## 2.9 SWF Files Become Archival References

The final runtime must not rely on:

- Adobe Flash Player
- Ruffle
- ActionScript runtime
- SWLoader.swf
- Basesec SWFs
- sprite SWFs
- FX SWFs
- AMF
- FlashVars

SWFs may remain inside:

```text
legacy/
```

for preservation and reference.

They must not be required by the final game runtime.

---

# 3. Legacy Component Classification

The existing repository should be classified before significant restructuring.

| Component | Strategy | Purpose |
|---|---|---|
| `server.py` | KEEP + FREEZE | Legacy HTTP behavior oracle |
| `sessions.py` | KEEP → REWRITE LATER | Save/session semantics |
| `command.py` | KEEP + DECOMPOSE | Primary game behavior specification |
| `engine.py` | AUDIT + EXTRACT | Reusable calculations where possible |
| `get_game_config.py` | KEEP + NORMALIZE | Content/configuration source |
| `get_player_info.py` | KEEP → REPLACE | Player bootstrap behavior |
| AMF/form protocol | LEGACY ONLY | Compatibility/reference |
| `templates/play.html` | ARCHIVE | Flash bootstrap |
| `SWLoader.swf` | ARCHIVE | Flash loader |
| `Basesec_*.swf` | ARCHIVE | Legacy client implementation |
| PNG/JPG assets | KEEP | Direct reusable content where legally permitted |
| MP3/audio assets | KEEP/CONVERT | Runtime audio source |
| SWF sprites | CONVERT | Godot-compatible assets |
| SWF effects | CONVERT/RECREATE | Godot effects |
| JSON game config | KEEP + VALIDATE | Canonical content source |
| JSON saves | KEEP + MIGRATE | Golden fixtures and migration source |

---

# 4. Target Repository Structure

Do not immediately restructure everything.

During early development the repository can gradually move toward:

```text
social-wars-legacy/
├── apps/
│   ├── client-godot/
│   ├── compat-v0/
│   └── server-v1/
│
├── packages/
│   └── game-content/
│       ├── raw/
│       ├── normalized/
│       ├── schemas/
│       └── generated/
│
├── tools/
│   ├── protocol-recorder/
│   ├── protocol-replay/
│   ├── state-diff/
│   ├── asset-pipeline/
│   ├── content-builder/
│   └── save-migrator/
│
├── tests/
│   ├── fixtures/
│   ├── golden/
│   ├── saves/
│   ├── integration/
│   ├── migration/
│   └── visual/
│
├── docs/
│   ├── architecture/
│   ├── legacy-protocol/
│   ├── game-systems/
│   ├── assets/
│   ├── migrations/
│   └── adr/
│
├── legacy/
│   ├── server/
│   ├── flash/
│   ├── assets/
│   └── saves/
│
└── README.md
```

Initially keep the existing structure intact.

Move legacy components only after the migration tooling and modern directories are established.

---

# 5. Phase 0 — Freeze and Preserve the Legacy Baseline

## Objective

Create a reproducible snapshot of the working legacy implementation before modifying architecture.

---

## Tasks

Create a Git tag:

```bash
git tag legacy-baseline
```

Document:

- Python version
- dependency versions
- operating system requirements
- startup procedure
- default ports
- required environment configuration
- directory expectations
- Flash client startup flow
- default player/save
- known bugs
- known broken features
- known incomplete features
- asset versions
- EXT_VERSION or equivalent content version
- expected URLs
- expected game bootstrap process

---

## Create Asset Hash Manifest

Generate SHA-256 hashes for:

```text
*.swf
*.json
*.xml
*.png
*.jpg
*.jpeg
*.mp3
*.wav
*.gif
```

Example:

```json
{
  "path": "assets/flash/SWLoader.swf",
  "sha256": "...",
  "size": 123456
}
```

This provides a permanent record of the original artifact set.

---

## Create Canonical Save Fixtures

Preserve multiple representative saves.

Recommended fixtures:

```text
tests/saves/fresh-player.json
tests/saves/early-game.json
tests/saves/mid-game.json
tests/saves/late-game.json
tests/saves/stress-town.json
```

Try to include:

### Fresh Player

- tutorial state
- starter buildings
- starter units
- starter currencies

### Early Game

- construction
- basic unit queues
- first quests

### Mid Game

- research
- collections
- larger inventory
- multiple zones

### Late Game

- advanced unlocks
- missions
- high-level buildings
- advanced units

### Stress Town

- dense town
- many buildings
- many units
- many queued operations
- large inventory

---

## Deliverables

```text
docs/legacy-baseline.md
docs/known-legacy-bugs.md
tests/saves/
tools/hash-manifest/
legacy-manifest.json
```

---

## Exit Criteria

The legacy game can be reproduced from a clean environment using documented instructions.

---

# 6. Phase 1 — Build the Legacy Protocol Recorder

This is one of the most important phases of the entire project.

## Objective

Turn the legacy implementation into an observable behavioral specification.

---

## Capture

For every request:

```text
timestamp
endpoint
HTTP method
request body
parsed command
player ID
session ID where appropriate
state before
response
state after
HTTP status
execution duration
```

---

## Important Rule

Instrumentation must not change behavior.

The recorder should observe the legacy system, not rewrite it.

---

## Golden Fixture Structure

Example:

```text
tests/golden/building-buy/
├── request.json
├── before.json
├── response.json
└── after.json
```

Other fixture examples:

```text
tests/golden/building-move/
tests/golden/unit-order/
tests/golden/collect-income/
tests/golden/start-research/
tests/golden/claim-quest/
tests/golden/mission-attack/
```

---

# 7. Build an Exhaustive Legacy Command Catalog

`command.py` is effectively a major portion of the existing game specification.

Create:

```text
docs/legacy-protocol/commands.md
```

or preferably a machine-readable catalog plus generated documentation.

Each command should include:

```text
Command name
Domain
Endpoint
Required parameters
Optional parameters
State read
State modified
Resources consumed
Rewards produced
Timers created
Dependencies
Client-trusted fields
Security concerns
Observed fixtures
Replacement API
Migration status
```

---

## Suggested Status Values

```text
UNOBSERVED
CAPTURED
DOCUMENTED
V0_SUPPORTED
V1_SUPPORTED
PARITY_VERIFIED
RETIRED
OUT_OF_SCOPE
```

---

## Example

```yaml
command: buy
domain: buildings
status: CAPTURED

inputs:
  - building_id
  - x
  - y

reads:
  - player.resources
  - player.level
  - town.objects
  - town.zones

writes:
  - player.resources
  - town.objects
  - player.xp

security:
  legacy_client_trust: high

replacement:
  endpoint: POST /v1/towns/me/buildings
```

---

# 8. Phase 2 — Define the Canonical Domain Model

Before building extensive modern code, define the conceptual game model.

Core domain objects should include:

```text
Player
Town
Map
Zone
TownObject
Building
Decoration
Unit
UnitInstance
Resource
InventoryItem
InventoryStack
ProductionQueue
Research
Quest
QuestObjective
Collection
Mission
Battle
Friend
Visit
Reward
Event
ContentDefinition
```

---

# 9. Separate Definitions From Player State

This distinction is extremely important.

## Definition Data

Shared static game content:

```text
Barracks
cost = 500 coins
build_time = 60
footprint = 3x3
required_level = 5
```

---

## Player Instance State

Player-owned object:

```text
instance_id = 8937
definition_id = barracks
x = 24
y = 17
level = 2
construction_ready_at = ...
```

Never merge these concepts.

Use patterns similar to:

```text
BuildingDefinition
BuildingInstance

UnitDefinition
UnitInstance

QuestDefinition
QuestProgress
```

---

# 10. Phase 3 — Build Canonical Game Content

Create a normalized content package.

```text
packages/game-content/
├── raw/
├── normalized/
│   ├── buildings.json
│   ├── units.json
│   ├── items.json
│   ├── quests.json
│   ├── research.json
│   ├── collections.json
│   └── missions.json
├── schemas/
│   ├── building.schema.json
│   ├── unit.schema.json
│   ├── quest.schema.json
│   └── ...
├── generated/
└── manifest.json
```

---

## Requirements

Every content definition should preserve:

```text
legacy_id
source
content version
asset references
dependencies
```

---

## Validate Content

The content builder should detect:

```text
duplicate IDs
unknown references
missing assets
invalid costs
invalid requirements
broken quest dependencies
broken research dependencies
missing unit references
missing building references
missing reward references
```

---

# 11. Phase 4 — Build the SWF Asset Migration Pipeline

Do not manually convert assets without tracking them.

Create a central asset registry.

---

## Asset Registry Fields

Each asset should track:

```text
source SWF
source hash
symbol/class name
legacy asset ID
category
dimensions
registration point
pivot
frame count
frame rate
frame labels
nested MovieClips
masks
blend modes
color transforms
filters
scale grids
ActionScript dependencies
output path
Godot resource
conversion status
notes
```

---

## Example

```yaml
legacy_id: building_barracks_01

source:
  file: assets/sprites/buildings.swf
  symbol: Barracks01

type: building

dimensions:
  width: 270
  height: 220

registration:
  x: 135
  y: 198

animation:
  frames: 12
  fps: 24

conversion:
  status: converted
  output: assets/runtime/buildings/barracks_01/
```

---

# 12. Preserve Important Flash Rendering Semantics

Asset conversion can easily become visually incorrect if these are ignored:

- registration points
- pivots
- nested MovieClips
- masks
- alpha
- color transforms
- blend modes
- shadows
- glow filters
- scale grids
- tween timing
- frame labels
- transform inheritance
- morph animations
- ActionScript-controlled states

These should be documented per asset where relevant.

---

# 13. Asset Conversion Mapping

Recommended mappings:

| Legacy Asset | Modern Replacement |
|---|---|
| Static bitmap | PNG / WebP |
| Vector icon | SVG or rasterized texture |
| Simple MovieClip | SpriteFrames |
| Complex animation | AnimationPlayer |
| Unit animation | AnimatedSprite2D / AnimationPlayer |
| UI panel | TextureRect / NinePatchRect |
| Flash scale-grid UI | NinePatchRect |
| MovieClip hierarchy | Godot scene |
| Flash particle effect | GPUParticles2D |
| Complex FX | Godot shader / scene animation |
| MP3 | OGG/WAV |
| Flash button | Godot Control/Button scene |

---

## Asset Directory Separation

Never overwrite original assets.

Use:

```text
assets/raw/
assets/converted/
assets/runtime/
```

or equivalent.

---

# 14. Asset Conversion Priorities

Do not attempt to convert every asset before the game runs.

Suggested order:

```text
1. Terrain
2. One building
3. One unit
4. Essential HUD
5. Selection indicators
6. Placement grid
7. Common buildings
8. Common units
9. Common UI
10. Combat effects
11. Missions
12. Rare content
13. Special events
```

---

# 15. Phase 5 — Initialize the Godot Client

Use a pinned stable Godot 4.x version.

Document it in:

```text
apps/client-godot/README.md
```

---

## Recommended Language

Use **GDScript initially** unless there is a strong reason to use C#.

Reasons:

- quickest Godot iteration
- excellent engine integration
- simpler deployment
- appropriate for UI-heavy and scene-heavy work
- easier contributor setup

C# can still be introduced later for specific systems if justified.

---

# 16. Suggested Godot Structure

```text
apps/client-godot/
├── project.godot
│
├── scenes/
│   ├── boot/
│   ├── town/
│   ├── buildings/
│   ├── units/
│   ├── missions/
│   └── ui/
│
├── scripts/
│   ├── core/
│   ├── networking/
│   ├── domain/
│   └── utils/
│
├── assets/
│
└── tests/
```

---

# 17. Godot Autoloads

Keep global singletons limited.

Potential autoloads:

```text
App
GameApi
Session
ContentRegistry
GameClock
Settings
AudioManager
```

Avoid creating a giant global `GameManager` containing every system.

---

# 18. Critical GameApi Abstraction

The Godot UI should never directly know about:

```text
command.php
AMF
FlashVars
form encoding
legacy URLs
legacy command names
```

Create an abstraction such as:

```gdscript
class_name GameApi
```

with operations similar to:

```text
get_bootstrap()
get_player()
get_town()

buy_building()
move_building()
sell_building()
upgrade_building()
collect_building()

order_unit()
cancel_unit_order()
collect_unit()

start_research()
cancel_research()
claim_research()

start_quest()
claim_quest()

start_mission()
attack_target()
```

---

## Initial Implementation

```text
LegacyV0Api
```

Later:

```text
ServerV1Api
```

The rest of Godot should not care which implementation is active.

---

# 19. Phase 5.5 — Compatibility API v0

Create a modern-facing API in front of the legacy server.

For example:

```http
POST /v0/buildings/buy
```

Request:

```json
{
  "building_id": "barracks",
  "x": 24,
  "y": 17
}
```

Internally:

```text
Compatibility API
    ↓
translate request
    ↓
legacy command semantics
    ↓
legacy response
    ↓
normalize
    ↓
Godot response
```

---

## Benefits

Godot never needs to implement:

```text
legacy form encoding
command.php specifics
Flash-oriented request structures
AMF
FlashVars
```

When Server v1 arrives, only the API implementation changes.

---

# 20. Phase 6 — First Flash-Free Vertical Slice

This is the first major development target.

Do not wait for full game parity.

---

## Required Flow

```text
Launch Godot
    ↓
Connect to compatibility server
    ↓
Load game configuration
    ↓
Load player
    ↓
Load town
    ↓
Render terrain
    ↓
Render buildings
    ↓
Render at least one unit
    ↓
Display HUD resources
    ↓
Allow camera movement
    ↓
Allow object selection
```

---

## Vertical Slice Requirements

### Bootstrap

Implement:

```text
configuration loading
player loading
town loading
content registry
session initialization
```

---

### Town Renderer

Implement:

```text
isometric grid
grid-to-screen conversion
screen-to-grid conversion
camera movement
zoom
town bounds
depth sorting
object footprint handling
selection
HUD
```

---

### First Building

Convert one real building.

Support:

```text
load
render
select
move
```

---

### First Unit

Convert one real unit.

Support:

```text
load
render
idle animation
select
```

---

# 21. First Major Gate

The following must work on a machine with:

```text
NO Adobe Flash
NO Ruffle
NO Flash plugin
NO ActionScript runtime
```

Godot should:

```text
launch
load an existing save
load game content
render town terrain
render buildings
render units
render HUD
pan camera
zoom camera
select objects
```

Once this works, the reconstruction has passed its first critical milestone.

---

# 22. Phase 7 — Building System Parity

Implement building functionality in dependency order.

```text
1. Load existing town objects
2. Select objects
3. Placement preview
4. Grid validation
5. Buy building
6. Construction
7. Move
8. Flip / rotate where applicable
9. Store
10. Restore
11. Upgrade
12. Sell
13. Remove
14. Unlock zones
15. Clear obstacles
16. Collect resources
```

---

# 23. Placement System Requirements

The town grid must properly understand:

```text
multi-tile footprints
town bounds
locked zones
occupied tiles
collision rules
placement previews
object pivots
base tile positions
selection hitboxes
orientation
depth sorting
```

Do not use texture dimensions as gameplay footprint dimensions.

A large image may occupy only a small number of logical tiles.

---

# 24. Isometric Coordinate Tests

Create automated tests for:

```text
grid → screen
screen → grid
negative coordinates
boundary coordinates
large coordinates
multi-tile footprints
camera transformations
zoom transformations
```

This logic will affect almost every town interaction.

---

# 25. Phase 8 — Economy and Timer Systems

Reconstruct:

```text
coins
resources
premium currency
XP
building income
production
construction
cooldowns
collections
rewards
```

---

# 26. Server-Based Timer Model

Never trust the client clock.

Server responses should include:

```json
{
  "server_time": 1789257600,
  "ready_at": 1789257900
}
```

The client computes a server offset.

---

## Persist Timers As State

Prefer:

```text
started_at
duration
ready_at
```

over creating one background worker for every timer.

---

# 27. Economy Invariants

Create tests such as:

```text
resource balances never become invalid
premium currency cannot be duplicated
purchases cannot execute without sufficient resources
rewards cannot be claimed twice
collect cannot execute before timer completion
client clocks cannot skip timers
```

---

# 28. Economy Ledger

For the production server, important currency mutations should create ledger entries.

Example fields:

```text
player_id
resource
amount
reason
related_entity
balance_before
balance_after
timestamp
request_id
```

This is especially important for:

```text
premium currency
quest rewards
mission rewards
admin grants
migration adjustments
purchases
```

---

# 29. Phase 9 — Inventory and Crafting

Implement:

```text
load inventory
add item
remove item
buy item
consume item
store item
activate item
deactivate item
craft
recycle
expiry
gift-related inventory behavior
```

---

## Inventory Invariants

```text
quantity >= 0
cannot consume missing item
cannot claim reward twice
crafting inputs removed atomically
crafting output added atomically
unknown definitions rejected or preserved during migration
```

---

# 30. Phase 10 — Unit Systems

Separate:

```text
UnitDefinition
UnitInstance
```

---

## Unit Definition

Contains shared data such as:

```text
unit type
health
damage
movement speed
animation references
production time
cost
unlock requirements
```

---

## Unit Instance

Contains:

```text
instance ID
definition ID
current health
position
state
energy
temporary effects
```

---

## Reconstruct

```text
unit loading
production
queues
queue cancellation
queue collection
town movement
idle animation
walking animation
attack animation
damage
death
energy
revive
healing
special behaviors
```

---

# 31. Phase 11 — Player Progression

Implement:

```text
XP
levels
level rewards
unlocks
tutorial state
objectives
challenges
progress flags
```

---

## Server Owns Unlock Logic

Do not simply trust:

```text
client says player reached level X
```

Server calculates progression.

---

# 32. Phase 12 — Quest System

Model quests explicitly.

Example:

```text
QuestDefinition
├── prerequisites
├── objectives
└── rewards

QuestProgress
├── state
├── objective progress
├── started_at
└── completed_at
```

---

## Objective Types

Potential objective types:

```text
build
upgrade
collect
produce
own
spend
earn
mission
combat
research
craft
visit
help
level
```

Do not hardcode every quest as custom logic if generic objective types can represent it.

---

# 33. Phase 13 — Research System

Implement:

```text
research definitions
requirements
prerequisites
research costs
research timers
start research
cancel research
complete research
unlock effects
```

Completed research must remain permanently recorded.

---

# 34. Phase 14 — Collection System

Model separately:

```text
CollectionDefinition
CollectionProgress
CollectionReward
```

Support:

```text
item acquisition
collection progress
collection completion
reward claim
```

Reward claiming must be transactional and one-time.

---

# 35. Phase 15 — Missions and Combat

Start by reproducing compatibility behavior.

Later transition combat to server authority.

---

## Bad Combat API

```json
{
  "target_hp": 0,
  "reward": 500
}
```

This trusts the client.

---

## Correct Combat Intent

```json
{
  "attacker_id": "unit-123",
  "target_id": "enemy-456",
  "action": "attack"
}
```

Server determines:

```text
attacker exists
target exists
mission active
attacker alive
target alive
range valid
cooldown valid
energy valid
damage amount
critical result
death result
reward result
```

---

# 36. Prefer Deterministic Action-Based Combat

Social Wars does not necessarily require MMO-style server simulation.

A simpler model:

```text
initial state
+
player action
+
game rules
=
result
+
state mutation
+
combat event
```

The Godot client animates the server result.

This makes:

```text
testing
replay
anti-cheat
debugging
migration
```

significantly easier.

---

# 37. Combat Event Log

Eventually record events such as:

```text
mission_id
action_number
attacker
target
action_type
damage
critical
status_effect
resulting_hp
timestamp
```

Useful for:

```text
debugging
replay
analytics
anti-cheat
support
```

---

# 38. Phase 16 — Social Systems

Reconstruct:

```text
friends
friend scores
visits
visit rewards
help mechanics
neighbor mechanics
leaderboards
social rewards
```

The production server must own social relationship state.

---

# 39. Phase 17 — Special and Rare Legacy Systems

`command.py` contains behavior outside the main town loop.

Examples that should be explicitly audited include:

```text
SOC/event systems
temporary events
rider mechanics
penguin mechanics
dive mechanics
superspy mechanics
rage mechanics
hero mechanics
special powers
temporary items
special crafting
special buildings
event progression
event-specific currencies
```

These should not block the first playable modern client.

However, each one must eventually receive one of:

```text
IMPLEMENTED
PARITY_VERIFIED
OUT_OF_SCOPE
RETIRED
```

Do not silently forget them.

---

# 40. Phase 18 — Begin Server API v1

Only begin this stage when the Godot client is substantially functional through Compatibility API v0.

---

# 41. Recommended Production Backend Stack

Because the existing game logic is Python, a practical target is:

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
PostgreSQL
Pytest
```

Optional later:

```text
Redis
background jobs
WebSockets
```

---

## Why Not Immediately Rewrite to NestJS?

A NestJS rewrite would simultaneously introduce:

```text
new language
new framework
new architecture
new persistence model
new game client
```

without materially helping the reconstruction.

Keeping Python initially allows legacy algorithms and knowledge to be migrated incrementally.

NestJS remains viable if there is a strong organizational reason to standardize on TypeScript.

---

# 42. Server v1 Domain Structure

Example:

```text
apps/server-v1/
├── api/
│   └── v1/
│
├── domain/
│   ├── players/
│   ├── towns/
│   ├── economy/
│   ├── buildings/
│   ├── units/
│   ├── inventory/
│   ├── research/
│   ├── quests/
│   ├── collections/
│   ├── missions/
│   ├── combat/
│   └── social/
│
├── services/
├── repositories/
├── infrastructure/
├── migrations/
└── tests/
```

---

# 43. Do Not Recreate `command.py`

The giant legacy command dispatcher should not become:

```text
/v1/command
```

forever.

Replace it with domain-oriented APIs.

Examples:

```http
GET /v1/bootstrap

GET /v1/towns/me

POST /v1/towns/me/buildings

POST /v1/towns/me/buildings/{id}/move

POST /v1/towns/me/buildings/{id}/upgrade

POST /v1/towns/me/buildings/{id}/collect

POST /v1/units/queues

DELETE /v1/units/queues/{id}

POST /v1/research/{id}/start

POST /v1/quests/{id}/claim

POST /v1/missions/{id}/start

POST /v1/missions/{id}/actions
```

---

# 44. Authoritative Server Rule

The legacy implementation may trust client-provided state changes.

The production implementation must not.

For example:

```text
Client:
"Build Barracks at tile 24,17"
```

Server:

```text
1. Load player state.
2. Load building definition.
3. Validate player level.
4. Validate unlock.
5. Validate prerequisites.
6. Validate town zone.
7. Validate placement.
8. Validate resource balance.
9. Calculate price.
10. Deduct resources.
11. Create building instance.
12. Calculate XP.
13. Start construction timer.
14. Increment state revision.
15. Commit transaction.
16. Return authoritative result.
```

---

# 45. PostgreSQL Data Model

Potential tables:

```text
accounts
players
towns
town_zones
town_objects
buildings
unit_instances
unit_queues
inventory_items
inventory_stacks
player_resources
economy_ledger
research_progress
quest_progress
objective_progress
collection_progress
missions
mission_sessions
combat_events
friendships
friend_visits
player_unlocks
content_versions
migration_runs
audit_events
```

Exact schema should follow discovered legacy behavior rather than being finalized prematurely.

---

# 46. Use JSONB Carefully

JSONB is useful for:

```text
unknown legacy fields
migration metadata
rare event payloads
temporary compatibility state
```

Do not simply move the entire old village JSON into one giant PostgreSQL JSONB column and call the migration complete.

Core production state should become structured.

---

# 47. Concurrency Protection

Use player or town revision numbers.

Example:

```json
{
  "expected_revision": 73
}
```

Server compares this against current revision.

If stale:

```http
409 Conflict
```

Client then resynchronizes.

---

# 48. Idempotency

Commands such as:

```text
purchase
collect
claim
craft
mission reward
premium transaction
```

must tolerate network retries.

Use:

```http
Idempotency-Key: UUID
```

If the same request is retried, the server should return the previous result instead of executing it twice.

---

# 49. Database Transactions

Operations that modify multiple pieces of state must be atomic.

Example building purchase:

```text
deduct coins
create building
award XP
update quest objective
write economy ledger
increase revision
```

All should succeed or fail together.

---

# 50. Phase 19 — Legacy Save Migration

Build a dedicated save migration CLI.

Example:

```bash
socialwars-migrate inspect old-save.json

socialwars-migrate validate old-save.json

socialwars-migrate import old-save.json

socialwars-migrate verify old-save.json
```

---

## Support Dry Runs

```bash
socialwars-migrate import old-save.json --dry-run
```

Dry-run output should show:

```text
player detected
resources detected
objects detected
units detected
inventory detected
quests detected
research detected
collections detected
unknown fields detected
validation errors
planned database mutations
```

---

# 51. Save Validation

Check:

```text
known object IDs
known unit IDs
known item IDs
known research IDs
known quests
known collections
resource validity
town positions
map bounds
object overlap
duplicate object IDs
duplicate unit IDs
queue state
timestamps
timer validity
unknown fields
```

---

# 52. Never Silently Drop Unknown Save Data

Unknown legacy fields should be retained somewhere like:

```text
legacy_extra
```

during migration.

This allows future investigation instead of destructive loss.

---

# 53. Migration Must Be Idempotent

Track:

```text
source save hash
migration version
player
import timestamp
migration status
```

Re-importing the same file should not duplicate objects or rewards.

---

# 54. Phase 20 — Authentication and Security

For local preservation mode, complex authentication may not be required.

For public hosting, implement proper account security.

---

## Required Production Measures

```text
no hardcoded secrets
environment-based secrets
HTTPS
secure password hashing where applicable
session expiry
refresh token rotation
request validation
rate limiting
payload limits
authorization checks
audit logging
server-side economy validation
server-side combat validation
server-side ownership validation
```

---

# 55. Local and Online Modes

The architecture could eventually support both.

## Preservation / Offline Mode

```text
Godot
    ↓
Local Compatibility Server
    ↓
Local Save
```

---

## Online Mode

```text
Godot
    ↓
Server API v1
    ↓
PostgreSQL
```

Because both use `GameApi`, the game client can avoid duplicating most gameplay/UI code.

---

# 56. Testing Strategy

Testing is essential because the goal is reconstruction rather than merely writing a similar game.

---

# 57. Golden-Master Tests

For each legacy operation compare:

```text
legacy before
legacy request
legacy response
legacy after
```

against the modern implementation.

Verify:

```text
resource mutations
object mutations
timers
XP
rewards
progression
queues
inventory
mission state
```

---

# 58. Replay Tests

Create gameplay sequences.

Example:

```text
load fresh player
buy building
move building
collect resource
order unit
collect unit
start research
claim research
complete quest
start mission
attack enemy
claim mission reward
```

Run the same sequence against:

```text
Legacy Server
Compatibility API v0
Server API v1
```

Compare state transitions.

---

# 59. Game Invariant Tests

Important invariants:

```text
resources remain valid
premium currency cannot duplicate
object IDs remain unique
unit IDs remain unique
buildings cannot overlap illegally
buildings cannot enter locked zones
queues respect capacity
rewards cannot be claimed twice
completed research remains completed
dead units cannot attack
unowned units cannot be controlled
client clock cannot complete timers early
```

---

# 60. Network Failure Tests

Test:

```text
request timeout
duplicate request
lost response
reconnect
server restart
database rollback
stale revision
request retry
out-of-order response
expired session
content version mismatch
client version mismatch
```

---

# 61. Visual Regression Tests

Maintain reference scenes for:

```text
town layout
building placement
unit animation
combat
HUD
missions
dialogs
```

Compare:

```text
position
scale
pivot
frame
orientation
depth
spacing
```

---

# 62. Performance Testing

Create stress scenarios for:

```text
large towns
hundreds of town objects
many animated units
many simultaneous FX
rapid pan/zoom
large inventory
large content catalog
network bootstrap
save imports
```

Measure before optimizing.

---

## Likely Optimization Areas

```text
off-screen animation throttling
visibility culling
sprite atlases
object pooling
resource caching
lazy UI loading
asset streaming
batching
```

---

# 63. CI Pipeline

The project should eventually run automated CI for:

```text
legacy regression tests
Python linting
Python type checking
Server v1 unit tests
PostgreSQL integration tests
content schema validation
save migration tests
asset manifest validation
Godot headless project import
Godot tests
Godot build
runtime dependency inspection
```

---

# 64. Flash-Free CI Gate

Production packaging should fail if the runtime artifact contains:

```text
*.swf
Flash Player runtime
Ruffle runtime
ActionScript runtime
legacy Flash loader
```

The final client should not depend on them.

---

# 65. Release Artifact Separation

Produce separate artifacts:

```text
legacy-reference
client
server
content
save-migrator
```

The production client must not accidentally package:

```text
legacy/
```

---

# 66. Observability

Production Server v1 should implement structured logging.

Include:

```text
request ID
player ID
action ID
domain
duration
result
revision
```

without exposing sensitive data.

---

## Useful Metrics

```text
request rates
error rates
database latency
slow actions
migration failures
economy anomalies
combat failures
queue failures
content mismatches
```

---

# 67. Admin and Support Tools

Eventually provide tools for:

```text
player lookup
town inspection
resource inspection
inventory inspection
action history
migration history
economy ledger
grant resource with reason
revoke resource with reason
restore snapshot
disable account
inspect content version
```

A CLI is sufficient initially.

A web dashboard can come later.

---

# 68. Content Versioning

Track:

```text
client version
protocol version
content version
server version
```

Bootstrap may return:

```json
{
  "server_version": "1.3.0",
  "protocol_version": 1,
  "content_version": "2026.09.01",
  "minimum_client_version": "0.8.0"
}
```

---

# 69. Server Owns Gameplay Rules

Critical values such as:

```text
building costs
unit costs
XP rewards
mission rewards
research requirements
timers
unlock rules
combat values
```

must be validated from server-controlled content.

Do not trust client copies of these values.

---

# 70. WebSocket Policy

Do not introduce WebSockets simply because the architecture is modern.

Use normal HTTPS requests for:

```text
town actions
building actions
inventory
quests
research
collections
mission commands
```

Use WebSockets later only when useful for:

```text
presence
real-time social events
live announcements
true live multiplayer
push notifications while connected
```

---

# 71. Legal and Provenance Workstream

This should not be ignored.

Create:

```text
PROVENANCE.md
```

and an asset registry containing:

```text
asset
source
original filename
modified status
creator where known
rights status
redistribution status
notes
```

---

## Important Distinction

The repository being GPL does **not automatically mean** every original Social Wars:

```text
art asset
music asset
sound asset
trademark
character
proprietary Flash client component
```

is automatically redistributable under GPL.

Before publicly redistributing reconstructed proprietary assets, obtain appropriate legal review.

---

# 72. Keep Implementations Distinguishable

Maintain separation between:

```text
legacy original material
decompiled reference
converted assets
clean modern implementation
```

This helps:

```text
maintenance
provenance
licensing review
debugging
preservation
```

---

# 73. Definition of Truly Flash-Free

The project is not genuinely Flash-free merely because Adobe Flash Player is gone.

For this project, Flash retirement means:

- Godot is the runtime client.
- No SWF executes during gameplay.
- No ActionScript executes.
- No Flash Player is required.
- No Ruffle runtime is required.
- `SWLoader.swf` is not packaged.
- `Basesec_*.swf` is not packaged.
- Sprite SWFs have been converted or recreated.
- FX SWFs have been converted or recreated.
- Flash UI assets have been converted or recreated.
- FlashVars are gone from the modern client.
- AMF is not required by the modern client.
- A clean machine can install and play the game without Flash-related software.
- CI verifies no Flash runtime dependency exists.

Archived SWFs may still exist in:

```text
legacy/
```

for preservation purposes.

---

# 74. Milestone Roadmap

## M0 — Preservation

Deliver:

```text
legacy baseline tag
environment documentation
dependency lock
asset hashes
canonical saves
known bug documentation
```

Exit:

Legacy implementation is reproducible.

---

## M1 — Protocol Discovery

Deliver:

```text
endpoint catalog
command catalog
legacy request examples
state mutation documentation
```

Exit:

Normal gameplay no longer contains major unknown commands.

---

## M2 — Behavioral Tooling

Deliver:

```text
protocol recorder
protocol replay
state diff
golden fixture format
```

Exit:

Legacy behavior can be automatically captured and compared.

---

## M3 — Content Normalization

Deliver:

```text
normalized game configuration
schemas
content validator
dependency validation
content manifest
```

Exit:

Godot can load validated game definitions without parsing arbitrary legacy structures.

---

## M4 — Asset Pipeline

Deliver:

```text
asset registry
SWF extraction workflow
conversion tooling
one converted building
one converted unit
```

Exit:

At least one authentic building and unit render correctly in Godot.

---

## M5 — Godot Foundation

Deliver:

```text
Godot project
GameApi
LegacyV0Api
ContentRegistry
Session
GameClock
camera
basic UI foundation
Settings
AudioManager
```

Exit:

Client boots and communicates with Compatibility API.

---

## M6 — Town Vertical Slice

Deliver:

```text
existing save loading
terrain
town objects
one building
one unit
camera
zoom
selection
HUD
```

Exit:

A player can launch and view a real legacy town without Flash.

This is the **first major project success target**.

---

## M7 — Construction and Economy

Deliver:

```text
placement
purchase
move
sell
store
upgrade
construction timers
collect income
town expansion
resources
XP basics
```

Exit:

Core town-building gameplay loop works.

---

## M8 — Units

Deliver:

```text
unit definitions
unit instances
queues
production
collection
movement
animations
basic behaviors
```

Exit:

Core unit gameplay works.

---

## M9 — Progression

Deliver:

```text
XP
levels
quests
research
collections
tutorial/progression
```

Exit:

Primary long-term progression systems work.

---

## M10 — Missions and Combat

Deliver:

```text
mission loading
mission state
combat actions
damage
death
mission completion
rewards
```

Exit:

Primary combat loop works.

---

## M11 — Social and Special Systems

Deliver:

```text
friends
visits
scores
social rewards
legacy event systems
special mechanics
```

Exit:

All relevant legacy game systems are classified and implemented or explicitly excluded.

---

## M12 — Asset Parity

Deliver:

```text
all runtime-required SWFs converted or recreated
UI assets converted
FX replaced
animation gaps resolved
```

Exit:

Godot no longer depends on runtime SWFs.

---

## M13 — Server API v1

Deliver:

```text
FastAPI architecture
domain services
authoritative validation
modern API
GameApi ServerV1 implementation
```

Exit:

Godot can operate against the modern server.

---

## M14 — PostgreSQL

Deliver:

```text
database schema
Alembic migrations
repositories
transactions
economy ledger
revisions
idempotency
```

Exit:

Production state no longer depends on filesystem JSON.

---

## M15 — Save Migration

Deliver:

```text
save validator
save importer
dry-run mode
migration report
verification
legacy_extra preservation
```

Exit:

Legacy saves can be migrated safely into PostgreSQL.

---

## M16 — Production Hardening

Deliver:

```text
authentication
authorization
rate limiting
secure secrets
HTTPS readiness
observability
admin tooling
network resilience
CI
deployment
```

Exit:

Server architecture is ready for controlled public deployment.

---

## M17 — Flash Retirement

Deliver:

```text
runtime Flash dependency scan
final package verification
legacy archival separation
documentation update
```

Exit:

The production game runs without:

```text
Flash Player
Ruffle
ActionScript
SWF execution
AMF
FlashVars
```

---

# 75. Exact Feature Migration Dependency Order

Use this order when migrating gameplay:

```text
BOOT
    ↓
CONTENT
    ↓
PLAYER
    ↓
TOWN RENDERING
    ↓
BUILDINGS
    ↓
ECONOMY
    ↓
INVENTORY
    ↓
CRAFTING
    ↓
UNITS
    ↓
XP / LEVELS
    ↓
QUESTS
    ↓
RESEARCH
    ↓
COLLECTIONS
    ↓
MISSIONS
    ↓
COMBAT
    ↓
SOCIAL
    ↓
SPECIAL EVENTS
```

Do not migrate systems randomly.

---

# 76. Initial Implementation Backlog

This is the recommended first concrete backlog.

## Preservation

### 1. Create legacy baseline Git tag

```text
chore: create legacy baseline tag
```

### 2. Document legacy environment

```text
docs: document legacy runtime and startup process
```

### 3. Lock Python dependencies

```text
chore: lock legacy Python dependencies
```

### 4. Build SHA-256 asset manifest

```text
tooling: add legacy asset hash manifest generator
```

### 5. Create canonical save fixtures

```text
test: add canonical legacy save fixtures
```

---

## Behavioral Tooling

### 6. Implement protocol recorder

```text
tooling: record legacy request and response behavior
```

### 7. Implement village state diff

```text
tooling: add before/after village state differ
```

### 8. Implement command replay

```text
tooling: add legacy command replay runner
```

### 9. Generate endpoint catalog

```text
docs: catalog legacy server endpoints
```

### 10. Generate command catalog

```text
docs: catalog legacy game commands and mutations
```

---

## Domain and Content

### 11. Define canonical game domain model

```text
docs: define canonical Social Wars domain model
```

### 12. Create game-content package

```text
feat: initialize normalized game content package
```

### 13. Add schemas

```text
feat: add schemas for normalized game content
```

### 14. Build content validator

```text
tooling: validate normalized game content
```

---

## Godot Foundation

### 15. Initialize Godot project

```text
feat: initialize Godot client
```

### 16. Implement GameApi abstraction

```text
feat: add GameApi abstraction
```

### 17. Implement Compatibility API v0

```text
feat: initialize compatibility API v0
```

### 18. Implement bootstrap loading

```text
feat: load player and game bootstrap data
```

### 19. Implement ContentRegistry

```text
feat: add canonical content registry
```

### 20. Implement asset ID registry

```text
feat: map legacy assets to modern runtime assets
```

---

## Town Renderer

### 21. Implement isometric grid-to-screen conversion

```text
feat: implement isometric coordinate conversion
```

### 22. Implement screen-to-grid conversion

```text
feat: implement inverse isometric coordinate conversion
```

### 23. Add coordinate tests

```text
test: verify isometric coordinate conversions
```

### 24. Implement town camera

```text
feat: add town camera pan and zoom
```

### 25. Implement town bounds

```text
feat: add town map boundaries
```

### 26. Render terrain

```text
feat: render legacy town terrain
```

### 27. Render static town objects

```text
feat: render town objects from existing save
```

### 28. Implement Y/depth sorting

```text
feat: implement isometric object depth sorting
```

### 29. Implement selection

```text
feat: add town object selection
```

### 30. Implement HUD resources

```text
feat: display authoritative player resource HUD
```

---

## First Asset Migration

### 31. Convert first building

```text
assets: convert first legacy building
```

### 32. Render first real building

```text
feat: render converted building in town
```

### 33. Convert first unit

```text
assets: convert first legacy unit
```

### 34. Render first real unit

```text
feat: render converted legacy unit
```

### 35. Add unit idle animation

```text
feat: play converted unit idle animation
```

---

## First Flash-Free Gate

### 36. Create no-Flash vertical-slice test

Verify:

```text
Godot launches
no Flash runtime installed
no Ruffle installed
existing legacy save loads
town renders
terrain renders
buildings render
unit renders
HUD renders
camera works
selection works
```

This is the first major milestone to target.

---

# 77. Second Implementation Backlog

After the Flash-free town works, implement:

```text
building placement preview
grid validation
building purchase
building movement
building flip/orientation
building storage
building restoration
building selling
construction timer
building collection
town expansion
obstacle clearing
inventory loading
unit queue
unit production
unit collection
unit movement
```

---

# 78. Do Not Build These Early

Avoid spending early development time on:

```text
Flask → NestJS rewrite
PostgreSQL migration before Godot works
Kubernetes
microservices
Redis everywhere
WebSockets everywhere
complete UI redesign
game rebalancing
mobile support
custom launcher/updater
public account infrastructure
new multiplayer functionality
```

The first problem to solve is:

Can the existing Social Wars game be faithfully reconstructed and played through a modern client with no Flash dependency?

Everything else follows from that.

---

# 79. Major Technical Risks

## Risk 1 — Important Logic Exists Only in Compiled SWFs

Mitigation:

```text
protocol recording
decompilation/reference analysis
behavioral observation
golden-master testing
state-diff testing
```

---

## Risk 2 — SWF Animations Are More Complex Than Expected

Mitigation:

```text
asset registry
conversion priority
automated extraction where practical
manual recreation for complex assets
visual regression testing
```

---

## Risk 3 — Hidden/Obscure Commands Are Missed

Mitigation:

```text
generated command catalog
coverage tracking
protocol recording
fixture requirements
migration status tracking
```

---

## Risk 4 — Legacy Saves Are Inconsistent

Mitigation:

```text
multiple fixtures
strict validator
raw source preservation
legacy_extra
migration reports
```

---

## Risk 5 — Server Rewrite Changes Behavior

Mitigation:

```text
replay tests
golden tests
legacy-vs-v1 comparison
state-diff tooling
```

---

## Risk 6 — Client Cheating

Mitigation:

```text
authoritative server
economy ledger
server-side rules
ownership validation
revision checking
idempotency
```

---

## Risk 7 — Duplicate Rewards Due to Network Retries

Mitigation:

```text
database transactions
idempotency keys
unique constraints
revision validation
reward claim records
```

---

## Risk 8 — Flash Dependency Survives in Rare UI/FX

Mitigation:

```text
asset dependency manifest
CI package scanning
conversion status tracking
final Flash-free gate
```

---

## Risk 9 — Original Asset Distribution Restrictions

Mitigation:

```text
provenance tracking
asset classification
distribution review
legal review before public release
```

---

# 80. Success Checkpoints

## Checkpoint A — Preservation

Successful when:

```text
legacy environment reproducible
asset hashes created
canonical saves preserved
protocol recorder operational
```

---

## Checkpoint B — First Modern Client

Successful when:

```text
Godot starts without Flash
existing player loads
existing town loads
terrain renders
buildings render
units render
camera works
HUD works
selection works
```

---

## Checkpoint C — Main Gameplay

Successful when Godot supports:

```text
build
move
collect
train units
research
quests
collections
missions
combat
```

---

## Checkpoint D — Legacy Parity

Successful when:

```text
all relevant command.py behavior classified
major replay tests pass
required assets converted
special systems classified
no unknown critical gameplay dependencies remain
```

---

## Checkpoint E — Production Server

Successful when:

```text
Server v1 authoritative
PostgreSQL active
legacy saves migrate
auth secure
economy protected
observability operational
CI operational
```

---

## Checkpoint F — Flash Retirement

Successful when the game can:

```text
install
launch
load player
load town
play normal game loop
save progress
close
restart
resume
```

without:

```text
Flash Player
SWF execution
ActionScript
Ruffle
AMF
FlashVars
```

---

# 81. Recommended Architecture Decision Record

Create:

```text
docs/adr/ADR-001-preservation-first-reconstruction.md
```

Suggested content:

# ADR-001 — Preservation-First Social Wars Reconstruction

## Status

Accepted

## Context

The current project contains a working or partially working reconstruction of Social Wars using a Flask server and the original Flash client architecture.

Although Flash is obsolete as a runtime platform, the existing repository contains valuable behavioral logic, game configuration, save data, server behavior, protocol behavior, images, sounds, and compiled client assets.

Replacing everything simultaneously would make regression detection difficult and risk losing undocumented gameplay behavior.

## Decision

The current Flask/Flash implementation will be treated as the reference implementation and preservation dataset.

The legacy implementation will be frozen while a new Godot client is built.

The first modern client will communicate through a compatibility API that preserves legacy game semantics.

Once client-side feature parity has been established, the backend will progressively migrate toward an authoritative FastAPI server backed by PostgreSQL.

Existing JSON saves will be treated as migration inputs and regression fixtures.

SWFs may remain under an archival legacy directory but must not be required by the final runtime or included in production client packages.

## Consequences

Positive:

- undocumented behavior remains discoverable
- migrations can be verified
- client and server rewrites are decoupled
- existing saves remain usable
- Flash removal can happen incrementally
- regressions become testable

Negative:

- legacy infrastructure remains temporarily
- compatibility code must be maintained during migration
- repository contains old and new implementations simultaneously

These costs are acceptable because they substantially reduce reconstruction risk.

---

# 82. End-State Repository

The eventual repository could look like:

```text
social-wars/
├── apps/
│   ├── client/
│   │   └── Godot
│   │
│   ├── server/
│   │   └── FastAPI
│   │
│   └── compat/
│       └── Legacy compatibility layer
│
├── packages/
│   └── game-content/
│
├── tools/
│   ├── asset-converter/
│   ├── protocol-recorder/
│   ├── protocol-replay/
│   ├── state-diff/
│   ├── save-migrator/
│   └── content-builder/
│
├── legacy/
│   ├── flask-server/
│   ├── flash-client/
│   ├── raw-assets/
│   └── saves/
│
├── tests/
│   ├── golden/
│   ├── integration/
│   ├── migration/
│   └── visual/
│
├── docs/
│   ├── architecture/
│   ├── legacy-protocol/
│   ├── game-systems/
│   ├── assets/
│   ├── migrations/
│   └── adr/
│
├── PROVENANCE.md
└── README.md
```

---

# 83. Immediate Priority Order

The immediate development sequence should be:

```text
FREEZE
    ↓
INSTRUMENT
    ↓
CATALOG
    ↓
REPLAY
    ↓
NORMALIZE CONTENT
    ↓
CREATE GODOT CLIENT
    ↓
BUILD COMPATIBILITY API
    ↓
RENDER ONE REAL TOWN
    ↓
BUILD MAIN GAMEPLAY LOOP
    ↓
REPLACE ALL RUNTIME SWFs
    ↓
BUILD AUTHORITATIVE SERVER
    ↓
MIGRATE TO POSTGRESQL
    ↓
HARDEN PRODUCTION
    ↓
RETIRE FLASH COMPLETELY
```

---

# 84. Most Important Near-Term Target

Do **not** make PostgreSQL or the backend rewrite the first visible result.

The first major target should be:

Launch the Godot client on a computer with no Flash runtime, load one real existing Social Wars save, and faithfully render the town, buildings, units, resources, camera, and basic selection using preserved legacy data.

Once that works, the project has proven that the Flash client can actually be replaced.

---

# 85. Core Architectural Thesis

The most important idea guiding the project is:

**The existing Social Wars repository is not obsolete code that should simply be replaced. It is the reference implementation, behavioral specification, protocol specification, preservation dataset, save corpus, content source, asset archive, and regression oracle for the reconstruction.**

The correct migration therefore is not:

```text
DELETE OLD GAME
    ↓
BUILD NEW GAME FROM MEMORY
```

It is:

```text
PRESERVE
    ↓
OBSERVE
    ↓
RECORD
    ↓
DOCUMENT
    ↓
REPRODUCE
    ↓
VERIFY
    ↓
REPLACE
    ↓
RETIRE
```

The existing Flask implementation should remain available until the Godot client and Server v1 can prove through recorded behavior, replay tests, golden fixtures, and state-diff tests that every required legacy system has a verified replacement.

That approach gives the project the best chance of achieving all four goals simultaneously:

1. **Preserve the original Social Wars behavior.**
2. **Remove the dependency on Flash/SWF completely.**
3. **Modernize the client/server architecture safely.**
4. **Create a maintainable foundation that can continue evolving after preservation parity is achieved.**

---

# 86. Recommended Development Workflow

For each major feature or migration unit:

```text
1. Explore legacy implementation.
2. Identify related commands/endpoints/assets/state.
3. Capture legacy fixtures.
4. Write/update OpenSpec change.
5. Define acceptance criteria.
6. Create feature branch.
7. Implement smallest complete vertical behavior.
8. Add automated tests.
9. Replay legacy fixtures.
10. Compare state.
11. Perform Godot/manual visual verification where applicable.
12. Update migration status.
13. Update documentation.
14. Review.
15. Merge.
16. Push.
```

---

# 87. Recommended Branch Strategy

Use branch-per-feature or branch-per-migration-unit.

Examples:

```text
feat/protocol-recorder
feat/state-diff
feat/content-normalization
feat/godot-bootstrap
feat/town-renderer
feat/building-placement
feat/unit-production
feat/quest-system
feat/server-v1-buildings
feat/save-migrator
```

Avoid creating enormous branches spanning several milestones.

---

# 88. OpenSpec Usage

Use OpenSpec for meaningful behavioral or architectural changes.

Each change should define:

```text
problem
scope
non-goals
existing behavior
target behavior
acceptance criteria
affected systems
migration concerns
testing requirements
```

For reconstruction work, include:

```text
Legacy reference:
- endpoint
- command
- source files
- fixtures

Parity requirements:
- expected state mutation
- expected response
- visual behavior where relevant
```

---

# 89. Definition of Done for a Migrated Feature

A migration feature is not complete merely because the new UI appears to work.

A migrated feature should normally satisfy:

```text
legacy behavior identified
legacy fixture captured
modern behavior implemented
automated test added
state mutation verified
error conditions tested
retry behavior considered
content IDs preserved
relevant assets migrated
documentation updated
migration status updated
no new Flash dependency introduced
```

For Server v1 features additionally require:

```text
server-authoritative validation
database transaction where needed
authorization
revision handling
idempotency where needed
economy ledger where needed
```

---

# 90. Final Project Definition of Done

The complete modernization is finished when:

```text
Godot is the only gameplay client.

Normal gameplay contains no SWF execution.

Normal gameplay contains no ActionScript execution.

Adobe Flash Player is unnecessary.

Ruffle is unnecessary.

The modern client does not know about command.php.

The modern client does not use FlashVars.

The modern client does not require AMF.

All gameplay-critical legacy commands are implemented,
retired, or explicitly declared out of scope.

All runtime-critical Flash assets have been converted
or recreated.

Existing supported legacy saves can be migrated.

Production player state lives in PostgreSQL.

Production game actions are server authoritative.

Important economy mutations are auditable.

Network retries cannot duplicate important rewards.

Client clock manipulation cannot bypass timers.

Authentication and authorization are production-safe.

Automated golden/replay tests verify important legacy parity.

Visual regression coverage exists for important scenes.

CI prevents accidental reintroduction of Flash dependencies.

Legacy files remain preserved separately for historical,
debugging, migration, and research purposes.

A clean machine can install the modern client,
connect to the server, load a player,
play the game, close it, reopen it,
and continue playing without installing
any Flash-related software.
```

---

# 91. Development Priority Summary

## Build Now

```text
legacy preservation
dependency locking
hash manifest
canonical saves
protocol recorder
state diff
command replay
endpoint catalog
command catalog
content normalization
Godot initialization
GameApi abstraction
Compatibility API v0
town bootstrap
isometric renderer
camera
terrain
town objects
first building
first unit
HUD
selection
no-Flash vertical slice
```

## Build Next

```text
building placement
economy
construction
collection
inventory
unit queues
unit movement
XP
quests
research
collections
missions
combat
social
special systems
asset parity
```

## Build After Parity Is Established

```text
Server API v1
authoritative game rules
PostgreSQL
save importer
authentication
rate limiting
observability
admin tools
production deployment
```

## Build Much Later If Needed

```text
Redis
WebSockets
mobile client
new multiplayer systems
major gameplay redesign
balance changes
microservices
advanced deployment infrastructure
```

---

# 92. The First Concrete Goal

The engineering team or coding agent should treat the following as the immediate mission:

**Preserve and instrument the legacy implementation, then build the smallest Godot vertical slice capable of loading and displaying a real Social Wars town from an existing save without executing Flash or SWF content.**

Everything before that target should directly support it.

Everything that does not directly support it should generally wait.

The first sequence therefore is:

M0 Preservation
    ↓
M1 Protocol Discovery
    ↓
M2 Recorder / Replay / State Diff
    ↓
M3 Content Normalization
    ↓
M4 Initial Asset Conversion
    ↓
M5 Godot Foundation
    ↓
M6 Flash-Free Town Vertical Slice

**M6 is the first major victory.**

Do not allow backend modernization, infrastructure work, or unrelated redesign to delay reaching it.

### The M8 entry position, recorded for the next run

M8's first deliver line is **unit definitions**, and the delivered work already constrains it
in three ways that the investigation must not re-derive:

- **The corpus contains no unit placements at all**, and 0 of its 40 placed rows carry
  `attr["xp"]`, which is why the XP line's unit XP (`add_xp_unit`) and the level curve's
  `reward_type`/`reward_amount` are out of scope there and recorded as such.
- **M4 established the unit asset truth**: `tools/asset-registry/convert_unit.py` produced one
  converted unit package — a per-sprite timeline inventory with shape/bitmap linkage, **no
  tessellation and no playback semantics** — and its README states it establishes "no animation
  correctness, rendering, visual fidelity, gameplay semantics, or Godot loading". So M8's
  `animations` and any rendering claim rest on that package plus the M6 slice evidence, which
  already proved authentic unit rendering through the Wild Elephant sprite in
  `apps/client-godot/evidence/town/` while recording that the fresh save has no unit placements.
- **The committed content already carries the unit definitions**: the items normalization
  committed **429 units** of the 900 `items` entries (470 buildings, 429 units, 1 documented
  special), each with schemas and round-trip evidence, so `unit definitions` is a content-delivery
  line over committed artifacts rather than a legacy-behaviour derivation.

The honest first questions for the M8 investigation are therefore: what does the legacy server
actually do with units (the command catalog's "Units and production queues" section is the place
to start, alongside `push_unit`, `pop_unit`, and `push_dead_unit`), what a unit instance looks
like in the save, and what the corpus can and cannot exercise — with every unobserved rule marked
derived-provisional exactly as M7's were.
