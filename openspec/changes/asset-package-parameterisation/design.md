# Design — asset package parameterisation

Binding investigation: `docs/legacy-m12-asset-parity.md` (merged `f7f9861`).
All figures below were measured from the working tree on 2026-10-09 by running the **committed**
converters into a temporary output root. No repository file was written by any measurement.

---

## D1 — The target becomes a required input; the module constants are removed, not defaulted

`TARGET_STEM` (and `TARGET_LEGACY_ID`) become required CLI inputs and the module-level constants
are deleted. A run without a target fails closed with a clear message and writes nothing.

*Rejected — keep the constant as the default.* A silent default is the failure mode a batch runner
cannot detect: converting the whole candidate population while one of them silently re-derives M4's
target would be indistinguishable from doing the work. The requirement is stated so a missing target
is an error, not a fallback.

> **VINDICATED BY MEASUREMENT (Apply stage, 2026-10-09).** This paragraph's stated failure mode is
> not hypothetical — the Propose-stage census *fell into it*. It drove the unit converter by
> reassigning `TARGET_STEM`/`TARGET_LEGACY_ID`, missed the third constant `SOURCE = "assets/sprites/"
> + TARGET_STEM + ".swf"` (computed at import time, therefore never moved), and so parsed the same
> elephant SWF for all **365** unit targets. The result was a false **365 / 365 (100%)** unit
> figure; the real figure is **68 / 365**. Full record in `proposal.md` §2. The third constant is
> also why D2's deletion of module-level state is not limited to the two obvious names.

*Rejected — a `--all` mode that sweeps every candidate.* That couples "parameterised" to "batch",
and the batch needs a target list with an explicit order for the census to be deterministic
(D5). The sweep belongs to the census tool, which writes to a contained root.

## D2 — The building takes one parameter and the unit takes two

The building converter resolves content by `img_name == stem` (line 609). The unit converter
requires `legacy_id == id` **and** `img_name == stem` (lines 313–314). Both are preserved exactly,
including their existing fail-closed behaviour on a non-unique match, because that guard is what
keeps a parameterised run from binding the wrong content row.

*Rejected — derive the unit's `legacy_id` from its stem* so both tools take one parameter. The
stem→id relation is **unestablished**: `10033_wild_elephant` is `933` and `0001_house_1_m` is `1`,
but no rule has been measured across the 429 units, and a wrong derivation would silently attach
the wrong definition to a package. Two explicit parameters are cheaper than a guessed join.

*Rejected — resolve the id by scanning for the unique row whose `img_name` matches, then reading
its `legacy_id`.* This is exactly what the current code already does *and* what makes the id
redundant; collapsing them would remove the existing two-key uniqueness guard, which is the one
thing standing between a parameterised run and a wrong-content package.

## D3 — `fingerprint_inputs` digests line-ending-normalised bytes, and the two unpinned inputs are pinned LF

`convert_building.py:517-525` hashes the **raw working-tree bytes** of `buildings.json`,
`inspection.json`, and `image_extraction.json`. Two of those three are not pinned in
`.gitattributes` and carry **170,096** and **1,219,378** CRLF on disk. The digest is the
package's `content_version`, so this is not merely a comparison problem — the provenance field
itself is checkout-form dependent:

| | raw disk bytes | LF-normalised |
|---|---|---|
| buildings fingerprint | `ddeca799…` = committed | `c4e76e6d…` |
| units fingerprint | `9d8ad3b3…` = committed | `a0c3861f…` |

The remedy is the one this project already adopted for the compatibility guard, quoted from
`apps/compat-api/guard_baseline.py`: *"text digests are line-ending invariant, so the baseline
holds across checkout forms"*. The converters get the same normalisation, and the two paths are
pinned LF alongside the existing `asset_ids.json` / `coverage.json` pins.

*Rejected — pin the paths LF and change nothing else (fix by configuration).* Pinning makes the
*checkout* deterministic but leaves the digest function itself reading raw bytes, so any future
unpinned input silently reintroduces the defect. The normalisation is the fix; the pin removes the
40 MB of churn that would otherwise keep re-flipping the working tree.

**Consequence, accepted deliberately:** both committed packages' `content_version` change, and so
do the `package_sha256` values in `conversions.json`. That is the *point* — those digests were
reproducible on exactly one checkout form. Because `guard_baseline.py` hashes
`assets/converted/buildings/0001_house_1_m`, `assets/converted/units/10033_wild_elephant`, and
`conversions.json` under `conversion_packages` and `registry_manifests`, its committed baseline at
`tests/fixtures/godot-compatibility-boot/guard-baseline.json` is regenerated in the same change.
Not regenerating it would leave the guard asserting digests of bytes that no longer exist.

## D4 — No manifest-merge threading; the merge is already cumulative

Reading `merge_conversion_document` suggested a single-target merge that would drop N−1 entries
in a batch. Measurement refutes it: running **either** converter alone emits a **two**-package
`packages` list with `counts.packages = 2`, and the committed manifest records both
(`0001_house_1_m`, `10033_wild_elephant`). `build_asset_ids.py` additionally already rejects a
manifest that repeats a `legacy_id` (line 208), so a clobbering batch would fail loudly rather
than silently. No merge state is threaded and no ordering requirement is introduced.

## D5 — The census is a separate tool beside the converters, writing a committed deterministic report

`tools/asset-registry/census_targets.py` walks a declared candidate set, calls each converter's
build into a **per-target** directory under a required `--out-root`, and writes
`tools/asset-registry/target_census.json` with each target's verdict and, on failure, its refusal
class and the distinct problem strings.

