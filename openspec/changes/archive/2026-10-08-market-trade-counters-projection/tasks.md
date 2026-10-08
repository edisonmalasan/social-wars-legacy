# Tasks — market / trade counters

Binding investigation: `docs/legacy-m11-special-mechanics.md` (merged `1c8786b`).
Binding design: `design.md`. Every task below is scoped to the two read-only modules and one
hermetic suite described in design D11.

**Ownership.** Task 1 is the only implementation task; task 2 is the only verification task.
The root orchestrator owns this file, the specs, and acceptance. No implementation subagent
may edit `proposal.md`, `design.md`, `specs/`, or `tasks.md`.

---

## 0. Preconditions, re-measured before anything is written

- [x] 0.1 Re-measure, from the working tree, and record in the report: the **63** named
      dispatcher branches on **raw** text (branch names live in string literals, so a
      code-only lexer returns zero — the one place the raw/code split cannot apply to the
      token); the trade-counter writer and reader sets; the **8** `MARKET_*` keys with their
      raw and quoted counts over **all eleven** modules; and the **10** save documents'
      `(numTradesDone, timestampLastTrade)` pairs.
- [x] 0.2 Confirm the baseline is unchanged before the first edit and record it: hermetic
      suites **49**, live phases **23**, `verify-boot.ps1` assertions **228**, guard digest
      `6978b959…ff348`, compat **3,077 tests OK**, validator **23 files / 22 schemas / 604
      references**, manifest **3,258 entries / 758,423,699 bytes**, `openspec --all --strict`
      **71 passed / 0 failed**.
- [x] 0.3 Confirm containment: `auctions/` and `saves/` absent, and `git status` clean apart
      from this change's own new paths. **Never run legacy Python that touches `auctions/`
      with the repository root as the working directory** (`AUCTIONS_DIR = ./auctions` and
      `__init__` calls `os.makedirs`).

---

## 1. Implementation — two read-only modules

