# M12 line 3 investigation: what the eight converter refusal classes actually are

Investigation only. **This document implements nothing** — no conversion, no
extraction, no client, tool, or spec change. It records a decision, and the
measurements the decision rests on.

Its predecessor, `docs/legacy-m12-fx-animation-rescope.md` (PR #353, merge
`5061bb5`), closed one of M12's three open decisions and left this one open. It
recommended, without authorising, a line against the largest refusal class:

> Lifting `shape byte overrun` (104 targets, 89 labelled) alone would take
> convertible animation sprites from **68 to 157**, more than doubling them.

It also stated the limit on its own recommendation:

> Whether `shape byte overrun` can be lifted without inventing a parsing rule is
> a separate question this document does not answer.

**That question is what this document answers, and the answer is no** — for that
class, by that route. The recommendation is recorded as **withdrawn** in §9.1, on
the measurement corrected in §7 as C6.

---

## 0. Scope and method

### 0.1 The question

M12 has **527 refused** conversion targets across **8 refusal classes**, and
those refusals stand on the critical path for two of M12's four deliver items.
The open decision is whether the refusal **class-domains** get investigation
lines of their own or are recorded as permanently refused.

This investigation answers it by classifying each class by **mechanism**, on the
measured question of *why the converter stopped* rather than *what the message
says*. The distinction is load-bearing: two of the eight classes turned out to
be documented scope decisions rather than parser limits, which is a different
kind of thing from a bound the parser hit.

### 0.2 Sources

All figures come from committed artifacts and from the committed converters
themselves. Nothing is transcribed, and no stem, id, or count is written into
any tool by this document.

| source | role |
|---|---|
| `tools/asset-registry/target_census.json` | the 817 candidates, 290 converted, 527 refused, 8 classes |
| `tools/asset-registry/inspection.json` | 1,176 per-file SWF records: `frame_labels`, `frame_count`, `bitmap_ids` |
| `tools/asset-registry/statuses.json` | per-file extraction status |
| `tools/asset-registry/asset_ids.json` | 1,627 content asset references |
| `tools/asset-registry/convert_building.py` | the shared shape parser and the building converter |
| `tools/asset-registry/convert_unit.py` | the unit converter and its timeline walk |

Every source-line citation in this document was read back against the committed
file before commit — `convert_building.py:285-310` (`parse_fill_style`),
`convert_building.py` `TAG_DEFUSED_SHAPE`, `convert_unit.py:71-77`
(`TIMELINE_REFUSED_TAGS`) and `census_targets.py:113-143` (`candidates`) are all
exact. One of those checks strengthened a finding; see §7 as C9.

### 0.3 Method: three requirements on every measurement

1. **The refusal class names the *first* failure.** Both converters raise on
   the first problem, so a refusal class is a property of where the parse first
   stopped, not of everything wrong with the file. Any measurement that
   aggregates over all failures in a file describes a different thing and will
   disagree with the census. Two of my own probes did exactly this before being
   corrected (§7, C3, C4).
2. **Reproduce through the committed converter**, not a re-implementation. A
   hand-written parser that reads the tag stream from offset 0 rather than past
   the frame header reports nonsense tag codes; two of my probes did this
   before being corrected (§7, C1, C2).
3. **Two independent measures for any figure that carries a decision.**

Containment: measurement scripts live outside the repository in
`%LOCALAPPDATA%\Temp\opencode`. No converter wrote into the working tree; the
end-to-end runs used a disposable `tempfile.mkdtemp()` out-root, removed in a
`finally`. No network, no Flash, Ruffle, ActionScript, or browser.

---

## 1. The eight classes, sized

Reproduced from `target_census.json`, with each class's domain split measured
rather than assumed:

| # | refusal class | targets | building | unit | labelled |
|---|---|---|---|---|---|
| 1 | `unknown fill style at swf <target>: #` | 137 | 61 | 76 | 76 |
| 2 | `unresolvable bitmap fill at shape # -> #` | 133 | 133 | 0 | 9 |
| 3 | `shape byte overrun at swf <target>` | 104 | 14 | 90 | 89 |
| 4 | `unsupported shape tag at swf <target>: #` | 64 | 20 | 44 | 53 |
| 5 | `unsupported timeline tag at swf <target> sprite #: code # (PlaceObject#)` | 57 | 0 | 57 | 56 |
| 6 | `shape bit overrun at swf <target>` | 20 | 2 | 18 | 18 |
| 7 | `shape byte misaligned at swf <target>` | 11 | 0 | 11 | 11 |
| 8 | `unsupported tag in timeline at swf <target>: code #` | 1 | 0 | 1 | 1 |
| | **sum** | **527** | **230** | **297** | **313** |

