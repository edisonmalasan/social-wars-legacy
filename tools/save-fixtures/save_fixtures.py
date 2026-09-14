"""Controlled legacy save evidence; standard-library tooling for Python 3.9."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
from unittest.mock import patch


BASELINE = 'e8c98a03c902eba70323538dc5d4eaba2f2927a1'
ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path('tests/saves')
PRE = 'fresh-player-pre-migration.json'
POST = 'fresh-player.json'
MANIFEST = 'manifest.json'
PLAYER_ID = '00000000-0000-4000-8000-000000000001'
TIMESTAMP = 1700000000
MODULES = ('sessions.py', 'version.py', 'bundle.py', 'engine.py',
           'constants.py', 'get_game_config.py', 'villages/initial.json')


class FixtureError(Exception):
    """Evidence could not be captured or verified."""


def git_read(root, *args):
    env = {key: value for key, value in os.environ.items()
           if not key.startswith('GIT_')}
    env.update(GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1',
               GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
    result = subprocess.run(
        ['git', '--no-replace-objects', '-c', 'protocol.allow=never',
         '-C', str(root), *args], env=env, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise FixtureError('Local baseline Git read failed: ' + args[0])
    return result.stdout


def source_provenance(root):
    resolved = git_read(root, 'rev-parse', '--verify', BASELINE + '^{commit}')
    if resolved.strip().decode('ascii') != BASELINE:
        raise FixtureError('Baseline commit mismatch: ' + BASELINE)
    # Include the real import closure and configuration consumed at import time.
    records = git_read(root, 'ls-tree', '-r', '-z', BASELINE, '--',
                       *MODULES, 'config', 'mods')
    sources = {}
    for record in records.rstrip(b'\0').split(b'\0'):
        metadata, name = record.split(b'\t')
        mode, kind, oid = metadata.decode('ascii').split()
        path = name.decode('utf-8')
        if mode not in ('100644', '100755') or kind != 'blob':
            raise FixtureError('Baseline source is not a regular file: ' + path)
        target = root / path
        if target.is_symlink() or not target.is_file():
            raise FixtureError('Missing or linked provenance source: ' + path)
        blob = git_read(root, 'cat-file', 'blob', oid)
        actual = target.read_bytes()
        # Git checkout may materialize these textual sources as CRLF on Windows.
        if actual.replace(b'\r\n', b'\n') != blob.replace(b'\r\n', b'\n'):
            raise FixtureError('Baseline source drift: ' + path)
        sources[path] = {'git_blob': oid, 'sha256': hashlib.sha256(blob).hexdigest(),
                         'size': len(blob)}
    for path in MODULES:
        if path not in sources:
            raise FixtureError('Baseline lacks required source: ' + path)
    return sources


def snapshot(path):
    if not path.exists():
        return None
    if not path.is_dir():
        return ('file', path.read_bytes())
    return {str(item.relative_to(path)): (None if item.is_dir() else item.read_bytes())
            for item in path.rglob('*')}


def json_bytes(value):
    # Legacy indent/ensure_ascii/key order, with no final newline.
    return json.dumps(value, indent=4).replace('\n', '\r\n').encode('ascii')


def capture_in_child(root, output):
    """Only called by the isolated child; all legacy state dies with that child."""
    sys.path.insert(0, str(root))
    import sessions
    import version
    import engine

    sessions.__saves = {}
    sessions.__villages = {}
    sessions.__quests = {}
    sessions.SAVES_DIR = str(output)
    before = []
    migrate = version.migrate_loaded_save

    def migration_boundary(state):
        before.append(copy.deepcopy(state))
        return migrate(state)

    with patch.object(sessions.uuid, 'uuid4', return_value=uuid.UUID(PLAYER_ID)), \
            patch.object(sessions, 'timestamp_now', return_value=TIMESTAMP), \
            patch.object(version, 'timestamp_now', return_value=TIMESTAMP), \
            patch.object(engine, 'timestamp_now', return_value=TIMESTAMP), \
            patch.object(sessions, 'migrate_loaded_save', migration_boundary):
        player = sessions.new_village()
        if player != PLAYER_ID or len(before) != 1:
            raise FixtureError('Actual new_village path did not reach migration once')
        persisted = (output / (player + '.save.json')).read_bytes()
        after = json.loads(persisted)
        if not sessions.is_valid_village(after):
            raise FixtureError('Persisted fresh-player state failed legacy validation')
        migrated = copy.deepcopy(before[0])
        migrate(migrated)
        if migrated != after or sessions.session(player) != after:
            raise FixtureError('Full-state migration/persistence mismatch: ' + POST)
        if persisted != json_bytes(after):
            raise FixtureError('Unexpected legacy persisted serialization: ' + POST)
    (output / PRE).write_bytes(json_bytes(before[0]))
    (output / POST).write_bytes(persisted)


def capture(root=ROOT):
    root = root.resolve()
    sources = source_provenance(root)
    saves_before = snapshot(root / 'saves')
    with tempfile.TemporaryDirectory(prefix='socialwars-save-fixtures-') as name:
        output = Path(name)
        result = subprocess.run(
            [sys.executable, '-I', '-B', str(Path(__file__).resolve()),
             '_capture', '--child-root', str(root), '--child-output', str(output)],
            cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if snapshot(root / 'saves') != saves_before:
            raise FixtureError('Capture changed repository runtime path: saves/')
        if result.returncode:
            raise FixtureError('Legacy capture child failed: ' +
                               result.stderr.decode('utf-8', errors='replace').strip())
        files = {PRE: (output / PRE).read_bytes(), POST: (output / POST).read_bytes()}
    if source_provenance(root) != sources:
        raise FixtureError('Provenance changed during capture')
    controls = {'uuid': PLAYER_ID, 'timestamp': TIMESTAMP}
    manifest = {
        'schema_version': 1, 'algorithm': 'sha256', 'baseline_commit': BASELINE,
        'source_comparison': 'Git blob bytes, permitting only CRLF/LF checkout conversion',
        'sources': sources, 'controlled_inputs': controls,
        'serialization': 'Windows ASCII JSON, CRLF, indent=4, insertion order, no final newline; persisted bytes unchanged',
        'classification': 'controlled repository behavior; not historical player observations',
        'coverage': {
            'fresh_player': 'verified controlled canonical input',
            'migration_boundary': 'verified complete controlled before/after states',
            'early_game': 'unavailable/unverified', 'mid_game': 'unavailable/unverified',
            'late_game': 'unavailable/unverified', 'stress_town': 'unavailable/unverified',
            'static_neighbors': 'non-player static content; not progression substitutes'},
        'fixtures': [
            {'path': (FIXTURE_DIR / name).as_posix(), 'role': role,
             'classification': 'controlled canonical test input',
             'controlled_inputs': controls, 'baseline_commit': BASELINE,
             'source_blob_ids': {path: entry['git_blob'] for path, entry in sources.items()},
             'sha256': hashlib.sha256(files[name]).hexdigest(), 'size': len(files[name])}
            for name, role in ((PRE, 'pre-migration input'),
                               (POST, 'persisted fresh-player/post-migration output'))]}
    files[MANIFEST] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode('utf-8')
    return files


def canonical_directory(root):
    target = root / FIXTURE_DIR
    for path in (root / 'tests', target, *(target / name for name in (PRE, POST, MANIFEST))):
        if path.is_symlink() or path.resolve() != path.absolute():
            raise FixtureError('Canonical output is linked or redirected: ' + str(path))
    return target


def generate(root=ROOT):
    target = canonical_directory(root)
    files = capture(root)
    target.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (target / name).write_bytes(data)
    return files


def verify(root=ROOT):
    target = canonical_directory(root)
    files = capture(root)
    for name, expected in files.items():
        path = target / name
        if not path.is_file():
            raise FixtureError('Missing canonical fixture: ' + str(FIXTURE_DIR / name))
        if path.read_bytes() != expected:
            raise FixtureError('Integrity/content/provenance mismatch: ' + str(FIXTURE_DIR / name))
    return files


def main():
    sys.dont_write_bytecode = True
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('generate', 'verify', '_capture'))
    parser.add_argument('--child-root', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--child-output', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.command == '_capture':
            if args.child_root is None or args.child_output is None:
                raise FixtureError('Internal capture requires disposable child paths')
            capture_in_child(args.child_root, args.child_output)
        else:
            if Path.cwd().resolve() != ROOT:
                raise FixtureError('Run from repository root: ' + str(ROOT))
            files = generate(ROOT) if args.command == 'generate' else verify(ROOT)
            print(args.command + ': verified 2 controlled fixtures and manifest (' +
                  str(sum(len(value) for value in files.values())) + ' bytes)')
    except (FixtureError, OSError, ValueError) as exc:
        print('save-fixtures: ' + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
