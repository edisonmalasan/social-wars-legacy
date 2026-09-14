## Context

The schema-version-1 recorder stores sanitized complete `before` and `after` objects around the in-memory `command()` boundary; failed commands can contain partial unsaved mutations, while parse failures can contain equal states. The controlled fresh-player fixture has nested dictionaries, positional arrays, exact string instance keys, unknown-compatible fields, and one verified migration-boundary difference at `/version`. No general structural differ or recorder JSON Schema exists, and importing legacy runtime modules can load content or runtime state. See `proposal.md` and the new capability spec for scope.

## Goals / Non-Goals

**Goals:**

- Provide one dependency-free comparison core and thin CLI that run on the verified Windows x64 CPython 3.9.13 environment.
- Make reports deterministic, reviewable, value-free, and explicit about state type and path changes.
- Bound memory/work and keep every failure read-only, diagnosable, and safe to share at the category level.
- Test against canonical fixtures as read-only evidence while labeling synthetic edge cases as controlled focused tests.

**Non-Goals:**

- Producing JSON Patch, applying changes, replaying commands, validating gameplay semantics, or declaring persistence.
- Reordering/matching legacy collections by inferred IDs, normalizing clocks/resources, ignoring paths, or adding domain summaries.
- Capturing or promoting evidence, acquiring progressed-player saves, changing recorder policy, or integrating into Flask.

## Decisions

### Use explicit mutually exclusive input modes

The CLI will expose `compare --before <file> --after <file>` and `compare --record <file>`. Explicit modes prevent a village containing fields named `before` or `after` from being mistaken for a transaction record. Record mode validates integer schema version `1` and object boundaries while allowing unknown metadata; pair mode requires object roots. Both read regular files only and do not import legacy modules.

Alternative: infer input shape. Rejected because unknown fields are preservation evidence and shape inference can silently select the wrong semantics.

### Emit a structural, value-free schema

One pure comparison walk will create entries containing operation, RFC 6901 path, and strict before/after type labels. Dictionary keys are traversed in Python string order; arrays remain positional; additions/removals are summarized at subtree roots. The final document is serialized once to memory and then written to stdout, so validation or serialization failures cannot emit a partial JSON document.

Alternative: include sanitized old/new values or generate JSON Patch. Rejected because values increase privacy exposure and an executable patch implies semantics the preservation evidence does not establish.

### Preserve JSON types and reject ambiguous JSON

A strict loader rejects duplicate names, non-finite numbers, and invalid Unicode input. The comparison distinguishes `bool`, `integer`, and `number`, avoiding Python's normal equality between `True`, `1`, and `1.0`. It performs no schema projection, migration, tolerance, or key coercion.

Alternative: use ordinary permissive `json.load` and Python equality. Rejected because both can conceal evidence differences.

### Bound work before publishing output

Each input is limited to 16 MiB; traversal tracks at most 128 container levels, 1,000,000 visited nodes, and 100,000 change entries. Exceeding a limit aborts with exit `2`. These conservative fixed limits cover the current 15 KiB fixtures and recorded village structures while preventing an offline diagnostic from consuming unbounded memory or recursion.

Alternative: unlimited traversal or silently truncated reports. Rejected because either can exhaust the process or present incomplete evidence as complete.

### Keep path sanitization local and compatibility-tested

The tool will implement a small pure sensitive-key/value collector compatible with the documented recorder policy rather than import the recorder module or legacy application. It compares original structures, then protects reported path components. A protected-path collision aborts the report; it never coalesces entries. Tests pin compatibility against representative recorder-sensitive keys and repeated secret strings.

Alternative: reuse the recorder module directly. Rejected because the diff capability should remain standalone and because shared imports could make future recorder changes alter historical report behavior without an explicit spec change.

### Keep diagnostics categorical

CLI exceptions map to fixed categories such as `before input invalid`, `record evidence unavailable`, `comparison limit exceeded`, or `output failed`. Decoder messages, filenames, paths, keys, values, exception text, and tracebacks are never printed. Broken stdout returns exit `2` where the platform exposes it.

Alternative: surface raw exceptions. Rejected because raw decoder and filesystem errors can disclose evidence or machine paths.

## Risks / Trade-offs

- [Value-free output cannot explain the semantic meaning of a change] → Preserve exact paths/types now; command catalogs and domain-aware analysis remain separate roadmap work.
- [Positional arrays can produce many changes after insertion] → Preserve the legacy representation faithfully and avoid inventing identifier semantics.
- [Known-sensitive-value collection cannot identify arbitrary personal or encoded data] → Emit no values, classify reports as private evidence, and document the limitation.
- [Fixed limits may reject a future very large authentic town] → Fail explicitly; changing limits later requires deliberate capability review rather than silent truncation.
- [A process can fail while stdout is being consumed] → Serialize completely before the first write and document that shell redirection lies outside tool containment.

## Migration Plan

Add the tool, focused tests, and documentation without changing existing runtime entry points. Rollback removes only those new files and their documentation links; recorder records and canonical fixtures are unaffected because the tool is read-only.
