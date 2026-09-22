"""Offline bitmap extractor (M4 slice 4: format-faithful image extraction).

Re-walks bitmap tags (DefineBits 6, DefineBitsJPEG2 21, DefineBitsJPEG3
35, DefineBitsLossless 20, DefineBitsLossless2 36) in every inspected
SWF, converts per family, and writes outputs under the ignored
`assets/converted/images/<swf-stem>/` plus the committed
`tools/asset-registry/image_extraction.json` (per-bitmap provenance,
family, format, dimensions, digests) and a `statuses.json` merge
advancing extracted files.

Family rules: plain JPEG payloads pass through verbatim (JPEGTables
spliced only when SOI is absent); JPEG3 payloads split into verbatim
`.jpg` plus zlib-decoded alpha as grayscale `_alpha.png` with exact
dimension match; lossless ARGB (format 5) and colormap (format 3,
expanded to RGBA) encode to `.png` via a hand-rolled stdlib writer
(signature, IHDR, filter-0 IDAT, IEND with CRCs). JPEG dimensions come
from a minimal SOF scan (structure only, never pixels). Unknown bitmap
formats fail closed.

Tag-structure reads, zlib decompression, and byte re-encoding only: no
rendering, no JPEG decoding to pixels, no Flash runtime in any form.
Standard library only: no legacy application import, no runtime save
reads, no network, server, browser, or subprocess activity.

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

POLICY = "bitmap-extraction-v1"
SCHEMA_VERSION = 1

REGISTRY_DIR = Path("tools") / "asset-registry"
SCHEMA_DIR = REGISTRY_DIR / "schemas"
EXTRACTION_SCHEMA_FILE = SCHEMA_DIR / "bitmap_extraction.schema.json"
BITMAP_SCHEMA_FILE = SCHEMA_DIR / "extracted_bitmap.schema.json"
INSPECTION_FILE = REGISTRY_DIR / "inspection.json"
STATUSES_FILE = REGISTRY_DIR / "statuses.json"
EXTRACTION_FILE = REGISTRY_DIR / "image_extraction.json"
CONVERTED_IMAGES_DIR = Path("assets") / "converted" / "images"

TAG_DEFINE_BITS = 6
TAG_JPEG_TABLES = 8
TAG_DEFINE_BITS_LOSSLESS = 20
TAG_DEFINE_BITS_JPEG2 = 21
TAG_DEFINE_BITS_JPEG3 = 35
TAG_DEFINE_BITS_LOSSLESS2 = 36
TAG_END = 0

LOSSLESS_FORMATS = (3, 5)
JPEG_SOI = b"\xff\xd8"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


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
        if kind == "string" and isinstance(value, str):
            return
        if kind == "object" and isinstance(value, dict):
            return
        if kind == "array" and isinstance(value, list):
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


def chunk(kind, payload):
    """One PNG chunk with CRC over kind plus payload."""
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(
        ">I", zlib.crc32(body) & 0xFFFFFFFF)


def encode_png(width, height, rows, color_type):
    """Minimal PNG writer: 8-bit RGBA (6) or grayscale (0), filter 0 rows."""
    if width < 1 or height < 1:
        raise ValidationFailure(["PNG dimensions invalid"])
    channels = 4 if color_type == 6 else 1
    if len(rows) != height:
        raise ValidationFailure(["PNG row count mismatch"])
    for row in rows:
        if len(row) != width * channels:
            raise ValidationFailure(["PNG row length mismatch"])
    ihdr = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    raw = b"".join(b"\x00" + row for row in rows)
    return (PNG_SIGNATURE + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def parse_png_ihdr(data, label):
    """Re-parse PNG signature plus IHDR into (width, height, color_type)."""
    if data[:8] != PNG_SIGNATURE:
        raise ValidationFailure(["PNG signature missing at " + label])
    if len(data) < 33:
        raise ValidationFailure(["PNG too short for IHDR at " + label])
    length = struct.unpack(">I", data[8:12])[0]
    if data[12:16] != b"IHDR" or length != 13:
        raise ValidationFailure(["PNG IHDR missing at " + label])
    width, height, depth, color = struct.unpack(">IIBB", data[16:26])
    if depth != 8 or color not in (0, 6):
        raise ValidationFailure(["PNG unsupported depth/type at " + label])
    return width, height, color


def jpeg_dimensions(data, label):
    """Minimal JPEG SOF scan into (width, height); structure only."""
    if data[:2] != JPEG_SOI:
        raise ValidationFailure(["JPEG SOI missing at " + label])
    position = 2
    while position + 4 <= len(data):
        if data[position] != 0xFF:
            raise ValidationFailure(["JPEG marker sync lost at " + label])
        marker = data[position + 1]
        if marker == 0xD8 or (0xD0 <= marker <= 0xD7):
            position += 2
            continue
        if marker == 0xD9:
            break
        if position + 4 > len(data):
            raise ValidationFailure(["JPEG segment truncated at " + label])
        length = struct.unpack(">H", data[position + 2:position + 4])[0]
        if length < 2 or position + 2 + length > len(data):
            raise ValidationFailure(["JPEG segment overrun at " + label])
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC9, 0xCA, 0xCB):
            if length < 7:
                raise ValidationFailure(["JPEG SOF truncated at " + label])
            height = struct.unpack(">H", data[position + 5:position + 7])[0]
            width = struct.unpack(">H", data[position + 7:position + 9])[0]
            if width < 1 or height < 1:
                raise ValidationFailure(["JPEG dimensions invalid at " + label])
            return width, height
        if marker == 0xDA:
            raise ValidationFailure(["JPEG SOF not found before SOS at " + label])
        position += 2 + length
    raise ValidationFailure(["JPEG SOF not found at " + label])


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


def walk_bitmap_tags(body, label):
    """Yield (tag, payload) for bitmap tags plus JPEGTables, skipping rest."""
    if not body:
        raise ValidationFailure(["missing frame rect at " + label])
    nbits = body[0] >> 3
    position = (5 + 4 * nbits + 7) // 8 + 4
    if position > len(body):
        raise ValidationFailure(["truncated SWF header at " + label])
    tables = None
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
        if code == TAG_END:
            ended = True
            break
        if code == TAG_JPEG_TABLES:
            tables = payload
        elif code in (TAG_DEFINE_BITS, TAG_DEFINE_BITS_JPEG2,
                      TAG_DEFINE_BITS_JPEG3, TAG_DEFINE_BITS_LOSSLESS,
                      TAG_DEFINE_BITS_LOSSLESS2):
            yield code, payload
    if not ended:
        raise ValidationFailure(["tag walk never reached End at " + label])


def convert_jpeg(code, payload, tables, label):
    """Verbatim JPEG with conditional JPEGTables splice; returns (bytes, spliced)."""
    if len(payload) < 2:
        raise ValidationFailure(["truncated bitmap id at " + label])
    character_id = struct.unpack("<H", payload[:2])[0]
    stream = payload[2:]
    spliced = False
    if not stream.startswith(JPEG_SOI):
        if tables is None:
            raise ValidationFailure(["JPEG without SOI and no tables at " + label])
        stream = tables + stream
        spliced = True
    width, height = jpeg_dimensions(stream, label)
    return character_id, stream, spliced, width, height


def convert_jpeg3(payload, label):
    """Split JPEG3 into verbatim JPEG plus decoded alpha; returns parts."""
    if len(payload) < 6:
        raise ValidationFailure(["truncated JPEG3 header at " + label])
    character_id = struct.unpack("<H", payload[:2])[0]
    alpha_offset = struct.unpack("<I", payload[2:6])[0]
    jpeg = payload[6:6 + alpha_offset]
    alpha_z = payload[6 + alpha_offset:]
    if not jpeg.startswith(JPEG_SOI):
        raise ValidationFailure(["JPEG3 image without SOI at " + label])
    width, height = jpeg_dimensions(jpeg, label)
    try:
        alpha = zlib.decompress(alpha_z)
    except zlib.error:
        raise ValidationFailure(["alpha zlib decompression failed at " + label])
    if len(alpha) != width * height:
        raise ValidationFailure(["alpha dimension mismatch at " + label + ": "
                                 + str(len(alpha)) + " bytes for "
                                 + str(width) + "x" + str(height)])
    rows = [alpha[row * width:(row + 1) * width] for row in range(height)]
    return character_id, jpeg, width, height, encode_png(width, height, rows, 0)


def convert_lossless(code, payload, label):
    """Decode lossless ARGB/colormap payloads into RGBA rows plus dims."""
    if len(payload) < 7:
        raise ValidationFailure(["truncated lossless header at " + label])
    character_id = struct.unpack("<H", payload[:2])[0]
    bitmap_format = payload[2]
    width = struct.unpack("<H", payload[3:5])[0]
    height = struct.unpack("<H", payload[5:7])[0]
    if width < 1 or height < 1:
        raise ValidationFailure(["lossless dimensions invalid at " + label])
    if bitmap_format not in (3, 5):
        raise ValidationFailure(["unsupported lossless format at " + label + ": "
                                 + str(bitmap_format)])
    rows = []
    if bitmap_format == 5:
        try:
            pixel_data = zlib.decompress(bytes(payload[7:]))
        except zlib.error:
            raise ValidationFailure(["pixel zlib decompression failed at " + label])
        expected = width * height * 4
        if len(pixel_data) != expected:
            raise ValidationFailure(["ARGB length mismatch at " + label])
        offset = 0
        for _ in range(height):
            row = bytearray()
            for _ in range(width):
                alpha, red, green, blue = pixel_data[offset:offset + 4]
                row.extend((red, green, blue, alpha))
                offset += 4
            rows.append(bytes(row))
    else:
        # Colormap: a U8 prefix holds palette-count-minus-one outside the
        # zlib stream; the stream decodes to palette entries plus padded
        # index rows (stride rounds width up to 4 bytes).
        palette_count = payload[7] + 1
        try:
            decoded = zlib.decompress(bytes(payload[8:]))
        except zlib.error:
            raise ValidationFailure(["pixel zlib decompression failed at " + label])
        entry_size = 4 if code == TAG_DEFINE_BITS_LOSSLESS2 else 3
        palette_end = palette_count * entry_size
        if len(decoded) < palette_end:
            raise ValidationFailure(["colormap palette truncated at " + label])
        palette = []
        offset = 0
        for _ in range(palette_count):
            entry = decoded[offset:offset + entry_size]
            offset += entry_size
            if code == TAG_DEFINE_BITS_LOSSLESS2:
                alpha, red, green, blue = entry
                palette.append((red, green, blue, alpha))
            else:
                red, green, blue = entry
                palette.append((red, green, blue, 255))
        indices = decoded[palette_end:]
        stride = (width + 3) & ~3
        if len(indices) == stride * height:
            step = stride
        elif len(indices) == width * height:
            step = width
        else:
            raise ValidationFailure(["colormap indices length mismatch at " + label])
        for row_index in range(height):
            row = bytearray()
            for column in range(width):
                row.extend(palette[indices[row_index * step + column]])
            rows.append(bytes(row))
    return character_id, bitmap_format, width, height, encode_png(width, height, rows, 6)


def load_all(root):
    root = Path(root)
    if not root.is_dir():
        raise InputError("repository root invalid: " + str(root))
    inspection = read_json_file(root / REGISTRY_DIR / "inspection.json",
                                "swf inspection")
    if not isinstance(inspection, dict):
        raise InputError("swf inspection not object")
    entries = inspection.get("entries")
    if not isinstance(entries, dict) or not entries:
        raise InputError("swf inspection entries not non-empty object")
    swf_paths = sorted(entries.keys())
    inspection_digest = hashlib.sha256(
        json.dumps(entries, sort_keys=True).encode("utf-8")).hexdigest()
    return {"inspection": inspection, "swf_paths": swf_paths,
            "inspection_digest": inspection_digest}


def build_package(repo_root, out_root):
    root = Path(repo_root)
    layers = load_all(root)
    problems = []
    bitmaps = []
    splices = 0
    for relative in layers["swf_paths"]:
        label = "swf " + relative
        data = read_bytes_file(root / relative, label)
        try:
            body = decompress_body(data, label)
            tables = None
            stem = relative.rsplit("/", 1)[-1][:-len(".swf")]
            for code, payload in walk_bitmap_tags(body, label):
                if code == TAG_JPEG_TABLES:
                    tables = payload
                    continue
                directory = (CONVERTED_IMAGES_DIR / stem).as_posix()
                if code in (TAG_DEFINE_BITS, TAG_DEFINE_BITS_JPEG2):
                    character_id, stream, spliced, width, height = \
                        convert_jpeg(code, payload, tables, label)
                    splices += 1 if spliced else 0
                    outputs = [(
                        directory + "/" + str(character_id) + ".jpg", stream)]
                    bitmaps.append({
                        "source": relative, "tag": code,
                        "character_id": character_id, "family": "jpeg",
                        "format": 0, "width": width, "height": height,
                        "outputs": outputs,
                    })
                elif code == TAG_DEFINE_BITS_JPEG3:
                    character_id, jpeg, width, height, alpha_png = \
                        convert_jpeg3(payload, label)
                    outputs = [
                        (directory + "/" + str(character_id) + ".jpg", jpeg),
                        (directory + "/" + str(character_id) + "_alpha.png",
                         alpha_png),
                    ]
                    bitmaps.append({
                        "source": relative, "tag": code,
                        "character_id": character_id, "family": "jpeg3",
                        "format": 0, "width": width, "height": height,
                        "outputs": outputs,
                    })
                else:
                    character_id, bitmap_format, width, height, png = \
                        convert_lossless(code, payload, label)
                    outputs = [(directory + "/" + str(character_id) + ".png",
                                png)]
                    bitmaps.append({
                        "source": relative, "tag": code,
                        "character_id": character_id, "family": "lossless",
                        "format": bitmap_format, "width": width,
                        "height": height, "outputs": outputs,
                    })
        except ValidationFailure as failure:
            problems.extend(failure.problems)
    if problems:
        raise ValidationFailure(problems)
    manifest_bitmaps = []
    families = {}
    output_bytes = 0
    for bitmap in bitmaps:
        outputs = []
        for relative, payload in bitmap["outputs"]:
            digest = hashlib.sha256(payload).hexdigest()
            outputs.append({"file": relative, "bytes": len(payload),
                            "sha256": digest})
            output_bytes += len(payload)
        # Re-parse check: PNG IHDR or JPEG SOF must agree with dimensions.
        for output in outputs:
            payload = dict(bitmap["outputs"])[output["file"]]
            if output["file"].endswith(".png"):
                width, height, _ = parse_png_ihdr(
                    payload, "re-parse " + output["file"])
            else:
                width, height = jpeg_dimensions(
                    payload, "re-parse " + output["file"])
            if width != bitmap["width"] or height != bitmap["height"]:
                problems.append("dimension drift at " + output["file"])
        manifest_bitmaps.append({
            "source": bitmap["source"],
            "tag": bitmap["tag"],
            "character_id": bitmap["character_id"],
            "family": bitmap["family"],
            "format": bitmap["format"],
            "width": bitmap["width"],
            "height": bitmap["height"],
            "outputs": outputs,
        })
        families[bitmap["family"]] = families.get(bitmap["family"], 0) + 1
    if problems:
        raise ValidationFailure(problems)
    extraction_schema = load_loose_schema(root, EXTRACTION_SCHEMA_FILE.name)
    bitmap_schema = load_loose_schema(root, BITMAP_SCHEMA_FILE.name)
    for bitmap in manifest_bitmaps:
        problems.extend(validate_against_schema(
            bitmap, bitmap_schema, "bitmap " + bitmap["source"] + "#"
            + str(bitmap["character_id"])))
    if problems:
        raise ValidationFailure(problems)
    document = {
        "schema_version": SCHEMA_VERSION,
        "policy": POLICY,
        "result": "success",
        "inputs": {
            "inspection": (REGISTRY_DIR / "inspection.json").as_posix(),
            "inspection_fingerprint": layers["inspection_digest"],
            "table_splices": splices,
        },
        "counts": {
            "bitmaps": len(manifest_bitmaps),
            "families": families,
            "output_bytes": output_bytes,
        },
        "bitmaps": manifest_bitmaps,
    }
    problems.extend(validate_against_schema(document, extraction_schema, "extraction"))
    if problems:
        raise ValidationFailure(problems)
    statuses = {}
    for bitmap in manifest_bitmaps:
        statuses[bitmap["source"]] = "extracted"
    return document, statuses, bitmaps


def write_outputs(out_root, document, statuses, bitmaps):
    out = Path(out_root)
    (out / CONVERTED_IMAGES_DIR).mkdir(parents=True, exist_ok=True)
    (out / REGISTRY_DIR).mkdir(parents=True, exist_ok=True)
    for bitmap in bitmaps:
        for relative, payload in bitmap["outputs"]:
            target = out / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    extraction_payload = (json.dumps(document, indent=2, sort_keys=True) + "\n"
                          ).encode("utf-8")
    statuses_path = out / REGISTRY_DIR / "statuses.json"
    if statuses_path.exists():
        try:
            previous = json.loads(statuses_path.read_text(encoding="utf-8"))
        except ValueError:
            raise InputError("existing statuses file not valid json")
        if not isinstance(previous, dict):
            raise InputError("existing statuses file not object")
        merged = dict(previous.get("statuses", {}))
        merged.update(statuses)
    else:
        merged = dict(statuses)
    # Neutral envelope: one statuses file accumulates lifecycle states
    # across extraction slices regardless of which tool wrote first.
    statuses_payload = (json.dumps({"schema_version": SCHEMA_VERSION,
                                    "policy": "asset-statuses-v1",
                                    "statuses": merged},
                                   indent=2, sort_keys=True) + "\n").encode("utf-8")
    (out / REGISTRY_DIR / "image_extraction.json").write_bytes(extraction_payload)
    statuses_path.write_bytes(statuses_payload)
    return {
        "extraction": {
            "file": (REGISTRY_DIR / "image_extraction.json").as_posix(),
            "bytes": len(extraction_payload),
            "sha256": hashlib.sha256(extraction_payload).hexdigest(),
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
                        help="extraction root to write (default: same as repo root)")
    return parser


def run_build(repo_root, out_root):
    document, statuses, bitmaps = build_package(repo_root, out_root)
    digests = write_outputs(out_root, document, statuses, bitmaps)
    return document, statuses, digests


def main(argv=None):
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    repo_root = args.repo_root or "."
    out_root = args.out_root or repo_root
    try:
        document, _statuses, digests = run_build(repo_root, out_root)
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
        "outputs": [digests["extraction"]["file"],
                    digests["statuses"]["file"]],
        "problems": [],
    }
    print(json.dumps(report, indent=2, sort_keys=True) + "\n", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
