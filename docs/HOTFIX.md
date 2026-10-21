# Pushing a hotfix to the rules engine

The rules engine is the **game**. A bug in it is a bug in the game, and
a fix to it is a change every player sees at once. So the procedure is
deliberately slow.

## What a hotfix is

A change to `packages/rules` that:

- fixes a rule the original had wrong, or
- fixes a rule **this** project got wrong.

It is **not** a change to the content, the assets or the interface. Those
have their own pipelines and their own procedures.

## The properties that make it possible

The engine is **pure**: no clock, no randomness, no I/O. A rule takes
its inputs and a seed and returns an answer. So:

- a hotfix cannot have a side effect, because there is nowhere for a
  side effect to go;
- a hotfix cannot depend on when it runs, because the time is an
  argument;
- a hotfix can be **replayed**: the same seed and the same inputs give
  the same answer, so a change to a rule changes the answers it touches
  and **only** those.

That last property is what makes a hotfix safe, and it is checked: the
**golden master** compares the engine's answers with the original's,
and the **reference vectors** are pinned.

## The procedure

1. **Reproduce it.** A test that fails on the current engine and passes
   with the fix. The test names the rule and the case.
2. **Work on a branch.** `fix/<what-it-is>`.
3. **Make the change.** In `packages/rules`, as a pure function. The
   arguments the rule needs come in; the clock and the randomness are
   not read.
4. **Pin the answer.** The failing test becomes a passing test with the
   answer written down.
5. **Check the golden master.** If the master now **differs**, the change
   altered the game's behaviour — which is what a hotfix does — and the
   difference has to be **explained and accepted**, not waved through.
6. **Check the cheat battery.** A change to the authority layer is the
   dangerous kind: it can weaken it. `node scripts/run-cheat-battery.mjs`.
7. **Check the coverage.** `node scripts/check-coverage.mjs` — a hotfix
   that adds a branch without a test lowers the coverage.
8. **Check the determinism.** `packages/rules/src/portability.test.ts`
   scans for the sources of nondeterminism. A hotfix that reads the
   clock would pass every other check and break the whole guarantee.
9. **Record it.** A decision record in `docs/adr/`, because a change to
   the rules is a change to the game and the reasoning belongs with it.
10. **Merge, and deploy.** The deploy runs the golden master, the cheat
    battery and the coverage — so a hotfix that skips one of them does
    not reach a server.

## Rolling it back

The rules are **code**, so a rollback is a redeploy of the previous
commit. Nothing in the players' saves depends on the rules' version:
a save is the **world**, not a recording of how the world was computed.

That is why the engine is pure, and why it is worth the trouble: the
answer to "can we undo this?" is always "yes, redeploy the old
commit", and it does not need a migration.

## What must never be hotfixed

- The **content**. It is versioned and hashed, and a change to it is a
  change to the bundle. See the deploy script.
- The **protocol**. The command table is the authority for the client,
  the server and the shim, and changing it changes what the original
  client sends. It is a release, not a hotfix.
- Anything that **weakens the authority layer**. The cheat battery is
  the check, and it is mutation-tested: eighteen weakenings of the
  authority layer were each caught by exactly the attack they weaken.
  A hotfix that is caught by the battery is not a hotfix.
