## 1. Establish the legacy baseline reference

- [x] 1.1 Confirm `legacy-baseline` is absent and `HEAD` resolves to the planned untouched legacy revision `e8c98a0`; verify with `git show-ref --verify --quiet refs/tags/legacy-baseline` and `git rev-parse HEAD` before mutation.
- [x] 1.2 Create the roadmap-defined lightweight tag with `git tag legacy-baseline e8c98a0` and verify `git rev-parse refs/tags/legacy-baseline^{commit}` returns `e8c98a0`.
- [x] 1.3 Verify the reference is lightweight with `git cat-file -t refs/tags/legacy-baseline` returning `commit`, and confirm the tag operation introduced no tracked-file changes beyond the already reviewed planning/status edits.
