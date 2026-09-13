# Legacy Runtime Reproducibility Specification

## Purpose

Defines the evidence and dependency contract required to reproduce the preserved legacy Python server from an isolated source environment without executing Flash.

## Requirements

### Requirement: Complete pinned source-runtime manifest
The repository SHALL provide a `requirements.txt` that names every third-party distribution required to start the legacy source server and pins every direct and transitive runtime distribution to one exact version. The manifest SHALL remain installable with `python -m pip install -r requirements.txt` and SHALL NOT include build-only tooling solely because historical packaging scripts reference it.

#### Scenario: Install the declared runtime graph
- **WHEN** an operator installs `requirements.txt` into a new isolated environment using the verified interpreter
- **THEN** the installer resolves no unpinned runtime distribution and the server's unconditional third-party imports are present

#### Scenario: Keep historical packaging outside the runtime lock
- **WHEN** a dependency is used only to build the historical packaged executable
- **THEN** it is recorded as an unverified build dependency rather than added to the source-runtime manifest

### Requirement: Explicit verified Python target
The preservation documentation SHALL identify the exact Python implementation, patch version, operating system, and architecture used for successful verification. The verified target SHALL use the Python 3.9 family indicated by the preserved bundle provenance, while clearly distinguishing that verification result from a broader supported-version claim.

#### Scenario: Report the verified environment
- **WHEN** clean-environment verification succeeds
- **THEN** the documentation records the exact interpreter and host details and does not claim that untested Python versions or platforms are supported

### Requirement: Repeatable clean-environment installation
The dependency lock SHALL be installed successfully in at least two newly created isolated environments from the same clean source revision. Each environment SHALL pass package consistency checking, and their installed locked runtime distributions SHALL match exactly.

#### Scenario: Repeat installation from the lock
- **WHEN** the lock is installed independently into two empty environments
- **THEN** both installations succeed, package consistency checks pass, and the recorded runtime distribution/version inventories are identical

#### Scenario: Installation cannot be reproduced
- **WHEN** no compatible fully pinned dependency set can be installed for the verified Python target without changing legacy application behavior
- **THEN** the change is reported as blocked and clean-environment reproducibility is not claimed

### Requirement: Source startup smoke evidence
The locked environment SHALL pass the repository's syntax compilation command and start `server.py` from the expected repository-root working directory. Verification SHALL confirm that the loopback root URL on port 5055 returns an HTTP response while containing writable runtime side effects in a disposable verification location.

#### Scenario: Verify source startup without Flash
- **WHEN** the server is launched with the locked environment from a disposable copy of the preserved source tree
- **THEN** syntax compilation succeeds, the process listens on `127.0.0.1:5055`, and an HTTP request to `/` receives a successful response

#### Scenario: Preserve the Flash-free verification boundary
- **WHEN** the startup smoke test is executed
- **THEN** no SWF, Flash Player, Ruffle, or Flash-capable browser is executed and no generated save or cache file is added to the repository worktree

### Requirement: Evidence-backed reproducibility documentation
The repository SHALL document the exact commands actually executed, the locked distribution versions, verification results, remaining limitations, and the distinction between syntax checks, package checks, and runtime smoke checks. Setup guidance SHALL only advertise commands that were successfully executed.

#### Scenario: Review verification evidence
- **WHEN** a maintainer reviews the completed change
- **THEN** the preservation documentation identifies what was verified, what remains unverified, and the evidence supporting each claim
