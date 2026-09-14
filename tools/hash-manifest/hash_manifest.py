"""Opaque, immutable Git-blob integrity evidence; Python 3.9 standard library."""
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile


EXTENSIONS = frozenset({'.swf', '.json', '.xml', '.png', '.jpg', '.jpeg',
                        '.mp3', '.wav', '.gif'})
PROTECTED = frozenset({'assets', 'config', 'villages', 'mods', 'templates',
                       'stub', 'tools', 'saves', 'auctions', '.git'})
COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
DIGEST = re.compile(r'[0-9a-f]{64}')


class ManifestError(Exception):
    """Invalid input, unavailable source, I/O or Git protocol failure."""


@dataclass(frozen=True)
class Blob:
    path: str
    oid: str


def git_environment():
    # Prevent ambient Git routing/replacement and partial-clone lazy fetching.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith('GIT_')}
    env.update(GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1',
               GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
    return env


def git_command(repo, *args):
    return ['git', '--no-replace-objects', '-c', 'protocol.allow=never',
            '-C', str(repo), *args]


def git_read(repo, *args):
    try:
        result = subprocess.run(git_command(repo, *args), env=git_environment(),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                check=False)
    except OSError as exc:
        raise ManifestError('Cannot launch local Git') from exc
    if result.returncode:
        # Git stderr can contain user-controlled data; never echo asset content.
        raise ManifestError('Local Git command failed: ' + args[0])
    return result.stdout


def repository(path):
    root = git_read(path, 'rev-parse', '--show-toplevel').rstrip(b'\n')
    try:
        return Path(os.fsdecode(root)).resolve(strict=True)
    except OSError as exc:
        raise ManifestError('Repository root is unavailable') from exc


def resolve_commit(repo, ref):
    if not ref or ref.startswith('-') or '\x00' in ref:
        raise ManifestError('Invalid source ref')
    value = git_read(repo, 'rev-parse', '--verify', '--end-of-options',
                     ref + '^{commit}').strip().decode('ascii')
    if not COMMIT.fullmatch(value):
        raise ManifestError('Invalid resolved commit')
    return value


def validate_path(path):
    if (not isinstance(path, str) or not path or '\\' in path
            or ':' in path or any(ord(c) < 32 or ord(c) == 127 for c in path)
            or path.startswith('/')
            or any(part in ('', '.', '..') for part in path.split('/'))):
        raise ManifestError('Unsafe repository-relative path')
    try:
        path.encode('utf-8', errors='strict')
    except UnicodeError as exc:
        raise ManifestError('Path is not valid UTF-8') from exc
    # Windows aliases (trailing dots/spaces, devices) must not become ambiguous.
    for part in path.split('/'):
        stem = part.split('.')[0].casefold()
        if (part.endswith((' ', '.')) or stem in {'con', 'prn', 'aux', 'nul'}
                or re.fullmatch(r'(com|lpt)[1-9]', stem)):
            raise ManifestError('Ambiguous repository-relative path')
    return path


def parse_tree(raw):
    if not raw.endswith(b'\x00'):
        raise ManifestError('Incomplete Git tree response')
    blobs = []
    seen = set()
    for record in raw[:-1].split(b'\x00'):
        try:
            metadata, raw_path = record.split(b'\t', 1)
            mode, kind, oid = metadata.decode('ascii').split(' ')
            path = raw_path.decode('utf-8', errors='strict')
        except (ValueError, UnicodeError) as exc:
            raise ManifestError('Malformed Git tree response') from exc
        if PurePosixPath(path).suffix.lower() not in EXTENSIONS:
            continue
        validate_path(path)
        if mode not in ('100644', '100755') or kind != 'blob':
            raise ManifestError('Selected entry is not a regular Git blob')
        if not COMMIT.fullmatch(oid):
            raise ManifestError('Malformed Git object identity')
        if path.casefold() in seen:
            raise ManifestError('Case-insensitive selected path collision')
        seen.add(path.casefold())
        blobs.append(Blob(path, oid))
    if not blobs:
        raise ManifestError('Empty asset selection')
    return sorted(blobs, key=lambda blob: blob.path)


def read_blob(stream, oid):
    header = stream.readline(256)
    try:
        object_id, kind, length = header.rstrip(b'\n').split(b' ')
    except ValueError as exc:
        raise ManifestError('Malformed or unavailable Git batch object') from exc
    if (not header.endswith(b'\n') or object_id != oid.encode('ascii')
            or kind != b'blob' or not re.fullmatch(b'0|[1-9][0-9]*', length)):
        raise ManifestError('Invalid Git batch header')
    size = int(length)
    remaining = size
    digest = hashlib.sha256()
    while remaining:
        data = stream.read(min(1024 * 1024, remaining))
        if not data:
            raise ManifestError('Truncated Git blob')
        digest.update(data)
        remaining -= len(data)
    if stream.read(1) != b'\n':
        raise ManifestError('Missing Git batch separator')
    return digest.hexdigest(), size


def hash_blobs(repo, blobs):
    # A disk-backed stderr sink prevents pipe deadlocks without buffering assets.
    with tempfile.TemporaryFile() as errors:
        try:
            process = subprocess.Popen(git_command(repo, 'cat-file', '--batch'),
                                       env=git_environment(), stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=errors)
        except OSError as exc:
            raise ManifestError('Cannot launch local Git batch') from exc
        try:
            entries = []
            for blob in blobs:
                process.stdin.write(blob.oid.encode('ascii') + b'\n')
                process.stdin.flush()
                digest, size = read_blob(process.stdout, blob.oid)
                entries.append({'path': blob.path, 'sha256': digest, 'size': size})
            process.stdin.close()
            if process.stdout.read(1):
                raise ManifestError('Unexpected extra Git batch output')
            if process.wait():
                raise ManifestError('Local Git batch failed')
            return entries
        except (OSError, ValueError) as exc:
            raise ManifestError('Git batch I/O failure') from exc
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            if not process.stdin.closed:
                process.stdin.close()
            process.stdout.close()


def build_manifest(repo, commit):
    blobs = parse_tree(git_read(repo, 'ls-tree', '-r', '-z', '--full-tree', commit))
    return {'schema_version': 1, 'algorithm': 'sha256',
            'source': {'kind': 'git-blob', 'commit': commit},
            'policy': 'legacy-assets-v1', 'files': hash_blobs(repo, blobs)}


def serialize(manifest):
    return (json.dumps(manifest, ensure_ascii=True, indent=2,
                       allow_nan=False) + '\n').encode('utf-8')


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError('Duplicate JSON key')
        result[key] = value
    return result


def fixed_keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ManifestError('Invalid manifest fields')


def parse_manifest(raw):
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=unique_object,
                           parse_constant=lambda _: None)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ManifestError('Malformed manifest JSON') from exc
    fixed_keys(value, ('schema_version', 'algorithm', 'source', 'policy', 'files'))
    if (type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['algorithm'] != 'sha256' or value['policy'] != 'legacy-assets-v1'):
        raise ManifestError('Unsupported manifest schema, algorithm or policy')
    fixed_keys(value['source'], ('kind', 'commit'))
    source = value['source']
    if (source['kind'] != 'git-blob' or not isinstance(source['commit'], str)
            or not COMMIT.fullmatch(source['commit'])):
        raise ManifestError('Invalid manifest source')
    if not isinstance(value['files'], list) or not value['files']:
        raise ManifestError('Invalid manifest file array')
    seen = set()
    for entry in value['files']:
        fixed_keys(entry, ('path', 'sha256', 'size'))
        path = validate_path(entry['path'])
        if path.casefold() in seen:
            raise ManifestError('Duplicate or ambiguous manifest path')
        seen.add(path.casefold())
        if (not isinstance(entry['sha256'], str)
                or not DIGEST.fullmatch(entry['sha256'])
                or type(entry['size']) is not int or entry['size'] < 0):
            raise ManifestError('Invalid manifest digest or size')
    return value


