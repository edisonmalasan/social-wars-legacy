# Legacy Git-blob integrity manifest

`hash_manifest.py` is a Python 3.9 standard-library CLI requiring local Git and
the recorded commit's complete objects. It treats assets as opaque bytes, uses
one streamed `git cat-file --batch`, and never fetches, checks out, parses, or
executes preservation content. Git replacement objects and lazy fetching are
disabled, and Git transport protocols are denied for these commands. It has no
application imports or third-party dependencies.

## Verified commands

Run from the repository root with a working Python interpreter:

```text
python -B tools/hash-manifest/hash_manifest.py generate
python -B tools/hash-manifest/hash_manifest.py verify
python -B -m unittest discover -s tools/hash-manifest -p test_hash_manifest.py -v
```

The `python` command above denotes the actual interpreter selected for the run;
the Windows Store aliases and `py` launcher were not used successfully. On
2026-09-14 the commands were executed with this explicit PowerShell executable:

```powershell
& C:/Users/Edison/AppData/Local/Temp/socialwars-runtime-740419ee065f46eab323c20a2d601e6b/cpython/tools/python.exe -B tools/hash-manifest/hash_manifest.py generate
& C:/Users/Edison/AppData/Local/Temp/socialwars-runtime-740419ee065f46eab323c20a2d601e6b/cpython/tools/python.exe -B tools/hash-manifest/hash_manifest.py verify
& C:/Users/Edison/AppData/Local/Temp/socialwars-runtime-740419ee065f46eab323c20a2d601e6b/cpython/tools/python.exe -B -m unittest discover -s tools/hash-manifest -p test_hash_manifest.py -v
```

That disposable executable is CPython 3.9.13, Windows AMD64, with provenance in
[the baseline guide](../../docs/legacy-baseline.md#interpreter-provenance-and-host).
It is evidence of the verification host, not a required installation location.
`-B` prevents bytecode writes. Tests create only disposable synthetic repositories.

`generate` defaults to the repository containing the tool, ref `legacy-baseline`,
and root `legacy-manifest.json`. Use `--repo PATH`, `--ref REF`, and
`--output PATH` after `generate` for a disposable repository/output. It resolves
the commit once, constructs the entire result, and atomically replaces only the
output through a temporary file in its existing parent directory. It rejects
protected preservation/runtime input locations, tracked inputs other than the
manifest, and symlink outputs; failure retains an existing output.

`verify` accepts `--repo PATH` and `--manifest PATH`. It uses only the manifest's
full recorded commit and the fixed policy, rejects malformed schemas and
duplicate keys, and reconstructs canonical bytes without rewriting the manifest.
It makes no repository writes; Git batch stderr uses a transient system-temp
sink. Success exits **0**, a valid-schema integrity/canonical-byte mismatch exits
**1**, and invalid arguments, schema, source, Git, or I/O failures exit **2**.
Diagnostics do not print asset content. Unavailable sources fail locally.

## Corpus and canonical format

Policy `legacy-assets-v1` selects case-insensitive `.swf`, `.json`, `.xml`,
`.png`, `.jpg`, `.jpeg`, `.mp3`, `.wav`, and `.gif` suffixes across the entire
immutable tree. Selected entries must be regular blobs (`100644` or `100755`),
with safe UTF-8 repository-relative paths and no case-insensitive collisions.
Symlinks, gitlinks, unsafe/ambiguous paths, and empty selections fail closed.
Duplicate content at separate paths remains separate entries.

The [manifest](../../legacy-manifest.json) has fixed top-level keys
`schema_version`, `algorithm`, `source`, `policy`, `files`; version `1`, algorithm
`sha256`, source kind `git-blob`, and a full commit. Each exact-path-sorted entry
has `path`, lowercase `sha256`, and a non-negative integer `size`. Sizes and
digests describe raw Git-blob bytes, independent of worktree CRLF conversion.
Serialization is ASCII-escaped UTF-8 JSON, two-space indentation, no BOM, and
exactly one final LF. The root attribute rule applies only to the manifest.

## Executed acceptance evidence (2026-09-14)

- Source: `e8c98a03c902eba70323538dc5d4eaba2f2927a1` (`legacy-baseline`).
- Generated twice with identical bytes; read-only verification exited 0.
- Exactly **3,258 entries**, totaling **758,423,699 raw blob bytes**.
- Manifest SHA-256: `91b0983af443075506dcaa3188a51b45da30cf6cb299a6723c92b4a040b782fb`.
- All **11 focused tests** passed on CPython 3.9.13. They cover suffixes,
  exclusions, later/untracked files, binary and duplicate content, CRLF checkout,
  ordering/determinism, schema/tampering, unsupported entries, unsafe paths,
  batch truncation/protocol/process errors, unavailable refs, and containment.
- Independent `git ls-tree -r -z --full-tree` enumeration matched the complete
  path set. Independent `git show COMMIT:PATH` reads matched SHA-256 and sizes
  for the eight samples below, including each selected preservation root.
- Before/after worktree SHA-256 snapshots during repeat generation and verification
  matched for **3,279 existing preservation/input files**, including existing
  tool inputs and root runtime Python files. No Flash/browser content executed.
- `openspec validate build-legacy-asset-hash-manifest --strict` exited 0.

| Independently sampled path | Raw size | SHA-256 |
| --- | ---: | --- |
| `assets/flash/Basesec_1.4.10.swf` | 4,147,037 | `79c18e157f78db7e9c69340b08f205a79bfd05341b7bdf75b43d322ad199cd30` |
| `assets/characters_2/evil_1.swf` | 92,719 | `6895e6a43ef705aafe5ba309b2593366860a2a92ee4bd8f3d37c393772707ab7` |
| `config/auctionhouse.json` | 436 | `a8dc79616f5effe4e3eb4d56ab532a14e7eff32056e18438df88fd8781f6498e` |
| `villages/AcidCaos.json` | 88,708 | `c5b4e988e4628eac58b9aa72822882a249a06f75af5a4ff9ce9248cc7f9baaaf` |
| `mods/no_hiring_needed.json` | 4,621 | `916aeb76c494ff518ccc6181e8f18887bae63c44dea35ded81b368832e5e88bf` |
| `templates/avatars/acidcaos.png` | 9,099 | `e8ab7a979d78a030535072e854505313c85b17be78e74efa6ef6f165098c3582` |
| `stub/crossdomain.xml` | 219 | `6fdeeab18c672616d7b28473dee32cd55f2c2382222491234d83e5617bec7a83` |
| `tools/atom_fusion_excluded_units.json` | 1,116 | `0c4a522aa0a80f06d9b52688fd762760e85839f2dc2933ba9b0a04ffe1eea456` |

The independent harness is transient local evidence at
`C:/Users/Edison/AppData/Local/Temp/socialwars-manifest-evidence.py`;
this document retains its results. The coordinator owns final Git diff/status
checks, independent implementation verification, task acceptance, and PR lifecycle.

## Limits

This is integrity evidence for selected immutable Git blobs only. Nonmatching
extensions (including `.txt`, `.csv`, and `.ico`), ignored/untracked files,
later commits, mutable player saves, canonical save fixtures, packaged-release
bytes, live-worktree integrity, Git LFS retrieval, runtime/gameplay parity,
asset conversion, and provenance/rights classification are excluded. Historical
village JSON remains static preservation material, not canonical player-save
evidence. The manifest makes no distribution-rights or security-audit claim.
