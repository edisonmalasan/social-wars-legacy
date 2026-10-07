# Tasks

## 1. Normalization — `packages/game-content/tools/build_auctions.py`

- [ ] 1.1 Read `config/auctionhouse.json` read-only. Do **not** import `auctions.py`.
- [ ] 1.2 Emit one definition per committed entry, preserving committed order.
      `legacy_id` stays the committed **string** `uuid`; `unit`, `level`,
      `interval`, `price`, `priceIncrement`, `betPrice` verbatim.
- [ ] 1.3 Record the content source as the standalone file `config/auctionhouse.json`,
      not one of `main.json`'s 20 keys.
- [ ] 1.4 Perform **no** conversion of `interval`. Add no `seconds`/`duration`
      field and no conversion factor as data.
- [ ] 1.5 Resolve `unit` against `normalized/units.json`, carrying the resolved
      display name. An unresolvable id is **recorded as unresolved**, still
      emitted, in order, and reported — never dropped or invented.
- [ ] 1.6 Carry `betPrice` and record `bet_price_consumed: false`, citing the
      zero-consumer measurement (no `gold/coins/cash/wood/steel/oil/xp/mana/
      energy/cost/apply_resources`, and `apply_resources` is never called).
- [ ] 1.7 Add `auction.schema.json` with the value types and the explicitly
      listed coercion ruleset.
- [ ] 1.8 Emit exact round-trip evidence: every field of every entry equal to the
      committed source, covering all 7 keys across all 3 entries.
- [ ] 1.9 Merge a new `auctions` section into the package manifest, leaving every
      prior section byte-identical.
- [ ] 1.10 Prove idempotence: two consecutive runs produce byte-identical output
      and manifest section.

## 2. Normalization verification

- [ ] 2.1 `python -B packages/game-content/tools/build_auctions.py` exits 0.
- [ ] 2.2 `python -B -m unittest discover -s packages/game-content/tests -p
      test_build_auctions.py -v` passes.
- [ ] 2.3 `python -B packages/game-content/tools/validate_content.py` exits 0 with
      the new output and schema counted.
- [ ] 2.4 Confirm `git status` shows **no** change to `config/auctionhouse.json`,
      any legacy module, any save or any fixture.
- [ ] 2.5 Confirm **no `auctions/` directory** exists in the repository after the
      build — the probe's containment property must hold for the builder too.

## 3. Client projection — `apps/client-godot/scripts/social/`

- [ ] 3.1 Add a read-only projection module reading the committed schedule
      **through the normalized content registry only**.
- [ ] 3.2 Project `legacy_id`, `level`, `interval`, `price`, `priceIncrement`,
      `betPrice`, unit id and resolved unit name, in committed order.
- [ ] 3.3 Add the single named conversion `interval → seconds` with factor `60`,
      a named inverse, and a round-trip assertion over every committed entry.
- [ ] 3.4 Derive **nothing** else. No price, fee, total, remaining time, round,
      winner or ranking — not inline, not in a helper.
- [ ] 3.5 Record the expiry semantics verbatim: `endDate + 1` with no bidder,
      `endDate + 60` with a bidder, round reset to the literal `1`, and
      `count_expired` computed and discarded.
- [ ] 3.6 Record the bootstrap defect as an oracle property, citing
      `auctions.py:32` guarding `FILE_AH_CONFIG` while `:33` reads
      `FILE_AH_STATE`, and attributing inertness to **two** independent reasons.
- [ ] 3.7 Record each client-dictated refusal with its measurement and label it
      a **divergence**, not parity: the unvalidated bid (bid `1` moved
      `currentPrice` `5000 → 1001`; `-5000` produced `-4000`), client-sent
      `checkFinish`, no winner from amounts, and `won` unconditionally `1`.
- [ ] 3.8 Contain **no** state-document creation, default or repair path for this
      surface.
- [ ] 3.9 Expose **no** callable action to place, bid on, start, extend or cancel
      an auction, and no countdown, scheduler or clock read.

## 4. Suite — `apps/client-godot/tests/test_auction_schedule.gd`

- [ ] 4.1 Assert the projection: three entries, committed order, committed
      `legacy_id` strings, every committed field verbatim, resolved unit names.
- [ ] 4.2 Assert exactly one derivation, and assert the **absence** of the others
      mechanically.
- [ ] 4.3 Assert the conversion round-trips for every committed entry, from both
      directions and across the one-unit boundary (`60 → 3600`).
