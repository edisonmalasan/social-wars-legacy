#!/usr/bin/env python3
"""Compatibility API v0 ``/v0/collection`` behavior tests (OpenSpec task 3.3).

No server and no socket: every request goes through Flask's in-process test
client under the ``offline`` guard, so the suite binds no port and opens no
connection.  The corpus is disposable and lives in the system temp root; every
test also proves the *working-tree* save directories (``saves/`` and
``tests/saves/``) stay byte-identical across collection execution.

Every test resets the storage and the collection ledger to the committed corpus
state first and asserts its post-condition against that snapshot, so the suite is
order-independent and no test can pass on a neighbour's mutation.

The committed corpus is the corpus's **own empty storage and empty collection
ledger**: ``maps[0]["store"] == {}`` and ``privateState["collections"] == []``,
so a completion writes the **committed** prize into the storage and appends one
id — a real, observable, content-derived mutation with **no fabricated player
state**.  That is what makes this the project's first content-derived,
server-authoritative unit acquisition.

Covered:

* **a successful completion** - the granted id and quantity equal the
  **committed** prize bag exactly, no other stored key moved, the ledger grew by
  exactly one appended id, every one of the seven stored resources is
  unchanged, and the response carries the legacy ``result``, the resolved
  ``collection_id``, the derived ``grant``, the projected ``prize``, the
  ``index`` resolution with its alias, the ``eligibility`` gap statement, both
  ledgers, the ``refusals``, and the current ``resources``.
* **the content-derived, not client-supplied, grant** - a request carrying
  ``prize``, ``item_id``, ``quantity``, ``item``, ``cost``, ``price``,
  ``resources_changed``, ``vector``, and ``grant`` changes nothing.
* **the one-based index and its alias** - id 1 resolves, id 0 and a negative id
  resolve to the **same** prize with ``aliased: true`` and ``alias_of: 1``, and
  an out-of-table id is refused.
* **the two-part post-execution proof** - a grant that does not match the
  committed bag, a ledger that grew by the wrong amount, and **any** stored
  resource that moved, each fail closed with ``internal_error`` rather than
  reporting legacy's success.  Each is exercised by a stub that lets the real
  dispatcher run and only rewrites the **post** read.
* **the append-if-absent ledger** - completing an already-completed collection
  grants the prize **again** while the ledger does **not** grow, which is the
  executed legacy behaviour and the case a naive "grew by exactly one" proof
  would reject.
* **fail-closed paths** - every structurally unresolvable input returns its
  documented structured error with the corpus byte-unchanged.
* **the recorded absences** - the route contains no eligibility check, no income,
  no cap, and no experience award.
* **session/bootstrap byte-identity** is retained after completions, and the
  legacy accessors agree with the persisted save.
"""

from __future__ import annotations

import copy
import json
import os
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

import compat_test_harness as harness

import collection_envelope
import compat_legacy
import compat_service

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
WORKING_TREE_PRE: List[Dict[str, str]] = []

# The committed corpus's own collection target and resources.
UNIT_COLLECTION_ID = 1
UNIT_PRIZE_ID = "1085"
UNIT_PRIZE_QUANTITY = 1
UNIT_COLLECTION_NAME = "Draggy Collection"
BUILDING_COLLECTION_ID = 4
BUILDING_PRIZE_ID = "164"
LAST_COLLECTION_ID = 10
LAST_PRIZE_ID = "1056"
OUT_OF_TABLE_ID = 11
RESOURCE_NAMES = ("xp", "gold", "wood", "oil", "steel", "cash", "mana")
COMMITTED_RESOURCES = {
    "xp": 4,
    "gold": 2000,
    "wood": 2000,
    "oil": 2000,
    "steel": 2000,
    "cash": 5,
    "mana": 0,
}


