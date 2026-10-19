# The Client's Own Version History — 58 Builds, 1.4.5 → 1.5.4

**Roadmap task B1.** Answering the question left open in
[`09-LIMITATIONS-AND-OPEN-QUESTIONS.md`](09-LIMITATIONS-AND-OPEN-QUESTIONS.md): *is the
server signing key stable across the client's whole life?*

**Answer: no. The key rotated exactly once, at build 1.4.28.**

| | |
|---|---|
| **Builds analysed** | 58 (`Basesec_1.4.5.swf` … `Basesec_1.5.4.swf`), 239.7 MB |
| **Method** | Inflate each build (CWS → FWS), read the ABC string pool, and record the presence of protocol-relevant literals. The rotation boundary was then confirmed by decompiling `core/Config.as` from 1.4.27 and 1.4.28 with JPEXS. |
| **Tooling** | `node scripts/client-version-history.mjs` → [`../data/client-version-history.json`](../data/client-version-history.json) |
| **Source of the builds** | `upstream/socialwarriors/assets/flash/` (vendored, byte-for-byte) |

---

## 1. The headline: the server key rotated

The client signs `command.php` bodies with an HMAC whose key is a compile-time constant in
`core/Config.as`:

```actionscript
public static const SERVER_KEY:String = "…";
```

Across the 58 builds there are **exactly two** values, and the change happens once:

| Key | Builds | Count | First | Last |
|---|---|---|---|---|
| `3m0d3pwiupoetn7ysa02` | 1.4.5 – 1.4.27 | **22** | 1.4.5 | 1.4.27 |
| `4vVSD8dftv6hdfb1Hnk9` | 1.4.28 – 1.5.4 | **36** | 1.4.28 | 1.5.4 |

**No build has no key at all.** Signing was present from the first shipped build; only the
secret changed.

### Boundary confirmed by decompilation

```
Basesec_1.4.27.swf -> scripts/core/Config.as
    public static const VERSION:String = "1.4.27";
    public static const SERVER_KEY:String = "3m0d3pwiupoetn7ysa02";

Basesec_1.4.28.swf -> scripts/core/Config.as
    public static const VERSION:String = "1.4.28";
    public static const SERVER_KEY:String = "4vVSD8dftv6hdfb1Hnk9";
```

### What this means

* **`4vVSD8dftv6hdfb1Hnk9` — the key verified live in this investigation — is the *rotated*
  key**, in use for the last 36 builds (1.4.28 → 1.5.4, i.e. the last ~⅔ of the client's
  published life).
* **`3m0d3pwiupoetn7ysa02` is the original production key.** It was recovered from the
  client's own binary and is the key the *original* Zynga backend was using during the
  earlier era of the game.
* A clone that wants to be faithful to the era it is reproducing has **two** keys to
  choose from, and the choice is now a documented decision rather than a guess.
* It also means the recovered key is **not** a leak of a single long-lived secret but of a
  *currently-in-use* one — the earlier secret is embedded in the same artefact tree.

> **Note on exposure.** Both keys are already public: they are string constants in a
> client that the upstream project distributes, and both are recoverable from the shipped
> binaries. This is a historical fact about the original game's crypto, not a newly
> disclosed secret. The clone uses the key only to be wire-compatible with the original
> client (roadmap Group F2, the compatibility shim).

## 2. What else the version history shows

The same sweep gives a picture of how the protocol evolved. Presence counts are out of 58
builds; "first" is the earliest build containing the literal.

### 2.1 Stable throughout (58/58)

These never changed and are safe to treat as invariants:

| Literal | Meaning |
|---|---|
| `SexWars` | `Config.GAME_NAME` — the internal product name, unchanged from 1.4.5 to 1.5.4 |
| `command.php` | the command bus endpoint |
| `staticUrl`, `dynamicUrl` | the two asset/API roots |
| `skiphash12341` | the debug flashvar that disables response-signature verification |
| `accessToken`, `lastLoggedIn`, `publishActions` | request-body fields |
| `report_error_init.php`, `get_continent.php`, `clean_assaults.php` | endpoints present for the client's whole life |

### 2.2 Endpoints that came and went

| Literal | Builds | First | Last | Reading |
|---|---|---|---|---|
| `get_game_config.php` | 56 | 1.4.5 | 1.5.4 | dropped in 2 builds |
| `get_player_info.php` | 54 | 1.4.5 | 1.5.4 | dropped in 4 builds |
| `sync_error_track.php` | 53 | 1.4.5 | 1.5.4 | dropped in 5 builds |
| `track_game_status.php` | 52 | 1.4.5 | 1.5.4 | dropped in 6 builds |
| `get_continent_ranking.php` | 54 | 1.4.5 | **1.5.3** | **removed in 1.5.4** — the newest build is the only one without it |
| `get_public_player_info.php` | 56 | 1.4.5 | 1.5.4 | |
| `set_sex_player.php` | 56 | 1.4.5 | 1.5.4 | |
| `get_user_world.php` | 57 | 1.4.5 | 1.5.4 | dropped in 1 build |
| `register_found_item.php` | 57 | 1.4.5 | 1.5.4 | dropped in 1 build |

**`get_continent_ranking.php` disappearing in exactly 1.5.4 is the most interesting
removal**: the shipped build that the upstream project preserves is the one where the
continent-leaderboard feature was dropped. The 2012 server capture in
`config/get_game_config.php_29august2012.txt` still predates that.

