# Design

## Context

See `proposal.md` for motivation and `specs/server-v1-authority-boundary/spec.md` for
requirements. What constrains the approach is three measured facts and one dependency
gap.

1. `command.py:40` applies an eight-slot client resource vector at dispatch and the
   `if cmd ==` chain opens at `:42`; `server.py:318-322` answers `{"result": "success"}`
   unconditionally. There is no refusal channel, and refusal could not reverse the delta
   even if one existed. Full record in `docs/legacy-m13-authority.md`.
2. The Compatibility API already refuses, but per route: 104 declared refusal constants
   across 24 routes, each deriving its own server-owned vector because the protocol gave
   the derivation nowhere central to live.
3. The route-coverage census (`tools/route-coverage/`) reports 24 of 63 legacy branches
   covered by a resolved line span and 39 with no resolved citation.
4. **Dependency gap:** the pinned runtime is Flask only. `fastapi`, `pydantic`,
   `sqlalchemy`, `alembic` and `uvicorn` are all **absent** from the pinned CPython
   3.9.13. `AGENTS.md` names FastAPI and Pydantic as the target server stack, so this
   is a real gap between the milestone's mandate and the environment, not an oversight.

Relevant non-constraints, both measured so the design does not re-litigate them:
`apps/compat-api/guard_baseline.py` guards file digests and the 3.9 interpreter only,
**not** the package set, and no test reads `requirements.txt`. Adding packages therefore
does not break an existing guard.

## Goals / Non-Goals

**Goals:**

- Build the authority boundary **once**, as a domain service, so the 39 uncited branches
  have a place to land that does not re-solve derivation per route.
- Make refusal a value the domain produces and the transport can only translate.
- Prove the boundary on one transaction against an oracle that already exists.
- Leave v0 byte-identical, so the milestone can proceed by replacing domains one at a
  time with a working surface behind it at every point.

