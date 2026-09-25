"""Offline first-unit converter (M4: unit package assembly).

Assembles the converted package for `10033_wild_elephant` (Wild
Elephant) from the committed inspection output (frame data, label list,
sprite count), the committed extraction outputs (bitmap files with
digests), the committed normalized units package (content definition),
the source SWF timeline tags (ShowFrame counting, PlaceObject2,
RemoveObject2, FrameLabel, SymbolClass, DefineSprite), and shape
records parsed by the shared style parser (bounds, fill/line arrays,
referenced fill indices), and writes
`assets/converted/units/10033_wild_elephant/` (package.json plus
byte-identical bitmap copies) with the `conversions.json` merge and a
`converted` statuses merge.

Timeline parsing only: depth-first placement decode, frame counting,
and verbatim label names. Matrix, ratio, name, color, clip, and action
payloads are skipped rather than decoded; label names are never mapped
to animation semantics; no edge-record tessellation, rasterization, or
Flash runtime in any form. Standard library only: no legacy
application import, no runtime save reads, no network, server,
browser, or subprocess activity.

Exit 0 prints a success report and writes outputs. Exit 1 prints a
`validation-failed` report and writes nothing. Exit 2 reports invalid
input on stderr.
"""

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import convert_building as shared

POLICY = "unit-conversion-v1"
TARGET_STEM = "10033_wild_elephant"
TARGET_LEGACY_ID = "933"
SOURCE = "assets/sprites/" + TARGET_STEM + ".swf"

NORMALIZED_DIR = shared.NORMALIZED_DIR
UNITS_FILE = NORMALIZED_DIR / "units.json"
REGISTRY_DIR = shared.REGISTRY_DIR
SCHEMA_DIR = shared.SCHEMA_DIR
UNIT_PACKAGE_SCHEMA_FILE = SCHEMA_DIR / "unit_package.schema.json"
CONVERSION_SCHEMA_FILE = shared.CONVERSION_SCHEMA_FILE
CONVERTED_UNITS_DIR = Path("assets") / "converted" / "units"
SCHEMA_VERSION = shared.SCHEMA_VERSION

TAG_END = shared.TAG_END
TAG_SHOW_FRAME = 1
TAG_PLACE_OBJECT2 = 26
TAG_REMOVE_OBJECT2 = 28
TAG_DEFINE_SPRITE = 39
TAG_FRAME_LABEL = 43
TAG_SYMBOL_CLASS = 76

# Control tags outside the recorded subset: refused with context so a
# timeline that would silently lose placements or frames fails closed.
TIMELINE_REFUSED_TAGS = {
    4: "PlaceObject",
    5: "RemoveObject",
    12: "DoAction",
    59: "DoInitAction",
    70: "PlaceObject3",
}

# Definitions and metadata tags that never carry timeline events; they
# are skipped without interpretation.
TIMELINE_IGNORED_TAGS = frozenset((
    2, 6, 8, 9, 10, 11, 13, 14, 17, 18, 19, 20, 21, 22, 24, 25,
    32, 33, 34, 35, 36, 37, 38, 48, 49, 50, 51, 53, 55, 56, 57,
    58, 60, 61, 62, 64, 65, 66, 69, 73, 75, 77, 78, 82, 83, 84,
    86, 87, 88, 89, 90, 91,
))


def load_all(root):
    root = Path(root)
    if not root.is_dir():
        raise shared.InputError("repository root invalid: " + str(root))
    inspection = shared.read_json_file(root / REGISTRY_DIR / "inspection.json",
                                       "swf inspection")
    if not isinstance(inspection, dict):
        raise shared.InputError("swf inspection not object")
    extraction = shared.read_json_file(root / REGISTRY_DIR / "image_extraction.json",
                                       "image extraction")
    if not isinstance(extraction, dict):
        raise shared.InputError("image extraction not object")
    units = shared.read_json_file(root / UNITS_FILE, "normalized units")
    if not isinstance(units, list) or not units:
        raise shared.InputError("normalized units not non-empty array")
    statuses_path = root / REGISTRY_DIR / "statuses.json"
    statuses = {}
    if statuses_path.exists():
        try:
            previous = json.loads(statuses_path.read_text(encoding="utf-8"))
        except ValueError:
            raise shared.InputError("existing statuses file not valid json")
        if not isinstance(previous, dict):
            raise shared.InputError("existing statuses file not object")
        statuses = dict(previous.get("statuses", {}))
    return {"inspection": inspection, "extraction": extraction,
            "units": units, "statuses": statuses}


