## Why

The legacy `command.php` path mutates and persists player state without durable request-to-state evidence, so replacement work cannot yet prove what a command batch changed. Recording this highest-value mutation boundary now establishes behavior evidence before protocol cataloging, replay, or modern API work.

## What Changes

- Add an opt-in recorder for legacy `command.php` transactions that observes the parsed command batch and the complete player state immediately before and after legacy execution.
- Record request metadata, safe player/session correlation, response status and body, execution duration, and success or failure without changing legacy command or persistence semantics.
- Store records only in an explicitly configured, contained local evidence directory using a deterministic documented schema and atomic writes.
- Redact or omit authentication-bearing values, and prevent recorder output from becoming tracked canonical evidence without a separate review workflow.
- Add focused tests proving disabled-mode transparency, successful and failed transaction evidence, state-boundary accuracy, sensitive-value handling, and write containment.

## Capabilities

### New Capabilities

- `legacy-command-recording`: Opt-in, behavior-preserving evidence capture for the legacy `command.php` mutation boundary.

### Modified Capabilities

None.

## Impact

- Affected runtime boundary: the Flask `command.php` route in `server.py`, the `command()` mutation/persistence call, and player-state reads from `sessions.py`.
- New recorder code and focused tests will be isolated from the legacy domain logic and disabled unless explicitly configured.
- Recorder files are local diagnostic evidence, not committed fixtures; no dependency, protocol response, save format, command behavior, Flash path, or modern runtime changes are included.
