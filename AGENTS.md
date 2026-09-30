# AGENTS.md

## Project overview

Social Wars is a preservation-first reconstruction of the original Flash game into a modern, Flash-free client/server application.

The existing Flask/Flash implementation is the reference implementation, behavioral oracle, protocol specification, save corpus, content source, and asset archive. The migration path is legacy Flask/JSON → Godot + Compatibility API v0 → authoritative Python API v1 + PostgreSQL.

Do not treat the legacy repository as disposable code.

---

## Stack

- Legacy server: Python + Flask
- Legacy storage: JSON save files
- Legacy client: Flash/SWF — reference only; must be retired from modern runtime
- Modern client: Godot 4.7.2.stable + GDScript `[pinned 2026-09-26 via winget package GodotEngine.GodotEngine; installed executable verified: Godot_v4.7.2-stable_win64.exe → 4.7.2.stable.official.ed1daf0bf]`
- Compatibility layer: Python
- Target server: Python + FastAPI + Pydantic + SQLAlchemy + Alembic
- Target database: PostgreSQL
- Specification workflow: OpenSpec
- Optional later infrastructure: Redis / WebSockets only when justified

---

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

---

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

Local Godot engine install (Windows x64; prerequisite for the Godot client
under `apps/client-godot/`):

```bash
winget install GodotEngine.GodotEngine --accept-package-agreements --accept-source-agreements
```

Verified 2026-09-26: running the installed `Godot_v4.7.2-stable_win64.exe`
with `--version` prints `4.7.2.stable.official.ed1daf0bf`. WinGet created no
`godot` PATH alias without administrator privileges; invoke the executable
under `%LOCALAPPDATA%\Microsoft\WinGet\Packages\GodotEngine.GodotEngine_*\`.

Verified first-render verification commands (Godot 4.7.2.stable, Windows x64
interactive session; the engine has no `godot` PATH alias — the scripts
locate the installed executable themselves):

```bash
powershell -File apps/client-godot/verify.ps1
```

This single command runs the five headless suites (package loader, scene
build, project scope, content registry, asset IDs), the comparator self-test
(expected exit 1), the windowed capture plus compare, and SHA-256 pre/post
guards over both conversion packages, the three registry manifests, the
asset-ID registry, and the canonical content package directory; it exits 0
only when everything passes. Viewport capture needs an interactive display session;
comparison and the self-test run headless. Individual engine invocations,
tolerances, and the correctness-claim limits are documented in
`apps/client-godot/README.md`; committed evidence lives under
`apps/client-godot/evidence/first-render/`. The windowed run passes
`res://scenes/first_render.tscn` explicitly, because the project's main scene
is now the boot scene.

Verified compatibility-boot verification commands (Godot 4.7.2.stable and
pinned CPython 3.9.13, Windows x64; `python` denotes the pinned interpreter,
never the PATH alias):

```bash
powershell -File apps/client-godot/verify-boot.ps1
```

This single command runs the Compatibility API guard verification before and
after, the Compatibility API unittest discovery and loopback smoke, the seventeen
headless Godot suites (package loader, scene build, fake GameApi, boot
scene, session, game clock, camera controls, UI foundation, settings,
audio manager, and the town vertical slice: projection, town state, town
scene, HUD, selection, placement, no-Flash gate), the
unreachable-endpoint scenario against a loopback port with nothing listening,
and four live
phases that start
`apps/compat-api/run.py`
on `127.0.0.1:5056` with a disposable corpus, boot the main scene, both
GameApi implementations, and one live placement against it, and tear it down
again — proving the port
is released, the corpus removed, no working-tree `saves/` exists, and (for
the placement phase) that the disposable corpus save actually mutated — then
writes `apps/client-godot/evidence/boot/boot-report.json` and exits 0 only
when every check passes. It needs no display session. The Compatibility API
commands it embeds can also be executed directly:

```bash
python -B apps/compat-api/guard_baseline.py verify
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
python -B apps/compat-api/tests/smoke_loopback.py
```

The executed-legacy fixture capture command, its exit code, and its
containment are recorded in
`tests/fixtures/godot-compatibility-boot/README.md`; that capture starts the
legacy Flask server in a disposable copy and is not re-run by either
verification command above.

Verified building-placement commands (milestone M7; Godot 4.7.2.stable and
pinned CPython 3.9.13, Windows x64; `python` denotes the pinned interpreter,
never the PATH alias):

```bash
python -B apps/compat-api/capture_placement_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_town_placement.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-09-29): the placement fixture capture
(one-shot executed-legacy `buy` oracle; exit codes and containment recorded
in `tests/fixtures/godot-building-placement/README.md`), the compat suite
including the placement envelope, `/v0/place` endpoint, and executed-legacy
parity tests (observed `Ran 90 tests ... OK`, exit `0`), the hermetic
picker-flow suite (observed 284 checks, PASS; runs without a service and
routes its transport-failure check against the dead endpoint the loop
passes), both batteries in the final state (each exit `0`; the second
embeds the `placement-live` phase that asserts a disposable corpus save
mutated), and the preservation manifest (3,258 entries, exit `0`). The
compatibility service listens on `127.0.0.1:5056` only, and every network
call in these commands is loopback. The evidence capture and report steps
are documented in `apps/client-godot/README.md` ("Building placement");
committed evidence lives under `apps/client-godot/evidence/placement/`.
Claim limits: parity covers one recorded transaction against the
fresh-player corpus (no progressed players, no other commands); the price
vector, envelope placeholders, and slot choice are derived-provisional,
never observed from the Flash client; insufficient resources reproduce the
legacy clamp, not rejection (authoritative validation belongs to Server v1
/ M13); no pixel-parity oracle exists; the committed capture runs the fake
implementation, so real-execution parity rests on the fixture-replay tests
and the live phase. No Flash, Ruffle, ActionScript, or browser executes in
any of these commands.

Verified building-purchase commands (milestone M7; Godot 4.7.2.stable and
pinned CPython 3.9.13, Windows x64; `python` denotes the pinned interpreter,
never the PATH alias):

```bash
python -B apps/compat-api/capture_purchase_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_town_purchase.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-09-29): the purchase fixture capture
(one-shot executed-legacy `buy_stored_item_cash` oracle for item 105 with the
cash price derived from its config `costs`; exit codes and containment recorded
in `tests/fixtures/godot-item-purchase/README.md`), the compat suite including
the purchase envelope, `/v0/purchase` endpoint, and executed-legacy parity
tests (observed `Ran 157 tests ... OK`, exit `0`), the hermetic purchase-flow
suite (observed 213 checks, PASS; runs without a service and routes its
transport-failure check against the dead endpoint the loop passes), both
batteries in the final state (each exit `0`; the second embeds the
`purchase-live` phase that asserts a disposable corpus save mutated), and the
preservation manifest (3,258 entries, exit `0`). The compatibility service
listens on `127.0.0.1:5056` only, and every network call in these commands is
loopback. The evidence capture and report steps are documented in
`apps/client-godot/README.md` ("Building purchase"); committed evidence lives
under `apps/client-godot/evidence/purchase/`. Claim limits: parity covers one
recorded transaction against the fresh-player corpus (no progressed players, no
other commands); the choice of `buy_stored_item_cash` and the cash-only price
derivation are derived-provisional, never observed from the Flash client, so
nothing is claimed about resource-priced storage purchases; insufficient cash
reproduces the legacy clamp, not rejection (authoritative validation belongs to
Server v1 / M13); storage is display-only (no placing from or selling out of
storage); no pixel-parity oracle exists; the committed capture runs the fake
implementation, so real-execution parity rests on the fixture-replay tests and
the live phase. No Flash, Ruffle, ActionScript, or browser executes in any of
these commands.

