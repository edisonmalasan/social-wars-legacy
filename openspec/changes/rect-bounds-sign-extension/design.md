# Design

## Context

`parse_rect_bits` (`convert_building.py:257-267`) reads a `RECT` as a 5-bit `Nbits` followed by four
`Nbits`-wide fields:

```
257  def parse_rect_bits(reader, label):
258      nbits = reader.read_bits(5, label)
259      if nbits > 31:
260          raise ValidationFailure(["rect nbits out of range at " + label])
261      xmin = reader.read_bits(nbits, label)
262      xmax = reader.read_bits(nbits, label)
263      ymin = reader.read_bits(nbits, label)
264      ymax = reader.read_bits(nbits, label)
265      return {... "width_px": max(0, xmax // 20), "height_px": max(0, ymax // 20)}
```

`BitReader.read_bits` (`:229-238`) is correct, unsigned, MSB-first. The bug is not in the bit reader:
the `RECT` fields are **`SB` (signed)** in the format, and `read_bits` cannot express a sign.

## Decisions

### D1 — Sign-extend each field independently

For a field of `Nbits` bits with raw value `v`, the decoded value is `v - 2**Nbits` when the bit at
position `Nbits-1` is set, and `v` otherwise.

**Sign extension is not a uniform shift, and this is the trap.** It is *not* "subtract `2**Nbits` from
every field of the rectangle". It subtracts only from the fields whose own sign bit is set, which means
it **reorders** the four fields relative to the unsigned reading. In this corpus the affected fields
overwhelmingly turn out to be the *near* edges (`xmin` moves on 1987 shapes, `ymin` on 1597) while the
*far* edges move on 10 and 22 — so a "just flip the sign" reading gets the common case accidentally
right and the rare case wrong. This is recorded because an earlier stage of this investigation ruled
the fix out on exactly that unexamined reasoning, and the defect survived a full stage as a result.
The implementation must therefore extend **per field**, and the per-field table in the proposal is the
evidence that it does.

Rejected alternatives:

| Alternative | Why not |
| --- | --- |
| Keep unsigned, floor the extent at 0 (status quo) | The clamp is what conceals the inversion; it cannot detect it. |
| `abs()` each field | Invents geometry. It would silently "fix" inverted rectangles by mirroring them. |
| Reject any `RECT` whose sign bits are set | Refuses the 74 majority instead of decoding them correctly. |
| Fix `BitReader.read_bits` to return signed | `read_bits` is used for genuinely unsigned fields too; changing it would leak sign semantics into every caller. |

### D2 — Defer the origin-relative extent to a separate change

`width_px` is `xmax // 20` and `height_px` is `ymax // 20` — measured from the **origin**, not the far
edge. Under D1 alone the 32 size fields that move across 13 targets all move **non-zero → 0**, because
D1 corrects a far edge into negative territory while the size is still measured from zero.

This is *not* a new defect and not a regression: an origin-relative size of 0 is the correct value for a
shape that genuinely extends left of or above the origin. But it means D1 alone leaves those 13 targets
with sizes that are correct-but-uninformative, and the change that makes them informative is to derive
the size from the extent (`xmax - xmin`).

Measured against the **true** extent only, that change (call it D2) would move **3452 of 4347 shapes**
and **76 of 290 targets** — a far larger behavioural change than D1, resting on a different judgement
about what `width_px` is *for*. Keeping them apart means each can be reviewed, measured, and reverted
independently, and D1's effect is attributable on its own.

**D1 is not blocked on D2.** Nothing in this change makes the deferred sizes worse than the corruption
they replace.

### D3 — Fail closed on an inverted RECT rather than clamping

Replace `max(0, xmax // 20)` with a validation failure when `xmax < xmin` or `ymax < ymin`, keeping the
extents unclamped so the failure is attributable.

This is free, and that was measured rather than assumed: after D1 the population contains **0** inverted
rectangles across all **290** targets and **4347** shapes, so the refusal costs nothing today. It is
insurance — it converts a future malformed file from "silently reported as a zero-extent shape" into
"refused with the file and tag named", which is the behaviour every neighbouring rule in these two
capabilities already follows.