**Owned files (this task's entire write surface):**

- `apps/client-godot/scripts/market/trade_counters.gd` (new)
- `apps/client-godot/scripts/market/market_schedule.gd` (new)
- `apps/client-godot/tests/test_market_trade.gd` (new)

- [x] 1.1 `trade_counters.gd`: a typed read-only projection over the map and private state.
      Report the committed count and the committed last-trade instant **verbatim**. Derive
      **no** price and move **no** resource. Expose **no** callable action.
- [x] 1.2 The cap is **one** named constant read from the branch literal at
      `command.py:470`, documented in-code as the branch's own value. The projection reports
      that the cap is **stored and never enforced**, and carries the measured reason: the
      count's only reader is its own increment at `command.py:469`.
- [x] 1.3 Reproduce the branch's remaining-trades arithmetic **unclamped**, as a separately
      labelled field from the stored count, so the divergence at `command.py:473` is visible
      rather than silent. At or above the cap the reported value is **negative**. The module
      contains no clamping of this value.
- [x] 1.4 Report the day bucket of the recorded instant and of the server clock, and the
      predicate `now // 86400 != last_trade // 86400` between them. **Perform no reset** and
      **do not reimplement** `engine.reset_stuff`; reference it as the owner.
- [x] 1.5 **Fail closed** on an absent or non-integer count or instant: report the field as
      unavailable, report no derived value needing it, and carry the recorded field beside the
      refusal, untouched. (Precedent: the M6 projection-evidence gap, where a key that nothing
      produces must render as an explicit missing-field indicator rather than a default.)
- [x] 1.6 `market_schedule.gd`: project the **8** committed `MARKET_*` values verbatim with
      their committed types, **read through the existing normalized content registry** — never
      transcribed. Carry each value's measured zero-consumer status.
- [x] 1.7 Compute **no** economy from the schedule: no price, cost, period, percentage, or
      increment bound. The module contains **no** multiplication or division over a projected
      committed value, so the no-derivation claim is mechanically true rather than asserted.
- [x] 1.8 Record both divergences as comments at the site, with line references: resource
      movement would arrive via `engine.apply_resources` before the dispatcher opens at
      `command.py:42`, and the instant is client-writable through `fast_forward`'s
      client-supplied `seconds = args[0]`.
- [x] 1.9 Reference, do not reimplement: the production queue (`godot-unit-queues`), the bonus
      ladders (`godot-rewards`), the darts instants (`godot-darts`). The modules name **none** of
      those foreign fields — not even in a comment.

---

## 2. Verification — one hermetic suite

- [x] 2.1 `test_market_trade.gd` covering every requirement and scenario in the spec delta,
      registered in `verify-boot.ps1`'s hermetic list. Target the family's usual shape: several
      hundred checks, `--report=` supported.
- [x] 2.2 **Re-measure, do not inherit.** The suite re-derives, every run: the branch set on
      raw text; the writer/reader sets for both counters; the `MARKET_*` consumer counts over
      all eleven modules; and the corpus pairs across all ten documents. Every count is
      reported under the rule that holds it.
- [x] 2.3 Assert the day-bucket finding that shapes every claim limit: **8 of 10** documents
      record `timestampLastTrade == 0`, for which the reset predicate is **unconditionally
      true** and the count is cleared on every load. Assert `Nerri.json` is the **only**
      document at the cap.
- [x] 2.4 Assert the `Neutral.json` proof's **premises**, not just its conclusion: that
      `command.py:471` is the only site that can raise the instant, and that
      `command.py:913` subtracts a client-supplied quantity and floors at zero. These are what
      make "the reset fired" a proof rather than an inference.
- [x] 2.5 Assert the **no-clamping** property directly (design D3), so the negative
      remaining-trades value cannot be "helpfully" corrected.
- [x] 2.6 Assert the ownership boundaries (design D8): each declared owner spec **exists** and
      projects the deferred surface, so no boundary is an orphan; and this line's modules name
      none of the foreign fields.
- [x] 2.7 Write the deterministic `market-trade-report-v1` evidence report from the suite
      itself, with its tables generated from the live modules so they cannot drift from the code
      they document. Re-run and confirm the bytes are identical across three consecutive runs.
- [x] 2.8 **Anti-invention guards proven by injection, not trusted** (design D9). Inject at
      minimum: a new static helper of any name; a **suffixed** helper wearing a reserved name as
      a prefix (the exact miss recorded on the friends line — an exact-name check passes it);
      an invented `trade_cost`; an invented `cap_for`; an invented `enforce_trade_limit`; an
      invented `is_trade_allowed`; a clamping of the remaining-trades value; a
      `MARKET_*` name in a delivered module; and a foreign-field reference. **Measure each
      probe's failure count**, do not record only its non-zero exit. Every restore is verified
      by sha256 with zero NUL bytes and the baseline's final-newline state, and
      `git diff --numstat --ignore-cr-at-eol` plus `git status --short` must equal their
      pre-probe values.
- [x] 2.9 Harness discipline, from the recorded defects: normalise to LF **before** mutating a
      probed file, and **abort if a probe fails with no `[test] FAIL` line** — a parse-error
      detection proves nothing about a guard. Pin the restored file's final byte to the
      baseline rather than asserting a universal trailing-newline rule, which was wrong for an
      already-delivered file.
- [x] 2.10 Amend `test_project_scope.gd`'s allow-list for exactly the new client sources and
      the new report, and re-run it. Confirm the 13 `FORBIDDEN` tokens and
      `test_town_gate.gd`'s `RUNTIME_NEEDLES` needed **no** relaxation — verified in design
      D10 that none collides.

---

## 3. Batteries and gates

- [x] 3.1 `powershell -File apps/client-godot/verify.ps1` — exit `0`.
- [x] 3.2 `powershell -File apps/client-godot/verify-boot.ps1` — exit `0`, **50** hermetic
      suites (was 49), **23** live phases (**unchanged** — no live phase is delivered),
      guard digest `6978b959…ff348` **identical before and after**, and zero `[test] FAIL`,
      `^ERROR:`, or `SCRIPT ERROR` lines across every log file.
- [x] 3.3 `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` —
      **3,077 tests OK**, exit `0`, a **verified re-run baseline**, because
      `apps/compat-api/**` is not touched at all. If it differs, that is a finding to
      investigate, not a number to update.
- [x] 3.4 `python -B packages/game-content/tools/validate_content.py` — exit `0`,
      `result: valid`, **23 files / 22 schemas / 604 references**.
- [x] 3.5 `python -B tools/hash-manifest/hash_manifest.py verify` — **3,258 entries /
      758,423,699 bytes**, exit `0`.
- [x] 3.6 `openspec validate --all --strict` — **72 passed / 0 failed**. Measured at
      proposal time: `--all` validates **71 main specs plus 1 change**, and the change appears
      in the output as `✓ change/2026-10-08-market-trade-counters-projection`. Note the total
      is **72 both during the change and after Sync**, because Sync converts the change into a
      72nd main spec and archiving removes the change — so the number alone does not say
      which stage is done. Record the *composition*, not just the total. Measured
      `openspec validate 2026-10-08-market-trade-counters-projection --strict` → valid, exit
      `0`.
- [x] 3.7 `git status` shows **no** legacy, config, save, village, content-package,
      conversion-package, registry-manifest, or fixture byte changed.

---

## 4. Recorded gaps and limits — to be carried into the PR description verbatim

- [x] 4.1 **No route, no compat-API change, no live phase, no executed-legacy fixture.** All
      four are decisions with measured reasons (design D1, D7), not omissions. The fixture
      refusal is a property of the corpus — 8 of 10 documents make the reset predicate
      unconditionally true — and additionally a fixture licensing a round trip this line
      refuses.
- [x] 4.2 **No enforcement, no price, no period, no percentage.** `numTradesDone`'s only
      reader is its own increment, so the cap is a stored value; the eight committed
      `MARKET_*` values have zero consumers.
- [x] 4.3 **`MARKET_MAX_NUM_TRADES == 20` matching the branch literal is a coincidence**,
      recorded as one. The cap is never derived from it.
- [x] 4.4 **The unclamped print is reproduced, not corrected**, and is negative from the 21st
      trade onward.
- [x] 4.5 **Two divergences are recorded, not reproduced**: client-sent resource movement, and
      the client-writable instant.
- [x] 4.6 **`Nerri.json` is one data point.** No claim of parity for any other document, and
      no claim that any player ever hit the cap twice.
- [x] 4.7 **Absence of a server rule says nothing about the Flash client**, which may have
      displayed, gated, or hid a market entirely client-side.
- [x] 4.8 **No ordinal** is claimed for the zero-consumer count. Four conflicting ordinals
      already exist in the delivered records, each over a different scope.
- [x] 4.9 **Not delivered here, recorded by the investigation:** the atom-fusion **powerup
      purchase** (`buy_powerups` is a `# TODO` with a committed six-row ladder and zero
      consumers) — candidate #2, adjacent to an owned surface; `first_time_marketplace` — a
      2-statement unowned branch, candidate #3; `rt_open_graph_unit` with
      `crossPromotionsFinished`/`unlockedSkins` — candidate #4; and the **24-declaration**
      `SPELL_*`/`TECH_*` coverage gap beside `godot-mission-vocabulary` — candidate #5.
- [x] 4.9b Carry the investigation's **eight instrument defects** into the report. Two of them
      — counting quoted keys through a lexer that blanks string contents, and the name/stem
      ownership test — would each have produced a false headline claim, and one produced a
      **false mismatch** that would have trained the reader to dismiss its output.
- [x] 4.10 Re-run before treating any of the **ten recorded flaky surfaces** as a regression:
      the `5055`/`5056` `port_is_free` assertions; `verify-boot.ps1` treating any `^ERROR:` as
      a script error (grep `SCRIPT ERROR` too); the display-sensitive `verify.ps1`; the
      `test_base.gd` abort-as-pass defect; the session `server_time` field; the collect
      sub-second time budget; the dead `VOLATILE_PLAYER_INFO_FIELDS` exemption at the wrong
      nesting depth; and the two committed-report gaps.

---

## 5. Archive

- [x] 5.1 Confirm the roadmap `Project Status` block records this line and that M11's exit
      criterion can now be assessed. **Root orchestrator only.** Done: thirteen ledger entries
      added to `docs/DEVELOPMENT_ROADMAP.md`, each inserted **above** the entry it supersedes
      and that entry retitled in place to the repository's established
      *before this entry, retained in full* form. Nothing was deleted. The verdict recorded is
      that **M11's exit criterion is MET** — every relevant system this oracle can see is now
      classified, four are projected, and the rest are refused with the reason measured — with
      the explicit note that this is a **different verdict from M10's** *unsatisfiable from this
      oracle* and that the two must not be conflated.
- [x] 5.2 Sync the new capability into `openspec/specs/godot-market-trade-counters/spec.md`.
      **No existing spec is amended** — the single existing mention,
      `godot-building-resources/spec.md:119`, is an out-of-scope note this line satisfies. Done:
      created at **7 requirements / 20 scenarios**, with the requirement-and-scenario body
      **byte-identical** to the delta's (verified by comparing from the first
      `### Requirement:` heading onward), and `openspec validate --all --strict` reporting
      **73 passed / 0 failed = 72 main specs plus 1 change**.
