extends RefCounted
## Server v1's own typed **combat-authority** answer, and the parser for it.
##
## ```
## {"result":"success","action":"combat","instant":<int>,
##  "combat":{"unit_id":<int>,"identity_field":"unit_id",
##            "identity_resolved_against":"<str>"},
##  "committed":{"id":"<str>","name":"<str>","type":"<str>","resolved_id":<int>,
##               "combat_fields":{"attack":"<str>", ... nine strings ...},
##               "combat_fields_legacy_consumers":0, "<str>":...},
##  "gates":{"gate_one_team":{...},"gate_two_resurrectable":{...},
##           "enforced":false,"<str>":...},
##  "gates_enforced":false,
##  "team_asymmetry":{...},"destruction":{...},
##  "rows_destroyed":0,
##  "resources_after":{... seven stored balances, all unchanged ...},
##  "stored_resources_compared":[<str>, ...],
##  "proof":[["<str>",true], ... five ordered named checks ...],
##  "leaf_paths_changed":[],
##  "document_unchanged":true,
##  "derived_damage":null,"derived_destruction_count":null,
##  "damage_derived":false,"derivation_performed":null,
##  "ledger_credited":false,"ledger_covered_by":"<str>",
##  "preserved_branch_behaviour":{...},"protocol":"server-v1"}
## ```
##
## ## Why it cannot be `CombatFlow.CombatResult`
##
## `combat_flow.gd` is the projection of the **preserved** server, and it carries
## v0's transaction report: a destruction figure, a `resolve` action, and a
## `recorded_after`. This module carries the opposite claim, and reusing one model
## for both would force a sign convention on three fields that mean different
## things in the two surfaces:
##
## 1. **`rows_destroyed` is always `0`.** Not "usually 0", not "0 so far" —
##    unconditionally `0`, because v1 has no write path at all. A shared field
##    would invite a caller to read a `CombatFlow` result's value as if v1 could
##    produce a non-zero one.
## 2. **The nine `combat_fields` are carried as strings and this module never
##    reads one as a number.** That is the *committed encoding* of the
##    `items` table, and no legacy consumer reads any of them, so a client that
##    parsed `attack` into damage would be inventing the one rule the whole
##    surface exists to refuse. The module's only arithmetic is the
##    whole-number test, and it is applied to `resources_after`, never to
##    `combat_fields`.
## 3. **The gates are reported, never enforced.** `gates_enforced` is a constant
##    `false` and the parser *requires* it to be `false`; a v1 answer claiming it
##    enforced a gate would be a shape this client refuses rather than one it
##    reads.
##
## ## Everything here is reported verbatim
##
## This module computes no damage, no destruction count, no hit chance, and no
## ledger credit. It does **not** re-verify `document_unchanged` or `proof`
## against the store — that is the server's post-execution proof, and redoing it
## here would be a second implementation of a rule the server already owns. What
## it does is refuse every malformed shape, which is the one thing a transport
## must do.
##
## **The only arithmetic-shaped expression in this file** is the whole-number test
## in `_whole_number()`, and it exists because Godot decodes every JSON number as a
## `float`: `7` arrives as `7.0`, and `int()` alone would silently truncate a
## `7.5`.

const BootData = preload("res://scripts/gameapi/boot_data.gd")

## The closed set of stored balance names `resources_after` must carry, exactly
## and completely. The same seven v1 reports and `BootData.Resources` models.
##
## **Seven, not eight.** The legacy eight-slot mutation vector's eighth target is
## read into `unknown` and never written, so `privateState.energy` is not a v1
## stored resource.
const STORED_RESOURCE_NAMES := [
	"xp", "gold", "wood", "oil", "steel", "cash", "mana",
]

## The protocol string v1 stamps on every answer.
const PROTOCOL := "server-v1"

## The only action this delivered v1 route performs.
const ACTION := "combat"

## The nine committed combat columns the server reports verbatim. A **reporting**
## list, not a damage list: no member is read as a number by anything here, and
## `tests/test_combat_v1.gd` asserts this file contains no name from it outside
## this constant.
const REPORTED_COMBAT_FIELDS := [
	"attack", "defense", "life", "attack_interval", "attack_range",
	"best_against", "best_against_mult", "min_level", "syringes",
]

