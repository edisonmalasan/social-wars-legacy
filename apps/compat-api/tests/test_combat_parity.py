#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/combat`` vs the executed-legacy combat
fixture (OpenSpec task 1.3, ``godot-combat-actions``).

No server and no network: the endpoint runs through Flask's in-process test
client under the ``offline`` guard (which fails the run if any socket tries to
connect), and :meth:`ReplayTests.test_no_server_is_running` asserts that neither
the legacy port (5055) nor the Compatibility API port (5056) is listening.

What is replayed
    The committed transactions under ``tests/fixtures/godot-combat-actions/``:
    **thirteen** executed-legacy transactions over **two** village seeds, each
    carrying the **neutral** vector ``[0, 0, 0, 0, 0, 0, 0, 0]``.  The endpoint
    derives the very same envelopes from the very same derivation module, so the
    replay compares the persisted corpus document against each recorded
    after-state, **leaf for leaf, with no pruning at all**.

    Two things are deliberately NOT compared by value:

    * the **raw bytes** of the corpus save.  ``sessions.save_session`` re-serialises
      the document with the platform's newline convention (CRLF on Windows), so an
      executed legacy batch and a replayed one can produce different bytes for an
      identical document.  The document comparison is the claim; a byte
      comparison would be a stronger claim than anything true.  Byte-identity IS
      asserted where it is available and meaningful: every **refused** request
      persists nothing at all, so the file the suite wrote itself is unchanged.
    * the ``server_time`` envelope field, which is a wall-clock reading and is
      asserted only to be a positive integer.

The two seeds in ONE corpus, and why that is not a deviation
    ``sessions.load_saves()`` caches every save in a module global at import and
    ``SAVES_DIR`` is frozen at the first ``initialize``, so one process can hold
    exactly one corpus -- which is why the capture started **one server per
    transaction**.  Seeding both village documents into a single corpus is
    therefore a test mechanism, not a reproduction of the capture's server
    layout, and it would be a silent weakening if nothing held it up.  What holds
    it up is measured rather than argued: the capture recorded each village
    **alone**, and this replay reproduces both recordings **exactly** -- the same
    derived key, the same removed rows, the same ledger -- with the other village
    resident.  A co-resident save that perturbed the combat path could not
    reproduce a one-village recording byte for byte in the state.  The suite also
    asserts the route's response carries **no session-list field** at all, so the
    one thing the extra save does change is never carried by this response.

Four classes of recorded transaction, and what each one means here

    ``STATE PARITY``
        ``resolve_first_by_recorded_order``, ``ledger_increment_existing``,
        ``ledger_key_created``, ``kill_unit_row``, ``kill_iid_no_op``.  The
        endpoint's persisted document equals the recorded after-state, leaf for
        leaf.

    ``STATE PARITY THROUGH A REFUSAL``
        ``resolve_no_eligible_row`` and ``kill_missing_row``.  The oracle answers
        legacy success while changing nothing; the endpoint **refuses** with a
        named code.  The persisted state matches, which is why the manifest calls
        these parity, and the refusal is a recorded divergence from the response.

    ``NOT EXPRESSIBLE BY THE DELIVERED ENDPOINT``
        The five malformed-blob transactions
        (``resolve_absent_attacker_units``, ``resolve_empty_payload``,
        ``resolve_absent_victim``, ``resolve_batch_discarded_on_raise``,
        ``resolve_empty_attacker_units``).  The oracle reads a **client blob**;
        this endpoint accepts no client blob at all, so there is no request that
        asks the same question.  They are asserted as **recorded state** -- the
        persisted document is byte-identical to the recorded after-state -- and
        are explicitly NOT counted as replayed parity.

    ``THE CENTRAL DIVERGENCE``
        ``client_dictated_count_two``.  The oracle removed **two** rows and
        incremented the ledger twice; this endpoint destroys **exactly one** and
        increments once, and refuses the client count outright.  The suite asserts
        the difference rather than reporting parity by omission: the recorded
        after-state really removed two rows, the replay really left the
        before-state untouched, and the manifest records the divergence.

The comparison is proved able to fail
    Task 1.3 requires this suite to fail if the recorded row-count change or the
    recorded ledger value is altered.  :meth:`ReplayTests.test_the_comparison_fails_on_an_altered_row_count_or_ledger_value`
    makes that permanent by feeding the comparator a recorded after-state with one
    row removed too few and one with a wrong ledger count, and requires it to
    report both.  A comparator that could not fail would pass this suite.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import compat_test_harness as harness

import combat_envelope
import compat_legacy
import compat_service

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-combat-actions"
STEPS = FIXTURES / "steps"
LOGIN_STEP = "login_post"

#: The two village seeds, in the manifest's own names.  The paths are read from
#: the manifest rather than restated, so a re-capture cannot leave this suite
#: pointing at a document the recording no longer used.
SEED_NAMES = ("destruction", "ledger")

#: Every recorded step directory, in the manifest's recorded order.
STEP_NAMES = tuple(
    [
        "txn_resolve_first_by_recorded_order",
        "txn_resolve_absent_attacker_units",
        "txn_resolve_empty_payload",
        "txn_resolve_absent_victim",
        "txn_resolve_batch_discarded_on_raise",
        "txn_resolve_empty_attacker_units",
        "txn_client_dictated_count_two",
        "txn_resolve_no_eligible_row",
        "txn_kill_unit_row",
        "txn_kill_missing_row",
        "txn_kill_iid_no_op",
        "txn_ledger_increment_existing",
        "txn_ledger_key_created",
    ]
)

#: Steps whose persisted state the endpoint reproduces **as a successful
#: execution**: ``(step, seed, action, addressing)``.
STATE_PARITY = (
    ("txn_resolve_first_by_recorded_order", "resolve", {"item_id": 1020}),
    ("txn_kill_unit_row", "kill", {"map_key": 1639}),
    ("txn_kill_iid_no_op", "kill_iid", {"item_id": 1076}),
    ("txn_ledger_increment_existing", "resolve", {"item_id": 1034}),
    ("txn_ledger_key_created", "resolve", {"item_id": 1023}),
)

#: Steps whose recorded no-change state the endpoint reproduces **through a named
#: refusal**: ``(step, action, addressing, expected code, expected status)``.
REFUSAL_PARITY = (
    ("txn_resolve_no_eligible_row", "resolve", {"item_id": 923},
     "no_eligible_row", 409),
    ("txn_kill_missing_row", "kill", {"map_key": 999999},
     "unaddressable_row", 409),
)

#: Steps the oracle recorded but the delivered endpoint **cannot be asked**: the
#: client blob is not part of this request shape at all.
NOT_EXPRESSIBLE = (
    "txn_resolve_absent_attacker_units",
    "txn_resolve_empty_payload",
    "txn_resolve_absent_victim",
    "txn_resolve_batch_discarded_on_raise",
    "txn_resolve_empty_attacker_units",
)

