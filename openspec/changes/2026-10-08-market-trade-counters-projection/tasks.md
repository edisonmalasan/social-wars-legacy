# Tasks — market / trade counters

Binding investigation: `docs/legacy-m11-special-mechanics.md` (merged `1c8786b`).
Binding design: `design.md`. Every task below is scoped to the two read-only modules and one
hermetic suite described in design D11.

**Ownership.** Task 1 is the only implementation task; task 2 is the only verification task.
The root orchestrator owns this file, the specs, and acceptance. No implementation subagent
may edit `proposal.md`, `design.md`, `specs/`, or `tasks.md`.

---

## 0. Preconditions, re-measured before anything is written

- [ ] 0.1 Re-measure, from the working tree, and record in the report: the **63** named
      dispatcher branches on **raw** text (branch names live in string literals, so a
      code-only lexer returns zero — the one place the raw/code split cannot apply to the
      token); the trade-counter writer and reader sets; the **8** `MARKET_*` keys with their
      raw and quoted counts over **all eleven** modules; and the **10** save documents'
      `(numTradesDone, timestampLastTrade)` pairs.
- [ ] 0.2 Confirm the baseline is unchanged before the first edit and record it: hermetic
      suites **49**, live phases **23**, `verify-boot.ps1` assertions **228**, guard digest
      `6978b959…ff348`, compat **3,077 tests OK**, validator **23 files / 22 schemas / 604
      references**, manifest **3,258 entries / 758,423,699 bytes**, `openspec --all --strict`
      **71 passed / 0 failed**.
- [ ] 0.3 Confirm containment: `auctions/` and `saves/` absent, and `git status` clean apart
      from this change's own new paths. **Never run legacy Python that touches `auctions/`
      with the repository root as the working directory** (`AUCTIONS_DIR = ./auctions` and
      `__init__` calls `os.makedirs`).

---

## 1. Implementation — two read-only modules