- [x] 5.3 Archive as `2026-10-08-market-trade-counters-projection` on
      `chore/archive-market-trade-counters`, **merge commit**, branch deleted, back to updated
      `main`. Done. **Ordering was not incidental:** the post-Sync LF defect fix (PR #341,
      `4b214dc`) was merged **before** Archive began, because Archive moves this change's
      artifacts out of `openspec/changes/` and a defect belonging to that change belongs ahead
      of it rather than inside its archive commit — folding it in would have put a red-to-green
      change to the suite inside a stage whose diff should be a pure rename plus ledger text.
      All five artifacts moved with `git mv` and `git status` confirms **pure renames** — every
      entry an `R` with **no** content modification, so the archived bytes are the merged bytes.
      `openspec validate --all --strict` reports **72 passed / 0 failed = 72 main specs plus 0
      changes** on the archive branch's tree, against Sync's **73 = 72 plus 1**: Archive removes
      the change, and the total falls by exactly one, so **the composition is what distinguishes
      the two stages**. (The first draft of this note claimed the total stayed at 73 and that the
      archive tree carried "72 main specs plus 0 changes" — internally inconsistent, because 72
      plus 0 is 72 and not 73. Measured, not assumed, and corrected here rather than shipped.)

---

## 6. Correction record — Apply stage

