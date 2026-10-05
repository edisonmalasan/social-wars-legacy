#!/usr/bin/env python3
"""Offline integrity guard for the executed-legacy unit-experience fixture.

Change: ``unit-experience-evidence``, task group 3.

**Why this module exists at all.** Every other capture in this repository is replayed
against a Compatibility API endpoint, and its parity test compares the endpoint's
response with the captured legacy one. This line has **no endpoint** — deliberately,
because the branch's amount is a client argument with no validation and the committed
per-unit experience field is refuted as its source by three independent measurements.
So there is nothing to replay *against*, and the meaningful guard is a different one:
the fixture **is** the evidence, and an evidence artefact nobody re-checks is a claim,
not evidence. This module therefore recomputes, offline and with no server and no
network, every structural claim the committed fixture makes about itself.

What it checks:

1. Per transaction, the recorded changed-leaf set equals the leaf diff **recomputed**
   from the recorded ``before.json`` / ``after.json`` documents — the states, not the
   summary.  The recomputation is over the full 2322-leaf document, so "exactly one
   leaf moved" is a claim about the whole save and not about one row.
2. The digest over **every leaf outside** the claimed set is equal before and after, so
   no second change hides anywhere the summary does not mention.
3. Every stored resource is unchanged, and every recorded batch carries the **neutral**
   vector — so the resource result is not an artefact of a vector nobody checked.
4. The manifest's recorded digests and corpus census still match a fresh measurement
   over the committed bytes.
5. The repository-wide census figures the contract rests on are **re-measured here**,
   not copied from the fixture.
6. The anti-invention guard: the Compatibility API answers **no** unit-experience
   route and contains **no** award helper — pinned structurally, so it fails loudly if
   either ever appears.
7. The capture-harness seam this line added stays **defaulted**: every
   ``build_disposable(`` call site under ``apps/compat-api/`` passes at most one
   argument.  If a future edit begins passing a second one, some other capture has
   silently acquired a non-fresh corpus and the assumptions of those fixtures need
   rechecking — which must be a failure, not a surprise.

No server, no network, no Flash, no Ruffle, no ActionScript, no browser.
"""

import io
import json
import re
import socket
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import compat_test_harness as harness

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-unit-experience"
STEPS_DIR = FIXTURES / "steps"
MANIFEST_PATH = FIXTURES / "capture-manifest.json"
README_PATH = FIXTURES / "README.md"
SEED_PATH = harness.REPO_ROOT / "villages" / "AcidCaos.json"
COMPAT_DIR = harness.REPO_ROOT / "apps" / "compat-api"
SERVICE_PATH = COMPAT_DIR / "compat_service.py"
HARNESS_PATH = COMPAT_DIR / "capture_legacy_fixtures.py"
UNITS_PATH = (
    harness.REPO_ROOT / "packages" / "game-content" / "normalized" / "units.json"
)

LOGIN_STEP = "login_post"

# The seven stored resource slots and their save locations, exactly as
# engine.apply_resources reads and writes them (engine.py:251-271). Three owners:
# five on the map, cash on playerInfo, mana on privateState.
RESOURCE_SLOTS: Dict[str, Tuple[str, ...]] = {
    "xp": ("maps", 0, "xp"),
    "gold": ("maps", 0, "gold"),
    "wood": ("maps", 0, "wood"),
    "oil": ("maps", 0, "oil"),
    "steel": ("maps", 0, "steel"),
    "cash": ("playerInfo", "cash"),
    "mana": ("privateState", "mana"),
}

NEUTRAL_VECTOR = [0, 0, 0, 0, 0, 0, 0, 0]
ADD_XP_UNIT_COMMAND = "add_xp_unit"

# This line's own capture. The build_disposable call sites permitted to pass a
# seed, because a line is the reason the parameter exists for it. AMENDED by the
# `combat-actions` line (M10 line 2): its capture seeds two committed village
# documents because the fresh-player corpus places ZERO unit rows, so the
# destruction and the ledger paths it records are unreachable against it. The
# guard is narrowed to a declared set rather than deleted -- a capture may join
# the set only by naming itself here, which is the review this pin exists to
# force.  AMENDED a second time by the `damage` line (M10 line 3): its capture
# seeds villages/Neutral.json because it is the ONLY committed corpus whose
# privateState.magics is non-empty, and an empty ledger is a ledger the increment
# arm cannot be observed against -- every key creation would look identical to
# every increment.  All ten committed save documents were measured and the other
# nine record an empty object.  Joining the set adds one call site and one
# exemption, so the pinned count stays at seventeen -- which is precisely why
# counting alone is a weak pin here and the exact-set assertion below has to be
# what catches a new capture.
OWN_CAPTURE_NAME = "capture_unit_xp_fixture.py"
SEEDED_CAPTURE_NAMES = frozenset(
    {OWN_CAPTURE_NAME, "capture_combat_fixture.py", "capture_magic_fixture.py"}
)

# Identifiers that would mean an award rule had been invented. Matched as
# SUBSTRINGS on purpose: an earlier by-name guard in this repository matched only
# the exact name and so missed a suffixed helper wearing the same disguise.
AWARD_FORBIDDEN_SUBSTRINGS = (
    "award_xp",
    "xp_award",
    "grant_xp",
    "xp_grant",
    "experience_for",
    "xp_for_level",
    "xp_schedule",
    "unit_xp_table",
)

# Route paths that would mean this line grew the endpoint it explicitly excludes.
UNIT_XP_ROUTE_FORBIDDEN_SUBSTRINGS = ("unit_xp", "unit-experience", "add_xp_unit")

_MANIFEST: Optional[Dict[str, Any]] = None
_TRANSACTIONS: List[Dict[str, Any]] = []
_WORKING_TREE_PRE: List[Dict[str, str]] = []


def manifest() -> Dict[str, Any]:
    global _MANIFEST
    if _MANIFEST is None:
        _MANIFEST = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return _MANIFEST


def transactions() -> List[Dict[str, Any]]:
    global _TRANSACTIONS
    if not _TRANSACTIONS:
        _TRANSACTIONS = list(manifest()["transactions"])
    return _TRANSACTIONS