#: The one recorded transaction whose row count the endpoint deliberately differs
#: on, measured rather than asserted.
DIVERGENT_STEP = "txn_client_dictated_count_two"

RESOURCE_NAMES = combat_envelope.RESOURCE_NAMES
LEDGER_KEY = combat_envelope.LEDGER_KEY

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PIDS: Dict[str, str] = {}
WORKING_TREE_PRE: List[Dict[str, str]] = []
FIXTURE: Dict[str, Any] = {}


# ------------------------------------------------------------------ the fixture --
def load_step(name: str) -> Dict[str, Any]:
    """Load one recorded step.

    ``transaction.json`` exists only for the thirteen real transactions: the
    ``login_post`` step is a state-neutral preliminary whose whole purpose is to
    be elided, so it carries no transaction record and the loader does not
    invent one.  Its ``transaction`` key is ``None`` and every assertion that
    reads it iterates :data:`STEP_NAMES`, which never contains it.
    """
    base = STEPS / name
    record: Dict[str, Any] = {
        "request": json.loads((base / "request.json").read_text(encoding="utf-8")),
        "before": json.loads((base / "before.json").read_text(encoding="utf-8")),
        "after": json.loads((base / "after.json").read_text(encoding="utf-8")),
        "meta": json.loads((base / "response.meta.json").read_text(encoding="utf-8")),
        "body": (base / "response.body").read_bytes(),
        "transaction": None,
    }
    transaction = base / "transaction.json"
    if transaction.is_file():
        record["transaction"] = json.loads(transaction.read_text(encoding="utf-8"))
    return record


def load_fixture() -> Dict[str, Any]:
    manifest = json.loads(
        (FIXTURES / "capture-manifest.json").read_text(encoding="utf-8")
    )
    fixture: Dict[str, Any] = {
        "manifest": manifest,
        LOGIN_STEP: load_step(LOGIN_STEP),
    }
    for name in STEP_NAMES:
        step = load_step(name)
        fixture[name] = step
        fixture[name]["seed"] = step["transaction"]["seed"]
    return fixture


def seed_of(name: str) -> str:
    return str(FIXTURE[name]["seed"])


def pid_of(seed: str) -> str:
    return PIDS[seed]


# --------------------------------------------------------------- the corpus --
def seed_village_corpora(manifest: Dict[str, Any]) -> None:
    """Copy **both** recorded village seeds into ONE disposable corpus.

    Both documents are written **verbatim** (raw bytes, not a re-serialisation),
    so each corpus save keeps its own recorded SHA-256 and nothing about either
    seed is fabricated.  ``compat_legacy.build_corpus`` writes exactly one seeded
    save, so the suite asks it to seed the **destruction** village and copies the
    **ledger** village in beside it; seeding with the default fresh-player
    document would have left a third resident save and quietly widened the
    co-residency this suite claims to control.  See the module docstring for why
    one corpus is required at all and what holds the mechanism up.
    """
    for name in SEED_NAMES:
        entry = manifest["seeds"][name]
        source = harness.REPO_ROOT / str(entry["path"])
        if not source.is_file():
            raise AssertionError("recorded seed is missing: %s" % source)
        target = save_path(str(entry["pid_read_from_document"]))
        target.write_bytes(source.read_bytes())
        if sha256_of(target) != entry["sha256"]:
            raise AssertionError(
                "recorded seed %r was not copied verbatim: %s" % (name, target)
            )


def save_path(pid: str) -> Path:
    return CORPUS / "saves" / ("%s.save.json" % pid)  # type: ignore[operator]


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_save(pid: str, document: Dict[str, Any]) -> None:
    """Write a save the way the suite's own seeding does: LF, indent four.

    The newline convention matters and is recorded rather than assumed.  The
    legacy ``save_session`` opens the file in TEXT mode with no ``newline``
    argument, so on Windows it writes CRLF while the suite writes LF.  Comparing
    raw BYTES between an executed legacy batch and a replayed one would therefore
    fail on an identical document, which is why the state comparisons parse the
    document and the byte comparisons are reserved for requests that persist
    nothing at all.
    """
    with open(save_path(pid), "w", encoding="utf-8", newline="\n") as stream:
        json.dump(document, stream, indent=4)
        stream.write("\n")


def persisted(pid: str) -> Dict[str, Any]:
    return json.loads(save_path(pid).read_text(encoding="utf-8"))


def committed_seed(seed: str) -> Dict[str, Any]:
    """The recorded village document for one seed, read from the repository.

    **This is the order of record, and the recorded snapshots deliberately are
    not.**  The shared capture writer sorts every fixture document's keys, so a
    step's ``before.json`` carries its ``items`` in lexicographic order while the
    oracle walked the in-memory save, whose order is this file's.  The two answer
    the D1 selection question differently -- 2425 against 1022 -- so the replay
    rebuilds the corpus from here.
    :meth:`FixtureIntegrityTests.test_the_order_of_record_is_the_committed_document_not_the_snapshot`
    measures that difference rather than assuming it.
    """
    entry = FIXTURE["manifest"]["seeds"][seed]
    return json.loads(
        (harness.REPO_ROOT / str(entry["path"])).read_text(encoding="utf-8")
    )


def reset(name: str) -> str:
    """Put the named seed's corpus save back to its **committed village document**.

    Both halves, deliberately: ``sessions.session`` hands out the **cached
    document by reference**, so the in-memory dict is rebuilt in place (which
    keeps that reference valid) and the file is rewritten so a request that
    persists nothing still leaves the file byte-identical to the state the
    corpus started in.

    Every recorded transaction ran against the pristine committed village -- one
    disposable server per transaction, each seeded from the same document -- so
    this is the state the oracle saw for **every** step of a seed, not only the
    first.  The recorded ``before`` snapshots are equal to it leaf for leaf and
    differ only in key ORDER, which
    :meth:`FixtureIntegrityTests.test_each_seed_starts_from_its_committed_document`
    establishes.
    """
    seed = seed_of(name)
    pid = pid_of(seed)
    template = committed_seed(seed)
    cached = BOOT.save_document(pid)  # type: ignore[union-attr]
    cached.clear()
    cached.update(json.loads(json.dumps(template)))
    write_save(pid, cached)
    return pid


def combat_now(pid: str, action: str, **addressing: Any):
    payload: Dict[str, Any] = {"user_id": pid, "action": action}
    payload.update(addressing)
    with harness.offline():
        return CLIENT.post("/v0/combat", json=payload)  # type: ignore[union-attr]


def resources_of(document: Dict[str, Any]) -> Dict[str, Any]:
    first_map = document["maps"][0]
    return {
        "xp": first_map["xp"],
        "gold": first_map["gold"],
        "wood": first_map["wood"],
        "oil": first_map["oil"],
        "steel": first_map["steel"],
        "cash": document["playerInfo"]["cash"],
        "mana": document["privateState"]["mana"],
    }


def placement_keys(document: Dict[str, Any]) -> List[str]:
    """The save's OWN recorded map-key order -- the order ``map_lose_item`` pops."""
    return list(document["maps"][0]["items"])