Verified building-move commands (milestone M7; Godot 4.7.2.stable and pinned
CPython 3.9.13, Windows x64; `python` denotes the pinned interpreter, never the
PATH alias):

```bash
python -B apps/compat-api/capture_move_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_town_move.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-09-29): the move fixture capture (one-shot
executed-legacy `move` oracle — Turret I at map slot 11 moved from `(58, 48)` to
the derived free cell `(58, 47)`; exit codes and containment recorded in
`tests/fixtures/godot-building-move/README.md`), the compat suite including the
move envelope, `/v0/move` endpoint, and executed-legacy parity tests (observed
`Ran 227 tests ... OK`, exit `0`), the hermetic move-flow suite (observed 288
checks, PASS; runs without a service and routes its transport-failure check
against the dead endpoint the loop passes), both batteries in the final state
(each exit `0`; the second embeds the `move-live` phase that asserts a
disposable corpus save mutated), and the preservation manifest (3,258 entries,
exit `0`). The compatibility service listens on `127.0.0.1:5056` only, and every
network call in these commands is loopback. The evidence capture and report
steps are documented in `apps/client-godot/README.md` ("Building move");
committed evidence lives under `apps/client-godot/evidence/building-move/`.
Claim limits: parity covers one recorded transaction against the fresh-player
corpus; the move command's argument values, the `frame`/`string` arguments
legacy discards, and the neutral price vector are derived-provisional, never
observed from the Flash client, so no claim is made about what moving costs in
the legacy client (the committed config records no move price); occupancy, the
no-op cell, and grid bounds are enforced client-side only, with no
server-authoritative validation (that belongs to Server v1 / M13); an
unaddressable legacy map key is never coerced; no pixel-parity oracle exists;
the committed capture runs the fake implementation, so real-execution parity
rests on the fixture-replay tests and the live phase. No Flash, Ruffle,
ActionScript, or browser executes in any of these commands.

Verified building-sell commands (milestone M7; Godot 4.7.2.stable and pinned
CPython 3.9.13, Windows x64; `python` denotes the pinned interpreter, never the
PATH alias):

```bash
python -B apps/compat-api/capture_sell_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_town_sell.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-09-29): the sell fixture capture (one-shot
executed-legacy `sell` oracle — Turret I at map slot 20 removed, 40 → 39
placements, every other row, the storage, the private state, and all seven
resources byte-identical; exit codes and containment recorded in
`tests/fixtures/godot-building-sell/README.md`), the compat suite including the
sell envelope, `/v0/sell` endpoint, and executed-legacy parity tests (observed
`Ran 306 tests ... OK`, exit `0`), the hermetic sell-flow suite (observed 169
checks, PASS; runs without a service and routes its transport-failure check
against the dead endpoint the loop passes), both batteries in the final state
(each exit `0`; the second embeds the `sell-live` phase that asserts a
disposable corpus save mutated), and the preservation manifest (3,258 entries,
exit `0`). The compatibility service listens on `127.0.0.1:5056` only, and every
network call in these commands is loopback. The evidence capture and report
steps are documented in `apps/client-godot/README.md` ("Building sell");
committed evidence lives under `apps/client-godot/evidence/building-sell/`.
Claim limits: parity covers one recorded transaction against the fresh-player
corpus; the derived sell reason and the neutral price vector are
derived-provisional, never observed from the Flash client, and **no refund is
claimed** (the committed configuration records no building-sale refund rule and
the legacy refund travels in client-sent deltas this contract refuses, so a sale
removes the building and changes no balance); the legacy combat `KILL` reason is
never reached because no reason is accepted from the client; sellability and
addressability are client-side rules only, with no server-authoritative
validation (that belongs to Server v1 / M13); no pixel-parity oracle exists; the
committed capture runs the fake implementation, so real-execution parity rests
on the fixture-replay tests and the live phase. No Flash, Ruffle, ActionScript,
or browser executes in any of these commands.

Verified building-store commands (milestone M7; Godot 4.7.2.stable and pinned
CPython 3.9.13, Windows x64; `python` denotes the pinned interpreter, never the
PATH alias):

```bash
python -B apps/compat-api/capture_store_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_town_store.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-09-29): the store fixture capture (one-shot
executed-legacy `store_item` oracle — the Tree at map slot 2 put into storage,
`store` `{}` to `{"905": 1}`, 40 to 39 placements, every other row, the
bought-units list, the private state, the player info, and all seven resources
byte-identical; exit codes and containment recorded in
`tests/fixtures/godot-building-store/README.md`), the compat suite including the
store envelope, the `/v0/store` endpoint with both post-execution proofs, and
executed-legacy parity tests (observed `Ran 390 tests ... OK`, exit `0`), the
hermetic store-flow suite, both batteries in the final state (each exit `0`; the
second embeds the `store-live` phase that asserts a disposable corpus save
mutated), and the preservation manifest (3,258 entries, exit `0`). The
compatibility service listens on `127.0.0.1:5056` only, and every network call
in these commands is loopback. The evidence capture and report steps are
documented in `apps/client-godot/README.md` ("Building store"); committed
evidence lives under `apps/client-godot/evidence/building-store/`. Claim limits:
parity covers one recorded transaction against the fresh-player corpus; the
command's argument value and the neutral price vector are derived-provisional,
never observed from the Flash client; **no storing cost and no capacity rule are
claimed** (the committed configuration records neither and the legacy server has
no capacity check); the bought-units list is deliberately not written by the
legacy branch; this line only moves a building *into* storage, so stored items
are not yet playable and `place_stored_item` remains open; storability and
addressability are client-side rules only, with no server-authoritative
validation (that belongs to Server v1 / M13); no pixel-parity oracle exists; the
committed capture runs the fake implementation, so real-execution parity rests
on the fixture-replay tests and the live phase. No Flash, Ruffle, ActionScript,
or browser executes in any of these commands.

Verified building-upgrade commands (milestone M7; Godot 4.7.2.stable and pinned
CPython 3.9.13, Windows x64; `python` denotes the pinned interpreter, never the
PATH alias). This is the first deliver line whose legacy contract was established
by investigation before implementation:

```bash
python -B apps/compat-api/capture_upgrade_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_town_upgrade.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-09-29): the upgrade fixture capture (one-shot
executed-legacy oracle; the request carries the derived two-command batch
`[[0,"sell",[12,"UPGR"],[0x8]],[0,"buy",[12,24,45,49,1,0,0,""],[0x8]]]` - Wall I
item 23 at map slot 12 upgraded to Wall II item 24 at the **same key and cell**, so
the row becomes `[24, 45, 49, <timestamp>, 0, [], {"nc": 0}, 1]`, the placement
count stays 40, `boughtUnits` goes `[]` to `[24]`, and every other row, the storage,
the rest of the private state, the player info, and all seven resources are
byte-identical; the reverse command order also answers `{"result":"success"}` and
leaves the key absent, which is why the endpoint proves the post-state; exit codes
and containment recorded in `tests/fixtures/godot-building-upgrade/README.md`), the
compat suite including the two-command envelope, the `/v0/upgrade` endpoint with its
`no_upgrade_path` guard and three post-execution proofs, and executed-legacy parity
tests (observed `Ran 491 tests ... OK`, exit `0`), the hermetic upgrade-flow suite
(observed 272 checks, PASS), both batteries in the final state (each exit `0`; the
second embeds the `upgrade-live` phase, which asserts the typed response reuses the
pre-request key and cell and that a disposable corpus save mutated), and the
preservation manifest (3,258 entries, exit `0`). The compatibility service listens
on `127.0.0.1:5056` only, and every network call in these commands is loopback. The
evidence capture and report steps are documented in
`apps/client-godot/README.md` ("Building upgrade"); committed evidence lives under
`apps/client-godot/evidence/building-upgrade/`. Claim limits: the composed pair is
**derived** (that the Flash client sends exactly this batch is never observed) while
its shape, reason, ordering, and result are **established**; parity covers one
recorded transaction against the fresh-player corpus; **no upgrade cost is claimed**
and the premium upgrade price field is unused; the `{"nc": 0}` construction counter
is reported but deliberately not consumed (the construction-timers deliver line owns
it); the legacy client's level gate, daily-upgrade limit, and space check are
deliberately not implemented (the level gate cannot be enforced on the committed
corpus, where the map level is 1 and no placed building's next tier is reachable at
that level); upgradability and addressability are client-side rules only, with the
endpoint enforcing structural input validity and the post-state proof, and no
server-authoritative validation (that belongs to Server v1 / M13); no pixel-parity
oracle exists; the committed capture runs the fake implementation, so real-execution
parity rests on the fixture-replay tests and the live phase. No Flash, Ruffle,
ActionScript, or browser executes in any of these commands.