- [ ] 4.4 Re-derive every zero-consumer and absent-helper figure from the
      committed legacy sources **on every run**, so a legacy edit fails the suite
      rather than silently contradicting it. Cover: `interval`/`expire`
      occurrences outside `auctions.py`; the three commented routes and the
      commented import; resource-token occurrences in the module; comparison
      operators against the four price identifiers.
- [ ] 4.5 Pin the declared-function inventory of every delivered module, and
      assert the reserved-name absence **in both directions** over declared names
      (case-folded, by substring), not raw source.
- [ ] 4.6 Assert the wording scope: the delivered text says "no **server-side**
      reader" and never "dead" or "unused". Scope the token list to
      non-forbidden words, as `godot-friends` had to.
- [ ] 4.7 Delegate the transport-token and raw-config-path guards to
      `test_project_scope.gd` by asserting the owner exists and its allow-list
      covers both delivered modules — do **not** duplicate a guard its own owner
      forbids.
- [ ] 4.8 Prove the guards by injection: invented duration/round/winner helpers,
      a suffixed reserved-name helper, a name matching a committed field, and
      **one probe borrowing no reserved word** so the inventory is proven to be
      the real gate. Measure each probe's failure count and restore every file
      byte-identically.
- [ ] 4.9 Assert the corpus figure: **zero** of the 10 genuine save documents
      carry any auction term, **excluding `tests/saves/manifest.json` by name**,
      and assert the exclusion is real by checking the manifest is in fact an
      index.
- [ ] 4.10 Assert the registry is the only content path: no delivered module
      references a raw `config/` path for this schedule.
- [ ] 4.11 Assert no route, no `apps/compat-api/**` change, and an unchanged
      registered live-phase count.
- [ ] 4.12 Write the deterministic evidence report via `--report=<path>`, with
      tables generated from the live projection and registry.
- [ ] 4.13 Register the suite in `verify-boot.ps1` and update the header prose
      (hermetic count, live count, assertion count).
- [ ] 4.14 Amend `test_project_scope.gd`'s allow-list for the new client sources,
      the new suite and the new report.

## 5. Full verification

- [ ] 5.1 `godot --headless --path apps/client-godot --script
      res://tests/test_auction_schedule.gd` exits 0.
- [ ] 5.2 Same suite with `--report=<repo>/apps/client-godot/evidence/auction-schedule/report.json`
      is byte-identical across three consecutive runs.
- [ ] 5.3 `powershell -File apps/client-godot/verify.ps1` exits 0.
- [ ] 5.4 `powershell -File apps/client-godot/verify-boot.ps1` exits 0; inspect
      every log file for `[test] FAIL`, `^ERROR:` **and** `SCRIPT ERROR`.
- [ ] 5.5 `python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v`
      is **unchanged** — this line touches `apps/compat-api/**` not at all.
- [ ] 5.6 `python -B packages/game-content/tools/validate_content.py` exits 0.
- [ ] 5.7 `python -B tools/hash-manifest/hash_manifest.py verify` exits 0. Record
      the new entry count and explain the delta.
- [ ] 5.8 `openspec validate --all --strict` passes.
- [ ] 5.9 `git status` shows no legacy, save, config, fixture or village byte
      changed, and no `auctions/` directory created.
- [ ] 5.10 Confirm the content-package byte-form of every new file: the recorded
      digest describes the **committed Git blob form** (LF), and the raw
      working-tree form is recorded separately with its own digest — the defect
      class recorded twice in this project.

## 6. Deviations and corrections

### 6.0 Baseline note, recorded at proposal time

`openspec validate --all --strict` counted **69** items with no active changes and
**70** with this one. My expectation was **71**, from assuming `--all` counts one
item per delta spec. Measured: it counts an active **change** as one item
(`✓ change/auction-schedule-projection`) and validates both delta specs inside it.
So the expected figure for this change is **70**, and after Sync it becomes **71**
when the new main spec adds an item, returning to **70** at Archive when the
change item is removed.

### 6.1 To be completed during Apply

Record every deviation from the tasks above and every figure corrected during
implementation **here**, with its cause — never as a quiet edit. Note at minimum:

- Any probe that fails with no `[test] FAIL` line (parse-error detection proves
  nothing about a guard) and how the harness was fixed.
- Any measured figure that differs from a figure asserted in
  `docs/legacy-m11-event-systems.md` or in design D1–D10, and which was wrong.
- Any guard that turned out to be able to pass when it should fail, as
  `godot-friends` recorded for a bare two-character substring.