def recorded_changed_pointers(transaction: Dict[str, Any]) -> List[str]:
    """The recorded leaf paths reduced to the pointers this route reports.

    The capture records the **leaf** pointers it diffed (``/maps/0/items/2425/0``
    and its siblings, plus ``/privateState/deadHeroes/1020``), while the delivered
    ``changed`` reports one pointer per touched stored object.  The reduction is
    therefore DERIVED from the recording rather than restated beside it: five
    segments for a placement, four for a ledger entry, deduplicated in recorded
    order.  Any recorded leaf this route moved that does not sit under exactly one
    of the reduced pointers makes the equality fail, which is the whole point.
    """
    segments = {
        "/maps/0/items/": 5,
        "/privateState/deadHeroes/": 4,
    }
    pointers: List[str] = []
    for leaf in transaction["changed_leaves"]:
        path = str(leaf["path"])
        for prefix, depth in segments.items():
            if path.startswith(prefix):
                pointer = "/".join(path.split("/")[:depth])
                if pointer not in pointers:
                    pointers.append(pointer)
                break
        else:
            raise AssertionError(
                "recorded changed leaf %r is outside the two stored objects this "
                "route reports" % path
            )
    return pointers


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, CLIENT, WORKING_TREE_PRE, FIXTURE
    ORIGINAL_CWD = os.getcwd()
    FIXTURE = load_fixture()
    CORPUS = Path(tempfile.mkdtemp(prefix=harness.CORPUS_TEMP_PREFIX))
    # Seeded with the RECORDED destruction village rather than the harness
    # default, so the corpus holds exactly the two recorded pids and nothing
    # else.  ``seed_village_corpora`` then writes both, verbatim.
    compat_legacy.build_corpus(
        CORPUS, seed=harness.REPO_ROOT / str(FIXTURE["manifest"]["seeds"]["destruction"]["path"])
    )
    seed_village_corpora(FIXTURE["manifest"])
    BOOT = compat_legacy.initialize(CORPUS)
    PIDS.clear()
    for name in SEED_NAMES:
        entry = FIXTURE["manifest"]["seeds"][name]
        pid = str(entry["pid_read_from_document"])
        PIDS[name] = pid
        if pid not in BOOT.known_user_ids():  # type: ignore[union-attr]
            raise AssertionError("recorded seed %r did not load: %r" % (name, pid))
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    CLIENT = app.test_client()
    WORKING_TREE_PRE = harness.working_tree_save_hashes()


def tearDownModule() -> None:
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a combat replay wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


