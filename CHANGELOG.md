# Changelog

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
