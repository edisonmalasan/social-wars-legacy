#!/usr/bin/env python3
"""Offline fixture-replay parity: ``/v0/place_stored`` and ``/v0/sell_stored``
against the executed-legacy stored-placement fixture (OpenSpec task 3.4).

No server and no network: both endpoints run through Flask's in-process test
client under the ``offline`` guard (which fails the run if any socket tries to
connect), and ``test_no_server_is_running`` asserts that neither the legacy port
(5055) nor the Compatibility API port (5056) is listening.

What is replayed
    The committed transaction under
    ``tests/fixtures/godot-stored-item-placement/`` - five real legacy calls
    against the committed fresh-player corpus, whose ``maps[0]["store"]`` is
    ``{}``, whose ``privateState["boughtUnits"]`` is ``[]``, and whose
    ``privateState["collections"]`` is ``[]``:

    1. ``login_post`` (the login form, recorded for session fidelity),
    2. ``complete_collection`` on collection **1** ("Draggy Collection"),
    3. ``place_stored_item`` on the content-derived prize ``1085`` at the
       derived slot ``41`` and cell ``(58, 47)``,
    4. ``complete_collection`` on collection **2** ("Transformer Collection"),
    5. ``sell_stored_item`` on the content-derived prize ``1062``.

    This is the round trip the delivered ``godot-unit-collection`` line recorded
    as a carried follow-up: a unit acquired from **committed content** reaches
    the map, the placement count grows ``40 -> 41``, and the placement count
    stays 41 through the sale. Every seed is content-derived, so no client-sent
    item id list appears in any recorded transaction and **no player state is
    fabricated**.

    The endpoints derive the very same envelopes from the very same modules, so
    the replay compares:

    * the four derived envelopes against the recorded ``form/data`` payloads,
      exactly (each recorded ``ts`` is passed back into the derivation);
    * the response ``result`` against each captured legacy response body;
    * the placement's derived slot, cell, orientation and eight-slot row against
      the recorded row, with **only** the row's clock slot excluded;
    * the storage block, both ledger blocks, and all seven stored resources by
      value against the captured states;
    * the corpus save after **each** of the four mutating calls against that
      call's captured after-state, leaf for leaf.

**One exclusion, and it is asserted to be the only one.**  The recorded state
carries exactly ONE time-dependent value: ``/maps/0/items/41/3``, the server
clock read inside ``engine.map_add_item``.  The capture's manifest names that
leaf and names the five documents carrying it; this suite asserts the exclusion
set is **exactly** that one leaf and that every other leaf of every recorded
document is compared by value.  The seed step is compared with **no** exclusion
at all, because it precedes the placement and contains no placed row.

A second mechanical proof is used in place of trusting that claim: calling
``expected_row`` with two different instants yields two rows differing at
**exactly** index ``ROW_SLOT_TIMESTAMP``, so no other slot can be clock-derived.

**The parity claim covers these recorded transactions against the fresh-player
corpus only** (see the fixture README's claim limits).  The four refusals are
NOT parity claims and are not replayed here: the legacy server answers success
in every one of the four cases, so they are recorded in the manifest as executed
probes with ``parity: false`` and are asserted to say so.
"""

from __future__ import annotations

import copy
import json
import os
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

import compat_test_harness as harness

import collection_envelope
import compat_legacy
import compat_service
import stored_placement_envelope as placement

FIXTURES = harness.REPO_ROOT / "tests" / "fixtures" / "godot-stored-item-placement"
LOGIN_STEP = "login_post"
SEED_STEP = "command_complete_collection"
PLACE_STEP = "command_place_stored_item"
SEED2_STEP = "command_complete_collection_2"
SELL_STEP = "command_sell_stored_item"

# The one volatile state leaf: the row's server-clock instant.
VOLATILE_LEAF = "/maps/0/items/41/3"
VOLATILE_DOCUMENTS = [
    "steps/command_place_stored_item/after.json",
    "steps/command_complete_collection_2/before.json",
    "steps/command_complete_collection_2/after.json",
    "steps/command_sell_stored_item/before.json",
    "steps/command_sell_stored_item/after.json",
]

FIXTURE_PLACE_ITEM = 1085
FIXTURE_SELL_ITEM = 1062
FIXTURE_SEED_COLLECTION = 1
FIXTURE_SEED2_COLLECTION = 2

CORPUS: Optional[Path] = None
ORIGINAL_CWD = ""
BOOT: Optional[compat_legacy.LegacyBoot] = None
CLIENT = None
PID = ""
CORPUS_SAVE: Dict[str, Any] = {}
WORKING_TREE_PRE: List[Dict[str, str]] = []
FIXTURE: Dict[str, Any] = {}


def load_step(name: str) -> Dict[str, Any]:
    base = FIXTURES / "steps" / name
    return {
        "name": name,
        "request": json.loads((base / "request.json").read_text(encoding="utf-8")),
        "before": json.loads((base / "before.json").read_text(encoding="utf-8")),
        "after": json.loads((base / "after.json").read_text(encoding="utf-8")),
        "meta": json.loads(
            (base / "response.meta.json").read_text(encoding="utf-8")
        ),
        "body": (base / "response.body").read_bytes(),
    }


def recorded_envelope(step: Dict[str, Any]) -> Dict[str, Any]:
    return placement.parse_data_field(step["request"]["form"]["data"])


def recorded_command(step: Dict[str, Any]) -> List[Any]:
    commands = recorded_envelope(step)["commands"]
    assert len(commands) == 1, "each recorded step carries exactly one command"
    return commands[0]


def recorded_args(step: Dict[str, Any]) -> List[Any]:
    return recorded_command(step)[2]


