#!/usr/bin/env python3
"""In-process adapter over the *unchanged* legacy boot modules (design D2).

The Compatibility API never re-implements legacy behavior: it imports the
legacy modules themselves and initializes their state in exactly the order
``server.py`` does::

    from get_game_config import get_game_config     # reads ./config, applies
                                                     # patches, mods, dedup
    from get_player_info import get_player_info, ...
    from sessions import load_saves, load_static_villages, load_quests, ...
    load_saves(); load_static_villages(); load_quests()

``bundle.py`` builds every legacy path from ``"."`` (the process working
directory), so the process must **chdir into a corpus directory** before the
first legacy import. That corpus contains ``config/``, ``mods/``, ``villages/``
and a ``saves/`` directory — never the working tree. Two consequences are part
of the contract and are asserted here:

* ``config/`` is read exactly once, at the first legacy import, so every later
  corpus must carry a byte-identical ``config/main.json`` (otherwise the
  already-loaded configuration would silently belong to another corpus).
* ``sessions.load_saves()`` creates ``./saves`` when it is missing, so a corpus
  without ``saves/`` is refused *before* legacy code runs.

Legacy modules are imported with ``sys.dont_write_bytecode`` forced on, so no
``__pycache__`` is written next to preserved sources. This module itself never
calls ``sessions.save_session`` — persistence happens only inside the legacy
dispatcher (see the persistence scope below).

Corpus construction (``build_corpus``) copies ``config/``, ``mods/`` and
``villages/`` and seeds ``saves/<pid>.save.json`` from
``tests/saves/fresh-player.json`` — byte-for-byte when the seed is not
mutated.

Persistence scope (design D6, spec ``godot-compatibility-boot``): the
session and bootstrap operations below have no persistence path at all —
they never call ``sessions.save_session``.  State-mutating gameplay
execution (``execute_commands``) runs the *unchanged* legacy ``command``
dispatcher, which persists through legacy ``save_session`` into this
corpus's ``saves/`` directory and nowhere else; a working-tree save is
never written.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
SEED_SAVE = REPO_ROOT / "tests" / "saves" / "fresh-player.json"

if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import collect_envelope  # noqa: E402
import expand_envelope  # noqa: E402
import level_envelope  # noqa: E402
from hashing import directory_entries, sha256_file  # noqa: E402

# Directories the legacy boot modules read through bundle.py's "." paths.
CORPUS_COPY_DIRS = ("config", "mods", "villages")

# ``upgrades_to`` / ``trains_ids`` sentinels that mean "no path", copied
# verbatim from the normalized content package's own rule
# (``packages/game-content/tools/build_items.py``: ``RELATION_NONE = (-1, 0)``
# at line 66, applied by ``validate_relations`` at lines 546-557).  Duplicated
# here rather than imported so the Compatibility API keeps depending only on
# the legacy modules it already wraps.
RELATION_NONE = (-1, 0)

_STATE: Dict[str, object] = {}


class LegacyBootError(Exception):
    """Initialization or resolution failure with a stable machine code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def corpus_layout_problems(corpus: Path) -> List[str]:
    """Paths a corpus must provide before legacy modules are imported."""
    problems: List[str] = []
    checks = (
        ("config/main.json", (corpus / "config" / "main.json").is_file()),
        ("villages/initial.json", (corpus / "villages" / "initial.json").is_file()),
        ("villages/quest", (corpus / "villages" / "quest").is_dir()),
        ("saves", (corpus / "saves").is_dir()),
    )
    for label, ok in checks:
        if not ok:
            problems.append(label)
    return problems


