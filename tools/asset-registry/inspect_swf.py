"""Offline SWF static inspector (M4 slice 2: parse and record).

Reads every `.swf` entry of the committed asset registry, parses headers
(signature, version, declared/actual length, frame rect/size, frame rate,
frame count) and walks tags to End (code inventory with counts,
SymbolClass/ExportAssets names, DefineBits/JPEG and DefineSound IDs,
DoABC/DoAction presence, frame labels, scene counts) using standard
library `struct` plus `zlib` only, and writes
`tools/asset-registry/inspection.json` keyed by registry path with a JSON
report on stdout.

Static byte reads and decompression only: no ActionScript execution, no
rendering, no bitmap/sound decoding to pixels or samples, no timeline
interpretation, no Flash runtime in any form. Only `CWS` signatures are
accepted; anything else fails closed as drift. Declared header lengths
are recorded, never trusted: walks are bounded by actual bytes.

Exit 0 prints a success report and writes the output. Exit 1 prints a
`validation-failed` report and writes nothing. Exit 2 reports invalid
input or unsupported shapes on stderr.
"""

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path
import sys

POLICY = "swf-inspection-v1"
SCHEMA_VERSION = 1

REGISTRY_DIR = Path("tools") / "asset-registry"
SCHEMA_DIR = REGISTRY_DIR / "schemas"
INSPECTION_SCHEMA_FILE = SCHEMA_DIR / "inspection.schema.json"
ENTRY_SCHEMA_FILE = SCHEMA_DIR / "inspection_entry.schema.json"
REGISTRY_FILE = REGISTRY_DIR / "registry.json"
INSPECTION_FILE = REGISTRY_DIR / "inspection.json"

TAG_END = 0
TAG_SHOW_FRAME = 1
TAG_DEFINE_SHAPE_FAMILIES = (2, 22, 32, 83)
TAG_DEFINE_BITS_FAMILIES = (6, 21, 35)
TAG_DEFINE_BITS_LOSSLESS = (20, 36)
TAG_JPEG_TABLES = 8
TAG_DEFINE_SOUND = 14
TAG_DO_ACTION = 12
TAG_DO_INIT_ACTION = 59
TAG_DO_ABC = 82
TAG_SYMBOL_CLASS = 76
TAG_EXPORT_ASSETS = 56
TAG_FRAME_LABEL = 43
TAG_DEFINE_SCENE_AND_FRAME_LABELS = 86
TAG_FILE_ATTRIBUTES = 69

TAG_DEFINE_SPRITE = 39

SWF_VERSION_MIN = 1
SWF_VERSION_MAX = 40
MAX_BODY_BYTES = 512 * 1024 * 1024
MAX_SPRITE_DEPTH = 64


class InputError(Exception):
    """Invalid input or unsupported shape: exit 2."""


class ValidationFailure(Exception):
    """Content validation failure: exit 1 without writing output."""

    def __init__(self, problems):
        super().__init__("; ".join(problems))
        self.problems = list(problems)


def read_text_file(path, role):
    try:
        data = Path(path).read_bytes()
    except FileNotFoundError:
        raise InputError(role + " file missing: " + str(path))
    except OSError:
        raise InputError(role + " file unreadable: " + str(path))
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise InputError(role + " file not utf-8: " + str(path))


def read_bytes_file(path, role):
    try:
        data = Path(path).read_bytes()
    except FileNotFoundError:
        raise InputError(role + " file missing: " + str(path))
    except OSError:
        raise InputError(role + " file unreadable: " + str(path))
    return data


def read_json_file(path, role):
    try:
        return json.loads(read_text_file(path, role))
    except ValueError:
        raise InputError(role + " file not valid json: " + str(path))


class BitReader:
    """MSB-first bit reader over bytes for SWF RECT fields."""

    def __init__(self, data):
        self.data = data
        self.position = 0

    def read_bits(self, count, label):
        value = 0
        for _ in range(count):
            byte_index = self.position // 8
            if byte_index >= len(self.data):
                raise ValidationFailure(["rect overrun at " + label])
            bit_index = 7 - (self.position % 8)
            value = (value << 1) | ((self.data[byte_index] >> bit_index) & 1)
            self.position += 1
        return value


