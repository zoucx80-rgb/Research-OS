# Research OS v1.5.09 Professional Research Depth Hardening — Implementation Plan

**Goal:** Fix the professional-depth defects exposed by the v1.5.08 real-company PDFs without weakening PIT/evidence lineage or turning Reporting into a second research engine.

**Baseline:** `85c810603ccb90c8a2abd3f8fdf1eef09d009023` on `main` (v1.5.08 code plus approved v1.5.09 design).

**Spec:** `docs/superpowers/specs/2026-08-31-research-os-v1-5-09-professional-research-depth-hardening-design.md`

**Global constraints:** work directly on `main`; Core API stays `1.0` unless an incompatible public contract is unavoidable; all new serialized fields are additive/defaultable; no database migration expected; no company-specific production logic; TDD RED before production GREEN; preserve the v1.5.08 Markdown→HTML→Playwright PDF chain.

## Task 1 — Canonical financial fact snapshot

**Tests:** `tests/unit/runtime/test_financial_fact_snapshot_v1_5_09.py`

**Production:** add a small runtime model/builder plus a built-in module providing `financial.fact_snapshot` after PIT lineage. Supported fact families are limited to the approved financial keys. Each row preserves fact key/value/unit/period/evidence IDs. Missing facts remain absent; no new financial change is calculated here.

RED must prove the artifact does not exist yet, missing values remain missing, and only PIT-supported facts can enter. GREEN must prove the normal `ResearchRunResult` carries the artifact and snapshot serialization remains deterministic.

## Task 2 — Human-readable depth semantics and hygiene

**Tests:** `tests/unit/reporting/test_research_depth_semantics_v1_5_09.py`

**Production:** project the canonical financial snapshot into typed human-readable rows; add deterministic zh-CN labels/interpretations; format evidence confidence with a visible scale; localize professional question text by stable semantic identity; prevent unmapped/internal reason-code fallbacks from appearing as material economic risks.

RED/GREEN cases: negative margin change = deterioration, not improvement; confidence is human-readable; Chinese body-facing question labels contain no raw English; unknown technical reason codes remain audit/presentation diagnostics rather than key risks; presenter does not mutate canonical artifacts.

Expected compatible component bump: `professional-research-view@1.4.0`; semantic presentation may bump to `1.1.0` if its public output behavior changes.

## Task 3 — Composer/Markdown professional depth

**Tests:** `tests/unit/reporting/test_professional_output_depth_v1_5_09.py`

**Production:** add canonical financial rows to the existing Financial/Operating report block using additive defaults; put core financial changes early in the body; keep state provenance/process metadata later; improve display-only CNY/percentage/pct-point/day/fitness formatting. Funding Loop CNY values must be investor-readable. Raw machine values stay unchanged.

RED/GREEN cases: absolute revenue/net profit/OCF/AR/inventory/capex can reach `ResearchReportDocument`; raw evidence IDs remain appendix-only; CNY becomes 亿/万元 in body; model fitness is sensibly rounded; missing values are omitted; reporting never reads `ResearchContext`/raw evidence.

Expected compatible component bumps: Composer `1.2.0`, Markdown renderer `1.1.0`. HTML/PDF fingerprints remain unchanged unless their implementation changes.

## Task 4 — Dual-status professional field acceptance

**Tests:** `tests/integration/presentation/test_field_acceptance_depth_v1_5_09.py`

**Production:** add `scripts/render_field_acceptance_v1_5_09.py`, keeping the v1.5.08 runner historical. New acceptance returns distinct `presentation_status`, `research_depth_status`, and `release_grade_status`.

Depth checks are deterministic fixture contracts: required financial fact keys, minimum material drivers/operating evidence, contradiction coverage when required, thesis/anti-thesis/falsifier/monitoring coverage, expectation/valuation completeness policy, zh-CN body hygiene, and provenance coverage. A structurally valid report with insufficient research inputs must be `INCOMPLETE`, not full PASS. Fixtures may explicitly expect incompleteness.

## Task 5 — Three-company / three-archetype depth regression

**Fixtures:** create `tests/fixtures/field_acceptance/v1_5_09/{300034.SZ,001287.SZ,301073.SZ}.json` from PIT-supported source facts only.

**Regression:** `tests/regression/research_patterns/test_v1_5_09_research_depth_patterns.py`.

Manufacturing must exercise product/margin/cash/AR/capex conflict where sourced; Distributor must preserve growth→working-capital→funding/factoring→financing burden→cash/valuation-fitness; lease-heavy Hospitality must preserve lease/capability limitations and never infer light-asset economics or fabricate RevPAR/ADR/OCC when unsupported. Real company names/values remain fixture data only.

If available evidence cannot support a full professional expectation/valuation result, the fixture must explicitly assert `research_depth_status=INCOMPLETE`; do not manufacture inputs just to make the gate pass.

## Task 6 — v1.5.09 release closeout

**RED first:** `tests/regression/architecture/test_release_contract_v1_5_09.py`.

Then update `src/research_os/version.py`, `pyproject.toml`, `research_os_version.json`, `README.md`, `CHANGELOG.md`, `docs/migrations/v1.5.09.md`, `docs/prompts/stock_research.md`, `.github/workflows/ci.yml`, and `src/research_os/release/runtime.py`. Convert the v1.5.08 historical release contract from an exact-current-version assertion to a historical compatibility assertion while retaining its exact v1.5.08 component/gate guarantees.

Target release: Research OS `1.5.9`, Core API `1.0`; bump only behaviorally changed component fingerprints. Add permanent release gates for canonical financial snapshot, research-depth semantics/output hygiene, dual-status field acceptance, and v1.5.09 cross-model depth regression. Preserve every historical gate.

CI must run the v1.5.09 three-case field runner and upload outputs in addition to historical v1.5.08 checks.

## Final verification

Only claim completion after fresh evidence on one exact final `main` HEAD:

- architecture/runtime tests PASS;
- PIT/evidence-lineage correctness PASS;
- reporting/expectation/valuation tests PASS;
- v1.5.09 targeted depth tests PASS;
- three-company field acceptance produces the expected presentation/depth statuses;
- existing Playwright/PDF regressions PASS;
- full `pytest -q` PASS;
- `python scripts/release_gate_v1_1.py` PASS and reports `READY: v1.5.9 stable`;
- version metadata/component fingerprints agree;
- remote `main` still equals the verified SHA and remains the only branch.
