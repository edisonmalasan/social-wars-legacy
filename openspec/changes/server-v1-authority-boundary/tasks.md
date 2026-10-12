# Tasks

Ordered by dependency. Each task states how completion is verified. Verification is not
collected into a final group: each group lands the tests and documentation its own work
calls for, so a failure surfaces in the group that caused it.

## 1. Runtime and scaffolding

- [x] 1.1 Add pinned `fastapi` and `pydantic` entries to `requirements.txt`, plus their
      transitives resolved against the pinned CPython 3.9.13, and verify
      `python -m pip install -r requirements.txt` succeeds and
      `python -m pip --isolated check` reports a consistent environment
- [x] 1.2 Create `apps/server-v1/` with its package structure and verify the expected
      modules import cleanly under the pinned interpreter
- [x] 1.3 Extend `docs/legacy-baseline.md` with the new pinned versions and their
      verification evidence, **adding to** the existing record and never editing the
      existing entries, and verify the new entries name the exact resolved versions
- [x] 1.4 Bind v1 to its own loopback port distinct from 5055 and 5056, and verify a
      plant registered on that port is visible to the same enumeration used to count it,
      so a port that cannot see its own rules fails rather than reporting zero

## 2. The authority boundary

- [x] 2.1 Define the typed refusal value the domain returns and verify it round-trips
      every refusal reason through its own test without loss
- [x] 2.2 Define the typed success value carrying server-derived resource deltas and
      verify a success cannot be constructed without a derivation, by test
- [x] 2.3 Implement the economy authority that derives resource movement from player
      intent and committed content, and verify its tests cover a derivation, a refusal,
      and a refusal that leaves every stored value byte-identical
- [x] 2.4 Implement the request-intent parsing layer that **rejects** any request
      carrying a resource, experience, health, damage, or result delta, and verify by
      test that such a request is refused with a structural input error and that no
      stored value moved
- [x] 2.5 Add the invariant test asserting the domain owns derivation in exactly one
      place, and verify it fails when a second derivation is introduced — inject one and
      observe the failure, then restore and observe it pass
- [x] 2.6 Decide the refusal vocabulary: a fresh set or a curated subset of the
      Compatibility API's 104 constants, recorded as a decision with its rationale, and
      verify every code v1 actually uses is declared and every declared code is used

## 3. Repository seam and save preservation

- [x] 3.1 Define the repository interface the domain depends on, with a filesystem
      implementation over the committed save document shape, and verify a round-trip
      through it reproduces the document
- [x] 3.2 Implement unknown-field preservation on every read and write, and verify by
      test that a field v1 does not model survives a write with its original value and
      that no other field was altered to accommodate it
- [x] 3.3 Verify the disposable-corpus containment helper leaves no working-tree `saves/`
      and releases the port, re-running the check so a single pass is not mistaken for a
      guarantee — note the recorded nuance that removing a corpus's files and removing its
      directories are different claims

## 4. The `collect` vertical slice

- [x] 4.1 Derive the collection payout from committed content and recorded state,
      reproducing the committed rung ladder as the derivation input, and verify by test
      that each stored resource changes by exactly the derived amount
- [x] 4.2 Implement the documented collection refusals — below the first committed rung,
      unaddressable row, no committed income, and construction in progress — and verify
      each refuses by name through the typed channel with the store byte-identical
- [x] 4.3 Implement the two-part post-execution proof: the collection instant moved
      forward **and** every stored resource changed by exactly the derived delta, and
      verify the proof fails when either half is violated — break each half in turn and
      observe the failure
- [x] 4.4 Compare v1's collection against the Compatibility API's committed
      executed-legacy fixture, and verify the comparison runs against the captured bytes
      rather than re-capturing from the legacy server
- [x] 4.5 Record in `docs/` which collection rules are **established** from committed
      legacy source and executed-legacy evidence and which are **derived** by this design
      and never observed, naming the rejected alternative for each derived rule

## 5. Client registration

- [x] 5.1 Implement `ServerV1Api` as a third `GameApi` implementation behind the existing
      facade, and verify no file outside `scripts/gameapi/` and its own new file changed
- [x] 5.2 Verify the fake and v0 implementations behave exactly as before, by running the
      existing GameApi and compatibility-boot suites unchanged
- [x] 5.3 Add a live phase proving the v1 implementation is selectable through the facade
      and reaches the v1 surface, asserting the port is released and no working-tree
      `saves/` remains afterwards

## 6. Integration verification

- [x] 6.1 Run the Compatibility API suite unchanged and verify it passes with no v0 route,
      envelope module, or fixture edited — established by `git diff --name-only`
- [x] 6.2 Run both Godot verification batteries and verify each exits 0 in the final
      state; where a battery fails on one of the four already-recorded flaky surfaces,
      re-run before recording it as a regression rather than reporting the first result
- [x] 6.3 Run `openspec validate --all --strict` and `tools/hash-manifest/hash_manifest.py
      verify`, verifying the manifest is unmoved at 3,258 entries and 758,423,699 bytes
      at commit `e8c98a03`
- [x] 6.4 Document the verified commands in `AGENTS.md` and `apps/server-v1/README.md`
      with their purposes, the loopback ports, the evidence paths, the
      established-versus-derived provenance of every v1 rule, and the claim limits —
      verifying each documented command runs exactly as written
- [x] 6.5 Update the roadmap `Project Status` with this line's delivered evidence and its
      remaining gaps, and record explicitly that the 39 uncited branches are **not**
      covered by it
