# Research OS v1.5.03 — Professional Research Integrity

## Status

Approved design for implementation. Display version: `v1.5.03`. Code SemVer: `1.5.3`. `CORE_API_VERSION` remains `1.0`.

## Problem Statement

v1.5.02 established semantic safety: period-aware routing, truthful Coverage Gaps, primary-industry isolation, coverage-aware Thesis blocking, Funding Loop material-risk propagation, expectation-quality flags, and end-to-end `ResearchViewPresenter` projection. Three-company regression (钢研高纳 / 中电港 / 君亭酒店) shows the next correctness boundary: the system is now honest about missing professional coverage, but professional research semantics are still incomplete.

The major defects are:

1. analyst-supplied high-level states can be presented as if they were OS-derived conclusions;
2. built-in Thesis generation can assert “fundamentals improve” without directional evidence for revenue, margin or capital efficiency;
3. Driver Graph lineage is overly broad because every node receives the full Evidence set;
4. industry report contributions can ask professional questions without exposing whether the system has capability, evidence or an answer for each question;
5. human-readable KPI output lacks formatting, scale, period and annualization semantics;
6. expectation freshness is calendar-relative only and can miss a new material disclosure published after the consensus vintage;
7. lease-heavy businesses can be biased toward Distributor by low PPE ratios even when right-of-use assets are economically material;
8. Distributor Funding Loop has no structured representation for factoring / receivable transfer / derecognized working-capital financing exposures.

## Design Goal

Make professional research claims traceable to evidence, capability and provenance, while preserving one canonical runtime and one Completion authority.

The canonical direction remains one-way:

```text
Evidence + Facts + ResearchInputs
        ↓
Canonical Modules / Plugins
        ↓
ResearchRunResult
        ↓
ResearchViewPresenter
        ↓
Human-readable research
```

Presentation must never recalculate Decision, Completion, Thesis, expectation direction or valuation state.

## Non-Goals

v1.5.03 does **not**:

- add a full **Hospitality Plugin**;
- create a second generic-financial Decision state machine;
- perform comprehensive lease-adjusted valuation or accounting restatement;
- rewrite the Forecast subsystem;
- redesign the DecisionEngine state vocabulary;
- equate non-recourse factoring with debt;
- infer missing industry evidence from narrative text.

## Work Package 1 — State Provenance

### Contract

Add a frozen `StateInput` value object:

```python
StateSource = Literal["derived", "analyst_assumption", "external_model", "manual_override"]

class StateInput(BaseModel):
    value: str
    source: StateSource
    evidence_ids: list[str] = []
    method: str | None = None
```

`ResearchInputs` keeps backward compatibility with the existing string fields, but gains optional provenance-aware inputs:

- `fundamental_state_input`
- `valuation_state_input`
- `expectation_state_input`

Resolution rule:

1. if provenance-aware input exists, use it;
2. otherwise wrap the legacy string as `analyst_assumption`;
3. never silently label a legacy string as derived.

`DecisionModule` emits a `decision.state_provenance` artifact containing all three resolved state inputs. `ResearchViewPresenter` displays provenance next to each high-level state.

### Invariant

Human-facing explanations must distinguish “OS-derived” from “analyst-provided”. Legacy callers remain valid but are explicitly labeled as analyst assumptions.

## Work Package 2 — Evidence-driven Thesis and Driver-specific Lineage

### Driver lineage

`DriverGraph.build` no longer assigns the entire run Evidence set to each node. It receives a fact/evidence mapping and maps node IDs to relevant facts.

Minimum built-in mappings:

Manufacturing:
- `revenue` ← revenue
- `margin` ← gross_margin, net_margin
- `ar` ← ar_begin, ar_end
- `inventory` ← inventory_begin, inventory_end
- `capex` ← capex_cash, ppe_begin, ppe_end
- `ocf` / `fcf` ← ocf, capex_cash

Distributor:
- `revenue` ← revenue
- `gross_margin` ← gross_profit, gross_margin
- `ar` ← ar, avg_ar
- `inventory` ← inventory, avg_inventory
- `ap` ← ap, avg_ap
- `nwc` ← delta_nwc, ar, inventory, ap
- `debt` ← short_debt, delta_debt
- `interest` ← interest_expense, financing_cost
- `ocf` ← ocf, operating_cash_flow