def step_dir(name: str) -> Path:
    return STEPS_DIR / ("txn_%s" % name)


def step_facts(name: str) -> Dict[str, Any]:
    """The per-transaction facts as committed in that step's own directory.

    These are the authority for the leaf and resource claims. An earlier version
    of this module read the manifest's *copy* of the same facts and never opened
    ``transaction.json`` at all — so corrupting the committed per-step evidence
    was silently undetectable, which an injection proved. :func:`ManifestIntegrityTests`
    now also pins the two copies equal, so neither file can drift alone.
    """
    return load_json(step_dir(name) / "transaction.json")


def manifest_facts(name: str) -> Dict[str, Any]:
    for entry in transactions():
        if entry["name"] == name:
            return entry
    raise AssertionError("the manifest records no transaction named %r" % name)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def leaf_items(document: Any, prefix: str = "") -> List[Tuple[str, Any]]:
    """Every leaf as ``(json pointer path, value)``, in sorted path order."""
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


def canonical_json(value: Any) -> str:
    """Deterministic serialization; identical to the capture's, deliberately.

    Implemented here rather than imported from the capture so this module depends
    on the FIXTURE and not on the tool that wrote it. The two are cross-checked in
    :meth:`RecomputedLeafTests.test_our_leaf_digest_matches_the_recorded_one`.
    """
    return json.dumps(value, separators=(",", ":"), sort_keys=True, ensure_ascii=True)


def digest_of(entries: List[Tuple[str, str]]) -> str:
    """The capture's ``canonical_digest`` recipe, reimplemented and cross-checked.

    Verified against ``hashing.canonical_digest`` rather than guessed: SHA-256 over
    ordinal-sorted ``"<digest>  <path>\\n"`` lines -- digest FIRST, two spaces.
    The first version of this function had the order reversed and one space, which
    every digest comparison in this module still reported as a mismatch -- which is
    why :meth:`RecomputedLeafTests.test_our_leaf_digest_matches_the_recorded_one`
    exists to fail loudly when the two recipes drift apart.
    """
    import hashlib

    material = sorted(set(entries), key=lambda item: item[0])
    running = hashlib.sha256()
    for path, value in material:
        running.update(("%s  %s\n" % (value, path)).encode("utf-8"))
    return running.hexdigest()


def typed_equal(left: Any, right: Any) -> bool:
    """Equality that will not call ``1``, ``1.0`` and ``True`` the same value.

    Reimplemented rather than imported for the same reason as ``canonical_json``,
    and because this distinction is the point: the fixture records a boolean
    reaching the experience field, and a plain ``==`` would pass that row for the
    wrong reason.
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
    if isinstance(left, dict) and isinstance(right, dict):
        if sorted(left) != sorted(right):
            return False
        return all(typed_equal(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False
        return all(typed_equal(a, b) for a, b in zip(left, right))
    return left == right


def leaf_diff(before: Any, after: Any) -> List[Tuple[str, Any, Any, Any]]:
    """``(path, present_before, before, present_after, after)``, sorted by path."""
    left = {path: value for path, value in leaf_items(before)}
    right = {path: value for path, value in leaf_items(after)}
    out: List[Tuple[str, Any, Any, Any]] = []
    for path in sorted(set(left) | set(right)):
        in_left = path in left
        in_right = path in right
        if in_left and in_right and typed_equal(left[path], right[path]):
            continue
        out.append(
            (path, in_left, left.get(path), in_right, right.get(path))
        )
    return out


def unchanged_digest(document: Any, excluded: List[str]) -> str:
    skip = set(excluded)
    return digest_of(
        [
            (path, canonical_json(value))
            for path, value in leaf_items(document)
            if path not in skip
        ]
    )


def whole_state_digest(document: Any) -> str:
    return digest_of([(path, canonical_json(value)) for path, value in leaf_items(document)])


def stored_resources(document: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for name, location in RESOURCE_SLOTS.items():
        cursor: Any = document
        for step in location:
            cursor = cursor[step]
        out[name] = cursor
    return out


def code_only(path: Path) -> str:
    """A Python/GDScript/PS1 source with comments and docstrings removed.

    Written as a small two-state lexer rather than a chain of regexes, because
    this repository has already been bitten twice by comment-blind scans: a
    ``_code_only()`` helper on an earlier line's predecessor was passed a *path*
    instead of a body and so became vacuously true, and a single-state scanner
    desynchronised on an apostrophe inside a double-quoted string. The first
    version of this function then compared a two-character slice against ``"#"``,
    which never matches a shebang's ``"#!"`` -- so shebang lines were not stripped.
    :meth:`CodeOnlyLexTests` now tests this function directly against a synthetic
    source exercising every delimiter.
    """
    return code_only_text(path.read_text(encoding="utf-8"))


def code_only_text(text: str) -> str:
    out: List[str] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        pair = text[index : index + 2]
        if char == "#":
            while index < length and text[index] != "\n":
                index += 1
            continue
        triple = text[index : index + 3]
        if triple in ('"""', "'''"):
            close = text.find(triple, index + 3)
            if close == -1:
                # An unterminated docstring is a real problem, not something to
                # paper over: the scanner would otherwise treat the rest of the
                # file as a string and every guard below it would pass vacuously.
                raise AssertionError(
                    "code_only found an unterminated docstring at offset %d" % index
                )
            index = close + 3
            continue
        if char in ('"', "'"):
            # String literals are PRESERVED verbatim, not blanked.
            #
            # The first version of this lexer replaced every string with a single
            # space, which made :func:`service_routes` return an empty list --
            # because a route path *is* a string literal. Every route guard built
            # on it was therefore vacuously true: the "no unit-experience route"
            # assertion would have passed no matter what the service answered.
            # Preserving literals also means a forbidden token appearing only
            # inside a string still trips the guard, which is the conservative
            # direction for an anti-invention guard.
            quote = char
            out.append(char)
            index += 1
            while index < length:
                out.append(text[index])
                if text[index] == "\\" and index + 1 < length:
                    out.append(text[index + 1])
                    index += 2
                    continue
                if text[index] == quote:
                    index += 1
                    break
                index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def call_arguments(body: str, name: str) -> List[str]:
    """Inner text of every ``name(...)`` call in ``body``, skipping the definition.

    Two mistakes are deliberately avoided here, because both were made once while
    writing this module and both made the guard read something other than what it
    claimed:

    * the ``def name(`` line is not a call, so it is excluded by requiring the
      preceding character not to be part of a definition;
    * the argument list is walked with a depth counter, so a comma nested inside a
      call or a subscript does not read as a second argument.
    """
    out: List[str] = []
    for match in re.finditer(r"(?<![\w.])%s\(" % re.escape(name), body):
        before = body[max(0, match.start() - 12) : match.start()]
        if re.search(r"\bdef\s+$", before) or before.endswith("def "):
            continue
        index = match.end()
        depth = 1
        while index < len(body) and depth:
            char = body[index]
            if char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            index += 1
        out.append(body[match.end() : index - 1])
    return out


