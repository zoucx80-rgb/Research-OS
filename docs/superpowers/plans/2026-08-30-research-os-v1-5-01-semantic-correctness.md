# Research OS v1.5.01 Semantic Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden Router semantics, distinguish business-model vs industry-plugin coverage gaps, and add a canonical zh-CN human-readable presentation layer without changing completion or decision truth sources.

**Architecture:** Keep `ResearchRunResult`, `DecisionSummary`, `ResearchCompletionGate` and the plugin runtime canonical. Add backward-compatible semantic metadata to Router/CoverageGap models and add a one-way presentation adapter that consumes the canonical summary. No second completion or decision engine is introduced.

**Tech Stack:** Python 3.12, Pydantic, pytest, GitHub Actions

**Spec:** `docs/superpowers/specs/2026-08-30-research-os-v1-5-01-semantic-correctness-design.md`

## Global Constraints

- Display version is `v1.5.01`; code SemVer is `1.5.1`.
- Frozen field-test baseline is `96a25e16c0e9aa33bcd99752d50037dc119b8608`.
- `CORE_API_VERSION` remains `1.0`.
- No Time Travel, No Fabricated Data, None != 0, and existing lineage semantics remain unchanged.
- `ResearchCompletionGate` remains the sole COMPLETE/INCOMPLETE source.
- `DecisionSummary` remains derived only from `ResearchRunResult`.
- Human-readable presentation must not recompute completion, decision state, valuation state, expectation state, thesis state or fundamental state.
- No Hotel Industry Plugin or Manufacturing-depth expansion in v1.5.01.

---

### Task 1: Router semantic safety and hospitality taxonomy

**Files:**
- Modify: `src/research_os/router/models.py`
- Modify: `src/research_os/router/classifier.py`
- Modify: `tests/unit/router/test_classifier.py`

**Interfaces:**
- Consumes: `Evidence.period`, `Evidence.source_table`, `Evidence.value`
- Produces: `BusinessModelProfile.classification_status`, `BusinessModelProfile.classification_reason`, `BusinessModelRouter.version == "router@1.1.0"`

- [ ] **Step 1: Write failing router tests**

Add tests equivalent to:

```python
def test_interim_inventory_to_revenue_does_not_add_distributor_score():
    interim = ev("inventory_to_revenue", 0.80, period="2026H1")
    profile = BusinessModelRouter().classify("X", [interim])
    assert profile.primary_model == "unknown"
    assert profile.classification_status == "insufficient_evidence"


def test_annual_inventory_to_revenue_can_add_distributor_score():
    annual = ev("inventory_to_revenue", 0.28, period="FY2025")
    profile = BusinessModelRouter().classify("X", [annual])
    assert profile.primary_model == "distributor"


def test_router_represents_hospitality_without_industry_plugin_assumption():
    profile = BusinessModelRouter().classify(
        "301073.SZ", [ev("business_description", "酒店运营与酒店管理 hospitality hotel")]
    )
    assert profile.primary_model == "hospitality"
    assert profile.classification_status == "classified"


def test_router_distinguishes_unsupported_taxonomy_from_missing_evidence():
    unsupported = BusinessModelRouter().classify(
        "X", [ev("business_description", "specialized laboratory testing services")]
    )
    missing = BusinessModelRouter().classify("Y", [])
    assert unsupported.classification_status == "unsupported_taxonomy"
    assert missing.classification_status == "insufficient_evidence"
```

Update the `ev()` test helper to accept `period=None` and pass it through to Evidence.

- [ ] **Step 2: Push tests only and verify RED in GitHub Actions**

Expected: router tests fail because the new fields/taxonomy/period gating do not exist.

- [ ] **Step 3: Implement minimal Router changes**

In `router/models.py` add the defaulted Literal fields. In `classifier.py`, preserve Evidence objects by key, add `_is_annual_period()`, add hospitality keywords, gate only `inventory_to_revenue`, and assign classification status/reason.

- [ ] **Step 4: Verify router tests GREEN**