Every item below was found during or after Apply and is recorded **with its cause**, not
quietly fixed in place. The standing rule is that a transposed figure, a wrong number, and a
guard that does not fire are the same defect class: they all *look* like evidence.

### 6.1 Corrections to the change's own artifacts

- **6.1.1 `test_auction_schedule.gd`'s `RECORDED_HERMETIC_COUNT` amended `49 → 50`.** This is
  the established pattern, not a redefinition: a *count pin the incoming line legitimately
  moves* is amended in place, where an already-archived line's **behavioural** assertion is not
  touched from an unrelated change. The rationale is recorded in a comment at the pin.
  `RECORDED_LIVE_PHASE_COUNT := 23` was deliberately **left alone** — this line adds no live
  phase, so the live count is not its to move.
- **6.1.2 The evidence report's `comparable_to_lf_normalised_digest` flag was hard-coded
  `false`, and was wrong.** The reasoning behind the constant was a true statement about the
  *checkout* attached to a field named for the *files*; a reader keying on the field name
  correctly concluded the digests could not be compared against an LF manifest. They can: both
  delivered modules are pure LF (measured, zero CRLF), so each raw digest **is** that file's
  LF-normalised digest. Now measured per run by `_modules_are_pure_lf()`. Three sibling reports
  carry this field as `false` and there it is correct — those were CRLF files. Copying a field
  and its value across file forms is how a guard becomes a lie.
