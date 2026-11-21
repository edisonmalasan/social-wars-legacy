#!/usr/bin/env python3
"""Full end-to-end play session in WebKit (Playwright), against the real server.

This is the WebKit entry point of the shared Playwright harness in
``scripts/e2e-test-firefox.py``. WebKit does not speak the Chrome DevTools
Protocol, so Python Playwright drives it. The same built client, the same
authoritative server and the same rendered controls are used as in the
Chrome/Edge and Firefox harnesses; only the engine changes.

What one run proves, through rendered controls only
---------------------------------------------------
* a fresh player registers through the ``#signin`` form;
* the tutorial is dismissed with its Skip button;
* a building is picked from the build menu and placed on the canvas, and the
  server's own map records it;
* a Wood Factory is placed and the server refuses an undue Collect;
* a unit is trained through the recruitment panel and the server's queue
  records it;
* the weekly quest is opened from the chapter map, fought with the rendered
  Strike / Report-kill buttons and finished with the rendered Finish button;
* the reward rows match the wallet delta and the persisted receipt, and a
  replay is refused without a second payment;
* a client reload and a full server restart preserve the award and receipt.

``window.__swl`` is never used to issue a command or grant anything. The client
renders; the server decides. WebKit here is Playwright's WebKit engine, not
branded Safari, and no real device is claimed.

The player id, temporary data directory and screenshot are distinct from the
Firefox harness so the two can run concurrently without collision.

Usage (from the repository root)::

    python scripts/e2e-test-webkit.py
    python scripts/e2e-test-webkit.py --screenshot path/to/shot.png
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

# The shared harness uses hyphens in its filename, so it cannot be imported by
# a normal module name. Load it by path, from any working directory. This does
# not copy or modify the harness: both entry points run exactly the same code.
HARNESS = Path(__file__).resolve().parent / "e2e-test-firefox.py"
spec = importlib.util.spec_from_file_location("swl_e2e_harness", HARNESS)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load the shared harness at {HARNESS}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

if __name__ == "__main__":
    sys.exit(module.main("webkit", description=__doc__))