def reset_state(store: Optional[Dict[str, Any]] = None,
                ledger: Optional[List[Any]] = None) -> None:
    """Reset the storage and the collection ledger, in memory **and** on disk.

    ``engine.add_store_item`` mutates ``map["store"]`` in place and
    ``complete_collection`` appends to ``privateState["collections"]`` in place,
    so both live in the in-memory save the endpoint reads *and* in the persisted
    corpus file.  Both representations are updated here, which is exactly the
    mechanism the legacy dispatcher itself uses to keep them in step.  It is a
    test-only, contained reset - never a claim about legacy behaviour and never a
    working-tree write.
    """
    save = BOOT.save_document(PID)  # type: ignore[union-attr]
    save["maps"][0]["store"] = copy.deepcopy({} if store is None else store)
    save["privateState"]["collections"] = copy.deepcopy([] if ledger is None else ledger)
    save_path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
    with open(save_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, CLIENT, PID, WORKING_TREE_PRE
    ORIGINAL_CWD = os.getcwd()
    CORPUS = harness.build_test_corpus()
    BOOT = compat_legacy.initialize(CORPUS)
    PID = str(harness.load_seed()["playerInfo"]["pid"])  # type: ignore[index]
    APP = compat_service.create_app(BOOT)
    APP.config["TESTING"] = True
    CLIENT = APP.test_client()
    WORKING_TREE_PRE = harness.working_tree_save_hashes()


def tearDownModule() -> None:
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a collection completion wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


def complete_now(payload: Dict[str, Any]):
    """POST one intent through the in-process client under the socket guard."""
    with harness.offline():
        return CLIENT.post("/v0/collection", json=payload)  # type: ignore[union-attr]


def store_now() -> Dict[str, Any]:
    return dict(BOOT.map_store(PID))  # type: ignore[union-attr]


def ledger_now() -> List[Any]:
    return BOOT.private_collections(PID)  # type: ignore[union-attr]


def resources_now() -> Dict[str, int]:
    return BOOT.resources(PID)  # type: ignore[union-attr]


def intent(collection_id: Any = UNIT_COLLECTION_ID) -> Dict[str, Any]:
    """The whole contract: a save id and a collection id."""
    return {"user_id": PID, "collection_id": collection_id}


def pristine() -> Dict[str, Any]:
    """Reset to the committed corpus state and snapshot it."""
    reset_state()
    return {
        "store": copy.deepcopy(store_now()),
        "ledger": copy.deepcopy(ledger_now()),
        "resources": copy.deepcopy(resources_now()),
        "items": copy.deepcopy(BOOT.map_items(PID)),  # type: ignore[union-attr]
        "save": copy.deepcopy(BOOT.save_document(PID)),  # type: ignore[union-attr]
    }


class Result:
    """A captured response plus the app that produced it.

    The app must stay referenced while the test reads the response: Flask's test
    client resolves the JSON decoder through a weak reference to the app, so
    returning only the response and letting the app go out of scope turns every
    later ``get_json()`` into a ``ReferenceError``.
    """

    def __init__(self, app: Any, response: Any) -> None:
        self.app = app
        self.response = response

    @property
    def status_code(self) -> int:
        return int(self.response.status_code)

    def get_json(self) -> Any:
        return self.response.get_json()


@contextmanager
def patched_boot(name: str, value: Any) -> Iterator[None]:
    """Install an instance-level stub on ``BOOT`` and restore it EXACTLY.

    A plain ``setattr``/``restore`` pair would leave the *unbound* class function
    behind in the instance dictionary when the attribute was not an instance
    attribute to begin with, and every later call would then miss its ``self``
    argument.  This restores the instance dictionary itself.
    """
    had = name in BOOT.__dict__  # type: ignore[union-attr]
    original = BOOT.__dict__[name] if had else None  # type: ignore[union-attr,index]
    setattr(BOOT, name, value)  # type: ignore[union-attr]
    try:
        yield
    finally:
        if had:
            setattr(BOOT, name, original)  # type: ignore[union-attr]
        else:
            delattr(BOOT, name)  # type: ignore[union-attr]


def _post_read_rewritten(
    name: str,
    transform: Callable[..., Any],
    payload: Dict[str, Any],
) -> Result:
    """Run one intent against a ``BOOT`` whose **post**-execution read is stubbed.

    The endpoint reads every accessor exactly **once** before dispatch (for its
    value-level proof) and exactly **once** afterwards (for the response), so the
    stub rewrites only the second read.  That reproduces a persisted state legacy
    could never report while leaving the pre-execution derivation and the real
    dispatcher's own write untouched.
    """
    app = compat_service.create_app(BOOT)
    app.config["TESTING"] = True
    real = getattr(BOOT, name)
    state = {"seen": 0}

    def stub(*args: Any) -> Any:
        state["seen"] += 1
        values = real(*args)
        if state["seen"] == 1:
            return values
        return transform(values)

    with patched_boot(name, stub):
        with harness.offline():
            return Result(app, app.test_client().post("/v0/collection", json=payload))


class SuccessfulCompletionTests(unittest.TestCase):
    """A completion of a unit-granting collection."""

    def setUp(self) -> None:
        self.before = pristine()

    def test_the_committed_corpus_is_empty_so_the_grant_is_observable(self) -> None:
        self.assertEqual(self.before["store"], {})
        self.assertEqual(self.before["ledger"], [])
        self.assertEqual(self.before["resources"], COMMITTED_RESOURCES)
        self.assertEqual(len(self.before["items"]), 40)

    def test_a_unit_granting_completion_succeeds_with_the_committed_grant(self) -> None:
        response = complete_now(intent(UNIT_COLLECTION_ID))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(
            sorted(body),
            sorted([
                "protocol", "ok", "game_version", "server_time", "result",
                "collection_id", "grant", "prize", "index", "eligibility",
                "store_before", "store_after", "ledger_before", "ledger_after",
                "ledger_appended", "refusals", "resources",
            ]),
        )
        self.assertTrue(body["ok"])
        self.assertEqual(body["protocol"], "compat-v0")
        self.assertEqual(body["result"], "success")
        self.assertEqual(body["collection_id"], UNIT_COLLECTION_ID)
        # The grant: the committed bag, by value, with the committed string key.
        self.assertEqual(body["grant"]["command"], "complete_collection")
        self.assertEqual(body["grant"]["item_id"], UNIT_PRIZE_ID)
        self.assertEqual(body["grant"]["quantity"], UNIT_PRIZE_QUANTITY)
        self.assertEqual(body["grant"]["item_count"], 1)
        self.assertEqual(body["grant"]["quantity_total"], 1)
        self.assertIn("committed collections table", body["grant"]["derived_from"])
        # The projection: the committed name and bag, verbatim.
        self.assertEqual(body["prize"]["name"], UNIT_COLLECTION_NAME)
        self.assertEqual(body["prize"]["id_column"], "1")
        self.assertEqual(body["prize"]["bag"], {UNIT_PRIZE_ID: UNIT_PRIZE_QUANTITY})
        self.assertEqual(
            body["prize"]["entries"],
            [{"item_id": UNIT_PRIZE_ID, "quantity": UNIT_PRIZE_QUANTITY}],
        )
        # The index: one-based, derived-provisional, with the rejected
        # alternative retained.
        self.assertEqual(body["index"]["base"], "one-based")
        self.assertEqual(body["index"]["derivation_status"], "derived-provisional")
        self.assertEqual(body["index"]["rejected_alternative"], "zero-based")
        self.assertEqual(body["index"]["requested"], 0)
        self.assertEqual(body["index"]["resolved"], 0)
        self.assertFalse(body["index"]["clamped"])
        self.assertFalse(body["index"]["aliased"])
        self.assertIsNone(body["index"]["alias_of"])
        self.assertIn("max(0, collection - 1)", body["index"]["rule"])
        self.assertIn("COLLECTION ID 0 AND COLLECTION ID 1", body["index"]["alias_rule"])
        # The recorded gap: no eligibility check, stated rather than implied.
        self.assertFalse(body["eligibility"]["checked"])
        self.assertIn("NO ELIGIBILITY CHECK", body["eligibility"]["rule"])
        # The two ledgers and the append flag.
        self.assertEqual(body["store_before"], {})
        self.assertEqual(body["store_after"], {UNIT_PRIZE_ID: UNIT_PRIZE_QUANTITY})
        self.assertEqual(body["ledger_before"], [])
        self.assertEqual(body["ledger_after"], [UNIT_COLLECTION_ID])
        self.assertTrue(body["ledger_appended"])
        # The three refusals travel with every success.
        self.assertEqual(
            [entry["refusal"] for entry in body["refusals"]],
            ["unit_income", "cap_semantics", "experience_award"],
        )
        for entry in body["refusals"]:
            self.assertFalse(entry["implemented"])
        # The value-level half of the proof: no resource moved.
        self.assertEqual(body["resources"], COMMITTED_RESOURCES)
        # The corpus really holds it.
        self.assertEqual(store_now(), {UNIT_PRIZE_ID: UNIT_PRIZE_QUANTITY})
        self.assertEqual(ledger_now(), [UNIT_COLLECTION_ID])

    def test_the_completion_changes_nothing_but_the_storage_and_the_ledger(self) -> None:
        complete_now(intent(UNIT_COLLECTION_ID))
        after = BOOT.save_document(PID)  # type: ignore[union-attr]
        before = self.before["save"]
        differing = []
        for section in sorted(set(before) | set(after)):
            if before.get(section) != after.get(section):
                differing.append(section)
        self.assertEqual(differing, ["maps", "privateState"],
                         "only the map and the private state changed at all")
        map_before = before["maps"][0]
        map_after = after["maps"][0]
        map_differing = sorted(
            key for key in set(map_before) | set(map_after)
            if map_before.get(key) != map_after.get(key)
        )
        self.assertEqual(map_differing, ["store"])
        private_differing = sorted(
            key for key in set(before["privateState"]) | set(after["privateState"])
            if before["privateState"].get(key) != after["privateState"].get(key)
        )
        self.assertEqual(private_differing, ["collections"])
        self.assertEqual(after["playerInfo"], before["playerInfo"])
        self.assertEqual(map_after["items"], map_before["items"])
        self.assertEqual(len(map_after["items"]), 40)
        self.assertEqual(after["privateState"]["boughtUnits"], [])
        self.assertEqual(map_after["level"], map_before["level"])
        self.assertEqual(map_after["expansions"], map_before["expansions"])

    def test_a_building_granting_completion_grants_the_committed_building(self) -> None:
        response = complete_now(intent(BUILDING_COLLECTION_ID))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["collection_id"], BUILDING_COLLECTION_ID)
        self.assertEqual(body["grant"]["item_id"], BUILDING_PRIZE_ID)
        self.assertEqual(body["grant"]["quantity"], 1)
        self.assertEqual(body["prize"]["name"], "Defense Collection")
        self.assertEqual(body["prize"]["id_column"], "4")
        self.assertEqual(body["store_after"], {BUILDING_PRIZE_ID: 1})
        self.assertEqual(body["ledger_after"], [BUILDING_COLLECTION_ID])
        self.assertEqual(body["index"]["resolved"], 3)

    def test_the_last_committed_collection_resolves_at_index_nine(self) -> None:
        response = complete_now(intent(LAST_COLLECTION_ID))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["index"]["resolved"], 9)
        self.assertEqual(body["prize"]["name"], "Animal Collection")
        self.assertEqual(body["grant"]["item_id"], LAST_PRIZE_ID)
        self.assertEqual(body["ledger_after"], [LAST_COLLECTION_ID])

    def test_a_client_supplied_prize_item_or_quantity_is_ignored(self) -> None:
        smuggled = {
            "prize": {"905": 99},
            "item_id": 905,
            "quantity": 99,
            "item": 905,
            "grant": {"item_id": 905, "quantity": 99},
            "cost": 5000,
            "price": "5000",
            "cashPrice": 5000,
            "resources_changed": [0, -5000, 0, 0, 0, 0, 0, 0],
            "vector": [0, -5000, 0, 0, 0, 0, 0, 0],
            "resources": {"gold": 999999},
        }
        payload = dict(intent(UNIT_COLLECTION_ID))
        payload.update(smuggled)
        response = complete_now(payload)
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        # The grant is exactly the COMMITTED bag: the client's 905 and 99 are
        # nowhere in it.
        self.assertEqual(body["grant"]["item_id"], UNIT_PRIZE_ID)
        self.assertEqual(body["grant"]["quantity"], 1)
        self.assertEqual(body["store_after"], {UNIT_PRIZE_ID: 1})
        self.assertNotIn("905", json.dumps(body["store_after"]))
        # And no client key can mint or burn a balance.
        self.assertEqual(body["resources"], COMMITTED_RESOURCES)
        self.assertEqual(store_now(), {UNIT_PRIZE_ID: 1})

    def test_the_client_cannot_choose_the_collection_by_prize_keys(self) -> None:
        # Naming collection 10 while sending collection 1's prize changes
        # nothing: the id is the only value read.
        payload = intent(LAST_COLLECTION_ID)
        payload["prize"] = {UNIT_PRIZE_ID: 99}
        response = complete_now(payload)
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["collection_id"], LAST_COLLECTION_ID)
        self.assertEqual(body["grant"]["item_id"], LAST_PRIZE_ID)
        self.assertEqual(store_now(), {LAST_PRIZE_ID: 1})