The sum reproduces the recorded **527** exactly, and `refused_targets_in_several_classes`
is **0**, so each refused target carries exactly one class. The domain column
reproduces the census's own `by_domain` totals (building 230 refused, unit 297
refused) — a second, independent confirmation of the partition.

**Two classes are single-valued.** This is the first structural fact, and it
reframes the whole question:

- Class 4 is **code 83 = DefineShape4** on **all 64** targets.
- Class 5 is **code 70 = PlaceObject3** on **all 57** targets.

Neither is "an unknown tag". Both are named, defined SWF tags (§4).

---

## 2. `shape byte overrun` is a bit-position desync, not a truncation

This is the class the predecessor recommended lifting, so it was measured
hardest, and from four directions.

### 2.1 Where the refusal actually fires

Tracing every refusal through the committed `parse_shape_with_style` with a
recording `BitReader` and `sys.settrace` (committed source unmodified):

| phase at failure | targets |
|---|---|
| `parse_style_arrays` → `parse_line_style` | 94 |
| `parse_style_arrays` → `parse_fill_style` | 5 |
| `count_shape_records` → `parse_style_arrays` → `parse_line_style` | 4 |
| `count_shape_records` → `parse_style_arrays` → `parse_fill_style` | 1 |

**All 104 fail inside the style arrays. None fail in geometry.** For a class
whose name suggests running off the end of the data, that is the first surprise.

### 2.2 The overflow is tiny and the payload is fully consumed

| unconsumed payload bytes at failure | targets |
|---|---|
| 0 | 46 |
| 1 | 32 |
| 2 | 7 |
| 3 | 19 |

| bytes requested past the end | targets |
|---|---|
| 1 | 47 |
| 2 | 35 |
| 3 | 9 |
| 4 | 13 |

So **every one of the 104 asks for between 1 and 4 bytes more than the payload
holds**, from a **byte-aligned** position (104 of 104 aligned). The reader is
not lost; it is a few bits out of step and reads one or two fields too far.

### 2.3 The files are structurally sound

An independent framing walk — one that reports the first structural defect
instead of raising — over all 104:

| | |
|---|---|
| top-level tag stream reaches an End tag | **104 of 104** |
| structural framing defects | **0** |
| signature | **104 `CWS`** (zlib-compressed) |
| sprite nesting depth at the failing shape | 1 (104 of 104 nested in a sprite, 0 top level) |

Nothing is truncated and nothing overruns its container. **The refusal is about
shape *content*, not about damaged files.**

### 2.4 The declared counts are not real counts

Measured at the **first failing shape of each target** — the only shape the
census records (§0.3 rule 1):

| | |
|---|---|
| targets with a located failing shape | 104 |
| …of which a `line_count` could be read at all | **99** (5 fail earlier) |
| declared `line_count` above 64 | **64** of 99 |
| declared `line_count` **65535** (the extended-count sentinel `0xFFFF`) | **6** |
| declared `line_count` **36716** | **1** |
| declared `line_count` ≤ the line slots the payload holds | **5 of 99** |

The leading absurd values, with the slots actually available:

| declared `line_count` | slots that fit | targets |
|---|---|---|
| 65535 | 7 | 5 |
| 65535 | 9 | 1 |
| 36716 | 6 | 1 |
| 251 | 4 | 1 |
| 232 | 15 | 1 |
| 230 | 7 | 2 |
| 224 | 6 | 2 |
| 212 | 11 | 1 |
| 208 | 10 | 1 |
| 192 | 7 | 1 |
| 191 | 14 | 1 |
| 185 | 2 | 1 |
| 174 | 10 | 1 |

A declared count of **65535** is the extended-count sentinel, and **36716** is
not a plausible style array in any asset. Only **5 of 99** declared counts fit
the bytes available.

These are the signature of a reader at the wrong bit offset, not of assets with
absurd numbers of line styles.

### 2.5 The failing shapes are almost all gradient-filled

Over the 99 shapes whose counts could be read, the fill types **declared on the
failing shape itself** are:

