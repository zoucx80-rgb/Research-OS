# Research OS v1.5.05 Professional Reporting & Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Research OS 1.5.5 with a one-way professional report composition layer, structured expectation-gap and valuation-result outputs, deterministic materiality/deduplication, monitoring presentation, and lease-heavy semantic safety without introducing a second research state source.

**Architecture:** Preserve `ResearchRunResult -> HumanReadableResearchView` as the sole machine-to-human semantic projection. Add additive canonical expectation/valuation result contracts and project them into the View, then introduce `ResearchReportComposer(HumanReadableResearchView) -> ResearchReportDocument`; renderers/templates may consume only the document. Composer logic is deterministic editorial composition only.

**Tech Stack:** Python 3.12, Pydantic, pytest, existing Research OS runtime/reporting/expectations/valuation modules.

**Spec:** `docs/superpowers/specs/2026-08-30-research-os-v1.5.05-professional-reporting-composition-design.md`

## Global Constraints

- Baseline is `ff718a3e7f1f2ea03e8546d9df2ea5e32cecbe6e`, derived from v1.5.04 `857663032bb540740473249f62e0f5ac37d11e19`.
- Work directly on `main`; no extra branch and no force push.
- `CORE_API_VERSION` remains `1.0` unless an unavoidable incompatible contract is discovered; if so stop for a SemVer decision.
- Composer must accept only `HumanReadableResearchView`; it must not read `ResearchRunResult`, raw evidence providers, web data, or knowledge providers.
- No second Decision, Completion, Thesis, Funding Loop, Forecast, or Valuation state source.
- Missing evidence remains missing; no synthetic consensus, valuation range, Hospitality KPI, or lease-adjusted return may be fabricated.
- All new serialized model fields are additive with defaults.
- No database/Alembic migration is expected.
- TDD is mandatory: test commit first, verify RED through CI, then production code commit and verify GREEN.

---

### Task 1: Structured Expectation Gap Contract

**Files:**
- Modify: `src/research_os/expectations/models.py`
- Modify: `src/research_os/expectations/surprise.py`
- Test: `tests/unit/expectations/test_expectation_gap.py`

**Interfaces:**
- Consumes: existing expectation/consensus facts and `ConsensusVintage` semantics.
- Produces: `ExpectationGapResult` with `metric`, market/OS values or ranges, `direction`, optional valid `magnitude`, quality/freshness metadata, evidence IDs and limitation.

- [ ] **Step 1: Write failing tests**

```python
from research_os.expectations.models import ExpectationGapResult
from research_os.expectations.surprise import build_expectation_gap


def test_missing_consensus_does_not_fabricate_gap():
    assert build_expectation_gap(metric="revenue", market=None, os_view=120.0) is None


def test_numeric_gap_preserves_lineage_and_quality():
    result = build_expectation_gap(
        metric="revenue",
        market={"value": 100.0, "source_count": 3, "source_quality": 0.8,
                "age_days": 12, "post_event_consensus": True,
                "evidence_ids": ["consensus-1"]},
        os_view=120.0,
        os_evidence_ids=["forecast-1"],
    )
    assert isinstance(result, ExpectationGapResult)
    assert result.direction == "ABOVE"
    assert result.magnitude == 20.0
    assert result.evidence_ids == ["consensus-1", "forecast-1"]


def test_thin_or_pre_event_consensus_is_qualified():
    result = build_expectation_gap(
        metric="net_profit",
        market={"value": 10.0, "source_count": 1, "source_quality": 0.6,
                "age_days": 30, "post_event_consensus": False,
                "evidence_ids": ["thin-1"]},
        os_view=11.0,
    )
    assert result is not None
    assert result.limitation
```

- [ ] **Step 2: Verify RED in CI**

Push the test-only commit and confirm GitHub Actions fails because `ExpectationGapResult` / `build_expectation_gap` do not exist.

- [ ] **Step 3: Implement minimal contract and builder**

