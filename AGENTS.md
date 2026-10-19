# AGENTS.md

> **Reusable template.** Populate the `{{PLACEHOLDERS}}` only when asked to initialize this repository. Verify details against the code, manifests, and existing documentation; never guess. Remove this line once initialized.

## Project

- **Name:** {{PROJECT_NAME}}
- **Purpose:** {{SHORT_PURPOSE_AND_PRIMARY_USERS}}
- **Current state:** {{VERIFIED_CURRENT_STATE}}

## Source of Truth

**Read only the documentation relevant to the task. Do not assume—verify.**

| Source                                  | Read when                                                    |
| --------------------------------------- | ------------------------------------------------------------ |
| `docs/CONTEXT.md`                       | Locating context, constraints, and relevant documentation    |
| `docs/ROADMAP.md`                       | Checking planned features, priorities, or verified progress  |
| `docs/ARCHITECTURE.md` _(if it exists)_ | Making changes to established boundaries or data flows       |
| Source code and tests                   | Determining actual current behavior and verifying a change   |
| `graphify-out/` _(if it exists)_        | Exploring code relationships; verify findings against source |

- Requirements and explicitly approved decisions define **intended behavior**; source code and passing tests provide evidence of **current behavior**.
- If documentation and code conflict, **report the discrepancy** and determine whether the code or documentation needs correction. Never silently rewrite a requirement to justify current code.
- Prefer one authoritative location per fact; link to it rather than copying it into multiple files.

## Tech Stack

_Fill from verified project files. Remove unused rows._

| Layer              | Technology / version      | Evidence        |
| ------------------ | ------------------------- | --------------- |
| Frontend / UI      | {{FRONTEND_OR_NA}}        | {{SOURCE_PATH}} |
| Backend / runtime  | {{BACKEND_OR_NA}}         | {{SOURCE_PATH}} |
| Database / storage | {{DATABASE_OR_NA}}        | {{SOURCE_PATH}} |
| Build / tooling    | {{BUILD_TOOLS}}           | {{SOURCE_PATH}} |
| Tests              | {{TEST_FRAMEWORKS_OR_NA}} | {{SOURCE_PATH}} |

## Build, Test, and Development Commands

_Use commands that really exist in this repository. Never invent a script._

| Purpose              | Command                   | Evidence / notes |
| -------------------- | ------------------------- | ---------------- |
| Install dependencies | `{{INSTALL_COMMAND}}`     | {{EVIDENCE}}     |
| Run locally          | `{{DEV_COMMAND}}`         | {{EVIDENCE}}     |
| Build                | `{{BUILD_COMMAND}}`       | {{EVIDENCE}}     |
| Test                 | `{{TEST_COMMAND}}`        | {{EVIDENCE}}     |
| Lint / type-check    | `{{CHECK_COMMAND_OR_NA}}` | {{EVIDENCE}}     |

Run from the repository root unless a command explicitly requires another directory.

## Architecture Non-Negotiables

_List only **verified** constraints from the repository or approved requirements. Reference `docs/ARCHITECTURE.md` if present. If none are documented, write `Not yet established`—do not manufacture rules._

- {{VERIFIED_CONSTRAINT_OR_NOT_YET_ESTABLISHED}}

## Working Method (Lightweight ICM)

1. **Orient:** Read `docs/CONTEXT.md`, then only the relevant roadmap section, existing source files, and needed references.
2. **Plan when warranted:** For substantial changes, summarize approach, affected files, risks, and verification criteria before coding. Small, clear fixes do not need separate plan documents.
3. **Implement within scope:** Follow existing conventions and avoid unrelated changes.
4. **Verify:** Run applicable checks; report passed, failed, skipped, and unavailable checks accurately.
5. **Preserve:** Update `docs/ROADMAP.md` only for verified outcomes, and update other authoritative docs only when facts change.

Do not create extra ICM stage folders or permanent plan files unless the task benefits from them.

## Graphify

