# Tasks

## 1. Normalization — `packages/game-content/tools/build_auctions.py`

- [x] 1.1 Read `config/auctionhouse.json` read-only. Do **not** import `auctions.py`.
- [x] 1.2 Emit one definition per committed entry, preserving committed order.
      `legacy_id` stays the committed **string** `uuid`; `unit`, `level`,
      `interval`, `price`, `priceIncrement`, `betPrice` verbatim.
- [x] 1.3 Record the content source as the standalone file `config/auctionhouse.json`,
      not one of `main.json`'s 20 keys.
- [x] 1.4 Perform **no** conversion of `interval`. Add no `seconds`/`duration`
      field and no conversion factor as data.
- [x] 1.5 Resolve `unit` against `normalized/units.json`, carrying the resolved
      display name. An unresolvable id is **recorded as unresolved**, still
      emitted, in order, and reported — never dropped or invented.
- [x] 1.6 Carry `betPrice` and record `bet_price_consumed: false`, citing the
      zero-consumer measurement (no `gold/coins/cash/wood/steel/oil/xp/mana/
      energy/cost/apply_resources`, and `apply_resources` is never called).
- [x] 1.7 Add `auction.schema.json` with the value types and the explicitly
      listed coercion ruleset.
- [x] 1.8 Emit exact round-trip evidence: every field of every entry equal to the
      committed source, covering all 7 keys across all 3 entries.
- [x] 1.9 Merge a new `auctions` section into the package manifest, leaving every
      prior section byte-identical.
- [x] 1.10 Prove idempotence: two consecutive runs produce byte-identical output
      and manifest section.

## 2. Normalization verification

- [x] 2.1 `python -B packages/game-content/tools/build_auctions.py` exits 0.
- [x] 2.2 `python -B -m unittest discover -s packages/game-content/tests -p
      test_build_auctions.py -v` passes.
- [x] 2.3 `python -B packages/game-content/tools/validate_content.py` exits 0 with
      the new output and schema counted.
- [x] 2.4 Confirm `git status` shows **no** change to `config/auctionhouse.json`,
      any legacy module, any save or any fixture.
- [x] 2.5 Confirm **no `auctions/` directory** exists in the repository after the
      build — the probe's containment property must hold for the builder too.

## 3. Client projection — `apps/client-godot/scripts/social/`

- [x] 3.1 Add a read-only projection module reading the committed schedule
      **through the normalized content registry only**.
- [x] 3.2 Project `legacy_id`, `level`, `interval`, `price`, `priceIncrement`,
      `betPrice`, unit id and resolved unit name, in committed order.
- [x] 3.3 Add the single named conversion `interval → seconds` with factor `60`,
      a named inverse, and a round-trip assertion over every committed entry.
- [x] 3.4 Derive **nothing** else. No price, fee, total, remaining time, round,
      winner or ranking — not inline, not in a helper.
- [x] 3.5 Record the expiry semantics verbatim: `endDate + 1` with no bidder,
      `endDate + 60` with a bidder, round reset to the literal `1`, and
      `count_expired` computed and discarded.
- [x] 3.6 Record the bootstrap defect as an oracle property, citing
      `auctions.py:32` guarding `FILE_AH_CONFIG` while `:33` reads
      `FILE_AH_STATE`, and attributing inertness to **two** independent reasons.
- [x] 3.7 Record each client-dictated refusal with its measurement and label it
      a **divergence**, not parity: the unvalidated bid (bid `1` moved
      `currentPrice` `5000 → 1001`; `-5000` produced `-4000`), client-sent
      `checkFinish`, no winner from amounts, and `won` unconditionally `1`.
- [x] 3.8 Contain **no** state-document creation, default or repair path for this
      surface.
- [x] 3.9 Expose **no** callable action to place, bid on, start, extend or cancel
      an auction, and no countdown, scheduler or clock read.

## 4. Suite — `apps/client-godot/tests/test_auction_schedule.gd`

- [x] 4.1 Assert the projection: three entries, committed order, committed
      `legacy_id` strings, every committed field verbatim, resolved unit names.
- [x] 4.2 Assert exactly one derivation, and assert the **absence** of the others
      mechanically.