Use a frozen Pydantic model with optional numeric/range fields and a builder that returns `None` when market evidence is absent. `magnitude` may be calculated only when both compared numeric values are explicit and use the same unit/basis supplied by the caller.

- [ ] **Step 4: Verify GREEN**

Run/observe targeted tests and full CI; all historical expectation tests remain green.

- [ ] **Step 5: Commit**

Commit message: `feat: add structured expectation gap contract`.

---

### Task 2: Numeric Valuation Result Contract

**Files:**
- Modify: `src/research_os/valuation/execution.py`
- Test: `tests/unit/valuation/test_result_contract.py`

**Interfaces:**
- Consumes: existing `ValuationExecution` plus explicitly supplied valuation outputs.
- Produces: additive `ValuationResult` and optional `ValuationExecution.result`.

- [ ] **Step 1: Write failing tests**

```python
from research_os.valuation.execution import ValuationExecution, ValuationResult


def test_valuation_result_defaults_to_missing_without_supported_output():
    execution = ValuationExecution(
        selected_model="dcf", model_fitness_score=0.8, selection_reason="cash economics",
        executed_model="dcf", business_model="manufacturing",
        inputs={"fcf": 1.0}, assumptions=[], scenario_logic="three cases",
        lineage={"fcf": ["e1"]}, driver_bridge=["FCF", "Valuation"],
    )
    assert execution.result is None


def test_valuation_result_carries_scenarios_ranges_and_lineage():
    result = ValuationResult(
        currency="CNY", per_share_value=18.0,
        bear_case=14.0, base_case=18.0, bull_case=22.0,
        primary_range_low=16.0, primary_range_high=20.0,
        current_price=15.0, implied_upside_downside=0.20,
        evidence_ids=["v1"], assumption_ids=["a1"],
    )
    assert result.primary_range_low == 16.0
    assert result.evidence_ids == ["v1"]
```

- [ ] **Step 2: Verify RED in CI**

Push test-only commit and confirm failure is caused by missing result contract.

- [ ] **Step 3: Implement minimal additive model**

`ValuationResult` fields are optional except currency when a result exists; use default factories for method payload, sensitivities, evidence IDs and assumption IDs. Do not derive `implied_upside_downside` inside presentation code.

- [ ] **Step 4: Verify GREEN**

Existing `ValuationExecutionValidator` semantics remain unchanged; targeted and full CI pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add valuation numeric result contract`.

---

### Task 3: Extend HumanReadableResearchView Without Recalculation

**Files:**
- Modify: `src/research_os/reporting/research_view.py`
- Modify: `src/research_os/reporting/__init__.py`
- Test: `tests/unit/reporting/test_research_view_v1_5_05.py`

**Interfaces:**
- Consumes: `artifacts["expectation.gap"]`, `artifacts["valuation.result"]`, existing thesis/falsifier/temporal/coverage artifacts, and lease-heavy profile/evidence flags already present in canonical artifacts.
- Produces: `HumanReadableExpectationGap`, `HumanReadableValuationResult`, `HumanReadableMonitoring`, and `presentation_limitations`; presenter version `professional-research-view@1.3.0`.

- [ ] **Step 1: Write failing projection tests**

Tests must prove: missing expectation gap remains `None`; explicit valuation scenarios are copied not recomputed; monitoring thresholds come from canonical falsifiers; lease-heavy limitation is emitted only from canonical lease-heavy indicator; machine fields remain unchanged after `build()`.

- [ ] **Step 2: Verify RED in CI**

Expected failure: missing new view fields/version/projection methods.

- [ ] **Step 3: Implement one-way projections**

Add frozen human-readable models. Translate only known direction/status codes. Preserve evidence IDs. Build monitoring from existing artifacts and never invent thresholds. Add a presentation limitation text such as `租赁负债/使用权资产具有重要性；当前报告未计算租赁调整后的资本回报或估值。` when canonical lease-heavy indication is true.

- [ ] **Step 4: Verify GREEN**

Run reporting tests plus full CI; historical v1.5.04 presentation tests continue to pass except explicit version expectations, which must be updated only where the public fingerprint intentionally changes.

- [ ] **Step 5: Commit**

Commit message: `feat: project v1.5.05 research outputs`.

---

### Task 4: ResearchReportDocument and Pure Composer

**Files:**
- Create: `src/research_os/reporting/document.py`
- Create: `src/research_os/reporting/composer.py`
- Modify: `src/research_os/reporting/__init__.py`
- Test: `tests/unit/reporting/test_composer.py`

**Interfaces:**
- Consumes: `ResearchReportComposer.compose(view: HumanReadableResearchView) -> ResearchReportDocument`.
- Produces: `InvestmentDecisionSnapshot`, typed report blocks/sections, audit appendix and `composition_version="research-report-composer@1.0.0"`.

- [ ] **Step 1: Write failing composer tests**

```python