| fill type | occurrences | shapes declaring at least one |
|---|---|---|
| gradient (`0x10`, `0x12`, `0x13`) | **91** | **91** |
| solid (`0x00`) | 10 | 10 |

Occurrences sum to 101 rather than 99 because two shapes declare two fills each:
`10003_chained_dual_blade_automech` declares `[0x00, 0x10]` and `1353_bismark`
declares `[0x00, 0x12]`. Every other failing shape declares exactly one fill, so
the occurrence count and the shape count coincide except on those two.

**91 of the 99 failing shapes carry a gradient fill**, and the gradient FILLSTYLE
is exactly the structure §3.1 finds to be mis-parsed. That is the strongest link
in this document between the refusal and the defect. §3.2 then measures what
fixing it actually buys, and the answer is less than the link suggests.

---

## 3. The root cause is reproducible, and the obvious fix does not work

### 3.1 A real defect, found by reading the specification against the code

`parse_fill_style` (`convert_building.py:285-310`) reads a gradient FILLSTYLE as:

```
FillStyle byte  ->  header (8 bits)  ->  gradient records  ->  MATRIX
```

and takes the fields out of that single byte:

```python
gradient_flags = reader.read_bits(8, label)
count         = gradient_flags & 0x0F          # NumGradients
spread        = (gradient_flags >> 6) & 0x03   # SpreadMode
interpolation = (gradient_flags >> 4) & 0x03   # InterpolationMode
```

The SWF specification defines the structure in a **different order and a
different width**:

```
FillStyle byte  ->  MATRIX  ->  header (12 bits)  ->  gradient records

header = SpreadMode UB[2], InterpolationMode UB[2], StartRatio UB[4], NumGradients UB[4]
```

So the committed parse both reads the header from the wrong place and from the
wrong width. It takes `NumGradients` from the low nibble of `StartRatio`, and —
because a MATRIX is a bit-aligned structure — reading it *last* instead of
*first* desynchronises every subsequent bit position. That is precisely the
mechanism §2.4 measures.

**This is a genuine defect in the committed converter.** It is recorded here
because it is real, not because fixing it is in scope for a docs-only stage.

### 3.2 Fixing it lifts nothing

The corrected parse was installed in memory (committed source untouched) and
the **real** converters were run end to end over all 104 targets, into a
disposable out-root:

| verdict | targets |
|---|---|
| newly converted | **0** |
| → `shape byte misaligned` | 66 |
| → still `shape byte overrun` | 28 |
| → `unknown fill style` | 7 |
| → `unsupported timeline tag` | 2 |
| → `shape bit overrun` | 1 |

**The correction converts zero of the 104.** It relocates the failure for 66 of
them, which confirms the desync diagnosis — the parse genuinely changes where it
fails — but it does not carry any target to a converted package. The remaining
desync is somewhere this hypothesis does not reach.

**The counts move, but not monotonically toward correctness.** On the 37 shapes
whose declared count is readable under *both* parses — the same shape and the
same population as §2.4, not the aggregate of §7 C4:

| | before | after |
|---|---|---|
| declared `line_count` > 64 | 64 | **19** |
| declared `line_count` ≤ slots that fit | 5 | **15** |
| declared `line_count` = 65535 | 6 | **12** |
| declared `line_count` = 36716 | 1 | **0** |

Read naively this looks like progress, and on two of the four rows it is. But
the **sentinel count rises from 6 to 12**, and the largest per-target shifts show
targets moving *into* the sentinel rather than out of it:

| target | before | after |
|---|---|---|
| `10057_chained_transformer_aracnid` | 65535 | **0** |
| `987_chained_ufo` | 30 | **65535** |
| `1177_ufo` | 30 | **65535** |
| `1266_spatial_paladin` | 42 | **65535** |
| `10002_chained_junk_bot` | 122 | **65535** |
| `0157_jet_robosoldier_academy_m` | 232 | **65535** |

Five targets leave the sentinel and seven enter it. **`0xFFFF` is no more a
plausible style count than 36716 is**, so a correction that produces more of them
has not found the correct parse — it has moved the fault.

**Prediction stated before the run:** the declared `line_count` becomes plausible
*and* the overrun disappears. **The second half was falsified and the first half
was overstated** — counts do become more plausible on average, but only by
relocating the fault, and nothing converts. Recorded in §7 as C6.

---

## 4. Two classes are documented scope decisions, not parser limits

### 4.1 `unsupported shape tag` is entirely DefineShape4