Critical nodes must have node-specific evidence. If critical evidence is absent, the specialized graph cannot validate as fully supported.

### Manufacturing graph

Replace the generic three-node manufacturing graph with a conservative financial-manufacturing graph that only uses supported facts:

`revenue → margin → ocf/fcf`, with optional `ar`, `inventory`, `capex`, `asset_efficiency` nodes when supporting facts exist.

This is **not** a high-end-manufacturing specialty graph. Order/backlog/utilization/yield are question-level Coverage states until a future specialized plugin can provide them.

### Thesis gate

Built-in Thesis must not assert directional improvement unless evidence supports the asserted direction.

Add a `ThesisSignalAssessment` artifact with:

- `status`: `SUPPORTED | MIXED | INSUFFICIENT`
- `positive_signals`
- `negative_signals`
- `evidence_ids`

Manufacturing/general Thesis behavior:

- positive directional Thesis only when at least two independent positive signals exist and no material contradiction is present;
- mixed signals produce a neutral “经营信号混合，等待进一步确认” Thesis with `weakening` or `active` only according to evidence;
- insufficient directional inputs produce no active directional Thesis and module status `INSUFFICIENT_EVIDENCE`.

Distributor cash-quality Thesis remains available but falsifiers expand beyond `CFO < 0` to include working-capital / financing conditions when those metrics exist.

## Work Package 3 — Professional Question Coverage

Replace bare `research_questions: list[str]` as the only semantic surface with a structured additive contract while retaining the legacy list.

```python
QuestionStatus = Literal["ANSWERED", "EVIDENCE_MISSING", "CAPABILITY_MISSING", "NOT_APPLICABLE"]

class ResearchQuestionSpec(BaseModel):
    question_id: str
    text: str
    required_capabilities: list[str]
    evidence_keys: list[str]

class ResearchQuestionAssessment(BaseModel):
    question_id: str
    text: str
    status: QuestionStatus
    answer: str | None
    evidence_ids: list[str]
    missing_evidence_keys: list[str]
    missing_capabilities: list[str]
```

`ReportContribution` gains `question_specs`. Runtime evaluates each spec from available capabilities and facts/evidence and stores `report.question_assessments`.

Built-in Manufacturing contribution questions must expose missing order/backlog/utilization/yield/qualification evidence as structured missing states, not imply coverage.

Built-in Distributor questions for receivables, inventory, payables, financing cost and factoring are similarly assessed.

## Work Package 4 — Quantitative Presentation Semantics

`HumanReadableMetric` gains:

- `formatted_value`
- `display_unit`
- `period_label`
- `period_days`
- `annualized`

Formatting metadata is derived from metric identity and canonical reporting-period facts; it does not change underlying values.

Rules:

- ratios/rates → percentage with two decimals when economically a percentage;
- turnover multiples → `x`;
- day metrics → `天`;
- currency metrics preserve configured `financial_unit`;
- raw value remains available as audit metadata;
- H1/Q1/Q2/Q3/Q4 metrics explicitly show period label and period days;
- annualized metrics explicitly state `annualized=True`.

Do not infer annualization merely from metric magnitude.

## Work Package 5 — Event-relative Expectation Freshness

Extend `ResearchInputs` with:

- `latest_material_event_ts: datetime | None`
- `latest_material_event_label: str | None`

`ExpectationQualityAssessment` adds:

- `latest_material_event_ts`
- `post_event_consensus: bool | None`

If the latest material event occurred after the consensus vintage, add reason code:

`CONSENSUS_PREDATES_MATERIAL_EVENT`

and quality becomes `LOW`, regardless of the 90-day calendar threshold.

This is a quality flag only. It does not infer beat/miss direction.

## Work Package 6 — Economic Exposure Integrity

### Lease-aware Router safeguard

Add optional routing facts:

- `right_of_use_assets_to_assets`
- `lease_liabilities_to_assets`

When either indicates economically material lease usage (default threshold `>= 0.20`), low `fixed_asset_to_assets` must **not** add Distributor score. No Hospitality score is created from lease ratios alone.