It is a tool rather than a converter mode because it must be re-runnable and diffable
independently of the packages it measures, and because containment is a property worth having in
one place. Containment is verified, not assumed: `write_outputs` writes the package directory, the
bitmap payloads, `conversions.json`, and `statuses.json` **only** beneath `out_root`
(`convert_building.py:718-733`), which is why the census is safe to run at all.

*Rejected — have the census write its results into `conversions.json`.* That file is a
`conversion-v1` envelope owned by `build_asset_ids.py`, which validates it; a census is not a
conversion and would either pollute the envelope or need a parallel schema nobody consumes.

## D6 — The census records refusals and does not exit non-zero for a refused target

The census must measure a **population**, so one unconvertible target cannot end the run. It
reports refusals as data with their class, and exits non-zero only for a genuine tool failure
(unreadable input, malformed census output). A census that aborted on the first refusal could not
have produced the **230**-target refusal table this change is built on.

*Rejected — fail the run on any refusal, as the converters do.* That is right for a build and
wrong for a census: it would make "how many convert" unanswerable, which is the whole question.

## D7 — No fix is attempted for any of the four building refusal classes

The classes and their measured counts are recorded as a refusal surface:

| class | targets |
|---|---|
| `unresolvable bitmap fill … -> 65535` | **133** |
| `unknown fill style` | **61** |
| `unsupported shape tag: 83` | **20** |
| `shape byte/bit overrun` | **16** |

The `unknown fill style` bytes observed are 155, 117, 216, 100, 174, 122, 6, 255, 13, 77, 223, 32,
246, 12, 200, 2, 55, 60, 209, 71 — **only `13` is a legal SWF fill type**, which is consistent with
a desynchronised read rather than an exotic format, but the cause is **not** established and no
record-format correlation is claimed either: the bucket with no `DefineShape*` tags at all still
converts **167 of 326**.

The 133-target sentinel class is explicitly **unestablished**, because my own two measurements
disagree. A spike porting `first-unit-conversion`'s referenced-only `65535` rule converted **0**
additional targets and regressed **0**; a separate 40-target probe found **697 unreferenced** and
**14 referenced** `65535` fills and found neither in **27 of 40**. Shipping either reading as the
fix would be guessing. Each class is a separate investigation line, and the census report is what
makes that line measurable.

> **EXTENDED (Apply stage, 2026-10-09).** D7 scoped the refusal question to the *building* domain
> and this change did not intend to extend it. The delivered census forced the extension: the unit
> domain refuses **297 of 365** candidates across **seven** further classes — `shape byte overrun`
> (**90**), `unknown fill style` (**76**), `unsupported timeline tag … (PlaceObject#)` (**57**),
> `unsupported shape tag: 83` (**44**), `shape bit overrun` (**18**), `shape byte misaligned`
> (**11**), `unsupported tag in timeline` (**1**). `unknown fill style` and `unsupported shape
> tag: 83` now span **both** domains, and the two overrun classes are no longer building-only.
>
> **No fix is attempted for any of them**, exactly as D7 decided for the building classes, and none
> is investigated here. What is claimed is only that they are *measured* and *classified*, with
> **no target in more than one class** in either domain. Each remains a separate investigation
> line. Notably, the unit converter's failure modes are dominated by shape decoding and timeline
> tags, **not** by fills — so the Propose-stage reasoning that "the unit converter generalises
> cleanly because it decodes timeline records and never touches fills" was wrong in both
> directions: it does touch fills, and its timeline support does not generalise either.

## D8 — No mass conversion in this change

**290** packages are available (**222** buildings + **68** units). Committing them is roughly
15,000 files, regenerates the preservation manifest (currently **3,258 entries / 758,423,699
bytes**), and delivers **no** client-visible progress while `apps/client-godot/scripts/package_paths.gd`
pins exactly two packages. That diff deserves its own line with its own measured file count, byte
total, and manifest delta. This change delivers the tooling and the census that makes that line
possible.

> **CORRECTED (Apply stage, 2026-10-09).** This decision originally read "**587** packages …
> (**222** buildings + **365** units) … roughly 30,000 files". The unit half was a false figure
> produced by a defect in the Propose-stage measuring instrument — see D1's vindication note and
> `proposal.md` §2. Re-measured by the delivered census: **222** buildings + **68** units =
> **290** available, **527** targets refused across **8** refusal classes. The decision itself is
> unchanged and, if anything, strengthened: there is now **no domain that is 100% convertible**, so
> the follow-up mass-conversion line cannot be scoped by domain and must first resolve refusal
> classes.

## D9 — The `legacy_id` field carrying the stem is recorded, not corrected

Both committed packages record `"legacy_id": "<stem>"` (`convert_building.py:670,697`;
`convert_unit.py:454`) even though the unit converter separately resolves the *content* id `933`,
and `conversions.json` keys its entries by stem. The field name is therefore misleading. It is
recorded here and **left alone**: it is committed in the packages, in the envelope, and in
`build_asset_ids.py`'s join, and renaming it changes the meaning of a schema this change does not
need to touch. Correcting a naming defect while parameterising is how an unearned fix ships.

## D10 — Containment and preservation discipline

- Every measurement and every new tool run writes **only** beneath an explicit `--out-root`.
- Preserved inputs — sprites, extracted bitmaps, `inspection.json`, `image_extraction.json`,
  normalized content, saves, config, villages — are read-only and must be byte-identical after.
- `auctions/` and `saves/` must remain absent; legacy Python that touches `auctions/` is never run
  with the repository root as the working directory.
- No Flash, Ruffle, ActionScript, or browser execution; no network access of any kind.