class AliasTests(unittest.TestCase):
    """The one-based clamp and its alias (design D3)."""

    def setUp(self) -> None:
        pristine()

    def test_id_zero_resolves_to_the_same_prize_as_id_one_and_says_so(self) -> None:
        response = complete_now(intent(0))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["collection_id"], 0)
        self.assertEqual(body["grant"]["item_id"], UNIT_PRIZE_ID)
        self.assertEqual(body["prize"]["name"], UNIT_COLLECTION_NAME)
        self.assertEqual(body["index"]["requested"], -1)
        self.assertEqual(body["index"]["resolved"], 0)
        self.assertTrue(body["index"]["clamped"])
        self.assertTrue(body["index"]["aliased"])
        self.assertEqual(body["index"]["alias_of"], 1)
        self.assertEqual(body["ledger_after"], [0])

    def test_a_negative_id_resolves_to_the_same_prize_as_id_one(self) -> None:
        response = complete_now(intent(-7))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["collection_id"], -7)
        self.assertEqual(body["grant"]["item_id"], UNIT_PRIZE_ID)
        self.assertTrue(body["index"]["aliased"])
        self.assertEqual(body["index"]["alias_of"], 1)
        self.assertEqual(body["ledger_after"], [-7])

    def test_id_zero_and_id_one_produce_the_identical_grant(self) -> None:
        zero = complete_now(intent(0)).get_json()
        reset_state()
        one = complete_now(intent(1)).get_json()
        self.assertEqual(zero["grant"], one["grant"])
        self.assertEqual(zero["prize"]["bag"], one["prize"]["bag"])
        self.assertFalse(one["index"]["aliased"])
        self.assertTrue(zero["index"]["aliased"])