def safe_output(repo, output):
    output = Path(output).absolute()
    resolved = output.resolve()
    # Do not follow an output symlink even outside the repository.
    if output.is_symlink():
        raise ManifestError('Output must not be a symlink')
    # Check lexical placement as well as the destination: a protected directory
    # itself may be a symlink to an external preservation store.
    for candidate in (output, resolved):
        try:
            parts = candidate.relative_to(repo).parts
        except ValueError:
            continue
        if not parts or parts[0].casefold() in PROTECTED:
            raise ManifestError('Output is inside a protected input path')
    for name in PROTECTED:
        protected = (repo / name).resolve()
        if resolved == protected or protected in resolved.parents:
            raise ManifestError('Output resolves inside a protected input path')
    try:
        relative = resolved.relative_to(repo)
    except ValueError:
        return output
    # Also protect tracked source files outside conventional preservation roots.
    tracked = git_read(repo, 'ls-files', '-z').split(b'\x00')
    selected = relative.as_posix().casefold()
    if selected != 'legacy-manifest.json' and any(
            os.fsdecode(path).casefold() == selected for path in tracked if path):
        raise ManifestError('Output would overwrite a tracked input')
    return output


def atomic_write(output, raw):
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=output.parent, prefix='.hash-manifest-',
                                         delete=False) as handle:
            name = handle.name
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, output)
        name = None
    finally:
        if name is not None:
            os.unlink(name)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    default_repo = Path(__file__).resolve().parents[2]
    for command in ('generate', 'verify'):
        child = commands.add_parser(command)
        child.add_argument('--repo', type=Path, default=default_repo)
        if command == 'generate':
            child.add_argument('--ref', default='legacy-baseline')
            child.add_argument('--output', type=Path)
        else:
            child.add_argument('--manifest', type=Path)
    args = parser.parse_args(argv)
    try:
        repo = repository(args.repo)
        if args.command == 'generate':
            output = safe_output(repo, args.output or repo / 'legacy-manifest.json')
            manifest = build_manifest(repo, resolve_commit(repo, args.ref))
            atomic_write(output, serialize(manifest))
        else:
            raw = (args.manifest or repo / 'legacy-manifest.json').read_bytes()
            recorded = parse_manifest(raw)
            commit = recorded['source']['commit']
            if resolve_commit(repo, commit) != commit:
                raise ManifestError('Recorded source identity does not resolve exactly')
            manifest = build_manifest(repo, commit)
            if raw != serialize(manifest):
                print('Integrity mismatch: manifest entries or canonical bytes differ',
                      file=sys.stderr)
                return 1
        print('{}: {} entries, {} bytes, commit {}'.format(
            args.command, len(manifest['files']),
            sum(entry['size'] for entry in manifest['files']),
            manifest['source']['commit']))
        return 0
    except (ManifestError, OSError, UnicodeError, ValueError) as exc:
        print('Manifest error: {}'.format(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
