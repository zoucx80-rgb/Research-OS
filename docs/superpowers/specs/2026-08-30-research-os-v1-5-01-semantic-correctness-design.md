# Research OS v1.5.01 Semantic Correctness Design

## Status

Approved direction from the 2026-08-30 three-company v1.4.0 field test. This design is intentionally narrow.

- Display version: `v1.5.01`
- Code SemVer: `1.5.1`
- Frozen field-test baseline: `96a25e16c0e9aa33bcd99752d50037dc119b8608`
- Core API: `1.0` (unchanged)

## Problem statement

The v1.4.0 field test across 钢研高纳, 中电港 and 君亭酒店 showed that the canonical runtime, plugin resolution, completion gate, funding-loop calculations and snapshot architecture remain structurally sound. The recurring correctness failures are narrower:

1. Router ratio features can be consumed without explicit period semantics. `inventory_to_revenue` is unsafe across annual and interim periods.
2. `unknown` business model currently collapses insufficient evidence and unsupported taxonomy into one state. Strategy resolution then misreports both as an industry-plugin coverage gap.
3. Canonical machine states are exposed too directly by reporting. Enum values, reason codes and internal business-model identifiers can become the primary human-facing output.

These are semantic-boundary problems, not reasons to redesign the runtime.

## Goals

### G1. Router semantic safety

The router must preserve existing automatic classification while refusing to use period-sensitive ratio evidence whose period meaning is not explicit enough for cross-company classification.

`inventory_to_revenue` may contribute only when its evidence explicitly represents an annual period. Description, gross margin and fixed-asset ratios remain usable under their existing semantics.

The router must record a classification status separate from `primary_model`:

- `classified`
- `unsupported_taxonomy`
- `insufficient_evidence`

`primary_model="unknown"` remains for compatibility when no supported model can be selected.

The standard taxonomy gains `hospitality`, detected from hotel/hospitality/lodging/accommodation and Chinese hotel/lodging terms. This is taxonomy support only; v1.5.01 does not add a hotel industry plugin.

### G2. CoverageGap correctness

StrategyResolver must distinguish three cases:

- represented model, no compatible industry plugin -> `industry_strategy`
- router has meaningful business description but taxonomy cannot represent it -> `business_model_taxonomy`
- router lacks enough usable business-model evidence -> `business_model_evidence`

CoverageGap remains a passive diagnostic record. It must never mutate plugin registries, completion status or decision state.

CoverageGap gains optional machine-readable metadata:

- `reason_code`
- `affected_capabilities`
- `fallback_available`

Existing serialized payloads remain valid.

For a recognized `hospitality` company with no hotel plugin, the resolver must emit an `industry_strategy` gap for `hospitality`, not an `unknown` taxonomy gap and never a manufacturing/distributor fallback.

### G3. Human-readable presentation contract

Canonical machine models remain canonical. `DecisionSummary` continues to carry machine values and remains derived only from `ResearchRunResult`.

A new presentation layer converts the canonical summary into a human-readable view without changing machine semantics.

The presentation contract is:

`machine code -> localized label -> localized explanation`

The machine code remains available as secondary metadata; the localized label/explanation are primary.

At minimum the zh-CN presenter must cover:

- module statuses: PASS / FAIL / INSUFFICIENT_EVIDENCE / NOT_APPLICABLE
- final status: COMPLETE / INCOMPLETE
- thesis, fundamental, expectation and valuation states
- research decision states
- business models including manufacturing, distributor, hospitality and unknown
- common Funding Loop reason codes
- blocking-module names and standard report section names

Unknown reason codes must not be printed as the primary conclusion. The fallback must say that no localized explanation is configured and preserve the raw code only as technical metadata.

The presenter must not calculate completion, decision state or any research signal. It only projects canonical values.

## Non-goals

v1.5.01 must NOT:

- add a Hotel/Hospitality Industry Plugin
- add RevPAR/ADR/OCC KPI modules
- deepen Manufacturing Pack with orders, backlog, utilization, yield or aerospace-specific logic
- rewrite Distributor Pack or Funding Loop thresholds
- add a second ResearchRunResult, Completion Gate or decision engine
- redesign ConsensusVintage; `source_count` and `source_quality` already exist and are not duplicated
- add company-specific 钢研高纳/中电港/君亭酒店 logic to Core
- change CORE_API_VERSION from `1.0`