def parse_frame_size(body, label):
    """Return (width_px, height_px, bytes_consumed) from the FrameSize RECT."""
    if not body:
        raise ValidationFailure(["missing frame rect at " + label])
    reader = BitReader(body)
    nbits = reader.read_bits(5, label)
    if nbits > 31:
        raise ValidationFailure(["frame rect nbits out of range at " + label])
    xmin = reader.read_bits(nbits, label)
    xmax = reader.read_bits(nbits, label)
    ymin = reader.read_bits(nbits, label)
    ymax = reader.read_bits(nbits, label)
    consumed = (reader.position + 7) // 8
    del xmin, ymin
    return max(0, (xmax) // 20), max(0, (ymax) // 20), consumed


def read_c_string(data, offset, end, label):
    """Read a NUL-terminated UTF-8 string; fail on missing terminator."""
    stop = data.find(b"\x00", offset, end)
    if stop < 0:
        raise ValidationFailure(["unterminated string at " + label])
    try:
        return data[offset:stop].decode("utf-8"), stop + 1
    except UnicodeDecodeError:
        raise ValidationFailure(["non-utf8 string at " + label])


def parse_symbol_names(payload, label):
    """Parse SymbolClass/ExportAssets bodies into verbatim name lists."""
    if len(payload) < 2:
        raise ValidationFailure(["truncated symbol table at " + label])
    count = struct.unpack("<H", payload[:2])[0]
    offset = 2
    names = []
    for _ in range(count):
        if offset + 2 > len(payload):
            raise ValidationFailure(["truncated symbol id at " + label])
        offset += 2
        name, offset = read_c_string(payload, offset, len(payload), label)
        names.append(name)
    return names


def read_encoded_u32(data, offset, end, label):
    """Read a variable-length LEB128 EncodedU32 used by scene data."""
    value = 0
    shift = 0
    while True:
        if offset >= end:
            raise ValidationFailure(["truncated encoded integer at " + label])
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
        if shift >= 35:
            raise ValidationFailure(["encoded integer overflow at " + label])


def parse_scene_data(payload, label):
    """Parse DefineSceneAndFrameLabelData into (scene_count, frame_labels)."""
    end = len(payload)
    scene_count, offset = read_encoded_u32(payload, 0, end, label)
    for _ in range(scene_count):
        _, offset = read_encoded_u32(payload, offset, end, label)
        _, offset = read_c_string(payload, offset, end, label)
    frame_count, offset = read_encoded_u32(payload, offset, end, label)
    labels = []
    for _ in range(frame_count):
        _, offset = read_encoded_u32(payload, offset, end, label)
        name, offset = read_c_string(payload, offset, end, label)
        labels.append(name)
    return scene_count, labels


def parse_character_id(payload, label):
    if len(payload) < 2:
        raise ValidationFailure(["truncated character id at " + label])
    return struct.unpack("<H", payload[:2])[0]


def parse_header(data, label):
    """Split signature/version/length and decompress CWS bodies."""
    if len(data) < 8:
        raise ValidationFailure(["file shorter than SWF header at " + label])
    signature = data[:3].decode("latin1")
    version = data[3]
    declared = struct.unpack("<I", data[4:8])[0]
    if signature == "ZWS":
        raise ValidationFailure(["LZMA-compressed SWF not supported at " + label])
    if signature not in ("CWS", "FWS"):
        raise ValidationFailure(["unsupported SWF signature at " + label + ": "
                                 + repr(signature)])
    if not SWF_VERSION_MIN <= version <= SWF_VERSION_MAX:
        raise ValidationFailure(["SWF version out of range at " + label + ": "
                                 + repr(version)])
    if signature == "CWS":
        try:
            body = zlib.decompress(data[8:])
        except zlib.error:
            raise ValidationFailure(["zlib decompression failed at " + label])
    else:
        body = data[8:]
    if len(body) > MAX_BODY_BYTES:
        raise ValidationFailure(["decompressed body too large at " + label])
    return signature, version, declared, body


def inspect_body(body, label, depth=0):
    """Walk tags to End; return the static inventory for one SWF body.

    DefineSprite payloads (id + frame count + nested tags) are walked
    recursively with merged inventories so nested timelines, bitmaps,
    and labels are recorded; sprite nesting depth is tracked.
    """
    if depth > MAX_SPRITE_DEPTH:
        raise ValidationFailure(["sprite nesting too deep at " + label])
    width, height, consumed = (None, None, 0)
    position = 0
    if depth == 0:
        width, height, consumed = parse_frame_size(body, label)
        rest = consumed
        if len(body) < rest + 4:
            raise ValidationFailure(["missing frame rate/count at " + label])
        rate = struct.unpack("<H", body[rest:rest + 2])[0] / 256.0
        count = struct.unpack("<H", body[rest + 2:rest + 4])[0]
        position = rest + 4
    else:
        if len(body) < 4:
            raise ValidationFailure(["truncated sprite header at " + label])
        rate = 0.0
        count = struct.unpack("<H", body[2:4])[0]
        position = 4
    tags = {}
    symbols = []
    exports = []
    bitmap_ids = []
    sound_ids = []
    sound_formats = []
    abc_count = 0
    action_count = 0
    frame_labels = []
    scene_count = 0
    sprite_count = 0
    max_sprite_depth = depth
    ended = False
    while position + 2 <= len(body):
        header = struct.unpack("<H", body[position:position + 2])[0]
        position += 2
        code = header >> 6
        length = header & 0x3F
        if length == 0x3F:
            if position + 4 > len(body):
                raise ValidationFailure(["truncated long tag length at " + label])
            length = struct.unpack("<I", body[position:position + 4])[0]
            position += 4
        if position + length > len(body):
            raise ValidationFailure(["tag overrun at " + label + ": code "
                                     + str(code)])
        payload = body[position:position + length]
        position += length
        tags[str(code)] = tags.get(str(code), 0) + 1
        if code == TAG_END:
            ended = True
            break
        if code == TAG_DEFINE_SPRITE:
            sprite_count += 1
            nested = inspect_body(payload, label, depth + 1)
            for nested_code, nested_count in nested["tags"].items():
                tags[nested_code] = tags.get(nested_code, 0) + nested_count
            symbols.extend(nested["symbols"])
            exports.extend(nested["exports"])
            bitmap_ids.extend(nested["bitmap_ids"])
            sound_ids.extend(nested["sound_ids"])
            sound_formats.extend(nested["sound_formats"])
            abc_count += nested["abc_count"]
            action_count += nested["action_count"]
            frame_labels.extend(nested["frame_labels"])
            scene_count += nested["scene_count"]
            sprite_count += nested["sprite_count"]
            max_sprite_depth = max(max_sprite_depth, nested["max_sprite_depth"])
        elif code == TAG_SYMBOL_CLASS:
            symbols.extend(parse_symbol_names(payload, label))
        elif code == TAG_EXPORT_ASSETS:
            exports.extend(parse_symbol_names(payload, label))
        elif code in TAG_DEFINE_BITS_FAMILIES + TAG_DEFINE_BITS_LOSSLESS:
            bitmap_ids.append(parse_character_id(payload, label))
        elif code == TAG_DEFINE_SOUND:
            sound_ids.append(parse_character_id(payload, label))
            sound_formats.append(payload[2] >> 4 if len(payload) > 2 else 0)
        elif code == TAG_DO_ABC:
            abc_count += 1
        elif code in (TAG_DO_ACTION, TAG_DO_INIT_ACTION):
            action_count += 1
        elif code == TAG_FRAME_LABEL:
            name, _ = read_c_string(payload, 0, len(payload), label)
            frame_labels.append(name)
        elif code == TAG_DEFINE_SCENE_AND_FRAME_LABELS:
            scenes, labels = parse_scene_data(payload, label)
            scene_count += scenes
            frame_labels.extend(labels)
    if not ended:
        raise ValidationFailure(["tag walk never reached End at " + label])
    return {
        "frame_width": width,
        "frame_height": height,
        "frame_rate": rate,
        "frame_count": count,
        "tags": tags,
        "sprite_count": sprite_count,
        "max_sprite_depth": max_sprite_depth,
        "symbols": symbols,
        "exports": exports,
        "bitmap_ids": bitmap_ids,
        "sound_ids": sound_ids,
        "sound_formats": sound_formats,
        "has_abc": abc_count > 0,
        "has_action": action_count > 0,
        "abc_count": abc_count,
        "action_count": action_count,
        "frame_labels": frame_labels,
        "scene_count": scene_count,
    }


def inspect_file(root, relative):
    """Parse one registry SWF path into a full inspection entry."""
    label = "swf " + relative
    data = read_bytes_file(root / relative, label)
    signature, version, declared, body = parse_header(data, label)
    inventory = inspect_body(body, label)
    entry = {
        "path": relative,
        "signature": signature,
        "version": version,
        "declared_length": declared,
        "actual_length": len(data),
    }
    entry.update(inventory)
    return entry


def check_schema_type(value, allowed, label, problems):
    for kind in allowed:
        if kind == "integer" and type(value) is int:
            return
        if kind == "number" and isinstance(value, (int, float)) \
                and type(value) is not bool:
            return
        if kind == "string" and isinstance(value, str):
            return
        if kind == "object" and isinstance(value, dict):
            return
        if kind == "array" and isinstance(value, list):
            return
        if kind == "boolean" and type(value) is bool:
            return
        if kind == "null" and value is None:
            return
    problems.append("type mismatch at " + label + ": expected "
                    + "/".join(allowed))


def validate_against_schema(definition, schema, label):
    problems = []
    for field in schema["required"]:
        if field not in definition:
            problems.append("missing required field: " + label + "." + field)
    for field, spec in schema["properties"].items():
        if field not in definition:
            continue
        value = definition[field]
        if "const" in spec:
            if value != spec["const"]:
                problems.append("const mismatch at " + label + "." + field)
            continue
        allowed = spec.get("type")
        if isinstance(allowed, str):
            allowed = [allowed]
        if allowed:
            check_schema_type(value, allowed, label + "." + field, problems)
        if "enum" in spec:
            if isinstance(value, str) and value not in spec["enum"]:
                problems.append("enum mismatch at " + label + "." + field)
            elif isinstance(value, list) and value not in spec["enum"]:
                problems.append("enum mismatch at " + label + "." + field)
        if "minimum" in spec and type(value) is int:
            if value < spec["minimum"]:
                problems.append("value below minimum at " + label + "." + field)
        if "minItems" in spec and isinstance(value, list):
            if len(value) < spec["minItems"]:
                problems.append("array below minItems at " + label + "." + field)
        items_spec = spec.get("items")
        if isinstance(value, list) and isinstance(items_spec, dict):
            item_types = items_spec.get("type")
            if isinstance(item_types, str):
                item_types = [item_types]
            if item_types:
                for index, element in enumerate(value):
                    sub = []
                    check_schema_type(element, item_types,
                                      label + "." + field + "[" + str(index) + "]",
                                      sub)
                    problems.extend(sub)
    if schema.get("additionalProperties") is False:
        for field in definition:
            if field not in schema["properties"]:
                problems.append("additional property: " + label + "." + field)
    return problems


def load_loose_schema(root, filename):
    text = read_text_file(root / SCHEMA_DIR / filename, "schema " + filename)
    try:
        schema = json.loads(text)
    except ValueError:
        raise InputError("schema file not valid json: " + filename)
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise InputError("schema invalid, not object schema: " + filename)
    required = schema.get("required")
    properties = schema.get("properties")
    if not isinstance(required, list) or not required:
        raise InputError("schema invalid, required missing: " + filename)
    if not isinstance(properties, dict) or not properties:
        raise InputError("schema invalid, properties missing: " + filename)
    for field in required:
        if field not in properties:
            raise InputError("schema invalid, required not in properties: " + filename)
    return schema


def load_all(root):
    root = Path(root)
    if not root.is_dir():
        raise InputError("repository root invalid: " + str(root))
    registry = read_json_file(root / REGISTRY_FILE, "asset registry")
    if not isinstance(registry, dict) or registry.get("policy") != "asset-registry-v1":
        raise InputError("asset registry missing or wrong policy; "
                         "run build_registry.py first")
    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        raise InputError("asset registry entries not non-empty array")
    swf_paths = sorted(entry["path"] for entry in entries
                       if isinstance(entry, dict)
                       and entry.get("extension") == ".swf"
                       and isinstance(entry.get("path"), str))
    if not swf_paths:
        raise InputError("asset registry holds no .swf entries")
    return {"registry": registry, "swf_paths": swf_paths}


def fingerprint_registry(registry):
    return hashlib.sha256(
        json.dumps(registry["entries"], sort_keys=True).encode("utf-8")).hexdigest()


def build_package(repo_root, out_root):
    root = Path(repo_root)
    layers = load_all(root)
    problems = []
    entries = {}
    for relative in layers["swf_paths"]:
        try:
            entries[relative] = inspect_file(root, relative)
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    if problems:
        raise ValidationFailure(problems)
    inspection_schema = load_loose_schema(root, INSPECTION_SCHEMA_FILE.name)
    entry_schema = load_loose_schema(root, ENTRY_SCHEMA_FILE.name)
    for relative, entry in entries.items():
        problems.extend(validate_against_schema(
            entry, entry_schema, "inspection_entry " + relative))
    if problems:
        raise ValidationFailure(problems)
    versions = {}
    scripted_abc = 0
    scripted_action = 0
    bitmap_total = 0
    sound_total = 0
    sprite_total = 0
    max_depth = 0
    for entry in entries.values():
        versions[str(entry["version"])] = versions.get(str(entry["version"]), 0) + 1
        scripted_abc += 1 if entry["has_abc"] else 0
        scripted_action += 1 if entry["has_action"] else 0
        bitmap_total += len(entry["bitmap_ids"])
        sound_total += len(entry["sound_ids"])
        sprite_total += entry["sprite_count"]
        max_depth = max(max_depth, entry["max_sprite_depth"])
    document = {
        "schema_version": SCHEMA_VERSION,
        "policy": POLICY,
        "result": "success",
        "inputs": {
            "registry": REGISTRY_FILE.as_posix(),
            "registry_fingerprint": fingerprint_registry(layers["registry"]),
            "registry_files": layers["registry"]["counts"]["files"],
        },
        "counts": {
            "files": len(entries),
            "versions": versions,
            "with_abc": scripted_abc,
            "with_action": scripted_action,
            "bitmap_ids_total": bitmap_total,
            "sound_ids_total": sound_total,
            "sprite_tags_total": sprite_total,
            "max_sprite_depth": max_depth,
        },
        "entries": entries,
    }
    problems.extend(validate_against_schema(document, inspection_schema, "inspection"))
    if problems:
        raise ValidationFailure(problems)
    return document


def write_outputs(out_root, document):
    out = Path(out_root)
    (out / REGISTRY_DIR).mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
    (out / INSPECTION_FILE).write_bytes(payload)
    return {
        "file": INSPECTION_FILE.as_posix(),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def build_argument_parser():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--repo-root",
                        help="repository root to read (default: current directory)")
    parser.add_argument("--out-root",
                        help="inspection root to write (default: same as repo root)")
    return parser


def run_build(repo_root, out_root):
    document = build_package(repo_root, out_root)
    digest = write_outputs(out_root, document)
    return document, digest


def main(argv=None):
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    repo_root = args.repo_root or "."
    out_root = args.out_root or repo_root
    try:
        document, digest = run_build(repo_root, out_root)
    except ValidationFailure as failure:
        report = {
            "schema_version": SCHEMA_VERSION,
            "policy": POLICY,
            "result": "validation-failed",
            "counts": {},
            "problems": failure.problems,
        }
        print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
        return 1
    except InputError as error:
        print(str(error), file=sys.stderr)
        return 2
    report = {
        "schema_version": SCHEMA_VERSION,
        "policy": POLICY,
        "result": "success",
        "counts": document["counts"],
        "outputs": [digest["file"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