### Working-capital financing exposures

Add optional Distributor facts:

- `factoring_balance`
- `derecognized_receivables`
- `receivable_transfer_balance`
- `other_working_capital_financing`
- `financing_cost`

Add metrics:

- `factoring_to_ar`
- `working_capital_financing_to_gross_profit`
- `total_financing_cost_to_gross_profit`

`FundingLoopResult` gains additive exposure fields but does not classify non-recourse factoring as debt. Exposures contribute reason codes such as `MATERIAL_FACTORING_EXPOSURE` when disclosed values are economically material.

`DecisionModule` treats material factoring as risk-enhancing only when combined with negative OCF / debt-funded working capital or another canonical stress signal. It must not automatically trigger `RISK_REVIEW` from factoring alone.

## ResearchView Additions

`HumanReadableResearchView` gains:

- `state_provenance`
- `question_assessments`
- `thesis_signal_assessment`
- enriched metric formatting
- enriched expectation event-freshness context
- valuation execution/assumption lineage summary when present

Process status and economic status must be linguistically separated. A Funding Loop module may have execution status “研究模块已完成计算” while its economic state is “融资循环承压”; presentation must not use a bare “通过” label in a way that implies economic health.

## Versioning

- `RESEARCH_OS_VERSION = "1.5.3"`
- display release `v1.5.03`
- `CORE_API_VERSION = "1.0"`
- Manufacturing built-in plugin: `1.1.0`
- Distributor built-in plugin: `1.1.0`
- Manufacturing pack: `manufacturing@1.1.0`
- Distributor pack: `distributor@1.2.0`
- Driver/Thesis component fingerprint: `core:driver-thesis@1.2.0`
- ResearchView presentation fingerprint: `professional-research-view@1.1.0`

Backward-compatible additive fields do not require a Core API major/minor change.

## Completion and Decision Invariants

- `ResearchCompletionGate` remains the only `COMPLETE/INCOMPLETE` authority.
- Presentation cannot change Completion or Decision.
- Missing professional questions do not automatically block the entire run unless their underlying canonical module already blocks completion; the assessments expose coverage truth without introducing a second completion system.
- Coverage-limited industry research remains incomplete for specialized coverage.
- State provenance does not change the DecisionEngine vocabulary.

## Acceptance Tests — Three Company Regression

### 钢研高纳

- Router remains Manufacturing with H1 period safety.
- Manufacturing Driver Graph is no longer only Revenue/Margin/FCF; AR/inventory/capex/OCF nodes appear only with supporting evidence.
- Driver nodes have fact-specific Evidence IDs.
- Thesis cannot say “基本面改善” solely because OCF is positive; mixed margin/AR evidence produces a neutral/mixed signal assessment.
- order/backlog/utilization/yield/qualification questions display `EVIDENCE_MISSING` or `CAPABILITY_MISSING` as appropriate.
- percentage and day metrics display `5.01%`, `140.05天`, and `2026H1 / 181天` semantics rather than raw decimals.

### 中电港

- Router remains Distributor.
- Funding Loop remains risk-relevant with debt-funded NWC and negative OCF.
- factoring / derecognized receivable exposure is visible without being relabeled as debt.
- financing burden includes total financing-cost-to-gross-profit when supplied.
- Driver node lineage is specific.
- Thesis falsifiers include financing / working-capital conditions when corresponding inputs exist.

### 君亭酒店

- Router remains Hospitality.
- material right-of-use assets suppress low-PPE Distributor heuristic.
- no Hospitality Plugin is invented; Coverage Gap and generic graph behavior remain truthful.
- consensus published before the latest H1 material event is flagged `CONSENSUS_PREDATES_MATERIAL_EVENT`, even if only 34 days old.
- no specialized Hospitality Thesis is generated.

## Release Gate

v1.5.03 may be marked stable only when:

1. all v1.4/v1.5.01/v1.5.02 release contracts remain green;
2. new v1.5.03 architecture/correctness tests pass;
3. migration smoke passes;
4. full pytest passes;
5. release gate prints exactly `READY: v1.5.3 stable`;
6. final verification runs on the exact final `main` HEAD after merge.
