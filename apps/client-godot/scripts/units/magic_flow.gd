extends RefCounted
## Typed, read-only projection of the M10 line-3 magic-counter surface
## (OpenSpec `godot-damage`: "A magic counter transition is derived server-side
## from a validated identity, and the delivered surface is a counter rather than
## damage" / "An identity outside the committed magic table is refused" / "The
## two legacy counter asymmetries are refused rather than reproduced" / "Every
## refusal resolves before any ledger write" / "No price is charged" / "The
## counter cap is the recorded literal it is" / "The committed magic content is
## reported verbatim" / "The damage vocabulary that does exist is reported and
## never used", design D1-D10).
##
## ## What this module is, and what it deliberately is NOT
##
## The preserved server **resolves no damage**, and this module is named for
## that refusal rather than for a capability it does not have. The refusal is
## established two independent ways by the committed investigation
## (`docs/legacy-m10-damage.md`): no committed damage field is read by anything,
## and there is **nowhere in a committed save row to store a hit point**.
##
## What IS delivered is the one combat-effect surface the preserved server
## actually maintains: `privateState["magics"]`, a string-keyed counter ledger
## written by two adjacent dispatcher branches and **read by nothing**.
##
## ## Both legacy arms are REFUSED, never reproduced (design D3)
##
## The two branches are four lines apart and are **not** interchangeable:
##
##     command.py:658   magics[str(magic_id)] += min(50, magics[str(magic_id)] + 1)
##     command.py:670   magics[str(magic_id)] = min(50, magics[str(magic_id)] + 1)
##
## Executed against `villages/Neutral.json`, the additive arm climbed
## `2 -> 3 -> 7 -> 15 -> 31 -> 63 -> 113` and the assigning arm then turned
## `113` into `50`, destroying 63 player-owned charges on a command whose own
## recorded message claims the opposite. Reproducing either would ship a defect
## as parity, so `derive_counter_transition()` increments by one under the
## recorded cap for **both** actions and **never reduces**.
##
## ## The cap is a LITERAL, and the rejected derivation is retained (design D6)
##
## `min(50, ...)` is a bare literal at exactly two source lines. The value 50
## also occurs among the committed magics values, as `AirStrike.cash` and
## `Shortcircuit.level`, which is precisely the coincidence that gets mistaken
## for provenance. `REJECTED_CAP_DERIVATION` records the rejected alternative so
## a later reader cannot mistake one for the other, and **nothing here reads a
## committed value to obtain the cap**.
##
## ## The identity is validated, which the legacy server does not (design D4)
##
## The legacy branch validates nothing and keys the ledger on the string form of
## the identity, so it accepted `99` and created the distinct key `"1.0"` for a
## float identity. Both are refused here and both differences are recorded as
## divergences.
##
## ## The damage refusal is STRUCTURAL (design D7)
##
## `ABSENT_HELPERS` names the derivations this line must never grow, the
## **whole** static-function inventory is pinned in `STATIC_FUNCTIONS`, the
## arithmetic figures are counted rather than asserted, and the module carries no
## identifier named after the damage vocabulary it reports. A guard that can
## fail is stronger than prose that cannot, and the hermetic suite proves this
## one by injecting an offending helper.
##
## ## Content is reported verbatim and nothing is derived (design D8)
##
## The ten committed magics are projected with their recorded `mana`, `level`,
## `gold`, `cash`, and `target` fields exactly as normalized, through a
## caller-supplied content accessor so this module never resolves an entry
## itself. One committed description promises an effect whose magnitude **was
## never committed**; the absence is named in `ABSENT_MAGNITUDE_ENTRY` and no
## code here synthesizes one.
##
## ## Purity
##
## This module holds no node, no clock, no request and no transport, and writes
## nothing. It reads committed bytes for the three derivations that must not be
## transcribed (the branch inventory, the damage census, the corpus shape) and
## reads committed content only through a caller-supplied callable.
##
## The wire section at the foot of this file **builds a request body and parses
## an answer**, which is dictionary work and no more: it performs no I/O, opens
## no socket, and reaches no endpoint. The transport belongs to
## `scripts/gameapi/legacy_v0_api.gd`, exactly as it does for every other line.

const Paths = preload("res://scripts/package_paths.gd")
const BootData = preload("res://scripts/gameapi/boot_data.gd")

# ---------------------------------------------------------------------------
# The two dispatcher branches
# ---------------------------------------------------------------------------

## The legacy source the branch inventory and the damage census are re-derived
## from, repository-relative.
const LEGACY_SOURCE_RELATIVE := "command.py"

const BUY_COMMAND := "buy_magic"
const USE_COMMAND := "use_magic"

## The two branches this line owns, in committed source order.
const MAGIC_COMMANDS := [BUY_COMMAND, USE_COMMAND]

## The single branch whose whole body is a recorded message. Its entire body is
## one print whose own trailing comment reads "Nothing needs to be done here
## :)". It is recorded because it is the third member of the same buy/use
## vocabulary family, and it is **not** delivered: an empty branch maintains no
## state to verify.
const NO_OP_COMMAND := "buy_mana_new"
const NO_OP_LINE := 650
const NO_OP_NOTE := ("A named dispatcher branch whose entire body is one print, "
	+ "whose own trailing comment says the work was never done. It is reported as "
	+ "a recorded absence and never delivered, because an empty branch maintains "
	+ "no state for a client to be verified against.")

## The closed action vocabulary. A closed set is what lets an unknown action be
## refused by name instead of falling through to a branch nobody reviewed.
const ACTIONS := ["buy", "use"]
const ACTION_BUY := "buy"
const ACTION_USE := "use"
const ACTION_COUNT := 2

## Closed one-to-one with the legacy branches: no action maps to no branch and
## no branch maps to no action. The suite asserts equality of both sets, so a
## fourth branch cannot appear unnoticed.
const ACTION_COMMAND := {ACTION_BUY: BUY_COMMAND, ACTION_USE: USE_COMMAND}

## Both actions address the same key: the committed magic identity.
const ACTION_ADDRESSING_KEY := {ACTION_BUY: "magic_id", ACTION_USE: "magic_id"}

## The legacy argument list is a single magic identity for both branches
## (`command.py:653` and `665`); nothing else is read.
const ACTION_ARGUMENT_COUNT := {ACTION_BUY: 1, ACTION_USE: 1}

## The loopback endpoint path the live implementation dials. Named here as the
## **contract**, NOT as transport: `legacy_v0_api.gd` is the only file allowed to
## reference an endpoint, which the project-scope suite enforces.
const MAGIC_PATH := "/v0/magic"

# ---------------------------------------------------------------------------
# The state vector
# ---------------------------------------------------------------------------

const PRIVATE_STATE_KEY := "privateState"
const LEDGER_KEY := "magics"

## The ledger is a mapping of **string** keys to integer counts. The legacy
## branch keys on the string form of the identity, which is why an identity sent
## as a float produces a second, unrelated entry.
const LEDGER_KEY_TYPE := "string"

## Eight stored resource slots, not seven. Six live on the map and two live in
## private state. The no-price proof compares **all eight**, because comparing a
## subset would make the claim weaker than the twelve-transaction measurement
## that established it.
const RESOURCE_NAMES := [
	"xp", "gold", "wood", "oil", "steel", "cash", "mana", "energy",
]
const RESOURCE_COUNT := 8
const PROOF_RESOURCE_COUNT := RESOURCE_COUNT

## No magic branch writes a resource, so the derived vector is the neutral one.
## The endpoint still compares every slot rather than trusting this, because the
## legacy dispatcher applies the request own vector **before** the branch runs.
const RESOURCE_VECTOR_SLOTS := RESOURCE_COUNT

# ---------------------------------------------------------------------------
# The recorded cap -- a literal, not a derivation (design D6)
# ---------------------------------------------------------------------------

## The cap as it appears in the preserved source, at `command.py:658` and
## `command.py:670`. It is a **hardcoded literal**: see
## `REJECTED_CAP_DERIVATION`.
const COUNTER_CAP := 50
const CAP_SOURCE_LINES := [658, 670]

const REJECTED_CAP_DERIVATION := {
	"rejected": "derive the cap from committed magics content",
	"candidates": [
		{"magic_id": 1, "magic_name": "AirStrike", "field": "cash",
			"value": 50},
		{"magic_id": 5, "magic_name": "Shortcircuit Inductor",
			"field": "level", "value": 50},
	],
	"reason": (
		"The preserved source contains no reference to any content when it "
		+ "applies the cap: min(50, ...) is a literal in a min call. The value "
		+ "50 occurring among the committed magics values is a coincidence of "
		+ "the value distribution, not its provenance. Recording it as "
		+ "content-derived would invent a derivation, which is the defect class "
		+ "this project own training_time and unit_capacity findings warn "
		+ "against. The cap is delivered as the hardcoded literal it is, and the "
		+ "suite asserts the literal is used and that no content lookup "
		+ "substitutes for it."
	),
	"applied": "COUNTER_CAP is the literal; no committed magic value is read to "
		+ "obtain it",
}

# ---------------------------------------------------------------------------
# Committed content
# ---------------------------------------------------------------------------

## The normalized content domain the committed magic table is published under.
const CONTENT_DOMAIN := "magics"

## The committed table own size, which is what makes an unknown identity a
## bounded refusal rather than an open one.
const COMMITTED_MAGIC_COUNT := 10
const COMMITTED_MAGIC_ID_MIN := 1
const COMMITTED_MAGIC_ID_MAX := 10

## The committed fields the projection reports verbatim. Nothing is derived from
## them: the ledger has zero readers, so no committed magics field can be
## consumed at all.
const REPORTED_FIELDS := ["mana", "level", "gold", "cash", "target"]
const REPORTED_FIELD_COUNT := 5

## One committed entry description promises an effect whose magnitude is **not
## committed**. Named rather than left implicit so that no delivered code
## synthesizes one (design D8).
const ABSENT_MAGNITUDE_ENTRY := {
	"magic_id": 10,
	"magic_name": "Attack Boost",
	"description": "Your units will increase their attack and life to wreak "
		+ "havoc on enemies!!",
	"committed_numbers": {"mana": 10, "level": 35, "gold": 10000, "cash": 30,
		"target": 1},
	"absent": "no multiplier, factor, magnitude, radius, or duration is "
		+ "committed for the promised attack and life increase",
	"rule": "No delivered code may synthesize the missing magnitude, and the "
		+ "suite asserts the absence rather than only the presence of the "
		+ "other fields",
}

## The field names a magnitude would arrive under. A projection carrying any of
## them would have synthesized one.
const MAGNITUDE_FIELD_NAMES := [
	"multiplier", "factor", "magnitude", "radius", "duration", "amount",
	"boost", "percent", "power",
]

# ---------------------------------------------------------------------------
# Refusal reasons
# ---------------------------------------------------------------------------

const REASON_INVALID_ACTION := "invalid_action"
const REASON_CLIENT_DICTATED_COUNT := "client_dictated_count"
const REASON_MISSING_MAGIC_ID := "missing_magic_id"
const REASON_INVALID_MAGIC_ID := "invalid_magic_id"
const REASON_NON_CANONICAL_MAGIC_ID := "non_canonical_magic_id"
const REASON_UNKNOWN_MAGIC_ID := "unknown_magic_id"
const REASON_UNREADABLE_ENTRY := "unreadable_entry"
const REASON_INVALID_LEDGER := "invalid_ledger"
const REASON_INVALID_COUNTER := "invalid_counter"
const REASON_COUNTER_ABOVE_CAP := "counter_above_cap"
const REASON_INVALID_PAYLOAD := "invalid_payload"

## Keys naming a client-dictated count. These are refused by name rather than
## ignored, so a caller can tell "you may not say how many" apart from "there
## was nothing to find".
const COUNT_KEYS := [
	"count", "delta", "new_value", "value", "amount", "uses", "charges",
	"quantity", "remaining", "cap", "max_uses",
]

## The legacy batch envelope own keys, refused if a client ever sends them.
## They are protocol plumbing, not player intent.
##
## Matched **case-insensitively** against the incoming key: the recorded
## envelope spells two of these in camel case (`publishActions`,
## `accessToken`), so folding the incoming key and comparing it against the
## literal list would have missed both while the list still claimed to close the
## vocabulary. The list is therefore stored folded, and the suite re-measures
## that every entry is already folded rather than trusting the comment.
const PROTOCOL_KEYS := [
	"first_number", "publishactions", "ts", "tries", "accesstoken", "commands",
]
const PROTOCOL_KEYS_CAMEL_CASE := ["publishActions", "accessToken"]

## Any request key that *names* a count is refused too, so a client cannot
## invent a synonym the closed list did not anticipate.
const COUNT_KEY_SUBSTRINGS := ["count", "delta", "amount", "charge", "uses"]

const CLIENT_DICTATED_REFUSAL := {
	"reason": REASON_CLIENT_DICTATED_COUNT,
	"keys": COUNT_KEYS,
	"protocol_keys": PROTOCOL_KEYS,
	"rule": "The request carries a validated identity and an action. A "
		+ "client-sent count, delta, resulting value, or cap is refused here "
		+ "with a named code, an empty payload, and no state change -- before "
		+ "the player recorded state is read at all, so the refusal does not "
		+ "depend on whether anything was there.",
	"legacy_reads": "The legacy branches read exactly one argument, the magic "
		+ "identity, and derive the counter from the player own recorded "
		+ "ledger. There is no client-sent count in the legacy request to "
		+ "refuse; the refusal is the Server v1 / M13 authority this project "
		+ "wants, not a reproduction of an absence.",
}

# ---------------------------------------------------------------------------
# The validation order -- every check above the write
# ---------------------------------------------------------------------------

const VALIDATION_ORDER := [
	{"step": 1, "key": "action_in_closed_vocabulary",
		"reads_player_state": false,
		"rule": "action must name one of the two recorded branches"},
	{"step": 2, "key": "no_client_dictated_count",
		"reads_player_state": false,
		"rule": "the request carries no count, delta, resulting value, or cap, "
			+ "and no protocol plumbing key"},
	{"step": 3, "key": "identity_present", "reads_player_state": false,
		"rule": "the request names a magic identity"},
	{"step": 4, "key": "identity_well_typed", "reads_player_state": false,
		"rule": "the identity is an integer and not a bool, and it is not a "
			+ "float, because the string form of 1.0 differs from the string "
			+ "form of 1 and the legacy ledger keys on that string form"},
	{"step": 5, "key": "identity_in_committed_table",
		"reads_player_state": false,
		"rule": "the identity resolves against the committed ten-entry magic "
			+ "table, which the legacy server never checks"},
	{"step": 6, "key": "ledger_readable", "reads_player_state": true,
		"rule": "the recorded ledger is a mapping of string keys to "
			+ "non-negative integers; an absent ledger and a non-mapping ledger "
			+ "are reported, never defaulted to an empty one"},
	{"step": 7, "key": "counter_readable", "reads_player_state": true,
		"rule": "the addressed counter is a non-negative integer when present"},
	{"step": 8, "key": "transition_derived", "reads_player_state": true,
		"rule": "the after value is the smaller of the cap and the before value "
			+ "plus one, for both actions, derived server-side, and is never "
			+ "below the before value; a recorded counter already above the cap "
			+ "is refused rather than reduced, because the obvious formula "
			+ "applied to it returns the very decrease the legacy assigning arm "
			+ "performs"},
]
const VALIDATION_ORDER_STEPS := 8

## The write happens after every step above.
const WRITE_STEP := VALIDATION_ORDER_STEPS + 1

const ORDERING_RULE := {
	"steps": VALIDATION_ORDER_STEPS,
	"write_step": WRITE_STEP,
	"rule": "Every check resolves before any ledger entry is created or "
		+ "modified, so a refused request provably leaves the whole recorded "
		+ "document byte-identical. The legacy branch performs no validation at "
		+ "all, so there is no recorded ordering to reproduce; this requirement "
		+ "exists so that this service refusals are safe rather than to match "
		+ "an ordering.",
	"content_before_state": "Step 5 reads committed content and steps 6 to 8 "
		+ "read player state, so a request naming a spell that does not exist "
		+ "never consults the corpus.",
}

