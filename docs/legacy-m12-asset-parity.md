# M12 — Asset Parity: investigation

Binding investigation for milestone **M12 — Asset Parity**. This record is the input to any
M12 proposal. **It implements nothing.** It contains no conversion, no extraction, no
decompilation, and no client change.

Everything below is measured from committed repository artifacts. The measurement script is
reproducible from the commands in §0.1 and every figure quoted in prose was produced by a single
consolidated run, so no number here is a recollection.

---

## 0. Scope, method, and the question M12 actually poses

M12's committed deliver list (`docs/DEVELOPMENT_ROADMAP.md`, "M12 — Asset Parity"):

```text
all runtime-required SWFs converted or recreated
UI assets converted
FX replaced
animation gaps resolved
```

M12's exit criterion:

```text
Godot no longer depends on runtime SWFs.
```

**These two are not the same kind of statement, and the difference decides the milestone.** Four
deliverables describe *asset content work*; the exit criterion describes *the client*. They can
therefore be independently satisfied or independently unmet, and in this repository they are
already in that state: the exit criterion is **met** while the deliverables are close to
untouched. Establishing that is the finding of this investigation, and every remaining section is
the evidence for it or the measurement of what is left.

### 0.1 Method and sources

| question | source |
|---|---|
| which assets does committed content name, and in what state | `tools/asset-registry/asset_ids.json` (1,627 entries, policy `asset-id-registry-v1`) |
| what is inside each SWF | `tools/asset-registry/inspection.json` (1,176 entries) |
| what exists as a conversion package | `tools/asset-registry/conversions.json` (2 packages) |
| what bitmaps were extracted | `tools/asset-registry/image_extraction.json` (61,702 bitmaps) |
| what the legacy client loaded | `templates/play.html`, `templates/login.html`, `server.py` |
| what the Godot client loads | `apps/client-godot/` sources and `package_paths.gd` |

