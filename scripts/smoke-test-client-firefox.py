#!/usr/bin/env python3
"""Smoke-test the built client in Firefox (Gecko) with Playwright.

The client has to **run**, not merely build. The other smoke harness
(``smoke-test-client.mjs``) drives Chrome and Edge over the Chrome DevTools
Protocol; Firefox does not speak CDP, so that harness cannot drive it. This
script is a thin, separate Playwright smoke test for Gecko only.

What it proves
--------------
* the built client boots under Gecko (it reaches ``#status[data-state=started]``);
* PixiJS creates a real WebGL2 canvas and draws sprites (the status detail);
* the React interface lays out its DOM (a numeric HUD readout and the goals
  panel, the same assertions the end-to-end harness makes);
* no console/page errors were raised along the way.

What it does NOT prove
----------------------
This is a **smoke** test, not full Firefox end-to-end coverage. It does not
play a session, place buildings or fight a battle. Safari/WebKit, real devices
and the full Firefox e2e session remain **NOT RUN**. The G5 Firefox/Safari
roadmap item stays open.

The shipped client gains no runtime dependency from this script: Python
Playwright and its Firefox build are test tools on this host only. The exact
provision step is::

    python -m playwright install firefox   # Firefox 150.0.2, Playwright v1522

Usage (from the repository root)::

    python scripts/smoke-test-client-firefox.py
    python scripts/smoke-test-client-firefox.py --screenshot path/to/shot.png
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path.cwd()

# The same three file roots as smoke-test-client.mjs: the build, the generated
# files and the atlas pages (served under /atlases/ from .work/frames).
ROOTS = [
    ROOT / "apps/client/dist",
    ROOT / "apps/client/public",
    ROOT / ".work/frames",
]

TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".woff2": "font/woff2",
    ".svg": "image/svg+xml",
}

# A small world for the client to draw, copied from smoke-test-client.mjs. The
# smoke test is about the client, not the server, so the world is a stub with a
# few real items so the scene is not empty.
STUB_WORLD = {
    "maps": [
        {
            "id": 0,
            "items": {
                "1": [1, 10, 20, 0, 0, [], {}, 1],
                "2": [2, 11, 20, 0, 0, [], {}, 1],
                "3": [4, 12, 21, 0, 0, [], {}, 1],
            },
        }
    ],
    "privateState": {},
    "resources": {"g": 2000, "w": 2000, "o": 2000, "s": 2000, "c": 2000, "e": 50, "x": 0, "m": 0},
}

# The session the smoke test signs in with. An hour ahead, so the client does
# not decide it has expired.
STUB_SESSION = {
    "token": "smoke-test-token",
    "playerId": "smoke",
    "issuedAt": 0,
    "expiresAt": 4102444800,  # 2100-01-01, comfortably in the future.
}

# The exact string the client reads from localStorage (packages/client/session.ts).
SESSION_STORAGE = json.dumps(
    {k: STUB_SESSION[k] for k in ("token", "playerId", "expiresAt")}
)


def make_handler():
    """Build a request handler bound to this script's ROOTS and stubs."""

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):  # keep the smoke output clean
            pass

        def _send(self, code, content_type, body: bytes):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            relative = path.lstrip("/") or "index.html"

            # Browsers ask for a favicon; a 204 keeps the console free of a
            # harmless 404 that would otherwise look like a page error.
            if relative == "favicon.ico":
                self._send(204, "text/plain", b"")
                return

            if relative == "api/world":
                self._send(200, "application/json", json.dumps(STUB_WORLD).encode())
                return

            if relative == "api/session":
                self._send(200, "application/json", json.dumps(STUB_SESSION).encode())
                return

            for root in ROOTS:
                if not root.is_dir():
                    continue
                try:
                    file = (root / relative).resolve()
                    file.relative_to(root.resolve())
                except (ValueError, OSError):
                    continue  # path escaped the root
                if not file.is_file():
                    continue
                content_type = TYPES.get(file.suffix.lower()) or mimetypes.guess_type(file.name)[0] or "application/octet-stream"
                try:
                    with file.open("rb") as stream:
                        body = stream.read()
                except OSError:
                    continue
                self._send(200, content_type, body)
                return

            self._send(404, "text/plain", b"not found")

    return Handler


