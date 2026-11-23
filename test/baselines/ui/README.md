# Visual checkpoint baselines (760x600)

These PNGs are the **frozen, reviewed checkpoint evidence** for the Phase 1
visual recovery. They are ordinary files in git: a change to one of them is a
change to the accepted presentation and must be reviewed as such.

| File | Checkpoint |
| --- | --- |
| `01-initial-town.png` | (a) at-rest town, tutorial dismissed |
| `02-tutorial-overlay.png` | (b) fresh player's tutorial overlay |
| `03-build-menu.png` | (c) build surface open |
| `04-quest-dialog.png` | (d) quest/dialog surface open |
| `05-desktop-window.png` | (e) the same client in a larger (1280x800) window |

## Rules

- A bare `node scripts/capture-ui.mjs` writes only to `.work/ui-captures/`.
  It **never** writes into this directory.
- `node scripts/capture-ui.mjs --check` captures the same five checkpoints and
  compares them with these files. A missing baseline or an unexplained
  difference fails the command.
- `node scripts/capture-ui.mjs --update` is the **only** way to replace these
  files. It is an explicit human action: review the new images first, then run
  it, then commit the result with a message explaining the visual change.

## Provenance of the files in this commit

These images were captured with the CDP harness from the pre-Phase-1 build at
base commit `8aef8a8` (2026-11-24), with a freshly registered development
player, `--headless=new` Chrome, a 760x600 device-metrics override and the
real authoritative server. They document the **regression baseline**, not an
approval of visual fidelity. The harness's machine-readable metrics report the
known defects (green coverage below 60%, too many at-rest UI surfaces,
overlapping bottom navigation and no canvas click-through). After the Phase 1
implementation lanes land and the owner approves the rendered result, a human
must run `--update` and commit the approved images as the accepted baselines.

No proprietary Flash art, SWF or original sprite/audio asset is read, copied or
embedded by the harness or by these files.
