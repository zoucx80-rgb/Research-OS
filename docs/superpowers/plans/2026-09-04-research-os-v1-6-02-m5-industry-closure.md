# Research OS 1.6.02 M5 Hospitality and Funding Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve hospitality through Plugin API 2.0 without fabricating hotel KPIs, publish evidence-level industry capability gaps, and preserve the quantitative funding-loop values already computed for distributors.

**Architecture:** Add a built-in hospitality KPI pack and plugin using the existing `KpiProvider` and report-contribution services. A generic capability evaluator uses resolved plugin service capabilities, question specifications, FactView evidence, and canonical MetricResult status to distinguish supported capability from available company evidence. Add a separate funding-loop bridge artifact mapped directly from the existing capital engine result.

**Tech Stack:** Python 3.12, Pydantic v2, Decimal, Plugin API 2.0, MetricDefinitionRegistry, PolicyRegistry, pytest.

**Spec:** `docs/superpowers/specs/2026-09-04-research-os-v1-6-02-professional-research-semantic-closure-design.md`

## Global Constraints

- M1 and M4 are required before final integration; hospitality KPI work may start independently.
- Keep Plugin API `2.0`; use existing manifest, KpiProvider, service-capability, and report-contribution contracts.
- Plugin capability support and company evidence availability are separate states.
- Missing ADR/OCC/RevPAR/same-store/room/mix/lease inputs remain missing; never substitute zero, industry average, or inferred occupancy.
- Lease-adjusted metrics distinguish reported facts, calculations, and assumptions and retain all lineage.
- Preserve existing `capital.funding_loop@2.0`; add `capital.funding_loop_bridge@2.0` rather than expanding its released payload.
- Do not complete the broad manufacturing operating chain or structural industry scenarios in this milestone.
- Before changing default hospitality behavior, freeze v1.6.01 no-plugin field behavior at exact SHA `fd4ce2a83187a251ea60df0d203271e1778fff6b` for historical replay in M6.

---

## File Structure

- Create `src/research_os/kpi/hospitality.py` for the KPI pack and capability metadata.
- Modify `src/research_os/metrics/registry.py` and `calculation.py` for registered hospitality formulas.
- Modify `src/research_os/plugins/builtins.py` to add `HospitalityIndustryPlugin`.
- Create `src/research_os/industry/{__init__,models,capability}.py` for generic capability assessment.
- Create `src/research_os/capital/models.py` and `bridge.py` for the canonical funding-loop bridge.
- Create `src/research_os/application/professional_modules/industry.py` and modify financial-capital/application plan wiring.
- Modify `src/research_os/runtime/core_artifacts.py`, `src/research_os/sufficiency/service.py`, and Decision builder inputs.
- Modify reporting projectors/contribution labels for new artifacts.
- Add plugin, metric, capital, runtime, reporting, and three-company regression tests.

---

### Task 1: Add evidence-gated hospitality metrics

**Files:**
- Create: `src/research_os/kpi/hospitality.py`
- Modify: `src/research_os/metrics/registry.py`
- Modify: `src/research_os/metrics/calculation.py`
- Test: `tests/unit/metrics/test_hospitality_metrics.py`
- Test: `tests/contract/plugins/test_kpi_provider_contract.py`

**Interfaces:**
- Consumes: bound FactView facts and registered metric definitions.
- Produces: `HospitalityPack.metric_ids` and normal `MetricResult` values/missingness.

- [ ] **Step 1: Write RED metric tests**

```python
def test_hospitality_operating_metrics_use_reported_denominators() -> None:
    metrics = calculate_hospitality(
        room_revenue=Decimal("900"),
        occupied_room_nights=Decimal("90"),
        available_room_nights=Decimal("100"),
    )
    assert valid(metrics, "adr").value == Decimal("10")
    assert valid(metrics, "occupancy_rate").value == Decimal("0.9")
    assert valid(metrics, "revpar").value == Decimal("9")


def test_missing_hotel_facts_remain_missing() -> None:
    metrics = calculate_hospitality(room_revenue=Decimal("900"))
    assert result(metrics, "adr").status == "missing"
    assert result(metrics, "revpar").status == "missing"
```

- [ ] **Step 2: Register formulas and definitions**

Add definitions for:

