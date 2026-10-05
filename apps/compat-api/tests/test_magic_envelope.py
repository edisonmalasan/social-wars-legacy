#!/usr/bin/env python3
"""Offline unit tests for ``magic_envelope`` (OpenSpec task 2.1, ``godot-damage``).

No server, no socket, no network, and **no endpoint**: this module imports the
derivation and asserts it against **the committed bytes themselves** --
``command.py``, ``get_game_config.py``, ``config/main.json``, the normalized
magics package, and the committed village documents -- so every recorded
constant here is a **measurement** rather than a restatement of the module's own
prose.  A constant that drifts from the source fails in this suite instead of
being published.

Covered:

* the **closed two-action** vocabulary, the one command each action dispatches,
  and the fact that the two are never exchanged -- asserted in both directions, so
  neither a swap nor a fourth action can pass;
* **every** key naming a count is refused by name, all eleven closed-list members
  and the substring synonyms the closed list did not anticipate, plus the six
  protocol-plumbing keys; and that a **pure intent** refuses nothing, so the guard
  cannot pass by refusing everything;
* the **identity split** between ``non_canonical_magic_id`` and
  ``invalid_magic_id``: a float and a string are refused as non-canonical because
  their *string form* differs from the committed ledger key, while a bool is
  refused as invalid because it is not an integer at all;
* the ledger and counter projections failing **closed** -- ``None`` and a
  non-mapping ledger reported rather than defaulted to ``{}``, and a present but
  ill-typed or negative counter refused rather than interpreted;
* the derived transition table including its three boundary rows, and the
  ``counter_above_cap`` refusal that ``min(cap, before + 1)`` makes unavoidable;
* the **validation order**: eight steps, the write at nine, and the content check
  at five sitting above the three that read player state, so a request naming a
  spell that does not exist never consults the corpus;
* the **eight** stored resource slots -- eight, not the seven
  ``LegacyBoot.resources`` exposes -- with ``mana`` and ``energy`` both present;
* the derived batch envelope: six keys, exactly one command, one argument, and
  the neutral eight-zero vector;
* the **re-derived source inventory**: the two branches and both operators read
  from ``command.py`` as bytes, the cap read as a **literal** at two lines, the
  dispatcher branch count **cross-checked against the project's own command
  catalog** rather than asserted by regex alone, and the damage census re-measured
  across all eleven legacy root modules;
* the recorded **absences**: seven divergences with pinned ids, the damage
  refusal, the ledger's zero readers, and the recorded no-op branch;
* the whole module's **function inventory** against a pinned list, so an invented
  ``damage_for`` / ``hit_points`` / ``combat_outcome`` helper fails the run
  wherever it is added.

Three measurement notes, each of which changed a claim rather than confirming one

    ``attack`` has 42 whole-file occurrences and **zero** tokens.  Both numbers
    are asserted.  The substring count is what a naive census reports; the token
    count is what a consumer actually needs; and this suite asserts that the scan
    is **not vacuous** by requiring the substring count to be large while the
    token count is zero, which is a combination only a working scanner produces.

    The committed magic table is a **list** of ten rows carrying a native ``id``
    column running ``1..10``, not a mapping keyed by id.  Both ``config/main.json``
    and the normalized package are read to establish that, so
    ``COMMITTED_MAGIC_COUNT`` and the id bounds are measured from committed
    content rather than trusted from the constant.

    ``get_game_config.py`` contains **zero** occurrences of the word ``magic``
    under all three counting views.  That is stronger than the committed
    investigation's "the ledger has zero readers": the magics are loaded into the
    configuration and never **indexed**, so there is no code path from a magic id
    to its content row at all.  It is asserted here because it is the fact that
    makes the endpoint's identity check a new authority rather than a reproduction.
"""

from __future__ import annotations

import ast
import json
import pathlib
import re
import unittest
from typing import Any, Dict, List, Optional

import compat_test_harness as harness  # noqa: F401  (path setup)

import magic_envelope as M

REPO = harness.REPO_ROOT
COMMAND_SOURCE = REPO / "command.py"
CONFIG_SOURCE = REPO / "get_game_config.py"
COMMITTED_CONFIG = REPO / "config" / "main.json"
NORMALIZED_MAGICS = (
    REPO / "packages" / "game-content" / "normalized" / "magics.json"
)
SEED_VILLAGE = REPO / "villages" / "Neutral.json"

#: The whole function inventory of ``magic_envelope``.  This is the
#: anti-invention gate: any helper added to the module shows up here and fails the
#: run, which is what makes the absence claims structural rather than a matter of
#: reading the module.
EXPECTED_MODULE_FUNCTIONS = [
    "_branch_span",
    "_repo_root",
    "_strip_string_literals",
    "actions",
    "branch_count_agrees_with_catalog",
    "branches",
    "build_envelope",
    "code_only",
    "count_field_consumers",
    "counter_value",
    "derive_counter_transition",
    "derive_field_inventory",
    "divergences",
    "inventory",
    "io_open",
    "is_action",
    "is_canonical_magic_key",
    "is_committed_magic",
    "ledger_key_for",
    "legacy_census_text",
    "legacy_source_text",
    "neutral_vector",
    "non_claims",
    "project_ledger",
    "project_magic",
    "refused_client_keys",
    "reported_vocabulary",
    "validate_vector",
]

#: Helper names whose mere existence would be an invented combat or damage rule.
#: Matched as SUBSTRINGS as well as by whole name, because an earlier by-name
#: guard in this repository matched only the exact name and so missed a suffixed
#: helper wearing the same disguise.  Compared case-insensitively, because a
#: guard that ``magic_damage`` slips past is not a guard.
FORBIDDEN_HELPER_FRAGMENTS = (
    "damage",
    "defence",
    "defense",
    "hit_point",
    "hitpoint",
    "hit_chance",
    "hitchance",
    "casualt",
    "wound",
    "armour",
    "armor",
    "shield",
    "combat_outcome",
    "combat_result",
    "resolution",
    "hp_total",
    "health",
    "life_total",
    "victim",
    "attacker",
    "award",
    "grant",
)

#: Identifiers that legitimately carry one of the fragments above because they
#: name the recorded **absence** or the recorded refusal instead of a rule.  This
#: list is measured against the module and required to be exact, so it cannot
#: quietly grow into a loophole -- and it was derived from the module rather than
#: guessed, because a hand-written list would have been wrong.
FORBIDDEN_HELPER_EXEMPT = (
    "ABSENT_MAGNITUDE_ENTRY",
    "COST_DAMAGE_ENEMY",
    "COST_DAMAGE_SELF",
    "COST_DAMAGE_TOKENS",
    "NO_DAMAGE",
    "REPORTED_DAMAGE_VOCABULARY",
    "ZERO_CONSUMER_DAMAGE_FIELDS",
    "damage_census",
)

#: The two counting rules that can establish a consumer at all.  Recorded here
#: because ``magic_envelope.CONSUMER_RULES`` names FOUR rules and its own module
#: docstring says only these two can -- see
#: :class:`ConsumerRuleConsistencyTests` for the measurement that settles it.
ESTABLISHING_RULES = ("token", "quoted")

#: The two rules that are substring counts and therefore cannot establish a
#: consumer on their own.
SUBSTRING_RULES = ("whole", "distinct_line", "code_only", "code_distinct_line")

#: The ONE field of the seven whose substring counts are non-zero, and every one
#: of those occurrences sits inside a longer identifier (``end_attack``,
#: ``attacker``, ``attacker_units``, ``tsAttacksReset``).  Measured, not assumed.
SUBSTRING_CARRYING_FIELD = "attack"

#: ``magic_envelope.PROTOCOL_KEYS`` mixes cases: four members are all-lowercase
#: and two are camelCase.  ``refused_client_keys`` lower-cases the client's key
#: before comparing, so the two camelCase members -- which are exactly two of the
#: legacy batch envelope's own keys -- are NOT refused.  This is a defect in a
#: module this line does not own, so it is pinned as a measured record rather than
#: asserted as intended behaviour; see
#: :meth:`ClientDictatedCountTests.test_two_protocol_keys_are_definitely_NOT_refused_and_why`.
UNREFUSABLE_PROTOCOL_KEYS = ("accessToken", "publishActions")

#: The seven divergence ids, pinned so a removal is a failure rather than a
#: quieter record.
EXPECTED_DIVERGENCE_IDS = [
    "absent_key_writes_zero_not_one",
    "buy_magic_unbounded_growth",
    "cap_applied_uniformly",
    "counter_above_cap_reduced_by_legacy",
    "float_identity_creates_distinct_key",
    "identity_outside_committed_table_accepted",
    "use_magic_decreases_counter",
]

#: The recorded key-order of ``VALIDATION_ORDER``.  Read here rather than
#: generated from the module, so a reordered projection fails.
EXPECTED_ORDER_KEYS = [
    "action_in_closed_vocabulary",
    "no_client_dictated_count",
    "identity_present",
    "identity_well_typed",
    "identity_in_committed_table",
    "ledger_readable",
    "counter_readable",
    "transition_derived",
]


def module_source() -> str:
    return pathlib.Path(M.__file__).read_text(encoding="utf-8")


