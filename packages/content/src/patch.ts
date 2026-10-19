/**
 * A dependency-free JSON Patch (RFC 6902) applier.
 *
 * The upstream config is patched by five JSON-Patch files, applied in the
 * order listed in `config/patch/patches.txt`. Those patches only use `add`
 * and `replace`, but a general applier is implemented here so the build never
 * silently ignores an operation it does not understand — an unknown `op` is a
 * hard error, not a no-op.
 *
 * The order matters: `atom_fusion_item` and `unit_patch` append to `/items`,
 * and `atom_fusion_items_data` then modifies specific item indices. Applying
 * them out of order corrupts the content.
 */

export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue };

export type JsonObject = { [key: string]: JsonValue };

export type PatchOperation =
  | { op: 'add'; path: string; value: JsonValue }
  | { op: 'replace'; path: string; value: JsonValue }
  | { op: 'remove'; path: string }
  | { op: 'move'; from: string; path: string }
  | { op: 'copy'; from: string; path: string }
  | { op: 'test'; path: string; value: JsonValue };

export class PatchError extends Error {
  readonly operation: PatchOperation;
  readonly index: number;

  constructor(message: string, operation: PatchOperation, index: number) {
    super(message);
    this.name = 'PatchError';
    this.operation = operation;
    this.index = index;
  }
}

/** Split a JSON Pointer into its unescaped reference tokens. */
export function parsePointer(pointer: string): string[] {
  if (pointer === '') return [];
  if (!pointer.startsWith('/')) {
    throw new Error(`invalid JSON pointer: ${JSON.stringify(pointer)}`);
  }
  return pointer
    .slice(1)
    .split('/')
    .map((token) => token.replace(/~1/g, '/').replace(/~0/g, '~'));
}

function isArrayIndex(token: string): boolean {
  return /^(0|[1-9][0-9]*)$/.test(token);
}

/** Resolve a pointer to the container that holds the final token. */
function resolveParent(
  root: JsonValue,
  tokens: string[],
  operation: PatchOperation,
  index: number,
): { parent: JsonValue[] | JsonObject; key: string } {
  let current: JsonValue = root;
  for (let i = 0; i < tokens.length - 1; i++) {
    const token = tokens[i]!;
    if (Array.isArray(current)) {
      if (!isArrayIndex(token)) {
        throw new PatchError(`expected an array index, got ${JSON.stringify(token)}`, operation, index);
      }
      const next = current[Number(token)];
      if (next === undefined) {
        throw new PatchError(`path does not exist: ${JSON.stringify(token)}`, operation, index);
      }
      current = next;
    } else if (current !== null && typeof current === 'object') {
      const next = (current as JsonObject)[token];
      if (next === undefined) {
        throw new PatchError(`path does not exist: ${JSON.stringify(token)}`, operation, index);
      }
      current = next;
    } else {
      throw new PatchError(`cannot descend into a ${typeof current}`, operation, index);
    }
  }
  const key = tokens[tokens.length - 1]!;
  const parent = current;
  if (!Array.isArray(parent) && (parent === null || typeof parent !== 'object')) {
    throw new PatchError('cannot resolve a parent for this path', operation, index);
  }
  return { parent: parent as JsonValue[] | JsonObject, key };
}

function getAtPointer(root: JsonValue, pointer: string): JsonValue {
  const tokens = parsePointer(pointer);
  let current: JsonValue = root;
  for (const token of tokens) {
    if (Array.isArray(current)) {
      if (!isArrayIndex(token)) throw new Error(`invalid array index in ${pointer}`);
      const next = current[Number(token)];
      if (next === undefined) throw new Error(`path does not exist: ${pointer}`);
      current = next;
    } else if (current !== null && typeof current === 'object') {
      const next = (current as JsonObject)[token];
      if (next === undefined) throw new Error(`path does not exist: ${pointer}`);
      current = next;
    } else {
      throw new Error(`cannot descend into a ${typeof current} at ${pointer}`);
    }
  }
  return current;
}

function setAtPointer(
  root: JsonValue,
  pointer: string,
  value: JsonValue,
  operation: PatchOperation,
  index: number,
  mode: 'add' | 'replace',
): void {
  const tokens = parsePointer(pointer);
  if (tokens.length === 0) {
    throw new PatchError('cannot replace the document root', operation, index);
  }
  const { parent, key } = resolveParent(root, tokens, operation, index);
  if (Array.isArray(parent)) {
    if (key === '-') {
      if (mode === 'replace') throw new PatchError('"-" is not a valid replace target', operation, index);
      parent.push(value);
      return;
    }
    if (!isArrayIndex(key)) throw new PatchError(`invalid array index ${key}`, operation, index);
    const at = Number(key);
    if (mode === 'add') {
      if (at > parent.length) throw new PatchError(`index ${at} is out of range`, operation, index);
      parent.splice(at, 0, value);
    } else {
      if (at >= parent.length) throw new PatchError(`index ${at} is out of range`, operation, index);
      parent[at] = value;
    }
    return;
  }
  if (mode === 'replace' && !(key in parent)) {
    throw new PatchError(`cannot replace a missing member ${key}`, operation, index);
  }
  parent[key] = value;
}

function removeAtPointer(
  root: JsonValue,
  pointer: string,
  operation: PatchOperation,
  index: number,
): void {
  const tokens = parsePointer(pointer);
  if (tokens.length === 0) throw new PatchError('cannot remove the document root', operation, index);
  const { parent, key } = resolveParent(root, tokens, operation, index);
  if (Array.isArray(parent)) {
    if (!isArrayIndex(key)) throw new PatchError(`invalid array index ${key}`, operation, index);
    const at = Number(key);
    if (at >= parent.length) throw new PatchError(`index ${at} is out of range`, operation, index);
    parent.splice(at, 1);
    return;
  }
  if (!(key in parent)) throw new PatchError(`cannot remove a missing member ${key}`, operation, index);
  delete parent[key];
}

/** Apply a patch document to a copy of `document`, returning the result. */
export function applyPatch(document: JsonValue, patch: PatchOperation[]): JsonValue {
  const root = structuredClone(document);
  patch.forEach((operation, index) => {
    switch (operation.op) {
      case 'add':
        setAtPointer(root, operation.path, structuredClone(operation.value), operation, index, 'add');
        break;
      case 'replace':
        setAtPointer(root, operation.path, structuredClone(operation.value), operation, index, 'replace');
        break;
      case 'remove':
        removeAtPointer(root, operation.path, operation, index);
        break;
      case 'move': {
        const value = getAtPointer(root, operation.from);
        removeAtPointer(root, operation.from, operation, index);
        setAtPointer(root, operation.path, structuredClone(value), operation, index, 'add');
        break;
      }
      case 'copy': {
        const value = getAtPointer(root, operation.from);
        setAtPointer(root, operation.path, structuredClone(value), operation, index, 'add');
        break;
      }
      case 'test': {
        const value = getAtPointer(root, operation.path);
        if (JSON.stringify(value) !== JSON.stringify(operation.value)) {
          throw new PatchError(`test failed at ${operation.path}`, operation, index);
        }
        break;
      }
      default: {
        const unknown = operation as { op: string };
        throw new PatchError(`unsupported patch operation: ${unknown.op}`, operation, index);
      }
    }
  });
  return root;
}
