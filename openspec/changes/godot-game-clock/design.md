# Design

## Context

The M5 foundation so far: `GameApi` (typed `list_sessions()` / `get_bootstrap()` over `LegacyV0Api` or `FakeApi`), the Compatibility API v0 on loopback, the boot scene as main scene (session list → bootstrap → typed summary, explicit failure states), the `ContentRegistry` autoload, and the `Session` autoload. Every v0 envelope carries `server_time` — legacy `engine.timestamp_now()` epoch seconds, embedded in the original page as the `serverTime` FlashVar — and `BootData.SaveListResult` already parses it (FakeApi serves the fixture epoch), yet the client has no notion of game time. Roadmap §17 reserves `GameClock` as a cross-cutting autoload. Constraints: no new dependencies, loopback-only, pinned engine/interpreter, guard-verified read-only inputs — see proposal.md for motivation and the `godot-game-clock` delta for the behavior contract.

## Goals / Non-Goals

**Goals:**
- One autoload that owns game time: the response's server epoch committed once at boot, then advanced deterministically from local processed frames.
- Explicit, fail-closed anchor/clear and pause/advance lifecycles with observable transitions, so later systems subscribe instead of polling.
- The boot flow as the only this-change producer of the anchor: ready ⟹ anchored clock; failed boot ⟹ no anchor.
- The grown project scope enforced by the existing scope test (four autoloads, two new files, reduced forbidden list).

**Non-Goals:**
- No server-time re-sync, drift correction, skew handling, or periodic refresh; the anchor is committed once per boot attempt (a consumer that needs re-sync — economy timers — brings its own change).
- No transport, persistence, or Compatibility-API changes; GameClock never calls GameApi itself.
- No camera, UI foundation, Settings, or AudioManager work (later M5 items).
- No legacy command-level time semantics (`timestamp_now()` call sites, production/queue schedules) — only the client-side time source.

## Decisions

**D1 — Local frame-delta timebase anchored to the response epoch; no wall clock.** `scripts/game_clock.gd` extends `Node`; `now_epoch_sec()` = committed `server_time` + accumulated whole-millisecond processed-frame time. The autoload never reads wall-clock/calendar time (immune to system clock jumps, and testable), never performs transport, and preloads nothing. *Rationale:* reproduces the legacy embedding pattern — the page committed `serverTime=timestamp_now()` at load and the client's timers run locally from there — using the value the v0 envelope already delivers. *Alternatives:* `Time.get_unix_time_from_system()` as timebase (rejected — jumps, ignores the response, no deterministic control), proxying `server_time` per read without local advance (rejected — a stale constant cannot drive timers or observe progress).

**D2 — Two independent axes: anchoring and running.** Anchoring: unanchored ↔ anchored, changed only by `anchor()` (fail-closed) and `clear()`; startup is unanchored with a zero epoch, and anchoring zeroes the elapsed base. Running: running ↔ paused, changed only by `pause()` / `resume()`; startup is running. The axes do not interact — a clock can be paused while unanchored, and `anchor()` leaves the paused state untouched. *Rationale:* pausing and anchoring in one synchronous block yields an exactly known epoch (deterministic assertions), and each axis has its own transition signal.

**D3 — Fail-closed `anchor(server_time) -> {ok, error}` and `advance(msec) -> {ok, error}`.** Anchor validation: positive epoch, and unanchored (a second anchor is rejected until `clear()` re-bases — re-anchoring mid-run would silently jump every future timer base). Advance validation: positive count, and paused (a running advance cannot be exact). On failure the error names the violated condition and committed state is untouched, even mid-run. *Alternative:* replace-on-reanchor like `Session.activate` (rejected — session identity changes are legitimate replacements; clock time jumps are not; `clear()` is the explicit re-base path). The `{ok, error}` envelope follows `ContentRegistry.load_content()` / `Session.activate()` so callers handle failures uniformly.

**D4 — Four signals with strict emission rules.** `clock_anchored(server_time)` once per successful anchor; `clock_cleared` only on anchored → unanchored (repeated `clear()` silent); `clock_paused_changed(paused)` only on running ↔ paused transitions (repeated `pause()`/`resume()` silent); `clock_ticked(elapsed_msec)` on every actual advance — a processed frame that crosses a new whole millisecond, or a successful manual advance — with the payload equal to the committed elapsed time. Base resets (anchor/clear zeroing elapsed) are announced by their own transition signal, never by a tick, so tick payloads are strictly increasing within one base. Signals let later M5 systems (UI, timers) subscribe without polling; the spec pins this contract.