- **6.1.3 The injection block was disclosing itself as live evidence.** `_injection_record()`
  returns a **transcribed** table of a prior session's external harness run; an earlier review
  of this change read the block as live evidence of nine guards firing, which is stronger than
  anything the code supports. `INJECTION_PROVENANCE` now states that the suite cannot execute a
  probe (it holds no `OS.execute`, no file write, no `await`, no engine call) and what the block
  *does* assert in run (the record's internal consistency) versus what it does not (that the
  guards still fire). The disclosure is **asserted**, so it cannot be dropped by an edit that
  leaves the table intact.

### 6.2 Two defects in my own instruments — the class that costs the most

- **6.2.1 `String(PackedByteArray)` does not exist on this engine.** The first fix for the
  digest flag called `String(raw)` on a byte array. That is a **parse** error, not a runtime
  one, so it surfaced as an unparseable suite rather than as a failing check. Replaced with
  `FileAccess.get_file_as_string`.
- **6.2.2 `sha(open(p).read()) == lf(open(p).read())` compares a hex digest to un-hashed
  bytes.** The purity check I wrote asserted `sha(bytes) == bytes`, which is `False` for every
  non-empty file, so `all(...)` printed `False` on two modules that are in fact pure LF. The
  corrected single-read form printed `True`. This is recorded because the *symptom* — a check
  claiming a file is CRLF when it is not — points in exactly the wrong direction, and a reader
  who believed it would have "fixed" a pure-LF file.

### 6.3 Measurements that moved from the recorded values

- **6.3.1 Injection probe counts re-measured against the final delivered state**, after both
  edits above — a later edit can silently restore or remove guard coverage, so a probe count
  measured mid-change does not describe the shipped bytes. All **nine** probes re-run:
  `6, 4, 7, 27, 8, 2, 2, 3, 4`, summing to the recorded **63**, every exit `1`, every
  `engine_error_lines` **0**, every restore verified by sha256 against the pre-probe bytes, and
  `git diff --numstat --ignore-cr-at-eol` plus `git status --short` equal to their pre-probe
  values. **No count moved.** The harness itself re-asserts the three recorded construction-
  assist defects rather than assuming them: LF normalisation before mutation, an **abort** when a
  probe reports zero `[test] FAIL` lines (a parse-error detection proves nothing about a
  guard), and restore verified by digest with no universal trailing-newline rule.
- **6.3.2 The baseline suite is checked before the first probe.** A probe set measured on a
  suite that is already failing proves nothing, so the harness runs the suite clean first and
  aborts otherwise.
- **6.3.3 A worker's reported baseline of "22 files / 21 schemas" is WRONG**; measured **23 /
  22 / 604**. It appeared only in the worker's chat report — the repository is correct and was
  never wrong. Recorded because a wrong figure in a report is exactly what a later reader
  re-measures and re-litigates.

### 6.4 Verification findings, resolved or recorded

- **6.4.1** `boot-report.json` **was** stale; regenerated and the diff **inspected rather than
  assumed**: 79 → 80 entries, exactly one added (`test_market_trade`), nothing removed, order
  preserved, and on the 25 retained entries **only the `log` field changed**. A rename and a
  content change are easy to confuse in an insertion diff.
- **6.4.2** Two findings against the evidence report were **fixed** (6.1.2, 6.1.3).
- **6.4.3** A verifier finding that **five sibling suites lack `--report=` absolute-path
  resolution** is **recorded as a follow-up, not fixed**: those are archived lines, and the
  honest fix belongs to whoever owns them. (Same rule as the ten recorded flaky surfaces.)
- **6.4.4** A verifier predicted **26** log renumberings; measured **25**. Off by one, no effect
  on the conclusion — recorded because a predicted figure that differs from the measured one is
  a claim that was never a measurement.

### 6.5 Correction from the Sync stage

- **6.5.1 The delta is not the same shape as a main spec, and a mechanical conversion loses
  exactly that.** Converting the delta by dropping its `## ADDED Requirements` wrapper also
  dropped the `## Requirements` header the main-spec schema **requires**, so
  `openspec validate godot-market-trade-counters --strict` failed with *"Spec must have a
  Requirements section."* Caught by strict validation rather than by reading the file, which is
  the argument for running the strict gate on a **converted** artifact and not only on a
  hand-written one.
