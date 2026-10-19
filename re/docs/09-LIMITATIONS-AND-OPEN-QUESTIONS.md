# Limitations & Open Questions

An honest register of what this investigation **did not** establish, what it could not
verify, and what remains ambiguous. Read this before relying on any claim in the other
documents.

---

## 1. Tooling limitations

### 1.1 REA cannot analyse SWF

`open_binary` rejects every Flash file with `unsupported binary format`. REA's format
detector has no SWF signature and its `format` enumeration has no SWF member. This is a
hard capability gap, not a configuration issue. Consequence: **no REA-produced
decompilation, control flow, or xref data exists for the game client.** All client
semantics in this report come from JPEXS (FFDec) 26.3.0 output, cross-checked against
source and against live traffic.

### 1.2 The 64 KiB chunking ceiling

REA's Ghidra adapter on Windows accepts only native PE and explicitly-selected **raw
6502** targets. The 6502 address width caps a raw mapping at 64 KiB, so the 2 MB ABC had
to be split into 16+ chunks. Consequences:

* `list_strings` returns **0** for every chunk (Ghidra defines no strings in an untyped
  raw blob) — `search_bytes` was the only usable string primitive.
* `list_procedures` reports 1–4 spurious procedures per chunk (6502 disassembly of byte
  noise). **They are not real code.** They were not used for any conclusion.
* Coverage is **partial**: the byte-pattern sweep in
  [`07-REA-EVIDENCE.md`](07-REA-EVIDENCE.md) §3.2 covers ~25 named protocol strings in
  6 of 32 chunks. It is a *presence* proof, not a *completeness* proof. The full string
  inventory was obtained from the decompiler instead.
* Chunk coverage beyond chunk 5 (the constant pool) is thin. Method-body-local strings
  were not exhaustively searched.

### 1.3 Other unavailable providers

| Provider | Status | Consequence |
|---|---|---|
| Hopper | macOS only | no Hopper disassembly of the Flashy Browser's `Flashy.exe` (92 MB PE) or `pepflashplayer.dll` (31 MB) |
| IDA | not configured | ditto |
| Rizin | `ERR_REA_WINDOWS_NATIVE` | no `izz` whole-file string dump as a cross-check |
| `inspect_binary_layout` | pwntools provider is Linux-x64 only | no ELF/PE section table for the browser binaries |
| `native-macos` tools | macOS only | no Mach-O/signature inspection |

**Consequence:** the 31 MB `pepflashplayer.dll` (the real Adobe Flash Player) and the
92 MB `Flashy.exe` were **not** disassembled. Nothing in this report depends on them; they
are the platform, not the target.

### 1.4 REA's browser-target filter excludes CEF webviews

`list_browser_targets` reported **0 targets** while the game was running, because the
game page's CDP `type` is `webview` (a CEF-specific type) and REA only admits `page`.
`list_javascript_runtime_targets` did see it. If you re-run this against a Chrome-hosted
build, `list_browser_targets` will work; against any CEF host, use the runtime-targets API.

## 2. Analysis limitations

### 2.1 FFDec output is not source code

The decompiled AS3 is occasionally imperfect (FFDec emits invalid syntax in a small number
of places, and `this`-scoping inside nested closures is lossy). Every non-trivial claim in
reports 01–03 was cross-checked against at least one second call site, and the highest-risk
claims (HMAC, resource vector order, command tuple shape) were confirmed against live
traffic. **Line numbers in the decompiled output are not the original source line
numbers** — they are positions in the FFDec output.

### 2.2 The 2012 config cannot describe the 2026 client

* `config/main.json` is byte-identical to the 29-Aug-2012 capture.
* The client contains **123 item ids the config has never heard of** (199, 302, and the
  1307–1431 mech/drone wave) and **722 asset files are unreferenced by the config**.
* 73 config→asset references do not resolve (10 sprites, 29 thumbs, 34 chapter/intro
  images).
* **Which side is authoritative is not settled.** The client is newer; the config is what
  the server ships. A clone needs an explicit policy (see M1 in the roadmap).

### 2.3 The original 2012 server responses could not be reproduced

`config/get_game_config.php_23july2012.txt` and `…_29august2012.txt` are captured
responses from the original Zynga backend. **The recovered `Config.SERVER_KEY` does not
reproduce their signature under any of the 13 candidate constructions tested**, and the
response *hash* scheme used by the original server was never recovered. The upstream
preservation server sidesteps this by serving the config **un-hashed** and relying on the
`skiphash12341` flashvar to disable the client's response verification.

