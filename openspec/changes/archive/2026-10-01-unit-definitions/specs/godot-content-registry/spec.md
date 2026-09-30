# Spec Delta

## MODIFIED Requirements

### Requirement: Domain indexing and lookup
The registry SHALL index each domain's entries by `legacy_id`, SHALL reject a duplicate `legacy_id` within a domain at load time with an error naming that domain, and SHALL expose lookups — the domain list, existence check, entry retrieval, entry count, domain id enumeration, and the package content fingerprint — that return an explicit not-found result for an unknown domain or reference rather than a null or guessed value. Domain id enumeration SHALL report the committed index order rather than a collation of the identifier strings, because the identifiers are digit strings and a lexicographic sort would interleave them.

#### Scenario: Look up known definitions
- **WHEN** lookups ask for known `legacy_id` values in several domains (a building, a quest, a sound)
- **THEN** each returns the exact stored entry and the reported count for its domain matches the manifest-verified entry total

#### Scenario: Report unknown references explicitly
- **WHEN** a lookup names an unknown domain or an unknown `legacy_id`
- **THEN** the result explicitly reports not-found, and the registry state is unchanged

#### Scenario: Reject duplicate identifiers
- **WHEN** an altered copy of a domain contains a repeated `legacy_id`
- **THEN** the load fails with an error naming that domain and no partial index is exposed

#### Scenario: Enumerate a domain's identifiers
- **WHEN** a caller asks a loaded registry for the legacy ids of a domain it did not
  hard-code
- **THEN** the registry returns those ids in the committed order they were indexed in,
  their count equals the domain's reported entry count, and the result comes from the
  index built during the manifest-verified load, so a consumer enumerates verified content
  instead of re-reading the committed file behind the registry's back

#### Scenario: Report an unknown domain when enumerating
- **WHEN** an enumeration names a domain that is not loaded
- **THEN** the result explicitly reports not-found with an empty list and a message naming
  the domain, never a guessed empty enumeration presented as a loaded one
