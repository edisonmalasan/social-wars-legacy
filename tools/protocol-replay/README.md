# Contained legacy command replay

This offline tool replays one explicitly supplied recorder-v1 transaction using
the preserved dispatcher. It imports no legacy code in the parent, discovers no
records or saves, and emits private, value-free comparison evidence. It does not
capture, promote, or modify fixtures.

## Environment and executed checks

The required runtime is Windows x64 CPython **3.9.13**, with the pinned source
runtime packages already installed. Git and the local preservation baseline
objects must be available; there is no fetch or dependency installation. The
parent uses its own `sys.executable` for the child. Other interpreter targets
are rejected rather than treated as verified.

The focused command, executed from the repository root, is:

```text
python -B -m unittest discover -s tools/protocol-replay -p test_protocol_replay.py -v
```

`python` denotes this selected executable, not the Windows Store alias:

```text
C:/Users/Edison/AppData/Local/Temp/socialwars-runtime-740419ee065f46eab323c20a2d601e6b/verify-one/Scripts/python.exe
```

Interpreter verification on 2026-09-15 returned CPython 3.9.13, AMD64, 64 bits.
See [baseline provenance](../../docs/legacy-baseline.md). The interpreter path is
transient local verification evidence, not a dependency to hardcode.

The final focused discovery run on 2026-09-15 exited 0: **32 tests passed**,
with no skips, in 139.405 seconds. With the same executable, the existing
command-recorder suite passed 13 tests in 1.118 seconds and the state-diff suite
passed 29 tests in 41.237 seconds. These are focused controlled preservation
checks; broader OpenSpec lifecycle verification belongs to the coordinator.

On 2026-09-17 the root repeated replay (32 tests), recorder (13), state-diff
(29), and hash-manifest (11) suites successfully, verified all 3,258 manifest
entries, and passed package consistency and strict OpenSpec validation. Orca
implementation task `task_f4cd12c944d7` reported no repairs necessary. Independent
verification task `task_b997b10ca3e6` / dispatch `ctx_2c7c034e9a5c` passed the
32-test replay suite in 151.085 seconds and independently exercised real
recorder-produced success and command-phase `IndexError` records through the
replay CLI, including repeat reports and mismatch/error exits.

No dedicated OpenSpec verification command or skill was exposed by the installed
tooling. The user authorized strict validation, independent verification,
required checks, and final diff review as the fallback completion gate. The
verifier also disclosed two mistaken in-checkout compileall runs that generated
bytecode. Those files were removed; root found no remaining cache files and the
verifier reported unchanged source bytes. This remediated verification-process
warning is not replay containment evidence and is non-blocking under the user's
instruction. No gameplay or historical progressed-player parity is implied.

The CLI takes `replay --record` followed by exactly one existing regular UTF-8
JSON filename. The focused tests execute that CLI against disposable controlled
records, including via a parent subprocess. Use `-B` for the parent invocation;
the child always receives `-I -B`. Neither a sample-record generator, report-file
option, directory discovery, nor batch catalog is provided. Shell redirection
is an operator action outside tool containment.

## Eligible evidence

Records follow the [recorder schema](../../docs/legacy-command-recording.md).
Schema version must be exact integer `1`; `true` and `1.0` are invalid. Method
must be POST and path must be `/dynamic/menvswomen/srvsexwars/command.php`.
Both boundaries must be available complete objects. Correlation `player_id`
must be a nonempty unredacted string equal to each boundary's `playerInfo.pid`.
No HTTP credentials, signature, authentication, or session are reconstructed.

The object envelope must contain the original dispatcher's `first_number`,
`publishActions`, `ts`, `tries`, `accessToken`, and `commands` members. The first
five are read but do not affect these branches; a recorder-redacted access
token is therefore valid. Unknown non-execution metadata and state fields are
accepted, bounded, inspected for known secrets, and retained without migration.

Every command is exactly `[map_index, name, arguments, resource_deltas]`:

| Name | Arguments |
| --- | --- |
| `complete_tutorial` | Exactly one non-boolean integer tutorial step |
| `level_up` | Exactly one non-boolean integer level |
| `ping` | Empty array |
| `set_variables` | Empty array |