def count_top_level_commas(inner: str) -> int:
    """Commas at depth zero in an argument list."""
    depth = 0
    commas = 0
    for char in inner:
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            commas += 1
    return commas


def service_routes() -> List[str]:
    """Every URL path this service registers, read statically.

    The pattern is ``@app.<method>("<path>")`` and deliberately does **not**
    require the method to be ``route``: this repository registers endpoints as
    ``@app.post("/v0/...")``. The first version of this function matched only
    ``.route(`` and returned an empty list against the real service, which would
    have made the "no unit-experience route" guard vacuous.
    """
    body = code_only(SERVICE_PATH)
    return sorted(
        set(re.findall(r"@\w+\.\w+\(\s*[\"'](/[^\"']*)[\"']", body))
    )


def service_static_functions() -> List[str]:
    body = code_only(SERVICE_PATH)
    return sorted(set(re.findall(r"^def\s+(\w+)\(", body, re.M)))


def setUpModule() -> None:
    global _WORKING_TREE_PRE
    _WORKING_TREE_PRE = harness.working_tree_save_hashes()


def tearDownModule() -> None:
    if _WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a unit-xp fixture check wrote a working-tree save")
    if (harness.REPO_ROOT / "saves").exists():
        raise AssertionError(
            "a unit-xp fixture check created a working-tree saves/ directory"
        )


class NoNetworkTests(unittest.TestCase):
    """The guard itself must not need a server, and must prove it."""

    def test_no_socket_connection_is_attempted(self) -> None:
        original = socket.socket.connect
        attempted: List[Any] = []

        def refuse(self, address):  # type: ignore[no-untyped-def]
            attempted.append(address)
            raise AssertionError(
                "offline fixture check attempted a connection to %r" % (address,)
            )

        socket.socket.connect = refuse  # type: ignore[assignment]
        try:
            for entry in transactions():
                base = step_dir(entry["name"])
                before = load_json(base / "before.json")
                after = load_json(base / "after.json")
                leaf_diff(before, after)
        finally:
            socket.socket.connect = original  # type: ignore[assignment]
        self.assertEqual(attempted, [])

    def test_neither_service_port_is_listening(self) -> None:
        for port in (5055, 5056):
            self.assertTrue(
                harness.port_is_free("127.0.0.1", port),
                "port %d is in use, so this check is not running offline" % port,
            )