def parse_place_object2(payload, label):
    """Decode depth-first PlaceObject2 fields; skip optional payloads."""
    if len(payload) < 3:
        raise shared.ValidationFailure(
            ["truncated PlaceObject2 at " + label])
    flags = payload[0]
    depth = struct.unpack("<H", payload[1:3])[0]
    character_id = None
    if flags & 0x02:
        if len(payload) < 5:
            raise shared.ValidationFailure(
                ["truncated PlaceObject2 character id at " + label])
        character_id = struct.unpack("<H", payload[3:5])[0]
    return {"depth": depth, "character_id": character_id,
            "move": bool(flags & 0x01)}


def parse_remove_object2(payload, label):
    if len(payload) != 2:
        raise shared.ValidationFailure(
            ["unexpected RemoveObject2 layout at " + label])
    return {"depth": struct.unpack("<H", payload)[0]}


def parse_frame_label(payload, label):
    """Read a FrameLabel name verbatim; optional named-anchor byte only."""
    terminator = payload.find(b"\x00")
    if terminator < 0:
        raise shared.ValidationFailure(
            ["FrameLabel without terminator at " + label])
    trailing = payload[terminator + 1:]
    if trailing not in (b"", b"\x01"):
        raise shared.ValidationFailure(
            ["unexpected FrameLabel trailing bytes at " + label])
    try:
        name = payload[:terminator].decode("utf-8")
    except UnicodeDecodeError:
        raise shared.ValidationFailure(
            ["FrameLabel name not utf-8 at " + label])
    if not name:
        raise shared.ValidationFailure(
            ["empty FrameLabel at " + label])
    return {"name": name, "anchor": trailing == b"\x01"}


def parse_symbol_class(payload, label):
    if len(payload) < 2:
        raise shared.ValidationFailure(
            ["truncated SymbolClass at " + label])
    count = struct.unpack("<H", payload[:2])[0]
    position = 2
    symbols = []
    for _ in range(count):
        if position + 2 > len(payload):
            raise shared.ValidationFailure(
                ["truncated SymbolClass id at " + label])
        symbol_id = struct.unpack("<H", payload[position:position + 2])[0]
        position += 2
        terminator = payload.find(b"\x00", position)
        if terminator < 0:
            raise shared.ValidationFailure(
                ["SymbolClass name without terminator at " + label])
        try:
            name = payload[position:terminator].decode("utf-8")
        except UnicodeDecodeError:
            raise shared.ValidationFailure(
                ["SymbolClass name not utf-8 at " + label])
        position = terminator + 1
        symbols.append({"id": symbol_id, "name": name})
    if position != len(payload):
        raise shared.ValidationFailure(
            ["unexpected SymbolClass trailing bytes at " + label])
    return symbols