## The ordered proof checks v1 emits, in the order it emits them. **The order is
## the claim**: the leaf census precedes the whole-document comparison, so a
## reader sees the specific before the general. This list pins that order, so a
## server that reordered its own proof would fail the client rather than being
## silently accepted.
const PROOF_CHECKS := [
	"identity_resolved_to_reported_row",
	"reported_gates_match_content_and_state",
	"no_leaf_path_changed",
	"whole_document_unchanged",
	"resources_unchanged",
]

## The preserved-branch behaviour table. Its **five** members are required and
## none is required to say anything in particular: this is quoted prose, and the
## client executes none of it.
const BEHAVIOUR_KEYS := [
	"absent_value", "destruction", "ledger", "reached",
]

## Client-LOCAL codes. **These are not v1 refusal codes**: they never reach the
## server, so they cannot be in `server_v1_refusals.REFUSAL_HTTP_STATUS`.
## `unsupported` means "v1 has no such route"; `bad_request` means "v1 answered
## something this parser refuses to guess at". Every code v1 itself refuses
## travels through `error_code` **verbatim**, in the same field, so a caller
## reads one field whatever refused the request.
const CODE_UNSUPPORTED := "unsupported_by_server_v1"
const CODE_BAD_REQUEST := "bad_request"


## v1's **addressing decision** for one combat identity, exactly as it reports it.
##
## `unit_id` is the committed identity the client named and the server resolved.
## It is carried beside `identity_resolved_against` rather than alone, because
## the resolution is the part of this answer that is genuinely derived: the id was
## checked against the committed rows whose `type` column is `u`, and a reader
## cannot tell that from the id alone.
class CombatIdentity:
	extends RefCounted
	var unit_id := -1
	var identity_field := ""
	var identity_resolved_against := ""


## One reported `push_dead_unit` gate. Every field is the server's; this class
## adds none and reads none of them as a rule.
##
## The two gates are deliberately **separate classes** rather than one with a
## `kind` tag: their fields do not overlap, and a merged class with nullable
## fields could not tell "absent" from "not applicable to this gate", which is
## exactly the distinction this surface exists to preserve.
class TeamGate:
	extends RefCounted
	var row_present := false
	var row_count := 0
	## Every recorded row carrying the addressed identity, in stored order.
	var rows: Array = []
	var recorded_team: Variant = null
	## **Null** when no row is present — reported as absent, never as `false`.
	var every_row_would_pass: Variant = null
	var any_row_would_pass: Variant = null


class ResurrectableGate:
	extends RefCounted
	## False when the committed `properties` object has no `resurrectable` key.
	## The preserved helper returns `False` on an absent key rather than reading
	## one, so absent is a committed fact and is never collapsed into zero.
	var present := false
	## The committed value verbatim — a **string** in the committed table.
	var committed_value: Variant = null
	## **Null** when `present` is false.
	var would_pass: Variant = null
	var absent_is_read_as_zero := false


## v1's typed answer to one combat intent.
##
## On success `ok` is true and every field below is populated from the response;
## on refusal `ok` is false, `error_code` carries v1's own code verbatim, and
## **every other field stays at its default** — there is no partial payload.
class CombatAuthorityResult:
	extends RefCounted
	var ok := false
	## `"server-v1"` on every answer v1 produced; "" on a local failure.
	var protocol := ""
	## `"combat"` on success; "" on failure. The action the server says it ran, so
	## a caller cannot read a combat answer as some other action's.
	var action := ""
	## The instant the server recorded for the transaction. **The preserved branch
	## records no instant at all**, so nothing in the store holds it.
	var instant := 0
	## The addressing decision, or null on failure.
	var combat: CombatIdentity = null
	## The committed unit row, verbatim, plus the nine unreported-as-numbers
	## combat columns.
	var committed_id := ""
	var committed_name := ""
	var committed_type := ""
	var resolved_id := -1
	## The nine committed combat columns, **as the strings the committed table
	## stores**. Nothing in this module reads one of these as a number.
	var combat_fields: Dictionary = {}
	var team_gate: TeamGate = null
	var resurrectable_gate: ResurrectableGate = null
	## Always false on a success this client accepts. A v1 answer claiming it
	## enforced a gate is refused.
	var gates_enforced := false
	var team_asymmetry: Dictionary = {}
	var destruction: Dictionary = {}
	## **Always 0** on a success this client accepts.
	var rows_destroyed := 0
	var resources_after: BootData.Resources = null
	var stored_resources_compared: Array = []
	## The ordered `(check, held)` pairs. On a success every entry is `true`;
	## a false entry means the server's own proof did not hold and the whole
	## answer is refused rather than modelled.
	var proof: Array = []
	var leaf_paths_changed: Array = []
	## The falsifiable half of the proof: whether the **whole** persisted document
	## was byte-identical across the transaction.
	var document_unchanged := false
	## Reported as explicit nulls rather than absent keys, so "nothing was
	## derived" can never be confused with "the answer said nothing about it".
	var derived_damage: Variant = null
	var derived_destruction_count: Variant = null
	var damage_derived := false
	var derivation_performed: Variant = null
	## Always false on a success this client accepts: v1 credits nothing.
	var ledger_credited := false
	var preserved_branch_behaviour: Dictionary = {}
	# --- populated on refusal only -------------------------------------------
	var error_code := ""
	var error_message := ""
	var error_detail: Dictionary = {}