| tag code | occurrences | name |
|---|---|---|
| 83 | **64 of 64** | DefineShape4 |

DefineShape4 is a defined SWF tag — a shape variant with separate fill and
shape bounds. The converter refuses it from a named constant, and that constant
has **exactly one member**:

```python
TAG_DEFINE_SHAPE = (2, 22, 32)          # DefineShape, DefineShape2, DefineShape3
TAG_REFUSED_SHAPE = (83,)               # DefineShape4
```

So DefineShape4 is **the only shape tag in the corpus the converter declines**,
and it is declined by an explicit one-line list rather than by falling through a
parse it could not handle. **This is a recorded scope boundary**, not a parse
failure, and the difference matters: a scope boundary is lifted by deciding to
support the tag, whereas a parse failure is lifted by fixing a reader.

### 4.2 `unsupported timeline tag` is entirely PlaceObject3

| tag code | from the census's recorded messages | reproduced by re-running the walk | name |
|---|---|---|---|
| 70 | 57 | 57 | PlaceObject3 |

**Two independent measures agree exactly.** The refusal comes from a named
table in `convert_unit.py:71-77`:

```python
TIMELINE_REFUSED_TAGS = {
    4: "PlaceObject", 5: "RemoveObject", 12: "DoAction",
    59: "DoInitAction", 70: "PlaceObject3",
}
```

PlaceObject3 is refused **by explicit decision**, alongside four other placement
and action tags. Its labelled share is **56 of 57** — the second-largest
animation lever in the whole census.

**And the reason it is refused is not recoverable from this oracle.** Placing an
object with a name, depth, or colour matrix is exactly the information a
converter would need to interpret correctly, and the converter's own choice to
refuse it is a scope statement about what it claims to model. Lifting it would
mean deciding what PlaceObject3 means here — which is a converter-design
decision, not a measurement.

### 4.3 `unresolvable bitmap fill`: a real sentinel, but not a clean case

The referenced character ids were read directly from the bitmap FILLSTYLEs:

| | |
|---|---|
| distinct referenced ids | 194 |
| occurrences of **65535** (`0xFFFF`, the SWF null-character sentinel) | **1138** |
| targets whose bitmap fills are **all** `0xFFFF` | **0** |
| targets with **some** `0xFFFF` and some real id | **127** |
| targets with **no** `0xFFFF` | **5** |

`0xFFFF` is genuinely the "no character" sentinel and it genuinely occurs. But
**no target is a clean null case** — in 127 of 133 it appears *alongside* real
ids (1, 7, 10, 3, 9 …). So there is no rule of the form "ignore null bitmap
fills" that these assets support; each target would need its own reading, and
that is not a general rule. This class is **133 of 133 buildings**, which is
itself a strong domain signal.

---

## 5. `unknown fill style` is the same desync signature

| | |
|---|---|
| targets in the class | 137 |
| distinct `fill_type` values observed | **76** |
| total occurrences | 137 (one per target — the refusal is first-failure) |
| occurrences that **are** a defined fill type | **0** |
| targets carrying only undefined values | **137 of 137** |

The values are effectively random — **237, 155, 223, 117, 216, 100, 122, 255,
213…** — and **not one of the 137 is a defined fill type at all**. The defined
set is **0** (solid), **16**/**18**/**19** (gradients) and **0x40–0x43**
(bitmaps).

A file with 76 different "unknown fill styles" does not have 76 strange fills.
It has one reader at the wrong bit offset, sampled at different places. This is
the same mechanism as §2, in a different class, which is why **class 1 (137
targets, 76 labelled) and class 3 (104 targets, 89 labelled) are one problem
wearing two names.**

---

## 6. Re-measuring the animation lever, and one scope correction

### 6.1 The population reproduces exactly

Every partition in the predecessor's `docs/legacy-m12-fx-animation-rescope.md`
§3.3 and §3.6 re-derives (those are that document's sections, not this one's):

| | |
|---|---|
| census candidates | 817 |
| converted / refused | 290 / 527 |
| labelled sprite files under `assets/sprites/` | **422** |
| …of which census candidates | **381** (68 converted + 313 refused) |
| …of which not candidates | **41** |
| unlabelled candidates | 436 |

`381 + 436 = 817` and `381 = 68 + 313`. The **422** and the **68 / 313 / 41**
split both reproduce.

