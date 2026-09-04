# Research OS 1.6.02 Professional Research Semantic Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the P0 semantic gaps found in the three-company v1.6.01 field output by adding comparable multi-period analysis, executable forecast benchmarking, PIT market-gap valuation, complete decision derivation, hospitality coverage, quantitative funding-loop output, and release-grade reporting without moving research logic into presentation.

**Architecture:** Preserve `ResearchApplication -> ResearchEngine -> ArtifactSnapshot` as the only semantic authority. Add new typed Core API 2.0 artifacts beside existing released artifacts, reuse the existing forecasting, valuation, plugin, snapshot, and reporting infrastructure, and project the new semantics through the existing one-way output chain. Execute M1 through M6 in dependency order; each milestone has its own detailed plan and independent verification gate.

**Tech Stack:** Python 3.12, Pydantic v2, Decimal, statsmodels, scikit-learn, pytest, Hypothesis, Ruff, mypy, import-linter, SQLAlchemy, FastAPI, Markdown/HTML, Playwright/Chromium PDF, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-04-research-os-v1-6-02-professional-research-semantic-closure-design.md`

## Global Constraints

- Planning parent: `c40bf7d08591376f82dc2abf94997db6034a4da6`; re-fetch and freeze the latest `main` SHA before implementation begins.
- Target product version: Research OS `1.6.02`.
- Keep Core API `2.0`, Plugin API `2.0`, Snapshot Schema `2.0`, and HTTP API `v1`.
- Work on the latest `main`; do not create another long-lived branch unless the user explicitly requests one.
- Research semantics are produced only by Engine-executed domain/application modules and stored in canonical artifacts.
- Presenter, Composer, Markdown, HTML, and PDF may select and format canonical values but may not calculate temporal changes, forecast metrics, valuation gaps, decision states, sufficiency, or industry KPIs.
- Preserve `publish_ts/available_ts <= decision_ts`, revision-bound evidence, same-company guards, immutable inputs, deterministic ordering, and content fingerprints.
- Missing data remains missing. Do not interpolate quarters, infer hotel KPIs, substitute zero, inject industry averages, or fabricate realized outcomes to make field acceptance pass.
- Forecast promotion requires out-of-sample evidence, a registered benchmark, PIT compliance, preregistered hypothesis, minimum folds, benchmark improvement, and stability.
- Market anchors never enter valuation reconciliation arithmetic; they are compared with a reconciled model band by a separate canonical market-gap service.
- Research Signal is not automatic trading. No order, position, or execution instruction may be emitted.
- Do not reimplement v1.6.01 sensitivity qualifiers, next verification event, PDF first-page semantic validation, professional canonical wiring, or the projector framework.
- Full Scenario Engine, Previous Snapshot / Research Delta, broad manufacturing/distributor deepening, and Investor Brief redesign remain out of scope for 1.6.02.

---

## Delivery Dependency

```text
M1 Temporal + Sufficiency
          │
          ├──────────────┐
          ▼              ▼
M2 Forecast         M3 Valuation / Market Gap
          │              │
          └──────┬───────┘
                 ▼
       M4 Decision Context v2
                 │
                 ▼
       M5 Industry P0 Closure
                 │
                 ▼
       M6 Field / Release Closure
```

M5 may develop hospitality and funding-loop contracts after M1 independently, but its final integration tests require M4 so Decision can consume the resulting artifacts. M6 starts only after M1-M5 targeted gates are green.

## Detailed Plans

| Milestone | Plan | Independently testable output |
|---|---|---|
| M1 | `2026-09-04-research-os-v1-6-02-m1-temporal-sufficiency.md` | Comparable temporal analysis and domain research sufficiency; one-point series no longer passes temporal coverage |
| M2 | `2026-09-04-research-os-v1-6-02-m2-forecast-benchmark.md` | Professional forecast module executes the existing PIT/OOS benchmark engine and publishes benchmark evidence |
| M3 | `2026-09-04-research-os-v1-6-02-m3-valuation-market-gap.md` | Controlled valuation execution, PIT market anchor, and basis-compatible market gap |
| M4 | `2026-09-04-research-os-v1-6-02-m4-decision-context.md` | Typed decision input assessment and rule-level derivation consuming M1-M3 |
| M5 | `2026-09-04-research-os-v1-6-02-m5-industry-closure.md` | Hospitality plugin/capability gates and full quantitative funding-loop bridge |
| M6 | `2026-09-04-research-os-v1-6-02-m6-field-release.md` | New artifacts reach Markdown/HTML/PDF; three-company and release gates pass |

## Stable Cross-Milestone Interfaces

The detailed plans use these names consistently:

```python
# M1
FinancialResearchInput.period_observations: tuple[FinancialPeriodObservation, ...]
TemporalAnalysisService.analyze(
    observations: tuple[FinancialPeriodObservation, ...],
    *,
    decision_ts: datetime,
) -> FinancialTemporalAnalysis
ResearchSufficiencyEvaluator.evaluate(
    state: ResearchStateView,
) -> ResearchSufficiencyAssessment

