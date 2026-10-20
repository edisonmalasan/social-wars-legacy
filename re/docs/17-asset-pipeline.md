# The Asset Pipeline — Converting 376 MB of Flash into Renderable Frames

**Roadmap task D.** The shipped product must not contain a Flash runtime, so every piece
of art in the vendored tree has to become an ordinary image the modern renderer can draw.
This document records the measurements that determine how that conversion is done, and
the pipeline they imply.

| | |
|---|---|
| **Source** | `upstream/socialwarriors/assets/**` — 1 176 SWF, 620.6 MB, plus 1 753 JPG and 140 MP3 |
| **Tooling** | JPEXS FFDec 26.3.0, driven by `node scripts/convert-assets.mjs` |
| **Corpus census** | [`../data/swf-corpus.json`](../data/swf-corpus.json) — every SWF characterised |
| **Frame manifest** | [`../data/frame-manifest.json`](../data/frame-manifest.json) — (swf, symbol, frame) → image |

---

## 1. What the corpus actually is

From the census in [`16-swf-corpus.md`](16-swf-corpus.md):

| | Files | MB | Real code | Stub class only | No ActionScript |
|---|---|---|---|---|---|
| `sprites/` | 862 | 357.2 | 4 | 858 | 0 |
| `flash/` | 60 | 244.2 | 60 | 0 | 0 |
| `fx/` | 205 | 9.0 | 0 | 205 | 0 |
| `images/` | 9 | 5.7 | 0 | 8 | 1 |
| `characters_2/` | 26 | 2.1 | 0 | 26 | 0 |
| `magic/` | 10 | 1.4 | 0 | 10 | 0 |
| `externalized/` | 1 | 0.5 | 0 | 1 | 0 |
| `swf/` | 1 | 0.5 | 1 | 0 | 0 |
| `fonts/` | 2 | 0.1 | 2 | 0 | 0 |
| **Total** | **1 176** | **620.6** | **67** | **1 108** | **1** |

**Only 67 files need decompiling.** The other 1 109 are pure art, so the conversion is a
**frame-and-atlas** problem. The "stub class" is an auto-generated `MovieClip` document
class with an `[Embed(symbol=…)]` attribute — the timeline expressed as code, not logic.

## 2. A sprite is a library, not an animation

This is the finding that determines the whole pipeline.

The 862 sprites have a **median of one top-level frame** and only **936 top-level frames
between them**. A sprite SWF is a *container of nested `DefineSprite` timelines*: one
building's parts, one unit's animation states, each a separate nested timeline. The
original client loads the SWF, asks for a symbol by name, and plays that symbol's
timeline.

The consequence is that the obvious export mode is the wrong one:

| Export mode | What it produces | On `0003_depot_oil_1_m.swf` |
|---|---|---|
| `-export frame` | one PNG per **top-level** frame | **1 PNG** — the art is thrown away |
| `-export sprite` | one PNG per **nested** timeline frame | **170 PNGs** across 4 symbol directories |

`-export sprite` is the mode. It flattens every nested timeline into a numbered PNG
sequence.

### The output layout

FFDec writes:

```
<outdir>/<swf-file-name>.swf/DefineSprite_<id>[_<symbol-name>]/<frame>.png
```

The `DefineSprite` directory name carries the character id and, where the SWF has one, the
**symbol name** — which is the link back to the game. For example
`DefineSprite_26_0003_depot_oil_1_m` and
`DefineSprite_22__978_chained_corfe_1_fla.DG_andarTcopy_3` name the *animation state*
(`andarTcopy_3` = "and attack, copy, frame 3"). **The symbol names are the game's own
vocabulary for what each timeline is**, and the converter must preserve them: the modern
renderer has to know that `fla.DG_andarTcopy_3` is the "attacking" pose of a unit.

## 3. The frames are mostly duplicates

A 43 KB sprite exports to 170 PNGs totalling 7.3 MB. Content-hashing them:

| Symbol | Frames | Unique images | Duplicate | Bytes |
|---|---|---|---|---|
| `DefineSprite_24` | 162 | **8** | **95 %** | 7.4 MB |
| `DefineSprite_25` | 2 | 2 | 0 % | 76 kB |
| `DefineSprite_26_0003_depot_oil_1_m` | 2 | 2 | 0 % | 76 kB |
| `DefineSprite_5` | 4 | 1 | 75 % | 122 kB |
| **Total** | **170** | **12** | **93 %** | **7.3 MB** |