Run via CI / targeted pytest: `pytest -q tests/unit/router/test_classifier.py`.

---

### Task 2: CoverageGap semantic distinction

**Files:**
- Modify: `src/research_os/plugins/models.py`
- Modify: `src/research_os/plugins/resolver.py`
- Modify: `tests/unit/plugins/test_resolver.py`
- Modify: `tests/unit/plugins/test_extension_request.py`

**Interfaces:**
- Consumes: `BusinessModelProfile.classification_status`
- Produces: new CoverageGap gap types and metadata while preserving existing constructor compatibility.

- [ ] **Step 1: Write failing coverage tests**

Add tests equivalent to:

```python
def test_resolver_distinguishes_unsupported_taxonomy_from_missing_plugin():
    profile = _profile(primary="unknown")
    profile = profile.model_copy(update={"classification_status": "unsupported_taxonomy"})
    result = StrategyResolver().resolve(profile, _context(), _registry())
    assert result.coverage_gaps[0].gap_type == "business_model_taxonomy"
    assert result.coverage_gaps[0].reason_code == "UNSUPPORTED_BUSINESS_MODEL_TAXONOMY"


def test_resolver_distinguishes_insufficient_model_evidence():
    profile = _profile(primary="unknown")
    profile = profile.model_copy(update={"classification_status": "insufficient_evidence"})
    result = StrategyResolver().resolve(profile, _context(), _registry())
    assert result.coverage_gaps[0].gap_type == "business_model_evidence"


def test_recognized_hospitality_gets_industry_strategy_gap():
    profile = _profile(primary="hospitality")
    result = StrategyResolver().resolve(profile, _context(), _registry())
    assert result.coverage_gaps[0].gap_type == "industry_strategy"
    assert result.coverage_gaps[0].business_model == "hospitality"
    assert result.coverage_gaps[0].reason_code == "NO_COMPATIBLE_INDUSTRY_PLUGIN"
```

Extend the ExtensionRequest serialization test to include the new optional metadata and confirm old fields remain valid.

- [ ] **Step 2: Verify RED**

Expected: Literal validation or missing attributes fail.

- [ ] **Step 3: Implement CoverageGap/resolver changes**

Expand the Literal; add defaulted metadata fields. In resolver, short-circuit only the primary `unknown` classification into business-model gaps. Recognized models continue normal plugin resolution.

- [ ] **Step 4: Verify plugin tests GREEN**

Run: `pytest -q tests/unit/plugins/test_resolver.py tests/unit/plugins/test_extension_request.py`.

---

### Task 3: Canonical zh-CN semantic presentation layer

**Files:**
- Create: `src/research_os/reporting/semantics.py`
- Modify: `src/research_os/reporting/__init__.py`
- Create: `tests/unit/reporting/test_semantics.py`
- Modify: `src/research_os/runtime/factory.py`

**Interfaces:**
- Consumes: `DecisionSummary` and `ResearchRunResult`
- Produces: `SemanticValue`, `HumanReadableDecisionSummary`, `DecisionSummaryPresenter`
- Presenter version: `semantic-report@1.0.0`

- [ ] **Step 1: Write failing presentation tests**

Tests must assert:

```python
def test_presenter_keeps_machine_code_secondary_and_chinese_label_primary():
    view = DecisionSummaryPresenter().present(summary)
    assert view.final_status.label == "研究流程未完成"
    assert view.final_status.code == "INCOMPLETE"
    assert view.expectation_evidence_status.label == "证据不足"
    assert view.business_model.label == "分销业务"


def test_presenter_does_not_recompute_completion_or_decision_state():
    view = DecisionSummaryPresenter().build(result)
    assert view.final_status.code == result.completion.final_status
    assert view.decision_state.code == DecisionSummaryBuilder().build(result).decision_state


def test_unknown_reason_code_has_readable_fallback():
    value = DecisionSummaryPresenter().semantic("SOME_INTERNAL_CODE", category="reason")
    assert value.label != "SOME_INTERNAL_CODE"
    assert value.code == "SOME_INTERNAL_CODE"
    assert "尚未配置" in value.explanation


def test_unsupported_locale_fails_explicitly():
    with pytest.raises(ValueError):
        DecisionSummaryPresenter().present(summary, locale="en-US")
```