class LedgerIdempotenceTests(unittest.TestCase):
    """The append-if-absent rule, which a naive proof would reject."""

    def setUp(self) -> None:
        pristine()

    def test_completing_an_already_completed_collection_grants_again(self) -> None:
        first = complete_now(intent(UNIT_COLLECTION_ID))
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.get_json()["ledger_appended"])
        self.assertEqual(store_now(), {UNIT_PRIZE_ID: 1})
        second = complete_now(intent(UNIT_COLLECTION_ID))
        self.assertEqual(second.status_code, 200, "the second completion succeeds")
        body = second.get_json()
        # The ledger does NOT grow again...
        self.assertFalse(body["ledger_appended"])
        self.assertEqual(body["ledger_before"], [UNIT_COLLECTION_ID])
        self.assertEqual(body["ledger_after"], [UNIT_COLLECTION_ID])
        # ...but the grant is NOT idempotent: the prize is stored again.
        self.assertEqual(body["store_before"], {UNIT_PRIZE_ID: 1})
        self.assertEqual(body["store_after"], {UNIT_PRIZE_ID: 2})
        self.assertEqual(store_now(), {UNIT_PRIZE_ID: 2})

    def test_a_pre_populated_ledger_appends_only_the_missing_id(self) -> None:
        reset_state(store={UNIT_PRIZE_ID: 4, "905": 2}, ledger=[4, 9])
        response = complete_now(intent(UNIT_COLLECTION_ID))
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertTrue(body["ledger_appended"])
        self.assertEqual(body["ledger_before"], [4, 9])
        self.assertEqual(body["ledger_after"], [4, 9, UNIT_COLLECTION_ID])
        # The pre-existing entries are untouched and an unrelated stored item is
        # carried through unchanged: the committed prize increments 1085 only.
        self.assertEqual(body["store_after"], {"1085": 5, "905": 2})
        self.assertEqual(body["ledger_after"], [4, 9, UNIT_COLLECTION_ID])

    def test_the_ledger_stores_the_id_the_client_named_verbatim(self) -> None:
        response = complete_now(intent(0))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ledger_after"], [0],
                         "an aliased id is recorded as the id sent, not its alias")