def walk_timeline(body, label, record, state, depth=0):
    """Record one tag stream's timeline events; recurse into sprites.

    `record` collects this stream's (frame, event) tuples; `state`
    collects sprite definitions and the SymbolClass mapping. Returns
    the observed ShowFrame count.
    """
    if depth > 64:
        raise shared.ValidationFailure(
            ["sprite nesting too deep at " + label])
    observed = 0
    position = 0
    while position + 2 <= len(body):
        header = struct.unpack("<H", body[position:position + 2])[0]
        position += 2
        code = header >> 6
        length = header & 0x3F
        if length == 0x3F:
            if position + 4 > len(body):
                raise shared.ValidationFailure(
                    ["truncated long tag length at " + label])
            length = struct.unpack("<I", body[position:position + 4])[0]
            position += 4
        if position + length > len(body):
            raise shared.ValidationFailure(
                ["tag overrun at " + label + ": code " + str(code)])
        payload = body[position:position + length]
        position += length
        if code == TAG_END:
            return observed
        if code == TAG_SHOW_FRAME:
            if payload:
                raise shared.ValidationFailure(
                    ["unexpected ShowFrame payload at " + label])
            observed += 1
        elif code == TAG_PLACE_OBJECT2:
            record["events"].append(
                ("place", observed + 1,
                 parse_place_object2(payload, label)))
        elif code == TAG_REMOVE_OBJECT2:
            record["events"].append(
                ("remove", observed + 1,
                 parse_remove_object2(payload, label)))
        elif code == TAG_FRAME_LABEL:
            record["events"].append(
                ("label", observed + 1,
                 parse_frame_label(payload, label)))
        elif code == TAG_DEFINE_SPRITE:
            if len(payload) < 4:
                raise shared.ValidationFailure(
                    ["truncated sprite header at " + label])
            sprite_id, declared = struct.unpack("<HH", payload[:4])
            if any(entry["sprite_id"] == sprite_id
                   for entry in state["sprites"]):
                raise shared.ValidationFailure(
                    ["duplicate sprite id " + str(sprite_id)
                     + " at " + label])
            child = {"sprite_id": sprite_id, "declared": declared,
                     "events": []}
            state["sprites"].append(child)
            child["observed"] = walk_timeline(
                payload[4:], label + " sprite " + str(sprite_id),
                child, state, depth + 1)
        elif code == TAG_SYMBOL_CLASS:
            if state["symbols"] is not None:
                raise shared.ValidationFailure(
                    ["duplicate SymbolClass tag at " + label])
            state["symbols"] = parse_symbol_class(payload, label)
        elif code in TIMELINE_REFUSED_TAGS:
            raise shared.ValidationFailure(
                ["unsupported timeline tag at " + label + ": code "
                 + str(code) + " (" + TIMELINE_REFUSED_TAGS[code] + ")"])
        elif code in TIMELINE_IGNORED_TAGS:
            continue
        else:
            raise shared.ValidationFailure(
                ["unsupported tag in timeline at " + label + ": code "
                 + str(code)])
    raise shared.ValidationFailure(
        ["tag walk never reached End at " + label])


def finalize_timeline(who, record, declared):
    """Split recorded events into label/placement/removal lists."""
    labels = []
    placements = []
    removes = []
    for kind, frame, data in record["events"]:
        if frame > declared:
            raise shared.ValidationFailure(
                [who + " records " + kind + " beyond declared frame count "
                 + str(declared) + " (frame " + str(frame) + ")"])
        if kind == "label":
            labels.append({"name": data["name"], "frame": frame,
                           "anchor": data["anchor"]})
        elif kind == "place":
            placements.append({"frame": frame,
                               "depth": data["depth"],
                               "character_id": data["character_id"],
                               "character_kind": None,
                               "move": data["move"]})
        else:
            removes.append({"frame": frame, "depth": data["depth"]})
    return {"frame_count": declared, "labels": labels,
            "placements": placements, "removes": removes}


def resolve_characters(timeline, who, shape_ids, sprite_ids):
    """Fill character_kind from defined ids; fail on unknown ids."""
    for placement in timeline["placements"]:
        character_id = placement["character_id"]
        if character_id is None:
            continue
        if character_id in shape_ids:
            placement["character_kind"] = "shape"
        elif character_id in sprite_ids:
            placement["character_kind"] = "sprite"
        else:
            raise shared.ValidationFailure(
                [who + " frame " + str(placement["frame"])
                 + " references undefined character "
                 + str(character_id)])


