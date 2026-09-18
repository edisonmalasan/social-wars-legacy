"""Offline read-only endpoint catalog verification.

Resolves @app.route registrations in the legacy Flask source with inert AST
analysis (string constants and concatenations only) and checks the reviewed
catalog and readable inventory against it. Never imports or executes the
legacy application. Exit 0 agreement, 1 catalog drift, 2 invalid input or
unsupported source syntax. Standard library only.
"""

import argparse
import ast
import json
from pathlib import Path
import sys

SOURCE_FILE = "server.py"
CATALOG_FILE = Path("docs") / "legacy-protocol" / "endpoints.json"
INVENTORY_FILE = Path("docs") / "legacy-protocol" / "endpoints.md"
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_ROUTES = 256
ACTIVE = "explicit_active"
FRAMEWORK = "framework_default"
DISABLED = "disabled"


class VerificationError(Exception):
    pass


def read_text_file(path, role):
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        raise VerificationError(role + " file missing")
    except OSError:
        raise VerificationError(role + " file unreadable")
    if len(data) > MAX_SOURCE_BYTES:
        raise VerificationError(role + " file too large")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise VerificationError(role + " file not utf-8")


def iter_route_decorators(tree):
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                yield node, decorator
            elif isinstance(decorator, ast.Attribute):
                yield node, decorator
            elif isinstance(decorator, ast.Name):
                yield node, decorator


def _is_route_call(decorator):
    func = decorator.func
    if isinstance(func, ast.Attribute):
        return func.attr == "route" and _is_app_root(func.value)
    if isinstance(func, ast.Name):
        return func.id == "route"
    return False


def _is_app_root(value):
    if isinstance(value, ast.Name):
        return value.id == "app"
    return False


