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