class FailClosedTests(unittest.TestCase):
    """Every structurally unresolvable input, with the corpus untouched."""

    def setUp(self) -> None:
        self.before = pristine()

    def _assert_untouched(self, label: str) -> None:
        self.assertEqual(store_now(), self.before["store"], label)
        self.assertEqual(ledger_now(), self.before["ledger"], label)
        self.assertEqual(resources_now(), self.before["resources"], label)
        self.assertEqual(BOOT.map_items(PID), self.before["items"], label)  # type: ignore[union-attr]

    def _assert_error(self, payload: Any, status: int, code: str, label: str) -> Any:
        with harness.offline():
            response = CLIENT.post("/v0/collection", json=payload)  # type: ignore[union-attr]
        self.assertEqual(response.status_code, status, label)
        body = response.get_json()
        self.assertFalse(body["ok"], label)
        self.assertEqual(body["error"]["code"], code, label)
        self._assert_untouched(label)
        return body

    def test_a_non_object_body_is_refused(self) -> None:
        self._assert_error(None, 400, "invalid_payload", "a null body")
        self._assert_error([1, 2, 3], 400, "invalid_payload", "an array body")
        self._assert_error("complete", 400, "invalid_payload", "a string body")

    def test_the_save_identity_codes_are_answered_in_order(self) -> None:
        self._assert_error({}, 400, "missing_user_id", "no save id")
        self._assert_error({"user_id": ""}, 400, "missing_user_id", "an empty save id")
        self._assert_error({"user_id": 7}, 400, "invalid_user_id", "a non-string save id")
        self._assert_error(
            {"user_id": "does-not-exist-0000", "collection_id": 1},
            404,
            "unknown_user_id",
            "an unknown save id",
        )

    def test_the_collection_id_codes_are_answered(self) -> None:
        self._assert_error(
            {"user_id": PID}, 400, "missing_collection_id", "no collection id"
        )
        for value in ("1", 1.0, 1.5, True, False, [1], {"id": 1}, None):
            self._assert_error(
                {"user_id": PID, "collection_id": value},
                400,
                "invalid_collection_id",
                "collection_id %r" % (value,),
            )

    def test_an_out_of_table_collection_is_refused(self) -> None:
        for value in (11, 12, 100, 10 ** 9):
            body = self._assert_error(
                {"user_id": PID, "collection_id": value},
                409,
                "unknown_collection_id",
                "collection_id %d" % value,
            )
            self.assertIn("outside", body["error"]["message"])

    def test_an_unreadable_committed_table_fails_closed(self) -> None:
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True
        with patched_boot("collection_table", lambda: None):
            with harness.offline():
                response = app.test_client().post("/v0/collection", json=intent())
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("collections table", body["error"]["message"])
        self._assert_untouched("an unreadable table")

    def test_a_save_without_a_collection_ledger_fails_closed(self) -> None:
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True

        def unreadable(user_id: str) -> List[Any]:
            raise compat_legacy.LegacyBootError(
                "invalid_save_state", "no privateState['collections'] list"
            )

        with patched_boot("private_collections", unreadable):
            with harness.offline():
                response = app.test_client().post("/v0/collection", json=intent())
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()["error"]["code"], "internal_error")
        self._assert_untouched("an unreadable ledger")

    def test_legacy_raising_after_validation_is_reported_not_claimed(self) -> None:
        app = compat_service.create_app(BOOT)
        app.config["TESTING"] = True

        def explode(user_id: str, envelope: Dict[str, Any]) -> None:
            raise RuntimeError("simulated legacy crash")

        with patched_boot("execute_commands", explode):
            with harness.offline():
                response = app.test_client().post("/v0/collection", json=intent())
        self.assertEqual(response.status_code, 500)
        body = response.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("RuntimeError", body["error"]["message"])
        self.assertNotIn("grant", body, "a failed execution carries no grant")