class RecomputedLeafTests(unittest.TestCase):
    """Task 3.1 / 3.2: the recorded leaf and resource claims, recomputed."""

    def test_every_recorded_transaction_has_a_step_directory(self) -> None:
        recorded = list(manifest()["recorded_steps"])
        for name in recorded:
            base = STEPS_DIR / name
            self.assertTrue(base.is_dir(), "recorded step %s has no directory" % name)
            for leaf in (
                "request.json",
                "before.json",
                "response.body",
                "response.meta.json",
                "after.json",
            ):
                self.assertTrue(
                    (base / leaf).is_file(), "%s/%s is missing" % (name, leaf)
                )

    def test_changed_leaf_set_equals_the_recomputed_diff(self) -> None:
        """The recorded summary is recomputed from the recorded states.

        This is the load-bearing check of the whole module. It reads
        ``before.json`` and ``after.json`` — the full save documents — and derives
        the changed paths itself, then compares them to what that step's own
        ``transaction.json`` claims.
        """
        for entry in transactions():
            name = entry["name"]
            base = step_dir(name)
            before = load_json(base / "before.json")
            after = load_json(base / "after.json")
            recomputed = [row[0] for row in leaf_diff(before, after)]
            recorded = [row["path"] for row in step_facts(name)["changed_leaves"]]
            self.assertEqual(
                recomputed,
                recorded,
                "%s: the recorded changed-leaf set is not the recomputed one"
                % name,
            )

    def test_every_recorded_change_is_a_single_xp_leaf_or_nothing(self) -> None:
        """The structural claim, pinned: at most one leaf, always the xp slot."""
        for entry in transactions():
            name = entry["name"]
            facts = step_facts(name)
            for row in facts["changed_leaves"]:
                self.assertRegex(
                    row["path"],
                    r"^/maps/0/items/[^/]+/6/xp$",
                    "%s changed a leaf outside the row's xp slot: %s"
                    % (name, row["path"]),
                )
            self.assertLessEqual(
                facts["changed_leaf_count"],
                1,
                "%s moved more than one leaf" % name,
            )

    def test_no_leaf_outside_the_claimed_set_moved(self) -> None:
        """The digest over every OTHER leaf, before and after, must agree.

        Without this, "exactly one leaf moved" would only be a claim about the
        addressed row; with it, it is a claim about all 2322 leaves.
        """
        for entry in transactions():
            name = entry["name"]
            facts = step_facts(name)
            base = step_dir(name)
            before = load_json(base / "before.json")
            after = load_json(base / "after.json")
            paths = [row["path"] for row in facts["changed_leaves"]]
            self.assertEqual(
                unchanged_digest(before, paths),
                unchanged_digest(after, paths),
                "%s: a leaf outside the claimed changed set also moved" % name,
            )
            self.assertEqual(
                facts["unchanged_leaves_sha256_before"],
                unchanged_digest(before, paths),
                "%s: the recorded unchanged-leaves digest is not reproducible"
                % name,
            )
            self.assertEqual(
                facts["unchanged_leaves_sha256_after"],
                unchanged_digest(after, paths),
                "%s: the recorded unchanged-leaves digest is not reproducible"
                % name,
            )

    def test_recorded_state_digests_are_reproducible(self) -> None:
        for entry in transactions():
            name = entry["name"]
            facts = step_facts(name)
            base = step_dir(name)
            before = load_json(base / "before.json")
            after = load_json(base / "after.json")
            self.assertEqual(
                facts["state_sha256_before"], whole_state_digest(before), name
            )
            self.assertEqual(
                facts["state_sha256_after"], whole_state_digest(after), name
            )

    def test_our_leaf_digest_matches_the_recorded_one(self) -> None:
        """Cross-check this module's digest recipe against the capture's.

        Both sides reimplement ``canonical_digest`` — see :func:`digest_of`. If the
        two recipes ever diverged, every check above would still be internally
        consistent while comparing against nothing, so this is the assertion that
        makes them the same function rather than two similar ones.
        """
        base = step_dir(transactions()[0]["name"])
        before = load_json(base / "before.json")
        self.assertEqual(
            whole_state_digest(before),
            transactions()[0]["state_sha256_before"],
        )

    def test_every_transaction_used_the_neutral_vector(self) -> None:
        """No transaction is excused from the resource proof by a vector."""
        from placement_envelope import parse_data_field

        for entry in transactions():
            name = entry["name"]
            request = load_json(step_dir(name) / "request.json")
            envelope = parse_data_field(request["form"]["data"])
            commands = envelope["commands"]
            self.assertEqual(len(commands), 1, name)
            self.assertEqual(commands[0][1], ADD_XP_UNIT_COMMAND, name)
            self.assertEqual(
                commands[0][3],
                NEUTRAL_VECTOR,
                "%s carried a non-neutral resource vector, so its 'no resource "
                "moved' result would be ambiguous rather than strong" % name,
            )
            self.assertTrue(entry["resource_neutral"], name)

    def test_no_stored_resource_moved_in_any_transaction(self) -> None:
        for entry in transactions():
            name = entry["name"]
            facts = step_facts(name)
            base = step_dir(name)
            before = stored_resources(load_json(base / "before.json"))
            after = stored_resources(load_json(base / "after.json"))
            self.assertEqual(
                sorted(before),
                sorted(RESOURCE_SLOTS),
                "%s does not report every stored resource slot" % name,
            )
            for slot in sorted(RESOURCE_SLOTS):
                self.assertTrue(
                    typed_equal(before[slot], after[slot]),
                    "%s moved stored resource %s: %r -> %r"
                    % (name, slot, before[slot], after[slot]),
                )
            self.assertEqual(
                facts["resources_before"], before, "%s recorded resources_before" % name
            )
            self.assertEqual(
                facts["resources_after"], after, "%s recorded resources_after" % name
            )

    def test_the_placed_row_count_never_moved(self) -> None:
        for entry in transactions():
            name = entry["name"]
            facts = step_facts(name)
            before = load_json(step_dir(name) / "before.json")
            after = load_json(step_dir(name) / "after.json")
            self.assertEqual(
                len(before["maps"][0]["items"]),
                len(after["maps"][0]["items"]),
                "%s added or removed a placed row" % name,
            )
            self.assertEqual(facts["placed_rows"], len(after["maps"][0]["items"]), name)

    def test_login_step_left_the_corpus_byte_identical(self) -> None:
        before = load_json(STEPS_DIR / LOGIN_STEP / "before.json")
        after = load_json(STEPS_DIR / LOGIN_STEP / "after.json")
        self.assertEqual(before, after)
        self.assertEqual(whole_state_digest(after), whole_state_digest(load_json(SEED_PATH)))

    def test_the_failing_transaction_writes_nothing(self) -> None:
        """The 500 arm: a raised branch leaves the save untouched."""
        failing = [e for e in transactions() if e["status"] != 200]
        self.assertEqual(len(failing), 1, "expected exactly one failing transaction")
        entry = failing[0]
        self.assertEqual(entry["name"], "string_amount_increment_fails")
        self.assertEqual(entry["status"], 500)
        self.assertEqual(step_facts(entry["name"])["changed_leaf_count"], 0)
        self.assertIsNone(entry["response_payload"])
        self.assertTrue(entry["failure_is_framework_error_page"])
        body = (step_dir(entry["name"]) / "response.body").read_bytes()
        text = body.decode("utf-8", errors="replace")
        self.assertNotIn("Traceback", text, "the recorded error body leaks a traceback")
        self.assertNotIn("socialwars-capture-", text, "the recorded body leaks a temp path")