def start_server():
    """Serve on a free loopback port; return (server, url)."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    return server, f"http://127.0.0.1:{port}/"


def probe(page, expression):
    """Evaluate a JavaScript expression in the page and return its value."""
    return page.evaluate(expression)


def run_browser(url: str, screenshot: Path):
    """Run the Firefox smoke check. Returns a list of failure strings."""
    from playwright.sync_api import sync_playwright  # imported lazily

    failures: list[str] = []
    console_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()

            # Any console error or uncaught exception is a failure.
            def on_console(message):
                if message.type == "error":
                    console_errors.append(f"console.error: {message.text}")

            def on_page_error(error):
                console_errors.append(f"pageerror: {error}")

            page.on("console", on_console)
            page.on("pageerror", on_page_error)

            print("  firefox: ", end="", flush=True)

            # First load gives the page an origin; seed the session and reload
            # so the client signs in without anybody typing anything.
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            page.evaluate(
                "(value) => window.localStorage.setItem('swl.session', value)",
                SESSION_STORAGE,
            )
            page.reload(wait_until="domcontentloaded", timeout=30_000)

            # The client is asynchronous: it fetches content, starts the
            # renderer and asks for the world. Wait until it says it started
            # (or failed) rather than guessing at a fixed delay.
            page.wait_for_function(
                """() => {
                    const e = document.getElementById('status');
                    if (!e) return false;
                    const s = e.getAttribute('data-state');
                    return s === 'started' || s === 'failed';
                }""",
                timeout=60_000,
            )
            status = probe(
                page,
                """(() => {
                    const e = document.getElementById('status');
                    return { state: e.getAttribute('data-state'), detail: e.textContent };
                })()""",
            )

            if status["state"] != "started":
                failures.append(
                    f"firefox: the client said '{status['state']}' ({status['detail']})"
                )
                print(f"FAILED ({status['state']}: {status['detail']})")
                return failures

            detail = status["detail"] or ""
            print(f"started ({detail})")

            # The renderer must have made a real WebGL2 canvas and drawn the
            # stub world's sprites into it. The sprite count comes from the
            # client's own handle, not from the status text: that text races
            # between "N sprites" and "N atlas page(s)" as pages load, while
            # visibleSprites() is a stable reading of the stage.
            canvas = probe(
                page,
                """(() => {
                    const c = document.querySelector('#game canvas');
                    if (!c) return { exists: false };
                    return {
                        exists: true,
                        width: c.width,
                        height: c.height,
                        webgl2: !!c.getContext('webgl2'),
                        sprites: window.__swl ? window.__swl.visibleSprites() : -1,
                    };
                })()""",
            )
            if not canvas.get("exists"):
                failures.append("firefox: no #game canvas (the renderer did not start)")
            elif not (canvas.get("width", 0) > 0 and canvas.get("height", 0) > 0):
                failures.append(f"firefox: the canvas has no size: {canvas}")
            elif not canvas.get("webgl2"):
                failures.append("firefox: the canvas has no WebGL2 context")
            elif not isinstance(canvas.get("sprites"), int) or canvas["sprites"] < 1:
                failures.append(f"firefox: no visible sprites were drawn ({canvas})")
            else:
                print(
                    f"  WebGL2 canvas {canvas['width']}x{canvas['height']}, "
                    f"{canvas['sprites']} visible sprite(s) drawn"
                )

            # The interface has to have laid itself out too. These are the
            # same DOM assertions the end-to-end harness makes.
            hud = probe(
                page,
                """(() => {
                    const bar = document.querySelector('#ui .swl-hud');
                    if (!bar) return { error: 'no top bar' };
                    const gold = bar.querySelector('.swl-resource-gold .swl-readout-value');
                    return { gold: gold ? gold.textContent.trim() : '' };
                })()""",
            )
            if hud.get("error") or not re.search(r"\d", str(hud.get("gold", ""))):
                failures.append(
                    f"firefox: the HUD shows no numeric gold readout ({hud})"
                )
            else:
                print(f"  the top bar shows {hud['gold']} gold")

            goals = probe(
                page,
                """(() => {
                    const panel = document.querySelector('#ui .swl-goals');
                    if (!panel) return { error: 'no goals panel' };
                    return {
                        slots: panel.querySelectorAll('.swl-goal-slot').length,
                        titles: Array.from(panel.querySelectorAll('.swl-goal-title'))
                            .map((e) => e.textContent.trim()).filter(Boolean),
                    };
                })()""",
            )
            if goals.get("error"):
                failures.append(f"firefox: {goals['error']}")
            elif goals.get("slots") != 3:
                failures.append(
                    f"firefox: the goals panel has {goals.get('slots')} slot(s), not 3"
                )
            else:
                print(f"  the goals panel shows {goals['slots']} goal slot(s)")

            # Capture evidence, then fold any captured errors into the result.
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot))
            print(f"  screenshot: {screenshot}")

            failures.extend(f"firefox: {error}" for error in console_errors)
            if console_errors:
                print(f"  console/page errors: {len(console_errors)}")
            else:
                print("  console/page errors: none")
        finally:
            browser.close()

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--screenshot",
        type=Path,
        default=Path(tempfile.gettempdir()) / "swl-firefox-smoke.png",
        help="where to write the proof-of-boot screenshot",
    )
    args = parser.parse_args()

    try:
        import playwright  # noqa: F401
    except ImportError:
        print(
            "Playwright for Python is not installed. Provision it with:\n"
            "  python -m playwright install firefox",
            file=sys.stderr,
        )
        return 2

    if not (ROOT / "apps/client/dist/index.html").is_file():
        print(
            "the client has not been built. Run:\n"
            "  pnpm --filter @swl/app-client build",
            file=sys.stderr,
        )
        return 2

    server, url = start_server()
    try:
        failures = run_browser(url, args.screenshot)
    finally:
        server.shutdown()
        server.server_close()

    print("")
    print("  browsers run: firefox (Playwright, Gecko)")
    print(
        "  browsers not run: WebKit/Safari (not provisioned), Chrome/Edge "
        "(covered by scripts/smoke-test-client.mjs, not this script), real devices"
    )
    print("  scope: smoke only - full Firefox e2e and Safari remain NOT RUN")

    if failures:
        print("", file=sys.stderr)
        print("the client did not pass the Firefox smoke check:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1

    print("OK: the client boots, renders and lays out its DOM in Firefox (smoke).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