- **6.5.2 `openspec validate --all --strict` totals 73 after Sync, against 72 during the
  change** — the composition is the claim, not the total: **72 main specs plus 1 change** now,
  **71 plus 1** during, and **72 plus 0** once archived. Sync converts a change into a main spec
  and Archive then removes the change, so **the total alone never says which stage is done.**
- **6.5.3 One Sync edit deliberately goes beyond the delta.** The measured findings that shape
  every requirement — the **8-of-10** corpus figure, the branch literal and its coincidence, and
  the clamped-store/unclamped-print asymmetry — are added to the new `## Purpose`. A delta's
  Purpose is a proposal artefact; a main spec's is what a later reader uses to judge the
  requirements, and leaving these out would make the requirements look arbitrary.

## 7. Correction record — post-Sync defect fix

Carried on `fix/market-trade-lf-digest-check`, its own branch and PR, per the established
precedent (`fix/auction-manifest-section-guard`) that an Apply- or Sync-stage defect gets its
own branch rather than being folded into the next stage's diff. §6 is left intact; nothing here
edits a §6 entry in place.

### 7.1 The defect reproduced on `main`, and the committed evidence proves it

- **7.1.1 The check asserted a property of the *checkout* as a required property of the
  *delivered bytes*.** `_check_evidence_record()` ended with `check(modules_are_pure_lf(), …)`.
  `core.autocrlf=true` (measured) and no `.gitattributes` rule for these paths meant a default
  Windows checkout delivers **CRLF**, so `_modules_are_pure_lf()` correctly measured `false` and
  the suite failed. This is the **same defect class as 6.1.2**, in the opposite direction: 6.1.2
  hard-coded `false` when the truth was `true`, and this one required `true` when the truth is
  *whatever the checkout produced*. Both mistake a property of how the file arrived for a
  property of what was delivered. A checkout form is never a delivery guarantee.
- **7.1.2 The committed `boot-report.json` on `main` records the failure**, which is the strongest
  available evidence and needed no reproduction argument: `"pass": false`, `failures: ["test_market_trade
  exits 0 (got 1)", "test_market_trade reports PASS"]`, with the `test_market_trade` command's
  `exit_code: 1`. The Apply-stage battery had passed on the authoring checkout; the artifact that
  shipped recorded a red run. The fix's regenerated report carries `"pass": true`, `failures: []`,
  `exit_code: 0` — so the diff is **load-bearing** rather than cosmetic, and it is the third
  recorded instance of the LF/checkout-form class after 6.1.2 and the byte-count guard
  `godot-unit-experience` fixed.

### 7.2 The fix, and why it is two things rather than one

- **7.2.1 The check now asserts only checkout-independent facts.** Each module carries a second
  `sha256_lf_normalised` beside its raw `sha256`, and the assertions are: both digests present and
  64 hex chars; the flag equals a **fresh** measurement; each module's raw and LF digests are equal
  **iff** the flag is true; both modules took one of the two branches, so neither was skipped; and
  **never neither** — either the checkout is pure LF, or it is CRLF and the LF-normalised digests
  are the ones to compare. No assertion requires the flag to be `true`, because that is the claim
  that was wrong. The equality check is **non-tautological**: the two digests are computed by
  independent routes (`FileAccess.get_sha256` over raw bytes vs `HashingContext` over a
  hand-assembled LF-normalised copy), so their agreement is a cross-check rather than a value
  compared with itself.
- **7.2.2 `.gitattributes` pins the three paths to LF** (`apps/client-godot/scripts/market/*.gd`,
  `apps/client-godot/tests/test_market_trade.gd`, `apps/client-godot/evidence/market-trade/report.json`),
  **+12 lines** with the rationale in the file, on the `/packages/game-content/**` precedent.
  Measured after: `git check-attr` resolves all three to `text: set, eol: lf` under
  `core.autocrlf=true`. This is what makes the committed report's digests **reproducible on any
  checkout**; 7.2.1 alone would make the suite pass everywhere but leave the evidence report's
  recorded digests differing by checkout form. Both halves are needed and they fix different things.
