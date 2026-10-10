# M12: the `FILL_GRADIENTS` branch, measured at the offsets it reads

## 1. Summary

This is the objective the predecessor named as next eligible: **measure** the
`FILL_GRADIENTS` branch of `convert_building.parse_fill_style` — per-ratio
offsets, and the offset the reader believes it is at when it returns to the
shape's own byte stream. It is a measurement, not a line. Nothing in
`tools/`, `packages/`, `docs/` other than this file, or `openspec/` changed,
and no conversion was attempted.

The measurement found something the predecessor could not have read off its
own trace, and found one thing that the trace's most tempting reading would
have gotten wrong.

**Found.** After a gradient `FILLSTYLE` the reader resumes at an offset from
which the following `LineStyleArray` count cannot be satisfied inside the
shape tag it was read from, in **86 of 87** cases. The same measurement over
the **5** shapes that stop at the same stage through a *solid* `FILLSTYLE`
finds **1**, and that one is a case the predecessor had already recorded as a
mid-stream `NewStyles` block rather than the shape's own array. The
divergence is therefore bracketed to the inside of the gradient record,
between the type byte and the end of that one fill style. Across the whole
817-target population, **129** gradient blocks are read, in **124** targets,
and **not one of them is in any of the 290 targets that convert**.

**Refuted.** The obvious reading — that the gradient block overruns or
consumes the rest of its own tag — is **false**. The block's span is smaller
than the bytes remaining in the tag in **87 of 87** cases, by between 2 and
314 bytes. The block does not run off the end of anything; it stops in the
wrong place inside it.

**Not done, deliberately.** The SWF format specification was not consulted.
That comparison is a diagnosis, and this stage is chartered to measure. It is
named as the next eligible objective in section 10.

---

## 2. What the predecessor left open

`docs/legacy-m12-shape-trace.md` section 7 recorded that **87** of the 92
targets stopping in the LineStyleArray read a gradient fill type, and that the
defect it had located — a solid colour width — is confined to `FILL_SOLID` and
so structurally cannot reach them. It recorded that the declared line count in
those 87 takes **46 distinct** values including **65535**, and warned that the
`FILL_GRADIENTS` branch contains a textually same-shaped expression to the
located defect, which is **not** evidence of anything.

That warning is respected here. This document reports what the reader *does*,
measured; it does not report what the reader *should* do, because nothing in
this repository says what a gradient fill style should contain.

---

## 3. What the probe wraps

`parse_fill_style` is wrapped, not reimplemented. The wrapper records, per
call: the reader's bit position at entry and exit, the fill type byte and the
offset it was read at, and the exact span of `BitReader` operations the call
issued. `BitReader` is subclassed with `BASE_READER` bound at class-creation
time, so no read method can resolve back to the subclass after patching —
recorded as instrument fault 1 of the predecessor and avoided by construction
rather than by testing.

The probe reads no bytes of its own. Every offset it reports is the offset the
shipped parser reached.

Two passes:

| Pass | Targets | Purpose |
| --- | --- | --- |
| `traced` | all **817** | inertness, census agreement, tag-extent oracle, discrimination, population census |
| focused | the **92** stopping in the LineStyleArray | the offsets, and the tag-extent contradiction |

Variants ran in **separate processes**. Running both in one process would
have let the first variant's module patches leak into the second, which is the
recorded failure mode from an earlier stage.

---

## 4. Controls

Five, in the order they were run. The planted control was run **before** any
population result was read, and its failures would have discarded the probe
rather than been explained.

### C1 — planted, not derived from the parser

A `DefineShape` payload of **18 bytes** was written byte by byte with one
linear gradient fill and the offsets recorded in the file's own header
comment. The probe must report 22 of them: fill entry at byte 4, flags at
byte 5, ratio offsets 6 and 10, colour offsets 7 and 11, colour values
`112233` and `445566`, matrix at byte 14, exit at byte 15, span 11 bytes,
declared count 2, spread 3, interpolation 2, and two bits of padding before
the tag's own end.

**22 of 22, PASS.** Without this the probe's ability to see an offset at all
would have been an assumption.

### C2 — inertness

Traced against unpatched over all 817 targets, compared on both verdict and
refusal class: **817 / 817 identical, 0 divergences.**

### C3 — the census it claims to observe

**817 / 817** match the committed `tools/asset-registry/target_census.json`
on both verdict and refusal class: 527 refused, 290 converted, and all eight
refusal classes at their recorded counts
(137 / 133 / 104 / 64 / 57 / 20 / 11 / 1).

### C4 — the tag-extent oracle has teeth

