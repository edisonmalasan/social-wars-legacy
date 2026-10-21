import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, utimes, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

import { checkBackups, snapshots } from './backups.ts';

describe('the backup check', () => {
  it('fails when there are no backups at all', async () => {
    const dir = await mkdtemp(path.join(os.tmpdir(), 'swl-bk-'));
    try {
      const result = await checkBackups(dir);
      assert.ok(result.problem);
      assert.match(result.problem, /no backups/);
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });

  it('fails when the directory is not there', async () => {
    const result = await checkBackups(path.join(os.tmpdir(), 'no-such-backups'));
    assert.ok(result.problem);
  });

  it('passes when the newest backup is recent', async () => {
    const dir = await mkdtemp(path.join(os.tmpdir(), 'swl-bk-'));
    try {
      await mkdir(path.join(dir, 'backup-1'));
      const result = await checkBackups(dir, 26);
      assert.equal(result.problem, null);
      assert.ok(result.newest);
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });

  it('fails when the newest backup is too old', async () => {
    const dir = await mkdtemp(path.join(os.tmpdir(), 'swl-bk-'));
    try {
      const old = path.join(dir, 'backup-old');
      await mkdir(old);
      // Two days ago.
      const twoDaysAgo = new Date(Date.now() - 48 * 60 * 60 * 1000);
      await utimes(old, twoDaysAgo, twoDaysAgo);

      const result = await checkBackups(dir, 26);
      assert.ok(result.problem);
      assert.match(result.problem, /hours old/);
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });

  it('looks at the newest, not the oldest', async () => {
    const dir = await mkdtemp(path.join(os.tmpdir(), 'swl-bk-'));
    try {
      const old = path.join(dir, 'backup-old');
      const fresh = path.join(dir, 'backup-new');
      await mkdir(old);
      await mkdir(fresh);
      const twoDaysAgo = new Date(Date.now() - 48 * 60 * 60 * 1000);
      await utimes(old, twoDaysAgo, twoDaysAgo);

      const result = await checkBackups(dir, 26);
      assert.equal(result.problem, null);
      assert.equal(result.newest!.name, 'backup-new');
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });

  it('ignores the things that are not snapshots', async () => {
    const dir = await mkdtemp(path.join(os.tmpdir(), 'swl-bk-'));
    try {
      await mkdir(path.join(dir, 'something-else'));
      const found = await snapshots(dir);
      assert.equal(found.length, 0);
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });
});