class RecordedContractTests(unittest.TestCase):
    """Task 3.2 continued: the specific recorded outcomes, pinned by value."""

    def test_the_two_arms_are_recorded_as_established(self) -> None:
        by_name = {entry["name"]: entry for entry in transactions()}
        increment = by_name["increment_existing"]
        assign = by_name["assign_absent_key"]
        self.assertEqual(increment["attr_before"], {"xp": 23})
        self.assertEqual(increment["attr_after"], {"xp": 28})
        self.assertEqual(assign["attr_before"], {})
        self.assertEqual(assign["attr_after"], {"xp": 7})

    def test_a_missing_row_still_answers_success(self) -> None:
        by_name = {entry["name"]: entry for entry in transactions()}
        missing = by_name["missing_row"]
        self.assertEqual(missing["status"], 200)
        self.assertEqual(missing["response_payload"], {"result": "success"})
        self.assertEqual(missing["changed_leaf_count"], 0)
        self.assertIsNone(missing["attr_after"])

    def test_a_negative_gain_is_not_clamped(self) -> None:
        by_name = {entry["name"]: entry for entry in transactions()}
        negative = by_name["negative_no_clamp"]
        self.assertEqual(negative["attr_after"], {"xp": -977})

    def test_the_amount_is_unbounded(self) -> None:
        by_name = {entry["name"]: entry for entry in transactions()}
        unbounded = by_name["unbounded_amount"]
        self.assertEqual(unbounded["attr_after"], {"xp": 1000000000023})

    def test_a_float_gain_persists_as_a_float(self) -> None:
        by_name = {entry["name"]: entry for entry in transactions()}
        row = by_name["float_amount_persisted"]["attr_after"]["xp"]
        self.assertIsInstance(row, float)
        self.assertNotIsInstance(row, bool)
        self.assertEqual(row, 25.5)

    def test_a_building_row_accepts_unit_experience(self) -> None:
        by_name = {entry["name"]: entry for entry in transactions()}
        building = by_name["building_row_type_agnostic"]
        self.assertEqual(building["addressed_map_key"], "3")
        self.assertEqual(building["attr_after"], {"xp": 11})

    def test_the_string_arms_are_asymmetric(self) -> None:
        by_name = {entry["name"]: entry for entry in transactions()}
        persisted = by_name["string_amount_assign_persisted"]
        raised = by_name["string_amount_increment_fails"]
        self.assertEqual(persisted["status"], 200)
        self.assertEqual(persisted["attr_after"], {"xp": "5"})
        self.assertEqual(raised["status"], 500)
        self.assertEqual(raised["attr_after"], {"xp": 23})

    def test_a_boolean_gain_is_worth_exactly_one(self) -> None:
        by_name = {entry["name"]: entry for entry in transactions()}
        row = by_name["bool_amount_increments_as_one"]["attr_after"]["xp"]
        self.assertIsInstance(row, int)
        self.assertNotIsInstance(row, bool)
        self.assertEqual(row, 24)

    def test_the_third_argument_is_display_only(self) -> None:
        """The pair that makes 'nil stored effect' a measurement, not a reading."""
        pair = manifest()["third_argument_pair"]
        self.assertEqual(
            pair["compared"], ["increment_existing", "level_argument_ignored"]
        )
        self.assertTrue(pair["same_attr_after"])
        self.assertTrue(pair["same_changed_leaves"])
        self.assertTrue(pair["same_state_sha256"])
        self.assertTrue(pair["printed_lines_differ"])
        self.assertNotEqual(pair["printed_two"], pair["printed_three"])
        self.assertTrue(any("BOUGHT LEVEL UP" in line for line in pair["printed_three"]))
        self.assertFalse(any("BOUGHT LEVEL UP" in line for line in pair["printed_two"]))

    def test_every_transaction_records_its_printed_branch_line(self) -> None:
        """The printed lines are evidence; a missing one would be a silent hole.

        Recorded deliberately: an earlier filter in the capture matched on a
        trailing ``xp`` and silently dropped the three-argument form's line --
        which is the single line the display-only proof depends on. This test is
        the regression guard for exactly that.
        """
        for entry in transactions():
            lines = entry["printed_branch_lines"]
            self.assertEqual(
                len(lines),
                1,
                "%s recorded %d printed lines, expected exactly 1"
                % (entry["name"], len(lines)),
            )
            self.assertIn(ADD_XP_UNIT_COMMAND, lines[0], entry["name"])

    def test_the_raise_left_the_dispatcher_trace_line_empty(self) -> None:
        by_name = {entry["name"]: entry for entry in transactions()}
        line = by_name["string_amount_increment_fails"]["printed_branch_lines"][0]
        self.assertTrue(
            line.rstrip().endswith("->"),
            "the failing branch's trace line should end at the arrow: %r" % line,
        )


