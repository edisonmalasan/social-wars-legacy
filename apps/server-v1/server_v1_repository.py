#!/usr/bin/env python3
"""The repository seam: the only way Server v1 touches a save document.

**Design D5** puts a seam between the domain and storage so that M14's
PostgreSQL is a substitution rather than a rewrite.  This module is that seam:
a :class:`SaveRepository` protocol the domain depends on, a
:class:`FilesystemSaveRepository` implementation over the committed save
document shape, and a :class:`SaveDocument` view that names the seven stored
resources and the placement rows v1 owns.

Three properties this module is responsible for, and the tests that hold them:

**Unknown fields survive (task 3.2).**  A document is read as parsed JSON and
written back from the same parsed structure; nothing is rebuilt from a model,
nothing is filtered, and nothing is normalised.  A field v1 does not model is
therefore not merely preserved but *unreachable* to be dropped: there is no
code path that reconstructs a document from known keys.  ``AGENTS.md``'s
``legacy_extra`` discipline is satisfied by construction here rather than by
convention, because there is no ``legacy_extra`` bucket — v1 has no idea which
fields it does not model.

**Decide before mutate (spec: "A refused action moves nothing").**  The
repository offers an explicit :meth:`SaveRepository.write`; a caller that
refused must simply not call it.  Nothing in this module writes on read, and
nothing caches an in-memory document that a later read would return — every
read goes to disk, so a refusal that skipped the write leaves the file's bytes
exactly as they were.

**A read/write round trip reproduces the document (task 3.1).**  At the
*value* level this is exact.  At the *byte* level it is not, and the divergence
is deliberate and measured rather than discovered later:

* legacy writes with ``json.dump(village, f, indent=4)`` (``sessions.py:253``)
  under ``open(..., 'w')``, which emits CRLF line endings on Windows and **no
  trailing newline**;
* the committed seed ``tests/saves/fresh-player.json`` is therefore CRLF with
  no trailing newline;
* v1 writes with ``newline="\\n"``, so LF with no trailing newline.

So a v1 round trip of an untouched document is byte-identical to v1's *own*
previous write and value-identical to the seed, but not byte-identical to the
seed.  The write is LF-deterministic on purpose: a save that changes its line
endings depending on the host it was written on is not comparable across hosts,
and determinism is what makes the write-idempotence assertion meaningful.
``tests/test_repository.py`` asserts value equality, write idempotence (a second
write produces identical bytes), and the recorded CRLF->LF normalisation, rather
than claiming a byte identity it does not have.

The seven stored resources are **ESTABLISHED** from ``engine.apply_resources``
(``engine.py:251-271``): the map's ``xp``, ``gold``, ``wood``, ``oil``,
``steel``, ``playerInfo.cash`` and ``privateState.mana``.  That function's
eighth slot is read into a local named ``unknown`` and never written, so it has
no stored value and is deliberately absent from
:data:`STORED_RESOURCE_PATHS`.  The ``max(current + delta, 0)`` clamp is the
behaviour v1 is replacing; no clamp is reproduced here, and this module adds no
floor of its own.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

#: The seven stored resources, named by where they are stored, not by the
#: vector's slot order.  **ESTABLISHED** from ``engine.apply_resources``; see
#: the module docstring.  The names are the save document's own field names, so
#: ``gold`` is ``gold`` and not ``coins`` — a discrepancy the M7 resource-readout
#: line already found and corrected in the Godot client.
STORED_RESOURCE_PATHS: Dict[str, Tuple[str, ...]] = {
    "xp": ("maps", 0, "xp"),
    "gold": ("maps", 0, "gold"),
    "wood": ("maps", 0, "wood"),
    "oil": ("maps", 0, "oil"),
    "steel": ("maps", 0, "steel"),
    "cash": ("playerInfo", "cash"),
    "mana": ("privateState", "mana"),
}

#: Insertion-ordered, so the post-execution proof can walk the resources in a
#: fixed order and produce a deterministic response.
STORED_RESOURCE_NAMES: Tuple[str, ...] = tuple(STORED_RESOURCE_PATHS)

#: Placement rows live at ``maps[0]["items"][str(index)]``.  The **string** key
#: is established: legacy's ``engine.map_get_item`` looks a row up by
#: ``str(index)`` (``engine.py:36-40``), so a row addressed with an integer key
#: is a different row as far as the preserved server is concerned.
ITEMS_PATH: Tuple[str, ...] = ("maps", 0, "items")


class RepositoryError(Exception):
    """A save document this service cannot read or write, with a machine code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@runtime_checkable
