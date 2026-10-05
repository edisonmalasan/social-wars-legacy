#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/magic`` vs the executed-legacy
magic-counter fixture (OpenSpec task 1.3, ``godot-damage``).

No server and no network: the endpoint runs through Flask's in-process test
client under the ``offline`` guard (which fails the run if any socket tries to
connect), and :meth:`ReplayTests.test_no_server_is_running` asserts that neither
the legacy port (5055) nor the Compatibility API port (5056) is listening.

What is replayed
    The committed transactions under ``tests/fixtures/godot-damage/``: **twelve**
    executed-legacy transactions against the single recorded seed
    ``villages/Neutral.json``, every one carrying the **neutral** eight-slot
    vector.  The endpoint executes the **unchanged** legacy dispatcher, so the
    comparison is the persisted corpus document against each recorded
    after-state, leaf for leaf, with no pruning at all.

    Only three things are deliberately NOT compared by value:

    * the **raw bytes** of the corpus save across a state boundary.
      ``sessions.save_session`` re-serialises the document with the platform's
      newline convention (CRLF on Windows) while this suite writes LF, so two
      identical documents can differ byte for byte.  Byte-identity IS asserted
      where it is available and meaningful: a **refused** request persists
      nothing at all, so the file the suite wrote itself must come back with its
      own digest unchanged.
    * the ``server_time`` envelope field, which is a wall-clock reading and is
      asserted only to be a positive integer.
    * the ledger's **key ORDER**, which the recording's sorted snapshots cannot
      carry.  The oracle walked the in-memory save and appended a created key;
      the two orders are asserted separately rather than folded into one equality.

The recording is ONE interleaved sequence, and both replay modes exist for that
    ``manifest['server']['starts']`` is **1** and ``cleanup['disposables']`` is
    **1**: the whole ladder ran against a single disposable corpus, so step N's
    pre-state is step N-1's after-state.  Two things follow, and the suite does
    both rather than picking one:

    ``per step``
        Reset the corpus to **that step's own recorded ``before.json``** and
        send only its request.  This is what makes each step's comparison a
        claim about that transaction rather than about a prefix of the ladder.

    ``chained``
        Reset to the **committed village** once and walk the twelve steps in the
        manifest's recorded order.  This is what proves the recording really is
        one sequence, and it is also where the delivered endpoint stops following
        the oracle.

Three classes of recorded transaction, and what each one means here

    ``STATE PARITY`` -- seven steps
        ``use_1_from_two``, the four ``buy_1_*`` growth steps,
        ``use_1_at_the_cap_unchanged`` and ``use_absent_id_3_creates_zero``.  The
        endpoint answers 200 and the persisted document equals the recorded
        after-state, leaf for leaf.

    ``STATE PARITY THROUGH A REFUSAL`` -- one step
        ``use_string_id_resolves_the_same_key``.  The oracle executed
        ``use_magic(['1'])``, which resolved to the same key and changed nothing;
        this endpoint **refuses** the string identity with
        ``non_canonical_magic_id`` and changes nothing either, so the state
        matches while the response does not.

    ``REFUSED, AND THE STATE UNCHANGED TOO`` -- four steps
        ``buy_1_still_climbing`` and ``use_1_destroys_charges``
        (``counter_above_cap``), ``buy_out_of_table_id_99_accepted``
        (``unknown_magic_id``) and ``use_float_id_creates_a_distinct_key``
        (``non_canonical_magic_id``).  The oracle answered legacy success and
        wrote a value; this endpoint refuses and leaves the recorded document
        byte-identical.

THE CENTRAL MEASUREMENT: three answers, not one
    ``buy_1_still_climbing`` (63 to 113) and ``use_1_destroys_charges`` (113 to
    50) are refused outright, because design D3 refuses both legacy defects and
    a recorded counter **above** the recorded literal cap is precisely the state
    those defects produced.  That is the sharpest thing in the line: the oracle's
    own ladder is what closes the modern endpoint, four requests later.

    It also means the flag ``parity_with_delivered_endpoint`` does **not** mean
    what its name says.  Measured over all twelve steps, the flag is the
    comparison of the oracle's number with the **derived** transition, and it is
    recorded only where a derived number exists -- four of the twelve
    transactions carry ``modern_derives_after`` and eight do not.  The three
    answers are therefore kept apart here:

    * the **oracle** value, read from the recording;
    * the **derived** value, reported by the endpoint under
      ``counter.derived_after``;
    * the **endpoint's response**, which for five of the twelve steps is a
      refusal and never a transition at all.

    :meth:`ReplayTests.test_the_recorded_parity_flag_is_not_an_endpoint_response`
    measures the contradiction on the one step whose flag is ``True`` while the
    endpoint refuses.

    And the inverse, the other half of the D3/D5 collision: for the seven
    ``STATE PARITY`` steps the persisted value equals the **oracle's**, because
    the unchanged dispatcher ran, while ``counter.matches_derived`` is ``False``
    on five of them.  The endpoint's own 200 response therefore does not
    reproduce its own contract, and
    :meth:`ReplayTests.test_the_endpoint_persists_the_oracle_value_while_reporting_its_own_differs`
    asserts exactly that rather than letting the state comparison imply
    agreement that is not there.

The comparison is proved able to fail
    Task 1.3 requires this suite to fail if the recorded ledger transition or the
    recorded resource-comparison result is altered.
    :meth:`ReplayTests.test_the_comparison_fails_on_an_altered_ledger_transition_or_an_altered_resource_comparison`
    makes that permanent by feeding the comparator an altered ledger value, a
    dropped ledger key, an extra ledger key and an altered resource slot, and
    requiring it to report each one.  A comparator that could not fail would pass
    this suite.
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

import magic_envelope
import compat_legacy
import compat_service

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-damage"
STEPS = FIXTURES / "steps"
LOGIN_STEP = "login_post"

#: Every recorded step directory, in the manifest's recorded order.
STEP_NAMES = (
    "txn_use_1_from_two",
    "txn_buy_1_unbounded_first",
    "txn_buy_1_unbounded_second",
    "txn_buy_1_unbounded_third",
    "txn_buy_1_crossed_the_cap",
    "txn_buy_1_still_climbing",
    "txn_use_1_destroys_charges",
    "txn_use_1_at_the_cap_unchanged",
    "txn_use_absent_id_3_creates_zero",
    "txn_buy_out_of_table_id_99_accepted",
    "txn_use_string_id_resolves_the_same_key",
    "txn_use_float_id_creates_a_distinct_key",
)

#: Steps the delivered endpoint reproduces **as a successful execution**:
#: ``(step, action, magic_id sent, derived_after, matches_derived)``.  The two
#: derived numbers that agree with the oracle are pinned exactly; the five that do
#: not are pinned exactly too, because "it agrees" and "it does not" are both
#: claims a re-capture could invalidate.
STATE_PARITY = (
    ("txn_use_1_from_two", "use", 1, 3, True),
    ("txn_buy_1_unbounded_first", "buy", 1, 4, False),
    ("txn_buy_1_unbounded_second", "buy", 1, 8, False),
    ("txn_buy_1_unbounded_third", "buy", 1, 16, False),
    ("txn_buy_1_crossed_the_cap", "buy", 1, 32, False),
    ("txn_use_1_at_the_cap_unchanged", "use", 1, 50, True),
    ("txn_use_absent_id_3_creates_zero", "use", 3, 1, False),
)

#: Steps the oracle executed and this endpoint **refuses**:
#: ``(step, action, magic_id sent, expected code, expected status)``.
REFUSALS = (
    ("txn_buy_1_still_climbing", "buy", 1, "counter_above_cap", 409),
    ("txn_use_1_destroys_charges", "use", 1, "counter_above_cap", 409),
    ("txn_buy_out_of_table_id_99_accepted", "buy", 99, "unknown_magic_id", 409),
    ("txn_use_string_id_resolves_the_same_key", "use", "1", "non_canonical_magic_id", 400),
    ("txn_use_float_id_creates_a_distinct_key", "use", 1.0, "non_canonical_magic_id", 400),
)