## The local failure factory. `code` and `message` are echoed verbatim; `detail` is
## copied, never merged into the success fields, so a refused answer cannot leave
## a half-populated success object behind.
static func combat_failure(code: String, message: String,
		detail: Dictionary = {}) -> CombatAuthorityResult:
	var result := CombatAuthorityResult.new()
	result.ok = false
	result.error_code = code
	result.error_message = message
	result.error_detail = detail.duplicate()
	return result


## Builds the typed result from v1's payload, failing CLOSED on every malformed
## shape. A refused answer keeps v1's own code, message and detail; a success is
## only built when **every** documented field is present and well-typed.
static func parse_combat_authority(payload: Variant) -> CombatAuthorityResult:
	if not (payload is Dictionary):
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer is not a JSON object")
	var body: Dictionary = payload
	var kind := str(body.get("result", ""))
	if kind == "refused":
		return _refusal(body)
	if kind != "success":
		# `%s`, never `%r`: this engine has no `%r` format character and reports
		# it as an engine ERROR line even though the statement completes, which
		# would fail `verify-boot.ps1` on a suite that reported itself green.
		var seen := "<absent>" if not body.has("result") else str(body["result"])
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer carries no recognised result field: %s" % seen)
	return _success(body)


## A v1 refusal, verbatim. No field is derived from it and none is defaulted.
static func _refusal(body: Dictionary) -> CombatAuthorityResult:
	var code := str(body.get("code", ""))
	if code == "":
		return combat_failure(CODE_BAD_REQUEST,
			"a refused v1 answer carries no code")
	var detail: Variant = body.get("detail", {})
	if not (detail is Dictionary):
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 refusal detail is not an object")
	var result := combat_failure(code, str(body.get("message", "")), detail)
	result.protocol = str(body.get("protocol", ""))
	return result