class SaveRepository(Protocol):
    """The persistence surface the domain depends on (design D5).

    Deliberately tiny: *list*, *read*, *write*.  A domain that needs a fourth
    operation is telling us the seam is wrong, and M14's job is to implement
    this same three-method protocol over PostgreSQL rather than to widen it here.
    """

    def player_ids(self) -> Tuple[str, ...]:
        """Every save this repository holds, in a stable sorted order."""

    def read(self, player_id: str) -> "SaveDocument":
        """The stored document for ``player_id``, or raise :class:`RepositoryError`."""

    def write(self, document: "SaveDocument") -> None:
        """Persist ``document`` in full, preserving every field it carries."""


class SaveDocument:
    """One save document, with named access to the paths v1 owns.

    Wraps the parsed JSON rather than copying it: v1 reads through this view and
    writes the whole thing back, so a field this view cannot name is still
    written out exactly as it was read.  The wrapper exists to make the seven
    resource paths and the row addressing *named and singular* — not to model
    the document.
    """

    def __init__(self, player_id: str, raw: Dict[str, Any], path: Path) -> None:
        self.player_id = player_id
        self._raw = raw
        self.path = path

    # -------------------------------------------------------------- raw view --
    @property
    def raw(self) -> Dict[str, Any]:
        """The underlying parsed document.

        Exposed for the *preservation* assertions — a test reads a field through
        here to prove v1 did not drop it — not for mutation by domain code.
        Domain code mutates through the named accessors below so that the set of
        paths v1 can change is enumerable from this file.
        """
        return self._raw

    def snapshot(self) -> Dict[str, Any]:
        """A deep, JSON-round-tripped copy of the document.

        Used for before/after comparison inside one request.  ``json.loads(
        json.dumps(...))`` is a *copy*, so a snapshot taken before an execution
        cannot alias the live document and report the after-state as the
        before-state — the aliasing hazard ``LegacyBoot.map_expansions``
        explicitly avoids by copying, and the reason it exists.
        """
        return json.loads(json.dumps(self._raw))

    # --------------------------------------------------------- structural ----
    def first_map(self) -> Dict[str, Any]:
        """``maps[0]``, or :class:`RepositoryError` if the document has none."""
        maps = self._raw.get("maps")
        if not isinstance(maps, list) or not maps or not isinstance(maps[0], dict):
            raise RepositoryError(
                "unreadable_state",
                "save %r has no first map object" % self.player_id,
            )
        return maps[0]

    def items(self) -> Dict[str, Any]:
        """``maps[0]["items"]``, or :class:`RepositoryError`."""
        rows = self.first_map().get("items")
        if not isinstance(rows, dict):
            raise RepositoryError(
                "unreadable_state",
                "save %r has no placements object" % self.player_id,
            )
        return rows

    def row(self, index: int) -> Optional[List[Any]]:
        """The placement row at ``index``, addressed as legacy addresses it.

        ``None`` means "no row at that key", which is the collection slice's
        ``unaddressable_row`` case.  A row that exists but is not a list is a
        different state and raises, because silently treating it as absent would
        let a malformed save look like an empty one.
        """
        value = self.items().get(str(index))
        if value is None:
            return None
        if not isinstance(value, list):
            raise RepositoryError(
                "unreadable_state",
                "save %r row %d is not a placement list" % (self.player_id, index),
            )
        return value

    # ------------------------------------------------------------ resources --
    def resources(self) -> Dict[str, int]:
        """Every stored resource, read by its own path.

        Raises rather than defaulting: a missing or non-integer balance is a
        state this service cannot reason about, and reporting it as ``0`` would
        let a derivation pay into a balance it never read.
        """
        values: Dict[str, int] = {}
        for name in STORED_RESOURCE_NAMES:
            raw = self._resolve(name)
            if isinstance(raw, bool) or not isinstance(raw, int):
                raise RepositoryError(
                    "unreadable_state",
                    "save %r resource %r is not an integer" % (self.player_id, name),
                )
            values[name] = raw
        return values

    def set_resource(self, name: str, value: int) -> None:
        """Write one stored resource, by its own path."""
        if name not in STORED_RESOURCE_PATHS:
            raise RepositoryError(
                "unknown_resource", "no stored resource is named %r" % name
            )
        if isinstance(value, bool) or not isinstance(value, int):
            raise RepositoryError(
                "unreadable_state",
                "refusing to write a non-integer %r value %r" % (name, value),
            )
        self._assign(name, value)

    # ------------------------------------------------------------ row fields --
    #: ``item[3]`` is both a construction start instant (written by ``activate``)
    #: and a last-collection instant (written by ``collect``).  The overlap is
    #: established — ``docs/legacy-construction-timing.md`` and
    #: ``docs/legacy-collect-income.md`` — and is the reason the collection
    #: slice refuses a row that also carries construction state.
    ROW_INSTANT = 3
    ROW_ITEM = 0
    ROW_ATTR = 6
    #: ``item[7]`` is the row's recorded **player team**, and the only field the
    #: preserved dead-hero gate reads (``push_dead_unit``'s ``if item[7] != 1:
    #: return False``, ``engine.py:151``).  The selectors here are truthy tests
    #: of the *same* slot (``map_lose_item``, ``engine.py:221``), which is the
    #: asymmetry the combat slice reports rather than reconciles.
    ROW_TEAM = 7
    #: The keys a construction writes into a row's attribute bag, and the one a
    #: queue start writes.  Presence of any of them means the row is not idle.
    CONSTRUCTION_ATTR_KEYS = ("cp", "nc")

    def row_instant(self, index: int) -> int:
        """``item[3]`` as an integer, or :class:`RepositoryError`."""
        row = self.row(index)
        if row is None:
            raise RepositoryError(
                "unaddressable_row", "save %r has no row %d" % (self.player_id, index)
            )
        return self._row_int(row, self.ROW_INSTANT, "instant")

    def set_row_instant(self, index: int, value: int) -> None:
        """Write ``item[3]``."""
        row = self.row(index)
        if row is None:
            raise RepositoryError(
                "unaddressable_row", "save %r has no row %d" % (self.player_id, index)
            )
        if isinstance(value, bool) or not isinstance(value, int):
            raise RepositoryError(
                "unreadable_state", "refusing to write a non-integer instant %r" % (value,)
            )
        row[self.ROW_INSTANT] = value

    def row_item_id(self, index: int) -> int:
        """``item[0]`` — the item the placed row is — as an integer."""
        row = self.row(index)
        if row is None:
            raise RepositoryError(
                "unaddressable_row", "save %r has no row %d" % (self.player_id, index)
            )
        return self._row_int(row, self.ROW_ITEM, "item id")

    def row_team(self, index: int) -> int:
        """``item[7]`` — the row's recorded player team, as an integer.

        A **reader only**: nothing in the delivered v1 surface writes a team, and
        there is deliberately no ``set_row_team``, because a team is a fact about
        which side a row was placed for rather than a value a transaction derives.

        ``0`` and ``None`` are both unreadable answers here and both raise,
        because ``map_lose_item``'s selector is a **truthy** test
        (``engine.py:221``): a team of ``0`` is a row that helper skips, and
        reporting it as a team the reader understood would invent a placement
        the selector would never have chosen.  The legacy selector's tolerance
        for *any* truthy value, against ``push_dead_unit``'s exact-``1`` test,
        is the asymmetry the combat slice reports; this reader takes neither side.
        """
        row = self.row(index)
        if row is None:
            raise RepositoryError(
                "unaddressable_row", "save %r has no row %d" % (self.player_id, index)
            )
        team = self._row_int(row, self.ROW_TEAM, "team")
        if team == 0:
            raise RepositoryError(
                "unreadable_state",
                "save %r row %d records team 0, which the preserved placement "
                "selector never chooses" % (self.player_id, index),
            )
        return team

    def rows_for_item_id(self, item_id: int) -> Tuple[int, ...]:
        """Every recorded map key whose row carries ``item_id``, in stored order.

        **The scan order is the preserved one.**  ``map_lose_item``
        (``engine.py:218-225``) walks ``map["items"]`` key by key and takes the
        **first** row whose item id matches *and* whose team is truthy, popping it
        and starting the walk again, so a repeated destruction of the same id
        consumes successive matches in recorded order.  This accessor keeps that
        order so a caller reporting which rows exist for an identity is reporting
        the rows the preserved helper would have considered, in the sequence it
        would have consumed them.

        It is a **reader**: it returns keys, removes nothing, and hands out no
        row object.  The combat slice uses it to report whether the addressed
        identity has a row at all, which is a report rather than a selection --
        the addressed identity names a **committed item id**, and the preserved
        branch's own subject is the per-tuple ``unit[0]`` (``command.py:870``),
        not a map key.
        """
        if isinstance(item_id, bool) or not isinstance(item_id, int):
            return ()
        keys: List[int] = []
        for key, row in self.items().items():
            if not isinstance(row, list) or len(row) <= self.ROW_ITEM:
                raise RepositoryError(
                    "unreadable_state",
                    "save %r row %r is not a readable placement row"
                    % (self.player_id, key),
                )
            value = row[self.ROW_ITEM]
            if isinstance(value, bool) or not isinstance(value, int):
                raise RepositoryError(
                    "unreadable_state",
                    "save %r row %r does not record an integer item id"
                    % (self.player_id, key),
                )
            if int(value) == item_id:
                keys.append(int(key))
        return tuple(keys)

    def row_attr(self, index: int) -> Dict[str, Any]:
        """``item[6]`` — a row's attribute bag, verified to be an object."""
        row = self.row(index)
        if row is None:
            raise RepositoryError(
                "unaddressable_row", "save %r has no row %d" % (self.player_id, index)
            )
        if len(row) <= self.ROW_ATTR:
            raise RepositoryError(
                "unreadable_state",
                "save %r row %d has no attribute bag" % (self.player_id, index),
            )
        bag = row[self.ROW_ATTR]
        if not isinstance(bag, dict):
            raise RepositoryError(
                "unreadable_state",
                "save %r row %d attribute bag is not an object" % (self.player_id, index),
            )
        return bag

    def row_is_under_construction(self, index: int) -> bool:
        """Whether the row's attribute bag carries construction state.

        ``nc`` is the construction click counter, seeded to ``0`` by
        ``engine`` from the item's ``clicks_to_build`` and incremented by the
        build-click command; ``cp`` is a speedup or duration the construction
        line writes.  Both are **presence** signals, not value signals: a row
        whose bag carries ``nc: 0`` is still a row a construction command has
        touched, and treating "zero" as "idle" would be exactly the string-flag
        hazard ``godot-unit-movement`` measured (``"0"`` is truthy as a string in
        GDScript) in the other direction.
        """
        bag = self.row_attr(index)
        return any(key in bag for key in self.CONSTRUCTION_ATTR_KEYS)

    # ------------------------------------------------- storage and ledger --
    #: ``maps[0]["store"]``: the item-id -> quantity map a **stored** item rides.
    #: This is where ``place_stored_item`` reads from and ``store_item`` writes
    #: to (``command.py:233-256``), and it is where a collections **prize** is
    #: granted.  Keyed by string, because JSON object keys are strings and the
    #: legacy branch itself writes ``store[itemstr] = qty`` after ``str(item)``.
    STORAGE_PATH: Tuple[str, ...] = ("maps", 0, "store")
    #: ``privateState["collections"]``: the collection ledger.  A list of
    #: collection ids, appended by ``complete_collection`` at
    #: ``command.py:517-518``.
    LEDGER_PATH: Tuple[str, ...] = ("privateState", "collections")

    def private_state(self) -> Dict[str, Any]:
        """``privateState``, or :class:`RepositoryError`.

        Structural, like :meth:`first_map`: the ledger lives here and the
        ``si`` assist list does too, so a document with no ``privateState``
        object is a document v1 cannot reason about rather than an empty one.
        """
        state = self._raw.get("privateState")
        if not isinstance(state, dict):
            raise RepositoryError(
                "unreadable_state",
                "save %r has no privateState object" % self.player_id,
            )
        return state

    def storage(self) -> Dict[str, Any]:
        """``maps[0]["store"]`` as a **snapshot copy**, or :class:`RepositoryError`.

        A **missing** store key is refused rather than defaulted to ``{}``: the
        corpus records an empty ``store`` object, so an absent one means a
        document whose shape v1 does not know.

        **This returns a copy, and that is load-bearing rather than
        defensive.**  The first version returned the live nested object — the
        same choice :meth:`items` makes — and the collection slice's
        post-execution proof then compared the store **against itself**: it read
        the "before" snapshot, then granted, then re-read, and the quantity
        half compared a mutated dict against itself and reported a movement of
        ``0`` on a successful grant.  It was caught by
        ``tests/test_collection.py`` failing every success case with
        ``storage_granted_quantity``, not by inspection.  A live read is safe
        only for a caller that never compares across a write; the grant slice is
        exactly such a caller, so the default is the copy and
        :meth:`_storage_node` is the private live path for the one writer.
        """
        return dict(self._storage_node())

    def _storage_node(self) -> Dict[str, Any]:
        """The **live** ``maps[0]["store"]`` object, or :class:`RepositoryError`.

        Private because a caller holding it can mutate the document without
        going through :meth:`set_storage_quantity`, which is the only reason
        the set of paths v1 can change stays enumerable from this file.
        """
        node: Any = self._raw
        for step in self.STORAGE_PATH:
            try:
                node = node[step]
            except (KeyError, IndexError, TypeError):
                raise RepositoryError(
                    "unreadable_state",
                    "save %r has no store object at /%s"
                    % (self.player_id, "/".join(str(s) for s in self.STORAGE_PATH)),
                )
        if not isinstance(node, dict):
            raise RepositoryError(
                "unreadable_state",
                "save %r store is not an object" % self.player_id,
            )
        return node

    def storage_quantity(self, item_id: int) -> int:
        """How many of ``item_id`` the player holds, or ``0`` when absent.

        Raises rather than coercing when a recorded quantity is not an integer:
        a string ``"1"`` is a state this service cannot reason about, and
        reading it as ``1`` would let a grant proceed on a shape the store does
        not actually have.
        """
        raw = self.storage().get(str(item_id), 0)
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise RepositoryError(
                "unreadable_state",
                "save %r store quantity for item %d is not an integer: %r"
                % (self.player_id, item_id, raw),
            )
        return int(raw)

    def set_storage_quantity(self, item_id: int, value: int) -> None:
        """Write the held quantity for one item id, keyed as JSON keys it.

        Assigning to an **existing** key keeps its position, and a new key is
        appended, which is what the preserved branch does too: it mutates a
        dict loaded from the file and serialises that same dict
        (``command.py:517``), so a grant that adds a key appends it.
        """
        if isinstance(value, bool) or not isinstance(value, int):
            raise RepositoryError(
                "unreadable_state",
                "refusing to write a non-integer storage quantity %r" % (value,)
            )
        if value < 0:
            raise RepositoryError(
                "unreadable_state",
                "refusing to write a negative storage quantity %r" % (value,),
            )
        self._storage_node()[str(item_id)] = value

    def ledger(self) -> List[int]:
        """The recorded collection ledger, in stored order.

        An **absent** key reads as an empty ledger: "nothing claimed yet" is
        the only honest reading of a document that never recorded a claim, and
        refusing it would make the first-ever claim refusable.  A key that
        exists but is not a list of integers is refused instead, because a
        malformed ledger means v1 cannot tell what has already been claimed,
        and that is exactly the question the once-only rule turns on.
        """
        raw = self.private_state().get("collections", [])
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise RepositoryError(
                "unreadable_state",
                "save %r collection ledger is not a list" % self.player_id,
            )
        claimed: List[int] = []
        for entry in raw:
            if isinstance(entry, bool) or not isinstance(entry, int):
                raise RepositoryError(
                    "unreadable_state",
                    "save %r collection ledger entry %r is not an integer"
                    % (self.player_id, entry),
                )
            claimed.append(int(entry))
        return claimed

    def set_ledger(self, claimed: Tuple[int, ...]) -> None:
        """Write the collection ledger, creating the key when it was absent.

        Creating it is the closest available equivalent to the preserved
        branch's ``append`` on a document that already carries the key: the
        corpus does carry it (``[]``), so the two agree where the corpus can
        exercise them, and where it does not carry one the recorded meaning is
        still "nothing claimed yet".
        """
        for entry in claimed:
            if isinstance(entry, bool) or not isinstance(entry, int):
                raise RepositoryError(
                    "unreadable_state",
                    "refusing to write a non-integer ledger entry %r" % (entry,)
                )
        self.private_state()["collections"] = [int(entry) for entry in claimed]

    # ----------------------------------------------------------- magic ledger --
    #: Where the magic counter map lives, named as a tuple for the same reason
    #: :data:`LEDGER_PATH` is one.
    MAGIC_LEDGER_PATH: Tuple[str, ...] = ("privateState", "magics")

    def magic_ledger(self) -> Dict[str, Any]:
        """``privateState["magics"]``, verbatim, or :class:`RepositoryError`.

        **An absent key is refused rather than read as empty**, and that is the
        opposite of :meth:`ledger`'s absent-key rule on purpose, with two
        measured reasons between them.

        An absent **collection** ledger honestly means "nothing claimed yet",
        because the claim is the thing being recorded.  An absent **magic**
        ledger instead means a document whose shape v1 cannot read: the
        preserved server's own migration (``version.py:32-37``) coerces an
        absent or non-dict ``magics`` into ``{}`` **before** any branch runs, so
        a document reaching a branch with no ``magics`` object is not a shape
        the legacy pipeline produces at all.  Refusing keeps v1 from answering
        "your counter is zero" about a state the server never recorded.

        A non-dict value is refused for the same reason, and for a second one:
        ``int`` on a list or a string would either raise deep inside the slice
        or coerce something the document never meant.

        **This refusal is unreachable through the committed corpus**: all **33**
        save documents already carry a dict ``magics``, exactly because the
        migration ran on each of them.  It is exercised over an in-memory row
        instead, which is the pattern ``no_build_time`` used on line 1.
        """
        raw = self.private_state().get("magics")
        if not isinstance(raw, dict):
            raise RepositoryError(
                "unreadable_state",
                "save %r has no magic ledger object at /%s"
                % (
                    self.player_id,
                    "/".join(str(step) for step in self.MAGIC_LEDGER_PATH),
                ),
            )
        return raw

    def magic_counter(self, magic_id: int) -> int:
        """The recorded counter for one magic id, or ``0`` when absent.

        Keyed as ``str(magic_id)``, which is the preserved branches' own key
        form (``str(magic_id)`` at ``command.py:659`` and ``:671``) and coincides
        with the committed id space because v1 validates the identity against
        the committed ``id`` column first (design D3).  The preserved server
        never validates it, which is why the executed fixture recorded a float
        identity producing a **distinct** key ``"1.0"``; v1 refuses that request
        as ``malformed_request`` at the intent layer instead of growing a second
        key space.

        An absent entry reads as **zero** rather than being refused: the derived
        transition needs a prior value, and "no recorded counter" has exactly
        one honest reading.  A recorded value that is not an integer **is**
        refused, for the same reason :meth:`storage_quantity` refuses one.

        **Membership, not ``.get()``, and the difference is measurable.**  A
        first version read ``self.magic_ledger().get(str(magic_id))`` and treated
        a returned ``None`` as absence, which made a ledger entry recorded as
        ``{"1": null}`` read as zero and then be **overwritten** by the derived
        value -- a destruction of a recorded-but-unreadable entry that the
        docstring above says must be refused.  ``{"1": null}`` is a recorded
        entry whose value is not an integer, not an absent key, and only a
        membership test can tell the two apart.
        """
        ledger = self.magic_ledger()
        key = str(magic_id)
        if key not in ledger:
            return 0
        raw = ledger[key]
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise RepositoryError(
                "unreadable_state",
                "save %r magic counter %r is not an integer"
                % (self.player_id, raw),
            )
        return int(raw)

    def set_magic_counter(self, magic_id: int, value: int) -> None:
        """Write the counter for one magic id, creating the key when absent.

        Creating it is the closest available equivalent to the preserved
        branch's ``else`` arm, and the two differ in a way this method cannot
        reproduce: the branch writes **zero** for an identity with no recorded
        entry, so its "acquire a spell you hold none of" path increments
        nothing.  v1 writes the value it derived.  That is recorded as a
        divergence in the response payload, never as parity.
        """
        if isinstance(value, bool) or not isinstance(value, int):
            raise RepositoryError(
                "unreadable_state",
                "refusing to write a non-integer magic counter %r" % (value,),
            )
        if value < 0:
            raise RepositoryError(
                "unreadable_state",
                "refusing to write a negative magic counter %r" % (value,),
            )
        self.magic_ledger()[str(magic_id)] = int(value)

    # ---------------------------------------------------------------- helpers --
    def _row_int(self, row: List[Any], position: int, label: str) -> int:
        if len(row) <= position:
            raise RepositoryError(
                "unreadable_state",
                "save %r row is shorter than %d fields" % (self.player_id, position + 1),
            )
        value = row[position]
        if isinstance(value, bool) or not isinstance(value, int):
            raise RepositoryError(
                "unreadable_state",
                "save %r row %s is not an integer" % (self.player_id, label),
            )
        return int(value)

    def _resolve(self, name: str) -> Any:
        node: Any = self._raw
        for step in STORED_RESOURCE_PATHS[name]:
            try:
                node = node[step]
            except (KeyError, IndexError, TypeError):
                raise RepositoryError(
                    "unreadable_state",
                    "save %r has no %r resource at /%s"
                    % (self.player_id, name, "/".join(str(s) for s in STORED_RESOURCE_PATHS[name])),
                )
        return node

    def _assign(self, name: str, value: int) -> None:
        path = STORED_RESOURCE_PATHS[name]
        node: Any = self._raw
        for step in path[:-1]:
            node = node[step]
        node[path[-1]] = value