#: The two steps refused because their OWN recorded counter was above the cap.
ABOVE_CAP_STEPS = (
    ("txn_buy_1_still_climbing", "buy", 63, 113),
    ("txn_use_1_destroys_charges", "use", 113, 50),
)

#: The five ``STATE PARITY`` steps whose derived transition and the oracle's
#: recorded value disagree.  Named so the collision is a fixture this suite
#: carries rather than a fact buried in a counter field.
DERIVED_DISAGREES = (
    "txn_buy_1_unbounded_first",
    "txn_buy_1_unbounded_second",
    "txn_buy_1_unbounded_third",
    "txn_buy_1_crossed_the_cap",
    "txn_use_absent_id_3_creates_zero",
)

#: The four transactions that carry a recorded ``modern_derives_after``, and the
#: eight that do not.  The asymmetry is the point: the flag is a comparison the
#: capture could only make where it had a derived number to compare.
WITH_DERIVED = (
    "txn_use_1_from_two",
    "txn_use_1_at_the_cap_unchanged",
    "txn_use_absent_id_3_creates_zero",
    "txn_use_string_id_resolves_the_same_key",
)

#: The one step whose recorded parity flag is ``True`` while the endpoint
#: refuses.  Named rather than left implicit, because it is the only place the
#: recording's own flag and the measured endpoint disagree.
FLAG_CONTRADICTED_STEP = "txn_use_string_id_resolves_the_same_key"

#: The two steps the endpoint executes whose oracle value EQUALS the derived
#: one.  Both are ``use`` steps with the key already present, which is the
#: measured reason the two arms agree -- see
#: :meth:`ReplayTests.test_the_two_arms_agree_on_use_at_every_counter_the_service_will_run`.
DERIVED_AGREES = ("txn_use_1_from_two", "txn_use_1_at_the_cap_unchanged")

#: The float half of the pair, whose oracle outcome is a SECOND ledger key.
FLOAT_KEY_STEP = "txn_use_float_id_creates_a_distinct_key"

#: The two recorded transactions whose whole-document leaf diff is EMPTY.  Both
#: sat at the cap on the ``use`` arm, which ASSIGNS the capped value, so
#: executing it cannot be told from a no-op assignment -- while the recording
#: could, because it diffed the whole document.  Only ONE of the two is executed
#: successfully by this endpoint; the other is refused for its string identity.
RECORDED_NO_CHANGE = (
    "txn_use_1_at_the_cap_unchanged",
    FLAG_CONTRADICTED_STEP,
)

#: The one of the two the endpoint still executes and still reports as a write.
CHANGED_POINTER_DIVERGES = "txn_use_1_at_the_cap_unchanged"

#: The ladder the oracle produced, step by step: the number of ledger keys each
#: of the twelve steps left behind, read from the recording in the test.
RECORDED_KEY_LADDER = (5, 5, 5, 5, 5, 5, 5, 5, 6, 7, 7, 8)

#: The first five steps of the recorded order -- the prefix the chained replay
#: still follows before the delivered endpoint refuses.
CHAINED_PREFIX = 5

RESOURCE_NAMES = magic_envelope.RESOURCE_NAMES
LEDGER_KEY = magic_envelope.LEDGER_KEY
PRIVATE_STATE_KEY = magic_envelope.PRIVATE_STATE_KEY

#: The nine refusals this route can answer, in the order it lists them.
ROUTE_REFUSALS = (
    magic_envelope.REASON_INVALID_ACTION,
    magic_envelope.REASON_CLIENT_DICTATED_COUNT,
    magic_envelope.REASON_MISSING_MAGIC_ID,
    magic_envelope.REASON_INVALID_MAGIC_ID,
    magic_envelope.REASON_NON_CANONICAL_MAGIC_ID,
    magic_envelope.REASON_UNKNOWN_MAGIC_ID,
    magic_envelope.REASON_INVALID_LEDGER,
    magic_envelope.REASON_INVALID_COUNTER,
    magic_envelope.REASON_COUNTER_ABOVE_CAP,
)

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []
FIXTURE: Dict[str, Any] = {}