- **7.2.3 The final LF-normalisation helper goes through neither String path**, so 6.2.1's parse
  error cannot recur: `FileAccess.get_file_as_bytes` → byte loop → `HashingContext`. The
  intermediate attempt used `FileAccess.get_file_as_string`, which is what 6.2.1 recorded; the
  byte-level form is what shipped.

### 7.3 Proof, re-measurements, and the corrected figures

- **7.3.1 The suite passes on both forms**: **1005 checks, exit 0** on a pure-LF tree, and
  **1005 checks, exit 0** on a tree where all three files were rewritten to CRLF (554 / 389 / 2592
  CRLF pairs measured). The second run is the defect proof — it is precisely the case that failed
  on `main` — and the files were restored to zero CRLF pairs afterwards with `git checkout --`.
- **7.3.2 Report regenerated and re-measured**: **40,006 bytes**, **zero CRLF**, sha256
  **`b2e2c9c6c3f7c322b87539d97dea33276515aefa30d2ed99fd1d39f8ff15348e`**, byte-identical across
  **three** runs including one written to a different output path. Suite reports **1007** checks
  with `--report`. The **raw module digests are unchanged** — `1f8d8dcf…` and `d8e1d852…` — so the
  diff against the previous report is only the two added `sha256_lf_normalised` fields and the
  corrected `form` prose. That the LF-normalised digest equals the raw one for these two modules
  is now **recorded per module** rather than argued in prose.
- **7.3.3 Injection probes re-run after the suite edit**: still `6, 4, 7, 27, 8, 2, 2, 3, 4`,
  summing to **63**. **No count moved**, and this is the second re-measurement against this final
  state — a suite edit can silently change what a probe trips.
- **7.3.4 Batteries re-run green on the fix branch**: `verify-boot.ps1` exit `0`,
  **230/230** assertions ok, **80** commands with **zero** non-zero exits, **23** live phases,
  guard digest `6978b959…ff348` **identical pre/post**, port 5056 released, no working-tree
  `saves/`, and **1,144** log files carrying zero `[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines;
  `verify.ps1` exit `0` (`PASS all checks succeeded`); compat suite **`Ran 3077 tests … OK`** exit
  `0` (unchanged — this fix touches no `apps/compat-api/**` file, established by `git status`);
  `validate_content.py` exit `0`, `result: valid`, **23 files / 22 schemas / 604 references**;
  `hash_manifest.py verify` **3,258 entries / 758,423,699 bytes** exit `0`;
  `openspec validate --all --strict` **73 passed / 0 failed** (72 main specs + 1 change).
- **7.3.5 `boot-report.json` diff inspected rather than assumed**, and it is the fix's own
  evidence: `generated_utc`, `git_commit` (`ab886f8` → `fccb9c5`), the `test_market_trade`
  `exit_code` `1 → 0`, its two assertions `ok: false → true`, `failures` emptied, and
  `pass: false → true`. **Nothing else changed** — 8 insertions, 9 deletions, no `log`
  renumbering, because the command list is unchanged.
- **7.3.6 Two recorded flaky surfaces fired on this branch, both on suites the fix does not
  touch, and the third run passed.** Run 1: `test_town_upgrade` crashed with a Windows access
  violation `0xC0000005`. Run 2: `test_game_api_live.gd` reported *"the live reference instant is
  not older than the instant it stamped"* — a **second-boundary clock race** of the same family as
  the recorded `server_time` surfaces, where a reference instant and a server-stamped instant are
  compared for strict inequality and both land inside one second. Neither is caused by this change
  (`git status` shows only `.gitattributes`, `test_market_trade.gd`, and two evidence reports; the
  modules are hermetic and make no network call). Run 3: `PASS all checks succeeded`. Recorded as
  the **eleventh** and **twelfth** surfaces; both remain open, and per the repo's rule they are
  re-run rather than treated as regressions.