Verified building-construction commands (milestone M7; Godot 4.7.2.stable and
pinned CPython 3.9.13, Windows x64; `python` denotes the pinned interpreter, never
the PATH alias). This is the second deliver line whose legacy contract was
established by investigation before implementation; the investigation record is
`docs/legacy-construction-timing.md`:

```bash
python -B apps/compat-api/capture_construction_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_town_construction.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-09-29): the construction fixture capture
(one-shot executed-legacy oracle; the request carries the derived two-command batch
`[[0,"activate",[11,5],[0x8]],[0,"add_click",[11],[0x8]]]` - the Turret I (item 22) at
map slot 11 started at its committed build time of 5 seconds and given one build
click, so the row becomes `[22, 58, 48, <start time>, 0, [], {"cp": 5, "nc": 1}, 1]`
while the placement count stays 40 and the whole private state, the storage, the
player info, and all seven resources are byte-identical; the completing command is
recorded but not captured, with its effect established by the earlier investigation
probe and covered by the endpoint's `finish` post-execution proof; exit codes and
containment recorded in `tests/fixtures/godot-building-construction/README.md`), the
compat suite including the three command derivations, the `/v0/construction`
endpoint with its closed action set, its content-derived start duration, its
`no_build_time` guard, and its per-action post-execution proofs, and executed-legacy
parity tests (observed `Ran 616 tests ... OK`, exit `0`), the hermetic
construction-flow suite (observed 363 checks, PASS), both batteries in the final
state (each exit `0`; the second embeds the `construction-live` phase, which walks
one row through start, click, and finish, asserts each typed response and its
post-condition, and asserts that a disposable corpus save mutated), and the
preservation manifest (3,258 entries, exit `0`). The compatibility service listens
on `127.0.0.1:5056` only, and every network call in these commands is loopback. The
evidence capture and report steps are documented in `apps/client-godot/README.md`
("Building construction"); committed evidence lives under
`apps/client-godot/evidence/building-construction/`. Claim limits: the three
commands and the start duration are **derived**, never observed from the Flash
client, while their shapes, effects, and recorded result are **established**;
parity covers one recorded transaction against the fresh-player corpus; **no
building cost is claimed** and the speedup prices are out of scope; the click
threshold and the remaining time are client-side derivations with no server
enforcement, and the steps are player-triggered; friend assistance is out of scope;
the attribute-bag-clearing command is never used as a cancel; a running countdown
with a consumed counter is indistinguishable from a freshly started build, so the
flow offers no step in-session and a finished build can be clicked again after a
view rebuild, which is what the legacy command permits; the `no_build_time` refusal
is exercised through an in-memory row because no placed building in the corpus has
a non-positive committed build time; buildability and addressability are
client-side rules only, with the endpoint enforcing structural input validity and
the per-action proof, and no server-authoritative validation (that belongs to
Server v1 / M13); no pixel-parity oracle exists; the committed capture runs the fake
implementation, so real-execution parity rests on the fixture-replay tests and the
live phase. No Flash, Ruffle, ActionScript, or browser executes in any of these
commands.

Verified building-collect commands (milestone M7; Godot 4.7.2.stable and pinned
CPython 3.9.13, Windows x64; `python` denotes the pinned interpreter, never the
PATH alias). This is the first deliver line whose resource vector is **derived
from committed content** rather than refused, and its six derivation rules were
resolved in the change's design after the committed investigation
`docs/legacy-collect-income.md`:

```bash
python -B apps/compat-api/capture_collect_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_town_collect.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-09-30): the collect fixture capture (one-shot
executed-legacy oracle; the request carries the content-derived top-rung vector
`[[0,"collect",[2],[0,3,0,60,0,0,0,0]]]` - the Tree (item 905) at map slot 2,
which has never been collected so the elapsed time is unbounded and the top
committed rung is deterministic, so the row becomes
`[905, 53, 39, <collection instant>, 0, [], {}, 1]` with **only** `item[3]`
changing, `xp 4` to `7` and `wood 2000` to `2060`, the placement count still 40,
and every other row, the storage, the private state, the player info, and the
other five resources byte-identical; a second probe recorded in the fixture's
README and manifest is the evidence for the shared-field refusal - a collection on
a just-started construction overwrites the build's start instant while the
countdown survives and the legacy server answers success; exit codes and
containment recorded in `tests/fixtures/godot-building-collect/README.md`), the
compat suite including the payout derivation, the `/v0/collect` endpoint with its
five 409 refusals (`no_income`, `capped_collection`, `unknown_collect_type`,
`too_early`, `construction_in_progress`) and its two-part post-execution proof
that checks the collection instant moved forward **and** every stored resource
changed by exactly the derived delta, and executed-legacy parity tests (observed
`Ran 768 tests ... OK`, exit `0`), the hermetic collection-flow suite (observed
379 checks, PASS), both batteries in the final state (each exit `0`; the second
embeds the `collect-live` phase, which asserts the typed response, its
value-level post-state proof, that a refused collection left a construction's
timers untouched, and that a disposable corpus save mutated), and the
preservation manifest (3,258 entries, exit `0`). The compatibility service
listens on `127.0.0.1:5056` only, and every network call in these commands is
loopback. The evidence capture and report steps are documented in
`apps/client-godot/README.md` ("Building collection"); committed evidence lives
under `apps/client-godot/evidence/building-collect/`. Claim limits: every payout
number is **derived**, never observed from the Flash client - the claim is that a
payout grows in four committed rungs derived from the item's committed income
fields, never any specific amount the legacy client pays; the committed
`COLLECT_MINUTES` ladder is in **minutes** while both row instants are Unix
seconds, so the comparison converts through one named constant (300 / 3 600 /
14 400 / 28 800 s) with every boundary covered from both sides, and comparing
them directly was found and corrected during implementation; the clamp is never
exercised by the fixture; the corpus's only income-bearing rows are decorations
because the real factories are not placed; **no cap semantics are implemented**
and a non-zero committed cap is refused; a collection is refused on a row under
construction **in both layers** (the client offers no action and the service fails
closed) because executing one overwrites the build's start instant, while the
legacy client's own behavior is unobserved; below the first committed rung no
collection is offered and none is executed; collectability and addressability are
client-side rules only, with the endpoint enforcing structural input validity,
the content refusals, and the two-part proof, and no server-authoritative
validation (that belongs to Server v1 / M13); no pixel-parity oracle exists; the
committed capture runs the fake implementation, so real-execution parity rests on
the fixture-replay tests and the live phase. No Flash, Ruffle, ActionScript, or
browser executes in any of these commands.