# ------------------------------------------------------------------ the fixture --
def load_step(name: str) -> Dict[str, Any]:
    """Load one recorded step.

    ``transaction.json`` exists only for the twelve real transactions: the
    ``login_post`` step is a state-neutral preliminary whose whole purpose is to
    be elided, so it carries no transaction record and the loader does not invent
    one.  Its ``transaction`` key is ``None`` and every assertion that reads it
    iterates :data:`STEP_NAMES`, which never contains it.
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
        fixture[name] = load_step(name)
    return fixture


def transaction_of(name: str) -> Dict[str, Any]:
    record = FIXTURE[name]["transaction"]
    assert record is not None, "%s has no transaction record" % name
    return record


def action_for(name: str) -> str:
    """The request ``action`` a step's own recorded command implies.

    Read through the envelope's own closed mapping rather than a restated table,
    so a command this route no longer accepts cannot be sent under a hand-written
    synonym.
    """
    command = str(transaction_of(name)["command"])
    for action, mapped in magic_envelope.ACTION_COMMAND.items():
        if mapped == command:
            return action
    raise AssertionError(
        "%s recorded the command %r, which this route's closed vocabulary does "
        "not accept" % (name, command)
    )


def recorded_payload(name: str) -> Dict[str, Any]:
    """The legacy JSON batch this step's request carried, parsed back out.

    The recorded request is the legacy **form** encoding -- ``user_key;json`` in a
    single ``data`` field -- so the batch is not a key of ``request.json``.  It is
    recovered by splitting at the recorded ``;`` rather than by a regex, and the
    shape is then asserted rather than assumed: one command, whose arguments are
    the crafted identity and the neutral vector, and whose ``ts`` is the pinned
    constant.  Nothing about the Flash client's own encoding is claimed; this is
    the record of what the capture SENT to the oracle.
    """
    data = str(FIXTURE[name]["request"]["form"]["data"])
    head, separator, tail = data.partition(";")
    if not separator:
        raise AssertionError("%s: the recorded form carries no ';' separator" % name)
    if not head:
        raise AssertionError("%s: the recorded form carries no redacted user key" % name)
    return json.loads(tail)


def moved_resource_slots(before: Dict[str, Any], after: Dict[str, Any]) -> List[str]:
    """The stored-resource slots that differ, over the envelope's own tuple.

    A slot missing from either side is a difference, not a skip: the loop runs
    over :data:`magic_envelope.RESOURCE_NAMES`, so a slot the comparison never
    looked at cannot pass as unchanged.
    """
    return sorted(
        name
        for name in RESOURCE_NAMES
        if name not in before or name not in after or before[name] != after[name]
    )


def sha256_of(path: Path) -> str:
    """SHA-256 over the **LF-normalised** bytes of ``path``.

    Every path this digests is a committed fixture artifact or a file this suite
    wrote itself, and the capture records its digest the same way.  Raw bytes
    would be a line-ending detector rather than a content guard: this repository
    sets ``core.autocrlf=true`` with no ``.gitattributes`` entry for
    ``villages/**`` or ``tests/fixtures/**``, so a checkout may hold CRLF or LF
    for byte-identical committed content.  See PR #280 for the same normalisation
    applied to the unit-xp fixture's byte-count guard.
    """
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


# --------------------------------------------------------------- the corpus --
def save_path(pid: str) -> Path:
    return CORPUS / "saves" / ("%s.save.json" % pid)  # type: ignore[operator]


def write_save(pid: str, document: Dict[str, Any]) -> None:
    """Write a save the way the suite's own seeding does: LF, indent four.

    The newline convention matters and is recorded rather than assumed: the legacy
    ``save_session`` opens the file in TEXT mode with no ``newline`` argument, so
    on Windows it writes CRLF while the suite writes LF.  Comparing raw BYTES
    across that boundary would fail on an identical document, which is why the
    state comparisons parse the document and the byte comparisons are reserved
    for requests that persist nothing at all.
    """
    with open(save_path(pid), "w", encoding="utf-8", newline="\n") as stream:
        json.dump(document, stream, indent=4)
        stream.write("\n")


def committed_village() -> Dict[str, Any]:
    """The recorded seed document, read from the repository.

    This is the order of record and the recorded step-1 snapshot deliberately is
    not: the shared capture writer sorts every fixture document's keys, so
    ``before.json`` carries its ledger in lexicographic order while the oracle
    walked the in-memory save, whose order is this file's.  The two orders differ
    and the suite asserts the difference rather than papering over it.
    """
    return json.loads(
        (harness.REPO_ROOT / str(FIXTURE["manifest"]["seed"]["path"])).read_text(
            encoding="utf-8"
        )
    )


def reset(document: Dict[str, Any]) -> str:
    """Put the corpus save back to ``document``, in memory and on disk.

    Both halves, deliberately: ``sessions.session`` hands out the **cached
    document by reference**, so the in-memory dict is rebuilt in place (which
    keeps that reference valid) and the file is rewritten so a request that
    persists nothing still leaves the file byte-identical to the state the corpus
    started in.
    """
    cached = BOOT.save_document(PID)  # type: ignore[union-attr]
    cached.clear()
    cached.update(json.loads(json.dumps(document)))
    write_save(PID, cached)
    return PID


def persisted() -> Dict[str, Any]:
    return json.loads(save_path(PID).read_text(encoding="utf-8"))


def ledger_of(document: Dict[str, Any]) -> Dict[str, Any]:
    return dict(document["privateState"][LEDGER_KEY])


def magic_now(action: str, magic_id: Any):
    payload: Dict[str, Any] = {"user_id": PID, "action": action, "magic_id": magic_id}
    with harness.offline():
        return CLIENT.post("/v0/magic", json=payload)  # type: ignore[union-attr]


def replay_step(name: str, action: str, magic_id: Any) -> Tuple[Any, Dict[str, Any]]:
    """Reset to **this step's own recorded pre-state** and send only its request."""
    reset(FIXTURE[name]["before"])
    return magic_now(action, magic_id), persisted()


def addressed_pointer(key: str) -> str:
    return "/%s/%s/%s" % (PRIVATE_STATE_KEY, LEDGER_KEY, key)


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, CLIENT, PID, WORKING_TREE_PRE, FIXTURE
    ORIGINAL_CWD = os.getcwd()
    FIXTURE = load_fixture()
    seed_path = harness.REPO_ROOT / str(FIXTURE["manifest"]["seed"]["path"])
    CORPUS = Path(tempfile.mkdtemp(prefix=harness.CORPUS_TEMP_PREFIX))
    # Seeded with the RECORDED village rather than the harness default, so the
    # corpus holds exactly the recorded pid and the ledger the recording used.
    compat_legacy.build_corpus(CORPUS, seed=seed_path)
    BOOT = compat_legacy.initialize(CORPUS)
    PID = str(json.loads(seed_path.read_text(encoding="utf-8"))["playerInfo"]["pid"])
    if PID != str(FIXTURE["manifest"]["seed"]["pid_read_from_document"]):
        raise AssertionError(
            "recorded pid %r does not match the document's %r"
            % (FIXTURE["manifest"]["seed"]["pid_read_from_document"], PID)
        )
    if PID not in BOOT.known_user_ids():  # type: ignore[union-attr]
        raise AssertionError("recorded seed did not load: %r" % PID)
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    CLIENT = app.test_client()
    WORKING_TREE_PRE = harness.working_tree_save_hashes()


def tearDownModule() -> None:
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a magic replay wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


# -------------------------------------------------- non-executing: the fixture --
class FixtureIntegrityTests(unittest.TestCase):
    """The committed recording, checked without executing anything."""

    def test_twelve_transactions_ran_against_one_server_and_one_disposable(
        self,
    ) -> None:
        manifest = FIXTURE["manifest"]
        self.assertEqual(manifest["schema"], "damage-magic-counter-fixture-v1")
        self.assertEqual(
            len(STEP_NAMES),
            12,
            "twelve transaction steps; the thirteenth recorded step is the login, "
            "which carries no transaction record",
        )
        self.assertEqual(len(manifest["transactions"]), 12)
        self.assertEqual(len(manifest["recorded_steps"]), 13)
        self.assertEqual(
            set(manifest["recorded_steps"]),
            set(STEP_NAMES) | {LOGIN_STEP},
            "every recorded step has a directory and no directory is unrecorded",
        )
        self.assertEqual(
            tuple(name for name in manifest["recorded_steps"] if name != LOGIN_STEP),
            STEP_NAMES,
            "the suite's own step order IS the manifest's recorded order, so the "
            "chain is replayed in the order the oracle walked it",
        )
        self.assertEqual(manifest["server"]["starts"], 1)
        self.assertEqual(manifest["cleanup"]["disposables"], 1)
        self.assertTrue(manifest["server"]["one_server_for_the_whole_sequence"])
        self.assertEqual(manifest["exit_code"], 0)

    def test_the_seed_is_the_village_and_no_ledger_entry_was_fabricated(self) -> None:
        seed = FIXTURE["manifest"]["seed"]
        self.assertEqual(seed["path"], "villages/Neutral.json")
        village = committed_village()
        self.assertEqual(
            str(village["playerInfo"]["pid"]),
            seed["pid_read_from_document"],
            "the pid is read from the document, never the filename stem",
        )
        self.assertEqual(
            sha256_of(harness.REPO_ROOT / str(seed["path"])),
            str(seed["sha256"]),
            "the recorded seed digest is the committed document's own, measured "
            "over LF-normalised bytes",
        )
        census = seed["census"]
        self.assertEqual(census["placed_rows"], len(village["maps"][0]["items"]))
        self.assertEqual(census["ledger_keys"], len(ledger_of(village)))
        self.assertEqual(census["ledger"], ledger_of(village))
        self.assertEqual(census["resource_slot_count"], len(RESOURCE_NAMES))
        self.assertEqual(sorted(census["resource_slots"]), sorted(RESOURCE_NAMES))
        self.assertEqual(census["mana"], village["privateState"]["mana"])
        self.assertEqual(census["energy"], village["privateState"]["energy"])
        # The no-fabrication claim, held up by measurement rather than prose: the
        # FIRST step's pre-state ledger is the committed village's ledger, so no
        # capture-side entry could have seeded the ladder.
        first = transaction_of("txn_use_1_from_two")
        self.assertEqual(first["ledger_before"], ledger_of(village))
        self.assertEqual(
            first["ledger_recomputed"],
            first["ledger_after"],
            "and the capture's own recomputation of the branch -- its re-execution "
            "of the recorded operator on the recorded PRE-state -- reproduces the "
            "ledger it recorded AFTER",
        )
        self.assertNotEqual(
            first["ledger_before"]["1"],
            first["ledger_after"]["1"],
            "so the recomputation really did move the addressed counter",
        )
        self.assertEqual(
            {key: value for key, value in first["ledger_after"].items() if key != "1"},
            {key: value for key, value in first["ledger_before"].items() if key != "1"},
            "and moved nothing else",
        )
        self.assertEqual(
            sorted(first["ledger_after"]),
            sorted(ledger_of(village)),
            "and the first transaction did not invent a sixth key either",
        )
        self.assertEqual(
            ledger_of(village),
            {"10": 0, "9": 1, "1": 2, "2": 0, "4": 2},
            "the committed village's own ledger, key for key",
        )
        self.assertIn(
            "No entry is written into the seed",
            seed["no_ledger_entry_fabricated"],
        )

    def test_the_twelve_chain_links_hold_on_the_whole_recorded_ledger(self) -> None:
        """The recording really is ONE interleaved sequence, and it is checkable.

        Settled two ways: every link is asserted, and the ladder itself is
        asserted.  A capture that had chained nothing would carry the same key
        count in every ``before`` and the ladder would be flat.
        """
        ladder: List[int] = []
        previous_after: Optional[Dict[str, Any]] = None
        for name in STEP_NAMES:
            transaction = transaction_of(name)
            with self.subTest(step=name):
                if previous_after is not None:
                    self.assertEqual(
                        FIXTURE[name]["before"],
                        previous_after,
                        "%s begins exactly where its predecessor left off" % name,
                    )
                self.assertEqual(
                    len(transaction["ledger_after"]),
                    transaction["ledger_keys_after"],
                    "%s: the recorded key count is the recorded ledger's own" % name,
                )
                self.assertEqual(
                    len(transaction["ledger_before"]),
                    transaction["ledger_keys_before"],
                    "%s: and so is the pre-state's" % name,
                )
                self.assertTrue(transaction["only_the_addressed_key_moved"])
                ladder.append(int(transaction["ledger_keys_after"]))
            previous_after = FIXTURE[name]["after"]
        self.assertEqual(tuple(ladder), RECORDED_KEY_LADDER)
        # The independent discriminator the manifest records: step 11's recorded
        # no-change is only reachable if step 8's 50 is still there.  On a fresh
        # seed that key holds 2 and the same request would make it 3.
        self.assertEqual(transaction_of(CHANGED_POINTER_DIVERGES)["ledger_value_after"], 50)
        self.assertEqual(transaction_of(FLAG_CONTRADICTED_STEP)["ledger_value_after"], 50)
        self.assertEqual(transaction_of(FLAG_CONTRADICTED_STEP)["ledger_value_before"], 50)

    def test_the_login_step_is_state_neutral_and_the_sequence_starts_from_it(
        self,
    ) -> None:
        login = FIXTURE[LOGIN_STEP]
        village = committed_village()
        self.assertIsNone(login["transaction"], "the login carries no transaction")
        self.assertEqual(
            login["before"],
            village,
            "the login began on the committed village, whole and leaf for leaf",
        )
        self.assertEqual(
            login["after"],
            village,
            "and left it byte-identical, which is what makes it elidable",
        )
        self.assertEqual(FIXTURE[STEP_NAMES[0]]["before"], login["after"])
        # Measured, not assumed: the legacy login answers 302, not 200.  It is a
        # state-neutral preliminary whose only purpose is to make the corpus
        # session live, so the suite pins the real code rather than the one a
        # successful transaction returns.
        self.assertEqual(
            login["meta"]["status"],
            302,
            "measured: the legacy login REDIRECTS to /play.html, so this step's "
            "recorded status is not the 200 a successful transaction returns",
        )
        self.assertEqual(login["meta"].get("reason"), "FOUND")
        self.assertIn("must be byte-identical", FIXTURE["manifest"]["login_step"])

    def test_every_recorded_request_is_one_crafted_command_under_a_neutral_vector(
        self,
    ) -> None:
        batch = FIXTURE["manifest"]["batch_shape"]
        self.assertEqual(sorted(batch["commands"]), ["buy_magic", "use_magic"])
        self.assertEqual(batch["arguments_per_command"], 1)
        self.assertEqual(batch["operators"], {"buy_magic": "+=", "use_magic": "="})
        self.assertEqual(
            batch["operator_source_lines"],
            {"buy_magic": [658], "use_magic": [670]},
            "one write site per command, and they are two different lines",
        )
        self.assertEqual(
            sorted(
                line
                for lines in batch["operator_source_lines"].values()
                for line in lines
            ),
            sorted(magic_envelope.CAP_SOURCE_LINES),
            "and the two write sites ARE the two lines the cap literal sits on, "
            "which is why the cap cannot be derived from either of them",
        )
        self.assertEqual(batch["ts"], 1700000000)
        neutral = list(magic_envelope.neutral_vector())
        self.assertEqual(len(neutral), magic_envelope.RESOURCE_VECTOR_SLOTS)
        self.assertEqual(batch["resource_vector"], neutral)
        self.assertEqual(
            neutral, [0] * magic_envelope.RESOURCE_VECTOR_SLOTS
        )
        for name in STEP_NAMES:
            transaction = transaction_of(name)
            with self.subTest(step=name):
                commands = recorded_payload(name)["commands"]
                self.assertEqual(len(commands), 1, "%s: exactly one command" % name)
                self.assertEqual(commands[0][1], transaction["command"])
                self.assertEqual(
                    commands[0][2],
                    [transaction["magic_id_sent"]],
                    "%s: the crafted argument list is the identity alone" % name,
                )
                self.assertEqual(
                    commands[0][3],
                    neutral,
                    "%s: the recorded vector is the neutral one" % name,
                )
                self.assertEqual(
                    commands[0][0],
                    0,
                    "%s: and the first slot is the recorded first_number" % name,
                )
                self.assertEqual(transaction["status"], 200)
                self.assertEqual(
                    transaction["response_payload"], {"result": "success"}
                )
                self.assertTrue(transaction["stdout_evidence_is_this_request_only"])
                self.assertTrue(transaction["printed_branch_lines"])
                self.assertEqual(
                    str(transaction["magic_id_sent"]),
                    transaction["magic_id_string_form"],
                    "%s: the branch keys on str(magic_id), which is the recorded "
                    "string form" % name,
                )
                self.assertEqual(
                    transaction["ledger_key"], transaction["magic_id_string_form"], name
                )

    def test_only_the_addressed_ledger_key_ever_moves(self) -> None:
        """Every recorded step's whole-document leaf diff is at most one path."""
        for name in STEP_NAMES:
            transaction = transaction_of(name)
            leaves = [str(leaf) for leaf in transaction["changed_leaf_paths"]]
            expected = addressed_pointer(str(transaction["ledger_key"]))
            with self.subTest(step=name):
                self.assertIn(
                    leaves,
                    ([expected], []),
                    "%s: the recorded diff is the addressed counter or nothing, "
                    "never another stored object" % name,
                )
                if leaves:
                    self.assertEqual(leaves, [expected])
                self.assertEqual(
                    len(transaction["changed_leaf_paths"]),
                    len(set(leaves)),
                    "%s: no leaf is reported twice" % name,
                )
                self.assertEqual(
                    bool(leaves),
                    name not in RECORDED_NO_CHANGE,
                    "%s: the recorded no-change is one of the recorded no-changes"
                    % name,
                )

    def test_all_eight_resource_slots_are_recorded_unchanged_in_every_step(
        self,
    ) -> None:
        census = FIXTURE["manifest"]["seed"]["census"]
        for name in STEP_NAMES:
            transaction = transaction_of(name)
            before = dict(transaction["resources_before"])
            after = dict(transaction["resources_after"])
            with self.subTest(step=name):
                self.assertEqual(
                    transaction["resource_slot_count"],
                    magic_envelope.RESOURCE_VECTOR_SLOTS,
                    "%s: the recorded comparison covers every slot" % name,
                )
                self.assertEqual(sorted(before), sorted(after))
                self.assertEqual(sorted(before), sorted(RESOURCE_NAMES))
                self.assertEqual(sorted(before), sorted(census["resource_slots"]))
                self.assertEqual(moved_resource_slots(before, after), [])
                self.assertEqual(transaction["resources_moved"], [])
                self.assertEqual(
                    transaction["resources_comparison"],
                    "all %d stored resource slots compared; moved: NONE"
                    % len(RESOURCE_NAMES),
                )
                # mana is the one a spell would cost, so it is pinned by name
                # rather than only as part of the whole-slot equality.
                self.assertEqual(before["mana"], transaction["mana_before"])
                self.assertEqual(after["mana"], transaction["mana_after"])

    def test_the_manifest_records_its_containment_around_the_run(self) -> None:
        containment = FIXTURE["manifest"]["containment"]
        self.assertTrue(containment["identical"])
        self.assertEqual(
            containment["combined_before"], containment["combined_after"]
        )
        self.assertEqual(
            containment["seed_sha256_before"], containment["seed_sha256_after"]
        )
        self.assertTrue(containment["protected_fixtures_unchanged"])
        self.assertTrue(containment["working_tree_saves_absent"])
        self.assertEqual(
            len(containment["protected_fixtures"]),
            19,
            "every committed fixture other than this one, which is staged outside "
            "the working tree",
        )
        self.assertNotIn("godot-damage", containment["protected_fixtures"])

    def test_the_manifest_records_the_five_deliberate_non_reproductions(self) -> None:
        """The five behaviours the recording exists to show this line refuses."""
        purpose = FIXTURE["manifest"]["purpose"]
        for phrase in (
            "unbounded buy growth",
            "charge-destroying use decrease",
            "an out-of-table identity",
            "a float-keyed identity",
            "an absent key written at zero",
        ):
            self.assertIn(phrase, purpose)
        divergences = FIXTURE["manifest"]["divergences"]
        self.assertEqual(divergences["count"], len(divergences["transactions"]))
        self.assertEqual(divergences["count"], 9)
        chain = divergences["asymmetry_chain"]
        self.assertFalse(chain["parity_claimed"])
        self.assertTrue(divergences["recorded_not_narrowed"])
        self.assertEqual(chain["buy_arm"]["operator"], "+=")
        self.assertEqual(chain["use_arm"]["operator"], "=")
        self.assertEqual(chain["use_arm"]["executed"]["charges_destroyed"], 63)
        self.assertEqual(chain["use_arm"]["executed"]["before"], 113)
        self.assertEqual(chain["use_arm"]["executed"]["after"], 50)
        self.assertEqual(chain["buy_arm"]["executed"]["sequence"], [3, 7, 15, 31, 63, 113])
        self.assertTrue(chain["buy_arm"]["executed"]["crossed_cap"])
        self.assertEqual(
            sorted(divergences["parity_claimed_for"]),
            sorted(
                name[len("txn_") :]
                for name in WITH_DERIVED[:2] + (FLAG_CONTRADICTED_STEP,)
            ),
            "the manifest keys its divergence rows by the BARE step name, and "
            "claims oracle/derived agreement for exactly three of the four steps "
            "that carry a derived number -- the absent-key arm is excluded because "
            "its two numbers differ",
        )
        self.assertEqual(
            len(divergences["transactions"]),
            9,
            "the fourth recorded step with a derived number, and the two steps "
            "the endpoint refuses that carry none, are outside this table",
        )

    def test_the_manifest_records_the_cap_as_a_literal_and_the_rejection_beside_it(
        self,
    ) -> None:
        cap = FIXTURE["manifest"]["cap"]
        self.assertEqual(cap["value"], magic_envelope.COUNTER_CAP)
        self.assertEqual(tuple(cap["source_lines"]), magic_envelope.CAP_SOURCE_LINES)
        self.assertIn("literal", cap["status"])
        self.assertEqual(
            cap["rejected_derivation"]["rejected"],
            "derive the cap from committed magics content",
        )
        self.assertEqual(
            magic_envelope.REJECTED_CAP_DERIVATION["rejected"],
            cap["rejected_derivation"]["rejected"],
        )
        # The coincidence the rejection is about, measured rather than asserted:
        # 50 really does occur among the committed magics values.
        self.assertEqual(
            [row["field"] for row in cap["rejected_derivation"]["candidates"]],
            ["cash", "level"],
        )
        self.assertEqual(
            [row["value"] for row in cap["rejected_derivation"]["candidates"]],
            [magic_envelope.COUNTER_CAP, magic_envelope.COUNTER_CAP],
        )
        for name in STEP_NAMES:
            transaction = transaction_of(name)
            with self.subTest(step=name):
                self.assertEqual(
                    transaction["cap_literal"], magic_envelope.COUNTER_CAP
                )
                self.assertEqual(
                    tuple(transaction["cap_source_lines"]),
                    magic_envelope.CAP_SOURCE_LINES,
                )

    def test_the_manifest_records_its_non_claims_and_the_volatile_fields(self) -> None:
        joined = " ".join(FIXTURE["manifest"]["not_claimed"])
        self.assertIn("The client was never executed", joined)
        self.assertIn("every payload here is crafted", joined)
        self.assertIn("deliberately does not", joined)
        self.assertIn("no damage", joined.lower())
        self.assertIn("A per-magic price, mana cost, or effect", joined)
        self.assertIn("no per-magic effect is claimed", joined)
        self.assertEqual(len(FIXTURE["manifest"]["not_claimed"]), 7)
        volatile = FIXTURE["manifest"]["time_dependent_fields"]
        self.assertIn(
            "ONLY fields that change", volatile["request_captured_at_utc"]
        )
        self.assertIn(
            "thirteen response.meta.json", volatile["request_captured_at_utc"]
        )

    def test_the_recorded_parity_flag_is_the_oracle_versus_the_derived_number(
        self,
    ) -> None:
        """What ``parity_with_delivered_endpoint`` actually computes, measured.

        It is the comparison of the oracle's recorded value with the **derived**
        transition, and it is recorded only where a derived number was recorded:
        four of the twelve transactions carry ``modern_derives_after`` and eight
        do not.  So the flag cannot mean "the endpoint reproduced the oracle" --
        on the eight steps with no derived number it is ``False`` by default
        rather than by measurement, and on one step it is ``True`` while the
        endpoint refuses.  The replay measures that second case directly.
        """
        without_derived: List[str] = []
        with_derived: List[str] = []
        for name in STEP_NAMES:
            transaction = transaction_of(name)
            derived = transaction.get("modern_derives_after")
            flag = bool(transaction["parity_with_delivered_endpoint"])
            with self.subTest(step=name):
                if "modern_derives_after" in transaction:
                    with_derived.append(name)
                    oracle = transaction["ledger_value_after"]
                    self.assertEqual(
                        flag,
                        derived == oracle,
                        "%s: the flag is exactly derived-after == oracle" % name,
                    )
                    self.assertEqual(
                        bool(transaction["modern_differs_from_oracle"]),
                        derived != oracle,
                    )
                    self.assertEqual(
                        oracle,
                        transaction["ledger_value_after"],
                        "%s: so the oracle number is the recorded value" % name,
                    )
                else:
                    without_derived.append(name)
                    self.assertFalse(
                        flag,
                        "%s: no derived number was recorded, so the flag is False "
                        "by default rather than by measurement" % name,
                    )
        self.assertEqual(sorted(with_derived), sorted(WITH_DERIVED))
        self.assertEqual(len(with_derived), 4)
        self.assertEqual(len(without_derived), 8)


# ------------------------------------------------------------------ the replay --
class ReplayTests(unittest.TestCase):
    """Each recorded transaction replayed against the delivered endpoint."""

    def test_every_state_parity_step_reproduces_the_recorded_after_state(self) -> None:
        for name, action, magic_id, derived_after, matches in STATE_PARITY:
            with self.subTest(step=name):
                self.assertEqual(action, action_for(name), name)
                response, document = replay_step(name, action, magic_id)
                self.assertEqual(response.status_code, 200, name)
                body = response.get_json()
                self.assertTrue(body["ok"], name)
                self.assertEqual(body["result"], "success", name)
                self.assertEqual(
                    harness.diff_documents(FIXTURE[name]["after"], document),
                    [],
                    "%s: the persisted document differs from the recorded "
                    "after-state" % name,
                )
                transaction = transaction_of(name)
                counter = body["counter"]
                self.assertEqual(counter["ledger_key"], transaction["ledger_key"], name)
                self.assertEqual(
                    counter["recorded_after"],
                    transaction["ledger_value_after"],
                    "%s: the executed value is the oracle's" % name,
                )
                if transaction["ledger_key_present_before"]:
                    self.assertEqual(
                        counter["before"], transaction["ledger_value_before"], name
                    )
                else:
                    self.assertIsNone(
                        transaction["ledger_value_before"],
                        "%s: an absent key records no pre-state value at all"
                        % name,
                    )
                    self.assertEqual(
                        counter["before"],
                        0,
                        "%s: and the route reads it as zero charges" % name,
                    )
                self.assertEqual(counter["derived_after"], derived_after, name)
                self.assertEqual(counter["matches_derived"], matches, name)
                self.assertEqual(
                    counter["legacy_expected_after"],
                    transaction["ledger_value_after"],
                    "%s: and the unchanged legacy arm's own arithmetic is the "
                    "oracle's number, which is what makes the recorded value a "
                    "verification rather than a restatement" % name,
                )
                self.assertFalse(counter["decreased"], name)
                self.assertEqual(counter["cap"], magic_envelope.COUNTER_CAP, name)
                self.assertEqual(
                    list(counter["cap_is_literal"]),
                    list(magic_envelope.CAP_SOURCE_LINES),
                    name,
                )
                self.assertEqual(
                    counter["legacy_absent_arm_writes_zero"],
                    not transaction["ledger_key_present_before"],
                    name,
                )
                self.assertEqual(
                    body["changed"],
                    [addressed_pointer(str(transaction["ledger_key"]))],
                    name,
                )
                self.assertEqual(
                    sorted(body["resources"]),
                    sorted(RESOURCE_NAMES),
                    name,
                )
                self.assertEqual(
                    body["resources"], dict(transaction["resources_after"]), name
                )

    def test_a_recorded_no_change_still_reports_the_addressed_pointer(self) -> None:
        """The one place the endpoint's ``changed`` differs from the recording.

        The unchanged branch ASSIGNS the capped value, so executing it is not
        distinguishable from a no-op assignment, while the capture could tell the
        two apart because it diffed the whole document and recorded an EMPTY leaf
        set.  The endpoint therefore reports one pointer where the oracle reported
        none -- and the state comparison still passes, because the recorded
        after-state really is the recorded before-state.
        """
        name = CHANGED_POINTER_DIVERGES
        transaction = transaction_of(name)
        self.assertEqual(transaction["changed_leaf_paths"], [])
        self.assertEqual(
            harness.diff_documents(FIXTURE[name]["before"], FIXTURE[name]["after"]),
            [],
        )
        response, document = replay_step(name, "use", 1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["counter"]["recorded_after"], 50)
        self.assertEqual(harness.diff_documents(FIXTURE[name]["after"], document), [])
        self.assertEqual(
            response.get_json()["changed"], [addressed_pointer("1")]
        )

    def test_every_refused_step_leaves_the_recorded_document_byte_identical(
        self,
    ) -> None:
        for name, action, magic_id, code, status in REFUSALS:
            with self.subTest(step=name):
                pid = reset(FIXTURE[name]["before"])
                digest_before = sha256_of(save_path(pid))
                response = magic_now(action, magic_id)
                body = response.get_json()
                self.assertEqual(response.status_code, status, name)
                self.assertFalse(body["ok"], name)
                self.assertEqual(body["error"]["code"], code, name)
                self.assertIn(code, body["error"]["message"], name)
                # An empty payload: a refusal reports no transition at all.
                for field in ("counter", "changed", "resources", "result"):
                    self.assertNotIn(field, body, "%s: %s" % (name, field))
                self.assertEqual(
                    harness.diff_documents(FIXTURE[name]["before"], persisted()),
                    [],
                    "%s: the persisted document moved" % name,
                )
                self.assertEqual(
                    sha256_of(save_path(pid)),
                    digest_before,
                    "%s: the refusal persisted nothing at all, so the file the "
                    "suite wrote itself is byte-identical" % name,
                )

    def test_the_two_above_cap_refusals_are_caused_by_the_oracles_own_ladder(
        self,
    ) -> None:
        """Why the endpoint refuses two recorded successes: the ladder above 50.

        Both steps were recorded at a recorded counter of 63 and 113, each
        **above** the recorded literal cap.  A recorded counter above the cap is
        exactly the state prior ``buy_magic`` requests produced, and it is the
        state design D3 refuses, because the only legacy outcomes from there are
        an unbounded add and a charge-destroying clamp.  So the oracle's own
        growth is what closes the modern endpoint -- and the manifest records NO
        refusal for either step, which this test measures against rather than
        repeats.
        """
        recorded_refusals = {
            row["name"]: row["delivered_endpoint_refusal"]
            for row in FIXTURE["manifest"]["divergences"]["transactions"]
        }
        for name, action, before, oracle_after in ABOVE_CAP_STEPS:
            with self.subTest(step=name):
                transaction = transaction_of(name)
                self.assertEqual(transaction["ledger_value_before"], before)
                self.assertEqual(transaction["ledger_value_after"], oracle_after)
                self.assertGreater(before, magic_envelope.COUNTER_CAP)
                self.assertTrue(transaction["ledger_key_present_before"])
                # The delivered derivation refuses to RUN on such a counter rather
                # than clamping it down -- which is why no number is reported.
                with self.assertRaises(magic_envelope.EnvelopeError) as raised:
                    magic_envelope.derive_counter_transition(
                        before, magic_envelope.COUNTER_CAP
                    )
                self.assertEqual(
                    raised.exception.code, magic_envelope.REASON_COUNTER_ABOVE_CAP
                )
                self.assertIn(
                    "refuses it rather than destroying charges",
                    str(raised.exception),
                )
                response, _document = replay_step(name, action, 1)
                self.assertEqual(response.status_code, 409)
                body = response.get_json()
                self.assertEqual(body["error"]["code"], "counter_above_cap")
                self.assertIn("above the recorded cap", body["error"]["message"])
                self.assertEqual(
                    str(before) in body["error"]["message"],
                    True,
                    "%s: the message names the recorded counter it refused" % name,
                )
                self.assertEqual(
                    persisted()["privateState"][LEDGER_KEY]["1"],
                    before,
                    "%s: and the counter does not move" % name,
                )
                bare = name[len("txn_") :]
                self.assertIn(bare, recorded_refusals)
                self.assertIsNone(
                    recorded_refusals[bare],
                    "the manifest records no delivered refusal for this step, so "
                    "the refusal above is a measurement and not a restatement",
                )

    def test_the_endpoint_persists_the_oracle_value_while_reporting_its_own_differs(
        self,
    ) -> None:
        """The D3/D5 collision, measured on the five steps where they disagree.

        Design D5 asks the proof for "the counter changed by exactly the derived
        delta" and D3 requires the modern transition to refuse both legacy
        defects, so on five of the seven successful steps the unchanged dispatcher
        wrote the **oracle's** number and the endpoint reports
        ``matches_derived: false``.  The persisted state therefore matches the
        recording while the endpoint's own contract does not.  Asserting only the
        state would imply an agreement that is not there; asserting only the
        derived number would fail.  Both are pinned.
        """
        disagreeing = tuple(
            name for name, _a, _m, _d, matches in STATE_PARITY if not matches
        )
        self.assertEqual(disagreeing, DERIVED_DISAGREES)
        self.assertEqual(len(disagreeing), 5)
        table = {name: (action, magic) for name, action, magic, _d, _m in STATE_PARITY}
        for name in DERIVED_DISAGREES:
            action, magic_id = table[name]
            with self.subTest(step=name):
                response, document = replay_step(name, action, magic_id)
                self.assertEqual(response.status_code, 200, name)
                counter = response.get_json()["counter"]
                self.assertFalse(counter["matches_derived"], name)
                self.assertNotEqual(
                    counter["recorded_after"], counter["derived_after"], name
                )
                self.assertEqual(
                    harness.diff_documents(FIXTURE[name]["after"], document),
                    [],
                    "%s: yet the persisted value IS the oracle's" % name,
                )
                # The derived number is REPORTED and is written nowhere: the stored
                # value is the recorded one and the derived one is absent from it.
                self.assertTrue(counter["derived"], name)
                stored = document["privateState"][LEDGER_KEY][counter["ledger_key"]]
                self.assertEqual(stored, counter["recorded_after"], name)
                self.assertNotEqual(stored, counter["derived_after"], name)

    def test_the_two_arms_agree_on_use_at_every_counter_the_service_will_run(
        self,
    ) -> None:
        """The CORRECTED claim, and the correction is the finding.

        An earlier draft of this suite asserted that the two arms agree at
        exactly one point -- a recorded counter of zero -- on the reasoning that
        the ``buy`` arm adds ``min(cap, x + 1)`` while the derivation adds one.
        That is **false**, and this test caught it: the legacy ``use`` arm ASSIGNS
        ``min(cap, x + 1)`` and the derivation returns ``min(cap, x + 1)``, so
        they are the same formula and agree at **every** recorded counter at or
        below the cap.  The measured map is therefore:

        * ``use``  -- agrees at every counter the service can legally start from
          (0 through the cap), and above the cap the derivation REFUSES to run
          rather than clamping, so there is nothing to compare;
        * ``buy``  -- agrees only at zero, because it adds the same quantity the
          ``use`` arm assigns;
        * the absent-key arm -- a third, separate disagreement: both actions write
          zero where the derivation gives one.

        So the whole recorded divergence is about ``buy`` and about the absent-key
        arm, which is why ``matches_derived`` is ``True`` on exactly the two
        ``use`` steps that start at or below the cap with the key already present,
        and ``False`` on every ``buy`` step.  The agreement is a property of the
        two formulas, and it is pinned over the WHOLE legal domain rather than at
        one point, because one point would not have caught the false claim.
        """
        cap = magic_envelope.COUNTER_CAP
        self.assertEqual(compat_service._legacy_recorded_after("use", 0, True, cap), 1)
        self.assertEqual(compat_service._legacy_recorded_after("buy", 0, True, cap), 1)
        self.assertEqual(magic_envelope.derive_counter_transition(0, cap)["after"], 1)
        # Measured over the entire legal domain, not a hand-picked sample.
        use_agreements = 0
        buy_disagreements = 0
        for before in range(0, cap + 1):
            derived = magic_envelope.derive_counter_transition(before, cap)["after"]
            with self.subTest(before=before):
                self.assertEqual(
                    compat_service._legacy_recorded_after("use", before, True, cap),
                    derived,
                    "the use arm and the derivation are the same formula",
                )
                use_agreements += 1
            with self.subTest(before=before, action="buy"):
                legacy_buy = compat_service._legacy_recorded_after(
                    "buy", before, True, cap
                )
                if before == 0:
                    self.assertEqual(
                        legacy_buy,
                        derived,
                        "at zero the two agree, and only here",
                    )
                else:
                    self.assertEqual(legacy_buy, before + derived)
                    buy_disagreements += 1
        self.assertEqual(use_agreements, cap + 1)
        self.assertEqual(buy_disagreements, cap)
        # The fixture agrees with the map: the only ``True`` flags are the two
        # ``use`` steps with the key already present, and both start at or below
        # the cap.
        self.assertEqual(
            sorted(name for name, _a, _i, _d, m in STATE_PARITY if m),
            sorted(DERIVED_AGREES),
        )
        # And the absent-key arm is a third, separate disagreement: it writes zero.
        self.assertEqual(compat_service._legacy_recorded_after("buy", 0, False, cap), 0)
        self.assertEqual(compat_service._legacy_recorded_after("use", 0, False, cap), 0)
        self.assertEqual(
            magic_envelope.derive_counter_transition(0, cap)["after"],
            1,
            "so an absent key is derived as 1 and recorded as 0",
        )

    def test_the_recorded_parity_flag_is_not_an_endpoint_response(self) -> None:
        """The measured contradiction, on the one step the recording calls parity.

        The recording flags ``use_string_id_resolves_the_same_key`` as parity
        because the oracle's 50 and the derived 50 are the same number.  The
        delivered endpoint does not reproduce the transaction at all: it refuses
        the string identity as ``non_canonical_magic_id`` and never executes.  The
        STATE matches -- nothing moved either way -- and the RESPONSE does not,
        which is why this suite keeps the two apart instead of inheriting the
        flag's name.
        """
        transaction = transaction_of(FLAG_CONTRADICTED_STEP)
        self.assertTrue(transaction["parity_with_delivered_endpoint"])
        self.assertEqual(transaction["modern_derives_after"], 50)
        self.assertEqual(transaction["magic_id_sent"], "1")
        self.assertEqual(transaction["magic_id_sent_type"], "str")
        self.assertEqual(transaction["ledger_key"], "1")
        self.assertEqual(transaction["changed_leaf_paths"], [])
        response, document = replay_step(FLAG_CONTRADICTED_STEP, "use", "1")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"]["code"], "non_canonical_magic_id"
        )
        self.assertEqual(
            harness.diff_documents(FIXTURE[FLAG_CONTRADICTED_STEP]["before"], document),
            [],
            "so the state is exactly the recorded no-change, which is what makes "
            "this recorded state parity THROUGH A REFUSAL",
        )
        # And the float half of the pair: the oracle created a SECOND key, which
        # is the hazard the string form was recorded to discriminate.
        float_transaction = transaction_of(FLOAT_KEY_STEP)
        self.assertEqual(float_transaction["ledger_key"], "1.0")
        self.assertEqual(float_transaction["magic_id_sent_type"], "float")
        self.assertIn("1.0", ledger_of(FIXTURE[FLOAT_KEY_STEP]["after"]))
        self.assertNotIn("1.0", ledger_of(FIXTURE[FLOAT_KEY_STEP]["before"]))
        response, _document = replay_step(FLOAT_KEY_STEP, "use", 1.0)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error"]["code"], "non_canonical_magic_id"
        )
        self.assertNotIn("1.0", ledger_of(persisted()))

    def test_the_absent_key_is_the_clearest_three_way_answer(self) -> None:
        """oracle 0, derived 1, persisted 0 -- three numbers, one step."""
        name = "txn_use_absent_id_3_creates_zero"
        transaction = transaction_of(name)
        self.assertFalse(transaction["ledger_key_present_before"])
        self.assertIsNone(transaction["ledger_value_before"])
        self.assertEqual(transaction["ledger_value_after"], 0)
        self.assertEqual(transaction["modern_derives_after"], 1)
        self.assertTrue(transaction["modern_differs_from_oracle"])
        self.assertTrue(transaction["ledger_key_created"])
        self.assertEqual(ledger_of(FIXTURE[name]["before"]).get("3"), None)
        self.assertEqual(ledger_of(FIXTURE[name]["after"])["3"], 0)
        response, document = replay_step(name, "use", 3)
        self.assertEqual(response.status_code, 200)
        counter = response.get_json()["counter"]
        self.assertEqual(
            counter["before"], 0, "an absent entry reads as zero charges"
        )
        self.assertFalse(counter["present_before"])
        self.assertTrue(counter["legacy_absent_arm_writes_zero"])
        self.assertEqual(counter["derived_after"], 1)
        self.assertEqual(counter["recorded_after"], 0)
        self.assertFalse(counter["matches_derived"])
        self.assertEqual(
            ledger_of(document)["3"],
            0,
            "the oracle's zero is what the unchanged branch wrote, so the state is "
            "the recorded state and the contract is still refused",
        )
        self.assertEqual(harness.diff_documents(FIXTURE[name]["after"], document), [])
        # The key ORDER is the other half of the else arm: it APPENDS, so "3" is
        # last in the ledger's own recorded order and the route reports that order.
        self.assertEqual(list(ledger_of(document))[-1], "3")
        self.assertEqual(
            response.get_json()["counter"]["ledger_after"],
            [str(key) for key in ledger_of(document)],
            "the route reports the ledger's own recorded order, not a sort",
        )
        self.assertTrue(response.get_json()["counter"]["ledger_after_keys_are_strings"])

    def test_the_chained_replay_follows_the_recording_then_the_endpoint_refuses(
        self,
    ) -> None:
        """The chain replay, in the recorded order, from the committed village.

        This is the shape the capture used -- one server, one disposable -- so it
        is the only replay that reproduces the ladder the oracle walked.  Steps 1
        to 5 are leaf-for-leaf the recorded states.  Step 6 is where the delivered
        endpoint stops following the oracle: the ladder's own growth took key "1"
        to 63, which is above the recorded cap, and the endpoint refuses
        ``counter_above_cap``.  Step 7 then refuses for the same reason at 63
        rather than at the recorded 113, because the recorded 113 was never
        written -- the state the recording recorded for step 7 is unreachable in
        this service by construction, and that is the finding.
        """
        reset(committed_village())
        for name in STEP_NAMES[:CHAINED_PREFIX]:
            with self.subTest(step=name):
                response = magic_now(action_for(name), 1)
                self.assertEqual(response.status_code, 200, name)
                self.assertEqual(
                    harness.diff_documents(FIXTURE[name]["after"], persisted()),
                    [],
                    "%s: the chained replay matches the recording leaf for leaf"
                    % name,
                )
        self.assertEqual(
            ledger_of(persisted())["1"],
            63,
            "the chained ladder ends at 63, which is what five requests produce "
            "from a recorded 2",
        )
        for index, name in enumerate(
            STEP_NAMES[CHAINED_PREFIX:CHAINED_PREFIX + 2]
        ):
            with self.subTest(step=name):
                recorded_before = transaction_of(name)["ledger_value_before"]
                response = magic_now(action_for(name), 1)
                body = response.get_json()
                self.assertEqual(response.status_code, 409, name)
                self.assertEqual(body["error"]["code"], "counter_above_cap", name)
                self.assertIn("the recorded counter 63", body["error"]["message"])
                # Measured: the chained ladder ends at exactly 63, and the FIRST
                # of these two recorded steps ALSO began at 63 -- so there the
                # refusal lands on the recorded value by coincidence, which is why
                # the coincidence is pinned rather than used as the claim.  It is
                # the SECOND step whose recorded 113 was never written, and that
                # state is therefore unreachable in this service.
                self.assertEqual(
                    str(recorded_before),
                    "63" if index == 0 else "113",
                    "%s: the recorded pre-state is %r, while the chain stands at 63"
                    % (name, recorded_before),
                )
                self.assertEqual(
                    ledger_of(persisted())["1"], 63, "%s: counter unmoved" % name
                )
        # The recorded 113 and the recorded 50 are therefore UNREACHABLE here.
        self.assertEqual(transaction_of(ABOVE_CAP_STEPS[0][0])["ledger_value_after"], 113)
        self.assertEqual(transaction_of(ABOVE_CAP_STEPS[1][0])["ledger_value_after"], 50)
        self.assertNotEqual(ledger_of(persisted())["1"], 113)
        self.assertNotEqual(ledger_of(persisted())["1"], 50)
        # And the chain is reproducible from scratch, so the refusals above are a
        # property of the ladder and not of a corpus left dirty by the suite.
        reset(committed_village())
        response = magic_now("use", 1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            ledger_of(persisted())["1"], 3, "a fresh seed starts the ladder again"
        )

    def test_the_comparison_fails_on_an_altered_ledger_transition_or_an_altered_resource_comparison(
        self,
    ) -> None:
        """Task 1.3: the comparator must be able to fail, proven here every run."""
        name = "txn_use_1_from_two"
        response, document = replay_step(name, "use", 1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            harness.diff_documents(FIXTURE[name]["after"], document),
            [],
            "the honest comparison passes first",
        )
        recorded = FIXTURE[name]["after"]
        counter = response.get_json()["counter"]
        self.assertEqual(counter["ledger_key"], "1")
        self.assertEqual(
            counter["recorded_after"],
            transaction_of(name)["ledger_value_after"],
            "the derived key is the ledger entry the replay really moved",
        )

        # (a) An altered ledger VALUE: the count the assignment moved.
        wrong_value = json.loads(json.dumps(document))
        wrong_value["privateState"][LEDGER_KEY]["1"] = 99
        altered_value = harness.diff_documents(recorded, wrong_value)
        self.assertTrue(altered_value, "a ledger-value change must be reported")
        self.assertTrue(any("magics/1" in entry for entry in altered_value), altered_value)

        # (b) An altered ledger KEY SET: the addressed key removed entirely, which
        # is what a caller-count check would never notice.
        dropped_key = json.loads(json.dumps(document))
        del dropped_key["privateState"][LEDGER_KEY]["1"]
        altered_keys = harness.diff_documents(recorded, dropped_key)
        self.assertTrue(altered_keys, "a missing ledger key must be reported")
        self.assertTrue(any("magics/1" in entry for entry in altered_keys), altered_keys)

        # (c) An altered key COUNT, which is the single ledger figure the recording
        # carries and the route does NOT report.
        extra_key = json.loads(json.dumps(document))
        extra_key["privateState"][LEDGER_KEY]["7"] = 0
        altered_count = harness.diff_documents(recorded, extra_key)
        self.assertTrue(altered_count, "a ledger key-count change must be reported")
        self.assertTrue(any("magics/7" in entry for entry in altered_count), altered_count)

        # (d) An altered RESOURCE-COMPARISON result: one of the eight slots moved.
        honest = moved_resource_slots(
            dict(transaction_of(name)["resources_before"]),
            dict(transaction_of(name)["resources_after"]),
        )
        self.assertEqual(honest, [], "the honest resource comparison finds nothing")
        altered_slots = dict(transaction_of(name)["resources_after"])
        altered_slots["mana"] = altered_slots["mana"] + 1
        self.assertEqual(
            moved_resource_slots(
                dict(transaction_of(name)["resources_before"]), altered_slots
            ),
            ["mana"],
            "a single moved slot must be reported, by name, out of all eight",
        )
        self.assertEqual(len(RESOURCE_NAMES), magic_envelope.PROOF_RESOURCE_COUNT)

        # (e) And the same two alterations against the LIVE document, so the
        # demonstration is not confined to a hand-edited copy.
        live_value = json.loads(json.dumps(document))
        live_value["privateState"][LEDGER_KEY]["1"] = 2
        self.assertTrue(
            harness.diff_documents(document, live_value),
            "a reverted ledger value is reported against the live document too",
        )
        live_resource = json.loads(json.dumps(document))
        live_resource["privateState"]["energy"] = live_resource["privateState"]["energy"] + 1
        self.assertTrue(
            harness.diff_documents(document, live_resource),
            "and so is a moved eighth resource slot nobody priced",
        )

    def test_every_replayed_step_proves_all_eight_resource_slots_unchanged(
        self,
    ) -> None:
        for name, action, magic_id, _derived, _matches in STATE_PARITY:
            with self.subTest(step=name):
                response, document = replay_step(name, action, magic_id)
                self.assertEqual(response.status_code, 200, name)
                body = response.get_json()
                transaction = transaction_of(name)
                self.assertEqual(sorted(body["resources"]), sorted(RESOURCE_NAMES), name)
                self.assertEqual(body["resource_count"], len(RESOURCE_NAMES), name)
                self.assertEqual(
                    moved_resource_slots(
                        dict(transaction["resources_before"]), dict(body["resources"])
                    ),
                    [],
                    "%s: every one of the eight slots is the recorded value" % name,
                )
                self.assertEqual(
                    moved_resource_slots(
                        dict(transaction["resources_before"]),
                        dict(transaction["resources_after"]),
                    ),
                    [],
                    "%s: and the recording's own comparison agrees" % name,
                )
                self.assertEqual(
                    body["resources"],
                    dict(transaction["resources_after"]),
                    name,
                )
                self.assertEqual(
                    moved_resource_slots(
                        dict(transaction["resources_after"]), dict(transaction["resources_after"])
                    ),
                    [],
                )
                # The eighth slot is read off the document, so it is asserted
                # present on both sides rather than defaulted to zero.
                self.assertIn("energy", body["resources"], name)
                self.assertEqual(
                    body["resources"]["energy"],
                    document["privateState"]["energy"],
                    name,
                )
                self.assertEqual(
                    document["privateState"]["energy"],
                    transaction["resources_before"]["energy"],
                    "%s: and the document agrees with the recorded snapshot, for "
                    "the one slot the boot accessor does not expose" % name,
                )
                self.assertEqual(
                    document["privateState"]["energy"],
                    transaction["resources_after"]["energy"],
                    name,
                )

    def test_the_response_carries_no_session_list_field(self) -> None:
        response, _document = replay_step("txn_use_1_from_two", "use", 1)
        body = response.get_json()
        for field in ("saves", "neighbors", "neighbours", "sessions", "users"):
            self.assertNotIn(field, body)
        self.assertGreater(
            body["server_time"], 0, "the one volatile field is a positive instant"
        )
        self.assertEqual(body["resource_count"], len(RESOURCE_NAMES))
        self.assertEqual(tuple(body["refusals"]), ROUTE_REFUSALS)
        self.assertEqual(len(ROUTE_REFUSALS), len(magic_envelope.VALIDATION_ORDER) + 1)
        self.assertEqual(
            magic_envelope.WRITE_STEP, len(magic_envelope.VALIDATION_ORDER) + 1
        )

    def test_the_working_tree_save_did_not_move(self) -> None:
        self.assertEqual(harness.working_tree_save_hashes(), WORKING_TREE_PRE)

    def test_no_server_is_running(self) -> None:
        for port in (5055, 5056):
            self.assertTrue(harness.port_is_free("127.0.0.1", port), port)


if __name__ == "__main__":
    unittest.main()