# ---------------------------------------------------------------------------
# The two refused legacy asymmetries (design D3)
# ---------------------------------------------------------------------------

const LEGACY_UNBOUNDED_ARM := {
	"command": BUY_COMMAND,
	"operator": "+=",
	"source_expression": "magics[str(magic_id)] += min(50, magics[str(magic_id)] + 1)",
	"source_lines": [658],
	"defect": "the additive operator adds a capped amount rather than assigning "
		+ "a capped value, so the result is not bounded by 50 and the counter "
		+ "grows without limit",
	"executed": {"start": 2, "sequence": [3, 7, 15, 31, 63, 113],
		"crossed_cap": true},
	"verdict": "REFUSED, never reproduced",
	"reason": "Reproducing an unbounded growth as parity would ship a defect as "
		+ "a contract. This service increments by one under the recorded cap "
		+ "instead, and records the difference as a divergence.",
}

const LEGACY_DECREASING_ARM := {
	"command": USE_COMMAND,
	"operator": "=",
	"source_expression": "magics[str(magic_id)] = min(50, magics[str(magic_id)] + 1)",
	"source_lines": [670],
	"defect": "the assigning operator assigns an absolute value, so the capped "
		+ "expression is a clamp that can reduce a counter already above the cap",
	"executed": {"before": 113, "after": 50, "charges_destroyed": 63},
	"recorded_message": "Used magic spell",
	"verdict": "REFUSED, never reproduced",
	"reason": "This is the sharpest measurement in the line: a command whose "
		+ "recorded message claims a spell was used deleted 63 player-owned "
		+ "charges. This service never reduces a counter, and records the "
		+ "difference as a divergence.",
}

const CAP_UNIFORMITY := {
	"legacy": "The two branches disagree about the cap, so there is no "
		+ "recorded rule for how a cap applies across actions: one is unbounded "
		+ "past the cap and the other clamps down to it.",
	"service": "The recorded cap applies uniformly to both actions, and that "
		+ "uniformity is a recorded decision rather than a reproduction.",
	"above_cap": "A recorded counter already above the cap is refused with "
		+ "counter_above_cap rather than reduced. The legacy server "
		+ "reduces it, and refusing is the only option that neither reproduces "
		+ "that decrease nor answers success for an operation that did nothing.",
	"verdict": "recorded divergence, not parity",
}

# ---------------------------------------------------------------------------
# The identity refusals (design D4)
# ---------------------------------------------------------------------------

const UNKNOWN_IDENTITY := {
	"reason": REASON_UNKNOWN_MAGIC_ID,
	"rule": "The identity must resolve against the committed ten-entry magic "
		+ "table. The legacy branch validates nothing, so an identity outside "
		+ "the table is accepted there and creates a ledger entry for a spell "
		+ "that does not exist.",
	"executed": {"command": BUY_COMMAND, "identity": 99,
		"outcome": "accepted; a ledger key was created at 0"},
	"verdict": "REFUSED, and the difference is recorded as a divergence",
}

const NON_CANONICAL_IDENTITY := {
	"reason": REASON_NON_CANONICAL_MAGIC_ID,
	"rule": "An identity whose string form differs from the committed key is a "
		+ "different identity and is refused rather than coerced. The legacy "
		+ "ledger keys on the string form, so a numeric identity sent as a "
		+ "float produces a distinct, unrelated ledger entry.",
	"executed": {"command": USE_COMMAND, "identity": 1.0,
		"string_form": "1.0", "committed_key": "1",
		"outcome": "accepted; the distinct key was created"},
	"verdict": "REFUSED, and the difference is recorded as a divergence",
}

# ---------------------------------------------------------------------------
# The damage refusal -- a structural claim, not a note (design D7)
# ---------------------------------------------------------------------------

## The seven committed damage-shaping fields, each measured to have zero legacy
## consumers under six counting rules. Recorded so the refusal is a re-measured
## census rather than an inherited assertion.
const ZERO_CONSUMER_DAMAGE_FIELDS := [
	"attack", "defense", "life", "attack_interval", "attack_range",
	"best_against", "best_against_mult",
]
const ZERO_CONSUMER_DAMAGE_FIELD_COUNT := 7

## Six counting rules, because the wrong rule produces a confidently wrong
## number. Only **two** of them can establish a consumer: `token` and `quoted`.
## The other four are substring or line measures, and they are the ones that
## mislead here -- the damage token occurs inside the two cost-token constant
## names and inside the attacking animation names, while the attack token occurs
## only inside the end-attack branch name and the attacker locals.
##
## A first draft of this module listed `code_only` and `code_distinct_line`
## among the consumer rules, which is wrong and was caught by measurement: the
## attack field measures 30 under `code_only` and **zero** under `token`, so a
## consumer rule that includes the substring rules would have reported the
## committed attack field as heavily consumed and inverted the finding this line
## exists to record.
const COUNTING_RULES := [
	"whole", "distinct_line", "code_only", "code_distinct_line", "token",
	"quoted",
]
const CONSUMER_RULES := ["token", "quoted"]
const SUBSTRING_RULES := ["whole", "distinct_line", "code_only",
	"code_distinct_line"]
const COUNTING_RULE_COUNT := 6

## Every recorded consumer-rule figure the census must reproduce this run.
## Recorded here so a legacy edit that introduced a consumer fails the suite
## rather than being explained away.
const RECORDED_DAMAGE_CENSUS := {
	"attack": {"whole": 42, "distinct_line": 38, "code_only": 30,
		"code_distinct_line": 30, "token": 0, "quoted": 0},
	"defense": {"whole": 0, "distinct_line": 0, "code_only": 0,
		"code_distinct_line": 0, "token": 0, "quoted": 0},
	"life": {"whole": 0, "distinct_line": 0, "code_only": 0,
		"code_distinct_line": 0, "token": 0, "quoted": 0},
	"attack_interval": {"whole": 0, "distinct_line": 0, "code_only": 0,
		"code_distinct_line": 0, "token": 0, "quoted": 0},
	"attack_range": {"whole": 0, "distinct_line": 0, "code_only": 0,
		"code_distinct_line": 0, "token": 0, "quoted": 0},
	"best_against": {"whole": 0, "distinct_line": 0, "code_only": 0,
		"code_distinct_line": 0, "token": 0, "quoted": 0},
	"best_against_mult": {"whole": 0, "distinct_line": 0, "code_only": 0,
		"code_distinct_line": 0, "token": 0, "quoted": 0},
}

## The eleven legacy root modules the census spans. Scoping it to `command.py`
## alone would report different substring counts for the same fields and would
## look like a contradiction of the investigation rather than a narrower view of
## it.
const LEGACY_MODULES := [
	"command.py", "engine.py", "sessions.py", "server.py", "constants.py",
	"get_game_config.py", "get_player_info.py", "version.py", "auctions.py",
	"bundle.py", "legacy_command_recorder.py",
]
const LEGACY_MODULE_COUNT := 11

const NO_DAMAGE := {
	"verdict": "No damage is resolved, computed, applied, or stored, because "
		+ "the preserved server has no damage rule to reproduce and no "
		+ "committed amount from which to derive one.",
	"no_consumer_fields": ZERO_CONSUMER_DAMAGE_FIELDS,
	"counting_rules": COUNTING_RULES,
	"consumer_rules": CONSUMER_RULES,
	"no_storage_evidence": {
		"row_slots": MAP_ROW_SLOTS,
		"row_length_is_constant": true,
		"attr_bag_union": ATTR_BAG_UNION,
		"private_state_damage_shaped_keys": 0,
		"rule": "Every placed row in every canonical committed save document is "
			+ "exactly eight slots with one type per slot, the attribute bag "
			+ "union contains no hit point, and no private-state key matches any "
			+ "damage-shaped token. A damage system needs somewhere to keep a "
			+ "remaining hit point and the committed format has nowhere.",
	},
	"structural_guard": "No delivered code contains a helper capable of "
		+ "computing a damage amount, a hit-point value, attack or defense "
		+ "arithmetic, a multiplier, a mitigation, or a combat outcome, and the "
		+ "hermetic suite asserts that absence by pinning the delivered module "
		+ "whole static inventory, so the guard fails when such a helper is "
		+ "introduced.",
	"committed_content_has_no_amount": {
		"field": "",
		"reason": "The committed magics carry mana, level, gold, cash, and "
			+ "target, and no damage, multiplier, magnitude, radius, or duration "
			+ "field at all.",
	},
}

# ---------------------------------------------------------------------------
# The committed row shape and the canonical corpus (design D9)
# ---------------------------------------------------------------------------

## The committed map row shape: item, x, y, timestamp, orientation, garrison,
## attribute bag, team.
const MAP_ROW_SLOTS := 8
const SLOT_ITEM_ID := 0
const SLOT_GARRISON := 5
const SLOT_ATTR := 6
const SLOT_TEAM := 7
const ROW_SHAPE := [
	"item", "cell_x", "cell_y", "timestamp", "orientation", "garrison",
	"attribute_bag", "team",
]

## The complete attribute-bag key union over every placed row of every
## canonical committed save document, re-measured every run.
const ATTR_BAG_UNION := ["cp", "nu", "si", "ts", "ui", "xp"]
const ATTR_BAG_UNION_SIZE := 6

## The canonical corpus, as an explicit **allow-list**.
##
## The recorded first row-shape walk reported 33 documents and 13,034 rows
## because it recursed into the fixture step documents and into a Godot build
## cache. An allow-list cannot repeat that class of fault: a new document is
## opted into, never swept up.
const CANONICAL_CORPUS := [
	"villages/AcidCaos.json",
	"villages/General_Mike_30.json",
	"villages/General_Mike_31.json",
	"villages/Kiriakos.json",
	"villages/Nerri.json",
	"villages/Neutral.json",
	"villages/Scarlet.json",
	"villages/initial.json",
	"tests/saves/fresh-player.json",
	"tests/saves/fresh-player-pre-migration.json",
]
const CANONICAL_CORPUS_COUNT := 10

## What the allow-list deliberately excludes, and why. Recorded so the exclusion
## is an assertion the suite can check rather than an accident.
const EXCLUDED_FROM_CORPUS := [
	{"excluded": "tests/fixtures", "reason": "fixture step documents are "
		+ "recorded evidence of a transaction, not canonical save documents; "
		+ "walking them is what produced the recorded 33-document figure"},
	{"excluded": "apps/client-godot/.godot", "reason": "a Godot build cache, "
		+ "which is the second half of the same recorded over-count"},
	{"excluded": "villages/quest", "reason": "quest documents of a different "
		+ "shape, not placed-row saves"},
	{"excluded": "tests/saves/manifest.json", "reason": "a manifest of saves, "
		+ "not a save"},
]

## Damage-shaped key tokens. A key matching **any** of them as a substring
## would mean the corpus stores a hit point somewhere.
const DAMAGE_SHAPED_KEYS := [
	"hp", "health", "damage", "dmg", "armor", "shield", "life", "wound",
]

const PLACED_ROWS_RECORDED := 3372

## The per-slot types the committed corpus records under CPython, where a JSON
## integer decodes to an int. **The pinned engine decodes every JSON number as a
## float**, so the census records the engine own view and the suite asserts slot
## uniformity plus the non-numeric slots; the table below is published so the
## difference is stated rather than hidden.
const RECORDED_PYTHON_SLOT_TYPES := [
	"int", "int", "int", "int", "int", "list", "dict", "int",
]
const UNIFORM_SLOT_COUNT := MAP_ROW_SLOTS

# ---------------------------------------------------------------------------
# The damage vocabulary that does exist -- reported, never used
# ---------------------------------------------------------------------------

## The resource-cost vocabulary with no consumer. Declared at
## `constants.py:894-895` and read by nothing anywhere.
const DAMAGE_SELF_TOKEN := {"name": "COST_DAMAGE_SELF", "value": "ds",
	"declared_at": "constants.py:894"}
const DAMAGE_ENEMY_TOKEN := {"name": "COST_DAMAGE_ENEMY", "value": "de",
	"declared_at": "constants.py:895"}
const COST_TOKEN_FIELD := "cost"
const DAMAGE_COST_TOKENS := [DAMAGE_SELF_TOKEN, DAMAGE_ENEMY_TOKEN]

## Exactly one occurrence in all eleven legacy modules, and it is a write inside
## the fast-forward branch. Its name implies a daily attack allowance; no such
## check exists, so no allowance, limit, window, or reset rule is derived from
## it.
const ATTACK_RESET_FIELD := {
	"name": "tsAttacksReset",
	"declared_at": "command.py:919",
	"occurrence_count": 1,
	"fate": "write_only",
	"readers": 0,
	"note": "A client-writable instant inside the fast-forward branch with no "
		+ "reader. Its name implies a daily attack allowance; no such check "
		+ "exists, so no allowance, limit, window, or reset rule is derived "
		+ "from the name.",
}
const SPYING_RESET_FIELD := {
	"name": "tsSpyingsReset",
	"declared_at": "command.py:920",
	"occurrence_count": 1,
	"fate": "write_only",
	"readers": 0,
}

## The combat-named mission types, **owned by `godot-mission-vocabulary`**.
## They are listed here as reported content and are referenced, never
## reimplemented: this capability projects no mission vocabulary and no mission
## state, and its code carries no identifier named after a mission type.
const COMBAT_NAMED_TYPES_OWNED_ELSEWHERE := [
	"MISSION_ATTACK_PLAYER",
	"MISSION_ATTACK_FRIEND",
	"MISSION_ASSAULTS_WON",
	"MISSION_KILLED_ENEMY",
	"MISSION_DEFEAT_ALL_TROLLS",
	"MISSION_SACRIFICE_UNIT",
]
const VOCABULARY_OWNER_PATH := "scripts/missions/mission_vocabulary.gd"

## Every reported-vocabulary token and where it is reported.
##
## The contract has exactly one measured column: **identifier sites**, which must
## be zero for every token. A future helper named `buy_mana_new`, or a constant
## named `tsAttacksReset`, therefore fails the suite.
##
## There is deliberately **no** pinned count of prose occurrences. A first draft
## pinned a raw-document site count of 2 and was wrong twice over: the figure was
## asserted before it was measured, and it counted the documentation too, so it
## moved every time this file own prose was edited -- which is a property of the
## prose, not of the contract. The suite instead checks the two things that
## matter and cannot drift: the token appears **nowhere** in this module own code
## (measured on code-only text), and it appears inside the reporting constant
## this row names.
const REPORTED_TOKEN_SITES := [
	{"token": "COST_DAMAGE_SELF", "identifier_sites": 0,
		"reported_in": "DAMAGE_SELF_TOKEN"},
	{"token": "COST_DAMAGE_ENEMY", "identifier_sites": 0,
		"reported_in": "DAMAGE_ENEMY_TOKEN"},
	{"token": "tsAttacksReset", "identifier_sites": 0,
		"reported_in": "ATTACK_RESET_FIELD"},
	{"token": "tsSpyingsReset", "identifier_sites": 0,
		"reported_in": "SPYING_RESET_FIELD"},
	{"token": "buy_mana_new", "identifier_sites": 0,
		"reported_in": "NO_OP_COMMAND"},
	{"token": "MISSION_", "identifier_sites": 0,
		"reported_in": "COMBAT_NAMED_TYPES_OWNED_ELSEWHERE",
		"note": "The two constants holding those six names are deliberately "
			+ "NOT named after the prefix -- they are COMBAT_NAMED_TYPES_"
			+ "OWNED_ELSEWHERE and VOCABULARY_OWNER_PATH -- so the identifier "
			+ "column is zero and the claim is literally true rather than "
			+ "nearly true"},
]
const REPORTED_TOKEN_COUNT := 6

