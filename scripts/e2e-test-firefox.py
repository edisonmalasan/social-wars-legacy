#!/usr/bin/env python3
"""Full end-to-end play session in Firefox (Gecko), against the real server.

The Chrome/Edge end-to-end harness (``scripts/e2e-test.mjs``) drives its
browsers over the Chrome DevTools Protocol. Firefox does not speak CDP; it
speaks Juggler/BiDi, which Playwright drives. This is the Gecko counterpart:
the *same* built client, the *same* real authoritative server, and the *same*
rendered controls, but driven with Python Playwright.

What this proves, in one run
----------------------------
* a fresh player is registered through the rendered ``#signin`` form;
* the client starts and fetches its world from the real server;
* the tutorial is dismissed through its rendered Skip button;
* a building is picked from the rendered build menu and placed on the rendered
  canvas, and the server's own map records it;
* a Wood Factory is placed, selected and collected through rendered controls,
  and the server refuses an undue collection (a rendered button cannot mint
  wood);
* a unit is trained through the rendered recruitment panel and the server's
  queue records it;
* the weekly quest is opened from the rendered chapter map, fought with the
  rendered Strike / Report-kill buttons, and finished with the rendered Finish
  button; the reward rows match the wallet delta and the persisted receipt;
* a replay of the same quest is refused through the same rendered buttons and
  pays no second reward;
* after a client reload the active quest and the award are still there;
* after a full server restart, signing in again with the same credential still
  sees the award.

Nothing here fabricates an outcome. Every state change is a click on a rendered
control; the client's own request builder and transport send it, and the
server's own rules decide the result. ``window.__swl`` is *not* used to issue
commands or grant anything.

Gecko only. Safari/WebKit and real devices are NOT RUN. The G5 "run in Firefox
and Safari" roadmap checkbox stays open because it also names Safari.

Usage (from the repository root)::

    python scripts/e2e-test-firefox.py
    python scripts/e2e-test-firefox.py --screenshot path/to/shot.png
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# The script lives in <repo>/scripts; the repository root is its parent.
ROOT = Path(__file__).resolve().parent.parent

# The same three file roots as the other harnesses: the build, the generated
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
    # Offline mode ships PostgreSQL compiled to WebAssembly; a browser refuses
    # to stream it unless it is served as application/wasm.
    ".wasm": "application/wasm",
}

# The Command Center's tile (the middle of a fresh map) and the projection the
# client uses to centre on it. These are the client's own numbers
# (packages/server/src/starttown.ts, packages/client/src/{iso,camera}.ts).
COMMAND_CENTER_TILE = (48, 48)
TILE_HEIGHT_PIXELS = 54
STAGE_WIDTH = 760
STAGE_HEIGHT = 600
BUILD_OUTLINE_OFFSET_Y = 54

# The wallet keys behind the protocol's resource names (server's
# QUEST_REWARD_RESOURCE map). Test-side mirror only, never an authority.
WALLET_KEY = {
    "energy": "e", "xp": "x", "gold": "g", "wood": "w",
    "oil": "o", "steel": "s", "cash": "c", "mana": "m",
}


def free_port() -> int:
    """Reserve and release a loopback port, so no stray server can hold it."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def camera_centred_on(tx: int, ty: int):
    """The client's computed camera for a tile (camera.ts:cameraCentredOn)."""
    h = TILE_HEIGHT_PIXELS
    return {
        "topX": STAGE_WIDTH / 2 + h * (ty - tx),
        "topY": STAGE_HEIGHT / 2 + BUILD_OUTLINE_OFFSET_Y - (h / 2) * (tx + ty) + h / 2,
    }


CAMERA = camera_centred_on(*COMMAND_CENTER_TILE)


def tile_to_pixel(tx: int, ty: int):
    """The client's projection (iso.ts:tileToPixel) for a fresh camera."""
    h = TILE_HEIGHT_PIXELS
    top_y = CAMERA["topY"] - BUILD_OUTLINE_OFFSET_Y
    return {
        "x": CAMERA["topX"] - h * ty + h * tx,
        "y": top_y + h * 0.5 * ty + h * 0.5 * tx - h / 2,
    }