The shape payload's length comes from the SWF tag header and is never shown to
the parser, so a correctly parsed shape must end inside its own tag with 0 to
7 bits of padding. Over **4347** parsed shapes in converted targets:

| Padding bits | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | outside |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Shapes | 51 | 824 | 114 | 994 | 175 | 679 | 126 | 1384 | **0** |

**4347 independently reproduces the predecessor's shipped shape count**, and
all eight buckets are populated, so the oracle is discriminating rather than
trivially satisfied. An empty histogram would have made this control
worthless and it is discarded if it ever goes empty.

### C5 — the probe separates

Across the population's gradient blocks: **10** distinct entry-byte values,
**42** distinct spans, **30** distinct flag bytes, **12** distinct declared
counts. Uniform values here would mean the probe separated nothing — the
predecessor's vacuous detector returned a clean uniform `True` for all 118 and
measured nothing at all.

---

## 5. The population census

25,898 shape calls across the 817 targets. Every fill type byte the reader
read, counted as read:

| Fill type | Read | Where |
| --- | --- | --- |
| `0x00` solid | 54,136 | both |
| `0x41` bitmap | 41,730 | both |
| `0x43` bitmap | 1,053 | both |
| `0x40` bitmap | 169 | both |
| **`0x12` radial gradient** | **85** | **refused only** |
| **`0x10` linear gradient** | **44** | **refused only** |
| `0x42` bitmap | 5 | both |

**129 gradient blocks, in 124 targets. Every one is the first fill in its
shape. Not one occurs in any of the 290 targets that convert.**

That is the second half of the finding and it is a property of the corpus, not
an inference: the gradient branch has **no successful instance anywhere in the
committed population**, so there is no completed parse against which its
offsets could be validated. A branch with no instance that works cannot be
calibrated by an instance that works.

By the refusal class those 129 targets carry:

| Refusal class | Gradient blocks |
| --- | --- |
| `shape byte overrun` | 96 |
| `unknown fill style` | 17 |
| `shape byte misaligned` | 11 |
| `unsupported shape tag` | 4 |
| `shape bit overrun` | 1 |

---

## 6. The 87 offsets

The 92 targets stopping in the LineStyleArray reproduce the predecessor's split
**exactly and independently**: **87** gradient, **5** solid; gradient types
`0x12` ×57 and `0x10` ×30; domain 78 unit / 9 building for the gradient group.

**Reading the gradient block.**

