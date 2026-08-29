# Changelog

## 1.4.0 — 2026-08-30

### Added
A canonical run-scoped `ResearchRuntime` / `ResearchRuntimeFactory` execution boundary; immutable `ResearchInputs`; one public `ResearchRunResult`; versioned industry and methodology plugin manifests; compatibility-aware `PluginRegistry`; deterministic `StrategyResolver`; `PluginProvider` extension point; explicit `CoverageGap` and extension-request contracts; PIT-safe knowledge-provider interface; component fingerprints in frozen snapshots; and architecture regression coverage for third-party synthetic plugin extensibility.

### Changed
Research composition policy now lives in `ResearchRuntime`, while `ResearchEngine` only executes capability dependencies and has no company, industry, or plugin identifiers. Plugin registries and module instances are rebuilt per run. Stable plugins are eligible for automatic resolution and experimental plugins require explicit opt-in. Reporting now accepts canonical `ResearchRunResult` only and obtains completion fields from the runtime's `ResearchCompletionResult`. Decision records retain optional decision-context fields so reporting remains self-contained without a parallel input dictionary.

### Removed
The legacy `src/research_os/orchestration.py` policy entry point and the duplicate KPI registry/facade were removed. No replacement compatibility surface is allowed to redefine execution, KPI applicability, or completion policy.

### Validation
CI now runs architecture contracts before correctness regressions, storage migration smoke, the full test suite, and the release gate. The release gate adds 18 v1.4 architecture checks covering ResearchContext, ResearchInputs, module contracts, dependency resolution, plugin manifest/compatibility/resolution, coverage gaps, plugin failure isolation, canonical runtime/result, knowledge PIT, component fingerprints, completion single-source behavior, Core API consistency, extensibility without engine changes, and absence of duplicate legacy runtime policy.

### Migration
No new database or Alembic migration is required. Existing callers should migrate from the deleted legacy orchestrator to `ResearchRuntimeFactory`, and reporting callers should pass `ResearchRunResult` rather than an arbitrary dictionary. Custom strategy extensions should use the `PluginProvider` / `PluginManifest` contracts. See `docs/migrations/v1.4.0.md` and `docs/architecture/plugin-authoring-v1.md`.

### Compatibility
`CORE_API_VERSION` remains `1.0`. v1.2.1 period, missing-value, KPI-applicability, funding-loop, completion, PIT, evidence-lineage, valuation-safety, and decision-safety semantics remain enforced. Existing historical release tags and versioned research snapshots remain immutable.

## 1.2.1 — 2026-08-29

### Fixed
Interim balance/flow KPIs now use explicit reporting-period semantics instead of silently assuming 365 days. Missing funding facts remain missing rather than being coerced to zero. A generic CorePack no longer counts as specialized KPI support for an unsupported routed business model. Reporting now propagates the authoritative `ResearchCompletionResult` instead of applying a second completion policy. Runtime and public version surfaces now share one `RESEARCH_OS_VERSION` source.

### Changed
Distributor and Manufacturing period-sensitive metrics share one period contract. Distributor inventory turnover exposes both period turns and annualized turns where the reporting period is known. Funding-loop classification can return `unknown`, which maps to `INSUFFICIENT_EVIDENCE`. KPI Pack completion requires specialized support for the routed primary model. Claim capabilities are normalized before completion-policy evaluation so expectation, valuation and decision claims are not conflated.

### Validation
Release Gate adds five v1.2.1 semantic checks: `period_semantics`, `missing_value_semantics`, `kpi_applicability`, `completion_consistency`, and `version_consistency`. CI runs an anonymous cross-cutting v1.2.1 regression before migration smoke, the full test suite and the release gate.

### Migration
No database or Alembic migration is required for v1.2.1. The reversible v1.2 Evidence-lineage migration remains the current schema baseline. Historical tags and versioned research snapshots remain immutable.

### Compatibility
This is a PATCH release. Existing v1.2 request shapes remain accepted, including `facts: dict`, optional `safety=None`, and free-text claimed conclusions. Missing or unsupported evidence may now correctly produce `INSUFFICIENT_EVIDENCE` where older behavior could produce a false PASS.

## 1.2.0 — 2026-08-29

### Added
Repository identity preflight contracts; persistent raw/normalized Evidence lineage; calculation and assumption lineage contracts; financial sanity validation; expectation-evidence validation; valuation execution/driver-bridge validation; explicit decision-state validation; research completion and temporal-consistency gates; distributor safety KPIs; completion-aware reporting; and reversible Evidence-lineage schema migration `0003_v1_2_evidence_lineage`.

### Changed
`ResearchOS.complete_run()` now composes safety gates in causal order so hard prerequisite failures cannot silently flow into valuation, decision, or a completed report. `DecisionSummary` carries machine-readable `final_status`, decision state, expectation-evidence status, and valuation-execution status. Research OS public version metadata is now `1.2.0`.

### Fixed
Prevents placeholder repository fingerprints, financial unit/scale corruption, unsupported expectation-gap claims, selected/executed valuation model mismatch, illegal decision states such as `NEUTRAL`, stale next-verification events, tool-completion being mistaken for research-completion, and loss of raw/normalized Evidence lineage during database round trips.

### Validation
Release Gate now includes repository preflight, evidence lineage, financial sanity, expectation evidence, valuation execution, decision validation, completion, temporal consistency, distributor KPI safety, complete-run integration, and reversible v1.2 lineage migration checks in addition to existing PIT/golden/regression coverage.

### Migration
See `docs/migrations/v1.1-to-v1.2.md`. Historical snapshots and the `v1.1.0` tag remain immutable.

### Compatibility
The release is additive. Existing v1.1 research-domain APIs remain available; callers that do not provide the new safety context are not silently promoted to `FINAL_STATUS=COMPLETE`. Missing evidence remains `INSUFFICIENT_EVIDENCE` rather than being fabricated for narrative completeness.

## 1.1.0 — 2026-08-29

### Added
Business Model Router, KPI Pack Registry, Distributor Pack, Capital Efficiency/Funding Loop, Driver Graph, Thesis/Falsifier Engine, Evidence Ledger, PIT Consensus Vintage, Expectation Surprise, Forecast Model Promotion, Valuation Fitness Router, Decision Engine, Event Engine, Peer Normalization, Research Post-Mortem, Drift Detection, Calibration, Decision Summary, read-only API.

### Changed
Manufacturing-specific research logic is now a versioned Manufacturing Pack instead of a global default. Automated reporting is downstream of research semantics and evidence validation.

### Deprecated
Implicit assumption that every A-share company should run the manufacturing KPI set.

### Removed
No v1.0 historical facts or research snapshots are removed.

### Fixed
Explicitly separates information availability from economic period and prevents low-fitness valuation models from dominating the primary valuation set.

### Validation
PIT no-lookahead, immutable revisions, manufacturing golden regression, distributor complete run, thesis falsifier, valuation fitness, decision-no-trade and snapshot reproducibility gates.

### Migration
See `docs/migrations/v1.0-to-v1.1.md`.

### Known Limitations
The v1.1 router is deterministic and explainable rather than ML-based. Probability calibration is optional and only applies to explicit probability forecasts. Source ingestion connectors and licensed commercial datasets are deployment integrations, not bundled data feeds.
