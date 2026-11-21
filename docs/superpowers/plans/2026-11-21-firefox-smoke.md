# Firefox Smoke Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the built client boots, renders through Gecko and lays out its DOM in Firefox using a thin Playwright smoke test, without rewriting the CDP e2e harness or claiming full Firefox/Safari parity.

**Architecture:** Python Playwright 1.60.0 is already installed; a separate `scripts/smoke-test-client-firefox.py` reuses the smoke harness's *idea* (serve client + stub world, seed session, wait for `#status`) but uses Playwright's API (`page.evaluate`, `page.reload`, `page.wait_for_function`). The existing Node CDP harnesses stay unchanged. Safari/WebKit and the full e2e session remain "not run".

**Tech Stack:** Python 3.9, Playwright 1.60.0, existing static server pattern from `scripts/smoke-test-client.mjs`.

**Spec:** `docs/GOAL.md` (autonomous roadmap, Group C platform clients); `docs/ROADMAP.md` G5 open Firefox/Safari item.

## Global Constraints

- No claim of full Firefox parity, Safari/WebKit, real device or a passing e2e session in Firefox. The roadmap checkbox stays open; record this as a smoke result only.
- No runtime dependency added to the shipped client. Python Playwright is a test tool already installed on this host; document the exact browser provision command (`python -m playwright install firefox`) and the pinned revision 1522.
- Do not weaken or rewrite the existing Chrome/Edge CDP harnesses.
- Keep all GOAL §7 gates green; 401-item roadmap accounting unchanged.

## Review Focus

- Does the smoke test genuinely boot the built client under Gecko (WebGL2/PixiJS `started` status + visible sprites or canvas)?
- Are DOM assertions real (HUD resource, goals panel) rather than trivial "page loaded"?
- Are page errors captured and reported as failures?
- Is the "smoke only, Safari not run, full e2e not run" limitation explicit in code/docs?

---

### Task 1: Firefox smoke script and verification

**Files:** `scripts/smoke-test-client-firefox.py` (new), `docs/ROADMAP.md`, task report.

- [ ] Step 1: provision the matching Firefox build if absent (`python -m playwright install firefox`), recording the exact command/output. Inspect `scripts/smoke-test-client.mjs` for the stub world/session and static-server pattern to reuse.
- [ ] Step 2: implement the Python script: start the same static server (or reuse a Node helper if simpler), seed `localStorage['swl.session']`, navigate, wait for `#status[data-state=started]`, assert `#game canvas` and HUD/goals DOM, capture console/page errors, screenshot, report "browsers that ran: firefox" or a precise failure.
- [ ] Step 3: run the script; record exact output (status, screenshot path, assertions). Run all GOAL §7 gates plus the existing Chrome/Edge smoke and e2e to prove no regression.
- [ ] Step 4: record only the verified smoke result in `docs/ROADMAP.md` outside Group headers, keeping 401 accounting and prior history; state that full Firefox e2e and Safari remain not run. Re-run doc checks.
- [ ] Step 5: commit `feat(test): smoke-test the client in Firefox with Playwright`.