const REPORTED_DAMAGE_VOCABULARY := {
	"cost_tokens": [DAMAGE_SELF_TOKEN, DAMAGE_ENEMY_TOKEN],
	"cost_token_field": COST_TOKEN_FIELD,
	"reset_instants": [ATTACK_RESET_FIELD, SPYING_RESET_FIELD],
	"no_op_branch": {"command": NO_OP_COMMAND, "declared_at":
		"command.py:%d" % NO_OP_LINE, "note": NO_OP_NOTE},
	"mission_types_owned_elsewhere": COMBAT_NAMED_TYPES_OWNED_ELSEWHERE,
	"mission_vocabulary_owner": VOCABULARY_OWNER_PATH,
	"rule": "Every entry here appears only as reported content. None of it is "
		+ "read to compute a value, gate an operation, or derive a limit. The "
		+ "combat-named mission types are owned by godot-mission-vocabulary "
		+ "and are referenced, not reimplemented.",
}

## The ledger has zero readers, which is a stronger statement than any field
## count: because nothing reads it, no committed magics field can be consumed.
const LEDGER_HAS_NO_READERS := {
	"ledger_write_sites": 4,
	"counter_subscript_occurrences": 6,
	"membership_tests": 2,
	"local_bindings": 2,
	"read_sites": 0,
	"migration_sites": 4,
	"migration_location": "version.py:32-37",
	"note": "The four shapes are counted separately because collapsing them "
		+ "into one number is ambiguous: four assignment statements, six "
		+ "subscript occurrences because the two assignment lines carry two "
		+ "each, two membership tests of the string form of the identity, and "
		+ "two local bindings of the ledger. The version module coerces a "
		+ "missing or non-mapping ledger to an empty one, which is a migration "
		+ "and not a reader. No statement anywhere reads a ledger value, so "
		+ "there is no code path from the committed magics content to any "
		+ "behaviour.",
	"consequence": "No committed magics field can be consumed at all: not the "
		+ "reported five, and not the zero-consumer ones.",
}

# ---------------------------------------------------------------------------
# No price, no reward, no effect
# ---------------------------------------------------------------------------

const NO_COST_OR_REWARD := {
	"price": "none charged",
	"reward": "none paid",
	"measured": {
		"transactions": 12,
		"resource_slots_compared": PROOF_RESOURCE_COUNT,
		"resource_names": RESOURCE_NAMES,
		"slots_that_moved": 0,
		"mana_before": 15,
		"mana_after": 15,
	},
	"rule": "No stored resource is charged and none is paid, measured across "
		+ "twelve executed transactions in which no resource slot moved and "
		+ "the mana value held steady across a use command. Any price would be "
		+ "invented.",
}

const NO_MAGIC_EFFECT := {
	"verdict": "no magic effect is applied to any unit",
	"reason": "The use command increments a number. Nothing happens to any "
		+ "unit, because the two branches touch no placement row and resolve no "
		+ "combat.",
}

# ---------------------------------------------------------------------------
# The divergences -- reported, never parity
# ---------------------------------------------------------------------------

const DIVERGENCES := [
	{
		"id": "buy_magic_unbounded_growth",
		"legacy_behaviour": "counter grows past the cap without limit (2 to 113)",
		"service_behaviour": "counter increments by one under the recorded cap",
		"classification": "refused, not reproduced",
		"authority": "server-side derivation (design D2/D3)",
	},
	{
		"id": "use_magic_decreases_counter",
		"legacy_behaviour": "counter reduced from 113 to 50, destroying 63 "
			+ "charges",
		"service_behaviour": "counter is never reduced",
		"classification": "refused, not reproduced",
		"authority": "server-side derivation (design D3)",
	},
	{
		"id": "cap_applied_uniformly",
		"legacy_behaviour": "the two branches disagree about the cap",
		"service_behaviour": "the cap applies to both actions",
		"classification": "recorded decision, not a reproduction",
		"authority": "design D3",
	},
	{
		"id": "identity_outside_committed_table_accepted",
		"legacy_behaviour": "an identity of 99 was accepted and created a "
			+ "ledger entry",
		"service_behaviour": "refused with unknown_magic_id",
		"classification": "divergence",
		"authority": "Server v1 / M13 (design D4)",
	},
	{
		"id": "float_identity_creates_distinct_key",
		"legacy_behaviour": "an identity of 1.0 created a distinct key",
		"service_behaviour": "refused rather than coerced to the committed key",
		"classification": "divergence",
		"authority": "Server v1 / M13 (design D4)",
	},
	{
		"id": "counter_above_cap_reduced_by_legacy",
		"legacy_behaviour": "a recorded counter above the cap is accepted and "
			+ "reduced: 113 to 50, destroying 63 charges",
		"service_behaviour": "refused with counter_above_cap; the recorded "
			+ "state is reported rather than rewritten",
		"classification": "refused, not reproduced",
		"authority": "server-side derivation (design D3)",
		"note": "Found by smoke-testing the derivation, not by review: the "
			+ "obvious formula applied to a before value of 113 returns 50, "
			+ "which is the very decrease this line refuses, wearing this "
			+ "service clothes. Clamping would reproduce the defect and leaving "
			+ "the value unchanged would answer success for an operation that "
			+ "did nothing, so the recorded state is refused.",
	},
	{
		"id": "absent_key_writes_zero_not_one",
		"legacy_behaviour": "an identity with no recorded entry takes the "
			+ "branch's else arm and the ledger gains the key at ZERO: executed, "
			+ "use_magic 3 created '3': 0 and buy_magic 99 created '99': 0",
		"service_behaviour": "an absent entry is read as zero charges and the "
			+ "transition increments it, so the key is created at ONE",
		"classification": "divergence",
		"authority": "server-side derivation (design D2)",
		"note": "Both arms of the legacy branch write 0 for an unknown key, so "
			+ "the legacy server's own 'acquire a spell you hold none of' path "
			+ "increments nothing at all. Treating the absent entry as zero "
			+ "charges and incrementing it is the coherent reading, and it is "
			+ "recorded here rather than left to be discovered as a mismatch. "
			+ "This is also the path a live phase against "
			+ "tests/saves/fresh-player.json exercises, because that corpus's "
			+ "privateState.magics is {}, so the phase drives a second request "
			+ "on the same identity to show a clean increment with no divergence "
			+ "alongside it.",
	},
]
## Seven, not six.
##
## The seventh -- `absent_key_writes_zero_not_one` -- was **missing from this
## record when the line was first delivered**, and the omission was found by the
## live phase rather than by review: `parse_magic()` compares this table against
## the endpoint's answer by index and refused a six-entry answer as a malformed
## one. The six that were recorded are the six that are only visible from the
## preserved source, and every one of them needs a crafted or progressed corpus
## to reproduce; the seventh is the one this line's own corpus reaches on its
## very first request, so it was the divergence most likely to be exercised and
## the only one missing. A recorded divergence is a claim, and a claim that is
## never produced is not evidence -- which is the reason this is a correction
## rather than an addition.
const DIVERGENCE_COUNT := 7

# ---------------------------------------------------------------------------
# Provenance and non-claims
# ---------------------------------------------------------------------------

## The dispatcher branch count the project own command-catalog tool reports,
## cross-checked against a measurement rather than a hand-kept table.
##
## A first character class without **digits** measured 62, because one branch
## name ends in a digit. The suite asserts that this is the branch the class
## would miss, so the class is not simplified back.
const CATALOG_COMMAND_BRANCHES := 63
const CATALOG_BRANCH_COUNT_REQUIRES_DIGITS := "push_queue_unit2"

const PROVENANCE = {
	"capability": "godot-damage",
	"milestone": "M10",
	"line": 3,
	"roadmap_line": "damage",
	"investigation": "docs/legacy-m10-damage.md",
	"delivered_surface": "the privateState magics counter transition, validated "
		+ "against the committed magic table",
	"primary_finding": "the damage refusal -- no damage is resolved, computed, "
		+ "applied, or stored, and no committed amount exists to derive one from",
	"legacy_branches": MAGIC_COMMANDS,
	"corpus": "villages/Neutral.json",
	"corpus_reason": "the only committed corpus whose ledger is non-empty, "
		+ "which is what makes this surface capturable against committed data",
	"executed_transactions": 12,
	"committed_magics_driven": 1,
	"committed_magics_total": COMMITTED_MAGIC_COUNT,
	"interpretation": "Every branch span, dispatcher count, damage census, and "
		+ "corpus figure is RE-DERIVED from committed bytes on every run. "
		+ "Nothing is transcribed, so a legacy edit fails the guard instead of "
		+ "silently contradicting the record.",
}

const NON_CLAIMS := [
	"No damage is resolved, computed, applied, or stored, and none is claimed.",
	"No magic effect is applied to any unit.",
	"No price is charged and no reward is paid; every one of the eight stored "
		+ "resource slots is unchanged across the measured transactions.",
	"No combat outcome, mission completion, or honour is computed.",
	"No attack allowance, limit, window, or reset rule is derived from the "
		+ "attack-reset instant.",
	"No magnitude is synthesized for the committed entry whose description "
		+ "promises an effect.",
	"No per-magic behaviour is claimed: one of ten committed magics was driven.",
	"The cap is the recorded literal, not a derivation from committed content.",
	"The two refused legacy asymmetries are divergences, never parity.",
	"No pixel parity is claimed and no windowed capture is claimed; nothing is "
		+ "rendered by this line.",
	"The ledger has zero readers, so no committed magics field can be consumed.",
	"no Flash, " + "Ruf" + "fle" + ", " + "Action" + "Script" + ", or browser "
		+ "executed, and no network was used in the hermetic suite",
]
const NON_CLAIM_COUNT := 12

# ---------------------------------------------------------------------------
# The coverage limit carried from the investigation (task 5.2)
# ---------------------------------------------------------------------------

const COVERAGE := {
	"committed_magics_total": COMMITTED_MAGIC_COUNT,
	"driven": 1,
	"driven_legacy_id": "1",
	"driven_name": "AirStrike",
	"driven_command_sequence": ["use_magic", "buy_magic", "buy_magic",
		"buy_magic", "buy_magic", "buy_magic", "use_magic", "use_magic"],
	"legacy_counter_path": [2, 3, 7, 15, 31, 63, 113, 50, 50],
	"service_counter_path": [2, 3, 4, 5, 6, 7, 8, 9, 10],
	"path_note": "The two paths are the SAME eight commands driven against the "
		+ "SAME committed ledger key, and they are recorded side by side "
		+ "because the difference between them is the whole deliverable. The "
		+ "committed investigation interleaved the arms deliberately so the "
		+ "divergence reads as one sequence; the service path is derived by "
		+ "replaying that same sequence through the delivered transition.",
	"ledger_keys_observed_in_the_committed_corpus": 5,
	"observed_but_not_driven": 4,
	"parity_transactions": 12,
	"corpora": 1,
	"per_magic_behaviour_claimed": false,
	"reason": "The two branches are identity-agnostic, so the transition shape "
		+ "is shared across the ten committed magics, but NO per-magic behaviour "
		+ "is claimed -- and none exists to claim, because no committed field "
		+ "has a legacy consumer. The five ledger keys the committed corpus "
		+ "carries were observed in the ledger and only one of them was driven "
		+ "through the recorded transactions.",
	"progressed_player_corpora": 0,
	"progressed_player_note": "No progressed-player save with a different "
		+ "ledger shape is exercised by this line.",
}

# ---------------------------------------------------------------------------
# The neighbouring capabilities this line does not duplicate (task 5.1)
# ---------------------------------------------------------------------------

const FOREIGN_OWNERS := [
	{"capability": "godot-combat-actions",
		"path": "scripts/units/combat_flow.gd",
		"surface": "the attack-resolution branches and the dead-hero ledger"},
	{"capability": "godot-mission-vocabulary",
		"path": "scripts/missions/mission_vocabulary.gd",
		"surface": "every mission-type declaration and the mission-state hand-off"},
	{"capability": "godot-unit-behaviors",
		"path": "scripts/units/unit_behaviors.gd",
		"surface": "the dead-hero ledger gates, the revival gate fields, and the "
			+ "syringe cost refusal"},
	{"capability": "godot-unit-queues",
		"path": "scripts/units/queue_flow.gd",
		"surface": "the training queue keys and their instants"},
	{"capability": "godot-building-construction",
		"path": "scripts/town/construction_flow.gd",
		"surface": "the construction countdown and the click threshold"},
	{"capability": "godot-unit-instances",
		"path": "scripts/units/unit_instance_projection.gd",
		"surface": "the stored-instance attribute bag projection"},
	{"capability": "godot-unit-experience",
		"path": "scripts/units/production_flow.gd",
		"surface": "the recorded unit experience kind and its two branch arms"},
]
const FOREIGN_OWNER_COUNT := 7

## The two parts of the two-part post-execution proof. Carried here so a caller
## cannot read the first half as the whole claim.
##
## ## Correction, measured against the delivered endpoint rather than assumed
##
## The first half's half name and `checks` text originally read
## `counter_moved_by_exactly_the_derived_delta` and claimed the persisted value
## equals the **server-derived** one. That is not what this route's proof does, and
## it could not be: design D3 requires the derived transition to disagree with
## the unchanged dispatcher for `buy` and for every absent key, so asserting the
## two equal would fail every one of those executions. The endpoint therefore pins
## the ledger against what the **unchanged legacy arm writes** --
## `_legacy_recorded_after`, re-derived here as `legacy_recorded_after()` -- and
## reports the derived value beside it under `matches_derived`.
##
## So the half is still a value comparison, and still non-tautological: it catches
## a smuggled delta, a misrouted command, and a wrong key, none of which a count
## comparison would see. What it compares changed, and the record now says so.
const PROOF_HALVES := [
	{
		"half": "the_recorded_ledger_entry_equals_what_the_unchanged_arm_writes",
		"checks": "the persisted ledger value for the addressed identity equals "
			+ "the value the unchanged legacy arm's own arithmetic produces, "
			+ "every entry the derivation did not address is byte-identical, and "
			+ "the recorded key order is preserved with a created key appended",
		"why": "the derived transition is deliberately NOT what executes, so "
			+ "pinning the recorded value is what makes this half a proof; the "
			+ "derived value travels beside it under matches_derived, and the two "
			+ "disagreeing is the recorded divergence rather than a failure",
		"not_this": "counter_moved_by_exactly_the_derived_delta",
		"not_this_why": "the derived transition cannot equal the recorded one for "
			+ "buy or for an absent key by construction, so that claim was never "
			+ "true of this route and asserting it would have failed every "
			+ "execution rather than caught a defect",
	},
	{
		"half": "every_stored_resource_unchanged",
		"checks": "all eight stored resource slots are compared, never a subset",
		"why": "the legacy dispatcher applies the request own vector BEFORE the "
			+ "branch, so this half is what forecloses a delta smuggled through "
			+ "the request",
	},
]
const PROOF_HALF_COUNT := 2

# ---------------------------------------------------------------------------
# The structural guards (design D7)
# ---------------------------------------------------------------------------

## The delivered module whole static-function inventory, pinned. The suite reads
## this file, extracts its static declarations, and requires this list to match
## exactly in BOTH directions -- nothing missing and nothing extra. Adding a
## resolution, damage, duration, honour, reward, or mission-completion helper
## therefore fails the suite rather than quietly contradicting the refusal.
const STATIC_FUNCTIONS := [
	"magic_failure",
	"legacy_source_path",
	"_read_source_bytes",
	"_code_only",
	"_strip_line",
	"_branch_name",
	"_branch_span",
	"_count_occurrences",
	"_count_lines_containing",
	"_count_tokens",
	"_count_quoted",
	"_is_word_character",
	"_count_field_consumers",
	"legacy_census_text",
	"derive_field_inventory",
	"_counter_operator",
	"_cap_literal_lines",
	"branch_count_agrees_with_catalog",
	"derive_corpus_census",
	"_record_row",
	"_kind_name",
	"is_action",
	"is_canonical_magic_key",
	"wire_magic_identity",
	"ledger_key_for",
	"refused_client_keys",
	"project_ledger",
	"counter_value",
	"derive_counter_transition",
	"_is_integer_valued",
	"is_committed_magic",
	"project_magic_entry",
	"_neutral_resource_delta",
	"project_magic",
	"result_from_projection",
	"divergences",
	"reported_vocabulary",
	"no_damage_record",
	"coverage_limit",
	"owners",
	"build_magic_intent",
	"legacy_recorded_after",
	"build_magic_response",
	"parse_magic",
	"_magic_error",
	"_order_step_agrees",
	"_wire_resources",
	"_wire_int",
]
const STATIC_FUNCTION_COUNT := 48

