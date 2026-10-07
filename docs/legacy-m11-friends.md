# M11 investigation — `friends` is a real surface, and the committed classification is wrong

**Status:** investigation only. No code, no spec, no endpoint, no client module.
**Milestone:** M11 — Social and Special Systems, deliver item **`friends`**.
**Branch:** `docs/friends-roster-proposal`.
**Predecessor:** `docs/legacy-m11-social.md` (PR #309, merged `0cccdde`, correction `fe63b85`).

---

## 0. Summary

`docs/legacy-m11-social.md` §7 classifies **`friends`** as *"State-only, no consumer.
Persisted in 33/33 documents, zero legacy occurrences, uniformly empty."*

**The "zero legacy occurrences" clause is false.** `friends` has **4 code-only
occurrences** in `sessions.py`, inside a function that is **called from a served
route**. Alongside it sits a second function, `neighbors()`, with **9** code-only
occurrences, whose output is a **root key of the recorded bootstrap response**.

`friends` is therefore **not** a closure. It is a **server-derived roster
projection** — the one M11 surface whose members, exclusions, and per-member
fields are all decided by the preserved server — and it has a **fully executed
legacy oracle** already committed to this repository.

The decisive finding is §7: **there is no friendship relationship at all.** The
deliver item named `friends` is served as *every other village, unconditionally*.
No add, no remove, no consent, no mutual acknowledgement. The
relationship-shaped fields are inert.

Two corrections to the committed record travel with this: the **zero-occurrence
clause is false** (§2), and the social fields are **not all `privateState`
keys** — `receivedAssists` and `resourcesTraded` live on **`maps[0]`** (§7),
which is the recorded M10 census defect recurring.

**Both roster arms already have executed-legacy oracles committed to this
repository** (§5.0, §8), making this the **first M11 line not to require a new
fixture capture**.

---

## 1. Denominators and instrument faults

**Legacy module census — 11 top-level `.py` modules**, unchanged from the
`docs/legacy-m11-darts.md` §1 figure:

| Module | Lines | | Module | Lines |
|---|---|---|---|---|
| `command.py` | 956 | | `server.py` | 346 |
| `constants.py` | 1111 | | `sessions.py` | 256 |
| `engine.py` | 271 | | `get_game_config.py` | 319 |
| `auctions.py` | 230 | | `get_player_info.py` | 42 |
| `legacy_command_recorder.py` | 228 | | `version.py` | 51 |
| `bundle.py` | 23 | | | |

### 1.1 Instrument faults committed by this investigation

Three, recorded here rather than quietly fixed — the standing rule is that a
measurement defect is a finding, not a nuisance.

1. **A singular/plural token miss, which is the same class that produced the
   error being corrected.** My first pass searched `neighbor` and measured
   **zero** code-only occurrences across all 11 modules, which *confirmed* the
   committed classification. The legacy code spells the identifier
   **`neighbors`** (`sessions.py:191`). A census that searches the singular and
   reports a confident zero against a plural identifier is an absence claim
   built on a spelling, and this is the **sixth** recorded instance of a
   zero-consumer census failing on identifier form after the aliased-local
   (`magics`), the quoted-subscript (`questsRank`), the whole-word
   (`push_queue_unit2`), the `cmd ==` vs `command ==`, and the
   column-zero-empty-subject failures.
2. **A near-miss that would have inverted the finding's scope.** Having found
   `fb_friends_str` is passed at `server.py:91`, the grep hit in
   `templates/play.html:99` sits next to `fb_sig_user` and `accessToken`, and the
   neighbouring FlashVars made it read as a **Facebook URL bridge** — a
   browser-only surface outside the game protocol. Reading the surrounding lines
   refuted this: lines **88–103** are all inside the `<embed>` **`flashvars`**
   attribute, and `friendsInfo` is a **FlashVar delivered to the SWF**. The
   surface is in-protocol. Recorded because a reader who greps and infers will
   reach the wrong scope, and because "not the client" would have made this
   surface look deliverable-as-refused for the wrong reason.
3. **A file-walk that crashed on a directory it assumed held files.** Walking
   `templates/` with `os.listdir` and opening every entry raised
   `PermissionError` on the `avatars` subdirectory and aborted the probe before
   the corpus derivation ran. An aborted probe that printed partial output is
   how a wrong figure becomes a reported one; the probe was rerun with an
   `isfile` test and every figure below comes from the completed run.
4. **A claim written before it was checked, and found false — recorded here
   rather than quietly fixed.** The first draft of §10 asserted that *no executed
   capture of `play.html` exists* in `tests/fixtures/`, on the reasoning that the
   route had no fixture. Checking found a committed **`play_page`** step
   containing the rendered `friendsInfo` FlashVar with **all five** derived
   entries — so the FlashVar arm *is* executed-captured, and the assertion was
   wrong in the direction that would have **understated** the available evidence.
   The correction is in §10 and the new §5.0. This is the mirror image of fault
   1: there, a singular token produced a confident **absence** that was false;
   here, an unexamined assumption produced a confident **absence** of evidence
   that was also false. **Both errors pointed the same way — toward concluding
   there was less here than there is** — which is worth recording, because that
   is the direction in which a cursor silently skips work.
5. **The document's own verifier reproduced the census defect it was checking
   for.** The claim under test is "`friends` across **11** modules"; the verifier
   looped `sessions.py` alone, so it measured whole-file occurrences as **4**
   against a committed table of **5**, and reported a FAILURE. The committed
   table was right and the verifier was wrong: the fifth occurrence is the
   `engine.py:142` comment. This is the recorded **subject-list** census failure
   — the same class as the column-zero probe that found **0** declarations and
   the rebound-variable probe that ran against the wrong subjects — recurring
   **in the tool written to validate the correction**. A verifier that scopes a
   cross-module claim to one module is worse than no verifier, because its
   failure is credible.
6. **The recorded `privateState`-vs-`maps[0]` defect recurred in this
   investigation's verifier, verbatim as `docs/legacy-m10-mission-completion.md`
   recorded it.** The verifier asserted `receivedAssists` is uniformly `{}` in
   33/33 by reading `privateState`, and got an empty set — because
   **`receivedAssists` and `resourcesTraded` are `maps[0]` keys**. The probe
   reported a confident **absence** where **33 of 33** documents carry the
   field. That is the M10 finding exactly: *"the mission fields live on
   `maps[0]`, not `privateState`, and a `privateState` probe reported a
   confident absence where 39 of 39 documents carry them."* It has now recurred
   **across milestones**, in the tool written to validate a correction to a
   census carrying the same defect. **A probe that looks in one place and
   reports absence is unproven**, and the fix is a whole-document path walk,
   which is what §7's table now records.
7. **Three further cosmetic defects in the verifier, recorded because the
   pattern is the point and because they changed no claim.** All five defects
   in this investigation's checking tool (faults 5, 6, and these three)
   **reported a document defect that did not exist**, in both directions: a
   **subject list** scoped to one file (fault 5), a **location** assumed to be
   `privateState` (fault 6), a **casefold** mismatch between a camelCase needle
   and a lowercased haystack, a **dotted-versus-slashed path** notation, and a
   **phrase wrapped across two lines behind backticks and italics** that a raw
   line scan could not see. None changed a recorded figure; all five produced a
   confident, wrong **failure**, which is the more dangerous direction, because a
   verifier's failure is believed. Every one was fixed by measuring the
   document's real form rather than by relaxing an assertion, and the final run
   is **44 checks, 0 failed** — re-measuring the six-rule census over all **11**
   modules and doing a **whole-document path walk** for the §7 table.

---

## 2. CORRECTION to `docs/legacy-m11-social.md` §7

The committed table row reads:

| Deliver item | Classification | Basis |
|---|---|---|
| **Friends** | **State-only, no consumer.** Persisted in 33/33 documents, **zero legacy occurrences**, uniformly empty | §4, §4.1 |

Two of the three clauses survive; one does not.

| Clause | Verdict |
|---|---|
| Persisted in 33/33 documents | **holds** (the relationship-shaped fields are uniformly empty, §7) |
| Uniformly empty | **holds** (unchanged) |
| **Zero legacy occurrences** | **FALSE — corrected here** |

**What the token census actually returns**, six rules over all 11 modules:

| Field | whole-file occ | whole-file lines | code-only occ | code-only lines | exact tokens | quoted access | verdict |
|---|---|---|---|---|---|---|---|
| `friends` | 5 | 5 | **4** | **4** | 4 | 0 | **PRESENT** |

All **four** code-only occurrences are in `sessions.py` (`169`, `179`, `188`,
`189`) — a local variable in a function with a live caller, not a field-name
match inside a payload.

The **fifth** whole-file occurrence is a **comment**, `engine.py:142`:
`attr["si"].append(0) # 0 is for buying instead of hiring friends`. It is
excluded by the code-only rules and is recorded here because it is the only
statement anywhere in the preserved server of what a roster member *is* — and
it says **hiring**, not friending. That is consistent with §7 and is not treated
as behaviour.

The rest of the §4 social-field census **does not change**. Re-measured here
across all 11 modules under the same six rules, **29 of 30** probed social
tokens return **zero under every rule**: `friendList`, `friend_list`,
`friendId`, `friend_id`, `friendsHelpedCoveredItem`, `firstTimeAlliance`,
`helpMap`, `neighborAssists`, `receivedAssists`, `neighbor_assists`,
`received_assists`, `assist`, `assists`, `helped`, `neighbor`, `neighbours`,
`allies`, `ally`, `cooperation`, `gift`, `gifts`, `rescue`, `rescued`,
`crossPromotionsFinished`, `unlockedSkins`, `tournament`, `event`, `specials`,
`special`.

So the committed investigation was **right that social content has no consumer
and right that social state is never written**, and **wrong only about the
existence of a social roster surface** — which is a different claim, and the one
this deliver item is named for.

---

## 3. Finding A — three undelivered social surfaces

All three live outside `command.py`, which is why a dispatcher-centred census
missed them. None is owned by any delivered capability.

| # | Symbol | Location | Reached by | Serves |
|---|---|---|---|---|
| 1 | `neighbors(USERID)` | `sessions.py:191-221` | `get_player_info.py:18` | the **bootstrap JSON** |
| 2 | `fb_friends_str(USERID)` | `sessions.py:168-189` | `server.py:91` → `play.html:99` | the **`friendsInfo` FlashVar** |
| 3 | `get_neighbor_info(userid, map_number)` | `get_player_info.py:23-42` | `server.py:174/178/182` | a **visit** payload |

Surface 3 is reached by **three** of the four branches of one route, which makes
it a first-class endpoint behaviour rather than a helper.

### 3.1 Ownership

No delivered capability, spec, envelope, client module, or endpoint names any of
the three. Measured over `openspec/specs/**`, **zero** spec files mention
`fb_friends_str`, `neighbor_session`, `get_neighbor_info`, or `pic_square`.

`pic_square` occurs **exactly twice across the 11 legacy modules**
(`sessions.py:178`, `:187`) — the two dictionary writes in §5. Its only other
occurrences in the repository are inside the committed `play_page` capture
(§5.0) and this document.

---

## 4. Finding B — the roster projection, `neighbors()`

```python
def neighbors(USERID: str):
    neighbors = []
    # static villages
    for key in __villages:
        vill = __villages[key]
        if vill["playerInfo"]["pid"] == "100000030" \
           or vill["playerInfo"]["pid"] == "100000031": # general Mike
            continue
        neigh = vill["playerInfo"]
        neigh = json.loads(json.dumps(vill["playerInfo"]))
        neigh["xp"] = vill["maps"][0]["xp"]
        neigh["level"] = vill["maps"][0]["level"]
        neigh["gold"] = vill["maps"][0]["gold"]
        neigh["wood"] = vill["maps"][0]["wood"]
        neigh["oil"] = vill["maps"][0]["oil"]
        neigh["steel"] = vill["maps"][0]["steel"]
        neighbors += [neigh]
    # other players
    for key in __saves:
        vill = __saves[key]
        if vill["playerInfo"]["pid"] == USERID:
            continue
        neigh = json.loads(json.dumps(vill["playerInfo"]))
        neigh["xp"] = vill["maps"][0]["xp"]
        ...
    return neighbors
```

**Recorded, not normalised:**

- Line `:199` assigns `vill["playerInfo"]` **by reference** and line `:200`
  immediately rebinds it to a `json.loads(json.dumps(...))` deep copy. The
  first assignment is dead and its only effect is that `playerInfo` is **not**
  aliased into the response. This is the recorded "stop clogging up playerInfo"
  comment at `:213`.
- **Six** fields are derived from `maps[0]`: `xp`, `level`, `gold`, `wood`,
  `oil`, `steel`. `steel` is derived; `cash` is **not**, even though
  `playerInfo` carries it.
- Two exclusion rules, in different scopes: the **two-pid literal pair** applies
  to `__villages` only; the **self** exclusion applies to `__saves` only. So a
  static village that is *your own* pid is **not** excluded from the static loop.
- `USERID` is used **only** for the self-exclusion. It is never compared against
  `__villages`.

### 4.1 The exclusion pair is a hardcoded literal, not derived from content

`"100000030"` and `"100000031"` are literals at `sessions.py:173-174` and
`:196-197`. They are **not** derived from any committed schedule, and the
committed comment `# general Mike` is the only statement of what they are.

They are, however, **exactly** two committed villages:

| File | `playerInfo.pid` | In roster? |
|---|---|---|
| `General_Mike_30.json` | `100000030` | **excluded** |
| `General_Mike_31.json` | `100000031` | **excluded** |
| `AcidCaos.json` | `AcidCaos` | served |
| `Kiriakos.json` | `Kiriakos` | served |
| `Nerri.json` | `Nerri` | served |
| `Neutral.json` | `Neutral` | served |
| `Scarlet.json` | `Scarlet` | served |
| `initial.json` | `null` | never loaded (skipped at `sessions.py:78`) |

**`load_static_villages()` loads every `villages/*.json` except `initial.json`
(`sessions.py:78`), so `__villages` holds 7 entries; the two-pid exclusion
removes 2, leaving 5.** This is the recorded *false attraction* class in the
inverted direction: the literal is a genuine filter with a corpus fact behind
it, and the derivation of **5** follows from the code rather than from the
number of files in the directory (**8**).

### 4.2 Entry shape: 12 carried + 6 derived = 18 keys

The `playerInfo` block carried into every entry has exactly **12** keys:
`cash`, `completed_tutorial`, `default_map`, `last_logged_in`, `map_names`,
`map_sizes`, `name`, `pic`, `pid`, `sp_ref_cat_install`, `sp_ref_uid`,
`world_id`.

Adding the six derived fields gives **18**. All six derived fields have **5
distinct values** across the served set, so the derivation is observable and
non-degenerate:

| pid | xp | level | gold | wood | oil | steel |
|---|---|---|---|---|---|---|
| `AcidCaos` | 117012 | 41 | 5898 | 1176 | 2750 | 107 |
| `Kiriakos` | 155520 | 46 | 63540 | 32700 | 23970 | 9870 |
| `Nerri` | 122956 | 42 | 58007 | 161960 | 129788 | 62811 |
| `Neutral` | 136878 | 44 | 37691 | 19705 | 15401 | 14151 |
| `Scarlet` | 107694 | 33 | 62395 | 96060 | 97521 | 94869 |

**No neighbour entry contains any `privateState` key** — verified by
intersecting every entry's keys against the recording player's `privateState`
keys: **zero** intersections. The roster exposes economy and identity, never
private progress.

---

## 5. Finding C — `fb_friends_str` is the `friendsInfo` FlashVar

```python
def fb_friends_str(USERID: str) -> list:
    friends = []
    for key in __villages:
        vill = __villages[key]
        if vill["playerInfo"]["pid"] == "100000030" \
           or vill["playerInfo"]["pid"] == "100000031": # general Mike
            continue
        frie = {}
        frie["uid"] = vill["playerInfo"]["pid"]
        frie["pic_square"] = vill["playerInfo"]["pic"]
        friends += [frie]
    for key in __saves:
        ...
    return friends
```

**Two fields, not eighteen.** Each entry is `{uid, pic_square}` — the
**Facebook profile-picture** field name, mapped from `playerInfo.pic`.
`pic_square` appears exactly twice in the repository, both here.

It reaches the client through `server.py:91`:

```python
return render_template("play.html", save_info=save_info(USERID),
    serverTime=timestamp_now(), friendsInfo=fb_friends_str(USERID), ...)
```

and `templates/play.html:99`:

```
&friendsInfo={{friendsInfo | tojson}}&brk=0
```

**That line is inside the `<embed>` `flashvars` attribute** (lines **88–103**),
so the roster is delivered to the SWF as a FlashVar, alongside `fb_sig_user`,
`accessToken`, `user_key`, `language`, `lastLoggedIn`, `dailyBonus`,
`serverTime`, `forceSyncError`, `forceAttackReload`, `forceQuestReload`.

### 5.0 The FlashVar arm is executed-captured too

`tests/fixtures/godot-compatibility-boot/steps/play_page/response.body` is a
committed executed-legacy capture of this route, and it contains the rendered
FlashVars verbatim:

```
&friendsInfo=[{"pic_square": "https://avatars.githubusercontent.com/u/11525599?s=68", "uid": "AcidCaos"}, {"pic_square": "https://github.com/AcidCaos/socialwarriors/blob/main/templates/avatars/kiriakos.png?raw=true", "uid": "Kiriakos"}, {"pic_square": "https://avatars.githubusercontent.com/u/49306390?s=68", "uid": "Nerri"}, {"pic_square": "https://avatars.githubusercontent.com/u/135655497?s=68", "uid": "Neutral"}, {"pic_square": "https://github.com/AcidCaos/socialwarriors/blob/main/templates/avatars/scarlet.png?raw=true", "uid": "Scarlet"}]&brk=0
```

**Five entries, exactly the derived set of §4.1, in the same order** as the
bootstrap roster's `neighbors` — which is consistent with a shared `os.listdir`
iteration and is *not* evidence of a committed order (§8.1).

One serialization detail, recorded so it is not mistaken for a contract: the
captured JSON lists `pic_square` **before** `uid` (alphabetical), while
`fb_friends_str` assigns `uid` first. The ordering is an artifact of the
template's JSON serialisation, not a field-order guarantee.

The same block records `lastLoggedIn=1349266517` and `dailyBonus=0` as
**template literals** in `play.html`, not server-derived values. Out of scope
here; noted so a future line does not read them as derived.

### 5.1 Two roster channels, and they disagree

| | `neighbors` (bootstrap JSON) | `friendsInfo` (FlashVar) |
|---|---|---|
| Function | `neighbors()` `sessions.py:191` | `fb_friends_str()` `sessions.py:168` |
| Per-entry fields | **18** (12 + 6 derived) | **2** (`uid`, `pic_square`) |
| Carries economy | **yes** (6 fields) | **no** |
| Carries `privateState` | no | no |
| Two-pid exclusion | yes | yes |
| Self exclusion | `__saves` only | `__saves` only |

**A roster is served twice, in two shapes, over two transports, by two
functions that are near-duplicates and were not derived from one another.** Any
line that delivers one and not the other must say which it chose and why.

---

## 6. Finding D — the visit branch and its four-way dispatch

`server.py:155-182`, one route, four branches selected by the **client-sent**
`user` value:

```python
user = request.values['user'] if 'user' in request.values else None
map  = int(request.values['map']) if 'map' in request.values else None

if user is None:                                    # Current Player
    return (get_player_info(USERID), 200)
elif user in ["100000030","100000031"]:             # General Mike
    return (get_neighbor_info("100000030", map), 200)
elif user.startswith("100000"):                     # Quest Maps
    return (get_neighbor_info(user, map), 200)
else:                                               # Static Neighbours
    return (get_neighbor_info(user, map), 200)
```

### 6.1 A preserved defect: the General Mike branch discards which pid was asked for

Branch 2 tests membership in the **two-pid pair** and then passes the
**literal `"100000030"`** for both. Requesting `100000031` returns
`100000030`'s data. This is a genuine, recordable behaviour of the preserved
server and **not** reproduced: passing the requested `user` would be a
correction, and `docs/legacy-town-expansion.md` records the standing rule that
a corrected server is a divergence, not parity.

### 6.2 `get_neighbor_info` exposes the neighbour's entire `privateState`

```python
def get_neighbor_info(userid, map_number):
    _session = neighbor_session(userid)
    if not _session:
        print(f"USERID {userid} not found.")
        return ""
    ...
    _map_number = map_number
    if not map_number:
        _map_number = 0
    neighbor_info = {
        "result": "ok", "processed_errors": 0,
        "timestamp": timestamp_now(),
        "playerInfo": neighbor_session(userid)["playerInfo"],
        "map":        neighbor_session(userid)["maps"][_map_number],
        "privateState": neighbor_session(userid)["privateState"],
    }
```

Recorded, with four consequences that are **not** softened:

1. A visit returns the visited player's **complete `privateState`** — the
   opposite of the roster, which is deliberate (§4.2).
2. On failure it returns the **empty string `""` with HTTP 200**, not an error
   object. A typed client that parses this as JSON fails closed.
3. `_map_number` defaults to `0` when `map` is falsy. Because `0` is itself
   falsy, `map=0` and an absent `map` are indistinguishable. A **negative** or
   out-of-range `map` is unguarded and raises.
4. `neighbor_session` resolves against `__saves`, then `__quests`, then
   `__villages` (`sessions.py:159-166`), and returns **`None`** when absent.
5. `neighbor_session(userid)` is called **four** times on the success path
   (`:24`, `:38`, `:39`, `:40`) rather than reusing `_session`.

### 6.3 The `"100000"` prefix is a routing convention, not an identity test

Branch 3 is `user.startswith("100000")`. **23** committed quest villages carry
pids in that space (`villages/quest/`, `100000001`…), and the branch prints
`Quests.QUEST[user] if user in Quests.QUEST else "?"`. The prefix test and the
quest membership test are **independent**, so a pid that begins `100000` but is
not in `Quests.QUEST` still routes here and prints `?`. **No claim is made that
the prefix identifies a quest map** — that would be reading a routing prefix as
an identity.

Note also that the two General Mike pids are **not** in the quest set, so the
General Mike branch and the quest branch never overlap in the committed corpus:
the pair is the only `100000`-prefixed value that is *not* a quest map.

---

## 7. Finding E — decisive: there is no friendship relationship

The deliver item is named `friends`. What the server serves is:

**`neighbors(USERID)` returns every other loaded village, unconditionally.**
There is no friendship record anywhere in the preserved server. Measured over all
11 modules under the six rules (§2), every relationship-shaped token is absent:

| Token | code-only occurrences | Lives at | Corpus value |
|---|---|---|---|
| `neighborAssists` | **0** | `privateState.neighborAssists` | `{}` in **33/33** |
| `receivedAssists` | **0** | **`maps[0].receivedAssists`** | `{}` in **33/33** |
| `resourcesTraded` | **0** | **`maps[0].resourcesTraded`** | `{}` in **33/33** |
| `friendsHelpedCoveredItem` | **0** | `privateState.friendsHelpedCoveredItem` | `null` in **33/33** |
| `firstTimeAlliance` | **0** | `privateState.firstTimeAlliance` | `null` in **33/33** |
| `helpMap` | **0** | `privateState.helpMap` | `[]` in **33/33** |
| `assist` / `assists` / `helped` | **0** | — | — |

**Correction to `docs/legacy-m11-social.md` §4/§4.1 — these fields are not
all in one place.** §4 measures "19 social-looking state keys" and §4.1 presents
their corpus values in a single table, which reads as a `privateState` census.
It is not one: **`receivedAssists` and `resourcesTraded` are `maps[0]` keys.**
The committed *values* (`{}` in 33/33) are correct; the committed *placement* is
unstated, and a reader who probes `privateState` alone gets a confident
**absence** for two fields that **33 of 33** documents carry.

So the shape is:

- **Membership** is total, not selective. Every other village is a "friend".
- **Direction** is absent. There is no "my friends" distinct from "friends of".
- **Consent** is absent. Nothing a player does can remove a village from the
  roster, because nothing selects membership in the first place.
- **Lifecycles** are absent. No add, no remove, no pending, no accepted.

**A line delivering this must call it a roster, and must refuse the word
"friend" as a relationship claim.** Presenting a directory listing as a social
relationship is precisely the "reports obtainable/active" failure that
`godot-darts` refused. The three social tables (41 entries, zero consumers,
`godot-social-state`) are the committed content a real relationship system
*would* have used, and they are unread — so the roster cannot be reconciled
against them and must not be.

---

## 8. Finding F — the recorded executed oracle already covers this

`tests/fixtures/godot-compatibility-boot/steps/get_player_info/response.body`
is a committed **executed-legacy** capture. Its root keys are:

```
map, neighbors, playerInfo, privateState, processed_errors, result, timestamp
```

**`neighbors` is a root key, and its content matches §4 derivation exactly:**

| Property | Derived (§4) | Recorded fixture | Agree |
|---|---|---|---|
| entry count | **5** | **5** | yes |
| pids | `AcidCaos`, `Kiriakos`, `Nerri`, `Neutral`, `Scarlet` | same 5 | yes |
| self present | no | **no** | yes |
| General Mike present | no | **no** | yes |
| keys per entry | 18 | **18** | yes |
| `playerInfo` keys carried | 12/12 | **12/12** | yes |
| extra keys | exactly the 6 derived | exactly `xp, level, gold, wood, oil, steel` | yes |
| `privateState` key in any entry | no | **no** | yes |
| every derived field distinct | 5 distinct values each | same values | yes |

This is the strongest evidence class available in this project: an executed
legacy transaction whose every leaf is derived from committed source and
committed corpus. **The roster arm has real parity evidence available today**,
which no M11 line so far can claim.

### 8.1 It is already environment-dependent, and already recorded as such

`tests/fixtures/godot-compatibility-boot/field-stability.json` records the field:

- `"symbol": "neighbors / load_static_villages"`
- `"claim": "Static-village iteration order follows os.listdir() order …"`
- classified **environment-dependent**, alongside
  `tests/fixtures/godot-compatibility-boot/README.md:101`.

So **list order is not derivable** from the corpus — it is `os.listdir` order.
Any delivered projection must report the roster as an **unordered set** and must
not assert a committed order.

### 8.2 The Compatibility API already serves it

`apps/compat-api/compat_legacy.py:221` returns the real in-process
`get_player_info(user_id)`, which calls `neighbors()`. `/v0/bootstrap` therefore
**already carries `neighbors`**, and `apps/compat-api/field_stability.py:75-76`
registers the legacy surface. What is undelivered is the **typed client
projection** and any explicit treatment of the rules — not transport.

---

## 9. False attractions recorded for whoever implements this

1. **`neighbors` has two unrelated meanings in this repository.** The
   `expansion_prices` schedule carries a `neighbors` **requirement count** (98
   entries, saturating at `15`), owned as content by
   `economy-schedules-normalization` and **refused as gameplay** by
   `godot-building-expand` design D3. The bootstrap key is a **list of
   villages**. A search for `neighbors` in the delivered client returns
   `boot_data.gd:607 var neighbors := 0` — the **requirement**, owned and
   refused — and **not** the roster. Searching the token will find the wrong
   thing and look like it already exists.
2. **The two roster functions are near-duplicates that were not derived from
   each other.** They are not one function with two callers; §5.1 shows they
   emit different shapes. Do not deduplicate them into one projection.
3. **The exclusion is a literal pair, not a content lookup.** Nothing in
   `config/` or the normalized package names General Mike. Deriving the
   exclusion from content would be an invention; §4.1 shows there is nothing to
   derive it from.
4. **`pic_square` is not a Facebook API call.** It is a dictionary key the
   server writes from `playerInfo.pic`. There is no Facebook traffic anywhere in
   the preserved server, and none is claimed.
5. **`"100000"` does not identify a quest map** (§6.3).

---

## 10. What this investigation does NOT establish

- **No parity claim is made for roster _ordering_**, which is `os.listdir`-dependent
  and already recorded as environment-dependent (§8.1). The narrower claims —
  membership, entry count, carried key set, derived values — **do** have
  executed evidence today, on both arms (§5.0, §8), and the claim is kept to
  what those bytes actually show.
- **No parity claim for the FlashVar's transport.** The `play_page` capture
  records the rendered `friendsInfo` value, so the roster content is executed
  evidence; **how the Flash client consumed that FlashVar is not**, and no
  delivered client may depend on FlashVars at all.
- **No parity claim for the visit branch.** `get_neighbor_info` is reached by
  three branches of a route whose recorded capture exercises the **current-player**
  branch only (`README.md:62`, "no `user` parameter"). No committed fixture
  exercises a visit, a General Mike request, or a quest-map request.
- **No claim that any roster entry is a friend**, a neighbour in the social
  sense, or an ally (§7).
- **No claim about what the Flash client did with `friendsInfo` or
  `neighbors`.** Absence of a server-side relationship is a statement about the
  preserved server; the Flash client may have held the relationship UI entirely
  client-side. This is the same limitation that made M10's exit criterion
  unsatisfiable and it is **unverifiable from this oracle**.
- **The corpus has no example of a populated social relationship field** — all
  uniformly empty in **33/33** documents. That is a *corpus* fact, recorded as
  such by the committed investigation, and not evidence that the behaviour is
  absent.
- **No claim about `__saves` participation.** The recorded capture runs with
  **no** `saves/` directory, so the "other players" loop contributed nothing and
  the roster is **static-villages-only** in every recorded observation. The
  `__saves` half is measured in source only.
- **`get_neighbor_info`'s empty-string failure mode was not executed.**

---

## 11. Recommended next step

A `godot-friends` line is warranted and is **not** a refusal line. It would:

- **deliver** the roster projection as an **unordered set**, each entry the 12
  carried `playerInfo` keys plus the **6** derived fields, failing **closed** on
  a malformed entry, a non-list roster, or a non-object entry;
- **deliver** the derivation of membership: all loaded static villages, minus
  the **hardcoded literal pid pair**, minus self in the saves loop only;
- **report** the roster's two channels and the disagreement between them (§5.1)
  rather than picking one silently;
- **record** the General Mike discarded-pid behaviour as a **divergence not
  reproduced** (§6.1), the `""`-with-200 failure mode (§6.2), the
  `privateState` exposure on visit (§6.2), the `os.listdir` order (§8.1), and the
  two meanings of `neighbors` (§9.1);
- **refuse** the relationship vocabulary entirely (§7) — no friendship, no
  ally, no assist, no consent — with the six-rule zero-consumer census and the
  uniformly-empty corpus state as its basis;
- **refuse** to derive the General Mike exclusion from content (§9.3), shipping
  the literal pair with the rejected derivation recorded.

**Evidence note — both roster arms already have an executed oracle** (§5.0,
§8). The `friends` line is therefore the **first M11 line not to need a new
fixture capture**, and the only one whose oracle is already committed:

| Arm | Executed evidence committed today |
|---|---|
| `neighbors` bootstrap list | `steps/get_player_info/response.body` — 5 entries, 18 keys each |
| `friendsInfo` FlashVar | `steps/play_page/response.body` — 5 entries, 2 keys each |
| visit / `get_neighbor_info` | **none** |
| `__saves` half of either roster | **none** — captures ran with no `saves/` |

The visit arm and the `__saves` half would need a capture taken in a disposable
copy with a **second player save present**, which the committed corpus cannot
supply. That is a strictly narrower gap than any prior line has carried.