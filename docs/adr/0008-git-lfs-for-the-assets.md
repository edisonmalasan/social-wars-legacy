# 8. Git LFS for the binary assets

**Status:** accepted

## Context

The vendored upstream carries 716.8 MB of binary assets, and the project
generates more: the atlas store alone is tens of gigabytes.

## Decision

The binary assets are kept in **Git LFS**, so the repository holds
pointers and `git lfs pull` restores the content.

## Alternatives

- **A release for the assets.** The tree would not be self-contained,
  and the "the vendored tree is unmodified" check would need the release
  as well as the repository.
- **No version control for the assets.** Then a change to an asset
  cannot be reviewed or reverted.

## Consequences

The repository stays small and the assets stay versioned. The cost is
that a clone needs LFS, and that the CI has to pull them.
