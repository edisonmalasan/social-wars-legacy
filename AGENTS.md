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

Verified building-resource commands (milestone M7; Godot 4.7.2.stable and
pinned CPython 3.9.13, Windows x64; `python` denotes the pinned interpreter, never the
PATH alias). This is the first deliver line whose legacy contract needed **no
derivation at all** — the seven stored resource slots and their save locations are
already established by `engine.apply_resources` (`engine.py:251-271`), the corpus
agrees exactly, and the Compatibility API's `resources()` accessor already returns
exactly those seven keys — so the defect was entirely inside the modern client's
projection. The investigation record `docs/legacy-resources.md` was committed before the
proposal (PR #193):

```bash
godot --headless --path apps/client-godot --script res://tests/test_town_resources.gd
godot --headless --path apps/client-godot --script res://tests/test_town_hud.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-09-30): the hermetic projection/readout suite
(observed 101 checks, PASS — every resource row, the summary group, both absent-field
paths, the response-driven update path, and the assertion that no delivered line's
semantics change) and the corrected HUD suite (observed 38 checks, PASS, was 28);
both batteries in the final state (each exit `0`; `verify-boot.ps1` now runs **26
hermetic suites and 12 live phases**); the compat suite, which is **unchanged** at
`Ran 947 tests ... OK`, exit `0`, because the Compatibility API is not modified at all;
and the preservation manifest (3,258 entries, exit `0`). The evidence steps are
documented in `apps/client-godot/README.md` ("Resource readout"); committed evidence
lives under `apps/client-godot/evidence/building-resources/` (a windowed capture plus
the deterministic `resources-report-v1` report, byte-identical across reruns, whose
projection table is generated from the projection module's own data so it cannot drift
from the code it documents). **What the change fixed:** `town_hud.gd` keyed its first
resource row `coins`, a field nothing produces — the server's field is `gold`,
`maps[0]` has `gold` and no `coins`, and the compat module's only occurrences of the
word are comments about the expansion price schedule — so the fail-closed readout
rendered an explicit missing-field indicator and **the player's primary currency was
displayed as missing and its real value never appeared**; the existing HUD suite
*pinned* that defect by supplying `coins` and `energy` in a crafted payload shape
nothing real produces. The fix is minimal because the table was never mis-shaped: its
own header named the intended set as "coins, wood, steel, oil, cash, energy, mana",
which is exactly its ten-row shape, so **one key was misnamed** and no row was added,
removed, or reordered. **A second recorded gap is closed:** `energy` is a real eighth
resource (`privateState.energy = 50`; `COST_ENERGY = "e"` at `constants.py:899`;
`TOKEN_ENERGY = 7`; `CAT_ENERGY = 8`) and is now displayed by value under the save's
own name. Claim limits: the readout claims to display **what the save stores**, never
what the legacy client displayed, and no pixel-parity oracle against it exists; **no
rule is claimed for how the stored energy value changes over time** (`apply_resources`
never writes it, the eight-slot mutation vector has no slot for it, no legacy branch
touches it, and no committed source records a regeneration interval); **the design's
premise that this value had to be added to the service was wrong and the change was
narrowed rather than implemented as designed** — the client already maps `energy` to
`privateState.energy`, so **the Compatibility API is not modified at all** and the
shared `resources()` accessor the nine delivered value-level proofs compare stays
untouched; the market and trade counters and item-cost mapping onto the resource
vocabulary are out of scope (`trade_resource`'s arguments are recorded as *read but
unused*, so its resource movement is client-sent — the untrusted pattern collect and
expand already refuse); eleven mechanical `displayed("coins")` → `displayed("gold")`
query-key renames across ten delivered suites follow the correction, with **no change
to any assertion value, threshold, or intent**; `TownState.Resources` still declares an
internal `coins` field aliasing `map.gold` that **no readout row is keyed by**, and
retiring it is a separate correction; labels and layout are the delivered provisional
convention; no pixel-parity oracle exists; the committed capture runs the fake
implementation. Two committed M6 artifacts (`evidence/town/town-player.png`,
`evidence/town/report.json`) were **regenerated** because the label correction
invalidated their bytes — the town report differs only in the two `hud` blocks, where
the key moves from `coins` to `gold` in both the fresh and slice views, with no count,
digest, projection constant, camera, or selection block changed; leaving them stale
would have broken the M6 deliverable's claim that rerunning the report reproduces its
bytes. No Flash, Ruffle, ActionScript, or browser executes in any of these commands.

Verified building-xp commands (milestone M7; Godot 4.7.2.stable and pinned
CPython 3.9.13, Windows x64; `python` denotes the pinned interpreter, never the
PATH alias). This is the **eleventh and final** M7 deliver line; the investigation record
`docs/legacy-xp-basics.md` was committed before the proposal (PR #198):

```bash
python -B apps/compat-api/capture_level_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_town_xp.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-09-30): the level fixture capture (one-shot
executed-legacy oracle; the request carries `[[0,"level_up",[1],[0,0,0,0,0,0,0,0]]]` with a
**neutral** vector, and **at the committed corpus the transaction moves nothing** — the save
already records level 1 and the committed curve derives level 1 for `xp 4` — so the row is
unchanged and **all seven resources, the 40 placements, every other row, the storage, the
whole private state, and the player info are byte-identical**; the manifest records this as
`level_moved: false` with a note, and a **recorded probe in the same run establishes level
*movement* itself** — `level_up([2])` with a client-sent experience vector moved `level 1` to
`2` and `xp 4` to `504` with the changed map keys exactly `['level', 'xp']` — which is what
makes the endpoint's "no resource moved" proof non-tautological; exit codes and containment
recorded in `tests/fixtures/godot-building-xp/README.md`), the compat suite including the
committed-schedule derivation, the `/v0/level_up` endpoint accepting **only** `{user_id}`
with a client-supplied level **ignored** exactly as a client amount or price is ignored
elsewhere, its two 409 refusals (`level_already_current`, `xp_below_threshold`) resolved
before the dispatcher runs, and its **two-part** post-execution proof that checks the
recorded level equals the derived level **and that every stored resource is unchanged** — the
family's third proof form, which forecloses vector smuggling through a command dispatched
like any other with a client-sent resource vector — and executed-legacy parity tests
(observed `Ran 1109 tests ... OK`, exit `0`), the hermetic progression suite (observed 767
checks, PASS), both batteries in the final state (each exit `0`; `verify-boot.ps1` now runs
**27 hermetic suites and 13 live phases**), and the preservation manifest (3,258 entries, exit
`0`). The compatibility service listens on `127.0.0.1:5056` only, and every network call in
these commands is loopback. The evidence capture and report steps are documented in
`apps/client-godot/README.md` ("Level progression"); committed evidence lives under
`apps/client-godot/evidence/building-xp/`. **The one consequential decision:** the committed
`levels` schedule has 100 entries with `exp_required` **strictly increasing** (no
duplicates, no non-positive gap, `0, 40, 60, 100, 200, 350, 550, 800, …` to `2016089205`),
and **nothing in the legacy server reads it** — zero references across `command.py`,
`engine.py`, `sessions.py`, `server.py`, `constants.py` — while the legacy `level_up` branch
writes the level from a **client integer with no range check and no XP validation**, so a
client could set level 99. The curve's index base was resolved from the committed corpus, and
**zero-based is actively contradicted**: at `xp 4` it implies level 0 while the save records
level 1, since the curve says level 1 begins at 40 experience, whereas **one-based** gives
`4 >= exp_required(1) = 0`. Guessing zero-based would shift **every** level in the game by
one, invisibly, until a player noticed the wrong level name — so the interpretation is
**derived-provisional everywhere it is recorded with the rejected zero-based alternative
retained**, and the conversion lives in **exactly one named function per layer**
(`level_envelope.entry_index_for_level` and `LevelFlow.entry_index_for_level`, each with a
named inverse and a round trip asserted across all 100 entries; `town.gd` contains no curve
indexing of its own), and the compat slice then confirmed it empirically by deriving level 1
for the corpus's `xp 4`. Claim limits: **the level is the one the committed curve implies for
the stored experience, never one observed from the Flash client**, and the one-based index is
derived from **one** corpus data point; **no level reward is paid and none displayed**
(`reward_type` and `reward_amount` are committed on every entry and consumed by no legacy
branch, so paying one would invent an economy); **unit XP and tutorial progression were out of
scope for M7, and the reason recorded for unit XP was false as a general claim** — the
fresh-player corpus carries `attr["xp"]` on **0 of 40** placed rows and contains no unit row at
all, which are facts about *that* corpus and not about the branch, while **171 of 12,954**
placed rows across **5 of the 31** committed save documents carry it — every one of them a
committed unit row — so the branch was always exercisable and is now owned by
`godot-unit-experience`; tutorial progression is owned by `godot-tutorial`; the committed
thresholds are **preserved verbatim** with no
rebalancing; the stored-versus-derived **disagreement reporting deliberately does not
reconcile**, surfacing both values instead, because the recorded level is unverified against
the curve; **a successful live level-up is unproven** — the committed corpus is already at its
derived level, so the `level-up-live` phase **deliberately does not assert a save mutation**
but asserts the refusal, its code, its empty payload, and the corpus's byte-identity, with a
marker in `verify-boot.ps1` recording the deliberate absence; parity covers one recorded
transaction against the fresh-player corpus; no pixel-parity oracle exists; the committed
capture shows the refused path and runs the fake implementation. No Flash, Ruffle,
ActionScript, or browser executes in any of these commands.

Verified unit-definitions commands (milestone M8 line 1; Godot 4.7.2.stable, Windows x64;
`python` denotes the pinned interpreter, never the PATH alias). This is the first M8
deliver line and the first one that is **not** a legacy-behaviour derivation — everything
it delivers is committed content the client already verifies:

```bash
godot --headless --path apps/client-godot --script res://tests/test_unit_definitions.gd
godot --headless --path apps/client-godot --script res://tests/test_content_registry.gd
godot --headless --path apps/client-godot --script res://tests/test_project_scope.gd
godot --headless --path apps/client-godot --script res://tests/test_scene_build.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-10-01): the hermetic unit-definitions suite
(observed **204 checks**, 207 with `--report`; the 28th hermetic suite) over a typed
read-only `UnitDefinition` covering the **429 committed unit definitions** of
`packages/game-content/normalized/units.json` — **58 committed fields** (56 on every row
plus `breeding_order`/`sm_training_time` on 300 each), distinct string `legacy_id`s over
`923`..`1431`, five named field groups, fail-closed on every malformed field, absent fields
kept distinct from committed zeros, and one documented raw-entry accessor; the corrected
content-registry suite (observed **87 checks**, was 52) covering the **public
`ContentRegistry.legacy_ids(domain)` accessor** this change added, including the
committed-order-not-collation contract; the scope suite (**1339**) and scene build (**36**);
both batteries in the final state (each exit `0`; `verify-boot.ps1` now runs **28 hermetic
suites and 13 live phases**, and its guard digest is identical before and after,
`6978b959…ff348`); the **unchanged** compat suite (observed `Ran 1109 tests ... OK`, exit `0`,
because this line adds no endpoint and no save shape); the content validator (exit `0`,
`result: valid`, 21 schemas); and the preservation manifest (3,258 entries, exit `0`).
`git status` showed no content-package, fixture, save, config, village,
conversion-package, or legacy-source byte changed. The evidence is the deterministic
`unit-definitions-report-v1` report under `apps/client-godot/evidence/unit-definitions/`,
written by the suite itself via `--report=<path>` so its tables are derived from the live
model and registry and cannot drift from the code they document (digest `f997eb2d…66d5`,
byte-identical across three consecutive runs). **Two design premises in the change's own
artifacts were disproved by the Apply stage and corrected rather than shipped** — `costs`
and `properties` are committed **objects**, not embedded-JSON strings (content rule R2
coerces them and `unit.schema.json` declares both `"type": "object"`), and the field count
is **58, not 53**; **a third was narrowed rather than implemented as designed**, because
reaching into the registry's private index was replaced with the public accessor above
rather than re-reading the committed file behind the registry's back. Claim limits: **no
unit is rendered, animated, or played**; **no unit instance, queue, production, collection,
movement, animation, or behaviour is implemented** — each is a separate later M8 deliver
line; **no gameplay semantics are attached to any parsed statistic** (`attack: 10` is a
committed number, not a damage rule, and the suite asserts the absence of any
behaviour-computing helper); the definitions are the committed normalized rows verbatim with
no tuning, balancing, scaling, rounding, or interpolation; **asset linkage is reported and
nothing more** (424/429 whole `img_name` references resolve — 419 `extracted`, 1
`converted`, 1 `missing_source`, 3 `pending` — and the 5 comma-joined rows resolve per part,
446/446), establishing no rendering correctness, animation correctness, or visual fidelity;
**no windowed capture is claimed** because the change alters nothing visual; the committed
`name` values are not unique (six shared by two rows), so `find_by_name()` returns every
match; the committed `-1` upgrade-chain value and every `properties` flag key are reproduced
without interpretation; and the committed corpus has **no unit placements at all**, so no
instance behaviour is evidenced. No Flash, Ruffle, ActionScript, or browser executes in any
of these commands, and no non-loopback traffic is used.

Verified unit-instances commands (milestone M8 line 2; Godot 4.7.2.stable, Windows x64;
`python` denotes the pinned interpreter, never the PATH alias). M8's first
behaviour-shaped line, scoped by the committed investigation
`docs/legacy-unit-instances.md`:

```bash
godot --headless --path apps/client-godot --script res://tests/test_unit_instances.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_definitions.gd
godot --headless --path apps/client-godot --script res://tests/test_project_scope.gd
godot --headless --path apps/client-godot --script res://tests/test_scene_build.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-10-01): the hermetic unit-instances suite
(observed **437 checks**, 440 with `--report`; the 29th hermetic suite) over a
typed read-only `UnitInstance` that **wraps** a legacy map row plus its resolved
definition, with nested-garrison parsing, a named fail-closed depth bound, and
classification by **committed `type`**; the corrected definition suite (observed
**213 checks**, was 204) whose boundary assertion was **rewritten** — it had
asserted that no client source *anywhere* declared a unit instance, a stronger
claim than its requirement made and one this line is chartered to falsify, and it
now asserts the boundary instead (the two delivered modules declare no instance or
queue state, and where an instance type exists it is a distinct script whose held
definition carries the same field inventory and no player state); the scope suite
(**1390**); both batteries in the final state (each exit `0`;
`verify-boot.ps1` now runs **29 hermetic suites and 13 live phases**, guard digest
identical pre/post, `6978b959…ff348`); the **unchanged** compat suite
(observed `Ran 1109 tests ... OK`, exit `0`); the content validator (exit `0`,
`result: valid`, 21 schemas); and the preservation manifest (3,258 entries, exit
`0`). `git status` showed no content-package, fixture, save, config, village,
conversion-package, or legacy-source byte changed. The evidence is the
deterministic `unit-instances-report-v1` report under
`apps/client-godot/evidence/unit-instances/`, written by the suite itself via
`--report=<path>` (digest `A02EEDC8…57BBA0`, byte-identical across three runs).
**Three investigation figures were found to be asserted rather than measured and
were corrected** — `unit_capacity` is non-zero on **5 of 429** units, not 0; the
garrison-capable placed count is **9 rows across 3 distinct item ids**, not 3
rows; and the design's "units carry neither" is restated per field. The capacity
decision is unaffected: the field has **zero** occurrences across five legacy
modules, so **no capacity rule is enforced** regardless of its committed value.
Claim limits: **no executed-legacy fixture, and none fabricated** — the committed
corpus has no unit row (40 rows, 11 distinct ids, all committed `type` `b`, 0
non-empty garrisons, every `attr` bag `{}`), so the zero-instance result is
asserted and instances are demonstrated over **crafted in-memory test input** only;
**no acquisition is claimed** (no committed unit is store-listed; the only
committed unit sources are the later-milestone `offer_packs` and `darts_items`);
**no queue, training, production, collection, movement, animation, or behaviour is
implemented**; the queue keys `nu`/`ts`/`ui` are **reserved and named, not
implemented**; the dead-unit pool is read as an integer count because
`push_dead_unit` discards the row; **no windowed capture is claimed**; and **the
first executed-legacy unit fixture belongs to the `production` line**, because the
Command Center at map key 1 is a real placed training producer and makes the queue
genuinely exercisable. No Flash, Ruffle, ActionScript, or browser executes in any
of these commands, and no network is used.