```text
adr = room_revenue / occupied_room_nights
occupancy_rate = occupied_room_nights / available_room_nights
revpar = room_revenue / available_room_nights
same_store_revenue_growth = (same_store_revenue_current / same_store_revenue_prior) - 1
hotel_count = identity(reported_hotel_count)
room_count = identity(reported_room_count)
mature_hotel_share = mature_hotel_count / reported_hotel_count
ramp_up_hotel_share = ramp_up_hotel_count / reported_hotel_count
managed_room_share = managed_room_count / reported_room_count
franchised_room_share = franchised_room_count / reported_room_count
leased_room_share = leased_room_count / reported_room_count
lease_adjusted_roic = (nopat + lease_interest * (1 - tax_rate)) / (average_invested_capital + average_lease_liabilities)
```

Implement `identity`, `growth_rate`, and `lease_adjusted_roic` in the central calculation engine. `same_store_revenue_growth` requires equal explicit comparison basis. Lease-adjusted ROIC requires all stated inputs and evidence; missing tax rate/lease interest/opening balances returns typed missingness.

- [ ] **Step 3: Implement the pack**

```python
class HospitalityKpiPack:
    pack_version = "hospitality@2.0.0"
    metric_ids = (
        "adr", "occupancy_rate", "revpar", "same_store_revenue_growth",
        "hotel_count", "room_count", "mature_hotel_share", "ramp_up_hotel_share",
        "managed_room_share", "franchised_room_share", "leased_room_share",
        "lease_adjusted_roic",
    )
```

- [ ] **Step 4: Run and commit**

```bash
pytest -q tests/unit/metrics/test_hospitality_metrics.py tests/contract/plugins/test_kpi_provider_contract.py tests/integration/metrics/test_existing_kpi_migration.py
git add src/research_os/kpi/hospitality.py src/research_os/metrics tests/unit/metrics/test_hospitality_metrics.py tests/contract/plugins/test_kpi_provider_contract.py
git commit -m "feat: add evidence-gated hospitality metrics"
```

### Task 2: Add the built-in HospitalityIndustryPlugin

**Files:**
- Modify: `src/research_os/plugins/builtins.py`
- Test: `tests/unit/plugins/test_builtin_industry_plugins.py`
- Test: `tests/unit/plugins/test_hospitality_plugin.py`
- Test: `tests/integration/runtime/test_plugin_services_v2.py`
- Test: `tests/integration/runtime/test_hospitality_plugin_snapshot.py`

**Interfaces:**
- Consumes: Router `primary_model="hospitality"`, `HospitalityKpiPack`.
- Produces: stable plugin `industry:hospitality@2.0.0` via existing Plugin API 2.0.

- [ ] **Step 1: Write resolution/absence RED**

```python
def test_hospitality_resolves_builtin_plugin() -> None:
    result = resolve_strategy(profile("hospitality"), hospitality_context())
    assert result.industry_plugins[0].plugin_id == "industry:hospitality"
    assert not result.coverage_gaps


def test_hospitality_plugin_does_not_make_missing_kpis_valid() -> None:
    metrics = run_hospitality_without_operating_facts().artifacts.require(KPI_METRICS)
    assert all(item.status == "missing" for item in metrics.metrics if item.metric_id in HOSPITALITY_METRIC_IDS)
```

- [ ] **Step 2: Implement plugin manifest/services**

```python
class HospitalityIndustryPlugin:
    manifest = PluginManifest(
        plugin_id="industry:hospitality",
        plugin_type="industry",
        plugin_version="2.0.0",
        plugin_api_version="2.0",
        core_api_specifier="~=2.0",
        research_os_specifier=">=1.6.02,<2",
        supported_business_models=frozenset({"hospitality"}),
        service_capabilities=frozenset({
            "kpi.metrics", "report.contributions", "hospitality.operating",
            "hospitality.portfolio_mix", "hospitality.lease_adjusted",
        }),
        priority=100,
        maturity="stable",
    )
```

Use `_BuiltinKpiProvider` with `HospitalityKpiPack`. Add question specifications for operating productivity, portfolio/mix, and lease-adjusted economics with explicit `evidence_keys`. Return plugins in deterministic plugin-ID order from `BuiltinPluginProvider`.

Add a manifest/component-fingerprint test and a Snapshot 2.0 round-trip test proving the resolved hospitality plugin identity and KPI artifacts survive replay. Exercise provider failure isolation separately from ordinary missing company evidence.

- [ ] **Step 3: Run and commit**

```bash
pytest -q tests/unit/plugins/test_builtin_industry_plugins.py tests/unit/plugins/test_hospitality_plugin.py tests/integration/runtime/test_plugin_services_v2.py tests/integration/runtime/test_hospitality_plugin_snapshot.py tests/unit/router
git add src/research_os/plugins/builtins.py tests/unit/plugins tests/integration/runtime/test_plugin_services_v2.py tests/integration/runtime/test_hospitality_plugin_snapshot.py
git commit -m "feat: add hospitality industry plugin"
```