# -------------------------------------------------- non-executing: the fixture --
class FixtureIntegrityTests(unittest.TestCase):
    """The committed recording, checked without executing anything."""

    def test_thirteen_transactions_over_two_seeds_are_recorded(self) -> None:
        manifest = FIXTURE["manifest"]
        self.assertEqual(manifest["schema"], "combat-actions-fixture-v1")
        self.assertEqual(len(STEP_NAMES), 13)
        self.assertEqual(len(manifest["transactions"]), 13)
        self.assertEqual(len(manifest["recorded_steps"]), 14)
        self.assertEqual(
            set(manifest["recorded_steps"]),
            set(STEP_NAMES) | {LOGIN_STEP},
            "every recorded step has a directory and no directory is unrecorded",
        )
        # ``seeds`` also carries two prose keys, so the check is that both seed
        # names are present and that no THIRD seed was recorded.
        self.assertEqual(
            sorted(set(SEED_NAMES) - set(manifest["seeds"])), [],
            "both recorded seeds are present under the manifest's own names",
        )
        self.assertEqual(
            sorted(set(manifest["seeds"]) - set(SEED_NAMES)),
            ["pid_note", "why_two"],
            "and the manifest records no seed beyond those two",
        )
        self.assertEqual(manifest["cleanup"]["disposables"], 13)
        self.assertEqual(manifest["server"]["starts"], 13)
        self.assertTrue(manifest["server"]["one_per_transaction"])
        self.assertIn(
            "module global at import",
            manifest["server"]["one_per_transaction_reason"],
        )

    def test_the_two_seeds_are_read_from_the_manifest_not_restated(self) -> None:
        seeds = FIXTURE["manifest"]["seeds"]
        self.assertEqual(seeds["destruction"]["path"], "villages/AcidCaos.json")
        self.assertEqual(seeds["ledger"]["path"], "villages/Neutral.json")
        for name in SEED_NAMES:
            with self.subTest(seed=name):
                entry = seeds[name]
                document = json.loads(
                    (harness.REPO_ROOT / entry["path"]).read_text(encoding="utf-8")
                )
                self.assertEqual(
                    str(document["playerInfo"]["pid"]),
                    entry["pid_read_from_document"],
                    "the pid is read from the document, never the filename stem",
                )
                self.assertEqual(len(document["maps"][0]["items"]),
                                 entry["census"]["placed_rows"])

    def test_each_seed_starts_from_its_committed_document(self) -> None:
        """Every recorded transaction ran against the pristine village.

        That is the recording's shape, not an accident: the manifest records one
        disposable **server** per transaction because ``sessions.load_saves()``
        caches the corpus in memory at import, so each transaction necessarily
        began from a freshly seeded corpus.  So the steps of one seed do **not**
        chain -- asserting that they chain would be asserting a shape the fixture
        does not have, and would fail on a correct recording.
        """
        for name in SEED_NAMES:
            ordered = [step for step in STEP_NAMES if seed_of(step) == name]
            village = json.loads(
                (
                    harness.REPO_ROOT
                    / str(FIXTURE["manifest"]["seeds"][name]["path"])
                ).read_text(encoding="utf-8")
            )
            with self.subTest(seed=name):
                self.assertGreaterEqual(len(ordered), 2)
                for step in ordered:
                    with self.subTest(step=step):
                        self.assertEqual(
                            FIXTURE[step]["before"],
                            village,
                            "each transaction's pre-state is its own committed "
                            "village, whole and leaf for leaf",
                        )
                # The two ledger steps are the independent proof that no step
                # inherits the previous one's write: both start from the same
                # 28-key ledger with the same count at 4.
                if name == "ledger":
                    first = FIXTURE[ordered[0]]["after"]
                    second = FIXTURE[ordered[1]]["before"]
                    self.assertEqual(
                        list(first["privateState"][LEDGER_KEY]),
                        list(second["privateState"][LEDGER_KEY]),
                        "both ledger steps start from the same key list",
                    )
                    self.assertEqual(
                        first["privateState"][LEDGER_KEY]["1034"], 5,
                        "the first step's ledger increment is 5 ...",
                    )
                    self.assertEqual(
                        second["privateState"][LEDGER_KEY]["1034"], 4,
                        "... and it did NOT carry into the second step's "
                        "pre-state, which is what 'one server each' means",
                    )

    def test_the_recorded_order_discriminator_is_committed_and_discriminating(
        self,
    ) -> None:
        """The D1 claim has a fixture that a sorting implementation would fail."""
        discriminator = FIXTURE["manifest"]["recorded_order_discriminator"]
        self.assertTrue(discriminator["recorded_order_discriminates"])
        self.assertEqual(discriminator["item_id"], 1020)
        self.assertEqual(discriminator["first_recorded"], "2425")
        self.assertEqual(discriminator["numeric_min"], "897")
        self.assertNotEqual(
            discriminator["first_recorded"], discriminator["numeric_min"]
        )
        self.assertEqual(
            discriminator["row_a_sorted_implementation_would_remove"], "897"
        )
        self.assertEqual(discriminator["row_removed_by_the_oracle"], ["2425"])
        self.assertEqual(len(discriminator["eligible_keys_recorded"]), 7)
        census = FIXTURE["manifest"]["seeds"]["destruction"]["census"]
        self.assertEqual(census["order_first_recorded"], "2425")
        self.assertEqual(census["order_numeric_min"], "897")
        self.assertFalse(
            census["recorded_map_key_order_is_sorted"],
            "the recorded order is NOT a sort, which is what makes it testable",
        )
        # And the eligible keys really are in the save's RECORDED order.  Two
        # independent derivations must agree, and neither may be the sort: one is
        # a hand-written walk of the two conditions ``engine.py:221`` tests (slot
        # 0 equal to the id, slot 7 truthy) over the committed document's own
        # insertion order, the other is the delivered selector itself.
        village = json.loads(
            (harness.REPO_ROOT / "villages" / "AcidCaos.json").read_text(
                encoding="utf-8"
            )
        )
        hand_walked = [
            str(key)
            for key, row in village["maps"][0]["items"].items()
            if isinstance(row, list) and len(row) > 7 and row[0] == 1020 and row[7]
        ]
        self.assertEqual(
            discriminator["eligible_keys_recorded"], hand_walked,
            "the manifest's eligible list is the recorded order of the two "
            "conditions the legacy helper tests",
        )
        delivered = combat_envelope.select_eligible_rows(
            village["maps"][0]["items"], 1020
        )
        self.assertEqual(
            delivered["eligible_keys"], hand_walked,
            "the delivered selector agrees with the hand-written walk",
        )
        self.assertEqual(delivered["addressed_key"], discriminator["first_recorded"])
        self.assertNotEqual(
            hand_walked[0], min(hand_walked, key=int),
            "and the first recorded eligible key is not its numeric minimum, which "
            "is what makes the order claim testable at all",
        )

    def test_the_order_of_record_is_the_committed_document_not_the_snapshot(
        self,
    ) -> None:
        """Where the selection order lives, measured rather than assumed.

        The shared capture writer serialises every fixture document with
        ``sort_keys=True``, so each snapshot's ``items`` keys are in
        LEXICOGRAPHIC order while the oracle walked the in-memory save, whose
        order is the committed village document's.  The two orders give
        DIFFERENT answers here -- 2425 against 1022 -- so the discriminator is
        only real against the committed document.  A replay that reset the corpus
        from ``before.json`` would remove 1022 and still compare equal leaf for
        leaf, because :func:`harness.diff_documents` walks keys rather than
        positions, which is exactly why this is asserted here.
        """
        record = FIXTURE["manifest"]["order_of_record"]
        self.assertTrue(record["writer_sorts_keys"])
        self.assertIn("sort_keys=True", record["writer"])

        village = json.loads(
            (harness.REPO_ROOT / "villages" / "AcidCaos.json").read_text(
                encoding="utf-8"
            )
        )
        snapshot = FIXTURE["txn_resolve_first_by_recorded_order"]["before"]
        committed_order = list(village["maps"][0]["items"])
        snapshot_order = list(snapshot["maps"][0]["items"])

        self.assertTrue(record["snapshot_order_differs_from_committed_order"])
        self.assertTrue(record["snapshot_order_is_lexicographic"])
        self.assertFalse(
            record["committed_order_is_lexicographic"],
            "the committed document's own order is the unsorted one the claim needs",
        )
        self.assertEqual(snapshot_order, sorted(snapshot_order))
        self.assertNotEqual(snapshot_order, committed_order)
        self.assertEqual(record["committed_order_first_three_keys"], committed_order[:3])
        self.assertEqual(record["snapshot_order_first_three_keys"], snapshot_order[:3])

        # The two orders really do answer differently, and the oracle followed the
        # committed one.
        committed_first = combat_envelope.select_eligible_rows(
            village["maps"][0]["items"], 1020
        )["eligible_keys"][0]
        snapshot_first = combat_envelope.select_eligible_rows(
            snapshot["maps"][0]["items"], 1020
        )["eligible_keys"][0]
        self.assertEqual(record["first_eligible_committed_order"], committed_first)
        self.assertEqual(record["first_eligible_snapshot_order"], snapshot_first)
        self.assertNotEqual(
            committed_first, snapshot_first,
            "if these agreed the recorded-order claim would be untestable",
        )
        self.assertEqual(
            record["row_the_oracle_actually_removed"], ["2425"]
        )
        self.assertEqual(committed_first, "2425")
        self.assertEqual(snapshot_first, "1022")
        self.assertIn(
            "COMMITTED VILLAGE DOCUMENT (villages/AcidCaos.json)",
            record["order_of_record"],
        )
        self.assertIn(
            "before.json/after.json are NOT the order of record",
            record["order_of_record"],
        )

        # And the difference is INVISIBLE to a document diff, which is the whole
        # hazard: a sorted copy of the same document reports no difference at all.
        reordered = json.loads(json.dumps(snapshot))
        reordered["maps"][0]["items"] = {
            key: snapshot["maps"][0]["items"][key] for key in committed_order
        }
        self.assertEqual(
            harness.diff_documents(snapshot, reordered), [],
            "re-ordering the keys is invisible to the comparator, so a snapshot-"
            "seeded replay would mis-select a row and still pass every state check",
        )

    def test_every_recorded_response_is_the_legacy_success_or_error_page(self) -> None:
        for name in STEP_NAMES:
            step = FIXTURE[name]
            with self.subTest(step=name):
                self.assertEqual(step["transaction"]["expected_status"],
                                 step["meta"]["status"])
                if step["transaction"]["status"] == 200:
                    self.assertEqual(
                        json.loads(step["body"]), {"result": "success"}
                    )
                else:
                    self.assertEqual(step["transaction"]["status"], 500)
                    self.assertTrue(
                        step["transaction"]["failure_is_framework_error_page"]
                    )
                    self.assertEqual(
                        step["transaction"]["failure_body_sha256"],
                        sha256_of(STEPS / name / "response.body"),
                        "the recorded 500 body digest matches the recorded file",
                    )

    def test_every_recorded_transaction_ran_under_the_neutral_vector(self) -> None:
        manifest = FIXTURE["manifest"]
        self.assertEqual(
            manifest["batch_shape"]["resource_vector"], [0] * 8
        )
        self.assertEqual(
            manifest["batch_shape"]["vector_status"],
            "neutral by construction, every transaction",
        )
        for name in STEP_NAMES:
            step = FIXTURE[name]
            with self.subTest(step=name):
                self.assertTrue(step["transaction"]["resource_neutral"])
                self.assertEqual(step["transaction"]["resources_before"],
                                 step["transaction"]["resources_after"])
                self.assertEqual(step["transaction"]["resources_before"],
                                 resources_of(step["before"]))

    def test_the_manifest_records_the_central_divergence_by_number(self) -> None:
        divergences = FIXTURE["manifest"]["divergences"]
        self.assertEqual(divergences["count"], 1)
        central = divergences["central"]
        self.assertFalse(central["parity_claimed"])
        self.assertEqual(central["oracle_rows_removed_one"], 1)
        self.assertEqual(central["oracle_rows_removed_two"], 2)
        self.assertEqual(central["modern_derives_rows_removed"], 1)
        self.assertEqual(central["oracle_printed_counts"], [[1], [2]])
        self.assertTrue(central["same_crafted_identity"])
        entry = FIXTURE[DIVERGENT_STEP]["transaction"]
        self.assertFalse(entry["parity_with_delivered_endpoint"])
        self.assertEqual(entry["removed_keys"], ["2425", "1022"])
        self.assertEqual(entry["rows_removed"], 2)
        self.assertEqual(entry["ledger_after"], {"1020": 2})
        self.assertEqual(entry["modern_derives_removed_keys"], ["2425"])
        self.assertEqual(entry["modern_derives_ledger"], {"1020": 1})
        self.assertEqual(entry["crafted_units"], [[1020, 0, 3, 1]])
        self.assertIn("EXHAUSTION OF MATCHES", entry["divergence"])
        self.assertEqual(divergences["recorded_not_narrowed"], True)

    def test_the_manifest_records_the_measured_batch_persistence_boundary(self) -> None:
        boundary = FIXTURE["manifest"]["divergences"]["persistence_boundary"]
        self.assertEqual(boundary["all_three_failed_with"], 500)
        for stage in ("before", "batch", "after"):
            self.assertEqual(boundary["%s_rows_removed" % stage], 0)
            self.assertTrue(boundary["%s_state_unchanged" % stage])
        self.assertTrue(boundary["in_memory_mutation_happened"])
        self.assertEqual(
            boundary["printed_but_not_persisted"]["resolve_absent_victim"][
                "printed"
            ],
            1,
        )
        for name in ("resolve_absent_victim", "resolve_batch_discarded_on_raise"):
            with self.subTest(step=name):
                self.assertEqual(boundary["printed_but_not_persisted"][name][
                    "persisted_rows_removed"
                ], 0)
        evidence = boundary["in_memory_mutation_evidence"]
        self.assertIn("save_session(command.py:32)", evidence)
        self.assertIn(
            "The persistence boundary is therefore the BATCH", evidence
        )
        self.assertIn("an exception skips it", evidence)

    def test_the_manifest_records_both_ledger_arms_as_distinct_transitions(self) -> None:
        increment = FIXTURE["txn_ledger_increment_existing"]["transaction"]
        created = FIXTURE["txn_ledger_key_created"]["transaction"]
        # A count that moves while the KEY COUNT does not.
        self.assertEqual(increment["ledger_keys_before"], 28)
        self.assertEqual(increment["ledger_keys_after"], 28)
        self.assertEqual(increment["ledger_before"]["1034"], 4)
        self.assertEqual(increment["ledger_after"]["1034"], 5)
        # A key created at 1.
        self.assertEqual(created["ledger_keys_before"], 28)
        self.assertEqual(created["ledger_keys_after"], 29)
        self.assertNotIn("1023", created["ledger_before"])
        self.assertEqual(created["ledger_after"]["1023"], 1)
        self.assertEqual(increment["ledger_before"]["1034"], 4)
        self.assertEqual(
            created["ledger_before"]["1034"], 4,
            "both ledger steps start from the same recorded ledger",
        )
        census = FIXTURE["manifest"]["seeds"]["ledger"]["census"]
        self.assertEqual(census["ledger_keys"], 28)
        self.assertEqual(census["ledger_item_count_before"], 4)
        self.assertEqual(census["create_item_count_before"], "<absent>")
        self.assertEqual(census["ledger_item_first_key"], "37521")
        self.assertEqual(census["create_item_first_key"], "20239")

    def test_the_manifest_records_its_containment_and_its_non_claims(self) -> None:
        containment = FIXTURE["manifest"]["containment"]
        self.assertTrue(containment["identical"])
        self.assertEqual(containment["combined_before"], containment["combined_after"])
        self.assertTrue(containment["working_tree_saves_absent"])
        self.assertTrue(containment["protected_fixtures_unchanged"])
        self.assertEqual(
            len(containment["protected_fixtures"]), 18,
            "the seventeen prior fixtures plus the boot fixture",
        )
        self.assertIn("godot-unit-experience", containment["protected_fixtures"])
        for seed in SEED_NAMES:
            self.assertEqual(
                containment["seed_sha256_before"][seed],
                containment["seed_sha256_after"][seed],
            )
        not_claimed = FIXTURE["manifest"]["not_claimed"]
        self.assertGreaterEqual(len(not_claimed), 8)
        joined = " ".join(not_claimed)
        for field in ("attack", "defense", "life", "attack_interval", "attack_range"):
            with self.subTest(field=field):
                self.assertIn(field, joined)
        self.assertIn("godot-mission-vocabulary", joined)
        self.assertIn("occupancy, bounds, type, or terrain validation", joined)
        self.assertIn("it is recorded, not exercised and not refused", joined)
        self.assertIn("The client was never executed", joined)
        self.assertIn("rather than reporting parity by omission", joined)
        self.assertIn("The oracle never persists one", joined)

    def test_the_five_malformed_blob_steps_are_marked_not_replayed(self) -> None:
        """They are recorded state, and this suite says so rather than counting them.

        The oracle reads a client blob; this endpoint accepts none, so there is no
        request that asks the same question.  Counting them as replayed parity
        would claim something the request shape cannot deliver.
        """
        for name in NOT_EXPRESSIBLE:
            with self.subTest(step=name):
                step = FIXTURE[name]
                self.assertEqual(step["transaction"]["command"], "end_attack")
                self.assertEqual(step["transaction"]["rows_removed"], 0)
                self.assertFalse(step["transaction"]["ledger_moved"])
                self.assertEqual(step["after"], step["before"])
                self.assertEqual(
                    step["transaction"]["parity_with_delivered_endpoint"], True,
                    "the manifest claims state parity for these, which is what the "
                    "state comparison below actually establishes",
                )
        replayed = {name for name, _, _ in STATE_PARITY}
        replayed |= {name for name, _, _, _, _ in REFUSAL_PARITY}
        replayed.add(DIVERGENT_STEP)
        self.assertEqual(
            replayed | set(NOT_EXPRESSIBLE), set(STEP_NAMES),
            "every recorded step is either replayed, refused, or explicitly not "
            "expressible -- none is silently dropped",
        )
        self.assertEqual(
            len(replayed), 8,
            "five state parity, two refusal parity, and the one divergence",
        )
        self.assertEqual(len(NOT_EXPRESSIBLE), 5)
        self.assertEqual(len(STATE_PARITY), 5)
        self.assertEqual(len(REFUSAL_PARITY), 2)