def test_composer_copies_canonical_decision_state(view_factory):
    view = view_factory(decision_state="WAIT_FOR_CONFIRMATION")
    before = view.model_dump(mode="json")
    doc = ResearchReportComposer().compose(view)
    assert doc.decision_snapshot.decision_state.code == "WAIT_FOR_CONFIRMATION"
    assert view.model_dump(mode="json") == before


def test_empty_sections_are_omitted(minimal_view):
    doc = ResearchReportComposer().compose(minimal_view)
    assert all(section.blocks for section in doc.sections)


def test_audit_metadata_is_not_main_body(full_view):
    doc = ResearchReportComposer().compose(full_view)
    main = doc.model_dump(mode="json")["sections"]
    assert full_view.commit_sha not in str(main)
    assert doc.audit_appendix.repository_commit == full_view.commit_sha
```

Also cover first-page driver/risk limits and company-specific primary thesis copy.

- [ ] **Step 2: Verify RED in CI**

Expected failure: missing `document` / `composer` modules.

- [ ] **Step 3: Implement document models and minimal composer**

Use typed Pydantic blocks: `NarrativeBlock`, `MetricTableBlock`, `CausalBridgeBlock`, `ThesisBlock`, `ExpectationGapBlock`, `ValuationBlock`, `MonitoringBlock`, `LimitationBlock`, `EvidenceNoteBlock`. Composer selection is deterministic and never takes `ResearchRunResult`.

- [ ] **Step 4: Verify GREEN**

Targeted composer tests and full CI pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add one-way research report composer`.

---

### Task 5: Materiality, Deduplication, Driver Bridge, Lease Guard and Number Formatting

**Files:**
- Modify: `src/research_os/reporting/composer.py`
- Create: `src/research_os/reporting/formatting.py`
- Test: `tests/unit/reporting/test_composition_rules.py`
- Test: `tests/regression/research_patterns/test_v1_5_05_reporting_patterns.py`

**Interfaces:**
- Consumes: human-readable risks, critical driver graph nodes/edges, Funding Loop, valuation driver bridge, expectation gap, monitoring and limitations.
- Produces: deterministic main-body ordering, deduplicated economic meaning, causal bridge and display-only scaled numbers.

- [ ] **Step 1: Write failing structural regressions**

Cover:
- duplicate `NEGATIVE_OCF`/equivalent risk appears once in main narrative;
- distributor bridge preserves `growth -> NWC -> funding -> OCF/financing -> valuation` when those edges/nodes are already supported;
- composer never invents a missing edge;
- Hospitality with no industry plugin shows a material capability limitation and does not fabricate RevPAR/ADR/OCC analysis;
- lease-heavy case does not emit unqualified `现金转化极佳`, `轻资产` or `低资本占用` language;
- CNY `73556000000` displays as `735.56亿元` while the stored numeric value remains unchanged.

- [ ] **Step 2: Verify RED in CI**

Expected failures reflect missing materiality/dedup/formatting behavior.

