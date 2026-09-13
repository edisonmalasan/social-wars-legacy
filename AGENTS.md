# AGENTS.md

## Project overview

Social Wars is a preservation-first reconstruction of the original Flash game into a modern, Flash-free client/server application.

The existing Flask/Flash implementation is the reference implementation, behavioral oracle, protocol specification, save corpus, content source, and asset archive. The migration path is legacy Flask/JSON → Godot + Compatibility API v0 → authoritative Python API v1 + PostgreSQL.

Do not treat the legacy repository as disposable code.

## Stack

- Legacy server: Python + Flask
- Legacy storage: JSON save files
- Legacy client: Flash/SWF — reference only; must be retired from modern runtime
- Modern client: Godot 4.x + GDScript `[exact Godot version must be pinned before M5]`
- Compatibility layer: Python
- Target server: Python + FastAPI + Pydantic + SQLAlchemy + Alembic
- Target database: PostgreSQL
- Specification workflow: OpenSpec
- Optional later infrastructure: Redis / WebSockets only when justified

## Architecture rules

- Follow the preservation-first sequence: **preserve → observe → record → reproduce → verify → replace → retire**.
- Keep the legacy implementation operational until its required behavior has verified replacements.
- Do not rewrite the client, backend behavior, persistence, and protocol simultaneously.
- Godot code must depend on `GameApi`, never directly on `command.php`, AMF, FlashVars, or legacy form encoding.
- Build `LegacyV0Api` before `ServerV1Api`.
- Preserve legacy content IDs; modern storage may add internal IDs but must retain `legacy_id`.
- Separate static definitions from player state, e.g. `BuildingDefinition` vs `BuildingInstance`.
- Production server actions are authoritative: clients send intent, never trusted resource/XP/HP/result deltas.
- Standard HTTPS/JSON is the default. Add WebSockets only for genuinely real-time behavior.
- SWFs may remain under archival legacy paths but must never become a modern runtime dependency.

```python
# Good: client sends intent.
buy_building(player_id, building_id, x, y)

# Bad: client dictates authoritative outcome.
apply_client_state(coins=999999, xp=5000)
```

## Setup & commands

Current legacy entry point:

```bash
python server.py
```

Current dependency manifest:

```bash
python -m pip install -r requirements.txt
```

Current baseline syntax check:

```bash
python -m compileall -q .
```

Important:

- The legacy dependency manifest is currently incomplete and must be fixed during baseline preservation before claiming clean-machine reproducibility.
- No verified automated test, lint, or type-check command exists in the current legacy baseline yet.
- Do not invent commands in this file.
- When Godot, compatibility API, Server v1, or test tooling is added, update this section with commands that were actually executed successfully.

## Code style

- Prefer small domain modules over another giant dispatcher like `command.py`.
- Use explicit names and domain types; avoid untyped dictionaries crossing modern domain boundaries.
- Keep transport, domain logic, persistence, and presentation separate.
- Prefer pure functions for reusable calculations where practical.
- Handle failures explicitly; never silently swallow exceptions.
- Do not leave dead compatibility code after its replacement is verified and the related migration explicitly retires it.
- Python imports: use consistent absolute package imports in new application packages.
- GDScript: keep scenes/components focused; do not create a giant global `GameManager`.
- Limit Godot autoloads to cross-cutting services such as `GameApi`, `Session`, `ContentRegistry`, `GameClock`, `Settings`, and `AudioManager`.

## Testing

- Every migrated legacy behavior must have a captured fixture or equivalent behavioral evidence before replacement.
- Prefer golden fixtures containing `request`, `before`, `response`, and `after` state.
- Bug fixes require a regression test when the affected system has test infrastructure.
- Server-authoritative actions must test invalid ownership, insufficient resources, duplicate requests, stale revisions, and invalid state where applicable.
- Asset/runtime changes must not reintroduce Flash/SWF execution.
- Run every relevant available check before finishing.
- Do not claim tests passed unless they were actually run.
- If a required check cannot be run, report exactly why.
- Never convert “code compiles” into “tests pass.”

## Boundaries — do not touch

