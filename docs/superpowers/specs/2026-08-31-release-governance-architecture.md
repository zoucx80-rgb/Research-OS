# Research OS Release Governance Architecture

## Context

Research OS v1.5.11 exposed a release-governance design debt: release identity, component fingerprints, verification checks, historical field replay, and CI orchestration are coupled through repeated version literals and version-specific modules. A patch release therefore requires unrelated edits across `version.py`, `pyproject.toml`, `research_os_version.json`, `release/gate.py`, versioned release runtimes, release scripts, CI YAML, and historical tests.

This is not a semantic-research problem. It is an architecture problem in release metadata and verification composition.

## Goals

1. Make the current release identity have one canonical source in production code.
2. Separate release identity from verification implementation.
3. Model verification as reusable capability packs rather than per-release copies.
4. Freeze historical field acceptance as replay profiles so new semantics cannot silently mutate old contracts.
5. Give CI a stable release-verification entry point that does not require a new YAML block for every patch release.
6. Keep explicit version names only where they carry historical meaning: migration docs, frozen replay fixtures/adapters, and historical compatibility tests.
7. Preserve the one-way research pipeline and prohibit release/presentation code from recomputing research semantics.
8. Keep `main` history policy: one small Research OS release equals one release commit on `main`.

## Non-goals

- Do not remove historical version identities from frozen fixtures or migration documents.
- Do not rewrite old research algorithms into generic release infrastructure.
- Do not introduce a plugin framework for release checks; a small typed registry is sufficient.
- Do not change Core API 1.0 in v1.5.11.
- Do not add company/security-specific production logic.

## Architecture

### 1. Canonical Release Manifest

Create `research_os.release.manifest` with immutable `ReleaseManifest` and `CURRENT_RELEASE`.

`CURRENT_RELEASE` is the single manually maintained release identity and contains:

- `version`
- `core_api_version`
- `status`
- `module_versions`
- `verification_packs`
- `field_replay_profiles`

`research_os.version` derives `RESEARCH_OS_VERSION` and `CORE_API_VERSION` from this manifest.

`pyproject.toml` uses setuptools dynamic version resolution from `research_os.version.RESEARCH_OS_VERSION`; it no longer carries an independently edited project version literal.

`research_os_version.json` remains as a public machine-readable artifact, but it is generated from `CURRENT_RELEASE.to_public_metadata()` and is verified byte-for-data against that canonical representation. It is an output surface, not an authority.

### 2. Verification Registry and Packs

Create `research_os.release.verification`.

A verification check has a stable `check_id` and pytest `nodeid`. A `VerificationPack` is a named immutable tuple of check ids. Packs represent durable capabilities such as:

- `stable-baseline`: all checks frozen through v1.5.10
- `semantic-correctness`: v1.5.11 semantic-safety checks

`resolve_release_checks(CURRENT_RELEASE)` expands packs into one ordered check mapping and fails closed on unknown packs, duplicate check ids, or missing registry entries.

Future releases add a new capability pack and add that pack name to `CURRENT_RELEASE.verification_packs`. They do not create `runtime_vX_Y_Z.py`, do not append version-specific REQUIRED constants to `gate.py`, and do not edit historical pack definitions.

`research_os.release.runtime` remains the stable compatibility/runtime facade and delegates to the registry. Version-specific runtime modules are removed.

### 3. Release Gate

`release.gate` derives its required check ids from `resolve_release_checks(CURRENT_RELEASE)`.

There is one source of truth for which checks are required. `evaluate_release_gate()` only evaluates status; it does not maintain a second list.

`scripts/release_gate_v1_1.py` imports the stable runtime facade. It never imports a current-version module.

### 4. Historical Field Replay Registry

Create `research_os.release.replays` with immutable `FieldReplayProfile` descriptors.

A replay profile names:

- stable profile id
- runner script
- fixture directory
- output directory
- whether it is historical/frozen

Historical v1.5.08, v1.5.09, and v1.5.10 profiles are frozen. v1.5.11 is registered as the current field profile. Future releases may add a profile when presentation/field semantics materially change, but old profiles are never rewritten to point at current default implementations.

A generic orchestration function runs profiles in manifest order. Historical runner internals may remain versioned because their version identity is intentional compatibility state.

### 5. Stable CI Entry Point

Create `scripts/verify_release_pipeline.py` as the stable CI orchestration entry point. It:

1. validates generated release metadata;
2. runs current release verification checks;
3. runs all manifest-selected field replay profiles;
4. runs the full pytest suite;
5. runs the release gate.

The GitHub Actions workflow installs dependencies once, invokes this stable entry point, and uploads the release field-acceptance build tree as a single release-verification artifact set. It does not add a new command block for each patch version.

The script prints stage/profile names so CI remains diagnosable despite using a stable wrapper.

### 6. Test Architecture

Add generic governance tests that assert invariants, not a particular future patch number:

- package version derives from `CURRENT_RELEASE`;
- `pyproject.toml` uses dynamic versioning;
- generated JSON equals manifest metadata;
- release gate required checks equal resolved manifest checks;
- no `runtime_v<version>.py` release runtime modules exist;
- stable release script imports the generic runtime;
- CI uses the generic release pipeline and contains no version-specific field runner commands;
- replay profiles are unique and frozen historical profiles remain registered;
- every verification nodeid path exists;
- production source contains no acceptance-company identity branches.

Historical tests remain versioned only when testing a frozen historical contract.

## Dependency Direction

The release layer may inspect versions and invoke tests/replay scripts, but it must not affect research semantics:

`Research semantics -> Reporting -> Presentation`

is unchanged. Release governance depends on public component fingerprints; research/runtime modules never depend on release verification registries.

## Upgrade Workflow After This Change

For a normal v1.5.12 patch release:

1. implement the new research capability;
2. add its tests and, if needed, one new verification pack;
3. update `CURRENT_RELEASE` version/component fingerprints and enable the new pack;
4. generate `research_os_version.json`;
5. add changelog/migration documentation;
6. run the unchanged CI/release pipeline.

No edits are expected to `release/gate.py`, `scripts/release_gate_v1_1.py`, GitHub Actions orchestration, or frozen historical replay definitions.

## Acceptance Criteria

- v1.5.08-v1.5.10 historical gates and field replay remain green.
- v1.5.11 semantic correctness, Markdown/HTML/PDF field acceptance, full pytest, and release gate are green.
- `pyproject.toml` has no independently maintained `project.version` literal.
- no `release/runtime_v1_5_11.py` remains.
- `release/gate.py` does not enumerate v1.5.11 check ids.
- CI has one stable release-verification invocation rather than per-patch release blocks.
- exact final v1.5.11 tree is integrated into `main` as one commit whose sole parent is v1.5.10 main.