**Open:** what did the original server's response signature look like, and did the July and
August 2012 captures use different keys?

### 2.4 `server_key` may be per-tenant / per-era

`Config.SERVER_KEY` is a compile-time constant in the shipped SWF. It was verified against
the *current* client build. Whether the original production server used the same key in
2012 is unknown. **Treat the recovered key as "the key this build signs with", not "the
original server's key".**

### 2.5 Combat was captured live — but only for quests

The live session reached tutorial step 14, then (after clearing the tutorial flag and the
level-8 PvP gate in the scratch save file) entered **Mission 1**, fought an assault and
finalised it. The **`end_quest`** payload was captured verbatim:

```json
{"difficulty":1,"map":0,"quest_id":"100000001","voluntary_end":1,"win":0,
 "units":[[1007,3,0,0]],"duration":662}
```

This confirms the server's parsing model exactly and closes the largest static-only gap.

**Still not observed live:**

* **`end_attack`** — the PvP battle report. The shape is documented from
  `scripts/commands/CmdEndAttack.as` and is the same family as `end_quest` (both carry
  `victim`/`attacker`, `win`, `voluntary_end`, `units` and `duration`), and the server
  parses them with near-identical code, but the *PvP* variant was not captured. The
  static-village neighbours are visitable but the client-side attack flow was not
  completed inside the session.
* **`attack_player` / `spy_player`** — the commands that *start* a PvP interaction.

**Still derived from static analysis only:**

* The **full** 94-command table in
  [`03-commands-quests-economy.md`](03-commands-quests-economy.md). 17 of the 94 were
  observed live; the other 77 come from the decompiled `Cmd*.as` classes.
* The "32 client commands the server ignores" list — **one of them, `set_help_map`, was
  confirmed live** as a command the client sends and the server drops.

**Next step if this matters:** visit a neighbour island from the town strip, select the
army, attack a building, and re-run the trace capture. The harness already supports it.

### 2.6 The ABC constant-pool parser did not complete

A hand-written AVM2 constant-pool reader was written to locate the string pool, but it
failed at a `CONSTANT` kind `0xff` and was abandoned in favour of the chunk-density
approach plus FFDec. The ABC is **not** encrypted (plaintext `IsoEngine`, `command.php`,
`menvswomen` etc. are all present at known offsets), so this is a parser bug, not a
format mystery. The consequence is that there is **no authoritative per-constant-pool
enumeration of the client** — the class list from FFDec (1 387) stands in for it.

### 2.7 Unreferenced content may still be reachable

722 asset files are unreferenced by the config. The 1307–1431 wave has sprites *and*
client delegates, so it is likely reachable in the client and merely absent from the
2012 config. But **722 includes items whose reachability was not individually proven.**
The asset report marks the resolution rules; it does not claim runtime reachability.

### 2.8 The `_m` / `_w` sprite suffix is not fully explained

Frame export proved that `1007_soldier_1_m` is a bearded male and `_w` a blonde female, and
that only 5 units have both. But **279 other `_m` sprites have no `_w` counterpart**, so
the token cannot mean "male". Its actual meaning is **UNVERIFIED** — most likely a legacy
art-pipeline marker, functionally inert.

### 2.9 `BlockBertholdRegular` does not exist

`SWLoader.as` embeds it via `[Embed(source="sing.ttf", fontName="BlockBertholdRegular", …)]`,
but a byte search of the entire tree for that name returns nothing and there are **zero**
TTF/OTF files in the repository. The loader's font is either missing from the captured
assets or the embed silently falls back. **Open.**

### 2.10 `weird.txt` is absent

`core/Base.as` has a fallback that reads `externalized/weird.txt` and takes the part
before `"SEC"` as a debug token. `assets/externalized/` contains only
`viral_buttons/crossDCi.swf`. **The fallback is dead code** in this capture — but it means
the archival build may be missing a file that the original distribution had.

### 2.11 The `__#__ITEMS_hint` annotation is informal

`villages/Neutral.json` carries a `__#__ITEMS_hint` key that documents the `items` array
layout. It is a hand-written annotation, not a schema the server enforces. The server's
own `is_valid_village()` only checks that `items` is a dict.

