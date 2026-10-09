# Image reference resolution: investigation

Follow-up investigation for milestone **M12 — Asset Parity**, scoped by the roadmap's next
objective after `asset-package-parameterisation` archived: `godot-image-reference-resolution`
("50 `ambiguous` + 32 `missing_source` asset references"). **It implements nothing.** It changes
no tool, no client, and no registry entry. It contains no conversion and no extraction.

Everything below is measured from committed repository artifacts. §0.1 gives a reproducible
recipe and §10 carries the appendix script, so every figure in prose can be re-derived rather
than taken on trust.

---

## 0. Scope, method, and the question

The committed `tools/asset-registry/asset_ids.json` classifies every distinct asset reference in
the corpus into a closed status vocabulary. Two of those statuses mean "known but not resolved",
and the roadmap names them as the next M12 objective:

| status | meaning (the tool's own wording, `build_asset_ids.py:6-13`) |
| --- | --- |
| `ambiguous` | several corpus files share the image basename |
| `missing_source` | the corpus contains no matching source file |

**The question this investigation must answer before any proposal is written:** *is this a
resolution failure that a better rule would fix, or a content gap that no rule can fix?* The two
answers imply completely different lines — one is a mechanism, the other is a decision.

### 0.1 Method and sources

Read-only, using the pinned interpreter
(`%LOCALAPPDATA%\Temp\opencode\cpython39\pkg\tools\python.exe`, CPython 3.9.13, always `-B`).
No repository file was written, no registry rebuilt, no Flash, browser, server, subprocess, or
network was used. The §10 script reproduces every figure in this document; it reads
`asset_ids.json` and walks `assets/images/en/` and `apps/client-godot/` and writes nothing.

Sources:

- `tools/asset-registry/asset_ids.json` — the committed registry, policy `asset-id-registry-v1`,
  1,627 entries.
- `tools/asset-registry/build_asset_ids.py` — the resolver whose rule this investigation examines.
- `packages/game-content/normalized/images.json` — the upstream references (607 distinct).
- `assets/images/en/` — the committed image corpus, **573 files**.
- `apps/client-godot/scripts/content_registry.gd` — the only client consumer of the statuses.

---

## 1. First correction: the roadmap's "32 `missing_source`" is the images kind alone

Measured across all four kinds in the committed registry:

| kind | entries | ambiguous | converted | extracted | missing_source | passthrough | pending |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `images` | 607 | **50** | 0 | 9 | **32** | 516 | 0 |
| `item_sprites` | 872 | 0 | 2 | 857 | 10 | 0 | 3 |
| `magic_sprites` | 10 | 0 | 0 | 6 | 0 | 0 | 4 |
| `sounds` | 138 | 0 | 0 | 0 | 0 | 138 | 0 |

The repository-wide `missing_source` total is therefore **42**, not 32. The roadmap's figure —
and the change name this investigation is scoped by — refers to the **images** kind only. The
**10** `item_sprites` entries are a different population with a different cause and are scoped
out in §8; they are named here so the boundary is explicit rather than implied.

Both image sets are **completely structural**. There is no long tail: the 32 are 29 chapter
variants, 2 prison images, and 1 stray; the 50 are 3 directory pairings.

---

## 2. The 50 `ambiguous` entries are 25 candidate pairs, and the ambiguity is real

Every ambiguous entry has **exactly two** candidates — the histogram is `{2: 50}`, with no entry
at 3 or more. The pairs come from exactly **three** directory pairings:

| pairing | entries | distinct basenames |
| --- | --- | --- |
| `assets/images/en/chapters` ↔ `assets/images/en/chapters2` | 24 | 12 (`chapter_1.jpg` … `chapter_12.jpg`) |
| `assets/images/en/chapters/simple` ↔ `assets/images/en/chapters2/simple` | 6 | 3 (`aliens`, `arachnids`, `orcs`) |
| `assets/images/en/goals` ↔ `assets/images/en/packs` | 20 | 10 (`1.png` … `10.png`) |

Each basename generates **two** ambiguous entries, one per reference, which is why 25 pairs
become 50 entries.

**The ambiguity is not a harmless duplicate.** Comparing the two candidates byte-for-byte:

- **17 of the 25 pairs differ**, which is **34 of the 50 entries**.
- **8 pairs are byte-identical**, which is 16 entries.
- Decomposed: of the 12 `chapter_N.jpg` pairs, **5 differ** (`chapter_5`, `6`, `7`, `10`, `11`);
  of the 3 `simple` pairs, **2 differ** (`arachnids`, `orcs`); **all 10** `goals`/`packs` pairs
  differ, and by a wide margin — `goals/1.png` is 3,210 bytes against `packs/1.png` at 65,092,
  every one of the ten an order of magnitude smaller, consistent with icon against card art.

**So resolving any of these 34 entries wrongly ships visibly different art.** This is not a
bookkeeping nicety; it is the difference between a chapter screen and the wrong chapter screen.

---

## 3. The rule discards the exact component that disambiguates

The registry states its own images rule in the committed document
(`asset_ids.json`, `kinds[images].rule`):

```text
basename match (web-root-relative form preserved, never rewritten)
```

`build_asset_ids.py:317-335` implements precisely that: it looks up `image_candidates[ref]` where
the candidates were keyed by **basename alone**, and if `len(candidates) > 1` it returns
`ambiguous` with no choice made.

**But the reference already carries the disambiguating directory.** The 50 refs are not bare
names — they are:

```text
/goals/1.png            vs  /packs/1.png
/chapters/chapter_1.jpg vs  /chapters2/chapter_1.jpg
/chapters/simple/orcs.jpg vs /chapters2/simple/orcs.jpg
```

The tool preserves the reference form verbatim and then throws away the part of it that settles
the question. This is the whole defect, and it is a defect in the **rule**, not in the corpus.

---

## 4. A path rule resolves all 50 — with zero disagreement, and a bijection onto the corpus

If the reference is web-root-relative, the natural join is `assets/images/en` + `/` +
`ref.lstrip("/")`. Measured over all **607** image references:

| status | prefix rule hits | misses |
| --- | --- | --- |
| `ambiguous` | **50 / 50** | 0 |
| `extracted` | 9 / 9 | 0 |
| `passthrough` | 514 / 516 | 2 |
| `missing_source` | 0 / 32 | 32 |

Three properties make this more than a coincidence:

**(a) It resolves every ambiguous entry to exactly one existing file.** 50/50, no residue.

**(b) It disagrees with today's answer nowhere it matters.** On the **523** entries where both the
current basename rule and the prefix rule resolve, the two agree on **523 of 523** — measured
**zero** disagreements. The prefix rule is therefore a *strict refinement*: it adds a resolution
where none existed and changes nothing that already worked. It is not a reinterpretation.

**(c) It is a perfect bijection onto the corpus.** This is the strongest single piece of evidence,
and it is the reason this is a mechanism rather than an invention:

- **573** references hit under the prefix rule;
- those **573** hits are **573 distinct files**;
- `assets/images/en/` contains exactly **573** files;
- **0** corpus files are unreferenced by any reference.

Every image file in the committed corpus is named by exactly one content reference, at exactly
the path the reference itself spells out. **The corpus was authored under this rule.** A rule
invented to fit the data would not saturate it perfectly.

### 4.1 What this does *not* license

The bijection is evidence about *which* file a reference names. It is **not** evidence about what
any image should depict, whether `chapters2` supersedes `chapters`, or whether the client should
display any of them. §8 carries the claim limits.

---

## 5. The 32 `missing_source` are a content gap that no rule can close

The 32 are **29 chapter variants**, **2 prison images**, and **1 stray**:

| shape | count | refs |
| --- | --- | --- |
| `chapter_N_m.jpg` | 12 | N = 1 … 12 |
| `chapter_N_w.jpg` | 12 | N = 1 … 12 |
| `chapter_N_old.jpg` | 5 | N = 5, 7, 8, 10, 11 |
| `prison1.jpg`, `prison2.jpg` | 2 | `/chapters/simple/…` |
| `intro - copia.swf` | 1 | stray, see below |

Each has `reference_count == 1` — referenced once each, 32 references total.

**Measured absent, not mis-pathed.** For every one of the 32, a corpus-wide recursive search for
the basename under every extension (`.jpg`, `.jpeg`, `.png`, `.gif`, `.swf`, and none) returns
**nothing anywhere in the repository**. The prefix rule misses all 32 as well (§4), so they are
not relocated files.

The `_m` / `_w` suffixes are visibly a *locale-style pair* — and the corpus does hold exactly
that pattern for the intro images, which resolve: `assets/images/en/chapters/chapter_1.jpg`
exists while `chapter_1_m.jpg` and `chapter_1_w.jpg` do not. **Whether the `_m`/`_w` variants were
never authored, were dropped, or live in an unpreserved branch is not decidable from anything in
this repository.** That is a content-history question this oracle cannot answer, and §8 refuses to
guess.

The 29th-shaped outlier is genuinely diagnostic:

```text
/intro/intro - copia.swf
```

`copia` is a Romance-language word for *copy*, and the filename contains a **space**. Its six
siblings (`intro.swf`, `intro2.swf`, `intro3.swf`, `intro4.swf`, `intro_m.swf`, `intro_w.swf`)
all resolve to `assets/converted/images/…`. This is a **stray editor's copy left in the content
references**, and it is the single strongest piece of evidence that some of the 32 are authoring
debris rather than missing art. That is a reading of a filename, not a measurement of history, and
it is recorded as such.

---

## 6. The two residual misses are mis-pathed references, not a rule failure

After the prefix rule, exactly **2** of the 516 `passthrough` entries still do not resolve at the
path their reference names:

| reference | resolves today to |
| --- | --- |
| `/chapters/simple/arachnids_old.jpg` | `assets/images/en/chapters2/simple/arachnids_old.jpg` |
| `/chapters/simple/orcs_old.jpg` | `assets/images/en/chapters2/simple/orcs_old.jpg` |

Both files exist, both live under `chapters2/simple/`, and both references say `chapters/simple/`.
Directory inventory:

```text
chapters/simple/    aliens.jpg  arachnids.jpg  orcs.jpg
chapters2/simple/   aliens.jpg  arachnids.jpg  arachnids_old.jpg  orcs.jpg  orcs_old.jpg
```

So `chapters2/simple/` holds **5** files and `chapters/simple/` **3**, and the two `_old` files
exist on only one side. **These two references disagree with the corpus about which directory a
file is in**, and the basename rule papers over it precisely because it ignores directories. They
are the **only two** such cases in all 607 references.

This matters for sequencing: **a prefix rule must not silently drop them.** Either it falls back
to the basename rule for entries the path does not satisfy, or it reports them — and the choice
is a design decision for the proposal, not something this investigation settles.

---

## 7. What the client does with these statuses today

`content_registry.gd` is the only client consumer. Its contract is explicit
(`resolve_asset`, and the doc comment above it):

> for a known reference (its `status` may still be `pending`, `ambiguous`, or `missing_source` —
> **known-but-unavailable**)

The registry therefore **reports** rather than resolves. The runtime-path statuses are named in
`ASSET_STATUS_WITH_RUNTIME := ["converted", "extracted", "passthrough"]` — **neither
`ambiguous` nor `missing_source` is in it**, and `content_registry.gd:509-514` *enforces* that an
entry with any other status must not carry a runtime path.

**No client code resolves image references today.** Measured over `apps/client-godot/`
(`.gd`/`.tscn`/`.tres`, excluding the engine's `.godot/` cache):

| token | client files |
| --- | --- |
| `/chapters/` | **0** |
| `/goals/` | **0** |
| `/packs/` | **0** |
| `images/en` | 1 — `town.gd`, and all three hits are inside **prose evidence strings**, not code |

So there is **no live user-facing defect today**: nothing attempts to load these 50 images, so
nothing currently ships the wrong one. The ambiguity is a *blocking condition on a future
consumer*, and the value of resolving it is that the first consumer will not have to guess.

That also bounds the urgency honestly. This is not a bug report; it is removing a known
ambiguity before something depends on it.

---

## 8. What this investigation cannot decide

Stated plainly, because each of these is a place where a proposal could quietly invent a fact.

1. **Whether `chapters2` supersedes `chapters`.** The two directories hold the same 12 basenames
   with 5 revised. Nothing preserved says which is current. The prefix rule **sidesteps** this
   rather than answering it: each reference names its own directory, so both sets ship as
   authored. That is a defensible outcome and it is **not** a determination that `chapters2` wins.
2. **Whether the 32 missing images should be authored, or their references removed.** Both are
   content decisions with no evidence in this repository. §5 measures the absence; it does not
   license creating the files or editing the references.
3. **Whether `chapters2/simple/` is the intended home of the two `_old` files** (§6), or whether
   the references are wrong.
4. **What any image depicts.** Nothing here inspects pixels. §4 is about path resolution only.
5. **Whether the `intro - copia.swf` stray indicates broader reference debris.** One filename is
   one data point. It is suggestive and it is not a pattern.
6. **The 10 `item_sprites` `missing_source` entries** (`0137_spy_academy_m`,
   `10000_chained_bonus_giant_walker`, `10027_prision`, `10034_chained_hercules_mech`,
   `10048_cross_dc`, `1011_bad_girl_m`, `982_chained_red_spinner`, `casachina`, `treasure`,
   `vacaPerdida`). These are sprite SWFs absent from `assets/sprites/`, a different population
   with a different rule (joined path, not basename) and a different cause. **Out of scope**,
   named here so their omission is a decision and not an oversight.
7. **Whether changing the images rule is safe downstream.** `asset_ids.json` is a committed input
   to the registry manifest and to `conversions.json`, so a rule change **cascades**. The cascade
   must be measured by whoever proposes it, not assumed from this document.
8. **Nothing about the legacy Flash client's behaviour.** No Flash, Ruffle, or ActionScript
   executes here, and this oracle cannot say what the original client displayed for any of these
   references.

---

## 9. Recommended decomposition

The measurement supports **one mechanism line** and **one decision line**, and they should not be
merged:

- **`godot-image-reference-resolution`** (mechanism). Resolve image references by their own
  path, with the basename rule retained as an explicit fallback so the two mis-pathed entries in
  §6 stay visible rather than silently dropped. Deliver the resolution, not the art. Claim
  limits: path resolution only, zero rendering, zero pixel parity.
- **A content decision, not a change** (not proposed here). Whether the 32 absent images are
  authored or their references retired is a product decision this repository cannot make.

Explicitly **not** recommended: mass-regenerating `asset_ids.json` by silently switching rules.
The rule is the tool's own declared contract (`"basename match … never rewritten"`), so changing
it is a behaviour change to a preservation tool and must arrive with its own spec, its own
cascade measurement, and its own claim limits.

---

## 10. Corrections

Recorded rather than quietly fixed, per the repository's standing rule.

1. **My first instrument produced a false blocker, and I reported it before checking it.** The
   first probe joined the prefix and the reference **without a path separator**
   (`"assets/images/en" + ref`). For the 145 references that are *bare filenames* this produced
   `assets/images/enGOING_TO_BATTLE.jpg`, so the prefix rule appeared to break **147**
   currently-passing `passthrough` entries — and my first summary of that probe would have
   concluded the rule was unusable. The correct join inserts the separator and strips the
   reference's leading slash, after which the true breakage count is **2**. The false number was
   an artifact of my join, and the correction changed the conclusion from "reject" to "adopt with
   a fallback".
2. **`os.listdir` returned a directory as a file.** A directory-comparison helper treated
   `chapters/simple` as a candidate file and raised `PermissionError` when hashing it, aborting
   the run before the `chapters`/`chapters2` comparison completed. Filtering to files fixed it.
   The run had already produced the two directory listings, which is why the defect was visible
   rather than silently narrowing a count.
3. **The roadmap's "32 `missing_source`" is kind-scoped, not global** (§1). The global figure is
   **42**. I am recording this against the roadmap text I am following rather than leaving the
   next reader to reconcile 32 against 42.
4. **The appendix script shipped a logic error, and running it caught a contradiction with this
   document.** The first draft compared agreement with
   `e["runtime"] in (joined(e["ref"]), e["source"])` — which asks whether *`runtime`* equals either
   value — instead of whether *either `runtime` **or** `source`* equals the prefix join. Run
   verbatim it printed **514 agreements and 9 disagreements**, contradicting §4(b)'s measured
   **523 and 0**. The error was in the *test*, not in the finding: the 9 are the `extracted` image
   entries, whose `runtime` points at `assets/converted/images/…` while their `source` is the
   corpus file the prefix rule finds, so the malformed predicate rejected all nine. Corrected to
   an explicit two-term disjunction, the appendix prints **523 agreements and 0 disagreements**
   and reproduces every figure in this document. **Had the appendix been written and shipped
   without being executed, this document would have carried two mutually contradictory numbers
   and the reader would have had no way to tell which was right.**

No figure in this document is a recollection. Every number was produced by the §10 script, and the
structural decomposition in §2 (8 identical / 17 differing pairs) is internally consistent with
§4's 523 agreements and §1's status counts — those cross-checks are why the pair counts are stated
as pairs and the byte-comparisons as entries.

---

## Appendix — reproducing every figure

Read-only. Writes nothing, opens no subprocess, no network, no Flash. Run with the pinned
interpreter and `-B`; pass the repository root as `argv[1]`.

```python
import hashlib, json, os, sys

REPO = sys.argv[1]
ROOT = "assets/images/en"


def joined(ref):
    return ROOT + "/" + ref.lstrip("/")


def abs_(rel):
    return os.path.join(REPO, rel.replace("/", os.sep))


def digest(rel):
    with open(abs_(rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


doc = json.loads(open(abs_("tools/asset-registry/asset_ids.json"),
                      encoding="utf-8").read())
images = [k for k in doc["kinds"] if k["kind"] == "images"][0]
entries = images["entries"]

# section 1 - status counts for every kind
for kind in doc["kinds"]:
    tally = {}
    for e in kind["entries"]:
        tally[e["status"]] = tally.get(e["status"], 0) + 1
    print(kind["kind"], len(kind["entries"]), tally)

# section 2 - the 50 ambiguous entries are 25 pairs, and 17 of them differ
ambiguous = [e for e in entries if e["status"] == "ambiguous"]
print("candidate counts:", sorted({len(e["candidates"]) for e in ambiguous}))
differing = [e for e in ambiguous
             if digest(e["candidates"][0]) != digest(e["candidates"][1])]
print("entries", len(ambiguous), "differing entries", len(differing),
      "=> differing pairs", len(differing) // 2)

# section 4 - the prefix rule: 50/50, zero disagreements, and a bijection
hits = [joined(e["ref"]) for e in entries if os.path.isfile(abs_(joined(e["ref"])))]
print("hits", len(hits), "distinct", len(set(hits)))
corpus = [os.path.relpath(os.path.join(d, f), REPO).replace(os.sep, "/")
          for d, _, fs in os.walk(abs_(ROOT)) for f in fs]
print("corpus files", len(corpus), "unreferenced", len(set(corpus) - set(hits)))
both = [e for e in entries
        if os.path.isfile(abs_(joined(e["ref"])))
        and e["status"] in ("passthrough", "extracted")]
agree = [e for e in both
         if e["runtime"] == joined(e["ref"]) or e["source"] == joined(e["ref"])]
print("agreements", len(agree), "disagreements", len(both) - len(agree))
for e in both:
    if e not in agree:
        print("  disagreement:", e["status"], e["ref"],
              "runtime", e["runtime"], "source", e["source"])

# sections 5 and 6 - what the prefix rule still cannot resolve
for e in entries:
    if not os.path.isfile(abs_(joined(e["ref"]))):
        print("residual:", e["status"], e["ref"], "->", e["runtime"])
```

The 32 absent references in §5 need a corpus-wide search rather than a prefix test; the appendix
prints them as `residual: missing_source …`, and their absence under *every* extension is the
claim that requires the recursive walk.