- [ ] **Step 3: Implement deterministic rules**

Use inspectable priority constants, semantic dedup keys and graph traversal limited strictly to existing edges. `format_cny()` is display-only and returns a string without mutating the source object.

- [ ] **Step 4: Verify GREEN**

Targeted unit/regression suites and full CI pass.

- [ ] **Step 5: Commit**

Commit message: `feat: compose material research narrative safely`.

---

### Task 6: Monitoring, Evidence Placement and Public Reporting Contract

**Files:**
- Modify: `src/research_os/reporting/composer.py`
- Modify: `src/research_os/reporting/document.py`
- Modify: `src/research_os/reporting/__init__.py`
- Test: `tests/unit/reporting/test_monitoring_and_evidence.py`

**Interfaces:**
- Consumes: canonical next event, falsifiers, monitoring fields, evidence IDs, coverage gaps and question assessments already projected into the View.
- Produces: `Monitoring Checklist`, material limitations, concise main-body evidence notes and complete audit provenance.

- [ ] **Step 1: Write failing tests**

Require conviction-up/thesis-broken conditions only when canonical inputs exist; evidence IDs live in audit appendix by default; main-body evidence note is concise and references evidence without raw dumps; unresolved evidence/capability gaps are classified separately.

- [ ] **Step 2: Verify RED in CI**

Expected failure: missing document/composer behavior.

- [ ] **Step 3: Implement minimal behavior**

Do not synthesize new thresholds. Keep complete provenance in the appendix. Separate `evidence_missing`, `capability_missing`, `not_applicable` and deferred/presentation limitations where source semantics support the distinction.

- [ ] **Step 4: Verify GREEN**

Targeted and full CI pass.

- [ ] **Step 5: Commit**

Commit message: `feat: add monitoring and evidence report composition`.

---

### Task 7: Version, Migration, Changelog and Release Gate

**Files:**
- Modify: `src/research_os/version.py`
- Modify: `research_os_version.json`
- Modify: `pyproject.toml` if package version is pinned there
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Create: `docs/migrations/v1.5.05.md`
- Modify: `docs/prompts/stock_research.md` only where the new report output contract must be named
- Modify: `scripts/release_gate_v1_1.py`
- Test: version/release regression files matching existing patterns

**Interfaces:**
- Produces: `RESEARCH_OS_VERSION="1.5.5"`, public display `v1.5.05`, `CORE_API_VERSION="1.0"`, presenter `professional-research-view@1.3.0`, composer `research-report-composer@1.0.0`.

- [ ] **Step 1: Write failing release/version assertions**

Require version consistency and new Release Gate checks: `report_composer_one_way`, `expectation_gap_missingness`, `valuation_result_contract`, `composition_dedup`, `lease_heavy_presentation_guard`, `audit_metadata_separation`.

- [ ] **Step 2: Verify RED in CI**

Expected failure: old version metadata and missing gate checks.

- [ ] **Step 3: Update version/docs/release gate**

Migration note explicitly states no DB migration, additive contracts, renderer migration path, preserved single state source and deferred Hospitality/lease-adjusted methodology.

- [ ] **Step 4: Verify full release**

Required final commands in GitHub Actions or equivalent exact-HEAD environment:

```bash
pytest -q tests/unit/reporting tests/unit/expectations tests/unit/valuation
pytest -q tests/regression/architecture tests/regression/research_patterns/test_v1_5_05_reporting_patterns.py
pytest -q
python scripts/release_gate_v1_1.py
```

All must pass with no warnings/errors material to release.

- [ ] **Step 5: Commit release**

Commit message: `release: professionalize research reporting for v1.5.05`.

- [ ] **Step 6: Final remote verification**

Re-read remote `main`, `research_os_version.json`, `CHANGELOG.md`, migration guide and GitHub Actions result at the exact final SHA. Confirm no extra branch, no DB migration and `CORE_API_VERSION=1.0`.
