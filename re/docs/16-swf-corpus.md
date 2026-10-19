# The SWF Corpus — 1 176 Files, Characterised

**Roadmap task B2.** The vendored asset tree holds **1 176 SWF files, 620.6 MB**. The
original plan was to decompile all of them and index the classes. Doing that would have
wasted roughly an hour of CPU to produce a thousand trivial document classes. This document
records what the corpus actually contains — and the finding that reframes the asset pipeline.

| | |
|---|---|
| **Source** | `upstream/socialwarriors/assets/**` (1 176 SWF) |
| **Tooling** | `node scripts/analyze-swf-corpus.mjs` → [`../data/swf-corpus.json`](../data/swf-corpus.json) |
| **Method** | A native SWF container parser (no JVM, no decompiler): header, RECT, frame rate, and the full tag stream, with the SHA-256 of every file |

---

## 1. The headline

| | Files | Bytes |
|---|---|---|
| **Contain real gameplay code** | **67** | 250.1 MB |
| **Contain only a stub document class** | **1 108** | 370.3 MB |
| **Contain no ActionScript at all** | **1** | 0.2 MB |
| **Total** | **1 176** | **620.6 MB** |

**Only 67 of the 1 176 SWF files need decompiling.** The other 1 109 are pure art.

### Why the sprites look like code but are not

Every sprite SWF does contain a `DoABC` tag — but the block is a few hundred bytes of
auto-generated glue. Decompiling `sprites/1001_worker_m.swf` gives exactly two things:

```actionscript
[Embed(source="/_assets/assets.swf", symbol="symbol195")]
public dynamic class A1001_worker_mA extends MovieClip { }
```

and the per-frame timeline scripts:

```actionscript
public dynamic class arquero1atacando3_4detras_17 extends MovieClip {
    public function arquero1atacando3_4detras_17() { super(); addFrameScript(9, this.frame10); }
    internal function frame10() : * { stop(); }
}
```

That is the Flash *timeline* expressed as code, not game logic. **The asset pipeline is a
frame-and-atlas problem, not a code problem.** This is the single most useful thing B2
produced, because it tells the team to spend its effort on frame extraction and atlasing
rather than on decompiling art.

## 2. The corpus by group

| Group | Files | MB | Real code | Stub only | None |
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

### The 67 files with real code

| Set | Count | What it is |
|---|---|---|
| `assets/flash/Basesec_*.swf` | 58 | the client builds, 1.4.5 → 1.5.4 |
| `assets/flash/SWLoader.swf` | 1 | the runtime loader (6 classes) |
| `assets/flash/Debug_1.5.4.swf` | 1 | the debug build |
| `assets/swf/dynamic2.swf` | 1 | loaded at runtime by the client — **still unanalysed** |
| `assets/fonts/en_ArialRoundedBold.swf`, `en_KomikaAxis.swf` | 2 | SWF font libraries with embedded font classes |
| `assets/sprites/10002_chained_junk_bot.swf` | 1 | sprite with a >4 KiB frame script block |
| `assets/sprites/1180_robot_hunter.swf` | 1 | " |
| `assets/sprites/1200_nebular_motorized.swf` | 1 | " |
| `assets/sprites/1201_junk_bot.swf` | 1 | " |

The four sprites above the 4 KiB threshold are worth a look in Group D: they may have real
per-frame logic rather than just `stop()` calls. They are the only art files that might
behave differently once converted.

## 3. What every entry records

| Field | Use |
|---|---|
| `path`, `bytes`, `sha256` | the content bundle references assets by hash |
| `swfVersion`, `compressed`, `declaredLength` | container facts; all are SWF v10, all compressed |
| `frameRate` | 24 fps for sprites, 30 fps for the client — the atlas must record this per asset |
| `frameCount`, `frames` | the frame count the converter must extract |
| `tagTotal`, `topTags` | the tag composition, which tells the converter what it is dealing with |
| `hasActionScript`, `abcBlocks[]` | the ABC block names and sizes |
| `codeClass` | `real` / `stub` / `none` — the scoping decision from §1 |

## 4. Implications for the asset pipeline (Group D)

| Finding | Consequence |
|---|---|
| Only 67 files have code | the converter needs a **frame** path, not a decompile path, for 1 109 of 1 176 files |
| Sprites carry an `[Embed(symbol=…)]` class | the symbol id in the class is the link between the SWF timeline and the exported frames — the converter must preserve it |
| Sprites use `DefineSprite` nesting (up to 7 per file) | frames are **nested timelines**, so a naive "one frame per ShowFrame" export is wrong; the converter must flatten the nested sprite structure |
| Frame rates differ (24 fps sprites, 30 fps client) | the atlas manifest must carry a per-asset frame rate and duration |
| `Tag86` (`DefineSceneAndFrameLabelData`) appears in sprites | the scene/frame-label structure is scene-based, and the converter should preserve scene boundaries |
| 4 sprites exceed the 4 KiB ABC threshold | worth auditing before the conversion starts — they may not be plain art |

**The `assets/swf/dynamic2.swf` file is the one remaining unanalysed code artefact.** The
client loads it at runtime (observed in the live session), so it is part of the client's
behaviour surface. It should be decompiled as part of Group D's first step.

## 5. Reproducing this

```bash
node scripts/analyze-swf-corpus.mjs     # -> re/data/swf-corpus.json
```

The parser is a few dozen lines and deliberately independent of FFDec, so the census can be
re-run in seconds rather than minutes and is not tied to a JVM being present.

> A note for anyone re-implementing a SWF tag reader: the `RECORDHEADER` is a `UI16` where
> **the tag id is the upper 10 bits and the length is the lower 6**. A length of `0x3F`
> means a `UI32` length follows. Getting this backwards silently mis-parses every file — it
> is the reason an earlier attempt at this scan reported "0 files with ActionScript".

## 6. Known limits

* The census is **structural**, not semantic: it does not decompile the 67 code-bearing
  files. That is a deliberate scoping decision, justified by §1.
* Frame counts come from `ShowFrame` tags at the top level; **nested `DefineSprite`
  timelines are not counted**, so `frames` is the top-level frame count, not the total number
  of drawable frames. The converter will need the real count.
* `topTags` is limited to the six most common tags per file.
* The corpus covers `assets/**` only. The upstream repository also has 1 753 JPG and 140 MP3
  files, catalogued in the assets report.