class PostExecutionProofTests(unittest.TestCase):
    """The two proof halves, each failing closed on its own."""

    def setUp(self) -> None:
        pristine()
        # Asserted, not assumed: a leaking reset would make every proof below
        # compare against the wrong pre-execution state.
        self.assertEqual(ledger_now(), [])
        self.assertEqual(store_now(), {})

    def test_a_grant_that_does_not_match_the_committed_bag_fails_closed(self) -> None:
        def wrong(store: Dict[str, Any]) -> Dict[str, Any]:
            return {UNIT_PRIZE_ID: 7}

        result = _post_read_rewritten("map_store", wrong, intent())
        self.assertEqual(result.status_code, 500)
        body = result.get_json()
        self.assertEqual(body["error"]["code"], "internal_error")
        self.assertIn("committed grant", body["error"]["message"])
        self.assertIn("derived", body["error"]["message"])

    def test_a_missing_grant_fails_closed(self) -> None:
        def empty(store: Dict[str, Any]) -> Dict[str, Any]:
            return {}

        result = _post_read_rewritten("map_store", empty, intent())
        self.assertEqual(result.status_code, 500)
        self.assertIn("absent", result.get_json()["error"]["message"])

    def test_an_unmentioned_stored_key_that_moved_fails_closed(self) -> None:
        def extra(store: Dict[str, Any]) -> Dict[str, Any]:
            merged = dict(store)
            merged["905"] = 1
            return merged

        result = _post_read_rewritten("map_store", extra, intent())
        self.assertEqual(result.status_code, 500)
        self.assertIn("never mentions", result.get_json()["error"]["message"])

    def test_a_ledger_that_grew_by_two_fails_closed(self) -> None:
        def grown(ledger: List[Any]) -> List[Any]:
            return list(ledger) + [UNIT_COLLECTION_ID, 4]

        result = _post_read_rewritten("private_collections", grown, intent())
        self.assertEqual(result.status_code, 500)
        self.assertIn("grew by", result.get_json()["error"]["message"])

    def test_a_ledger_that_appends_the_wrong_id_fails_closed(self) -> None:
        # One entry was appended, and it is NOT the id the client named: the
        # pre-execution ledger was empty, so a single [4] is the wrong append.
        def wrong(ledger: List[Any]) -> List[Any]:
            return [4]

        result = _post_read_rewritten("private_collections", wrong, intent())
        self.assertEqual(result.status_code, 500)
        self.assertIn("not the derived", result.get_json()["error"]["message"])

    def test_a_ledger_that_never_grew_fails_closed(self) -> None:
        def empty(ledger: List[Any]) -> List[Any]:
            return []

        result = _post_read_rewritten("private_collections", empty, intent())
        self.assertEqual(result.status_code, 500)
        self.assertIn("not the derived", result.get_json()["error"]["message"])

    def test_a_ledger_entry_rewritten_in_place_fails_closed(self) -> None:
        def rewritten(ledger: List[Any]) -> List[Any]:
            return [9]

        reset_state(ledger=[7])
        result = _post_read_rewritten("private_collections", rewritten, intent())
        self.assertEqual(result.status_code, 500)
        self.assertIn("changed from", result.get_json()["error"]["message"])

    def test_any_stored_resource_that_moved_fails_closed(self) -> None:
        for name in RESOURCE_NAMES:
            def moved(values: Dict[str, int], name: str = name) -> Dict[str, int]:
                changed = dict(values)
                changed[name] = changed[name] + 1
                return changed

            reset_state()
            result = _post_read_rewritten("resources", moved, intent())
            self.assertEqual(result.status_code, 500, "a moved %s is reported" % name)
            message = result.get_json()["error"]["message"]
            self.assertIn(name, message)
            self.assertIn("unchanged", message)

    def test_the_neutral_vector_is_what_forecloses_the_mint(self) -> None:
        # The derived vector cannot express a non-zero slot at all, which is the
        # structural form of the proof above.
        with self.assertRaises(collection_envelope.EnvelopeError):
            collection_envelope.validate_vector([0, 1, 0, 0, 0, 0, 0, 0])