class ManifestIntegrityTests(unittest.TestCase):
    """Task 3.3: the manifest's own figures still hold against the bytes."""

    def test_the_readme_inventory_matches_the_bytes_on_disk(self) -> None:
        """The README's size claim is measured, not remembered.

        This fixture's first README said "1,453 KB across 78 files" and "24 copies"
        while the directory held 79 files, 1,465 KB, and 26 full save documents --
        three wrong numbers in the one paragraph a reviewer reads first to judge the
        size of what they are being asked to review. Asserting the figures here is
        what stops them drifting again.
        """
        readme = self.readme_text()
        match = re.search(r"\*\*([\d,]+) KB\*\* across (\d+) files", readme)
        self.assertIsNotNone(
            match,
            "the README no longer states its size in the asserted form "
            "'**N KB** across M files'",
        )
        stated_kb, stated_files = match.group(1), int(match.group(2))

        actual_files = 0
        actual_bytes = 0
        save_documents = 0
        for path in FIXTURES.rglob("*"):
            if not path.is_file():
                continue
            actual_files += 1
            # Count the bytes GIT STORES, not the bytes that happen to be on
            # disk. This path has no .gitattributes entry and the repository
            # sets core.autocrlf=true, so a working tree may legitimately hold
            # LF or CRLF for byte-identical committed content: a stash
            # round-trip elsewhere in this repository re-checked-out all 79
            # files as CRLF and moved this total by 99,282 bytes with no
            # content change whatsoever. Measured with st_size, this guard was
            # therefore a line-ending detector -- it failed on a CRLF checkout
            # and passed on an LF one, and said nothing at all about the
            # inventory it exists to protect. Normalizing CRLF to LF makes it
            # measure exactly the committed blob size, verified to be equal
            # for all 79 tracked files.
            actual_bytes += len(path.read_bytes().replace(b"\r\n", b"\n"))
            if path.name in ("before.json", "after.json"):
                save_documents += 1

        self.assertEqual(
            stated_files,
            actual_files,
            "the README states %d files but the fixture holds %d"
            % (stated_files, actual_files),
        )
        self.assertEqual(
            stated_kb.replace(",", ""),
            str(round(actual_bytes / 1024.0)),
            "the README states %s KB but the fixture holds %d bytes"
            % (stated_kb, actual_bytes),
        )
        # 12 transactions plus one login step, each with a before and an after.
        self.assertEqual(save_documents, 26)
        self.assertIn(
            "**26 copies**",
            readme,
            "the README no longer states the full-document copy count",
        )

    def test_the_manifest_and_each_step_agree(self) -> None:
        """The two copies of the facts must be equal, in both directions.

        The facts are committed twice: once per step, where they belong next to
        the states they describe, and once in the manifest, where they can be read
        without opening twelve directories. An earlier version of this module read
        only the manifest's copy — so the per-step files, described in the fixture
        README as "the evidence, so the fixture stays checkable offline forever",
        were not read by anything at all. Injecting a corruption into one of them
        produced a clean pass, which is what exposed this.
        """
        for entry in transactions():
            name = entry["name"]
            self.assertEqual(
                manifest_facts(name),
                step_facts(name),
                "%s: the manifest's copy of the facts differs from the step's own" % name,
            )

    def test_the_schema_is_the_one_this_line_declares(self) -> None:
        self.assertEqual(manifest()["schema"], "unit-experience-fixture-v1")

    def test_the_recorded_step_list_matches_the_directories(self) -> None:
        recorded = list(manifest()["recorded_steps"])
        on_disk = sorted(p.name for p in STEPS_DIR.iterdir() if p.is_dir())
        self.assertEqual(sorted(recorded), on_disk)

    def test_the_recorded_seed_digest_matches_the_committed_seed(self) -> None:
        import hashlib

        data = SEED_PATH.read_bytes()
        self.assertEqual(
            manifest()["seed"]["sha256"], hashlib.sha256(data).hexdigest()
        )

    def test_the_recorded_census_matches_a_fresh_measurement(self) -> None:
        seed = load_json(SEED_PATH)
        census = manifest()["seed"]["census"]
        rows = seed["maps"][0]["items"]
        self.assertEqual(census["placed_rows"], len(rows))
        self.assertEqual(census["pid"], str(seed["playerInfo"]["pid"]))
        self.assertEqual(
            census["rows_carrying_attr_xp"],
            sum(
                1
                for row in rows.values()
                if isinstance(row[6], dict) and "xp" in row[6]
            ),
        )
        self.assertEqual(census["state_sha256"], whole_state_digest(seed))
        self.assertFalse(census["target_absent_present"])

    def test_containment_is_recorded_as_identical(self) -> None:
        containment = manifest()["containment"]
        self.assertEqual(containment["combined_before"], containment["combined_after"])
        self.assertTrue(containment["identical"])
        self.assertEqual(
            containment["seed_sha256_before"], containment["seed_sha256_after"]
        )
        self.assertTrue(containment["working_tree_saves_absent"])
        self.assertTrue(containment["protected_fixtures_unchanged"])

    def readme_text(self) -> str:
        """The README with its hard line wraps collapsed to single spaces.

        Prose assertions have to normalise wrapping first: a phrase that happens
        to straddle a newline is not absent, and an assertion that treats it as
        absent is a guard that fails for a reason unrelated to what it guards.
        The first version of this test did exactly that, failing on
        ``no windowed capture`` because the file said ``any\\nwindowed capture``.
        """
        return " ".join(README_PATH.read_text(encoding="utf-8").split())

    def test_the_closure_claims_are_present(self) -> None:
        readme = self.readme_text()
        for phrase in (
            "No Flash, Ruffle, ActionScript, or browser executes",
            "loopback `127.0.0.1:5055` only",
            "**not** license a modern endpoint",
            "No player state is fabricated",
            "no windowed capture",
            "derived-provisional",
            "one per transaction",
            "server-authoritative validation",
        ):
            self.assertIn(phrase, readme, "the README no longer states: %r" % phrase)

    def test_the_readme_disclaims_pixel_parity_and_award(self) -> None:
        """The two things this line must never be read as claiming.

        Asserted as the presence of the disclaimer rather than the absence of a
        phrase: the README legitimately says the word "pixel parity" precisely to
        deny the claim, so a substring-absence test would be both wrong and
        weaker. Every occurrence must sit inside a denial.
        """
        readme = self.readme_text().lower()
        self.assertIn("no pixel parity", readme)
        self.assertIn("no windowed capture", readme)
        for match in re.finditer(r"pixel parity", readme):
            window = readme[max(0, match.start() - 32) : match.start()].lower()
            self.assertTrue(
                any(token in window for token in ("no ", "not ", "any ", "never ")),
                "the README mentions pixel parity without denying it: %r"
                % readme[max(0, match.start() - 40) : match.end() + 10],
            )

    def test_the_readme_names_the_seed_and_the_one_server_rule(self) -> None:
        readme = self.readme_text()
        self.assertIn("villages/AcidCaos.json", readme)
        self.assertIn("`sessions.load_saves()` caches the corpus", readme)
        self.assertIn("`playerInfo.pid`", readme)