- Graphify is **derived project knowledge**, not the source of truth for code behavior.
- When available and relevant, query the existing graph to find related symbols and dependencies; inspect source files before acting on results.
- After meaningful structural changes, refresh the graph using the **installed** Graphify skill or CLI workflow. Do not presume Graphify is installed or that a graph exists.
- If exporting to Obsidian, use only this project's generated area: `{{OBSIDIAN_VAULT_PATH}}/10 - Projects/{{PROJECT_NAME}}/_Graphify/`.
- Never export into the vault root or overwrite curated PARA notes. Refreshing the graph is **not** the same as saving session decisions.

## Obsidian / Cross-Project Knowledge

- **Central vault:** `{{OBSIDIAN_VAULT_PATH_OR_NOT_CONFIGURED}}`
- **Project notes:** `10 - Projects/{{PROJECT_NAME}}/`, if present.
- Read only relevant notes, when the vault is configured and accessible; repository docs remain authoritative for project-specific requirements.
- Propose meaningful updates after substantial work: project progress/decisions under `10 - Projects`, reusable lessons under `30 - Resources`, unverified ideas under `00 - Inbox`.
- **Ask before editing curated vault notes.** Avoid duplicates, stale claims, secrets, and copying entire chat transcripts.
- If the vault is inaccessible, continue using local project context and mention the limitation.

## Git Workflow

1. **Never commit directly to `main`.** Use task branches prefixed with `feat/`, `fix/`, `chore/`, `docs/`, or `refactor/`.
2. Before modifying files, check `git status`, switch to `main`, pull the latest `origin/main`, create a task branch, and push it with upstream tracking.
3. Commit at logical checkpoints and push changes to the remote.
4. Use the `git` subagent when available; otherwise, use permitted Git tools.
5. After implementation, run relevant tests, resolve issues, and **merge verified work into `main`**. Follow required CI checks and branch protections.
6. Never discard existing changes, force-push, or commit temporary agent-generated plans unless explicitly authorized.
7. **Do not consider a task complete until it is verified, merged, and reflected in `docs/ROADMAP.md`.**

### Branch Lifecycle

```bash
git status
git switch main
git pull --ff-only origin main
git switch -c <branch-name>
git push -u origin <branch-name>
```

If the working tree is dirty or Git operations are blocked, resolve safely without overwriting existing work.

---

## Autonomous Orchestration Mode

_Activate only when the user explicitly requests autonomous roadmap execution._

1. **Orchestrator:** Read `docs/CONTEXT.md` and `docs/ROADMAP.md`, select the next eligible task, manage Git operations, and verify completion.
2. **Subagent:** Spawn **one implementation-and-testing subagent** per task when supported. Otherwise, perform the work directly.
3. **Execution:** Create branch → Implement → Test → Commit → Push → Merge → Update roadmap.
4. **Continuity:** Automatically proceed to the next eligible roadmap task. **Do not stop after one feature or merge.**
5. **Blockers:** Attempt safe recovery. Pause only for unresolved errors, missing requirements, permissions, required approvals, or unsafe operations. Continue independent tasks when possible.
6. **Completion:** Stop when all authorized tasks are finished, remaining tasks are deferred or blocked, or the user stops execution.
7. **Knowledge:** Update relevant documentation, preserve reusable lessons in Obsidian, and refresh Graphify after significant changes.

## Template Initialization (only when requested)

When asked to initialize these templates for a new repository:

1. Inspect the repository's `README`, manifests, folder structure, configuration, tests, and existing documentation.
2. Fill this file plus `docs/CONTEXT.md` and `docs/ROADMAP.md` using **verified** information. Keep the roadmap grouped by useful milestones, not implementation steps.
3. Preserve existing user-written requirements. Use `Not verified` or ask a targeted question for genuinely unknown details.
4. Remove inapplicable template rows and placeholders. Do not claim features are complete without evidence.
5. Do **not** automatically install Graphify, create branches/commits, modify the Obsidian vault, or create optional docs without permission.
6. Summarize the populated files, sources consulted, and remaining uncertainties for review.