def _route_source() -> str:
    """The ``/v0/collection`` route body, from its definition to the next block.

    The route is the LAST one inside ``create_app``, so it is bounded by the
    closing ``app.config`` assignment rather than by a following decorator.
    """
    source = (Path(compat_service.__file__)).read_text(encoding="utf-8")
    route = source[source.index("def v0_collection()"):]
    for marker in ("\n    @app.", "\n    app.config"):
        if marker in route:
            return route[:route.index(marker)]
    return route


class RecordedAbsenceTests(unittest.TestCase):
    """The route carries no eligibility check, income, cap, or award."""

    def test_the_route_code_mentions_no_eligibility_or_award_identifier(self) -> None:
        import ast
        import textwrap

        tree = ast.parse(textwrap.dedent(_route_source().lstrip("\n")))
        identifiers: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                identifiers.append(node.id)
            elif isinstance(node, ast.Attribute):
                identifiers.append(node.attr)
            elif isinstance(node, ast.keyword) and node.arg:
                identifiers.append(node.arg)
        for forbidden in (
            "item_ids", "eligible", "eligibility_checked", "earned",
            "collect", "collect_xp", "collect_type", "max_collects",
            "max_elem_vol", "harvester", "payout", "income", "award",
            "experience", "threshold", "cap", "limit", "reward",
        ):
            self.assertNotIn(
                forbidden, identifiers,
                "the route's code names no %r: the legacy server has no such "
                "rule and none is invented" % forbidden,
            )
        # The one eligibility identifier the route DOES carry is the recorded
        # ``checked: False`` statement, never a check.
        self.assertIn("eligibility", identifiers)
        self.assertEqual(tree.body[0].name, "v0_collection")

    def test_the_route_computes_no_payout_cap_or_experience(self) -> None:
        before = pristine()
        body = complete_now(intent(UNIT_COLLECTION_ID)).get_json()
        # Every stored resource is the value it started from: no payout, no
        # debit, no experience award is computed anywhere on this route.
        self.assertEqual(body["resources"], before["resources"])
        self.assertEqual(body["resources"]["xp"], before["resources"]["xp"])

    def test_the_response_states_the_recorded_gap_rather_than_a_verdict(self) -> None:
        pristine()
        body = complete_now(intent(UNIT_COLLECTION_ID)).get_json()
        self.assertFalse(body["eligibility"]["checked"])
        self.assertIn("server-authoritative milestone",
                      body["eligibility"]["rule"])
        for entry in body["refusals"]:
            self.assertFalse(entry["implemented"])
            self.assertTrue(entry["rule"].strip())