## Helpers this capability deliberately does **not** define, and the reason each
## is absent. Recorded as a named list so the absence is an assertion the suite
## can check and the report can publish, not merely a sentence in a docstring.
##
## The suite matches these as **substrings of the delivered code**, not as exact
## names, because a by-name-only guard was measured to miss a suffixed helper
## wearing the same disguise on an earlier line of this project.
const ABSENT_HELPERS := [
	{"helper": "resolve_damage", "absent_because": "no committed damage field "
		+ "has a legacy consumer and there is nowhere to store a hit point, so "
		+ "there is no committed damage rule to resolve"},
	{"helper": "damage_for", "absent_because": "the same absence, stated as "
		+ "the noun a caller would reach for"},
	{"helper": "derive_damage", "absent_because": "the same absence again, "
		+ "stated in this module own verb"},
	{"helper": "magic_damage", "absent_because": "the same absence, stated "
		+ "for the delivered surface"},
	{"helper": "apply_attack", "absent_because": "the attack and attack-interval "
		+ "fields are content with zero consumers, so there is no outcome to "
		+ "apply"},
	{"helper": "attack_of", "absent_because": "the committed attack field is "
		+ "read by no branch, so it is content and never a rule"},
	{"helper": "defend", "absent_because": "the defense field is a constant on "
		+ "every committed unit and is read by no branch"},
	{"helper": "defense_of", "absent_because": "the same absence as defend"},
	{"helper": "life_of", "absent_because": "the life field is read by no "
		+ "branch and no row stores a remaining hit point"},
	{"helper": "hit_points", "absent_because": "the committed row shape has no "
		+ "slot for a hit point and the attribute bag has no key for one"},
	{"helper": "mitigate", "absent_because": "no committed field records a "
		+ "mitigation and no branch applies one"},
	{"helper": "multiplier_for", "absent_because": "no committed field records "
		+ "a multiplier, and the one committed description that promises an "
		+ "increased attack and life commits no magnitude at all"},
	{"helper": "magnitude_for", "absent_because": "the same absence, for the "
		+ "magnitude the committed content never states"},
	{"helper": "synthesize_magnitude", "absent_because": "the same absence, "
		+ "named as the act the line forbids outright"},
	{"helper": "hit_chance", "absent_because": "no committed field records a "
		+ "probability and no branch draws a random number"},
	{"helper": "resolve_combat", "absent_because": "no combat is resolved by "
		+ "the preserved server, so there is no outcome to reproduce"},
	{"helper": "combat_outcome", "absent_because": "the same absence, stated as "
		+ "the value a caller would want"},
	{"helper": "cap_from_content", "absent_because": "the cap is a bare literal "
		+ "in the preserved source; deriving it from a committed value would "
		+ "invent a derivation, and the rejected alternative is retained "
		+ "instead"},
	{"helper": "price_for", "absent_because": "no stored resource slot moved "
		+ "across any measured transaction, so a price would be invented"},
	{"helper": "honor_for", "absent_because": "no committed field records an "
		+ "honour amount and neither branch writes one"},
	{"helper": "reward_for", "absent_because": "no committed field records a "
		+ "reward and neither branch writes a resource"},
	{"helper": "attack_allowance", "absent_because": "the attack-reset instant "
		+ "has one write site and no reader, so no allowance, limit, window, or "
		+ "reset rule exists to reproduce and none may be derived from the name"},
	{"helper": "complete_mission", "absent_because": "the mission vocabulary "
		+ "remains owned by godot-mission-vocabulary, which measured zero "
		+ "consumers; this line references no mission state"},
]

## The arithmetic claim, recorded as MEASURED figures rather than as a slogan,
## so the suite can prove it mechanically instead of by reading (design D7).
##
## Every figure below is measured on this file own code-only text -- comments
## and string literals blanked by `_code_only` -- and the suite re-measures all
## of them on every run. Exactly one class of operator is non-zero, and it is
## named precisely rather than folded into a boastful sentence:
##
##   * two percent operators, both the binary string-format operator. The first
##     is applied to a literal (`"command.py:%d" % NO_OP_LINE`); the second is
##     applied to an argument **array** and continues the format onto the next
##     line. **Neither is a modulo over a number**, which is why they are
##     classified against the raw document rather than the code-only text: a
##     format operator written on its own continuation line would otherwise be
##     reported as a modulo.
##
## There is **no** asterisk, no division, no power, no shift, and no bitwise
## operator anywhere in the code -- the neutral resource vector is built by an
## explicit loop precisely so this sentence needs no exception carved out for
## an array repeat.
##
## So the module computes no damage figure, no hit-point value, no ratio, no
## multiplier, no mitigation, no price, no honour amount, no reward, and no
## combat outcome from any committed value. The ONE arithmetic this contract
## performs is the counter transition: a before value plus one, bounded by the
## recorded literal cap.
const ARITHMETIC_RECORD := {
	"multiply_operators": 0,
	"divide_operators": 0,
	"power_operators": 0,
	"shift_left_operators": 0,
	"shift_right_operators": 0,
	"bitwise_and_operators": 0,
	"bitwise_or_operators": 0,
	"bitwise_xor_operators": 0,
	"format_operators": 2,
	"format_operator_left_operands": "one string literal, and one string "
		+ "literal continued on the following line; both are the binary "
		+ "format operator and neither is a modulo",
	"modulo_operators": 0,
	"arithmetic_over_a_committed_damage_field": 0,
	"arithmetic_over_a_reported_committed_field": 0,
	"comparisons_of_one_committed_value_against_another": 0,
	"the_one_arithmetic": "the counter transition: a before value plus one, "
		+ "bounded by the recorded literal cap",
}

# ---------------------------------------------------------------------------
# The typed projections
# ---------------------------------------------------------------------------

## One committed magic, reported verbatim.
##
## It is declared HERE rather than in the shared type module because no other
## capability owns the committed magic table.
##
## The property inventory is pinned by the suite, so a derived field -- a
## multiplier above all -- cannot be added unnoticed.
class MagicEntry:
	extends RefCounted
	## The committed key the ledger addresses, as a decimal string.
	var legacy_id := ""
	var name := ""
	var mana := 0
	var level := 0
	var gold := 0
	var cash := 0
	var target := 0
	var description := ""
	## False when the committed entry could not be read at all; the projection is
	## then refused rather than defaulted.
	var readable := false
	## Always false. Recorded so a caller can read the absence rather than infer
	## it from a missing field.
	var magnitude_present := false


## The typed outcome of one magic intent: the server-derived transition, the
## committed entry behind it, the recorded cap and its rejected derivation, the
## structural damage refusal, the reported vocabulary, and the divergences -- or a
## structured failure with **no partial payload**.
##
## The wire half of the record lives here too, on the same type, because there is
## one contract and one refusal vocabulary: a field a caller could read from an
## offline projection but not from the service's own answer would be exactly the
## kind of half-surface this project records as a defect. Every wire field is
## therefore declared with a value that cannot be mistaken for a parsed one -- an
## empty string, an empty collection, `false`, or `-1` -- so an unparsed field is
## visible as such and never reads as a real zero.
class MagicResult:
	extends RefCounted
	var ok := false
	var reason := ""
	var error := ""
	var action := ""
	var command := ""
	var addressing_key := ""
	## The committed ledger key the identity resolves to, "" on failure.
	var ledger_key := ""
	var counter_before := 0
	var counter_present := false
	var counter_after := 0
	var change := 0
	var capped := false
	## The recorded literal cap, never a value read from committed content.
	var cap := COUNTER_CAP
	## The verbatim committed entry, or a failure with `entry_readable` false.
	var entry: MagicEntry = null
	var entry_readable := false
	## The two-part proof this transition is measured against.
	var proof_halves: Array = []
	var ordering_rule: Dictionary = {}
	var validation_order: Array = []
	var no_damage: Dictionary = {}
	var reported_vocabulary: Dictionary = {}
	var divergences: Array = []
	var non_claims: Array = []

	# --- the wire record ----------------------------------------------------

	var protocol := ""
	var result := ""
	var game_version := ""
	## -1 until parsed; a stamped instant, never the wall clock on this side.
	var server_time := -1
	var addressing_value := -1
	var addressing_kind := ""
	var addressing_note := ""
	## What the UNCHANGED legacy branch wrote, re-derived by
	## `legacy_recorded_after` from the branch bodies rather than echoed.
	var recorded_after := -1
	## The endpoint's own expectation of the same figure.
	var legacy_expected_after := -1
	## Whether the recorded value equals the derived transition. **False is the
	## normal case** for `buy` and for an absent key, and that is the divergence,
	## not a failure.
	var matches_derived := false
	var legacy_absent_arm_writes_zero := false
	## Always false; recorded so the absence is readable rather than inferred.
	var decreased := false
	## True only on an answer the service marked server-derived.
	var derived := false
	var cap_is_literal: Array = []
	var rejected_cap_derivation: Dictionary = {}
	var refused_count: Dictionary = {}
	## The recorded ledger key order, as the persisted document's own order.
	var ledger_before_keys: Array = []
	var ledger_after_keys: Array = []
	var ledger_after_present := false
	var ledger_after_keys_are_strings := false
	var write_step := 0
	var cap_uniformity: Dictionary = {}
	var legacy_unbounded_arm: Dictionary = {}
	var legacy_decreasing_arm: Dictionary = {}
	var ledger_has_no_readers: Dictionary = {}
	var no_cost_or_reward: Dictionary = {}
	var no_magic_effect: Dictionary = {}
	var refusals: Array = []
	var provenance: Dictionary = {}
	## All eight stored slots after execution, never a subset.
	var resources: Dictionary = {}
	var resource_count := 0
	var changed: Array = []

# ---------------------------------------------------------------------------
# The typed result constructor
# ---------------------------------------------------------------------------


## A structured failure for a magic intent -- never a partial payload.
static func magic_failure(code: String, message: String) -> MagicResult:
	var result := MagicResult.new()
	result.ok = false
	result.reason = code
	result.error = message
	result.entry_readable = false
	return result

# ---------------------------------------------------------------------------
# Source re-derivation (design D9) -- never transcribed
# ---------------------------------------------------------------------------


## Absolute path of the legacy source the derivations are re-derived from.
static func legacy_source_path() -> String:
	return Paths.repo_root().path_join(LEGACY_SOURCE_RELATIVE)


## Read the legacy source bytes, or return the recorded failure.
static func _read_source_bytes() -> Dictionary:
	var handle := FileAccess.open(legacy_source_path(), FileAccess.READ)
	if handle == null:
		return {"ok": false, "text": "",
			"error": "cannot read " + LEGACY_SOURCE_RELATIVE + ": "
				+ legacy_source_path()}
	var bytes := handle.get_buffer(handle.get_length())
	handle = null
	return {"ok": true, "text": bytes.get_string_from_utf8(), "error": ""}


## Blank comments and string literals from Python source, one line at a time, so
## line N of the stripped text is line N of the source.
##
## This is a **real two-state scanner**, not a regular expression, and the
## distinction is load-bearing twice over in this project's history: a one-pass
## expression desynchronised on an apostrophe inside a double-quoted string and
## made three downstream scans vacuously true, and a caller once passed a **path**
## where the **body** was expected so that the same three scans silently passed
## while measuring an unreadable file. The scanner here tracks both quote
## characters, honours backslash escapes, and stops at a comment to the end of
## the line -- and the suite proves both failure modes are caught by perturbing
## its own input.
##
## ## The per-line scan is measured, not chosen for convenience
##
## An earlier draft of this module scanned the whole document with the quote
## state carried **across** newlines. Measured against the same eleven modules,
## that draft produced **3,821** lines where the source has **3,832**: a newline
## inside a string literal was consumed as a space, so multi-line strings merged
## their neighbours and a line number on the stripped text stopped meaning what it
## means on the source. The recorded census figures happened to survive it
## (`code_distinct_line` for the attack field measured 30 either way), which is
## exactly why the fault is dangerous: it is invisible until a legacy edit puts a
## damage token on one of the merged lines.
##
## The scan is therefore per line with the quote state reset at every newline,
## which mirrors the recorded contract this module measures against and makes the
## line-preservation claim true by construction. The hermetic suite re-measures
## the line count on every run, against the same eleven modules, and fails if the
## stripped text has fewer lines than the source.
static func _code_only(body: String) -> String:
	var lines := body.split("\n")
	var out: Array = []
	for line: String in lines:
		out.append(_strip_line(line))
	return "\n".join(out)


## Blank comments and string literals from ONE line of Python source, keeping the
## line exactly as long as it arrived.
static func _strip_line(line: String) -> String:
	var out := ""
	var index := 0
	var length := line.length()
	var quote := ""
	while index < length:
		var character := line[index]
		if quote != "":
			if character == "\\" and index < length - 1:
				out += "  "
				index += 2
				continue
			if character == quote:
				quote = ""
			out += " "
			index += 1
			continue
		if character == "#":
			out += " ".repeat(length - index)
			break
		if character == "\"" or character == "'":
			quote = character
			out += " "
			index += 1
			continue
		out += character
		index += 1
	return out


## The committed dispatcher-branch name declared on one Python line, or "".
##
## Hand-parsed rather than pattern-matched, and the identifier class contains
## **digits on purpose**: a class without them measures 62 dispatcher branches
## instead of 63, because one branch name ends in a digit. The suite asserts both
## the count and the identity of that branch.
static func _branch_name(line: String) -> String:
	var text := line.rstrip("\r")
	var stripped := text.strip_edges()
	var rest := ""
	if stripped.begins_with("elif "):
		rest = stripped.substr(5).strip_edges()
	elif stripped.begins_with("if "):
		rest = stripped.substr(3).strip_edges()
	else:
		return ""
	var prefix := "cmd == "
	if not rest.begins_with(prefix):
		return ""
	var after := rest.substr(prefix.length())
	if not after.begins_with("\""):
		return ""
	var close := after.find("\"", 1)
	if close < 0:
		return ""
	var name := after.substr(1, close - 1)
	if after.substr(close + 1).strip_edges() != ":":
		return ""
	if name.length() == 0:
		return ""
	for offset in name.length():
		var code := name.unicode_at(offset)
		var lower := code >= 97 and code <= 122
		var upper := code >= 65 and code <= 90
		var digit := code >= 48 and code <= 57
		if not (lower or upper or digit or code == 95):
			return ""
	return name


## The 1-based half-open line span of one named dispatcher branch.
static func _branch_span(lines: Array, name: String) -> Dictionary:
	var start := -1
	for offset in lines.size():
		var found := _branch_name(str(lines[offset]))
		if found == "":
			continue
		if found == name:
			start = offset + 1
			continue
		if start > 0:
			return {"found": true, "start": start, "end": offset}
	if start > 0:
		return {"found": true, "start": start, "end": lines.size()}
	return {"found": false, "start": 0, "end": 0}


## Occurrences of `needle` in `haystack`, counted per occurrence rather than per
## line, so a line carrying two occurrences counts as two.
static func _count_occurrences(haystack: String, needle: String) -> int:
	if needle.is_empty():
		return 0
	var total := 0
	var index := haystack.find(needle)
	while index >= 0:
		total += 1
		index = haystack.find(needle, index + 1)
	return total


## How many lines of `body` contain `needle` at least once.
static func _count_lines_containing(body: String, needle: String) -> int:
	if needle.is_empty():
		return 0
	var total := 0
	for line in body.split("\n"):
		if str(line).to_lower().contains(needle):
			total += 1
	return total


## Occurrences of `field` as a **standalone identifier token**, case-sensitive.
##
## Word boundaries treat the underscore as a word character, which is what makes
## the committed attack field measure zero: it appears only inside longer
## identifiers, so a substring count is an artifact and this count is not.
static func _count_tokens(body: String, field: String) -> int:
	if field.is_empty():
		return 0
	var total := 0
	var index := body.find(field)
	while index >= 0:
		var before_ok := index == 0 or not _is_word_character(body[index - 1])
		var after_index := index + field.length()
		var after_ok := after_index >= body.length() \
				or not _is_word_character(body[after_index])
		if before_ok and after_ok:
			total += 1
		index = body.find(field, index + 1)
	return total


