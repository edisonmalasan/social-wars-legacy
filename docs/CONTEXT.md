# Project Context

> This file is a **router**, not a duplicate of the README or an architecture specification.

## At a Glance

- **Project:** Social Wars Legacy — a cross-platform client-server re-implementation of
  *Social Wars* (Zynga, Flash client v1.5.4), built from a full reverse-engineering of the
  original Flash client and the community preservation server.
- **What it does:** Replaces the Adobe Flash client and the Flask/Python backend with a
  modern client (web/desktop/mobile) and an authoritative, authenticated server.
- **Primary users / use cases:** Players who want the game to keep working; preservation
  archivists; anyone studying the original client's game rules.
- **Current focus:** **Investigation and documentation are complete.** The production
  roadmap is defined in [`ROADMAP.md`](ROADMAP.md) and **autonomous execution is active**.
  No product code exists yet — Group A (vendoring the upstream project) is the first task.

## Where to Look

| Need | Canonical source |
|---|---|
| **Start here** — the findings in one page | [`../README.md`](../README.md) and [`../re/README.md`](../re/README.md) |
| Goals, features, priorities, verified progress | [`ROADMAP.md`](ROADMAP.md) |
| Full investigation report set | [`../re/docs/`](../re/docs/) |
| Observed wire protocol (verified live) | [`../re/docs/06-LIVE-SESSION-PROTOCOL.md`](../re/docs/06-LIVE-SESSION-PROTOCOL.md) |
| Command catalogue, economy, quests, goals | [`../re/docs/03-commands-quests-economy.md`](../re/docs/03-commands-quests-economy.md) |
| Combat rules and unit stats | [`../re/docs/02-combat-and-units.md`](../re/docs/02-combat-and-units.md) |
| Save format, config pipeline, server routes | [`../re/docs/04-python-server-and-data.md`](../re/docs/04-python-server-and-data.md) |
| Asset inventory and conversion plan | [`../re/docs/05-assets-and-content-pipeline.md`](../re/docs/05-assets-and-content-pipeline.md) |
| The detailed workstream breakdown | [`../re/docs/08-CLONE-ROADMAP.md`](../re/docs/08-CLONE-ROADMAP.md) |
| What is still unknown | [`../re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md`](../re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md) |
| Raw evidence (traffic, digests, screenshots) | [`../re/evidence/`](../re/evidence/) |
| How to work in this repository | [`../AGENTS.md`](../AGENTS.md) |
| The upstream project under analysis | `C:\Users\Edison\Desktop\socialwarriors` (external, unmodified, to be vendored in Group A) |

## The Upstream Project Under Investigation

| | |
|---|---|
| Location | `C:\Users\Edison\Desktop\socialwarriors` — a separate checkout, **not** part of this repository yet |
| Upstream commit | `c3fceeb1f8e93734a293b9bc25ae6025656f6822` ("Minimal server support", 2026-10-01), tags `0.01a` / `0.02a` |
| Stack | Python 3.9 + Flask 2.2.5 server; Adobe Flash (AS3) client; JSON game config; 3 199 asset files (716.8 MB) |
| Client | `Basesec_1.5.4.swf` — SWF v10, 1 387 AS3 classes in one 2 MB AVM2 block, loaded by `SWLoader.swf` |
| Licence | GPL v3 (code). The **content** (sprites, audio, config) is Zynga's — see the roadmap's Group I gate. |
| Role in this repository | A **read-only reference and test oracle**. It is vendored verbatim in Group A and never edited. |

## Project-Specific Constraints

*Only record constraints that affect many tasks. The full, binding list is in
[`../AGENTS.md`](../AGENTS.md) § "Architecture Non-Negotiables".*

- **The client is the specification.** The decompiled ActionScript 3 describes the real
  game; the Python upstream server is an approximation of it. Where they disagree, the AS3
  wins. Port behaviour from the client, not from `command.py`.
- **The server must become authoritative.** The upstream server trusts client-declared
  resource costs, combat outcomes, goal completion and rewards. A rewrite must not
  preserve that — see the cheat battery in the roadmap.
- **The rules engine is deterministic and pure.** No `Date.now()`, no unseeded randomness,
  no I/O inside the simulation. Same seed + same inputs ⇒ same outcome on any machine.
- **Content is versioned and reproducible.** `config/main.json` plus the 5 JSON-Patch
  deltas (778 → 900 items, 104 → 105 globals) produce a single hashed content bundle.
- **No Flash in the shipped product.** The original client may be used *only* as a test
  oracle — never as a runtime dependency.
- **The upstream tree is vendored, never edited**, and keeps its GPL v3 notices.
- **Licensing must be settled before any public release.** The upstream code is GPL v3; the
  Zynga assets are not.

## Context Loading Rules

1. Start with the user's task and this routing file.
2. Open `re/README.md` for the document map, then only the specific report the task needs.
3. Inspect the upstream checkout directly when a claim needs re-verification.
4. Consult [`../re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md`](../re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md)
   before promising certainty.
5. If sources disagree, report the conflict; do not silently choose whichever is convenient.
6. The upstream project is a **read-only reference**. Do not edit it — copy what is needed
   into a working area, or vendor it under `upstream/` per Group A.