**Non-Goals (design-level boundaries beyond the proposal's scope list):**

- No concurrency, transaction, or locking design. Storage stays single-writer filesystem
  JSON until M14, which owns that ground.
- No migration of v0 clients, routes, or tests.
- No shared code between v0 and v1 domain layers in this line. Sharing a derivation
  would couple the surface being replaced to the surface replacing it; the parity method
  is a comparison, not an import.

## Decisions

### D1 — Server v1 coexists with v0 and does not absorb it

**Rationale, measured:** the Compatibility API is **5,752,183 bytes / 122,022 lines**
(48 modules, 65 test files) across **24 routes**, against the **51,275 bytes / 1,572
lines** of the entire preserved legacy server it fronts — a ratio above **112×**. That
layer is not incidental scaffolding; it carries 3,077 tests and 21 executed-legacy
fixture captures, and it is the measurement instrument for every delivered line from M7
onward.

**Alternative considered — absorb and replace:** rewrite v1 as the only surface. Rejected:
it is the exact simultaneous-rewrite of client, backend, persistence and protocol that
`AGENTS.md` forbids, it converts a routing decision into a migration with no rollback
path, and it would throw away the fixture corpus that v1's own parity method needs.

**Retirement path:** v0 domains retire individually, in later lines, only once v1 has
demonstrated parity for that domain against the existing captured fixtures.

### D2 — The authority boundary is a domain service, not route middleware

The economy authority and the refusal type live in the domain layer. A route adapts a
request into an intent, calls the domain, and translates the returned outcome — success
with derived deltas, or a typed refusal — into HTTP. The route has no arithmetic.

**Alternative considered — a shared route helper or FastAPI dependency.** Rejected: both
keep the decision reachable from transport, which is how v0 ended up with 24 derivations.
A dependency that injects a service still leaves the *decision* in the handler if the
handler is the one calling it. The invariant enforced instead is a test asserting the
domain owns derivation exactly once, not a convention.

### D3 — A request carrying a resource delta is refused, not clamped and not ignored

**Rationale:** the preserved server applies the client's delta and clamps each slot at
zero. Clamping reproduces the anti-pattern under new names. Silently ignoring the field
is worse: it is indistinguishable from a working feature, and it produces a response that
looks like success while the client believes it paid a different amount.

**Alternative considered — accept and discard.** Rejected for the reason above.

### D4 — FastAPI and Pydantic are added to the pinned runtime; SQLAlchemy and Alembic are not

**Rationale:** `AGENTS.md` names FastAPI and Pydantic as the target server stack, and a
typed request/response boundary is exactly what D2 depends on. Feasibility was checked
rather than assumed: `fastapi` resolves and downloads on the pinned interpreter
(`fastapi-0.128.8-py3-none-any.whl`), and no existing guard reads the package set.

SQLAlchemy and Alembic are **deferred to M14**, which owns PostgreSQL, the schema, and
migrations. Adding an ORM now would mean adding a database abstraction with no database
behind it — the seam is created by D5 instead.

**Consequence that must not be skipped:** `docs/legacy-baseline.md` records the pinned
runtime with its verification evidence. The Apply stage extends that record with the new
versions' evidence; it does **not** edit the existing entries.

### D5 — v1 persists through the committed filesystem JSON, behind a repository seam

**Rationale:** PostgreSQL is M14. v1 must therefore read and write the same committed
save document shape to be comparable against the corpus and against v0's fixtures. The
seam — a repository interface the domain depends on, with a filesystem implementation —
is what makes M14 a substitution rather than a rewrite, and it costs nothing now.

Unknown fields are preserved on every read/write, per the spec requirement; `legacy_extra`
discipline applies to anything v1 does not model.

### D6 — `collect` is the first vertical slice

**Rationale:** v0's collection is already proven against a captured executed-legacy
fixture, so v1's first slice is measured against an **existing oracle** rather than a
newly captured one, and the two surfaces become directly comparable. It also exercises
all three boundary properties at once — a derived payout, named refusals, and a
post-execution proof that the store moved by exactly the derived amount.

**Alternatives considered:** `expand` (a debit, also proven) — nearly as good, chosen
against. `add_xp_unit` — rejected, because the amount is entirely client-supplied and
unvalidated in the preserved branch, so there is no committed content from which a v1
amount could be *derived*; porting it would either reproduce the anti-pattern or invent
a schedule, and inventing an economy is out of scope for this line.

### D7 — v1 listens on its own loopback port

A port distinct from the legacy 5055 and the Compatibility API's 5056. The containment
harness already asserts those two are free; v1 needs its own assertion so a test can
prove v1's port was released and its disposable corpus removed. Four recorded flaky
surfaces already exist around port assertions, so v1's containment assertion is written
to be re-runnable rather than trusted once.

### D8 — `ServerV1Api` is a third `GameApi` implementation

The facade is already the client's only network path, so adding v1 is registering a
third implementation behind the existing interface, with no gameplay code touched. This
closes the gap PR #381 recorded: the facade currently declares only `IMPL_FAKE` and
`IMPL_LEGACY_V0`.

**Non-goal within D8:** this line does not switch any delivered gameplay capability to
v1. `collect`'s client flow continues to run against v0; v1 is reachable and proven, not
adopted.

## Risks / Trade-offs

- **[v1 re-inflates toward the 112× ratio]** → The boundary is specified once and the
  test suite asserts the domain owns derivation in one place. A second derivation
  appearing is a test failure, not a code-review opinion.
- **[v0 and v1 drift, and the fixture corpus stops being a shared oracle]** → v1's first
  slice is compared against v0's captured fixture, establishing the parity method while
  the surface is one transaction wide rather than after it is 24 routes wide.
- **[Adding packages perturbs a preservation-pinned runtime]** → `guard_baseline.py` does
  not read the package set and no test reads `requirements.txt`, both measured. The
  baseline record is extended with new evidence in Apply, never rewritten in place.
- **[Refusing client deltas makes v1 incompatible with a v0-era client]** → Intended, and
  stated: v1 is not a drop-in for the preserved protocol. This is one more reason D1
  keeps v0 serving.
- **[Four flaky surfaces already open]** → Two are port assertions and one is a
  display-sensitive windowed capture. This line adds a fifth port assertion, so
  containment must be re-runnable and re-run before any failure is called a regression.
- **[The 39 uncited branches now look implementable and get ported in bulk]** → Explicitly
  out of scope. The boundary is what this line builds; the census is what schedules the
  rest, and a citation is not a capability.

## Migration Plan

Not applicable in the deployment sense: no existing surface is replaced, and v0 continues
to serve unchanged. The rollback is deletion of `apps/server-v1/` and one facade
registration.

## Open Questions

- Whether v1's refusal vocabulary should be a fresh set or a curated subset of the
  Compatibility API's 104 constants. Deferrable: it changes naming and reuse, not the
  requirement that refusal is a typed domain decision reaching the client.
- Whether the repository seam in D5 should be a Protocol or an ABC. Deferrable, and
  settled by whatever the first implementation naturally wants.
