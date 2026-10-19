# Project Context

> This file is a **router**, not a duplicate of the README or an architecture specification.

## At a Glance

- **Project:** Social Wars Legacy — a cross-platform client-server re-implementation of
  *Social Wars* (Zynga, Flash), built from a full reverse-engineering of the original
  Flash client and the community preservation server.
- **What it does:** Replaces the Adobe Flash client and the Flask/Python backend with a
  modern client (web/desktop/mobile) and an authoritative, authenticated server.
- **Primary users / use cases:** Players who want the game to keep working; preservation
  archivists; anyone studying the original client's game rules.
- **Current focus:** Investigation and documentation are **complete**. The rewrite plan is
  defined in [`re/docs/08-CLONE-ROADMAP.md`](../re/docs/08-CLONE-ROADMAP.md) but **no
  implementation code exists in this repository yet**.

## Where to Look

| Need | Canonical source |
|---|---|
| **Start here** — the findings in one page | [`re/README.md`](../re/README.md) |
| Goals, features, and progress | [`docs/ROADMAP.md`](../docs/ROADMAP.md) |
| Full investigation report set | [`re/docs/`](../re/docs/) |
| Observed wire protocol (verified live) | [`re/docs/06-LIVE-SESSION-PROTOCOL.md`](../re/docs/06-LIVE-SESSION-PROTOCOL.md) |
| Command catalogue, economy, quests, goals | [`re/docs/03-commands-quests-economy.md`](../re/docs/03-commands-quests-economy.md) |
| Combat rules and unit stats | [`re/docs/02-combat-and-units.md`](../re/docs/02-combat-and-units.md) |
| Save format, config pipeline, server routes | [`re/docs/04-python-server-and-data.md`](../re/docs/04-python-server-and-data.md) |
| Asset inventory and conversion plan | [`re/docs/05-assets-and-content-pipeline.md`](../re/docs/05-assets-and-content-pipeline.md) |
| The rewrite plan (6 workstreams, 10 milestones) | [`re/docs/08-CLONE-ROADMAP.md`](../re/docs/08-CLONE-ROADMAP.md) |
| What is still unknown | [`re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md`](../re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md) |
| Raw evidence (traffic, digests, screenshots) | [`re/evidence/`](../re/evidence/) |
| The upstream project under analysis | `C:\Users\Edison\Desktop\socialwarriors` (external, unmodified) |

## The Upstream Project Under Investigation

| | |
|---|---|
| Location | `C:\Users\Edison\Desktop\socialwarriors` — a separate checkout, **not** part of this repository |
| Stack | Python 3 + Flask server; Adobe Flash (AS3) client; JSON game config; 3 199 asset files |
| Licence | GPL v3 (code). The **content** (sprites, audio, config) is Zynga's — see the licensing section of the roadmap. |
| Status of this repository | Documentation and evidence only. The upstream code was **not** modified, vendored, or copied. |

## Project-Specific Constraints

- **The client is the specification.** The decompiled ActionScript 3 (1 387 classes) is the
  authoritative description of game behaviour; the Python server is an approximation of it.
  Do not port behaviour from the Python when the two disagree.
- **The server must become authoritative.** The upstream server trusts client-declared
  resource costs, combat outcomes, goal completion and daily rewards. A rewrite must not
  preserve that. See the cheat battery in the roadmap.
- **Content is versioned.** `config/main.json` is a 29-Aug-2012 capture plus five
  JSON-Patch deltas. Both must travel with any derived content bundle.
- **Licensing must be settled before publishing.** GPL v3 covers the upstream code; the
  Zynga assets do not.
- **The original Flash client must keep working.** A protocol-compatibility shim is a
  first-class deliverable, not an afterthought — it is what makes this a preservation.

## Context Loading Rules

1. Start with the user's task and this routing file.
2. Open `re/README.md` for the document map, then only the specific report the task needs.
3. Inspect the upstream checkout directly when a claim needs re-verification.
4. Consult [`re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md`](../re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md)
   before promising certainty.
5. If sources disagree, report the conflict; do not silently choose whichever is convenient.
6. The upstream project is a **read-only reference**. Do not edit it — copy what is needed
   into a working area.