def build_corpus(
    destination: Path,
    seed: Path = SEED_SAVE,
    repo_root: Path = REPO_ROOT,
    mutate: Optional[Callable[[Dict[str, object]], None]] = None,
) -> Dict[str, object]:
    """Create a disposable legacy corpus and seed it with one save.

    ``mutate`` (test-only) receives the parsed seed document before it is
    written; when it is ``None`` the seed file is copied verbatim, so the
    seeded save keeps the seed's own SHA-256.
    """
    destination = Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise LegacyBootError(
            "corpus_not_empty", "corpus destination is not empty: %s" % destination
        )
    if not seed.is_file():
        raise LegacyBootError("seed_missing", "seed save not found: %s" % seed)

    document = json.loads(seed.read_text(encoding="utf-8"))
    try:
        pid = str(document["playerInfo"]["pid"])
    except (KeyError, TypeError) as error:
        raise LegacyBootError("seed_invalid", "seed has no playerInfo.pid: %s" % error)
    if not pid:
        raise LegacyBootError("seed_invalid", "seed playerInfo.pid is empty")

    destination.mkdir(parents=True, exist_ok=True)
    for name in CORPUS_COPY_DIRS:
        source = repo_root / name
        if not source.is_dir():
            raise LegacyBootError("source_missing", "legacy directory missing: %s" % source)
        shutil.copytree(source, destination / name)

    saves_dir = destination / "saves"
    saves_dir.mkdir(parents=True, exist_ok=True)
    target = saves_dir / ("%s.save.json" % pid)
    if mutate is None:
        shutil.copy2(seed, target)
    else:
        mutate(document)
        with open(target, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(document, stream, indent=4)
            stream.write("\n")

    return {
        "corpus": str(destination),
        "pid": pid,
        "seed": str(seed),
        "seed_sha256": sha256_file(seed),
        "save_sha256": sha256_file(target),
        "save_bytes_copied_verbatim": mutate is None,
        "copied_dirs": list(CORPUS_COPY_DIRS),
    }


def _file_sha256(path: Path) -> str:
    return sha256_file(path)


class LegacyBoot:
    """Initialized legacy state plus the read-only boot operations."""

    def __init__(self, corpus: Path, previous_cwd: str) -> None:
        self.corpus = corpus
        self.previous_cwd = previous_cwd
        self._sessions = _import("sessions")
        self._config = _import("get_game_config")
        self._player = _import("get_player_info")
        self._engine = _import("engine")
        self._version = _import("version")
        self._command = _import("command")

    # --- legacy constants -------------------------------------------------
    @property
    def game_version(self) -> str:
        return str(self._version.version_name)

    @property
    def version_code(self) -> str:
        return str(self._version.version_code)

    # --- legacy calls -----------------------------------------------------
    def server_time(self) -> int:
        return int(self._engine.timestamp_now())

    def known_user_ids(self) -> List[str]:
        return list(self._sessions.all_saves_userid())

    def session_list(self) -> List[Dict[str, object]]:
        """Legacy ``all_saves_info()`` renamed into the v0 envelope shape."""
        return [
            {
                "id": entry["userid"],
                "name": entry["name"],
                "xp": entry["xp"],
                "level": entry["level"],
            }
            for entry in self._sessions.all_saves_info()
        ]

    def config(self) -> dict:
        """Legacy ``get_game_config()`` payload (live configuration object)."""
        return self._config.get_game_config()

    def player_info(self, user_id: str) -> dict:
        """Legacy ``get_player_info(USERID)`` including its in-memory effects."""
        if user_id not in self.known_user_ids():
            raise LegacyBootError("unknown_user_id", "no save for user id %r" % user_id)
        return self._player.get_player_info(user_id)

    # --- gameplay execution (design D2/D6; godot-building-placement) ------
    def has_item(self, item_id: int) -> bool:
        """Whether the loaded legacy config resolves this item id."""
        return self._config.get_item_from_id(item_id) is not None

    def item_costs(self, item_id: int) -> Optional[str]:
        """Raw config ``costs`` attribute (JSON string), or ``None``."""
        return self._config.get_attribute_from_item_id(item_id, "costs")

    def item_upgrade_to(self, item_id: int) -> Optional[int]:
        """The resolved next tier of ``item_id`` from the committed config.

        Every item carries an ``upgrades_to`` reference, read here exactly as
        ``item_costs`` reads ``costs`` — through the loaded legacy
        configuration, never from a save or a client.  The reference is
        **string-encoded** in the committed config (``"24"``), is coerced to an
        ``int`` here, and ``None`` is returned for every value that means *no
        path*:

        * the attribute is absent from the config (``None`` from legacy's
          ``get_attribute_from_item_id``), or the item id itself is not one the
          config resolves;
        * the ``-1`` / ``0`` sentinels, which the normalized content package
          documents as "none"
          (``packages/game-content/tools/build_items.py``:
          ``RELATION_NONE = (-1, 0)`` at line 66, applied by
          ``validate_relations`` at lines 546-557);
        * a reference that is not an integer at all; and
        * a reference naming an id the config does **not** resolve, checked
          with the same ``has_item`` lookup every other resolution uses.

        Returning ``None`` rather than raising is deliberate and fail-closed:
        the upgrade endpoint turns it into a structured ``no_upgrade_path``
        error **before** the legacy dispatcher runs, so a building that cannot
        be upgraded is never reduced to a bare sale.
        """
        try:
            raw = self._config.get_attribute_from_item_id(item_id, "upgrades_to")
        except (TypeError, ValueError, KeyError, IndexError):
            # An id the loaded config cannot even index is simply no path.
            return None
        if raw is None:
            return None
        try:
            reference = int(str(raw).strip())
        except (TypeError, ValueError):
            return None
        if reference in RELATION_NONE:
            return None
        if not self.has_item(reference):
            return None
        return reference

    def item_build_time(self, item_id: int) -> Optional[int]:
        """The item's committed construction duration, or ``None``.

        The construction deliver line's content accessor, read exactly as
        ``item_costs`` reads ``costs`` and ``item_upgrade_to`` reads
        ``upgrades_to`` — through the loaded legacy configuration, never from a
        save or a client.  The committed ``build_time`` is **string-encoded**
        (``"5"`` for the Turret I and the Command Center, ``"1"`` for the
        walls, ``"600"`` for the Turret II, ``"3600"`` for the Command Center
        II, ``"180"`` for the map decorations), is coerced to a positive
        ``int`` here, and ``None`` is returned for every value that cannot be a
        build duration:

        * the attribute is absent from the config, or the item id itself is one
          the config cannot index (the ``get_attribute_from_item_id`` lookup
          raises, which is caught exactly as ``item_upgrade_to`` catches it);
        * the value is not an integer at all; and
        * the value is **zero or negative** — which matters beyond tidiness,
          because a non-positive duration sent to legacy's ``activate`` clears
          the addressed row's *whole* attribute bag (``command.py:425-427``),
          destroying the click counter and any friend-assist entries.

        Returning ``None`` rather than raising is deliberate and fail-closed:
        the construction endpoint turns it into a structured ``no_build_time``
        error **before** the legacy dispatcher runs, so an unbuildable row is
        never handed a coerced duration — and never a clearing one.
        """
        try:
            raw = self._config.get_attribute_from_item_id(item_id, "build_time")
        except (TypeError, ValueError, KeyError, IndexError):
            # An id the loaded config cannot even index has no build time.
            return None
        if raw is None or isinstance(raw, bool):
            return None
        try:
            seconds = int(str(raw).strip())
        except (TypeError, ValueError):
            return None
        if seconds <= 0:
            return None
        return seconds

    # --- collection income content (godot-building-collect) ---------------
    # Every accessor below reads the loaded legacy configuration exactly as
    # ``item_costs`` reads ``costs`` and ``item_build_time`` reads
    # ``build_time`` — never from a save and never from a client.  The four
    # income fields are **string-encoded** in the committed config
    # (``"20"``, ``"1"``, ``"0"`` for the Tree; ``"w"`` is the one string that
    # is not a number) and the content census over the 778 stored items of
    # ``config/main.json`` records: ``collect`` is ``"0"`` for 727 of them;
    # ``collect_type`` is exactly ``g`` (731), ``w`` (23), ``o`` (11), ``s``
    # (11), ``c`` (2); ``collect_xp`` is ``"0"`` for 419; ``max_collects`` is
    # ``"0"`` for 767 with ``"25"`` (9 items) and ``"100"`` (2 items) for the
    # rest.  The resolution rules below follow that census and refuse anything
    # it does not describe rather than coercing it.

    def _item_string(self, item_id: int, attribute: str) -> Optional[str]:
        """One raw committed item attribute as a trimmed string, or ``None``.

        The shared read for the four income fields: an id the loaded config
        cannot even index (the ``get_attribute_from_item_id`` lookup raises) and
        an absent attribute are both ``None``, exactly as
        ``item_upgrade_to`` and ``item_build_time`` treat them.
        """
        try:
            raw = self._config.get_attribute_from_item_id(item_id, attribute)
        except (TypeError, ValueError, KeyError, IndexError):
            return None
        if raw is None or isinstance(raw, bool):
            return None
        if isinstance(raw, str):
            return raw.strip()
        return str(raw).strip()

    def _item_non_negative_int(self, item_id: int, attribute: str) -> Optional[int]:
        """One committed item attribute as a non-negative ``int``, or ``None``.

        A missing attribute, a non-integer value, and a **negative** value are
        all ``None``: an income field that is negative cannot be a collection
        amount, and never becoming a negative vector entry keeps legacy's
        ``max(…, 0)`` clamp out of this contract's own transactions.  ``0`` is
        a real, resolved value here — unlike ``build_time``, where zero means
        "no duration" — because ``collect "0"`` is the committed content of 727
        items and is what the endpoint turns into a ``no_income`` refusal.
        """
        text = self._item_string(item_id, attribute)
        if text is None or text == "":
            return None
        try:
            value = int(text)
        except (TypeError, ValueError):
            return None
        if value < 0:
            return None
        return value

    def item_collect_amount(self, item_id: int) -> Optional[int]:
        """The item's committed collection amount, or ``None`` if unusable.

        The collect deliver line's content accessor for the payout's magnitude,
        read from the item's ``collect`` field.  ``None`` means the committed
        content cannot describe an amount (absent attribute, an id the config
        does not resolve, a non-integer value, or a negative one) and the
        endpoint fails closed with ``no_income`` **before** the legacy
        dispatcher runs rather than paying zero or a coerced figure.

        A resolved ``0`` is returned as ``0``, never as ``None``: it is the
        committed content of 727 of the 778 stored items and it is exactly the
        "this building produces nothing" case D4/D6 must refuse.
        """
        return self._item_non_negative_int(item_id, "collect")

    def item_collect_type(self, item_id: int) -> Optional[str]:
        """The item's committed collection resource type, or ``None``.

        Read from the item's ``collect_type`` field and returned **verbatim**:
        the mapping onto the vector's slots is the closed
        :data:`collect_envelope.COLLECT_RESOURCE_SLOTS` vocabulary, so this
        accessor deliberately does not validate, upper-case, or coerce.  Only an
        absent attribute or an id the config cannot index yields ``None``; a
        value outside the committed five reaches the derivation, which fails
        closed with ``unknown_collect_type`` (design D6).
        """
        text = self._item_string(item_id, "collect_type")
        if text is None or text == "":
            return None
        return text

    def item_collect_xp(self, item_id: int) -> Optional[int]:
        """The item's committed collection experience, or ``None`` if unusable.

        Read from the item's ``collect_xp`` field, non-negative like
        :meth:`item_collect_amount`, and scaled by the **same** committed ladder
        rung as the amount (design D2 — a flat ``collect_xp`` is the rejected
        alternative, recorded as derived-provisional).  A resolved ``0`` is a
        real value: it is the committed content of 419 of the 778 stored items,
        and a building pays resource income with no experience at all.
        """
        return self._item_non_negative_int(item_id, "collect_xp")

    def item_max_collects(self, item_id: int) -> Optional[int]:
        """The item's committed collection cap, or ``None`` if unusable.

        Read from the item's ``max_collects`` field, non-negative like the two
        income accessors.  **A non-zero value is refused, never interpreted**
        (design D4): the committed census is ``"0"`` for 767 of the 778 stored
        items with ``"25"`` (9 items) and ``"100"`` (2 items) for the rest, and
        nothing in the repository says whether a non-zero cap limits one
        collection, a daily total, or a building's lifetime output — the three
        readings imply different payouts.  The endpoint therefore answers
        ``capped_collection`` (409) for such an item, so the ambiguity can never
        be resolved by guessing.  ``None`` (absent or unusable) is answered the
        same way rather than treated as "no cap".
        """
        return self._item_non_negative_int(item_id, "max_collects")

    def collect_ladder(self) -> Optional[Tuple[Tuple[int, ...], Tuple[float, ...]]]:
        """The committed collection ladder, or ``None`` if it does not resolve.

        Read from the loaded configuration's ``globals``:
        ``COLLECT_MINUTES = [5, 60, 240, 480]`` and the parallel
        ``COLLECT_MULTIPLIER = [0.25, 1, 2, 3]``.  The pair is validated and
        normalized by :func:`collect_envelope.collect_ladder`, which refuses an
        empty, mismatched, non-monotonic, or non-positive ladder with
        ``no_tier``; that refusal is mapped to ``None`` here so a caller
        fails closed at the endpoint boundary instead of importing the
        derivation's error type into the adapter.
        """
        globals_object = self._config.get_game_config().get("globals")
        if not isinstance(globals_object, dict):
            return None
        pair = (globals_object.get("COLLECT_MINUTES"), globals_object.get("COLLECT_MULTIPLIER"))
        try:
            return collect_envelope.collect_ladder(pair)
        except collect_envelope.EnvelopeError:
            return None

    # --- town expansion content (godot-building-expand) -------------------
    # The three accessors below read the loaded legacy configuration and the
    # loaded save exactly as ``item_costs`` reads ``costs`` and ``collect_ladder``
    # reads the ladder globals — never from a client.  The committed expansion
    # content census (``docs/game-content/census.md`` and
    # ``docs/game-content/field-types.md``, and the committed normalization
    # package's economy section) records **98** ``expansion_prices`` entries with
    # **no stable id** — the id space is the positional index, and all four
    # fields are fully native numbers: ``coins``, ``cash``, ``neighbors``, and
    # ``inventory_qte`` on every stored row, with indexes ``0..3`` all zero
    # (the free expansions), index ``4`` at ``2500 / 5 / 1 / 1``, index ``5`` at
    # ``5000 / 8 / 2 / 2``, and per-field saturation at ``coins`` index ``14``,
    # ``cash`` index ``11``, ``neighbors`` index ``18``, and ``inventory_qte``
    # index ``33`` — so the whole row equals ``100000 / 20 / 15 / 30`` from
    # index ``33`` to ``97`` and is unchanged in between.  ``town_prices`` and
    # ``map_prices`` are
    # separate four-entry schedules (levels ``15 / 25 / 35 / 45``) and are
    # deliberately never used by this line: the corpus's own
    # ``[35, 36, 45, 46]`` is a valid index into the 98-entry schedule and is
    # neither a valid four-entry index nor a level set (36 and 46 are not
    # levels).  The rules below follow that census and refuse anything it does
    # not describe rather than coercing it.

    def expansion_price_count(self) -> Optional[int]:
        """The committed expansion schedule's length, or ``None`` if unusable.

        The **id space** of design D1 is exactly ``0 <= expansion_id <
        this value`` against the loaded configuration's ``expansion_prices``
        list, so the length is the one number every range decision needs and
        it lives here rather than being re-derived by each caller.  The
        committed value is ``98``.

        ``None`` is returned for a configuration whose ``expansion_prices`` is
        not a non-empty sequence of rows — a content-side problem, never client
        input — and the endpoint fails closed with ``internal_error`` on it
        rather than pricing against a schedule it could not read.
        """
        schedule = self._config.get_game_config().get("expansion_prices")
        return expand_envelope.schedule_length(schedule)

    def expansion_price(self, expansion_id: Any) -> Optional[Any]:
        """The committed price row for ``expansion_id``, verbatim, or ``None``.

        Design **D1**: the id indexes the positional ``expansion_prices``
        schedule, and the corpus's own ``[35, 36, 45, 46]`` is only valid under
        that reading.  ``None`` therefore means exactly **"the committed
        schedule has no row for this id"**, and the endpoint turns it into the
        structured ``unknown_expansion_id`` conflict.  That refusal is
        load-bearing rather than defensive: the legacy server does **no** range
        check, so an executed-legacy probe had ``expand(999)`` answer
        ``{"result":"success"}``.

        A non-integer id, a ``bool`` (an ``int`` in Python, so it would index
        the list as ``1``), a **negative** id (which Python would resolve from
        the end of the list), and an out-of-range one are all ``None`` here,
        and the endpoint's own ``invalid_expansion_id`` structural check
        answers first for the non-integer case — the endpoint never lets a
        non-integer reach the dispatcher, where legacy's ``int("abc")`` would
        raise out of the branch and answer an unhandled HTTP 500.

        The row is returned **verbatim** as a shallow **copy** and never
        coerced, defaulted, or filtered, exactly as :meth:`item_collect_type`
        returns its committed string; the copy is what keeps a caller that
        mutates the returned mapping from reaching the loaded legacy
        configuration.  A row that is not a mapping reaches the derivation,
        which refuses it with ``invalid_price`` — the real committed schedule
        has all 98 rows as mappings, so that path is only reachable against a
        configuration drift, and failing closed is the honest response to one.
        """
        schedule = self._config.get_game_config().get("expansion_prices")
        size = expand_envelope.schedule_length(schedule)
        if size is None:
            return None
        # ``is_strict_int`` excludes ``bool`` (which is an ``int`` in Python and
        # would index the list as ``1``), and the explicit bounds check
        # excludes a **negative** index, which Python would resolve from the
        # end of the list.  Both would otherwise be a silently wrong price row
        # rather than a refusal.
        if not expand_envelope.is_strict_int(expansion_id):
            return None
        if expansion_id < 0 or expansion_id >= size:
            return None
        row = schedule[expansion_id]  # type: ignore[index]
        # A **copy**, so a caller mutating the returned mapping can never reach
        # the loaded legacy configuration, and so two reads of the same id
        # return equal but independent mappings.
        if isinstance(row, dict):
            return dict(row)
        return row

    def map_expansions(self, user_id: str) -> List[Any]:
        """``save["maps"][0]["expansions"]`` — the owned-expansions ledger.

        Legacy ``command.expand`` appends to this list in place
        (``map["expansions"] += [int(expansion)]``, ``command.py:214``), so the
        accessor returns a **copy**: the endpoint reads the pre-execution list
        for its range/duplicate checks and its first post-execution proof half,
        and a list returned by reference would alias the live list and report
        the after-state as the before-state — exactly the aliasing the collect
        endpoint avoids with its row copy.

        A map with no ``expansions`` list is a state this service cannot reason
        about, so it raises ``LegacyBootError("invalid_save_state")`` rather
        than inventing an empty ledger.  Entries are **never** rewritten,
        normalized, reordered, or deduplicated here: the committed corpus's own
        ids are recorded as incoherent under the chosen schedule and the
        endpoint must tolerate them exactly as they are.
        """
        expansions = self.first_map(user_id).get("expansions")
        if not isinstance(expansions, list):
            raise LegacyBootError(
                "invalid_save_state",
                "first map of save for user id %r has no expansions list" % user_id,
            )
        return list(expansions)

    def map_level(self, user_id: str) -> Optional[int]:
        """``save["maps"][0]["level"]`` — the **recorded** level, or ``None``.

        Design **D2**: the recorded level is *unverified* against the committed
        curve.  ``command.level_up`` writes it straight from a client-supplied
        integer with no range check and no experience validation
        (``command.py:81-85``), so it is evidence of what a client once asked
        for and of nothing else.  The accessor's only job is to report it
        faithfully so the endpoint can compare it with the level the committed
        curve derives and **report** any disagreement rather than prefer one
        value silently.

        ``None`` is returned for an absent or non-integer level, exactly as the
        other delivered accessors report absent or unusable content: a level
        this service cannot read as an integer is never coerced into one, and
        the endpoint fails closed with ``internal_error`` rather than inventing
        a starting point for its comparison.  A ``bool`` is excluded because it
        is an ``int`` in Python.
        """
        value = self.first_map(user_id).get("level")
        if not level_envelope.is_strict_int(value):
            return None
        return int(value)

    # --- level curve content (godot-building-xp) --------------------------
    # The two accessors below read the loaded legacy configuration's committed
    # ``levels`` curve exactly as ``expansion_price_count`` reads
    # ``expansion_prices`` and ``collect_ladder`` reads the ladder globals —
    # never from a client.  Nothing in the legacy server reads this curve at all
    # (zero references across ``command.py``, ``engine.py``, ``sessions.py``,
    # ``server.py``, and ``constants.py``): the level model is content the
    # client owns, which is precisely why the endpoint's target level is derived
    # here instead.  The committed census (``docs/game-content/census.md``,
    # ``docs/game-content/field-types.md``, the committed normalization
    # package's tables extension, and the investigation record
    # ``docs/legacy-xp-basics.md``) records **100** entries with ``legacy_id``
    # as the 0-based positional index, four fully native fields each
    # (``name``, ``exp_required``, ``reward_type``, ``reward_amount``), an
    # ``exp_required`` ladder that is **strictly increasing** from ``0`` to
    # ``2016089205`` with no duplicate and no non-positive gap
    # (``0, 40, 60, 100, 200, 350, 550, 800, …``), a ``name`` that is **not**
    # distinct (44 names across 100 entries, so it is a label and not an
    # identifier), and ``reward_type`` / ``reward_amount`` that **nothing
    # consumes**.  Design D1's one-based conversion is applied by the envelope
    # module's single named function, never here.

    def level_entry_count(self) -> Optional[int]:
        """The committed level curve's length, or ``None`` if unusable.

        The **level space** of design D1 is exactly ``1 <= level <= this
        value``, so the length is the one number every range decision needs and
        it lives here rather than being re-derived by each caller.  The
        committed value is ``100``.

        ``None`` is returned for a configuration whose ``levels`` is not a
        non-empty sequence of entries — a content-side problem, never client
        input — and the endpoint fails closed with ``internal_error`` on it
        rather than deriving a level from a curve it could not read.
        """
        return level_envelope.schedule_length(self._config.get_game_config().get("levels"))

    def level_entry(self, position: Any) -> Optional[Any]:
        """The committed level-curve entry at a **0-based** position, or ``None``.

        The positional twin of :meth:`level_entry_count`, mirroring
        :meth:`expansion_price`'s "``None`` means the committed table has no row
        here" contract.  ``position`` is the schedule's own index and carries no
        level semantics at all: the level/entry conversion is
        :func:`level_envelope.entry_index_for_level`, one named function, and
        this accessor deliberately performs none.

        A non-integer position, a ``bool`` (an ``int`` in Python, so it would
        read the first entry), a **negative** position (which Python would
        resolve from the end of the list), and an out-of-range one are all
        ``None`` here — each would otherwise be a silently wrong entry rather
        than a refusal.

        The entry is returned **verbatim** as a shallow **copy** and never
        coerced, defaulted, or filtered: the commitment to preserve
        ``exp_required`` exactly as committed is structural, and the copy is
        what keeps a caller that mutates the returned mapping from reaching the
        loaded legacy configuration.
        """
        entries = self._config.get_game_config().get("levels")
        size = level_envelope.schedule_length(entries)
        if size is None:
            return None
        if not level_envelope.is_strict_int(position):
            return None
        if position < 0 or position >= size:
            return None
        row = entries[position]  # type: ignore[index]
        if isinstance(row, dict):
            return dict(row)
        return row

    def save_document(self, user_id: str) -> dict:
        """The in-memory save document for ``user_id`` (legacy ``session()``)."""
        if user_id not in self.known_user_ids():
            raise LegacyBootError("unknown_user_id", "no save for user id %r" % user_id)
        save = self._sessions.session(user_id)
        if not isinstance(save, dict):
            raise LegacyBootError(
                "invalid_save_state", "save for user id %r is not a document" % user_id
            )
        return save

    def first_map(self, user_id: str) -> dict:
        """``save["maps"][0]`` with its structural preconditions checked."""
        save = self.save_document(user_id)
        maps = save.get("maps")
        if not isinstance(maps, list) or not maps or not isinstance(maps[0], dict):
            raise LegacyBootError(
                "invalid_save_state", "save for user id %r has no first map" % user_id
            )
        return maps[0]

    def map_items(self, user_id: str) -> Dict[str, object]:
        """``save["maps"][0]["items"]`` — the slot allocation state."""
        items = self.first_map(user_id).get("items")
        if not isinstance(items, dict):
            raise LegacyBootError(
                "invalid_save_state",
                "first map of save for user id %r has no items" % user_id,
            )
        return items

    def has_map_item(self, user_id: str, index: int) -> bool:
        """Whether ``map["items"][str(index)]`` names a row in this save.

        This is the move deliver line's addressability rule: legacy
        ``engine.map_get_item`` looks the row up by ``str(index)``
        (``engine.py:36-40``) and returns ``None`` for a missing key, after
        which ``command.move`` logs an error and returns early — a silent
        no-op that still persists the save.  The endpoint therefore resolves
        the index against the corpus itself and answers a structured error
        instead of reporting that no-op as success.
        """
        return str(index) in self.map_items(user_id)

    def map_item(self, user_id: str, index: int) -> object:
        """``map["items"][str(index)]`` — one placement row, or ``None``.

        The row is the eight-field entry legacy writes through
        ``engine.map_add_item`` (``engine.py:31``): ``[item, x, y, timestamp,
        orientation, store, attr, player]``.  It is returned by reference on
        purpose: after ``execute_commands`` the same list object is what the
        legacy dispatcher just persisted, so a read back through this accessor
        is the authoritative post-execution state (exactly as ``map_store``
        does for the purchase superset).
        """
        return self.map_items(user_id).get(str(index))

    def map_store(self, user_id: str) -> Dict[str, object]:
        """``save["maps"][0]["store"]`` — the player's storage mapping.

        Legacy ``engine.add_store_item`` increments
        ``map["store"][str(item_id)]`` (``command.buy_stored_item_cash``), so
        the post-execution storage is read back from the same in-memory save
        the legacy dispatcher just persisted.  Real saves may hold buildings
        and units and may hold quantity ``0``; entries are never filtered here.
        """
        store = self.first_map(user_id).get("store")
        if not isinstance(store, dict):
            raise LegacyBootError(
                "invalid_save_state",
                "first map of save for user id %r has no store" % user_id,
            )
        return store

    def execute_commands(self, user_id: str, envelope: Dict[str, object]) -> None:
        """Run the unchanged legacy ``command()`` batch dispatcher (D2).

        The legacy dispatcher applies each command's resource vector,
        executes the command (``buy`` writes the placement entry through
        ``engine.map_add_item`` and records ``boughtUnits``), and persists
        via ``save_session`` into **this corpus's** ``saves/`` directory —
        never a working-tree save.  The response the legacy HTTP route
        would return (``{"result": "success"}``) is exactly what a
        returning ``command()`` produces, so success here is equivalent.
        """
        self._command.command(user_id, envelope)

    def resources(self, user_id: str) -> Dict[str, int]:
        """Post-application resource values the legacy code maintains.

        Every slot ``engine.apply_resources`` writes: map ``xp`` and the
        four map resources, ``playerInfo.cash``, ``privateState.mana``
        (the vector's unread ``unknown`` slot 0 has no stored value).
        """
        save = self.save_document(user_id)
        first_map = self.first_map(user_id)
        return {
            "xp": int(first_map["xp"]),
            "gold": int(first_map["gold"]),
            "wood": int(first_map["wood"]),
            "oil": int(first_map["oil"]),
            "steel": int(first_map["steel"]),
            "cash": int(save["playerInfo"]["cash"]),
            "mana": int(save["privateState"]["mana"]),
        }

    # --- state / containment helpers -------------------------------------
    def reload_state(self) -> None:
        """Re-run the three ``server.py`` loaders (as login does per request)."""
        self._sessions.load_saves()
        self._sessions.load_static_villages()
        self._sessions.load_quests()

    def save_records(self) -> List[Dict[str, object]]:
        """SHA-256 of every file in this corpus's saves directory."""
        saves_dir = self.corpus / "saves"
        if not saves_dir.is_dir():
            raise LegacyBootError("corpus_layout", "corpus has no saves directory")
        return [
            {"path": path, "sha256": digest}
            for path, digest in directory_entries(saves_dir, "saves")
        ]


def _import(name: str):
    try:
        return __import__(name)
    except ImportError as error:
        raise LegacyBootError(
            "legacy_import",
            "legacy module %r could not be imported from the repository root: %s"
            % (name, error),
        )


def initialize(corpus: Path, repo_root: Path = REPO_ROOT) -> LegacyBoot:
    """Chdir into ``corpus`` and initialize legacy state like ``server.py``.

    Re-initializing is allowed (later corpora reload saves/villages/quests
    exactly as ``server.py`` re-runs ``load_saves()`` on every login) but the
    already-loaded configuration is only valid for a byte-identical
    ``config/main.json``.
    """
    corpus_path = Path(corpus).resolve()
    problems = corpus_layout_problems(corpus_path)
    if problems:
        raise LegacyBootError(
            "corpus_layout",
            "corpus %s is missing: %s" % (corpus_path, ", ".join(problems)),
        )

    repo_config = Path(repo_root) / "config" / "main.json"
    corpus_config = corpus_path / "config" / "main.json"
    if not repo_config.is_file():
        raise LegacyBootError("source_missing", "legacy config missing: %s" % repo_config)
    if sha256_file(repo_config) != sha256_file(corpus_config):
        raise LegacyBootError(
            "config_mismatch",
            "corpus config/main.json differs from the legacy config; the legacy "
            "configuration is read once at import",
        )

    previous_cwd = os.getcwd()
    os.chdir(str(corpus_path))

    repo_text = str(Path(repo_root).resolve())
    if repo_text not in sys.path:
        sys.path.insert(0, repo_text)

    # server.py import order: get_game_config, get_player_info, sessions.
    _import("get_game_config")
    _import("get_player_info")
    sessions = _import("sessions")

    boot = LegacyBoot(corpus_path, previous_cwd)
    # server.py init order: load_saves, load_static_villages, load_quests.
    sessions.load_saves()
    sessions.load_static_villages()
    sessions.load_quests()

    _STATE["boot"] = boot
    return boot


def initialized() -> bool:
    return "boot" in _STATE


def current() -> LegacyBoot:
    boot = _STATE.get("boot")
    if boot is None:
        raise LegacyBootError(
            "not_initialized",
            "legacy state is not initialized; call initialize(corpus) first",
        )
    assert isinstance(boot, LegacyBoot)
    return boot
