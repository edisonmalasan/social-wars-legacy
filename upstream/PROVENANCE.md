# Vendored Upstream — Provenance

This directory contains an **unmodified copy** of the upstream project that this
repository is re-implementing. It is vendored so that the analysis is reproducible, so
that the original Flash client can be used as a test oracle, and so that the original
Python server can be run side by side with the new one.

> **It is a reference and a test fixture. It is never a runtime dependency of the
> shipped product, and it is never edited.**

---

## 1. Upstream identity

| | |
|---|---|
| **Project** | Social Wars preservation project, by the Social Warriors team |
| **Upstream remote** | `https://github.com/AcidCaos/socialwarriors.git` |
| **Pinned commit** | `c3fceeb1f8e93734a293b9bc25ae6025656f6822` |
| **Commit subject** | `Minimal server support` |
| **Commit date** | 2026-10-01 |
| **Tags at that commit** | `0.01a`, `0.02a` |
| **Licence** | GPL v3 — see `socialwarriors/LICENSE` (verbatim copy) |
| **Client version** | `Basesec_1.5.4.swf` / `Config.VERSION = "1.5.4"` / `Config.GAME_NAME = "SexWars"` |
| **Server version** | `version.version_name = "alpha 0.02"`, `version_code = "0.02a"` |
| **Production origin** | The client targets `http://dynamicmw.socialpointgames.com/appsfb/menvswomen/srvsexwars/` — the original Zynga/Socialpoint backend, now offline |

## 2. What was vendored, and what was not

| | |
|---|---|
| **Vendored** | The complete upstream **working tree** — 3 292 files, 726.5 MB |
| **Not vendored** | The upstream `.git` directory (655.9 MB of VCS history for *their* repository, not project content). Our pin is recorded in this file and in `MANIFEST.json` instead. |
| **Not vendored** | Nothing else. No file was added, removed, renamed or edited inside `socialwarriors/`. |

### Tree breakdown

| Path | Files | Size | Notes |
|---|---|---|---|
| `assets/sprites/` | 862 | 357.2 MB | Per-building / per-unit vector sprites |
| `assets/flash/` | 60 | 244.2 MB | The client itself: 58 `Basesec_1.5.x.swf` builds + `SWLoader.swf` + `Debug_1.5.4.swf` |
| `assets/images/` | 578 | 65.2 MB | Chapters, intro, UI images (localised) |
| `assets/thumbs/` | 1 314 | 31.1 MB | Inventory thumbnails |
| `assets/fx/` | 205 | 9.0 MB | Combat effects |
| `assets/sounds/` | 140 | 5.5 MB | Audio |
| `assets/characters_2/` | 26 | 2.1 MB | Cutscene characters |
| `assets/magic/` | 10 | 1.4 MB | Magic / tech spell effects |
| `assets/externalized/` | 1 | 0.5 MB | `viral_buttons/crossDCi.swf` |
| `assets/swf/` | 1 | 0.5 MB | `dynamic2.swf` |
| `assets/fonts/` | 2 | 0.1 MB | SWF font libraries |
| `config/` | 12 | 6.1 MB | The 2012 game config + 5 JSON-Patch deltas + the raw server captures |
| `villages/` | 31 | 2.5 MB | `initial.json`, 6 static neighbours, 23 quest villages |
| `templates/` | 19 | 0.9 MB | The HTML host page and CSS |
| `build/`, `tools/`, `mods/`, `stub/` | 14 | 0.1 MB | Upstream build scripts, content tooling, the mod system, `crossdomain.xml` |
| root files | 14 | 0.2 MB | Python sources, `LICENSE`, `README.md`, `FLASH.md`, `LINUX.md`, `RELEASES.md` |
| **Total** | **3 292** | **726.5 MB** | |

## 3. Integrity

Two artefacts describe the vendored tree:

| File | Purpose |
|---|---|
| `MANIFEST.sha256` | GNU `sha256sum` format, sorted by path. Verifiable with `sha256sum -c` on any POSIX system. |
| `MANIFEST.json` | The same data plus byte sizes and a per-directory breakdown, for tooling. |

