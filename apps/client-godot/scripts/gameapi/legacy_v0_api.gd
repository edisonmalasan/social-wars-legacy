extends Node
## `LegacyV0Api` — GameApi implementation that speaks JSON over loopback HTTP
## to Compatibility API v0 (design D5, specs "Boot live against Compatibility
## API" and "Place through either implementation").
##
## This is the ONLY project file allowed to name the compat endpoint or to
## use the built-in HTTP request/enumeration types; the scope test restricts
## those tokens to this path so no boot or presentation code can reach a
## transport (spec: "Keep legacy transport out of the UI"). Only `127.0.0.1`
## is ever dialed — the default endpoint below is the documented loopback
## address of the v0 service (design D3/D9).

const BootData = preload("res://scripts/gameapi/boot_data.gd")

## Loopback default: the v0 service binds 127.0.0.1 only (design D3).
const DEFAULT_ENDPOINT := "http://127.0.0.1:5056"
const SESSION_PATH := "/v0/session"
const BOOTSTRAP_PATH := "/v0/bootstrap"
const PLACE_PATH := "/v0/place"
const REQUEST_TIMEOUT_SECONDS := 30.0

## Endpoint override from the `gameapi/endpoint` setting or the
## `--gameapi-endpoint=` user argument ("" = the loopback default).
var endpoint := ""

var _request: HTTPRequest


func _ready() -> void:
	_request = HTTPRequest.new()
	_request.timeout = REQUEST_TIMEOUT_SECONDS
	add_child(_request)


## Endpoint actually dialed (explicit override or the loopback default).
func resolved_endpoint() -> String:
	if endpoint != "":
		return endpoint
	return DEFAULT_ENDPOINT


## The session list over loopback HTTP; structured failures for unreachable
## endpoints, non-JSON bodies, and v0 structured API errors.
func list_sessions() -> BootData.SaveListResult:
	var outcome := await _call("GET", SESSION_PATH, "")
	if not outcome.get("ok", false):
		return BootData.save_list_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_save_list(outcome.get("payload"))


## Bootstrap over loopback HTTP; same failure rules as `list_sessions()`.
func get_bootstrap(user_id: String) -> BootData.BootstrapResult:
	var outcome := await _call("POST", BOOTSTRAP_PATH,
		JSON.stringify({"user_id": user_id}))
	if not outcome.get("ok", false):
		return BootData.bootstrap_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_bootstrap(outcome.get("payload"), user_id)


## One placement intent over loopback HTTP: the client sends only the
## intent (`user_id`, `item_id`, anchor `x`/`y`, `orientation`) and the
## service derives the legacy envelope server-side (design D3/D4), so the
## typed result's entry and resources are authoritative (design D7).
## Structured service errors pass through with their original codes;
## transport failures keep the boot failure rules — never a partial payload.
func place_building(user_id: String, item_id: int, x: int, y: int,
		orientation: int = 0) -> BootData.PlacementResult:
	var outcome := await _call("POST", PLACE_PATH, JSON.stringify({
		"user_id": user_id,
		"item_id": item_id,
		"x": x,
		"y": y,
		"orientation": orientation,
	}))
	if not outcome.get("ok", false):
		return BootData.placement_failure(
			str(outcome.get("code", "bad_response")),
			str(outcome.get("message", "")))
	return BootData.parse_placement(outcome.get("payload"))


## One HTTP round trip. Success returns `{ok: true, payload: Dictionary}`;
## every failure returns `{ok: false, code, message}` with the failure named.
func _call(method: String, path: String, body: String) -> Dictionary:
	var url := resolved_endpoint() + path
	var headers := PackedStringArray()
	var verb := HTTPClient.METHOD_GET
	if method == "POST":
		headers = PackedStringArray(["Content-Type: application/json"])
		verb = HTTPClient.METHOD_POST
	var request_error := _request.request(url, headers, verb, body)
	if request_error != OK:
		return _failure("request_failed",
			"cannot start the request to %s (error %d)" % [url, request_error])
	var completion: Array = await _request.request_completed
	var transport := int(completion[0])
	var status := int(completion[1])
	var raw: PackedByteArray = completion[3]
	if transport != HTTPRequest.RESULT_SUCCESS:
		return _failure("unreachable_endpoint", _transport_message(transport, url))
	if status == 0:
		return _failure("unreachable_endpoint", "no HTTP response from " + url)
	var parser := JSON.new()
	if parser.parse(raw.get_string_from_utf8()) != OK:
		return _failure("bad_response",
			"response from %s is not JSON (HTTP %d)" % [url, status])
	if not (parser.data is Dictionary):
		return _failure("bad_response",
			"response from %s is not a JSON object (HTTP %d)" % [url, status])
	var payload: Dictionary = parser.data
	if payload.get("ok") == false:
		return _structured_error(payload, status)
	if status < 200 or status >= 300:
		return _failure("bad_response",
			"HTTP %d from %s without a structured error" % [status, url])
	return {"ok": true, "payload": payload}


## The service's own structured error (`{protocol, ok:false, error:{...}}`);
## never a partial payload.
func _structured_error(payload: Dictionary, status: int) -> Dictionary:
	var code := "bad_response"
	var message := "compatibility API reported an error (HTTP %d)" % status
	var error: Variant = payload.get("error")
	if error is Dictionary:
		var typed: Dictionary = error
		code = str(typed.get("code", code))
		message = str(typed.get("message", message))
	return _failure(code, message)


func _failure(code: String, message: String) -> Dictionary:
	return {"ok": false, "code": code, "message": message}


## Names the transport failure the way the boot scene must display it.
## Every branch names the endpoint itself, because the boot scene must show
## *which* endpoint could not be reached, not a generic failure. Observed on
## the pinned engine (Windows x64): a refused loopback port is reported as
## `RESULT_TIMEOUT`, never as `RESULT_CANT_CONNECT`, so the timeout branch is
## the one the unreachable-endpoint scenario actually exercises.
func _transport_message(transport: int, url: String) -> String:
	match transport:
		HTTPRequest.RESULT_CANT_CONNECT:
			return "endpoint unreachable (connection refused): " + url
		HTTPRequest.RESULT_CANT_RESOLVE:
			return "endpoint unreachable (cannot resolve the loopback host): " + url
		HTTPRequest.RESULT_CONNECTION_ERROR:
			return "endpoint unreachable (connection error): " + url
		HTTPRequest.RESULT_TIMEOUT:
			return "endpoint unreachable (no response within %.0f seconds): " % REQUEST_TIMEOUT_SECONDS + url
		HTTPRequest.RESULT_NO_RESPONSE:
			return "endpoint unreachable (no HTTP response): " + url
		_:
			return "endpoint unreachable (transport error %d): %s" % [transport, url]
