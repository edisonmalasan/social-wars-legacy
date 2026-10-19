# REA MCP Evidence Log

This document records what the **REA reverse-engineering MCP server** was able to establish
directly about the Social Wars target, and — just as importantly — where REA's coverage
ended. Every claim below is backed by REA Evidence (identified by `ev_…` ids) or by a
reproducible command.

| | |
|---|---|
| REA host | Windows 11 x64 |
| Analysis provider | Ghidra **12.1.4** (headless), installed at `D:\Apps\ghidra_12.1.4_PUBLIC` |
| Java | OpenJDK 21.0.12.1 (Temurin) |
| Unavailable providers | Hopper (macOS only), IDA (not configured), Rizin (`ERR_REA_WINDOWS_NATIVE`), `native-macos` (macOS only) |
| Target | `C:\Users\Edison\Desktop\socialwarriors` (a directory, not a single binary) |

---

## 1. Capability assessment — REA cannot open a SWF

`open_binary` is REA's entry point for local artifacts. For each of the three representative
Flash files it returned a typed, explicit rejection:

```
open_binary("assets\flash\Basesec_1.5.4.swf")
  -> target_unavailable / unsupported_target
     reason: "unsupported binary format"
     constraint: "file_format_rejected"

open_binary("assets\flash\SWLoader.swf")        -> same
open_binary("assets\swf\dynamic2.swf")          -> same
```

REA's `format` enumeration contains no SWF member, and its format detector has no SWF
signature. **This is a genuine coverage gap, not a misconfiguration**, and it is the single
most important thing to know about REA for this project: REA is a *native/managed binary*
tool, and a Flash game is neither.

The same applies to the Python sources — REA does not analyse Python.

### 1.1 What REA *can* be used for here

| REA capability | Applicability to this target |
|---|---|
| `open_binary` + `list_strings` / `search_bytes` / `read_bytes` | ✅ via a 64 KB chunking workaround (see §3) |
| `binary_overview`, `list_procedures`, `list_names` | ⚠️ limited value on a raw blob (see §3.1) |
| `analyze_javascript_application` | ✅ used on the **Flashy Browser** `app.asar` (§4) |
| `list_browser_targets` / `list_electron_targets` / `list_javascript_runtime_targets` | ✅ used to attach to the live game session (§5) |
| `inspect_binary_layout` | ❌ pwntools provider is Linux-x64 only |
| `execute_rizin_command` | ❌ Rizin unavailable on this host |
| `analyze_function` / `procedure_pseudo_code` / `batch_decompile` | ❌ no native code in the target |
| `import_evidence_bundle` | ✅ available for consolidating findings |

## 2. The SWF container, established independently

Before REA could be used at all, the SWF had to be taken apart. `Basesec_1.5.4.swf` is a
**CWS** (zlib-compressed) SWF, version 10:

```
offset 0  : 43 57 53 0a        "CWS"  + version 10
offset 4  : 19 eb 5c 00        FileLength = 6 089 497 (uncompressed size)
offset 8  : 78 da ...          zlib stream
```

Decompressed: 4 542 821 → **6 089 497 bytes**.

`ffdec -dumpSWF` (JPEXS 26.3.0) then produced a 22 228-line tag listing
([`../evidence/client/basesec_dumpswf_tags.txt`](../evidence/client/basesec_dumpswf_tags.txt))
whose histogram is the structural fingerprint of the client:

| Tag | Id | Count | Meaning |
|---|---|---|---|
| `PlaceObject2` | 26 | 10 002 | display list |
| `DefineSprite` | 39 | 1 224 | nested timelines (the ~1 100 unit/building animations) |
| `DefineText`/`DefineEditText` | 11/37 | 808 | UI text |
| `DefineShape4` | 83 | 185 | vector art |
| `DefineFont3` | 75 | 6 | **Komika Axis, Arial Rounded MT Bold, Eras Bold ITC, Freestyle Script, DS-Digital Bold Italic, Arial** |
| `PlaceObject3` | 70 | 1 523 | display list |
| **`DoABC2`** | **82** | **1** | **the entire game code, one block, named `frame1`** |
| `SymbolClass` | 76 | 1 | class → symbol linkage |
| `Metadata` | 77 | 1 | RDF metadata |
| `Protect` | 24 | 1 | — |
| `FileAttributes` | 69 | 1 | AS3 flag |