def make_handler(api_port: int):
    """A static-file handler that proxies /api/* to the real server."""

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):
            pass  # keep the e2e output clean

        def _send(self, code: int, content_type: str, body: bytes):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def do_GET(self):
            self._route("GET")

        def do_POST(self):
            self._route("POST")

        def _route(self, method: str):
            parsed = urllib.parse.urlsplit(self.path)
            path = parsed.path

            # The API goes to the REAL server, so the client talks to the same
            # server it would in production. The request's own headers (most
            # importantly Authorization) are forwarded.
            if path.startswith("/api/") or path == "/health":
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else None
                headers = {}
                content_type = self.headers.get("Content-Type")
                if content_type:
                    headers["Content-Type"] = content_type
                authorization = self.headers.get("Authorization")
                if authorization:
                    headers["Authorization"] = authorization
                upstream = urllib.request.Request(
                    f"http://127.0.0.1:{api_port}{self.path}",
                    data=body,
                    headers=headers,
                    method=method,
                )
                try:
                    with urllib.request.urlopen(upstream, timeout=30) as response:
                        payload = response.read()
                        status = response.status
                        content_type = response.headers.get("Content-Type", "application/json")
                except urllib.error.HTTPError as error:
                    payload = error.read()
                    status = error.code
                    content_type = error.headers.get("Content-Type", "application/json")
                except Exception:
                    payload = b'{"error": "the server is not reachable"}'
                    status = 502
                    content_type = "application/json"
                self._send(status, content_type, payload)
                return

            relative = path.lstrip("/") or "index.html"
            if relative == "favicon.ico":
                self._send(204, "text/plain", b"")
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
                content_type = (
                    TYPES.get(file.suffix.lower())
                    or mimetypes.guess_type(file.name)[0]
                    or "application/octet-stream"
                )
                try:
                    with file.open("rb") as stream:
                        payload = stream.read()
                except OSError:
                    continue
                self._send(200, content_type, payload)
                return
            self._send(404, "text/plain", b"not found")

    return Handler


def start_static_server(api_port: int):
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(api_port))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.server_address[1]
    return server, port