### 6.2 The non-candidate side is a content-side gap, reproduced

The 41 labelled non-candidates decompose by the census's own two-clause rule
(`census_targets.py:113-143`):

| cause | files |
|---|---|
| clause (a) fails: status is not `extracted` | 4 |
| clause (b) fails: zero content rows claim it | 9 |
| clause (b) fails: 2+ content rows claim it | 28 |
| **sum** | **41** |

The 28 multi-row cases are genuine content ambiguity and remain a content
decision this oracle cannot make.

### 6.3 Correction: the label vocabulary is 61, not 10 — and both are right

A re-measurement over `inspection.json` without a path filter counted **494**
labelled files, against the recorded **422**. Resolved: the 72 extras are
`assets/flash/Basesec_*.swf` **UI builds**, not sprites. **422 is correct**, and
my first probe lacked a path filter (§7, C5).

The same re-measurement then disagreed on the label vocabulary — **61** distinct
labels across `assets/sprites/` against the recorded **10**. Measuring every
plausible scope resolves it as a scope difference, not a contradiction:

| scope | files | distinct labels |
|---|---|---|
| all labelled `assets/sprites/` files | 422 | **61** |
| labelled census candidates | 381 | 60 |
| **labelled CONVERTED candidates** | **68** | **10** |
| labelled REFUSED candidates | 313 | 57 |
| all census candidates | 817 | 60 |

**"10" is the labelled-converted scope** — the five core labels (`QUIETO`,
`ANDAR`, `ATAQUE`, `MUERTE` on all 68, `PICAR` on 63) plus five singletons. The
sprite-scope figure is **61**, and the vocabulary is heavily concentrated:

| label | sprite files |
|---|---|
| QUIETO, ANDAR, ATAQUE, MUERTE | 417 each |
| PICAR | 311 |
| sp1, sp2 | 66 each |
| sp3 | 59 |

The five leading labels account for **1,979 of 2,405** label occurrences across
the 422 files, and appear on **417 of 422** files between them. **Both figures
are correct and both are now named**, which the predecessor's single "10" did not
make possible. Recorded in §7 as C7 — a clarification, not a contradiction.

### 6.4 The lever, by class

| class | labelled | labelled convertible if lifted alone |
|---|---|---|
| `unknown fill style` | 76 | 68 → 144 |
| `unresolvable bitmap fill` | 9 | 68 → 77 |
| **`shape byte overrun`** | **89** | **68 → 157** |
| `unsupported shape tag` (DefineShape4) | 53 | 68 → 121 |
| `unsupported timeline tag` (PlaceObject3) | 56 | 68 → 124 |
| `shape bit overrun` | 18 | 68 → 86 |
| `shape byte misaligned` | 11 | 68 → 79 |
| `unsupported tag in timeline` | 1 | 68 → 69 |
| **every class** | **313** | **68 → 381** |

The arithmetic is additive only because `refused_targets_in_several_classes` is
**0**; in general lifting two classes need not yield the sum.

---

## 7. Corrections

Eight defects, all in this investigation's own instruments or draft figures, and
all recorded rather than quietly fixed. C1–C8 fall into three classes worth
distinguishing: **mis-scoped probes** that produced numbers about the wrong
population (C1, C3, C4, C5, C8), **a broken tool call** (C2), and **an asserted
conclusion that measurement falsified** (C6, and the overstatement of C7). C6 is
the one that changed the decision. **C9 is a different class again** — defects
found by reading the finished draft, which no probe could catch because none of
them is a number.

**C1 — walked the tag stream from offset 0.** A probe called
`walk_shape_tags(body, ...)` on the whole decompressed body. The committed
converters pass `body[consumed + 4:]` — past the frame RECT, the frame rate and
the frame count. Walking from offset 0 read header bytes as tag headers and
reported nonsense codes (`code 1023`, `code 771`). It located **2 of 104**
failures and would have read as "the failure is not reproducible".

**C2 — reused `read_bytes_file` with the wrong argument shape.** That helper
builds its own path from its first argument; passing the label made it attempt
to read the repository root as a file, raising `PermissionError`. Instrument
error, not a finding.

**C3 — keyed measurements to the first shape, not the failing shape.** One probe
reported the declared `line_count` of the *first* shape tag in each file while
another reported the shape that actually overran. They disagreed — **0** versus
**122** line styles on `10002_chained_junk_bot`. Both were right about their own
shape; the probe asked about the wrong one. Corrected by keying both passes to
the same failing shape. This is the direct consequence of §0.3 rule 1.