## A v1 success, or a closed refusal. Nothing is defaulted.
static func _success(body: Dictionary) -> CombatAuthorityResult:
	if str(body.get("protocol", "")) != PROTOCOL:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer is not stamped %s" % PROTOCOL)
	if str(body.get("action", "")) != ACTION:
		return combat_failure(CODE_BAD_REQUEST, "the v1 combat answer reports action %s"
			% str(body.get("action", "")))
	var instant: Variant = _whole_number(body.get("instant", null))
	if instant == null:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer carries no whole-number instant")
	var identity: CombatIdentity = _identity(body.get("combat", null))
	if identity == null:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer carries no usable combat block")
	var committed: Variant = _committed(body.get("committed", null))
	if committed == null:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer carries no complete committed report")
	var gates: Variant = _gates(body.get("gates", null))
	if gates == null:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer carries no usable gates report")
	if gates["enforced"]:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer claims it enforced a gate, and this client "
			+ "refuses to model an enforced gate it was told does not exist")
	if bool(body.get("gates_enforced", null)):
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer reports gates_enforced true, which its own "
			+ "gates block contradicts")
	var balances: BootData.Resources = _resources(body.get("resources_after", null))
	if balances == null:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer carries no complete stored balance set")
	var compared: Variant = _string_list(body.get("stored_resources_compared", null))
	if compared == null:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer carries no stored-resource comparison list")
	# The list is what makes the "no stored resource moved" half of v1's proof
	# checkable, so it must name **exactly** the seven stored balances. A list
	# naming an eighth is not a longer answer: it is a claim about a balance
	# this client cannot read.
	if compared != _sorted(STORED_RESOURCE_NAMES):
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer compares %s, which is not the seven stored balances"
				% str(compared))
	var proof: Variant = _proof(body.get("proof", null))
	if proof == null:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer carries no usable ordered proof")
	var changed: Variant = _string_list(body.get("leaf_paths_changed", null))
	if changed == null:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer carries no leaf-path list")
	# **Empty, not merely present.** An answer listing a changed leaf path is a
	# report of a transaction that mutated something, and this client has no way to
	# model that: the whole delivered contract is "the report resolves an identity
	# and nothing moves". The first draft accepted any list of strings here, and
	# the fail-closed walk found it -- a non-empty list parsed into a success whose
	# own `leaf_paths_changed` field then said the opposite of its `ok`.
	if (changed as Array).size() != 0:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer reports a changed leaf path, which this client refuses because v1 has no write path")
	if not body.get("document_unchanged", null) is bool:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer carries no boolean document_unchanged")
	# **True, not merely boolean.** The same reasoning: `false` is a report that the
	# document moved, and it is refused here rather than carried as a success whose
	# `document_unchanged` field is falsifiable but whose `ok` is not.
	if not bool(body["document_unchanged"]):
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer admits the document moved, which this client refuses because v1 has no write path")
	# The three explicit "nothing was derived" nulls. Their presence is the
	# claim; a missing key would make an absent field read as an unstated one.
	for field in ["derived_damage", "derived_destruction_count",
			"derivation_performed"]:
		if not body.has(field) or body[field] != null:
			return combat_failure(CODE_BAD_REQUEST,
				"the v1 combat answer does not report %s as an explicit null"
				% field)
	if bool(body.get("damage_derived", null)):
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer claims it derived damage")
	if bool(body.get("ledger_credited", null)):
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer claims it credited the dead-hero ledger")
	var destroyed: Variant = _whole_number(body.get("rows_destroyed", null))
	if destroyed == null or int(destroyed) != 0:
		return combat_failure(CODE_BAD_REQUEST,
		"the v1 combat answer reports rows_destroyed %s, which this client refuses because v1 has no write path"
			% str(body.get("rows_destroyed", "<absent>")))
	var behaviour: Variant = _behaviour(body.get("preserved_branch_behaviour", null))
	if behaviour == null:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer carries no complete preserved-behaviour table")
	var asymmetry: Variant = _report_block(body.get("team_asymmetry", null))
	if asymmetry == null:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer carries no team-asymmetry report")
	var destruction: Variant = _report_block(body.get("destruction", null))
	if destruction == null:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer carries no destruction report")
	if destruction.get("applied", null) != false:
		return combat_failure(CODE_BAD_REQUEST,
			"the v1 combat answer reports a destruction it applied")

	var result := CombatAuthorityResult.new()
	result.ok = true
	result.protocol = PROTOCOL
	result.action = ACTION
	result.instant = int(instant)
	result.combat = identity
	result.committed_id = committed["id"]
	result.committed_name = committed["name"]
	result.committed_type = committed["type"]
	result.resolved_id = committed["resolved_id"]
	result.combat_fields = committed["combat_fields"]
	result.team_gate = gates["team"]
	result.resurrectable_gate = gates["resurrectable"]
	result.gates_enforced = false
	result.team_asymmetry = asymmetry
	result.destruction = destruction
	result.rows_destroyed = 0
	result.resources_after = balances
	result.stored_resources_compared = compared
	result.proof = proof
	result.leaf_paths_changed = changed
	result.document_unchanged = bool(body["document_unchanged"])
	result.derived_damage = null
	result.derived_destruction_count = null
	result.damage_derived = false
	result.derivation_performed = null
	result.ledger_credited = false
	result.preserved_branch_behaviour = behaviour
	return result


static func _identity(value: Variant) -> CombatIdentity:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	var unit: Variant = _whole_number(source.get("unit_id", null))
	if unit == null:
		return null
	if not (source.get("identity_field", null) is String):
		return null
	if not (source.get("identity_resolved_against", null) is String):
		return null
	var out := CombatIdentity.new()
	out.unit_id = int(unit)
	out.identity_field = str(source["identity_field"])
	out.identity_resolved_against = str(source["identity_resolved_against"])
	return out


