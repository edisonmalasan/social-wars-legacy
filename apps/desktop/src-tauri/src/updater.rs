//! Update and rollback **decisions**, with no release infrastructure.
//!
//! This module is deliberately pure. It parses a small, synthetic update
//! manifest, compares versions, chooses a candidate, asks an injected
//! verifier to check its signature, and plans a rollback to the last
//! version that was confirmed good. It does **not** fetch a URL, install
//! an artefact, or roll anything back.
//!
//! ## What remains blocked
//!
//! A real auto-update needs things this repository does not have:
//!
//! - a **release stream** with minisign signatures and a public key
//!   (`plugins.updater.pubkey` and `TAURI_SIGNING_PRIVATE_KEY`);
//! - an **HTTPS endpoint** serving the manifest and its artefacts, with
//!   `bundle.createUpdaterArtifacts` enabled;
//! - an **installation path** through Tauri's updater plugin, and a
//!   confirmation that the new build started successfully;
//! - an **automatic rollback** — the plugin does not provide one, so the
//!   plan produced here would have to be carried out by a later layer.
//!
//! None of that is configured here, and nothing in this module claims it
//! is. [`ReleaseVerifier`] is a seam so the decision logic can be tested
//! with a deterministic fake until a real signature check exists. The
//! client has no update UI yet, so there is no `#[tauri::command]` for
//! this logic: it is library-only for now.

use std::fmt;

use serde::Deserialize;

/// A `major.minor.patch` version.
///
/// Compared as numbers, not as strings: `0.10.0` is newer than `0.9.0`.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct Version {
    pub major: u32,
    pub minor: u32,
    pub patch: u32,
}

impl Version {
    /// Parse exactly three decimal numbers.
    pub fn parse(text: &str) -> Result<Self, String> {
        let parts: Vec<&str> = text.split('.').collect();
        if parts.len() != 3 {
            return Err(format!("\"{text}\" is not a major.minor.patch version"));
        }
        let mut numbers = [0_u32; 3];
        for (index, part) in parts.iter().enumerate() {
            if part.is_empty() || !part.bytes().all(|byte| byte.is_ascii_digit()) {
                return Err(format!("\"{text}\" has a non-numeric component"));
            }
            numbers[index] = part
                .parse::<u32>()
                .map_err(|_| format!("\"{text}\" has a component that is too large"))?;
        }
        Ok(Self {
            major: numbers[0],
            minor: numbers[1],
            patch: numbers[2],
        })
    }
}

impl fmt::Display for Version {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}.{}.{}", self.major, self.minor, self.patch)
    }
}

/// One release in the manifest. The URL is data: nothing here fetches it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Release {
    pub version: Version,
    pub url: String,
    pub signature: String,
}

/// The manifest's on-disk shape, before versions are parsed.
#[derive(Debug, Deserialize)]
struct ReleaseWire {
    version: String,
    url: String,
    signature: String,
}

#[derive(Debug, Deserialize)]
struct ManifestWire {
    releases: Vec<ReleaseWire>,
}

/// An update manifest, parsed from a local string.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Manifest {
    pub releases: Vec<Release>,
}

/// Parse a manifest. No network, no signature check: just readable data.
pub fn parse_manifest(json: &str) -> Result<Manifest, String> {
    let wire: ManifestWire = serde_json::from_str(json)
        .map_err(|error| format!("the update manifest is not readable: {error}"))?;
    let mut releases = Vec::with_capacity(wire.releases.len());
    for release in wire.releases {
        releases.push(Release {
            version: Version::parse(&release.version)
                .map_err(|error| format!("a release has a bad version: {error}"))?,
            url: release.url,
            signature: release.signature,
        });
    }
    Ok(Manifest { releases })
}

/// The seam for signature verification.
///
/// A real implementation would check a minisign signature against the
/// release public key. There is no key in this repository, so the tests
/// inject a deterministic fake and the shell wires nothing to this yet.
pub trait ReleaseVerifier {
    fn verify(&self, release: &Release) -> Result<(), String>;
}

/// What the decision says to do.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UpdateDecision {
    /// Nothing newer than the running version was offered.
    UpToDate,
    /// A verified release is ready; the caller would install it.
    Ready { release: Release },
}

/// Choose the newest release, but only offer it if it verifies.
///
/// An older release is never a downgrade, and an up-to-date app does not
/// even ask the verifier. A failed verification is an error, not a
/// silently skipped update.
pub fn decide(
    current: &Version,
    manifest: &Manifest,
    verifier: &dyn ReleaseVerifier,
) -> Result<UpdateDecision, String> {
    let candidate = manifest
        .releases
        .iter()
        .filter(|release| release.version > *current)
        .max_by(|left, right| left.version.cmp(&right.version));
    let Some(release) = candidate else {
        return Ok(UpdateDecision::UpToDate);
    };
    verifier.verify(release)?;
    Ok(UpdateDecision::Ready {
        release: release.clone(),
    })
}