def build_package(repo_root, out_root):
    root = Path(repo_root)
    layers = load_all(root)
    problems = []
    matches = [entry for entry in layers["units"]
               if isinstance(entry, dict)
               and str(entry.get("legacy_id")) == TARGET_LEGACY_ID
               and entry.get("img_name") == TARGET_STEM]
    if len(matches) != 1:
        raise shared.ValidationFailure(
            ["content ref not unique for unit " + TARGET_STEM
             + " (legacy_id " + TARGET_LEGACY_ID + "): "
             + str(len(matches))])
    content = matches[0]
    entries = layers["inspection"].get("entries", {})
    if SOURCE not in entries or not isinstance(entries[SOURCE], dict):
        raise shared.ValidationFailure(
            ["inspection entry missing for " + SOURCE])
    inspected = entries[SOURCE]
    inspected_sprites = inspected.get("sprite_count")
    if type(inspected_sprites) is not int:
        raise shared.ValidationFailure(
            ["inspection sprite count not integer for " + SOURCE])
    inspected_labels_raw = inspected.get("frame_labels")
    if not isinstance(inspected_labels_raw, list):
        raise shared.ValidationFailure(
            ["inspection frame labels not array for " + SOURCE])
    data = shared.read_bytes_file(root / SOURCE, "swf " + SOURCE)
    try:
        body = shared.decompress_body(data, "swf " + SOURCE)
        width, height, consumed = shared.parse_frame_size(body, "swf " + SOURCE)
        rest = consumed
        rate = struct.unpack("<H", body[rest:rest + 2])[0] / 256.0
        count = struct.unpack("<H", body[rest + 2:rest + 4])[0]
        stream = body[rest + 4:]
        shapes = []
        shape_ids = set()
        for tag, shape_id, payload, context in shared.walk_shape_tags(
                stream, "swf " + SOURCE):
            if shape_id in shape_ids:
                raise shared.ValidationFailure(
                    ["duplicate shape id " + str(shape_id)
                     + " at " + context])
            shape_ids.add(shape_id)
            shapes.append(shared.parse_shape_with_style(
                payload, tag, shape_id, context, collect_refs=True))
        state = {"sprites": [], "symbols": None}
        main_record = {"events": []}
        observed_main = walk_timeline(stream, "swf " + SOURCE,
                                      main_record, state)
    except shared.ValidationFailure as failure:
        raise shared.ValidationFailure(failure.problems)
    if count != observed_main:
        raise shared.ValidationFailure(
            ["declared frame count mismatch for main timeline: declared "
             + str(count) + " observed " + str(observed_main)])
    if len(state["sprites"]) != inspected_sprites:
        raise shared.ValidationFailure(
            ["sprite count mismatch for " + SOURCE + ": inspection "
             + str(inspected_sprites) + " source "
             + str(len(state["sprites"]))])
    for sprite in state["sprites"]:
        if sprite["declared"] != sprite["observed"]:
            raise shared.ValidationFailure(
                ["declared frame count mismatch for sprite "
                 + str(sprite["sprite_id"]) + ": declared "
                 + str(sprite["declared"]) + " observed "
                 + str(sprite["observed"])])
    if state["symbols"] is None:
        raise shared.ValidationFailure(
            ["SymbolClass tag missing for " + SOURCE])
    sprite_ids = {sprite["sprite_id"] for sprite in state["sprites"]}
    main_timeline = finalize_timeline("main timeline", main_record, count)
    timelines = [(main_timeline, "main timeline")]
    for sprite in sorted(state["sprites"],
                         key=lambda entry: entry["sprite_id"]):
        entry = finalize_timeline(
            "sprite " + str(sprite["sprite_id"]), sprite,
            sprite["declared"])
        entry["sprite_id"] = sprite["sprite_id"]
        timelines.append((entry, "sprite " + str(sprite["sprite_id"])))
    recorded_labels = sorted(
        label["name"]
        for timeline, _who in timelines
        for label in timeline["labels"])
    inspected_labels = sorted(str(name) for name in inspected_labels_raw)
    if recorded_labels != inspected_labels:
        raise shared.ValidationFailure(
            ["frame label mismatch against inspection: recorded "
             + repr(recorded_labels) + " inspection "
             + repr(inspected_labels)])
    for timeline, who in timelines:
        resolve_characters(timeline, who, shape_ids, sprite_ids)
    bitmap_by_id = {}
    for bitmap in layers["extraction"].get("bitmaps", []):
        if isinstance(bitmap, dict) and bitmap.get("source") == SOURCE:
            for output in bitmap.get("outputs", []):
                bitmap_by_id.setdefault(
                    bitmap.get("character_id"), []).append(output)
    referenced_ids = []
    for shape in shapes:
        fills = shape["fills"]
        for index in shape["fill_refs"]:
            if index < 1 or index > len(fills):
                raise shared.ValidationFailure(
                    ["fill index out of range at shape "
                     + str(shape["character_id"]) + ": index "
                     + str(index) + " (" + str(len(fills)) + " fills)"])
            fill = fills[index - 1]
            if "bitmap_id" not in fill:
                continue
            bitmap_id = fill["bitmap_id"]
            if bitmap_id == 65535:
                raise shared.ValidationFailure(
                    ["referenced fill uses placeholder bitmap id 65535 at "
                     "shape " + str(shape["character_id"])])
            if bitmap_id not in bitmap_by_id:
                raise shared.ValidationFailure(
                    ["unresolvable bitmap fill at shape "
                     + str(shape["character_id"]) + " -> "
                     + str(bitmap_id)])
            if bitmap_id not in referenced_ids:
                referenced_ids.append(bitmap_id)
    fingerprint = shared.fingerprint_inputs(
        root, (UNITS_FILE, REGISTRY_DIR / "inspection.json",
               REGISTRY_DIR / "image_extraction.json"))
    bitmaps = []
    payloads = {}
    for bitmap_id in referenced_ids:
        for output in bitmap_by_id[bitmap_id]:
            target = (CONVERTED_UNITS_DIR / TARGET_STEM
                      / output["file"].rsplit("/", 1)[-1]).as_posix()
            payloads[target] = shared.read_bytes_file(
                root / output["file"], "extracted " + output["file"])
            bitmaps.append({
                "character_id": bitmap_id,
                "file": target,
                "bytes": len(payloads[target]),
                "sha256": hashlib.sha256(payloads[target]).hexdigest(),
                "expected_sha256": output["sha256"],
            })
    for bitmap in bitmaps:
        if bitmap["sha256"] != bitmap["expected_sha256"]:
            problems.append("bitmap digest mismatch at " + bitmap["file"])
    if problems:
        raise shared.ValidationFailure(problems)
    package = {
        "legacy_id": TARGET_STEM,
        "kind": "converted_unit",
        "source_file": SOURCE,
        "source_layer": "converted(asset-registry)",
        "content_version": fingerprint,
        "content_ref": content,
        "frame_width": width,
        "frame_height": height,
        "frame_rate": rate,
        "frame_count": count,
        "symbols": list(state["symbols"]),
        "main": main_timeline,
        "sprites": [timeline for timeline, _who in timelines[1:]],
        "shapes": shapes,
        "bitmaps": [{key: bitmap[key] for key in
                     ("character_id", "file", "bytes", "sha256")}
                    for bitmap in bitmaps],
    }
    package_schema = shared.load_loose_schema(
        root, UNIT_PACKAGE_SCHEMA_FILE.name)
    problems.extend(shared.validate_against_schema(
        package, package_schema, "converted_unit " + TARGET_STEM))
    if problems:
        raise shared.ValidationFailure(problems)
    package_payload = (json.dumps(package, indent=2, sort_keys=True) + "\n"
                       ).encode("utf-8")
    conversion_schema = shared.load_loose_schema(
        root, CONVERSION_SCHEMA_FILE.name)
    document = shared.merge_conversion_document(root, {
        "legacy_id": TARGET_STEM,
        "directory": (CONVERTED_UNITS_DIR / TARGET_STEM).as_posix(),
        "package_sha256": hashlib.sha256(package_payload).hexdigest(),
        "bitmaps": len(bitmaps),
        "output_bytes": len(package_payload) + sum(
            bitmap["bytes"] for bitmap in bitmaps),
        "policy": POLICY,
    }, {
        "units": UNITS_FILE.as_posix(),
        "inspection": (REGISTRY_DIR / "inspection.json").as_posix(),
        "extraction": (REGISTRY_DIR / "image_extraction.json").as_posix(),
        "units_content_version": fingerprint,
    }, POLICY)
    problems.extend(shared.validate_against_schema(
        document, conversion_schema, "conversion"))
    if problems:
        raise shared.ValidationFailure(problems)
    merged = dict(layers["statuses"])
    merged[SOURCE] = "converted"
    return package, package_payload, document, merged, payloads