An empty `level_up` argument array is eligible only for a command-phase failure
record with exception type `IndexError`. Every command, including trailing
commands after that failure, must be eligible. Map indexes are in-range
non-boolean integers addressing before-state maps. Deltas are exactly eight
finite, non-boolean JSON numbers, in legacy order: unused, XP, gold, wood, oil,
steel, cash, mana. Resource inputs touched by execution must also be finite
non-boolean numbers. Negative deltas and levels are reproduced without gameplay
rebalancing. Redaction placeholders in command tuples, consumed state fields,
or player correlation are rejected. Redacted unknown state fields remain
sanitized evidence, not recovered original values.

A success record requires null `error`, status 200, and body
`{"result": "success"}`. The sole supported failure requires command phase,
`IndexError`, recorder's fixed safe error message, status 500, and null body.
Parse-phase, snapshot/response failures, unavailable boundaries, unsupported
commands, and incoherent metadata are rejected before any legacy execution.
Unknown response-envelope metadata does not alter the response contract.

## Oracle and containment

[oracle-manifest.json](oracle-manifest.json) pins 16 UTF-8 textual inputs,
totaling 1,956,489 immutable Git-blob bytes, to baseline
`e8c98a03c902eba70323538dc5d4eaba2f2927a1`. The reviewed import closure is
`bundle.py`, `command.py`, `constants.py`, `engine.py`, `get_game_config.py`,
`sessions.py`, and `version.py`. Import-time content is `config/main.json`,
`config/patch/patches.txt`, its five configured JSON patches, `mods/mods.txt`,
and `villages/initial.json`. No mod is enabled by the pinned mod list, so the
unused `no_hiring_needed.json` is excluded. No SWF, server, recorder, runtime
save, or surrounding asset tree is copied.

The parent verifies manifest membership, baseline path-to-blob identity, blob
size and Git object digest, and checkout bytes before copying. Only CRLF/LF
conversion is tolerated; other whitespace or content differences fail. Missing
files, symlinks, directory junctions/reparse points, hardlinks, extra manifest
members, and configured-list drift fail. Local Git uses no replacement objects,
global/system configuration, filesystem monitor, network protocol, lazy fetch,
or interactive prompting. Bytes are copied from the checked read, avoiding a
second checkout read after verification. This pins the executed oracle; it
cannot attest to the historical source used by an unproven record.

External storage is created below the resolved Windows system temporary root,
checked against the repository before creation. TMP/TEMP overrides are ignored.
The isolated child receives only SystemRoot/WINDIR environment entries, starts
with bytecode disabled, and explicitly inserts only the copied oracle root into
its import path. Installed dependencies and interpreter files are still read.
The child suppresses legacy stdout/stderr with nonaccumulating sinks, seeds
`sessions.__saves` directly from before-state, uses fixed alias `replay-player`
for the save filename without altering state IDs, redirects `sessions.SAVES_DIR`,
and replaces the dispatcher-visible clock with a child-only sentinel.

No `server.py` or recorder import, save loader, state migration, listener,
network connection, browser, subprocess service, or Flash runtime is needed.
Child audit guards reject server/recorder imports, socket/service/browser launch
operations, writes outside disposable storage, and reads of ambient save names.
The child is killed and reaped on timeout or oversized pipe output; its output
pipe is closed. Handled storage cleanup completes before report emission.

This is process and storage containment, **not an OS security sandbox**. It
assumes operator-controlled tool/dependency code and an unchanged filesystem
during checks. Hostile filesystem races, compromised installed packages, forced
parent termination, power loss, and unremovable temporary storage are not
guaranteed recoverable. Cleanup failure returns exit 2 and no report; the tool
does not claim cleanup succeeded when the OS refuses removal. Private evidence
and temporary storage should be protected by local operator permissions.

## Boundaries, comparison, and reports