### Task 3: Publish generic industry capability assessment

**Files:**
- Create: `src/research_os/industry/__init__.py`
- Create: `src/research_os/industry/models.py`
- Create: `src/research_os/industry/capability.py`
- Create: `src/research_os/application/professional_modules/industry.py`
- Modify: `src/research_os/application/professional_modules/__init__.py`
- Modify: `src/research_os/runtime/core_artifacts.py`
- Modify: `src/research_os/application/plan.py`
- Test: `tests/unit/industry/test_capability.py`
- Test: `tests/integration/runtime/test_industry_capability.py`

**Interfaces:**
- Consumes: `StrategyResolution`, resolved plugin services, FactView, `KPI_METRICS`.
- Produces: `INDUSTRY_CAPABILITY_ASSESSMENT`.

- [ ] **Step 1: Write capability-vs-evidence RED**

```python
def test_supported_plugin_capability_can_still_lack_company_evidence() -> None:
    assessment = evaluate_hospitality_capabilities(context_without_room_data())
    item = assessment.require("hospitality.operating")
    assert item.capability_status == "SUPPORTED"
    assert item.evidence_status == "MISSING"
    assert "occupied_room_nights" in item.missing_evidence_keys
```

- [ ] **Step 2: Implement contracts**

```python
class IndustryCapabilityItem(LineageValue):
    capability_id: str
    capability_status: Literal["SUPPORTED", "MISSING", "NOT_APPLICABLE"]
    evidence_status: Literal["AVAILABLE", "PARTIAL", "MISSING", "NOT_APPLICABLE"]
    metric_ids: tuple[str, ...] = ()
    available_evidence_keys: tuple[str, ...] = ()
    missing_evidence_keys: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()


class IndustryCapabilityAssessment(DomainArtifact):
    business_model: str
    plugin_ids: tuple[str, ...] = ()
    capabilities: tuple[IndustryCapabilityItem, ...] = ()

    def require(self, capability_id: str) -> IndustryCapabilityItem: ...
```

- [ ] **Step 3: Implement evaluator/module**

The evaluator reads resolved plugin manifest capabilities and existing `ReportContribution.question_specs`; it uses FactView evidence keys and the plugin provider's MetricResult statuses. Report contributions provide plugin-authored requirement metadata but never compute answers. Missing required capability yields `capability_status=MISSING`; supported calculation with absent facts yields `evidence_status=MISSING`.

Insert `IndustryCapabilityModule` after methodology and before `ResearchSufficiencyModule`; require `STRATEGY_RESOLUTION` and `KPI_METRICS`, then let Sufficiency and Decision consume its output. Keep the final ordering `... -> methodology -> industry capability -> research sufficiency -> portfolio decision`.

Register:

```python
INDUSTRY_CAPABILITY_ASSESSMENT = ArtifactKey(
    artifact_id="industry.capability_assessment",
    schema_version="2.0",
    value_type=IndustryCapabilityAssessment,
)
```

- [ ] **Step 4: Run and commit**

```bash
pytest -q tests/unit/industry/test_capability.py tests/integration/runtime/test_industry_capability.py tests/unit/plugins/test_coverage_gap_v1_6.py
git add src/research_os/industry src/research_os/application/professional_modules/industry.py src/research_os/application/professional_modules/__init__.py src/research_os/runtime/core_artifacts.py src/research_os/application/plan.py tests/unit/industry tests/integration/runtime/test_industry_capability.py
git commit -m "feat: assess industry capability evidence"
```

### Task 4: Preserve the quantitative funding-loop bridge

**Files:**
- Create: `src/research_os/capital/models.py`
- Create: `src/research_os/capital/bridge.py`
- Modify: `src/research_os/capital/__init__.py`
- Modify: `src/research_os/application/professional_modules/financial_capital.py`
- Modify: `src/research_os/runtime/core_artifacts.py`
- Test: `tests/unit/capital/test_bridge.py`
- Test: `tests/integration/runtime/test_funding_loop_bridge.py`

**Interfaces:**
- Consumes: existing `FundingLoopResult`, policy thresholds, fact evidence refs.
- Produces: `FundingLoopBridgeService.build(result, evidence_refs) -> FundingLoopBridge`, artifact `CAPITAL_FUNDING_LOOP_BRIDGE`.

- [ ] **Step 1: Write lossless-mapping RED**