- [x] 4.3 Assert the conversion round-trips for every committed entry, from both
      directions and across the one-unit boundary (`60 → 3600`).
- [x] 4.4 Re-derive every zero-consumer and absent-helper figure from the
      committed legacy sources **on every run**, so a legacy edit fails the suite
      rather than silently contradicting it. Cover: `interval`/`expire`
      occurrences outside `auctions.py`; the three commented routes and the
      commented import; resource-token occurrences in the module; comparison
      operators against the four price identifiers.
- [x] 4.5 Pin the declared-function inventory of every delivered module, and
      assert the reserved-name absence **in both directions** over declared names
      (case-folded, by substring), not raw source.
- [x] 4.6 Assert the wording scope: the delivered text says "no **server-side**
      reader" and never "dead" or "unused". Scope the token list to
      non-forbidden words, as `godot-friends` had to.
- [x] 4.7 Delegate the transport-token and raw-config-path guards to
      `test_project_scope.gd` by asserting the owner exists and its allow-list
      covers both delivered modules — do **not** duplicate a guard its own owner
      forbids.
- [x] 4.8 Prove the guards by injection: invented duration/round/winner helpers,
      a suffixed reserved-name helper, a name matching a committed field, and
      **one probe borrowing no reserved word** so the inventory is proven to be
      the real gate. Measure each probe's failure count and restore every file
      byte-identically.
- [x] 4.9 Assert the corpus figure: **zero** of the 10 genuine save documents
      carry any auction term, **excluding `tests/saves/manifest.json` by name**,
      and assert the exclusion is real by checking the manifest is in fact an
      index.
- [x] 4.10 Assert the registry is the only content path: no delivered module
      references a raw `config/` path for this schedule.
- [x] 4.11 Assert no route, no `apps/compat-api/**` change, and an unchanged
      registered live-phase count.
- [x] 4.12 Write the deterministic evidence report via `--report=<path>`, with
      tables generated from the live projection and registry.
- [x] 4.13 Register the suite in `verify-boot.ps1` and update the header prose
      (hermetic count, live count, assertion count).
- [x] 4.14 Amend `test_project_scope.gd`'s allow-list for the new client sources,
      the new suite and the new report.

## 5. Full verification

- [x] 5.1 `godot --headless --path apps/client-godot --script
      res://tests/test_auction_schedule.gd` exits 0.
- [x] 5.2 Same suite with `--report=<repo>/apps/client-godot/evidence/auction-schedule/report.json`
      is byte-identical across three consecutive runs.
- [x] 5.3 `powershell -File apps/client-godot/verify.ps1` exits 0.
- [x] 5.4 `powershell -File apps/client-godot/verify-boot.ps1` exits 0; inspect
      every log file for `[test] FAIL`, `^ERROR:` **and** `SCRIPT ERROR`.
- [x] 5.5 `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v`
      is **unchanged** — this line touches `apps/compat-api/**` not at all.
- [x] 5.6 `python -B packages/game-content/tools/validate_content.py` exits 0.
- [x] 5.7 `python -B tools/hash-manifest/hash_manifest.py verify` exits 0. Record
      the new entry count and explain the delta.
- [x] 5.8 `openspec validate --all --strict` passes.
- [x] 5.9 `git status` shows no legacy, save, config, fixture or village byte
      changed, and no `auctions/` directory created.
- [x] 5.10 Confirm the content-package byte-form of every new file: the recorded
      digest describes the **committed Git blob form** (LF), and the raw
      working-tree form is recorded separately with its own digest — the defect
      class recorded twice in this project.

## 6. Deviations and corrections

### 6.0 Baseline note, recorded at proposal time

`openspec validate --all --strict` counted **69** items with no active changes and
**70** with this one. My expectation was **71**, from assuming `--all` counts one
item per delta spec. Measured: it counts an active **change** as one item
(`✓ change/auction-schedule-projection`) and validates both delta specs inside it.
So the expected figure for this change is **70** before Sync.