## The committed unit row. `combat_fields` is required to carry **exactly** the
## nine reported columns, each of them a **string** — the committed encoding. A
## number here would mean the server parsed a committed column it says it never
## reads, and this client refuses rather than accepting a nicer answer.
static func _committed(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	for key in ["id", "name", "type"]:
		if not (source.get(key, null) is String):
			return null
	var resolved: Variant = _whole_number(source.get("resolved_id", null))
	if resolved == null:
		return null
	var fields: Variant = source.get("combat_fields", null)
	if not (fields is Dictionary):
		return null
	var table: Dictionary = fields
	if table.size() != REPORTED_COMBAT_FIELDS.size():
		return null
	var out_fields: Dictionary = {}
	for name in REPORTED_COMBAT_FIELDS:
		if not table.has(name):
			return null
		if not (table[name] is String):
			return null
		out_fields[name] = str(table[name])
	return {
		"id": str(source["id"]),
		"name": str(source["name"]),
		"type": str(source["type"]),
		"resolved_id": int(resolved),
		"combat_fields": out_fields,
	}


## Both reported gates. Returns `{"team": TeamGate, "resurrectable":
## ResurrectableGate, "enforced": bool}` or null.
##
## The team gate's per-row list is kept **whole** rather than summarised, because
## "how many rows carry this identity" is a fact about the addressed identity and
## not a detail: an identity with zero rows, one row and several rows are three
## different answers, and a client that read only a count could not tell them
## apart from a gate verdict.
static func _gates(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	if not (source.get("enforced", null) is bool):
		return null
	var team_value: Variant = source.get("gate_one_team", null)
	if not (team_value is Dictionary):
		return null
	var team_source: Dictionary = team_value
	if not (team_source.get("row_present", null) is bool):
		return null
	var count: Variant = _whole_number(team_source.get("row_count", null))
	if count == null:
		return null
	var rows: Variant = team_source.get("rows", null)
	if not (rows is Array):
		return null
	var team := TeamGate.new()
	team.row_present = bool(team_source["row_present"])
	team.row_count = int(count)
	team.rows = rows.duplicate()
	team.recorded_team = team_source.get("recorded_team", null)
	team.every_row_would_pass = team_source.get("every_row_would_pass", null)
	team.any_row_would_pass = team_source.get("any_row_would_pass", null)
	# A gate with no input must report **null** verdicts. A `false` verdict on an
	# absent row is a committed fact the preserved helper never states: it
	# returns False on an absent key rather than reading one.
	if not team.row_present:
		if team.rows.size() != 0:
			return null
		if team.every_row_would_pass != null or team.any_row_would_pass != null:
			return null
		if team.recorded_team != null:
			return null

	var flag_value: Variant = source.get("gate_two_resurrectable", null)
	if not (flag_value is Dictionary):
		return null
	var flag_source: Dictionary = flag_value
	if not (flag_source.get("present", null) is bool):
		return null
	if not (flag_source.get("absent_is_read_as_zero", null) is bool):
		return null
	var resurrectable := ResurrectableGate.new()
	resurrectable.present = bool(flag_source["present"])
	resurrectable.absent_is_read_as_zero = bool(
		flag_source["absent_is_read_as_zero"])
	resurrectable.committed_value = flag_source.get("committed_value", null)
	resurrectable.would_pass = flag_source.get("would_pass", null)
	if resurrectable.absent_is_read_as_zero:
		return null
	# An absent committed key and a committed zero are different facts. The
	# parser therefore forbids the one combination that would collapse them.
	if not resurrectable.present:
		if resurrectable.committed_value != null or resurrectable.would_pass != null:
			return null
	if resurrectable.present:
		if not (resurrectable.committed_value is String):
			return null
		if not (resurrectable.would_pass is bool):
			return null
	return {
		"team": team,
		"resurrectable": resurrectable,
		"enforced": bool(source["enforced"]),
	}


## The ordered proof, pinned to :data:`PROOF_CHECKS` in that exact order.
##
## Every entry must be `true`. A false entry means the server's own proof did not
## hold, and modelling that answer would report a destruction this client has no
## way to interpret — so the whole answer is refused.
static func _proof(value: Variant) -> Variant:
	if not (value is Array):
		return null
	var source: Array = value
	if source.size() != PROOF_CHECKS.size():
		return null
	var out: Array = []
	for index in range(PROOF_CHECKS.size()):
		var entry: Variant = source[index]
		if not (entry is Array):
			return null
		var pair: Array = entry
		if pair.size() != 2:
			return null
		if str(pair[0]) != str(PROOF_CHECKS[index]):
			return null
		if not (pair[1] is bool):
			return null
		if not bool(pair[1]):
			return null
		out.append([str(pair[0]), true])
	return out


static func _resources(value: Variant) -> BootData.Resources:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	if source.size() != STORED_RESOURCE_NAMES.size():
		return null
	var out := BootData.Resources.new()
	for name in STORED_RESOURCE_NAMES:
		if not source.has(name):
			return null
		var amount: Variant = _whole_number(source[name])
		if amount == null:
			return null
		out.set(str(name), int(amount))
	return out


## A list of strings. An **empty** list is accepted and kept distinct from an
## absent one: "the server changed no leaf" is a reportable answer and "the answer
## said nothing" is not.
static func _string_list(value: Variant) -> Variant:
	if not (value is Array):
		return null
	var out: Array = []
	for entry in value:
		if not (entry is String):
			return null
		out.append(str(entry))
	return out


## A report block: every value copied **with its JSON kind intact**, so a boolean
## stays a boolean, a number stays a number and an explicit null stays a null. A
## member may itself be a mapping of the same kinds, which the observed answers
## require once (`destruction.rejected_alternatives`); a list anywhere is refused.
##
## Requiring each **named** member would pin prose the client does not read, and
## requiring nothing would let a missing report pass — so the block is checked for
## shape and read by name, and nothing in it is stringified.
##
## **Corrected premise.** This helper's first draft claimed both report blocks hold
## "every value quoted prose" and stringified accordingly. The observed answers
## falsify that: `destruction.applied`, `destruction.count_derived` and
## `team_asymmetry.reconciled` are JSON booleans, `destruction.refused_status` is a
## number, `destruction.count` is an explicit null, and `rejected_alternatives` is a
## nested mapping. Stringifying turned `applied` into the string `"false"`, so
## `destruction["applied"] != false` raised a typed-operand engine error instead of
## returning, and **no real answer could ever be accepted**. The kind-preserving
## rule below is what makes the boolean refusal check below a check, not a crash.
static func _report_block(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var out: Dictionary = {}
	for key in value:
		var entry: Variant = value[key]
		if entry == null or entry is bool or entry is String:
			out[str(key)] = entry
		elif entry is int or entry is float:
			# `_whole_number` already returns an int, so no `int()` is applied to
			# the reported value here and the module's own "never int() a
			# reported number outside that test" rule stays literally true.
			var amount: Variant = _whole_number(entry)
			if amount == null:
				return null
			out[str(key)] = amount
		elif entry is Dictionary:
			var nested: Variant = _report_block(entry)
			if nested == null:
				return null
			out[str(key)] = nested
		else:
			# A list inside a report is not a shape this client reads, and
			# accepting one would model prose it never inspects.
			return null
	return out


static func _behaviour(value: Variant) -> Variant:
	if not (value is Dictionary):
		return null
	var source: Dictionary = value
	for key in BEHAVIOUR_KEYS:
		if not source.has(key):
			return null
		if not (source[key] is String):
			return null
	var out: Dictionary = {}
	for key in source:
		out[str(key)] = str(source[key])
	return out


static func _sorted(names: Array) -> Array:
	var out: Array = names.duplicate()
	out.sort()
	return out


## A JSON number that really is a whole number, or null.
##
## Godot decodes **every** JSON number as a `float`, so `7` arrives as `7.0` and
## `7.5` arrives as `7.5`. Comparing against the rounded value is therefore the
## only honest whole-number test available on this engine, and it is why
## `int()` alone is never used to validate a reported number: it would accept
## `7.5` by truncating it, which would be a silently wrong id or balance.
static func _whole_number(value: Variant) -> Variant:
	if not (value is float or value is int):
		return null
	if float(value) != floor(float(value)):
		return null
	return int(value)