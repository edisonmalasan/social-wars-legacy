"""Focused preservation checks; no server, network, browser, or Flash."""
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import save_fixtures as fixture


class SaveFixturesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = fixture.source_provenance(fixture.ROOT)
        cls.canonical = fixture.capture()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='socialwars-fixture-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in self.sources:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(fixture.ROOT / name, target)
        target = self.root / fixture.FIXTURE_DIR
        target.mkdir(parents=True)
        for name, data in self.canonical.items():
            (target / name).write_bytes(data)
        real_git = fixture.git_read
        git_root = fixture.ROOT
        self.git = patch.object(fixture, 'git_read',
                                side_effect=lambda root, *args: real_git(git_root, *args))
        self.git.start()
        self.addCleanup(self.git.stop)

    def test_actual_path_and_full_state_boundary(self):
        generated = fixture.capture(self.root)
        self.assertEqual(generated, self.canonical)
        before = json.loads(generated[fixture.PRE])
        after = json.loads(generated[fixture.POST])
        self.assertIsNone(before['version'])
        self.assertEqual(after['version'], '0.02a')
        self.assertEqual(after['playerInfo']['pid'], fixture.PLAYER_ID)
        self.assertEqual(after['maps'][0]['timestamp'], fixture.TIMESTAMP)
        self.assertEqual(before['privateState']['timeStampDartsReset'], 0)

    def test_unknown_fields_survive_actual_migration_and_persistence(self):
        # Only a disposable test template changes; this is not canonical history.
        initial_path = self.root / 'villages/initial.json'
        initial = json.loads(initial_path.read_bytes())
        unknown = {'nested': [None, {'opaque': 'retained'}]}
        initial['uninterpreted_test_field'] = unknown
        initial['maps'][0]['uninterpreted_test_field'] = unknown
        initial_path.write_bytes(fixture.json_bytes(initial))
        output = self.root / 'capture'
        output.mkdir()
        result = subprocess.run(
            [sys.executable, '-I', '-B', str(Path(fixture.__file__).resolve()),
             '_capture', '--child-root', str(self.root), '--child-output', str(output)],
            cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in (fixture.PRE, fixture.POST):
            state = json.loads((output / name).read_bytes())
            self.assertEqual(state['uninterpreted_test_field'], unknown)
            self.assertEqual(state['maps'][0]['uninterpreted_test_field'], unknown)

    def test_two_generations_are_identical_and_only_named_outputs_change(self):
        marker = self.root / fixture.FIXTURE_DIR / 'unrelated.txt'
        marker.write_bytes(b'keep')
        first = fixture.generate(self.root)
        second = fixture.generate(self.root)
        self.assertEqual(first, second)
        self.assertEqual(marker.read_bytes(), b'keep')
        self.assertFalse((self.root / 'saves').exists())

    def test_manifest_independent_hashes_sizes_and_provenance(self):
        manifest = json.loads(self.canonical[fixture.MANIFEST])
        self.assertEqual(manifest['baseline_commit'], fixture.BASELINE)
        self.assertEqual(manifest['sources'], self.sources)
        self.assertEqual(len(manifest['fixtures']), 2)
        for entry in manifest['fixtures']:
            data = self.canonical[Path(entry['path']).name]
            self.assertEqual(entry['size'], len(data))
            self.assertEqual(entry['sha256'], hashlib.sha256(data).hexdigest())
        for name in ('early_game', 'mid_game', 'late_game', 'stress_town'):
            self.assertEqual(manifest['coverage'][name], 'unavailable/unverified')

    def test_verify_is_read_only_and_preserves_existing_runtime_saves(self):
        saves = self.root / 'saves'
        saves.mkdir()
        (saves / 'untouched.save.json').write_bytes(b'opaque original save')
        before = fixture.snapshot(self.root)
        fixture.verify(self.root)
        self.assertEqual(fixture.snapshot(self.root), before)

    def test_tampered_fixtures_and_manifest_fail_without_repair(self):
        target = self.root / fixture.FIXTURE_DIR
        for name in (fixture.PRE, fixture.POST, fixture.MANIFEST):
            with self.subTest(name=name):
                path = target / name
                original = path.read_bytes()
                path.write_bytes(original + b' ')
                before = fixture.snapshot(self.root)
                with self.assertRaisesRegex(fixture.FixtureError, name):
                    fixture.verify(self.root)
                self.assertEqual(fixture.snapshot(self.root), before)
                path.write_bytes(original)

    def test_source_drift_fails_before_capture_and_does_not_refresh_outputs(self):
        path = self.root / 'version.py'
        path.write_bytes(path.read_bytes() + b'\n# drift\n')
        before = fixture.snapshot(self.root)
        with self.assertRaisesRegex(fixture.FixtureError, 'Baseline source drift: version.py'):
            fixture.generate(self.root)
        self.assertEqual(fixture.snapshot(self.root), before)

    def test_cli_source_rejection_is_actionable_and_nonzero(self):
        path = self.root / 'sessions.py'
        path.write_bytes(path.read_bytes() + b'\n# drift\n')
        before = fixture.snapshot(self.root)
        error = io.StringIO()
        with patch.object(fixture, 'ROOT', self.root), \
                patch.object(Path, 'cwd', return_value=self.root), \
                patch.object(sys, 'argv', ['save_fixtures.py', 'generate']), \
                patch.object(sys, 'stderr', error):
            self.assertEqual(fixture.main(), 1)
        self.assertIn('Baseline source drift: sessions.py', error.getvalue())
        self.assertEqual(fixture.snapshot(self.root), before)

    def test_cli_tamper_rejection_is_actionable_and_nonzero(self):
        path = self.root / fixture.FIXTURE_DIR / fixture.POST
        path.write_bytes(path.read_bytes() + b' ')
        before = fixture.snapshot(self.root)
        error = io.StringIO()
        with patch.object(fixture, 'ROOT', self.root), \
                patch.object(Path, 'cwd', return_value=self.root), \
                patch.object(sys, 'argv', ['save_fixtures.py', 'verify']), \
                patch.object(sys, 'stderr', error):
            self.assertEqual(fixture.main(), 1)
        self.assertIn('tests/saves/fresh-player.json', error.getvalue().replace('\\', '/'))
        self.assertEqual(fixture.snapshot(self.root), before)

    def test_manifest_provenance_drift_is_detected(self):
        path = self.root / fixture.FIXTURE_DIR / fixture.MANIFEST
        manifest = json.loads(path.read_bytes())
        manifest['baseline_commit'] = '0' * 40
        path.write_text(json.dumps(manifest), encoding='utf-8')
        before = fixture.snapshot(self.root)
        with self.assertRaisesRegex(fixture.FixtureError, 'manifest.json'):
            fixture.verify(self.root)
        self.assertEqual(fixture.snapshot(self.root), before)

    def test_missing_evidence_fails_without_writing(self):
        (self.root / fixture.FIXTURE_DIR / fixture.PRE).unlink()
        before = fixture.snapshot(self.root)
        with self.assertRaisesRegex(fixture.FixtureError, 'Missing canonical fixture'):
            fixture.verify(self.root)
        self.assertEqual(fixture.snapshot(self.root), before)


if __name__ == '__main__':
    unittest.main()