The original `command()` applies each command's deltas before its branch,
clamps resource balances at zero, preserves order, and saves once after success.
`complete_tutorial` marks completion at step 15 or steps at least 25; `level_up`
assigns the supplied map level. `ping` and `set_variables` still apply deltas.
The unused delta remains unused. The sentinel call does not affect these states;
focused tests compare both successful and partial-failure results under two
sentinels. This is not reconstruction of recorded wall-clock inputs.

A supported `IndexError` preserves all earlier in-memory mutations and the
failing command's resource application, suppresses trailing commands, produces
the normalized failure response, and creates no save. No rollback is added.
Success must create exactly one disposable save equal to complete replay memory;
missing, malformed, extra, oversized, or inconsistent persistence is an execution
failure. This checks disposable replay persistence only. A recorded failure's
after-state is memory and provides no historical disk-persistence assertion.

The parent reuses [state-diff](../state-diff/README.md)'s existing core and
`structural-json-types-v1` policy, with expected recorded after-state as the
comparison's before-side and actual replay memory as its after-side. All fields,
unknown subtrees, strict scalar types, exact keys, array positions, and RFC 6901
paths participate. There are no ignore rules or domain normalization. Known
sensitive values are collected from the complete input record and actual child
result before paths are protected; known recorded/actual player IDs are protected
too. Colliding protected changes fail explicitly.

A completed replay emits exactly one JSON object with `schema_version: 1`,
`policy: "legacy-command-replay-v1"`, `replay: "match"` or `"different"`, nested
`state` following the durable state-diff schema, and `outcome`, `response`, and
`persistence` each `"equal"` or `"different"`. It contains no command arguments,
deltas, payload or state values, response/error text, player IDs, filenames,
source paths or hashes, clocks, durations, random identifiers, machine metadata,
or legacy prints. Serialization uses sorted keys, two-space indentation,
ASCII-escaped UTF-8, LF endings, and one final newline. Repeated unchanged inputs
produce byte-identical output.

| Exit | Meaning |
| --- | --- |
| `0` | Complete state, outcome, response, and disposable persistence match |
| `1` | Execution completed; at least one comparison differs |
| `2` | No trustworthy comparison completed; fixed bounded stderr category |

Invalid/unavailable/unsupported input, provenance drift, limits, protected-path
ambiguity, child/dependency/legacy failure, persistence inconsistency, cleanup,
serialization, and output failure emit no successful report. Serialization
finishes before stdout begins. A failed downstream pipe can already have
received a prefix or a complete document before flush fails; exit 2 remains
authoritative. Broken stderr cannot guarantee diagnostic visibility. No report
is written into the repository by the tool.

Limits are 16 MiB input, 128 container levels, 1,000,000 visited JSON nodes,
100,000 structural changes, 256 positional commands, 32 MiB child result data,
and 30 seconds child wall time. Core inspection counts nodes across supplied
roots, including metadata and the actual result's persisted copy. Oversized or
ambiguous evidence is rejected, never truncated into a match.

## Evidence classification and limits

The suite builds controlled transactions from the complete fresh-player fixture
and the command shapes exercised by recorder tests. They are not authentic
historical or progressed-player observations. It checks success/difference,
partial failure, both sentinels, resource ordering/clamping, persistence,
strict eligibility and JSON, provenance adversaries, secret paths, process and
storage failures, deterministic sinks, and byte containment. Full repository
content is hashed before and after the suite (Git internal storage excluded);
sources, fixtures, supplied evidence, and surrounding sentinel files are also
checked around each test. Directory checks detect added cache or other storage.
Every created replay directory is tracked and checked for actual removal.
Failure probes alter only disposable/test-injected oracle bytes, never the
preserved files. Timeout/pipe probes use reduced limits to check the same
termination mechanism without repeatedly waiting 30 seconds.

Reports remain private: path names can contain unknown personal data or secrets
that known-key collection does not identify. Recorder sanitization is lossy and
cannot reconstruct original credentials or values. A matching report verifies
only this sanitized controlled boundary under this pinned execution source.
Clock-dependent and all other commands, generalized persistence parity, raw
HTTP/Flask error-page parity, authentication/signature behavior, authentic
progressed-player coverage, gameplay parity, command catalogs, modern APIs,
Godot, database migration, and Flash execution remain unavailable or unverified.
