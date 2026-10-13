#!/usr/bin/env python3
"""Committed-content loading for Server v1, read from an explicit content root.

**v1 loads the same committed content the preserved server loads, and it loads
it itself.**  It imports nothing from ``apps/compat-api`` (design's non-goal:
"no shared code between v0 and v1 domain layers in this line") and nothing
from the legacy root modules either, because a v1 boundary that reached into
the code it is meant to replace would not be a boundary.

What is reproduced from committed legacy source (``get_game_config.py``):

* ``main.json`` is read from ``<content root>/config/main.json``;
* the ordered patch list ``config/patch/patches.txt`` is honoured line by line —
  a blank line and a ``#`` line are skipped, ``.json`` is stripped, a missing
  patch file is reported rather than skipped silently (legacy prints a ``Patch
  ERROR`` and continues), and each patch is applied in place with
  :mod:`jsonpatch`, already pinned by the repository's own requirements;
* ``mods/mods.txt`` is read the same way, so a corpus with a mod enabled loads
  it and a corpus with none (the committed repository: one commented-out
  entry) loads none;
* **duplicate item cleaning keeps the LAST occurrence** of an item id, which is
  what ``get_game_config.remove_duplicate_items`` does — it walks the array
  left to right, and on a repeat deletes the *earlier* entry and restarts.
  Keeping the first instead would be a different rule with the same name;
* the resulting ``items`` array is indexed by ``int(item["id"])`` with last-wins
  assignment, exactly as the module-level ``items_dict_id_to_items_index``
  comprehension does.

One step is deliberately **not** reproduced, and the omission is recorded here
because a silent divergence is what this project records most often:

    ``make_dynamic`` is skipped.

Legacy calls it on every ``get_game_config()``, and it rewrites the
``start_date`` of every ``darts_items`` row so the darts minigame's week wraps
around the present.  v1 has no darts route in this line and no committed
dependence on a rewritten date, so running it would introduce a wall-clock
dependence into content v1 does not read, for no gain.  This is a **narrowing**
of legacy's loader, and it is observable: a ``darts_items`` row's
``start_date`` under v1 is the committed stored value, which is what the
preservation tools (``tools/content-census``) also see, and not the wrapped
value legacy's server hands to a client.

Everything else here is content *reading*, not rule derivation.  The ladder,
the income fields, and their interpretation live in
:mod:`server_v1_economy`; this module's job is to hand over committed values
verbatim and to fail closed on a document it cannot read.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

import jsonpatch

#: Repository-relative locations a content root must provide.
CONFIG_MAIN = ("config", "main.json")
PATCH_LIST = ("config", "patch", "patches.txt")
MOD_LIST = ("mods", "mods.txt")

#: Steps legacy's loader takes that v1 does not, named so a test can assert the
#: omission is real rather than a comment (see the module docstring).
SKIPPED_LOADER_STEPS: Tuple[str, ...] = ("make_dynamic",)


class ContentError(Exception):
    """Committed content this service cannot read, with a stable machine code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class CommittedContent:
    """The loaded committed configuration, with the reads v1 needs.

    Read-only after construction: the one rule is that a caller cannot reach
    the loaded document and mutate it, because ``items`` is indexed once here
    and a mutation from outside would make the index and the array disagree.
    """

    def __init__(
        self,
        document: Mapping[str, Any],
        *,
        applied_patches: Tuple[str, ...],
        applied_mods: Tuple[str, ...],
        missing_patches: Tuple[str, ...],
        missing_mods: Tuple[str, ...],
        removed_duplicate_items: int,
    ) -> None:
        self._document = document
        self._items = document.get("items")
        self._globals = document.get("globals")
        self._collections = document.get("collections")
        self._magics = document.get("magics")
        self.applied_patches = applied_patches
        self.applied_mods = applied_mods
        self.missing_patches = missing_patches
        self.missing_mods = missing_mods
        self.removed_duplicate_items = removed_duplicate_items

        if not isinstance(self._items, list):
            raise ContentError(
                "no_items", "the committed configuration has no items array"
            )
        index: Dict[int, Mapping[str, Any]] = {}
        for entry in self._items:
            if not isinstance(entry, Mapping):
                raise ContentError(
                    "no_items", "the committed items array holds a non-object entry"
                )
            # ``int(item["id"])`` is legacy's own coercion, and last-wins
            # assignment is its dict comprehension's behaviour.
            try:
                key = int(entry["id"])
            except (KeyError, TypeError, ValueError) as error:
                raise ContentError(
                    "no_items", "a committed item has no readable id: %s" % error
                )
            index[key] = entry
        self._by_id = index

    # ------------------------------------------------------------- accessors --
    def item(self, item_id: int) -> Optional[Mapping[str, Any]]:
        """The committed item row for ``item_id``, verbatim, or ``None``."""
        return self._by_id.get(item_id)

    def item_count(self) -> int:
        """The number of entries in the cleaned ``items`` array."""
        return len(self._items)  # type: ignore[arg-type]

    def distinct_item_count(self) -> int:
        """The number of distinct item ids the cleaned array resolves."""
        return len(self._by_id)

    def collect_ladder(self) -> Tuple[Tuple[int, ...], Tuple[float, ...]]:
        """``(COLLECT_MINUTES, COLLECT_MULTIPLIER)`` as validated tuples.

        **ESTABLISHED**: the two globals exist, are committed, and are parallel
        four-element arrays (minutes ``[5, 60, 240, 480]``, multipliers
        ``[0.25, 1, 2, 3]``).  **DERIVED**: what they *mean* — see
        :mod:`server_v1_economy`, which is the only module that reads them.
        """
        if not isinstance(self._globals, Mapping):
            raise ContentError(
                "no_ladder", "the committed configuration has no globals object"
            )
        minutes = _number_tuple(self._globals.get("COLLECT_MINUTES"))
        multipliers = _number_tuple(self._globals.get("COLLECT_MULTIPLIER"))
        if not minutes or len(minutes) != len(multipliers):
            raise ContentError(
                "no_ladder",
                "the committed collection ladder is not a non-empty pair of equal "
                "length: %r / %r" % (list(minutes), list(multipliers)),
            )
        previous: Optional[float] = None
        for value in minutes:
            if value != int(value) or int(value) <= 0:
                raise ContentError(
                    "no_ladder",
                    "a committed ladder threshold is not a positive integer: %r" % (value,),
                )
            if previous is not None and value < previous:
                raise ContentError(
                    "no_ladder",
                    "the committed ladder thresholds are not non-decreasing: %r"
                    % (list(minutes),),
                )
            previous = value
        for value in multipliers:
            if value <= 0:
                raise ContentError(
                    "no_ladder",
                    "a committed ladder multiplier is not positive: %r" % (value,),
                )
        return (
            tuple(int(value) for value in minutes),
            tuple(multipliers),
        )

    def item_rows(self) -> Tuple[Mapping[str, Any], ...]:
        """The cleaned ``items`` array as a tuple, in array order.

        A tuple, not the list: this is the loader-parity comparison's window
        onto the whole array, and handing out the live list would let a caller
        mutate it and leave :attr:`_by_id` disagreeing with it — the exact
        failure this class exists to prevent.  Order is preserved because the
        array order is itself something the two loaders must agree on.
        """
        return tuple(self._items)  # type: ignore[arg-type]

    def globals_object(self) -> Mapping[str, Any]:
        """The loaded ``globals`` object, verbatim, or ``{}`` when absent.

        Present so the loader-parity test can compare the whole object against
        the preserved loader's rather than one named constant at a time: a
        test that checked only ``COLLECT_MINUTES`` would pass while any other
        committed global drifted.
        """
        if not isinstance(self._globals, Mapping):
            return {}
        return self._globals

    def section(self, name: str) -> Any:
        """One loaded top-level section, verbatim, or ``None`` when absent.

        Public for the same reason as :meth:`sections`: the loader-parity test
        compares the two loaders section by section, and reading the document
        through ``_document`` from a test is reaching behind the module that
        owns it.
        """
        return self._document.get(name)

    def sections(self) -> Tuple[str, ...]:
        """The loaded document's top-level keys, in document order.

        Public so the loader-parity test can compare the two loaders' section
        sets without reaching into ``_document``.  Reaching behind the module
        was recorded and rejected on an earlier line
        (``godot-unit-definitions``): the index is private because a mutation
        from outside would make it and the array disagree, and the same
        argument applies to a test reading the document that owns it.
        """
        return tuple(self._document.keys())

    def darts_start_date(self) -> Optional[str]:
        """The **stored** ``darts_items`` week start, or ``None``.

        Stored means exactly what the committed file says, i.e. the value
        *before* legacy's ``make_dynamic`` wraps it around the present.  This
        exists so the one deliberate loader divergence can be asserted as a
        real, located difference rather than excluded silently from an
        equality check — see :data:`SKIPPED_LOADER_STEPS` and the module
        docstring.  It returns ``None`` when the key is absent rather than
        guessing a default date, because an invented date would make the
        comparison below it meaningless.
        """
        rows = self._document.get("darts_items")
        if not isinstance(rows, list) or not rows:
            return None
        first = rows[0]
        if not isinstance(first, Mapping):
            return None
        value = first.get("start_date")
        if value is None or isinstance(value, bool):
            return None
        return str(value).strip()

    def item_attribute(self, item_id: int, name: str) -> Optional[str]:
        """One committed item attribute as a trimmed string, or ``None``.

        The committed income fields are **string-encoded** (``"20"``, ``"1"``,
        ``"0"``; ``"w"`` is the one that is not a number), so this returns the
        stored text and the caller decides whether it parses.  An absent
        attribute and an id the content does not resolve are both ``None``,
        which is deliberately indistinguishable here: both mean "committed
        content does not describe this", and neither is a zero.
        """
        row = self.item(item_id)
        if row is None:
            return None
        if name not in row:
            return None
        raw = row[name]
        if raw is None or isinstance(raw, bool):
            return None
        if isinstance(raw, str):
            return raw.strip()
        return str(raw).strip()

    def item_non_negative_int(self, item_id: int, name: str) -> Optional[int]:
        """One committed item attribute as a non-negative ``int``, or ``None``.

        ``0`` is a real resolved value, not an absence: ``collect "0"`` is the
        committed content of most items and it is precisely the "this row
        produces nothing" case the collection slice must refuse rather than pay.
        """
        text = self.item_attribute(item_id, name)
        if text is None or text == "":
            return None
        try:
            value = int(text)
        except (TypeError, ValueError):
            return None
        if value < 0:
            return None
        return value

    # ------------------------------------------------------- collections table ---
    #: The committed collections section's fields this module reads.  Named as a
    #: tuple so a test can assert the reader covers exactly the four the
    #: repository's own normalization declares, instead of a chosen example.
    COLLECTION_FIELDS: Tuple[str, ...] = ("id", "item_ids", "prize", "cashPrice")

    def collection_rows(self) -> Tuple[Mapping[str, Any], ...]:
        """The committed ``collections`` rows, verbatim, in array order.

        **Verbatim means string-encoded.**  Measured on the committed raw
        configuration, every one of the ten rows stores ``id`` and
        ``cashPrice`` as **strings** and ``item_ids`` and ``prize`` as
        **embedded JSON strings** (``'[66,67,68,69,70]'``,
        ``'{"1085":1}'``).  The readers below decode those encodings; this one
        does not, so a test can compare the loaded bytes against the committed
        normalized package field by field.

        An absent or non-array section yields ``()`` rather than raising, so a
        caller can refuse an unresolvable collection with a *content* reason
        instead of a load failure.  Whether an empty table is acceptable is not
        this module's decision; it reports what it found.
        """
        rows = self._collections
        if not isinstance(rows, list):
            return ()
        return tuple(row for row in rows if isinstance(row, Mapping))

    def collection_row(self, index: int) -> Optional[Mapping[str, Any]]:
        """One committed collections row **by position**, or ``None``.

        Positional, not by id, because that is the addressing the preserved
        branch uses: ``get_collection_prize`` (``get_game_config.py:170-175``)
        computes ``index = max(0, collection - 1)`` and indexes the array.  v1
        keeps the positional index (design D2) and refuses the clamp (design
        D3), but it does not re-address the table by id, because that would be
        a second addressing rule with the same name.
        """
        rows = self.collection_rows()
        if isinstance(index, bool) or not isinstance(index, int):
            return None
        if index < 0 or index >= len(rows):
            return None
        return rows[index]

    def collection_id(self, index: int) -> Optional[int]:
        """A row's committed ``id`` as an ``int``, or ``None``.

        Stored as a **string** on every committed row, so this is a decoding,
        not a conversion.  ``None`` means the field is absent or unreadable,
        which is kept distinct from ``0``: a row whose id will not parse is a
        content defect, and reporting it as id ``0`` would make it address
        collection 1's prize.
        """
        text = self._collection_text(index, "id")
        if text is None or text == "":
            return None
        try:
            return int(text)
        except (TypeError, ValueError):
            return None

    def collection_cash_price(self, index: int) -> Optional[int]:
        """A row's committed ``cashPrice`` as a non-negative ``int``, or ``None``.

        Stored as a string; see :meth:`collection_id`.  Negative prices are
        refused here rather than clamped, because a negative price would make a
        debit a credit, and clamping it to ``0`` would make the service claim
        the committed price was free.
        """
        text = self._collection_text(index, "cashPrice")
        if text is None or text == "":
            return None
        try:
            value = int(text)
        except (TypeError, ValueError):
            return None
        if value < 0:
            return None
        return value

    def collection_requirement_ids(self, index: int) -> Optional[Tuple[int, ...]]:
        """A row's committed ``item_ids``, decoded, or ``None``.

        Stored as an embedded JSON **array string**.  Decoding is this module's
        job in the same way ``item_non_negative_int`` decodes a committed
        string field: the *shape* is content's, and the *rule* about what the
        ids mean belongs to :mod:`server_v1_collection`.

        An empty list is a real resolved value and is **not** ``None``: a
        collection with no requirements is a content shape v1 does not have an
        opinion about, and conflating it with "unreadable" would let a
        malformed row pass an all-or-nothing test vacuously.
        """
        decoded = self._collection_json(index, "item_ids")
        if not isinstance(decoded, list):
            return None
        ids: List[int] = []
        for value in decoded:
            if isinstance(value, bool) or not isinstance(value, int):
                return None
            ids.append(int(value))
        return tuple(ids)

    def collection_prize(self, index: int) -> Optional[Tuple[int, int]]:
        """A row's committed ``prize`` as ``(item_id, quantity)``, or ``None``.

        Stored as an embedded JSON object string mapping **string** keys to
        counts, and every committed row carries exactly one entry.

        **Only** a single-entry prize resolves.  A zero-entry or multi-entry
        prize is ``None``, because returning the first of several would silently
        pick one of the committed outcomes the server never chose.  The string
        key is decoded to an ``int`` here so the caller never sees a store key;
        a key that will not parse as an integer is ``None`` too, since the save
        document's own keys are integers.
        """
        decoded = self._collection_json(index, "prize")
        if not isinstance(decoded, dict) or len(decoded) != 1:
            return None
        key, quantity = next(iter(decoded.items()))
        if isinstance(quantity, bool) or not isinstance(quantity, int):
            return None
        if isinstance(key, str):
            try:
                item_id = int(key)
            except (TypeError, ValueError):
                return None
        elif isinstance(key, int) and not isinstance(key, bool):
            item_id = int(key)
        else:
            return None
        return (item_id, int(quantity))

    def _collection_text(self, index: int, field: str) -> Optional[str]:
        row = self.collection_row(index)
        if row is None or field not in row:
            return None
        raw = row[field]
        if raw is None or isinstance(raw, bool):
            return None
        if isinstance(raw, str):
            return raw.strip()
        if isinstance(raw, int):
            return str(raw)
        return None

    def _collection_json(self, index: int, field: str) -> Any:
        """Decode one committed embedded-JSON string field, or raise.

        ``ContentError`` rather than ``None`` for a **malformed** encoding:
        "the field is absent" is reported as ``None`` by
        :meth:`_collection_text` and reaches the caller as an unresolvable
        collection, while "the field is present and does not parse" is a content
        defect the service must not paper over by treating the requirement list
        as empty.
        """
        text = self._collection_text(index, field)
        if text is None:
            return None
        try:
            return json.loads(text)
        except ValueError as error:
            raise ContentError(
                "no_collection",
                "committed %s at position %d is not decodable JSON: %s"
                % (field, index, error),
            )

    # ---------------------------------------------------------- magics table --
    #: The committed magics section's fields this module reads.  A tuple, for
    #: the same reason :data:`COLLECTION_FIELDS` is one: a test can then assert
    #: the reader's declared surface against the normalized package's own field
    #: set rather than against a chosen example.
    MAGIC_FIELDS: Tuple[str, ...] = (
        "id",
        "name",
        "description",
        "mana",
        "area",
        "level",
        "gold",
        "cash",
        "img_name",
        "target",
    )

    def magic_rows(self) -> Tuple[Mapping[str, Any], ...]:
        """The committed ``magics`` rows, verbatim, in array order.

        An absent or non-array section yields ``()`` rather than raising, for
        the same reason :meth:`collection_rows` does: the caller then refuses an
        identity no committed row carries with a *content* reason instead of
        turning a missing table into a load failure.  Whether an empty table is
        acceptable is not this module's decision; it reports what it found.
        """
        rows = self._magics
        if not isinstance(rows, list):
            return ()
        return tuple(row for row in rows if isinstance(row, Mapping))

    def magic_row(self, magic_id: int) -> Optional[Mapping[str, Any]]:
        """The committed magic row whose ``id`` column is ``magic_id``, or ``None``.

        **Keyed by the committed ``id`` column, not by position** (design D3),
        and that is a measured decision rather than a preference: the preserved
        ``buy_magic``/``use_magic`` branches never index the table at all — they
        use the client's value as a ledger key and never consult ``magics.json``
        — so there is no legacy index base to reproduce and the question is
        "which committed row is this id", not "which position does it name".
        Both candidate readings were checked against the corpus: the zero-based
        *position* reading is **falsified** by ``villages/Neutral.json``, whose
        ledger key ``"10"`` is out of range for a ten-row zero-based table and
        whose four other keys would retarget to different spells, while the
        one-based ``id`` reading is supported by ``id == position + 1`` on all ten
        rows with no gaps and by all five corpus keys resolving.

        A ``bool`` is refused here for the same reason :meth:`collection_row`
        refuses one: ``True`` is an ``int`` in Python and would otherwise name
        magic 1 without ever being an identity.
        """
        if isinstance(magic_id, bool) or not isinstance(magic_id, int):
            return None
        for row in self.magic_rows():
            value = row.get("id")
            if isinstance(value, bool) or not isinstance(value, int):
                continue
            if int(value) == magic_id:
                return row
        return None

    def magic_ids(self) -> Tuple[int, ...]:
        """The committed ``id`` values, in array order.

        Returned as an index, not a lookup, so the id space is inspectable: the
        per-route claim that the space is contiguous needs the whole sequence,
        and building it here means the assertion reads the table rather than a
        transcribed range.
        """
        ids: List[int] = []
        for row in self.magic_rows():
            value = row.get("id")
            if isinstance(value, bool) or not isinstance(value, int):
                continue
            ids.append(int(value))
        return tuple(ids)

    def magic_field(self, magic_id: int, name: str) -> Any:
        """One committed magic field, **verbatim**, or ``None`` when absent.

        This is a *reader*, not an interpreter, and the distinction is the point
        of design D2: the committed table carries four numeric columns
        (``gold``, ``cash``, ``mana``, ``level``) and **none of them is named a
        price**, so nothing here combines them, scales them, or turns one into
        another.  A row the table does not carry and a field the row does not
        carry are both ``None``, which is deliberately indistinguishable: both
        mean "committed content does not describe this", and neither is a zero.
        """
        row = self.magic_row(magic_id)
        if row is None:
            return None
        return row.get(name)

    def magic_area(self, magic_id: int) -> Optional[Tuple[int, ...]]:
        """A row's committed ``area``, decoded, or ``None``.

        **Stored as an embedded JSON string** (``"[5,7,9]"``) on every committed
        row and coerced to a list by the repository's own normalization; the
        coercion is recorded, not interpreted, exactly as for the collections
        table's ``item_ids``/``prize``.  Decoding is a decoding: it recovers the
        shape content already decided and says nothing about what the numbers
        mean.
        """
        raw = self.magic_field(magic_id, "area")
        if raw is None or isinstance(raw, bool):
            return None
        if isinstance(raw, (list, tuple)):
            decoded: Any = list(raw)
        elif isinstance(raw, str):
            try:
                decoded = json.loads(raw)
            except ValueError as error:
                raise ContentError(
                    "no_magic",
                    "committed area for magic %r is not decodable JSON: %s"
                    % (magic_id, error),
                )
        else:
            return None
        if not isinstance(decoded, list):
            return None
        values: List[int] = []
        for value in decoded:
            if isinstance(value, bool) or not isinstance(value, int):
                return None
            values.append(int(value))
        return tuple(values)

    # --------------------------------------------------------- unit id space --
    #: The committed ``type`` value a **unit** row carries, as a literal and not
    #: a derived label: the three committed id spaces are separated by this
    #: column and by nothing else, so an identity validated against the unit
    #: space cannot accidentally name a building or the one special.
    UNIT_TYPE = "u"

    def ids_for_type(self, type_value: str) -> Tuple[int, ...]:
        """Every committed item id whose ``type`` column is ``type_value``.

        Read from the **cleaned** ``items`` array rather than from a per-type
        table, because the committed configuration stores one array and a
        ``type`` column, and a second index maintained beside it could disagree
        with the array it indexes.  Ids that will not parse as an integer are
        skipped rather than guessed at, and the array order is preserved so a
        caller comparing two id spaces sees the committed order rather than a
        sort of it.
        """
        ids: List[int] = []
        for row in self.item_rows():
            if str(row.get("type")) != type_value:
                continue
            value = row.get("id")
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                continue
            try:
                ids.append(int(value))
            except ValueError:
                continue
        return tuple(ids)

    def unit_rows(self) -> Tuple[Mapping[str, Any], ...]:
        """The committed **unit** rows, verbatim, in array order.

        ``type`` is the whole of the separation: measured over the committed
        configuration this is **429** rows carrying ``type`` ``"u"``, against
        **470** carrying ``"b"`` and **1** carrying ``"l"``, with **zero** id
        overlap between the three spaces.  The suite re-derives that overlap
        from this reader on every run rather than asserting a constant.
        """
        return tuple(
            row for row in self.item_rows() if str(row.get("type")) == self.UNIT_TYPE
        )

    def unit_row(self, unit_id: int) -> Optional[Mapping[str, Any]]:
        """The committed unit row whose ``id`` column is ``unit_id``, or ``None``.

        **Keyed by the committed ``id`` column, which is the column the
        repository's normalized package names ``legacy_id``,** and not by
        position in the unit array: an identity is a content id, and the
        preserved branch has no positional index for it -- its subject is the
        per-tuple item id at ``command.py:870`` (``item = unit[0]``), which is a
        committed id and not a position.

        **Restricted to ``type`` ``"u"``** for the measured reason in
        :meth:`unit_rows`: a lookup that ignored the column would let a building
        or the one special be addressed as a combat identity.  ``0`` and every
        negative id resolve to no row, which is the true statement about them --
        there is no positional clamp here for a non-positive id to alias, the
        same asymmetry ``server_v1_magic.magic_row`` records.
        """
        if isinstance(unit_id, bool) or not isinstance(unit_id, int):
            return None
        for row in self.unit_rows():
            value = row.get("id")
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                continue
            try:
                if int(value) == unit_id:
                    return row
            except ValueError:
                continue
        return None

    def unit_ids(self) -> Tuple[int, ...]:
        """The committed unit id space, in array order.

        An index rather than a lookup, for the same reason as
        :meth:`magic_ids`: the refusal that names an out-of-table identity needs
        the whole space to report, and building it here means the assertion reads
        the committed table instead of a transcribed range.
        """
        return self.ids_for_type(self.UNIT_TYPE)

    def unit_properties(self, unit_id: int) -> Optional[Mapping[str, Any]]:
        """A unit row's committed ``properties``, **decoded**, or ``None``.

        **Stored as an embedded JSON string** on every committed row -- measured,
        ``'{"ft_building":"1","bulldozable":"1",...}'`` -- and decoded by the
        repository's own normalization into an object.  Decoding recovers a shape
        content already decided and says nothing about what the keys mean; the
        keys themselves are read one at a time by :meth:`unit_flag`.

        A malformed encoding raises :class:`ContentError` rather than degrading
        to ``None``, exactly as :meth:`_collection_json` does: "the field is
        absent" and "the field is present and does not parse" are different
        facts, and the first is a real committed shape while the second is a
        content defect this service must not paper over.
        """
        row = self.unit_row(unit_id)
        if row is None:
            return None
        raw = row.get("properties")
        if raw is None or isinstance(raw, bool):
            return None
        if isinstance(raw, Mapping):
            return raw
        if not isinstance(raw, str):
            return None
        if raw.strip() == "":
            # The preserved helper's own first gate is ``if not properties:
            # return False`` (``engine.py:155-156``), so an empty committed
            # properties value is an **absence** there rather than a parse.
            return None
        try:
            decoded = json.loads(raw)
        except ValueError as error:
            raise ContentError(
                "no_unit",
                "committed properties for unit %r is not decodable JSON: %s"
                % (unit_id, error),
            )
        if not isinstance(decoded, dict):
            return None
        return decoded

    def unit_flag(self, unit_id: int, name: str) -> Optional[Any]:
        """One committed ``properties`` key, **verbatim**, or ``None`` when absent.

        ``None`` is the absence and is **never** a zero: the preserved helper
        tests key presence and returns ``False`` on an absent key
        (``engine.py:159-160``) rather than reading it as ``0``, so a reader that
        collapsed the two would report a committed fact the source never states.
        Measured on the committed content: ``resurrectable`` is the **string**
        ``"1"`` on **426** of **429** units and **absent** on ids ``923``,
        ``933`` and ``1176`` -- three units whose absence is exactly the case
        this accessor keeps distinct.
        """
        properties = self.unit_properties(unit_id)
        if properties is None:
            return None
        if name not in properties:
            return None
        value = properties[name]
        if isinstance(value, (dict, list)):
            return None
        return value

    def unit_flag_is_positive(self, unit_id: int, name: str) -> Optional[bool]:
        """Whether a committed flag reads as **greater than zero**, or ``None``.

        The comparison is the preserved helper's own (``int(properties[name]) >
        0``, ``engine.py:162``) and nothing more: no scaling, no clamping, no
        default.  ``None`` means the flag is absent or will not parse as an
        integer, and both are reported rather than resolved -- a value legacy
        would raise on is a value v1 refuses to interpret, which is the same
        posture every other unparseable committed field takes in this module.

        **The value is compared as a number, never as a truthy test.**
        The committed flags are **strings**, and a non-empty string is truthy in
        both languages this repository writes in: ``"0"`` would pass a bare
        ``if value:`` while the preserved helper reads it as zero.  Measured on
        the committed content, every one of the 426 present ``resurrectable``
        values is ``"1"``, so no committed row distinguishes the two readings --
        which is exactly why the reader has to.
        """
        raw = self.unit_flag(unit_id, name)
        if raw is None:
            return None
        if isinstance(raw, bool):
            return None
        if isinstance(raw, int):
            return raw > 0
        if isinstance(raw, float):
            return raw > 0
        if isinstance(raw, str):
            text = raw.strip()
            if text == "":
                return None
            try:
                return int(text) > 0
            except ValueError:
                return None
        return None

    def provenance(self) -> Dict[str, Any]:
        """What was loaded, for the response envelope and the containment record."""
        return {
            "item_entries": self.item_count(),
            "distinct_item_ids": self.distinct_item_count(),
            "applied_patches": list(self.applied_patches),
            "applied_mods": list(self.applied_mods),
            "missing_patches": list(self.missing_patches),
            "missing_mods": list(self.missing_mods),
            "removed_duplicate_items": self.removed_duplicate_items,
            "skipped_loader_steps": list(SKIPPED_LOADER_STEPS),
            "collection_rows": len(self.collection_rows()),
            "magic_rows": len(self.magic_rows()),
            "unit_rows": len(self.unit_rows()),
        }


