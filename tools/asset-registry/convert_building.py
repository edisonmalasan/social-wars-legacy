"""Offline first-building converter (M4 slice 5: package assembly).

Assembles the converted package for `0001_house_1_m` (House I) from the
committed inspection output (frame data, symbols), committed extraction
outputs (bitmap files with digests), the committed normalized buildings
package (content definition, placement tiles), and newly parsed
SHAPEWITHSTYLE records (bounds, fill/line style arrays with counts and
types, bitmap-fill character IDs, raw matrices, edge-record counts),
and writes `assets/converted/buildings/0001_house_1_m/` (package.json
plus byte-identical bitmap copies) with `tools/asset-registry/
conversions.json` (package digests) and a `converted` statuses merge.

Shape-style parsing only: bounds RECTs, style arrays, bitmap-fill IDs,
matrices as raw bytes, and record-type counts. No edge-record
tessellation, no curve flattening, no rasterization, no matrix or
script interpretation, no Flash runtime in any form. Standard library
only: no legacy application import, no runtime save reads, no network,
server, browser, or subprocess activity.

Exit 0 prints a success report and writes outputs. Exit 1 prints a
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

POLICY = "building-conversion-v1"
ENVELOPE_POLICY = "conversion-v1"
SCHEMA_VERSION = 1
TARGET_STEM = "0001_house_1_m"

NORMALIZED_DIR = Path("packages") / "game-content" / "normalized"
BUILDINGS_FILE = NORMALIZED_DIR / "buildings.json"
REGISTRY_DIR = Path("tools") / "asset-registry"
SCHEMA_DIR = REGISTRY_DIR / "schemas"
PACKAGE_SCHEMA_FILE = SCHEMA_DIR / "building_package.schema.json"
CONVERSION_SCHEMA_FILE = SCHEMA_DIR / "conversion.schema.json"
INSPECTION_FILE = REGISTRY_DIR / "inspection.json"
EXTRACTION_FILE = REGISTRY_DIR / "image_extraction.json"
STATUSES_FILE = REGISTRY_DIR / "statuses.json"
CONVERSIONS_FILE = REGISTRY_DIR / "conversions.json"
CONVERTED_BUILDINGS_DIR = Path("assets") / "converted" / "buildings"

TAG_DEFINE_SHAPE = (2, 22, 32)
TAG_REFUSED_SHAPE = (83,)
TAG_WALKABLE_SHAPE = TAG_DEFINE_SHAPE + TAG_REFUSED_SHAPE
TAG_END = 0

FILL_SOLID = 0x00
FILL_GRADIENTS = (0x10, 0x12, 0x13)
FILL_BITMAPS = (0x40, 0x41, 0x42, 0x43)


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
        if "enum" in spec and isinstance(value, str):
            if value not in spec["enum"]:
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
            # Object item schemas with their own required/properties are
            # validated field by field (package entries, nested records).
            if isinstance(items_spec.get("required"), list) \
                    and isinstance(items_spec.get("properties"), dict):
                for index, element in enumerate(value):
                    if isinstance(element, dict):
                        problems.extend(validate_against_schema(
                            element, items_spec,
                            label + "." + field + "[" + str(index) + "]"))
        elif allowed and "object" in allowed and isinstance(value, dict):
            # Object properties with their own required/properties are
            # validated field by field (nested timeline records).
            if isinstance(spec.get("required"), list) \
                    and isinstance(spec.get("properties"), dict):
                problems.extend(validate_against_schema(
                    value, spec, label + "." + field))
    if schema.get("additionalProperties") is False:
        for field in definition:
            if field not in schema["properties"]:
                problems.append("additional property: " + label + "." + field)
    return problems


def validate_digest(text, label, problems):
    if not isinstance(text, str) or len(text) != 64:
        problems.append("digest malformed at " + label)
        return
    try:
        int(text, 16)
    except ValueError:
        problems.append("digest not hexadecimal at " + label)
    if text != text.lower():
        problems.append("digest not lowercase at " + label)


class BitReader:
    """MSB-first bit reader for SHAPEWITHSTYLE and shape records."""

    def __init__(self, data):
        self.data = data
        self.position = 0

    def read_bits(self, count, label):
        value = 0
        for _ in range(count):
            byte_index = self.position // 8
            if byte_index >= len(self.data):
                raise ValidationFailure(["shape bit overrun at " + label])
            bit_index = 7 - (self.position % 8)
            value = (value << 1) | ((self.data[byte_index] >> bit_index) & 1)
            self.position += 1
        return value

    def read_bytes(self, count, label):
        if self.position % 8 != 0:
            raise ValidationFailure(["shape byte misaligned at " + label])
        start = self.position // 8
        if start + count > len(self.data):
            raise ValidationFailure(["shape byte overrun at " + label])
        self.position += count * 8
        return self.data[start:start + count]

    def byte_position(self):
        return (self.position + 7) // 8

    def align_to_byte(self):
        """Advance to the next byte boundary (SWF aligns past RECTs)."""
        self.position = ((self.position + 7) // 8) * 8


def parse_rect_bits(reader, label):
    """Parse a RECT into (xmin, xmax, ymin, ymax) twips plus pixel size."""
    nbits = reader.read_bits(5, label)
    if nbits > 31:
        raise ValidationFailure(["rect nbits out of range at " + label])
    xmin = reader.read_bits(nbits, label)
    xmax = reader.read_bits(nbits, label)
    ymin = reader.read_bits(nbits, label)
    ymax = reader.read_bits(nbits, label)
    return {"xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax,
            "width_px": max(0, xmax // 20), "height_px": max(0, ymax // 20)}


def parse_matrix(reader, label):
    """Record a MATRIX as raw bytes without interpretation."""
    start = reader.byte_position()
    if reader.read_bits(1, label):
        scale_bits = reader.read_bits(5, label)
        reader.read_bits(2 * scale_bits, label)
    if reader.read_bits(1, label):
        rotate_bits = reader.read_bits(5, label)
        reader.read_bits(2 * rotate_bits, label)
    translate_bits = reader.read_bits(5, label)
    reader.read_bits(2 * translate_bits, label)
    end = reader.byte_position()
    return reader.data[start:end].hex()


def parse_fill_style(reader, rgba, label):
    """Parse one FILLSTYLE; bitmap fills keep id plus raw matrix."""
    fill_type = int.from_bytes(reader.read_bytes(1, label), "big")
    if fill_type == FILL_SOLID:
        color = reader.read_bytes(4 if rgba else 3, label).hex()
        return {"type": fill_type, "color": color}
    if fill_type in FILL_GRADIENTS:
        gradient_flags = reader.read_bits(8, label)
        count = gradient_flags & 0x0F
        spread = (gradient_flags >> 6) & 0x03
        interpolation = (gradient_flags >> 4) & 0x03
        for _ in range(count):
            reader.read_bytes(1, label)
            reader.read_bytes(4 if rgba else 3, label)
        if fill_type == 0x13:
            reader.read_bytes(2, label)
        matrix = parse_matrix(reader, label)
        return {"type": fill_type, "spread": spread,
                "interpolation": interpolation, "ratios": count,
                "matrix": matrix}
    if fill_type in FILL_BITMAPS:
        bitmap_id = struct.unpack("<H", reader.read_bytes(2, label))[0]
        matrix = parse_matrix(reader, label)
        return {"type": fill_type, "bitmap_id": bitmap_id, "matrix": matrix}
    raise ValidationFailure(["unknown fill style at " + label + ": "
                             + str(fill_type)])


def parse_line_style(reader, rgba, index, label):
    """Parse one LINESTYLE (v1/v2 distinguished by caller version)."""
    width = struct.unpack("<H", reader.read_bytes(2, label))[0]
    color = reader.read_bytes(4 if rgba else 3, label).hex()
    return {"index": index, "width": width, "color": color}


def parse_style_arrays(reader, rgba, label):
    """Parse a FillStyleArray plus LineStyleArray; return (fills, lines).

    Fill styles end wherever their MATRIX ends, so the byte-oriented
    LineStyleArray resumes on the next byte boundary (bitmap fills in
    sprite libraries end mid-byte; a single already-aligned fill is a
    no-op for this alignment).
    """
    fill_count = int.from_bytes(reader.read_bytes(1, label), "big")
    if fill_count == 0xFF:
        fill_count = struct.unpack("<H", reader.read_bytes(2, label))[0]
    fills = [parse_fill_style(reader, rgba, label) for _ in range(fill_count)]
    reader.align_to_byte()
    line_count = int.from_bytes(reader.read_bytes(1, label), "big")
    if line_count == 0xFF:
        line_count = struct.unpack("<H", reader.read_bytes(2, label))[0]
    lines = [parse_line_style(reader, rgba, index + 1, label)
             for index in range(line_count)]
    return fills, lines


def count_shape_records(reader, fill_bits, line_bits, rgba, label, extra):
    """Count shape record types without tessellating geometry.

    Mid-stream NewStyles blocks are parsed into extra style arrays (the
    counts and bitmap references matter for conversion); only geometry
    stays uncomputed. Referenced fill indices (1-based; index 0 means
    no fill) are collected into extra["fill_refs"] in record order.
    """
    counts = {"end": 0, "style_change": 0, "straight": 0, "curved": 0,
              "new_styles": 0}
    while True:
        record_type = reader.read_bits(1, label)
        if record_type == 0:
            flags = reader.read_bits(5, label)
            if flags == 0:
                counts["end"] += 1
                return counts, fill_bits, line_bits
            counts["style_change"] += 1
            if flags & 0x01:
                move_bits = reader.read_bits(5, label)
                reader.read_bits(2 * move_bits, label)
            if flags & 0x02:
                index = reader.read_bits(fill_bits, label)
                if index:
                    extra.setdefault("fill_refs", []).append(index)
            if flags & 0x04:
                index = reader.read_bits(fill_bits, label)
                if index:
                    extra.setdefault("fill_refs", []).append(index)
            if flags & 0x08:
                reader.read_bits(line_bits, label)
            if flags & 0x10:
                counts["new_styles"] += 1
                # Style arrays resume byte-aligned after the flag bits.
                reader.align_to_byte()
                fills, lines = parse_style_arrays(reader, rgba, label)
                extra["fills"].extend(fills)
                extra["lines"].extend(lines)
                fill_bits = reader.read_bits(4, label)
                line_bits = reader.read_bits(4, label)
        else:
            if reader.read_bits(1, label):
                counts["straight"] += 1
                bits = reader.read_bits(4, label) + 2
                if reader.read_bits(1, label):
                    reader.read_bits(2 * bits, label)
                else:
                    reader.read_bits(1, label)
                    reader.read_bits(bits, label)
            else:
                counts["curved"] += 1
                bits = reader.read_bits(4, label) + 2
                reader.read_bits(4 * bits, label)


def parse_shape_with_style(payload, tag, shape_id, label, collect_refs=False):
    """Parse bounds plus style arrays; count edge records, skip geometry.

    With collect_refs the returned dict gains "fill_refs" (referenced
    1-based fill indices in record order); the default result shape is
    unchanged so existing package output stays byte-identical.
    """
    if tag in TAG_REFUSED_SHAPE:
        raise ValidationFailure(["unsupported shape tag at " + label + ": "
                                 + str(tag)])
    if tag not in TAG_DEFINE_SHAPE:
        raise ValidationFailure(["unexpected shape tag at " + label + ": "
                                 + str(tag)])
    rgba = tag in (22, 32, 83)
    reader = BitReader(payload)
    actual_id = struct.unpack("<H", reader.read_bytes(2, label))[0]
    if actual_id != shape_id:
        raise ValidationFailure(["shape id mismatch at " + label])
    bounds = parse_rect_bits(reader, label)
    reader.align_to_byte()
    fills, lines = parse_style_arrays(reader, rgba, label)
    fill_bits = reader.read_bits(4, label)
    line_bits = reader.read_bits(4, label)
    extra = {"fills": [], "lines": []}
    records, fill_bits, line_bits = count_shape_records(
        reader, fill_bits, line_bits, rgba, label, extra)
    fills.extend(extra["fills"])
    lines.extend(extra["lines"])
    result = {"character_id": shape_id, "tag": tag, "bounds": bounds,
              "fills": fills, "lines": lines, "records": records}
    if collect_refs:
        result["fill_refs"] = list(extra.get("fill_refs", []))
    return result


def decompress_body(data, label):
    if len(data) < 8:
        raise ValidationFailure(["file shorter than SWF header at " + label])
    signature = data[:3].decode("latin1")
    if signature == "ZWS":
        raise ValidationFailure(["LZMA-compressed SWF not supported at " + label])
    if signature not in ("CWS", "FWS"):
        raise ValidationFailure(["unsupported SWF signature at " + label + ": "
                                 + repr(signature)])
    if signature == "CWS":
        try:
            return zlib.decompress(data[8:])
        except zlib.error:
            raise ValidationFailure(["zlib decompression failed at " + label])
    return data[8:]


def parse_frame_size(body, label):
    if not body:
        raise ValidationFailure(["missing frame rect at " + label])
    reader = BitReader(body)
    bounds = parse_rect_bits(reader, label)
    consumed = (reader.position + 7) // 8
    return bounds["width_px"], bounds["height_px"], consumed


def walk_shape_tags(body, label, depth=0):
    """Yield (tag, id, payload, context) for shape tags incl. sprites."""
    if depth > 64:
        raise ValidationFailure(["sprite nesting too deep at " + label])
    position = 0
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
        if code == TAG_END:
            return
        if code == 39:
            if len(payload) < 4:
                raise ValidationFailure(["truncated sprite header at " + label])
            sprite_id = struct.unpack("<H", payload[:2])[0]
            for item in walk_shape_tags(payload[4:], label + " sprite "
                                        + str(sprite_id), depth + 1):
                yield item
        elif code in TAG_WALKABLE_SHAPE:
            if len(payload) < 2:
                raise ValidationFailure(["truncated shape id at " + label])
            yield code, struct.unpack("<H", payload[:2])[0], payload, label
    raise ValidationFailure(["tag walk never reached End at " + label])


def load_all(root):
    root = Path(root)
    if not root.is_dir():
        raise InputError("repository root invalid: " + str(root))
    inspection = read_json_file(root / REGISTRY_DIR / "inspection.json",
                                "swf inspection")
    if not isinstance(inspection, dict):
        raise InputError("swf inspection not object")
    extraction = read_json_file(root / REGISTRY_DIR / "image_extraction.json",
                                "image extraction")
    if not isinstance(extraction, dict):
        raise InputError("image extraction not object")
    buildings = read_json_file(root / BUILDINGS_FILE, "normalized buildings")
    if not isinstance(buildings, list) or not buildings:
        raise InputError("normalized buildings not non-empty array")
    statuses_path = root / REGISTRY_DIR / "statuses.json"
    statuses = {}
    if statuses_path.exists():
        try:
            previous = json.loads(statuses_path.read_text(encoding="utf-8"))
        except ValueError:
            raise InputError("existing statuses file not valid json")
        if not isinstance(previous, dict):
            raise InputError("existing statuses file not object")
        statuses = dict(previous.get("statuses", {}))
    return {"inspection": inspection, "extraction": extraction,
            "buildings": buildings, "statuses": statuses}


def fingerprint_inputs(root, files=None):
    if files is None:
        files = (BUILDINGS_FILE, REGISTRY_DIR / "inspection.json",
                 REGISTRY_DIR / "image_extraction.json")
    digest = hashlib.sha256()
    for relative in files:
        digest.update(read_bytes_file(root / relative,
                                      "fingerprint " + relative.as_posix()))
    return digest.hexdigest()


def merge_conversion_document(root, own_entry, own_inputs, tool_policy):
    """Merge this converter's package entry into the shared manifest.

    Reads the existing `conversions.json`, preserves foreign package
    entries and input keys verbatim, replaces this converter's entry
    (keyed by directory), sorts entries by directory, recomputes counts
    from the entries, and stamps the neutral envelope policy so the
    result does not depend on which converter ran last. A legacy
    `building-conversion-v1` envelope is migrated only by the building
    converter and only while it holds exactly the building entry; the
    unit converter rejects it with a clear failure.
    """
    entries = []
    inputs = {}
    path = root / CONVERSIONS_FILE
    if path.exists():
        existing = read_json_file(path, "conversion manifest")
        if not isinstance(existing, dict):
            raise InputError("conversion manifest not object")
        policy = existing.get("policy")
        packages = existing.get("packages")
        foreign_inputs = existing.get("inputs")
        if not isinstance(packages, list):
            raise ValidationFailure(["conversion manifest packages not array"])
        if not isinstance(foreign_inputs, dict):
            raise ValidationFailure(["conversion manifest inputs not object"])
        if policy == ENVELOPE_POLICY:
            # Foreign input keys are preserved verbatim.
            inputs = dict(foreign_inputs)
            entries = list(packages)
        elif policy == POLICY:
            if tool_policy != POLICY:
                raise ValidationFailure(
                    ["conversion manifest is legacy " + POLICY
                     + "; run convert_building.py to migrate it first"])
            foreign = [entry for entry in packages
                       if not isinstance(entry, dict)
                       or entry.get("directory") != own_entry["directory"]]
            if foreign:
                raise ValidationFailure(
                    ["legacy conversion manifest holds foreign entries; "
                     "refusing to migrate"])
            # Migration supersedes the legacy content_version key with
            # the tool-scoped key stamped by the caller.
            inputs = {key: value for key, value in foreign_inputs.items()
                      if key != "content_version"}
            entries = []
        else:
            raise ValidationFailure(
                ["conversion manifest policy not recognized: "
                 + repr(policy)])
    entries = [entry for entry in entries
               if isinstance(entry, dict)
               and entry.get("directory") != own_entry["directory"]]
    entries.append(own_entry)
    entries.sort(key=lambda entry: entry["directory"])
    inputs.update(own_inputs)
    output_bytes = 0
    for entry in entries:
        value = entry.get("output_bytes")
        if type(value) is not int or value < 0:
            raise ValidationFailure(
                ["conversion manifest entry missing output_bytes: "
                 + str(entry.get("directory"))])
        output_bytes += value
    return {
        "schema_version": SCHEMA_VERSION,
        "policy": ENVELOPE_POLICY,
        "result": "success",
        "inputs": inputs,
        "counts": {"packages": len(entries), "output_bytes": output_bytes},
        "packages": entries,
    }


def build_package(repo_root, out_root):
    root = Path(repo_root)
    layers = load_all(root)
    source = "assets/sprites/" + TARGET_STEM + ".swf"
    problems = []
    matches = [entry for entry in layers["buildings"]
               if isinstance(entry, dict) and entry.get("img_name") == TARGET_STEM]
    if len(matches) != 1:
        raise ValidationFailure(["content ref not unique for " + TARGET_STEM + ": "
                                 + str(len(matches))])
    content = matches[0]
    entries = layers["inspection"].get("entries", {})
    if source not in entries or not isinstance(entries[source], dict):
        raise ValidationFailure(["inspection entry missing for " + source])
    inspected = entries[source]
    data = read_bytes_file(root / source, "swf " + source)
    try:
        body = decompress_body(data, "swf " + source)
        width, height, consumed = parse_frame_size(body, "swf " + source)
        rest = consumed
        rate = struct.unpack("<H", body[rest:rest + 2])[0] / 256.0
        count = struct.unpack("<H", body[rest + 2:rest + 4])[0]
        shapes = []
        for tag, shape_id, payload, context in walk_shape_tags(
                body[rest + 4:], "swf " + source):
            shapes.append(parse_shape_with_style(payload, tag, shape_id, context))
    except ValidationFailure as failure:
        raise ValidationFailure(failure.problems)
    bitmap_by_id = {}
    for bitmap in layers["extraction"].get("bitmaps", []):
        if isinstance(bitmap, dict) and bitmap.get("source") == source:
            for output in bitmap.get("outputs", []):
                bitmap_by_id.setdefault(bitmap.get("character_id"), []).append(output)
    for shape in shapes:
        for fill in shape["fills"]:
            if "bitmap_id" in fill:
                if fill["bitmap_id"] not in bitmap_by_id:
                    problems.append("unresolvable bitmap fill at shape "
                                    + str(shape["character_id"]) + " -> "
                                    + str(fill["bitmap_id"]))
    if problems:
        raise ValidationFailure(problems)
    fingerprint = fingerprint_inputs(root)
    bitmaps = []
    payloads = {}
    for shape in shapes:
        for fill in shape["fills"]:
            if "bitmap_id" not in fill:
                continue
            for output in bitmap_by_id[fill["bitmap_id"]]:
                target = (CONVERTED_BUILDINGS_DIR / TARGET_STEM
                          / output["file"].rsplit("/", 1)[-1]).as_posix()
                payloads[target] = read_bytes_file(root / output["file"],
                                                   "extracted " + output["file"])
                bitmaps.append({
                    "character_id": fill["bitmap_id"],
                    "file": target,
                    "bytes": len(payloads[target]),
                    "sha256": hashlib.sha256(payloads[target]).hexdigest(),
                    "expected_sha256": output["sha256"],
                })
    for bitmap in bitmaps:
        if bitmap["sha256"] != bitmap["expected_sha256"]:
            problems.append("bitmap digest mismatch at " + bitmap["file"])
    if problems:
        raise ValidationFailure(problems)
    package = {
        "legacy_id": TARGET_STEM,
        "kind": "converted_building",
        "source_file": source,
        "source_layer": "converted(asset-registry)",
        "content_version": fingerprint,
        "content_ref": content,
        "frame_width": width,
        "frame_height": height,
        "frame_rate": rate,
        "frame_count": count,
        "symbols": list(inspected.get("symbols", [])),
        "shapes": shapes,
        "bitmaps": [{key: bitmap[key] for key in
                     ("character_id", "file", "bytes", "sha256")}
                    for bitmap in bitmaps],
        "placement": {"width": content.get("width"),
                      "height": content.get("height")},
    }
    package_schema = load_loose_schema(root, PACKAGE_SCHEMA_FILE.name)
    problems.extend(validate_against_schema(
        package, package_schema, "converted_building " + TARGET_STEM))
    if problems:
        raise ValidationFailure(problems)
    package_payload = (json.dumps(package, indent=2, sort_keys=True) + "\n"
                       ).encode("utf-8")
    conversion_schema = load_loose_schema(root, CONVERSION_SCHEMA_FILE.name)
    document = merge_conversion_document(root, {
        "legacy_id": TARGET_STEM,
        "directory": (CONVERTED_BUILDINGS_DIR / TARGET_STEM).as_posix(),
        "package_sha256": hashlib.sha256(package_payload).hexdigest(),
        "bitmaps": len(bitmaps),
        "output_bytes": len(package_payload) + sum(
            bitmap["bytes"] for bitmap in bitmaps),
        "policy": POLICY,
    }, {
        "buildings": BUILDINGS_FILE.as_posix(),
        "inspection": (REGISTRY_DIR / "inspection.json").as_posix(),
        "extraction": (REGISTRY_DIR / "image_extraction.json").as_posix(),
        "buildings_content_version": fingerprint,
    }, POLICY)
    problems.extend(validate_against_schema(document, conversion_schema, "conversion"))
    if problems:
        raise ValidationFailure(problems)
    merged = dict(layers["statuses"])
    merged[source] = "converted"
    return package, package_payload, document, merged, payloads


def write_outputs(out_root, package, package_payload, document, statuses, payloads):
    out = Path(out_root)
    package_dir = out / CONVERTED_BUILDINGS_DIR / TARGET_STEM
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "package.json").write_bytes(package_payload)
    for relative, payload in payloads.items():
        (out / relative).write_bytes(payload)
    conversions_payload = (json.dumps(document, indent=2, sort_keys=True) + "\n"
                           ).encode("utf-8")
    statuses_payload = (json.dumps({"schema_version": SCHEMA_VERSION,
                                    "policy": "asset-statuses-v1",
                                    "statuses": statuses},
                                   indent=2, sort_keys=True) + "\n").encode("utf-8")
    (out / REGISTRY_DIR).mkdir(parents=True, exist_ok=True)
    (out / REGISTRY_DIR / "conversions.json").write_bytes(conversions_payload)
    (out / REGISTRY_DIR / "statuses.json").write_bytes(statuses_payload)
    return {
        "package": {
            "directory": (CONVERTED_BUILDINGS_DIR / TARGET_STEM).as_posix(),
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
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
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
        "outputs": [digests["package"]["directory"],
                    digests["conversions"]["file"],
                    digests["statuses"]["file"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