The `nbits > 31` guard at `:260` is unreachable (a 5-bit field cannot exceed 31). It is left in place:
removing it is unrelated cleanup and the change scope forbids it.

### D4 — Fix the fixture encoder, not the expectations

`rect_bytes` in both converter test modules sizes `Nbits` from the **unsigned** bit length:

```
nbits = max(xmax_twips.bit_length(), ymax_twips.bit_length(), 1)
```

Two of the three crafted RECTs then declare a field too narrow for their own values as signed —
`rect_bytes(200, 100)` declares `Nbits = 8` and carries 200 against a sign bit of 128;
`rect_bytes(2000, 2000)` declares `Nbits = 11` and carries 2000 against a sign bit of 1024. These
fixtures were not neutral: they depended on the unsigned reading to be parseable.

The amendment widens `Nbits` by one bit so every crafted value is representable as a signed field,
which makes sign extension a no-op on all of them. Chosen over relaxing the parser or adjusting
expected values because variant B measured **81 tests, 0 failures, 0 errors** with **not one
expectation value changed** — the fixtures were wrong, not the assertions.

### D5 — Regenerate exactly one committed package

Only `assets/converted/units/10033_wild_elephant/package.json` changes bytes. It is regenerated with
the declared target stem and legacy id (`10033_wild_elephant`, `933`) so the package's provenance is
its own. `assets/converted/buildings/0001_house_1_m/package.json` was converted under both parsers and
is byte-identical, so it is **not** touched.

## Method

Every figure quoted in the proposal and this design was measured on this repository at pinned CPython
3.9.13, and each measurement was taken with an instrument whose correctness was itself checked:

- **Population measurements** route every target through `census_targets.CONVERTER_BY_DOMAIN` rather
  than through one converter. An earlier instrument routed all 272 candidates through
  `convert_building.build_package`, which raises `content ref not unique` on a unit target *before*
  parsing — so it silently measured 77 buildings and mislabelled the rest.
- **A refusal class present identically in a patched and an unpatched run** is treated as proof the
  patch did not cause it. That single check is what exposes a routing fault immediately.
- **The `max(0, ...)` clamp makes `width_px` incapable of showing the defect**, so inversion is counted
  on the raw `xmin`/`xmax`/`ymin`/`ymax`, and "inverted" and "size changed" are reported as two
  separate counts rather than one.
- **Test impact is an A/B, not an argument.** Variant A (parser changed, fixtures untouched) is what
  establishes that the fixture amendment is required; variant B establishes that it is sufficient. All
  three variants run in **separate processes**, because loading the two test modules into one process
  leaks state between runs and produces a test count that varies with variant order.

Measurements whose *instrument* was found defective were discarded rather than reported: an end-to-end
run that mis-routed domains, a plausibility probe that read shapes from the manifest instead of the
package and re-committed the same routing error, and a D2 probe that was vacuous twice over.

## Claim limits

- The rule is **spec conformance**, established from the format's `SB` field type, not from observed
  Flash client behaviour. No Flash, Ruffle, ActionScript, or browser executes in this change.
- **No mass conversion.** The 290 packages are not regenerated; the population figures are measurements,
  not delivered output. Mass conversion remains a separate, unauthorised decision.
- **D2 is not implemented.** `width_px`/`height_px` keep their origin-relative definition, and the 13
  targets whose sizes would move are not delivered.
- **The 13 targets and 32 size fields are a measurement over unconverted packages.** They are recorded
  so a future mass conversion knows the interaction in advance; nothing here commits them.
- **`width_px`/`height_px` remain provisional labels for a provisional quantity.** This change corrects
  the decode; it does not decide what the number is for.
- No pixel parity is claimed and no windowed capture is taken, because nothing is rendered.
- `legacy-manifest.json` does not cover `assets/converted`, so the preservation manifest is unaffected
  and no SWF, save, config, village, or legacy source byte changes.