- Never delete original SWFs, saves, configs, images, sounds, XML, or other preservation material merely because a replacement exists.
- Never overwrite raw source assets during conversion; write converted/runtime assets separately.
- Never silently drop unknown legacy save fields; preserve them for migration analysis, e.g. `legacy_extra`.
- Never manually edit generated files under `.agents/skills/`.
- Never commit `.env`, `.env.*`, credentials, tokens, private keys, or production secrets.
- Never hardcode production secrets.
- Never package Flash Player, Ruffle, ActionScript runtimes, or runtime-required SWFs into the final modern client.
- Do not modify legacy behavior merely to make modern implementation easier; document and reproduce it first.

## Change scope

- Make the smallest coherent change that satisfies the active task/OpenSpec change.
- Do not perform unrelated refactors or cleanup.
- Do not modify unrelated files.
- Do not upgrade dependencies without a concrete reason.
- Do not reorganize legacy files during feature work unless the active change requires it.
- Use `git mv` when relocating preserved repository files where practical.
- Preserve existing behavior unless the task or approved spec explicitly changes it.
- Do not rebalance gameplay during parity work.
- Prefer one migration domain/vertical slice at a time.

## Migration order

Unless an approved OpenSpec change intentionally requires otherwise:

    Boot / Content
        ↓
    Player
        ↓
    Town Rendering
        ↓
    Buildings
        ↓
    Economy
        ↓
    Inventory / Crafting
        ↓
    Units
        ↓
    XP / Levels
        ↓
    Quests / Research / Collections
        ↓
    Missions / Combat
        ↓
    Social
        ↓
    Special / Event Systems

The first major target is a real town rendered in Godot without executing Flash, not PostgreSQL or infrastructure modernization.

## Git / PR conventions

- Commit style: Conventional Commits — `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`, `assets:`
- Branch naming: `<type>/<short-kebab-description>`, e.g. `feat/protocol-recorder`
- Keep branches scoped to one coherent feature or migration unit.
- Do not merge, force-push, or rewrite shared history unless the task explicitly authorizes it.

### Git safety

- Check `git status` before significant work.
- Inspect `git diff` before finishing.
- Never discard existing user changes.
- Do not use destructive Git operations unless explicitly authorized.
- Do not rewrite history unless explicitly required.
- Preserve repository history for legacy material wherever practical.
- Always close/delete the branch after PR merge

## Source of truth

When deciding what the project should do, use this order:

1. Explicit user/task requirements
2. Approved active OpenSpec change
3. `openspec/specs/`
4. Recorded legacy behavior / golden fixtures
5. Existing implementation and architecture
6. Tests
7. Repository documentation
8. Agent assumptions

When sources conflict, investigate the conflict. Do not silently invent a resolution.

For preservation parity, observed legacy behavior is evidence; an accidental modern implementation difference is not automatically an improvement.

## Existing / brownfield project rules

Before modifying an existing capability:

- Inspect its implementation.
- Search `command.py`, `engine.py`, server routes, configuration, saves, and related assets as applicable.
- Read the relevant OpenSpec spec/change.
- Check `openspec/changes/` for active work.
- Identify the current request → state mutation → response behavior.
- Capture or locate behavioral fixtures before replacing legacy behavior.
- Do not assume undocumented means unused.
- Do not rewrite working legacy systems merely because they are unfamiliar.
- Classify obscure systems explicitly as implemented, parity-verified, retired, or out-of-scope.

## Spec-driven development — OpenSpec

This project uses OpenSpec for nontrivial behavioral and architectural changes.

Expected structure:

    openspec/
    ├── config.yaml
    ├── specs/
    └── changes/

Rules:

- Check `openspec/changes/` before starting nontrivial implementation.
- Continue an existing relevant change instead of creating a duplicate.
- Read the relevant `openspec/specs/` capability before modifying it.
- Create/propose a change before implementing new nontrivial behavior when no appropriate change exists.
- Keep implementation aligned with the active change's requirements, design, and tasks.
- If implementation reveals a missing or incorrect requirement, update the change instead of silently diverging.
- Do not expand an active change with unrelated work.
- Sync approved behavior back into main specs and archive completed changes using the installed OpenSpec workflow.
- Do not manually edit generated `.agents/skills/`; use `openspec update` when regeneration is required.

Typical workflow:

    Explore → Propose → Apply → Verify → Sync → Archive

Use exploration for investigation only; it is not permission to implement.

OpenSpec owns feature requirements and change artifacts. This file owns durable repository-wide engineering rules.

## Reconstruction workflow