## The committed quoted-access form of a field, case-sensitive.
static func _count_quoted(body: String, field: String) -> int:
	if field.is_empty():
		return 0
	return _count_occurrences(body, "\"" + field + "\"") \
		+ _count_occurrences(body, "'" + field + "'")


static func _is_word_character(character: String) -> bool:
	if character.is_empty():
		return false
	var code := character.unicode_at(0)
	var lower := code >= 97 and code <= 122
	var upper := code >= 65 and code <= 90
	var digit := code >= 48 and code <= 57
	return lower or upper or digit or code == 95


## Measure one field presence under all six counting rules.
##
## The two substring rules are **not** consumer tests: the damage token occurs
## inside two cost-token constant names, and the attack token occurs inside
## longer identifiers. Only the token and quoted rules can establish a consumer,
## which is why both are recorded beside the substring figures rather than
## instead of them.
static func _count_field_consumers(body: String, field: String) -> Dictionary:
	var stripped := _code_only(body)
	var folded := field.to_lower()
	return {
		"whole": _count_occurrences(body.to_lower(), folded),
		"distinct_line": _count_lines_containing(body, folded),
		"code_only": _count_occurrences(stripped.to_lower(), folded),
		"code_distinct_line": _count_lines_containing(stripped, folded),
		"token": _count_tokens(body, field),
		"quoted": _count_quoted(body, field),
	}


## Every legacy root module joined, in the fixed order of `LEGACY_MODULES`.
##
## Joined rather than counted per module because the investigation figures are
## totals across the eleven, and a per-module breakdown would invite a reader to
## add them up and get a different answer to a question they did not ask.
static func legacy_census_text() -> Dictionary:
	var parts: Array = []
	var missing: Array = []
	for module: String in LEGACY_MODULES:
		var handle := FileAccess.open(Paths.repo_root().path_join(module),
			FileAccess.READ)
		if handle == null:
			missing.append(module)
			continue
		var bytes := handle.get_buffer(handle.get_length())
		handle = null
		parts.append(bytes.get_string_from_utf8())
	return {
		"ok": missing.is_empty(),
		"error": "cannot read: " + ", ".join(missing) if not missing.is_empty()
			else "",
		"modules": LEGACY_MODULES.size() - missing.size(),
		"missing": missing,
		"text": "\n".join(parts),
	}


## Re-derive the two branches, both operators, the dispatcher count, and the
## damage census from committed bytes.
##
## `source_text` is injectable on purpose: it is what makes this derivation
## testable by perturbation rather than only by hope, and the suite uses that to
## prove the derivation counts what it claims.
static func derive_field_inventory(source_text: String = "") -> Dictionary:
	var text := source_text
	var read_error := ""
	if source_text.is_empty():
		var read: Dictionary = _read_source_bytes()
		if not bool(read.get("ok", false)):
			read_error = str(read.get("error", ""))
			text = ""
		else:
			text = str(read["text"])
	var lines := text.split("\n")

	var names: Array = []
	for line in lines:
		var name := _branch_name(str(line))
		if name != "":
			names.append(name)

	var branches: Array = []
	var operators := {}
	var cap_sites: Array = []
	for command: String in MAGIC_COMMANDS:
		var span := _branch_span(lines, command)
		branches.append({
			"name": command,
			"start": int(span["start"]) if bool(span["found"]) else 0,
			"end": int(span["end"]) if bool(span["found"]) else 0,
			"found": bool(span["found"]),
		})
		operators[command] = _counter_operator(lines, span)
		cap_sites.append_array(_cap_literal_lines(lines, span))

	var census_text := text
	var census_modules := 1
	var census_missing: Array = []
	if source_text.is_empty():
		var census := legacy_census_text()
		census_text = str(census["text"])
		census_modules = int(census["modules"])
		census_missing = census["missing"]
	var census := {}
	for field: String in ZERO_CONSUMER_DAMAGE_FIELDS:
		census[field] = _count_field_consumers(census_text, field)

	# The four distinct ledger shapes are counted separately, because collapsing
	# them into one number is ambiguous: the membership tests are not subscripts,
	# and the two assignment lines carry two subscripts each.
	var writes := 0
	var membership := 0
	var bindings := 0
	for line in lines:
		var raw := str(line)
		if raw.contains("magics[str(magic_id)]") and raw.contains("+="):
			writes += 1
		elif raw.contains("magics[str(magic_id)] ="):
			writes += 1
		if raw.contains("if str(magic_id) in magics"):
			membership += 1
		if raw.contains("magics = privateState["):
			bindings += 1

	var found_all := true
	for branch: Dictionary in branches:
		if not bool(branch["found"]):
			found_all = false

	return {
		"ok": found_all and read_error == "",
		"error": read_error,
		"source": LEGACY_SOURCE_RELATIVE,
		"branch_names": names,
		"branches": branches,
		"counter_operators": operators,
		"cap_literals": cap_sites,
		"damage_census": census,
		"damage_census_scope": LEGACY_MODULES,
		"damage_census_modules": census_modules,
		"damage_census_missing": census_missing,
		"dispatcher_branches": names.size(),
		"catalog_command_branches": CATALOG_COMMAND_BRANCHES,
		"ledger_write_sites": writes,
		"ledger_membership_tests": membership,
		"ledger_bindings": bindings,
		"ledger_read_sites": 0,
	}


## The counter operator inside one branch span, or "" when the span carries no
## counter assignment at all.
static func _counter_operator(lines: Array, span: Dictionary) -> String:
	if not bool(span.get("found", false)):
		return ""
	var start := int(span["start"])
	var end := int(span["end"])
	var region := ""
	for offset in range(start - 1, mini(end, lines.size())):
		var line := str(lines[offset])
		if not line.contains("magics[str(magic_id)]"):
			continue
		if line.contains("] += min("):
			region += "+="
		elif line.contains("] = min("):
			region += "="
	return region


## The 1-based lines carrying the cap literal inside one branch span.
static func _cap_literal_lines(lines: Array, span: Dictionary) -> Array:
	var out: Array = []
	if not bool(span.get("found", false)):
		return out
	var start := int(span["start"])
	var end := int(span["end"])
	for offset in range(start - 1, mini(end, lines.size())):
		if str(lines[offset]).contains("min(50,"):
			out.append(offset + 1)
	return out


## Whether the measured dispatcher count equals the project own catalog figure.
##
## This is the guard that catches a too-narrow identifier character class, which
## is the specific instrument fault the investigation recorded as its fourth
## correction.
static func branch_count_agrees_with_catalog(inventory: Dictionary) -> bool:
	return int(inventory.get("dispatcher_branches", -1)) == CATALOG_COMMAND_BRANCHES


## Re-measure the no-storage evidence: the row shape, the attribute-bag key
## union, and the absence of any damage-shaped private-state key.
##
## `documents` is injectable so the suite can perturb the walk and prove it
## counts the documents it claims. The default is an explicit **allow-list**, not
## a directory sweep: the recorded first walk over-counted by recursing into the
## fixture step documents and into a Godot build cache.
static func derive_corpus_census(documents: Array = CANONICAL_CORPUS) -> Dictionary:
	var rows := 0
	var lengths := {}
	var slot_kinds := {}
	var attr_keys := {}
	var damage_shaped := []
	var damage_shaped_count := 0
	var reset_instants := {"tsAttacksReset": 0, "tsSpyingsReset": 0}
	var walked: Array = []
	var unreadable: Array = []
	var bad_shape := 0

	for relative: String in documents:
		var handle := FileAccess.open(Paths.repo_root().path_join(relative),
			FileAccess.READ)
		if handle == null:
			unreadable.append(relative)
			continue
		var bytes := handle.get_buffer(handle.get_length())
		handle = null
		# A malformed document is refused BEFORE the parser is invoked, so a
		# refusal never prints an engine error line: the parse result of "" is
		# not an object, and the engine message would be the only evidence.
		if bytes.size() == 0:
			unreadable.append(relative)
			continue
		var parsed: Variant = JSON.parse_string(bytes.get_string_from_utf8())
		if not (parsed is Dictionary):
			unreadable.append(relative)
			continue
		var document: Dictionary = parsed
		walked.append(relative)
		var maps: Variant = document.get("maps", null)
		if not (maps is Array) or (maps as Array).is_empty():
			unreadable.append(relative)
			continue
		var first: Variant = (maps as Array)[0]
		if not (first is Dictionary):
			unreadable.append(relative)
			continue
		var items: Variant = (first as Dictionary).get("items", null)
		if items is Dictionary:
			for key: Variant in (items as Dictionary).keys():
				rows += 1
				_record_row(str(key), items as Dictionary, lengths, slot_kinds,
					attr_keys, bad_shape)
		elif items is Array:
			for key: Variant in (items as Array).size():
				rows += 1
				_record_row(str(key), items as Array, lengths, slot_kinds,
					attr_keys, bad_shape)
		else:
			unreadable.append(relative)
			continue
		var private_state: Variant = document.get("privateState", null)
		if private_state is Dictionary:
			for key: Variant in (private_state as Dictionary).keys():
				var folded := str(key).to_lower()
				var shaped := ""
				for token: String in DAMAGE_SHAPED_KEYS:
					if folded.contains(token):
						shaped = token
						break
				if shaped != "":
					damage_shaped_count += 1
					damage_shaped.append({"document": relative, "key": str(key),
						"token": shaped})
				if reset_instants.has(str(key)):
					reset_instants[str(key)] = \
						int(reset_instants[str(key)]) + 1

	var union: Array = attr_keys.keys()
	union.sort()
	var uniform := 0
	for index in MAP_ROW_SLOTS:
		var kinds: Array = slot_kinds.get(index, [])
		if kinds.size() == 1:
			uniform += 1
	return {
		"ok": unreadable.is_empty() and walked.size() == documents.size(),
		"error": "" if unreadable.is_empty()
			else "cannot read or parse: " + ", ".join(unreadable),
		"documents": walked,
		"document_count": walked.size(),
		"unreadable": unreadable,
		"placed_rows": rows,
		"distinct_row_lengths": lengths.keys(),
		"rows_not_eight_slots": bad_shape,
		"slot_kinds": slot_kinds,
		"uniform_slot_count": uniform,
		"attr_bag_union": union,
		"private_state_damage_shaped_keys": damage_shaped_count,
		"private_state_damage_shaped": damage_shaped,
		"reset_instants_present_in_documents": reset_instants,
	}


## Record one placed row into the running shape census.
static func _record_row(key: String, source: Variant, lengths: Dictionary,
		slot_kinds: Dictionary, attr_keys: Dictionary, bad_shape: int) -> void:
	var row: Variant = source[key] if source is Dictionary else null
	if source is Array:
		row = source[int(key)]
	if not (row is Array):
		return
	var slots: Array = row
	lengths[slots.size()] = true
	if slots.size() != MAP_ROW_SLOTS:
		bad_shape += 1
	for index in mini(slots.size(), MAP_ROW_SLOTS):
		var kind := _kind_name(slots[index])
		var recorded: Array = slot_kinds.get(index, [])
		if not recorded.has(kind):
			recorded.append(kind)
		slot_kinds[index] = recorded
	if slots.size() > SLOT_ATTR and slots[SLOT_ATTR] is Dictionary:
		for attr_key: Variant in (slots[SLOT_ATTR] as Dictionary).keys():
			attr_keys[str(attr_key)] = true


## The recorded name of a decoded JSON value kind. The engine decodes every JSON
## number as a float, which is why the per-slot type table published by the
## CPython census differs for the numeric slots; slot **uniformity** and the
## non-numeric slots are what the client asserts.
static func _kind_name(value: Variant) -> String:
	match typeof(value):
		TYPE_NIL:
			return "null"
		TYPE_BOOL:
			return "bool"
		TYPE_INT:
			return "int"
		TYPE_FLOAT:
			return "float"
		TYPE_STRING:
			return "string"
		TYPE_ARRAY:
			return "list"
		TYPE_DICTIONARY:
			return "dict"
		_:
			return "other"

# ---------------------------------------------------------------------------
# The identity, the ledger, and the transition
# ---------------------------------------------------------------------------


## Whether `value` names one of the two recorded branches.
static func is_action(value: Variant) -> bool:
	return typeof(value) == TYPE_STRING and ACTIONS.has(str(value))


## True only for an integer, non-bool identity.
##
## This is the float-hazard refusal. The string form of a float differs from the
## string form of the same integer, and the legacy ledger keys on that string
## form, so accepting a float would create a second, unrelated entry for the
## same spell.
##
## Recorded cross-layer note, and the named adapter that resolves it: the
## pinned engine decodes every JSON number as a `float`, so an identity arriving
## over the wire is a float. This projection keeps the **strict** rule -- an
## identity is an integer, never a float -- because that is exactly the recorded
## legacy rule and widening it here would reintroduce the float-hazard this
## refusal exists to close. A live transport therefore must pass an identity
## through `wire_magic_identity`, which is the one place the engine decode is
## unwrapped, and which refuses a value that is not integral.
static func is_canonical_magic_key(value: Variant) -> bool:
	return typeof(value) == TYPE_INT


## Unwrap the engine own JSON decode for one wire identity, and nothing else.
##
## This is deliberately narrow and deliberately named. The engine has no JSON
## integer type, so a transport that read a response would otherwise hand a
## `float` to `is_canonical_magic_key` and be refused for a decode artefact
## rather than for anything it did. Three properties keep it from becoming a
## coercion in disguise:
##
##   * it accepts a value only when that value is **integral**, so `1.5` is
##     refused rather than rounded;
##   * it refuses a `bool`, so a client-sent `true` cannot become identity 1 --
##     the same refusal `add_xp_unit` would need and that this project records as
##     worth an explicit rule;
##   * it returns the **canonical integer**, and a caller that keeps the original
##     value still gets refused, so nothing downstream can quietly rely on the
##     float form.
##
## It does not look at committed content and it does not create a ledger key:
## both remain the job of `is_committed_magic` and `ledger_key_for`, in the
## recorded order.
static func wire_magic_identity(value: Variant) -> Dictionary:
	if typeof(value) == TYPE_BOOL:
		return {"ok": false, "reason": REASON_INVALID_MAGIC_ID,
			"error": "a wire identity of a bool is refused; a client-sent true "
				+ "is not the integer 1", "identity": 0}
	if not _is_integer_valued(value):
		return {"ok": false, "reason": REASON_NON_CANONICAL_MAGIC_ID,
			"error": "a wire identity must be an integer-valued number, got "
				+ _kind_name(value), "identity": 0}
	return {"ok": true, "reason": "", "error": "", "identity": int(value)}


## The committed ledger key for a validated identity.
##
## The ledger is string-keyed and the committed table keys are the decimal
## spellings of the committed ids. This is called only after
## `is_canonical_magic_key` has accepted the identity, so a float never reaches
## the key form.
static func ledger_key_for(value: Variant) -> Dictionary:
	if not is_canonical_magic_key(value):
		return {"ok": false, "reason": REASON_NON_CANONICAL_MAGIC_ID,
			"error": "magic identity must be an integer and not a bool",
			"key": ""}
	return {"ok": true, "reason": "", "error": "", "key": str(int(value))}


## The request keys naming a count, a cap, or protocol plumbing, in the request
## own key order, so the refusal message is stable across runs.
static func refused_client_keys(payload: Variant) -> Array:
	var out: Array = []
	if not (payload is Dictionary):
		return out
	for key: Variant in (payload as Dictionary).keys():
		if typeof(key) != TYPE_STRING:
			continue
		var name := str(key)
		var folded := name.to_lower()
		if COUNT_KEYS.has(folded) or PROTOCOL_KEYS.has(folded):
			out.append(name)
			continue
		# Any key that *names* a count is refused too, so a client cannot invent
		# a synonym the closed list did not anticipate.
		for token: String in COUNT_KEY_SUBSTRINGS:
			if folded.contains(token):
				out.append(name)
				break
	return out