**Owned files (this task's entire write surface):**

- `apps/client-godot/scripts/market/trade_counters.gd` (new)
- `apps/client-godot/scripts/market/market_schedule.gd` (new)
- `apps/client-godot/tests/test_market_trade.gd` (new)

- [ ] 1.1 `trade_counters.gd`: a typed read-only projection over the map and private state.
      Report the committed count and the committed last-trade instant **verbatim**. Derive
      **no** price and move **no** resource. Expose **no** callable action.
- [ ] 1.2 The cap is **one** named constant read from the branch literal at
      `command.py:470`, documented in-code as the branch's own value. The projection reports
      that the cap is **stored and never enforced**, and carries the measured reason: the
      count's only reader is its own increment at `command.py:469`.
- [ ] 1.3 Reproduce the branch's remaining-trades arithmetic **unclamped**, as a separately
      labelled field from the stored count, so the divergence at `command.py:473` is visible
      rather than silent. At or above the cap the reported value is **negative**. The module
      contains no clamping of this value.
- [ ] 1.4 Report the day bucket of the recorded instant and of the server clock, and the
      predicate `now // 86400 != last_trade // 86400` between them. **Perform no reset** and
      **do not reimplement** `engine.reset_stuff`; reference it as the owner.
- [ ] 1.5 **Fail closed** on an absent or non-integer count or instant: report the field as
      unavailable, report no derived value needing it, and carry the recorded field beside the
      refusal, untouched. (Precedent: the M6 projection-evidence gap, where a key that nothing
      produces must render as an explicit missing-field indicator rather than a default.)
- [ ] 1.6 `market_schedule.gd`: project the **8** committed `MARKET_*` values verbatim with
      their committed types, **read through the existing normalized content registry** — never
      transcribed. Carry each value's measured zero-consumer status.
- [ ] 1.7 Compute **no** economy from the schedule: no price, cost, period, percentage, or
      increment bound. The module contains **no** multiplication or division over a projected
      committed value, so the no-derivation claim is mechanically true rather than asserted.
- [ ] 1.8 Record both divergences as comments at the site, with line references: resource
      movement would arrive via `engine.apply_resources` before the dispatcher opens at
      `command.py:42`, and the instant is client-writable through `fast_forward`'s
      client-supplied `seconds = args[0]`.
- [ ] 1.9 Reference, do not reimplement: the production queue (`godot-unit-queues`), the bonus
      ladders (`godot-rewards`), the darts instants (`godot-darts`). The modules name **none** of
      those foreign fields — not even in a comment.

---

## 2. Verification — one hermetic suite

- [ ] 2.1 `test_market_trade.gd` covering every requirement and scenario in the spec delta,
      registered in `verify-boot.ps1`'s hermetic list. Target the family's usual shape: several
      hundred checks, `--report=` supported.
- [ ] 2.2 **Re-measure, do not inherit.** The suite re-derives, every run: the branch set on
      raw text; the writer/reader sets for both counters; the `MARKET_*` consumer counts over
      all eleven modules; and the corpus pairs across all ten documents. Every count is
      reported under the rule that holds it.
- [ ] 2.3 Assert the day-bucket finding that shapes every claim limit: **8 of 10** documents
      record `timestampLastTrade == 0`, for which the reset predicate is **unconditionally
      true** and the count is cleared on every load. Assert `Nerri.json` is the **only**
      document at the cap.
- [ ] 2.4 Assert the `Neutral.json` proof's **premises**, not just its conclusion: that
      `command.py:471` is the only site that can raise the instant, and that
      `command.py:913` subtracts a client-supplied quantity and floors at zero. These are what
      make "the reset fired" a proof rather than an inference.
- [ ] 2.5 Assert the **no-clamping** property directly (design D3), so the negative
      remaining-trades value cannot be "helpfully" corrected.
- [ ] 2.6 Assert the ownership boundaries (design D8): each declared owner spec **exists** and
      projects the deferred surface, so no boundary is an orphan; and this line's modules name
      none of the foreign fields.
- [ ] 2.7 Write the deterministic `market-trade-report-v1` evidence report from the suite
      itself, with its tables generated from the live modules so they cannot drift from the code
      they document. Re-run and confirm the bytes are identical across three consecutive runs.
- [ ] 2.8 **Anti-invention guards proven by injection, not trusted** (design D9). Inject at
      minimum: a new static helper of any name; a **suffixed** helper wearing a reserved name as
      a prefix (the exact miss recorded on the friends line — an exact-name check passes it);
      an invented `trade_cost`; an invented `cap_for`; an invented `enforce_trade_limit`; an
      invented `is_trade_allowed`; a clamping of the remaining-trades value; a
      `MARKET_*` name in a delivered module; and a foreign-field reference. **Measure each
      probe's failure count**, do not record only its non-zero exit. Every restore is verified
      by sha256 with zero NUL bytes and the baseline's final-newline state, and
      `git diff --numstat --ignore-cr-at-eol` plus `git status --short` must equal their
      pre-probe values.
- [ ] 2.9 Harness discipline, from the recorded defects: normalise to LF **before** mutating a
      probed file, and **abort if a probe fails with no `[test] FAIL` line** — a parse-error
      detection proves nothing about a guard. Pin the restored file's final byte to the
      baseline rather than asserting a universal trailing-newline rule, which was wrong for an
      already-delivered file.
- [ ] 2.10 Amend `test_project_scope.gd`'s allow-list for exactly the new client sources and
      the new report, and re-run it. Confirm the 13 `FORBIDDEN` tokens and
      `test_town_gate.gd`'s `RUNTIME_NEEDLES` needed **no** relaxation — verified in design
      D10 that none collides.

---

## 3. Batteries and gates

- [ ] 3.1 `powershell -File apps/client-godot/verify.ps1` — exit `0`.
- [ ] 3.2 `powershell -File apps/client-godot/verify-boot.ps1` — exit `0`, **50** hermetic
      suites (was 49), **23** live phases (**unchanged** — no live phase is delivered),
      guard digest `6978b959…ff348` **identical before and after**, and zero `[test] FAIL`,
      `^ERROR:`, or `SCRIPT ERROR` lines across every log file.
- [ ] 3.3 `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v` —
      **3,077 tests OK**, exit `0`, a **verified re-run baseline**, because
      `apps/compat-api/**` is not touched at all. If it differs, that is a finding to
      investigate, not a number to update.
- [ ] 3.4 `python -B packages/game-content/tools/validate_content.py` — exit `0`,
      `result: valid`, **23 files / 22 schemas / 604 references**.
- [ ] 3.5 `python -B tools/hash-manifest/hash_manifest.py verify` — **3,258 entries /
      758,423,699 bytes**, exit `0`.
- [ ] 3.6 `openspec validate --all --strict` — **72 passed / 0 failed**. Measured at
      proposal time: `--all` validates **71 main specs plus 1 change**, and the change appears
      in the output as `✓ change/2026-10-08-market-trade-counters-projection`. Note the total
      is **72 both during the change and after Sync**, because Sync converts the change into a
      72nd main spec and archiving removes the change — so the number alone does not say
      which stage is done. Record the *composition*, not just the total. Measured
      `openspec validate 2026-10-08-market-trade-counters-projection --strict` → valid, exit
      `0`.
- [ ] 3.7 `git status` shows **no** legacy, config, save, village, content-package,
      conversion-package, registry-manifest, or fixture byte changed.

---

## 4. Recorded gaps and limits — to be carried into the PR description verbatim

- [ ] 4.1 **No route, no compat-API change, no live phase, no executed-legacy fixture.** All
      four are decisions with measured reasons (design D1, D7), not omissions. The fixture
      refusal is a property of the corpus — 8 of 10 documents make the reset predicate
      unconditionally true — and additionally a fixture licensing a round trip this line
      refuses.
- [ ] 4.2 **No enforcement, no price, no period, no percentage.** `numTradesDone`'s only
      reader is its own increment, so the cap is a stored value; the eight committed
      `MARKET_*` values have zero consumers.
- [ ] 4.3 **`MARKET_MAX_NUM_TRADES == 20` matching the branch literal is a coincidence**,
      recorded as one. The cap is never derived from it.
- [ ] 4.4 **The unclamped print is reproduced, not corrected**, and is negative from the 21st
      trade onward.
- [ ] 4.5 **Two divergences are recorded, not reproduced**: client-sent resource movement, and
      the client-writable instant.
- [ ] 4.6 **`Nerri.json` is one data point.** No claim of parity for any other document, and
      no claim that any player ever hit the cap twice.
- [ ] 4.7 **Absence of a server rule says nothing about the Flash client**, which may have
      displayed, gated, or hid a market entirely client-side.
- [ ] 4.8 **No ordinal** is claimed for the zero-consumer count. Four conflicting ordinals
      already exist in the delivered records, each over a different scope.
- [ ] 4.9 **Not delivered here, recorded by the investigation:** the atom-fusion **powerup
      purchase** (`buy_powerups` is a `# TODO` with a committed six-row ladder and zero
      consumers) — candidate #2, adjacent to an owned surface; `first_time_marketplace` — a
      2-statement unowned branch, candidate #3; `rt_open_graph_unit` with
      `crossPromotionsFinished`/`unlockedSkins` — candidate #4; and the **24-declaration**
      `SPELL_*`/`TECH_*` coverage gap beside `godot-mission-vocabulary` — candidate #5.
- [ ] 4.9b Carry the investigation's **eight instrument defects** into the report. Two of them
      — counting quoted keys through a lexer that blanks string contents, and the name/stem
      ownership test — would each have produced a false headline claim, and one produced a
      **false mismatch** that would have trained the reader to dismiss its output.
- [ ] 4.10 Re-run before treating any of the **ten recorded flaky surfaces** as a regression:
      the `5055`/`5056` `port_is_free` assertions; `verify-boot.ps1` treating any `^ERROR:` as
      a script error (grep `SCRIPT ERROR` too); the display-sensitive `verify.ps1`; the
      `test_base.gd` abort-as-pass defect; the session `server_time` field; the collect
      sub-second time budget; the dead `VOLATILE_PLAYER_INFO_FIELDS` exemption at the wrong
      nesting depth; and the two committed-report gaps.

---

## 5. Archive

- [ ] 5.1 Confirm the roadmap `Project Status` block records this line and that M11's exit
      criterion can now be assessed. **Root orchestrator only.**
- [ ] 5.2 Sync the new capability into `openspec/specs/godot-market-trade-counters/spec.md`.
      **No existing spec is amended** — the single existing mention,
      `godot-building-resources/spec.md:119`, is an out-of-scope note this line satisfies.
- [ ] 5.3 Archive as `2026-10-08-market-trade-counters-projection` on
      `chore/archive-market-trade-counters`, **merge commit**, branch deleted, back to updated
      `main`.