class FilesystemSaveRepository:
    """A repository over ``<root>/saves/<player_id>.save.json``.

    ``root`` is the **corpus**, named explicitly; nothing here resolves a path
    from the process working directory.  That is what makes the containment
    assertion possible: a test can hand this repository a disposable directory,
    assert the bytes that directory holds afterwards, and assert the working
    tree is untouched — where a working-directory-relative repository would
    make "untouched" unprovable.

    The filename convention is legacy's (``sessions.save_session``,
    ``sessions.py:250``): ``"{USERID}.save.json"``.
    """

    #: Name legacy gives a save file.  ``USERID`` is the value the client sends,
    #: which for the committed corpus is the ``playerInfo.pid`` string.
    FILE_SUFFIX = ".save.json"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._saves = self.root / "saves"

    def saves_dir(self) -> Path:
        """The directory this repository reads and writes, for containment."""
        return self._saves

    def player_ids(self) -> Tuple[str, ...]:
        """Every save in the directory, sorted, with the suffix stripped."""
        if not self._saves.is_dir():
            return ()
        found: List[str] = []
        for entry in self._saves.iterdir():
            if entry.is_file() and entry.name.endswith(self.FILE_SUFFIX):
                found.append(entry.name[: -len(self.FILE_SUFFIX)])
        return tuple(sorted(found))

    def path_for(self, player_id: str) -> Path:
        """The file one player's save lives in.

        ``player_id`` is **not** sanitised into a path by escaping: a value
        containing a path separator or ``..`` would address a file outside the
        saves directory, so this refuses it.  The refused ids are reported by
        name rather than silently mapped, because "no such player" and "that
        player id is not addressable" are different facts and the domain
        answers them differently.
        """
        if not player_id or "/" in player_id or "\\" in player_id:
            raise RepositoryError(
                "unaddressable_player", "player id %r is not addressable" % player_id
            )
        if player_id in (".", "..") or "\x00" in player_id:
            raise RepositoryError(
                "unaddressable_player", "player id %r is not addressable" % player_id
            )
        return self._saves / ("%s%s" % (player_id, self.FILE_SUFFIX))

    def read(self, player_id: str) -> SaveDocument:
        """Read one save, or :class:`RepositoryError`.

        Read fresh every call and never cached: caching would make the
        post-execution proof compare a live object with itself.
        """
        path = self.path_for(player_id)
        if not path.is_file():
            raise RepositoryError(
                "unknown_player", "no save document for player %r" % player_id
            )
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise RepositoryError(
                "unreadable_state", "save %r is unreadable: %s" % (player_id, error)
            )
        if not isinstance(raw, dict):
            raise RepositoryError(
                "unreadable_state", "save %r is not a JSON object" % player_id
            )
        return SaveDocument(player_id, raw, path)

    def write(self, document: SaveDocument) -> None:
        """Write the whole document back, in v1's LF-deterministic form.

        ``indent=4`` matches legacy's; ``newline="\\n"`` is the deliberate
        divergence documented in the module docstring.  No trailing newline,
        also matching legacy.
        """
        path = document.path
        if not path.parent.is_dir():
            raise RepositoryError(
                "unreadable_state", "save directory does not exist: %s" % path.parent
            )
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(document.raw, stream, indent=4)
        except OSError as error:
            raise RepositoryError(
                "unreadable_state", "save %r could not be written: %s"
                % (document.player_id, error)
            )


__all__ = [
    "ITEMS_PATH",
    "LEDGER_PATH",
    "STORED_RESOURCE_NAMES",
    "STORED_RESOURCE_PATHS",
    "STORAGE_PATH",
    "FilesystemSaveRepository",
    "RepositoryError",
    "SaveDocument",
    "SaveRepository",
]