**CORRECTION, measured at Sync.** The sentence this note originally ended with
predicted **71** after Sync and **70** at Archive. Both figures are wrong, by one
each, and the cause is in the note itself rather than in the validator: it
assumed the change adds **one** main spec ("when the new main spec adds an
item"), while `auction-schedule-projection` declares **two** capabilities,
`auction-schedule-normalization` and `godot-auction-schedule`. The validator was
right and the arithmetic was not.

Measured, with both new specs confirmed present and counted:

| Stage | `--specs` | `--all` |
| --- | --- | --- |
| No active change | 69 | 69 |
| Change active, before Sync | 69 | **70** |
| After Sync, both main specs added | **71** | **72** |
| After Archive, change item removed | 71 | **71** |

So the correct sequence for this change is **70 → 72 → 71**, not 70 → 71 → 70. The
structural point stands and is worth keeping: `--all` counts an active **change**
as a single item and validates both delta specs inside it, so a change with *N*
capabilities still costs one item until it is synced.

### 6.1 Recorded during Apply

Every item below was found during implementation or review, not inherited.

**1. Module placement deviated from the task and was corrected by the
orchestrator.** Task 3 named `apps/client-godot/scripts/events/auction_schedule.gd`.
The implementation worker placed both modules under `scripts/social/` instead.
They were moved to `scripts/events/` before acceptance, on two measured facts:
`scripts/social/` holds exactly four modules and every one of them is genuinely
social (`assist_transitions`, `construction_assist_state`, `friends_roster`, and
the pre-existing set), while the closest precedent for reading a committed
schedule through the registry, `premium_purchase.gd`, lives in `scripts/darts/`.
The auction house has no friend, neighbor or assist concept, which is precisely
what the investigation measured, so `social/` would have signalled semantics the
preserved server does not have — the same misleading-name defect `godot-friends`
corrected when its deliver item turned out to name the opposite of the surface.
`scripts/social/` is back to its original four modules; the move touched two
`preload`/`MODULE_PATH`/`*_REPO_PATH` constants and two `test_project_scope.gd`
allow-list entries, and both affected suites were re-run afterwards.

**2. The claim "no `apps/compat-api/**` file is modified" was FALSE, and the
requirement is amended rather than the claim being dropped.** Adding any
normalized output to the content package forces one pinned count inside an
existing compat-API guard to move: `test_research_envelope.py`'s
`test_no_normalized_package_carries_a_research_section` asserts the normalized
file count, so it reads `23` where it read `22`. The spec requirement, design D5
and the proposal's summary were all amended to the narrower claim that is true —
no route, no endpoint, no envelope, no dispatcher, no save shape — with the
cause recorded in each. The guard's meaning is untouched and in fact slightly
strengthened: it still requires that no normalized file carries a research
section, and it now also scans the new `auctions.json`, which carries no
research key. This is a general property of the package, not a quirk of this
line, and it is recorded so the next builder extension that reaches
`apps/compat-api/**` knows the edit is expected and narrow instead of
discovering it as a violation.

**3. A false correction, found in the delivered report and reverted.** The
first draft of the suite recorded a "FOURTH CORRECTION" asserting that two
searched tokens disagree between the raw-substring and whole-token counting
rules, naming `mana` alongside `xp`, and declaring the committed
`resource_tokens_substring.mana = 0` wrong by one. That was wrong, and the
committed figure is correct. The suite counted raw occurrences in a **case-folded**
copy of the module (`module_text.to_lower()`), while `build_auctions.py` counts
them **case-sensitively** with `source_text.count(token)`; the two sides were
measured under different rules and then compared against each other.
Re-measured under the builder's own rule, `mana` has zero raw and zero
whole-token occurrences, so only `xp` disagrees. The suite now measures the
builder's rule for every comparison against a committed figure, and reports the
case-folded view separately as the differently-ruled measurement it is —
`Manage` at `auctions.py:161` really does contain that letter run — without
letting it make a claim about the committed figure. The false correction was
replaced rather than deleted, because deleting it would hide the real defect.
My own first re-measurement of this was also wrong in the opposite direction
(case-sensitive, reporting zero everywhere) before the case-folded reading
explained it; the case-folded count is 1 and the case-sensitive count is 0, and
both are now pinned separately so neither can be confused for the other.

**4. Two defects of the orchestrator's own tooling, recorded because both
nearly produced a false conclusion.**
  - *Backtick escaping.* A replacement block was first written through a
    PowerShell double-quoted here-string. PowerShell consumes backticks as
    escapes: the `b` of `build_auctions.py` vanished and the `r` of
    `resource_tokens_substring` became a literal carriage return that split a
    line. The suite then failed to parse. All such edits were moved to script
    files, which is the harness fix.
  - *Encoding on redirect.* `git show HEAD:<path> > file` writes **UTF-16LE**,
    so a subsequent `Select-String` under-matched and I briefly concluded that
    `HEAD`'s suite code did not emit the report block it demonstrably emits.
    Re-checked against the working-tree file, which is byte-identical to `HEAD`
    for that path. Byte-safe reads only, from here.

**5. A stale committed report from an earlier line was exposed here, and
regenerated.** Regenerating the nine prior evidence reports changed
`evidence/unit-production/report.json` by more than the package census: an
`experience` block appeared that the committed file never had. This was
investigated rather than accepted, because the extra block was not a census
field. The committed artifact is stale, and the staleness predates this change:
`test_unit_production.gd` emits `"experience": ProductionFlow.experience_record()`
and `production_flow.gd` supplies `arm_asymmetry`, `recorded_kinds` and
`field_repaired`, but both files are **unmodified by this change**. The M9
`godot-unit-experience` line amended the module and the suite and did not
regenerate this report. Nothing catches it: `verify-boot.ps1` runs every suite
**without** `--report=`, so committed report bytes are never compared against
their own generator. Regenerating is correct — leaving it stale would preserve a
false claim that rerunning reproduces the bytes — and the finding is recorded
here because the gap is real: **no automated check compares any committed
evidence report against the suite that writes it.** The other eight reports
differ on package-census fields only, each verified leaf by leaf.

**6. Nine prior evidence reports were regenerated, and only for the census.**
Adding `auctions` changed the package from 22 to 23 outputs, so every report
recording that census legitimately changed. Each was diffed leaf by leaf against
`HEAD` and the differing paths are only
`package_files`, `package_sha256`, `outputs_verified`, `bytes_verified`,
`manifest_outputs_verified`, `manifest_bytes_verified`, `normalized_files` and
`content_absence` — plus, for `unit-production`, the item in §5 above. Leaving
them stale would break each line's claim that rerunning reproduces its bytes.

**7. `references_checked` stays at 604.** The three new auction unit references
are real but are **not** counted by the shared validator, so the cross-domain
reference edge is proved by the builder's own tests alone and not by
`validate_content.py`. This is recorded rather than left to look like full
validator coverage.

**8. `openspec validate --all --strict` counts 70, as §6.0 predicted.** No
further correction to that figure — **at Apply**. Sync then added the two main
specs and the figure moved to **72**, which §6.0's original prediction of 71 got
wrong by one; the correction and the measured table are in §6.0.

**9. Verification actually run, at the final state, after all edits above.**
  - `test_auction_schedule.gd`: **1218 checks**, exit 0.
  - `test_project_scope.gd`: **2223 checks**, exit 0.
  - `verify.ps1`: exit 0, `PASS all checks succeeded`.
  - `verify-boot.ps1`: exit 0, `PASS all checks succeeded`. One command and two
    assertions added, both `ok: true`; guard digest identical before and after
    (`6978b959…ff348`); port 5056 released; no working-tree `saves/`.
  - **1092** log files inspected for `[test] FAIL`, `^ERROR:` **and**
    `SCRIPT ERROR`: **zero** hits on all three. The first attempt at this grep
    matched zero files because the logs are `.txt` and the filter said `.log`;
    the zeros were vacuous and were re-measured.
  - compat suite: `Ran 3077 tests … OK`, exit 0 — the baseline, unchanged.
  - `validate_content.py`: exit 0, `result: valid`, 23 files, 22 schemas, 604
    references.
  - `hash_manifest.py verify`: exit 0, **3258 entries, 758423699 bytes**,
    unchanged.
  - `openspec validate --all --strict`: **70 passed, 0 failed**.
  - Report: 36,636 bytes, sha256 `495d29abd4e38ae01be36222…`, LF form, and
    **byte-identical across three consecutive runs**.

**10. Five injection probes re-run independently by the orchestrator, not taken
on the worker's word.** Failure counts are measured, and every restore is
verified by sha256:
  - a neutral helper borrowing **no** reserved word: **4** `[test] FAIL` lines.
    This is the probe that matters most, because it shows the declared-function
    inventory pin is the real gate and the reserved-name guard is the belt.
  - a **suffixed** reserved stem (`winner` inside a longer name): **7** lines. An
    exact-name check would have passed this.
  - arithmetic in a non-permitted function: **6** lines, so the allowance is
    per-function and not per-file.
  - the forbidden word `dead` in the schedule module: **1** line.
  - the forbidden word `unused` in the **oracle** module: **1** line, so the
    wording guard covers both modules.
  All five produced real `[test] FAIL` lines with no parse error, every restore
  was byte-identical (`c04b416d8ef1c891…` and `6db9d6e6d1ec0558…`), and the
  post-probe suite returned to exit 0.

**11. No preservation material changed.** `auctions.py`,
`config/auctionhouse.json`, `tests/saves/`, `villages/`, `tests/fixtures/`, and
the normalized package, its schemas and its manifest all show **zero** modified
paths. No runtime `auctions/` directory was created, which is the whole point of
recording the module's bootstrap defect rather than repairing it.

### 6.2 Recorded at the Archive gate — a required check I did not run, and the defect it hid

**12. Task 2.2 was never executed during Apply, and it was not optional.**
Task 2.2 requires
`python -B -m unittest discover -s packages/game-content/tests -p "test_build_auctions.py"`.
Section 5's verification list ran `validate_content.py` (task 5.6) and **not**
the builder's own suite, and I reported the Apply stage verified on that basis.
That was a claim about a check I had not run, and it was wrong in a way that
would have shipped broken work.

Running it at the Archive gate produced `Ran 86 tests ... FAILED (failures=1)`:

```
FAIL: test_committed_manifest_prior_sections_are_byte_identical
AssertionError: Lists differ: [] != ['auctions']
```

**13. The defect is a git-state-dependent guard that could only ever pass once.**
The assertion compared the working-tree manifest against
`git show HEAD:packages/game-content/manifest.json` and required
`set(current) - set(committed) == ["auctions"]` — that the builder adds exactly
its own section. That is true **only while the section is uncommitted**. Measured:
`auctions` absent from `af63a77~1`, present from `af63a77` onward, and present
in `HEAD` today. So the test was green on the Apply branch and became
permanently red the instant the Apply PR merged, **including on `main`**,
forever. It was a time bomb with a one-run fuse, and it was in a file the
preservation manifest's byte guard does not execute.

**14. The correction, and why the original form cannot be restored.** The claim
under test is real — the merge re-serializes the whole manifest with
`sort_keys`, so a prior section changing would mean the working manifest drifted
for a reason other than this builder's section. Only its *reference* was wrong.
The corrected form is state-independent and holds both before and after the
commit: **no committed section may be removed**, **this builder's own section is
present**, and **every section other than its own is byte-identical**.
`auctions` is excluded from the byte-identity comparison because this builder
owns it and is expected to have changed it.

**15. The loosened guard is re-proven by injection, not trusted**, because a
correction that loosens an assertion is exactly the change that can silently
stop guarding. Three probes, each restored byte-identically
(sha256 `e336f8dc218e2e9e…` before and after every one, `21` sections):

| Probe | Injected | Result |
| --- | --- | --- |
| I1 | prior section `coercion_ruleset` drifts to `{"drifted": true}` | **detected** — `AssertionError: {'drifted': True} != 'coercion-ruleset-v1' : coercion_ruleset` |
| I2 | unrelated section `content_fingerprint` removed | **detected** — the no-removal assertion names it |
| I3 | this builder's **own** section `auctions` removed | **detected** — the no-removal assertion names it |

**I3 is informative and is recorded rather than tidied**: removing the builder's
own section also fires the **no-removal** assertion, because `auctions` *is* in
the committed manifest. So the added presence assertion is **unreachable in the
committed state** — it is a belt for the pre-commit window only. It is kept
because it is cheap and it is what would catch a builder that never wrote its
section at all in a fresh checkout, but this project records which guard is the
real gate, and here the no-removal assertion is.

**16. A harness defect of my own, recorded because it nearly produced three fake
passes.** The first run of the injection probe reported
`RESULT: A PROBE FAILED TO DETECT` while **all three probes had failed
correctly** with the right `AssertionError`s. The probe asserted on expected
*message text*; unittest reformats it, and the assertion that fires first is
not always the one the probe was aimed at. The detection criterion was corrected
to the test failing **plus which assertion named the target**, which is the claim
worth reporting. Asserting on message text in a guard harness is the same defect
class as asserting on a byte count that is line-ending dependent.

**17. The detection gap this exposed, which is larger than the defect.**
`packages/game-content` appears in `verify.ps1` exactly **once**, at line 197, and
only inside the SHA-256 pre/post **byte** guard over the directory. **No battery
executes any of the twelve** `packages/game-content/tests/test_*.py` suites — they
are run by hand. That is why task 2.2 was missed, why this time bomb merged, and
it is the **same class** as the stale-evidence-report gap already recorded in
§6.1: a committed artifact with **no automated check comparing it against the
code that produces it**. Two instances, one instrument, and neither is caught by
`verify.ps1` or `verify-boot.ps1`. Closing it is recorded as a follow-up and
**not** done here, because wiring twelve builder suites into a display-sensitive
Windows battery is a separate change with its own evidence, not a footnote to a
manifest guard.

**18. Post-fix verification actually run**, all on this fix branch:
`python -B -m unittest discover -s packages/game-content/tests -p "test_build_auctions.py"`
→ `Ran 86 tests ... OK`, exit 0; the full
`python -B -m unittest discover -s packages/game-content/tests -p "test_*.py"`
→ **`Ran 559 tests ... OK`**, exit 0;
`validate_content.py` → exit 0, `result: valid`, **23 files, 22 schemas, 604
references**; `hash_manifest.py verify` → exit 0, **3258 entries, 758423699
bytes**, unchanged. The only modified path in the working tree is the one test
file.

**Fix branch:** `fix/auction-manifest-section-guard`, merged before the Archive
stage. The Archive stage is therefore not purely archival for this change, and
that deviation is recorded here rather than hidden inside it.

### 6.3 Recorded at the Archive gate — ticking 48 boxes that Apply never ticked

**19. All 48 boxes were unchecked at the Archive gate**, and one of them (2.2)
had been reported verified without ever being run. Ticking them on the strength
of the boxes' own history would repeat exactly that failure, so **no box was
ticked until its task was re-derived from the implementation**. A throwaway
verifier re-checks each task's claim and **refuses to write on a red result**;
the result was **35 mechanically re-derived checks PASS / 0 FAIL**, plus 13
measured live in the transcript (1.10, 2.1, 2.2, 2.3, and 5.1-5.10), covering
all 48.

**20. The verifier's first run reported 11 FAILs and every one was its own
defect, not the delivered work's.** All eleven are recorded because a checker
that cries wolf eleven times has told you nothing:

| Task | What the verifier did wrong |
| --- | --- |
| 1.3 | split the builder on a Python ``def `` to find its header |
| 1.4 | searched for a literal `* 60`, so it could not tell the two **prose** mentions of the legacy expression from a conversion |
| 1.5 | read `normalized/units.json` as a list; it is a dict, so the name index came out **empty** and every comparison was vacuous |
| 1.7 | looked for `coercion_ruleset`; the schema key is `x-coercion-ruleset` |
| 1.9 | probed manifest keys that do not exist (inputs live under `inputs`) |
| 3.1 | a `str.replace` with a zero count, which is a no-op |
| 3.3 | used a **Python** `def\s+` regex against GDScript's `func`, and demanded a literal `60` where the code correctly uses the named constant `SECONDS_PER_MINUTE` — so it found zero arithmetic and reported **the opposite of the truth** |
| 3.4, 3.9 | scanned `fee`, `winner`, `ranking`, `countdown`, `scheduler` in **raw source**, so the prose documenting their absence counted as their presence — the precise inversion those claims are about |
| 3.5 | searched for the strings `+ 1` / `+ 60`; the semantics are recorded as structured keys |
| 3.7 | searched for `checkFinish`; the recorded key is `client_sent_completion_flag` |

The fix was **not** to weaken the checks but to strip GDScript `##` comments and
string payloads before scanning for forbidden tokens — the two-state lexer this
project already had to build for `godot-construction-assist` when its
reserved-name guard tripped on its own inventory text. **A forbidden-token scan
over raw source cannot distinguish "this helper exists" from "this module says
no such helper exists", and every one of those claims is the second kind.**

**21. The lexer then had two more defects of its own, found by measurement.**
Stripping string payloads removed exactly the tokens task 3.2 checks, because
GDScript **dictionary keys are string literals** — so two lexers were needed,
one for forbidden-token scans and one that strips comments but keeps literals.
And a `"""` docstring was not recognised, so the lone `"` in
`auction["interval"]` **falsely closed it** and the rest of the builder returned
to "code", making a prose line report as a conversion. Both were found by the
verifier disagreeing with code I had already read, not by reading the lexer.

**22. The verifier was then probed, because one that has only ever reported
success is indistinguishable from one that does nothing.** **Twelve probes, all
twelve detected, every restore byte-identical by sha256**, post-probe green:

| Probe | Injected | Detected by |
| --- | --- | --- |
| P1 | a third `* SECONDS_PER_MINUTE` | 3.3 |
| P2 | a `derive_winner` helper | 3.4 |
| P3 | `FileAccess.open` on a state document | 3.8 **and** 3.1 |
| P4 | a `start_countdown` helper | 3.9 |
| P5, P9 | rename / remove the projected `betPrice`, `priceIncrement` | 3.2 |
| P6 | `divergence: true` → `parity: true` | 3.7 |
| P7 | no-bidder boundary `1` → `999` | 3.5 |
| P8 | the forbidden word `dead` | 4.6 |
| P10-P12 | coerce `legacy_id` to int, flip the consumption flag, emit a `seconds` field, **in the builder source** | **1.11** |

**23. P10-P12 exposed a uniform gap in my own verifier, and it is the third
instance of one class.** Tasks 1.2/1.4/1.6/1.8 all inspect the **committed
output**, so a change to the **builder source** that would emit something
different was invisible while the committed file was still checked in isolation —
an artifact checked without the code that produces it. The same class as the
stale-report gap (§6.1) and the missing-battery gap (item 17). Closed by an
added check, **1.11**: rebuild into a **temporary work tree** with `--out-root`
and compare the produced bytes against the committed ones — measured identical,
**1542 bytes, sha256 `8e9c1d958010b24a…`**. 1.11 is **not** ticked, because it was
not in the plan; it is a check this verification added and it is recorded here
instead.

Building that temporary work tree was itself non-obvious: an **empty**
`--out-root` fails with `FileNotFoundError` on
`packages/game-content/manifest.json`, because the builder merges into an
existing manifest and reads the normalized units package for its reference edge.
The shape was taken from the builder's own suite rather than guessed.

**24. The probe harness damaged two delivered files, and this is the third
recorded instance of the same defect class.** It read with universal newlines and
wrote text back, **converting both `auction_schedule.gd` and `auction_oracle.gd`
from CRLF to LF**, so all ten restores honestly reported
`restored byte-identical: False` and the tree was left dirty. Recovered with
`git checkout --` and confirmed through `git cat-file` that the committed blobs
still hash to the recorded **`c04b416d8ef1c891…`** and **`6db9d6e6d1ec0558…`**
at **19627** and **20744** bytes with **zero** CRLF — so no damage reached the
repository, and the honest signal is what caught it. Prior instances: the
byte-count guard fixed in PR #280, and a `git show > file` redirection writing
**UTF-16LE** earlier in this stage. **Three instances, one root cause: tooling
that rewrites bytes without asserting the bytes it read are the bytes it wrote
back.** The fix is decoding UTF-8 directly rather than through text mode, which
leaves a CRLF pair as two literal characters.

**Disposition of the scratch tooling:** the verifier and its probe were
**deleted, not committed**. They are honest instruments and they found four real
defects, but they are single-use Archive-gate scaffolding, and committing a new
tool during an archival stage — wired into no battery, guarded by nothing — would
repeat the missing-battery gap this stage just recorded. The findings are in this
section; the instruments are not in the tree.
