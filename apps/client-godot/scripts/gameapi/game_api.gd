extends Node
## `GameApi` autoload — the only bridge between presentation code and server
## data (design D5, spec "GameApi abstraction").
##
## Boot code calls `list_sessions()` / `get_bootstrap()` and receives typed
## boot data (`scripts/gameapi/boot_data.gd`); raw transport dictionaries
## never reach presentation code, and no other script references a transport.
##
## Implementations, selected by the project setting `gameapi/implementation`
## (default `fake` so tests are hermetic):
##
##   fake      - reads the committed executed-legacy fixtures under
##               `tests/fixtures/godot-compatibility-boot/`; no process,
##               no server, no socket.
##   legacy_v0 - JSON over loopback HTTP to Compatibility API v0 through the
##               built-in HTTP request client; endpoint from the project
##               setting `gameapi/endpoint` (default: loopback 127.0.0.1 on
##               the documented v0 port).
##
## Runtime overrides for verification (user arguments after `--`):
##
##   --gameapi=fake|legacy_v0   implementation switch
##   --gameapi-endpoint=<url>   endpoint override (legacy_v0 only)
##
## verify-boot.ps1 passes these explicitly; nothing outside `legacy_v0_api`
## ever names an endpoint (the scope test enforces that).

const BootData = preload("res://scripts/gameapi/boot_data.gd")
const FakeApi = preload("res://scripts/gameapi/fake_api.gd")
const LegacyV0Api = preload("res://scripts/gameapi/legacy_v0_api.gd")

const SETTING_IMPLEMENTATION := "gameapi/implementation"
const SETTING_ENDPOINT := "gameapi/endpoint"
const IMPL_FAKE := "fake"
const IMPL_LEGACY_V0 := "legacy_v0"
const ARG_IMPLEMENTATION := "--gameapi="
const ARG_ENDPOINT := "--gameapi-endpoint="

## Selected implementation: "fake" or "legacy_v0".
var implementation := IMPL_FAKE
## Endpoint for the legacy-v0 implementation ("" = the loopback default).
var endpoint := ""
## Number of bootstrap requests this process has issued (M6 launch
## contract: exactly one per launch — the legacy bootstrap mutates
## `last_logged_in`, so the boot suite asserts the count and the town
## evidence report records it). Monotonic: `configure()` swaps the
## implementation without hiding history, so callers snapshot and compare.
var bootstrap_requests := 0

## The active implementation node (FakeApi or LegacyV0Api).
var _impl: Variant = null
var _configured := false


func _ready() -> void:
	if _configured:
		return
	configure(_resolve_implementation(), _resolve_endpoint())


## Selects and (re)builds the implementation. Tests call this explicitly to
## pin the implementation under examination; otherwise the selection comes
## from the project setting and the `--gameapi` / `--gameapi-endpoint`
## runtime overrides.
func configure(implementation_name: String, endpoint_url: String = "") -> void:
	var resolved := implementation_name
	if resolved != IMPL_FAKE and resolved != IMPL_LEGACY_V0:
		push_error("[gameapi] unknown implementation %r (expected %r or %r)"
			% [resolved, IMPL_FAKE, IMPL_LEGACY_V0])
		resolved = IMPL_FAKE
	_configured = true
	implementation = resolved
	endpoint = endpoint_url
	if _impl != null:
		_impl.queue_free()
		_impl = null
	if implementation == IMPL_LEGACY_V0:
		var legacy := LegacyV0Api.new()
		legacy.name = "LegacyV0Api"
		legacy.endpoint = endpoint
		add_child(legacy)
		_impl = legacy
	else:
		var fake := FakeApi.new()
		fake.name = "FakeApi"
		add_child(fake)
		_impl = fake


## Typed session list from the selected implementation.
func list_sessions() -> BootData.SaveListResult:
	var result: BootData.SaveListResult = await _impl.list_sessions()
	return result


## Typed bootstrap for one save id from the selected implementation.
func get_bootstrap(user_id: String) -> BootData.BootstrapResult:
	bootstrap_requests += 1
	var result: BootData.BootstrapResult = await _impl.get_bootstrap(user_id)
	return result


## Short transport description for the boot scene's connection state.
func describe_transport() -> String:
	if implementation == IMPL_FAKE:
		return "fake fixtures, offline"
	var legacy := _impl as LegacyV0Api
	if legacy != null:
		return legacy.resolved_endpoint()
	return ""


## The implementation the next call will use, for test assertions.
func implementation_name() -> String:
	return implementation


static func _user_arg(prefix: String) -> String:
	for argument in OS.get_cmdline_user_args():
		if argument.begins_with(prefix):
			return argument.trim_prefix(prefix)
	return ""


func _resolve_implementation() -> String:
	var from_arg := _user_arg(ARG_IMPLEMENTATION)
	if from_arg != "":
		return from_arg
	var from_setting := str(ProjectSettings.get_setting(
		SETTING_IMPLEMENTATION, IMPL_FAKE))
	if from_setting == "":
		return IMPL_FAKE
	return from_setting


func _resolve_endpoint() -> String:
	var from_arg := _user_arg(ARG_ENDPOINT)
	if from_arg != "":
		return from_arg
	return str(ProjectSettings.get_setting(SETTING_ENDPOINT, ""))