| Measured | Value |
| --- | --- |
| Entry byte | 5 distinct values: 8, 9, 10, 11, 12 |
| Entry byte-aligned | **87 / 87** |
| Flags byte offset relative to entry | **+1, in 87 / 87** |
| Flags byte-aligned | **87 / 87** |
| Flags byte value | **25 distinct** |
| Declared gradient count (the code's low nibble) | **12 distinct**, 1 to 13, mode 13 (23 cases) |
| Ratio offsets | 47 distinct |
| Colour offsets | 47 distinct |
| Colour length | 3 bytes ×74, 4 bytes ×651 — matching tag 2 against tags 22/32/83 |
| Span | 14 to 84 bytes |
| Exits byte-aligned | **25 / 87** |

The ratio loop entered **exactly** the declared count in **87 / 87** cases, so
the span is arithmetically self-consistent. **Self-consistency is not
correctness**, and section 8 is the test that separates them.

**The return offset, tested against the tag.** At block entry the tag has
between **43** and **355** bytes left; the block spans **14** to **84**. The
span is therefore **smaller** than the bytes remaining in **87 / 87** cases,
by between **2** and **314** bytes. The block does not eat its tag, and does
not overrun it.

**The decisive test, which needs no format reading.** A `LINESTYLE` is at
least five bytes — a UI16 width and an RGB triple — so a declared line count
that cannot fit inside the tag it was read from is unsatisfiable whatever the
format intends. Comparing the two groups at the identical failure stage:

| | Gradient (87) | Solid (5) |
| --- | --- | --- |
| Distinct declared line counts | **39** | **2** |
| Median declared count | **89** | **16** |
| Count values include | 65535 (×6), 36716, 251, 232, 224, 212, 208, 192, 191, 185, 174, 157, 152, 140, 138 | 16 (×4), 112 (×1) |
| Median bytes left in the tag after the count | **42** | 87 |
| **Declared count unsatisfiable in the tag** | **86 / 87** | **1 / 5** |

The single solid exception is `10003_chained_dual_blade_automech`, declaring
112 against 19 bytes left, and the predecessor had already recorded that
shape as reaching its failing style inside a mid-stream `NewStyles` block
rather than its own array — so the group sizes do not even compare like with
like, and the gradient group's advantage is larger than 86 against 1.

At the point of refusal the gradient shapes have **0 to 3** bytes left in their
tag (36 / 29 / 6 / 16). The reader is not running off the end of the tag; it
is running off the end of the *stream it believes it is in*.

---

## 7. What the byte at the type offset is doing

The divergence is bracketed to *after* the type byte because that byte is
demonstrably at the right offset, on this repository's own evidence:

- in **87 / 87** gradient cases the byte at the structural fill-type offset is
  a member of `{0x10, 0x12}`, and only those two values;
- in **5 / 5** solid cases it is `0x00`;
- across the whole population only **seven** distinct type bytes are ever read
  at that offset.

An offset that is wrong does not land on a two-value set 87 times running. This
supports, and does not prove, that the type byte is read correctly; the proof
would be an external authority this stage declined to consult.

---

## 8. Three things the measurement refutes, and one it does not reach

1. **The gradient block does not overrun or consume its tag.** Span minus
   bytes-left-at-entry is negative in 87 of 87. This was the most tempting
   reading of the predecessor's numbers and it is wrong.
2. **Leaving the reader mid-byte is not a defect.** 62 of 87 exit unaligned,
   but `parse_matrix` is a bit-oriented structure and legitimately ends
   mid-byte. This looked like a signal on first reading and is not one.
3. **Arithmetic self-consistency is not correctness.** The loop entered
   exactly the declared count every time; that is a statement about the
   reader agreeing with itself.
4. **Not reached: the `0x13` focal branch.** No `0x13` fill type is read
   anywhere in the 817-target population, so the branch that reads two focal
   bytes on type `0x13` rather than on a flag bit is **entirely unexercised and
   unmeasured**. It is recorded here so that no later reader mistakes silence
   about it for a clean result.

---

## 9. What is **not** claimed

- **No diagnosis.** The SWF format specification was not read, in the
  repository or over the network. This document says where the reader ends up,
  not what the record should have contained.
- **No fix, and no conversion.** No production code changed. The converter
  fails open on these 87 exactly as it did before this document existed.
- **No claim that the gradient branch is the sole cause of the desync family.**
  It reaches 124 targets that read a gradient block; whether repairing it
  converts any of them is untested and is not estimated here.
- **No claim about the 5-byte line style minimum beyond what the predecessor
  established.** It is used as a bound, not as a model.
- **No claim that the low nibble is the gradient record count.** It is what
  the shipped code treats as the count; this document reports it as such.
- **The 25 targets stopping inside the FillStyleArray are outside the 92.** The
  population figure is 129 blocks; the offset analysis is the 92.
- **No rendering, no asset truth, no gameplay parity.** Nothing was converted
  or displayed.

---

## 10. Instrument faults committed with this document

1. **The reduction selected the wrong shape.** It took each target's *first*
   shape rather than the *failing* one, which produced a clean-looking split
   of 1 gradient / 18 solid / 73 other. Every figure in section 6 is from the
   corrected reduction, which selects the shape whose outcome is `refused`.
   The wrong run was discarded rather than reported.
2. **A grouping predicate indexed a list it had not tested for emptiness**, and
   raised `KeyError` on the first row. Written defensively after the first
   failure rather than patched around.
3. **The line count was not observable from the population pass**, because the
   read log lives in memory and only offsets were persisted. Rather than
   re-run the 817, a focused 92-target pass persists the failing shape's
   payload so the count is read out of the committed bytes. This was found
   before any figure was quoted, not after.
4. **The population pass was killed twice** — once by a 600-second tool
   timeout and once by a server restart — and neither kill produced a partial
   file. Both are harness events, not parser faults; the runs were restarted
   and both exited 0. The instrument writes its document only at the end, so a
   killed run leaves nothing rather than something partial.
5. **The tagged sweep of the committed trace was recomputed rather than
   inherited.** The 92 were re-derived from the trace's own per-target
   verdicts and reproduced its 57 / 30 / 5 split, its 78 / 9 domain split and
   its 92 total before any new figure was computed.

---

## 11. Where this leaves the cursor

The gradient branch is now measured rather than suspected, and the measurement
brackets the divergence without explaining it. The next eligible objective is
therefore bounded and named:

**Compare the measured layout against the documented SWF `FILLSTYLE` gradient
layout**, one field at a time, and record which field the measured offsets
contradict. That is a diagnosis step and is deliberately not begun here.

The two open decisions are unchanged and still not pre-authorised:
mass-converting the 290 available packages, and revisiting the three
scope-decision classes. Neither was advanced by this stage, which changed no
production code.