## Project the recorded ledger, failing closed rather than defaulting.
##
## An absent ledger and a non-mapping ledger are **reported**, never replaced
## with an empty one, because a default would make an unreadable save look like
## an empty one and turn a server fault into a silent create.
static func project_ledger(raw: Variant) -> Dictionary:
	if raw == null:
		return {"ok": false, "reason": REASON_INVALID_LEDGER,
			"error": PRIVATE_STATE_KEY + " ledger is absent",
			"keys": [], "count": 0}
	if not (raw is Dictionary):
		return {"ok": false, "reason": REASON_INVALID_LEDGER,
			"error": PRIVATE_STATE_KEY + " ledger must be a mapping, got "
				+ _kind_name(raw),
			"keys": [], "count": 0}
	var ledger: Dictionary = raw
	var keys: Array = ledger.keys()
	var bad := 0
	for key: Variant in keys:
		if typeof(key) != TYPE_STRING:
			bad += 1
			continue
		var value: Variant = ledger[key]
		if not _is_integer_valued(value) or int(value) < 0:
			bad += 1
	if bad > 0:
		return {"ok": false, "reason": REASON_INVALID_LEDGER,
			"error": "%d of %d ledger entries are not string keys to "
				% [bad, keys.size()]
				+ "non-negative integers",
			"keys": keys, "count": keys.size()}
	return {"ok": true, "reason": "", "error": "", "keys": keys,
		"count": keys.size()}


## The addressed counter, defaulting an **absent** key to zero.
##
## An absent key legitimately means zero: the legacy branch own else arm writes
## zero for a key it has never seen, so absent and zero are the same recorded
## state. A key that *is* present with a non-integer or negative value is a
## different matter and is refused, because incrementing it would require
## inventing an interpretation.
static func counter_value(ledger: Variant, key: String) -> Dictionary:
	if not (ledger is Dictionary):
		return {"ok": false, "reason": REASON_INVALID_LEDGER,
			"error": "the recorded ledger is not a mapping"}
	var recorded: Dictionary = ledger
	if not recorded.has(key):
		return {"ok": true, "reason": "", "error": "", "value": 0,
			"present": false}
	var value: Variant = recorded[key]
	if not _is_integer_valued(value):
		return {"ok": false, "reason": REASON_INVALID_COUNTER,
			"error": "the counter at " + key + " must be a non-negative "
				+ "integer, got " + _kind_name(value)}
	if int(value) < 0:
		return {"ok": false, "reason": REASON_INVALID_COUNTER,
			"error": "the counter at " + key + " must not be negative"}
	return {"ok": true, "reason": "", "error": "", "value": int(value),
		"present": true}


## The server-derived transition, for **both** actions.
##
## The after value is the smaller of the cap and the before value plus one, and
## is therefore:
##
##   * an increment of exactly one;
##   * never above the cap, refusing the unbounded additive arm;
##   * never below the before value, refusing the absolute-clamp arm.
##
## There is deliberately **no action parameter**: both actions derive the same
## transition, because the two legacy arms disagree about the cap and
## `CAP_UNIFORMITY` records that the uniformity is a decision rather than a
## reproduction.
##
## A before value already **above** the cap is refused rather than handled, and
## this is worth recording why, because the obvious formula is wrong in exactly
## the dangerous direction: applied to a before value of 113 it returns 50, which
## is the legacy charge-destroying decrease this line exists to refuse, wearing
## this service clothes. Clamping down would reproduce the defect and leaving
## the value unchanged would answer success for an operation that did nothing.
static func derive_counter_transition(before: Variant,
		cap: Variant = COUNTER_CAP) -> Dictionary:
	if not _is_integer_valued(before):
		return {"ok": false, "reason": REASON_INVALID_COUNTER,
			"error": "the recorded counter must be an integer",
			"before": 0, "after": 0, "change": 0, "capped": false, "cap": 0,
			"decreased": false}
	if not _is_integer_valued(cap) or int(cap) < 0:
		return {"ok": false, "reason": REASON_INVALID_PAYLOAD,
			"error": "the cap must be a non-negative integer",
			"before": 0, "after": 0, "change": 0, "capped": false, "cap": 0,
			"decreased": false}
	if int(before) > int(cap):
		return {"ok": false, "reason": REASON_COUNTER_ABOVE_CAP,
			"error": "the recorded counter " + str(int(before)) + " is above "
				+ "the recorded cap " + str(int(cap)) + "; the legacy server "
				+ "reduces such a value and this service refuses it rather "
				+ "than destroying charges or silently blessing it",
			"before": int(before), "after": int(before), "change": 0,
			"capped": false, "cap": int(cap), "decreased": false}
	var after := int(before) + 1
	if after >= int(cap):
		after = int(cap)
	return {
		"ok": true,
		"reason": "",
		"error": "",
		"before": int(before),
		"after": after,
		"change": after - int(before),
		"capped": after == int(cap),
		"cap": int(cap),
		"decreased": false,
	}


## Whether `value` is an integer-valued number, refusing a bool, a
## non-finite number, and any number with a fractional part.
##
## This exists because the pinned engine decodes every JSON number as a
## `float`, which is stated on `project_magic_entry` and measured by the suite on
## the real committed content rather than assumed. It deliberately does NOT
## accept a `bool`: in GDScript a `bool` is not a number, and accepting one
## would reproduce the exact class of defect this line refuses elsewhere, where a
## client-sent `true` is worth an increment.
static func _is_integer_valued(value: Variant) -> bool:
	if typeof(value) == TYPE_INT:
		return true
	if typeof(value) != TYPE_FLOAT:
		return false
	var number := float(value)
	return is_finite(number) and absf(number - round(number)) < 0.000001


## Whether the identity resolves against the committed magic table.
##
## `magic_of` is a callable taking an **identity** and returning that entry
## committed row or null, so this module reads committed content through a
## parameter and never resolves an entry itself. Null falls back to the bounded
## identity range, which is what an offline caller without a content accessor
## uses -- and that fallback is a **range**, never a guess at an entry.
static func is_committed_magic(value: Variant, magic_of: Variant = null) -> bool:
	if not is_canonical_magic_key(value):
		return false
	if magic_of == null:
		return int(value) >= COMMITTED_MAGIC_ID_MIN \
			and int(value) <= COMMITTED_MAGIC_ID_MAX
	if not (magic_of is Callable):
		return false
	var resolved: Variant = (magic_of as Callable).call(int(value))
	return resolved != null


## Project one committed magic verbatim, or refuse it.
##
## The typed entry exposes the five recorded fields and nothing else, so a
## magnitude cannot appear without the suite noticing. A malformed entry is
## **refused**, never defaulted: a missing field is an unreadable save, not a
## zero.
##
## ## Why the numeric check accepts an integral float
##
## **The pinned engine decodes every JSON number as a `float`**, so every
## committed magic field arrives as `30.0`, not `30`. A strict `TYPE_INT` check
## would therefore refuse all ten committed entries and this projection would
## deliver nothing at all -- a refusal that looks like integrity and is
## actually a decode bug. The recorded contract's own field census was taken
## under CPython, where those same bytes decode to `int`, which is why
## `RECORDED_PYTHON_SLOT_TYPES` and the engine own view differ and both are
## published rather than one of them quietly chosen.
##
## What is accepted is therefore an **integer-valued** number, following the
## same rule the shared content registry already applies to its own numeric
## manifest fields: a `bool` is refused outright, a non-finite number is
## refused, and a number with a fractional part is refused. A value that is not
## exactly an integer cannot be a committed `mana`, `level`, `gold`, `cash`, or
## `target`, so refusing it invents nothing.
static func project_magic_entry(entry: Variant, value: Variant) -> Dictionary:
	var out := {"ok": false, "reason": REASON_UNREADABLE_ENTRY, "error": "",
		"entry": null}
	if not is_canonical_magic_key(value):
		out["reason"] = REASON_NON_CANONICAL_MAGIC_ID
		out["error"] = ("a committed entry is projected only for an integer "
			+ "identity")
		return out
	if not (entry is Dictionary):
		out["error"] = "the committed entry " + str(int(value)) + " is not an object"
		return out
	var row: Dictionary = entry
	var unreadable: Array = []
	for field: String in REPORTED_FIELDS:
		if not row.has(field) or not _is_integer_valued(row[field]):
			unreadable.append(field)
	if not row.has("name") or typeof(row["name"]) != TYPE_STRING:
		unreadable.append("name")
	if not row.has("description") or typeof(row["description"]) != TYPE_STRING:
		unreadable.append("description")
	if not unreadable.is_empty():
		out["error"] = ("the committed entry " + str(int(value))
			+ " has no readable " + ", ".join(unreadable))
		return out
	var magnitude := ""
	for field: String in MAGNITUDE_FIELD_NAMES:
		if row.has(field):
			magnitude = field
			break
	var projected := MagicEntry.new()
	projected.legacy_id = str(int(value))
	projected.name = str(row["name"])
	projected.mana = int(row["mana"])
	projected.level = int(row["level"])
	projected.gold = int(row["gold"])
	projected.cash = int(row["cash"])
	projected.target = int(row["target"])
	projected.description = str(row["description"])
	projected.readable = true
	projected.magnitude_present = magnitude != ""
	out["ok"] = true
	out["reason"] = ""
	out["error"] = ""
	out["entry"] = projected
	out["magnitude_field"] = magnitude
	return out

# ---------------------------------------------------------------------------
# The whole projection
# ---------------------------------------------------------------------------


## The neutral resource vector: one zero per stored slot, built by an explicit
## loop rather than by repeating a count.
##
## A literal loop rather than the array-repeat operator so this module contains
## no asterisk at all: `ARITHMETIC_RECORD` can then claim **zero** operators of
## every kind other than the binary string format, with nothing to carve out and
## nothing to explain. The length is checked against `RESOURCE_COUNT` on every
## run, so a slot added to `RESOURCE_NAMES` without this vector failing is
## impossible.
static func _neutral_resource_delta() -> Array:
	var out: Array = []
	for index in RESOURCE_VECTOR_SLOTS:
		out.append(0)
	return out


## The whole read-only projection of one magic intent, or its refusal.
##
## Every step of `VALIDATION_ORDER` except the request-shape check runs **here**,
## above any write, which is what makes a refused request leave the recorded
## document byte-identical.
##
## The content check deliberately precedes the ledger read, so a request naming
## a spell that does not exist never consults the corpus.
static func project_magic(ledger: Variant, action: Variant, value: Variant,
		magic_of: Variant = null) -> Dictionary:
	var out := {
		"ok": false,
		"reason": "",
		"error": "",
		"action": action,
		"command": "",
		"addressing_key": "",
		"addressing": value,
		"addressing_kind": "magic_id",
		"ledger_key": "",
		"ledger_before": {},
		"counter_before": 0,
		"counter_present": false,
		"counter_after": 0,
		"change": 0,
		"capped": false,
		"cap": COUNTER_CAP,
		"entry": null,
		"magnitude_field": "",
		"ordering_rule": ORDERING_RULE,
		"validation_order": VALIDATION_ORDER,
		"resource_delta": _neutral_resource_delta(),
		"no_damage": NO_DAMAGE,
		"reported_vocabulary": reported_vocabulary(),
		"divergences": divergences(),
	}

	# --- step 1: a closed action vocabulary ------------------------------
	if not is_action(action):
		out["reason"] = REASON_INVALID_ACTION
		out["error"] = "action must be one of " + ", ".join(ACTIONS)
		return out
	var name := str(action)
	out["command"] = str(ACTION_COMMAND[name])
	out["addressing_key"] = str(ACTION_ADDRESSING_KEY[name])

	# --- steps 3 and 4: the identity is present and well typed -------------
	if value == null:
		out["reason"] = REASON_MISSING_MAGIC_ID
		out["error"] = "a magic identity is required for action " + name
		return out
	if not is_canonical_magic_key(value):
		if typeof(value) == TYPE_FLOAT or typeof(value) == TYPE_STRING:
			out["reason"] = REASON_NON_CANONICAL_MAGIC_ID
			out["error"] = ("the identity " + str(value) + " has a string form "
				+ "that is not the committed ledger key form; the legacy "
				+ "branch would create a distinct entry for it")
		else:
			out["reason"] = REASON_INVALID_MAGIC_ID
			out["error"] = ("a magic identity must be an integer and not a "
				+ "bool, got " + _kind_name(value))
		return out

	# --- step 5: the identity resolves against committed content ----------
	if not is_committed_magic(value, magic_of):
		out["reason"] = REASON_UNKNOWN_MAGIC_ID
		out["error"] = ("the identity " + str(int(value))
			+ " is not one of the " + str(COMMITTED_MAGIC_COUNT)
			+ " committed magics; the legacy server accepts any value here "
			+ "and creates a ledger entry for it")
		return out

	# --- step 6: the ledger is readable -----------------------------------
	var ledger_projection := project_ledger(ledger)
	out["ledger_before"] = ledger_projection
	if not bool(ledger_projection["ok"]):
		out["reason"] = str(ledger_projection["reason"])
		out["error"] = str(ledger_projection["error"])
		return out

	# --- step 7: the addressed counter is readable -----------------------
	var key_result := ledger_key_for(value)
	if not bool(key_result["ok"]):
		out["reason"] = str(key_result["reason"])
		out["error"] = str(key_result["error"])
		return out
	var key := str(key_result["key"])
	out["ledger_key"] = key
	var counter := counter_value(ledger, key)
	if not bool(counter["ok"]):
		out["reason"] = str(counter["reason"])
		out["error"] = str(counter["error"])
		return out
	out["counter_before"] = int(counter["value"])
	out["counter_present"] = bool(counter["present"])

	# --- step 8: the transition is derived server-side -------------------
	var transition := derive_counter_transition(int(counter["value"]),
		COUNTER_CAP)
	if not bool(transition["ok"]):
		out["reason"] = str(transition["reason"])
		out["error"] = str(transition["error"])
		return out
	out["counter_after"] = int(transition["after"])
	out["change"] = int(transition["change"])
	out["capped"] = bool(transition["capped"])
	out["ok"] = true
	return out


## The typed result of a projection: the derived transition, the verbatim
## committed entry, and every recorded refusal and divergence.
##
## A refused projection yields a typed failure with **no partial payload**: the
## counter, the entry, and the transition all stay at their declared defaults
## and `ok` is false, so a caller cannot mistake a refusal for a zero-valued
## success.
static func result_from_projection(projection: Dictionary,
		entry: Variant = null) -> MagicResult:
	var result := MagicResult.new()
	result.proof_halves = PROOF_HALVES
	result.ordering_rule = ORDERING_RULE
	result.validation_order = VALIDATION_ORDER
	result.no_damage = NO_DAMAGE
	result.reported_vocabulary = reported_vocabulary()
	result.divergences = divergences()
	result.non_claims = NON_CLAIMS
	result.action = str(projection.get("action", ""))
	result.command = str(projection.get("command", ""))
	result.addressing_key = str(projection.get("addressing_key", ""))
	result.ledger_key = str(projection.get("ledger_key", ""))
	result.cap = int(projection.get("cap", COUNTER_CAP))
	result.ok = bool(projection.get("ok", false))
	result.reason = str(projection.get("reason", ""))
	result.error = str(projection.get("error", ""))
	if not result.ok:
		# A refusal carries NO partial payload. The projection resolves the
		# ledger key before the transition, so the key is present on the
		# dictionary even when the transition is what failed; handing it back
		# would be exactly the partial payload this contract refuses.
		result.ledger_key = ""
		return result
	result.counter_before = int(projection.get("counter_before", 0))
	result.counter_present = bool(projection.get("counter_present", false))
	result.counter_after = int(projection.get("counter_after", 0))
	result.change = int(projection.get("change", 0))
	result.capped = bool(projection.get("capped", false))
	if entry is MagicEntry:
		result.entry = entry
		result.entry_readable = true
	return result

# ---------------------------------------------------------------------------
# Accessors
# ---------------------------------------------------------------------------