/// The result of trying to install a release.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InstallOutcome {
    Succeeded,
    Failed { reason: String },
}

/// One recorded attempt. `from` and `to` are the versions either side.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InstallAttempt {
    pub from: Version,
    pub to: Version,
    pub outcome: InstallOutcome,
}

impl InstallAttempt {
    pub fn succeeded(from: Version, to: Version) -> Self {
        Self {
            from,
            to,
            outcome: InstallOutcome::Succeeded,
        }
    }

    pub fn failed(from: Version, to: Version, reason: impl Into<String>) -> Self {
        Self {
            from,
            to,
            outcome: InstallOutcome::Failed {
                reason: reason.into(),
            },
        }
    }
}

/// The versions the updater is deciding about.
///
/// `current` is what is running. `last_known_good` starts equal to it and
/// only moves when a caller confirms the running build started cleanly —
/// installing an update is not the same as proving it works.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UpdateState {
    pub current: Version,
    pub last_known_good: Version,
    pub attempts: Vec<InstallAttempt>,
}

impl UpdateState {
    pub fn new(version: Version) -> Self {
        Self {
            current: version.clone(),
            last_known_good: version,
            attempts: Vec::new(),
        }
    }

    /// Record an attempt. A success moves `current`; a failure does not.
    pub fn record(&mut self, attempt: InstallAttempt) {
        if matches!(attempt.outcome, InstallOutcome::Succeeded) {
            self.current = attempt.to.clone();
        }
        self.attempts.push(attempt);
    }

    /// The caller confirms that the current build started successfully.
    pub fn confirm_good(&mut self) {
        self.last_known_good = self.current.clone();
    }
}

/// A rollback to carry out, not one that has been carried out.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RollbackPlan {
    pub from: Version,
    pub to: Version,
}

