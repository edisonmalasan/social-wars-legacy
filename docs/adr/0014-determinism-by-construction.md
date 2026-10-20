# 14. The determinism is provable by construction

**Status:** accepted

## Context

The claim is "the same seed and inputs produce the same outcome **on any
machine**". That is stronger than "it was tested on two machines", and
it is a claim that can rot silently.

## Decision

Three things, and each is enforced:

- the generator's every operation is a **32-bit integer** operation, and
  those are defined exactly by the language;
- the arithmetic is **IEEE 754 double**, which the specification requires
  every engine to give identically for the identical expression, and
  the order of the operations is fixed by the code;
- the rules engine is **scanned** for the sources of nondeterminism that
  would break the claim: an unseeded generator, the wall clock, the
  locale, the environment, a platform API or the filesystem.

The generator's **reference vectors are pinned**, so a change to it
cannot pass unnoticed.

## Alternatives

- **Test on two machines.** It catches the common failures and misses
  the rest.
- **Rely on the scan alone.** The vectors are what make a change to the
  generator loud rather than quiet.

## Consequences

The scan found two real defects when it was written: the darts schedule
was worked in the server's **local** time, and the shared core imported
`node:assert`. Both are fixed. The cost is the scan, which has to be
maintained as the engine grows.