class ContainmentTests(unittest.TestCase):
    """Session/bootstrap identity and the working-tree save guarantee."""

    def test_session_stays_byte_identical_and_bootstrap_changes_only_its_own_targets(
        self,
    ) -> None:
        # `/v0/session` is byte-identical. `/v0/bootstrap` **legitimately** reports
        # the player's storage and collection ledger, so it is compared with
        # exactly those two fields excluded and every other field asserted
        # byte-identical — which is the honest form of the claim, rather than a
        # byte-identity this route could not possibly hold.
        pristine()
        with harness.offline():
            before_list = CLIENT.get("/v0/session").get_json()  # type: ignore[union-attr]
            before_boot = CLIENT.post(
                "/v0/bootstrap", json={"user_id": PID}  # type: ignore[union-attr]
            ).get_json()
        complete_now(intent(UNIT_COLLECTION_ID))
        complete_now(intent(BUILDING_COLLECTION_ID))
        with harness.offline():
            after_list = CLIENT.get("/v0/session").get_json()  # type: ignore[union-attr]
            after_boot = CLIENT.post(
                "/v0/bootstrap", json={"user_id": PID}  # type: ignore[union-attr]
            ).get_json()
        self.assertEqual(before_list, after_list)
        self.assertEqual(sorted(before_boot), sorted(after_boot))
        differing = [
            key for key in sorted(set(before_boot) | set(after_boot))
            if before_boot.get(key) != after_boot.get(key)
        ]
        self.assertEqual(differing, ["player_info"])
        before_info = dict(before_boot["player_info"])
        after_info = dict(after_boot["player_info"])
        for section in sorted(set(before_info) | set(after_info)):
            if section in ("map", "privateState"):
                continue
            self.assertEqual(
                after_info.get(section), before_info.get(section), section
            )
        map_differing = sorted(
            key for key in set(before_info["map"]) | set(after_info["map"])
            if before_info["map"].get(key) != after_info["map"].get(key)
        )
        self.assertEqual(map_differing, ["store"])
        private_differing = sorted(
            key
            for key in set(before_info["privateState"])
            | set(after_info["privateState"])
            if before_info["privateState"].get(key)
            != after_info["privateState"].get(key)
        )
        self.assertEqual(private_differing, ["collections"])
        self.assertEqual(after_info["map"]["store"],
                         {UNIT_PRIZE_ID: 1, BUILDING_PRIZE_ID: 1})
        self.assertEqual(
            after_info["privateState"]["collections"],
            [UNIT_COLLECTION_ID, BUILDING_COLLECTION_ID],
        )

    def test_completions_never_touch_working_tree_saves(self) -> None:
        pristine()
        pre = harness.working_tree_save_hashes()
        for collection_id in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
            reset_state()
            response = complete_now(intent(collection_id))
            self.assertEqual(response.status_code, 200, "collection %d" % collection_id)
        self.assertEqual(pre, harness.working_tree_save_hashes())

    def test_every_committed_collection_is_exercisable_against_the_corpus(self) -> None:
        pre = harness.working_tree_save_hashes()
        table = BOOT.collection_table()  # type: ignore[union-attr]
        self.assertEqual(collection_envelope.table_length(table), 10)
        granted: List[str] = []
        for collection_id in range(1, 11):
            reset_state()
            body = complete_now(intent(collection_id)).get_json()
            self.assertTrue(body["ok"])
            self.assertEqual(body["collection_id"], collection_id)
            self.assertEqual(body["ledger_after"], [collection_id])
            self.assertEqual(body["index"]["resolved"], collection_id - 1)
            self.assertEqual(body["grant"]["item_count"], 1)
            granted.append(str(body["grant"]["item_id"]))
        self.assertEqual(granted,
                         ["1085", "1062", "1096", "164", "1073", "1010", "45",
                          "136", "106", "1056"])
        self.assertEqual(pre, harness.working_tree_save_hashes())

    def test_the_legacy_accessors_agree_with_the_persisted_save(self) -> None:
        pristine()
        complete_now(intent(UNIT_COLLECTION_ID))
        persisted = harness.read_seeded_save(CORPUS)  # type: ignore[arg-type]
        self.assertEqual(
            persisted["maps"][0]["store"], {UNIT_PRIZE_ID: 1}
        )
        self.assertEqual(persisted["privateState"]["collections"],
                         [UNIT_COLLECTION_ID])
        self.assertEqual(store_now(), persisted["maps"][0]["store"])
        self.assertEqual(ledger_now(), persisted["privateState"]["collections"])


if __name__ == "__main__":
    unittest.main()