# 18. The roadmap's item counts are checked

**Status:** accepted

## Context

The roadmap is a **list of items**, and an item that is silently
swallowed is worse than an item that is visibly unfinished. It happened:
a block-end rule that ended an item's block at the next blank line ate
fourteen items across two groups, because the items are packed with no
blank line between them. The road was only noticed because the counts
were compared.

## Decision

Each group has a **floor** — the number of items it had the last time
somebody looked — and a group with fewer items than its floor is a
**failure**. The floor is a file, so raising it is a deliberate act
rather than a side effect of an edit.

The check runs in the CI, in the release workflow, and as a test.

## Alternatives

- **A review checklist.** It depends on somebody remembering.
- **A diff of the roadmap in the pull request.** It shows the change but
  does not fail on it.

## Consequences

An item cannot go missing quietly. The cost is a floor to maintain, and
a check that has to be updated when a group is deliberately restructured.
