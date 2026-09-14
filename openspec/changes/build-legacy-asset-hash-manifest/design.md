## Context

See `proposal.md` for motivation and the `legacy-asset-integrity` delta for the behavioral contract. The lightweight `legacy-baseline` tag resolves to `e8c98a03c902eba70323538dc5d4eaba2f2927a1`, and the nine roadmap extensions select 3,258 regular blobs. The preservation trees have no committed differences between that tag and current `main`. Windows `core.autocrlf=true` already materializes several selected JSON files with CRLF although their Git blobs contain LF, so worktree-byte hashing would not provide platform-independent baseline identity.

## Goals / Non-Goals

**Goals:**

- Derive reproducible per-file SHA-256 evidence from immutable Git object bytes.
- Keep generation bounded in memory while hashing roughly 759 MB across thousands of files.
- Make the committed manifest canonical and independently checkable.
- Fail closed on malformed Git responses, unsupported entries, unsafe paths, or invalid manifests.
- Keep all tests and generated side effects away from preserved inputs.

**Non-Goals:**

- Live-worktree monitoring, arbitrary directory hashing, or ignored/untracked file capture.
- Canonical save fixtures, packaged-release verification, dependency artifact hashes, or Git LFS retrieval.
- Asset parsing, conversion, deduplication, runtime integration, provenance/rights classification, or Flash execution.
- Expanding coverage to `.txt`, `.csv`, `.ico`, source code, or every tracked repository file.

## Decisions

### Hash immutable Git blobs rather than checkout files

The tool resolves `legacy-baseline` once to a full commit, enumerates that tree, and reads selected blob bytes through local Git plumbing without a shell. It computes SHA-256 over those bytes and records the Git-reported byte length. This makes identity independent of checkout line-ending conversion and prevents ambient ignored files from entering the corpus.

Alternatives rejected:

- Hashing the working tree is platform-dependent because selected JSON files are already converted by `core.autocrlf`.
- Extracting an archive to disk duplicates roughly 759 MB and adds cleanup risk.
- Using Git object IDs would record SHA-1 object identity, not the roadmap-required SHA-256 of file content.

### Apply the roadmap extension policy across the whole baseline tree

Selection is based on regular-blob type plus the nine case-insensitive suffixes, across the full immutable tree rather than a maintained root allowlist. All 3,258 current matches happen to live under `assets/`, `config/`, `villages/`, `mods/`, `templates/`, `stub/`, or `tools/`. The fixed commit prevents future repository additions from changing this historical set.

The alternative of hashing all preservation-looking files would add text, CSV, and icon formats the roadmap did not authorize and blur the bounded change with later provenance cataloging.

### Use one streamed Git batch

A Python 3.9 standard-library CLI will parse NUL-delimited tree output and stream the selected objects through a single `git cat-file --batch` process. It will validate modes, object types, declared lengths, complete reads, process exits, UTF-8 paths, traversal/absolute path rejection, and case-insensitive collisions. It never invokes a shell, network command, filter, checkout, or asset parser.

### Commit a minimal canonical JSON contract

The top-level fixed keys are `schema_version`, `algorithm`, `source`, `policy`, and `files`. `source` records kind `git-blob` and the full commit; policy is `legacy-assets-v1`. Entries contain `path`, `sha256`, and `size` in that order and are sorted by exact path. Serialization uses deterministic ASCII-escaped UTF-8 JSON, two-space indentation, no BOM, and one final LF. A root `.gitattributes` rule pins `legacy-manifest.json` to LF without changing attributes for preserved inputs.

Derived counts and byte totals are reported by the CLI rather than duplicated as authoritative manifest fields.

### Separate generation from strict read-only verification

`generate` reconstructs the entire result before atomically replacing only the designated output and refuses an output that resolves inside a preserved input path. `verify` strictly parses and validates the committed schema, regenerates the canonical bytes in memory from the recorded commit and fixed policy, compares exact bytes, and never writes. Success exits `0`; integrity mismatches exit `1`; invalid arguments, schema, unavailable sources, Git failures, and I/O failures exit `2`.

The default commands target the repository root, `legacy-baseline`, and `legacy-manifest.json`, while explicit `--repo`, `--ref`, and output/manifest paths support disposable tests. Verification does not accept a filesystem source from manifest data.

### Use synthetic repositories plus full-corpus checks

Standard-library tests create disposable local Git repositories covering every suffix and exclusions, deterministic order, binary bytes, line-ending conversion, spaces/mixed case, duplicate content, unsafe or unsupported entries, invalid schema values, tampering, missing commits, Git failures, and write containment. Full-corpus acceptance generates twice, compares bytes, verifies the manifest, independently checks the selected path count and sample digests/sizes, and confirms no preserved file or worktree input changed.

## Risks / Trade-offs

- [The manifest intentionally omits preserved `.txt`, `.csv`, and `.ico` files] -> Document that this is the exact roadmap extension contract, not a claim to cover every tracked byte.
- [The tool depends on locally available Git plumbing] -> Treat Git and the recorded commit as explicit prerequisites and fail without fetching.
- [A malformed batch stream could misalign binary reads] -> Parse byte counts exactly, require trailing separators, validate every response, and cover truncation/error cases.
- [A future selected symlink, gitlink, unsafe path, or case collision could be mishandled] -> Reject the entire operation before output rather than follow or omit it.
- [The 759 MB corpus makes repeated verification nontrivial] -> Stream one object at a time and avoid caches or parallel complexity in M0.
- [Canonical JSON can be altered by checkout policy] -> Pin only `legacy-manifest.json` to LF and verify canonical serialized bytes.

## Migration Plan

1. Add and test the generator/verifier without touching preserved inputs.
2. Generate `legacy-manifest.json` from the immutable tag and independently verify its count, representative entries, deterministic bytes, and containment.
3. Document commands, evidence, and limitations; add command guidance only after successful execution.
4. Roll back by removing the tool, tests, manifest, narrow attribute rule, and documentation additions. Original assets require no rollback because this change never modifies them.