**C4 — counted every overrunning shape instead of the first.** A per-shape scan
identified **1154** "failing shapes" across 104 targets, because it recorded
every shape that overran rather than the first. The census records one verdict
per target because the converter raises on the first. Every denominator built on
that count was wrong. Corrected to first-failure semantics.

**C5 — counted labelled files without a path filter.** **494** against the
recorded **422**. The 72 extra files are `assets/flash/Basesec_*.swf` UI builds.
The recorded 422 is correct; the probe was under-specified.

**C6 — the stated prediction about the gradient fix was wrong in both halves,
and its supporting figure was wrong too.** Before running it, the probe
predicted that reading the gradient header as its specified 12 bits would make
the declared counts plausible *and* stop the overrun.

Measurement: **0 of 104 converted.** The desync diagnosis is supported — the
failure site moves for 66 — but the fix carries no target to a converted
package, so the recommended route does not work. **The predecessor's
recommendation is withdrawn on this basis** (§9).

Two defects are recorded together here because they are the same mistake. The
original figure ("absurd counts fall 735 → 22") came from the mis-keyed probe of
C4 and had to be **discarded and re-measured**, not adjusted. Re-measured at
first-failure scope (§3.2), absurd counts do fall 64 → 19 — but the `0xFFFF`
sentinel count **rises 6 → 12**, with seven targets entering the sentinel against
five leaving it. So the correction *relocates* the desync rather than removing
it, which the original figure had hidden by reporting only the row that
improved. **A favourable aggregate from the wrong population would have
supported the recommendation this document withdraws.**

**C7 — a figure I had to correct in the other direction.** The label vocabulary
was first read as contradicting the predecessor's "10". It does not: 10 is the
labelled-**converted** scope and 61 is the sprite scope. Recorded because the
predecessor's single unqualified "10" invited exactly this error, and the fix is
to name the scope rather than to pick a number.

**C8 — a derived figure presented as a measured one.** An earlier draft of §6.3
stated that the five leading labels "cover 2,000 of the 2,228 label
occurrences". The **2,228** was the *top-ten* sum printed by the probe, used
against a claim about five labels, and the "2,000" was my own estimate rather
than any probe's output. Measured properly, the top-five sum is **1,979 of
2,405** total occurrences. Corrected in §6.3. This is the same defect class as
C4 — an aggregate from the wrong population, stated without being measured.

**No correction changes the decision.** C1–C5 and C8 changed or restored
figures; C6 withdrew the recommendation; C7 named a scope.

**C9 — five defects found by reading the finished draft, not by measurement.**
C1–C8 were all found by measurement. A final read-through of the assembled
document found five more, none of which any probe could have caught because none
of them is a number:

| defect | found | corrected |
|---|---|---|
| the withdrawal was cited to **§7** (where C6 records it) rather than to the decision in **§9.1** | read | §0 header now cites §9.1 and §7 together |
| "the *commit*'s own choice" — a placeholder that survived into the prose | read | §4.2 |
| §5 said a file has "**80** different unknown fill styles" when the measured distinct count is **76** | read | §5 |
| §4.1 called `TAG_REFUSED_SHAPE` "a named set" | read | §4.1 now quotes the constant, and records that it has exactly one member — which is a **stronger** finding than the draft made |
| §10 attributed §6.1's source figures to the predecessor's §6.2 rather than its §3.3/§3.6 | read | §10 |

The `TAG_REFUSED_SHAPE` case is the reason this pass is worth recording: the
draft's phrasing understated the evidence, and checking it produced a *stronger*
claim — DefineShape4 is the only shape tag the converter declines at all — from
a line of committed source that was sitting in a cited file the whole time.
**Verification of a citation is not a formality; here it changed a finding.**

---

## 8. Claim limits

- **This investigation implements nothing.** No conversion, extraction, client,
  tool, or spec change. Every figure comes from committed artifacts or from the
  committed converters.
- **The gradient-order defect in §3.1 is reported, not fixed.** It is real and
  it converts nothing on its own (§3.2). Whether it should be fixed, and what
  "fixed" means when the remaining desync is unexplained, is a separate
  decision.
- **A refusal class names the first failure only.** Nothing here claims a target
  has exactly one defect, and the per-file aggregates in §3.2 describe where the
  parse stopped, not everything wrong with the file.