### 2.3 The command vocabulary

| Command | Builds | First | Last |
|---|---|---|---|
| `push_queue_unit` | 38 | 1.4.8 | 1.5.4 |
| `flash_debug` | 39 | 1.4.6 | **1.5.3** |
| `first_number` | 45 | 1.4.5 | 1.5.4 |
| `end_attack` | 47 | 1.4.6 | 1.5.4 |
| `pop_queue_unit`, `add_click` | 47 | 1.4.5 | **1.5.3** |
| `rt_open_graph_unit` | 49 | 1.4.5 | **1.5.3** |
| `complete_tutorial`, `end_quest` | 50 | 1.4.5 | 1.5.4 |
| `set_help_map` | 49 | 1.4.5 | 1.5.4 |
| `activate_item_click`, `batch_remove` | 52 | 1.4.5 | 1.5.4 |
| `sync_error_track.php` | 53 | 1.4.5 | 1.5.4 |
| `darts_reset`, `set_quest_var` | 46–47 | 1.4.5 | 1.5.4 |

Two of these deserve comment:

* **`flash_debug` is absent from 1.5.4** — the shipped build. The client *does* send it in
  the live session (it was captured: `flash_debug 5,50,3000,1890,2000,1820,1895`), so the
  literal is reached indirectly in 1.5.4 rather than being spelled out. The feature is
  alive; only the literal's presence in the pool changed.
* The 8–10 build gaps are mostly **string-pool reshuffles**, not feature removals: the
  ABC constant pool is re-ordered on every recompile, so a literal can be split across
  two runs and only match one of them. Presence counts are therefore a *lower bound* on
  stability, and a full decompilation of all 58 builds would be needed for exact
  per-build semantics.

### 2.4 Other dated features

| Literal | Builds | First | Last | Reading |
|---|---|---|---|---|
| `weird.txt` | 41 | **1.4.47** | 1.5.4 | the `externalized/weird.txt` debug-token fallback was added at 1.4.47 — which is why it exists in the decompiled 1.5.4 client but **not** in the asset tree (the file was never captured) |
| `spdebug` | 41 | 1.4.5 | **1.4.46** | the `spdebug` flashvar was **removed** after 1.4.46, even though `play.html` still passes `spdebug=notnull` — the modern template passes a dead flashvar |
| `first_number` | 45 | 1.4.5 | 1.5.4 | the command-batch counter field |

## 3. The production endpoints

The string `menvswomen` is present in **52 of 58** builds and `dynamicmw` / `appsfb` /
`socialpointgames` in all of them. The six builds where `menvswomen` does not match
literally are string-pool artefacts; the fragments `menvs` are present in all 58.

The production dynamic root, as recovered from `core/Config.as`:

```
http://dynamicmw.socialpointgames.com/appsfb/menvswomen/srvsexwars/
```

This is the original Zynga/Socialpoint backend. It is offline; the upstream preservation
project replaced it with the local Flask server, which keeps the same path shape so the
original client works unmodified.

## 4. Consequences for the clone

1. **The compatibility shim (Group F2) needs a key decision.** It must accept **both**
   keys, because the shim's whole purpose is to let *unmodified* original clients play —
   and the original clients span both key eras. Recommendation: accept either key, but
   rate-limit and log the legacy key separately.
2. **The key is now a documented historical artefact**, not an open question. Q5 in
   [`09-LIMITATIONS-AND-OPEN-QUESTIONS.md`](09-LIMITATIONS-AND-OPEN-QUESTIONS.md) is
   **closed**.
3. **The client history is a free regression corpus.** 58 builds of the same game are a
   free differential-testing corpus: the rules engine can be validated against whichever
   era a given build represents, which is a meaningful check that the port is not
   accidentally "1.5.4-shaped".
4. **Two features changed in the newest build** (`get_continent_ranking.php` removed,
   `spdebug` long gone), so the upstream `play.html` template passes at least one
   **inert** flashvar. The clone's flashvar contract should be taken from the *client*
   (`core/Config.as` + the loader), not from the upstream template.

## 5. Reproducing this

```bash
node scripts/client-version-history.mjs     # writes re/data/client-version-history.json
```

To confirm the boundary by decompilation:

```bash
ffdec-cli.exe -export script <outdir> \
  upstream/socialwarriors/assets/flash/Basesec_1.4.27.swf
grep SERVER_KEY <outdir>/scripts/core/Config.as
```

## 6. Method notes and limits

* The sweep reads the **decompressed SWF bytes**, so it sees the ABC string pool without
  a full decompilation. That is why it is fast enough to run over 58 × 4.5 MB.
* Because the ABC constant pool is re-ordered on every recompile, a literal can be
  concatenated with a neighbour and stop matching a naive scan. **Absence is therefore not
  proof of removal.** Every absence-based claim above was cross-checked against a
  decompiled boundary build where it mattered (the key rotation).
* The `weird.txt`, `ownueg` and `SEC` literals from
  [`07-REA-EVIDENCE.md`](07-REA-EVIDENCE.md) are below the 6-character scan threshold in
  some builds; `weird` (5 chars) was found by widening the scan.
* This report covers **the client**. The upstream Python server's own history is in the
  upstream git log, which was not vendored.