def module_functions() -> List[str]:
    tree = ast.parse(module_source())
    return sorted(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def module_code_identifiers() -> List[str]:
    """Every identifier the module's CODE declares, binds, or reads.

    Docstrings, comments and string literals are excluded **by parsing** rather
    than by scanning, so a recorded refusal sentence that happens to use the word
    "damage" can never be mistaken for a computation.  A scanning implementation
    would also be desynchronised by an apostrophe inside a double-quoted string,
    which is a fault this repository has already recorded once.
    """
    names: List[str] = []
    for node in ast.walk(ast.parse(module_source())):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
        elif isinstance(node, ast.arg):
            names.append(node.arg)
        elif isinstance(node, ast.keyword) and node.arg:
            names.append(node.arg)
    return sorted(set(names))


def command_lines() -> List[str]:
    # Newlines are NOT universal-newline translated, so the reported line numbers
    # agree with the committed file on a CRLF checkout.  ``Path.read_text`` grew
    # a ``newline`` argument only in CPython 3.13 and this line runs on the pinned
    # 3.9, so the open is explicit.
    with open(COMMAND_SOURCE, "r", encoding="utf-8", newline="") as handle:
        return handle.read().split("\n")


def config_source() -> str:
    with open(CONFIG_SOURCE, "r", encoding="utf-8", newline="") as handle:
        return handle.read()


def committed_magics() -> List[Dict[str, Any]]:
    config = json.loads(COMMITTED_CONFIG.read_text(encoding="utf-8"))
    magics = config["magics"]
    if not isinstance(magics, list):
        raise AssertionError("committed config magics is a %s" % type(magics).__name__)
    return magics


def magic_of(magic_id: int) -> Optional[Dict[str, Any]]:
    """One magic id's committed row, resolved the way an endpoint would."""
    for row in committed_magics():
        if int(row.get("id")) == int(magic_id):
            return row
    return None


def refusal_code(projection: Dict[str, Any]) -> str:
    return str(projection.get("reason", ""))


# ------------------------------------------------------- the action vocabulary --
class ActionVocabularyTests(unittest.TestCase):
    """Two actions, two commands, and no way to exchange them."""

    def test_the_vocabulary_is_exactly_the_two_recorded_branches(self) -> None:
        self.assertEqual(M.ACTIONS, ("buy", "use"))
        self.assertEqual(M.ACTION_COUNT, 2)
        self.assertEqual(tuple(M.actions()), M.ACTIONS)

    def test_every_action_maps_to_exactly_one_command_and_back(self) -> None:
        self.assertEqual(sorted(M.ACTION_COMMAND), sorted(M.ACTIONS))
        self.assertEqual(
            sorted(M.ACTION_COMMAND.values()),
            sorted(M.MAGIC_COMMANDS),
            "no action maps to no branch and no branch maps to no action",
        )
        self.assertEqual(len(set(M.ACTION_COMMAND.values())), 2)
        self.assertEqual(
            sorted(M.ACTION_ADDRESSING_KEY), sorted(M.ACTIONS)
        )
        self.assertEqual(
            sorted(M.ACTION_ARGUMENT_COUNT), sorted(M.ACTIONS)
        )
        self.assertEqual(
            set(M.ACTION_ARGUMENT_COUNT.values()),
            {1},
            "both branches read exactly one argument -- magic_id (command.py:653, 665)",
        )

    def test_the_two_actions_are_never_exchanged(self) -> None:
        self.assertEqual(M.ACTION_COMMAND["buy"], M.BUY_COMMAND)
        self.assertEqual(M.ACTION_COMMAND["use"], M.USE_COMMAND)
        self.assertNotEqual(M.ACTION_COMMAND["buy"], M.ACTION_COMMAND["use"])
        self.assertNotEqual(
            M.ACTION_COMMAND["buy"], M.USE_COMMAND,
            "buy must not reach use_magic, whose recorded assignment is the "
            "charge-destroying decrease",
        )
        self.assertNotEqual(
            M.ACTION_COMMAND["use"], M.BUY_COMMAND,
            "use must not reach buy_magic, whose recorded += is unbounded",
        )

    def test_both_actions_address_the_same_committed_identity(self) -> None:
        self.assertEqual(
            sorted(set(M.ACTION_ADDRESSING_KEY.values())),
            ["magic_id"],
            "the ledger is keyed by the committed magic id for both branches",
        )

    def test_is_action_accepts_exactly_the_two_and_rejects_the_commands(self) -> None:
        for action in M.ACTIONS:
            self.assertTrue(M.is_action(action), action)
        # The COMMAND NAMES are not actions.  A client that sends the legacy
        # command name instead of the closed action must be refused rather than
        # silently mapped onto the branch it names -- which would let it choose
        # the arm whose defect it wants.
        for refused in (
            M.BUY_COMMAND,
            M.USE_COMMAND,
            M.NO_OP_COMMAND,
            "BUY",
            "Buy",
            "buy ",
            "",
            None,
            1,
            True,
            ["buy"],
            {"action": "buy"},
        ):
            with self.subTest(value=refused):
                self.assertFalse(M.is_action(refused))

    def test_the_recorded_no_op_branch_is_named_and_not_delivered(self) -> None:
        self.assertEqual(M.NO_OP_COMMAND, "buy_mana_new")
        self.assertNotIn(M.NO_OP_COMMAND, M.ACTIONS)
        self.assertNotIn(M.NO_OP_COMMAND, M.ACTION_COMMAND.values())
        self.assertIn("Nothing needs to be done here", M.NO_OP_NOTE)
        lines = command_lines()
        # The branch spans exactly two lines: its own `elif` and one body line,
        # and the body is a print whose own trailing comment is the finding.
        self.assertEqual(lines[M.NO_OP_LINE - 2].strip(), 'elif cmd == "buy_mana_new":')
        body = lines[M.NO_OP_LINE - 1].strip()
        self.assertEqual(body, 'print("Bought mana") # Nothing needs to be done here :)')
        # The very next line opens the buy branch, so the no-op really is one
        # `elif` plus one print and not a longer arm truncated here.
        self.assertEqual(lines[M.NO_OP_LINE + 1].strip(), 'elif cmd == "buy_magic":')

    def test_no_fourth_magic_branch_exists_in_the_committed_dispatcher(self) -> None:
        branches = [entry["name"] for entry in M.branches()]
        self.assertEqual(branches, list(M.MAGIC_COMMANDS))
        # And no OTHER branch anywhere in command.py touches the ledger, which is
        # what makes "two branches" a measurement rather than a naming choice.
        inv = M.derive_field_inventory()
        self.assertEqual(inv["ledger_write_sites"], 4)
        self.assertEqual(inv["ledger_membership_tests"], 2)
        self.assertEqual(inv["ledger_bindings"], 2)
        self.assertEqual(inv["ledger_read_sites"], 0)


# ------------------------------------------------- the client-dictated count --
class ClientDictatedCountTests(unittest.TestCase):
    """A request may name an identity; it may never name a count."""

    def test_the_closed_list_is_the_eleven_recorded_keys(self) -> None:
        self.assertEqual(
            list(M.COUNT_KEYS),
            [
                "count", "delta", "new_value", "value", "amount", "uses",
                "charges", "quantity", "remaining", "cap", "max_uses",
            ],
        )
        self.assertEqual(len(set(M.COUNT_KEYS)), len(M.COUNT_KEYS))
        # The compared tuple holds LOWER-CASE forms only.  It used to hold the
        # legacy wire spellings, two of which are camelCase, and the guard folded
        # only the client's key -- so those two were unrefusable.  The wire
        # spellings are no longer lost: they are recorded in
        # `PROTOCOL_KEY_WIRE_SPELLINGS`, which is asserted immediately below.
        self.assertEqual(
            list(M.PROTOCOL_KEYS),
            ["first_number", "publishactions", "ts", "tries", "accesstoken",
             "commands"],
        )
        # `cap` is in the list because the cap is a LITERAL this service applies;
        # a client that restates it is trying to move it.
        self.assertIn("cap", M.COUNT_KEYS)

    def test_the_legacy_wire_spelling_is_recorded_not_discarded(self) -> None:
        # Folding the compared tuple must not erase what the legacy batch envelope
        # actually sends, so both camelCase spellings are preserved verbatim here
        # and each maps onto a member of the compared tuple.
        self.assertEqual(
            M.PROTOCOL_KEY_WIRE_SPELLINGS,
            {"publishactions": "publishActions", "accesstoken": "accessToken"},
        )
        for folded, wire in sorted(M.PROTOCOL_KEY_WIRE_SPELLINGS.items()):
            with self.subTest(wire=wire):
                self.assertIn(folded, M.PROTOCOL_KEYS)
                self.assertEqual(folded, wire.lower())
                self.assertNotEqual(folded, wire, "a recorded wire spelling that "
                                 "is already lower case records nothing")

    def test_both_compared_tuples_are_lower_case_so_they_cannot_drift(self) -> None:
        # This is the guard for the CLASS of defect, not the instance.  The
        # original fault was a compared tuple holding a mixed-case member while
        # the comparison folded only one side; an import-time assertion in the
        # module refuses to load if either tuple ever grows one again, and this
        # test is the visible form of that.
        for name, keys in (("COUNT_KEYS", M.COUNT_KEYS),
                           ("PROTOCOL_KEYS", M.PROTOCOL_KEYS)):
            for key in keys:
                with self.subTest(tuple=name, key=key):
                    self.assertEqual(key, key.lower())
        self.assertEqual(M.COUNT_KEYS_FOLDED,
                         frozenset(k.lower() for k in M.COUNT_KEYS))
        self.assertEqual(M.PROTOCOL_KEYS_FOLDED,
                         frozenset(k.lower() for k in M.PROTOCOL_KEYS))

    def test_every_closed_count_key_is_refused_by_name(self) -> None:
        for key in M.COUNT_KEYS:
            with self.subTest(key=key):
                refused = M.refused_client_keys({key: 5})
                self.assertEqual(refused, [key])

    def test_all_six_protocol_keys_are_refused(self) -> None:
        refused = [
            key for key in M.PROTOCOL_KEYS
            if M.refused_client_keys({key: "x"}) == [key]
        ]
        self.assertEqual(
            sorted(refused),
            sorted(M.PROTOCOL_KEYS),
            "every protocol key is refused, whichever way it is spelled",
        )

    def test_the_formerly_unrefusable_camelCase_keys_are_now_refused(self) -> None:
        """The pinned defect, REPAIRED -- and the repair is what this asserts.

        ``refused_client_keys`` folded the client's key (``folded = key.lower()``)
        and compared it against ``PROTOCOL_KEYS``, four members of which were
        lower case and **two of which were camelCase**.  So ``publishActions`` and
        ``accessToken`` -- two of the six keys of the legacy batch envelope this
        line itself builds -- were silently accepted, which is what the guard
        exists to prevent.

        This suite **pinned that measurement rather than asserting the intended
        behaviour**, so the fault could not pass unnoticed, and it was fixed in
        ``magic_envelope`` by folding **both** sides.  The assertions below are
        the repair made visible; they were failures the moment the module changed,
        which is exactly what pinning was for.

        The refusal is case-insensitive, so the wire spelling, the folded form,
        and an upper-case variant are all refused -- and the refusal is reported
        under the spelling the client actually sent, not the folded one.
        """
        for key in UNREFUSABLE_PROTOCOL_KEYS:
            folded = key.lower()
            with self.subTest(wire=key):
                self.assertNotEqual(key, folded, "this key is the camelCase case")
                self.assertIn(folded, M.PROTOCOL_KEYS)
                self.assertEqual(M.refused_client_keys({key: "anything"}), [key])
                self.assertEqual(M.refused_client_keys({folded: "x"}), [folded])
                self.assertEqual(M.refused_client_keys({key.upper(): "x"}),
                                 [key.upper()])

    def test_the_keys_are_refused_case_insensitively(self) -> None:
        for key in ("COUNT", "Count", "Delta", "MAX_USES", "Value"):
            with self.subTest(key=key):
                self.assertEqual(M.refused_client_keys({key: 1}), [key])

    def test_a_synonym_the_closed_list_did_not_anticipate_is_still_refused(self) -> None:
        # The substring rule is what stops a client inventing `n_spells` or
        # `charge_count` to get a count through.
        for key in (
            "counter",
            "charges_left",
            "charge",
            "my_amount",
            "delta_total",
            "how_many_uses",
            "count_of_spells",
            "REMAINING_charges",
        ):
            with self.subTest(key=key):
                self.assertEqual(
                    M.refused_client_keys({key: 1}),
                    [key],
                    "%r names a count and was accepted" % key,
                )

    def test_a_pure_intent_refuses_nothing(self) -> None:
        self.assertEqual(
            M.refused_client_keys(
                {"user_id": "u", "action": "buy", "magic_id": 1}
            ),
            [],
            "the guard must pass by accepting an honest request, not by refusing "
            "everything",
        )
        # And each of the three keys the delivered request actually carries,
        # tested alone, because a whole-payload pass can hide a single bad key.
        for key in ("user_id", "action", "magic_id"):
            with self.subTest(key=key):
                self.assertEqual(M.refused_client_keys({key: None}), [])

    def test_a_non_mapping_payload_refuses_nothing_rather_than_raising(self) -> None:
        for payload in (None, [], "count", 1, True, ("count",)):
            with self.subTest(payload=payload):
                self.assertEqual(M.refused_client_keys(payload), [])

    def test_a_non_string_key_is_skipped_rather_than_raising(self) -> None:
        # JSON cannot produce a non-string key, but a direct caller can, and the
        # guard must not be the thing that raises on one.
        self.assertEqual(M.refused_client_keys({1: "x", "action": "buy"}), [])

    def test_the_result_follows_the_requests_own_key_order(self) -> None:
        payload = {"user_id": "u", "charges": 3, "action": "buy", "count": 9}
        self.assertEqual(
            M.refused_client_keys(payload), ["charges", "count"],
            "the refusal names every offending key in the order the client sent "
            "them, so the message is stable across runs",
        )

    def test_a_repeated_json_key_collapses_to_one_refusal(self) -> None:
        # json.loads keeps the last value for a repeated key, so one JSON text
        # naming `count` twice yields one refusal.  Asserted rather than assumed
        # because it is the property that makes the refusal a stable message.
        parsed = json.loads('{"count": 1, "count": 2}')
        self.assertEqual(M.refused_client_keys(parsed), ["count"])
        self.assertEqual(parsed["count"], 2)

    def test_the_refusal_is_its_own_named_reason(self) -> None:
        self.assertEqual(M.REASON_CLIENT_DICTATED_COUNT, "client_dictated_count")
        self.assertEqual(M.CLIENT_DICTATED_REFUSAL["reason"], "client_dictated_count")
        self.assertEqual(
            M.CLIENT_DICTATED_REFUSAL["keys"], list(M.COUNT_KEYS)
        )
        self.assertEqual(
            M.CLIENT_DICTATED_REFUSAL["protocol_keys"], list(M.PROTOCOL_KEYS)
        )
        # It is a SEPARATE reason from every eligibility and identity refusal,
        # which is the whole point of naming it.
        others = {
            M.REASON_UNKNOWN_MAGIC_ID,
            M.REASON_INVALID_LEDGER,
            M.REASON_INVALID_COUNTER,
            M.REASON_COUNTER_ABOVE_CAP,
        }
        self.assertNotIn(M.REASON_CLIENT_DICTATED_COUNT, others)


# --------------------------------------------------------- the identity split --
class IdentityTests(unittest.TestCase):
    """Non-canonical is not the same refusal as invalid."""

    def test_only_an_integer_non_bool_identity_is_canonical(self) -> None:
        for accepted in (1, 2, 10, 0, -1, 999):
            with self.subTest(value=accepted):
                self.assertTrue(M.is_canonical_magic_key(accepted))
        for refused in (1.0, 0.0, "1", True, False, None, [1], {"id": 1}, 1 + 0j):
            with self.subTest(value=refused):
                self.assertFalse(M.is_canonical_magic_key(refused))

    def test_a_float_and_a_string_are_non_canonical_because_of_their_string_form(
        self,
    ) -> None:
        # str(1.0) != str(1), and the legacy branch keys on the string form, so
        # these two would create a SECOND, unrelated ledger entry.
        self.assertNotEqual(str(1.0), str(1))
        for value, string_form in ((1.0, "1.0"), ("1", "1")):
            with self.subTest(value=value):
                projection = M.project_magic({}, "use", value)
                self.assertFalse(projection["ok"])
                self.assertEqual(
                    refusal_code(projection), M.REASON_NON_CANONICAL_MAGIC_ID
                )
                self.assertIn(string_form, str(projection["error"]))

    def test_a_bool_is_invalid_because_it_is_not_an_integer_at_all(self) -> None:
        for value in (True, False):
            with self.subTest(value=value):
                projection = M.project_magic({}, "use", value)
                self.assertFalse(projection["ok"])
                self.assertEqual(refusal_code(projection), M.REASON_INVALID_MAGIC_ID)
                self.assertNotEqual(
                    refusal_code(projection), M.REASON_NON_CANONICAL_MAGIC_ID
                )

    def test_a_container_identity_is_invalid(self) -> None:
        for value in ([1], {"id": 1}, (1,), set()):
            with self.subTest(value=value):
                self.assertEqual(
                    refusal_code(M.project_magic({}, "use", value)),
                    M.REASON_INVALID_MAGIC_ID,
                )

    def test_an_absent_identity_is_missing_not_invalid(self) -> None:
        projection = M.project_magic({}, "use", None)
        self.assertEqual(refusal_code(projection), M.REASON_MISSING_MAGIC_ID)

    def test_ledger_key_for_is_the_decimal_spelling_and_refuses_a_bool(self) -> None:
        self.assertEqual(M.ledger_key_for(1), "1")
        self.assertEqual(M.ledger_key_for(10), "10")
        for refused in (True, False, 1.0, "1", None):
            with self.subTest(value=refused):
                with self.assertRaises(M.EnvelopeError) as caught:
                    M.ledger_key_for(refused)
                self.assertEqual(caught.exception.code, M.REASON_INVALID_MAGIC_ID)

    def test_an_identity_outside_the_committed_table_is_unknown(self) -> None:
        for value in (0, 11, 99, 1000, -1):
            with self.subTest(value=value):
                projection = M.project_magic({}, "buy", value, magic_of)
                self.assertFalse(projection["ok"])
                self.assertEqual(
                    refusal_code(projection), M.REASON_UNKNOWN_MAGIC_ID
                )

    def test_the_content_check_runs_before_the_ledger_is_read(self) -> None:
        # A ledger that could never be read still yields unknown_magic_id, which
        # is the observable proof that step 5 precedes steps 6-8.
        projection = M.project_magic(None, "buy", 99, magic_of)
        self.assertEqual(refusal_code(projection), M.REASON_UNKNOWN_MAGIC_ID)
        self.assertIsNone(
            projection["ledger_before"],
            "no ledger was read at all, so no ledger projection is reported",
        )

    def test_is_committed_magic_agrees_with_and_without_a_content_accessor(self) -> None:
        for value in range(1, 11):
            self.assertTrue(M.is_committed_magic(value), value)
            self.assertTrue(M.is_committed_magic(value, magic_of), value)
        for value in (0, 11, 99, -5):
            self.assertFalse(M.is_committed_magic(value), value)
            self.assertFalse(M.is_committed_magic(value, magic_of), value)
        self.assertFalse(M.is_committed_magic(1.0, magic_of))
        self.assertFalse(M.is_committed_magic(1.0))


# ------------------------------------------------------- the ledger projection --
class LedgerProjectionTests(unittest.TestCase):
    """An unreadable save is reported, never defaulted to an empty one."""

    def test_a_mapping_ledger_reports_its_keys_and_count(self) -> None:
        projection = M.project_ledger({"1": 2, "9": 1})
        self.assertTrue(projection["ok"])
        self.assertEqual(projection["reason"], "")
        self.assertEqual(list(projection["keys"]), ["1", "9"])
        self.assertEqual(projection["count"], 2)

    def test_an_empty_mapping_is_readable_and_holds_no_keys(self) -> None:
        projection = M.project_ledger({})
        self.assertTrue(projection["ok"])
        self.assertEqual(projection["keys"], [])
        self.assertEqual(projection["count"], 0)

    def test_an_absent_or_non_mapping_ledger_is_refused(self) -> None:
        for raw in (None, [], "magics", 1, 0, True, {"1"}):
            with self.subTest(raw=raw):
                projection = M.project_ledger(raw)
                self.assertFalse(projection["ok"])
                self.assertEqual(projection["reason"], M.REASON_INVALID_LEDGER)
                self.assertEqual(projection["keys"], [])
                self.assertEqual(projection["count"], 0)

    def test_an_absent_counter_is_zero_charges_and_reports_absence(self) -> None:
        projection = M.counter_value({"1": 4}, "3")
        self.assertTrue(projection["ok"])
        self.assertEqual(projection["value"], 0)
        self.assertFalse(
            projection["present"],
            "absent and zero are the same recorded state (command.py:660, 672 "
            "write 0 for a key they have never seen) but they are told apart here "
            "because the else-arm divergence turns on the difference",
        )

    def test_a_present_counter_reports_its_value_and_presence(self) -> None:
        projection = M.counter_value({"1": 0}, "1")
        self.assertTrue(projection["ok"])
        self.assertEqual(projection["value"], 0)
        self.assertTrue(projection["present"])

    def test_an_ill_typed_or_negative_counter_is_refused_not_interpreted(self) -> None:
        for value in ("2", 2.0, None, [1], {"n": 1}, True, False, -1, -50):
            with self.subTest(value=value):
                projection = M.counter_value({"1": value}, "1")
                self.assertFalse(projection["ok"])
                self.assertEqual(projection["reason"], M.REASON_INVALID_COUNTER)

    def test_counter_value_refuses_a_non_mapping_ledger(self) -> None:
        for ledger in (None, [], "x", 1):
            with self.subTest(ledger=ledger):
                projection = M.counter_value(ledger, "1")
                self.assertFalse(projection["ok"])
                self.assertEqual(projection["reason"], M.REASON_INVALID_LEDGER)


# ------------------------------------------------------- the counter transition --
class CounterTransitionTests(unittest.TestCase):
    """Increment by one, cap at the literal, never decrease."""

    def test_the_transition_table_including_every_boundary(self) -> None:
        cases = [
            # before, after, change, capped
            (0, 1, 1, False),
            (1, 2, 1, False),
            (48, 49, 1, False),
            (49, 50, 1, True),
            (50, 50, 0, True),
        ]
        for before, after, change, capped in cases:
            with self.subTest(before=before):
                transition = M.derive_counter_transition(before)
                self.assertEqual(transition["before"], before)
                self.assertEqual(transition["after"], after)
                self.assertEqual(transition["change"], change)
                self.assertEqual(transition["capped"], capped)
                self.assertFalse(transition["decreased"])
                self.assertEqual(transition["cap"], M.COUNTER_CAP)

    def test_the_cap_row_is_an_unchanged_SUCCESS_not_a_refusal(self) -> None:
        # min(50, 51) == 50 for the use_magic arm too, so at the cap both the
        # legacy assignment and the derived transition are the cap.  This is the
        # one boundary where the two agree while staying still.
        transition = M.derive_counter_transition(M.COUNTER_CAP)
        self.assertEqual(transition["change"], 0)
        projection = M.project_magic({"1": M.COUNTER_CAP}, "use", 1, magic_of)
        self.assertTrue(projection["ok"])
        self.assertEqual(projection["change"], 0)
        self.assertEqual(projection["counter_after"], M.COUNTER_CAP)
        self.assertTrue(projection["capped"])

    def test_a_counter_above_the_cap_is_REFUSED_not_clamped_down(self) -> None:
        # min(50, 114) == 50, so the obvious formula applied to a recorded 113
        # returns exactly the charge-destroying decrease this line refuses.
        with self.assertRaises(M.EnvelopeError) as caught:
            M.derive_counter_transition(113)
        self.assertEqual(caught.exception.code, M.REASON_COUNTER_ABOVE_CAP)
        for before in (51, 63, 113, 10 ** 6):
            with self.subTest(before=before):
                with self.assertRaises(M.EnvelopeError) as caught:
                    M.derive_counter_transition(before)
                self.assertEqual(
                    caught.exception.code, M.REASON_COUNTER_ABOVE_CAP
                )

    def test_the_same_refusal_reaches_the_projection_with_no_write(self) -> None:
        projection = M.project_magic({"1": 113}, "use", 1, magic_of)
        self.assertFalse(projection["ok"])
        self.assertEqual(refusal_code(projection), M.REASON_COUNTER_ABOVE_CAP)
        self.assertIsNone(projection["counter_after"])
        self.assertEqual(projection["change"], 0)
        self.assertEqual(projection["counter_before"], 113)

    def test_a_non_integer_before_or_cap_is_refused(self) -> None:
        for before in ("2", 2.0, None, True, False, [1]):
            with self.subTest(before=before):
                with self.assertRaises(M.EnvelopeError) as caught:
                    M.derive_counter_transition(before)
                self.assertEqual(caught.exception.code, M.REASON_INVALID_COUNTER)
        for cap in ("50", 50.0, -1, True):
            with self.subTest(cap=cap):
                with self.assertRaises(M.EnvelopeError) as caught:
                    M.derive_counter_transition(0, cap)
                self.assertEqual(caught.exception.code, M.REASON_INVALID_PAYLOAD)

    def test_the_transition_takes_no_action_parameter_at_all(self) -> None:
        # There is deliberately no action argument, because the two legacy arms
        # disagree about the cap and there is no recorded rule for it.
        import inspect

        parameters = list(inspect.signature(M.derive_counter_transition).parameters)
        self.assertEqual(parameters, ["before", "cap"])
        self.assertNotIn("action", parameters)

    def test_no_transition_anywhere_ever_decreases(self) -> None:
        for before in range(0, M.COUNTER_CAP + 1):
            with self.subTest(before=before):
                transition = M.derive_counter_transition(before)
                self.assertGreaterEqual(transition["after"], before)
                self.assertEqual(
                    transition["change"],
                    0 if before == M.COUNTER_CAP else 1,
                )


# ---------------------------------------------------------- the validation order --
class ValidationOrderTests(unittest.TestCase):
    """Eight checks, then the write.  The content check sits above the state."""

    def test_the_order_is_the_eight_recorded_steps_in_order(self) -> None:
        self.assertEqual(
            [entry["step"] for entry in M.VALIDATION_ORDER], list(range(1, 9))
        )
        self.assertEqual(
            [entry["key"] for entry in M.VALIDATION_ORDER], EXPECTED_ORDER_KEYS
        )
        self.assertEqual(M.VALIDATION_ORDER_STEPS, 8)
        self.assertEqual(M.WRITE_STEP, 9)
        self.assertEqual(M.ORDERING_RULE["steps"], 8)
        self.assertEqual(M.ORDERING_RULE["write_step"], 9)

    def test_the_first_five_steps_read_no_player_state(self) -> None:
        for entry in M.VALIDATION_ORDER[:5]:
            with self.subTest(step=entry["step"]):
                self.assertFalse(
                    entry["reads_player_state"],
                    "step %d must resolve before the corpus is consulted"
                    % entry["step"],
                )

    def test_exactly_the_last_three_steps_read_player_state(self) -> None:
        readers = [entry["step"] for entry in M.VALIDATION_ORDER
                   if entry["reads_player_state"]]
        self.assertEqual(readers, [6, 7, 8])

    def test_the_content_check_sits_above_every_state_read(self) -> None:
        by_key = {entry["key"]: entry for entry in M.VALIDATION_ORDER}
        content_step = by_key["identity_in_committed_table"]["step"]
        for key in ("ledger_readable", "counter_readable", "transition_derived"):
            with self.subTest(key=key):
                self.assertLess(content_step, by_key[key]["step"])
        self.assertIn("never consults", M.ORDERING_RULE["content_before_state"])

    def test_the_projection_carries_the_whole_order_and_the_write_step(self) -> None:
        projection = M.project_magic({"1": 1}, "buy", 1, magic_of)
        self.assertEqual(
            projection["validation_order"], [
                dict(entry) for entry in M.VALIDATION_ORDER
            ]
        )
        self.assertEqual(projection["ordering_rule"], M.ORDERING_RULE)

    def test_every_refusal_resolves_above_the_write(self) -> None:
        # Every reason the projection can produce is produced with no write, and
        # the transition is absent from all of them.
        cases = [
            ({}, "nope", 1, M.REASON_INVALID_ACTION),
            ({}, "buy", None, M.REASON_MISSING_MAGIC_ID),
            ({}, "buy", 1.0, M.REASON_NON_CANONICAL_MAGIC_ID),
            ({}, "buy", True, M.REASON_INVALID_MAGIC_ID),
            ({}, "buy", 99, M.REASON_UNKNOWN_MAGIC_ID),
            (None, "buy", 1, M.REASON_INVALID_LEDGER),
            ("x", "buy", 1, M.REASON_INVALID_LEDGER),
            ({"1": "2"}, "buy", 1, M.REASON_INVALID_COUNTER),
            ({"1": -1}, "buy", 1, M.REASON_INVALID_COUNTER),
            ({"1": 113}, "buy", 1, M.REASON_COUNTER_ABOVE_CAP),
        ]
        for ledger, action, magic_id, expected in cases:
            with self.subTest(action=action, magic_id=magic_id, ledger=ledger):
                projection = M.project_magic(ledger, action, magic_id, magic_of)
                self.assertFalse(projection["ok"])
                self.assertEqual(refusal_code(projection), expected)
                self.assertIsNone(projection["counter_after"])

    def test_the_every_reason_list_is_exactly_the_nine_recorded_codes(self) -> None:
        # The route's own refusal list, mirrored here so a new reason cannot be
        # added to one side only.
        self.assertEqual(
            [
                M.REASON_INVALID_ACTION,
                M.REASON_CLIENT_DICTATED_COUNT,
                M.REASON_MISSING_MAGIC_ID,
                M.REASON_INVALID_MAGIC_ID,
                M.REASON_NON_CANONICAL_MAGIC_ID,
                M.REASON_UNKNOWN_MAGIC_ID,
                M.REASON_INVALID_LEDGER,
                M.REASON_INVALID_COUNTER,
                M.REASON_COUNTER_ABOVE_CAP,
            ],
            [
                "invalid_action", "client_dictated_count", "missing_magic_id",
                "invalid_magic_id", "non_canonical_magic_id", "unknown_magic_id",
                "invalid_ledger", "invalid_counter", "counter_above_cap",
            ],
        )


# -------------------------------------------------------- the eight resources --
class ResourceSetTests(unittest.TestCase):
    """Eight slots, and the set cannot quietly lose one."""

    def test_the_proof_set_is_exactly_the_eight_stored_slots(self) -> None:
        self.assertEqual(len(M.RESOURCE_NAMES), 8)
        self.assertEqual(M.RESOURCE_NAME_COUNT, 8)
        self.assertEqual(M.RESOURCE_VECTOR_SLOTS, 8)
        self.assertEqual(M.PROOF_RESOURCE_COUNT, M.RESOURCE_VECTOR_SLOTS)
        self.assertEqual(
            sorted(M.RESOURCE_NAMES),
            ["cash", "energy", "gold", "mana", "oil", "steel", "wood", "xp"],
        )
        self.assertEqual(len(set(M.RESOURCE_NAMES)), 8)

    def test_mana_and_energy_are_both_in_the_set(self) -> None:
        # `mana` is written by no magic branch and `energy` by no branch at all,
        # which is why both are proof slots rather than incidental ones.
        self.assertIn("mana", M.RESOURCE_NAMES)
        self.assertIn("energy", M.RESOURCE_NAMES)

    def test_the_set_is_eight_where_the_boot_accessor_exposes_seven(self) -> None:
        # The claim the fixture established was measured over eight slots; a
        # seven-slot proof would be narrower than the evidence it reproduces.
        accessor_slots = set(
            ["xp", "gold", "wood", "oil", "steel", "cash", "mana"]
        )
        self.assertEqual(len(accessor_slots), 7)
        self.assertEqual(
            set(M.RESOURCE_NAMES) - accessor_slots, {"energy"}
        )
        self.assertEqual(
            accessor_slots - set(M.RESOURCE_NAMES), set(),
            "every accessor slot is a proof slot, so the proof is a superset",
        )

    def test_the_derived_vector_is_neutral_across_all_eight_slots(self) -> None:
        vector = M.neutral_vector()
        self.assertEqual(vector, [0] * 8)
        self.assertEqual(len(vector), M.RESOURCE_VECTOR_SLOTS)
        self.assertEqual(M.validate_vector(vector), vector)

    def test_every_vector_shape_the_validator_cannot_vouch_for_is_refused(self) -> None:
        # SHAPE and TYPE only.  A non-zero vector is well formed, so the
        # validator accepts it -- the projection is what always derives the
        # neutral one, and turning this into a "non-zero is refused" rule would be
        # a second, weaker no-price claim pretending to be the first.
        for bad in (
            None, {}, "00000000", (0,) * 8, [0] * 7, [0] * 9, [],
            [0, 0, 0, 0, 0, 0, 0, "0"],
            [0, 0, 0, 0, 0, 0, 0, 0.0], [0, 0, 0, 0, 0, 0, 0, None],
            [0, 0, 0, 0, 0, 0, 0, True],
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(M.EnvelopeError) as caught:
                    M.validate_vector(bad)
                self.assertEqual(caught.exception.code, M.REASON_INVALID_VECTOR)

    def test_a_well_formed_non_zero_vector_is_accepted_but_never_produced(self) -> None:
        # The validator refuses a shape it cannot vouch for; it is not a price
        # check.  What the endpoint actually derives is asserted separately, by
        # the envelope suite, on the vector that goes to the dispatcher.
        self.assertEqual(M.validate_vector([1] * 8), [1] * 8)
        self.assertEqual(M.neutral_vector(), [0] * 8)


# ------------------------------------------------------------ the derived batch --
class DerivedEnvelopeTests(unittest.TestCase):
    """Six keys, one command, one argument, and no resource movement."""

    def test_the_envelope_has_exactly_the_six_legacy_batch_keys(self) -> None:
        envelope = M.build_envelope("buy", 1, ts=1700000000)
        self.assertEqual(
            sorted(envelope),
            # Sorted by code point, so 'tries' precedes 'ts': 'r' (114) is below
            # 's' (115).  The list is written in sorted order on purpose so the
            # assertion cannot be satisfied by an expectation that happens to
            # match the insertion order.
            [
                "accessToken", "commands", "first_number", "publishActions",
                "tries", "ts",
            ],
        )
        self.assertEqual(len(envelope), 6)

    def test_it_carries_exactly_one_command_and_that_is_the_action_s_own(self) -> None:
        for action in M.ACTIONS:
            with self.subTest(action=action):
                envelope = M.build_envelope(action, 3, ts=1700000000)
                self.assertEqual(len(envelope["commands"]), 1)
                batch = envelope["commands"][0]
                self.assertEqual(len(batch), 4)
                self.assertEqual(batch[0], 0)
                self.assertEqual(batch[1], M.ACTION_COMMAND[action])
                self.assertEqual(batch[2], [3])
                self.assertEqual(
                    batch[2], [int(3)],
                    "the argument is the committed integer identity, not its "
                    "client-sent form",
                )

    def test_the_resource_vector_is_the_neutral_eight_zero_one(self) -> None:
        envelope = M.build_envelope("use", 1, ts=1700000000)
        vector = envelope["commands"][0][3]
        self.assertEqual(vector, [0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(len(vector), 8)
        self.assertEqual(vector, M.neutral_vector())

    def test_the_envelope_is_deterministic_for_a_pinned_ts(self) -> None:
        first = M.build_envelope("buy", 7, ts=1700000000)
        second = M.build_envelope("buy", 7, ts=1700000000)
        self.assertEqual(first, second)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))

    def test_the_two_actions_produce_different_envelopes_and_only_in_the_command(
        self,
    ) -> None:
        bought = M.build_envelope("buy", 7, ts=1700000000)
        used = M.build_envelope("use", 7, ts=1700000000)
        self.assertNotEqual(bought, used)
        differing = [
            key for key in sorted(bought) if bought[key] != used[key]
        ]
        self.assertEqual(differing, ["commands"])

    def test_a_closed_action_is_required_and_a_non_canonical_identity_refused(self) -> None:
        for action in (None, "", "BUY", M.BUY_COMMAND, 1, True, ["buy"]):
            with self.subTest(action=action):
                with self.assertRaises(M.EnvelopeError) as caught:
                    M.build_envelope(action, 1, ts=1700000000)
                self.assertEqual(caught.exception.code, M.REASON_INVALID_ACTION)
        for magic_id in (1.0, "1", True, None):
            with self.subTest(magic_id=magic_id):
                with self.assertRaises(M.EnvelopeError) as caught:
                    M.build_envelope("buy", magic_id, ts=1700000000)
                self.assertEqual(
                    caught.exception.code, M.REASON_NON_CANONICAL_MAGIC_ID
                )

    def test_the_timestamp_is_validated(self) -> None:
        for ts in ("1700000000", -1, True, 1.0):
            with self.subTest(ts=ts):
                with self.assertRaises(M.EnvelopeError) as caught:
                    M.build_envelope("buy", 1, ts=ts)
                self.assertEqual(caught.exception.code, M.REASON_INVALID_TIMESTAMP)
        # An OMITTED or explicitly None ts is derived from the clock, so neither
        # is a refusal: `None` is the documented "no stamp supplied" sentinel and
        # treating it as a malformed timestamp would be a refusal of a request
        # shape the function itself offers.
        self.assertGreaterEqual(M.build_envelope("buy", 1)["ts"], 0)
        self.assertGreaterEqual(M.build_envelope("buy", 1, ts=None)["ts"], 0)

    def test_the_envelope_is_json_serialisable_with_no_python_specifics(self) -> None:
        envelope = M.build_envelope("buy", 1, ts=1700000000)
        self.assertEqual(json.loads(json.dumps(envelope)), envelope)


# ------------------------------------------------ the re-derived source inventory --
class SourceReDerivationTests(unittest.TestCase):
    """Every recorded source claim is re-read from the committed bytes."""

    def test_the_two_branches_are_located_at_their_recorded_lines(self) -> None:
        inv = M.derive_field_inventory()
        self.assertTrue(inv["ok"])
        located = {entry["name"]: entry for entry in inv["branches"]}
        self.assertTrue(located[M.BUY_COMMAND]["found"])
        self.assertTrue(located[M.USE_COMMAND]["found"])
        self.assertEqual(located[M.BUY_COMMAND]["start"], 652)
        self.assertEqual(located[M.USE_COMMAND]["start"], 664)
        self.assertLess(
            located[M.BUY_COMMAND]["start"], located[M.USE_COMMAND]["start"],
            "buy_magic is committed above use_magic, four lines of body apart",
        )

    def test_both_operators_are_re_derived_not_transcribed(self) -> None:
        inv = M.derive_field_inventory()
        self.assertEqual(inv["counter_operators"][M.BUY_COMMAND], "+=")
        self.assertEqual(inv["counter_operators"][M.USE_COMMAND], "=")
        self.assertNotEqual(
            inv["counter_operators"][M.BUY_COMMAND],
            inv["counter_operators"][M.USE_COMMAND],
            "the two arms disagree, which is the finding",
        )

    def test_the_cap_is_a_literal_at_two_named_lines(self) -> None:
        self.assertEqual(M.COUNTER_CAP, 50)
        self.assertEqual(M.CAP_SOURCE_LINES, (658, 670))
        inv = M.derive_field_inventory()
        self.assertEqual(inv["cap_literals"], list(M.CAP_SOURCE_LINES))
        lines = command_lines()
        for line_number in M.CAP_SOURCE_LINES:
            with self.subTest(line=line_number):
                text = lines[line_number - 1]
                self.assertIn("min(50,", text)
                self.assertIn('magics[str(magic_id)]', text)

    def test_the_cap_line_references_no_committed_content(self) -> None:
        # This is what makes the rejected derivation below a rejection rather
        # than a preference: the literal is the whole of it.
        lines = command_lines()
        for line_number in M.CAP_SOURCE_LINES:
            with self.subTest(line=line_number):
                text = lines[line_number - 1]
                for forbidden in ("config", "content", "main.json", "items",
                                  "magics_table", "get_magic"):
                    self.assertNotIn(forbidden, text)

    def test_the_rejected_cap_derivation_is_retained_with_both_candidates(self) -> None:
        rejected = M.REJECTED_CAP_DERIVATION
        self.assertIn("magics content", rejected["rejected"])
        self.assertEqual(len(rejected["candidates"]), 2)
        for candidate in rejected["candidates"]:
            with self.subTest(candidate=candidate["magic_name"]):
                self.assertEqual(candidate["value"], 50)
                self.assertEqual(candidate["magic_id"], magic_of(candidate["magic_id"])["id"])
        # And the coincidence is real: 50 really does occur in the committed rows,
        # which is why the rejected alternative had to be written down.
        values = [
            row[candidate["field"]]
            for candidate in rejected["candidates"]
            for row in [magic_of(candidate["magic_id"])]
        ]
        self.assertEqual(values, [50, 50])

    def test_the_dispatcher_count_is_measured_and_cross_checked(self) -> None:
        inv = M.derive_field_inventory()
        self.assertEqual(inv["dispatcher_branches"], 63)
        self.assertEqual(inv["catalog_command_branches"], 63)
        self.assertTrue(M.branch_count_agrees_with_catalog(inv))
        self.assertTrue(M.branch_count_agrees_with_catalog())
        # The character class must include digits, or push_queue_unit2 is
        # invisible and the measurement reads 62.  Asserted by name so the class
        # is not "simplified" back.
        self.assertIn("push_queue_unit2", inv["branch_names"])
        self.assertEqual(inv["branch_names"].count("push_queue_unit2"), 1)
        self.assertEqual(len(inv["branch_names"]), len(set(inv["branch_names"])))

    def test_the_census_spans_all_eleven_legacy_root_modules(self) -> None:
        inv = M.derive_field_inventory()
        self.assertEqual(inv["damage_census_module_count"], 11)
        self.assertEqual(M.LEGACY_MODULE_COUNT, 11)
        self.assertEqual(len(M.LEGACY_MODULES), 11)
        self.assertEqual(sorted(inv["damage_census_scope"]), sorted(M.LEGACY_MODULES))
        for module in M.LEGACY_MODULES:
            with self.subTest(module=module):
                self.assertTrue((REPO / module).is_file(), module)

    def test_all_seven_damage_fields_have_zero_consumers(self) -> None:
        inv = M.derive_field_inventory()
        self.assertEqual(
            sorted(inv["damage_census"]), sorted(M.ZERO_CONSUMER_DAMAGE_FIELDS)
        )
        self.assertEqual(len(M.ZERO_CONSUMER_DAMAGE_FIELDS), 7)
        for field, counts in sorted(inv["damage_census"].items()):
            with self.subTest(field=field):
                for rule in ESTABLISHING_RULES:
                    self.assertEqual(
                        counts[rule], 0,
                        "%s has %d %s consumer(s), which would mean the "
                        "preserved server does read it"
                        % (field, counts[rule], rule),
                    )

    def test_six_of_the_seven_are_zero_under_EVERY_rule(self) -> None:
        inv = M.derive_field_inventory()
        for field, counts in sorted(inv["damage_census"].items()):
            if field == SUBSTRING_CARRYING_FIELD:
                continue
            with self.subTest(field=field):
                for rule in M.COUNTING_RULES:
                    self.assertEqual(counts[rule], 0)

    def test_the_census_is_NOT_vacuous(self) -> None:
        # A scanner that found nothing anywhere would pass the tests above.  This
        # requires the opposite shape: a field with LARGE substring counts and
        # zero tokens, which is exactly what `attack` really looks like.
        inv = M.derive_field_inventory()
        attack = inv["damage_census"][SUBSTRING_CARRYING_FIELD]
        self.assertGreater(attack["whole"], 0)
        self.assertGreater(attack["distinct_line"], 0)
        self.assertGreater(attack["code_only"], 0)
        self.assertGreater(attack["code_distinct_line"], 0)
        self.assertEqual(attack["token"], 0)
        self.assertEqual(attack["quoted"], 0)
        self.assertEqual(len(M.COUNTING_RULES), 6)
        # Every rule reports the same six keys, so no rule is silently missing
        # from the projection.
        for counts in inv["damage_census"].values():
            self.assertEqual(sorted(counts), sorted(M.COUNTING_RULES))
        self.assertEqual(sorted(SUBSTRING_RULES + ESTABLISHING_RULES),
                         sorted(M.COUNTING_RULES))

    def test_every_attack_occurrence_sits_inside_a_longer_identifier(self) -> None:
        # The claim that makes the substring counts artifacts rather than
        # consumers: walk the committed bytes and show each code-only match is
        # part of a bigger token.  A bare `attack` would be a consumer.
        census = M.legacy_census_text()
        stripped = M.code_only(census)
        identifier = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
        bare = [
            match.group(0)
            for match in identifier.finditer(stripped)
            if match.group(0).lower() == "attack"
        ]
        self.assertEqual(
            bare, [],
            "a standalone `attack` identifier exists, which would mean the "
            "preserved server reads the field",
        )
        # And the longer identifiers that carry it really are in the source.
        for longer in ("end_attack", "attacker", "tsAttacksReset"):
            with self.subTest(identifier=longer):
                self.assertIn(longer, census)

    def test_the_lexer_strips_comments_and_literals_without_desynchronising(self) -> None:
        # The apostrophe inside the double-quoted string is the fault an earlier
        # guard in this project actually had, so it is the input here.
        source = (
            "value = 1  # a comment with attack inside\n"
            'text = "it\'s not a string delimiter, and damage lives here"\n'
            "other = 'single quoted with damage'\n"
            "bare = attack\n"
        )
        stripped = M.code_only(source).split("\n")
        self.assertIn("bare = attack", stripped[3])
        self.assertNotIn("attack", stripped[0])
        self.assertNotIn("damage", stripped[1])
        self.assertNotIn("damage", stripped[2])
        # An escaped quote does not end the literal early.
        self.assertEqual(M.code_only('a = "x\\"y damage"') .strip(), "a =")

    def test_the_ledger_shape_counts_are_four_six_two_and_zero_reads(self) -> None:
        inv = M.derive_field_inventory()
        self.assertEqual(inv["ledger_write_sites"], 4)
        self.assertEqual(inv["ledger_membership_tests"], 2)
        self.assertEqual(inv["ledger_bindings"], 2)
        self.assertEqual(inv["ledger_read_sites"], 0)
        recorded = M.LEDGER_HAS_NO_READERS
        self.assertEqual(recorded["ledger_write_sites"], 4)
        self.assertEqual(recorded["counter_subscript_occurrences"], 6)
        self.assertEqual(recorded["membership_tests"], 2)
        self.assertEqual(recorded["local_bindings"], 2)
        self.assertEqual(recorded["read_sites"], 0)
        self.assertEqual(recorded["migration_sites"], 4)
        self.assertIn("version.py", recorded["migration_location"])

    def test_there_is_no_legacy_accessor_from_a_magic_id_to_its_row(self) -> None:
        # Measured, not asserted from the investigation: get_game_config.py
        # indexes items, goals, inventory_items and the rest, and never magics.
        source = config_source()
        self.assertEqual(len(re.findall("magic", source, re.IGNORECASE)), 0)
        self.assertEqual(len(re.findall(r"\bmagic\b", source, re.IGNORECASE)), 0)
        self.assertEqual(
            len(re.findall("magic", M.code_only(source), re.IGNORECASE)), 0
        )
        # The same index shape DOES exist for other domains, so the zero above is
        # a fact about magics and not about an empty file.
        self.assertGreater(len(re.findall("_from_id", source)), 0)

    def test_the_inventory_accessor_returns_the_measurement_whole(self) -> None:
        inv = M.inventory()
        self.assertEqual(inv["source"], "command.py")
        self.assertEqual(inv["notes"], M.derive_field_inventory()["notes"])
        self.assertIn("push_queue_unit2", inv["notes"])


class ConsumerRuleConsistencyTests(unittest.TestCase):
    """A recorded INCONSISTENCY inside the derivation -- now REPAIRED.

    ``magic_envelope`` stated the rule twice and the two statements disagreed:

    * ``COUNTING_RULES`` documents ``whole`` and ``code_only`` as **substring**
      counts that "cannot establish a consumer on their own", and the module
      docstring says "Only ``token`` and ``quoted`` can establish a consumer";
    * ``CONSUMER_RULES`` nevertheless named **four** rules, the two substring ones
      included.

    The measurement settled which statement is right, and it is the first one:
    ``attack`` scores **30** code-only occurrences and **0** tokens.  Reading
    ``CONSUMER_RULES`` at face value would therefore have reported that the
    preserved server has thirty consumers of ``attack``, which is false -- every
    one of the thirty sits inside ``end_attack``, ``attacker``, or
    ``tsAttacksReset``.

    **The declaring tuple now declares the stricter pair this suite named all
    along**, so the two statements agree.  This class existed to make the repair a
    visible change to an assertion rather than a silent edit to a tuple, and the
    assertions below are that repair: they were failures the moment the module
    changed.  The lesson generalises past this line -- a measurement module that
    states a rule in two places will eventually disagree with itself, and the
    cheap guard is to pin both statements from the outside.
    """

    def test_the_module_declares_exactly_the_two_establishing_rules(self) -> None:
        # This suite already carried `ESTABLISHING_RULES = ("token", "quoted")`
        # while the module declared FOUR -- the two establishing rules plus two
        # code-only substring counts that cannot establish a consumer.  The two
        # rule sets disagreed about what counts as evidence, and a consumer census
        # is the entire point of the measurement, so the module now declares the
        # stricter pair this suite named all along.
        self.assertEqual(list(M.CONSUMER_RULES), list(ESTABLISHING_RULES))
        self.assertEqual(len(M.CONSUMER_RULES), 2)
        # And the block that reports the rules agrees with the tuple, which it did
        # not before -- that disagreement was the defect.
        self.assertEqual(M.NO_DAMAGE["consumer_rules"], list(M.CONSUMER_RULES))

    def test_no_substring_rule_is_declared_able_to_establish_a_consumer(
        self,
    ) -> None:
        # The guard is a SUBSTRING check rather than a membership check, so a
        # substring count can never be read as a consumer: for `attack` these
        # rules report non-zero, and every one of those occurrences sits inside a
        # longer identifier (`end_attack`, `attacker`, `tsAttacksReset`).
        inv = M.derive_field_inventory()
        for rule in SUBSTRING_RULES:
            with self.subTest(rule=rule):
                self.assertNotIn(
                    rule, M.CONSUMER_RULES,
                    "%r is a substring count; listing it as a consumer rule would "
                    "let a substring artifact establish a consumer" % rule,
                )
        for rule in ("code_only", "code_distinct_line"):
            with self.subTest(substring_rule=rule):
                self.assertGreater(
                    inv["damage_census"][SUBSTRING_CARRYING_FIELD][rule], 0,
                    "if this rule now reports zero for the one field that "
                    "carries substring occurrences, the exclusion is no longer "
                    "load-bearing and this class should say so",
                )

    def test_the_two_establishing_rules_are_zero_for_every_field(self) -> None:
        inv = M.derive_field_inventory()
        for rule in ESTABLISHING_RULES:
            with self.subTest(rule=rule):
                self.assertIn(rule, M.CONSUMER_RULES)
                for field, counts in sorted(inv["damage_census"].items()):
                    self.assertEqual(counts[rule], 0, field)

    def test_the_substring_carrying_field_is_the_only_one(self) -> None:
        carrying = [
            field for field, counts in sorted(
                M.derive_field_inventory()["damage_census"].items()
            )
            if any(counts[rule] for rule in SUBSTRING_RULES)
        ]
        self.assertEqual(carrying, [SUBSTRING_CARRYING_FIELD])

    def test_the_conflicting_docstrings_both_exist_in_the_module(self) -> None:
        # Recorded so the fix, when it happens, changes something this class can
        # see.  `magic_envelope`'s NO_DAMAGE block carries the same six rules
        # under a key of its own, and it is the two-rule claim that agrees with
        # the measurement.
        self.assertEqual(M.NO_DAMAGE["counting_rules"], list(M.COUNTING_RULES))
        self.assertEqual(M.NO_DAMAGE["consumer_rules"], list(M.CONSUMER_RULES))
        self.assertEqual(sorted(M.NO_DAMAGE["consumer_rules"]), sorted(M.CONSUMER_RULES))


# ------------------------------------------------------ the committed magics --
class CommittedContentTests(unittest.TestCase):
    """The ten committed magics, measured from the committed bytes."""

    def test_the_committed_table_is_a_list_of_ten_rows(self) -> None:
        rows = committed_magics()
        self.assertIsInstance(rows, list)
        self.assertEqual(len(rows), M.COMMITTED_MAGIC_COUNT)
        self.assertEqual(M.COMMITTED_MAGIC_COUNT, 10)

    def test_the_ids_run_one_to_ten_with_no_duplicate(self) -> None:
        ids = [row["id"] for row in committed_magics()]
        self.assertEqual(ids, list(range(1, 11)))
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(min(ids), M.COMMITTED_MAGIC_ID_MIN)
        self.assertEqual(max(ids), M.COMMITTED_MAGIC_ID_MAX)
        self.assertEqual((M.COMMITTED_MAGIC_ID_MIN, M.COMMITTED_MAGIC_ID_MAX), (1, 10))

    def test_the_normalized_package_agrees_with_the_committed_config(self) -> None:
        normalized = json.loads(NORMALIZED_MAGICS.read_text(encoding="utf-8"))
        self.assertEqual(len(normalized), M.COMMITTED_MAGIC_COUNT)
        self.assertEqual(
            [row["legacy_id"] for row in normalized],
            [str(row["id"]) for row in committed_magics()],
            "the normalized package preserves the legacy ids in the same order",
        )
        for row in normalized:
            with self.subTest(legacy_id=row["legacy_id"]):
                self.assertEqual(row["id"], int(row["legacy_id"]))

    def test_every_row_carries_the_reported_fields_and_no_damage_amount(self) -> None:
        for row in committed_magics():
            with self.subTest(magic=row["name"]):
                for field in M.REPORTED_FIELDS:
                    self.assertIn(field, row)
                # No multiplier, magnitude, radius or duration anywhere.
                for absent in ("damage", "multiplier", "factor", "magnitude",
                               "radius", "duration", "amount"):
                    self.assertNotIn(absent, row)
                self.assertTrue(row["description"])

    def test_the_entry_whose_description_promises_an_effect_is_named(self) -> None:
        entry = M.ABSENT_MAGNITUDE_ENTRY
        row = magic_of(entry["magic_id"])
        self.assertIsNotNone(row)
        self.assertEqual(row["name"], entry["magic_name"])
        self.assertEqual(row["description"], entry["description"])
        for field, value in sorted(entry["committed_numbers"].items()):
            self.assertEqual(row[field], value)
        self.assertIn("No delivered code", entry["rule"])

    def test_the_committed_seed_carries_the_only_non_empty_ledger(self) -> None:
        village = json.loads(SEED_VILLAGE.read_text(encoding="utf-8"))
        ledger = village["privateState"][M.LEDGER_KEY]
        self.assertEqual(list(ledger), ["10", "9", "1", "2", "4"])
        self.assertEqual(len(ledger), 5)
        self.assertEqual(ledger["1"], 2)
        self.assertEqual(village["privateState"]["mana"], 15)
        self.assertEqual(village["privateState"]["energy"], 50)
        self.assertEqual(str(village["playerInfo"]["pid"]), "Neutral")


# --------------------------------------------------------- the recorded absences --
class RecordedAbsenceTests(unittest.TestCase):
    """What the line refuses to deliver is asserted, not merely documented."""

    def test_the_seven_divergences_are_pinned_by_id(self) -> None:
        ids = [entry["id"] for entry in M.DIVERGENCES]
        self.assertEqual(sorted(ids), EXPECTED_DIVERGENCE_IDS)
        self.assertEqual(M.DIVERGENCE_COUNT, 7)
        self.assertEqual(len(M.DIVERGENCES), M.DIVERGENCE_COUNT)
        for entry in M.divergences():
            with self.subTest(divergence=entry["id"]):
                for key in ("id", "legacy_behaviour", "service_behaviour",
                            "classification", "authority"):
                    self.assertIn(key, entry)
                self.assertTrue(entry["legacy_behaviour"])
                self.assertTrue(entry["service_behaviour"])

    def test_the_two_refused_arms_carry_their_executed_evidence(self) -> None:
        unbounded = M.LEGACY_UNBOUNDED_ARM
        self.assertEqual(unbounded["command"], M.BUY_COMMAND)
        self.assertEqual(unbounded["operator"], "+=")
        self.assertEqual(unbounded["source_lines"], [658])
        self.assertTrue(unbounded["executed"]["crossed_cap"])
        self.assertEqual(unbounded["executed"]["start"], 2)
        self.assertEqual(unbounded["executed"]["sequence"], [3, 7, 15, 31, 63, 113])
        self.assertIn("REFUSED", unbounded["verdict"])

        decreasing = M.LEGACY_DECREASING_ARM
        self.assertEqual(decreasing["command"], M.USE_COMMAND)
        self.assertEqual(decreasing["operator"], "=")
        self.assertEqual(decreasing["source_lines"], [670])
        self.assertEqual(decreasing["executed"]["before"], 113)
        self.assertEqual(decreasing["executed"]["after"], 50)
        self.assertEqual(decreasing["executed"]["charges_destroyed"], 63)
        self.assertEqual(decreasing["recorded_message"], "Used magic spell")
        self.assertIn("REFUSED", decreasing["verdict"])

    def test_the_absent_key_divergence_is_present_and_states_both_numbers(self) -> None:
        entry = [
            item
            for item in M.DIVERGENCES
            if item["id"] == "absent_key_writes_zero_not_one"
        ]
        self.assertEqual(len(entry), 1)
        body = entry[0]
        self.assertIn("ZERO", body["legacy_behaviour"])
        self.assertIn("ONE", body["service_behaviour"])
        self.assertIn("note", body)

    def test_the_cap_uniformity_is_a_decision_and_not_a_reproduction(self) -> None:
        uniformity = M.CAP_UNIFORMITY
        self.assertIn("disagree", uniformity["legacy"])
        self.assertIn("uniformly", uniformity["service"])
        self.assertIn("counter_above_cap", uniformity["above_cap"])
        self.assertIn("recorded divergence", uniformity["verdict"])

    def test_no_damage_is_a_structural_claim_with_a_re_measurable_census(self) -> None:
        self.assertIn("No damage is resolved", M.NO_DAMAGE["verdict"])
        self.assertEqual(
            M.NO_DAMAGE["no_consumer_fields"], list(M.ZERO_CONSUMER_DAMAGE_FIELDS)
        )
        self.assertEqual(M.NO_DAMAGE["counting_rules"], list(M.COUNTING_RULES))
        self.assertEqual(M.NO_DAMAGE["consumer_rules"], list(M.CONSUMER_RULES))
        storage = M.NO_DAMAGE["no_storage_evidence"]
        self.assertEqual(storage["row_slots"], 8)
        self.assertTrue(storage["row_length_is_constant"])
        self.assertEqual(storage["private_state_damage_shaped_keys"], 0)
        self.assertIsNone(M.NO_DAMAGE["committed_content_has_no_amount"]["field"])
        self.assertIn("structural_guard", M.NO_DAMAGE)

    def test_the_storage_evidence_is_measured_against_the_committed_saves(self) -> None:
        # Measured here rather than trusted from the record, because "there is
        # nowhere to STORE damage" is the load-bearing half of the refusal.
        pattern = re.compile(r"hp|health|damage|dmg|armor|shield|life|wound", re.I)
        widths = set()
        shaped = 0
        documents = 0
        for root in ("villages", "tests/saves"):
            directory = REPO / root
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.json")):
                try:
                    document = json.loads(path.read_text(encoding="utf-8"))
                except ValueError:
                    continue
                if not isinstance(document, dict):
                    continue
                maps = document.get("maps")
                if not isinstance(maps, list) or not maps:
                    continue
                items = maps[0].get("items")
                if not isinstance(items, dict):
                    continue
                documents += 1
                for row in items.values():
                    if isinstance(row, list):
                        widths.add(len(row))
                private = document.get("privateState")
                if isinstance(private, dict):
                    shaped += len([key for key in private if pattern.search(key)])
        self.assertGreaterEqual(documents, 10)
        self.assertEqual(widths, {8})
        self.assertEqual(shaped, 0)

    def test_the_reported_damage_vocabulary_is_reported_and_never_used(self) -> None:
        vocabulary = M.reported_vocabulary()
        self.assertEqual(
            [token["name"] for token in vocabulary["cost_tokens"]],
            [M.COST_DAMAGE_SELF["name"], M.COST_DAMAGE_ENEMY["name"]],
        )
        self.assertEqual(vocabulary["cost_tokens"][0]["value"], "ds")
        self.assertEqual(vocabulary["cost_tokens"][1]["value"], "de")
        self.assertEqual(
            [entry["name"] for entry in vocabulary["reset_instants"]],
            ["tsAttacksReset", "tsSpyingsReset"],
        )
        self.assertEqual(vocabulary["no_op_branch"]["command"], M.NO_OP_COMMAND)
        self.assertIn("None of it is read", vocabulary["rule"])
        # The combat-named MISSION_* types belong to godot-mission-vocabulary.
        for name in vocabulary["mission_types_owned_elsewhere"]:
            with self.subTest(mission=name):
                self.assertIn("MISSION_", name)
        # And the two reset instants really are single write-only sites, which is
        # what the report claims about them.
        for entry in vocabulary["reset_instants"]:
            with self.subTest(name=entry["name"]):
                self.assertEqual(entry["readers"], 0)
                self.assertEqual(entry["fate"], "write_only")

    def test_no_cost_and_no_reward_are_measured_not_asserted(self) -> None:
        measured = M.NO_COST_OR_REWARD["measured"]
        self.assertEqual(measured["transactions"], 12)
        self.assertEqual(measured["resource_slots_compared"], 8)
        self.assertEqual(measured["resource_names"], list(M.RESOURCE_NAMES))
        self.assertEqual(measured["slots_that_moved"], 0)
        self.assertEqual(measured["mana_before"], 15)
        self.assertEqual(measured["mana_after"], 15)

    def test_no_magic_effect_is_applied_to_any_unit(self) -> None:
        self.assertIn("no magic effect", M.NO_MAGIC_EFFECT["verdict"])
        self.assertIn("no placement row", M.NO_MAGIC_EFFECT["reason"])

    def test_the_provenance_names_the_line_and_its_corpus(self) -> None:
        provenance = M.PROVENANCE
        self.assertEqual(provenance["capability"], "godot-damage")
        self.assertEqual(provenance["milestone"], "M10")
        self.assertEqual(provenance["corpus"], "villages/Neutral.json")
        self.assertEqual(provenance["executed_transactions"], 12)
        self.assertEqual(provenance["committed_magics_driven"], 1)
        self.assertEqual(
            provenance["committed_magics_total"], M.COMMITTED_MAGIC_COUNT
        )
        self.assertEqual(provenance["legacy_branches"], list(M.MAGIC_COMMANDS))
        self.assertIn("damage", provenance["primary_finding"])

    def test_the_non_claims_are_listed_and_include_the_central_ones(self) -> None:
        claims = M.non_claims()
        self.assertEqual(claims, M.NON_CLAIMS)
        self.assertEqual(len(claims), len(M.NON_CLAIMS))
        joined = " ".join(claims)
        for required in (
            "No damage is resolved",
            "No price is charged",
            "No magic effect",
            "The cap is the recorded literal",
            "never parity",
        ):
            with self.subTest(claim=required):
                self.assertIn(required, joined)


# --------------------------------------------------------- the anti-invention --
class AntiInventionTests(unittest.TestCase):
    """Nothing here may gain a helper that computes a combat outcome."""

    def test_the_whole_function_inventory_is_pinned(self) -> None:
        self.assertEqual(module_functions(), EXPECTED_MODULE_FUNCTIONS)
        self.assertEqual(
            len(module_functions()),
            len(set(module_functions())),
            "a duplicate definition would shadow an earlier one silently",
        )

    def test_no_identifier_names_a_damage_or_combat_rule(self) -> None:
        names = module_code_identifiers()
        exempt = {name for name in names if name in FORBIDDEN_HELPER_EXEMPT}
        self.assertTrue(
            exempt,
            "the exemption list must still match something, or it is dead",
        )
        for name in names:
            if name in FORBIDDEN_HELPER_EXEMPT:
                continue
            folded = name.lower()
            for fragment in FORBIDDEN_HELPER_FRAGMENTS:
                with self.subTest(identifier=name, fragment=fragment):
                    self.assertNotIn(
                        fragment, folded,
                        "%r would be an invented rule" % name,
                    )

    def test_the_exemption_list_is_exactly_what_the_module_declares(self) -> None:
        # Not "close enough": an exemption naming something that no longer exists
        # is a hole left open for the next helper.
        names = set(module_code_identifiers())
        missing = [
            name for name in FORBIDDEN_HELPER_EXEMPT if name not in names
        ]
        self.assertEqual(
            missing, [],
            "these exemptions name identifiers the module no longer declares: %r"
            % missing,
        )

    def test_no_function_takes_an_action_parameter_it_could_branch_on(self) -> None:
        # The single mechanism by which a defect could re-enter is a helper that
        # asks which action it is serving and behaves differently for each.
        for name in ("derive_counter_transition", "counter_value",
                     "ledger_key_for", "is_canonical_magic_key"):
            with self.subTest(function=name):
                import inspect

                parameters = list(inspect.signature(getattr(M, name)).parameters)
                self.assertNotIn("action", parameters)

    def test_the_module_declares_no_content_accessor_of_its_own(self) -> None:
        # Content is read through a PARAMETER, so a delivered helper could not
        # resolve a magic id against a table the endpoint chose.
        import inspect

        parameters = list(inspect.signature(M.is_committed_magic).parameters)
        self.assertIn("magic_of", parameters)
        self.assertEqual(parameters, ["magic_id", "magic_of"])
        self.assertEqual(
            list(inspect.signature(M.project_magic).parameters),
            ["ledger", "action", "magic_id", "magic_of"],
        )