# ------------------------------------------------------------------ loading --
def load_content(content_root: Path) -> CommittedContent:
    """Load the committed configuration from ``content_root``.

    ``content_root`` is explicit and is never the process working directory.
    Legacy resolves its content from ``"."`` at import time (``bundle.py``),
    which means the process can only ever load the content it was started in;
    v1 names the root it reads so a test can load a disposable copy and a
    reader can see which bytes produced a derivation.
    """
    root = Path(content_root)
    main_path = root.joinpath(*CONFIG_MAIN)
    if not main_path.is_file():
        raise ContentError(
            "content_missing", "committed configuration not found: %s" % main_path
        )
    try:
        document = json.loads(main_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ContentError(
            "content_unreadable", "committed configuration is unreadable: %s" % error
        )
    if not isinstance(document, dict):
        raise ContentError(
            "content_unreadable", "the committed configuration is not a JSON object"
        )

    applied_patches, missing_patches = _apply_list(
        document, root, PATCH_LIST, "patch"
    )
    applied_mods, missing_mods = _apply_list(document, root, MOD_LIST, "mod")
    removed = _remove_duplicate_items(document)

    # ``make_dynamic`` is deliberately not run: see the module docstring.
    return CommittedContent(
        document,
        applied_patches=applied_patches,
        applied_mods=applied_mods,
        missing_patches=missing_patches,
        missing_mods=missing_mods,
        removed_duplicate_items=removed,
    )


def _apply_list(
    document: Dict[str, Any], root: Path, relative: Tuple[str, ...], label: str
) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Apply the ordered ``patches.txt`` / ``mods.txt`` list, in file order.

    Legacy's rule, reproduced exactly: strip each line; skip a blank line and a
    line starting with ``#``; replace ``".json"`` with ``""`` anywhere in what
    remains; apply the file if it exists and record the name as missing if it
    does not.  The committed repository's list contains four comments and five
    patch names, all present, and its ``mods.txt`` contains only comments, so
    this line loads five patches and zero mods on the committed content root.
    """
    listing = root.joinpath(*relative)
    if not listing.is_file():
        # Legacy skips an absent list entirely and prints nothing about it.
        return (), ()
    try:
        lines = listing.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ContentError(
            "content_unreadable", "%s list is unreadable: %s" % (label, error)
        )
    base = listing.parent
    applied: List[str] = []
    missing: List[str] = []
    for raw in lines:
        name = raw.strip()
        if name == "" or name.startswith("#"):
            continue
        name = name.replace(".json", "")
        path = base / ("%s.json" % name)
        if not path.is_file():
            missing.append(name)
            continue
        try:
            patch = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ContentError(
                "content_unreadable",
                "%s file %s is unreadable: %s" % (label, name, error),
            )
        try:
            jsonpatch.apply_patch(document, patch, in_place=True)
        except (jsonpatch.JsonPatchException, ValueError) as error:
            raise ContentError(
                "content_unreadable",
                "%s file %s does not apply: %s" % (label, name, error),
            )
        applied.append(name)
    return tuple(applied), tuple(missing)


def _remove_duplicate_items(document: Dict[str, Any]) -> int:
    """Legacy's duplicate cleaning, keeping the LAST occurrence.

    ``get_game_config.remove_duplicate_items`` restarts its scan on every
    deletion and deletes ``items[indexes[id]]`` — the entry it had **already
    seen** — so the survivor of a duplicate id is the later one.  A
    first-wins implementation would produce a different items array for the
    same bytes, so this is the rule, not a summary of it.

    Returns the number of deletions, which the committed content reports as
    ``0`` in the final state of the patched array (the measured value is
    asserted by ``tests/test_content.py`` rather than assumed here).
    """
    items = document.get("items")
    if not isinstance(items, list):
        raise ContentError(
            "no_items", "the committed configuration has no items array"
        )
    removed = 0
    while True:
        seen: Dict[Any, int] = {}
        duplicate = False
        for index, entry in enumerate(items):
            if not isinstance(entry, Mapping) or "id" not in entry:
                raise ContentError(
                    "no_items", "a committed item has no readable id while cleaning"
                )
            key = entry["id"]
            if key in seen:
                del items[seen[key]]
                removed += 1
                duplicate = True
                break
            seen[key] = index
        if not duplicate:
            return removed


def _number_tuple(values: Any) -> Tuple[float, ...]:
    """A tuple of finite numbers, or ``()`` for anything that is not one.

    A ``bool`` is an ``int`` in Python and would index a ladder as ``1`` /
    ``0``, so it is excluded here rather than silently accepted as a
    threshold.
    """
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        return ()
    numbers: List[float] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return ()
        if value != value or value in (float("inf"), float("-inf")):
            return ()
        numbers.append(float(value))
    return tuple(numbers)


__all__ = [
    "CONFIG_MAIN",
    "MOD_LIST",
    "PATCH_LIST",
    "SKIPPED_LOADER_STEPS",
    "CommittedContent",
    "ContentError",
    "load_content",
]
