# Research OS Engineering Architecture Principles

Research OS is a professional research system. Its engineering architecture must be held to the same standard as its research methodology: explicit assumptions, stable boundaries, reproducible behavior, and evidence-backed change.

These principles are repository-level rules. Feature design, refactoring, tests, release work, and plugins should conform to them unless an ADR explicitly records a justified exception.

## 1. Architecture Style

Research OS is a **modular monolith with explicit bounded contexts**, not a collection of scripts and not a premature microservice system.

The codebase combines four mature architecture ideas pragmatically:

- **Clean Architecture dependency rule**: policy and domain semantics do not depend on presentation, release, or infrastructure details.
- **Domain-Driven Design bounded contexts**: evidence, routing/KPI, thesis, expectations, valuation, decision, reporting/presentation, plugins, and release governance have explicit responsibilities.
- **Hexagonal ports and adapters**: external mechanisms such as storage, web/API, PDF/browser backends, and future data providers sit behind contracts rather than leaking into domain policy.
- **Open/Closed composition**: new industries, methodologies, release verification capabilities, and adapters extend registries/manifests; stable orchestration code should not require patch-version branches.

Use patterns only when they clarify ownership or dependency direction. Do not add factories, abstract classes, event buses, repositories, or plugins merely because the pattern exists.

## 2. Dependency Rule

The core dependency direction is inward toward research semantics.

Conceptually:

```text
Evidence / Domain Contracts
        ↓
Research Semantics and Application Modules
        ↓
Canonical ResearchRunResult
        ↓
Human-Readable Research View
        ↓
Research Report Document
        ↓
Markdown
        ↓
HTML
        ↓
PDF
```

Cross-cutting infrastructure such as release verification observes public contracts but must not feed semantic decisions back into the research pipeline.

Forbidden directions include:

- domain/research semantics importing reporting, presentation, or release governance;
- reporting or presentation recomputing research state;
- release/CI code changing research conclusions;
- historical replay importing an unpinned current implementation when its historical contract requires frozen behavior.

## 3. Single Source of Truth

Each material fact or policy has one authority.

Examples:

- product/Core version identity: the import-free `research_os.version` leaf;
- release descriptor and policy composition: `research_os.release.manifest.CURRENT_RELEASE`;
- research conclusion: canonical runtime artifacts / `ResearchRunResult`;
- presentation semantics: versioned presenter/renderer projections, never a second decision engine;
- release checks: verification registry + enabled manifest packs;
- historical replay selection: replay registry + manifest profiles.

Generated files and projections may duplicate representation, but never ownership. Generated representations require consistency tests against their authority.

## 4. Stable Contracts and Explicit Boundaries

Boundary types should be typed, immutable where practical, and semantically named.

Prefer:

- value objects/enums over magic strings;
- immutable dataclasses/Pydantic models for manifests and externalized results;
- explicit provenance, comparison basis, units, periods, and missingness;
- deterministic registries and ordered composition;
- additive schema evolution where backward compatibility matters.

Avoid passing unstructured dictionaries across long-lived boundaries when a stable domain type exists or is warranted.

## 5. Composition Root

Object selection and version/configuration composition belong at a small number of composition roots.

A domain module should not inspect the Research OS patch version and choose behavior internally. Version selection belongs in runtime/release composition or frozen compatibility adapters.

New patch releases must not create scattered logic such as:

```python
if RESEARCH_OS_VERSION >= "1.5.12":
    ...
```

inside research semantics. If behavior differs materially, define a stable strategy/adapter boundary and select the implementation at composition time.

## 6. Open/Closed Extension

Stable orchestration should be changed less often than capability definitions.

Examples:

- industry/methodology extensions register plugins;
- release verification registers checks and capability packs;
- field replay registers immutable profiles;
- presentation backends implement adapter contracts.

Adding a capability should normally add a new implementation/registration and tests, not copy an orchestration module with a new version suffix.

## 7. Backward Compatibility as an Anti-Corruption Boundary

Historical behavior is isolated, not allowed to contaminate active semantics.

Frozen historical presenters, runners, fixtures, or adapters are acceptable when they protect a published contract. They act as an **anti-corruption layer** between current semantics and historical replay.

Rules:

- historical artifacts never become the default implementation again;
- current code does not branch on company identity to satisfy historical fixtures;
- frozen replay is explicit and testable;
- a new release cannot silently mutate a prior release's acceptance semantics.

## 8. DRY Without False Abstraction

Duplicate **policy** and **orchestration** are architecture defects; duplicate tiny local expressions are not automatically defects.

Extract when two call sites share the same semantic responsibility and must evolve together. Do not create a generic framework merely to remove a few lines.

The repository specifically rejects:

- one `runtime_vX_Y_Z.py` per patch release;
- repeated release version constants across files;
- repeated CI blocks per historical version;
- copied tests that differ only by version string.

## 9. Error and Missingness Semantics

Fail closed when metadata required for a semantic conclusion is absent or incompatible.

Do not convert:

- unknown into mixed;
- incomparable into negative/positive;
- missing into zero;
- unavailable provenance into confidence;
- presentation absence into a research conclusion.

Errors crossing boundaries should retain enough context to identify the responsible module/check/profile without exposing implementation detail to user-facing research output.

## 10. Test Architecture

Tests are organized by responsibility, not by release ceremony.

- **Unit**: one domain/service behavior, fast and local.
- **Contract**: stable public boundary or adapter contract.
- **Integration**: collaboration across real modules/boundaries.
- **Regression**: one previously observed defect or invariant that must never regress.
- **Acceptance**: end-to-end investor-facing or field artifact validation, including Markdown/HTML/PDF when relevant.
- **Architecture**: dependency direction, source-of-truth, forbidden coupling, registry consistency, and release topology.
- **Historical replay**: frozen compatibility evidence for published releases.

Do not copy the same assertions into every layer. A lower-level invariant should be tested once at the narrowest useful layer; higher layers verify integration outcomes.

Fixtures follow three classes:

1. generic synthetic fixtures for reusable semantic correctness;
2. focused builders/factories for unit and integration tests;
3. frozen real-field fixtures only for historical/acceptance evidence.

Production code must never depend on acceptance fixture identity.

## 11. Change Discipline

Meaningful changes follow:

1. define/confirm the contract;
2. add a failing test for behavior or architecture invariant;
3. implement the smallest coherent change;
4. run focused tests;
5. run affected integration/regression suites;
6. run release verification before claiming completion.

Architecture changes require a short design and an ADR when they establish a durable repository-wide decision.

## 12. Release Discipline

Research OS follows semantic versioning at the product level and independent versions for material components.

A patch release should normally require changes only to:

- the capability implementation and tests;
- release manifest version/component fingerprints and enabled capability packs;
- generated release metadata;
- changelog/migration documentation.

It should not require edits to stable release orchestration, old release gates, old field runners, or CI topology.

`main` preserves one release commit per Research OS small version so release history is auditable at product granularity.