- **"Structurally sound" means framing sound** (§2.3): tag lengths stay inside
  their containers and the streams reach End. It says nothing about whether the
  shape *content* is well-formed, which §2.4 shows it is not.
- **`0xFFFF` is identified as the SWF null-character sentinel** and its
  occurrence is measured. No rule for handling it is proposed, and §4.3 shows
  why: no target is a clean null case.
- **PlaceObject3 and DefineShape4 are reported as scope decisions.** That they
  are *refused* is established; that supporting them is *correct* is not, and
  PlaceObject3's semantics cannot be recovered from this oracle.
- **The lever table in §6.4 is arithmetic, not a plan.** Lifting a class is not
  the same as supporting its tag, and the classes overlap in cause even though
  they do not overlap in membership.
- **Labels are reported verbatim and are not translated.** No label is claimed
  to name a game state, because nothing in the oracle selects a state.
- **No pixel parity and no windowed capture**, because nothing is rendered.
- **No Flash, Ruffle, ActionScript, or browser executes**, and no network is
  used.

---

## 9. The decision

### 9.1 `shape byte overrun` is **not** liftable by the recommended route

The predecessor recommended lifting this class as the highest-value single move
(89 labelled sprites, 68 → 157). This investigation **withdraws that
recommendation**:

- The refusal is a **bit-position desync**, not a truncation (§2), and the
  files are structurally intact (§2.3).
- A **real defect** in the gradient FILLSTYLE parse was found and is reported
  (§3.1).
- Fixing it **converts 0 of 104** and merely relocates 66 failures (§3.2).

So the lever is real in *size* but the named route does not deliver it, and the
remaining desync is not yet located. **Proposing a line against this class now
would be guessing at a parsing rule** — the exact failure this project has
declined repeatedly.

### 9.2 The classes are not eight, and that changes the line boundaries

| kind | classes | what a line would be |
|---|---|---|
| **One shared cause** | `unknown fill style` (137) + `shape byte overrun` (104) + `shape bit overrun` (20) + `shape byte misaligned` (11) = **272 targets, 194 labelled** | one parser line: locate the remaining desync |
| **A documented scope decision** | `unsupported shape tag` / DefineShape4 (64, 53 labelled) | a support decision, not a bug fix |
| **A documented scope decision** | `unsupported timeline tag` / PlaceObject3 (57, 56 labelled) | a converter-design decision |
| **Content-side, per-target** | `unresolvable bitmap fill` (133, 9 labelled) | no general rule exists (§4.3) |
| **Not worth a line** | `unsupported tag in timeline` (1 target, 1 labelled) | — |

**The largest group is not one class but a family with one shared cause.** That
is the finding that reorders the work: a line aimed at "`shape byte overrun`"
would have addressed 104 of a 272-target problem and left 168 behind, while a
line aimed at the family would address all four at once.

### 9.3 Recommendation

**One line, aimed at the desync family, and only after its cause is located.**
The evidence for the family is strong and measured (§2, §5); the evidence for
*where the remaining desync is* is not yet in hand, and §3.2 is a concrete
demonstration of how a plausible-looking fix converts nothing.

The three scope-decision classes are **recorded, not queued**. DefineShape4 and
PlaceObject3 are refused by named tables on purpose; lifting them is a decision
about what the converter claims to model, and for PlaceObject3 the oracle cannot
recover the semantics. `unresolvable bitmap fill` has no general rule to
implement — 127 of 133 targets mix the sentinel with real ids.

This is a **recommendation, not an authorisation.** It is recorded in the
roadmap's open decisions, and M12's two remaining open decisions — per-class
investigations, and mass-converting the 290 available packages — both stay open.

---

## 10. Where to read next

- `docs/legacy-m12-fx-animation-rescope.md` — the predecessor decision this
  investigation revises in part. Its §3.3 and §3.6 are the source of the
  partitions reproduced in §6.1 here.
- `docs/legacy-m12-asset-parity.md` — the binding M12 investigation, §6 item 3
  being the decision this document answers.
- `tools/asset-registry/convert_building.py:285-310` — the gradient FILLSTYLE
  parse (§3.1).
- `tools/asset-registry/convert_unit.py:71-77` — `TIMELINE_REFUSED_TAGS`
  (§4.2).
- `tools/asset-registry/census_targets.py:113-143` — the two-clause candidate
  derivation (§6.2).