Verified unit-queues commands (milestone M8 line 3; Godot 4.7.2.stable, Windows x64;
`python` denotes the pinned interpreter, never the PATH alias). M8's first
behaviour-bearing line and the **first to own a real executed-legacy unit
fixture**, scoped by the committed investigation `docs/legacy-production-queues.md`:

```bash
python -B apps/compat-api/capture_queue_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_unit_queues.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_definitions.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_instances.gd
godot --headless --path apps/client-godot --script res://tests/test_content_registry.gd
godot --headless --path apps/client-godot --script res://tests/test_game_api_fake.gd
godot --headless --path apps/client-godot --script res://tests/test_project_scope.gd
godot --headless --path apps/client-godot --script res://tests/test_scene_build.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-10-01): the executed-legacy fixture capture
(exit 0, containment identical, re-runnable) recording a `push_queue_unit` then
`pop_queue_unit` against the committed corpus's **real placed training producer,
id 26 Command Center at map key 1** with an empty `attr` bag — the push sets
`{'nu': 1, 'ts': <instant>}` and the pop removes both keys **together**, while
**every stored resource (gold, wood, steel, oil, xp, energy, mana) is
byte-identical across all three steps**, which is what makes the endpoint's "no
resource moved" half of its two-part proof non-tautological; the fixture manifest
records that a push and a pop were captured, that **no completion was captured**,
and that **no completion command exists**; the hermetic unit-queues suite
(observed **411 checks**, 423 with `--report`; the 30th hermetic suite); the
sibling unit suites (**213** and **437**), the content registry (**87**), the fake
GameApi (**1205**, was 1106), the scope suite (**1441**, was 1339), and the scene
build (**36**); both batteries in the final state (each exit `0`;
`verify-boot.ps1` now runs **30 hermetic suites and 14 live phases**, guard digest
identical pre/post, `6978b959…ff348`); the **grown** compat suite (observed
**`Ran 1257 tests ... OK`**, exit `0` — up from 1109 by **+148**, because this line
adds a state-mutating endpoint, unlike the previous two M8 lines where it stayed
unchanged); the content validator (exit `0`, `result: valid`, 21 schemas); and the
preservation manifest (3,258 entries, exit `0`). `git status` showed no legacy,
config, save, content-package, or prior-fixture byte changed. The evidence is the
deterministic `unit-queues-report-v1` report under
`apps/client-godot/evidence/unit-queues/` (digest `807477db…92090`, byte-identical
across reruns). **The line implements no readiness, no remaining time, no progress
ratio, no completion, no cost, and no count bound**, because the legacy server has
none to reproduce: every `attr["ts"]` use in the legacy source is a write or a
deletion, `apply_resources` applies a **client-sent** vector before dispatch, and
the engine sets no bound on the count — so a documented absence is recorded as a
property and never read as permission to invent a rule. `soulmixer_speedup` is
recorded **verbatim and implemented not at all**: its two-key `ts`+`ui` precondition
(the legacy code raises `KeyError` without both, and the client **refuses** with a
named error instead), the duration read from the **queued unit** rather than the
building, the **seconds** reading, the `ceil(remaining/3600)` shape, the fact that
it **charges nothing**, and the legacy author's own *"Quite useless cost calculation
for understanding it"* verdict. Claim limits: **a queue can never be shown to
finish** — that absence is the finding and is the `production` line's to own;
`sm_training_time` is **absent from 129 units and all 470 buildings**, so it is a
soul-mixer field and not a general training duration; **no acquisition is claimed**
(no committed unit is store-listed; the real sources are the later-milestone
`offer_packs` and `darts_items`); **no unit is produced, trained, or placed**;
production, collection, movement, animations, and basic behaviors remain
undelivered; parity covers **one recorded push/pop transaction** against the
fresh-player corpus, which places only one training producer, and no
progressed-player save is available; no pixel-parity oracle exists. No Flash,
Ruffle, ActionScript, or browser executes in any of these commands, and every
network call is loopback.

**Known-flaky guard:** `verify-boot.ps1` treats any line matching `^ERROR:` as a
script error, so a **nondeterministic** engine shutdown line —
`ERROR: 1 RID allocations of type '…ShapedTextDataAdvanced…' were leaked at exit` —
can fail the battery even though the suite itself exits 0 and passes. It was
observed once on `test_town_xp`; two consecutive reruns passed clean. **Re-run
before treating such a failure as a regression.** Narrowing the guard to
`SCRIPT ERROR` or a fatal-error allowlist is a recorded follow-up.

Verified unit-production commands (milestone M8 line 4; Godot 4.7.2.stable, Windows x64;
`python` denotes the pinned interpreter, never the PATH alias). This is a **refusal
made a capability** rather than a mechanism, scoped by the committed
investigation `docs/legacy-unit-production.md`:

```bash
godot --headless --path apps/client-godot --script res://tests/test_unit_production.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_queues.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_instances.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_definitions.gd
godot --headless --path apps/client-godot --script res://tests/test_project_scope.gd
godot --headless --path apps/client-godot --script res://tests/test_scene_build.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-10-01): the hermetic unit-production suite
(observed **568 checks**, 581 with `--report`; the 31st hermetic suite) over a pure
`production_flow.gd` that projects a queue's presence and start instant **while
stating the server cannot say whether it is ready**, the row-entry inventory with
each item id's source and classification, and the `training_time` and
`add_xp_unit` refusals; the sibling unit suites (**411**, **437**, **213**), the
scope suite (**1475**, was 1441), and the scene build (**36**); both batteries in
the final state (each exit `0`; `verify-boot.ps1` now runs **31 hermetic suites and
14 live phases**, guard digest identical pre/post, `6978b959…ff348`); the
**unchanged** compat suite (observed `Ran 1257 tests … OK`, exit `0`, because this
line adds **no endpoint** and touches `apps/compat-api/**` not at all); the content
validator (exit `0`, `result: valid`, 21 schemas); and the preservation manifest
(3,258 entries, exit `0`). `git status` showed no legacy, config, save,
content-package, or fixture byte changed. The evidence is the deterministic
`unit-production-report-v1` report under
`apps/client-godot/evidence/unit-production/` (digest `E56A470B…33CD6`,
byte-identical across reruns). **The finding is that the legacy server cannot
produce a unit at all**: exactly **five** branches can place a row on the map and
**all five take the item id from the client** — four directly, and `pop_unit` after
it has already **overwritten** the garrison row's item with the client's value.
**`training_time` has zero legacy consumers** (the only matches are the distinct
`sm_training_time`), making it the **third** committed content field with no legacy
consumer after `unit_capacity` and the level curve's unread reward fields, where the
established precedent is to record the field and refuse to invent a rule. The
acquisition routes are **unvalidated client-sent item lists** (`buy_offer_pack`
reads `package_id` and never uses it), so the committed `offer_packs` and
`darts_items` tables are read by no **command branch**. **The suite ASSERTS THE
ABSENCE of any readiness, duration, or award helper, and that guard was tested
rather than trusted**: injecting one `static func is_complete` makes the suite fail
with four independent failures, verified by injection and restore. **Five errors of
mine were corrected after independent measurement**, and **one worker claim was
REJECTED** — it reported 2 occurrences of `training_time` where there are **3**,
having counted distinct *lines* rather than occurrences, and had pinned that wrong
number; the measurement now counts occurrences per line and the occurrence count
and distinct-line count are recorded and asserted separately (566 → 568 checks).
Claim limits: **no production mechanism, completion, or readiness is implemented**;
**no unit is created, trained, or placed**; **no acquisition is implemented or
claimed**; **no duration is derived** from the committed training time; **no
experience is awarded** from the recorded `attr["xp"]`; **no executed-legacy
fixture, because there is no production behaviour to capture** — a stronger
statement than a corpus limitation; death and resurrection are unreachable from
the delivered client and unimplemented; `collection`, `movement`, `animations`, and
`basic behaviors` remain undelivered; no windowed capture and no pixel-parity
oracle. No Flash, Ruffle, ActionScript, or browser executes in any of these
commands, and **no network is used at all**.

Verified unit-collection commands (milestone M8 line 5; Godot 4.7.2.stable, Windows x64;
`python` denotes the pinned interpreter, never the PATH alias). M8's first
**content-derived, server-authoritative** grant and its first genuinely capturable
unit transaction, scoped by the committed investigation
`docs/legacy-unit-collection.md`:

```bash
python -B apps/compat-api/capture_collection_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_unit_collection.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_production.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_queues.gd
godot --headless --path apps/client-godot --script res://tests/test_project_scope.gd
godot --headless --path apps/client-godot --script res://tests/test_game_api_fake.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-10-01): the executed-legacy fixture capture
(exit 0, containment identical, re-runnable) recording one `complete_collection`
against collection 1 (Draggy Collection) whose committed prize is exactly
`{"1085": 1}` — the corpus's **empty** store became exactly `{"1085": 1}` and the
collection ledger went `[]` to `[1]`, so the grant matches the **committed bag
exactly**, the ledger grew by **exactly one appended id**, and **no player state
was fabricated**; this is the **project's first content-derived,
server-authoritative unit acquisition**; the hermetic unit-collection suite
(observed **1884 checks**, 1896 with `--report`, on a 93-file client source tree; the 32nd hermetic suite — **re-measured 2026-10-02**: the earlier recorded 1793/1805 was stale, and a 1845/1857 reading was itself already stale within a day. **This suite's count is NOT a fixed number**: it walks `CLIENT_SCAN_ROOTS` (`res://scripts` and `res://tests`) and asserts per walked source, so **every delivered line that adds a client source raises it**. Re-measure before quoting it); the
sibling unit suites (**568**, **411**), the scope suite (**1526**, was 1475), and
the fake GameApi (**1322**, was 1205); both batteries in the final state (each
exit `0`; `verify-boot.ps1` now runs **32 hermetic suites and 15 live phases**, and
`collection-live` drove one completion with its content-derived two-part proof and
mutated the disposable corpus; guard digest identical pre/post, `6978b959…ff348`);
the **grown** compat suite (observed **`Ran 1352 tests ... OK`**, exit `0` — up
from 1257 by **+95**); the content validator (exit `0`, `result: valid`, 21
schemas); and the preservation manifest (3,258 entries, exit `0`). `git status`
showed no legacy, config, save, content-package, or prior-fixture byte changed.
The evidence is the deterministic `unit-collection-report-v1` report under
`apps/client-godot/evidence/unit-collection/` (digest `81EFAD48…64C`,
byte-identical across three runs). **This COMPLETED, rather than amended, the
`production` line's acquisition finding**: `buy_offer_pack` and
`buy_stored_item_cash` remain unvalidated client-sent item lists, but they are not
the only route, and `godot-unit-production` now names this as the **sole
content-derived** path — without that delta a delivered spec would assert
something false at exactly the moment this line disproved it. Two authority gaps
are recorded as requirements rather than smoothed over: **nothing verifies a
collection was earned**, and the **one-based index makes ids 0 and 1 alias** (the
one-based reading is derived-provisional, corroborated by the committed `id`
column running `1..10` against `legacy_id` `0..9`, with the rejected zero-based
alternative retained). **One imprecision of mine was corrected** after the worker
found it: `harvester` is **not** a top-level committed field but a `properties` flag
key on **5** units (Worker I–IV, Orc Worker), **every one with `collect` 0**; the
zero-consumer finding is unchanged but the list is no longer read as six top-level
fields. Claim limits: **no unit income, payout, cap semantics, or experience
award** — 0 of 429 units carry a positive `collect`, no collect field is ever read,
`max_collects` is 0 on every unit, and `collect_xp`'s only writer is client-sent;
**no collection eligibility is checked**; **ids 0 and 1 alias**; **the stored-item
placement step is not delivered**, so the fixture evidences the grant into storage
and **not** a unit placed on the map, leaving that round trip a carried follow-up;
the committed collections' `item_ids` requirements are unchecked by the server;
`production`, `movement`, `animations`, and `basic behaviors` remain undelivered;
no windowed capture and no pixel-parity oracle. **Known-flaky guard:**
`verify-boot.ps1` treats any `^ERROR:` line as a script error, so a
nondeterministic engine-shutdown RID-leak warning can fail the battery even though
the suite exits 0 — one occurrence was seen, two reruns passed clean, and narrowing
the guard is a recorded follow-up. No Flash, Ruffle, ActionScript, or browser
executes in any of these commands, and every network call is loopback.