## The recorded divergences, as fresh copies.
static func divergences() -> Array:
	var out: Array = []
	for entry: Dictionary in DIVERGENCES:
		out.append(entry.duplicate(true))
	return out


## The recorded damage vocabulary, as a fresh copy.
static func reported_vocabulary() -> Dictionary:
	return REPORTED_DAMAGE_VOCABULARY.duplicate(true)


## The structural damage refusal, as a fresh copy.
static func no_damage_record() -> Dictionary:
	return NO_DAMAGE.duplicate(true)


## The coverage limit carried from the investigation.
static func coverage_limit() -> Dictionary:
	return COVERAGE.duplicate(true)


## The neighbouring capabilities this line does not duplicate.
static func owners() -> Array:
	var out: Array = []
	for entry: Dictionary in FOREIGN_OWNERS:
		out.append(entry.duplicate())
	return out

# ---------------------------------------------------------------------------
# The wire contract -- the body this client builds and the answer it parses
# ---------------------------------------------------------------------------

## The request body carries **exactly three keys**: the save identity, the closed
## action, and the addressing under that action's own wire key.
##
## The count is recorded rather than described because it is the whole of design
## D2: no count, no delta, no resulting value, no cap, and no price is not
## expressible here, and the closed body key count is what makes that true rather
## than merely intended. Both actions address by the same wire key, so the
## vocabulary cannot grow one action at a time.
const BODY_KEY_COUNT := 3

## The addressing kind the service reports. It is a magic **identity**: an
## integer, never a count and never a map key.
const ADDRESSING_KIND := "magic_id"

## The refusals carried by every successful answer, in the endpoint's own order.
##
## The two the offline client can raise before any transport is touched --
## `invalid_action` and `client_dictated_count` -- are here too, because the
## answer reports the route's whole vocabulary rather than the subset this
## particular request could have reached. That is what lets a caller read "these
## nine exist" off a success and never off a failure.
const WIRE_REFUSALS := [
	REASON_INVALID_ACTION,
	REASON_CLIENT_DICTATED_COUNT,
	REASON_MISSING_MAGIC_ID,
	REASON_INVALID_MAGIC_ID,
	REASON_NON_CANONICAL_MAGIC_ID,
	REASON_UNKNOWN_MAGIC_ID,
	REASON_INVALID_LEDGER,
	REASON_INVALID_COUNTER,
	REASON_COUNTER_ABOVE_CAP,
]
const WIRE_REFUSAL_COUNT := 9

## The two legacy arms, named by what each one writes. Recorded so the recorded
## outcome can be **derived and checked** rather than trusted, and so the two
## refusals this line exists for have a name attached to them.
const LEGACY_ARMS := {
	ACTION_BUY: {
		"arm": "adds_stepped_unbounded",
		"writes": "the counter plus the smaller of the cap and one more",
		"defect": "never bounded by the cap; executed as 2, 3, 7, 15, 31, 63, "
			+ "113 against the committed corpus key",
	},
	ACTION_USE: {
		"arm": "assigns_stepped_absolute_clamp",
		"writes": "the smaller of the cap and one more",
		"defect": "an ABSOLUTE clamp, so a counter already above the cap loses "
			+ "charges: executed as 113 becoming 50",
	},
}


## Build the request body for one magic intent, or refuse it before any
## transport is touched.
##
## The body is assembled from exactly the three keys `BODY_KEY_COUNT` names, so a
## client-dictated count is not merely refused by `refused_client_keys()` when one
## arrives: it is **inexpressible** in what this function can produce. The
## `client_dictated_count` refusal therefore exists against a hand-built request,
## and this function's signature is what makes that an honest statement rather
## than a claim about a client that cannot be written.
##
## The identity is unwrapped through `wire_magic_identity` and no further: that
## function already refuses a bool, a non-finite number, and any number with a
## fractional part, and it returns the **canonical integer**, so
## `is_canonical_magic_key` is satisfied by construction and is not re-tested
## here. Testing it again would be a branch no input could reach.
static func build_magic_intent(user_id: String, action: Variant,
		value: Variant) -> Dictionary:
	if not is_action(action):
		return {"ok": false, "reason": REASON_INVALID_ACTION,
			"error": "action must be one of " + ", ".join(ACTIONS)}
	var name := str(action)
	if value == null:
		return {"ok": false, "reason": REASON_MISSING_MAGIC_ID,
			"error": "a magic identity is required for action " + name}
	var unwrapped := wire_magic_identity(value)
	if not bool(unwrapped["ok"]):
		return {"ok": false, "reason": str(unwrapped["reason"]),
			"error": str(unwrapped["error"])}
	var body := {"user_id": user_id, "action": name}
	body[str(ACTION_ADDRESSING_KEY[name])] = int(unwrapped["identity"])
	return {"ok": true, "reason": "", "error": "", "body": body}


## What the UNCHANGED legacy branch writes, so the recorded outcome can be
## **derived and checked** rather than taken on trust.
##
## This is never the service's transition, and the distinction is the whole point
## of the function. `derive_counter_transition` is the contract -- increment by
## one under the cap, never below the before value -- and both legacy defects stay
## refused. What the preserved dispatcher actually writes is a different number:
##
##   * an **absent** key takes the branch's `else` arm and is written at **zero**,
##     for both actions, so the counter is created and nothing is incremented;
##   * `use_magic` **assigns** the smaller of the cap and one more, which equals
##     the derived transition whenever the before value is at or under the cap and
##     destroys charges when it is not;
##   * `buy_magic` **adds** that same stepped value to the counter, so its result
##     is unbounded by the cap at all.
##
## The three figures are literals of the two branch bodies, which are four lines
## apart and mutually inconsistent; there is no shared helper in the preserved
## source to call, which is itself part of the recorded defect.
##
## Deriving the legacy outcome so it can be **verified** is not reproducing it: the
## result of this function is never written to a save, and the derived transition
## and this expectation are required to disagree for `buy` and for an absent key,
## so an edit that quietly made them equal would fail.
static func legacy_recorded_after(action: Variant, before: Variant,
		present: Variant, cap: Variant = COUNTER_CAP) -> Dictionary:
	if not is_action(action):
		return {"ok": false, "reason": REASON_INVALID_ACTION,
			"error": "no recorded arm exists for action " + str(action),
			"after": -1, "arm": ""}
	if not _is_integer_valued(before):
		return {"ok": false, "reason": REASON_INVALID_COUNTER,
			"error": "the recorded counter must be an integer",
			"after": -1, "arm": ""}
	if not _is_integer_valued(cap) or int(cap) < 0:
		return {"ok": false, "reason": REASON_INVALID_PAYLOAD,
			"error": "the cap must be a non-negative integer",
			"after": -1, "arm": ""}
	if not (present is bool):
		return {"ok": false, "reason": REASON_INVALID_COUNTER,
			"error": "the presence statement must be a boolean",
			"after": -1, "arm": ""}
	if not bool(present):
		return {"ok": true, "reason": "", "error": "", "after": 0,
			"arm": "absent_else_arm_writes_zero"}
	var stepped := int(before) + 1
	if stepped >= int(cap):
		stepped = int(cap)
	if str(action) == ACTION_BUY:
		return {"ok": true, "reason": "", "error": "",
			"after": int(before) + stepped, "arm": "adds_stepped_unbounded"}
	return {"ok": true, "reason": "", "error": "", "after": stepped,
		"arm": "assigns_stepped_absolute_clamp"}


## Assemble the response envelope for one **accepted** magic intent.
##
## `projection` is a `project_magic()` result and `post` carries the
## post-execution state a caller measured:
##
##     ledger_after  the persisted ledger in its RECORDED key order, or null
##     resources     all eight stored slots AFTER execution
##     changed       the changed-pointer list the proof produced
##     server_time   a recorded instant -- never the wall clock
##     game_version  the recorded game version, "" when unknown
##
## The envelope's shape is written in **exactly one place** in this module, and
## that is deliberate: the live service builds the same shape in
## `compat_service.py`, and this module's typed parser is what both answers pass
## through, so a shape assembled twice inside one implementation is a shape that
## can drift from the parser that has to accept it.
##
## The `counter` body deliberately reports the **recorded** value, the **derived**
## value, and whether they agree. A caller that only ever saw the derived one
## would be unable to tell that the unchanged dispatcher wrote a different number,
## which is the divergence this line exists to report.
static func build_magic_response(action: Variant, value: Variant,
		projection: Dictionary, post: Dictionary) -> Dictionary:
	var name := str(action)
	var recorded := legacy_recorded_after(name,
		int(projection.get("counter_before", 0)),
		bool(projection.get("counter_present", false)),
		int(projection.get("cap", COUNTER_CAP)))
	var recorded_after := int(recorded["after"])
	var ledger_projection: Dictionary = {}
	if projection.get("ledger_before") is Dictionary:
		ledger_projection = projection.get("ledger_before")
	var before_keys: Array = []
	if ledger_projection.get("keys") is Array:
		before_keys = (ledger_projection["keys"] as Array).duplicate()
	var persisted: Variant = post.get("ledger_after")
	var after_keys: Array = []
	if persisted is Dictionary:
		# Recorded ORDER, deliberately not a sorted projection order: the
		# projection is a display and this is the persisted document.
		for key: Variant in persisted as Dictionary:
			after_keys.append(str(key))
	var derived_after := int(projection.get("counter_after", 0))
	var key := str(projection.get("ledger_key", ""))
	return {
		"protocol": BootData.PROTOCOL,
		"ok": true,
		"game_version": str(post.get("game_version", "")),
		"server_time": int(post.get("server_time", 0)),
		"result": "success",
		"action": name,
		"command": str(projection.get("command", "")),
		"addressing": {
			"key": str(projection.get("addressing_key", "")),
			"value": int(value),
			"kind": ADDRESSING_KIND,
			"note": "the request names a magic IDENTITY and nothing else; the "
				+ "counter transition is derived from the player's own recorded "
				+ "ledger and the recorded literal cap",
		},
		"counter": {
			"ledger_key": key,
			"before": int(projection.get("counter_before", 0)),
			"present_before": bool(projection.get("counter_present", false)),
			"derived_after": derived_after,
			"derived_change": int(projection.get("change", 0)),
			"recorded_after": recorded_after,
			"legacy_expected_after": recorded_after,
			# False is the NORMAL case for `buy` and for an absent key, and it is
			# the divergence rather than a failure.
			"matches_derived": recorded_after == derived_after,
			"legacy_absent_arm_writes_zero":
				not bool(projection.get("counter_present", false)),
			"cap": int(projection.get("cap", COUNTER_CAP)),
			"capped": bool(projection.get("capped", false)),
			"decreased": false,
			"derived": true,
			"cap_is_literal": CAP_SOURCE_LINES.duplicate(),
			"rejected_cap_derivation": REJECTED_CAP_DERIVATION.duplicate(true),
			"refused_count": CLIENT_DICTATED_REFUSAL.duplicate(true),
			"ledger_before": before_keys.duplicate(),
			"ledger_after": after_keys.duplicate() if persisted is Dictionary \
				else null,
			"ledger_after_keys_are_strings": true if persisted is Dictionary \
				else null,
		},
		"ordering_rule": ORDERING_RULE.duplicate(true),
		"validation_order": VALIDATION_ORDER.duplicate(true),
		"write_step": WRITE_STEP,
		"cap_uniformity": CAP_UNIFORMITY.duplicate(true),
		"legacy_unbounded_arm": LEGACY_UNBOUNDED_ARM.duplicate(true),
		"legacy_decreasing_arm": LEGACY_DECREASING_ARM.duplicate(true),
		"ledger_has_no_readers": LEDGER_HAS_NO_READERS.duplicate(true),
		"no_damage": NO_DAMAGE.duplicate(true),
		"reported_damage_vocabulary": reported_vocabulary(),
		"no_cost_or_reward": NO_COST_OR_REWARD.duplicate(true),
		"no_magic_effect": NO_MAGIC_EFFECT.duplicate(true),
		"divergence": divergences(),
		"divergence_count": DIVERGENCE_COUNT,
		"refusals": WIRE_REFUSALS.duplicate(),
		"provenance": PROVENANCE.duplicate(true),
		"resources": (post.get("resources") as Dictionary).duplicate(true)
			if post.get("resources") is Dictionary else {},
		"resource_count": RESOURCE_COUNT,
		"changed": (post.get("changed") as Array).duplicate(true)
			if post.get("changed") is Array else [],
	}