An animation holds each drawing for many ticks, so the same image is exported over and
over. **Deduplicating by content hash is not an optimisation, it is the design**: it turns
the corpus from an estimated 6–7 GB of PNG into a content-addressed store of a few hundred
megabytes, and it is what makes atlasing tractable.

The converter therefore writes each distinct image **once**, named by its SHA-256, and the
manifest maps `(swf, symbol, frame)` to that hash. Two symbols in different files that
draw the same picture share one stored image.

### Measured on a sample

A 30-file sample of `sprites/`, converted with 3 parallel FFDec processes:

| | |
|---|---|
| SWF files | 30 |
| Symbols (nested timelines) | **230** |
| PNG frames written | **8 245** |
| Unique images | **2 024** |
| Duplicate rate | **75.4 %** |
| Raw PNG bytes | 414.5 MB |
| Store bytes (deduplicated) | **233.6 MB** |
| Wall clock | 107 s |

So 30 files → 7.7 symbols each, and the deduplication already halves the payload on this
sample. The per-sprite figure above (93 %) is the worst case, for a file whose animation
holds each drawing for a long time; the sample's 75 % is the realistic average.

The manifest for the sample is
[`../data/frame-manifest-sample.json`](../data/frame-manifest-sample.json).

## 4. FFDec's cost model, and how to make it bearable

Measured on this machine (Java 21, JPEXS 26.3.0):

| Invocation | Wall clock | Notes |
|---|---|---|
| One file, `-export frame` | 6.0–12.4 s | of which ~6 s is JVM start-up |
| One file, `-export sprite` | 6.7 s | 170 PNGs written |
| A **directory** of 3 files | 16 s | one JVM, three files |
| A **directory** of 3 files (large) | 12.3 s of export | 403 PNGs across 18 symbol directories |

**FFDec accepts a directory as its input**, and exports every file in it. That matters
because the JVM start-up is a fixed ~6 s per invocation: converting 1 116 files one at a
time would spend **~2 hours of pure start-up**. Converting them in directory batches
amortises it away.

The converter therefore:

1. splits a group into *N* batches of SWFs,
2. runs *N* FFDec processes in parallel, each on its own batch directory,
3. walks each batch's output, hashes every PNG, and writes only the **new** images into
   the content-addressed store,
4. deletes the batch's temporary PNGs immediately.

Step 4 is what keeps the temporary space bounded: FFDec writes a whole batch before the
converter can look at it, so the batches are sized to keep the peak temporary size
manageable rather than to minimise the number of JVM invocations.

## 5. The pipeline

```
upstream/socialwarriors/assets/**/*.swf
        │
        │  ffdec -export sprite  (N batches in parallel)
        ▼
<tmp>/<swf>.swf/DefineSprite_<id>[_<name>]/<frame>.png
        │
        │  sha256 → content-addressed store, duplicates dropped
        ▼
.work/frames/store/<sha256>.png          (one file per DISTINCT image)
        │
        ▼
re/data/frame-manifest.json
    images:  { <sha256>: { file, width, height, bytes } }
    symbols: [ { swf, symbol, frameCount, uniqueFrames,
                  frames: [ { frame, image } ] } ]
```

### The manifest's shape

| Field | Meaning |
|---|---|
| `swf` | the source file, e.g. `sprites/0003_depot_oil_1_m.swf` |
| `symbol` | the `DefineSprite` directory name, including the character id and the symbol name |
| `frameCount` | how many frames the timeline has |
| `uniqueFrames` | how many of those frames are distinct images |
| `frames[]` | the frame index → the content hash of its image |

The manifest is the contract between the asset pipeline and the client: the renderer asks
for *(sprite, animation state, frame)* and gets a region of an atlas.

## 6. Trimming and packing

The converter produces a *content-addressed store* of distinct frames. The client
cannot ship that, because a WebGL texture is one image. So there is a second step.

### 6.1 Trim

A frame exported from a SWF is the **whole stage**, so most of it is transparent
padding. Every image is cut to its alpha bounding box, and the offset is recorded,
so the renderer can place the sprite and the atlas holds no empty space.

On the 32-image sample the trim removed **24.1 %** of the pixels.

### 6.2 Pack

The trimmed images are packed into square atlases with a **shelf packer**: rows of
images, sorted by height first so the rows are uniform and the wasted space is
small. The manifest records, for every image, the trim offset and the region it
occupies in its atlas.

