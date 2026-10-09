# M12: locating the origin of the converter's desync refusal family

**Status:** investigation complete, **no deliver line proposed**.
**Branch:** `docs/m12-desync-origin-investigation`
**Question:** the eight converter refusal classes were shown to contain one
272-target desync family (four classes). Where does the desync begin?

**Answer: partially located, and the family does not have a single origin.**
One real defect is located and sharply bounded — the solid fill colour width —
it makes **138 of 272** payloads parse exactly, and it converts **0 of 272**
targets. A proposal on that basis would be a line that changes no outcome, so
none is proposed. The blocker is recorded in §8.

---

## 1. What is being explained

From `docs/legacy-m12-refusal-classes.md` (PR #355): of 527 refused conversion
targets, four classes form one bit-position desync family.

| refusal class | targets |
|---|---|
| `unknown fill style` | 137 |
| `shape byte overrun` | 104 |
| `shape bit overrun` | 20 |
| `shape byte misaligned` | 11 |
| **total** | **272** |

272/272 were traced to their **first** refusal (not every overrunning shape,
which is correction C4 of that document and the error this probe design
avoids). The four classes partition the 272 exactly.

## 2. Preconditions verified before any grammar was blamed

Before searching the grammar, the two inputs the grammar operates on were
checked, because a grammar argument applied to wrong bytes explains nothing.

| check | result |
|---|---|
| payload slice correct (`UI16 ShapeID` == the walk's shape id) | **272 of 272** |
| tag is style-bearing (`DefineShape`/`2`/`3`/`4`) | **272 of 272** — 22×tag 2, 141×tag 22, 109×tag 32 |
| morph tags (`4`/`46`/`48`) present | **0** |
| payload too short to carry a shape id | **0** |

So the bytes are right, the tag is right, and the declared length is
authoritative. The defect is in what the parser reads.

## 3. The oracle was wrong, and correcting it changed the results

Every probe below is scored by **exact consumption**: the style arrays plus the
records, run from the target's committed entry bit, must land at the end of the
payload.

The first version of that oracle demanded `position == payload_len * 8`. That
is too strict. A shape payload ends with an `EndShapeRecord`, which is 6 zero
bits, and the encoder then pads the tag to a byte boundary. A correct parse may
therefore land anywhere in the last **7** bits provided the remainder is zero.
The strict oracle scored every one of those as a failure — and since a 6-bit
end record is followed by 2 to 7 padding bits in the typical case, it rejected
precisely the parses it should have accepted.

Re-running the witness search under the corrected oracle:

| | strict oracle | corrected oracle |
|---|---|---|
| `shape bit overrun` | 2 of 20 have a witness | **5** of 20 |
| `shape byte misaligned` | 0 of 11 | **5** of 11 |
| `shape byte overrun` | 32 of 104 | **35** of 104 |
| `unknown fill style` | 8 of 137 | **50** of 137 |
| **any witness offset** | **42** of 272 | **95** of 272 |

The correction is material (42 → 95) and it invalidated the four falsifications
made against the strict oracle, so all of them were re-tested rather than
reported. See correction **C1**.

Under the corrected oracle **177 of 272** payloads still have no witness at any
offset, and **0 of 272** have the committed offset as a witness.

## 4. Falsified candidate origins

Each was enumerated in full against the corrected oracle.

| # | candidate | best coverage | verdict |
|---|---|---|---|
| 1 | missing alignment between fills | 11 of 272 | falsified |
| 2 | the reader being at the wrong offset | — | falsified (177 of 272 have no witness at *any* offset) |
| 3 | the gradient fill layout (216 layouts) | ≤ 14 of 272 | falsified, and the winner was **underdetermined** |
| 4 | the edge-record grammar (16 grammars × 3 gradient layouts) | ≤ 6 of 272 | falsified |

Candidate 4 deserves a note, because it was the only defect found by reading the
code against the specification rather than by fitting data. `count_shape_records`
(`convert_building.py:381-393`) deviates from the specification in **four** ways
at once: `NumBits` read as `UB[4] + 2` rather than `UB[5]`, an extra 1 bit
before the straight-edge deltas that the specification does not have, the same
`UB[4] + 2` on the curved arm, and the curved arm's `FillSegmentHint UB[2]` +
`LineSegmentHint UB[2]` never read. Three of the four change the bit count
consumed, so they desynchronise every record after the first edge. Correcting
all four converts 6 of 272. The defect is real; it is not this family's origin.

## 5. The located defect: the solid fill colour width

`parse_fill_style` reads the solid branch's colour as `4 if rgba else 3`. The
`rgba` flag is true for tags 22 and 32, which are RGBA forms — but the committed
census measured the defect as a **gradient** problem, and a first reading of a
brute-force result appeared to confirm that. Both were wrong, in different ways.

Sweeping the solid and gradient colour widths **independently**, from the
committed entry bit:

| solid width | gradient width | targets resolved |
|---|---|---|
| **3 bytes** | tag-keyed | **138** |
| 3 bytes | 4 bytes | 136 |
| 3 bytes | 3 bytes | 131 |
| tag-keyed (committed) | tag-keyed | **9** |
| tag-keyed | 3 bytes | 9 |
| tag-keyed | 4 bytes | 9 |

The committed rule scores 9 and the corrected one scores 138 — a 15× gap, and
the only sharply constrained parameter in the whole layout. The nine that
resolve under the committed rule are the tag-2 shapes, where "tag-keyed" *is*
3 bytes.

So the defect is: **a solid fill colour in an RGBA-tagged shape is 3 bytes, not
4.** It is one expression, in one branch, of one function.

Per refusal class:

| class | resolved by the located layout |
|---|---|
| `unknown fill style` | 109 of 137 |
| `shape bit overrun` | 15 of 20 |
| `shape byte misaligned` | 4 of 11 |
| `shape byte overrun` | 10 of 104 |
| **total** | **138 of 272** |

`shape byte overrun` — the largest single class — is barely touched.

## 6. The located layout is underdetermined in four of its six parameters

A single winning combination is not an identified layout. Every axis, varied
alone with the others at the winner:

| axis | values → targets resolved | status |
|---|---|---|
| solid colour width | tag 9, **3 → 138**, 4 → 9 | **constrained** |
| gradient colour width | tag 138, 4 → 136, 3 → 131 | weak (7-wide spread) |
| matrix position | first 138, last → 128 | weak |
| header width | 8 → 135, **12 → 138**, 16 → 128 | weak |
| count nibble | low → 138, >>4 → 128, >>8 → 128 | weak |
| focal-point width | 0 → 138, 2 → 138, 10 → 138 | **free** |

Four of six parameters are weakly constrained and one is entirely free. This is
the same defect as in the earlier 216-layout run, which was recorded as
underdetermined for exactly this reason: the data does not pin the layout down.
The solid width is the one thing it does pin down.

## 7. End to end, the located layout converts nothing

Exact consumption is **necessary** for a correct parse and is nowhere near
**sufficient** for a converted package. This project has already paid for
believing otherwise: the gradient field-order correction in PR #355 is a real,
specification-supported defect and it converted 0 of 104 targets.

So the located layout was installed as a monkeypatch and the real
`build_package` was run against all 272, with two controls.

**Control 1 — return shape.** The patched parser was asserted to produce the
committed key set (`ratios`, not `count`, for the gradient stop count; no
`count`/`start_ratio`/`gradient`/`focus` keys). It matches on all three audited
fill types.

**Control 2 — calibration.** The unpatched harness was run against ten targets
the committed census records as `converted`. It reported **10 of 10** converted.
A harness that cannot report a success measures nothing; the previous run is
exactly what an uncalibrated harness looks like.

Result:

| | before | after |
|---|---|---|
| converted | 0 | **0** |
| refused | 272 | 272 |

Refusal classes after the change: `shape byte overrun` 104 → 52,
`unknown fill style` 137 → 7, `unresolvable bitmap fill` **0 → 8**,
`unsupported shape tag` **0 → 2**, `shape bit overrun` 20 → 4,
`shape byte misaligned` 11 → 4.

The change relocates refusals and converts nothing. The total is unchanged. Two
classes that were previously **masked** behind the earlier refusal now surface
on their own, which is itself informative: `unresolvable bitmap fill` and
`unsupported shape tag` were never absent, only hidden.

## 8. Conclusion, and why no line is proposed

1. The inputs are correct — payload slices, tags, declared lengths (§2).
2. The oracle was defective and its correction is recorded; four candidate
   origins were falsified against the corrected oracle (§3, §4).
3. One real, sharply-bounded defect is located: the solid fill colour width,
   worth 129 targets' difference in exact consumption (§5).
4. That layout is underdetermined in five of its six parameters (§6).
5. It converts **0 of 272** end to end, with a calibrated harness and an audited
   return shape (§7).

A line built on the located defect would therefore convert no target. §3.2 of
PR #355 established the pattern; this stage establishes that it is not the
exception.

**The blocker:** at least one further defect lies downstream of the parse, on the
content-reference and asset-resolution path. The 130 `unknown fill style`
targets that now parse land in refusals that are *not* parse failures. Locating
that path is the next investigation, and it needs new evidence rather than
another grammar enumeration — the grammar has now been searched exhaustively and
five candidate origins are falsified.

## 9. Also recorded, not the origin

`parse_line_style` (`convert_building.py:313-317`) reads only `Width UI16` and
`Color`. The specification's `LINESTYLE`, used by `DefineShape2` and
`DefineShape3`, carries a conditional tail: `MiterLimitFactor FIXED` and
`StrokeFlag UB[1]`, present when `Width` is below the 20-twip default limit. The
committed parser omits both, and under the located layout **12 of 12** sampled
line styles are below the limit, so the omission is exercisable.

Enabling it changes nothing: 131 targets resolved with the pair and 131 without.
It is a real deviation from the specification, recorded, and **not** this
family's origin.

## 10. A tension recorded, not resolved

The landed shape report for PR #355 states that **geometry never fails** — 0
fail in the geometry family. That is in tension with a fix in the style/record
grammar, because the 272 refuse *before* geometry is reached, so a grammar
defect would not directly explain a geometry-free corpus. The tension is
recorded rather than resolved by assumption: the two are reconcilable only if
the geometry path is simply never reached by these payloads, which is exactly
what "refuse first" implies and therefore not independent evidence.

## 11. Corrections

Every correction from this stage, including the ones to my own instruments. A
measurement whose instrument is defective is discarded, not reported.

**C1 — the oracle was too strict.** `position == payload_len * 8` ignored the
byte-alignment padding that follows the 6-bit `EndShapeRecord`. Effect: the
witness search reported 42 of 272 instead of 95. Four candidate origins had been
falsified against it; all four were re-tested under the corrected oracle and
their verdicts stand, but they could not have been reported from the strict
oracle. This is an instrument fault reading as a finding, the same class as the
`count_shift` error below.

**C2 — the gradient count was read from the wrong nibble.** `GRADRECORD`'s
header is 12 bits laid out `[11:10] Spread | [9:8] Interp | [7:4] StartRatio |
[3:0] NumGradients`, so the count is `header & 0x0F`. A nine-variant enumeration
used `(header >> 8) & 0x0F`, which is Spread+Interp, so its "spec order"
variants never actually tested the specification's count. Its 0-of-272 result is
a broken instrument and was **discarded**, not reported. The corrected
216-layout run is the one in §4.

**C3 — a hand-decode figure.** The bounds decoded by hand for
`10002_chained_junk_bot` were first written as `(0, 4434, 0, 4369)`, i.e.
221×218 px. The trace says `(0, 1152, 0, 1111)`, i.e. **57×55 px**. The
conclusion drawn from the hand-decode (a 122-line-style count against 7
remaining bytes, i.e. an overrun) is unchanged; the number was wrong.

**C4 — the first brute-force reading was mis-attributed.** A result of 131 was
read as "gradient records are 3 bytes". The probe that produced it shared one
colour-width override between the solid and the gradient branch, so it was
actually measuring the **solid** width. A follow-up that keyed the solid colour
off the tag scored 7 for the same parameter, which is what exposed the
mis-attribution. §5 re-measures the two widths independently.

**C5 — the first end-to-end run's headline class was the patch's own defect.**
It reported 0 of 272 converted and moved 173 targets into a new
`content ref not unique` refusal. That class was not a finding: the patched
parser returned the gradient stop count under the key `count` where the
committed code uses `ratios`, and added three keys the committed code never
produces, so downstream code saw a shape it does not expect. Fixed, then
guarded by a key-set audit and a calibrated success control (§7).

**C6 — a summary line double-counted.** The first miter probe's last line
reported 274 targets resolved "by a combination with the miter pair" in a run
that resolved 138 distinct targets, because it summed per-combination hits
instead of distinct stems.

**C7 — probe crashes are instrument faults, not results.** A format-string
`TypeError` in a free-parameter table, a walrus operator inside a subscript
(`SyntaxError` on CPython 3.9), and reading the census `targets` as a mapping
when it is a list of records with a `verdict` key. Each aborted its run before a
conclusion was drawn.

**C8 — the two "absurd fill style" figures disagreed for a reason, not a defect.**
An earlier probe reported 0 absurd gradient counts while PR #355 §2.5 recorded
64; one measured the gradient count and the other the *line* count. The
disagreement was an instrument definition difference, not a contradiction in the
corpus.

## 12. Claim limits

- The located layout is **derived-provisional**. It resolves 138 of 272 payloads
  exactly, but five of its six parameters are weakly constrained or free (§6),
  and no converted package demonstrates it.
- The solid-colour-width claim rests on **15× coverage difference** on the
  committed corpus, not on an observed encoder.
- Nothing here claims what the Flash authoring tool wrote. These are 272 payloads
  that the committed parser cannot consume; the correct reading of any of them is
  unobserved.
- **No proposal follows.** The blocker in §8 requires new evidence on the
  content-reference path, not another grammar enumeration.
- No committed source, save, config, content package, or conversion output was
  modified. All probes ran as monkeypatches in a separate process and wrote only
  to a disposable temp directory.

## 13. Reproduction

All probes are read-only with respect to the repository and were run with the
pinned CPython 3.9.13 on Windows x64.

| probe | what it establishes |
|---|---|
| identity census over the 272 | §2 |
| corrected-oracle witness search | §3 |
| inter-fill alignment measurement | §4 candidate 1 |
| corrected 216-layout gradient brute force | §4 candidate 3 |
| 16-grammar edge brute force | §4 candidate 4 |
| two-stage colour-width sweep | §5, §6 |
| calibrated end-to-end run | §7 |

Input: the 272-target committed read traces produced during the PR #355
investigation. The 272 and their first-refusal class partition were re-verified
as summing to exactly 272 before any probe was run.