# M2
ForecastResearchInput.experiment: ForecastExperimentInput | None
ForecastBenchmarkEvidence

# M3
ValuationResearchInput.execution_requests: tuple[ValuationExecutionRequest, ...]
ValuationResearchInput.market_anchor: PitMarketAnchor | None
ValuationMarketGapService.compare(
    reconciliation: ValuationReconciliation,
    ranges: tuple[ValuationRange, ...],
    anchor: PitMarketAnchor | None,
) -> ValuationMarketGap

# M4
DecisionContextBuilder.build(
    context: ResearchContext,
    state: ResearchStateView,
) -> tuple[DecisionContext, DecisionInputAssessment]

# M5
IndustryCapabilityAssessment
FundingLoopBridge
```

Canonical artifact IDs:

```text
financial.temporal_analysis@2.0
research.sufficiency@2.0
forecast.benchmark_evidence@2.0
valuation.market_anchor@2.0
valuation.market_gap@2.0
decision.input_assessment@2.0
decision.derivation@2.0
industry.capability_assessment@2.0
capital.funding_loop_bridge@2.0
```

## Milestone Exit Sequence

For each milestone:

1. Re-fetch `origin/main` and confirm local `main` has not diverged.
2. Read the design spec and that milestone's detailed plan.
3. Use TDD: focused RED, minimal GREEN, refactor, focused regression.
4. Run that milestone's verification pack inputs before committing.
5. Review `git diff --check`, changed-file scope, artifact lineage, PIT behavior, and absence of secrets.
6. Commit only the verified milestone changes to `main` and push without force.
7. Re-read remote `main` before beginning the next milestone.

## Final Verification

M6 must run fresh, in this order:

```bash
python -m ruff format --check .
python -m ruff check .
python -m mypy src
lint-imports
python -m pytest -q
RESEARCH_OS_RUN_PDF_INTEGRATION=1 python scripts/verify_release_pipeline.py
python -m pip_audit
python -m build
python -m twine check dist/*
python scripts/verify_distribution.py dist/*.whl
git diff --check
```

The three current field cases must also be regenerated into a new temporary directory and their Markdown, HTML, and every PDF page inspected. A test pass alone is not visual/semantic field acceptance.

## Definition of Done

- [ ] M1-M5 targeted verification packs pass independently.
- [ ] A one-point financial series cannot produce temporal coverage `PASS`.
- [ ] At least one real-company case executes an OOS registered benchmark; every insufficient case identifies exact missing evidence.
- [ ] At least one real-company case produces a PIT- and basis-compatible valuation market gap.
- [ ] Decision valuation state is no longer a constant and every consumed dimension appears in decision derivation.
- [ ] `301073.SZ` resolves the hospitality plugin without fabricated ADR/OCC/RevPAR.
- [ ] `001287.SZ` reports the quantitative funding-loop bridge, not only status/reason codes.
- [ ] New artifacts survive Snapshot 2.0 encode/decode/tamper validation and generic HTTP API v1 reads.
- [ ] Markdown/HTML/PDF preserve new semantics without presentation recomputation.
- [ ] Historical replays and all existing v1.6.01 gates remain green.
- [ ] Full quality, test, acceptance, security, package, and release pipeline passes.
- [ ] Verified local `HEAD` equals verified `origin/main`; no force-push, tag rewrite, or historical snapshot mutation occurs.
