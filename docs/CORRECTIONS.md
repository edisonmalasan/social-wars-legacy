# Corrections

**If you own the rights to anything in this project and you would like it
changed, removed or credited differently, this is where that is said, and
this is where it is answered.**

## The short version

1. **Open a draft issue** in this repository, titled *Rights request*, and
   say what you would like changed.
2. Say **what you own** and **what you would like done** — a change, a
   removal, or different credit. A link to the work is enough; a formal
   notice is not required.
3. You will get an **answer**. A request is not a matter for the
   project's convenience, and it is not a matter for a maintainer's
   schedule either.
4. What was done is **recorded** in the log below, with the date and what
   changed.

A **draft** issue is used so that a request need not be public while it
is being discussed. A draft is visible to the maintainer and is not
listed publicly, and it can be made public later if both sides want it
to be.

## What can be asked for

- **A removal.** An asset, a sound, a font, a piece of text or a whole
  file can be taken out of the project.
- **A change.** A name, a credit, a description or a piece of
  documentation can be corrected.
- **Different credit.** The way the work is attributed can be changed,
  and the attribution file can be changed with it.
- **A licence.** A piece of work can be relicensed, with the rights
  holder's agreement, and the licence report is regenerated afterwards.

## What is answered, and when

| The request | What happens |
| --- | --- |
| A removal | The work is removed, the licence report and the checks are re-run, and the log records the removal. |
| A change | The change is made, the checks are re-run, and the log records it. |
| Different credit | The attribution and the licence report are changed, and the log records it. |
| A relicensing | The work is relicensed with the rights holder's agreement, and the log records it. |
| A request that cannot be honoured | The request is **answered anyway**, with the reason, and the log records the answer. |

A request that is **not** honoured is still answered. A rights holder who
is told nothing has been told that they may be ignored, and that is the
worst possible answer.

## The log

Every request and every answer is recorded below, with the date. The log
is append-only: a request is never removed from it, because the record
that a request was answered is part of the answer.

## The log

Every request and every answer is recorded here, with the date. The log
is append-only: a request is never removed from it, because the record
that a request was answered is part of the answer.

| The date | The request | What was done |
| --- | --- | --- |
| 2026-10-21 | The policy was adopted. **No rights request had been received.** | The policy, the notice and this log were added, and `node scripts/check-corrections.mjs` was added to the CI. |

The log is checked by `node scripts/check-corrections.mjs`, which fails
if the policy and the notices disagree about where to write, or if the
log's shape is broken.

## Why this exists

This project preserves a game that other people made. Preserving
somebody's work accurately is a debt to them, and the people who made it
deserve to be able to say when the record is wrong. The analysis is
published in the hope that it is useful, and the rule is simple: the
people who own the rights get to say what happens to the material that
carries their rights.

## Where the rights position itself is

`docs/LICENSING.md` sets out the licensing position in detail, and
`docs/LICENCES.md` is the generated enumeration of every dependency's
licence. `docs/ATTRIBUTION.md` carries the notices.