## Router design

`BusinessModelProfile` receives backward-compatible default fields:

```python
classification_status: Literal[
    "classified",
    "unsupported_taxonomy",
    "insufficient_evidence",
] = "classified"
classification_reason: str | None = None
```

Router selection rules:

1. Build evidence records by metric key without discarding the Evidence object.
2. Run description keyword scoring.
3. `inventory_to_revenue` contributes only when the corresponding Evidence period is explicitly annual.
4. Other existing ratios preserve existing behavior.
5. If scores exist, status is `classified`.
6. If no scores and a non-empty business description exists, status is `unsupported_taxonomy`.
7. If no scores and no useful description exists, status is `insufficient_evidence`.

Annual-period recognition is intentionally conservative. Accepted examples include `FY2025`, `2025`, `annual`, `year`, `年度`, `年报`, and common annual suffixes. Unknown/interim periods do not contribute the inventory/revenue score.

Router version becomes `router@1.1.0`.

## CoverageGap design

`CoverageGap.gap_type` expands to:

```text
industry_strategy
methodology
capability
business_model_taxonomy
business_model_evidence
```

Optional fields:

```python
reason_code: str | None = None
affected_capabilities: list[str] = []
fallback_available: bool | None = None
```

Resolver behavior for `primary_model == "unknown"`:

- `unsupported_taxonomy` -> one `business_model_taxonomy` gap, skip industry plugin search for unknown.
- `insufficient_evidence` -> one `business_model_evidence` gap, skip industry plugin search for unknown.

Recognized unsupported models such as `hospitality` proceed through normal industry resolution and generate `industry_strategy` when no plugin exists.

## Presentation design

Create `research_os.reporting.semantics` with:

```python
class SemanticValue(BaseModel):
    label: str
    explanation: str
    code: str

class HumanReadableDecisionSummary(BaseModel):
    ...

class DecisionSummaryPresenter:
    version = "semantic-report@1.0.0"
    def present(self, summary: DecisionSummary, locale: str = "zh-CN") -> HumanReadableDecisionSummary: ...
    def build(self, result: ResearchRunResult, locale: str = "zh-CN") -> HumanReadableDecisionSummary: ...
```

`build()` must first call the canonical `DecisionSummaryBuilder`; this preserves the single result/completion source.

The initial locale is `zh-CN`. Unsupported locales fail explicitly instead of silently returning raw machine values.

`SemanticValue.code` is technical metadata. `label` and `explanation` are the human-facing surface.

## Snapshot/version semantics

No snapshot payload redesign is required. Existing VersionBundle already includes `report_version`. Runtime default report version changes from `runtime-result@1.0.0` to `semantic-report@1.0.0`, making presentation semantics auditable without introducing another fingerprint system.

Research OS public version becomes `1.5.1`; Core API remains `1.0`.

## Release gates

v1.5.01 adds regression gates for:

1. interim inventory/revenue evidence cannot bias router classification
2. hospitality is represented but honestly receives an industry strategy CoverageGap
3. unsupported taxonomy and insufficient business-model evidence are distinct
4. human-readable presentation never uses raw machine codes as primary labels
5. presentation mirrors canonical completion/decision values rather than recomputing them
6. v1.4 architecture invariants remain green
7. full pytest and release gate remain green

## Compatibility

All additions to existing Pydantic models use defaults. Existing callers that construct BusinessModelProfile, CoverageGap and ExtensionRequest remain valid. No public method is removed. No legacy orchestration path is reintroduced.

## Deferred candidates

### v1.5.02

Industry Strategy Depth: improve Manufacturing Pack and industry report contributions using 钢研高纳 as a regression fixture.

### v1.5.03

Hospitality Strategy Plugin: RevPAR, ADR, OCC, same-store, network opening/maturity, managed vs direct economics and lease-adjusted capital efficiency using 君亭酒店 as the first fixture.

Expectation consensus-quality use of existing `source_count` and `source_quality` remains a methodology candidate unless subsequent regression evidence shows it is a v1.5.01 blocker.