## 3. Upstream bugs found (not fixed upstream)

| Bug | Location | Impact |
|---|---|---|
| Duplicate dict keys shadow 3 quest ids | `constants.py` class `Quests` | `100000024/25/26` resolve to `ISLA_RUBEN3D` / `ISLA_KASPAR` / `ISLA_EGG2` instead of `HARDCORE8` / `HARDCORE10` / `HARDCORE9` |
| `PropertyManager.FIGHTING_TYPE_ARMORED = "ft__armored"` | AS3 `core/isoengine/PropertyManager.as` | never matches the config's `ft_armored`; the armoured damage rule is inert |
| `UnitFilters.filterByRangeHealth` upper bound | AS3 `core/generalAttacks/UnitFilters.as` | broken bound in unit filtering |
| `build/build.bat` uses `--add-data "..\..\assets;assets"` | upstream `build/` | resolves outside the repo; the Windows build has not worked since 2022 |
| `requirements.txt` unpinned | upstream root | `flask.debughelpers` was removed in Flask 2.3; `server.py` imports it |
| `mods/no_hiring_needed.json` is commented out | `mods/mods.txt` | the "no hiring needed" mod is not applied; the server logs 0 mods applied |

## 4. Open questions worth answering next

| # | Question | How to answer it |
|---|---|---|
| Q1 | What is the exact `end_attack` (PvP) payload shape? | Visit a neighbour island from the town strip, select the army, attack a building, and capture the trace. `end_quest` is already captured — see §2.5. |
| Q2 | What are the 32 ignored commands' real semantics? | Read the `Cmd*.as` classes (already in report 03) and decide which the clone must implement. `set_help_map` is confirmed live as one of them. |
| Q3 | Which of the 123 client-only item ids should the clone ship? | Diff the client's `items` handling against the config; the 1307–1431 wave is the obvious candidate |
| Q4 | What was the original server's **response** hash scheme? | Recover from a 2012 capture, or from the original PHP if it is ever located |
| Q5 | Is `Config.SERVER_KEY` stable across all shipped `Basesec_1.5.x.swf` builds? | Extract `Config.as` from each of the 59 shipped SWFs and diff — **the diff is cheap and worth doing** |
| Q6 | What are the 34 missing chapter/intro images? | Recover from an older asset dump or the original CDN |
| Q7 | What does `_m` actually mean in the 279 sprite names without a `_w`? | Inspect the original art pipeline or diff against another Socialpoint title |
| Q8 | What is the `alliance/` endpoint contract? | The client sends 11 `alliance/?method=…` variants; the server answers `{}` for all of them. The real contract is in the AS3 `popups/alliances/**` classes |
| Q9 | Does the original server enforce the `data` HMAC on requests? | Almost certainly yes — the client computes it. The upstream server simply does not. The original PHP would settle it |

### Q5 is the cheapest high-value follow-up

There are **58 `Basesec_1.5.x.swf` builds** in `assets/flash/` (1.4.5 → 1.5.4, with
1.4.7 absent), plus `SWLoader.swf` and `Debug_1.5.4.swf` — 60 files in total. Each build
embeds its own `Config.as`. Extracting and diffing them would:

* confirm whether `SERVER_KEY` is constant across the whole build history,
* show the client-side evolution of the protocol (new endpoints, new commands, new globals),
* give a version-by-version changelog of the *client*, which is the actual game history.

That is a mechanical task with the same tooling already in use.

## 5. Confidence legend used across these documents

| Marker | Meaning |
|---|---|
| *(stated in the text as "verified live")* | observed in the captured traffic from the real Flash Player |
| **VERIFIED** | read directly from decompiled code or source, cross-checked at a second call site |
| **UNVERIFIED** | inferred, hypothesised, or dependent on behaviour not observable from the artefacts at hand |

## 6. What would change the conclusions

* A capture of a real battle or quest would replace the last major static-only section.
  **A quest battle has since been captured** (§2.5) — only the PvP `end_attack` variant
  remains static-only.
* The 59-build SWF diff could reveal an earlier protocol dialect (e.g. an older command
  framing) that the current build has migrated away from.
* Finding the original PHP backend would settle the response-hash and alliance questions
  outright.
* A 2012-era asset dump would close the 73 missing-asset references and possibly explain
  `weird.txt` and `sing.ttf`.