def write_outputs(out_root, package, package_payload, document, statuses,
                  payloads):
    out = Path(out_root)
    package_dir = out / CONVERTED_UNITS_DIR / TARGET_STEM
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "package.json").write_bytes(package_payload)
    for relative, payload in payloads.items():
        (out / relative).write_bytes(payload)
    conversions_payload = (json.dumps(document, indent=2, sort_keys=True)
                           + "\n").encode("utf-8")
    statuses_payload = (json.dumps({"schema_version": SCHEMA_VERSION,
                                    "policy": "asset-statuses-v1",
                                    "statuses": statuses},
                                   indent=2, sort_keys=True) + "\n"
                        ).encode("utf-8")
    (out / REGISTRY_DIR).mkdir(parents=True, exist_ok=True)
    (out / REGISTRY_DIR / "conversions.json").write_bytes(
        conversions_payload)
    (out / REGISTRY_DIR / "statuses.json").write_bytes(statuses_payload)
    return {
        "package": {
            "directory": (CONVERTED_UNITS_DIR / TARGET_STEM).as_posix(),
            "bytes": len(package_payload),
            "sha256": hashlib.sha256(package_payload).hexdigest(),
        },
        "conversions": {
            "file": (REGISTRY_DIR / "conversions.json").as_posix(),
            "bytes": len(conversions_payload),
            "sha256": hashlib.sha256(conversions_payload).hexdigest(),
        },
        "statuses": {
            "file": (REGISTRY_DIR / "statuses.json").as_posix(),
            "bytes": len(statuses_payload),
            "sha256": hashlib.sha256(statuses_payload).hexdigest(),
        },
    }


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__,
                                      allow_abbrev=False)
    parser.add_argument("--repo-root",
                        help="repository root to read (default: current directory)")
    parser.add_argument("--out-root",
                        help="conversion root to write (default: same as repo root)")
    return parser


def run_build(repo_root, out_root):
    package, package_payload, document, statuses, payloads = build_package(
        repo_root, out_root)
    digests = write_outputs(out_root, package, package_payload, document,
                            statuses, payloads)
    return package, document, digests


def main(argv=None):
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    repo_root = args.repo_root or "."
    out_root = args.out_root or repo_root
    try:
        _package, document, digests = run_build(repo_root, out_root)
    except shared.ValidationFailure as failure:
        report = {
            "schema_version": SCHEMA_VERSION,
            "policy": POLICY,
            "result": "validation-failed",
            "counts": {},
            "problems": failure.problems,
        }
        print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
        return 1
    except shared.InputError as error:
        print(str(error), file=sys.stderr)
        return 2
    report = {
        "schema_version": SCHEMA_VERSION,
        "policy": POLICY,
        "result": "success",
        "counts": document["counts"],
        "outputs": [digests["package"]["directory"],
                    digests["conversions"]["file"],
                    digests["statuses"]["file"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