/// Plan a rollback after a failed install of a version that was never
/// confirmed good. Nothing is installed or restarted here.
pub fn plan_rollback(state: &UpdateState) -> Option<RollbackPlan> {
    let last_failed = matches!(
        state.attempts.last(),
        Some(attempt) if matches!(&attempt.outcome, InstallOutcome::Failed { .. })
    );
    if last_failed && state.current != state.last_known_good {
        Some(RollbackPlan {
            from: state.current.clone(),
            to: state.last_known_good.clone(),
        })
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;

    fn v(text: &str) -> Version {
        Version::parse(text).unwrap()
    }

    /// A verifier whose answer is fixed, and which records what it saw.
    #[derive(Debug)]
    struct FakeVerifier {
        accept: bool,
        seen: RefCell<Vec<String>>,
    }

    impl FakeVerifier {
        fn accepting(accept: bool) -> Self {
            Self {
                accept,
                seen: RefCell::new(Vec::new()),
            }
        }
    }

    impl ReleaseVerifier for FakeVerifier {
        fn verify(&self, release: &Release) -> Result<(), String> {
            self.seen.borrow_mut().push(release.signature.clone());
            if self.accept {
                Ok(())
            } else {
                Err(format!(
                    "the signature for {} was not accepted",
                    release.version
                ))
            }
        }
    }

    const TWO_RELEASES: &str = r#"{
      "releases": [
        {"version":"0.1.0","url":"https://releases.example/0.1.0.exe","signature":"sig-1"},
        {"version":"0.2.0","url":"https://releases.example/0.2.0.exe","signature":"sig-2"}
      ]
    }"#;

    #[test]
    fn a_version_is_three_numbers() {
        let version = Version::parse("1.2.3").unwrap();
        assert_eq!((version.major, version.minor, version.patch), (1, 2, 3));
        assert_eq!(version.to_string(), "1.2.3");
    }

    #[test]
    fn a_version_needs_three_numbers() {
        for bad in ["", "1", "1.2", "1.2.3.4", "1.a.3", "-1.2.3"] {
            assert!(Version::parse(bad).is_err(), "{bad} should not parse");
        }
    }

    #[test]
    fn versions_order_numerically_not_lexically() {
        assert!(v("0.10.0") > v("0.9.0"));
        assert!(v("1.0.0") > v("0.99.99"));
        assert_eq!(v("0.2.0"), Version::parse("0.2.0").unwrap());
    }

    #[test]
    fn a_manifest_is_parsed_from_json() {
        let manifest = parse_manifest(TWO_RELEASES).unwrap();
        assert_eq!(manifest.releases.len(), 2);
        assert_eq!(manifest.releases[1].version, v("0.2.0"));
        assert_eq!(
            manifest.releases[1].url,
            "https://releases.example/0.2.0.exe"
        );
        assert_eq!(manifest.releases[1].signature, "sig-2");
    }

    #[test]
    fn a_broken_manifest_is_refused() {
        assert!(parse_manifest("not json").is_err());
        assert!(
            parse_manifest(r#"{"releases":[{"version":"x","url":"u","signature":"s"}]}"#).is_err()
        );
        assert!(parse_manifest(r#"{"releases":[]}"#).is_ok());
    }

    #[test]
    fn the_highest_newer_release_is_chosen() {
        let manifest = parse_manifest(TWO_RELEASES).unwrap();
        let verifier = FakeVerifier::accepting(true);
        let decision = decide(&v("0.1.0"), &manifest, &verifier).unwrap();
        assert_eq!(
            decision,
            UpdateDecision::Ready {
                release: manifest.releases[1].clone()
            }
        );
        // Only the chosen candidate is verified, not every release.
        assert_eq!(*verifier.seen.borrow(), vec!["sig-2".to_string()]);
    }

    #[test]
    fn an_up_to_date_app_does_not_verify_or_download() {
        let manifest = parse_manifest(TWO_RELEASES).unwrap();
        let verifier = FakeVerifier::accepting(true);
        let decision = decide(&v("0.2.0"), &manifest, &verifier).unwrap();
        assert_eq!(decision, UpdateDecision::UpToDate);
        assert!(verifier.seen.borrow().is_empty());
    }

    #[test]
    fn an_older_release_is_never_an_update() {
        let manifest = parse_manifest(TWO_RELEASES).unwrap();
        let verifier = FakeVerifier::accepting(true);
        let decision = decide(&v("9.0.0"), &manifest, &verifier).unwrap();
        assert_eq!(decision, UpdateDecision::UpToDate);
    }

    #[test]
    fn an_unverified_release_is_not_offered() {
        let manifest = parse_manifest(TWO_RELEASES).unwrap();
        let verifier = FakeVerifier::accepting(false);
        let error = decide(&v("0.1.0"), &manifest, &verifier).unwrap_err();
        assert!(error.contains("signature"), "error was {error}");
        assert_eq!(*verifier.seen.borrow(), vec!["sig-2".to_string()]);
    }

    #[test]
    fn a_successful_install_moves_current_but_not_last_known_good() {
        let mut state = UpdateState::new(v("0.1.0"));
        state.record(InstallAttempt::succeeded(v("0.1.0"), v("0.2.0")));
        assert_eq!(state.current, v("0.2.0"));
        assert_eq!(state.last_known_good, v("0.1.0"));
        assert_eq!(state.attempts.len(), 1);
    }

    #[test]
    fn a_failed_install_keeps_the_running_version() {
        let mut state = UpdateState::new(v("0.1.0"));
        state.record(InstallAttempt::succeeded(v("0.1.0"), v("0.2.0")));
        state.record(InstallAttempt::failed(v("0.2.0"), v("0.3.0"), "network"));
        assert_eq!(state.current, v("0.2.0"));
        assert_eq!(state.last_known_good, v("0.1.0"));
        assert_eq!(state.attempts.len(), 2);
        assert!(matches!(
            state.attempts[1].outcome,
            InstallOutcome::Failed { .. }
        ));
    }

    #[test]
    fn a_failed_install_plans_a_rollback_to_last_known_good() {
        let mut state = UpdateState::new(v("0.1.0"));
        state.record(InstallAttempt::succeeded(v("0.1.0"), v("0.2.0")));
        state.record(InstallAttempt::failed(v("0.2.0"), v("0.3.0"), "network"));
        assert_eq!(
            plan_rollback(&state),
            Some(RollbackPlan {
                from: v("0.2.0"),
                to: v("0.1.0"),
            })
        );
    }

    #[test]
    fn no_rollback_is_planned_without_a_failure() {
        let mut state = UpdateState::new(v("0.1.0"));
        state.record(InstallAttempt::succeeded(v("0.1.0"), v("0.2.0")));
        assert_eq!(plan_rollback(&state), None);
    }

    #[test]
    fn a_confirmed_version_becomes_the_rollback_target() {
        let mut state = UpdateState::new(v("0.1.0"));
        state.record(InstallAttempt::succeeded(v("0.1.0"), v("0.2.0")));
        state.confirm_good();
        state.record(InstallAttempt::failed(v("0.2.0"), v("0.3.0"), "network"));
        assert_eq!(state.last_known_good, v("0.2.0"));
        assert_eq!(plan_rollback(&state), None);
    }

    #[test]
    fn a_failure_to_the_same_version_needs_no_rollback() {
        let mut state = UpdateState::new(v("0.1.0"));
        state.record(InstallAttempt::failed(v("0.1.0"), v("0.1.0"), "network"));
        assert_eq!(plan_rollback(&state), None);
    }
}