**D5 — Deterministic controls.** `_process(delta)` accumulates float milliseconds while running and emits a tick only when the integer payload advances (no duplicate payloads); while paused it does no work, so reported time is bit-stable across frames. `advance()` is the only way time moves while paused, and it moves by exactly the requested count. These rules are what the suite asserts — every "unchanged" or "exactly" claim is established by construction, not by timing luck.

**D6 — Boot integration points.** `_boot()` guards the new autoload (`gameclock_missing`, mirroring `session_missing`), clears any previous anchor on entry (next to `session.clear()`), and a successful bootstrap anchors the clock with `save_list.server_time` immediately before `Session.activate(...)`; if anchoring unexpectedly fails, the boot fails closed with `gameclock_anchor` instead of reaching ready. *Rationale:* ready ⟹ active session AND anchored clock become invariants; every failure path (unreachable, structured error, bad response) occurs before the anchor point, so failed boots leave the clock unanchored; clear-on-entry means a retry can never double-anchor.

**D7 — Suite wiring.** New `tests/test_game_clock.gd` joins `verify-boot.ps1`'s hermetic list as the sixth suite (bootstrap domain: scaffold lifecycle, then two in-process boot runs proving anchor-at-ready and clear-on-retry), and `test_boot_scene.gd` gains clock assertions at ready (anchored; epoch at or ahead of the fixture response timestamp and within a bounded post-anchor interval — time-dependent values asserted as flags and ranges per the field-stability time rule, never exact wall-epoch equality) and in both error scenarios (unanchored, zero epoch). *Alternative:* running it under `verify.ps1` (rejected — `verify.ps1` is the render/content battery; the clock belongs with the bootstrap verification, exactly as `godot-session` D7 recorded).

**D8 — No coupling beyond the boot write.** GameClock references no other autoload or script; boot is the only writer this change; nothing reads the clock yet (later systems consume the signals); `GameApi`, `Session`, `ContentRegistry`, and the compatibility fixtures are unchanged — `Session` does not read or depend on the clock, and activation order is anchor → activate.

**D9 — Scope contract growth and spec-boundary ownership.** `project.godot` autoload order: `GameApi`, `ContentRegistry`, `Session`, `GameClock`. `test_project_scope.gd`: `ALLOWED` += `scripts/game_clock.gd`, `tests/test_game_clock.gd`; `EXPECTED_AUTOLOADS` = those four lines in order; `FORBIDDEN` drops `"GameClock"` (count assertion 17 → 16) — dropping the token stops scanning it entirely, so the reference boundary becomes the file inventory itself (`ALLOWED` plus `project.godot`, where the autoload line must live); every other forbidden token (camera, UI foundation, legacy protocol, non-loopback transport) remains. Spec boundary: `first-render-in-godot` R1 is the single living allow-list statement and is MODIFIED here to the four-autoload boundary; the per-change containment requirements of earlier capabilities record their own change's boundary and remain historical (unchanged), as established by `godot-session` not modifying `godot-content-registry`.

## Risks / Trade-offs

- [Clock state persists across in-process boot attempts] → deliberate: `test_game_clock.gd` runs a successful boot then a failing boot in the same process precisely to prove clear-on-retry; each suite still runs in its own engine process.
- [`GameClock` token removal weakens the forbidden list] → the remaining 16 tokens still exclude every not-yet-built system and all legacy/transport primitives, and the file inventory (`ALLOWED`) still bounds where any reference can live: `GameClock` now appears only in allow-listed project files (`project.godot`, the boot script, the clock script, and the two suites) plus docs, while the token itself is no longer scanned.
- [Unexpected anchor failure at boot] → fail-closed path (`gameclock_anchor` error) keeps ready ⟹ anchored honest rather than silently degrading; `BootData` accepts `server_time >= 0` while the anchor requires positive, so the branch is theoretically reachable from a malformed-but-parsing envelope and is unit-covered by direct `anchor(0)` rejection — the boot failure branch exists for integrity, not expectation (same epistemic status as `session_activate`).
- [Time-dependent assertions flake] → every clock assertion is a flag, an exactly constructed value (synchronous pause+anchor, integer advance), or a bounded range; no assertion compares against wall time, matching the field-stability time rule.
- [Boot-report/evidence churn] → regenerated by the verification run and committed as `test:` with provenance noted; first-render evidence and all guarded bytes stay byte-identical (they are not inputs to this change).

## Migration Plan

Additive only — no state to migrate, no rollback beyond removing the autoload line and the two new files. No OpenSpec-unspecified behavior changes.

## Open Questions

None.