def recorded_intent(step: Dict[str, Any]) -> Dict[str, Any]:
    entry = recorded_command(step)
    return {
        "user_id": step["request"]["form"]["USERID"],
        "command": entry[1],
        "map_id": entry[0],
        "args": entry[2],
        "vector": entry[3],
    }


def load_fixture() -> Dict[str, Any]:
    return {
        "login": load_step(LOGIN_STEP),
        "seed": load_step(SEED_STEP),
        "place": load_step(PLACE_STEP),
        "seed2": load_step(SEED2_STEP),
        "sell": load_step(SELL_STEP),
        "manifest": json.loads(
            (FIXTURES / "capture-manifest.json").read_text(encoding="utf-8")
        ),
        "readme": (FIXTURES / "README.md").read_text(encoding="utf-8"),
    }


def setUpModule() -> None:
    global CORPUS, ORIGINAL_CWD, BOOT, CLIENT, PID, CORPUS_SAVE, WORKING_TREE_PRE
    global FIXTURE
    ORIGINAL_CWD = os.getcwd()
    FIXTURE = load_fixture()
    CORPUS = harness.build_test_corpus()
    BOOT = compat_legacy.initialize(CORPUS)
    PID = str(harness.load_seed()["playerInfo"]["pid"])  # type: ignore[index]
    # The pristine post-initialize corpus state, snapshotted ONCE. Resetting to
    # it makes every test independent without re-reading the live corpus.
    CORPUS_SAVE = copy.deepcopy(BOOT.save_document(PID))  # type: ignore[union-attr]
    APP = compat_service.create_app(BOOT)
    APP.config["TESTING"] = True
    CLIENT = APP.test_client()
    WORKING_TREE_PRE = harness.working_tree_save_hashes()


def tearDownModule() -> None:
    if WORKING_TREE_PRE != harness.working_tree_save_hashes():
        raise AssertionError("a stored-placement execution wrote a working-tree save")
    os.chdir(ORIGINAL_CWD)
    harness.remove_corpus(CORPUS)


# ------------------------------------------------------------------ replay --