The asset-ID status vocabulary is closed and defined at `build_asset_ids.py:8-13`; the two
statuses that matter most here are **`converted`** ("an assembled conversion package directory
exists") and **`extracted`** ("bitmap outputs are recorded for the source SWF"). Extraction and
conversion are different products: bitmaps without geometry and timeline cannot be drawn.

No Flash, Ruffle, ActionScript, or browser executed; no network was used; no preservation byte
was modified. This is a read-only measurement.

---

## 1. The exit criterion is already met, and was never at risk

**Godot loads no SWF.** Measured two ways:

1. **Token scan.** Every `.swf` occurrence under `apps/client-godot/` resolves to one of five
   files, and all five are non-loads: `scripts/units/research_flow.gd` (a rationale string
   *naming* committed asset filenames), `tests/test_friends.gd` (a **forbidden-token list** that
   guards *against* SWF references), `tests/test_research.gd`, and two committed evidence
   reports. There is no `load()`, no `preload()`, and no resource path to any `.swf`.
2. **Standing gates.** `tests/test_town_gate.gd` scans project sources for
   `RUNTIME_NEEDLES := ["ruffle", "actionscript", "flashvars", "shockwave"]`, and
   `tests/test_project_scope.gd` holds a `FORBIDDEN` token table. Both are already green in
   every recorded battery.

The conclusion is narrow and deliberate: **M12's exit criterion is satisfied by the client's
existing design, not by M12's work.** No M12 deliverable is required to satisfy it. That does not
make the deliver list unnecessary — it makes the milestone's *reporting* wrong, and §3 gives the
honest accounting.

---

## 2. The runtime-required SWF set is two files, not 1,176

The temptation on reading "all runtime-required SWFs" is to assume the whole corpus is
runtime-required. Measured, it is not, and the distinction is large.

### 2.1 The legacy client's actual entry path

`templates/play.html:85` — the only SWF reference in the game's own template:

```html
src="http://{{SERVERIP}}:{{SERVERPORT}}/static/socialwars/flash/SWLoader.swf?swftoload=/static/socialwars/flash/{{GAMEVERSION}}"
```

So the client was **a SWF loader that loaded a versioned game SWF**. `GAMEVERSION` comes from the
session: `templates/login.html:49-50` offers a version dropdown marking `1.5.4` as *Latest*, and
`server.py:96` pins `session['GAMEVERSION'] = "Basesec_1.5.4.swf"` for a new village.

### 2.2 The pinned runtime pair, measured

| file | bytes | ABC blocks | DefineSprite | exports | symbols | frame labels |
|---|---|---|---|---|---|---|
| `assets/flash/SWLoader.swf` | 127,786 | 6 | 20 | 1 | 3 | 1 |
| `assets/flash/Basesec_1.5.4.swf` | 4,542,821 | **1** | **1,224** | 419 | 420 | 39 |
| `assets/flash/Debug_1.5.4.swf` | 4,585,198 | 1 | 1,224 | 419 | 420 | (see §2.3) |

`Basesec_1.5.4.swf` also carries **10,002** `PlaceObject2` tags, **5,445** `ShowFrame` tags, and
**369** embedded bitmap ids. All three files exist in the committed corpus. Two further ABC-bearing
SWFs sit outside `assets/flash/` and are named by nothing in content or templates:
`assets/swf/dynamic2.swf` (492,559 bytes, 1 ABC, 34 sprites, 0 exports, 49 symbols) and
`assets/externalized/viral_buttons/crossDCi.swf`. Whether the game loads them is undecidable
here (§5.1); they are recorded so the "two entry SWFs" framing is not mistaken for "only two
SWFs exist with logic in them".

### 2.3 Fifty-seven of the sixty `flash/` SWFs are historical builds

`assets/flash/` holds **60** SWFs: **58** `Basesec_<version>.swf` spanning `1.4.9`…`1.5.4`, plus
`SWLoader.swf` and **`Debug_1.5.4.swf`**. Only `Basesec_1.5.4.swf` is pinned by the server, so the
other **57** versioned builds are superseded, not runtime requirements.

The debug build is the interesting one and is recorded rather than collapsed into a count:
`Debug_1.5.4.swf` is **4,585,198 bytes** against the release's **4,542,821**, and it carries an
**identical structural fingerprint** — 1 ABC block, 1,224 `DefineSprite`, 419 exports, 420
symbols. It is the same build with instrumentation. So the *current-version* corpus is **three**
files (loader, release, debug) while the *server-pinned* set is **one**. Nothing in the preserved
server selects the debug build, so which of the two a player loaded is **not established here**;
the claim is only that the server names one of them.

The narrowing from 1,176 to a handful is therefore **measured from the server's own pin and the
template's loader path**, not assumed from intent.

### 2.4 The sprite corpus is named by content; the game SWF is not

This is the trap the standing rule warns about ("do not assume undocumented means unused"), and
it runs in the direction that would have made this investigation wrong.

| family | SWFs | stems appearing in `packages/game-content/normalized/*.json` |
|---|---|---|
| `sprites/` | 862 | (all 862, via the registry's join rule) |
| `magic/` | 10 | (all 10) |
| `fx/` | 205 | **0 of 205** |
| `flash/` | 60 | **0 of 60** |
| `characters_2/` | 26 | **0 of 26** |

**0 of 60** for `flash/` is *not* evidence that the game SWFs are unneeded — §2.1 and §2.2 show
`Basesec_1.5.4.swf` is the game. It is evidence that **content naming is the wrong place to look
for the two entry SWFs**: they are loaded by the loader and by client-side ActionScript, not by a
content row. Any M12 work that classified assets by content reference alone would have declared
the game itself unused.

### 2.5 One hypothesis of mine was tested and rejected

I first expected the `0 of 26` for `characters_2/` to be a **rule limitation**: the registry's
`item_sprites` join rule is `assets/sprites/<stem>.swf`, so sprites living in `characters_2/`
would be *structurally invisible* rather than proven unneeded. That hypothesis is **false**,
disproved by direct search: the 26 `characters_2` stems appear **nowhere** in any of the 23
normalized content files. The `0` is a real absence of naming, not an artifact of the join rule.
Recorded because a rejected hypothesis that reads like a finding is exactly what a later reader
would re-derive.

---

## 3. The four deliver items, each classified

### 3.1 "all runtime-required SWFs converted or recreated" — **not convertible; only recreatable**

The corpus is **1,175 of 1,176** SWFs carrying an ABC (ActionScript 3) block, and **0** carrying
legacy AVM1 actions. `abc_count` is a **counter only** — `inspect_swf.py:267,303,319,344,346`
increments a number and nothing else. **This repository contains no ABC parser or decompiler**,
measured by searching all Python under `tools/`, `packages/`, and `apps/` for ABC parsing: the
only other matches are *prohibitions* on Flash and Ruffle.

The existing converters say the same thing about themselves. `convert_building.py` (805 lines)
and `convert_unit.py` (596 lines) both state they decode **timeline only** — placement, frame
counting, verbatim label names — and explicitly *skip* "Matrix, ratio, name, color, clip, and
action payloads". So:

- The **2 entry SWFs** carry the entire game's logic in **1 + 6 ABC blocks**. Converting them
  means translating ActionScript 3, which this project has no tooling for and no licence to
  execute. They must be **recreated** in Godot — which is precisely what milestones M6 through M11
  have been doing, line by line, for the pieces this oracle *can* see.
- The **872 sprite SWFs** (862 + 10) *can* be converted, because a sprite SWF's useful content is
  timeline and bitmaps. **2 are converted; 870 are not.**

**The honest accounting of this item is therefore a scope correction, not a work estimate:** as
written it is unsatisfiable for the part that matters (the game) and 0.2% complete for the part
that is feasible (the sprites).

### 3.2 "UI assets converted" — **85% already runtime-loadable; the residue is not conversion work**

The `images` kind has **607** references:

| status | count | extension |
|---|---|---|
| `passthrough` | **516** | 409 `.jpg` + 107 `.png` — already runtime-readable |
| `extracted` | 9 | `.swf` |
| `ambiguous` | **50** | — |
| `missing_source` | 32 | 31 `.jpg` + 1 `.swf` |

So **516 of 607 (85%) need nothing at all**, and the 9 SWF-backed ones join the sprite pipeline.
The residue is two categories of **evidence gap, not conversion**:

- **`ambiguous` (50).** Every one has exactly **2** candidate corpus files, and all candidates
  live in one of three colliding directory pairs: `images/en/chapters` vs `images/en/chapters2`
  (and the same pair again under `simple/`), plus `images/en/goals` and `images/en/packs`. This
  is a **content question** — which directory is canonical for a given reference — and the answer
  is not derivable from the corpus. Picking one would fabricate a content rule.
- **`missing_source` (32).** Predominantly `chapter_*` artwork (`/chapters/chapter_10_m.jpg` and
  siblings) that the corpus simply does not contain.

### 3.3 "FX replaced" — **no committed content reference exists to replace**

`assets/fx/` holds **205** SWFs and **0 of 205** stems appear in the normalized content package
(§2.4). There is no content row naming an FX asset, so there is no committed FX *specification*.

The likely explanation — that FX is referenced from ActionScript inside the game SWF, which this
oracle cannot read (§3.1) — is a **candidate**, not a conclusion. Recording it as the explanation
would be the "guess the mechanism" error this project has repeatedly declined. What is
established: **the deliver item cannot be satisfied from committed content, and its evidence
requires either new evidence or an explicit re-scope.**

### 3.4 "animation gaps resolved" — **blocked behind §3.1, with one measured contradiction already recorded**

Animation data lives in the sprite timeline, so this item is downstream of converting the 870
unconverted sprites. Two constraints are already measured and must not be re-litigated:

- The existing packages establish **asset and timeline *linkage* only, never playback
  correctness**. There is no pixel-parity oracle and no animation is played anywhere.
- `max_frame` is **not** the asset's frame count. `godot-unit-animations` measured, for the one
  committed converted unit package, that the content's `img_name` equals the package's
  `legacy_id` (so both describe the same unit), yet committed `max_frame` is **2** while the
  parsed root `frame_count` is **1** and the labelled sprite carries **29**. So the one field
  that looks like an animation length **contradicts** the asset. A line that adopted `max_frame`
  as a frame count would be wrong.

The five label names on the one converted unit are Portuguese (`QUIETO`, `ANDAR`, `ATAQUE`,
`MUERTE`, `PICAR`) and are deliberately untranslated, because nothing selects a state for a
translation to name.

---

## 4. The tooling gap: both converters are one-shot by construction

This is the concrete engineering obstacle for §3.1's feasible half, and it is small enough to
state exactly.

| tool | lines | target | mechanism |
|---|---|---|---|
| `convert_building.py` | 805 | `TARGET_STEM = "0001_house_1_m"` (`L36`) | module-level constant |
| `convert_unit.py` | 596 | `TARGET_STEM = "10033_wild_elephant"`, `TARGET_STEM`/`SOURCE` (`L38-40`) | module-level constants |

**Neither accepts a target argument.** The only CLI arguments on either tool are `--repo-root`
and `--out-root`. Converting sprite *n* requires editing a constant and rerunning. There is **no
batch mechanism**, and the target is not a parameter by policy or by accident — it is a constant.

The consumer side is symmetrically small: `apps/client-godot/scripts/package_paths.gd` pins
**exactly two** package directories, the two M4 conversions. So the end-to-end asset path is
2 of 872, and both ends are hardcoded to the same two.

**Generalising these tools is the one clearly feasible, well-specified piece of M12**, and it is
the natural first deliver line: parameterise the target, make the output deterministic per input,
and establish the batch runner and the manifest that lets a client consume *n* packages.

---

## 5. What this oracle cannot decide

Stated plainly, because the M10 precedent is a **different** verdict and must not be conflated
with it.

1. **Whether the game SWF's ActionScript loads any asset the content never names.** §2.4 and §3.3
   both turn on this. It is undecidable without an ABC reader, and this project will not execute
   ActionScript.
2. **Whether `Basesec_1.5.4.swf`'s 419 exports and 420 symbols cover the full UI.** The symbol
   names are Portuguese/Flash idioms (`PopupUpgradeBuildingAsset`, `QuestsMapLib.QuestsMapMC`,
   `PopUpNextMissionMC`) and are **evidence the surface is large**, not evidence of its content.
3. **Whether the 50 `ambiguous` images resolve to the `chapters/` or `chapters2/` file.** A
   content question with two equally supported answers.
4. **Whether any extracted bitmap is correct, correctly cropped, or correctly colour-managed.**
   Extraction is a byte copy with re-parse validation. No rendering claim exists anywhere.

**M12's exit criterion is nevertheless MET and is not "unsatisfiable from this oracle"** — that
was M10's verdict on combat, and it does not apply here. The criterion is a statement about the
client, the client loads no SWF, and that is a measurement.

---

## 6. Recommended decomposition

Offered as the investigation's recommendation, not as an authorisation. Each line needs its own
proposal on its own branch, and **none is pre-authorised**.

1. **`godot-asset-package-parameterisation`** — make `convert_building.py` / `convert_unit.py`
   take a target, add a deterministic batch runner and a manifest, and prove one **new** package
   reproduces M4's two by byte when run against them. Smallest coherent change, unblocks
   everything else, and has an existing oracle (the two committed packages).
2. **`godot-image-reference-resolution`** — resolve or explicitly record the 50 `ambiguous` and 32
   `missing_source` image references. Pure evidence work; may correctly conclude some are
   unresolvable.
3. **FX / animation re-scope decision** — §3.3 and §3.4 both need a scope decision before they
   can be planned, because neither has committed content to work from. This is a decision, not a
   line.

Line 1 is recommended first: it is the only item on M12's list that is unambiguously feasible,
has a working oracle, and unblocks the measurable part of the list.

---

## 7. Claim limits

- **This investigation implements nothing.** No conversion, extraction, decompilation, or client
  change. Every figure comes from committed artifacts read by a script.
- **"Converted" means an assembled package exists; "extracted" means bitmaps exist.** Extraction
  is not conversion, and no claim is made that an extracted bitmap can be drawn, cropped
  correctly, or placed at the right scale.
- **"Runtime-required" is measured as "named by committed content or by the legacy client's
  entry path"** — that is, `server.py:96`, `templates/login.html`, and `templates/play.html:85`.
  It is **not** measured from the game SWF's internal load list, which is undecidable here (§5.1).
- **The 57 superseded `Basesec` builds are measured as not pinned by the server**, not as useless.
  They are preserved and untouched. `Debug_1.5.4.swf` is called out separately in §2.3 because it
  is **not** a superseded version but a same-version debug build, and which of the two a player
  actually loaded is **not established here**.
- **The `0 of 205` / `0 of 60` / `0 of 26` figures are absences of *naming* in the normalized
  content package**, and §2.4 shows one case where naming-absence is *not* evidence of
  unimportance. They must not be read as "these assets are unnecessary".
- **No rendering correctness, animation correctness, visual fidelity, or pixel parity** is claimed
  or established. No converted package has ever been rendered in a verified pixel comparison.
- **No Flash, Ruffle, ActionScript, or browser executed, and no network was used.** No
  preservation byte changed; `assets/` was read only.

---

## 8. Corrections

- **§2.5 — my own hypothesis was tested and rejected.** I expected the `0 of 26` for
  `characters_2/` to be a limitation of the registry's `assets/sprites/<stem>.swf` join rule
  making those sprites structurally invisible. Direct search disproved it: the stems appear
  **nowhere** in the 23 normalized files. Recorded because the hypothesis is a plausible reading
  and a later reader would otherwise re-derive it and treat it as a finding.
- **§3.1 — "not convertible" is scoped to the 2 entry SWFs and is not a claim about the 872
  sprites**, which *are* mechanically convertible. The distinction is the whole of this
  investigation's practical content and a single sentence would have destroyed it.