```python
def test_bridge_preserves_engine_quantities_and_basis() -> None:
    engine_result = engine().funding_loop(distributor_facts())
    bridge = FundingLoopBridgeService().build(engine_result, evidence_refs())
    assert bridge.incremental_revenue == Decimal(str(engine_result.incremental_revenue))
    assert bridge.incremental_nwc == Decimal(str(engine_result.incremental_nwc))
    assert bridge.incremental_debt == Decimal(str(engine_result.incremental_debt))
    assert bridge.factoring_to_ar == Decimal(str(engine_result.factoring_to_ar))
    assert bridge.comparison_basis_status == engine_result.comparison_basis_status
```

- [ ] **Step 2: Implement bridge contract/service**

```python
class FundingLoopBridge(DomainArtifact):
    funding_state: str = "unknown"
    incremental_revenue: Decimal | None = None
    incremental_nwc: Decimal | None = None
    incremental_debt: Decimal | None = None
    incremental_equity: Decimal | None = None
    reported_equity_change: Decimal | None = None
    operating_cash_flow: Decimal | None = None
    factoring_balance: Decimal | None = None
    derecognized_receivables: Decimal | None = None
    receivable_transfer_balance: Decimal | None = None
    other_working_capital_financing: Decimal | None = None
    factoring_to_ar: Decimal | None = None
    comparison_basis_status: str = "NOT_APPLICABLE"
    comparison_basis_errors: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
    deterioration_conditions: tuple[str, ...] = ()
    repair_conditions: tuple[str, ...] = ()
```

Map every engine field. Conditions are stable policy-derived monitoring statements; they cannot assert future outcomes.

- [ ] **Step 3: Register and write both capital artifacts**

```python
CAPITAL_FUNDING_LOOP_BRIDGE = ArtifactKey(
    artifact_id="capital.funding_loop_bridge",
    schema_version="2.0",
    value_type=FundingLoopBridge,
)
```

`CapitalResearchModule` writes existing `FundingLoop` and new bridge from the same engine result and evidence refs.

- [ ] **Step 4: Run and commit**

```bash
pytest -q tests/unit/capital tests/integration/runtime/test_funding_loop_bridge.py tests/unit/contracts/test_core_artifacts.py tests/unit/snapshots tests/property/snapshots
git add src/research_os/capital src/research_os/application/professional_modules/financial_capital.py src/research_os/runtime/core_artifacts.py tests/unit/capital tests/integration/runtime/test_funding_loop_bridge.py
git commit -m "feat: preserve quantitative funding loop"
```

### Task 5: Integrate industry artifacts with Sufficiency and Decision

**Files:**
- Modify: `src/research_os/sufficiency/service.py`
- Modify: `src/research_os/decision/context.py`
- Modify: `src/research_os/application/plan.py`
- Test: `tests/unit/sufficiency/test_industry_sufficiency.py`
- Test: `tests/unit/decision/test_context_builder.py`
- Test: `tests/regression/professional/test_v1_6_02_industry_closure.py`

**Interfaces:**
- Consumes: industry capability assessment and funding-loop bridge.
- Produces: industry sufficiency gaps and quantitative funding inputs in decision assessment.

- [ ] **Step 1: Write RED**

```python
def test_hospitality_plugin_resolves_without_fabricating_metrics() -> None:
    result = run_hospitality_case_without_room_data()
    assert result.strategy_resolution.industry_plugins[0].plugin_id == "industry:hospitality"
    assert result.execution_completion.final_status == "COMPLETE"
    assert result.artifacts.require(INDUSTRY_CAPABILITY_ASSESSMENT).require("hospitality.operating").evidence_status == "MISSING"
    assert no_valid_hospitality_metrics(result)


def test_distributor_decision_input_contains_quantitative_funding_bridge() -> None:
    result = run_distributor_case()
    assert result.artifacts.require(CAPITAL_FUNDING_LOOP_BRIDGE).incremental_debt is not None
    assert result.artifacts.require(DECISION_INPUT_ASSESSMENT).require_dimension("funding_loop").artifact_ids == ("capital.funding_loop", "capital.funding_loop_bridge")
```

- [ ] **Step 2: Implement integration**

Add industry coverage to `ResearchSufficiencyEvaluator`; missing hotel evidence is a material gap but not an Engine failure when the plugin is present. Use quantitative bridge state/reasons in Decision context while preserving the existing material funding veto.

- [ ] **Step 3: Run and commit**

