# Proposal

## Why

The preserved protocol has **no way to say no**, and it applies the client's numbers
before it knows which command is arriving. `command.py:40` runs `apply_resources` for
every entry of the client-supplied batch, and the `if cmd ==` dispatch chain does not
open until `command.py:42`; `server.py:318-322` then returns `{"result": "success"}`
unconditionally, so a branch's only way to decline is to print a log line and return,
after the delta has already landed. This is measured, not suspected, in
`docs/legacy-m13-authority.md` across all **63** named branches.

The modern side already knows how to refuse, and has paid for that knowledge 24 times:
`apps/compat-api` declares **104** refusal constants and derives a server-owned
resource vector independently in every `/v0` route, because the protocol gave that
derivation nowhere central to live. That per-route re-solve is the cost of the
preserved shape, and it is the shape Server v1 must not inherit.

So the first Server v1 line is not a new endpoint. It is the **authority boundary
itself**, built once at the domain level, with the refusal channel and the
server-derived resource path as domain services rather than as something each route
re-solves. The route-coverage census merged in PR #379 is what makes this urgent
rather than merely next: **39 of 63 legacy branches have no modern route behind them
at all**, and without a shared authority boundary there is no architecture for them to
land in — only 24 more copies of the same derivation.

## What Changes

- **New `apps/server-v1/` FastAPI application**, the first modern server surface. It
  coexists with the Compatibility API and does not replace it.
- **A domain-level economy authority** that derives every resource movement from
  player intent. No v1 request shape may carry a resource, experience, health, or
  result delta; a request that attempts to is refused, not clamped.
- **A typed refusal channel** returned by the domain and translated to HTTP by the
  route layer, so refusal is a value the domain decides rather than a status code each
  route invents.
- **`collect` implemented end to end as the first vertical slice**, with a
  post-execution proof that every stored resource moved by exactly the derived amount
  and that a refusal moves nothing.
- **`ServerV1Api` registered as a third `GameApi` implementation**, closing the gap
  recorded in PR #381: `game_api.gd` currently declares only `IMPL_FAKE` and
  `IMPL_LEGACY_V0`, so the switch that would select v1 does not exist.
- **The Compatibility API is untouched.** No v0 route changes behaviour, no v0 test
  changes, and no v0 client capability is re-pointed at v1 by this line.

### Explicit non-goals

- **No PostgreSQL.** That is M14. v1 persists through the same filesystem JSON save
  document shape, preserving unknown fields.
- **No absorption of the Compatibility API.** See the proposal's design record; the
  measured ratio is 5,752,183 bytes and 122,022 lines of v0 against 51,275 bytes and
  1,572 lines for the entire preserved legacy server it fronts.
- **No client-visible visual change**, and no windowed capture.
- **No coverage claim for the 39 uncited branches.** This line builds the boundary they
  would land in; it does not convert them.

## Capabilities

### New Capabilities

- `server-v1-authority-boundary`: the server-authoritative resource and refusal model
  for Server v1 — that resource movement is derived server-side from intent, that
  refusal is a typed domain decision with a channel to reach the client, and that one
  transaction (`collect`) demonstrates both end to end.

### Modified Capabilities

None. `godot-building-collect` and every other delivered capability describe v0's
behaviour, which this line does not change. v0 and v1 are separate surfaces with
separate requirements, and merging them under one capability is the near-duplicate the
capability inventory exists to prevent.

## Impact

- **New:** `apps/server-v1/` (application, domain services, tests).
- **New:** `apps/client-godot/scripts/gameapi/server_v1_api.gd`, registered behind the
  existing `GameApi` autoload. Because the autoload is already the client's only
  network path, this adds an implementation without touching gameplay code.
- **Unchanged:** `apps/compat-api/**`, all 63 legacy branches, `command.py`,
  `engine.py`, `server.py`, `config/`, every committed save and fixture, the
  conversion packages, and the preservation manifest.
- **Constraint carried forward:** execution stays on loopback under the pinned
  CPython 3.9.13 with existing locked dependencies and no new packages.
- **Evidence precedent reused:** v1's `collect` is compared against v0's
  already-captured executed-legacy fixture rather than against a new oracle, and the
  post-execution proof follows the established two-part form.
