"""Focused synthetic-repository tests; no application or preservation execution."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import hash_manifest as hm


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Synthetic test')
        self.git('config', 'user.email', 'synthetic@example.invalid')
        self.git('config', 'core.autocrlf', 'false')
        self.payloads = {}
        for index, suffix in enumerate(sorted(hm.EXTENSIONS)):
            path = 'assets/Space {}{}'.format(index, suffix.upper())
            data = b'\x00\xff\r\n\n' + bytes([index])
            self.write(path, data)
            self.payloads[path] = data
        self.write('config/lines.json', b'{"a":1}\n')
        self.payloads['config/lines.json'] = b'{"a":1}\n'
        self.write('assets/duplicate.png', self.payloads['assets/Space 0.GIF'])
        self.payloads['assets/duplicate.png'] = self.payloads['assets/Space 0.GIF']
        for suffix in ('.txt', '.csv', '.ico', '.py'):
            self.write('excluded' + suffix, b'excluded')
        self.git('add', '.')
        self.git('commit', '-qm', 'Synthetic baseline')
        self.git('tag', 'legacy-baseline')
        self.commit = hm.resolve_commit(self.repo, 'legacy-baseline')
        self.output = Path(self.temp.name) / 'manifest.json'

    def git(self, *args):
        result = subprocess.run(hm.git_command(self.repo, *args),
                                env=hm.git_environment(), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def write(self, path, data):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def generate(self):
        self.assertEqual(hm.main(['generate', '--repo', str(self.repo),
                                  '--output', str(self.output)]), 0)
        return self.output.read_bytes()

    def verify(self):
        return hm.main(['verify', '--repo', str(self.repo),
                        '--manifest', str(self.output)])

    def test_all_suffixes_binary_duplicates_order_and_later_files(self):
        self.write('assets/later.json', b'later')
        self.git('add', '.')
        self.git('commit', '-qm', 'Later selected file')
        self.write('assets/untracked.json', b'untracked')
        raw = self.generate()
        manifest = hm.parse_manifest(raw)
        self.assertEqual(manifest['source']['commit'], self.commit)
        self.assertEqual([entry['path'] for entry in manifest['files']],
                         sorted(self.payloads))
        for entry in manifest['files']:
            data = self.payloads[entry['path']]
            self.assertEqual(entry['sha256'], hashlib.sha256(data).hexdigest())
            self.assertEqual(entry['size'], len(data))
        self.assertEqual(raw, self.generate())
        self.assertEqual(self.verify(), 0)

    def test_checkout_line_endings_and_read_only_verification(self):
        raw = self.generate()
        self.git('config', 'core.autocrlf', 'true')
        (self.repo / 'config/lines.json').unlink()
        self.git('checkout', '--', 'config/lines.json')
        self.assertEqual((self.repo / 'config/lines.json').read_bytes(), b'{"a":1}\r\n')
        before = {p: p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        self.assertEqual(self.generate(), raw)
        self.assertEqual(self.verify(), 0)
        self.assertEqual(before, {p: p.read_bytes() for p in self.repo.rglob('*')
                                  if p.is_file()})

    def test_tampering_and_noncanonical_bytes_are_integrity_failures(self):
        original = hm.parse_manifest(self.generate())
        mutations = []
        for action in ('add', 'remove', 'reorder', 'rename', 'digest', 'size'):
            value = copy.deepcopy(original)
            entries = value['files']
            if action == 'add':
                entries.append(dict(entries[0], path='added.png'))
            elif action == 'remove':
                entries.pop()
            elif action == 'reorder':
                entries.reverse()
            elif action == 'rename':
                entries[0]['path'] = 'renamed.png'
            elif action == 'digest':
                entries[0]['sha256'] = '0' * 64
            else:
                entries[0]['size'] += 1
            mutations.append(hm.serialize(value))
        mutations.extend([json.dumps(original).encode(),
                          hm.serialize(original).replace(b'\n', b'\r\n')])
        for raw in mutations:
            with self.subTest(raw=raw[:40]):
                self.output.write_bytes(raw)
                self.assertEqual(self.verify(), 1)
                self.assertEqual(self.output.read_bytes(), raw)

    def test_invalid_schema_and_missing_commit_exit_two(self):
        original = hm.parse_manifest(self.generate())
        variants = [b'not json', b'\xef\xbb\xbf' + hm.serialize(original),
                    hm.serialize(original).replace(b'"size": 6', b'"size": NaN')]
        for key, replacement in [('schema_version', True), ('algorithm', 'sha1'),
                                 ('policy', 'other'), ('files', []), ('extra', 1)]:
            value = copy.deepcopy(original)
            value[key] = replacement
            variants.append(hm.serialize(value))
        for key, replacement in [('size', True), ('size', -1), ('size', 1.5),
                                 ('sha256', 'A' * 64), ('path', '../bad.json')]:
            value = copy.deepcopy(original)
            value['files'][0][key] = replacement
            variants.append(hm.serialize(value))
        value = copy.deepcopy(original)
        value['source']['commit'] = '0' * 40
        variants.append(hm.serialize(value))
        value = copy.deepcopy(original)
        value['source']['kind'] = 'filesystem'
        variants.append(hm.serialize(value))
        variants.append(hm.serialize(original).replace(b'"algorithm": "sha256",',
                       b'"algorithm": "sha256", "algorithm": "sha256",'))
        for raw in variants:
            self.output.write_bytes(raw)
            self.assertEqual(self.verify(), 2)
            self.assertEqual(self.output.read_bytes(), raw)

    def test_failed_generation_preserves_output_and_protects_inputs(self):
        self.output.write_bytes(b'keep')
        self.assertEqual(hm.main(['generate', '--repo', str(self.repo),
                                  '--ref', 'missing', '--output', str(self.output)]), 2)
        self.assertEqual(self.output.read_bytes(), b'keep')
        for path in ('assets/new.json', 'config/lines.json', 'tools/new.json',
                     'saves/new.json', 'excluded.py', '.git/overwrite'):
            self.assertEqual(hm.main(['generate', '--repo', str(self.repo),
                                      '--output', str(self.repo / path)]), 2)
        self.assertFalse((self.repo / 'assets/new.json').exists())
        with mock.patch('hash_manifest.os.replace', side_effect=OSError('synthetic')):
            self.assertEqual(hm.main(['generate', '--repo', str(self.repo),
                                      '--output', str(self.output)]), 2)
        self.assertEqual(self.output.read_bytes(), b'keep')
        self.assertFalse(list(self.output.parent.glob('.hash-manifest-*')))

    def test_batch_protocol_truncation_types_lengths_and_separators(self):
        oid = '1' * 40
        self.assertEqual(hm.read_blob(io.BytesIO((oid + ' blob 0\n\n').encode()), oid),
                         (hashlib.sha256(b'').hexdigest(), 0))
        for raw in (b'', (oid + ' missing\n').encode(),
                    (oid + ' tree 0\n\n').encode(), (oid + ' blob -1\n').encode(),
                    (oid + ' blob 01\nx\n').encode(),
                    (oid + ' blob 2\nx').encode(), (oid + ' blob 1\nx!').encode(),
                    ('2' * 40 + ' blob 0\n\n').encode()):
            with self.assertRaises(hm.ManifestError):
                hm.read_blob(io.BytesIO(raw), oid)

    def test_tree_validation(self):
        oid = '1' * 40
        def tree(path, mode='100644', kind='blob'):
            return '{} {} {}\t'.format(mode, kind, oid).encode() + path + b'\x00'
        for path in (b'../x.json', b'/x.json', b'a//x.json', b'C:/x.json',
                     b'a\\x.json', b'\xff.json', b'CON.json', b'a./x.json',
                     b'a\n.json'):
            with self.assertRaises(hm.ManifestError):
                hm.parse_tree(tree(path))
        for mode, kind in [('120000', 'blob'), ('160000', 'commit')]:
            with self.assertRaises(hm.ManifestError):
                hm.parse_tree(tree(b'link.json', mode, kind))
        for raw in (tree(b'a.json') + tree(b'A.JSON'), tree(b'x.txt'),
                    tree(b'a.json')[:-1], b'bad\x00', b''):
            with self.assertRaises(hm.ManifestError):
                hm.parse_tree(raw)

    def test_real_selected_symlink_and_gitlink(self):
        self.git('update-index', '--add', '--cacheinfo',
                 '120000,{},link.json'.format(self.git('rev-parse',
                 'HEAD:config/lines.json').decode().strip()))
        self.git('commit', '-qm', 'Synthetic symlink')
        with self.assertRaises(hm.ManifestError):
            hm.build_manifest(self.repo, hm.resolve_commit(self.repo, 'HEAD'))
        self.git('update-index', '--force-remove', 'link.json')
        self.git('update-index', '--add', '--cacheinfo',
                 '160000,{},link.json'.format(self.commit))
        self.git('commit', '-qm', 'Synthetic gitlink')
        with self.assertRaises(hm.ManifestError):
            hm.build_manifest(self.repo, hm.resolve_commit(self.repo, 'HEAD'))

    def test_output_symlink_and_parent_alias_containment(self):
        # Mocking is portable to Windows hosts without symlink privileges.
        with mock.patch('hash_manifest.Path.is_symlink', return_value=True):
            with self.assertRaises(hm.ManifestError):
                hm.safe_output(self.repo, self.output)
        with mock.patch('hash_manifest.Path.resolve',
                        return_value=self.repo / 'assets' / 'alias.json'):
            with self.assertRaises(hm.ManifestError):
                hm.safe_output(self.repo, self.output)

    def test_batch_process_failure_and_extra_output(self):
        oid = '1' * 40
        for trailing, exit_code in [(b'', 1), (b'extra', 0)]:
            process = mock.Mock()
            process.stdin = io.BytesIO()
            process.stdout = io.BytesIO((oid + ' blob 0\n\n').encode() + trailing)
            process.wait.return_value = exit_code
            process.poll.return_value = exit_code
            with mock.patch('hash_manifest.subprocess.Popen', return_value=process):
                with self.assertRaises(hm.ManifestError):
                    hm.hash_blobs(self.repo, [hm.Blob('empty.json', oid)])

    def test_git_failures_are_explicit(self):
        with mock.patch('hash_manifest.subprocess.run', side_effect=OSError('missing')):
            self.assertEqual(hm.main(['generate', '--repo', str(self.repo)]), 2)
        with mock.patch('hash_manifest.subprocess.Popen', side_effect=OSError('missing')):
            with self.assertRaises(hm.ManifestError):
                hm.build_manifest(self.repo, self.commit)
        with self.assertRaises(hm.ManifestError):
            hm.resolve_commit(self.repo, '--help')


if __name__ == '__main__':
    unittest.main()