```bash
pytest -q tests/unit/sufficiency/test_industry_sufficiency.py tests/unit/decision/test_context_builder.py tests/regression/professional/test_v1_6_02_industry_closure.py
git add src/research_os/sufficiency/service.py src/research_os/decision/context.py src/research_os/application/plan.py tests/unit/sufficiency tests/unit/decision/test_context_builder.py tests/regression/professional/test_v1_6_02_industry_closure.py
git commit -m "feat: consume industry evidence in research state"
```

### Task 6: Project industry output and add the M5 gate

**Files:**
- Modify: `src/research_os/reporting/projectors/_core.py`
- Modify: `src/research_os/reporting/projectors/_registry.py`
- Modify: `src/research_os/reporting/projectors/_shared.py`
- Create: `tests/unit/reporting/test_v1_6_02_industry.py`
- Modify: `tests/fixtures/field_acceptance/v1_6_02/301073.SZ.json`
- Modify: `src/research_os/release/replays.py`
- Modify: `src/research_os/release/verification.py`
- Modify: `tests/unit/release/test_historical_replay_v1_6.py`
- Modify: `tests/regression/architecture/test_release_governance.py`

**Interfaces:**
- Consumes: capability/funding artifacts and exact v1.6.01 release SHA.
- Produces: investor-readable industry output, frozen v1.6.01 replay metadata, and pack `v1-6-02-industry-closure`.

- [ ] **Step 1: Freeze v1.6.01 before changing current expectations**

```python
"field-v1.6.01": ReplayProfile(
    profile_id="field-v1.6.01",
    source_commit_sha="fd4ce2a83187a251ea60df0d203271e1778fff6b",
    expected_product_version="1.6.01",
    expected_core_api_version="2.0",
    runner_script="scripts/render_field_acceptance_v1_6_01.py",
    fixture_dir="tests/fixtures/field_acceptance/v1_6_01",
    output_dir="build/historical-replay/v1.6.01",
    artifact_name="v1.6.01-historical-replay",
)
```

This preserves the accepted no-plugin result at its exact code. Current v1.6.02 tests must not pretend that the old default behavior is still current, and no runtime compatibility switch is introduced.

- [ ] **Step 2: Write reporting/field RED**

```python
def test_hospitality_projection_separates_capability_and_evidence() -> None:
    payload = project_artifact("industry.capability_assessment", hospitality_assessment()).payload
    assert payload["行业能力"][0]["计算能力"] == "支持"
    assert payload["行业能力"][0]["公司证据"] == "缺失"


def test_distributor_projection_contains_quantitative_funding_loop() -> None:
    payload = project_artifact("capital.funding_loop_bridge", distributor_bridge()).payload
    assert payload["增量营运资本"]
    assert payload["增量债务"]
    assert payload["修复条件"]
```

- [ ] **Step 3: Register the M5 pack**

```python
_V1_6_02_INDUSTRY_CHECKS = {
    "v1_6_02_hospitality_metrics": "tests/unit/metrics/test_hospitality_metrics.py",
    "v1_6_02_hospitality_plugin": "tests/unit/plugins/test_hospitality_plugin.py",
    "v1_6_02_industry_capability": "tests/unit/industry",
    "v1_6_02_funding_bridge": "tests/unit/capital/test_bridge.py",
    "v1_6_02_industry_runtime": "tests/integration/runtime/test_industry_capability.py",
    "v1_6_02_industry_field": "tests/regression/professional/test_v1_6_02_industry_closure.py",
    "v1_6_02_industry_reporting": "tests/unit/reporting/test_v1_6_02_industry.py",
}
```

- [ ] **Step 4: Run M5 exit gate and commit**

```bash
pytest -q tests/unit/metrics/test_hospitality_metrics.py tests/unit/plugins/test_hospitality_plugin.py tests/unit/industry tests/unit/capital/test_bridge.py tests/integration/runtime/test_industry_capability.py tests/integration/runtime/test_funding_loop_bridge.py tests/regression/professional/test_v1_6_02_industry_closure.py tests/unit/reporting/test_v1_6_02_industry.py tests/unit/release/test_historical_replay_v1_6.py tests/regression/architecture/test_release_governance.py
python -m ruff check src/research_os/kpi/hospitality.py src/research_os/industry src/research_os/capital tests/unit/industry
git diff --check
git add src/research_os/reporting/projectors tests/unit/reporting/test_v1_6_02_industry.py tests/fixtures/field_acceptance/v1_6_02/301073.SZ.json src/research_os/release tests/unit/release/test_historical_replay_v1_6.py tests/regression/architecture/test_release_governance.py
git commit -m "test: gate v1.6.02 industry closure"
```