def start_server(data_dir: Path, port: int):
    """Start the real server on ``port`` and wait for /health to answer."""
    node = shutil.which("node") or "node"
    env = os.environ.copy()
    env["SWL_DATA_DIR"] = str(data_dir)
    env["PORT"] = str(port)
    child = subprocess.Popen(
        [node, "apps/server/src/main.ts"],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    output: list[str] = []

    def drain():
        # The Node harness reads the child's output continuously for the same
        # reason: an undrained pipe fills up and blocks the server process.
        assert child.stdout is not None
        for line in child.stdout:
            output.append(line.rstrip())
            if len(output) > 200:
                output.pop(0)

    threading.Thread(target=drain, daemon=True).start()
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if child.poll() is not None:
            raise RuntimeError("the server exited early:\n" + "\n".join(output))
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                if response.status == 200:
                    return child, output
        except Exception:
            pass
        time.sleep(0.2)
    child.kill()
    raise RuntimeError("the server did not start:\n" + "\n".join(output))


def stop_server(child: subprocess.Popen):
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()


# --------------------------------------------------------------------------
# Small Playwright helpers. DOM conditions use wait_for_function (no fixed
# sleeps); server-state polls use a short interval until a condition is met.
# --------------------------------------------------------------------------

def wait_status(page, timeout: int = 60_000):
    page.wait_for_function(
        """() => {
            const e = document.getElementById('status');
            if (!e) return false;
            const s = e.getAttribute('data-state');
            return s === 'started' || s === 'failed';
        }""",
        timeout=timeout,
    )
    return page.evaluate(
        """(() => {
            const e = document.getElementById('status');
            return { state: e.getAttribute('data-state'), detail: e.textContent || '' };
        })()"""
    )


def wait_js(page, js_bool: str, label: str, timeout: int = 15_000):
    try:
        page.wait_for_function(js_bool, timeout=timeout)
    except Exception as error:
        raise RuntimeError(f"the interface never showed {label} ({error})") from error


def click_and_wait(page, selector: str, signature: str, label: str, timeout: int = 15_000):
    """Click a rendered control and wait for a named signature to change."""
    before = page.evaluate(f"JSON.stringify(({signature}))")
    clicked = page.evaluate(
        """(s) => {
            const e = document.querySelector(s);
            if (!e) return { error: 'no control for ' + s };
            e.click();
            return { ok: true };
        }""",
        selector,
    )
    if not clicked or clicked.get("error"):
        raise RuntimeError(clicked.get("error") if clicked else f"the {label} could not be clicked")
    wait_js(
        page,
        f"() => JSON.stringify(({signature})) !== {json.dumps(before)}",
        f"the {label} to take effect",
        timeout,
    )
    return page.evaluate(signature)


def click_plain(page, selector: str, label: str):
    clicked = page.evaluate(
        """(s) => {
            const e = document.querySelector(s);
            if (!e) return { error: 'no control for ' + s };
            e.click();
            return { ok: true };
        }""",
        selector,
    )
    if not clicked or clicked.get("error"):
        raise RuntimeError(clicked.get("error") if clicked else f"the {label} could not be clicked")


def tile_click(page, tx: int, ty: int):
    """A player's canvas pointer gesture on a tile's projected top corner."""
    pixel = tile_to_pixel(tx, ty)
    result = page.evaluate(
        """([x, y]) => {
            const canvas = document.querySelector('#game canvas');
            if (!canvas) return { error: 'the client has no canvas' };
            const rect = canvas.getBoundingClientRect();
            const px = rect.left + (x / canvas.width) * rect.width;
            const py = rect.top + (y / canvas.height) * rect.height;
            const top = document.elementFromPoint(px, py);
            if (top !== canvas) {
                return { error: 'tile is covered by ' + (top?.className || top?.tagName) };
            }
            canvas.dispatchEvent(new PointerEvent('pointerdown', {
                clientX: px, clientY: py, bubbles: true, cancelable: true,
                pointerId: 1, isPrimary: true, pointerType: 'mouse',
            }));
            return { ok: true };
        }""",
        [pixel["x"], pixel["y"]],
    )
    if not result or result.get("error"):
        raise RuntimeError(result.get("error") if result else f"tile {tx},{ty} could not be clicked")


def world_of(context, server_port: int, token: str):
    response = context.request.get(
        f"http://127.0.0.1:{server_port}/api/world",
        headers={"Authorization": f"Bearer {token}"},
    )
    if not response.ok:
        raise RuntimeError(f"the world was not served ({response.status})")
    return response.json()


def world_wait(context, server_port: int, token: str, predicate, label: str, timeout: int = 15_000):
    """Poll the server's world until ``predicate(world)`` agrees."""
    deadline = time.monotonic() + timeout / 1000
    last = None
    while time.monotonic() < deadline:
        last = world_of(context, server_port, token)
        if predicate(last):
            return last
        time.sleep(0.15)
    raise RuntimeError(f"the world never showed {label} (last: {json.dumps(last)})")


def cash_of(world) -> float:
    return float((world or {}).get("resources", {}).get("c") or 0)


# Exact selectors, from scripts/e2e-test.mjs.
INFO_NAME = "document.querySelector('#ui .swl-info .swl-info-name')?.textContent ?? ''"
FEEDBACK = "document.querySelector('#ui .swl-feedback')?.textContent ?? ''"
PLACING_TEXT = "document.querySelector('#ui .swl-placing')?.textContent ?? ''"
RECRUIT_TITLE = "document.querySelector('#ui .swl-recruit .swl-recruit-title')?.textContent ?? ''"
COUNTDOWN = "document.querySelector('#ui .swl-recruit .swl-recruit-countdown')?.textContent ?? ''"
DIALOG_TITLE = "document.querySelector('#ui .swl-dialog-title')?.textContent ?? ''"
WON_TEXT = "document.querySelector('#ui .swl-dialog .swl-quest-won')?.textContent ?? ''"
LOST_TEXT = "document.querySelector('#ui .swl-dialog .swl-quest-lost')?.textContent ?? ''"
ROSTER_COUNT = "document.querySelectorAll('#ui .swl-dialog .swl-quest-roster .swl-quest-unit').length"
KILLED = """(() => {
    const rows = Array.from(document.querySelectorAll('#ui .swl-dialog .swl-quest-counter'));
    const row = rows.find((r) => r.querySelector('dt')?.textContent === 'botsKilled');
    return row ? Number(row.querySelector('dd')?.textContent ?? 0) : 0;
})()"""
SLOT_SELECTOR = "#ui .swl-chapter:first-child .swl-chapter-quests > button:first-child"


def factory_of(world):
    return next(
        (
            tuple_
            for tuple_ in (world or {}).get("maps", [{}])[0].get("items", {}).values()
            if int(tuple_[0]) == 2 and int(tuple_[1]) == 46 and int(tuple_[2]) == 46
        ),
        None,
    )


def play_session(page, context, server_port: int, player_id: str, password: str):
    """Drive the whole gameplay loop through rendered controls."""
    # --- registration through the rendered form ---------------------------
    # A fresh player: no stored session, so the client shows #signin.
    page.evaluate("window.localStorage.removeItem('swl.session'); true")
    page.reload(wait_until="domcontentloaded", timeout=30_000)
    wait_js(page, "!!document.querySelector('#signin')", "the account form")

    submitted = page.evaluate(
        """(info) => {
            const form = document.querySelector('#signin');
            const register = form.querySelector('button[data-mode="register"]');
            if (!register) return { error: 'the form has no Register mode' };
            register.click();
            const name = form.querySelector('input[name="playerId"]');
            const secret = form.querySelector('input[name="password"]');
            if (!name || !secret) return { error: 'the form has no credential fields' };
            name.value = info[0];
            secret.value = info[1];
            form.requestSubmit();
            return { ok: true };
        }""",
        [player_id, password],
    )
    if not submitted or submitted.get("error"):
        raise RuntimeError(submitted.get("error") if submitted else "the form did not submit")

    signed = wait_status(page)
    if signed["state"] != "started":
        raise RuntimeError(f"the client said {signed['state']} ({signed['detail']})")
    session = page.evaluate("JSON.parse(window.localStorage.getItem('swl.session') || 'null')")
    if not session or not session.get("token"):
        raise RuntimeError("the registration remembered no session")
    token = session["token"]
    print(f"  UI: registered \"{player_id}\" through the rendered form", flush=True)

    # --- tutorial through its rendered Skip button ------------------------
    click_and_wait(
        page,
        "#ui .swl-tutorial-skip",
        "!!document.querySelector('#ui .swl-tutorial')",
        "tutorial Skip button",
    )
    wait_js(page, "!document.querySelector('#ui .swl-tutorial')", "the tutorial to close")
    print("  UI: skipped the tutorial with its rendered button", flush=True)

    # --- the 760x600 layout: the HUD and inventory must not overlap -------
    layout = page.evaluate(
        """(() => {
            const rect = (s) => {
                const e = document.querySelector(s);
                if (!e) return null;
                const r = e.getBoundingClientRect();
                return { left: r.left, top: r.top, right: r.right, bottom: r.bottom };
            };
            const stage = document.querySelector('#stage');
            return {
                stage: rect('#stage'), hud: rect('#ui .swl-hud'),
                inventory: rect('#ui .swl-inventory'),
                stageCss: stage ? {
                    width: getComputedStyle(stage).width,
                    height: getComputedStyle(stage).height,
                } : null,
            };
        })()"""
    )
    if not layout.get("stage") or not layout.get("hud") or not layout.get("inventory"):
        raise RuntimeError("the HUD or the inventory is missing from the 760x600 layout")
    if layout["stageCss"].get("width") != "760px" or layout["stageCss"].get("height") != "600px":
        raise RuntimeError(f"the stage is not 760x600: {layout['stageCss']}")
    hud, inv = layout["hud"], layout["inventory"]
    overlap = not (
        hud["right"] <= inv["left"] or inv["right"] <= hud["left"]
        or hud["bottom"] <= inv["top"] or inv["bottom"] <= hud["top"]
    )
    if overlap:
        raise RuntimeError(f"the HUD overlaps the inventory: {layout}")
    if inv["right"] > layout["stage"]["right"] + 0.5 or inv["bottom"] > layout["stage"]["bottom"] + 0.5:
        raise RuntimeError(f"the inventory falls outside the stage: {layout}")
    print(
        f"  UI: at 760x600 the HUD ends at y={hud['bottom']:.0f} "
        f"and the inventory starts at y={inv['top']:.0f} (no overlap)",
        flush=True,
    )

    # --- build and place a building through rendered controls -------------
    before_build = world_of(context, server_port, token)
    before_items = len((before_build or {}).get("maps", [{}])[0].get("items", {}))
    click_and_wait(
        page,
        "#ui .swl-build-menu .swl-build-item:not(.swl-build-locked) button",
        PLACING_TEXT,
        "build-menu item",
    )
    # The first unlocked item is a 4x4 building, so the tile must clear the
    # Command Center's own 4x4 footprint at 48,48.
    tile_click(page, 52, 51)
    wait_js(page, "!document.querySelector('#ui .swl-placing')", "the build to be placed")
    after_build = world_of(context, server_port, token)
    items = (after_build or {}).get("maps", [{}])[0].get("items", {})
    if len(items) != before_items + 1:
        raise RuntimeError(
            f"the rendered build did not add a building to the server's map "
            f"({before_items} -> {len(items)}; feedback: {page.evaluate(FEEDBACK)!r})"
        )
    if not any(int(t[1]) == 52 and int(t[2]) == 51 for t in items.values()):
        raise RuntimeError("the rendered build did not place the item on the clicked tile")
    print("  UI: picked a build-menu item and placed it on a tile through the canvas", flush=True)

    # --- a Wood Factory, then a rendered Collect the server must refuse ---
    factory_pick = page.evaluate(
        """() => {
            const items = Array.from(document.querySelectorAll(
                '#ui .swl-build-menu .swl-build-item:not(.swl-build-locked) button'));
            const item = items.find((b) =>
                b.querySelector('.swl-build-name')?.textContent === 'Wood Factory I');
            if (!item) return { error: 'the build menu has no Wood Factory I' };
            item.click();
            return { ok: true };
        }"""
    )
    if not factory_pick or factory_pick.get("error"):
        raise RuntimeError(factory_pick.get("error") if factory_pick else "the factory could not be picked")
    wait_js(page, f"{PLACING_TEXT}.includes('Wood Factory I')", "the Wood Factory placement")
    tile_click(page, 46, 46)
    wait_js(page, "!document.querySelector('#ui .swl-placing')", "the Wood Factory to be placed")
    if factory_of(world_of(context, server_port, token)) is None:
        raise RuntimeError("the Wood Factory was not placed by the rendered canvas click")

    tile_click(page, 46, 46)
    wait_js(page, f"{INFO_NAME} === 'Wood Factory I'", "the Wood Factory info panel")
    wood_before = float((world_of(context, server_port, token) or {}).get("resources", {}).get("w") or 0)
    click_plain(page, "#ui .swl-info button.swl-info-collect", "Collect button")
    wait_js(page, f"/refused|not-due|collect/i.test({FEEDBACK})", "the server answer to Collect")
    collect_answer = str(page.evaluate(FEEDBACK))
    if not re.search(r"not-due", collect_answer, re.I):
        raise RuntimeError(f"the Collect gesture drew an unexpected answer: {collect_answer}")
    wood_after = float((world_of(context, server_port, token) or {}).get("resources", {}).get("w") or 0)
    if wood_after != wood_before:
        raise RuntimeError("the client changed wood before the server said the collection was due")
    print(
        f"  UI: the rendered Collect button asked the server, which refused "
        f"an undue cycle (\"{collect_answer.strip()}\") and granted no wood",
        flush=True,
    )

    # --- train a unit through the rendered recruitment panel --------------
    tile_click(page, *COMMAND_CENTER_TILE)
    wait_js(page, f"{RECRUIT_TITLE}.includes('Command Center')", "the Command Center recruitment panel")
    click_and_wait(page, "#ui .swl-recruit button.swl-recruit-train", COUNTDOWN, "Train button")
    countdown = str(page.evaluate(COUNTDOWN))
    if not re.search(r"Training|queued", countdown, re.I):
        raise RuntimeError(f"the training queue did not start (\"{countdown}\")")
    trained = world_of(context, server_port, token)
    cc = next(
        (t for t in (trained or {}).get("maps", [{}])[0].get("items", {}).values() if int(t[0]) == 26),
        None,
    )
    if not (int((cc or [None, None, None, None, None, None, {}])[6].get("nu") or 0) >= 1):
        raise RuntimeError("the server did not record the trained unit in the queue")
    print(f"  UI: trained a unit ({countdown})", flush=True)

    # --- weekly quest, opened from the rendered chapter map ----------------
    slot = page.evaluate(
        """(s) => {
            const e = document.querySelector(s);
            return e ? { tag: e.tagName, title: e.getAttribute('title') } : null;
        }""",
        SLOT_SELECTOR,
    )
    if not slot or slot["tag"] != "BUTTON":
        raise RuntimeError("the open weekly quest slot is not a rendered button")
    cash_before_quest = cash_of(world_of(context, server_port, token))

    click_and_wait(page, SLOT_SELECTOR, DIALOG_TITLE, "weekly quest slot")
    radios = page.evaluate(
        "document.querySelectorAll('#ui .swl-dialog .swl-quest-difficulty input[type=radio]').length"
    )
    if radios != 3:
        raise RuntimeError(f"the briefing drew {radios} difficulty choices, not 3")
    team_picker = page.evaluate("!!document.querySelector('#ui .swl-dialog [data-swl-team-picker]')")
    if team_picker is not False:
        raise RuntimeError("a non-team quest drew a team picker")

    click_and_wait(page, "#ui .swl-dialog button.swl-quest-primary", ROSTER_COUNT, "Start mission button")
    roster_size = int(page.evaluate(ROSTER_COUNT))
    # The roster is drawn from the server's active quest, so its size is the
    # honest, content-derived number of bots the player must defeat.
    if roster_size < 1:
        raise RuntimeError("the quest roster was empty")
    print(f"  UI: opened the weekly quest from the chapter map ({roster_size} roster rows)", flush=True)

    combat_signature = (
        "JSON.stringify({"
        "c: document.querySelector('#ui .swl-dialog .swl-quest-counters')?.textContent ?? '',"
        "r: document.querySelector('#ui .swl-dialog .swl-quest-roster')?.textContent ?? ''"
        "})"
    )
    reported = False
    for _ in range(16):
        if int(page.evaluate(KILLED)) >= roster_size:
            break
        has_kill_report = page.evaluate(
            '!!document.querySelector(\'#ui .swl-dialog button[data-swl-action="kill-report"]\')'
        )
        if has_kill_report and not reported:
            click_plain(page, '#ui .swl-dialog button[data-swl-action="kill-report"]', "Report kill button")
            world_wait(
                context, server_port, token,
                lambda w: len(((w or {}).get("privateState", {}).get("activeQuest", {}) or {}).get("script", {}).get("destroyed") or []) >= 1,
                "the server to record the reported kill",
            )
            reported = True
            print("  UI: reported a server-verified kill with the two-argument builder", flush=True)
            continue
        wait_js(
            page,
            'document.querySelectorAll(\'#ui .swl-dialog button[data-swl-action="strike"]:not([disabled])\').length >= 1',
            "an enabled Strike button after the previous request settled",
        )
        click_and_wait(
            page,
            '#ui .swl-dialog button[data-swl-action="strike"]:not([disabled])',
            combat_signature,
            "Strike button",
        )
    if not reported:
        raise RuntimeError("no dead element ever offered the two-argument Report kill")
    if int(page.evaluate(KILLED)) < roster_size:
        raise RuntimeError(f"the rendered strikes did not move botsKilled to {roster_size}")
    print(f"  UI: strikes on {roster_size} rendered roster rows moved the kill counter", flush=True)

    # --- finish: the server decides the win and pays the reward -----------
    wallet_before_finish = world_of(context, server_port, token)
    click_and_wait(page, '#ui .swl-dialog button[data-swl-action="end"]', WON_TEXT, "Finish quest button")
    won_text = str(page.evaluate(WON_TEXT))
    if not re.search(r"server completed", won_text, re.I):
        raise RuntimeError(f"the victory dialog did not confirm the server's win: {won_text}")
    result_text = str(page.evaluate("document.querySelector('#ui .swl-dialog')?.textContent ?? ''"))
    print(f"  UI: the server's result dialog read \"{result_text.strip()}\"", flush=True)

    awarded = world_of(context, server_port, token)
    weekly_id = _weekly_id(awarded)
    play_index = _weekly_play_index(awarded)
    progress = (awarded or {}).get("privateState", {}).get("questProgress", {}) or {}
    if weekly_id not in (progress.get("awarded") or []):
        raise RuntimeError("the server did not record the weekly award")
    if float((progress.get("ranks") or {}).get(str(play_index)) or 0) < 1:
        raise RuntimeError("the server did not record the weekly rank")
    if cash_of(awarded) <= cash_before_quest:
        raise RuntimeError("the server paid no cash for the weekly quest")

    reward_rows = page.evaluate(
        """Array.from(document.querySelectorAll(
                '#ui .swl-dialog [data-swl-rewards] [data-swl-reward]')).map((li) => ({
            resource: li.getAttribute('data-swl-reward'),
            text: li.textContent ?? '',
            amount: Number((li.textContent ?? '').split('+').pop().trim()),
        }))"""
    )
    if not isinstance(reward_rows, list) or len(reward_rows) == 0:
        raise RuntimeError("the result dialog drew no authoritative reward rows")
    wallet_before = (wallet_before_finish or {}).get("resources", {}) or {}
    wallet_after = (awarded or {}).get("resources", {}) or {}
    for row in reward_rows:
        key = WALLET_KEY.get(row["resource"])
        if not key:
            raise RuntimeError(f"the result named an unknown resource: {row['resource']}")
        if not isinstance(row["amount"], (int, float)) or row["amount"] != row["amount"]:  # NaN guard
            raise RuntimeError(f"the {row['resource']} row has no amount: {row['text']!r}")
        delta = float(wallet_after.get(key) or 0) - float(wallet_before.get(key) or 0)
        if delta != float(row["amount"]):
            raise RuntimeError(f"the {row['resource']} row says +{row['amount']} but the server paid {delta}")
    receipt = (awarded or {}).get("privateState", {}).get("lastQuestReward")
    if not receipt or receipt.get("questId") != weekly_id or not isinstance(receipt.get("rewards"), list):
        raise RuntimeError(f"the server kept no reward receipt: {json.dumps(receipt)}")
    if len(receipt["rewards"]) != len(reward_rows):
        raise RuntimeError("the receipt and the rendered rows disagree on their length")
    for index, row in enumerate(reward_rows):
        stored = receipt["rewards"][index]
        if stored.get("resource") != row["resource"] or float(stored.get("amount") or 0) != float(row["amount"]):
            raise RuntimeError(f"receipt row {index} disagrees with the rendered row")
    reward_summary = ", ".join("{} +{}".format(r["resource"], r["amount"]) for r in reward_rows)
    print(
        f"  UI: {len(reward_rows)} reward row(s) match the wallet delta and the persisted receipt "
        f"({reward_summary})",
        flush=True,
    )

    # --- a replay must not pay twice --------------------------------------
    click_and_wait(page, "#ui .swl-dialog button.swl-dialog-close", "!!document.querySelector('#ui .swl-dialog')", "reward dialog Close button")
    cash_before_replay = cash_of(world_of(context, server_port, token))
    click_and_wait(page, SLOT_SELECTOR, DIALOG_TITLE, "weekly quest slot on replay")
    click_and_wait(page, "#ui .swl-dialog button.swl-quest-primary", ROSTER_COUNT, "Start mission button on replay")
    for _ in range(16):
        if int(page.evaluate(KILLED)) >= roster_size:
            break
        click_and_wait(
            page,
            '#ui .swl-dialog button[data-swl-action="strike"]:not([disabled])',
            combat_signature,
            "Strike button on replay",
        )
    click_and_wait(page, '#ui .swl-dialog button[data-swl-action="end"]', LOST_TEXT, "Finish quest button on replay")
    refusal = str(page.evaluate(LOST_TEXT))
    if not re.search(r"already-awarded|not finished", refusal, re.I):
        raise RuntimeError(f"the replay produced no refusal dialog (\"{refusal}\")")
    after_replay = world_of(context, server_port, token)
    if cash_of(after_replay) != cash_before_replay:
        raise RuntimeError(f"the replay paid a second reward ({cash_before_replay} -> {cash_of(after_replay)})")
    awards = ((after_replay or {}).get("privateState", {}).get("questProgress", {}) or {}).get("awarded") or []
    if awards.count(weekly_id) != 1:
        raise RuntimeError(f"the server's award list is not unique: {json.dumps(awards)}")
    print(f"  UI: replay refused with \"{refusal.strip()}\" and paid no second reward", flush=True)

    # --- reload: the active quest and the award survive -------------------
    page.reload(wait_until="domcontentloaded", timeout=30_000)
    reloaded = wait_status(page)
    if reloaded["state"] != "started":
        raise RuntimeError(f"the reloaded client said {reloaded['state']} ({reloaded['detail']})")
    wait_js(page, "!!document.querySelector('#ui .swl-dialog .swl-quest-roster')", "the restored combat dialog")
    persisted = world_of(context, server_port, token)
    if weekly_id not in (((persisted or {}).get("privateState", {}).get("questProgress", {}) or {}).get("awarded") or []):
        raise RuntimeError("the award did not survive the client reload")
    if not (persisted or {}).get("privateState", {}).get("activeQuest"):
        raise RuntimeError("the active quest did not survive the client reload")
    print("  UI: after a client reload the active quest and the server award are still there", flush=True)

    return {
        "playerId": player_id,
        "password": password,
        "weeklyId": weekly_id,
        "playIndex": play_index,
        "receipt": {"questId": receipt.get("questId"), "rank": receipt.get("rank"), "rewards": receipt.get("rewards")},
    }


def _weekly_id(world) -> str:
    """The weekly quest id from the server's active quest or award list."""
    private = (world or {}).get("privateState", {}) or {}
    active = private.get("activeQuest") or {}
    if active.get("questId"):
        return str(active["questId"])
    # After the win the active quest is cleared; take the freshly awarded id
    # that is not the one the player had before (exactly one new award here).
    progress = private.get("questProgress", {}) or {}
    awarded = progress.get("awarded") or []
    if awarded:
        return str(awarded[0])
    raise RuntimeError("the server's world named no weekly quest id")


def _weekly_play_index(world) -> int:
    """The weekly quest's play index, from the server's own rank record."""
    progress = ((world or {}).get("privateState", {}) or {}).get("questProgress", {}) or {}
    ranks = progress.get("ranks") or {}
    # The weekly mission is playIndex 0 (rules/quest.ts); its rank is present
    # after the win. Prefer that key when it exists.
    if "0" in ranks:
        return 0
    if ranks:
        return int(next(iter(ranks)))
    return 0


def run_browser(server_port: int, client_port: int, data_dir: Path, screenshot: Path):
    """Run the full Firefox session. Returns (ran, failures, console_errors)."""
    from playwright.sync_api import sync_playwright

    player_id = "e2e-ui-firefox"
    password = "correct horse"
    failures: list[str] = []
    console_errors: list[str] = []
    ran = False
    restart_port = free_port()
    restart_child = None

    with sync_playwright() as playwright:
        browser = playwright.firefox.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()

            def on_console(message):
                if message.type == "error":
                    console_errors.append(f"console.error: {message.text}")

            def on_page_error(error):
                console_errors.append(f"pageerror: {error}")

            page.on("console", on_console)
            page.on("pageerror", on_page_error)

            print("  firefox: ", end="", flush=True)
            server, _ = start_server(data_dir, server_port)
            try:
                url = f"http://127.0.0.1:{client_port}/"
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                player = play_session(page, context, server_port, player_id, password)
                ran = True
                print("session played", flush=True)

                screenshot.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(screenshot))
                print(f"  screenshot: {screenshot}", flush=True)

                # --- restart the real server over the same database ---------
                stop_server(server)
                restart_child, _ = start_server(data_dir, restart_port)
                print("  the server was restarted with the same database", flush=True)
                sign_in = context.request.post(
                    f"http://127.0.0.1:{restart_port}/api/session",
                    data=json.dumps({
                        "playerId": player["playerId"],
                        "password": player["password"],
                    }),
                    headers={"Content-Type": "application/json"},
                )
                if sign_in.status != 200:
                    raise RuntimeError(f"the player could not sign in after the restart: {sign_in.status}")
                fresh_token = sign_in.json()["token"]
                persisted = world_of(context, restart_port, fresh_token)
                progress = ((persisted or {}).get("privateState", {}) or {}).get("questProgress", {}) or {}
                if player["weeklyId"] not in (progress.get("awarded") or []):
                    raise RuntimeError("the weekly award did not survive the server restart")
                if float((progress.get("ranks") or {}).get(str(player["playIndex"])) or 0) < 1:
                    raise RuntimeError("the weekly rank did not survive the server restart")
                receipt = ((persisted or {}).get("privateState", {}) or {}).get("lastQuestReward")
                expected = player["receipt"]
                same = (
                    receipt
                    and receipt.get("questId") == expected["questId"]
                    and float(receipt.get("rank") or 0) == float(expected["rank"] or 0)
                    and isinstance(receipt.get("rewards"), list)
                    and len(receipt["rewards"]) == len(expected["rewards"])
                    and all(
                        r.get("resource") == e["resource"] and float(r.get("amount") or 0) == float(e["amount"])
                        for r, e in zip(receipt["rewards"], expected["rewards"])
                    )
                )
                if not same:
                    raise RuntimeError("the reward receipt did not survive the server restart")
                print(
                    f"  {player['playerId']} signed in again and {player['weeklyId']} "
                    "was still awarded, with the same receipt",
                    flush=True,
                )
            except Exception as error:
                failures.append(f"firefox: {error}")
                print(f"FAILED ({error})", flush=True)
            finally:
                stop_server(server)
                if restart_child is not None:
                    stop_server(restart_child)
        finally:
            browser.close()

    if console_errors:
        failures.extend(f"firefox: {error}" for error in console_errors)
        print(f"  console/page errors: {len(console_errors)}", flush=True)
    else:
        print("  console/page errors: none", flush=True)

    return ran, failures, console_errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--screenshot",
        type=Path,
        default=Path(tempfile.gettempdir()) / "swl-firefox-e2e.png",
        help="where to write the proof-of-session screenshot",
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
    if not (ROOT / "packages/content/dist/content-bundle.json").is_file():
        print("the content bundle has not been built. Run: pnpm build:content", file=sys.stderr)
        return 2

    data_dir = Path(tempfile.mkdtemp(prefix="swl-ff-e2e-"))
    server_port = free_port()
    static, client_port = start_static_server(server_port)
    try:
        ran, failures, _ = run_browser(server_port, client_port, data_dir, args.screenshot)
    finally:
        static.shutdown()
        static.server_close()
        shutil.rmtree(data_dir, ignore_errors=True)

    print("")
    print("  browsers run: firefox (Playwright, Gecko)")
    print(
        "  browsers not run: WebKit/Safari (not provisioned), Chrome/Edge "
        "(covered by scripts/e2e-test.mjs and scripts/smoke-test-client.mjs), real devices"
    )
    print("  scope: full Firefox gameplay session; Safari/WebKit and devices NOT RUN")

    if failures:
        print("", file=sys.stderr)
        print("the Firefox end-to-end session failed:", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    if not ran:
        print("no Firefox browser was available to play in.", file=sys.stderr)
        return 2

    print("OK: a player registered, played and signed in again after a server restart in Firefox.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