class RepositoryCensusTests(unittest.TestCase):
    """Task 3.4: re-measure the figures the contract rests on. Never copy them."""

    def test_the_field_is_present_in_exactly_five_committed_saves(self) -> None:
        carrying = 0
        total_rows = 0
        for path in sorted((harness.REPO_ROOT / "villages").glob("*.json")):
            document = load_json(path)
            rows = document["maps"][0]["items"]
            total_rows += len(rows)
            if any(
                isinstance(row[6], dict) and "xp" in row[6] for row in rows.values()
            ):
                carrying += 1
        self.assertEqual(
            carrying,
            5,
            "the committed village corpus no longer carries attr['xp'] in five saves",
        )
        self.assertGreater(total_rows, 0)

    def test_the_fresh_corpus_carries_the_field_on_no_row(self) -> None:
        """The reason this line needed a village seed, asserted so it stays true."""
        document = load_json(harness.REPO_ROOT / "tests" / "saves" / "fresh-player.json")
        rows = document["maps"][0]["items"]
        self.assertEqual(
            [
                key
                for key, row in rows.items()
                if isinstance(row[6], dict) and "xp" in row[6]
            ],
            [],
            "the fresh corpus now exercises this branch, so the village-seeded "
            "capture's justification must be revisited",
        )

    def test_the_committed_per_unit_field_is_refuted_as_the_award(self) -> None:
        """Three independent measurements, recomputed from committed bytes.

        The refusal to invent a schedule rests on all three together; any one alone
        would be arguable.
        """
        definitions = {str(row["legacy_id"]): row for row in load_json(UNITS_PATH)}

        # (1) One definition carries many distinct accumulated totals in one save.
        seed = load_json(SEED_PATH)
        rows = seed["maps"][0]["items"]
        per_definition: Dict[str, List[Any]] = {}
        for row in rows.values():
            bag = row[6]
            if isinstance(bag, dict) and "xp" in bag:
                per_definition.setdefault(str(row[0]), []).append(bag["xp"])
        spread = {
            key: sorted(set(values), key=lambda v: (str(type(v)), str(v)))
            for key, values in per_definition.items()
        }
        widest = max(len(values) for values in spread.values())
        self.assertGreater(
            widest,
            1,
            "no single unit definition carries two distinct accumulated totals, so "
            "the 'not one value per definition' measurement no longer holds",
        )

        # (2) Most ratios to the committed value are not integral. The per-unit
        # committed field is ``xp`` (units.json), not ``experience``.
        integral = 0
        total = 0
        for item_id, values in per_definition.items():
            committed = definitions.get(item_id, {}).get("xp")
            if committed is None:
                continue
            for value in values:
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    total += 1
                    if committed and value % committed == 0:
                        integral += 1
        self.assertGreater(
            total,
            0,
            "no accumulated value matched a committed unit definition, so the "
            "ratio measurement has nothing to measure",
        )
        self.assertLess(
            integral,
            total,
            "every ratio to the committed value is now integral, so the "
            "'committed field is not the award' measurement no longer holds",
        )

        # (3) No row equals its own save's stored player experience.
        player_xp = seed["maps"][0]["xp"]
        self.assertTrue(
            all(value != player_xp for values in per_definition.values() for value in values),
            "a row now equals the save's stored player experience, so the third "
            "independent refutation no longer holds",
        )


class AntiInventionTests(unittest.TestCase):
    """Task 3.5: this line delivers NO route and NO award rule. Enforced."""

    def test_the_service_answers_no_unit_experience_route(self) -> None:
        routes = service_routes()
        self.assertGreater(len(routes), 0, "no routes were read from the service")
        for route in routes:
            lowered = route.lower()
            for token in UNIT_XP_ROUTE_FORBIDDEN_SUBSTRINGS:
                self.assertNotIn(
                    token,
                    lowered,
                    "the Compatibility API now answers a unit-experience route "
                    "(%s); this line delivers evidence, not an endpoint" % route,
                )

    def test_the_service_declares_no_experience_award_helper(self) -> None:
        names = service_static_functions()
        self.assertGreater(len(names), 0, "no static functions were read")
        for name in names:
            lowered = name.lower()
            for token in AWARD_FORBIDDEN_SUBSTRINGS:
                self.assertNotIn(
                    token,
                    lowered,
                    "the Compatibility API now declares an award helper (%s); this "
                    "line's whole refusal is that no trusted award exists" % name,
                )

    def test_the_compat_directory_declares_no_other_unit_xp_module(self) -> None:
        """No *delivered* module may be named for this line.

        The capture and this guard are the two files that legitimately carry the
        name -- one records the oracle, the other checks the record -- so the
        guard is scoped to everything else, which is where an accidentally
        delivered ``unit_xp_service.py`` would appear.
        """
        modules = sorted(p.name for p in COMPAT_DIR.glob("*.py"))
        self.assertTrue(modules)
        allowed = {OWN_CAPTURE_NAME}
        offenders = [
            name
            for name in modules
            if name not in allowed and ("unit_xp" in name.lower() or "unit-experience" in name.lower())
        ]
        self.assertEqual(
            offenders,
            [],
            "a new module is named for unit experience; this line delivers evidence "
            "and must not grow a delivery surface: %r" % offenders,
        )

    def test_the_service_module_has_no_unit_xp_identifier_anywhere(self) -> None:
        body = code_only(SERVICE_PATH)
        for token in ("add_xp_unit", "attr[\"xp\"]", "attr['xp']"):
            self.assertNotIn(
                token,
                body,
                "the Compatibility API now names %r; this line delivers evidence, "
                "not a route" % token,
            )


