# ADR-0001: Manifest-Driven Release Governance

- **Status:** Accepted
- **Date:** 2026-08-31
- **Scope:** Release identity, verification composition, historical replay, CI orchestration

## Context

Research OS patch releases had accumulated version literals and release-specific orchestration across packaging metadata, release gates, CI, field acceptance, and historical tests. A new patch release therefore required editing unrelated old release code. Active semantic changes could also leak into historical replay when old runners imported current defaults.

The v1.5.11 work exposed both problems directly: historical v1.5.09/v1.5.10 replay was affected by current semantic defaults, and release checks/CI required patch-specific additions.

## Decision

Research OS uses four separated release-governance responsibilities.

### 1. Build-safe release identity leaf

`research_os.version` contains only the product version and Core API version as import-free constants. It is deliberately a leaf module because setuptools must be able to read the package version in an isolated build environment before the package is installed.

No domain, reporting, verification, plugin, or infrastructure import is allowed from this module.

### 2. Canonical release manifest

`research_os.release.manifest.CURRENT_RELEASE` consumes the build-safe identity leaf and defines the release descriptor:

- status;
- component fingerprints;
- enabled verification packs;
- selected field replay profiles.

Public machine-readable release metadata is generated from this descriptor. The JSON file is a projection, not another authority.

### 3. Verification and replay registries

Release verification is composed from stable check IDs grouped into reusable capability packs. The release gate derives its required checks from the manifest-selected packs; it does not maintain a second required-check list.

Historical field acceptance is represented by immutable replay profiles. Published historical profiles use pinned runners/fixtures and are not redirected to current default implementations.

### 4. Stable CI orchestration

GitHub Actions invokes one stable release-verification entry point. Patch releases extend manifests/registries rather than append version-specific YAML blocks or `runtime_vX_Y_Z.py` modules.

## Dependency Direction

```text
research_os.version                  (build-safe identity leaf)
        ↓
release.manifest                     (release descriptor)
        ↓
verification / replay registries     (composition definitions)
        ↓
release runtime / CI adapters        (execution)
```

Research semantics never depend on release verification or CI. Release governance may observe public component fingerprints but must never feed decisions back into the research pipeline.

## Consequences

### Positive

- Normal patch releases do not require CI topology changes.
- Release Gate has one required-check source.
- Historical replay is insulated from current semantic defaults.
- Packaging can resolve the version before package installation.
- Verification capabilities are reusable rather than copied per patch.
- Architecture invariants can be guarded by generic architecture tests.

### Costs

- Historical replay profiles remain explicit compatibility assets.
- A public JSON metadata file still exists as a generated projection and must be checked for staleness.
- The pre-v1.5.11 cumulative verification baseline remains a frozen compatibility dataset until a future deliberate migration; new checks must not be appended to it.

## Rejected Alternatives

### Patch-specific release runtime modules

Rejected because they copy orchestration and force every patch to create another runtime/gate path.

### CI auto-discovery from filenames

Rejected because implicit discovery hides release intent and makes auditability weaker. Manifest-selected registries keep extension explicit.

### Making the manifest itself the setuptools version attribute

Rejected after v1.5.11 build verification demonstrated that importing the release subsystem during isolated package metadata evaluation is unsafe. The import-free identity leaf preserves clean build-time dependency direction.

### Rewriting the repository into microservices or a framework-heavy architecture

Rejected as unnecessary. Research OS remains a modular monolith with explicit bounded contexts and stable ports/adapters.

## Enforcement

`tests/regression/architecture/test_release_governance.py` guards the release topology, source-of-truth relationships, replay freezing, stable CI entry point, and absence of patch-specific release runtimes. Release governance is itself a required verification pack for subsequent releases.
