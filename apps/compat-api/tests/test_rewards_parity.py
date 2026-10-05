#!/usr/bin/env python3
"""Offline integrity guard for the executed-legacy reward-cursor fixture.

Change: ``2026-10-05-rewards``, task group 1.

**What this module is for.** ``apps/compat-api/capture_rewards_fixture.py`` drives the
two preserved reward branches (``weekly_reward``, ``command.py:345-363``, and
``win_daily_bonus``, ``command.py:444-463``) against one disposable copy of
``villages/Neutral.json`` and one legacy server, and publishes what it observed to
``tests/fixtures/godot-rewards/``.  Nothing about those observations survives
re-running: both branches stamp the wall clock unconditionally, so **every**
``before.json`` and ``after.json`` differs on every rerun (measured: 37 of the 48
capture-output files differ between two consecutive runs).  The fixture is
therefore the *only* record of what the oracle did, and a record nobody re-checks
is a claim, not evidence.

So this module recomputes, offline, with no server and no socket:

1. **The changed-leaf set of every transaction**, from the recorded
   ``before.json`` / ``after.json`` documents -- the states, not the summary.  The
   recomputation is over the full ~2,300-leaf document, so "exactly two leaves
   moved" is a claim about the whole save rather than about one row.
2. **The whole-state digest** of each recorded state, by this module's own
   reimplementation of the capture's recipe, cross-checked against the capture's
   so the two cannot drift apart silently.
3. **The container-size changes**, which the leaves-only projection cannot see --
   the same defect class the delivered endpoint's leaf allowlist exists to catch.
4. **All eight stored resource slots**, unchanged in every one of the seven steps.
5. **The cursor linkage**: every step's before-state is the previous step's
   after-state over the whole document, and exactly one of the two cursors moves
   per step while the other stands still.
6. **The recorded ladders** and every pinned outcome (the arity-selected arms, the
   deduplicating unit-list helper, the accumulating storage helper, and the
   backwards cursor move).
7. **The manifest's own figures** -- inventory, containment, census, seed digest --
   against the bytes on disk.
8. **The cross-projection agreement**: the capture's leaves-only diff and the
   envelope's container-inclusive diff must describe the same change.

**Every digest and byte count here is LF-normalised.**  This repository sets
``core.autocrlf=true`` with no ``.gitattributes`` entry for ``tests/fixtures/**``,
so byte-identical committed content is CRLF in one checkout and LF in another.  A
guard measured with ``st_size`` or a raw-byte digest is a line-ending detector: it
fails on one checkout and passes on the other while saying nothing about the
inventory it exists to protect.  That defect was found and fixed once in this
repository (PR #280), so the rule is applied here from the start.

**Nothing here replays the endpoint.**  That is ``test_rewards_endpoint.py``'s job,
and it needs a disposable corpus and a Flask app.  This module needs neither, and
proves it: ``NoNetworkTests`` asserts both service ports are free and runs the
whole recomputation with ``socket.socket`` replaced.

No server, no network, no Flash, no Ruffle, no ActionScript, no browser.
"""

from __future__ import annotations

import hashlib
import json
import re
import socket
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import compat_test_harness as harness

from placement_envelope import parse_data_field

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-rewards"
STEPS_DIR = FIXTURES / "steps"
MANIFEST_PATH = FIXTURES / "capture-manifest.json"
README_PATH = FIXTURES / "README.md"
SEED_PATH = harness.REPO_ROOT / "villages" / "Neutral.json"
COMPAT_DIR = harness.REPO_ROOT / "apps" / "compat-api"
CAPTURE_PATH = COMPAT_DIR / "capture_rewards_fixture.py"

SCHEMA = "rewards-cursor-fixture-v1"
LOGIN_STEP = "login_post"

#: The committed vocabulary of the two branches, transcribed from the preserved
#: source.  ``RESOURCE_SLOTS`` is the set ``engine.apply_resources`` reads and
#: writes (``engine.py:251-271``) plus ``privateState['energy']``, which no legacy
#: branch ever writes and which ``LegacyBoot.resources`` does not expose -- the
#: reason the delivered proof reads it off the document instead of trusting the
#: accessor.  Eight slots, and a subset comparison would prove nothing about a
#: slot nobody read, so the set is compared whole.
WEEKLY_COMMAND = "weekly_reward"
DAILY_COMMAND = "win_daily_bonus"
WEEKLY_CURSOR = "weeklyRewardIndex"
DAILY_CURSOR = "bonusNextId"
WEEKLY_STAMP = "timeStampMondayBonus"
DAILY_STAMP = "timestampLastBonus"
NEUTRAL_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]
RESOURCE_VECTOR_SLOTS = 8

#: Which private-state instant each branch stamps, from ``command.py:361``
#: (``timeStampMondayBonus``) and ``command.py:454`` (``timestampLastBonus``).
#: Held as its own table rather than read out of each transaction's own
#: ``instant_key``, because reading it back from the record under test would make
#: the assertion ``x == x``.
STAMP_KEY_FOR_COMMAND: Dict[str, str] = {
    WEEKLY_COMMAND: WEEKLY_STAMP,
    DAILY_COMMAND: DAILY_STAMP,
}

RESOURCE_SLOTS: Dict[str, Tuple[Any, ...]] = {
    "xp": ("maps", 0, "xp"),
    "gold": ("maps", 0, "gold"),
    "wood": ("maps", 0, "wood"),
    "oil": ("maps", 0, "oil"),
    "steel": ("maps", 0, "steel"),
    "cash": ("playerInfo", "cash"),
    "mana": ("privateState", "mana"),
    "energy": ("privateState", "energy"),
}

#: The recorded cursor ladders, over the whole seven-step sequence.  The weekly
#: ladder is **4 -> 0 -> 1** and the daily ladder is **3 -> 4 -> 1 -> 2**; the
#: daily 4 -> 1 is the backwards move design D5 records, and it is the reason step
#: 7 exists -- without it the fixture could not show that the next link depends on
#: the recorded cursor rather than on anything sent.
RECORDED_WEEKLY_LADDER = [4, 0, 1]
RECORDED_DAILY_LADDER = [3, 4, 1, 2]

#: The seven recorded steps, in recorded order, with the file each one must
#: publish.  ``transaction.json`` is per-step evidence; the login step is not a
#: transaction and carries no ``transaction.json`` and no parity claim.
RECORDED_STEPS: Tuple[str, ...] = (
    "txn_weekly_short_arm_grants_nothing",
    "txn_weekly_long_arm_appends_an_absent_unit",
    "txn_weekly_long_arm_deduplicates_a_present_unit",
    "txn_daily_short_arm_grants_nothing",
    "txn_daily_granting_arm_lands_in_storage",
    "txn_daily_oversized_next_id_moves_the_cursor_backwards",
    "txn_daily_after_the_backwards_move",
)

#: How far the capture output's byte total may move from the figure the README
#: states, and the same number the README states.  It exists because the branches
#: stamp the wall clock unconditionally: every recorded instant is a fresh
#: ten-digit number, so the serialized total drifts by a few tens of bytes between
#: runs of an identical capture.  Measured on two consecutive runs of this
#: capture: 1,816,142 and 1,816,177 -- 35 bytes apart.  The bound is deliberately
#: an order of magnitude wider than the observed drift, so it catches a real
#: inventory change and nothing else.
BYTE_TOTAL_TOLERANCE = 512

_MANIFEST: Optional[Dict[str, Any]] = None
_WORKING_TREE_PRE: List[Dict[str, str]] = []


# ------------------------------------------------------------------- helpers --
def manifest() -> Dict[str, Any]:
    global _MANIFEST
    if _MANIFEST is None:
        _MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return _MANIFEST


def transactions() -> List[Dict[str, Any]]:
    return list(manifest()["transactions"])


def by_name(name: str) -> Dict[str, Any]:
    for entry in transactions():
        if entry["name"] == name:
            return entry
    raise AssertionError("the fixture records no transaction named %r" % name)


