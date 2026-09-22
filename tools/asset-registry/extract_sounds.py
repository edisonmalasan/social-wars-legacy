"""Offline sound extractor (M4 slice 3: verbatim MP3 extraction).

Re-walks DefineSound tags in the inspected source SWF
(`assets/swf/dynamic2.swf`, resolved from the committed inspection
output, never hardcoded discovery), validates format nibble 2 (MP3)
with sane rate/size/type characteristics, slices each payload from its
first `FF Ex` frame sync (uniform offset asserted) to payload end, and
writes one `.mp3` per character ID under `assets/converted/sounds/`
plus `tools/asset-registry/extraction.json` (per-sound provenance and
digests) and `tools/asset-registry/statuses.json` (registry-path to
`extracted` overlay).

Tag-structure reads and byte slicing only: no decoding to samples, no
playback, no transcoding, no Flash runtime in any form. Standard
library only: no legacy application import, no runtime save reads, no
network, server, browser, or subprocess activity.

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

POLICY = "sound-extraction-v1"
SCHEMA_VERSION = 1
EXPECTED_FORMAT = 2
EXPECTED_SYNC_OFFSET = 9

REGISTRY_DIR = Path("tools") / "asset-registry"
SCHEMA_DIR = REGISTRY_DIR / "schemas"
EXTRACTION_SCHEMA_FILE = SCHEMA_DIR / "extraction.schema.json"
SOUND_SCHEMA_FILE = SCHEMA_DIR / "extraction_sound.schema.json"
INSPECTION_FILE = REGISTRY_DIR / "inspection.json"
EXTRACTION_FILE = REGISTRY_DIR / "extraction.json"
STATUSES_FILE = REGISTRY_DIR / "statuses.json"
CONVERTED_SOUNDS_DIR = Path("assets") / "converted" / "sounds"

TAG_DEFINE_SOUND = 14
TAG_END = 0

RATE_TABLE = {0: "5.5 kHz", 1: "11 kHz", 2: "22 kHz", 3: "44 kHz"}


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
        if "maximum" in spec and type(value) is int:
            if value > spec["maximum"]:
                problems.append("value above maximum at " + label + "." + field)
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


def decompress_body(data, label):
    """Split header and decompress CWS bodies; FWS passes through."""
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


def walk_sound_tags(body, label):
    """Yield (character_id, characteristics, payload) per DefineSound tag."""
    position = 0
    # Skip FrameSize RECT + rate/count: reuse minimal header skip.
    if not body:
        raise ValidationFailure(["missing frame rect at " + label])
    nbits = body[0] >> 3
    position = (5 + 4 * nbits + 7) // 8 + 4
    if position > len(body):
        raise ValidationFailure(["truncated SWF header at " + label])
    sounds = []
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
        if code != TAG_DEFINE_SOUND:
            continue
        if len(payload) < 3:
            raise ValidationFailure(["truncated sound header at " + label])
        character_id = struct.unpack("<H", payload[:2])[0]
        flags = payload[2]
        sounds.append({
            "character_id": character_id,
            "format": (flags >> 4) & 0x0F,
            "rate": (flags >> 2) & 0x03,
            "size": (flags >> 1) & 0x01,
            "sound_type": flags & 0x01,
            "payload": payload,
        })
    if not ended:
        raise ValidationFailure(["tag walk never reached End at " + label])
    return sounds


def first_sync_offset(payload, label):
    """Offset of the first FF Ex frame sync inside a tag payload."""
    for index in range(len(payload) - 1):
        if payload[index] == 0xFF and payload[index + 1] & 0xE0 == 0xE0:
            return index
    raise ValidationFailure(["no MP3 frame sync at " + label])


def load_all(root):
    root = Path(root)
    if not root.is_dir():
        raise InputError("repository root invalid: " + str(root))
    inspection = read_json_file(root / INSPECTION_FILE, "swf inspection")
    if not isinstance(inspection, dict):
        raise InputError("swf inspection not object")
    entries = inspection.get("entries")
    if not isinstance(entries, dict) or not entries:
        raise InputError("swf inspection entries not non-empty object")
    sounded = sorted(path for path, entry in entries.items()
                     if isinstance(entry, dict) and entry.get("sound_ids"))
    if not sounded:
        raise InputError("swf inspection holds no sounded files")
    return {"inspection": inspection, "sounded": sounded}


def build_package(repo_root, out_root):
    root = Path(repo_root)
    layers = load_all(root)
    problems = []
    sounds = []
    for relative in layers["sounded"]:
        label = "swf " + relative
        data = read_bytes_file(root / relative, label)
        try:
            body = decompress_body(data, label)
            tags = walk_sound_tags(body, label)
        except ValidationFailure as failure:
            problems.extend(failure.problems)
            continue
        for tag in tags:
            if tag["format"] != EXPECTED_FORMAT:
                problems.append("non-MP3 sound format at " + label + ": id "
                                + str(tag["character_id"]) + " format "
                                + str(tag["format"]))
                continue
            try:
                offset = first_sync_offset(tag["payload"], label + " id "
                                           + str(tag["character_id"]))
            except ValidationFailure as failure:
                problems.extend(failure.problems)
                continue
            if offset != EXPECTED_SYNC_OFFSET:
                problems.append("frame sync drift at " + label + " id "
                                + str(tag["character_id"]) + ": offset "
                                + str(offset))
                continue
            output = (CONVERTED_SOUNDS_DIR / (str(tag["character_id"]) + ".mp3"))
            sounds.append({
                "character_id": tag["character_id"],
                "format": tag["format"],
                "rate": tag["rate"],
                "size": tag["size"],
                "sound_type": tag["sound_type"],
                "sync_offset": offset,
                "payload_bytes": len(tag["payload"]),
                "output_bytes": len(tag["payload"]) - offset,
                "output": output.as_posix(),
                "sha256": hashlib.sha256(tag["payload"][offset:]).hexdigest(),
                "frames": tag["payload"][offset:],
            })
    if problems:
        raise ValidationFailure(problems)
    if not sounds:
        raise ValidationFailure(["no sounds extracted"])
    identifiers = [sound["character_id"] for sound in sounds]
    if len(set(identifiers)) != len(identifiers):
        raise ValidationFailure(["duplicate sound character_id"])
    sounds.sort(key=lambda sound: sound["character_id"])
    manifest_sounds = []
    for sound in sounds:
        manifest_sounds.append({key: sound[key] for key in
                                ("character_id", "format", "rate", "size",
                                 "sound_type", "sync_offset", "payload_bytes",
                                 "output_bytes", "output", "sha256")})
    extraction_schema = load_loose_schema(root, EXTRACTION_SCHEMA_FILE.name)
    sound_schema = load_loose_schema(root, SOUND_SCHEMA_FILE.name)
    for sound in manifest_sounds:
        problems.extend(validate_against_schema(
            sound, sound_schema, "sound " + str(sound["character_id"])))
    if problems:
        raise ValidationFailure(problems)
    inspection_digest = hashlib.sha256(
        json.dumps(layers["inspection"]["entries"], sort_keys=True).encode("utf-8")
    ).hexdigest()
    document = {
        "schema_version": SCHEMA_VERSION,
        "policy": POLICY,
        "result": "success",
        "inputs": {
            "inspection": INSPECTION_FILE.as_posix(),
            "inspection_fingerprint": inspection_digest,
            "expected_sync_offset": EXPECTED_SYNC_OFFSET,
        },
        "counts": {
            "sounds": len(manifest_sounds),
            "output_bytes": sum(sound["output_bytes"] for sound in manifest_sounds),
        },
        "sounds": manifest_sounds,
    }
    problems.extend(validate_against_schema(document, extraction_schema, "extraction"))
    if problems:
        raise ValidationFailure(problems)
    statuses = {path: "extracted" for path in layers["sounded"]}
    # Re-derive check: payloads, digests, and counts recomputed equal.
    for sound, tag_frames in zip(manifest_sounds,
                                 [sound["frames"] for sound in sounds]):
        if hashlib.sha256(tag_frames).hexdigest() != sound["sha256"]:
            problems.append("digest mismatch at sound "
                            + str(sound["character_id"]))
    if problems:
        raise ValidationFailure(problems)
    payloads = {sound["output"]: sound["frames"] for sound in sounds}
    return document, statuses, payloads


def write_outputs(out_root, document, statuses, payloads):
    out = Path(out_root)
    (out / CONVERTED_SOUNDS_DIR).mkdir(parents=True, exist_ok=True)
    (out / REGISTRY_DIR).mkdir(parents=True, exist_ok=True)
    for relative, frames in payloads.items():
        (out / relative).write_bytes(frames)
    extraction_payload = (json.dumps(document, indent=2, sort_keys=True) + "\n"
                          ).encode("utf-8")
    statuses_payload = (json.dumps({"schema_version": SCHEMA_VERSION,
                                    "policy": "asset-statuses-v1",
                                    "statuses": statuses},
                                   indent=2, sort_keys=True) + "\n").encode("utf-8")
    (out / EXTRACTION_FILE).write_bytes(extraction_payload)
    (out / STATUSES_FILE).write_bytes(statuses_payload)
    return {
        "extraction": {
            "file": EXTRACTION_FILE.as_posix(),
            "bytes": len(extraction_payload),
            "sha256": hashlib.sha256(extraction_payload).hexdigest(),
        },
        "statuses": {
            "file": STATUSES_FILE.as_posix(),
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
    document, statuses, payloads = build_package(repo_root, out_root)
    digests = write_outputs(out_root, document, statuses, payloads)
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