def resolve_route_string(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return node.value
        raise VerificationError("unsupported route expression: non-string constant")
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return resolve_route_string(node.left) + resolve_route_string(node.right)
    raise VerificationError("unsupported route expression")


def declared_methods(decorator):
    for keyword in decorator.keywords:
        if keyword.arg == "methods":
            value = keyword.value
            if not isinstance(value, (ast.List, ast.Tuple, ast.Set)):
                raise VerificationError("unsupported methods expression")
            methods = []
            for element in value.elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    methods.append(element.value.upper())
                else:
                    raise VerificationError("unsupported methods expression")
            return methods
    return None


def effective_methods(declared):
    declared = declared or ["GET"]
    declared = list(dict.fromkeys(declared))
    effective = set(declared)
    if "GET" in effective:
        effective.add("HEAD")
    effective.add("OPTIONS")
    return sorted(effective)


def load_catalog(path):
    catalog = read_text_file(path, "catalog")
    try:
        document = json.loads(catalog)
    except ValueError:
        raise VerificationError("catalog file not valid json")
    if not isinstance(document, dict):
        raise VerificationError("catalog file not valid json")
    if document.get("schema_version") != 1:
        raise VerificationError("catalog schema invalid")
    policy = document.get("policy")
    if not isinstance(policy, dict):
        raise VerificationError("catalog schema invalid")
    for field in ("source_file", "dynamic_root", "static_root", "method_policy", "evidence_policy"):
        if not isinstance(policy.get(field), str) or not policy[field]:
            raise VerificationError("catalog schema invalid: policy field " + field)
    entries = document.get("endpoints")
    if not isinstance(entries, list) or not entries:
        raise VerificationError("catalog schema invalid")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise VerificationError("catalog schema invalid")
        route = entry.get("route")
        for field in ("route", "handler", "classification", "evidence"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise VerificationError("catalog schema invalid: entry field " + field)
        if entry["classification"] not in (ACTIVE, FRAMEWORK, DISABLED):
            raise VerificationError("catalog schema invalid: classification " + entry["classification"])
        declared = entry.get("declared_methods")
        if declared is not None and (not isinstance(declared, list)
                                     or not all(isinstance(m, str) and m for m in declared)):
            raise VerificationError("catalog schema invalid: declared_methods " + entry["route"])
        effective = entry.get("effective_methods")
        if not isinstance(effective, list) or not all(isinstance(m, str) for m in effective):
            raise VerificationError("catalog schema invalid: effective_methods " + entry["route"])
        if entry["classification"] == DISABLED and effective:
            raise VerificationError("catalog schema invalid: disabled entry has effective methods")
        inputs = entry.get("inputs")
        if not isinstance(inputs, dict) or not isinstance(inputs.get("required"), list) \
                or not isinstance(inputs.get("optional"), list) \
                or not isinstance(inputs.get("route_parameters"), list):
            raise VerificationError("catalog schema invalid: inputs " + entry["route"])
        for field in ("responses", "state_effects", "persistence_effects"):
            if not isinstance(entry.get(field), list) or not entry[field]:
                raise VerificationError("catalog schema invalid: field " + field)
        references = entry.get("source_references")
        if not isinstance(references, list) or not references:
            raise VerificationError("catalog schema invalid: source_references " + entry["route"])
        for reference in references:
            if not isinstance(reference, dict) \
                    or not isinstance(reference.get("file"), str) or not reference["file"] \
                    or type(reference.get("line")) is not int or reference["line"] < 1 \
                    or type(reference.get("end_line")) is not int or reference["end_line"] < reference["line"]:
                raise VerificationError("catalog schema invalid: source reference " + entry["route"])
        if route in seen:
            raise VerificationError("catalog schema invalid: duplicate route")
        seen.add(route)
    return document


def validate_source_references(document, root):
    try:
        anchored = root.resolve()
    except OSError:
        raise VerificationError("repository root invalid")
    for entry in document["endpoints"]:
        for reference in entry.get("source_references", []):
            name = reference.get("file")
            try:
                resolved = (root / name).resolve()
                resolved.relative_to(anchored)
            except (OSError, ValueError):
                raise VerificationError(
                    "catalog source reference outside repository: " + entry["route"])
            if not resolved.is_file():
                raise VerificationError(
                    "catalog source reference missing: " + entry["route"])
            content = read_text_file(resolved, "reference")
            total = len(content.splitlines())
            line = reference["line"]
            end_line = reference["end_line"]
            if not 1 <= line <= end_line <= total:
                raise VerificationError(
                    "catalog source reference out of range: " + entry["route"])


def active_catalog_entries(document):
    return [entry for entry in document["endpoints"]
            if entry.get("classification") == ACTIVE]


def collect_string_bindings(tree):
    bindings = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                bindings[node.targets[0].id] = resolve_route_string(node.value)
            except VerificationError:
                bindings[node.targets[0].id] = None
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            try:
                bindings[node.target.id] = resolve_route_string(node.value)
            except VerificationError:
                bindings[node.target.id] = None
    return bindings


def _resolve_name(node, bindings):
    if isinstance(node, ast.Name):
        value = bindings.get(node.id)
        if value is None:
            raise VerificationError("unsupported route expression: unresolved name")
        return value
    return resolve_route_string(node)


def resolve_route_or_name(node, bindings):
    if isinstance(node, ast.Name):
        return _resolve_name(node, bindings)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return (resolve_route_or_name(node.left, bindings)
                + resolve_route_or_name(node.right, bindings))
    return resolve_route_string(node)


def extract_registrations_with_bindings(source_text):
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        raise VerificationError("source file not parseable")
    bindings = collect_string_bindings(tree)
    registrations = []
    for node, decorator in iter_route_decorators(tree):
        if not isinstance(decorator, ast.Call):
            if isinstance(decorator, ast.Attribute) and decorator.attr == "route":
                raise VerificationError("unsupported route expression")
            continue
        if not _is_route_call(decorator):
            continue
        if not decorator.args:
            raise VerificationError("unsupported route expression")
        route = resolve_route_or_name(decorator.args[0], bindings)
        methods = declared_methods(decorator)
        registrations.append({
            "route": route,
            "declared_methods": methods,
            "function": node.name,
        })
        if len(registrations) > MAX_TOTAL_ROUTES:
            raise VerificationError("route limit exceeded")
    return registrations


def check_route_coverage(registrations, document):
    problems = []
    catalog_active = active_catalog_entries(document)
    source_routes = {}
    for registration in registrations:
        source_routes[registration["route"]] = registration
    catalog_routes = {}
    for entry in catalog_active:
        catalog_routes[entry["route"]] = entry
    for route in sorted(set(source_routes) - set(catalog_routes)):
        problems.append("catalog missing active route: " + route)
    for route in sorted(set(catalog_routes) - set(source_routes)):
        problems.append("catalog lists unregistered active route: " + route)
    for route in sorted(set(source_routes) & set(catalog_routes)):
        source_methods = effective_methods(source_routes[route]["declared_methods"])
        catalog_declared = catalog_routes[route].get("declared_methods")
        catalog_effective = catalog_routes[route].get("effective_methods")
        expected_effective = effective_methods(catalog_declared)
        if sorted(catalog_effective or []) != expected_effective:
            problems.append("catalog effective methods inconsistent: " + route)
        if catalog_effective != source_methods:
            problems.append("catalog effective methods drift: " + route)
        source_declared = source_routes[route]["declared_methods"]
        if source_declared is None and catalog_declared is not None or source_declared is not None and catalog_declared is None:
            problems.append("catalog declared methods drift: " + route)
        elif (catalog_declared or []) != (source_declared or []):
            problems.append("catalog declared methods drift: " + route)
    return problems


def check_disabled_entries(registrations, document):
    problems = []
    live_routes = {registration["route"] for registration in registrations}
    disabled = [entry for entry in document["endpoints"]
                if entry.get("classification") == DISABLED]
    for entry in disabled:
        if entry["route"] in live_routes:
            problems.append("disabled entry registered in source: " + entry["route"])
        methods = entry.get("declared_methods")
        if methods and "GET" in methods:
            problems.append("disabled entry unexpected default GET: " + entry["route"])
    return problems


def check_inventory_consistency(document, inventory_text):
    problems = []
    for entry in document["endpoints"]:
        route = entry["route"]
        if route not in inventory_text:
            problems.append("inventory missing route: " + route)
        classification = entry.get("classification")
        if classification == DISABLED and "Disabled" not in inventory_text:
            problems.append("inventory missing disabled labeling")
        if classification == FRAMEWORK and "framework" not in inventory_text.lower():
            problems.append("inventory missing framework labeling")
    if "not implemented" not in inventory_text.lower():
        problems.append("inventory missing alliance placeholder labeling")
    return problems


def compare_and_report(registrations, document, inventory_text):
    problems = []
    problems.extend(check_route_coverage(registrations, document))
    problems.extend(check_disabled_entries(registrations, document))
    problems.extend(check_inventory_consistency(document, inventory_text))
    report = {
        "schema_version": 1,
        "policy": "endpoint-catalog-verification-v1",
        "result": "agreement" if not problems else "drift",
        "active_routes": len(active_catalog_entries(document)),
        "problems": problems,
    }
    return report


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--repo-root", help="repository root to verify (default: current directory)")
    return parser


def run_verification(repo_root):
    root = Path(repo_root)
    if not root.is_dir():
        raise VerificationError("repository root invalid")
    source = read_text_file(root / SOURCE_FILE, "source")
    document = load_catalog(root / CATALOG_FILE)
    validate_source_references(document, root)
    inventory = read_text_file(root / INVENTORY_FILE, "inventory")
    registrations = extract_registrations_with_bindings(source)
    return compare_and_report(registrations, document, inventory)


def main(argv=None):
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        report = run_verification(args.repo_root or ".")
    except VerificationError as error:
        message = str(error)
        print(message, file=sys.stderr)
        return 2
    output = json.dumps(report, indent=2, sort_keys=True) + "\n"

    print(output, end="")
    return 0 if report["result"] == "agreement" else 1


if __name__ == "__main__":
    sys.exit(main())
