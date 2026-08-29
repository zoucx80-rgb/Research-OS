# Research Completion Safety Gates — Implementation Delta

**Date:** 2026-08-29  
**Release:** Research OS `1.2.0`  
**Parent design:** `docs/superpowers/specs/2026-08-29-research-completion-safety-gates-design.md`

This note records implementation discoveries that supersede assumptions in the original design while preserving its goals and invariants.

## 1. Evidence lineage requires persistent schema support

The original design initially treated `raw_value`, `normalized_value`, `period`, and `version` as compatible in-memory additions and stated that no schema migration was required.

A dedicated RED storage regression proved that assumption false: `EvidenceStore` persisted only the legacy `value` field, so the new lineage metadata was lost after a database round trip.

The implemented v1.2 design therefore adds reversible Alembic revision `0003_v1_2_evidence_lineage` with:

- `raw_value_json`
- `normalized_value_json`
- `period`
- `version`

`EvidenceRow.from_domain()` / `to_domain()` round-trip these fields. The migration is release-gated through `tests/integration/storage/test_v1_2_lineage_migration.py` and is explicitly executed by CI before the full test suite.

This delta supersedes any statement in the parent design that says no schema migration is required.

## 2. Completion-aware reporting is a hard validation boundary

`DecisionSummary` now carries:

- `decision_state`
- `final_status`
- `expectation_evidence_status`
- `valuation_execution_status`

A report labeled `COMPLETE` must contain a legal canonical `ResearchDecisionState`, validated expectation evidence, and validated valuation execution. `INCOMPLETE` reports may expose `INSUFFICIENT_EVIDENCE` without manufacturing a supported conclusion.

## 3. Release Gate and CI are part of the safety architecture

The v1.2 release gate adds `migration_lineage` alongside repository preflight, financial sanity, expectation evidence, valuation execution, decision validation, completion, temporal consistency, distributor KPI safety, and complete-run integration.

CI order is intentionally explicit:

1. install test dependencies;
2. run the reversible v1.2 lineage migration regression;
3. run full `pytest -q`;
4. run the Research OS Release Gate.

The compatibility script remains named `scripts/release_gate_v1_1.py`, but it reads `research_os.__version__` dynamically and reports the active `1.2.0` release.

## 4. Version/documentation surface

The following are synchronized to `1.2.0`:

- `pyproject.toml`
- `research_os_version.json`
- `src/research_os/__init__.py`
- `CHANGELOG.md`
- `README.md`
- `docs/prompts/stock_research.md`
- `docs/specs/Research_OS_v1.2_安全门禁增量规范.md`
- `docs/migrations/v1.1-to-v1.2.md`

Historical `v1.1.0` artifacts and Research Snapshots remain immutable.

## 5. Verification evidence at implementation closeout

Commit `2e05443ead04ca8ffc4832ec7c563665638c07a8` produced a GitHub Actions run in which:

- reversible v1.2 lineage migration test: PASS;
- full `pytest -q`: PASS;
- Release Gate: PASS;
- workflow job conclusion: SUCCESS.

A later documentation-only closeout commit must also pass its own fresh CI before `RESEARCH_OS_UPGRADE_STATUS = COMPLETE` is reported.
