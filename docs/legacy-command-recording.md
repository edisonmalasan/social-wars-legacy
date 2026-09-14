# Legacy command transaction recording

Recording observes only the `command.php` route and is disabled when
`SOCIALWARS_COMMAND_RECORD_DIR` is absent or empty. It changes no command,
signature validation, persistence, response, or exception behavior.

## Enablement and verified commands

Run from the repository root using the Windows x64 CPython 3.9.13 environment
described in the [legacy baseline](legacy-baseline.md). The executable used on
2026-09-14 was:

```text
C:\Users\Edison\AppData\Local\Temp\socialwars-runtime-740419ee065f46eab323c20a2d601e6b\verify-one\Scripts\python.exe
```

The following PowerShell setting and focused test command were executed
successfully with that interpreter (`python` means the selected working
interpreter, without activation or new dependencies):

```powershell
$env:SOCIALWARS_COMMAND_RECORD_DIR = Join-Path $env:TEMP 'socialwars-command-records-verification'
python -B -m unittest discover -s tests -p test_legacy_command_recorder.py -v
```

The tests override the setting for each case, capture into disposable external
directories, and redirect actual legacy save persistence there. They compile
the actual route body without importing `server.py` and its startup loaders,
then exercise it with Flask request contexts and its test client, the real
command dispatcher, and the complete controlled
[fresh-player fixture](../tests/saves/fresh-player.json). No listening server,
network request, browser, or Flash execution is involved. The junction boundary
test uses Windows `mklink /J` in temporary storage and removes only that junction.
This is controlled transaction evidence, not gameplay parity or historical
player observation. Remove the environment setting to disable capture.

For an operator-run source server, the same setting enables observation when
using the existing `python server.py` entry point. This change's checks did not
launch that entry point or execute real player requests.

Destinations must be absolute, resolve outside the checkout, and be directories
or nonexistent directory paths. Checkout descendants, the checkout itself,
its ancestors, files, and links resolving into the checkout are rejected.
Validation runs before observation and again before persistence. Use a dedicated
operator-controlled directory; do not allow other processes to change its path
or ancestors while recording. The recorder is not an OS sandbox against hostile
filesystem races. Missing directories are created only during persistence.

## Schema version 1

Each UTF-8 JSON file has sorted keys, two-space indentation, ASCII escapes,
LF line endings, and a final newline. Fields are:

| Field | Meaning |
| --- | --- |
| `schema_version` | Integer `1` |
| `record_id` | Unique random UUID hex correlation for this observation |
| `observed_at` | UTC ISO timestamp at record construction |
| `request` | Method, route path, and allowlisted headers |
| `correlation` | `player_id`; no session identifier because this route uses none |
| `commands` | Complete parsed command payload, sanitized; null if parsing failed |
| `before`, `after` | Complete deep-copied player states, sanitized; null if unavailable |
| `response` | Status and returned route body; body null when the route raised |
| `outcome` | `success` or `failure` |
| `duration_seconds` | Legacy execution duration excluding evidence persistence |
| `error` | Null on success; bounded exception type, phase, and fixed safe text on failure |

Before is captured immediately before `command()`, after immediately following
its return or exception. On parse failure the available current state is copied
into both boundaries because command execution never began. Parse-failure
duration covers parsing; successful command duration starts after the before
snapshot and ends before the after snapshot. The after state is in-memory state:
a failed batch can partially mutate it without saving. No disk-save reread or
transaction correction is performed. Exceptions record their HTTP code when
available, otherwise 500; Flask generates any eventual error page outside this
boundary, so it is not a captured body.

Files use independent random UUID names. Exclusive same-directory `.claim`
files reserve names, retrying existing evidence and concurrent claims. A unique
same-directory `.tmp` is flushed and fsynced before `os.replace()` publishes
the complete JSON. Normal completion and handled failures clean temporary and
claim files. Abrupt process termination can leave those files or no evidence;
directory metadata durability after power loss is not promised. No prior record
is overwritten by cooperating recorder writers, including repeated record IDs.

## Sanitization and failure semantics

The raw signed `data` form field is never included. Form metadata and cookies
are omitted, as are authorization headers. Only `Content-Type`, `Content-Length`,
and `Accept` headers are considered. Recursive sanitization applies to parsed
payload, complete state, correlation, and all record fields. Key matching is
case-insensitive and ignores punctuation: `user_key`, `accessToken`,
`authorization`, `proxyAuthorization`, `cookie`, `cookies`, `setCookie`,
`signature`, `data_hash`, `password`, `secret`, `token`, `session_id`, and
`api_key` values become `[REDACTED]`. Known string secrets from those fields,
all cookie values, authorization headers, and the signature prefix are also
replaced wherever they recur in strings, including dictionary keys. Sanitization
happens before JSON serialization. Unknown legacy fields otherwise remain.

Exception messages and tracebacks are omitted, with fixed diagnostic text and
an exception class name limited to 80 characters. Recorder configuration,
snapshot, construction, serialization, and persistence failures emit a warning
that names the failed phase and asks the operator to check the external
destination/configuration; payloads, secret values, exception text, and paths
are never printed by recorder diagnostics. Logging failure falls back to
stderr. If both diagnostics fail, the original legacy result or exception still
wins; visibility cannot be guaranteed when both sinks are broken.

Records retain player-associated state and are private local diagnostic evidence.
Known-key redaction does not identify every personal datum or arbitrary secret
under an unknown key, nor encoded secrets. Review records before sharing or
promoting them to canonical fixtures; nothing automatically commits them.
Capture adds snapshot and I/O cost and can miss evidence after process exits.

Other routes, replay, generalized state diff, endpoint/command catalogs,
dependency changes, signature/security remediation, save migrations, and modern
API/client work are explicitly excluded.

## Executed focused evidence (2026-09-14)

The final discovery run exited 0: **13 tests passed**, with no skips, in
0.973 seconds on CPython 3.9.13 Windows AMD64. Checks include complete states,
unknown-field retention, secret exclusion, disabled/enabled response and exact
save-byte parity, partial mutation with the real dispatcher on failure, HTTP
200/400 behavior, three parsing failures, forced snapshot/sanitization/write
failures, logging/stderr failures, unsafe paths and a repository junction,
10 serial writes, 20 concurrent writes, a forced filename collision, atomic
publication, and handled-failure cleanup. These are focused observation tests;
the coordinator owns broader preservation checks and OpenSpec acceptance.