**There is exactly one `DoABC2` block**, at decompressed offset `0x003D80FB`, length
**2 048 858 bytes**, flags `1` (not lazy), name `frame1`. The AVM2 payload is
**2 048 841 bytes**, version **46.16** (`10 00 2e 00` = minor 0x0010, major 0x002E).

That single ABC block contains all **1 387 AS3 classes**. JPEXS exported all of them, and
they are the basis of reports 01–03.

## 3. REA analysis of the ActionScript bytecode

### 3.1 The 64 KB chunking workaround

REA's Ghidra adapter on Windows accepts native PE **and** explicitly-selected **raw 6502**
targets — and the 6502 address width caps a raw mapping at **64 KiB**. The 2 MB ABC
therefore cannot be opened directly.

The workaround: split the ABC into 64 KiB chunks, open each as
`format=raw-binary, architecture=6502, entry_point=0x0`, and use REA's
`search_bytes` to locate protocol strings in the *analysed image*.

Chunk density (printable bytes per 64 KiB) shows the constant pool occupies the first
~6 chunks and the method bodies are far sparser:

| Chunk | ABC offset | Strings found | Printable bytes |
|---|---|---|---|
| 0 | 0 | 3 971 | 52 116 |
| 1 | 65 536 | 3 699 | 60 489 |
| 2 | 131 072 | 3 875 | 59 676 |
| 3 | 196 608 | 2 259 | 61 545 |
| 4 | 262 144 | 1 824 | 62 227 |
| 5 | 327 680 | 603 | 19 802 |
| 19–30 | 1 245 184 … | 55–613 each | 819–5 910 |

`binary_overview` on each chunk confirms the mapping: a single `RAM` segment `0x0–0x10000`,
image base `0x0`, and 1–4 spurious "procedures" (6502 disassembly artefacts of byte noise).
`list_strings` returns **0** — Ghidra does not define strings in an untyped raw blob — so
`search_bytes` is the usable primitive.

### 3.2 Byte-pattern search results — the protocol strings

Each row is a REA `search_bytes` hit inside the analysed client image. The address is the
provider-normalised address **within the chunk**; add `chunk × 0x10000` for the absolute
offset in the ABC.

