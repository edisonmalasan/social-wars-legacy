# Design

## Context

The M5 foundation so far: `GameApi` (typed `list_sessions()` / `get_bootstrap()` over `LegacyV0Api` or `FakeApi`), the Compatibility API v0 on loopback, the boot scene as main scene (session list → bootstrap → typed summary, explicit failure states), and the `ContentRegistry` autoload. The boot scene keeps `boot_user_id` and `summary` as scene-local state; nothing else can observe the active session. Roadmap §17 reserves `Session` as a cross-cutting autoload. Constraints: no new dependencies, loopback-only, pinned engine/interpreter, guard-verified read-only inputs — see proposal.md for motivation and the `godot-session` delta for the behavior contract.

## Goals / Non-Goals

**Goals:**
- One autoload that owns "which session is active" with an explicit, fail-closed lifecycle and observable transitions.
- The boot flow as the first (and only this change) producer of session state: ready ⟹ session active with the bootstrapped save; failed boot ⟹ no session.
- The grown project scope enforced by the existing scope test (three autoloads, two new files, reduced forbidden list).

**Non-Goals:**
- No session switching UI, login flows, save selection UI, or multi-session concurrency.
- No transport, persistence, re-bootstrap, or Compatibility-API changes; Session never calls GameApi itself.
- No GameClock, camera, UI foundation, Settings, or AudioManager work (later M5 items).
- No new typed payloads: the summary type already exists.

## Decisions

**D1 — Pure state holder, no transport.** `scripts/session.gd` extends `Node`, references only `boot_data.gd` types, and exposes `activate` / `clear` / getters / signals. The boot scene mediates every GameApi call and then commits the result. *Alternative:* Session owning bootstrap itself (rejected — duplicates GameApi's role, couples a cross-cutting holder to transport, and would rewrite the verified boot flow).

**D2 — Reuse `BootData.PlayerSummary`.** Activation takes the typed summary the boot scene already derives from `BootstrapResult`. *Alternatives:* a new `SessionInfo` type (rejected — duplicates name/level/xp/user_id), storing the raw envelope or whole `BootstrapResult` (rejected — leaks config/player_info payloads into a holder that only needs identity).

**D3 — Fail-closed `activate(user_id, summary) -> {ok, error}`.** Validation: non-empty `user_id`, non-null summary, `summary.user_id == user_id`. On failure the error names the violated condition and committed state is untouched (even mid-session). Re-activation while active is allowed and replaces the committed session. *Alternative:* silent coercion or asserting (rejected — the fail-closed `{ok, error}` convention is established by `load_content` / `resolve_asset`, and asserts crash the client). This mirrors `ContentRegistry.load_content`'s envelope so callers handle failures uniformly.

**D4 — Transition signals `session_activated(user_id)` / `session_cleared`.** Each successful activation emits once (observers learn "a session is now active as X"); `session_cleared` emits only on active → inactive, so a repeated `clear()` is silent. Signals let later M5 systems (UI, clock) subscribe without polling; the spec pins this contract so observers can rely on it.

**D5 — No implicit session at startup.** The scaffold starts inactive; only a successful boot activates it. This mirrors the ContentRegistry no-implicit-load contract and makes `is_active()` at startup a testable invariant.

**D6 — Boot integration points.** `_boot()` clears the session on entry (every attempt starts from a known state), and a successful bootstrap calls `Session.activate(boot_user_id, summary)` immediately before `_complete()`; if activation unexpectedly fails, the boot fails closed with `session_activate` instead of reaching ready. *Rationale:* ready ⟹ active session becomes an invariant, and failure paths (unreachable, structured error, bad response) can never leave a stale session.

**D7 — Suite wiring.** New `tests/test_session.gd` joins `verify-boot.ps1`'s hermetic list (bootstrap domain: scaffold lifecycle, then two in-process boot runs proving activation and replacement), and `test_boot_scene.gd` gains session assertions at ready and in both error scenarios. *Alternative:* running it under `verify.ps1` (rejected — `verify.ps1` is the render/content battery; Session belongs with the bootstrap verification, and `verify-boot.ps1` already owns boot-report provenance).

**D8 — Scope contract growth.** `project.godot` autoload order: `GameApi`, `ContentRegistry`, `Session`. `test_project_scope.gd`: `ALLOWED` += `scripts/session.gd`, `tests/test_session.gd`; `EXPECTED_AUTOLOADS` = those three lines in order; `FORBIDDEN` drops `"Session"` (count assertion 18 → 17) — the token scan is content-based, so `Session` references confined to the two allow-listed files plus `project.godot` are exactly what the new boundary permits; every other forbidden token (GameClock, camera, UI foundation, legacy protocol, non-loopback transport) remains. Boot-report churn from the new suite is committed as a `test:` commit per established convention.

## Risks / Trade-offs

- [Session state persists across scenes within one test process] → deliberate: `test_session.gd` runs a successful boot then a failing boot in the same process precisely to prove clear-before-attempt; each suite still runs in its own engine process.
- [`Session` token removal weakens the forbidden list] → the remaining 17 tokens still exclude every not-yet-built system and all legacy/transport primitives; allow-listing bounds `Session` references to three declared files.
- [Unexpected `activate` failure at boot] → fail-closed path (`session_activate` error) keeps ready ⟹ active honest rather than silently degrading; validation only rejects inputs derived from an already-validated response, so it should be unreachable in practice — the failure branch exists for integrity, not expectation.
- [Boot-report/evidence churn] → regenerated by the verification run and committed as `test:` with provenance noted; first-render evidence and all guarded bytes stay byte-identical (they are not inputs to this change).

## Migration Plan

Additive only — no state to migrate, no rollback beyond removing the autoload line and the two new files. No OpenSpec-unspecified behavior changes.

## Open Questions

None.