class CaptureHarnessSeamTests(unittest.TestCase):
    """Task 1.3: the seam this line added must stay defaulted."""

    def test_build_disposable_takes_the_seed_as_a_defaulted_parameter(self) -> None:
        body = code_only(HARNESS_PATH)
        signature = re.search(
            r"^def build_disposable\(\s*(.*?)\)\s*->", body, re.S | re.M
        )
        self.assertIsNotNone(signature, "build_disposable was not found")
        text = signature.group(1)
        self.assertIn("seed_path", text)
        self.assertIn(
            "FRESH_PLAYER_SAVE",
            text,
            "the seed parameter has no default, so every existing caller had to "
            "change and the 'provably non-breaking' claim is void",
        )

    def test_every_other_build_disposable_call_site_passes_at_most_one_argument(self) -> None:
        """The structural pin (task 1.3).

        Seventeen call sites existed when the parameter was added and all of them
        passed a single positional argument. That is why adding a defaulted
        parameter could not break them. The property decays the moment someone
        passes a second argument — at which point some other capture has acquired a
        non-fresh corpus and the corpus assumptions of its committed fixture need
        rechecking. That must be a loud failure.

        Seventeen are still pinned, and that is measured rather than asserted by
        hand: twenty call sites exist and three captures are declared seeded
        (unit-xp, combat-actions, damage) -- twenty minus three. A seeded capture
        adds one call site AND one exemption, so joining the set leaves this number
        exactly where it was. That is a real weakness of counting alone and it is
        why the number cannot catch a new capture; the separate exact-set assertion
        below is what does.

        Each capture in SEEDED_CAPTURE_NAMES is a deliberate exception, asserted
        separately below, so the exception cannot silently widen.
        """
        offenders: List[str] = []
        pinned = 0
        for path in sorted(COMPAT_DIR.glob("*.py")):
            body = code_only(path)
            for inner in call_arguments(body, "build_disposable"):
                if path.name in SEEDED_CAPTURE_NAMES:
                    continue
                pinned += 1
                if count_top_level_commas(inner) >= 1:
                    offenders.append(
                        "%s: build_disposable(%s)" % (path.name, inner.strip()[:70])
                    )
        self.assertEqual(
            offenders,
            [],
            "a build_disposable call site now passes a second argument, so a "
            "capture other than the declared ones may be seeding from a different "
            "corpus: %r" % offenders,
        )
        self.assertEqual(
            pinned,
            17,
            "the number of pinned call sites changed (%d, expected 17); a new "
            "capture must be reviewed before it inherits this property" % pinned,
        )

    def test_each_declared_seeded_capture_passes_exactly_one_seed(self) -> None:
        """The exception set is exact, not approximate, and every member exists.

        Measured by name rather than by hardcoding an argument count per member,
        so adding a capture to the set cannot quietly give it a different number
        of seeds -- which would be a third corpus this pin has never reviewed.
        """
        found = sorted(
            path.name for path in COMPAT_DIR.glob("*.py")
            if path.name in SEEDED_CAPTURE_NAMES
        )
        self.assertEqual(found, sorted(SEEDED_CAPTURE_NAMES))
        for name in sorted(SEEDED_CAPTURE_NAMES):
            path = COMPAT_DIR / name
            self.assertTrue(path.is_file(), "%s is declared but absent" % name)
            counts = [
                count_top_level_commas(inner)
                for inner in call_arguments(code_only(path), "build_disposable")
            ]
            with self.subTest(capture=name):
                self.assertEqual(
                    counts,
                    [1],
                    "%s's call site changed shape: exactly one call may pass a "
                    "seed, got argument counts %r" % (name, sorted(counts)),
                )


class CodeOnlyLexTests(unittest.TestCase):
    """The lexer this module's guards are built on, tested directly.

    Every static guard here scans comment-stripped source. If the stripper is
    wrong, those guards silently weaken: a mention inside a comment would be
    read as code (a false failure) or, worse, real code inside a string would be
    discarded. Both are silent, so the stripper itself gets a test rather than
    trust -- the same standard applied to the injection guards elsewhere in this
    repository.
    """

    def test_a_line_comment_is_removed(self) -> None:
        self.assertEqual(code_only_text("x = 1  # gone\n"), "x = 1  \n")

    def test_a_shebang_is_removed(self) -> None:
        """The regression: a two-character ``"#!"`` slice never equals ``"#"``."""
        self.assertEqual(code_only_text("#!/usr/bin/env python3\nx = 1\n"), "\nx = 1\n")

    def test_a_hash_inside_a_string_is_preserved(self) -> None:
        """Strings are kept verbatim -- a route path IS a string literal.

        Blanking them made :func:`service_routes` return nothing at all.
        """
        self.assertEqual(code_only_text('x = "a # b"\n'), 'x = "a # b"\n')

    def test_a_hash_inside_a_docstring_is_removed(self) -> None:
        stripped = code_only_text('"""doc # text"""\nx = 1\n')
        self.assertEqual(stripped, "\nx = 1\n")

    def test_a_single_triple_quoted_docstring_is_removed(self) -> None:
        """The second lexer defect: ``pair`` is two characters, so ``"'''"``
        could never match. Docstrings delimited with single quotes were read as a
        string literal followed by code, which is how this module came to think
        ``compat_service.py`` named ``add_xp_unit`` -- a phrase that appears only
        in a prose design note."""
        self.assertEqual(code_only_text("'''doc # text'''\nx = 1\n"), "\nx = 1\n")

    def test_an_unterminated_docstring_is_refused(self) -> None:
        """Better to fail loudly than to read the rest of a file as prose."""
        with self.assertRaises(AssertionError):
            code_only_text('"""never closed\nx = 1\n')

    def test_a_comment_after_a_string_is_removed(self) -> None:
        stripped = code_only_text('x = "keep"  # drop\n')
        self.assertEqual(stripped, 'x = "keep"  \n')

    def test_an_apostrophe_inside_a_double_quoted_string_does_not_desynchronise(self) -> None:
        """The earlier single-state scanner's failure, as a regression."""
        self.assertEqual(code_only_text('x = "it\'s"\ny = 2\n'), 'x = "it\'s"\ny = 2\n')

    def test_escaped_quote_does_not_end_the_string(self) -> None:
        stripped = code_only_text('x = "a \\" # b"\ny = 2\n')
        self.assertEqual(stripped.count("\n"), 2)
        self.assertIn("# b", stripped, "the lexer treated an escaped quote as a close")

    def test_a_real_route_is_read_back_from_the_service(self) -> None:
        """Positive control: the stripper still leaves real code behind.

        Without this, a stripper that removed everything would pass every guard
        above vacuously -- the exact defect this repository has already suffered
        once, when a ``_code_only`` helper was handed a path instead of a body.
        """
        routes = service_routes()
        self.assertGreater(len(routes), 12, "too few routes were read: %r" % routes)
        for expected in ("/v0/level_up", "/v0/place", "/v0/tutorial"):
            self.assertIn(expected, routes)

    def test_a_real_function_is_read_back_from_the_service(self) -> None:
        names = service_static_functions()
        self.assertIn("create_app", names)
        self.assertIn("envelope", names)

    def test_the_route_list_holds_no_unit_experience_route(self) -> None:
        """The guard this whole class exists to keep honest, restated."""
        self.assertEqual(
            [r for r in service_routes() if "unit" in r.lower() and "xp" in r.lower()],
            [],
        )


class ContainmentTests(unittest.TestCase):
    def test_working_tree_saves_were_never_written(self) -> None:
        self.assertEqual(harness.working_tree_save_hashes(), _WORKING_TREE_PRE)
        self.assertFalse((harness.REPO_ROOT / "saves").exists())


if __name__ == "__main__":
    unittest.main()