For each migrated feature:

    1. Inspect legacy implementation and assets.
    2. Identify commands/endpoints/state involved.
    3. Capture or locate legacy fixtures.
    4. Read/create the OpenSpec change.
    5. Implement the smallest complete behavior.
    6. Add/update tests.
    7. Replay/compare against legacy behavior.
    8. Perform visual verification when relevant.
    9. Update migration status and documentation.
    10. Inspect diff and report checks actually run.

Do not mark a legacy feature replaced until parity has been verified or an approved spec explicitly changes its behavior.

## Orchestration mode

For nontrivial OpenSpec changes, the root Codex agent acts as the orchestrator.

- Use real Codex subagents when work can be divided into concrete, independent tasks without overlapping file ownership.
- The root orchestrator owns the active OpenSpec artifacts and task status.
- Implementation subagents must not independently edit `proposal.md`, `design.md`, specs, or `tasks.md` unless explicitly assigned that responsibility.
- Assign each worker a bounded task, owned files/directories, requirements, dependencies, and required verification.
- Do not parallelize tasks that depend on unfinished interfaces or behavior.
- Do not have multiple agents edit the same files unless intentionally coordinated.
- Worker agents must report files changed, checks run, results, and unresolved concerns.
- The root orchestrator must review worker diffs/results before accepting them.
- After implementation, use a separate verification pass or verifier subagent to compare the actual implementation against the active OpenSpec artifacts.
- Do not trust checked task boxes as evidence; inspect the implementation.
- Run OpenSpec strict validation and the installed OpenSpec verification workflow before considering the change complete.
- Any unresolved CRITICAL verification issue blocks completion.
- Any unresolved WARNING blocks completion unless explicitly accepted by the user or active specification.
- If verification fails, create bounded repair tasks, delegate when useful, then rerun verification.
- Only the root orchestrator may declare the OpenSpec change complete.
- Worker subagents should not spawn additional subagents unless the root explicitly authorizes nested delegation.

### Subagent

- Default to at most two active subagents per root session.
- Preferred roles are:
  1. implementation agent
  2. verification agent
- The root agent remains the orchestrator and owns OpenSpec artifacts, architectural decisions, integration, and final acceptance.
- Do not spawn additional agents merely because work can technically be parallelized.
- Prefer sequential delegation when the verifier depends on implementation output.
- Spawn additional agents beyond this default only when the task has clearly independent workstreams and the expected benefit outweighs duplicated context/token cost.
- Give subagents only the context necessary for their assigned task; do not require every subagent to rediscover the entire repository.

### OpenSpec bootstrap and resume

The root orchestrator must support both bootstrap and resume workflows.

Before creating a new OpenSpec change:

- Inspect `openspec/changes/` and the project status recorded in the development roadmap.
- If a relevant active change already exists, resume it instead of creating a duplicate.
- If a completed but unverified or unarchived change exists, finish its verification/lifecycle before creating another dependent change.
- If no active change exists, use the development roadmap and current repository state to determine the smallest coherent next change.
- Use OpenSpec exploration before proposing a new change when repository investigation, legacy behavior, architecture, dependencies, or scope need confirmation.
- Exploration must not implement code.
- After exploration is sufficiently resolved, create the change with the installed OpenSpec propose workflow.
- Validate the generated change before implementation.
- Do not create an OpenSpec change for the entire development roadmap. The roadmap is the program-level plan; OpenSpec changes are bounded implementation units.
- Do not skip ahead to a later roadmap milestone while required exit criteria or dependencies of the current milestone remain incomplete.
- Default to completing one OpenSpec change per orchestration run unless the user explicitly requests continuous milestone execution.

### Development roadmap ownership

The development roadmap contains a root-orchestrator-owned `Project Status` block.

- Only the root orchestrator may update the roadmap's `Project Status` block.
- Implementation and verification subagents must not modify the roadmap unless explicitly assigned.
- Treat the status block as a progress ledger, not as the behavioral source of truth.
- OpenSpec specs and active change artifacts remain the source of truth for specified behavior.
- Repository implementation and tests provide implementation evidence.
- Reconcile the roadmap status against Git, OpenSpec, and the repository before trusting stale status from a previous session.
- Update project status whenever the active change enters a meaningful lifecycle transition: proposed, implementing, verifying, blocked, verified, archived, or completed.
- Record blockers and unresolved verification findings rather than hiding them.
- After archiving a verified change, update the roadmap cursor to the next eligible objective but do not automatically begin that change unless the current orchestration request allows it.