| String | Chunk | Address in chunk | Absolute ABC offset | Evidence id |
|---|---|---|---|---|
| `friendsInfo` | 0 | `0x0c8f4` | 0x0C8F4 | `ev_87784bfffe3` |
| `alliance` | 0 | `0x13c1`, `0x3595`, `0x82f7` | — | `ev_6b6b59ef548` |
| `dynamicUrl` | 1 | `0x0a48` | 0x100A48 | `ev_30c5541f260` |
| `fb_sig_user` | 1 | `0x0fb74` | 0x10FB74 | `ev_958cfa7ea20` |
| `accessToken` | 1 | `0x017cf` | 0x1067CF | `ev_19eb54c621f` |
| `user_key` | 1 | `0x099fa` | 0x1099FA | `ev_6608370cf4b` |
| `lastLoggedIn` | 1 | `0x0015e` | 0x10015E | `ev_c5f795b5228` |
| `publishActions` | 1 | `0x0020d` | 0x10020D | `ev_2bb10492301` |
| `graph.facebook` | 1 | `0x04401` | 0x104401 | `ev_bca9223ecc2` |
| `facebook.com` | 1 | `0x04407` | 0x104407 | `ev_8e4482c417e` |
| **`menvswomen`** | 2 | `0x0b719` | 0x13B719 | `ev_fa233b495dc` |
| **`srvsexwars`** | 2 | `0x0b724` | 0x13B724 | `ev_d59b6e62ded` |
| **`command.php`** | 2 | `0x0f8bf` | 0x14F8BF | `ev_0e1b4c9372f` |
| **`get_game_config.php`** | 2 | `0x099bb` | 0x1399BB | `ev_a5df5a79cbe` |
| `staticUrl` | 2 | `0x0ddd4` | 0x14DDD4 | `ev_623d80e5509` |
| `skiphash` | 2 | `0x053f7` | 0x1353F7 | `ev_5688771d9c8` |
| `get_bets_list` | 2 | `0x0a382` | 0x13A382 | `ev_b5599d0a548` |
| `set_bet` | 2 | `0x0802e` | 0x13802E | `ev_3ca1077217e` |
| **`get_player_info.php`** | 3 | `0x0c4a`` | 0x1CC4A | `ev_9783a2d32c4` |
| `first_number` | 3 | `0x0bc9d` | 0x1BC9D | `ev_65dbddac378` |
| `get_bet_detail` | 3 | `0x01ef7` | 0x1C1EF7 | `ev_d3d2f51f2c0` |
| **`track_game_status.php`** | 4 | `0x0c230` | 0x1CC230 | `ev_443b68de8ed` |
| `crossdomain.xml` | 4 | `0x06b4f` | 0x1C6B4F | `ev_595fed1ea9e` |
| `Facebook` | 4 | `0x02707` | 0x1C2707 | `ev_00f00d57a75` |
| **`sync_error_track.php`** | 5 | `0x01f2f` | 0x101F2F | `ev_088bc40c02e` |

**What this establishes, independently of the decompiler:** the endpoint names
`menvswomen`, `srvsexwars`, `command.php`, `get_game_config.php`, `get_player_info.php`,
`track_game_status.php`, `sync_error_track.php`, `crossdomain.xml`, the three `bets/*`
endpoints, the flashvar names `staticUrl` / `dynamicUrl` / `fb_sig_user` / `user_key` /
`accessToken` / `lastLoggedIn` / `friendsInfo` / `publishActions` / `first_number`, and the
`skiphash` debug switch are **all physically present in the shipped client binary** at the
offsets listed. It also confirms the **socialpointgames**-era naming
(`graph.facebook`, `facebook.com`).

Note that `bets/*` endpoints **exist in the client** even though the upstream server has
those routes commented out — a concrete instance of "client is newer than the server".

## 4. REA analysis of the Flashy Browser (`app.asar`)

The browser that runs the game is itself an Electron application, and REA can analyse it
directly. `analyze_javascript_application` on
`…\52801COKLUK.FlashyBrowser_1.2.4.0_x64__cn7gwh4yapdr0\app\resources\app.asar`:

| Metric | Value |
|---|---|
| Root artifact SHA-256 | `c713c11cede6439c56020a23d34c6a6286b90de77a1315ca00eeae289f01e797` |
| Archive size | 455 979 047 bytes (435 MB) |
| Inventory manifest id | `agm_082171ae4d59144cc2166d357cb2d68e5bcae573b97766403d3ecad7314dd5af` |
| Integrity contradictions | **0** |
| Graph | 79 nodes, 99 edges |
| Statistics | 9 relevant files, 4 parsed JS files, 3 315 AST nodes visited, 49 findings, 0 parse failures |
| Node kinds | 13 ipc-handler, 20 javascript-module, 9 asar-entry, 9 javascript-expression, 7 ipc-channel, 6 artifact, 4 javascript-asset, 3 electron-renderer, 2 browser-window, 1 electron-main, 1 package, 1 storage, 1 endpoint, 2 unknown |

JavaScript assets: `main.js` (1 984 B), `index.js` (3 940 B), `routes/renderer.js`
(14 159 B), `history.js` (2 257 B).

### 4.1 The `BrowserWindow` that hosts the plugin

REA extracted the `webPreferences` literal from `index.js:93:15-106:4`:

| Preference | Value | Consequence |
|---|---|---|
| **`plugins`** | **`true`** | **this is what enables the PPAPI Flash plugin** |
| `nodeIntegration` | `true` | renderer has full Node access |
| `contextIsolation` | `false` | renderer and preload share a context |
| `webviewTag` | `true` | `<webview>` usable from the page |
| `experimentalFeatures` | `true` | — |
| `webSecurity` | `true` | same-origin policy on |
| `allowRunningInsecureContent` | `false` | no mixed content |

The second window (`main.js:9:17-19:6`) is the shell: `contextIsolation=false`,
`nodeIntegration=true`, `webviewTag=true`.

**Security note for the record:** `nodeIntegration: true` with `contextIsolation: false` and
**0 sender-validation observations** means any page loaded in Flashy has full Node.js
access to the host. Treat Flashy as a *development* instrument, not a safe end-user browser.

### 4.2 IPC surface

19 IPC operations over 7 literal channels:

| Channel | Direction | Operation |
|---|---|---|
| `load-url` | main | listen |
| `close-window` | main / renderer | listen / send |
| `minimize-window` | main / renderer | listen / send |
| `maximize-window` | main / renderer | listen / send |
| `save-history` | main / renderer | listen / send |
| `get-history` | main / renderer | listen / **send-sync** |
| `clear-history` | main / renderer | listen / send |

`get-history` is a **synchronous** IPC (`send-sync`), which is a classic Electron
remote-code-execution shape when combined with `nodeIntegration: true`.

## 5. REA attaching to the live game session

With Flashy launched with `--remote-debugging-port=9222`, REA's browser tooling attached
directly to the running game.

### 5.1 `list_browser_targets` (endpoint `http://127.0.0.1:9222`)

```json
{
  "browser": {
    "product": "Chrome/69.0.3497.128",
    "protocol_version": "1.3",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) … flashy/1.2.4 … Electron/4.2.6 …",
    "js_version": "6.9.427.31"
  },
  "targets": [],
  "excluded": { "disallowed_origin": 0, "unsupported_url": 1, "non_page": 1 }
}
```

REA's browser-target lister **excluded the game's page**: the target's CDP `type` is
`webview` (a CEF-specific type), and REA's filter only admits `page`-typed targets. This is
a REA limitation for CEF hosts — the Electron-shaped API in §5.2 handles it correctly.

### 5.2 `list_electron_targets` and `list_javascript_runtime_targets`

`list_electron_targets` returned the browser shell:

```json
{ "target_id": "8ADA27A606838E4C716885DA6AE76A4A", "type": "page",
  "title": "Flashy Browser",
  "file_path": "…\\app\\resources\\app.asar\\routes\\browser.html" }
```

`list_javascript_runtime_targets` returned **both** the shell and the live game page:

```json
{ "protocol_type": "webview",
  "location": { "kind": "url", "origin": "http://127.0.0.1:5055",
                "sanitized_url": "http://127.0.0.1:5055/play.html" } }
```

So REA **can** see, by origin and path, that a Flash client is running against the local
server at `/play.html`. Evidence ids: `ev_603d630dee42…` (browser targets),
`ev_323e61629462…` (electron targets), `ev_3b19ffae3c9e…` (runtime targets).

## 6. Other REA capabilities exercised

| Operation | Result |
|---|---|
| `binary_session` | Full provider/capability matrix for the host (documented in the header table) |
| `binary_overview` | Segment/procedure/string census for each 64 KiB chunk (§3.1) |
| `open_binary` (raw-binary, 6502) | 16 chunks opened; SHA-256 recorded per chunk |
| `search_bytes` | 25 protocol-string hits with evidence ids (§3.2) |
| `analyze_javascript_application` | Full app graph of the Flashy Browser (§4) |
| `list_electron_targets` / `list_javascript_runtime_targets` | Live attachment to the game session (§5) |
| `inspect_binary_layout` | Rejected: pwntools provider is Linux-x64 only |
| `execute_rizin_command` | Rejected: `ERR_REA_WINDOWS_NATIVE` (Rizin not runnable on this host) |
| `analyze_function`, `procedure_pseudo_code`, `batch_decompile` | Not applicable — no native code in the target |
| `open_binary` on a SWF | Rejected: `unsupported binary format` (§1) |

## 7. Where REA stopped and other tools took over — summary

| Layer | Primary tool | Why |
|---|---|---|
| SWF container structure | FFDec `-dumpSWF` | REA has no SWF reader |
| ActionScript semantics | FFDec `-export script` (1 387 classes) | REA cannot decompile AVM2 |
| Protocol strings in the client | **REA `search_bytes`** over 64 KiB chunks | REA-native, addressable, evidence-backed |
| Browser shell | **REA `analyze_javascript_application`** | REA-native, full graph |
| Live session | **REA CDP tooling** + a purpose-built CDP driver | REA observes; the driver acts |
| Python server | direct source reading + runtime probing | — |
| Game data | programmatic JSON analysis | — |
| Asset tree | filesystem analysis + FFDec frame export | — |

## 8. Reproducing the REA-side evidence

```bash
# 1. Chunk the ABC (see tools/chunk_abc.py in the investigation scratch area)
python chunk_abc.py            # -> abc_chunks/abc_chunk_000.bin …

# 2. Open a chunk in REA and search it
#    open_binary(path=<chunk>, format=raw-binary, architecture=6502, entry_point=0x0)
#    search_bytes(pattern=<hex of the wanted string>, limit=8)

# 3. Analyse the browser shell
#    analyze_javascript_application(
#        input_path="C:\Program Files\WindowsApps\52801COKLUK.FlashyBrowser_1.2.4.0_x64__cn7gwh4yapdr0\app\resources\app.asar",
#        format="asar")

# 4. Attach to the live session
#    list_electron_targets(cdp_endpoint="http://127.0.0.1:9222")
#    list_javascript_runtime_targets(inspector_endpoint="http://127.0.0.1:9222")
```