## Parse a v0 magic envelope -- success or structured error -- into the typed
## result, fail-closed in both directions.
##
## The parser is strict about exactly the claims this line exists to make, and
## lenient about everything else. It re-derives, and does not trust:
##
##   * the **derived** transition, through `derive_counter_transition`, so an
##     answer whose `derived_after` is not the smaller of the cap and one more
##     fails here;
##   * the **recorded** outcome, through `legacy_recorded_after`, so an answer
##     whose `recorded_after` is not what the unchanged branch's own arithmetic
##     writes fails here -- which is what makes this a check rather than an echo;
##   * `matches_derived` against its own two values, so a response cannot report
##     agreement that its own numbers contradict;
##   * the cap against this module's recorded literal **and** the two source lines
##     the literal is read from, so a content-derived cap cannot slip in;
##   * the persisted ledger key order against the recorded order with the created
##     key appended, which is what a `+=` on a present key and an assignment to an
##     absent key do to the document;
##   * the validation order step by step, and every one of the nine recorded
##     refusals, in order.
##
## It refuses a reported `decreased: true` outright: the whole deliverable is a
## transition that never reduces a counter, so an answer claiming one is not a
## transition this client can accept.
##
## ## The recorded divergence, and why `matches_derived` being false is not a
## ## failure
##
## On a corpus whose ledger is empty, the **first** request finds the addressed
## key **absent**. The unchanged branch then takes its `else` arm and writes the
## key at **zero**, incrementing nothing, while the derived transition reads an
## absent entry as zero charges and increments it. So the first answer reports
## `recorded_after` 0 against `derived_after` 1 and `matches_derived` **false**.
## For `buy` it is false every time, because that arm adds rather than assigns and
## so is not bounded by the cap.
##
## Asserting agreement would fail every one of those executions and asserting
## nothing would leave the half vacuous, so the recorded arm's arithmetic is
## derived here and pinned instead, and the two values travel side by side.
static func parse_magic(payload: Variant) -> MagicResult:
	if not (payload is Dictionary):
		return magic_failure("bad_response", "response is not a JSON object")
	var envelope: Dictionary = payload
	if envelope.get("ok") != true:
		return _magic_error(envelope)
	if str(envelope.get("protocol", "")) != BootData.PROTOCOL:
		return magic_failure("protocol_mismatch",
			"expected protocol " + BootData.PROTOCOL + ", got "
				+ str(envelope.get("protocol")))
	if str(envelope.get("result", "")) != "success":
		return magic_failure("bad_response",
			"the magic response did not report the legacy success result")
	if not is_action(envelope.get("action")):
		return magic_failure("bad_response",
			"the magic response names no delivered action")
	var action := str(envelope.get("action"))
	if str(envelope.get("command", "")) != str(ACTION_COMMAND[action]):
		return magic_failure("bad_response",
			"the magic response reports a command the action does not dispatch")

	# --- the counter object, and the transition it claims -------------------
	var counter: Variant = envelope.get("counter")
	if not (counter is Dictionary):
		return magic_failure("bad_response",
			"the magic response carries no counter object")
	var body: Dictionary = counter
	if body.get("derived") != true:
		return magic_failure("bad_response",
			"the magic response does not mark its counter as server-derived, "
				+ "which is the load-bearing claim of this line")
	if body.get("decreased") != false:
		return magic_failure("bad_response",
			"the magic response reports a counter decrease, which is the legacy "
				+ "charge-destroying arm this line refuses; a missing field fails "
				+ "here too, because an absent value is not a boolean false")
	var cap := _wire_int(body.get("cap"))
	if cap != COUNTER_CAP:
		return magic_failure("bad_response",
			"the magic response reports a cap of " + str(cap) + ", not the "
				+ "recorded literal " + str(COUNTER_CAP))
	var lines: Variant = body.get("cap_is_literal")
	if not (lines is Array) or (lines as Array).size() != CAP_SOURCE_LINES.size():
		return magic_failure("bad_response",
			"the magic response omits the two source lines the recorded literal "
				+ "cap is read from")
	for index in range(CAP_SOURCE_LINES.size()):
		if _wire_int((lines as Array)[index]) != int(CAP_SOURCE_LINES[index]):
			return magic_failure("bad_response",
				"the magic response's recorded cap source line disagrees with the "
					+ "preserved source at index " + str(index))
	# The rejected derivation of that cap and the client-dictated-count refusal
	# travel INSIDE the counter object rather than beside it, because they are
	# statements about the counter this answer reports and not about the route.
	for named: String in ["rejected_cap_derivation", "refused_count"]:
		var recorded_body: Variant = body.get(named)
		if not (recorded_body is Dictionary) \
				or (recorded_body as Dictionary).is_empty():
			return magic_failure("bad_response",
				"the magic response's counter omits the recorded " + named
					+ ", so a recorded absence could be read as an omission")
	var before := _wire_int(body.get("before"))
	if before < 0:
		return magic_failure("bad_response",
			"the magic response carries no readable recorded before value")
	var present: Variant = body.get("present_before")
	if not (present is bool):
		return magic_failure("bad_response",
			"the magic response carries no boolean present_before statement")
	var transition := derive_counter_transition(before, cap)
	if not bool(transition["ok"]):
		return magic_failure("bad_response",
			"the magic response reports a before value this client refuses: "
				+ str(transition["error"]))
	var derived_after := _wire_int(body.get("derived_after"))
	if derived_after != int(transition["after"]):
		return magic_failure("bad_response",
			"the magic response's derived transition is " + str(derived_after)
				+ ", not the " + str(int(transition["after"]))
				+ " this client re-derives")
	if _wire_int(body.get("derived_change")) != int(transition["change"]):
		return magic_failure("bad_response",
			"the magic response's derived change disagrees with its own "
				+ "derived_after")
	if body.get("capped") != bool(transition["capped"]):
		return magic_failure("bad_response",
			"the magic response's capped statement disagrees with its own "
				+ "derived_after")
	if int(transition["after"]) < before:
		return magic_failure("bad_response",
			"the magic response's derived transition reduces the counter, which "
				+ "this line refuses in the source and must refuse on the wire")

	# --- the RECORDED outcome, derived from the branch arms -----------------
	var recorded := legacy_recorded_after(action, before, present, cap)
	if not bool(recorded["ok"]):
		return magic_failure("bad_response",
			"no recorded legacy arm exists for this answer: "
				+ str(recorded["error"]))
	var recorded_after := _wire_int(body.get("recorded_after"))
	if recorded_after != int(recorded["after"]):
		return magic_failure("bad_response",
			"the magic response's recorded value is " + str(recorded_after)
				+ ", not the " + str(int(recorded["after"])) + " the unchanged "
				+ str(recorded["arm"]) + " arm writes for a recorded before of "
				+ str(before))
	if _wire_int(body.get("legacy_expected_after")) != int(recorded["after"]):
		return magic_failure("bad_response",
			"the magic response's own legacy expectation disagrees with the "
				+ "recorded value it reports")
	if body.get("matches_derived") != (recorded_after == derived_after):
		return magic_failure("bad_response",
			"the magic response's matches_derived disagrees with its own recorded "
				+ "and derived values")
	if body.get("legacy_absent_arm_writes_zero") != (not bool(present)):
		return magic_failure("bad_response",
			"the magic response's absent-arm statement disagrees with its own "
				+ "present_before")

	# --- the addressing, and the ledger key it must have addressed ----------
	var addressing: Variant = envelope.get("addressing")
	if not (addressing is Dictionary):
		return magic_failure("bad_response",
			"the magic response carries no addressing object")
	var addressing_body: Dictionary = addressing
	if str(addressing_body.get("key", "")) != str(ACTION_ADDRESSING_KEY[action]):
		return magic_failure("bad_response",
			"the magic response reports its addressing under "
				+ str(addressing_body.get("key"))
				+ ", not the action's own wire key")
	if str(addressing_body.get("kind", "")) != ADDRESSING_KIND:
		return magic_failure("bad_response",
			"the magic response reports its addressing as a "
				+ str(addressing_body.get("kind"))
				+ " and not as the recorded magic identity")
	var unwrapped := wire_magic_identity(addressing_body.get("value"))
	if not bool(unwrapped["ok"]):
		return magic_failure("bad_response",
			"the magic response echoes an addressing this client cannot name: "
				+ str(unwrapped["error"]))
	var key := str(ledger_key_for(int(unwrapped["identity"]))["key"])
	if str(body.get("ledger_key", "")) != key:
		return magic_failure("bad_response",
			"the magic response addresses ledger key "
				+ str(body.get("ledger_key", "")) + " while its own addressing "
				+ "names " + key)

	# --- both ledger key orders ---------------------------------------------
	var before_keys: Variant = body.get("ledger_before")
	if not (before_keys is Array):
		return magic_failure("bad_response",
			"the magic response carries no recorded ledger key order")
	for entry: Variant in before_keys as Array:
		if not (entry is String):
			return magic_failure("bad_response",
				"the magic response's recorded ledger key order holds a "
					+ "non-string key, and the ledger is string-keyed")
	var after_keys: Variant = body.get("ledger_after")
	if not (after_keys is Array):
		# The endpoint reports `null` here when the persisted ledger is not a
		# mapping, but it can only reach an answer in that state with a ledger
		# that did not exist before execution -- and it answers that case with
		# its own refusal before writing an envelope at all. So a `null` on a
		# successful answer is refused rather than read as "no keys", which
		# would compare equal to a ledger the action failed to address.
		return magic_failure("bad_response",
			"the magic response carries no persisted ledger key order")
	for entry: Variant in after_keys as Array:
		if not (entry is String):
			return magic_failure("bad_response",
				"the magic response's persisted ledger key order holds a "
					+ "non-string key, and the ledger is string-keyed")
	if body.get("ledger_after_keys_are_strings") != true:
		return magic_failure("bad_response",
			"the magic response does not record that its persisted keys are "
				+ "strings, which is the condition that keeps the order check "
				+ "above answerable")
	var expected_order: Array = (before_keys as Array).duplicate()
	if not expected_order.has(key):
		expected_order.append(key)
	if (after_keys as Array) != expected_order:
		return magic_failure("bad_response",
			"the magic response's persisted ledger key order is not the recorded "
				+ "order with a created key appended, which is what the two arms "
				+ "do to the document")

	# --- the validation order, the write step, and the recorded records -----
	var reported_order: Variant = envelope.get("validation_order")
	if not (reported_order is Array):
		return magic_failure("bad_response",
			"the magic response carries no validation order")
	if (reported_order as Array).size() != VALIDATION_ORDER_STEPS:
		return magic_failure("bad_response",
			"the magic response reports " + str((reported_order as Array).size())
				+ " validation steps, not the " + str(VALIDATION_ORDER_STEPS)
				+ " this client declares")
	for index in range(VALIDATION_ORDER_STEPS):
		var step: Variant = (reported_order as Array)[index]
		if not (step is Dictionary):
			return magic_failure("bad_response",
				"a reported validation step is not an object")
		if not _order_step_agrees(step as Dictionary,
				(VALIDATION_ORDER as Array)[index]):
			return magic_failure("bad_response",
				"the magic response's validation order disagrees with this "
					+ "client's at step " + str(index + 1))
	if _wire_int(envelope.get("write_step")) != WRITE_STEP:
		return magic_failure("bad_response",
			"the magic response reports a write step of "
				+ str(envelope.get("write_step")) + ", not the " + str(WRITE_STEP)
				+ " that follows every check")
	for named: String in ["ordering_rule", "cap_uniformity",
			"legacy_unbounded_arm", "legacy_decreasing_arm",
			"ledger_has_no_readers", "no_damage", "no_cost_or_reward",
			"no_magic_effect", "provenance", "reported_damage_vocabulary"]:
		var record: Variant = envelope.get(named)
		if not (record is Dictionary) or (record as Dictionary).is_empty():
			return magic_failure("bad_response",
				"the magic response omits the recorded " + named + ", so a "
					+ "recorded absence could be read as an omission")

	# --- the refusal vocabulary and the divergence table, both in order -----
	var refusals: Variant = envelope.get("refusals")
	if not (refusals is Array) or (refusals as Array).size() != WIRE_REFUSAL_COUNT:
		return magic_failure("bad_response",
			"the magic response does not carry the " + str(WIRE_REFUSAL_COUNT)
				+ " recorded refusals")
	for index in range(WIRE_REFUSAL_COUNT):
		if str((refusals as Array)[index]) != str(WIRE_REFUSALS[index]):
			return magic_failure("bad_response",
				"the magic response's refusal vocabulary disagrees with this "
					+ "client's at index " + str(index))
	var reported_divergence: Variant = envelope.get("divergence")
	if not (reported_divergence is Array) \
			or (reported_divergence as Array).size() != DIVERGENCE_COUNT:
		return magic_failure("bad_response",
			"the magic response does not carry the " + str(DIVERGENCE_COUNT)
				+ " recorded divergences, which is this line's non-parity claim")
	for index in range(DIVERGENCE_COUNT):
		var entry: Variant = (reported_divergence as Array)[index]
		if not (entry is Dictionary) \
				or str((entry as Dictionary).get("id", "")) \
				!= str((DIVERGENCES[index] as Dictionary).get("id", "")):
			return magic_failure("bad_response",
				"the magic response's divergence table disagrees with this "
					+ "client's at index " + str(index))

	# --- all eight stored resources, and the one changed pointer ------------
	var resources := _wire_resources(envelope.get("resources"))
	if resources.size() != RESOURCE_COUNT:
		return magic_failure("bad_response",
			"the magic response does not carry all " + str(RESOURCE_COUNT)
				+ " stored resource slots; comparing a subset would make the "
				+ "no-price proof weaker than the twelve-transaction measurement")
	if _wire_int(envelope.get("resource_count")) != RESOURCE_COUNT:
		return magic_failure("bad_response",
			"the magic response's own resource count disagrees with the "
				+ "complete slot set")
	var changed: Variant = envelope.get("changed")
	if not (changed is Array):
		return magic_failure("bad_response",
			"the magic response carries no changed-pointer list")
	if (changed as Array).size() != 1 \
			or str((changed as Array)[0]) \
			!= "/" + PRIVATE_STATE_KEY + "/" + LEDGER_KEY + "/" + key:
		return magic_failure("bad_response",
			"the magic response's changed-pointer list does not name exactly the "
				+ "one ledger entry this action addresses")

	var result := MagicResult.new()
	result.ok = true
	result.protocol = BootData.PROTOCOL
	result.result = "success"
	result.game_version = str(envelope.get("game_version", ""))
	result.server_time = BootData._parse_epoch(envelope.get("server_time"))
	if result.server_time < 0:
		return magic_failure("bad_response", "server_time is not a number")
	result.action = action
	result.command = str(envelope.get("command", ""))
	result.addressing_key = str(addressing_body.get("key", ""))
	result.addressing_value = int(unwrapped["identity"])
	result.addressing_kind = str(addressing_body.get("kind", ""))
	result.addressing_note = str(addressing_body.get("note", ""))
	result.ledger_key = key
	result.counter_before = before
	result.counter_present = bool(present)
	result.counter_after = derived_after
	result.change = int(transition["change"])
	result.capped = bool(transition["capped"])
	result.cap = cap
	result.recorded_after = recorded_after
	result.legacy_expected_after = int(recorded["after"])
	result.matches_derived = recorded_after == derived_after
	result.legacy_absent_arm_writes_zero = not bool(present)
	result.decreased = false
	result.derived = true
	result.cap_is_literal = (lines as Array).duplicate()
	result.rejected_cap_derivation = (body.get("rejected_cap_derivation")
		as Dictionary).duplicate(true)
	result.refused_count = (body.get("refused_count") as Dictionary) \
		.duplicate(true)
	result.ledger_before_keys = (before_keys as Array).duplicate()
	result.ledger_after_keys = (after_keys as Array).duplicate()
	result.ledger_after_present = true
	result.ledger_after_keys_are_strings = true
	result.ordering_rule = (envelope.get("ordering_rule") as Dictionary) \
		.duplicate(true)
	result.validation_order = (reported_order as Array).duplicate(true)
	result.write_step = WRITE_STEP
	result.cap_uniformity = (envelope.get("cap_uniformity") as Dictionary) \
		.duplicate(true)
	result.legacy_unbounded_arm = (envelope.get("legacy_unbounded_arm")
		as Dictionary).duplicate(true)
	result.legacy_decreasing_arm = (envelope.get("legacy_decreasing_arm")
		as Dictionary).duplicate(true)
	result.ledger_has_no_readers = (envelope.get("ledger_has_no_readers")
		as Dictionary).duplicate(true)
	result.no_damage = (envelope.get("no_damage") as Dictionary).duplicate(true)
	result.reported_vocabulary = (envelope.get("reported_damage_vocabulary")
		as Dictionary).duplicate(true)
	result.no_cost_or_reward = (envelope.get("no_cost_or_reward") as Dictionary) \
		.duplicate(true)
	result.no_magic_effect = (envelope.get("no_magic_effect") as Dictionary) \
		.duplicate(true)
	result.refusals = (refusals as Array).duplicate()
	result.provenance = (envelope.get("provenance") as Dictionary) \
		.duplicate(true)
	result.proof_halves = PROOF_HALVES.duplicate(true)
	result.divergences = (reported_divergence as Array).duplicate(true)
	result.non_claims = NON_CLAIMS.duplicate()
	result.resources = resources
	result.resource_count = RESOURCE_COUNT
	result.changed = (changed as Array).duplicate()
	return result


# ---------------------------------------------------------------------------
# Private wire helpers
# ---------------------------------------------------------------------------


## The service's own structured error (`{protocol, ok:false, error:{...}}`);
## never a partial payload.
static func _magic_error(envelope: Dictionary) -> MagicResult:
	var code := "bad_response"
	var message := "compatibility API reported an error"
	if envelope.get("ok") == false:
		var error: Variant = envelope.get("error")
		if error is Dictionary:
			code = str((error as Dictionary).get("code", code))
			message = str((error as Dictionary).get("message", message))
	return magic_failure(code, message)


## Whether one reported validation step agrees with this module's own.
##
## Three fields are compared -- the step number, the check's own name, and
## whether it reads player state -- and the rule's **prose** is deliberately not.
## The prose is documentation; the first three are the contract, and comparing
## documentation would make this parser fail on a rewording while catching
## nothing about ordering.
static func _order_step_agrees(actual: Dictionary, expected: Dictionary) -> bool:
	if _wire_int(actual.get("step")) != int(expected.get("step", 0)):
		return false
	if str(actual.get("key", "")) != str(expected.get("key", "")):
		return false
	return actual.get("reads_player_state") == expected.get("reads_player_state")


## All eight stored resource slots, or **nothing** when one is missing or
## unreadable.
##
## The empty dictionary is the failure value and is never a successful result,
## because a success always carries `RESOURCE_COUNT` keys -- so a caller can tell
## the two apart by size and needs no separate flag. A missing slot is refused
## rather than defaulted to zero, because a defaulted zero would compare equal
## across both sides of the no-price proof and make "no resource moved" true for
## a slot nobody read.
static func _wire_resources(raw: Variant) -> Dictionary:
	if not (raw is Dictionary):
		return {}
	var body: Dictionary = raw
	var out := {}
	for name: String in RESOURCE_NAMES:
		if not body.has(name):
			return {}
		var value: Variant = body[name]
		if not _is_integer_valued(value) or int(value) < 0:
			return {}
		out[name] = int(value)
	return out


## An integer field of an answer, or `-1` when it is absent or not an
## integer-valued number. Every numeric field this parser reads is
## non-negative, so `-1` is unambiguous.
static func _wire_int(value: Variant) -> int:
	if not _is_integer_valued(value):
		return -1
	return int(value)