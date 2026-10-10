# M12: a per-shape trace of the desync family, and where the untouched 118 diverge

Status: investigation. No production code is changed by this document, and no
line is proposed.

Predecessors: `docs/legacy-m12-desync-downstream.md` (PR #362, merged `be3cf7d`),
`docs/legacy-m12-signed-rect.md` (PR #357, merged `ef93fdb`) and
`docs/legacy-m12-desync-origin.md` (PR #356, merged `07c8b19`).

This document does the one thing its predecessor named as the next eligible
objective: it partitions the **118 untouched targets** by *where inside a shape
the walk first diverges*, rather than by the refusal class name they all share.

---

## 1. Summary

The **118 untouched** targets are **not one group**. They split into three, and
the largest is a code path the located defect cannot reach:

| Group | n | Leaf stage | Recorded class |
| --- | --- | --- | --- |
| Gradient fills | **87** | `S5_line` | `shape byte overrun` (all) |
| Solid fills | **5** | `S5_line` | `shape byte overrun` (all) |
| Fill-array refusals | **25** | `S4_fill` | four different classes |
| Inline read | **1** | `S3S6_inline` | `shape bit overrun` |

**87 of the 92** that stop in the LineStyleArray declare a **gradient** fill
type as read (`0x12` radial **57**, `0x10` linear **30**); only **5** declare
`0x00` solid. The located defect is a **solid** fill colour width
(`docs/legacy-m12-desync-origin.md` §5), so it is confined to the `FILL_SOLID`
branch and structurally cannot reach those 87.

In those 87 the walk reaches the line count with the reader at the wrong offset:
the declared FILL count is **1** for 91 of the 92, and the declared LINE count
takes **46 distinct values** including **65535**, exceeding the number of line
styles actually entered in **89 of 92**.

**No cause is established here, and no line is proposed.** What this document
delivers is a partition that routes, and one specific unmeasured expression to
measure next.

---

## 2. What the predecessor left unmeasured

`docs/legacy-m12-desync-downstream.md` recorded, as the next eligible
objective:

> The census captures a target's first refusal and stops, so it carries no
> information about how far the walk got, where inside the shape the parse
> diverged, or how many bytes were left unconsumed. [...] What a next step
> needs is a trace recording the **entry bit position** of the first
> divergence, so the untouched 118 can be partitioned by *where* they desync.

That is what this is. `target_census.json` stores no positional information at
all — every family target records `problem_count` exactly 1 — so nothing
already committed could answer it.

---

## 3. What the trace wraps, and why it is not a re-implementation

The shape parse is a fixed sequence of stages, and the shipped code already
calls each one as a module global, so the trace wraps the real functions rather
than restating the sequence:

| Stage | Code |
| --- | --- |
| S1 `ShapeId` (UI16) | read inline in `parse_shape_with_style` |
| S2 `ShapeBounds` RECT | `parse_rect_bits` |
| S3 align | `align_to_byte` |
| S4 `FillStyleArray` | `parse_style_arrays` → `parse_fill_style` |
| S5 `LineStyleArray` | `parse_style_arrays` → `parse_line_style` |
| S6 fill/line bit counts | read inline |
| S7 shape record walk | `count_shape_records` |

`convert_unit.py` imports `convert_building` as `shared` and calls
`shared.parse_shape_with_style`, so one patch set covers both domains.
`BitReader` is subclassed only to capture the shape's reader, which is what
makes a failure's **bit offset** readable at the instant it raises.

Because `walk_shape_tags` yields each shape's payload with the 2-byte id
intact, the reader's bit position **is** the offset from the shape's entry.

The trace records per target: shapes attempted, shapes parsed before the
failure, the failing shape's id and tag, its payload length, the **leaf** stage
and bit offset, bytes left unconsumed, the full stage event list, and — for the
style arrays — the FILL count, the FILLSTYLE type byte, and the LINE count as
read **off the payload bytes at the offsets the reader actually reached**, so
those counts are an observation rather than a restatement of the converter's
return value.

Routing is delegated to the committed `census_targets.evaluate`, so the
per-domain converter choice is never re-implemented here.

---

## 4. Controls

Four, each with the failure it was written to catch. All four pass.

**Calibration.** All **290** converted targets were traced: every shape parses,
no fabricated failure anywhere. A recorder that can invent a failure measures
nothing. As a by-product the trace counts **4347** shapes across those targets,
which **independently reproduces** the figure the shipped sign-extension line
reports — evidence the trace sees exactly the shapes the converter does, and
*not* evidence that either is correct.

**Inertness.** The refusal class recorded by the traced run must equal the class
recorded by the untraced run for all **272**. It does: **272 of 272**.
Instrumenting changed no verdict.

**Discrimination.** A partition into one bucket is not a partition. The stage
distribution contains **4 distinct** leaf stages; the `(declared line count,
styles entered)` distribution contains **46 distinct** pairs.

**The own-versus-mid-stream detector must return both values.** A detector that
has only ever returned one value has not been shown to discriminate. Over the
290 converted targets it returns **own 12132 / nested 654**, and within the
family run itself it returns **108 own / 9 nested** — both values, one process,
one population.

---

## 5. The partition of all 272

| Leaf stage | Targets |
| --- | --- |
| `S4_fill` | **164** |
| `S5_line` | **98** |
| `S7_records` | **9** |
| `S3S6_inline` | **1** |

By domain: `S4_fill` 100 unit / 64 building, `S5_line` 85 unit / 13 building,
`S7_records` 9 unit, `S3S6_inline` 1 unit.

---

## 6. The partition of the untouched 118

The 118 are recomputed here from the recorded per-target verdicts rather than
read from the predecessor's output, so this document does not inherit a figure
it cannot check.

| Leaf stage | Targets | Domain |
| --- | --- | --- |
| `S5_line` | **92** | 82 unit / 10 building |
| `S4_fill` | **25** | 23 unit / 2 building |
| `S3S6_inline` | **1** | 1 unit |

Identity: 92 + 25 + 1 = **118**.

Leaf stage against recorded class — the 92 are **uniform**, the 25 are not:

| n | Stage | Class |
| --- | --- | --- |
| 92 | `S5_line` | `shape byte overrun` |
| 9 | `S4_fill` | `shape bit overrun` |
| 6 | `S4_fill` | `shape byte overrun` |
| 6 | `S4_fill` | `unknown fill style` |
| 4 | `S4_fill` | `shape byte misaligned` |
| 1 | `S3S6_inline` | `shape bit overrun` |

Own arrays versus mid-stream `NewStyles` blocks: **90** of the 92 are the
shape's **own** LineStyleArray and 2 are a `NewStyles` block reached from the
record walk; of the 25, **18** are the shape's own FillStyleArray and **7** are
mid-stream.

Bytes left unconsumed in the failing shape: `S5_line` median **1**, max **3**;
`S4_fill` median **0**, max **1095**.

---

## 7. Routing the 92 by the fill type actually read

The FILLSTYLE type byte, read at the offset the walk reached:

| Fill type | n | Route |
| --- | --- | --- |
| `0x12` | **57** | radial gradient |
| `0x10` | **30** | linear gradient |
| `0x00` | **5** | solid |

**87 of 92 are gradients** — 78 unit, 9 building — and **5 are solid** — 4 unit,
1 building. The located defect concerns the solid colour width and lives in the
`FILL_SOLID` branch, so it is confined to those 5.

What the reader believed when it reached the line count:

- declared FILL count is **1** for **91** of 92 (2 for the remainder);
- declared LINE count takes **46 distinct** values — 89, 47, 138, **65535**, 81,
  122, 140, 30, 230, 224, 98, 232 among them;
- the declared LINE count **exceeds the number of line styles entered** for
  **89 of 92**;
- a LINESTYLE is at least 5 bytes (UI16 width + RGB), so a count of 65535
  against a finite payload is not a count that was ever meant to be satisfied.

The five solid cases separately:

| Stem | Declared line count | Styles entered | Own/nested |
| --- | --- | --- | --- |
| `1299_gameraMech` | 16 | 27 | nested |
| `1358_bushwacker` | 16 | 21 | nested |
| `1401_supressorGunner` | 16 | 14 | own |
| `1412_pauldronMech` | 16 | 15 | own |
| `10003_chained_dual_blade_automech` | 112 | 4 | own |

The first two enter **more** styles than they declared, because the count read
at their own array was 16 and the failing style is in a later `NewStyles` block.

---

## 8. What is **not** claimed

- **No cause is established for the 87.** The trace localises and routes; it
  does not diagnose.
- **The `FILL_GRADIENTS` branch contains an expression of the same textual form
  as the one located as defective** — `reader.read_bytes(4 if rgba else 3, label)`
  inside its per-ratio loop, against the solid branch's located defect. That is
  an **observation about the code**, recorded as the next place to measure. It
  is **not** a claim that the expression is wrong, and this document does not
  assert that correcting it would convert anything. The located defect converts
  2 of 272 and net 0 across all 817; that is the standing precedent against
  treating a same-shaped expression as a fix.
- **The located defect is not contradicted.** Its domain is the solid fill, and
  the trace is consistent with its reach.
- **The 4347 shape count is not a correctness claim.** It shows the trace and
  the converter see the same shapes, nothing more.
- **`problem_count` uniformity is unchanged** and still records only the first
  refusal. This document adds a trace beside the census; the census itself is
  untouched and still stores no input digests, which remains the recorded gap.
- Nothing is rendered, so there is no windowed capture and no pixel-parity
  oracle. No production code, OpenSpec change or committed artifact changed.

---

## 9. Instrument faults, committed with this document

Six, all mine, all found by the controls rather than by inspection.

1. **`RecursionError`.** After `cb.BitReader = TracingReader`, the
   `cb.BitReader.__init__(self, data)` inside the subclass body resolved to the
   subclass itself and recursed 990 frames deep. Fixed by capturing the base
   class **by name before the patch is installed**.
2. **The inertness control measured the wrong thing and reported 0 of 272
   matching.** The trace records the raw converter message; the recorded class
   is produced by `census_targets.refusal_pattern`, which substitutes the
   **full sprite path**. The control substituted the bare stem instead, so every
   target mismatched on a difference that had nothing to do with the
   instrumentation. Fixed by **calling** the shipped reduction rather than
   reimplementing it.
3. **The own-versus-mid-stream detector was vacuous, and it reported a clean,
   uniform, confident-looking result.** It tested `depth > 1`; the shape's own
   `parse_fill_style` is *already* at depth 2, so the check returned `True` for
   **all 118** and separated nothing. Replaced with a **causal entry-order**
   test — a mid-stream block is entered while the record walk is still on the
   stack — and only accepted after a planted control showed both values occur.
   **The intermediate "all 118 are mid-stream" result is withdrawn.** This is
   the same defect class as `docs/legacy-m12-signed-rect.md` C-4's 1,154
   "failing shapes": a check with no discriminating power returning a tidy
   aggregate that would have supported a conclusion.
4. **The enclosing wrapper overwrote `failed_at`.** The leaf stage raised first
   and the outer wrapper then replaced it, collapsing the fill and line stages
   back into one bucket. Fixed by keeping the first failure.
5. **The style arrays were wrapped as one stage**, so the fill array and the line
   array could not be told apart — the exact distinction that turned out to
   carry the finding. Split into leaf stages.
6. **The calibration sample was too small to witness its own control.** Ten
   converted targets yielded 22 `own` and **0** `nested`, which established
   nothing. Widened to the full 290, where both values occur.

---

## 10. Corrections to predecessors

None of the predecessor figures change. `118 of 272` reproduces exactly, and
the 106 unit / 12 building domain split reproduces exactly.

One thing is **added** rather than corrected: the predecessor's "not one defect"
statement was a statement about the located defect's *reach*. This document
gives that phrase a **measured shape** — 87 gradient, 5 solid, 25 fill-array, 1
inline — and that shape is why "not one defect" may now be acted on rather
than only restated.

---

## 11. Where this leaves the cursor

The next eligible objective is **not a line**. It is a measurement of the
`FILL_GRADIENTS` branch of `parse_fill_style`, using the same trace discipline:
record the per-ratio offsets and the offset the reader believes it is at when
it returns to the shape's own byte stream. It is the largest routed group in
the untouched 118 and it is untouched by the located defect.

Two decisions remain open and are **not** pre-authorised: mass-converting the
290 available packages, and revisiting the three scope-decision classes.