Also assert translated common Funding Loop reasons and standard module names.

- [ ] **Step 2: Verify RED**

Expected: semantics module/imports do not exist.

- [ ] **Step 3: Implement the presenter**

Implement explicit dictionaries for module status, final status, business model, fundamental/expectation/valuation/thesis state, decision state, common Funding Loop reasons, module names and sections. Fallback returns a Chinese explanatory label while retaining raw code only in `SemanticValue.code`.

`DecisionSummaryPresenter.build()` must call `DecisionSummaryBuilder().build(result)`.

- [ ] **Step 4: Change runtime default `report_version`**

In `_version_bundle`, default to `semantic-report@1.0.0`.

- [ ] **Step 5: Verify reporting tests GREEN**

Run: `pytest -q tests/unit/reporting`.

---

### Task 4: v1.5.01 release contract and version metadata

**Files:**
- Modify: `src/research_os/version.py`
- Modify: `src/research_os/__init__.py`
- Modify: `pyproject.toml`
- Modify: `research_os_version.json`
- Modify: `src/research_os/release/runtime.py`
- Create: `tests/regression/architecture/test_release_contract_v1_5_01.py`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Create: `docs/migrations/v1.5.01.md`

**Interfaces:**
- Produces: public version `1.5.1`, Router module version `1.1.0`, report template/presentation version update, new release-gate nodeids.

- [ ] **Step 1: Write failing release-contract test**

Assert all public version surfaces equal `1.5.1`, Core API remains `1.0`, router metadata equals `1.1.0`, and new gate IDs exist:

```text
router_period_semantics
business_model_gap_semantics
human_readable_reporting
presentation_single_source
```

- [ ] **Step 2: Verify RED**

Expected: current version is 1.4.0 and new gate IDs are absent.

- [ ] **Step 3: Update version surfaces and release checks**

Add CHECKS entries pointing to exact tests created in Tasks 1-3. Do not remove any v1.4 gates.

- [ ] **Step 4: Add migration/release documentation**

Document backward compatibility, new profile/gap metadata and new presentation API. Explicitly document that `DecisionSummary` remains machine canonical and `DecisionSummaryPresenter` is the human-facing adapter.

- [ ] **Step 5: Verify release-contract test GREEN**

Run: `pytest -q tests/regression/architecture/test_release_contract_v1_5_01.py`.

---

### Task 5: Regression and release verification

**Files:**
- No production changes unless a failing regression demonstrates a real defect.

**Interfaces:**
- Confirms all previous v1.4 architecture and correctness guarantees remain intact.

- [ ] **Step 1: Run targeted architecture suite**

`pytest -q tests/unit/runtime tests/unit/plugins tests/unit/knowledge tests/integration/runtime tests/regression/architecture`

Expected: zero failures.

- [ ] **Step 2: Run correctness regression**

`pytest -q tests/regression/research_patterns/test_v1_2_1_correctness_patterns.py tests/unit/kpi/test_period_sensitive_packs.py tests/unit/capital/test_engine.py tests/unit/kpi/test_applicability.py tests/unit/completion/test_consistency.py tests/unit/test_version_consistency_v1_2_1.py`

Expected: zero failures.

- [ ] **Step 3: Run migration smoke**

`pytest -q tests/integration/storage/test_v1_2_lineage_migration.py`

Expected: zero failures.

- [ ] **Step 4: Run full pytest**

`pytest -q`

Expected: zero failures.

- [ ] **Step 5: Run Release Gate**

`python scripts/release_gate_v1_1.py`

Expected: all checks PASS.

- [ ] **Step 6: Compare branch with frozen baseline and review scope**

Confirm no Hotel plugin, Manufacturing-depth logic, second completion source or second canonical result was introduced.

- [ ] **Step 7: Open PR to `main` only after fresh verification evidence is green**