The sample packed 32 images into four 512×512 atlases at **65.1 % occupancy**.

### 6.3 The PNG codec

Both steps need to read and write PNGs, and the repository has **no runtime
dependencies** by design, so `scripts/lib/png.mjs` is a minimal PNG codec on top
of Node's built-in zlib:

* decode: 8-bit, non-interlaced, colour types 0 (grey), 2 (RGB), 3 (palette),
  4 (grey+alpha) and 6 (RGBA) — which is what JPEXS writes
* encode: RGBA, filter type 0, `zlib` level 9

### 6.4 The verification

The packer is checked by comparing **every trimmed region, pixel by pixel, against
its source image**:

```
pixels compared : 682 856
opaque pixels   : 323 257
mismatched      : 0
```

and the PNG codec by a round-trip test (decode → encode → decode is byte-identical),
an exact alpha-bounding-box test, and a decode of a real exported frame.

### 6.5 Using it

```bash
node scripts/pack-atlases.mjs                      # the default 2048px atlases
node scripts/pack-atlases.mjs --size 512 --padding 2
```

The atlases are a build artefact (`.work/frames/atlases/`); the manifest is the
contract.

## 7. What is still to do

| Step | Status |
|---|---|
| Corpus census (every SWF characterised) | ✅ done — `re/data/swf-corpus.json` |
| Frame export + dedup + manifest | ✅ done — `scripts/convert-assets.mjs` |
| Trim to the alpha bounding box | ✅ done — `scripts/pack-atlases.mjs` |
| Pack the atlases | ✅ done — `scripts/pack-atlases.mjs` |
| The full run over all 1 116 SWF files | 🔄 in progress |
| **Audio** | **todo** — the 140 MP3s in `assets/sounds/` need a format and a manifest. |
| **Fonts** | **todo** — the two SWF font libraries need to become a web font or a bitmap font. |
| **The 4 sprites above the stub threshold** | **todo** — `10002_chained_junk_bot`, `1180_robot_hunter`, `1200_nebular_motorized`, `1201_junk_bot` have more than 4 KiB of ABC and may hold real per-frame logic rather than `stop()` calls. They need an audit before the conversion is trusted. |
| **`assets/swf/dynamic2.swf`** | **todo** — the one remaining unanalysed code artefact; the client loads it at runtime. |
| **Thumbnails and chapter images** | **todo** — the 1 314 JPG thumbnails and the 578 chapter/intro JPGs are already plain images and need only a manifest. |
| **A viewer** | **todo** — renders every item at 3 zoom levels, so missing art is visible immediately. |
| **A content-hashed asset bundle** | **todo** — so a stale cache is impossible. |

### Two things the measurements changed about the plan

1. **The atlas count.** With a ~93 % duplicate rate, the corpus holds far fewer distinct
   images than the naive "one PNG per frame" estimate. The atlases will be far smaller
   than the roadmap's rough figure implied, and the dedup must happen *before* packing,
   not after.
2. **The symbol names matter.** `DefineSprite_26_0003_depot_oil_1_m` and
   `DefineSprite_22__978_chained_corfe_1_fla.DG_andarTcopy_3` encode the game's own
   animation-state vocabulary. A converter that renamed them to `sprite_1`, `sprite_2`
   would throw away the naming that makes the art usable. The manifest keeps them
   verbatim.

## 7. Reproducing this

```bash
node scripts/convert-assets.mjs                       # every group
node scripts/convert-assets.mjs --group sprites       # one group
node scripts/convert-assets.mjs --limit 40 --jobs 6   # a sample
```

`FF_DEC` must point at `ffdec-cli.exe`. The image store lives in `.work/frames/store/`
and is a build artefact — it is git-ignored, and the committed artefact is the manifest.

## 8. Method notes and limits

* The measurements are from JPEXS 26.3.0 on Java 21, on one machine. The *ratios* (the
  duplicate rate, the export mode, the directory batching) are properties of the files;
  the *timings* are not.
* The duplicate rate is measured on one sprite in detail and on the sample as a whole.
  It will vary per file — a building with a genuinely changing animation will have a
  lower duplicate rate.
* The converter measures PNG dimensions from the IHDR chunk. It does not yet measure the
  alpha bounding box, which the trim step needs.
* Frame indices are FFDec's own numbering, which starts at 1. The renderer will need the
  frame *rate* per symbol as well; the corpus census records the SWF's frame rate (24 fps
  for sprites, 30 fps for some), and it belongs in the manifest.
