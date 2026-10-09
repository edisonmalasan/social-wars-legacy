# Tasks

## 1. Correct the RECT decode

- [ ] 1.1 In `tools/asset-registry/convert_building.py::parse_rect_bits`, sign-extend each of the four
      coordinate fields independently: subtract `1 << nbits` from a field whose bit at `nbits - 1` is
      set, leave every other field untouched, and do **not** apply one shift to all four — verify by
      re-running the population probe and confirming `xmin` moves on 1987 shapes, `ymin` on 1597,
      `xmax` on 10 and `ymax` on 22, i.e. near and far edges move independently
- [ ] 1.2 Replace the `max(0, ...)` extent clamp with a validation failure when `xmax < xmin` or
      `ymax < ymin`, identifying the file and tag, and verify the refusal writes no package — verify by
      confirming the population inversion count is **0** across 290 targets / 4347 shapes, so the
      refusal rejects nothing that legitimately parses
- [ ] 1.3 Leave the unreachable `nbits > 31` guard at its current line untouched, and verify by reading
      the diff that no unrelated cleanup rode along

## 2. Make the crafted fixtures spec-conformant

- [ ] 2.1 In `rect_bytes` in `tools/asset-registry/tests/test_convert_building.py`, size `Nbits` as
      `max(bit_length) + 1` so every crafted value is representable as a signed field, and verify
      `rect_bytes(200, 100)` then declares `Nbits = 9` and `rect_bytes(2000, 2000)` declares `Nbits = 12`
- [ ] 2.2 Apply the same amendment to the `rect_bytes` that `tools/asset-registry/tests/test_convert_unit.py`
      imports, and verify it is the same function object rather than a second copy
- [ ] 2.3 Run `python -B -m unittest discover -s tools/asset-registry/tests -p test_convert_building.py -v`
      and verify **81 tests, OK**
- [ ] 2.4 Run `python -B -m unittest discover -s tools/asset-registry/tests -p test_convert_unit.py -v`
      and verify **OK**
- [ ] 2.5 Verify **no expected value in either suite was edited** — confirm by diff that the only test
      changes are inside `rect_bytes`, and that `width_px`/`height_px` assertions at
      `test_convert_building.py:240-241`, `test_convert_building.py:464-465` and
      `test_convert_unit.py:268-269` are untouched

## 3. Regenerate the one affected committed package

- [ ] 3.1 Run `python -B tools/asset-registry/convert_unit.py --target-stem 10033_wild_elephant
      --target-legacy-id 933` and verify it exits 0 and rewrites
      `assets/converted/units/10033_wild_elephant/package.json`
- [ ] 3.2 Verify the regenerated package differs from the committed bytes in **exactly** the 19 of 28
      shapes' `xmin`/`ymin` (`xmin` on 9, `ymin` on 17), with `xmax`, `ymax`, `width_px` and
      `height_px` unchanged on all 28 and every non-shape field unchanged
- [ ] 3.3 Verify `assets/converted/buildings/0001_house_1_m/package.json` is byte-identical, by running
      `python -B tools/asset-registry/convert_building.py --target-stem 0001_house_1_m` and confirming
      `git status` reports it unmodified
- [ ] 3.4 Verify re-running the unit conversion a second time is byte-stable, so the package's
      determinism requirement still holds
- [ ] 3.5 Inspect `git status` after 3.1 for the converter's other tracked outputs — `conversions.json`
      and `statuses.json` are both rewritten by every converter run and both pinned `text eol=lf` — and
      verify each is either byte-identical or changed only in the way the merge semantics require,
      recording which
- [ ] 3.6 Verify `assets/converted/units/10033_wild_elephant/package.json` is LF-terminated in the
      working tree, per the `assets/converted/**/package.json text eol=lf` pin

## 4. Integration checks

- [ ] 4.1 Run `python -B tools/hash-manifest/hash_manifest.py verify` and verify it exits 0 with 3258
      entries — `legacy-manifest.json` does not cover `assets/converted`, so this must be unchanged
- [ ] 4.2 Run `python -B packages/game-content/tools/validate_content.py` and verify `result: valid`
      with 22 schemas
- [ ] 4.3 Run `openspec validate --all --strict` and verify 0 failed
- [ ] 4.4 Verify `git status` shows no SWF, save, config, village, registry, coverage, inspection, or
      extraction-manifest byte changed
- [ ] 4.5 Re-measure the whole converted population under the shipped parser and record the result —
      290 targets parse, 4347 shapes, 0 inverted rectangles — and verify the shipped code reproduces the
      per-field table quoted in `proposal.md`

## 5. Record the landing

- [ ] 5.1 Append an "as landed" section to `docs/legacy-m12-signed-rect.md` naming the change, the
      branch and PR, the shipped per-field measurements, and the D2 interaction (13 targets, 32 size
      fields moving non-zero → 0), and verify the document still states that D2 is deferred
- [ ] 5.2 Verify `docs/legacy-m12-signed-rect.md` and both spec deltas are pure CRLF, matching every
      other document and spec in the repository