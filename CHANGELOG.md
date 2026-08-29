# Changelog

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