Both cover the 3 292 working-tree files (the upstream `.git` directory is excluded, as
stated above).

### Verifying

```bash
node scripts/verify-upstream.mjs           # verify (exit 1 on any drift)
node scripts/verify-upstream.mjs --write   # regenerate the manifest, then verify
```

The verifier reports changed, missing and unexpected files separately, and exits non-zero
if any of the three counts is non-zero.

## 4. Git LFS

`assets/` is 716.8 MB of pure binary and is therefore tracked in **Git LFS**
(see the repository `.gitattributes`). Consequences:

* The git history stores small pointer objects; the binaries live in LFS storage.
* A fresh clone needs `git lfs pull` before the assets are present.
* **A partial clone is supported.** The build only needs the assets it actually uses, so
  a targeted pull avoids the 239.7 MB of archival `Basesec` builds:

  ```bash
  # everything except the 57 historical client builds
  git lfs pull --include="upstream/socialwarriors/assets/sprites/**" \
                --include="upstream/socialwarriors/assets/fx/**" \
                --include="upstream/socialwarriors/assets/thumbs/**" \
                --include="upstream/socialwarriors/assets/sounds/**" \
                --include="upstream/socialwarriors/assets/magic/**" \
                --include="upstream/socialwarriors/assets/characters_2/**" \
                --include="upstream/socialwarriors/assets/images/**"
  ```

  `Basesec_1.5.4.swf` and `SWLoader.swf` are still needed — they are the reference client
  used by the test oracle — but they are a 4.5 MB download rather than 244 MB.

## 5. The 58 `Basesec` builds

`assets/flash/` holds 58 versions of the client, from `1.4.5` to `1.5.4`, totalling
239.7 MB. They are the **client's own version history** and are the subject of roadmap
task B1, which diffs the embedded `Config.as` across all of them to establish whether
the server signing key was constant and how the protocol evolved.

Only `Basesec_1.5.4.swf` (4.33 MB) and `SWLoader.swf` (128 kB) are needed to run the
game or the test oracle.

## 6. How the upstream tree is used

| Use | Where |
|---|---|
| The specification of game behaviour | The decompiled ActionScript 3 from `assets/flash/Basesec_1.5.4.swf` |
| The reference for the wire protocol | `server.py`, `command.py`, `engine.py`, `sessions.py`, `get_game_config.py`, `get_player_info.py` |
| The source of the game data | `config/main.json` + `config/patch/*.json` → the content bundle |
| The source of the art and audio | `assets/` → the atlases the new client renders |
| The oracle | The original client, run against the new server, to diff game rules |

**Never edit anything under `socialwarriers/`.** Changes to the vendored tree break the
manifest, invalidate the pin, and destroy the ability to diff against upstream.

## 7. Provenance of the analysis

The findings in [`../re/`](../re/README.md) were produced against this exact tree. The
supporting evidence is in [`../re/evidence/`](../re/evidence/):

| Artefact | Covers |
|---|---|
| `live/requests.jsonl` | 1 664 HTTP requests captured from the real Flash client |
| `live/command-payloads.txt` | 34 decoded `command.php` batches |
| `live/hmac-verification.txt` | The 13-construction signature test that confirms the key |
| `client/artifact-digests.txt` | SHA-256 of the key upstream artefacts |
| `client/basesec_dumpswf_tags.txt` | The 22 228-line SWF tag dump of the client |

## 8. Licensing

The vendored tree is **GPL v3** and keeps its `LICENSE` file verbatim. It is **not** linked
into the new client's source; it is a separate, clearly-marked GPL component of this
repository.

The **content** inside it — the sprites, the audio, the fonts and the game config — is
**Zynga's**, not GPL. The upstream project itself frames its distribution as archival
preservation, citing the US Copyright Office's PCCPSACT exemption, EFGAMP, the UNESCO
PERSIST programme, BlueMaxima's Flashpoint and the Adobe Flash Player Archive.

That position must be settled before any public release of this repository's builds. It is
tracked as a release gate in Group I of [`../../docs/ROADMAP.md`](../../docs/ROADMAP.md).