def reset_state() -> None:
    """Restore the pristine corpus state in the LIVE document, then persist it.

    ``LegacyBoot.save_document`` returns ``sessions.session(user_id)`` - the live
    in-memory document that the legacy dispatcher persists on every command - so
    a reset that only rewrote the corpus FILE would leave the running state
    untouched. That is precisely how an accumulating derived slot (41, then 55,
    then 56, ...) and a doubled ledger would sneak in and make every leaf
    comparison below vacuously unequal.
    """
    save = live_save()
    for field in ("items", "store"):
        save["maps"][0][field] = copy.deepcopy(CORPUS_SAVE["maps"][0][field])
    for field in ("boughtUnits", "collections"):
        save["privateState"][field] = copy.deepcopy(
            CORPUS_SAVE["privateState"][field]
        )
    save_path = CORPUS / "saves" / ("%s.save.json" % PID)  # type: ignore[operator]
    with open(save_path, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(save, stream, indent=4)
        stream.write("\n")


def complete_now(payload: Dict[str, Any]):
    with harness.offline():
        return CLIENT.post("/v0/collection", json=payload)  # type: ignore[union-attr]


def place_now(payload: Dict[str, Any]):
    with harness.offline():
        return CLIENT.post("/v0/place_stored", json=payload)  # type: ignore[union-attr]


def sell_now(payload: Dict[str, Any]):
    with harness.offline():
        return CLIENT.post("/v0/sell_stored", json=payload)  # type: ignore[union-attr]


def seed_first() -> Dict[str, Any]:
    return complete_now(
        {"user_id": PID, "collection_id": FIXTURE_SEED_COLLECTION}
    ).get_json()


def seed_second() -> Dict[str, Any]:
    return complete_now(
        {"user_id": PID, "collection_id": FIXTURE_SEED2_COLLECTION}
    ).get_json()


def place_derived(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    body = place_now(
        {"user_id": PID, "item_id": FIXTURE_PLACE_ITEM, "x": 58, "y": 47}
        if payload is None
        else dict({"user_id": PID}, **payload)
    )
    assert body.status_code == 200, body.get_data(as_text=True)
    return body.get_json()


def sell_derived(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    body = sell_now(
        {"user_id": PID, "item_id": FIXTURE_SELL_ITEM}
        if payload is None
        else dict({"user_id": PID}, **payload)
    )
    assert body.status_code == 200, body.get_data(as_text=True)
    return body.get_json()


def live_save() -> Dict[str, Any]:
    return BOOT.save_document(PID)  # type: ignore[union-attr,return-value]


def resources_of(document: Dict[str, Any]) -> Dict[str, int]:
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


def leaf_differences(left: Any, right: Any) -> List[str]:
    """Every JSON-pointer leaf at which two documents differ."""

    def walk(one: Any, other: Any, path: str, out: List[str]) -> None:
        if isinstance(one, dict) and isinstance(other, dict):
            for key in sorted(set(one) | set(other)):
                child = "%s/%s" % (path, key)
                if key not in one or key not in other:
                    out.append(child)
                    continue
                walk(one[key], other[key], child, out)
        elif isinstance(one, list) and isinstance(other, list):
            if len(one) != len(other):
                out.append(path)
                return
            for index, (a, b) in enumerate(zip(one, other)):
                walk(a, b, "%s/%d" % (path, index), out)
        elif one != other:
            out.append(path or "/")

    paths: List[str] = []
    walk(left, right, "", paths)
    return paths


def differing_from_capture(step: Dict[str, Any], live: Dict[str, Any],
                           exclude: Optional[List[str]] = None) -> List[str]:
    """The leaves at which ``live`` differs from a captured after-state."""
    excluded = set(exclude or [])
    return [
        leaf for leaf in leaf_differences(step["after"], live) if leaf not in excluded
    ]


def replay_all() -> None:
    """The whole recorded transaction, in the recorded order."""
    seed_first()
    place_derived()
    seed_second()
    sell_derived()


# ------------------------------------------------------- non-executing ----

class FixtureIntegrityTests(unittest.TestCase):
    """Non-executing: the committed fixture obeys the shared derivations."""

    def test_the_recorded_place_request_carries_the_derived_intent(self) -> None:
        intent = recorded_intent(FIXTURE["place"])
        self.assertEqual(intent["user_id"], PID)
        self.assertEqual(intent["command"], placement.PLACE_COMMAND)
        self.assertEqual(intent["map_id"], 0)
        args = intent["args"]
        self.assertEqual(len(args), placement.PLACE_ARGUMENT_COUNT)
        self.assertEqual(args[placement.ARG_SLOT], placement.COMMITTED_DERIVED_SLOT)
        self.assertEqual(args[placement.ARG_ITEM_ID], FIXTURE_PLACE_ITEM)
        self.assertEqual(
            [args[placement.ARG_X], args[placement.ARG_Y]],
            list(placement.COMMITTED_CELL),
        )
        self.assertEqual(args[placement.ARG_PLAYER_ID], 1)
        self.assertEqual(
            args[placement.ARG_ORIENTATION], placement.COMMITTED_ORIENTATION
        )
        self.assertEqual(intent["vector"], placement.neutral_vector())
        envelope = recorded_envelope(FIXTURE["place"])
        self.assertEqual(sorted(envelope), sorted(placement.ENVELOPE_KEYS))

    def test_the_recorded_sell_request_carries_one_argument_and_nothing_else(self) -> None:
        intent = recorded_intent(FIXTURE["sell"])
        self.assertEqual(intent["command"], placement.SELL_COMMAND)
        self.assertEqual(intent["args"], [FIXTURE_SELL_ITEM])
        self.assertEqual(len(intent["args"]), placement.SELL_ARGUMENT_COUNT)
        self.assertEqual(placement.SELL_ARG_ITEM_ID, 0)
        self.assertEqual(intent["vector"], placement.neutral_vector())
        envelope = recorded_envelope(FIXTURE["sell"])
        self.assertEqual(sorted(envelope), sorted(placement.ENVELOPE_KEYS))

    def test_the_derivation_reproduces_the_recorded_place_envelope_exactly(self) -> None:
        recorded = recorded_envelope(FIXTURE["place"])
        derived = placement.build_place_envelope(
            item_id=FIXTURE_PLACE_ITEM,
            x=placement.COMMITTED_CELL[0],
            y=placement.COMMITTED_CELL[1],
            items=CORPUS_SAVE["maps"][0]["items"],
            orientation=placement.COMMITTED_ORIENTATION,
            ts=int(recorded["ts"]),
        )
        self.assertEqual(derived, recorded)

    def test_the_derivation_reproduces_the_recorded_sell_envelope_exactly(self) -> None:
        recorded = recorded_envelope(FIXTURE["sell"])
        derived = placement.build_sell_envelope(
            item_id=FIXTURE_SELL_ITEM, ts=int(recorded["ts"])
        )
        self.assertEqual(derived, recorded)

    def test_the_derivation_reproduces_both_recorded_seed_envelopes_exactly(self) -> None:
        for step, collection_id in (
            (FIXTURE["seed"], FIXTURE_SEED_COLLECTION),
            (FIXTURE["seed2"], FIXTURE_SEED2_COLLECTION),
        ):
            recorded = collection_envelope.parse_data_field(
                step["request"]["form"]["data"]
            )
            derived = collection_envelope.build_envelope(
                collection_id=collection_id, ts=int(recorded["ts"])
            )
            self.assertEqual(derived, recorded)

    def test_the_recorded_requests_redact_their_secrets(self) -> None:
        for name in ("seed", "place", "seed2", "sell"):
            form = FIXTURE[name]["request"]["form"]
            self.assertEqual(form["user_key"], "<redacted>", name)
            self.assertEqual(form["USERID"], PID, name)
            self.assertEqual(form["language"], "en", name)
            # The crafted EMPTY accessToken placeholder survives redaction
            # untouched, which is what lets the replay parse the payload back.
            self.assertEqual(
                placement.parse_data_field(form["data"])["accessToken"], "", name
            )

    def test_the_capture_starts_from_the_committed_corpus_state(self) -> None:
        seed_before = FIXTURE["seed"]["before"]
        self.assertEqual(FIXTURE["login"]["before"], seed_before)
        self.assertEqual(FIXTURE["login"]["after"], seed_before)
        self.assertEqual(seed_before["maps"][0]["store"], {})
        self.assertEqual(seed_before["privateState"]["boughtUnits"], [])
        self.assertEqual(seed_before["privateState"]["collections"], [])
        self.assertEqual(resources_of(seed_before), placement.COMMITTED_RESOURCE_BEFORE)
        self.assertEqual(
            len(seed_before["maps"][0]["items"]), placement.COMMITTED_PLACEMENTS
        )
        self.assertEqual(
            sorted(int(key) for key in seed_before["maps"][0]["items"]),
            list(range(1, placement.COMMITTED_PLACEMENTS + 1)),
            "the committed corpus places keys 1..40, so the first derived slot is 41",
        )
        self.assertEqual(seed_before, CORPUS_SAVE)

    def test_the_capture_recorded_the_derived_row_and_the_ledger_append(self) -> None:
        after = FIXTURE["place"]["after"]
        before = FIXTURE["place"]["before"]
        recorded_row = FIXTURE["manifest"]["placement"]["row"]
        row = after["maps"][0]["items"][str(placement.COMMITTED_DERIVED_SLOT)]
        self.assertEqual(len(row), placement.ROW_SLOTS)
        self.assertEqual(row[:3], recorded_row[:3])
        self.assertEqual(row[4:], recorded_row[4:])
        self.assertIsInstance(row[placement.ROW_SLOT_TIMESTAMP], int)
        self.assertGreater(row[placement.ROW_SLOT_TIMESTAMP], 0)
        self.assertEqual(row, after["maps"][0]["items"]["41"])
        self.assertEqual(after["maps"][0]["store"], {})
        self.assertEqual(after["privateState"]["boughtUnits"], [FIXTURE_PLACE_ITEM])
        self.assertEqual(resources_of(after), placement.COMMITTED_RESOURCE_BEFORE)
        self.assertEqual(
            len(after["maps"][0]["items"]), placement.COMMITTED_PLACEMENTS + 1
        )
        self.assertEqual(after["playerInfo"], before["playerInfo"])
        for key, row_before in before["maps"][0]["items"].items():
            self.assertEqual(after["maps"][0]["items"][key], row_before, key)
        self.assertEqual(
            json.loads(FIXTURE["place"]["body"].decode("utf-8")),
            {"result": "success"},
        )

    def test_the_row_is_clock_derived_at_exactly_one_slot(self) -> None:
        # The exclusion claim is proved rather than trusted: two instants produce
        # two rows differing at exactly ROW_SLOT_TIMESTAMP, so no other slot of
        # the eight can carry a clock reading.
        early = placement.expected_row(
            FIXTURE_PLACE_ITEM, 58, 47, 1700000000, placement.COMMITTED_ORIENTATION
        )
        late = placement.expected_row(
            FIXTURE_PLACE_ITEM, 58, 47, 1700009999, placement.COMMITTED_ORIENTATION
        )
        differing = [
            index for index, (a, b) in enumerate(zip(early, late)) if a != b
        ]
        self.assertEqual(differing, [placement.ROW_SLOT_TIMESTAMP])
        self.assertEqual(
            [early[i] for i in differing], [1700000000]
        )
        # And the recorded row agrees with the derivation at every other slot.
        recorded_row = FIXTURE["manifest"]["placement"]["row"]
        for index in range(placement.ROW_SLOTS):
            if index == placement.ROW_SLOT_TIMESTAMP:
                continue
            self.assertEqual(recorded_row[index], late[index], index)

    def test_the_capture_declares_one_time_dependent_state_leaf(self) -> None:
        # This is what licenses the suite's single exclusion, and it is asserted
        # rather than assumed: a re-capture that started stamping a second clock
        # would fail here instead of quietly acquiring an unchecked leaf.
        time_dependent = FIXTURE["manifest"]["time_dependent_fields"]
        self.assertEqual(time_dependent["state_leaf"], VOLATILE_LEAF)
        self.assertEqual(
            sorted(time_dependent["state_leaf_documents"]),
            sorted(VOLATILE_DOCUMENTS),
        )
        self.assertEqual(
            leaf_differences(FIXTURE["place"]["before"], FIXTURE["place"]["after"]),
            FIXTURE["manifest"]["placement"]["changed_leaves"],
        )

    def test_the_sale_changed_exactly_one_leaf_and_credited_nothing(self) -> None:
        before = FIXTURE["sell"]["before"]
        after = FIXTURE["sell"]["after"]
        self.assertEqual(leaf_differences(before, after), ["/maps/0/store/1062"])
        self.assertEqual(
            leaf_differences(before, after),
            FIXTURE["manifest"]["sale"]["changed_leaves"],
        )
        self.assertEqual(before["maps"][0]["store"], {str(FIXTURE_SELL_ITEM): 1})
        self.assertEqual(after["maps"][0]["store"], {})
        self.assertEqual(after["privateState"]["boughtUnits"], before["privateState"]["boughtUnits"])
        self.assertEqual(after["maps"][0]["items"], before["maps"][0]["items"])
        self.assertEqual(resources_of(after), resources_of(before))
        self.assertEqual(resources_of(after), placement.COMMITTED_RESOURCE_BEFORE)
        self.assertFalse(FIXTURE["manifest"]["sale"]["credited"])
        self.assertIsNone(FIXTURE["manifest"]["sale"]["refund"])
        self.assertEqual(
            json.loads(FIXTURE["sell"]["body"].decode("utf-8")),
            {"result": "success"},
        )

    def test_the_manifest_records_the_three_leaf_correction(self) -> None:
        correction = FIXTURE["manifest"]["changed_leaf_correction"]
        recorded = FIXTURE["manifest"]["placement"]
        self.assertEqual(correction["measured"], recorded["changed_leaves"])
        self.assertEqual(correction["measured_map_scoped"], recorded["changed_map_leaves"])
        self.assertEqual(len(correction["measured"]), 3)
        self.assertEqual(len(correction["measured_map_scoped"]), 2)
        self.assertIn("exactly two leaves", correction["task_text_predicted"])
        self.assertIn("THREE for the whole document", correction["cause"])
        # The two-at-map-scope reading is mechanically true of the capture.
        map_scoped = [
            leaf for leaf in correction["measured"] if leaf.startswith("/maps/0/")
        ]
        self.assertEqual(map_scoped, correction["measured_map_scoped"])

    def test_the_manifest_records_four_refusals_that_are_not_parity(self) -> None:
        refusals = FIXTURE["manifest"]["refusals"]
        self.assertEqual(len(refusals), placement.REFUSAL_COUNT)
        self.assertEqual(
            [entry["refusal"] for entry in refusals],
            [
                placement.REASON_NOT_IN_STORAGE,
                placement.REASON_SLOT_OCCUPIED,
                placement.REASON_UNKNOWN_ITEM_ID,
                placement.REASON_ITEM_NOT_PLACEABLE,
            ],
        )
        for entry, module in zip(refusals, placement.REFUSALS):
            self.assertTrue(entry["implemented"])
            self.assertTrue(entry["divergence"])
            self.assertEqual(entry["status"], 409)
            self.assertEqual(entry["why"], module["why"])
        # The first three are executed probes against the real legacy server, so
        # each records that the legacy server answered success anyway. The
        # fourth is recorded as unreached instead, because no committed row
        # lacks both derived fields.
        for entry in refusals[:3]:
            self.assertIn("success", entry["legacy"])
        self.assertTrue(refusals[3]["legacy"].startswith("n/a"))
        probes = FIXTURE["manifest"]["probes"]
        self.assertEqual(len(probes), 4)
        for probe in probes:
            self.assertTrue(probe["executed_in_this_capture"])
            self.assertFalse(probe["parity"], probe["probe"])
            self.assertTrue(probe["changed_leaves"], probe["probe"])
        self.assertEqual(
            [probe["modern_refusal"] for probe in probes],
            [
                placement.REASON_NOT_IN_STORAGE,
                placement.REASON_SLOT_OCCUPIED,
                placement.REASON_UNKNOWN_ITEM_ID,
                None,
            ],
        )

    def test_the_manifest_records_the_geometry_gap_and_the_deferred_branches(self) -> None:
        manifest = FIXTURE["manifest"]
        self.assertIn("M6 tile-to-cell geometry gap", manifest["geometry_gap"])
        self.assertIn("CELL OCCUPANCY IS NOT CHECKED", manifest["cell_occupancy_gap"])
        self.assertIn("NO CAPACITY", manifest["no_capacity_rule"])
        self.assertIn("OUT OF SCOPE", manifest["no_stock_rule"])
        self.assertEqual(manifest["target"]["fabricated_state"], False)
        self.assertEqual(manifest["target"]["store_before"], {})
        self.assertEqual(manifest["target"]["ledger_before"], [])
        self.assertEqual(manifest["target"]["placement_count_before"], 40)
        self.assertEqual(
            manifest["target"]["seed_collection"]["prize"],
            {str(FIXTURE_PLACE_ITEM): 1},
        )
        self.assertEqual(
            manifest["target"]["sell_collection"]["prize"],
            {str(FIXTURE_SELL_ITEM): 1},
        )
        for record in (manifest["target"]["seed_collection"],
                       manifest["target"]["sell_collection"]):
            self.assertIn("DERIVED-PROVISIONAL", record["index_rule"])
            self.assertIn("Nothing here is observed from the Flash client",
                          record["index_rule"])

    def test_the_manifest_records_the_capture_containment(self) -> None:
        manifest = FIXTURE["manifest"]
        self.assertEqual(manifest["schema"],
                         "godot-stored-item-placement/legacy-capture-v1")
        self.assertEqual(manifest["exit_code"], 0)
        self.assertEqual(manifest["interpreter"]["version"].split(" ")[0], "3.9.13")
        containment = manifest["containment"]
        self.assertTrue(containment["identical"])
        self.assertTrue(containment["loopback_only"])
        self.assertTrue(containment["no_flash_browser_external_network"])
        self.assertTrue(containment["protected_fixtures"]["identical"])
        self.assertEqual(len(containment["protected_fixtures"]["paths"]), 16)
        self.assertEqual(
            containment["pre_combined_sha256"], containment["post_combined_sha256"]
        )
        self.assertTrue(manifest["cleanup"]["server_stopped_within_run"])
        self.assertTrue(manifest["cleanup"]["disposable_removed_before_manifest_write"])
        self.assertTrue(manifest["server"]["port_free_after_stop"])
        self.assertEqual(manifest["server"]["port"], 5055)
        self.assertEqual(manifest["server"]["host"], "127.0.0.1")

    def test_the_manifest_records_five_steps_in_the_replayed_order(self) -> None:
        steps = FIXTURE["manifest"]["recorded_steps"]
        self.assertEqual(steps["count"], 5)
        self.assertEqual(
            [entry["name"] for entry in steps["steps"]],
            [LOGIN_STEP, SEED_STEP, PLACE_STEP, SEED2_STEP, SELL_STEP],
        )
        self.assertEqual(steps["placement_count_before"], 40)
        self.assertEqual(steps["placement_count_after"], 41)
        self.assertTrue(steps["map_key_set_grew_by_one"])
        self.assertTrue(steps["other_rows_unchanged"])
        self.assertTrue(steps["other_map_fields_unchanged"])
        self.assertTrue(steps["player_info_unchanged"])
        self.assertEqual(
            steps["resource_delta"], {name: 0 for name in
                                     placement.COMMITTED_RESOURCE_BEFORE}
        )
        self.assertEqual(steps["ledger_before"], [])
        self.assertEqual(steps["ledger_after"], [FIXTURE_PLACE_ITEM])
        self.assertEqual(steps["collections_before"], [])
        self.assertEqual(steps["collections_after"],
                         [FIXTURE_SEED_COLLECTION, FIXTURE_SEED2_COLLECTION])
        self.assertEqual(steps["store_before"], {})
        self.assertEqual(steps["store_after"], {})
        for entry in steps["steps"]:
            if entry["name"] == LOGIN_STEP:
                # The login form answers a 207-byte redirect to /play.html; every
                # command step answers the 21-byte legacy success string.
                self.assertEqual(entry["status"], 302)
                self.assertEqual(entry["response_bytes"], 207)
            else:
                self.assertEqual(entry["status"], 200)
                self.assertEqual(entry["response_bytes"], 21, entry["name"])
        self.assertTrue(steps["steps"][0]["save_unchanged_by_call"])
        for entry in steps["steps"][1:]:
            self.assertFalse(entry["save_unchanged_by_call"], entry["name"])

    def test_the_fixture_readme_states_the_claim_limits(self) -> None:
        # The README hard-wraps, so every fragment is matched against a
        # whitespace-flattened copy: a phrase must survive reflowing, but its
        # wording may not change.
        readme = " ".join(FIXTURE["readme"].split())
        self.assertIn("executed-legacy parity oracle", readme)
        self.assertIn("no fabricated player state", readme.lower())
        self.assertIn("three leaves", readme.lower())
        self.assertIn("two at map scope", readme.lower())
        self.assertIn("one volatile state leaf", readme.lower())
        self.assertIn("NO normalization is applied", readme)
        self.assertIn("sale credits NOTHING", readme)
        self.assertIn("deliberate divergence", readme.lower())
        self.assertIn("M6 tile-to-cell geometry gap", readme)
        self.assertIn("derived-provisional", readme)
        self.assertIn("never observed from the Flash client", readme)
        self.assertIn("no pixel parity", readme.lower())
        self.assertIn("127.0.0.1:5055", readme)
        self.assertIn("exit code 0", readme.lower())
        self.assertIn("re-runnable", readme.lower())
        self.assertIn("sixteen", readme.lower())
        self.assertIn("no Flash, Ruffle, ActionScript, or browser", readme)


# ------------------------------------------------------------- executing --

class ParityTests(unittest.TestCase):
    """Both endpoints reproduce the recorded transaction exactly."""

    def setUp(self) -> None:
        reset_state()

    # -- the seed -----------------------------------------------------------

    def test_the_seed_response_reproduces_the_captured_legacy_result(self) -> None:
        body = seed_first()
        self.assertEqual(body["result"], "success")
        self.assertEqual(
            json.loads(FIXTURE["seed"]["body"].decode("utf-8"))["result"],
            body["result"],
        )

    def test_the_seed_matches_its_capture_with_no_exclusion_at_all(self) -> None:
        seed_first()
        self.assertEqual(
            leaf_differences(FIXTURE["seed"]["after"], live_save()),
            [],
            "the seed step precedes the placement, so it carries no clock value "
            "and is compared leaf for leaf with no normalization",
        )

    # -- the placement ------------------------------------------------------

    def test_the_place_response_reproduces_the_captured_legacy_result(self) -> None:
        seed_first()
        body = place_derived()
        self.assertEqual(body["result"], "success")
        self.assertEqual(
            json.loads(FIXTURE["place"]["body"].decode("utf-8"))["result"],
            body["result"],
        )

    def test_the_derived_slot_cell_and_orientation_match_the_capture(self) -> None:
        seed_first()
        body = place_derived()
        block = body["placement"]
        self.assertEqual(block["command"], placement.PLACE_COMMAND)
        self.assertEqual(block["item_id"], FIXTURE_PLACE_ITEM)
        self.assertEqual(
            [block["x"], block["y"]], list(placement.COMMITTED_CELL)
        )
        self.assertEqual(block["orientation"], placement.COMMITTED_ORIENTATION)
        self.assertEqual(block["map_key"], placement.COMMITTED_DERIVED_SLOT)
        self.assertEqual(block["slot_rule"], placement.SLOT_RULE)
        self.assertEqual(block["row_derivation"], placement.ROW_DERIVATION)
        recorded = FIXTURE["place"]["after"]["maps"][0]["items"][
            str(placement.COMMITTED_DERIVED_SLOT)
        ]
        self.assertEqual(body["row"]["item_id"], recorded[placement.ROW_SLOT_ITEM])
        self.assertEqual(body["row"]["x"], recorded[placement.ROW_SLOT_X])
        self.assertEqual(body["row"]["y"], recorded[placement.ROW_SLOT_Y])
        self.assertEqual(body["row"]["orientation"],
                         recorded[placement.ROW_SLOT_ORIENTATION])
        self.assertEqual(body["row"]["store"], recorded[placement.ROW_SLOT_STORE])
        self.assertEqual(body["row"]["attr"], recorded[placement.ROW_SLOT_ATTR])
        self.assertEqual(body["row"]["player"], recorded[placement.ROW_SLOT_PLAYER])
        self.assertEqual(body["row"]["attr_rule"], placement.ATTR_RULE)
        self.assertEqual(body["row"]["attr_derived_from"], [])
        self.assertEqual(body["row"]["timestamp_note"], placement.TIMESTAMP_NOTE)

    def test_the_row_is_the_derived_row_not_the_recorded_instant(self) -> None:
        seed_first()
        body = place_derived()
        slots = body["row"]["slots"]
        self.assertEqual(
            slots,
            placement.expected_row(
                FIXTURE_PLACE_ITEM, 58, 47, slots[placement.ROW_SLOT_TIMESTAMP],
                placement.COMMITTED_ORIENTATION,
            ),
            "every slot but the instant is a fixed constant or a pure function "
            "of committed content, so the row cannot have been copied from the "
            "capture",
        )
        self.assertEqual(slots[placement.ROW_SLOT_ATTR], {})
        self.assertEqual(slots[placement.ROW_SLOT_STORE], [])
        self.assertEqual(slots[placement.ROW_SLOT_PLAYER], placement.DERIVED_PLAYER_TEAM)

    def test_the_placement_consumed_exactly_one_stored_unit(self) -> None:
        seed_first()
        body = place_derived()
        recorded_before = FIXTURE["place"]["before"]["maps"][0]["store"]
        recorded_after = FIXTURE["place"]["after"]["maps"][0]["store"]
        self.assertEqual(body["storage_before"], recorded_before)
        self.assertEqual(body["storage_after"], recorded_after)
        self.assertEqual(body["quantity"]["consumed"], placement.QUANTITY)
        self.assertEqual(body["quantity"]["count_before"], 1)
        self.assertEqual(body["quantity"]["count_after"], 0)
        self.assertEqual(body["quantity"]["rule"], placement.QUANTITY_RULE)
        self.assertEqual(BOOT.map_store(PID), recorded_after)  # type: ignore[union-attr]

    def test_the_ledger_grew_by_exactly_the_placed_id(self) -> None:
        seed_first()
        body = place_derived()
        recorded_before = FIXTURE["place"]["before"]["privateState"]["boughtUnits"]
        recorded_after = FIXTURE["place"]["after"]["privateState"]["boughtUnits"]
        self.assertEqual(body["ledger_before"], recorded_before)
        self.assertEqual(body["ledger_after"], recorded_after)
        self.assertEqual(body["ledger_rule"], placement.LEDGER_RULE)
        self.assertEqual(body["ledger_after"], [FIXTURE_PLACE_ITEM])
        self.assertEqual(
            live_save()["privateState"]["boughtUnits"], recorded_after
        )

    def test_the_placement_moved_no_resource(self) -> None:
        seed_first()
        body = place_derived()
        recorded = resources_of(FIXTURE["place"]["after"])
        self.assertEqual(body["resources"], recorded)
        self.assertEqual(recorded, placement.COMMITTED_RESOURCE_BEFORE)
        self.assertEqual(BOOT.resources(PID), recorded)  # type: ignore[union-attr]

    def test_the_replayed_placement_state_equals_the_capture_at_one_leaf(self) -> None:
        seed_first()
        place_derived()
        differing = leaf_differences(FIXTURE["place"]["after"], live_save())
        self.assertEqual(
            differing,
            [VOLATILE_LEAF],
            "the ONLY difference between the captured placement after-state and "
            "the replayed one is the row's server-clock instant",
        )
        self.assertEqual(
            differing_from_capture(FIXTURE["place"], live_save(), [VOLATILE_LEAF]),
            [],
            "with that single documented exclusion, every other leaf matches by "
            "value",
        )

    def test_a_client_sent_slot_row_bag_team_count_and_price_are_all_ignored(
        self,
    ) -> None:
        seed_first()
        body = place_derived({
            "item_id": FIXTURE_PLACE_ITEM,
            "x": 58,
            "y": 47,
            "map_key": 7,
            "index": 7,
            "item_index": 7,
            "slot": 7,
            "row": [999, 1, 1, 1, 1, [1], {"nc": 99}, 3],
            "attr": {"nc": 99},
            "attribute": {"nc": 99},
            "player": 3,
            "player_id": 3,
            "playerID": 3,
            "team": 3,
            "orientation_flag": 1,
            "quantity": 99,
            "count": 99,
            "price": 5000,
            "cost": 5000,
            "costs": {"gold": 5000},
            "refund": 5000,
            "value": 5000,
            "timestamp": 1700000000,
            "autoactivable": True,
            "img_index": 5,
            "bought": True,
            "reason": "KILL",
            "vector": [1, 1, 1, 1, 1, 1, 1, 1],
            "resources_changed": {"gold": -1},
            "placement": 41,
        })
        self.assertEqual(body["placement"]["map_key"],
                         placement.COMMITTED_DERIVED_SLOT)
        slots = body["row"]["slots"]
        self.assertEqual(slots[placement.ROW_SLOT_ITEM], FIXTURE_PLACE_ITEM)
        self.assertEqual(slots[placement.ROW_SLOT_X], 58)
        self.assertEqual(slots[placement.ROW_SLOT_Y], 47)
        self.assertEqual(slots[placement.ROW_SLOT_STORE], [])
        self.assertEqual(slots[placement.ROW_SLOT_ATTR], {})
        self.assertEqual(slots[placement.ROW_SLOT_PLAYER], 1)
        self.assertEqual(body["quantity"]["count_before"], 1)
        self.assertEqual(body["resources"], placement.COMMITTED_RESOURCE_BEFORE)
        self.assertEqual(BOOT.resources(PID), placement.COMMITTED_RESOURCE_BEFORE)  # type: ignore[union-attr]

    # -- the second seed and the sale --------------------------------------

    def test_the_second_seed_grants_the_sale_subject_by_value(self) -> None:
        seed_first()
        place_derived()
        body = seed_second()
        recorded = FIXTURE["seed2"]["after"]["maps"][0]["store"]
        self.assertEqual(body["grant"]["item_id"], str(FIXTURE_SELL_ITEM))
        self.assertEqual(body["grant"]["quantity"], 1)
        self.assertEqual(body["prize"]["bag"], recorded)
        self.assertEqual(recorded, {str(FIXTURE_SELL_ITEM): 1})
        self.assertEqual(body["store_after"], recorded)

    def test_the_sale_response_reproduces_the_captured_legacy_result(self) -> None:
        seed_first()
        place_derived()
        seed_second()
        body = sell_derived()
        self.assertEqual(body["result"], "success")
        self.assertEqual(
            json.loads(FIXTURE["sell"]["body"].decode("utf-8"))["result"],
            body["result"],
        )

    def test_the_sale_consumed_one_stored_unit_and_credited_nothing(self) -> None:
        seed_first()
        place_derived()
        seed_second()
        body = sell_derived()
        self.assertEqual(body["sale"]["command"], placement.SELL_COMMAND)
        self.assertEqual(body["sale"]["item_id"], FIXTURE_SELL_ITEM)
        self.assertFalse(body["sale"]["credited"])
        self.assertIsNone(body["sale"]["refund"])
        self.assertEqual(body["sale"]["note"], placement.NO_REFUND_NOTE)
        self.assertEqual(body["quantity"]["consumed"], placement.QUANTITY)
        self.assertEqual(body["quantity"]["count_before"], 1)
        self.assertEqual(body["quantity"]["count_after"], 0)
        self.assertEqual(
            body["storage_before"],
            FIXTURE["sell"]["before"]["maps"][0]["store"],
        )
        self.assertEqual(body["storage_after"],
                         FIXTURE["sell"]["after"]["maps"][0]["store"])
        self.assertEqual(body["placements"]["untouched"], True)
        self.assertEqual(body["placements"]["before"],
                         body["placements"]["after"])

    def test_the_sale_left_the_placements_and_the_ledger_untouched(self) -> None:
        seed_first()
        place_derived()
        seed_second()
        before_items = copy.deepcopy(BOOT.map_items(PID))  # type: ignore[union-attr]
        before_ledger = list(live_save()["privateState"]["boughtUnits"])
        body = sell_derived()
        self.assertEqual(BOOT.map_items(PID), before_items)  # type: ignore[union-attr]
        self.assertEqual(len(before_items), placement.COMMITTED_PLACEMENTS + 1)
        self.assertEqual(body["ledger_before"], before_ledger)
        self.assertEqual(body["ledger_after"], before_ledger)
        self.assertEqual(body["ledger_rule"], placement.LEDGER_RULE)
        self.assertEqual(before_ledger, [FIXTURE_PLACE_ITEM])

    def test_the_sale_moved_no_resource(self) -> None:
        seed_first()
        place_derived()
        seed_second()
        body = sell_derived()
        recorded = resources_of(FIXTURE["sell"]["after"])
        self.assertEqual(body["resources"], recorded)
        self.assertEqual(recorded, placement.COMMITTED_RESOURCE_BEFORE)
        self.assertEqual(BOOT.resources(PID), recorded)  # type: ignore[union-attr]

    def test_the_replayed_sale_state_equals_the_capture_at_one_leaf(self) -> None:
        seed_first()
        place_derived()
        seed_second()
        sell_derived()
        differing = leaf_differences(FIXTURE["sell"]["after"], live_save())
        self.assertEqual(
            differing,
            [VOLATILE_LEAF],
            "the sale's captured documents contain the placed row, so the sale's "
            "own after-state differs at that one leaf and nowhere else",
        )
        self.assertEqual(
            differing_from_capture(FIXTURE["sell"], live_save(), [VOLATILE_LEAF]),
            [],
        )

    def test_the_whole_replay_reproduces_the_final_state_leaf_for_leaf(self) -> None:
        replay_all()
        self.assertEqual(
            differing_from_capture(FIXTURE["sell"], live_save(), [VOLATILE_LEAF]),
            [],
        )
        final = live_save()
        self.assertEqual(final["maps"][0]["store"], {})
        self.assertEqual(final["privateState"]["boughtUnits"], [FIXTURE_PLACE_ITEM])
        self.assertEqual(
            final["privateState"]["collections"],
            [FIXTURE_SEED_COLLECTION, FIXTURE_SEED2_COLLECTION],
        )
        self.assertEqual(len(final["maps"][0]["items"]),
                         placement.COMMITTED_PLACEMENTS + 1)
        self.assertEqual(resources_of(final), placement.COMMITTED_RESOURCE_BEFORE)

    def test_a_client_sent_price_cannot_turn_the_sale_into_a_payout(self) -> None:
        seed_first()
        place_derived()
        seed_second()
        body = sell_derived({
            "item_id": FIXTURE_SELL_ITEM,
            "price": 5000,
            "cost": 5000,
            "costs": {"gold": 5000},
            "refund": 5000,
            "quantity": 99,
            "count": 99,
            "cash": 5000,
            "gold": 5000,
            "value": 5000,
            "vector": [1, 1, 1, 1, 1, 1, 1, 1],
            "resources_changed": {"gold": 1},
            "x": 1,
            "y": 2,
            "map_key": 7,
            "row": [1],
            "team": 3,
            "reason": "KILL",
        })
        self.assertFalse(body["sale"]["credited"])
        self.assertIsNone(body["sale"]["refund"])
        self.assertEqual(body["quantity"]["consumed"], placement.QUANTITY)
        self.assertEqual(body["quantity"]["count_before"], 1)
        self.assertEqual(body["resources"], placement.COMMITTED_RESOURCE_BEFORE)
        self.assertEqual(BOOT.resources(PID), placement.COMMITTED_RESOURCE_BEFORE)  # type: ignore[union-attr]

    def test_the_working_tree_saves_are_untouched_by_the_replay(self) -> None:
        replay_all()
        self.assertEqual(WORKING_TREE_PRE, harness.working_tree_save_hashes())


class NoServerTests(unittest.TestCase):
    """The replay opened no connection and started no service."""

    def test_no_server_is_running(self) -> None:
        for port in (5055, 5056):
            self.assertTrue(
                harness.port_is_free("127.0.0.1", port),
                "nothing is listening on 127.0.0.1:%d" % port,
            )

    def test_the_corpus_lives_in_the_system_temp_root(self) -> None:
        self.assertIsNotNone(CORPUS)
        self.assertFalse(str(CORPUS).startswith(str(harness.REPO_ROOT)))
        temp_root = Path(os.environ.get("TEMP", "/tmp"))
        self.assertTrue(str(CORPUS).startswith(str(temp_root)))
        self.assertFalse((harness.REPO_ROOT / "saves").exists())


if __name__ == "__main__":
    unittest.main()