# ---------------------------------------------------------------- the replay --
class ReplayTests(unittest.TestCase):
    """Each recorded transaction replayed against the delivered endpoint."""

    def replay(self, name: str, action: str, addressing: Dict[str, Any]):
        pid = reset(name)
        response = combat_now(pid, action, **addressing)
        return response, persisted(pid)

    def test_every_state_parity_step_reproduces_the_recorded_after_state(self) -> None:
        for name, action, addressing in STATE_PARITY:
            with self.subTest(step=name):
                response, document = self.replay(name, action, addressing)
                self.assertEqual(response.status_code, 200, name)
                body = response.get_json()
                self.assertTrue(body["ok"], name)
                self.assertEqual(body["result"], "success", name)
                recorded = FIXTURE[name]
                differences = harness.diff_documents(recorded["after"], document)
                self.assertEqual(
                    differences, [],
                    "%s: the persisted document differs from the recorded "
                    "after-state" % name,
                )
                self.assertEqual(
                    body["changed"],
                    recorded_changed_pointers(recorded["transaction"]),
                    "%s: the derived changed-pointer set is exactly the recorded "
                    "one, reduced from the recorded leaf diff" % name,
                )
                if recorded["transaction"]["changed_leaf_count"] == 0:
                    self.assertEqual(
                        body["changed"], [],
                        "%s: a recorded no-change replay reports no pointer" % name,
                    )

    def test_the_derived_row_is_the_recorded_first_by_recorded_order(self) -> None:
        """D1 end to end, on the one committed identity that discriminates it."""
        response, document = self.replay(
            "txn_resolve_first_by_recorded_order", "resolve", {"item_id": 1020}
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        recorded = FIXTURE["txn_resolve_first_by_recorded_order"]["transaction"]
        self.assertEqual(body["destruction"]["derived_key"], "2425")
        self.assertEqual(body["destruction"]["count"], 1)
        self.assertEqual(body["destruction"]["rows_before"],
                         recorded["rows_before"])
        self.assertEqual(body["destruction"]["rows_after"],
                         recorded["rows_after"])
        self.assertEqual(body["ledger_written"], True)
        self.assertEqual(body["ledger_gates"]["player_team_one"]["holds"], True)
        self.assertEqual(body["ledger_gates"]["resurrectable_positive"]["holds"], True)
        # The recorded order, not a sort: 2425 is removed while the numeric
        # minimum 897 survives, and the surviving key order still holds 897.
        self.assertNotIn("2425", document["maps"][0]["items"])
        self.assertIn("897", document["maps"][0]["items"])
        self.assertEqual(body["destruction"]["eligible_keys"],
                         FIXTURE["manifest"]["recorded_order_discriminator"][
                             "eligible_keys_recorded"])
        # The surviving key ORDER is compared against the **committed village
        # document**, not the recorded snapshot: the snapshot's own keys are
        # lexicographically sorted by the shared writer, so comparing against it
        # would assert the sorted order and prove nothing about recorded order.
        # See test_the_order_of_record_is_the_committed_document_not_the_snapshot.
        self.assertEqual(
            placement_keys(document),
            [
                key for key in placement_keys(committed_seed("destruction"))
                if key != "2425"
            ],
            "the surviving keys keep the committed document's own insertion "
            "order, with the one derived key gone",
        )
        self.assertNotEqual(
            placement_keys(document),
            sorted(placement_keys(document)),
            "and that order is not lexicographic, which is what makes it the "
            "recorded order rather than a sort",
        )
        self.assertNotEqual(placement_keys(document),
                            sorted(placement_keys(document), key=int))

    def test_the_two_ledger_arms_are_reproduced_as_two_distinct_transitions(self) -> None:
        # Arm one: a count that moves while the KEY COUNT does not.
        response, document = self.replay(
            "txn_ledger_increment_existing", "resolve", {"item_id": 1034}
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        recorded = FIXTURE["txn_ledger_increment_existing"]["transaction"]
        self.assertEqual(body["destruction"]["derived_key"], "37521")
        self.assertEqual(body["ledger_written"], True)
        self.assertEqual(len(document["privateState"][LEDGER_KEY]), 28,
                         "the key count does not move")
        self.assertEqual(document["privateState"][LEDGER_KEY]["1034"], 5)
        self.assertEqual(harness.diff_documents(recorded["ledger_after"],
                                                document["privateState"][LEDGER_KEY]),
                         [])
        # Key ORDER against the committed village, for the same reason the
        # placement order is: the recorded snapshot sorts its keys.
        committed_ledger_keys = list(
            committed_seed("ledger")["privateState"][LEDGER_KEY]
        )
        self.assertEqual(
            list(document["privateState"][LEDGER_KEY]),
            committed_ledger_keys,
            "the committed document's ledger insertion order survives the "
            "increment, with no key added and none moved",
        )
        self.assertEqual(
            [entry["item_id"] for entry in body["ledger_after"]],
            committed_ledger_keys,
            "and the response reports that persisted order, not the shared "
            "projection's sort",
        )

        # Arm two: a key created at 1, appended.
        response, document = self.replay(
            "txn_ledger_key_created", "resolve", {"item_id": 1023}
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        recorded = FIXTURE["txn_ledger_key_created"]["transaction"]
        self.assertEqual(body["destruction"]["derived_key"], "20239")
        self.assertEqual(body["ledger_written"], True)
        self.assertEqual(len(document["privateState"][LEDGER_KEY]), 29,
                         "the key count DOES move")
        self.assertEqual(document["privateState"][LEDGER_KEY]["1023"], 1)
        self.assertEqual(harness.diff_documents(recorded["ledger_after"],
                                                document["privateState"][LEDGER_KEY]),
                         [])
        self.assertEqual(
            list(document["privateState"][LEDGER_KEY]),
            committed_ledger_keys + ["1023"],
            "the committed document's key order with the created key appended at "
            "the end (engine.py:164-167)",
        )
        self.assertEqual(list(document["privateState"][LEDGER_KEY])[-1], "1023",
                         "the created key is appended, not sorted in")
        self.assertNotEqual(
            list(document["privateState"][LEDGER_KEY]),
            sorted(document["privateState"][LEDGER_KEY], key=int),
            "and the appended order really is not the numerically sorted order",
        )

    def test_kill_deletes_the_addressed_row_and_the_ledger_stays_byte_identical(
        self,
    ) -> None:
        response, document = self.replay(
            "txn_kill_unit_row", "kill", {"map_key": 1639}
        )
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        recorded = FIXTURE["txn_kill_unit_row"]["transaction"]
        self.assertEqual(body["command"], combat_envelope.KILL_COMMAND)
        self.assertEqual(body["destruction"]["derived_key"], "1639")
        self.assertFalse(body["ledger_written"])
        self.assertEqual(body["ledger_before"], [])
        self.assertEqual(body["ledger_after"], [])
        self.assertNotIn("1639", document["maps"][0]["items"])
        self.assertEqual(
            harness.diff_documents(FIXTURE["txn_kill_unit_row"]["after"], document), []
        )
        self.assertEqual(
            document["maps"][0]["items"]["2425"],
            FIXTURE["txn_kill_unit_row"]["before"]["maps"][0]["items"]["2425"],
            "a neighbouring row is untouched",
        )

    def test_kill_iid_reproduces_the_recorded_no_op_on_the_persisted_document(self) -> None:
        pid = reset("txn_kill_iid_no_op")
        recorded = FIXTURE["txn_kill_iid_no_op"]
        response = combat_now(pid, "kill_iid", item_id=1076)
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["command"], combat_envelope.KILL_IID_COMMAND)
        self.assertEqual(body["destruction"]["count"], 0)
        self.assertIsNone(body["destruction"]["derived_key"])
        self.assertEqual(body["changed"], [])
        self.assertFalse(body["ledger_written"])
        self.assertEqual(harness.diff_documents(recorded["after"], persisted(pid)), [])
        # The documented BYTES caveat, exercised rather than asserted.  The legacy
        # batch always calls ``save_session``, which re-serialises the document
        # with its own newline convention, so a proven no-op still rewrites the
        # file: the raw bytes differ from the recorded file's while the documents
        # are identical.  Both halves are asserted, so the difference cannot be
        # waved through as "close enough" in either direction.
        replayed_bytes = save_path(pid).read_bytes()
        recorded_bytes = (STEPS / "txn_kill_iid_no_op" / "after.json").read_bytes()
        self.assertNotEqual(
            replayed_bytes,
            recorded_bytes,
            "the raw bytes differ while the documents match, which is exactly why "
            "the byte comparison is not the claim",
        )
        self.assertEqual(
            json.loads(replayed_bytes.decode("utf-8")),
            json.loads(recorded_bytes.decode("utf-8")),
            "and the two byte strings really do parse to the same document",
        )

    def test_each_refusal_reproduces_the_recorded_no_change_by_a_named_code(self) -> None:
        for name, action, addressing, code, status in REFUSAL_PARITY:
            with self.subTest(step=name):
                pid = reset(name)
                recorded = FIXTURE[name]
                before_bytes = save_path(pid).read_bytes()
                response = combat_now(pid, action, **addressing)
                self.assertEqual(response.status_code, status, name)
                body = response.get_json()
                self.assertFalse(body["ok"])
                self.assertEqual(body["error"]["code"], code, name)
                self.assertEqual(
                    body["error"]["code"],
                    recorded["transaction"]["delivered_endpoint_refusal"],
                    "the refusal code is the one the capture recorded",
                )
                self.assertEqual(sorted(body), ["error", "ok", "protocol"])
                self.assertEqual(
                    save_path(pid).read_bytes(), before_bytes,
                    "%s: a refusal persists nothing, so the file the suite wrote "
                    "is byte-identical" % name,
                )
                self.assertEqual(
                    harness.diff_documents(recorded["after"], persisted(pid)), [],
                    "%s: the recorded oracle changed nothing and neither did the "
                    "endpoint" % name,
                )
                # The oracle's own answer was legacy SUCCESS, so the refusal is a
                # recorded divergence from the response and a parity match from
                # the state.  Both halves are asserted, not one of them.
                self.assertEqual(recorded["transaction"]["status"], 200)
                self.assertEqual(
                    json.loads(recorded["body"]), {"result": "success"}
                )

    def test_the_five_malformed_blob_steps_are_recorded_state_and_not_parity(self) -> None:
        """No request on this endpoint asks the question the oracle answered.

        So the only honest replay is the STATE claim the manifest makes for these
        five: the recorded document does not move.  Asserting that they replay
        would require inventing a client blob the request shape deliberately has
        no field for.
        """
        for name in NOT_EXPRESSIBLE:
            with self.subTest(step=name):
                step = FIXTURE[name]
                self.assertEqual(step["after"], step["before"])
                self.assertEqual(step["transaction"]["rows_removed"], 0)
                self.assertEqual(step["transaction"]["ledger_moved"], False)
                self.assertEqual(step["transaction"]["changed_leaf_count"], 0)
                self.assertEqual(step["transaction"]["changed_leaves"], [])
                self.assertEqual(
                    harness.diff_documents(step["after"], step["before"]), []
                )

    def test_the_client_dictated_count_is_refused_and_the_divergence_is_real(self) -> None:
        """The recorded difference, measured from BOTH sides rather than asserted."""
        name = DIVERGENT_STEP
        recorded = FIXTURE[name]["transaction"]
        pid = reset(name)
        before_bytes = save_path(pid).read_bytes()
        before = persisted(pid)

        # 1. The oracle really removed TWO rows and incremented the ledger twice.
        self.assertEqual(recorded["removed_keys"], ["2425", "1022"])
        self.assertEqual(recorded["rows_removed"], 2)
        self.assertEqual(recorded["rows_before"] - recorded["rows_after"], 2)
        self.assertEqual(recorded["ledger_after"], {"1020": 2})
        recorded_after = FIXTURE[name]["after"]
        for key in ("2425", "1022"):
            with self.subTest(oracle_removed=key):
                self.assertIn(key, before["maps"][0]["items"])
                self.assertNotIn(key, recorded_after["maps"][0]["items"])
        self.assertEqual(
            len(before["maps"][0]["items"]) - len(recorded_after["maps"][0]["items"]),
            2,
        )

        # 2. The endpoint REFUSES the same client-dictated count.
        payload_keys = list(combat_envelope.DESTRUCTION_COUNT_KEYS) + list(
            combat_envelope.SENT_SURVIVED_KEYS
        )
        self.assertGreaterEqual(len(payload_keys), 2)
        for key in payload_keys:
            with self.subTest(client_key=key):
                body = combat_now(pid, "resolve", item_id=1020, **{key: 1}).get_json()
                self.assertFalse(body["ok"])
                self.assertEqual(body["error"]["code"],
                                 "client_dictated_destruction")
                self.assertEqual(save_path(pid).read_bytes(), before_bytes)

        # 3. And the SAME request WITHOUT the client count destroys exactly one.
        response = combat_now(pid, "resolve", item_id=1020)
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["destruction"]["derived_key"], "2425")
        self.assertEqual(body["destruction"]["count"], 1)
        self.assertEqual(body["ledger_after"], [{"item_id": "1020", "count": 1}])
        self.assertEqual(
            body["destruction"]["rows_before"],
            len(before["maps"][0]["items"]),
            "the derived pre-state row count is the corpus's own",
        )
        self.assertEqual(
            body["destruction"]["rows_after"],
            len(before["maps"][0]["items"]) - 1,
            "exactly one row, where the oracle removed two",
        )
        self.assertIn("1022", persisted(pid)["maps"][0]["items"],
                      "the second eligible row survives where the oracle took it")
        self.assertNotEqual(
            harness.diff_documents(recorded_after, persisted(pid)), [],
            "the two states genuinely differ, so this is a divergence and not a "
            "fixture that happens to agree",
        )

    def test_the_comparison_fails_on_an_altered_row_count_or_ledger_value(self) -> None:
        """Task 1.3: the comparator must be able to fail, proven here every run."""
        step = FIXTURE["txn_ledger_increment_existing"]
        response, document = self.replay(
            "txn_ledger_increment_existing", "resolve", {"item_id": 1034}
        )
        self.assertEqual(response.status_code, 200)
        body_derived_key = response.get_json()["destruction"]["derived_key"]
        self.assertIsInstance(body_derived_key, str)
        self.assertNotIn(
            body_derived_key, document["maps"][0]["items"],
            "the derived row really is the one the replay removed",
        )
        self.assertEqual(harness.diff_documents(step["after"], document), [],
                         "the honest comparison passes first")

        # (a) An altered ROW COUNT: one row removed too FEW, i.e. one row that the
        # recording says is gone is put back.  The injected key is measured
        # absent first, so the copy genuinely carries one row more rather than
        # overwriting a real one and changing nothing.
        short = json.loads(json.dumps(step["after"]))
        injected_key = "897"
        self.assertNotIn(
            injected_key, step["after"]["maps"][0]["items"],
            "the injected key is absent from the recorded after-state, so adding "
            "it changes the row count instead of replacing a row",
        )
        self.assertNotIn(
            injected_key, document["maps"][0]["items"],
            "and the replay really did not place it",
        )
        short["maps"][0]["items"][injected_key] = [0, 0, 0, 0, 0, [], {}, 1]
        self.assertEqual(
            len(step["after"]["maps"][0]["items"]) + 1,
            len(short["maps"][0]["items"]),
            "the hand-edited copy really does carry one row too many",
        )
        altered_rows = harness.diff_documents(step["after"], short)
        self.assertTrue(altered_rows, "a row-count change must be reported")
        self.assertTrue(
            any("maps/0/items/%s" % injected_key in entry for entry in altered_rows),
            altered_rows,
        )

        # (b) An altered LEDGER VALUE: the count the increment moved.
        wrong = json.loads(json.dumps(document))
        wrong["privateState"][LEDGER_KEY]["1034"] = 99
        altered_ledger = harness.diff_documents(step["after"], wrong)
        self.assertTrue(altered_ledger, "a ledger-value change must be reported")
        self.assertTrue(
            any("deadHeroes/1034" in entry for entry in altered_ledger),
            altered_ledger,
        )

        # (c) And the same two alterations against the LIVE document, so the
        # demonstration is not confined to a hand-edited copy.
        live_rows = json.loads(json.dumps(document))
        # The derived key is the row the replay really removed, so re-adding it
        # is the same alteration against the LIVE document rather than a copy.
        live_rows["maps"][0]["items"][body_derived_key] = [0, 0, 0, 0, 0, [], {}, 1]
        self.assertTrue(
            harness.diff_documents(document, live_rows),
            "re-adding the derived row is reported against the live document too",
        )
        live_ledger = json.loads(json.dumps(document))
        live_ledger["privateState"][LEDGER_KEY]["1034"] = 4
        self.assertTrue(
            harness.diff_documents(document, live_ledger),
            "and so is a reverted ledger value",
        )

    def test_no_stored_resource_moves_across_every_replayed_step(self) -> None:
        for name, action, addressing in STATE_PARITY:
            with self.subTest(step=name):
                response, document = self.replay(name, action, addressing)
                self.assertEqual(response.status_code, 200, name)
                body = response.get_json()
                self.assertEqual(sorted(body["resources"]), sorted(RESOURCE_NAMES))
                self.assertEqual(
                    body["resources"], resources_of(FIXTURE[name]["after"]),
                    "%s: every stored resource is the recorded value" % name,
                )
                self.assertEqual(
                    resources_of(document), resources_of(FIXTURE[name]["before"]),
                    "%s: and the pre-execution values were identical" % name,
                )

    def test_the_response_carries_no_session_list_field(self) -> None:
        """The one thing the co-resident save changes is never carried here."""
        response, _ = self.replay(
            "txn_resolve_first_by_recorded_order", "resolve", {"item_id": 1020}
        )
        body = response.get_json()
        for field in ("saves", "neighbors", "neighbours", "sessions", "users"):
            self.assertNotIn(field, body)
        self.assertGreater(body["server_time"], 0,
                           "the one volatile field is a positive instant")

    def test_the_co_resident_village_did_not_perturb_the_replay(self) -> None:
        """What holds the two-seeds-in-one-corpus mechanism up, stated and checked.

        The capture ran each village in its own server, and this corpus holds
        both.  The claim that the extra save cannot have changed the combat path
        is therefore checked where it can be: the recorded single-village results
        are reproduced exactly, and every recorded identity resolves against its
        own save and no other.
        """
        # Both seeds are put back to their first recorded step first.  The census
        # below is a statement about the two committed documents, and every other
        # test in this class mutates them, so reading the counts off whatever the
        # previous test happened to leave would measure the class's own ordering.
        for name in SEED_NAMES:
            first = [step for step in STEP_NAMES if seed_of(step) == name][0]
            reset(first)
        self.assertEqual(
            sorted(BOOT.known_user_ids()),  # type: ignore[union-attr]
            sorted(PIDS.values()),
            "exactly the two recorded village pids are resident",
        )
        for name in SEED_NAMES:
            with self.subTest(seed=name):
                pid = pid_of(name)
                document = BOOT.save_document(pid)  # type: ignore[union-attr]
                self.assertEqual(
                    str(document["playerInfo"]["pid"]), pid
                )
                self.assertEqual(
                    len(document["maps"][0]["items"]),
                    FIXTURE["manifest"]["seeds"][name]["census"]["placed_rows"],
                )
                self.assertEqual(
                    len(document["privateState"][LEDGER_KEY]),
                    FIXTURE["manifest"]["seeds"][name]["census"]["ledger_keys"],
                )
        # The recorded order discriminator belongs to the destruction seed only.
        pid = pid_of("destruction")
        self.assertEqual(
            len(BOOT.save_document(pid)["maps"][0]["items"]),  # type: ignore[union-attr]
            319,
        )

    def test_the_working_tree_save_did_not_move(self) -> None:
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_no_server_is_running(self) -> None:
        for port in (5055, 5056):
            self.assertTrue(harness.port_is_free("127.0.0.1", port), port)


if __name__ == "__main__":
    unittest.main()