def step_dir(name: str) -> Path:
    """The published directory for one step.

    The step list and the manifest's ``recorded_steps`` are **directory names**
    (they carry the ``txn_`` prefix the capture adds), while the manifest's
    ``transactions[].name`` is the **bare** transaction name.  This helper accepts
    either and must not double the prefix -- an earlier draft of these tests
    concatenated unconditionally and every ``step_dir`` call raised ``FileNotFoundError``
    on a path that did exist, which reads like a missing fixture rather than like
    a doubled prefix.
    """
    if name.startswith("txn_"):
        return STEPS_DIR / name
    return STEPS_DIR / ("txn_%s" % name)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_bytes_lf(path: Path) -> bytes:
    """The committed blob form of a file: CRLF folded to LF, and nothing else."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def committed_sha(path: Path) -> str:
    return hashlib.sha256(read_bytes_lf(path)).hexdigest()


def typed_equal(left: Any, right: Any) -> bool:
    """Equality that will not call ``1``, ``1.0`` and ``True`` the same value.

    Reimplemented rather than imported, so this module depends on the FIXTURE and
    not on the tool that wrote it -- and because the distinction matters: the
    reward schedules commit both integers and, elsewhere in the corpus, booleans,
    and a plain ``==`` would pass a mistyped row for the wrong reason.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, int) or isinstance(right, int):
        return (
            isinstance(left, int)
            and isinstance(right, int)
            and not isinstance(left, bool)
            and not isinstance(right, bool)
            and left == right
        )
    if isinstance(left, float) or isinstance(right, float):
        return (
            isinstance(left, float) and isinstance(right, float) and left == right
        )
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        if sorted(left) != sorted(right):
            return False
        return all(typed_equal(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False
        return all(typed_equal(a, b) for a, b in zip(left, right))
    return left == right


def leaf_items(document: Any, prefix: str = "") -> List[Tuple[str, Any]]:
    """Every LEAF of a JSON document as sorted ``(json pointer path, value)``.

    Containers are deliberately not recorded here; :func:`container_items` records
    those.  Keeping the two projections separate is what lets
    :meth:`ProjectionAgreementTests` assert they describe the same change.
    """
    out: List[Tuple[str, Any]] = []
    if isinstance(document, dict):
        for key in sorted(document):
            out.extend(leaf_items(document[key], "%s/%s" % (prefix, key)))
    elif isinstance(document, list):
        for index, value in enumerate(document):
            out.extend(leaf_items(value, "%s/%d" % (prefix, index)))
    else:
        out.append((prefix, document))
    return out


def container_items(document: Any, prefix: str = "") -> List[Tuple[str, int]]:
    """Every CONTAINER of a JSON document as sorted ``(json pointer path, size)``.

    Needed because an added or emptied container is a real change that
    :func:`leaf_items` reports nothing for: the weekly granting arm creates
    ``/maps/0/items/600`` and grows ``/maps/0/items`` from 549 to 550, and a
    leaves-only comparison sees the new row's leaves but not either size change.
    """
    out: List[Tuple[str, int]] = []
    if isinstance(document, dict):
        out.append((prefix, len(document)))
        for key in sorted(document):
            out.extend(container_items(document[key], "%s/%s" % (prefix, key)))
    elif isinstance(document, list):
        out.append((prefix, len(document)))
        for index, value in enumerate(document):
            out.extend(container_items(value, "%s/%d" % (prefix, index)))
    return out


def canonical_json(value: Any) -> str:
    """The capture's deterministic serialization, reimplemented."""
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=True)


def canonical_digest(entries: List[Tuple[str, str]]) -> str:
    """The capture's ``canonical_digest`` recipe, reimplemented.

    SHA-256 over ordinal-sorted ``"<digest>  <path>\\n"`` lines -- digest FIRST,
    two spaces.  Verified against ``hashing.canonical_digest`` rather than
    guessed; an earlier guard in this repository had the order reversed and one
    space, which made every digest comparison report a mismatch for a reason that
    had nothing to do with what it was guarding.
    """
    material = sorted(entries, key=lambda item: item[0])
    running = hashlib.sha256()
    for path, value in material:
        running.update(("%s  %s\n" % (value, path)).encode("utf-8"))
    return running.hexdigest()


def canonical_state_sha(document: Any) -> str:
    """Whole-document digest over every leaf **and** container, order-independent.

    The two path sets are disjoint -- a node is either a container or a leaf, never
    both -- which is what lets them share one digest.  ``canonical_digest``
    requires unique paths and would raise on a collision, so a mistake here is a
    loud failure rather than a silently weaker digest.
    """
    parts: List[Tuple[str, str]] = [
        (path, "leaf %s" % canonical_json(value))
        for path, value in leaf_items(document)
    ]
    parts.extend(
        (path, "container %d" % size) for path, size in container_items(document)
    )
    self_test_unique_paths(parts)
    return canonical_digest(parts)


def self_test_unique_paths(parts: List[Tuple[str, str]]) -> None:
    paths = [path for path, _ in parts]
    if len(set(paths)) != len(paths):
        seen = set()
        duplicate = next(path for path in paths if path in seen or seen.add(path))
        raise AssertionError(
            "the leaf and container projections collide on %r, so the whole-state "
            "digest would be ambiguous" % duplicate
        )


def leaf_diff(before: Any, after: Any) -> List[Tuple[str, bool, Any, bool, Any]]:
    """``(path, present_before, before, present_after, after)``, sorted by path.

    A path present on one side only is a difference, not a skip: the union of both
    key sets is walked, so a key the comparison never looked at cannot pass as
    unchanged.
    """
    left = {path: value for path, value in leaf_items(before)}
    right = {path: value for path, value in leaf_items(after)}
    out: List[Tuple[str, bool, Any, bool, Any]] = []
    for path in sorted(set(left) | set(right)):
        in_left = path in left
        in_right = path in right
        if in_left and in_right and typed_equal(left[path], right[path]):
            continue
        out.append((path, in_left, left.get(path), in_right, right.get(path)))
    return out


#: The sentinel standing for "this path is not present on that side".  A distinct
#: object rather than ``None``, because ``null`` is a legal leaf value in this
#: corpus and a sentinel equal to ``None`` would make a value change to or from
#: ``null`` look like a presence change -- which is a different defect.
ABSENT = object()


def leaf_diff_paths(before: Any, after: Any) -> List[str]:
    """Just the paths of :func:`leaf_diff`, sorted."""
    return [row[0] for row in leaf_diff(before, after)]


def container_diff(before: Any, after: Any) -> List[str]:
    """Container paths whose child count changed, added or removed."""
    left = dict(container_items(before))
    right = dict(container_items(after))
    return sorted(
        path
        for path in set(left) | set(right)
        if left.get(path) != right.get(path)
    )


def _skip_string_and_comments(text: str, index: int) -> int:
    """The index just past the string or comment starting at ``text[index]``.

    A two-state scanner rather than a regular expression, because this corpus has
    both nested quoting (``'a "b" c'``) and an apostrophe inside a double-quoted
    string.  A naive quote-counter desynchronises on the second and then reports a
    whole file as one string, which is a guard that silently checks nothing.
    """
    char = text[index]
    if char in "'\"":
        # `text[index:index + 3]` is the whole opening delimiter for a triple
        # quoted string and a one-character prefix otherwise, so it is the
        # delimiter to scan to directly -- no arithmetic on a boolean, which
        # silently produced the integer 1 or 3 and then blew up on `len()`.
        quote = text[index : index + 3] if text[index : index + 3] in ("'''", '"""') else char
        index += len(quote)
        while index < len(text):
            if text[index] == "\\":
                index += 2
                continue
            if text.startswith(quote, index):
                return index + len(quote)
            index += 1
        return index
    if char == "#":
        newline = text.find("\n", index)
        return len(text) if newline == -1 else newline
    return index


def code_only(source: str) -> str:
    """The source with comments and string literals blanked, offsets preserved.

    Offsets are preserved because the callers here slice the result by index; a
    whitespace-substituted form would shift every offset and quietly make a
    position-based scan look at the wrong characters.
    """
    out = list(source)
    index = 0
    while index < len(source):
        char = source[index]
        if char in "'\"" or char == "#":
            end = _skip_string_and_comments(source, index)
            for position in range(index, min(end, len(source))):
                if out[position] != "\n":
                    out[position] = " "
            index = end
            continue
        index += 1
    return "".join(out)


def call_argument_texts(source: str, name: str) -> List[str]:
    """The argument text of every ``name(...)`` call, with nested parens respected."""
    body = code_only(source)
    out: List[str] = []
    for match in re.finditer(r"\b%s\s*\(" % re.escape(name), body):
        depth = 0
        for index in range(match.end() - 1, len(body)):
            char = body[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    out.append(source[match.end() : index])
                    break
        else:
            raise AssertionError("unbalanced call to %r in the capture source" % name)
    return out


def count_top_level_commas(arguments: str) -> int:
    """Commas in ``arguments`` that are not inside brackets or quotes."""
    body = code_only(arguments)
    depth = 0
    count = 0
    for char in body:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            count += 1
    return count


def read_at(document: Dict[str, Any], location: Tuple[Any, ...]) -> Any:
    cursor: Any = document
    for step in location:
        cursor = cursor[step]
    return cursor


def stored_resources(document: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, location in RESOURCE_SLOTS.items():
        out[name] = read_at(document, location)
    return out


def placed_rows(document: Dict[str, Any]) -> Dict[str, Any]:
    return document["maps"][0]["items"]


def private_state(document: Dict[str, Any]) -> Dict[str, Any]:
    return document["privateState"]


def both_cursors(document: Dict[str, Any]) -> Dict[str, int]:
    """The two cursors read straight off a state document."""
    private = private_state(document)
    return {name: private[name] for name in (WEEKLY_CURSOR, DAILY_CURSOR)}


def expected_both_cursors(before: Dict[str, int], after: Dict[str, int]) -> Dict[str, Any]:
    """The capture's ``both_cursors`` column, in the shape the record uses.

    Keyed by CURSOR with a ``before``/``after`` pair inside, not the other way
    round.  The first draft of these tests assumed the outer keys were
    ``before``/``after``, so the assertion compared a cursor-keyed record against a
    phase-keyed one and failed with a diff that named neither shape clearly.
    """
    return {
        cursor: {"before": before[cursor], "after": after[cursor]}
        for cursor in (WEEKLY_CURSOR, DAILY_CURSOR)
    }


def setUpModule() -> None:
    global _WORKING_TREE_PRE
    _WORKING_TREE_PRE = harness.working_tree_save_hashes()


def tearDownModule() -> None:
    if _WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a rewards fixture check wrote a working-tree save")
    if (harness.REPO_ROOT / "saves").exists():
        raise AssertionError(
            "a rewards fixture check created a working-tree saves/ directory"
        )


# ------------------------------------------------------------------- offline --
class NoNetworkTests(unittest.TestCase):
    """This module must need no server, and must prove it rather than assert it."""

    def test_the_whole_recomputation_runs_with_sockets_disabled(self) -> None:
        original = socket.socket
        attempted: List[Any] = []

        def refuse(self, address):  # type: ignore[no-untyped-def]
            attempted.append(address)
            raise AssertionError(
                "offline fixture check attempted a connection to %r" % (address,)
            )

        socket.socket = refuse  # type: ignore[assignment]
        try:
            with harness.offline():
                for entry in transactions():
                    base = step_dir(entry["name"])
                    before = load_json(base / "before.json")
                    after = load_json(base / "after.json")
                    self.assertTrue(leaf_diff(before, after))
                    canonical_state_sha(before)
                    canonical_state_sha(after)
        finally:
            socket.socket = original  # type: ignore[assignment]
        self.assertEqual(attempted, [])

    def test_neither_service_port_is_listening(self) -> None:
        """This suite runs offline; a listening port would mean it was not.

        Recorded as a **known-flaky** surface in this project: roughly twenty
        pre-existing compat suites assert these two ports are free, and three
        back-to-back full-suite runs once produced 19, 24, and 2 failures that were
        all this assertion, with no process holding either port, no TIME_WAIT
        blocking the probe, and neither port in a Windows excluded range.  Re-run
        before treating a failure here as a regression.
        """
        for port in (5055, 5056):
            self.assertTrue(
                harness.port_is_free("127.0.0.1", port),
                "port %d is in use, so this check is not running offline" % port,
            )


# ------------------------------------------------------- recomputed evidence --
class RecomputedLeafTests(unittest.TestCase):
    """Task 1.5: the recorded leaf claims, recomputed from the recorded states."""

    def test_every_recorded_step_published_its_own_evidence(self) -> None:
        for name in manifest()["recorded_steps"]:
            base = STEPS_DIR / name
            self.assertTrue(base.is_dir(), "recorded step %s has no directory" % name)
            leaves = [
                "request.json",
                "before.json",
                "after.json",
                "response.meta.json",
                "response.body",
            ]
            if name != LOGIN_STEP:
                leaves.append("transaction.json")
            for leaf in leaves:
                self.assertTrue(
                    (base / leaf).is_file(), "%s/%s is missing" % (name, leaf)
                )

    def test_the_recorded_step_list_matches_the_directories(self) -> None:
        recorded = list(manifest()["recorded_steps"])
        on_disk = sorted(path.name for path in STEPS_DIR.iterdir() if path.is_dir())
        self.assertEqual(sorted(recorded), on_disk)
        # The manifest lists the login step LAST, which is the order the fixture
        # README uses as well. Pinned so a reordering is a deliberate act.
        self.assertEqual(recorded[-1], LOGIN_STEP)
        self.assertEqual(recorded[:-1], list(RECORDED_STEPS))

    def test_the_manifest_and_each_step_agree(self) -> None:
        """The facts are committed twice, so neither copy may drift alone.

        An earlier guard in this repository read only the manifest's copy of the
        facts and never opened a single per-step file, so corrupting the committed
        per-step evidence was undetectable -- which an injection proved.  The
        fixture README calls those per-step files "the evidence, so the fixture
        stays checkable offline forever", which is only true while something reads
        them.
        """
        for entry in transactions():
            name = entry["name"]
            own = load_json(step_dir(name) / "transaction.json")
            self.assertEqual(
                entry, own, "%s: the manifest's copy of the facts differs" % name
            )

    def test_changed_leaf_set_equals_the_recomputed_diff(self) -> None:
        """The load-bearing check: the summary, recomputed from the states."""
        for entry in transactions():
            name = entry["name"]
            base = step_dir(name)
            before = load_json(base / "before.json")
            after = load_json(base / "after.json")
            recomputed = [row[0] for row in leaf_diff(before, after)]
            self.assertEqual(
                recomputed,
                list(entry["changed_leaf_paths"]),
                "%s: the recorded changed-leaf set is not the recomputed one" % name,
            )
            self.assertEqual(entry["changed_leaf_count"], len(recomputed), name)
            # The recorded before/after values must be the recomputed ones too, so
            # a tampered `leaf_diff` payload cannot sit beside a correct path list.
            self.assertEqual(
                [
                    {
                        "path": row[0],
                        "present_before": row[1],
                        "before": row[2],
                        "present_after": row[3],
                        "after": row[4],
                    }
                    for row in leaf_diff(before, after)
                ],
                list(entry["leaf_diff"]),
                "%s: the recorded leaf values are not the recomputed ones" % name,
            )

    def test_no_leaf_outside_the_recorded_set_moved(self) -> None:
        """The digest over every OTHER leaf must agree, before and after.

        Without this, "exactly two leaves moved" would be a claim about the two
        paths the summary names.  With it, it is a claim about all ~2,300 leaves of
        a real save document.
        """
        for entry in transactions():
            name = entry["name"]
            base = step_dir(name)
            before = load_json(base / "before.json")
            after = load_json(base / "after.json")
            skip = set(entry["changed_leaf_paths"])
            left = canonical_digest(
                [
                    (path, "leaf %s" % canonical_json(value))
                    for path, value in leaf_items(before)
                    if path not in skip
                ]
            )
            right = canonical_digest(
                [
                    (path, "leaf %s" % canonical_json(value))
                    for path, value in leaf_items(after)
                    if path not in skip
                ]
            )
            self.assertEqual(left, right, "%s: a leaf outside the set also moved" % name)

    def test_recorded_state_digests_are_recomputable(self) -> None:
        """Recomputed, never compared to a fixed constant.

        This is the difference from every earlier fixture in this repository.
        Both preserved branches stamp the wall clock unconditionally
        (``command.py:361``, ``command.py:454``), so the recorded states cannot be
        byte-reproduced by a rerun and a pinned digest would only ever fail.  The
        recorded digests are therefore checked against a **fresh measurement over
        the committed bytes**, which is the only claim a fixture digest can make.
        """
        for entry in transactions():
            name = entry["name"]
            base = step_dir(name)
            self.assertEqual(
                entry["state_sha256_before"],
                canonical_state_sha(load_json(base / "before.json")),
                name,
            )
            self.assertEqual(
                entry["state_sha256_after"],
                canonical_state_sha(load_json(base / "after.json")),
                name,
            )

    def test_every_transaction_used_the_neutral_vector(self) -> None:
        """No step is excused from the resource proof by a vector nobody checked.

        ``do_command`` applies the request's per-command vector **before** the
        branch runs (``command.py:40`` -> ``engine.apply_resources``,
        ``engine.py:251-271``), so a non-neutral vector would let a client mint or
        burn and would make "no stored resource moved" ambiguous rather than
        strong.  Eight slots, because the legacy vector is eight wide.
        """
        for entry in transactions():
            name = entry["name"]
            request = load_json(step_dir(name) / "request.json")
            envelope = parse_data_field(request["form"]["data"])
            commands = envelope["commands"]
            self.assertEqual(len(commands), 1, name)
            self.assertEqual(commands[0][0], 0, name)
            self.assertIn(commands[0][1], (WEEKLY_COMMAND, DAILY_COMMAND), name)
            self.assertEqual(
                commands[0][3],
                NEUTRAL_VECTOR,
                "%s carried a non-neutral resource vector" % name,
            )
            self.assertEqual(len(commands[0][3]), RESOURCE_VECTOR_SLOTS, name)

    def test_the_pinned_batch_timestamp_is_the_recorded_constant(self) -> None:
        """``ts`` is pinned so the request record is byte-stable.

        Legacy parses it and never reads it, which is exactly why a fixed constant
        is legitimate here rather than a shortcut.
        """
        for entry in transactions():
            request = load_json(step_dir(entry["name"]) / "request.json")
            envelope = parse_data_field(request["form"]["data"])
            self.assertEqual(envelope["ts"], 1700000000, entry["name"])

    def test_the_login_step_left_the_corpus_byte_identical(self) -> None:
        """The login's neutrality is asserted, not assumed."""
        before = load_json(STEPS_DIR / LOGIN_STEP / "before.json")
        after = load_json(STEPS_DIR / LOGIN_STEP / "after.json")
        self.assertEqual(leaf_diff(before, after), [])
        self.assertEqual(container_diff(before, after), [])
        self.assertEqual(canonical_state_sha(after), canonical_state_sha(before))
        # ...and identical to the committed seed, which is what makes the first
        # transaction's recorded before-state the seed's own state.
        self.assertEqual(
            canonical_state_sha(after), canonical_state_sha(load_json(SEED_PATH))
        )

    def test_the_login_step_carries_no_transaction_record(self) -> None:
        """It is a neutrality witness, not a transaction, and must not borrow
        another fixture's habit of recording parity for a step that made no
        change."""
        self.assertFalse((STEPS_DIR / LOGIN_STEP / "transaction.json").exists())
        self.assertNotIn(
            LOGIN_STEP, [entry["name"] for entry in transactions()]
        )


class ResourceProofTests(unittest.TestCase):
    """All eight stored slots, compared as a complete set in every step."""

    def test_the_committed_seed_records_every_one_of_the_eight_slots(self) -> None:
        slots = stored_resources(load_json(SEED_PATH))
        self.assertEqual(sorted(slots), sorted(RESOURCE_SLOTS))
        for name in sorted(slots):
            self.assertTrue(
                isinstance(slots[name], int) and not isinstance(slots[name], bool),
                "%s is %r, not an integer" % (name, slots[name]),
            )

    def test_no_stored_resource_moved_in_any_transaction(self) -> None:
        for entry in transactions():
            name = entry["name"]
            base = step_dir(name)
            before = stored_resources(load_json(base / "before.json"))
            after = stored_resources(load_json(base / "after.json"))
            self.assertEqual(
                sorted(before), sorted(RESOURCE_SLOTS), "%s reads a partial set" % name
            )
            self.assertEqual(
                sorted(before), sorted(entry["resources_before"]), name
            )
            for slot in sorted(RESOURCE_SLOTS):
                self.assertTrue(
                    typed_equal(before[slot], after[slot]),
                    "%s moved stored resource %s: %r -> %r"
                    % (name, slot, before[slot], after[slot]),
                )
            self.assertEqual(after, dict(entry["resources_after"]), name)
            self.assertEqual(entry["resources_moved"], [], name)
            self.assertEqual(entry["resource_slot_count"], len(RESOURCE_SLOTS), name)

    def test_the_eighth_slot_is_energy_and_no_legacy_branch_writes_it(self) -> None:
        """Why the comparison is eight wide and not the accessor's seven.

        ``privateState['energy']`` is a real stored slot, recorded as 50 in this
        seed, that ``LegacyBoot.resources`` does not expose.  A subset comparison
        against the accessor would leave it unread and the claim "no stored
        resource moved" would be true for a slot nobody looked at -- which is
        exactly the "defaults to zero on both sides" defect this file's own
        docstring warns about.
        """
        self.assertIn("energy", RESOURCE_SLOTS)
        slots = stored_resources(load_json(SEED_PATH))
        self.assertEqual(slots["energy"], 50)
        self.assertEqual(len(slots), 8)


class CursorLinkageTests(unittest.TestCase):
    """Sequence linkage over the whole document, on BOTH cursors.

    ``sessions.load_saves()`` caches the corpus in a module global **at import
    time**, so one server serves the whole sequence and the save file must not be
    restored between steps -- doing so would leave the in-memory corpus already
    mutated and silently produce different results.  These tests are what make the
    recorded cursor ladders mean anything: they assert each step really ran
    against its predecessor's recorded state.
    """

    def test_each_step_began_at_the_previous_steps_after_state(self) -> None:
        previous: Optional[Dict[str, Any]] = load_json(
            STEPS_DIR / LOGIN_STEP / "after.json"
        )
        for name in RECORDED_STEPS:
            entry = by_name(name[len("txn_") :])
            before = load_json(step_dir(name) / "before.json")
            self.assertEqual(
                canonical_state_sha(before),
                canonical_state_sha(previous),
                "%s did not begin at its predecessor's recorded state" % name,
            )
            previous = load_json(step_dir(name) / "after.json")

    def test_each_step_moved_exactly_one_of_the_two_cursors(self) -> None:
        for name in RECORDED_STEPS:
            short = name[len("txn_") :]
            entry = by_name(short)
            base = step_dir(name)
            before = both_cursors(load_json(base / "before.json"))
            after = both_cursors(load_json(base / "after.json"))
            self.assertEqual(
                entry["both_cursors"],
                expected_both_cursors(before, after),
                "%s: the recorded both-cursors row is not the one these two "
                "documents carry" % short,
            )
            moved = [
                cursor
                for cursor in (WEEKLY_CURSOR, DAILY_CURSOR)
                if before[cursor] != after[cursor]
            ]
            self.assertEqual(
                len(moved),
                1,
                "%s moved %d cursors; each branch writes exactly one" % (short, len(moved)),
            )
            self.assertEqual(moved[0], entry["cursor_key"], short)

    def test_the_recorded_ladders_are_the_recorded_transitions(self) -> None:
        """The successor ladders, read off the recorded transitions.

        A ladder is the list of **successors**, not of every before/after pair: the
        first step's *before* is the seed's own cursor, which is recorded once in
        the census and pinned separately below.  An earlier draft of this test
        appended both ends of every transition and so produced ``[3, 4, 4, 0, 0,
        1]`` -- seven numbers compared against a three-number constant, which
        reports a mismatch without saying which end of which pair is wrong.
        """
        weekly: List[int] = []
        daily: List[int] = []
        for name in RECORDED_STEPS:
            entry = by_name(name[len("txn_") :])
            cursors = entry["both_cursors"]
            for cursor, ladder in ((WEEKLY_CURSOR, weekly), (DAILY_CURSOR, daily)):
                if cursors[cursor]["after"] != cursors[cursor]["before"]:
                    ladder.append(cursors[cursor]["after"])
        self.assertEqual(weekly, RECORDED_WEEKLY_LADDER)
        self.assertEqual(daily, RECORDED_DAILY_LADDER)
        # The ladders are read off the recorded transitions, so the recorded
        # `cursor_before`/`cursor_after` columns cannot be the authority instead.
        self.assertEqual(RECORDED_WEEKLY_LADDER, [4, 0, 1])
        self.assertEqual(RECORDED_DAILY_LADDER, [3, 4, 1, 2])
        # And each ladder starts from the seed's own recorded cursor, which is the
        # link that makes the ladder a chain rather than a list of successors.
        seed = load_json(SEED_PATH)
        self.assertEqual(weekly[0], private_state(seed)[WEEKLY_CURSOR] + 1)
        self.assertEqual(daily[0], private_state(seed)[DAILY_CURSOR] + 1)

    def test_the_committed_seed_carries_both_cursors_and_both_instants(self) -> None:
        seed = load_json(SEED_PATH)
        private = private_state(seed)
        census = manifest()["seed"]["census"]
        self.assertEqual(private[WEEKLY_CURSOR], 3)
        self.assertEqual(private[DAILY_CURSOR], 2)
        self.assertEqual(census["weekly_cursor"], private[WEEKLY_CURSOR])
        self.assertEqual(census["daily_cursor"], private[DAILY_CURSOR])
        self.assertEqual(private[WEEKLY_STAMP], 1686569823)
        self.assertEqual(private[DAILY_STAMP], 1688653422)
        self.assertEqual(census["weekly_stamp"], private[WEEKLY_STAMP])
        self.assertEqual(census["daily_stamp"], private[DAILY_STAMP])


class ProjectionAgreementTests(unittest.TestCase):
    """The capture's leaves-only diff and the endpoint's container-inclusive one.

    ``rewards_envelope.document_leaves`` records containers with a size marker so
    an added or emptied container is a change; this fixture's ``changed_leaf_paths``
    records leaves only.  They are different projections of the same two
    documents, so they must agree about every **leaf**, and the endpoint's extra
    paths must be **only** containers.  Without this, the fixture would be checked
    against one projection and the delivered proof would be checked against the
    other, and a disagreement between them could never be noticed.
    """

    def test_the_two_projections_agree_on_every_leaf(self) -> None:
        for entry in transactions():
            name = entry["name"]
            base = step_dir(name)
            before = load_json(base / "before.json")
            after = load_json(base / "after.json")
            # The identity this test asserts, stated exactly:
            #
            #   {paths whose inclusive VALUE differs between before and after}
            #       == {paths whose leaf value differs} U {containers whose size
            #                                                differs}
            #
            # Both sides are computed independently -- the left from the
            # delivered projection, the right from this module's two separate
            # projections -- so this is a real cross-check of the two rules and
            # not a restatement of one.
            #
            # It is written as an EQUALITY of the full symmetric difference rather
            # than as two subset checks.  An earlier draft of this test asserted
            # only that the recorded leaf paths were a subset of the inclusive
            # projection, which the capture satisfies trivially on every step and
            # which cannot fail for a newly-created path -- those exist in the
            # after document alone, so the ``before``-side projection never
            # contains them.  The equality is what forces both directions.
            inclusive_before = rewards_document_leaves(before)
            inclusive_after = rewards_document_leaves(after)
            differing = {
                path
                for path in set(inclusive_before) | set(inclusive_after)
                if inclusive_before.get(path, ABSENT)
                != inclusive_after.get(path, ABSENT)
            }
            recorded = set(entry["changed_leaf_paths"])
            self.assertEqual(
                differing,
                set(leaf_diff_paths(before, after))
                | set(container_diff(before, after)),
                "%s: the inclusive projection's changed paths are not exactly the "
                "changed leaves together with the changed containers" % name,
            )
            # And the recorded column agrees with the recomputed leaf diff, so the
            # capture's own summary is checked against the documents it recorded.
            self.assertEqual(
                recorded,
                set(leaf_diff_paths(before, after)),
                "%s: recorded changed_leaf_paths differ from the recomputed leaf "
                "diff of the two recorded state documents" % name,
            )

    def test_a_granting_step_changes_a_container_the_leaf_projection_cannot_see(self) -> None:
        """The reason the two projections differ at all, measured.

        The weekly long arm creates a placed row, so ``/maps/0/items`` grows and
        ``/maps/0/items/<index>`` appears.  Both are containers, and neither has a
        leaf of its own, so the recorded leaf list cannot mention them.  Without
        this assertion, a future reader could conclude the two projections are
        interchangeable and drop the size markers from the delivered allowlist.
        """
        entry = by_name("weekly_long_arm_appends_an_absent_unit")
        base = step_dir("txn_weekly_long_arm_appends_an_absent_unit")
        before = load_json(base / "before.json")
        after = load_json(base / "after.json")
        containers = container_diff(before, after)
        self.assertIn("/maps/0/items", containers)
        self.assertIn("/maps/0/items/600", containers)
        self.assertIn("/privateState/boughtUnits", containers)
        leaf_paths = set(entry["changed_leaf_paths"])
        for path in containers:
            self.assertNotIn(path, leaf_paths)


def rewards_document_leaves(document: Any) -> Dict[str, Any]:
    """The delivered projection, reimplemented from its documented rule.

    Kept local rather than imported so this module still runs when the envelope
    module is not importable, and so the check is against the **rule** (leaves, plus
    containers carrying a size marker) rather than against one implementation of
    it.  ``EndpointProjectionParityTests`` in ``test_rewards_endpoint.py`` asserts
    the rule and the implementation agree.
    """
    out: Dict[str, Any] = {}

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            out[path] = "<object:%d>" % len(node)
            for key in sorted(node):
                walk(node[key], "%s/%s" % (path, key))
        elif isinstance(node, list):
            out[path] = "<array:%d>" % len(node)
            for index, value in enumerate(node):
                walk(value, "%s/%d" % (path, index))
        else:
            out[path] = node

    walk(document, "")
    return out


# ------------------------------------------------------- pinned observations --
class RecordedOutcomeTests(unittest.TestCase):
    """The specific recorded results, pinned by value.

    These are the findings the contract rests on, and each one is a claim about
    the **oracle** -- not about the delivered endpoint, which refuses every
    grant-shaped arm.  Four of the seven transactions are recorded as divergences
    and are labelled that way here rather than as parity.
    """

    def test_every_transaction_succeeded_with_the_legacy_success_body(self) -> None:
        for entry in transactions():
            name = entry["name"]
            self.assertEqual(entry["status"], 200, name)
            self.assertEqual(entry["response_payload"], {"result": "success"}, name)
            meta = load_json(step_dir(name) / "response.meta.json")
            self.assertEqual(meta["status"], 200, name)
            body = (step_dir(name) / "response.body").read_bytes()
            self.assertEqual(meta["body_bytes"], len(read_bytes_lf(step_dir(name) / "response.body")), name)
            self.assertEqual(meta["body_sha256"], committed_sha(step_dir(name) / "response.body"), name)

    def test_the_weekly_short_arm_grants_nothing_and_moves_two_leaves(self) -> None:
        entry = by_name("weekly_short_arm_grants_nothing")
        self.assertEqual(entry["args_sent"], [])
        self.assertEqual(entry["arm"], "short")
        self.assertEqual(entry["changed_leaf_count"], 2)
        self.assertEqual(
            sorted(entry["changed_leaf_paths"]),
            sorted(["/privateState/timeStampMondayBonus", "/privateState/weeklyRewardIndex"]),
        )
        self.assertEqual(entry["placed_rows_before"], entry["placed_rows_after"])
        self.assertTrue(entry["unit_list_byte_identical"])
        self.assertTrue(entry["storage_byte_identical"])
        self.assertTrue(entry["only_the_cursor_and_instant_moved"])

    def test_the_weekly_long_arm_places_a_row_and_appends_an_absent_unit(self) -> None:
        entry = by_name("weekly_long_arm_appends_an_absent_unit")
        self.assertEqual(entry["args_sent"], [600, 1198, 58, 47, 1])
        self.assertEqual(entry["argument_count"], 5)
        self.assertEqual(entry["arm"], "long")
        self.assertEqual(entry["placed_rows_after"], entry["placed_rows_before"] + 1)
        self.assertEqual(
            entry["unit_list_length_after"], entry["unit_list_length_before"] + 1
        )
        self.assertFalse(entry["unit_list_byte_identical"])
        self.assertFalse(entry["only_the_cursor_and_instant_moved"])
        self.assertTrue(entry["grant_is_client_sent"])
        self.assertFalse(entry["parity_with_delivered_endpoint"])
        self.assertEqual(entry["divergence"], "arity_selects_the_arm")

    def test_the_deduplicating_helper_is_observed_not_hypothesised(self) -> None:
        """Same arm, same arity, same cell, same team; only the item differs.

        ``engine.bought_unit_add`` (``engine.py:86-89``) appends **only when the id
        is absent**, so steps 2 and 3 are the pair that makes the deduplication
        visible: a row is placed in both, the unit list grows in one and stands
        still in the other.  An earlier draft of this fixture described step 3 as a
        hypothetical; it was executed, and it is pinned here as recorded.
        """
        appending = by_name("weekly_long_arm_appends_an_absent_unit")
        present = by_name("weekly_long_arm_deduplicates_a_present_unit")
        for field in ("arm", "argument_count", "placed_cell_sent", "placed_player_sent"):
            self.assertEqual(appending[field], present[field], field)
        self.assertNotEqual(appending["args_sent"][1], present["args_sent"][1])
        self.assertEqual(
            appending["unit_list_length_after"], appending["unit_list_length_before"] + 1
        )
        self.assertEqual(
            present["unit_list_length_after"], present["unit_list_length_before"]
        )
        self.assertTrue(
            present["unit_list_byte_identical"],
            "the present-id arm must leave the unit list byte-identical; the "
            "deduplicating half of engine.bought_unit_add did not reproduce",
        )
        self.assertEqual(
            present["placed_rows_after"], present["placed_rows_before"] + 1
        )
        # One leaf fewer than the appending arm, and the missing one is exactly the
        # appended list element.  This is the pair that makes the rule visible: same
        # arm, same arity, same cell, same team, a row placed in both -- and the
        # only difference in the whole document is that one list element.
        self.assertEqual(
            len(present["changed_leaf_paths"]), appending["changed_leaf_count"] - 1
        )
        # Compared only over the unit-list prefix.  The two arms also place rows at
        # DIFFERENT client-sent indexes (600 against 601), so every placed-row leaf
        # differs between them too and a whole-path subtraction is meaningless --
        # an earlier draft of this test did exactly that and the assertion failed
        # on eight row paths while saying nothing about the rule it was named for.
        self.assertEqual(
            [
                path
                for path in appending["changed_leaf_paths"]
                if path.startswith("/privateState/boughtUnits/")
            ],
            [
                "/privateState/boughtUnits/%d"
                % appending["unit_list_length_before"]
            ],
            "the appending arm's only unit-list leaf is the appended element",
        )
        self.assertEqual(
            [
                path
                for path in present["changed_leaf_paths"]
                if path.startswith("/privateState/boughtUnits/")
            ],
            [],
            "the present-id arm moved a unit-list leaf, so the deduplicating half "
            "of the helper did not reproduce",
        )
        # And the two placed-row sets differ only by their client-sent index, with
        # the same row shape -- so the row half really is arm-independent.
        self.assertEqual(
            [path for path in appending["changed_leaf_paths"] if "/items/" in path],
            ["/maps/0/items/%d/%d" % (appending["args_sent"][0], slot) for slot in (0, 1, 2, 3, 4, 7)],
        )
        self.assertEqual(
            [path for path in present["changed_leaf_paths"] if "/items/" in path],
            ["/maps/0/items/%d/%d" % (present["args_sent"][0], slot) for slot in (0, 1, 2, 3, 4, 7)],
        )

    def test_the_daily_resources_arm_grants_nothing(self) -> None:
        entry = by_name("daily_short_arm_grants_nothing")
        self.assertEqual(entry["args_sent"], [0, 2])
        self.assertEqual(entry["arm"], "resources")
        self.assertEqual(entry["changed_leaf_count"], 2)
        self.assertTrue(entry["only_the_cursor_and_instant_moved"])

    def test_one_daily_grant_lands_in_two_places_by_two_different_rules(self) -> None:
        """The deduplicating unit list and the **accumulating** store, at once.

        ``engine.add_store_item`` (``engine.py:70-75``) increments an existing key
        rather than skipping it, so one granted id reaches two landing places under
        two different rules.  The seed's storage is **empty**, which is the only
        reason this is observable at all.
        """
        entry = by_name("daily_granting_arm_lands_in_storage")
        self.assertEqual(entry["args_sent"], [1198, 3])
        self.assertEqual(entry["arm"], "granting")
        self.assertEqual(entry["storage_before"], {})
        self.assertEqual(entry["storage_after"], {"1198": 1})
        self.assertFalse(entry["storage_byte_identical"])
        self.assertEqual(entry["placed_rows_before"], entry["placed_rows_after"])
        # The unit list was already carrying 1198 from step 2, so the
        # deduplicating helper left it alone -- which is what makes the pair
        # observable rather than two independent grants.
        self.assertEqual(
            entry["unit_list_length_after"], entry["unit_list_length_before"]
        )
        self.assertTrue(
            entry["unit_list_byte_identical"],
            "the deduplicating helper must leave the list byte-identical when the "
            "id is already present; recorded as changed, so the helper's skip half "
            "did not reproduce",
        )
        # Byte-identical, not merely the same length: the helper returns without
        # writing, and a length check alone would pass a list rewritten with the
        # same elements in a different order.
        self.assertEqual(
            set(entry["storage_after"]) - set(entry["storage_before"]),
            {"%s" % entry["args_sent"][0]},
            "the accumulating helper must add exactly the client-sent id",
        )
        # ...and this one step really did touch both landing places' rules at once:
        # the storage grew by exactly one key while the list grew by nothing.
        self.assertEqual(
            set(entry["changed_leaf_paths"]),
            {
                "/maps/0/store/%s" % entry["args_sent"][0],
                "/privateState/%s" % DAILY_CURSOR,
                "/privateState/%s" % DAILY_STAMP,
            },
            "the granting daily arm must touch exactly the storage, the cursor, "
            "and the instant",
        )

    def test_an_oversized_next_id_moves_the_recorded_cursor_backwards(self) -> None:
        """``command.py:446`` then ``:451-452``: the sharpest divergence, executed.

        The branch computes ``next_id = args[1] + 1`` from the **client** and then
        overwrites anything above the literal ``5`` with ``1``, so a client that
        sent 99 moved the recorded cursor 4 -> 1.  This is visible in the preserved
        source; the fixture executes it rather than arguing it.
        """
        entry = by_name("daily_oversized_next_id_moves_the_cursor_backwards")
        self.assertEqual(entry["args_sent"], [0, 99])
        self.assertEqual(entry["cursor_before"], 4)
        self.assertEqual(entry["cursor_after"], 1)
        self.assertTrue(entry["cursor_moved_backwards"])
        self.assertLess(entry["cursor_after"], entry["cursor_before"])
        self.assertEqual(entry["changed_leaf_count"], 2)
        self.assertEqual(entry["parity_with_delivered_endpoint"], False)
        self.assertEqual(entry["divergence"], "client_supplied_next_id")
        # The delivered endpoint derives 5 from the recorded 4, not 1.
        self.assertEqual(entry["modern_derives_after"], 5)
        self.assertTrue(entry["modern_differs_from_oracle"])

    def test_the_step_after_the_backwards_move_depends_on_it(self) -> None:
        """Without step 7 the ladder could not show the dependency exists."""
        backwards = by_name("daily_oversized_next_id_moves_the_cursor_backwards")
        after = by_name("daily_after_the_backwards_move")
        self.assertEqual(after["cursor_before"], backwards["cursor_after"])
        self.assertEqual(after["cursor_after"], 2)
        self.assertEqual(after["args_sent"], [0, 1])

    def test_parity_is_claimed_for_exactly_three_of_seven_transactions(self) -> None:
        """Three parity, four divergences, **three divergence classes**.

        The three counts are different numbers and every one of them is asserted,
        because the manifest used to carry a single key named ``count`` beside a
        block named ``three_divergences``, and a reader comparing the two saw 3
        against 4 and no explanation.  The two arity transactions share a class:
        steps 2 and 3 are the same arm with the same five arguments, differing only
        in whether the client-sent id was already in the unit list.
        """
        parity = sorted(
            entry["name"]
            for entry in transactions()
            if entry["parity_with_delivered_endpoint"]
        )
        expected_parity = [
            "daily_after_the_backwards_move",
            "daily_short_arm_grants_nothing",
            "weekly_short_arm_grants_nothing",
        ]
        self.assertEqual(parity, expected_parity)
        self.assertEqual(
            sorted(manifest()["divergences"]["parity_claimed_for"]), expected_parity
        )

        divergences = manifest()["divergences"]
        self.assertEqual(len(divergences["transactions"]), 4)
        self.assertEqual(divergences["transaction_count"], 4)
        self.assertEqual(
            len(transactions()) - len(expected_parity),
            divergences["transaction_count"],
            "the recorded divergence count does not account for every non-parity "
            "transaction",
        )
        self.assertEqual(divergences["class_count"], 3)
        self.assertEqual(
            sorted(divergences["divergence_classes"]),
            ["arity_selects_the_arm", "client_supplied_item", "client_supplied_next_id"],
        )
        self.assertEqual(
            sorted(
                item["divergence"] for item in divergences["transactions"]
            ),
            [
                "arity_selects_the_arm",
                "arity_selects_the_arm",
                "client_supplied_item",
                "client_supplied_next_id",
            ],
            "the two arity transactions must be the pair that shares one class",
        )
        # Every parity row must be the non-granting arm, or parity would be claimed
        # for a step that granted something the delivered route refuses.
        for name in expected_parity:
            entry = by_name(name)
            self.assertTrue(
                entry["only_the_cursor_and_instant_moved"],
                "%s claims parity but its whole-document leaf diff is not exactly "
                "the cursor and the instant" % name,
            )
            self.assertTrue(entry["storage_byte_identical"], name)
            self.assertTrue(entry["unit_list_byte_identical"], name)
            self.assertEqual(
                entry["placed_rows_after"], entry["placed_rows_before"], name
            )
            self.assertNotIn("divergence", entry, name)
        self.assertTrue(divergences["recorded_not_narrowed"])

    def test_the_sixth_position_names_no_weekly_schedule_entry(self) -> None:
        """The line's finding, reached from recorded state rather than argued.

        The derived weekly bound is 5 while the committed schedule holds 3 entries,
        so positions 3 and 4 answer nothing -- and step 1's recorded successor is
        exactly one of them.  Step 2 then wraps to 0, which does answer.
        """
        first = by_name("weekly_short_arm_grants_nothing")
        self.assertEqual(first["cursor_after"], 4)
        self.assertTrue(first["successor_unaddressable"])
        self.assertEqual(first["weekly_schedule_cardinality"], 3)
        second = by_name("weekly_long_arm_appends_an_absent_unit")
        self.assertEqual(second["cursor_after"], 0)
        # The record carries the flag only where it is TRUE, so "not recorded" is
        # the negative case -- asserted as absence rather than read with ``[]``,
        # which on a missing key raises and reports a shape error instead of the
        # claim being tested.
        self.assertNotIn(
            "successor_unaddressable",
            second,
            "the wrapping successor 0 answers position 0 of a three-entry "
            "schedule, so it must not be recorded as unaddressable",
        )
        self.assertIn("note_on_the_gap", first)

    def test_every_step_records_its_printed_branch_line(self) -> None:
        """The printed lines are evidence; a missing one would be a silent hole.

        An earlier capture in this repository matched on a trailing token and
        silently dropped one branch's line, which is the single line a display-only
        proof depended on.  One line per step is asserted rather than "at least
        one", so the same class of hole cannot recur.
        """
        for entry in transactions():
            name = entry["name"]
            lines = entry["printed_branch_lines"]
            self.assertEqual(len(lines), 1, "%s recorded %d lines" % (name, len(lines)))
            self.assertIn(entry["command"], lines[0], name)
            self.assertIn(entry["printed_message"], lines[0], name)
            self.assertTrue(entry["stdout_evidence_is_this_request_only"], name)

    def test_the_three_item_messages_name_committed_content(self) -> None:
        """Derived from committed content, never transcribed.

        An earlier draft hardcoded ``"Won Metal Draggy"``.  Item 1055 is in fact
        ``Mr. Treat``, so the literal was both unfaithful and unmaintainable.  The
        guard that would have caught it is this one: every message that names an
        item must render the item's committed ``name``.

        Three of the seven steps name an item -- the two weekly granting arms and
        the daily granting arm -- and four name none.  The four are not ignored:
        each is pinned to the branch's own fixed string below, so a branch that
        started printing a name on an arm that grants nothing would fail here
        rather than slip past as an uninteresting ``None``.

        The capture derives the name from ``config/main.json`` via
        ``get_name_from_item_id``'s rule (``get_game_config.py:127``); the
        definitions are re-read here from the normalized package, so the two are
        independent reads of committed content.
        """
        named = [
            entry
            for entry in transactions()
            if entry["printed_message_names_a_committed_item"] is not None
        ]
        self.assertEqual(
            sorted(entry["name"] for entry in named),
            [
                "daily_granting_arm_lands_in_storage",
                "weekly_long_arm_appends_an_absent_unit",
                "weekly_long_arm_deduplicates_a_present_unit",
            ],
            "the number or identity of the steps that name an item changed",
        )
        definitions = {
            str(row["legacy_id"]): row
            for row in json.loads(
                (
                    harness.REPO_ROOT
                    / "packages"
                    / "game-content"
                    / "normalized"
                    / "units.json"
                ).read_text(encoding="utf-8")
            )
        }
        for entry in transactions():
            item_id = entry["printed_message_names_a_committed_item"]
            if item_id is None:
                self.assertIsNone(entry["printed_message_item_name_committed"])
                self.assertNotIn("%s", entry["printed_message_template"], entry["name"])
                self.assertNotIn("%", entry["printed_message"], entry["name"])
                self.assertIn(
                    entry["printed_message"],
                    ("Won resources", "Rewarded resources"),
                    "%s: an arm that grants nothing must print one of the "
                    "branches' two fixed strings" % entry["name"],
                )
                continue
            self.assertIn("%s", entry["printed_message_template"], entry["name"])
            committed = definitions[str(item_id)]["name"]
            self.assertEqual(
                entry["printed_message_item_name_committed"],
                committed,
                "%s: the capture recorded a committed name that differs from the "
                "normalized package's" % entry["name"],
            )
            self.assertEqual(
                entry["printed_message"],
                entry["printed_message_template"] % committed,
                "%s: the recorded message is not its own template with the "
                "committed name substituted" % entry["name"],
            )
            # The printed name must be the name of the item the client SENT --
            # which is the divergence this line is about: the message agrees with
            # the client, and nothing in the server derived it.
            self.assertIn(
                str(item_id),
                str(entry["args_sent"]),
                "%s names item %s, which is not among the client-sent arguments; "
                "the name came from somewhere other than the request"
                % (entry["name"], item_id),
            )

    def test_the_stamped_instant_is_compared_by_shape_never_by_value(self) -> None:
        """A wall clock cannot be pinned to a constant, so the record does not try."""
        for entry in transactions():
            name = entry["name"]
            self.assertTrue(entry["instant_is_volatile"], name)
            self.assertEqual(entry["instant_after_shape"], "int", name)
            self.assertEqual(
                entry["instant_key"],
                STAMP_KEY_FOR_COMMAND[entry["command"]],
                "%s: the recorded instant key is not the one this command stamps" % name,
            )
            self.assertIn("shape only", entry["instant_compared_by"], name)
            self.assertIn(
                "/privateState/%s" % entry["instant_key"], entry["changed_leaf_paths"], name
            )


# ------------------------------------------------------------ manifest claims --
class ManifestIntegrityTests(unittest.TestCase):
    """The manifest's and the README's own figures, against the bytes on disk."""

    def test_the_schema_and_exit_code_are_the_ones_this_line_declares(self) -> None:
        self.assertEqual(manifest()["schema"], SCHEMA)
        self.assertEqual(manifest()["exit_code"], 0)
        self.assertEqual(
            manifest()["invocation"], "python -B apps/compat-api/capture_rewards_fixture.py"
        )

    def test_the_readme_inventory_matches_the_bytes_on_disk(self) -> None:
        """The size a reviewer reads first, measured rather than remembered.

        Every byte count here is **LF-normalised**.  This repository sets
        ``core.autocrlf=true`` with no ``.gitattributes`` entry for
        ``tests/fixtures/**``, so a CRLF checkout holds the same committed content
        in more bytes with nothing changed; a guard measured with ``st_size`` would
        be a line-ending detector.  That defect was found and fixed once in this
        project (PR #280) and is not reintroduced here.

        The README is itself a file in the directory it describes, which is the
        fixed-point problem: it cannot state its own byte count.  The README
        therefore excludes itself and says so, and this test asserts exactly that
        convention -- the capture-output inventory, the capture-output byte total,
        and the directory total, which must exceed the first by exactly one.
        """
        readme = README_PATH.read_text(encoding="utf-8")
        match = re.search(
            r"\*\*(\d+) capture-output files, ([\d,]+) bytes\*\*", readme
        )
        self.assertIsNotNone(
            match,
            "the README no longer states its inventory in the asserted form "
            "'**N capture-output files, B bytes**'",
        )
        stated_files = int(match.group(1))
        stated_bytes = int(match.group(2).replace(",", ""))

        capture_files = 0
        capture_bytes = 0
        state_documents = 0
        for path in FIXTURES.rglob("*"):
            if not path.is_file() or path == README_PATH:
                continue
            capture_files += 1
            capture_bytes += len(read_bytes_lf(path))
            if path.name in ("before.json", "after.json"):
                state_documents += 1

        self.assertEqual(
            stated_files,
            capture_files,
            "the README states %d capture-output files but the directory holds %d"
            % (stated_files, capture_files),
        )
        # The byte TOTAL is bounded, not exact, and the bound is stated rather than
        # implied.  Both branches stamp the wall clock unconditionally, so each
        # recorded instant is a fresh ten-digit number and the byte total moves by
        # a few tens of bytes between runs -- measured: 1,816,142 then 1,816,177 on
        # two consecutive runs of this same capture.  An exact-byte assertion
        # would therefore fail on every rerun of a perfectly good capture, which is
        # how a guard teaches people to ignore it.
        self.assertGreaterEqual(
            capture_bytes,
            stated_bytes,
            "the README states %d bytes but the capture output holds %d -- fewer "
            "than the stated floor" % (stated_bytes, capture_bytes),
        )
        self.assertLessEqual(
            capture_bytes,
            stated_bytes + BYTE_TOTAL_TOLERANCE,
            "the README states %d bytes but the capture output holds %d -- more "
            "than the stated ceiling of +%d"
            % (stated_bytes, capture_bytes, BYTE_TOTAL_TOLERANCE),
        )
        self.assertEqual(
            len([p for p in FIXTURES.rglob("*") if p.is_file()]),
            stated_files + 1,
            "the directory must hold exactly the stated files plus this README",
        )
        # Seven transactions plus one login step, each with a before and an after.
        self.assertEqual(state_documents, 16)

    def test_the_readme_also_states_the_kilobyte_figure(self) -> None:
        """The one figure stated twice, so a single edit cannot drift.

        ``round`` rather than a floor, so this test can tell a rounding change from
        a byte-total change.  The figure is then stated in the README **and**
        recomputed here from the same tolerance window the byte test uses, so the
        two cannot disagree by more than the volatility they share.
        """
        readme = README_PATH.read_text(encoding="utf-8")
        total = sum(
            len(read_bytes_lf(path))
            for path in FIXTURES.rglob("*")
            if path.is_file() and path != README_PATH
        )
        self.assertEqual(round(total / 1024.0), 1774)
        self.assertIn(
            "%s KB" % format(round(total / 1024.0), ","),
            readme,
            "the README's KB figure is not %d KB" % round(total / 1024.0),
        )
        self.assertIn(
            "%d-byte ceiling" % BYTE_TOTAL_TOLERANCE,
            readme,
            "the README must state the ceiling its byte figure is measured "
            "against, or the bound is an invention in the test",
        )

    def test_the_readme_states_the_one_server_and_the_clock_collision(self) -> None:
        readme = " ".join(README_PATH.read_text(encoding="utf-8").split())
        for phrase in (
            "No Flash, Ruffle, ActionScript, or browser executes",
            "loopback to `127.0.0.1:5055`",
            "`sessions.load_saves()` caches the corpus in a module global **at import time**",
            "`playerInfo.pid`",
            "`await_clock_past()`",
            "37 of the 48 files differed",
            "must **recompute** each transaction's state digest",
            "test_rewards_parity.py",
        ):
            self.assertIn(phrase, readme, "the README no longer states: %r" % phrase)

    def test_the_readme_never_calls_the_divergences_parity(self) -> None:
        """Asserted as the presence of the disclaimer, not the absence of a word."""
        readme = " ".join(README_PATH.read_text(encoding="utf-8").split()).lower()
        self.assertIn("never called parity", readme)
        self.assertIn("recorded, never called parity", readme)
        for phrase in (
            "no price is claimed in either direction",
            "parity is claimed for exactly **three** transactions",
            "four** transactions diverge from the delivered route, across **three**",
        ):
            self.assertIn(phrase, readme, "the README no longer states: %r" % phrase)

    def test_the_seed_digest_matches_the_committed_seed(self) -> None:
        self.assertEqual(manifest()["seed"]["sha256"], committed_sha(SEED_PATH))

    def test_the_recorded_census_matches_a_fresh_measurement(self) -> None:
        seed = load_json(SEED_PATH)
        census = manifest()["seed"]["census"]
        private = private_state(seed)
        self.assertEqual(census["placed_rows"], len(placed_rows(seed)))
        self.assertEqual(census["unit_list_length"], len(private["boughtUnits"]))
        self.assertEqual(census["storage"], seed["maps"][0]["store"])
        self.assertEqual(census["resource_slot_count"], len(RESOURCE_SLOTS))
        self.assertEqual(sorted(census["resource_slots"]), sorted(RESOURCE_SLOTS))
        self.assertEqual(
            census["pid_read_from_document"], str(seed["playerInfo"]["pid"])
        )
        self.assertEqual(census["pid_read_from_document"], "Neutral")
        self.assertTrue(census["storage_is_empty_so_the_grant_lands_visibly"])
        # The committed census is a measurement of THIS document.  For THIS seed the
        # pid happens to agree with the filename stem, so the claim that a stem is
        # never a substitute for the document is asserted where it is actually
        # observable: over every committed village save, measured here rather than
        # inherited from the contract.
        self.assertEqual(census["pid_read_from_document"], SEED_PATH.stem)
        disagreeing = []
        for path in sorted((harness.REPO_ROOT / "villages").glob("*.json")):
            document = load_json(path)
            if str(document["playerInfo"]["pid"]) != path.stem:
                disagreeing.append(path.name)
        self.assertEqual(
            disagreeing,
            ["General_Mike_30.json", "General_Mike_31.json", "initial.json"],
            "the set of village saves whose playerInfo.pid disagrees with the "
            "filename changed; the pid must be read from the document",
        )
        self.assertEqual(
            len(list((harness.REPO_ROOT / "villages").glob("*.json"))),
            8,
            "the census of village saves changed, so the count above is no longer "
            "the fraction this line recorded",
        )

    def test_containment_is_recorded_as_identical(self) -> None:
        containment = manifest()["containment"]
        self.assertEqual(containment["combined_before"], containment["combined_after"])
        # Pinned by PREFIX and by length, not by the full digest.  The containment
        # digest is a function of every byte of every prior fixture plus the seed,
        # so pinning it whole would turn any future legitimate fixture addition
        # into a red suite -- and the exact-suffix form of this assertion in an
        # earlier draft of these tests was simply wrong, pinning a 16-character
        # truncation against a 64-character hex digest.
        self.assertEqual(len(containment["combined_before"]), 64)
        self.assertEqual(len(containment["combined_after"]), 64)
        self.assertTrue(
            containment["combined_before"].startswith("18e5e55ba85473bb"),
            "the containment digest changed: %s" % containment["combined_before"],
        )
        self.assertTrue(containment["identical"])
        self.assertEqual(
            containment["seed_sha256_before"], containment["seed_sha256_after"]
        )
        self.assertEqual(containment["seed_sha256_before"], committed_sha(SEED_PATH))
        self.assertTrue(containment["working_tree_saves_absent"])
        self.assertTrue(containment["protected_fixtures_unchanged"])
        self.assertEqual(
            sorted(containment["protected_fixtures"]),
            sorted(
                path.name
                for path in (harness.REPO_ROOT / "tests" / "fixtures").iterdir()
                if path.is_dir() and path.name != FIXTURES.name
            ),
            "the protected-fixture list must be every other committed fixture "
            "directory, or a new predecessor could be skipped silently",
        )

    def test_the_protected_fixture_list_is_twenty_and_names_every_one(self) -> None:
        """Counted, and matched against the directories on disk.

        The README's containment table said "19" and the capture records 20,
        because ``godot-unit-experience`` joined the set after that sentence was
        written.  The number is asserted here so it cannot drift silently again.
        """
        protected = list(manifest()["containment"]["protected_fixtures"])
        self.assertEqual(len(protected), 20)
        self.assertEqual(len(set(protected)), len(protected))
        self.assertIn("godot-damage", protected)
        self.assertNotIn(FIXTURES.name, protected)
        self.assertIn(
            "20 prior committed fixture directories",
            " ".join(README_PATH.read_text(encoding="utf-8").split()),
        )

    def test_the_capture_names_every_prior_fixture_in_its_own_pins(self) -> None:
        """The capture's own constant must be the same set, or containment is a claim."""
        source = CAPTURE_PATH.read_text(encoding="utf-8")
        protected = list(manifest()["containment"]["protected_fixtures"])
        for name in protected:
            self.assertIn(
                '"%s"' % name,
                source,
                "the capture does not name %r, so it could not have protected it"
                % name,
            )
        # One definition plus one use in each of the three places the set is consumed:
# the pre-run snapshot, the post-run comparison, and the manifest record.  Pinned
# because a fourth use could widen what the set protects without this file
# noticing, and a second definition could shadow the first.
        self.assertEqual(source.count("\nPROTECTED_FIXTURES = ("), 1)
        self.assertEqual(source.count("PROTECTED_FIXTURES") - 1, 3)
        self.assertEqual(len(protected), 20)

    def test_the_seed_was_never_written_by_the_capture(self) -> None:
        """The capture is handed a disposable copy; the committed seed is read-only.

        Asserted by looking for any write-shaped call **whose first argument is the
        seed constant**, not by the absence of a bare write helper.  The earlier
        form of this test asserted ``write_bytes`` never appears anywhere in the
        capture, which is false for a good reason -- the capture writes every
        recorded ``response.body`` -- and a guard that must be false is a guard
        that gets deleted rather than fixed.
        """
        source = CAPTURE_PATH.read_text(encoding="utf-8")
        self.assertIn("build_disposable(", source)
        self.assertNotIn("SEED.write", source)
        self.assertNotIn("SEED.unlink", source)
        writes = re.findall(
            r"\b(?:write\w*|copy\w*|rmtree|rename|unlink|touch|mkdir\w*)\(\s*SEED\b",
            source,
        )
        self.assertEqual(
            writes,
            [],
            "the capture appears to write through the committed seed: %r" % writes,
        )
        # And the positive form: the seed is read, and its digest is checked
        # against the disposable copy the harness made from it.
        self.assertIn("SEED.read_text", source)
        self.assertIn("seed_target_of(", source)
        self.assertIn("committed_digest(SEED", source)

    def test_every_disposable_and_server_was_torn_down(self) -> None:
        self.assertEqual(manifest()["cleanup"]["disposables"], 1)
        self.assertEqual(manifest()["server"]["starts"], 1)
        self.assertEqual(manifest()["server"]["port"], 5055)
        self.assertEqual(manifest()["server"]["host"], "127.0.0.1")
        self.assertTrue(manifest()["server"]["one_server_for_the_whole_sequence"])

    def test_the_declared_exit_codes_are_distinct_and_ordered(self) -> None:
        source = CAPTURE_PATH.read_text(encoding="utf-8")
        for name in ("EXIT_OK", "EXIT_ENVIRONMENT", "EXIT_CONTAINMENT", "EXIT_REQUEST",
                     "EXIT_SERVER", "EXIT_PORT_BUSY"):
            self.assertIn(name, source, name)


# ------------------------------------------------- capture-contract assertions --
class CaptureContractTests(unittest.TestCase):
    """The seams this capture added, pinned so they stay non-breaking.

    ``build_disposable`` grew a defaulted ``seed_path`` parameter so a capture
    could seed a committed village document rather than the fresh-player corpus.
    The property that made that safe -- every pre-existing call site passed a single
    positional argument -- decays the moment a call site passes a second one, at
    which point some other capture has silently acquired a non-fresh corpus and its
    committed fixture's corpus assumptions need rechecking.  The guard lives in
    ``test_unit_xp_fixture.py`` and declares the seeded captures by name; this
    capture must be one of them, and that membership is asserted here so the
    exemption cannot widen silently.
    """

    def test_build_disposable_still_defaults_its_seed_parameter(self) -> None:
        harness_source = (COMPAT_DIR / "capture_legacy_fixtures.py").read_text(
            encoding="utf-8"
        )
        signature = re.search(
            r"^def build_disposable\(\s*(.*?)\)\s*->", harness_source, re.S | re.M
        )
        self.assertIsNotNone(signature, "build_disposable was not found")
        text = signature.group(1)
        self.assertIn("seed_path", text)
        self.assertIn("FRESH_PLAYER_SAVE", text)

    def test_this_capture_is_a_declared_seeded_capture(self) -> None:
        """One call site, one seed, and the seed is the village corpus.

        The argument text is extracted by a **balanced-paren** scan rather than by
        ``[^)]*``.  The capture's real call site is
        ``build_disposable(\\n    Path(tempfile.gettempdir()), SEED\\n)``, and a
        non-greedy ``[^)]*`` stops at the ``)`` of ``gettempdir(`` -- so it
        reported an argument string with no ``SEED`` in it and the assertion read
        as "the seed constant is absent from the call site" when the seed constant
        is the second argument of it.
        """
        source = CAPTURE_PATH.read_text(encoding="utf-8")
        calls = call_argument_texts(source, "build_disposable")
        self.assertEqual(
            len(calls), 1, "expected exactly one build_disposable call site"
        )
        arguments = calls[0]
        self.assertIn("SEED", arguments)
        self.assertEqual(
            count_top_level_commas(arguments),
            1,
            "the call site must pass exactly one seed",
        )
        self.assertIn("villages", str(SEED_PATH).replace("\\", "/"))
        self.assertEqual(SEED_PATH.parent.name, "villages")

    def test_the_rewards_capture_is_registered_as_a_seeded_capture(self) -> None:
        """Membership is by name, so a new capture cannot inherit the exemption.

        ``build_disposable`` grew a defaulted second parameter, and the guard in
        ``test_unit_xp_fixture.py`` is the one place that knows which captures are
        deliberate exceptions.  This capture is an exception -- it seeds from a
        committed village document, not the fresh-player corpus -- so it has to be
        declared there, and this asserts the declaration exists.  Without it the
        structural guard counts this capture among the pinned single-argument call
        sites and fails.
        """
        xp = (harness.TESTS_DIR / "test_unit_xp_fixture.py").read_text(encoding="utf-8")
        self.assertIn('"capture_rewards_fixture.py"', xp)
        block = re.search(
            r"SEEDED_CAPTURE_NAMES\s*=\s*frozenset\(\s*\{(.*?)\}\s*\)", xp, re.S
        )
        self.assertIsNotNone(block, "SEEDED_CAPTURE_NAMES was not found")
        members = re.findall(r'"([^"]+)"', block.group(1))
        self.assertIn("capture_rewards_fixture.py", members)
        # The owning suite names itself through a variable, so it is not a literal
        # inside the set; the block must still reference it by that name.
        self.assertIn("OWN_CAPTURE_NAME", block.group(1))
        own = re.search(r'OWN_CAPTURE_NAME\s*=\s*"([^"]+)"', xp)
        self.assertIsNotNone(own, "OWN_CAPTURE_NAME was not found")
        for name in members:
            self.assertTrue((harness.REPO_ROOT / "apps" / "compat-api" / name).is_file(),
                            "%s is declared but absent" % name)
        # And the guard still pins the same number of NON-seeded call sites, which
        # is the property that joining the set is supposed to leave untouched.
        self.assertIn("            17,\n", xp)

    def test_the_capture_does_not_import_the_module_built_on_its_own_output(self) -> None:
        """The recorder must not import the service that replays its own records.

        The capture legitimately imports ``rewards_envelope`` -- it re-derives the
        weekly bound and the per-action argument counts from the same module the
        endpoint uses, so a content change fails both rather than one -- and that
        is asserted as a POSITIVE below.  What it must never import is
        ``compat_service``, the module whose entire job is to read this fixture;
        a recorder importing its own reader would make the fixture and its
        interpreter share a bug.
        """
        source = CAPTURE_PATH.read_text(encoding="utf-8")
        body = source.split("def main(", 1)[0]
        self.assertNotIn(
            "import compat_service",
            body,
            "the capture must not import the module built on its own output; "
            "that is the endpoint's job, not the recorder's",
        )
        self.assertNotIn("import compat_service", source)
        # The positive form: the derivation module IS imported, and used by name
        # rather than only imported.
        self.assertIn("import rewards_envelope", body)
        self.assertGreaterEqual(
            source.count("rewards_envelope."), 10,
            "the capture imports rewards_envelope but barely uses it, which would "
            "make the import a seam rather than a shared derivation",
        )
        for attribute in (
            "rewards_envelope.weekly_bound",
            "rewards_envelope.WEEKLY_SCHEDULE_KEY",
            "rewards_envelope.DAILY_BOUND_LITERAL",
            "rewards_envelope.ACTION_ARGUMENT_COUNT",
            "rewards_envelope.ACTION_FOR_COMMAND",
            "rewards_envelope.CURSORS",
        ):
            self.assertIn(attribute, source, attribute)