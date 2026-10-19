# Social Wars Legacy — Roadmap

> **Purpose:** an outcome-based guide to what gets built and in what order. Milestones are
> defined in detail in [`re/docs/08-CLONE-ROADMAP.md`](re/docs/08-CLONE-ROADMAP.md); this
> file is the short, checkable version.

## Status Rules

- `[ ]` = not yet verified as complete. `[x]` = implemented **and verified**.
- **Not started:** no required items verified. **In progress:** some required items pending.
  **Complete:** all required items verified.
- **Deferred:** intentionally excluded from the current milestone.
- The agent must check actual implementation/tests before marking an item complete; if
  evidence is missing, leave it unchecked and note the uncertainty.
- Each checkbox should describe an **observable, testable outcome**, not a class name,
  code snippet, or implementation technique.
- Follow approved priorities; do not assume the next unchecked item is automatically
  authorized work.

---

## Group 0 — Investigation & Documentation

*Outcome: everything needed to rebuild the game as a cross-platform client-server
application is written down, evidenced, and navigable.*

- [x] The Flash client is fully decompiled and the 1 387 AS3 classes are analysed
      ([`re/docs/02`](re/docs/02-combat-and-units.md), [`re/docs/03`](re/docs/03-commands-quests-economy.md))
- [x] The network protocol is documented end to end, including the recovered HMAC key
      ([`re/docs/01`](re/docs/01-network-protocol.md))
- [x] The HMAC key is **verified against live traffic** from a real Adobe Flash Player
      ([`re/evidence/live/hmac-verification.txt`](re/evidence/live/hmac-verification.txt))
- [x] The save format and game-config pipeline are documented
      ([`re/docs/04`](re/docs/04-python-server-and-data.md))
- [x] The asset tree is inventoried and mapped to every config item
      ([`re/docs/05`](re/docs/05-assets-and-content-pipeline.md))
- [x] A live session is captured and reproducible (309 requests, 16 command batches)
      ([`re/docs/06`](re/docs/06-LIVE-SESSION-PROTOCOL.md))
- [x] REA's contribution and its coverage limits are recorded
      ([`re/docs/07`](re/docs/07-REA-EVIDENCE.md))
- [x] The rewrite plan, risks and open questions are written
      ([`re/docs/08`](re/docs/08-CLONE-ROADMAP.md), [`re/docs/09`](re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md))
- [ ] Combat (`end_attack`) and quest (`end_quest`) payloads are captured from a live
      battle — the last static-only part of the protocol

**Status:** Complete, except the live battle capture.

---

## Group 1 — Content & Assets

*Outcome: the game's data and art exist as versioned, renderable, non-Flash artefacts.*

- [ ] A content bundle builds reproducibly from `config/main.json` + the 5 JSON-Patch
      deltas and is validated against a schema
- [ ] The 123 client-only item ids (199, 302, 1307–1431) are reconciled: shipped, or
      explicitly excluded
- [ ] The weekly darts schedule still advances correctly after a year of running
- [ ] Every `items[].img_name` renders in a test viewer at 3 zoom levels
- [ ] The 1 114 SWF files are converted to frame atlases (or SVG paths) with a frame table
- [ ] The 73 missing asset references (10 sprites, 29 thumbs, 34 chapter/intro images) are
      resolved or documented as permanently unavailable

---

## Group 2 — Rules Engine

*Outcome: the game simulation runs server-side and reproduces the original client's rules.*

- [ ] Unit stat resolution, the damage pipeline and unit XP level-up match the decompiled
      client on a golden test corpus
- [ ] The 15 special attacks, 6 attack conditions and 10 damage classes are implemented
- [ ] Combat resolves server-side from a server-issued seed, and the client renders the
      result
- [ ] The economy — resource caps, collect timers, population, energy, build costs,
      upgrade chains, market, daily/weekly cycles — is authoritative
- [ ] The quest state machine and the 134 goals are evaluated server-side

---

## Group 3 — Authoritative Server

*Outcome: the server is safe, concurrent, persistent, and speaks the original protocol.*

- [ ] Players authenticate; a session token replaces the `USERID`-in-the-body model
- [ ] Every command's resource cost is computed by the server, not accepted from the client
- [ ] `flash_debug` is removed
- [ ] The 12-entry cheat battery in the roadmap is rejected or has no effect
- [ ] State is stored transactionally in a database; concurrent commands cannot corrupt it
- [ ] Bad input returns typed 4xx responses, never a 500
- [ ] A protocol shim lets the **original** `Basesec_1.5.4.swf` play against this server
      with no client change

---

## Group 4 — Modern Client

*Outcome: the game is playable on desktop and mobile without Flash.*

- [ ] The tutorial and the first chapter are completable in a web build
- [ ] Building, training, upgrading, collecting, the world map and attacking all work
- [ ] Quests, goals, the darts minigame, magic and tech, the marketplace, premium and
      the weekly bonus are functional
- [ ] One source tree produces web, desktop (Tauri) and mobile (Capacitor) builds
- [ ] The UI is rebuilt — the original Flash UI chrome is not in the asset tree

---

## Deferred / Future Work

*Intentionally postponed outcomes, with the reason.*

- [ ] Alliance / multiplayer features beyond the static neighbours — the upstream server
      answers `{}` for all 11 `alliance/?method=…` variants, so the real contract has to
      be recovered from the client classes first
- [ ] The auction house / betting subsystem — `auctions.py` exists but is disabled
      upstream and the client only reaches it through the commented-out `bets/*` routes
- [ ] Facebook / social-point integration — the original `graph.facebook` calls are inert
      in this build
- [ ] Recovering the 33 missing `Basesec` builds (1.4.7 and others) or the original PHP
      backend

## Status Summary

| Group | Milestone | Status |
|---|---|---|
| 0 | Investigation & Documentation | Complete (1 item open) |
| 1 | Content & Assets | Not started |
| 2 | Rules Engine | Not started |
| 3 | Authoritative Server | Not started |
| 4 | Modern Client | Not started |

## Maintenance

- Revisit this roadmap when scope or priorities change.
- Update statuses only after verification; distinguish untested from failed.
- Keep implementation details in code, code review, or a task-specific plan — not here.
- Preserve reasons for significant technical decisions in
  [`re/docs/08-CLONE-ROADMAP.md`](re/docs/08-CLONE-ROADMAP.md) and
  [`re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md`](re/docs/09-LIMITATIONS-AND-OPEN-QUESTIONS.md).