Verified unit-movement commands (milestone M8 line 6; Godot 4.7.2.stable, Windows x64;
`python` denotes the pinned interpreter, never the PATH alias). This is the **first M8
line with no Compatibility API endpoint and no executed-legacy fixture**, and both are the
deliverable rather than a gap, scoped by the committed investigation
`docs/legacy-unit-movement.md`:

```bash
godot --headless --path apps/client-godot --script res://tests/test_unit_movement.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_movement.gd -- --report
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-10-01): the hermetic unit-movement suite (observed
**245 checks**, 246 with `--report`; the 33rd hermetic suite) over a typed read-only
placement projection reporting the committed cell, orientation, `width`, `height`,
`elevation`, and `velocity` **verbatim** with nothing derived from another, failing
**closed** with the recorded coordinate slots travelling untouched beside the refusal;
`verify.ps1` exit 0; `verify-boot.ps1` exit 0 with **33 hermetic suites and 15 live phases**
and **no new live phase**; the **unchanged** compat suite (observed `Ran 1352 tests … OK`,
exit 0, because this line adds no endpoint and touches `apps/compat-api/**` not at all); the
content validator (exit 0, `result: valid`, 21 schemas); and the preservation manifest
(3,258 entries, exit 0). `git status` showed no content-package, fixture, save, config,
village, conversion-package, or legacy-source byte changed. The evidence is the
deterministic `unit-movement-report-v1` report under
`apps/client-godot/evidence/unit-movement/` (digest `785B0482…9165E`, byte-identical across
three consecutive runs). **The line implements nothing and that is its finding:** the legacy
server has **no movement rule**, and the one command that moves a row — `move` — is
**type-agnostic**, rewrites the two coordinate slots from client arguments with **no** type,
occupancy, bounds, terrain, or speed check and with `frame` and `string` read but **unused**,
and **already ships** as M7's `building-move`. Across the seven legacy modules there are only
**five** writes to a row's slots 0–2 and exactly **two** branches write coordinates; `orient`
is a plain slot write; and `pop_unit` is the only other coordinate writer, releasing a
garrison row at client-supplied coordinates with the item id overwritten. **`velocity` is the
sixth committed content field with no legacy consumer** and the sharpest instance in the
project — positive on **all 429** committed units and on 145 of 470 buildings and read by
nothing. `fast_forward` makes the row instant **client-writable**, subtracting a
client-supplied number of seconds from every row's instant, every row's queue start instant,
and eleven further map, private-state, research, and quest instants; it has no observable
effect precisely because nothing evaluates elapsed time, and it is named because it is the
instant a client-side readiness check would trust. The **anti-invention guard is structural
and was tested rather than trusted**: injecting one deliberately invented
`static func travel_time(from_cell, to_cell, velocity)` produced **two independent failures**
and restoring the file returned the suite to its 224-check passing state and exit 0. **Two defects were found
and corrected during the line:** the investigation's own slot-0–2 write count was **six**
until `engine.py:62` was measured as `if item[0] == item_id:` — a **comparison** inside
`pop_unit`'s garrison scan, not an assignment — making the count **five** and leaving the
two-coordinate-writer conclusion unchanged (`docs/legacy-unit-movement.md` carries the
correction); and the suite's own measurement reported `ft_flying` as set on **137** units
where the content says **135**, because the normalized package stores the `properties` flags
as **strings** and a non-empty String is truthy in GDScript, so `int(value or 0)` collapsed
the committed `"0"` to `true` and `int(true)` is 1 — verified by probe that `int("0")` is 0,
so **135** is correct, and the flags are now read through one named helper with the encoding
recorded in the report. Claim limits: **no velocity-based travel time, path, terrain or
elevation interaction, occupancy, bounds, readiness, or interpolation is implemented** — the
eighteen recorded `ABSENT_HELPERS` entries are the contract, not omissions; **the committed
movement fields are read by no legacy branch** and are reported as content only; **no
unit-specific movement command exists and none was invented**; **no unit is placed or moved**
and `tests/saves/fresh-player.json` holds no unit row (40 placements, 11 distinct ids, every
committed `type` `b`); **no executed-legacy fixture was captured** because there
is **no unit-specific movement behaviour to capture**, which is stronger than that document's
missing unit row and is recorded as a second and independent reason, while the type-agnostic
move command already has its own executed-legacy fixture under `godot-building-move`; **no
animation is implemented** and M4's converted unit package establishes asset and timeline
**linkage** only, never playback correctness; **no pixel parity is claimed**, the M6
tile-geometry gap remains a recorded gap, and **no windowed capture is claimed** because
nothing is rendered; the placement **view** is owned here while `godot-unit-instances` keeps
ownership of the row, so the two cannot drift; and `animations` and `basic behaviors` remain
undelivered. No Flash, Ruffle, ActionScript, or browser executes in any of these commands,
and no network is used at all.


Verified unit-animations commands (milestone M8 line 7; Godot 4.7.2.stable, Windows x64;
`python` denotes the pinned interpreter, never the PATH alias). The line is scoped by the
committed investigation `docs/legacy-unit-animations.md` (PR #237, merged `ff77e8f`), which was
itself scoped by an explicit instruction **not** to infer animation semantics from M4's converted
unit package — a caution that proved load-bearing, because the single most tempting reading of the
evidence is **wrong** and the package itself refutes it:

```bash
godot --headless --path apps/client-godot --script res://tests/test_unit_animations.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_animations.gd -- --report
godot --headless --path apps/client-godot --script res://tests/test_unit_movement.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_definitions.gd
godot --headless --path apps/client-godot --script res://tests/test_project_scope.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-10-02): the hermetic unit-animations suite (observed **628
checks**, 629 with `--report`; the 34th hermetic suite) over a typed read-only asset-timeline
**linkage** projection reporting the recorded labels, each label's recorded frame position, the
per-sprite recorded frame counts, and the recorded frame rate **verbatim**, failing **closed** when
an asset is absent, unreadable, or label-less rather than defaulting it to an empty, nominal, or
single-frame animation; `verify.ps1` exit 0; `verify-boot.ps1` exit 0 with **34 hermetic suites and
15 live phases** and **no new live phase**; the **unchanged** compat suite (observed `Ran 1352 tests
... OK`, exit 0, because this line adds no endpoint and touches `apps/compat-api/**` not at all);
the content validator (exit 0, `result: valid`, 21 schemas); and the preservation manifest (3,258
entries, exit 0). `git status` showed no content-package, conversion-package, registry-manifest,
fixture, save, config, village, or legacy-source byte changed. The evidence is the deterministic
`unit-animations-report-v1` report under `apps/client-godot/evidence/unit-animations/` (digest
`f06784cb…d8556`, 46,703 bytes, byte-identical across three consecutive runs). **The line implements
nothing and that is its finding:** the legacy server has **no animation rule and no animation
command** — of the 63 named `command.py` branches, five contain animation vocabulary as a substring
and every one is an artifact, with `move` and `orient` being whole-`_`-token matches already owned by
`godot-unit-movement` and `batch_remove` and `remove_inventory_item` pure substring artifacts, while
`end_attack` is combat termination; and **six animation-adjacent committed fields have zero legacy
consumers** across the seven modules (`max_frame`, `img_name`, `attack`, `attack_interval`,
`attack_range`, `velocity`, plus the `animal` flag). **`max_frame` is the seventh zero-consumer
committed field in this project** and is a near-constant: `5` on **427** of the 429 units, `2` on
exactly ids **923** and **933**, and over the 470 buildings `2` on **446** and `1` on **24**. **A
measured contradiction settled the scope:** for the one committed converted unit package the content's
own `img_name` equals the package's `legacy_id`, so both describe the same unit, yet committed
`max_frame` is **2** while the parsed root `frame_count` is **1** and the labelled sprite 63 has
**29** — so `max_frame` is **not** the asset's frame count, and a line that adopted it as one would
be **wrong**. That is recorded as **one** data point and derived-provisional: enough to **refuse
adopting** `max_frame`, not enough to claim what it means, and not a measurement of any other unit,
since only **one** converted unit package and **one** building package are committed. The
**anti-invention guard is structural and was tested rather than trusted**: injecting one invented
`static func frame_duration(frame_count, rate)` produced **two independent failures**, and restoring
the file from a byte-identical copy returned the suite to its passing state. Claim limits: **no
frame duration, loop count, state machine, transition, priority, interrupt, playback order,
per-state timing, animation trigger, or event-to-state mapping is implemented** — the recorded
`ABSENT_HELPERS` are the contract, not omissions, and the module's code contains **zero**
multiplication or division lines, so the no-derivation claim is mechanically true; **the committed
animation fields are read by no legacy branch** and are reported as content only; **`max_frame` is
adopted nowhere** as a frame count, duration, or loop bound, which forced the public accessor to be
named `non_equivalence_record()` rather than after the field, because the suite asserts no code
identifier is named after it; **no legacy branch selects an animation**; **no animation is played,
animated, or rendered**, and the converted unit package establishes asset and timeline **linkage**
only, never playback correctness; **the five label names are reported verbatim in Portuguese and
are deliberately NOT translated** into English state words, because nothing selects a state for a
translation to name — a later line wanting those readings must re-derive them; **no claim is made
for any unit other than the one committed converted package**, which is coverage of **1 of 429**,
with every other path exercised over crafted in-memory packages; **no executed-legacy fixture was
captured**, because there is **no animation behaviour for the legacy server to have**; **no pixel
parity is claimed**; and **no windowed capture is claimed**, because nothing is rendered. No Flash,
Ruffle, ActionScript, or browser executes in any of these commands, and **no network is used**.


Verified unit-behaviors commands (milestone M8 line 8, the **final** M8 deliver line; Godot
4.7.2.stable, Windows x64; `python` denotes the pinned interpreter, never the PATH alias). **This
is the first M8 line that is NOT a refusal**: the investigation it is scoped by
(`docs/legacy-unit-behaviors.md`, PR #244, merged `2e98d55`) was explicitly instructed to measure
its own fields rather than assume the refusal pattern repeats, and that caution was decisive —

```bash
godot --headless --path apps/client-godot --script res://tests/test_unit_behaviors.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_behaviors.gd -- --report
godot --headless --path apps/client-godot --script res://tests/test_unit_animations.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_movement.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_production.gd
godot --headless --path apps/client-godot --script res://tests/test_project_scope.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-10-02): the hermetic unit-behaviors suite (observed **573
checks**, 587 with `--report`; the 35th hermetic suite) over a typed read-only dead-hero ledger
projection reporting the recorded counts, the increment and decrement shapes, the **delete-at-zero**
rule, and **both** legacy gates — the row on **player team 1** and the committed
**`resurrectable > 0`** — verbatim, deriving no third gate, and failing **closed** on an absent
ledger, a non-object ledger, a non-string key, or a non-integer count; `verify.ps1` exit 0;
`verify-boot.ps1` exit 0 with **35 hermetic suites and 16 live phases**; the **grown** compat suite
(observed **`Ran 1444 tests ... OK`**, exit 0 — up from 1352 by **+92**, because this line adds a
state-mutating endpoint, the first M8 line since `collection` to do so); the content validator (exit
0, `result: valid`, 21 schemas); and the preservation manifest (3,258 entries, exit 0). `git status`
showed no content-package, save, config, village, conversion-package, registry-manifest, fixture,
or legacy-source byte changed. The evidence is the deterministic `unit-behaviors-report-v1` report
under `apps/client-godot/evidence/unit-behaviors/` (digest `0FE80C47…8F59`, 39,979 bytes,
byte-identical across three consecutive runs).

**The finding: of twenty-three behavioural committed fields, twenty-one have ZERO legacy consumers**
across the seven modules (`attack` 131 distinct, `defense` 1, `life` 150, `min_level` 21,
`syringes` 6, and every behavioural `properties` flag) — but **two** do not, and one is the **first
committed field in this project whose legacy consumer is a MUTATION of private state rather than a
read**: **`resurrectable`**, **carried by 426 of 429 units** and **0 of 470 buildings** (the key is
**absent entirely** on ids 923, 933, and 1176 rather than set to zero), with exactly **two** reads at
`engine.py:159,162`. **The eighth zero-consumer candidate is not one.** The second is
**`clicks_to_build`**, one read at `engine.py:26` seeding `attr["nc"] = 0`, whose consumer is owned
by `godot-building-construction` and is **referenced, not reimplemented**, here. The mechanism is
`privateState["deadHeroes"]`, a **string-keyed count per item id**, reached by **three** of the 63
dispatcher branches: **`kill`** deletes the row and **never** touches the ledger; **`sell`** calls the
`push_dead_unit` **engine helper** (not a branch) **only** behind the combat-reason guard; and
**`resurrect_hero`** decrements and **deletes the key at zero**, then re-places the row at
**client-supplied** `index`/`x`/`y`. **`used_syringe` is read from `args[4]` and discarded** while the
committed `syringes` field is its obvious counterpart with **zero** consumers, so **no syringe cost
is ever charged** — and the endpoint's **two-part post-execution proof** includes that **every
stored resource is unchanged**, which is what makes that claim non-tautological. The **anti-invention
guard is structural and was tested rather than trusted**: injecting one invented `static func
syringe_cost(syringes)` produced **five independent failures**, and restoring the file from a
byte-identical copy returned the suite to its passing state.

**Five figures in the investigation record were asserted rather than measured, and all five were
corrected by the Apply stage and independently re-verified**: the zero-consumer count was
**twenty-one**, not twenty (the prose said "twenty of twenty-two" while naming twenty-one), and the
behavioural total is **twenty-three**; the source lines were each **off by one** (`push_dead_unit` is
`engine.py:149-170`, `resurrect_hero` is `172-181`, and `del deadHeroes[itemstr]` is at **179**
behind the guard at **178**); `resurrectable` is **carried** by 426 units with the key **absent** on
923/933/1176 rather than set to zero; **`clicks_to_build` takes two distinct values** over the units
(both `0`) rather than three; and **`collect_type` takes two** over the units (`g` 427, `w` 2), the
five-value spread being the *buildings'* only. **None changes the conclusion**, and
`docs/legacy-unit-behaviors.md` carries a corrections section rather than quiet edits.

**A second discrepancy in that same record is annotated here rather than corrected.** The five
combat-field figures it cites — `attack` 131, `defense` 1, `life` 150, `min_level` 21,
`syringes` 6 — read **zero** as legacy consumers under **all six** counting rules applied
over the seven modules `unit_behaviors.gd` declares as `SEARCHED_MODULES`, so **none of the
five reproduces as a consumer**: whole-file occurrences, whole-file distinct lines,
code-only occurrences (comments and string literals stripped), code-only distinct lines,
exact identifier tokens, and the quoted-access form (`"field"` / `'field'`). The measured
`attack` row is `12 / 10 / 5 / 5 / 0 / 0`, and all twelve of its whole-file occurrences sit
inside **longer identifiers** — `end_attack`, `attacker`, `attacker_units`,
`flash_reload_attack` — never the committed field name as a standalone token; the other four
fields have **no** occurrence at all in any view. The figures were **not** invented to match
the prose, because each reproduces **exactly** as the count of distinct committed values over
the **429** committed unit definitions — 131, 1, 150, 21, and 6 — which is the `unit_distinct`
column of `unit_behaviors.gd`'s own `ZERO_CONSUMER_FIELDS` table, with all five present on
all 429 rows and all `int`. The record's numbers are therefore correct and its **placement**
misleads: it reads as a consumer census and is a content-distribution census. **M8's
conclusion is left intact** — these fields are content with no legacy consumer, which this
measurement strengthens — and **no figure is silently replaced**. Note that this change's own
proposal counted "four of five" and is itself **off by one**: it is five of five.

**Three bugs in the new suite were found and fixed by measurement, not by luck**: `_code_only()` was
passed a *path* instead of the body, making the syringe-cost, `nc`, and clicks scans **vacuously
true**; it then desynchronised on an apostrophe inside a double-quoted string, fixed with a proper
two-state lexer; and the live scenario's `addressed.size() != 3` guard silently aborted after 7
checks, which is why the first two live attempts showed no save mutation.

**One deviation was flagged and approved**: `scripts/gameapi/game_api.gd` was edited although it was
not in the worker's ownership list, because all 15 existing live phases drive through the `GameApi`
autoload facade and the `behavior-live` phase would otherwise have had to instantiate `LegacyV0Api`
directly, diverging from the established pattern. The change is three additive pieces in the exact
shape of the 15 existing forwarders, and `test_game_api_fake.gd` (1322 checks) still passes.

Claim limits: **no executed-legacy fixture**, and the reason is **specific** rather than the refusal
lines' "no behaviour exists" — `resurrectable` is **unit-only**, `tests/saves/fresh-player.json` places
**only buildings** and **no unit row**, and its ledger is present and `{}`; manufacturing a
unit row is refused, as `godot-unit-instances` refused. Unlike the refusal lines, the cause is the
**absence of a resurrectable row**, not the absence of behaviour. **That premise is now SCOPED, and the
scope is measured rather than implied**: it is true of that ONE document and false of the repository, which
places **441 unit rows across 7 of the 10 committed save documents** (`test_unit_behaviors.gd`'s `repository_census`, and
`test_combat_actions.gd`'s census, agree). The absence-of-fixture cause is therefore
unchanged, because the document this line measures and drives is the fresh-player one. **No combat is resolved** — `attack`,
`defense`, `life`, `attack_interval`, `attack_range`, `best_against`, and `best_against_mult` are
content with zero consumers. **No syringe cost** and **no resource movement**. **No occupancy,
bounds, type, or terrain validation** is added to the revived placement, reproducing the legacy
branch's absence and recording it as a Server v1 / M13 gap. The **death/resurrection pairing is
derived**, not asserted by the source. The committed corpus is **not** all team 1 — keys 1–20 are
team 1 and **21–40 are team 3** — which gate one alone does not need but which any future claim must
respect. **No pixel parity** and **no windowed capture**. This **completes** the delivered
`godot-unit-production` record: its claim that death and resurrection are unimplemented stays **true
of the delivered client**, but the server behaviour it left unstated is now recorded. No Flash,
Ruffle, ActionScript, or browser executes in any of these commands, and every network call is
loopback.

Verified unit-research commands (milestone M9 line 1; Godot 4.7.2.stable, Windows x64;
`python` denotes the pinned interpreter, never the PATH alias). M9's deliver list is `XP`, `levels`,
`quests`, `research`, `collections`, and `tutorial/progression`, and its exit criterion is "Primary
long-term progression systems work." This is its **first** line, and the first M9 deliver line at all.
The contract is committed in `docs/legacy-m9-progression.md` (PR #250, merged `f74647c`), extended by the
research measurements in PR #252 (merged `3d44159`):

```bash
python -B apps/compat-api/capture_research_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_research.gd
godot --headless --path apps/client-godot --script res://tests/test_research.gd -- --report
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-10-02): the executed-legacy fixture capture (exit 0, **re-runnable
across three runs**, containment identical) recording **eight** branch-track transactions against the
committed corpus's real `[0, 0]` research vector — `login_post` plus `next_research_step`,
`research_buy_step_cash`, `next_research_item`, and `reset_research_item`, each on **both** tracks — with
transitions such as `next_research_step` track 0 `[[0,0],[0,0],[0,0]] -> [[1,0],[0,0],[<instant>]]` and
`next_research_item` track 0 `[[1,1],[0,0],[0,0]] -> [[0,1],[1,0],[0,0]]`, the latter showing the **paired**
step-and-instant reset; the hermetic research suite (observed **1024 checks**, 1038 with `--report`; the
**36th** hermetic suite) over a typed read-only projection of both tracks and all three counters reported
**verbatim**, failing **closed** on five malformed shapes; the **grown** compat suite (observed
**`Ran 1572 tests ... OK`**, exit 0 — up from 1444 by **+128**); both batteries in the final state (each
exit `0`; `verify-boot.ps1` runs **36 hermetic suites and 17 live phases**, and **221** log files
inspected with **zero** `^ERROR:` or `SCRIPT ERROR` lines); the content validator (exit `0`, `result:
valid`, 21 schemas); and the preservation manifest (3,258 entries, exit `0`). Evidence is the
deterministic `research-report-v1` report under `apps/client-godot/evidence/research/` (digest
**`e62f2666…c86`**, 32,607 bytes, byte-identical across **four** runs).

**The finding: the three research counters are WRITE-ONLY.** `researchStepNumber` has **3** sites and
`researchItemNumber` **2**, every one a write, and `timeStampDoResearch` has **5** — the four branch
writes plus **one read at `command.py:923` that is itself a write**, because it sits inside
`fast_forward` and subtracts a **client-supplied** number of seconds, clamped at zero (`seconds = args[0]`
at `command.py:906`). **Nothing anywhere reads a research counter to decide anything**: a guard audit of
all four branches finds **no** bounds check, numeric clamp, membership test, exception guard, or existence
check. `fast_forward` is therefore recorded as a **fourth writer** and makes the research instant
**client-writable** — and since no readiness check exists, an instant trusted by nothing is the only
elapsed-time input the research system has. `research_buy_step_cash` reads a **client-supplied cash value
and discards it**, structurally identical to M8 line 8's `used_syringe`, and **no research price is
charged** — proved non-tautologically by every action's post-execution check that the **complete** stored
resource set is unchanged. **No committed research content exists to derive a schedule from:** `research`
appears in the content **only** as asset names and one building's display name. **The anti-invention
guard is structural and was tested rather than trusted**: injecting one invented `static func
research_price(track, step)` produced **four independent failures** against a pinned whole
static-function inventory, and restoring the file from a byte-identical copy returned the suite to its
1024-check passing state and exit 0.

**Three figures in the committed investigation were asserted rather than measured, and all three
overstated the absence of committed research content; they were corrected by the Apply stage after
independent re-verification**, and `docs/legacy-m9-progression.md` carries a corrections section rather
than quiet edits: `research` appears in **two** normalized files (`buildings.json` **1**, `images.json`
**6** from three popup-asset rows), not one; `config/main.json` **does** have **three** nested keys
containing it, all in the `/images` asset namespace, so "no key at any depth" is **false**, though no
top-level key contains it; and the building's `legacy_id` is the **string** `"256"`, not an integer, since
every `legacy_id` in `buildings.json` is a string. **The conclusion is unchanged** — every hit is an asset
name or a display name, so there is still **no committed research cost, step count, unlock requirement, or
reward** — but the refusal now rests on a **correctly measured** basis rather than an overstated one.

**One measurement strengthened the cross-milestone correction rather than weakening it:** `map_lose_item`
is `engine.py:215-228` with `push_dead_unit` called at **223**, and its only **two** callers are
`command.py:796` inside **`end_quest`** and `command.py:872` inside **`end_attack`**. So the dead-hero
ledger has **four** doors, not the three `godot-unit-behaviors` claimed, and the fourth is reached from
**two** branches — the quest path and the attack path — not one.

Claim limits: the delivered feature means **these counter transitions and nothing more**, because the
counters have **no in-game consumer**; **no price is charged and no stored resource moves**; **no
completion, readiness, remaining-time, or unlock semantics** are implemented; **no counter bound,
membership rule, or clamp** is added, the legacy branches having none, so a client could still send track
`7` or `999` and that is a recorded **Server v1 / M13** gap; **no reward** is paid; **no committed
research content is invented**, none existing; the **track-to-building mapping is reported and never
used** — `TYPE_AREA_51` and `TYPE_ROBOTIC` appear **4** times each in `command.py`, **0** in the other six
modules, on comment lines `269`, `278`, `285`, `294` and are defined nowhere, so the suite asserts **no
delivered code identifier is named after either**, which makes the "never used" claim mechanical; **no
fast-forward operation is delivered**; fixture parity covers **eight** transactions against the
fresh-player corpus only, and the item branch's instant half is a recorded **0→0** transition because the
recorded capture order had already zeroed both instants, with the pairing established instead by
`command.py:288-289`; the track-to-building mapping is **derived-provisional** from the comment's word
order and the four `print` display lists; **no pixel parity** and **no windowed capture** are claimed,
because nothing is rendered and the corpus places neither research building. **Known-flaky guard:** as on
every prior line, `verify-boot.ps1` treats any `^ERROR:` as a script error, so an engine-shutdown RID leak
or a transient Windows module-load crash can fail it on an untouched phase; narrow it to `SCRIPT ERROR` or
a fatal-error allowlist. No Flash, Ruffle, ActionScript, or browser executes in any of these commands, and
every network call is loopback.
Verified unit-quests commands (milestone M9 line 2; Godot 4.7.2.stable, Windows x64;
`python` denotes the pinned interpreter, never the PATH alias). M9's deliver list is `XP`, `levels`,
`quests`, `research`, `collections`, and `tutorial/progression`; this is its **second** line and its
**largest surface**, with six undelivered branches. The contract is committed in
`docs/legacy-m9-quests.md` (PR #258, merged `0e886f2`):

```bash
python -B apps/compat-api/capture_quest_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_quests.gd
godot --headless --path apps/client-godot --script res://tests/test_quests.gd -- --report
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-10-03): the executed-legacy fixture capture (exit 0, re-runnable,
containment identical) recording **six** branch transactions plus login and **five** executed probes
against the committed corpus's quest state; the hermetic quest suite (observed **1223 checks**, 1238 with
`--report`; the **37th** hermetic suite); the **grown** compat suite (observed **`Ran 1751 tests ... OK`**,
exit 0 — up from 1572 by **+179**); both batteries in the final state (each exit `0`;
`verify-boot.ps1` runs **37 hermetic suites and 18 live phases** with guard digest `6978b959…ff348`
identical pre/post); **484** log files inspected with **zero** `[test] FAIL`, `^ERROR:`, or
`SCRIPT ERROR` lines; the content validator (exit `0`, `result: valid`, 21 schemas); and the preservation
manifest (3,258 entries, exit `0`). Evidence is the deterministic `quests-report-v1` report under
`apps/client-godot/evidence/quests/` (digest **`412dd271…6019`**, 37,102 bytes, byte-identical across
**three** runs).

**Only TWO committed quest fields are read by anything**, measured as quoted occurrences across the seven
modules so comments cannot contribute: `id` has **8** and `title` has **2**, the latter being the two
`print` statements. `hint`, `description`, `kind`, `legacy_id`, `source_file`, `source_layer`,
`content_version` all have **zero** — and **`reward` has ZERO** while being committed on all **91**
entries and **uniformly the value `10`**, so it carries no information even if it were read. **There is
therefore no quest reward, cost, or price to derive**, and none is.

**`complete_goal` mutates nothing at all**, and the executed fixture proves it: the captured transaction
changed **no** `privateState` key and **no** `maps[0]` key. A goal "completes" by being narrated in a
`print` statement.

**Three legacy type and shape facts are reproduced rather than normalized, each confirmed by the captured
oracle:** `collect_mission` wrote `idCurrentMission` as the **string** `'5'` against a corpus recording the
**integer** `0`; `set_quest_var` self-healed `currentQuestVars` from the corpus's **`None`** to a dict; and
`end_quest` wrote `questTimes` `{}` to `{'7': <instant>}`.

**THE DIVERGENCE IS MEASURED, NOT ASSERTED.** Probe 4 sends `end_quest` with `units = [[26, 0, 1, 0]]` so
the legacy branch's client-computed `lost = max(0, unit[2] - unit[3])` is **1**: the legacy server
**destroyed a placed row, 40 → 39**, while the modern endpoint derives `units: []`, destroys nothing, and
leaves **all 40 rows byte-identical**. The manifest records this as a **divergence**, not as parity, and
records separately that the *captured transaction's* rows were byte-identical — because that step carried
no lossy tuple. **Reproducing a client-dictated destruction count would be exactly the anti-pattern
`AGENTS.md` names as "Bad".**

**Three more probes establish the refusals with executed evidence:** `set_goals([500, "[0,0]"])` grew the
list from **151 to 501** entries — **350** appended from one client-sent id, with **no upper bound**, so the
endpoint **reproduces** the unbounded growth rather than closing it; `set_quest_var(["idSimpleChapter", 5])`
wrote **nothing** (the branch returns at `command.py:95` before any write) while an invented key **was**
accepted, so exactly **one** key is refused and it is the one the legacy branch itself ignores; and
`collect_mission([150])` wrapped to **`1`** at bound `99`, stored as a **`str`**.

**FIVE CROSS-LAYER DEFECTS THAT THE HERMETIC SUITE STRUCTURALLY COULD NOT CATCH.** The offline suite builds
its own response envelope, so **1223 hermetic checks passed while the live phase failed five separate
times** — the most important verification finding of this line. Each was found only by `quests-live`: the
transport sent every action's addressing under a fixed `addressing` key while the service reads the
*per-action* key; `project_quests()` never emitted the `resolvable` flag the typed parser requires, so all
six live responses were refused `bad_response`; the parser demanded `end_quest_blob` unconditionally while
the service sends `null` for the other five; `int()` on a recorded null goal is a nonexistent constructor in
Godot 4; and **Godot decodes every JSON number as a `float`**, so `[0,0]` arrives as `[0.0,0.0]`. New guards
were added for the class — the third request key is asserted equal to `ACTION_ADDRESSING_KEY[action]`, the
transport must call `wire_key()` and must contain no hardcoded `"addressing":`, and the suite asserts the
double builds no body at all, **recording why it could not catch any of the five**.

**Two anti-invention guards, both tested by injection rather than trusted.** Re-run by the orchestrator:
injecting `quest_reward` produced **4 independent failures** and exit 1, injecting `mark_goal_complete`
produced **4 independent failures** and exit 1, and restoring the byte-identical file (SHA-256
`631a564d…fa12`) returned the suite to exit **0** with **1223 checks**. The report digest reproduced exactly
across three runs.

Claim limits: **no quest reward is paid and no stored resource moves**, and the uniform `10` is recorded as
**not** a payout; **the `end_quest` destruction count is refused** and the difference from the legacy server
is a **divergence**, not parity; **no bound is added** to the on-demand goals list and **no membership test**
to the quest-variable writer, both absences being Server v1 / M13 gaps deliberately not filled; **no
completion state exists** because the completion branch mutates nothing; `unlockedQuestIndex` is reported
and **never written**, having **zero** legacy sites — the ninth such field in this project; **no
fast-forward operation is delivered**, though `command.py:942-944` and `911` are recorded as quest-state
writers making quest timing client-writable, and `version.py:38-44` is recorded as a **migration**, not
gameplay; the committed content is **reported and never used**, and no delivered identifier is named after
the reward field; parity covers **six** transactions and five probes against the fresh-player corpus only;
the five **missing-key** refusals are **structurally unreachable through the typed client**, because the
addressing is a required parameter, and the live phase proves this rather than asserting it; the hermetic
suite **cannot** detect envelope or wire drift by construction, so `quests-live` is the only guard for that
class and is a single phase; **no pixel parity** and **no windowed capture**, because nothing is rendered.
**Known-flaky guard:** as on every prior line, `verify-boot.ps1` treats any `^ERROR:` as a script error, so a
nondeterministic RID-leak/shutdown line or a transient `0xC06D007F` module-load crash can fail it on an
untouched phase. `verify.ps1` additionally returned **-1** on one of two runs and **0** with
`PASS all checks succeeded` on the second, because its windowed-capture step is display-sensitive — a third
recorded flaky surface. Re-run before treating any of the three as a regression. No Flash, Ruffle,
ActionScript, or browser executes in any of these commands, and every network call is loopback.
**A seventh flaky surface, found by this line: the `test_no_server_is_running`
family can fail transiently.** Roughly 20 pre-existing compat test classes
assert that ports 5055 and 5056 are free, via
`compat_test_harness.port_is_free()`. Running
`python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py"`
**three times back to back** produced **19, 24, and 2** failures, while
single runs and later back-to-back runs passed clean (`Ran 2438 tests ... OK`).
Every failure was one of those port assertions. **Three candidate causes were
measured and all three DISPROVED**, which is why this is recorded as open
rather than explained: **TIME_WAIT** does not block the helper's `bind()`
probe (verified by generating real TIME_WAIT sockets -- a single one and ~120
on one port both bind fine, and `port_is_free(5056)` returns `True` right now
with ~300 TIME_WAIT entries present); there is **no stray process** holding the
port; and **neither port is in a Windows excluded range** (`netsh` reports only
5357). No compat test binds either port -- `test_compat_v0.py` uses
`APP.test_client()` in-process and `run.py --help` never binds. **The mechanism
is not established.** This line did not introduce it (it adds one more instance
of an existing assertion) but it did increase exposure, by adding a suite that
binds 5056 in its live phase. **Re-run before treating it as a regression.**
Note also that `port_is_free` is a *bind* probe, which on Windows cannot
distinguish "in use" from "cannot bind"; a `connect` probe would answer the
real question but would raise inside the harness's own `offline()` guard, whose
`_NoConnectSocket.connect` raises `AssertionError`. **Not changed here** --
reworking a shared containment assertion across 20 existing suites is a
separate change, and guessing at the mechanism is how an unearned fix ships.

**An eighth recorded flaky surface, found by the M11 friends line:
`test_collect_endpoint.ContentRefusalTests.test_a_recent_instant_is_too_early`
has a sub-second time budget and can fail under load.** It stubs the row's
collection instant to `BOOT.server_time() - 299`, and `BOOT.server_time()` is
`int(self._engine.timestamp_now())` -- the **live** clock
(`compat_legacy.py:195-196`) -- while the refusal it expects, `too_early`, is
decided against the endpoint's **own** live clock. So the test only holds while
the gap between reading `reference` and the request landing is **under one
second**; one second of build-up flips elapsed from 299 to 300, the first
committed rung is reached, and the assertion sees `200 != 409`. It failed
exactly once, inside `verify-boot.ps1`'s compat step, immediately after 47
headless Godot suites had run; `test_collect_endpoint.py` alone then passed
**five consecutive times** (`Ran 57 tests`, OK, ~1.85 s each) and the full
discovery passed at `Ran 3077 tests ... OK`. **It is pre-existing and unrelated
to the friends line**, whose diff touches **no** `apps/compat-api/**` file --
established by `git diff --name-only` returning only
`apps/client-godot/evidence/boot/boot-report.json`,
`apps/client-godot/tests/test_project_scope.gd` and
`apps/client-godot/verify-boot.ps1`, plus three new client-side paths. The
sibling boundary test `test_the_rung_is_reached_at_exactly_the_first_threshold`
confirms the mechanism: the refusal really is at elapsed 300. **Not fixed
here** -- the honest fix belongs to `godot-building-collect`, which owns the
collect refusal, and reworking an already-archived line's clock stub from an
unrelated change is how an unearned fix ships. **Re-run before treating it as a
regression.**

Verified unit-tutorial commands (milestone M9 line 3; Godot 4.7.2.stable, Windows
x64; `python` denotes the pinned interpreter, never the PATH alias). M9's deliver
list is `XP`, `levels`, `quests`, `research`, `collections`, and
`tutorial/progression`; this is its **third** line and the first **not** to be a
refusal line. The contract is committed in `docs/legacy-m9-tutorial.md`
(PR #264, merged `2dbf715`):

```bash
python -B apps/compat-api/capture_tutorial_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_tutorial.gd
godot --headless --path apps/client-godot --script res://tests/test_tutorial.gd -- --report=<repo>/apps/client-godot/evidence/tutorial/report.json
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-10-03): the fixture capture (exit **0**,
containment **UNCHANGED**, re-runnable across **five** consecutive runs,
recording two transactions against a disposable corpus over loopback); the compat
suite (observed **`Ran 1914 tests ... OK`**, exit `0` — **1912** at Apply, plus
**+2** from the recorded follow-up PR #268); the hermetic tutorial suite
(observed **639 checks**, 642 with `--report`; the **38th** hermetic suite, and
**re-measured 2026-10-05 at 639, exit 0**); both batteries in the final state
(each exit `0`; the second embeds the `tutorial-live` phase, and at delivery ran
**38 hermetic suites and 19 live phases** with guard digest `6978b959…ff348`
identical pre/post and **264** log files carrying zero `[test] FAIL`, `^ERROR:`,
or `SCRIPT ERROR` lines); the content validator (exit `0`, `result: valid`, 21
schemas); and the preservation manifest (3,258 entries, exit `0`). Evidence is
the deterministic `tutorial-report-v1` report under
`apps/client-godot/evidence/tutorial/` (digest **`05f7b12d…c38b`**, **10,634**
bytes in LF form — **re-verified 2026-10-05** against the committed Git blob,
which is byte-identical, so the figure holds on an LF or a CRLF checkout; the
CRLF working tree shows 11,026 bytes for the same content). On merged `main`
today `verify-boot.ps1` registers **40 hermetic suites and 20 live phases**, and
`test_tutorial.gd` is among them.

**The finding: one branch, one write, one stored field, and three reachable
verdicts.** `command.py:60-66` is the entire tutorial system:

```python
if command == "complete_tutorial":
    tutorial_step = args[0]                                 # :61  a LOCAL
    print("Tutorial step", tutorial_step)                    # :62  a log line
    if tutorial_step >= 25 or tutorial_step == 15:           # :63  the gate
        save["playerInfo"]["completed_tutorial"] = 1         # :65  the write
```

`completed_tutorial` occurs **once** across the eleven legacy root modules, and
that line is the **write**, making it the **tenth** committed field in this
project with no legacy consumer. `tutorial_step` occurs **4** times over **3**
lines and is a **local** that is **never persisted**, so there is **no stored
step** and therefore nothing to resume from. The gate has **no lower bound, no
upper bound, and no type check**: it completes at `15, 25, 26, 100, 1000000,
1000000000` and declines at `-1000000000, -5, -1, 0, 1, 14, 16..24`, so the
**hole is exactly `16..24`**, nine steps wide, between the two arms. The endpoint
checks the **flag before the gate**, so once a tutorial completes it stays
complete regardless of the step sent.

This line is the clearest case for the standing instruction to *measure your own
fields rather than assume the refusal pattern repeats*: the field was assumed to
be dead by the two preceding M8 lines and is not.

Claim limits: **no total step count is derived** — none is committed, so a
`total_steps()` helper would invent one (and injecting one was **proven** to fail
three independent checks); **the stored flag has zero readers**, so the delivered
gate is a faithful reproduction of an inert one and does not gate any client
option; **the step is client-supplied and unvalidated**, and the `16..24` hole is
**recorded, not reproduced as a client affordance**; **the three verdicts and
their order are derived from the branch**, not observed from the Flash client;
raising-shape divergences between the service and the client are **recorded
rather than reproduced**; parity covers **two** recorded transactions against the
fresh-player corpus only, with no progressed-player save available; **no pixel
parity** and **no windowed capture**, because nothing is rendered. **A fourth
recorded flaky surface** was added by this line: a GDScript `%`-binding slip in
the live phase's marker line made the suite unparseable and `verify-boot.ps1`
failed while every hermetic suite passed — caught by reading the log files, which
is why `SCRIPT ERROR` and not only `^ERROR:` must be grepped. No Flash, Ruffle,
ActionScript, or browser executes in any of these commands, and every network
call is loopback.
Verified stored-item-placement commands (M9's first post-assessment line; Godot 4.7.2.stable,
Windows x64; `python` denotes the pinned interpreter, never the PATH alias). This is the **first
working round trip** in the M8/M9 sequence rather than a refusal line, and the contract is committed
in `docs/legacy-stored-unit-placement.md` (PR #271, merged `6bb7a46`):

```bash
python -B apps/compat-api/capture_stored_placement_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_stored_item_placement.gd
godot --headless --path apps/client-godot --script res://tests/test_stored_item_placement.gd -- --report=<repo>/apps/client-godot/evidence/stored-placement/report.json
godot --headless --path apps/client-godot --script res://tests/test_unit_collection.gd
godot --headless --path apps/client-godot --script res://tests/test_project_scope.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
openspec validate --all --strict
```

Purposes and observed results (2026-10-03/04): the executed-legacy fixture capture (exit 0 on **four**
consecutive runs, containment **UNCHANGED** at `18e5e55b…a724`, five steps chained
`login_post` → `complete_collection(1)` → `place_stored_item` → `complete_collection(1)` →
`sell_stored_item`, seeded through committed content because the corpus's own `maps[0]["store"]` is
`{}`; the placement changed exactly **3** top-level paths = 8 leaves with the count 40 → 41, the sale
changed exactly **1** leaf — a **removed** storage key — and **no refund**, `login_post` changed **0**
leaves, and **all seven stored resources are byte-identical in all five steps**); the hermetic
stored-item-placement suite (observed **544 checks**, the **39th** hermetic suite); the
**amended** collection suite (observed **1,894**); `test_project_scope.gd` (**1,781**),
`test_game_api_fake.gd` (**1,322**), `test_unit_production.gd` (**568**),
`test_unit_animations.gd` (**628**), `test_unit_behaviors.gd` (**573**), `test_research.gd` (**1,024**),
`test_quests.gd` (**1,223**), `test_tutorial.gd` (**639**), `test_content_registry.gd` (**87**), and
`test_scene_build.gd` (**36**); both batteries in the final state (each exit `0`;
`verify-boot.ps1` now runs **39 hermetic suites and 20 live phases**, guard digest
`6978b959…ff348` identical pre/post, and **574** log files inspected with **zero** `[test] FAIL`,
`^ERROR:`, or `SCRIPT ERROR` lines); the **grown** compat suite (observed **`Ran 2130 tests ... OK`**,
exit `0` — **+216** over the 1,914 baseline, because this line adds two state-mutating routes, the
envelope module, and three test modules); the content validator (exit `0`, `result: valid`, 21
schemas); the preservation manifest (3,258 entries, exit `0`); and `openspec validate --all --strict`
**60 passed / 0 failed**. Evidence is the deterministic `stored-placement-report-v1` report under
`apps/client-godot/evidence/stored-placement/` (digest **`c5bea9dd…8d18`**, 13,618 bytes, byte-identical
across **four** runs). The compatibility service listens on `127.0.0.1:5056` only, and every network call
in these commands is loopback.

**The finding: `place_stored_item` is NOT a refusal line.** **24 executed probe transactions**
established that the two branches at `command.py:233-256` are **type-agnostic** (no building/unit
distinction), **charge nothing**, and are **server-derived in five of eight row slots** — the instant,
the orientation, the garrison list, the player team, and an `attr` bag that is a **pure function of
committed content**. Four unguarded behaviours were confirmed by execution and **three are refused**
(`unknown_item_id`, `item_not_placeable`, `not_in_storage`, in that pinned order, to
`compat_service.py:1562`, `:1570`, `:1596`); the **fourth**, an out-of-grid cell, is the
**already-recorded M6 geometry gap** and is therefore *recorded and reported, never refused*, because
inventing a bound would fabricate a rule the oracle does not have. `store_add_items` is **out of
scope**: it is an unvalidated client-sent grant and is probe-only. Four of the ten committed collection
prizes are **buildings**, which corrects the assessment's framing and is why the scope is written
against the **prize**, not the word "unit".

**Two corrections the Apply stage made to its own prior claims, recorded rather than quietly fixed.**
(1) *"each appears on exactly one line"* is true only **branch-scoped** for `playerID` and
`orientation` — whole-file `args[4]`×7, `args[5]`×4, `args[6]`×4, `args[7]`×2 — and **globally
unique** only for `unknown_autoactivable_bool` and `unknown_imgIndex`; the suite now asserts **both**
scopes. (2) The service's `resources()` returns `xp, gold, wood, oil, steel, cash, mana` — **seven**,
**not** the M7 readout's set, which also surfaces the never-written `privateState.energy` — so every
no-resource-moved proof compares the seven.

**Two anti-invention guards, both proven by injection rather than trusted:** injecting
`static func cell_is_free(from_cell: int, to_cell: int) -> bool` into the delivered flow module
produced **3 independent failures** and exit 1, and `static func refund_for(item_id: int) -> int`
produced **1** — which is how the by-name guard was found to match only the exact name and miss a
suffixed helper wearing the same disguise, so a substring check was added and the same injection then
produced **2**; restoring the byte-identical module (SHA-256 `0b437e5d…0edbd`, re-measured after
restore) returned the suite to its 544-check passing state and exit 0 both times. The whole-inventory
pin is the real gate; the by-name guard is the belt.

**A cross-suite boundary was amended, not deleted.** `test_unit_collection.gd::_check_boundary()`
asserted that the placement token was absent from **every** client source; that claim became **false**
the moment this line landed and was **measured failing with 4 failures** before being touched. The
whole-tree absence was replaced by an **ownership claim**, and — because two suites scanning one tree
for one token with two hand-maintained owner lists is drift waiting to happen — the owner list lives
**only** in this line's suite while the collection suite asserts that the hand-off's **recipient exists
and asserts it**.

**Four cross-layer defects the hermetic suite structurally could not catch**, all found by
`stored-placement-live`: the bootstrap payload is keyed `map` while the recorded fixture documents are
keyed `maps[0]`, so one storage assertion had been **passing for the wrong reason**;
`CollectionResult` has no `count_after`, so a bad field aborted the function before the sale and both
refusals ever ran; the service's and the client's copies of the recorded geometry and quantity notes
are deliberately **not** identical, so the suite had been asserting byte-equality and claiming
"verbatim" — **stronger than anything true** — and now asserts the identifying **clauses** instead; and
the sale's ledger append is **if-absent**, so a repeat completion grants the prize again while the
collection ledger **stands still**, the opposite of what the first draft asserted and the fact that
makes the sale reachable at all.

**A sixth recorded flaky surface was found by this battery and FIXED rather than re-run.**
`verify-boot.ps1` failed `test_collection_endpoint.ContainmentTests` once on `server_time`
**1791066504** against **1791066505** with every other field identical, while three immediate reruns
passed; `/v0/session` stamps the current time on every response, so a whole-document equality across
two calls was always going to fail when they straddled a second. The first fix was then found wrong in
the **other** direction by running that file alone, because when both calls land inside one second the
clock does *not* differ — so the assertion is now that the differing-field set is a **subset** of the
documented volatile field, the only claim true in both cases and exactly as strict about every other
field as before. That guard was made to fail rather than trusted: injecting a real session-list change
produced `AssertionError: {'saves'} not less than or equal to {'server_time'}`, and restoring the
byte-identical file (`8efd62d8…7ab6`) returned it to 36 tests and `OK`. **This is the first recorded
flaky surface in this project that was closed rather than re-run.** The other five remain as recorded
above.

Claim limits: **the round trip only** — storage to map and storage to gone, with no intermediate step;
**no price in either direction**, because the legacy refund travels in **client-sent deltas** this
contract refuses; **no capacity, expiry, value, or price rule**; **no bounds and no occupancy check** —
the M6 geometry gap is recorded, never refused; **no refund is claimed or paid**; `store_add_items` is
out of scope; **placement is type-agnostic**, exactly as the legacy branch is, so a building prize is
placed through the same route, and because occupancy is unchecked this line cannot give any 2×2 or 3×3
prize a correct cell — it ships on the 1×1 Metal Draggy prize and records the rest; **nothing is
rendered**, so there is **no windowed capture** and **no pixel-parity oracle**, and storage remains a
readout; **no unit is moved, trained, or animated**; **parity covers five recorded transactions against
the fresh-player corpus only**, and no progressed-player save exists; the **committed capture runs the
fake** implementation, so real-execution parity rests on the fixture-replay tests and the live phase.
No Flash, Ruffle, ActionScript, or browser executes in any of these commands, and every network call is
loopback.
Verified unit-experience commands (M9's second post-assessment line; Godot
4.7.2.stable, Windows x64; `python` denotes the pinned interpreter, never the
PATH alias). This is the **eleventh and final** M9 line, and the only one whose
deliverable is **two branches that disagree with each other**. The contract is
committed in `docs/legacy-unit-xp.md` (PR #276, merged `79d13ac`):

```bash
python -B apps/compat-api/capture_unit_xp_fixture.py
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
godot --headless --path apps/client-godot --script res://tests/test_unit_experience.gd
godot --headless --path apps/client-godot --script res://tests/test_unit_experience.gd -- --report=<repo>/apps/client-godot/evidence/unit-experience/report.json
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
```

Purposes and observed results (2026-10-04): the executed-legacy fixture capture
(exit **0**, **12 transactions, 12 disposables, 12 servers**, containment digest
`18e5e55b…a724` identical before and after, no working-tree `saves/`, all **17**
prior fixtures untouched, re-runnable); the compat suite (observed **`Ran 2187
tests … OK`**, exit `0`, against the 2,130 baseline — **+57**); the hermetic
unit-experience suite (observed **2,432 checks**, **2,430** without `--report`,
exit `0`; the **40th** hermetic suite — **re-measured 2026-10-05 at 2,430**, exit
`0`); both batteries in the final state (each exit `0`, `PASS all checks
succeeded`; `verify-boot.ps1` ran **40 hermetic suites and 20 live phases** with
guard digest `6978b959…ff348` identical pre/post and **636 log files inspected
with zero** `ERROR:` / `SCRIPT ERROR` / `[test] FAIL`; **no new live phase**, since
the line adds no endpoint); the content validator (exit `0`, `result: valid`, 22
files / 21 schemas / 604 references); the preservation manifest (3,258 entries,
exit `0`); and `openspec validate --all --strict` (**61 passed / 0 failed** at
Apply, **62 / 0** after Sync, the new capability being a new spec item).
`test_project_scope.gd` needed an amendment and was re-run to **1,798 checks**
after a stray build artifact was **deleted, not worked around**. Evidence is the
deterministic `unit-experience-report-v1` report under
`apps/client-godot/evidence/unit-experience/` (digest
**`d83282ac…a7ef4`**, **38,465** bytes in LF form — **re-verified 2026-10-05**
against the committed Git blob, byte-identical; byte-identical across three
consecutive runs at delivery, and the CRLF working tree shows 39,726 bytes for the
same content). Committed evidence lives under
`tests/fixtures/godot-unit-experience/` (79 files, 1,465 KB).

**The finding: the two arms disagree, and that asymmetry is the deliverable.**
`add_xp_unit` at `command.py:334-340` assigns `attr["xp"] = xp_gain` when the key
is **absent** and increments with `+=` when it is **present**. The amount is
`args[1]`, **entirely client-supplied**, with **no validation whatsoever — not
even `int()`**. So one request can poison a save (`{"xp": "5"}` is persisted on
the assign arm) while the increment arm **raises** on the same string (HTTP 500,
zero leaves changed). A projection that folded `bool` into `int` would be right
by accident and wrong by reason, which is why the delivered model records
`recorded_kind`. **Boolean is narrower than it first looks:** on the increment arm
a client-sent `true` is worth exactly **+1** and the row moved **23 → 24**, an
`int`, so no `True` is persisted there; a stored `True` is reachable only on the
assign arm (**derived from the branch, not executed**), and `True + 5` is `6`.
Exactly one leaf moves on success: `/maps/0/items/<key>/6/xp`. The
third-argument level rule was established as **display-only** by execution —
`[772,5]` and `[772,5,9]` give an identical `attr_after`, leaf set, and
whole-state sha256, with only the printed lines differing — and is **recorded, not
implemented**. All seven stored resources were byte-identical across all twelve
transactions, **non-tautologically**, since the printed lines differ between arms.

**A false delivered claim was found and corrected rather than inherited.** The
prior record asserted unit XP was unreachable because the corpus carries
`attr["xp"]` on **0 of 40** placed rows and contains no unit row. That is true of
`tests/saves/fresh-player.json` and **false of the repository**: **171 of 12,954**
placed rows across **5 of the 31** committed save documents carry it, every one a
committed unit row. Separately, `units[].xp` was **refuted** as the award source by
three recomputed measurements, and the pid must be read from `playerInfo.pid`,
never from a filename stem (**3 of 8** village saves disagree; `initial.json` has
`null`).

Claim limits: **no XP award is paid and no stored resource moves**; **no award
schedule is derived**, because the amount is client-supplied and unvalidated —
this is the refusal the whole line exists to preserve; **no readiness, threshold,
unit level, or schedule** is implemented; the third-argument rule is **recorded,
not implemented**; **the client's role in the round trip is undelivered** and the
fixture **does not license a route**; parity covers **one recorded transaction per
case against a single village corpus**, with no progressed-player save available;
coverage is **1 of 429** committed units; **no pixel parity** and **no windowed
capture**, because nothing is rendered. **This line also found the second
byte-count guard defect in this project** (PR #280): the fixture integrity test
compared `stat().st_size` against a recorded byte count, which passes on an LF
checkout and fails on a CRLF one. It was **fixed, not re-run** — the guard now
counts LF-normalized bytes — and was proven by injection in three directions and
re-proven on a **fresh CRLF checkout of `main`** (pristine blob fails, fixed file
passes, full suite `Ran 2187 tests … OK`). A measurement scoped the defect class:
this was the **only** instance in the repository; every prior fixture verifies by
**sha256**, which is line-ending invariant. No Flash, Ruffle, ActionScript, or
browser executes in any of these commands, and every network call is loopback.

Verified mission-vocabulary commands (milestone M10 line 1; Godot 4.7.2.stable,
Windows x64; `python` denotes the pinned interpreter, never the PATH alias). This
is **M10's first deliver line**, and the first since M9 that is neither a refusal
nor a transaction: the contract is committed in `docs/legacy-m10-missions.md`
(PR #283, merged `e4fc5e2`), which measured that mission *state* is already
delivered by `godot-quests` (`collect_mission`, `command.py:430-442`, the only
mission-mutating command in the server) and that the **only undelivered surface
is vocabulary**:

```bash
godot --headless --path apps/client-godot --script res://tests/test_mission_vocabulary.gd
godot --headless --path apps/client-godot --script res://tests/test_mission_vocabulary.gd -- --report=<repo>/apps/client-godot/evidence/mission-vocabulary/report.json
godot --headless --path apps/client-godot --script res://tests/test_project_scope.gd
godot --headless --path apps/client-godot --script res://tests/test_content_registry.gd
godot --headless --path apps/client-godot --script res://tests/test_game_api_fake.gd
godot --headless --path apps/client-godot --script res://tests/test_scene_build.gd
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
openspec validate --all --strict
```

Purposes and observed results (2026-10-05): the hermetic mission-vocabulary
suite (observed **208 checks**, **211** with `--report`; the **41st** hermetic
suite) over a typed read-only `Entry`/`Vocabulary` projection of the **64**
committed `MISSION_*` declarations at `constants.py:984-1047`; the scope suite
(**1,832**, was 1,798); the **unchanged** sibling suites (content registry
**87**, fake GameApi **1,322**, scene build **36**, quests **1,223**, tutorial
**639** — all PASS, all unchanged, because this line adds **no endpoint** and
**no registry entry** and touches `apps/compat-api/**` not at all);
`verify.ps1` (exit `0`, `PASS all checks succeeded`); `verify-boot.ps1` (exit `0`, `PASS all checks succeeded`; **41** hermetic suites (was 40), **20** live phases (unchanged), guard digest `6978b959…ff348` **identical before and after**, and **682** log files inspected carrying zero `[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines); the **unchanged**
compat suite (`Ran 2187 tests in 63.502s` then `OK`, exit `0` — unchanged at the 2,187 baseline); the content validator (exit `0`, `result: valid` — 22 outputs, 21 schemas, 604 references); the
preservation manifest (3,258 entries, 758423699 bytes, exit `0`); and `openspec validate --all --strict`
(**62 passed, 0 failed** (62 items)). Evidence is the deterministic `mission-vocabulary-report-v1`
report under `apps/client-godot/evidence/mission-vocabulary/` (digest
**`1aeee8d2…b6f4b`**, **13,850** bytes in LF form, byte-identical across
**four** consecutive runs). `git status` showed no content-package, fixture,
save, config, village, conversion-package, registry-manifest, or legacy-source
byte changed.

**The finding is that the vocabulary exists and nothing ever read it.** A first
classifier reported three consumers at `constants.py:997`, `:998`, and `:1012`,
and **all three are substring artifacts** — `MISSION_DESTROYED` prefixes
`MISSION_DESTROYED_SUBCATFUNC` and `MISSION_DESTROYED_ID`, and
`MISSION_COMPLETE_QUEST` prefixes `MISSION_COMPLETE_QUEST_IN_MAP`. The suite
re-measures the absence **every run** across the **ten** other legacy modules and
requires **zero** `MISSION_` occurrences, so the claim is a measurement rather
than an inherited assertion, and it fails if an artifact is ever miscounted as a
consumer. The vocabulary is nevertheless **why this line precedes the combat
lines**: it is the only surviving statement of what they must resolve, and it
resolves none of it, naming `MISSION_ATTACK_PLAYER` (37), `MISSION_ATTACK_FRIEND`
(38), `MISSION_ASSAULTS_WON` (46), `MISSION_KILLED_ENEMY` (67),
`MISSION_DEFEAT_ALL_TROLLS` (30), `MISSION_SACRIFICE_UNIT` (63), and others.

**Design D1 was a decision, not an omission: the vocabulary is NOT normalized
into the content package.** Every `packages/game-content/normalized/globals.json`
entry records `source_file: "config/main.json"`, because that package describes
content the server *serves*; this vocabulary is dead source in a module the
server never serves. Verified before deciding: **no** legacy `constants.py`
vocabulary (e.g. `CAT_ENERGY` / `TOKEN_ENERGY` / `COST_ENERGY`) is normalized
today either. Normalization is recorded as a deferred alternative. Because D1
leaves a duplicated table, **design D2** makes the suite prove byte-faithfulness
instead: it re-derives the declarations from `constants.py` **as bytes** and
requires name, value, and declared line to match for all **64** entries plus
entry-count and gap-set equality in both directions — stronger than a
normalization pass for the failure mode that matters, a mistranscribed value.

**All three structural guards were proven by injection rather than trusted, and
all eight injections were detected**, each followed by a byte-identical restore:
an invented dispatch helper `resolve_type` (**5** failures); a helper named after
a mission type `mission_killed_enemy` (**5**); a suffixed absent helper
`damage_for`, caught by the **substring** check (**5**); a mission-state
reference `"timestampLastChapter"` (**4**); a colliding mistranscribed value
(**3**); a clean mistranscribed value (**3**); a mistranscribed name (**2**); and
a removed entry (**3**).

**Three defects in this line's own work were found and fixed by measurement, not
by luck.** (1) The projection **silently dropped entries**: the ordering pass
scanned `range(first, last)` using the *last entry in file order* as its upper
bound, so mistranscribing one value above the committed range shrank the
projection from **64** entries to **63** and surfaced as an entry-count mismatch
rather than as the value mismatch it was. The min/max fix was then **refused by
the suite's own guard**, because it added exactly two comparisons over a
committed value; the final fix sorts the value keys, keeping the "no comparison
of one committed value against another" claim literally true and making the
projection independent of storage order, with a regression check. (2) The by-name
guard was **case-sensitive**, so `mission_killed_enemy` would have slipped past
it; it was strengthened only after measuring that the module is clean
case-insensitively and that a lower-cased probe is caught by a folded comparison
but not by the exact-case one. (3) A **deliberate refusal test failed the
battery**: `JSON.parse_string` emits an engine `ERROR:` line for malformed input
and `verify-boot.ps1` treats any `^ERROR:` as a script error, so a document that
does not begin with `{` is now refused *before* the parser is invoked, with the
identical verdict and no engine error — coverage kept rather than dropped.

Claim limits: **the vocabulary only** — **64** committed names, values, and
provenance lines, with **nothing derived**; **zero consumers is a statement about
the preserved server** and says nothing about what the Flash client did with
these names, and no mission type is dispatched, triggered, resolved, or
displayed; **no combat, damage, death, mission completion, or reward** is
implemented, and this line deliberately starts none; the numbering gaps
`[9, 10, 20, 57]` are **reported and never closed**, with nothing synthesised to
fill one; the two overlapping declarations (`destroyed_family` 15/16/17,
`complete_quest_pair` 31/47) are reported **`resolved: false`** with no preferred
member and **no grouping rule**, which would be an invention; the three committed
globals (`NUM_ACTIVE_MISSIONS` 5, `PERMISSION_PACK_UNITS` `[10, 20, 30, 40]`,
`PERMISSION_COSTS` `{10, 20, 30, 40}`) are read **through the existing
normalized registry** and never transcribed here, and **no cap, limit, or price
is derived** — `NUM_ACTIVE_MISSIONS` is specifically **not** turned into an
active-mission bound; **mission state is owned by `godot-quests`**, so this
capability may not reference a mission-state field anywhere except the one
literal declaring it foreign, and the suite verifies the owner really does
project all **five** fields, making the boundary a hand-off and not an orphan;
the cost of D1 is a duplicated table, which the byte-faithfulness guard pays for;
the declaration count and gap set are **re-derived every run**, so a legacy edit
fails the suite rather than silently contradicting it; **no windowed capture and
no pixel-parity oracle** are claimed, because nothing is rendered. No Flash,
Ruffle, ActionScript, or browser executes in any of these commands, and **no
network is used at all**.

Verified darts and premium commands (milestone M11 line 2; Godot 4.7.2.stable,
Windows x64; `python` denotes the pinned interpreter, never the PATH alias). This
is the first M11 line that **derives a value**: `buy_premium_account` is the first
server-derived value the project has derived from a committed schedule rather
than refused. The contract is committed in `docs/legacy-m11-darts.md` (PR #315,
merged `7964523`), whose **§0b corrections C3/C4** this line is bound by; the
proposal is PR #316, merged `7340c33`.

```bash
godot --headless --path apps/client-godot --script res://tests/test_darts.gd
godot --headless --path apps/client-godot --script res://tests/test_darts.gd -- --report=<repo>/apps/client-godot/evidence/darts/report.json
godot --headless --path apps/client-godot --script res://tests/test_social_state.gd
godot --headless --path apps/client-godot --script res://tests/test_project_scope.gd
python -B -m unittest discover -s apps/compat-api/tests -p "test_darts_envelope.py" -v
python -B -m unittest discover -s apps/compat-api/tests -p "test_darts_endpoint.py" -v
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
openspec validate --all --strict
```

Purposes and observed results (2026-10-06): the hermetic darts suite (observed
**610 checks**, exit 0; the 46th registered hermetic suite) over four delivered
read-only modules — `darts_state.gd`, `premium_purchase.gd`, `week_reset.gd`,
`darts_transitions.gd` — re-deriving its corpus figures from the committed
documents every run; the **amended** social-state suite (**405 checks**); the
**amended** scope suite (**2053 checks**, was 1832) after adding the four new
client sources, the new suite, and the new report to its allow-list; the darts
envelope suite (**82 tests**); the darts endpoint suite (**73 tests**); the
**grown** compat suite (observed **`Ran 3077 tests … OK`**, exit 0 — **+156** over
the 2921 baseline, because this line adds a state-mutating route); `verify.ps1`
(exit 0, `PASS all checks succeeded`); `verify-boot.ps1` (exit 0, `PASS all checks
succeeded`, **46 hermetic suites and 23 live phases**, guard digest
`6978b959…ff348` **identical before and after**, and **976** log files inspected
carrying zero `[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines); the content
validator (exit 0, `result: valid` — 22 outputs, 21 schemas, 604 references); the
preservation manifest (3,258 entries, 758,423,699 bytes, exit 0); and
`openspec validate --all --strict` (**67 passed / 0 failed**). Evidence is the
deterministic `darts-report-v1` report under `apps/client-godot/evidence/darts/`
(digest **`e4859928…2a044`**, 28,484 bytes, byte-identical across **three**
consecutive runs). `apps/client-godot/evidence/boot/boot-report.json` was
**regenerated** and differs only in its `generated_utc`, its `git_commit`, the one
added `test_darts` entry, and the log-index renumbering that follows — leaving it
stale would have broken the battery's claim that rerunning reproduces its bytes.

**The finding: a committed price with zero consumers.** The committed
`PREMIUM_ACCOUNTS` schedule carries an amount beside every duration and that
amount has **zero** consumers across all eleven legacy modules —
`get_premium_days` returns the committed *duration* and never reads the amount
beside it (`get_game_config.py:181-189`). So **no price is charged** and every one
of the seven stored resource slots must be byte-identical. This is deliberately
**not** the same mechanism as `research_buy_step_cash`, where the server
*discards* a client-sent price; here it *ignores* a committed one. And "nothing is
charged" is a **refusal, not parity**: `engine.apply_resources`
(`engine.py:251-271`) applies a **client-sent** vector *before* the `if cmd ==`
chain opens at `command.py:42`, and it unpacks **eight** slots (slot 0 read into
`unknown` and never written; **seven** real write targets, each
`max(current + delta, 0)`), so a legacy client could pair a debit with this
purchase. The derived neutral vector forecloses that here, with no claim about
what the Flash client did. **No executed-legacy fixture exists**, because
`tests/saves/fresh-player.json` carries every darts field at its seeded value
(shot list `[]`, `dartsGotExtra` False, all three instants `0`), so the shot arm
and the extend arm have no committed coverage in either direction — which is also
what makes the client-dictated `won_extra` refusal have **no corpus evidence at
all** (correction C4: `dartsGotExtra` is `false` in **33 of 33** committed
documents).

**Two invariants were invented and refused, each with a corpus fact behind it.**
The shot list is **unbounded** and the shot index is **never** tested against the
committed `darts_items` schedule, because `villages/Nerri.json` records shot
index `0`, which is absent from the committed `1..27` ids — a membership test
would contradict the corpus rather than reproduce the branch. The shot index is
delivered as client-sent intent with nothing derived and nothing bounded (design
D10, Reading B); the response reports `shot_list_length_bound: null` and
`schedule_membership_tested: false` as **source spellings without quotes**, while
the JSON response spells them quoted.

**A cross-line consequence was found and fixed at the source, not patched over.**
Adding `/v0/darts` broke **eight** guards owned by four earlier delivered lines,
and the cause is a delivered invariant rather than eight coincidences: every
family slices a route's source from its `def` to *some* end marker, and two
suites reach **forward across every route declared between them**
(`test_research_endpoint` cuts at `@app.post("/v0/level_up")`), while four suites
assert `markers[-1] == '@app.post("/v0/level_up")'`. Two placements were tried
and rejected — after the level route, and between research and level_up — before
the darts route was declared **second**, immediately after the tutorial route,
which is the only slot no span reaches. The four `markers[-1]` invariants are
therefore **untouched**, and the placement is now a **pinned property** rather
than an accident: `test_tutorial_endpoint.RoutePlacementTests` gained `darts` in
its names tuple and a new test asserting both the route's own single-function
slice and its absence from both forward-reaching spans. **That guard was proven by
injection, not trusted**: moving the route into the forbidden research→level_up
slot produced **four independent detections** — the new test (twice), the
delivered `test_the_two_most_fragile_delivered_spans_still_parse`, and 13
research-suite errors — with a byte-identical restore (`5926d87b…5c1de`).

**Two of my own measured figures were wrong in the endpoint suite, and both are
recorded rather than quietly fixed.** A reset writes **six** fields but the
changed set reports **four**, because the committed corpus already carries an
empty shot list and a cleared extra flag; and a shot writes **three** but reports
**two**, because `dartsHasFree` is already `false`. A third expectation — that a
70-bit integer seed would be refused — was wrong in the other direction: Python
integers are unbounded and the preserved branch stores whatever it is sent, so it
is a legal intent, and refusing it would be exactly the kind of range rule this
line refuses to invent. The suite now asserts the **values** plus a companion
test that makes each flag genuinely move, so the smaller changed sets are proved
to be the corpus's starting value rather than a narrower observation.

**One deviation was recorded and one narrowing was decided.** The unreadable
premium instant refuses **all four** actions, not just the premium one, because
the response reports `instant_before`/`instant_after` for every action; that is
asserted explicitly so it cannot read as an accident. And **no `darts-live` phase
is delivered** — a live phase would first have to deliver a client darts
transport (intent builder, typed result, `GameApi` forwarder, fake
implementation), none of which is in this change's requirements, and a client able
to fire `darts_shoot_balloon` is precisely the client surface this line exists to
refuse. `godot-social-state` set the precedent of a state-mutating endpoint with
no live phase; live phases stay at **23**.

Claim limits: **no price is charged and no stored resource moves**; **no
premium entitlement is granted by the delivered client** — the duration is
derived and reported, and the server derives it again, and nothing here decides
whether a player may act on it; **the extend arm has no corpus coverage**, as no
committed document records a future instant; **the week reset delivers no
mutation and no route at all**, because `engine.reset_stuff` writes the instant
to **zero** rather than to the server clock, and that offset's own comment says it
exists because timestamp zero is a Thursday and the reset should land on Monday —
reported **as a comment**, deriving no weekday rule; **no shot is ever bounded,
validated against the schedule, or resolved for a win**; **the client-dictated
`won_extra` refusal is a divergence from the preserved branch, not parity**;
parity is not claimed for any arm the corpus cannot exercise; **no windowed
capture** and **no pixel-parity oracle** are claimed, because nothing is
rendered; and absence of a token is not absence of a feature — the Flash client
may have held darts and premium UI entirely client-side, which this oracle cannot
verify. The four recorded flaky surfaces remain open: `test_no_server_is_running`
port assertions (5055/5056), `verify-boot.ps1` treating any `^ERROR:` as a script
error (grep `SCRIPT ERROR` too), the display-sensitive `verify.ps1`, and the
`test_base.gd` abort-as-pass defect. No Flash, Ruffle, ActionScript, or browser
executes in any of these commands, and every network call is loopback.

Verified friends-roster commands (milestone M11 line 3; Godot 4.7.2.stable, Windows
x64; `python` denotes the pinned interpreter, never the PATH alias). M11's deliver
list is `friends`, `visits`, `scores`, `social rewards`, `legacy event systems`,
and `special mechanics`; this is its **third** line, and the **first in this
project that adds no route and touches no Compatibility API file at all**. The
binding investigation is `docs/legacy-m11-friends.md` (PR #321, merge `3df888a`,
content `82b6df9`); the proposal is `friends-roster-projection` (PR #322, merge
`f7cc36b`). **The deliver item's name turned out to be the opposite of what the
preserved server has**, which is why the line delivers a *roster* and refuses the
relationship vocabulary:

```bash
godot --headless --path apps/client-godot --script res://tests/test_friends.gd
godot --headless --path apps/client-godot --script res://tests/test_friends.gd -- --report=<repo>/apps/client-godot/evidence/friends/report.json
godot --headless --path apps/client-godot --script res://tests/test_social_state.gd
godot --headless --path apps/client-godot --script res://tests/test_project_scope.gd
python -B -m unittest discover -s apps/compat-api/tests -p "test_*.py" -v
powershell -File apps/client-godot/verify.ps1
powershell -File apps/client-godot/verify-boot.ps1
python -B packages/game-content/tools/validate_content.py
python -B tools/hash-manifest/hash_manifest.py verify
openspec validate --all --strict
```

Purposes and observed results (2026-10-07): the hermetic friends suite
(observed **570 checks** PASS, exit 0; the **47th** registered hermetic suite)
over a pure read-only projection of each roster entry as **12 carried
`playerInfo` keys** plus **6 fields derived from `maps[0]`**, kept distinguishable
per key; the **unchanged** sibling suites (`test_social_state` **405**,
`test_project_scope` **2087** — was 2053, the allow-list grew by exactly three
paths — `test_content_registry` **87**, `test_game_api_fake` **1322**,
`test_scene_build` **36**, `test_darts` **610**); the **unchanged** compat suite
(observed `Ran 3077 tests in 52.428s`, **OK**, exit 0 — a *verified* baseline,
because this line adds no endpoint and touches `apps/compat-api/**` not at all);
`verify.ps1` (exit 0, `PASS all checks succeeded`); `verify-boot.ps1` (exit 0,
`PASS all checks succeeded`, **47 hermetic suites** was 46, **23 live phases
UNCHANGED** because no live phase was delivered, **224 assertions** was 222,
guard digest `6978b959…ff348` **identical before and after**, port 5056 released,
no working-tree `saves/`, and **988** log files inspected carrying **zero**
`[test] FAIL`, `^ERROR:`, or `SCRIPT ERROR` lines); `validate_content.py` (exit
0, `result: valid` — 22 outputs, 21 schemas, 604 references); `hash_manifest.py
verify` (**3,258 entries**, 758,423,699 bytes, exit 0); and
`openspec validate --all --strict` (**68 passed / 0 failed**). Evidence is the
deterministic `friends-report-v1` report under
`apps/client-godot/evidence/friends/` (**29,220 bytes in LF form** — the
committed Git blob form; sha256 `6318c9b5…81f4` taken over those bytes, and
byte-identical across **three** consecutive runs).
`apps/client-godot/evidence/boot/boot-report.json` was **regenerated** and its
diff **inspected rather than assumed**: it contained only `generated_utc`, the
advanced `git_commit` (`5240bb6` → `f7cc36b`, the proposal merge), the one added
`test_friends` entry, and the **25** log-index renumberings that follow from
inserting one command — every one of them confirmed to be the `log` field and
nothing else, because a rename and a content change are easy to confuse in a
51-insertion diff.

**The finding: `friends` is a directory listing, not a social relationship.**
`neighbors()` (`sessions.py:191-221`) returns **every other loaded village,
unconditionally** — no add, no remove, no accept, no decline, no consent, no
direction anywhere in the preserved source. Membership therefore derives from
**code, never from a file count**: `every villages/*.json except initial.json`
(skipped at `sessions.py:78`) gives 7 loaded villages, minus the two-pid literal
pair gives **5** members. Both pids ship as a **literal** because
`sessions.py:173-174` and `:196-197` hardcode them as string literals and
nothing in `config/` or the normalized content package names them, so there is
nothing to derive them *from*; deriving the exclusion from content is recorded as
the **rejected alternative**, because a derivation from a file count is an
invention that happens to agree with the corpus today. **The committed
classification of `friends` was falsified before this line was proposed** —
`docs/legacy-m11-social.md` §7 called it *zero legacy occurrences*, and re-counted
over all eleven modules under six rules it has **5** whole-file and **4** code-only
occurrences, all four code-only ones in `sessions.py`. That is why
`godot-social-state`'s requirement 1 was **amended as an ownership hand-off**
rather than left standing: its premise was measured false. The hand-off moves
**zero** state fields, because a roster entry is not private state.

**Three false attractions were recorded rather than followed**, each of which would
have produced an invented rule: **`neighbors` has two meanings** (the bootstrap
roster, and the `expansion_prices` requirement string at `boot_data.gd:607`);
**`"100000"` is a routing prefix, not an identity test** (the visit dispatch's
branch 3 is `user.startswith(100000)`, and no claim is made that the prefix
identifies a quest map); and **`pic_square` is a dictionary key**, not a Facebook
API call. The two roster channels are reported **side by side and not
deduplicated** — **2** entry fields per roster from the Flash-embed-variable
channel against **18** from v0 — because deduplicating near-duplicates would hide
the disagreement that is the interesting fact; the FlashVar channel's four tokens
(`friendsInfo`, `pic_square`, `fb_friends_str`, `uid`) measured **zero** across
all **48** non-test compat service modules, while the bare word `FlashVar`
measured **9** occurrences and is **pinned as a capture-tool-only** exception
rather than silently folded in (`capture_legacy_fixtures.py` 1,
`field_stability.py` 8 — both analysis tools, neither on the request path). The
visit surface is recorded as a **divergence and delivered as nothing**: branch 2
tests membership in the literal pair and then passes `100000030` for **both**, so
requesting `100000031` returns `100000030`'s data; its failure mode is the **empty
string with HTTP 200**; and a visit returns the visited player's **complete
`privateState`**. No committed fixture exercises it.

**A tautology was found and closed rather than shipped.** The privateState
intersection reads each entry's **real** key names through a new
`all_key_names()` rather than against the projection's own declared 18 — because
a widened key table is exactly the edit the guard exists to catch, so checking
against the declaration would have made the empty intersection true by
construction. The measurement is real: the recording player's `privateState` has
**47** keys (an earlier eyeball count of "50" was wrong; the measured figure is
47) and the intersection is empty.

**Seven injections, all detected, all byte-identically restored, and re-run
against the final delivered state** because a later edit can silently restore a
guard's coverage. Failure counts **3, 3, 4, 3, 3, 34, 1**; every probe exit 1.
The whole-inventory pin is the real gate and the reserved-name guard is the belt,
and the belt earned its place: probes 2 and 4 were **suffixed** helpers wearing a
reserved name as a **prefix** (`roster_order_by_xp`, `assist_neighbor_reward`),
which an exact-name check would have passed. Two pinned facts were corrected
rather than tidied: the module declares **29 distinct function names across 34
declarations**, so the inventory is compared as a **sorted-unique set** with the
declaration count pinned separately — a positional list comparison fails against
the delivered module itself, because `_init`, `carried_key_names`,
`derived_key_names`, `entry_key_names` and `entry_key_count` are each declared
**twice**; and the reserved name `select_entry` was **renamed**
`select_from_roster`, because a bidirectional substring rule collided with the
delivered accessor `entry`. Probe 6 produced a **34-failure cascade** instead of a
tidy single failure, because emptying the roster costs thirty-three other checks;
its own line is the **seventh** of the thirty-four, confirmed from a **full**
failure listing because the harness's three-line sample would not have shown it.
The module digest after all seven probes equalled the digest before the first:
`ed4d88a8…b9dd`, 32,470 bytes, with zero NUL bytes and a final newline asserted
on every restore, a loud abort when a probe's anchor text is absent, and
`git diff --numstat --ignore-cr-at-eol` plus `git status --short` required to
equal their pre-probe values (design D7's three measured harness defects).

**Two literal tokens had to be reworded rather than relaxed.** Both no-Flash gates
are **raw substring** scans over project sources, and `USERID` + the Flash
variable name are in `test_project_scope.gd`'s `FORBIDDEN` table while the Flash
variable name is also in `test_town_gate.gd`'s `RUNTIME_NEEDLES`. The module's
prose therefore **describes** the transport and cites `templates/play.html:99` and
`server.py:91` instead of quoting it, with the reason recorded at the site — and
the suite's own boundary token list drops the two forbidden literals for the same
reason, moving that claim onto the four **non-forbidden** roster tokens. Neither
gate was relaxed to permit a quote. **The first `verify-boot.ps1` run of this line
failed on exactly this**, and the failure is recorded rather than hidden.

Claim limits: **no relationship, request, accept, decline, consent or lifecycle
exists** and the delivered client cannot create one; **no order, rank, score,
best, closest or total** is computed over roster values, because the served order
follows `os.listdir()` and is already recorded as environment-dependent, so
membership, entry count, carried key set and derived values are covered and
**order is not**; **the saves-loop half of both channels has no executed
evidence**, because the committed captures ran with no `saves/` directory, so the
recorded roster is static-villages-only and that limit is **asserted, not noted**;
**no assist reward** is derived (`neighborAssists`, `receivedAssists` and
`resourcesTraded` have zero code-only occurrences); **no windowed capture and no
pixel-parity oracle**, because nothing is rendered; and **absence of a server-side
relationship says nothing about what the Flash client displayed**, which may have
been entirely client-side. **An eighth recorded flaky surface was found and
recorded, not fixed**: `test_collect_endpoint`'s
`test_a_recent_instant_is_too_early` has a **sub-second** time budget, because it
stubs the row instant to `BOOT.server_time() - 299` against the **live** clock
while the `too_early` refusal is decided against the endpoint's **own** live clock,
so one second of build-up flips `409` to `200`. It failed once, inside
`verify-boot.ps1` immediately after 47 headless suites; the file then passed
**five consecutive times** alone and the full discovery passed at 3077. It is
pre-existing and unrelated — established by `git diff --name-only` returning no
`apps/compat-api/**` path — and the honest fix belongs to `godot-building-collect`.
The other seven recorded flaky surfaces remain open. No Flash, Ruffle,
ActionScript, or browser executes in any of these commands, and **no network is
used at all**.

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