Verified building-expand commands (milestone M7; Godot 4.7.2.stable and pinned
CPython 3.9.13, Windows x64; `python` denotes the pinned interpreter, never the
PATH alias). This is the first deliver line whose derived vector is a **debit**,
and the first whose two guards exist because an executed probe showed the legacy
server omits them; the investigation record `docs/legacy-town-expansion.md` was
committed before the proposal (PR #188):

```bash
python -B apps/compat-api/capture_expand_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_town_expand.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-09-30): the expand fixture capture (one-shot
executed-legacy oracle; the request carries `[[0,"expand",[0],[0,0,0,0,0,0,0,0]]]`
- expansion id 0, the free committed row - so `expansions` goes
`[35, 36, 45, 46]` to `[35, 36, 45, 46, 0]`, growing by exactly one entry at the
end with the existing four unchanged, in order, and **not** deduplicated, while all
40 items, the map level, the storage, the whole private state, the player info, and
**all seven resources** stay byte-identical; there is **no** time-dependent field in
the after-state, so a rerun reproduces the committed bytes exactly; exit codes and
containment recorded in `tests/fixtures/godot-building-expand/README.md`), the compat
suite including the schedule derivation, the `/v0/expand` endpoint with its **two
guards the legacy server omits** (`unknown_expansion_id` for an id outside the
98-entry table and `already_expanded` for an owned id, justified by a probe in which
the real server accepted `expand(999)`, a duplicate `expand(35)`, and `expand(-1)`,
all answering success), its `expansion_requirements_unmet` and
`insufficient_resources` refusals, and its **two-part** post-execution proof that
checks the owned list grew by exactly one appended id **and** every stored resource
changed by exactly the derived debit, and executed-legacy parity tests with **no
normalization** (observed `Ran 947 tests ... OK`, exit `0`), the hermetic
expansion-flow suite (observed 615 checks, PASS), both batteries in the final state
(each exit `0`; the second embeds the `expand-live` phase, which asserts the typed
response, its two-part post-state proof, that a refused expansion left the corpus
byte-identical, and that a disposable corpus save mutated), and the preservation
manifest (3,258 entries, exit `0`). The compatibility service listens on
`127.0.0.1:5056` only, and every network call in these commands is loopback. The
evidence capture and report steps are documented in `apps/client-godot/README.md`
("Town expansion"); committed evidence lives under
`apps/client-godot/evidence/building-expand/`. Claim limits: **the tile-to-cell
geometry is a known evidence gap**, so no terrain, grid, buildable-cell, or
placement-bound behavior is claimed or implemented, and closing the gap requires new
evidence rather than a derivation; the **id-space indexing is derived** and the claim
is that the debit is the one the committed positional table assigns to that id,
never the price a coherent player pays; `coins` is **established as the client's
`gold`** by the committed images `expansion_gold.jpg` and `expansion_cash.jpg`; the
`neighbors` and `inventory_qte` requirements are refused rather than invented, which
means **94 of 98 rows are unpurchasable, including all four ids the corpus owns**,
so **the delivered transaction is a zero-cost expansion and no balance moves** and
the priced path and the affordability refusal are covered only through stubbed
schedule rows; the per-resource clamp is **reachable** (a client-sent 2500 gold debit
against a 2000 balance landed on `0`, not `-500`, which is why the endpoint derives
the debit server-side) but is **not exercised** by the fixture; a negative id is
refused as `invalid_expansion_id` because Python would otherwise index the schedule
from its end; expandability and addressability are client-side rules only, with the
endpoint enforcing structural input validity, the two guards, the two refusals, and
the two-part proof, and no server-authoritative validation (that belongs to
Server v1 / M13); no pixel-parity oracle exists; the committed capture runs the fake
implementation, so real-execution parity rests on the fixture-replay tests and the
live phase. No Flash, Ruffle, ActionScript, or browser executes in any of these
commands.

Verified town vertical-slice commands (Godot 4.7.2.stable, Windows x64;
the two windowed captures need an interactive display session):

```bash
godot --path apps/client-godot res://scenes/boot.tscn -- --gameapi=fake --town-capture=<repo>/apps/client-godot/evidence/town/town-player.png
godot --path apps/client-godot res://scenes/town_slice.tscn -- --town-capture=<repo>/apps/client-godot/evidence/town/town-slice.png
godot --headless --path apps/client-godot res://scenes/town.tscn -- --town-report=<repo>/apps/client-godot/evidence/town/report.json
```

These are the D10 evidence steps committed under
`apps/client-godot/evidence/town/` (two 1400x600 captures plus the
deterministic report; rerunning the report step reproduces its bytes, and
the bare `--town-report` flag defaults to that report path). The six town
suites and the no-Flash gate run inside `verify-boot.ps1`. These commands
execute no Flash and establish no pixel parity: the claim limits and the
projection evidence gap are recorded in
`apps/client-godot/README.md` ("Town vertical slice").

Important:

- The source-runtime manifest is fully pinned and verified only on Windows x64 CPython 3.9.13; see `docs/legacy-baseline.md` for interpreter provenance, two clean installs, and contained root HTTP evidence.
- Executed package consistency check: `python -m pip --isolated check`.
- Run startup and syntax checks in a disposable source copy to contain saves and bytecode; the verified HTTP smoke requests only `http://127.0.0.1:5055/` without a browser or Flash execution.
- No verified automated gameplay test, lint, or type-check command exists in the current legacy baseline yet. Focused preservation-tool tests are verified separately below.
- Do not invent commands in this file.
- When Godot, compatibility API, Server v1, or test tooling is added, update this section with commands that were actually executed successfully.

Verified preservation-tool commands (CPython 3.9.13 Windows x64 and local Git;
`python` denotes a working selected interpreter, not the Windows Store alias):

```bash
python -B tools/hash-manifest/hash_manifest.py generate
python -B tools/hash-manifest/hash_manifest.py verify
python -B -m unittest discover -s tools/hash-manifest -p test_hash_manifest.py -v
```

See `tools/hash-manifest/README.md` for the explicit executable used, immutable
Git-blob source/policy, 3,258-entry evidence, exit codes, and scope limitations.
These commands execute no Flash or application runtime and establish no gameplay
or canonical-save parity.

Verified offline asset-registry commands (Windows x64 CPython 3.9.13):

```bash
python -B tools/asset-registry/build_registry.py
python -B -m unittest discover -s tools/asset-registry/tests -p test_build_registry.py -v
```

See `tools/asset-registry/README.md` and `docs/assets/registry.md` for the
executable, invocation, exit codes, evidence classification, and containment.
These commands enumerate the worktree asset corpus (3,215 files including
1,176 SWFs), join normalized content references against it, and establish no
parsing, conversion, asset validity, gameplay parity, or Godot rendering.
Registry hashes identify worktree bytes and are distinct from the baseline
Git-blob hashes owned by `legacy-manifest.json`.

Verified offline SWF-inspection commands (Windows x64 CPython 3.9.13):

```bash
python -B tools/asset-registry/inspect_swf.py
python -B -m unittest discover -s tools/asset-registry/tests -p test_inspect_swf.py -v
```

See `tools/asset-registry/README.md` and `docs/assets/registry.md` for the
executable, parsing rules, exit codes, evidence classification, and
containment. These commands statically inventory all 1,176 SWF headers, tags,
symbols, and embedded-asset IDs (1,175 with ABC, 0 with legacy actions) and
establish no conversion, timeline semantics, script behavior, asset validity,
gameplay parity, or Godot rendering. No ActionScript executes and no Flash
runtime is involved.

Verified offline sound-extraction commands (Windows x64 CPython 3.9.13):

```bash
python -B tools/asset-registry/extract_sounds.py
python -B -m unittest discover -s tools/asset-registry/tests -p test_extract_sounds.py -v
```

See `tools/asset-registry/README.md` and `docs/assets/registry.md` for the
executable, slicing rule, exit codes, evidence classification, and
containment. These commands extract all 27 embedded MP3 payloads verbatim
(no decoding, playback, transcoding, or source mutation) and establish no
timeline semantics, audio-quality claims, gameplay parity, or Godot
rendering.

Verified offline bitmap-extraction commands (Windows x64 CPython 3.9.13):

```bash
python -B tools/asset-registry/extract_images.py
python -B -m unittest discover -s tools/asset-registry/tests -p test_extract_images.py -v
```

See `tools/asset-registry/README.md` and `docs/assets/registry.md` for the
executable, per-family rules, committed-vs-ignored output split, exit codes,
evidence classification, and containment. These commands extract all 61,702
bitmap payloads (verbatim JPEG, JPEG-plus-alpha, RGBA PNGs via a hand-rolled
stdlib writer) with re-parse validation and establish no rendering
correctness, color judgment, timeline assembly, gameplay parity, or Godot
rendering. Bulk outputs regenerate under ignored `assets/converted/images/`;
the committed digest manifest is the permanent evidence.

Verified offline first-building conversion commands (Windows x64 CPython 3.9.13):

```bash
python -B tools/asset-registry/convert_building.py
python -B -m unittest discover -s tools/asset-registry/tests -p test_convert_building.py -v
```

See `tools/asset-registry/README.md` and `docs/assets/registry.md` for the
executable, parsing boundary, exit codes, evidence classification, and
containment. These commands assemble one converted building package (shape
bounds/styles with bitmap linkage, no tessellation) and establish no
rendering correctness, visual fidelity, gameplay footprint semantics, or Godot
loading. No Godot project is created or required.

Verified offline first-unit conversion commands (Windows x64 CPython 3.9.13):

```bash
python -B tools/asset-registry/convert_unit.py
python -B -m unittest discover -s tools/asset-registry/tests -p test_convert_unit.py -v
```

See `tools/asset-registry/README.md` and `docs/assets/registry.md` for the
executable, extraction prerequisite, worktree-form note, parsing boundary
(depth-first placement order, labels names-only, fill-array alignment,
placeholder rule), neutral `conversion-v1` envelope, exit codes, evidence
classification, and containment. These commands assemble one converted unit
package (per-sprite timeline inventory with shape/bitmap linkage, no
tessellation, no playback semantics) and establish no animation correctness,
rendering, visual fidelity, gameplay semantics, or Godot loading. No Godot
project is created or required.

Verified opt-in command-recorder check (Windows x64 CPython 3.9.13):

```bash
python -B -m unittest discover -s tests -p test_legacy_command_recorder.py -v
```

See `docs/legacy-command-recording.md` for the executed external-directory
enablement setting, schema, sanitization, containment, and failure semantics.
The focused checks use disposable saves and no Flash or listening server.

Verified offline structural state-diff commands (Windows x64 CPython 3.9.13):

```bash
python -B tools/state-diff/state_diff.py compare --before tests/saves/fresh-player-pre-migration.json --after tests/saves/fresh-player.json
python -B tools/state-diff/state_diff.py compare --before tests/saves/fresh-player.json --after tests/saves/fresh-player.json
python -B -m unittest discover -s tools/state-diff -p test_state_diff.py -v
```

See `tools/state-diff/README.md` for the executable, explicit record mode,
value-free report, limits, privacy and containment evidence. The comparisons
exit `1` for the canonical `/version` difference and `0` for equality; these
checks establish structural evidence, not gameplay parity or persistence.

Verified contained legacy command-replay check (Windows x64 CPython 3.9.13,
installed pinned source-runtime packages, and local Git baseline objects):

```bash
python -B -m unittest discover -s tools/protocol-replay -p test_protocol_replay.py -v
```

See `tools/protocol-replay/README.md` for the executable, four-command
recorder-v1 eligibility, immutable oracle closure, isolated disposable child,
private value-free report, limits, persistence meaning, and containment evidence.
These are controlled replay checks without server, network, browser, or Flash
execution; they establish no authentic progressed-player or gameplay parity.

Verified offline endpoint-catalog check (Windows x64 CPython 3.9.13):

```bash
python -B tools/endpoint-catalog/verify_endpoints.py
python -B -m unittest discover -s tools/endpoint-catalog -p test_endpoint_catalog.py -v
```

See `docs/legacy-protocol/endpoints.md` and `tools/endpoint-catalog/README.md`
for the executable, invocation, exit codes, evidence classification, and
containment. These checks establish source-grounded catalog/inventory/source
consistency, not executed endpoints, gameplay parity, or command discovery.

Verified offline command-catalog check (Windows x64 CPython 3.9.13):

```bash
python -B tools/command-catalog/verify_commands.py
python -B -m unittest discover -s tools/command-catalog -p test_command_catalog.py -v
```

See `docs/legacy-protocol/commands.md` and `tools/command-catalog/README.md`
for the executable, invocation, exit codes, evidence classification, and
containment. These checks establish source-grounded catalog/inventory/source
consistency for the 63 named `command.py` dispatcher branches plus the
unhandled fallthrough (the approved proposal estimated 64 named branches; the
extra row, `push_dead_unit`, is an engine helper, not a dispatcher branch),
not executed commands, gameplay parity, or progressed-player coverage.

Verified offline content-census check (Windows x64 CPython 3.9.13):

```bash
python -B tools/content-census/verify_content.py
python -B -m unittest discover -s tools/content-census -p test_content_census.py -v
```

See `docs/game-content/census.md` and `tools/content-census/README.md`
for the executable, invocation, exit codes, evidence classification, and
containment. These checks establish source-grounded census/inventory/source
consistency for the 20 top-level keys of `config/main.json`, the five
ordered patches, the inactive mods pipeline, import-time duplicate
cleaning, and the dynamic-derivation boundary (stored sources only;
served bytes are time-dependent and explicitly unverified), not
served-byte equality, content validity, gameplay parity, or normalization.

Verified offline content field-type survey check (Windows x64 CPython 3.9.13):

```bash
python -B tools/field-survey/verify_fields.py
python -B -m unittest discover -s tools/field-survey -p test_field_survey.py -v
```

See `docs/game-content/field-types.md` and `tools/field-survey/README.md`
for the executable, invocation, exit codes, evidence classification, and
containment. These checks establish source-grounded survey/readable/source
consistency for per-field encoding profiles of the 15 array-of-object keys
and value-shape profiles of the 5 object keys of `config/main.json`
(stored sources only; served bytes are time-dependent and explicitly
unverified), not served-byte equality, content validity, gameplay parity,
normalization, coercion, or schema authoring.

Verified offline items-normalization check (Windows x64 CPython 3.9.13):

```bash
python -B packages/game-content/tools/build_items.py
python -B -m unittest discover -s packages/game-content/tests -p test_build_items.py -v
```

See `packages/game-content/README.md` for the executable, invocation,
exit codes, evidence classification, and containment. These checks
establish source-grounded normalization consistency for the 900 loaded
`items` entries (470 buildings, 429 units, 1 documented special with
schemas, round-trip evidence, and manifest), not served-byte equality,
content validity, gameplay parity, asset existence, or
progressed-player coverage.

Verified offline quest-normalization check (Windows x64 CPython 3.9.13):

```bash
python -B packages/game-content/tools/build_quests.py
python -B -m unittest discover -s packages/game-content/tests -p test_build_quests.py -v
```

See `packages/game-content/README.md` (quest normalization extension)
for the executable, invocation, exit codes, evidence classification,
and containment. Run the items-normalization build first: the quest
builder reads the committed normalized items outputs as its
cross-domain reference edge and merges its `quests` section into the
package manifest. These checks establish source-grounded normalization
consistency for the 91 stored `goals` entries (quests with schemas,
uniform hint/reward preserved with notes, and round-trip evidence) and
the 10 stored `collections` entries (collections with schemas,
coerced item references resolving against the 900 normalized items
legacy IDs, and manifest), not served-byte equality, content validity,
gameplay parity, asset existence, or progressed-player coverage.

Verified offline reference-tables normalization check (Windows x64 CPython 3.9.13):

```bash
python -B packages/game-content/tools/build_tables.py
python -B -m unittest discover -s packages/game-content/tests -p test_build_tables.py -v
```

See `packages/game-content/README.md` (reference-tables normalization
extension) for the executable, invocation, exit codes, evidence
classification, and containment. This extension has no cross-domain
reference edge and merges its `tables` section into the package
manifest while leaving the items and quests keys untouched. These
checks establish source-grounded normalization consistency for the 10
stored `magics` entries (magics with schemas, embedded-JSON area
coerced, asset names recorded), the 100 stored `levels` entries
(levels with schemas, positional XP-curve order preserved with
`legacy_id` as the 0-based index, native fields verbatim), and the
139 stored `sounds` entries (sounds with schemas, string-encoded
numerics coerced, asset names recorded), with round-trip evidence and
manifest, not served-byte equality, content validity, gameplay parity,
asset existence, or progressed-player coverage.

Verified offline economy-schedules normalization check (Windows x64 CPython 3.9.13):

```bash
python -B packages/game-content/tools/build_economy.py
python -B -m unittest discover -s packages/game-content/tests -p test_build_economy.py -v
```

See `packages/game-content/README.md` (economy-schedules normalization
extension) for the executable, invocation, exit codes, evidence
classification, and containment. Run the items-normalization build first: the
economy builder reads the committed normalized items outputs as its
cross-domain reference edge for ranking rewards and merges its `economy`
section into the package manifest while leaving the items, quests, and
tables keys untouched. These checks establish source-grounded normalization
consistency for the 98 stored `expansion_prices` entries, the 4 stored
`town_prices` entries, the 4 stored `map_prices` entries (identical values
preserved as separate schedules, never deduplicated), and the 50 stored
`level_ranking_reward` entries (levels 50..1 with native single-entry units
maps resolving against the 900 normalized items legacy IDs), with schemas,
exact round-trip evidence, and manifest, not served-byte equality, content
validity, gameplay parity, asset existence, or progressed-player coverage.

Verified offline social-tables normalization check (Windows x64 CPython 3.9.13):

```bash
python -B packages/game-content/tools/build_social.py
python -B -m unittest discover -s packages/game-content/tests -p test_build_social.py -v
```

See `packages/game-content/README.md` (social-tables normalization
extension) for the executable, invocation, exit codes, evidence
classification, and containment. This extension has no cross-domain
reference edge and merges its `social` section into the package
manifest while leaving the items, quests, tables, and economy keys
untouched. These checks establish source-grounded normalization
consistency for the 5 stored `neighbor_assists` entries (positional
assists with verbatim rewards and display strings), the 10 stored
`findable_items` entries (sequential ids, uniform coin rewards), and
the 26 stored `social_items` entries (non-sequential ids, verbatim
worker names, uniformly-empty descriptions preserved with notes),
with schemas, exact round-trip evidence, and manifest, not
served-byte equality, content validity, gameplay parity, asset
existence, progressed-player coverage, or implemented social behavior.

Verified offline inventory-taxonomy normalization check (Windows x64 CPython 3.9.13):

```bash
python -B packages/game-content/tools/build_taxonomy.py
python -B -m unittest discover -s packages/game-content/tests -p test_build_taxonomy.py -v
```

See `packages/game-content/README.md` (inventory-taxonomy normalization
extension) for the executable, invocation, exit codes, evidence
classification, and containment. Run the items-normalization build first: the
taxonomy builder reads the committed normalized items outputs as its
cross-domain reference edge (collection units, stored `inventory_ids` keys)
and merges its `taxonomy` section into the package manifest while leaving
the items, quests, tables, economy, and social keys untouched. These checks
establish source-grounded normalization consistency for the 90 stored
`inventory_items` entries (string-encoded numerics coerced, object keys
preserved), the 6 stored `categories` entries (sub arrays carried with
parent checks, patch-era item category codes recorded as opaque with notes),
and the 20 stored `units_collections_categories` entries (units resolving
against the 900 normalized items legacy IDs, single null costs and
uniformly-empty Greek names preserved with notes), with schemas, round-trip
evidence modulo documented coercions, and manifest, not served-byte
equality, content validity, gameplay parity, asset existence,
progressed-player coverage, or implemented inventory/shop behavior.

Verified offline darts-schedule normalization check (Windows x64 CPython 3.9.13):

```bash
python -B packages/game-content/tools/build_darts.py
python -B -m unittest discover -s packages/game-content/tests -p test_build_darts.py -v
```

See `packages/game-content/README.md` (darts-schedule normalization
extension) for the executable, invocation, exit codes, evidence
classification, and containment. Run the items-normalization build first: the
darts builder reads the committed normalized items outputs as its
cross-domain reference edge for pooled and extra ids, applies only the
`targets` whole-array replace of `/darts_items` (stored 30 entries recorded
as replace inputs, 27 patched entries normalized), and merges its `darts`
section into the package manifest while leaving the prior keys untouched.
These checks establish source-grounded normalization consistency for the 27
patched `darts_items` entries (ids 1..27 with six-id native pools and extra
ids resolving against the 900 normalized items legacy IDs, `start_date`
values preserved verbatim as derivation inputs), with schema, exact
round-trip evidence against the patched array, and manifest, not
served-byte equality (`make_dynamic` rewrites served dates and never runs
here), content validity, gameplay parity, asset existence, or
progressed-player coverage.

Verified offline globals-tuning normalization check (Windows x64 CPython 3.9.13):

```bash
python -B packages/game-content/tools/build_globals.py
python -B -m unittest discover -s packages/game-content/tests -p test_build_globals.py -v
```

See `packages/game-content/README.md` (globals-tuning normalization
extension) for the executable, invocation, exit codes, evidence
classification, and containment. This extension has no cross-domain
reference edge and merges its `globals` section into the package
manifest while leaving the prior keys untouched. These checks
establish source-grounded normalization consistency for the 105 loaded
`globals` entries (104 stored constants plus the single powerup-added
schedule, heterogeneous values kept verbatim with recorded types and
opaque string constants never parsed), with schema including the
value-type union, exact round-trip evidence against the loaded object,
and manifest, not served-byte equality, content validity, gameplay
parity, tuning correctness, asset existence, or progressed-player
coverage.

Verified offline offers normalization check (Windows x64 CPython 3.9.13):

```bash
python -B packages/game-content/tools/build_offers.py
python -B -m unittest discover -s packages/game-content/tests -p test_build_offers.py -v
```

See `packages/game-content/README.md` (offers normalization
extension) for the executable, invocation, exit codes, evidence
classification, and containment. Run the items-normalization build first: the
offers builder reads the committed normalized items outputs as its
cross-domain reference edge and merges its `offers` section into the
package manifest while leaving the prior keys untouched. These checks
establish source-grounded normalization consistency for the 44 stored
`offer_packs` entries (verbatim scalars and item shapes with null/flat/
pairs/groups classes, flat/pair-first/group leaves resolving against
the 900 normalized items legacy IDs, pair seconds opaque, two pinned
leaf anomalies preserved verbatim under an exact-match allowlist),
with schema, exact round-trip evidence, and manifest, not served-byte
equality, content validity, gameplay parity, pack-semantics
correctness, asset existence, or progressed-player coverage.

Verified offline images normalization check (Windows x64 CPython 3.9.13):

```bash
python -B packages/game-content/tools/build_images.py
python -B -m unittest discover -s packages/game-content/tests -p test_build_images.py -v
```

See `packages/game-content/README.md` (images normalization
extension) for the executable, invocation, exit codes, evidence
classification, and containment. This extension has no cross-domain
reference edge and merges its `images` section into the package
manifest while leaving the prior keys untouched. These checks
establish source-grounded normalization consistency for the 607 stored
`images` entries (asset paths preserved verbatim with locale `en`
enforced, extension split and swf paths recorded), with schema, exact
round-trip evidence, and manifest, not served-byte equality, content
validity, gameplay parity, asset existence or convertibility (M4 owns
asset truth), or progressed-player coverage. With this extension every
one of the 20 census content keys has a normalized counterpart.

Verified offline asset-ID registry commands (Windows x64 CPython 3.9.13):

```bash
python -B tools/asset-registry/build_asset_ids.py
python -B -m unittest discover -s tools/asset-registry/tests -p test_build_asset_ids.py -v
```

See `tools/asset-registry/README.md` (asset ID registry section) for the
executable, invocation, join and status rules, exit codes, worktree-form
note, evidence classification, and containment. These commands join
every distinct content asset reference (images, item sprites, magic
sprites, sounds)
against the committed corpus registry and the M4 conversion and
extraction manifests, writing the deterministic
`tools/asset-registry/asset_ids.json` (ten recorded inputs, 1,627
entries across the closed status vocabulary, byte-identical rerun), and
they establish no asset validity, conversion correctness, rendering,
gameplay parity, or Godot loading (client-side resolution is exercised
by the Godot asset-ID suite).

Verified offline content-validator commands (Windows x64 CPython 3.9.13):

```bash
python -B packages/game-content/tools/validate_content.py
python -B -m unittest discover -s packages/game-content/tests -p test_validate_content.py -v
```

See `packages/game-content/README.md` (content validator extension) for
the executable, invocation, four check families, exit codes, evidence
classification, and containment. These commands validate the committed
normalized package (22 outputs, 21 schemas, manifest bytes/digests/counts,
and every cross-domain reference edge) with a read-only standard-library
tool and establish no source freshness, served-byte equality, content
validity, asset existence, gameplay parity, or progressed-player
coverage.

---

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

---

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

---

## Boundaries — do not touch

- Never delete original SWFs, saves, configs, images, sounds, XML, or other preservation material merely because a replacement exists.
- Never overwrite raw source assets during conversion; write converted/runtime assets separately.
- Never silently drop unknown legacy save fields; preserve them for migration analysis, e.g. `legacy_extra`.
- Never manually edit generated files under `.agents/skills/`.
- Never commit `.env`, `.env.*`, credentials, tokens, private keys, or production secrets.
- Never hardcode production secrets.
- Never package Flash Player, Ruffle, ActionScript runtimes, or runtime-required SWFs into the final modern client.
- Do not modify legacy behavior merely to make modern implementation easier; document and reproduce it first.

---

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

---

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

---

## Git / PR workflow 
 
`main` is the integration branch. Never perform planned work directly on `main`. 
 
Every repository-mutating OpenSpec stage must use a remote branch and PR. Local-only working branches are not allowed. 
 
### Branch naming 
 
Branch names describe the technical work, not the raw OpenSpec change name. 
 
- Proposal/docs: `docs/<technical-scope>-proposal` 
- Feature: `feat/<technical-scope>` 
- Fix: `fix/<technical-scope>` 
- Refactor: `refactor/<technical-scope>` 
- Tests/validation: `test/<technical-scope>` 
- Technical spike: `spike/<technical-scope>` 
- Spec sync: `docs/<technical-scope>-spec-sync` 
- Archive: `chore/archive-<technical-scope>` 
 
Examples: 
 
- `docs/.....-proposal` 
- `feat/quest-progress-api` 
- `fix/duplicate-xp-award` 
- `docs/....-spec-sync` 
- `chore/archive-...-validation` 
 
Do not use the OpenSpec change ID as the branch name unless it is also the clearest technical description. 
 
### Branch lifecycle 
 
Before starting any repository-mutating stage: 
 
1. Check `git status`. 
2. Switch to `main`. 
3. Pull the latest `origin/main`. 
4. Create a new branch from the updated `main`. 
5. Immediately push the new branch to `origin` and set upstream tracking. 
6. Only then begin modifying files. 
 
Never leave active repository work only on a local branch. 
 
Recommended pattern: 
 
    git switch main 
    git pull --ff-only origin main 
    git switch -c <branch-name> 
    git push -u origin <branch-name> 
 
### OpenSpec Git lifecycle 
 
#### Explore 
 
`/openspec-explore` is normally read-only. 
 
If no repository files change, no branch or PR is required. 
 
If exploration intentionally modifies tracked documentation, treat it as a normal repository-mutating stage and use a branch + PR. 
 
#### Propose 
 
For `/openspec-propose`: 
 
1. Start from updated `main`. 
2. Create a technical proposal branch such as `docs/<scope>-proposal`. 
3. Immediately push the branch to `origin`. 
4. Create/update the OpenSpec proposal, design, specs, tasks, and roadmap status. 
5. Review the diff. 
6. Commit using Conventional Commits. 
7. Push all proposal commits to the remote branch. 
8. Open a PR into `main`. 
9. After required checks pass, merge the PR using a **merge commit**. 
10. Delete the merged local and remote branch. 
11. Return to `main` and pull the merged result before starting Apply. 
 
Proposal artifacts should be committed and pushed so the exact remote PR diff can be reviewed. 
 
Do not reuse the proposal branch for Apply. 
 
#### Apply 
 
For `/openspec-apply-change`: 
 
1. Ensure the proposal PR has already been merged. 
2. Return to `main`. 
3. Pull the latest `origin/main`. 
4. Create a new implementation branch from `main`. 
5. Immediately push the new branch to `origin`. 
6. Apply only the approved OpenSpec tasks. 
7. Commit coherent implementation steps using Conventional Commits. 
8. Push commits regularly to the remote branch. 
9. Run all required verification. 
10. Review the final diff and test results. 
11. Open or update the PR into `main`. 
12. Merge after required checks pass. 
13. Merge using a **merge commit**. 
14. Delete the merged local and remote branch. 
15. Return to updated `main`. 
 
Do not reuse the proposal branch for Apply. 
 
Do not begin Sync or Archive from an unmerged Apply branch. 
 
#### Sync 
 
If `/openspec-sync` modifies repository files: 
 
1. Ensure the Apply PR has already been merged. 
2. Return to `main` and pull latest `origin/main`. 
3. Create `docs/<scope>-spec-sync`. 
4. Immediately push it to `origin`. 
5. Run the approved OpenSpec sync. 
6. Review the diff. 
7. Commit using Conventional Commits. 
8. Push the commit(s). 
9. Open a PR into `main`. 
10. Merge using a **merge commit** after required checks pass. 
11. Delete the local and remote branch. 
12. Return to updated `main`. 
 
Skip this stage when no spec synchronization is required. 
 
#### Archive 
 
For `/openspec-archive`: 
 
1. Archive only after Apply and any required Sync are merged. 
2. Return to `main`. 
3. Pull latest `origin/main`. 
4. Create `chore/archive-<technical-scope>`. 
5. Immediately push the branch to `origin`. 
6. Run the OpenSpec archive workflow. 
7. Update Project Status, roadmap references, and archive links where required. 
8. Review the diff. 
9. Commit using Conventional Commits. 
10. Push the archive commit(s). 
11. Open a PR into `main`. 
12. Merge after required checks pass. 
13. Merge using a **merge commit**. 
14. Delete the local and remote branch. 
15. Return to `main` and pull latest `origin/main` before beginning the next roadmap phase. 
 
### Commit conventions 
 
Use Conventional Commits: 
 
- `feat:` new product capability 
- `fix:` bug fix 
- `refactor:` behavior-preserving restructuring 
- `test:` tests or technical validation 
- `docs:` documentation/specification 
- `chore:` repository/tooling/archive maintenance 
 
Examples: 
 
- `docs: propose browser runtime validation` 
- `test: add worker containment probes` 
- `feat: add quest progress endpoint` 
- `fix: prevent duplicate xp awards` 
- `docs: sync runtime validation requirements` 
- `chore: archive browser runtime validation` 
 
Keep commits coherent and scoped. 
 
Do not bundle unrelated changes into one commit. 
 
### PR / merge conventions 
 
- Every Propose, Apply, Sync, and Archive stage that changes repository files must go through a PR into `main`. 
- Never silently commit completed stage work directly to `main`. 
- Keep one coherent OpenSpec stage per branch. 
- Open the PR from the remote branch, not from local-only work. 
- Use **merge commits only** for OpenSpec and development PRs. 
- Do **not** squash merge. 
- Do **not** rebase merge. 
- Preserve branch topology and individual branch commits in Git history. 
- When using GitHub CLI, merge with: 
 
    gh pr merge <PR_NUMBER> --merge --delete-branch 
 
- Do not use: 
 
    gh pr merge <PR_NUMBER> --squash 
 
or: 
 
    gh pr merge <PR_NUMBER> --rebase 
 
- Do not replace the default GitHub merge-commit title unless there is a specific reason. 
- Prefer preserving the normal GitHub merge message, for example: 
 
    Merge pull request #123 from owner/feat/quest-progress-api 
 
- Delete local and remote branches only after the PR has successfully merged. 
- The PR and merge commit are the permanent historical record after branch deletion. 
- Never begin the next OpenSpec stage from an unmerged branch. 
- After every merge, switch back to `main` and update it from `origin/main` before creating the next branch. 
 
### Expected OpenSpec branch flow 
 
For one OpenSpec change, the normal flow is: 
 
    main 
      │ 
      ├── docs/<scope>-proposal 
      │      ↓ push remote immediately 
      │      ↓ /openspec-propose 
      │      ↓ commit + push 
      │      ↓ PR 
      │      ↓ merge commit 
      │ 
      ├── feat|spike|test/<scope> 
      │      ↓ push remote immediately 
      │      ↓ /openspec-apply-change 
      │      ↓ implementation 
      │      ↓ verification 
      │      ↓ commit + push 
      │      ↓ PR 
      │      ↓ merge commit 
      │ 
      ├── docs/<scope>-spec-sync 
      │      ↓ only if sync is required 
      │      ↓ /openspec-sync 
      │      ↓ PR 
      │      ↓ merge commit 
      │ 
      └── chore/archive-<scope> 
             ↓ /openspec-archive 
             ↓ update roadmap/status 
             ↓ PR 
             ↓ merge commit 
             ↓ delete branch 
             ↓ return to updated main 
 
### Git safety 
 
- Check `git status` before significant work. 
- Inspect `git diff` before every commit. 
- Inspect the final diff before opening a PR. 
- Never discard existing user changes. 
- Never force-push unless explicitly authorized. 
- Never use destructive Git operations unless explicitly authorized. 
- Never rewrite history unless explicitly authorized. 
- Never merge a PR with failing required checks unless explicitly authorized. 
- Never claim a branch was pushed, a PR was opened, or a merge occurred unless it actually happened.

---

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

---

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

---

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

---

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

---

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
