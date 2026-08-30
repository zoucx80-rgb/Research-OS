# Research OS v1.5.07 Presentation Renderer Design

## Status

Approved direction from the 2026-08-30 three-company output field validation: add a standalone presentation renderer downstream of `ResearchReportDocument`; do not push layout/publishing concerns back into `ResearchReportComposer` or any research engine.

## Problem

Research OS v1.5.06 closes the composition-coverage gap: material canonical artifacts present in `HumanReadableResearchView` are now carried into typed `ResearchReportDocument` blocks. The repository still has no canonical renderer for those blocks. Therefore the system can guarantee *what* belongs in the report but cannot guarantee *how* those typed blocks become professional human-readable Markdown/HTML/PDF.

A naive serializer would expose intermediate implementation details such as `block_type`, `metric_id`, `formula_version`, semantic `code`, Python/dict representations, empty `None` fields, repository/plugin/module metadata, raw evidence IDs, and assumption IDs. That would reintroduce the field-test problem at a later layer.

## Goals

1. Add one deterministic Markdown renderer that consumes `ResearchReportDocument` only.
2. Render the decision snapshot and every existing typed report block into professional zh-CN Markdown without recomputing research semantics.
3. Keep machine/audit metadata separate from primary investment prose.
4. Make identical `ResearchReportDocument` inputs produce byte-identical Markdown.
5. Establish a stable renderer fingerprint and Release Gate so renderer quality is testable in the repository.
6. Preserve cross-model truthfulness for Manufacturing, Distributor, and coverage-limited Hospitality patterns.

## Non-goals

- No PDF engine, browser engine, CSS framework, chart engine, or document-layout engine in v1.5.07.
- No direct `ResearchRunResult` or `HumanReadableResearchView` input to the renderer.
- No KPI, Funding Loop, Thesis, expectation, Forecast, valuation, Decision, Completion, Router, or coverage computation.
- No company-specific rendering branches.
- No Hospitality Plugin, hotel KPI synthesis, lease-adjusted ROIC, or lease-adjusted valuation.
- No rewriting of canonical conclusions for rhetorical strength.

## Architecture

```text
ResearchRunResult
    ↓
ResearchViewPresenter
    ↓
HumanReadableResearchView
    ↓
ResearchReportComposer
    ↓
ResearchReportDocument
    ↓
ResearchReportMarkdownRenderer
    ↓
Markdown
    ↓
future HTML/PDF adapter
```

`ResearchReportMarkdownRenderer.render(document: ResearchReportDocument) -> str` is the only new public rendering entry point.

The renderer is presentation-only. It may select display fields, order fields, format already-humanized values, omit empty values, and convert typed blocks into Markdown syntax. It may not derive a new value or change a canonical semantic state.

## Renderer output contract

### Document header

Render:
- report title using company id from document metadata;
- decision date;
- business-model display label;
- renderer fingerprint as secondary metadata only when audit metadata is emitted.

Do not expose internal repository SHA, plugin IDs, module statuses, evidence IDs, or assumption IDs in the opening body.

### Decision snapshot

The first substantive section is `投资决策快照` and contains:
- business model label;
- decision state label when present;
- fundamental, thesis, expectation, and valuation state labels;
- primary thesis;
- material drivers;
- up to the composed material risks;
- evidence confidence;
- next verification event;
- top material limitation when present.

Semantic codes are not primary prose. Use `SemanticValue.label` and, where useful, `explanation`.

### Core investment judgment

Render `NarrativeBlock` as normal research prose. No repr/JSON wrappers.

### FinancialOperatingBlock

Render Financial Sanity as a compact statement and KPI metrics as a Markdown table with the user-facing columns:

`指标 | 数值 | 期间 | 状态 | 说明`

Field-selection rules:
- prefer `formatted_value`; if absent, use existing `value` without deriving a new scale;
- use `period_label` when present;
- use semantic status label, not raw status code;
- use metric explanation/reason as concise explanation;
- do not display `metric_id`, `formula_version`, `period_days`, `annualized`, or evidence IDs as ordinary table columns. Period/annualization detail may be appended to the period text only when already explicit and necessary; no annualization is calculated by the renderer.

### CapitalFundingBlock

Render two subsections when available:
- `资本效率`
- `融资循环`

Use existing canonical values directly. Suppress empty fields. Show semantic labels for calculation status, funding state, comparison-basis status, and limitations. Do not infer funding state from the numeric fields.

### CausalBridgeBlock

Render existing steps as one ordered arrow chain. Never add or reorder causal nodes.

### ThesisDebateBlock

For each thesis render:
- thesis title/state;
- thesis statement;
- mechanism;
- anti-thesis;
- falsifiers with existing metric label/operator/threshold/explanation;
- confidence and next-check date when present.

Render thesis signal assessment separately as positive and negative evidence lists. Raw evidence IDs stay out of the body.

### ExpectationForecastBlock

Keep the two concepts distinct:
- `市场预期质量`
- `预测纪律`

Render existing quality state, source count/quality, age, post-event-consensus flag, and reasons when present. Render Forecast Discipline status/reason as-is. Do not create a directional expectation gap here.

### ExpectationGapBlock

Render existing market-vs-OS fields only when they exist. Missing consensus remains missing. Do not calculate magnitude, implied direction, or percentages from other fields.

### ValuationRationaleBlock

Render:
- candidate model label/status/score/reasons;
- selected/executed model;
- selection reason;
- scenario logic;
- display assumptions already provided by Composer.

Do not show raw lineage IDs. Do not rank or re-score models.

### ValuationBlock

Render supported valuation date/currency, Bear/Base/Bull values, primary range, current price, existing implied upside/downside, method results, sensitivities, and limitations. Omit absent fields instead of printing `None`.

### MonitoringBlock

Render existing next verification event, conviction-up conditions, thesis-broken conditions, and key metrics. The renderer never creates missing monitoring thresholds or conditions.

### StateProvenanceBlock

Render as a secondary `状态来源` table with:
`维度 | 状态 | 来源 | 方法`

Do not show evidence IDs.

### GapClassificationBlock

Keep four buckets separate:
- Evidence Missing → `证据缺口`
- Capability Missing → `能力缺口`
- Not Applicable → `不适用`
- Presentation/Deferred → `展示/延期项`

Do not turn a capability gap into a negative economic conclusion.

### LimitationBlock / EvidenceNoteBlock

Render limitations as bullets. Evidence note is concise prose. `EvidenceNoteBlock.evidence_ids` must not be emitted in the main body.

### Audit appendix

Render audit metadata only after a clear `审计附录` boundary. It may include repository, commit, OS/Core/Presenter/Composer/Renderer versions, plugin/module identities, evidence IDs, and assumption IDs because those are explicitly audit data. Primary report sections must remain free of raw IDs.

## Formatting invariants

The renderer must never emit:
- Python object repr (`SemanticValue(...)`, model reprs);
- raw dict/list repr as a substitute for presentation;
- JSON serialization as body prose;
- literal `None` for missing optional values;
- `block_type`;
- raw semantic `code` as the primary human-facing state;
- raw evidence or assumption IDs before the audit appendix;
- company-specific hard-coded names or ticker branches.

Markdown must end with exactly one newline and be deterministic for an identical input document.

## Cross-model acceptance patterns

### Manufacturing

The renderer must be capable of presenting positive and negative canonical signals side-by-side. It must not collapse mixed evidence into a generic positive narrative. Missing manufacturing professional questions remain gaps rather than invented backlog/utilization/yield facts.

### Distributor

Funding Loop content must remain prominent and numeric. Rapid growth can coexist with negative operating cash flow and debt-funded working-capital expansion. The renderer must not reinterpret factoring as debt and must not elevate PE merely because a PE model is present.

### Coverage-limited Hospitality

If the document contains no hotel KPIs, the renderer must not invent RevPAR, ADR, OCC, same-store, unit economics, or maturity curves. Lease-heavy limitations and missing-industry-plugin capability gaps must remain visible. Low owned PPE must not be rewritten as asset-light economics.

## Versioning

Target release:
- Research OS `1.5.7`
- `CORE_API_VERSION = 1.0`
- `professional-research-view@1.3.0` unchanged
- `research-report-composer@1.1.0` unchanged
- new `professional-markdown-renderer@1.0.0`
- `research_os_version.json.module_versions.report_renderer = "1.0.0"`

## Testing strategy

Use TDD with synthetic `ResearchReportDocument` fixtures. Permanent tests must cover:
- deterministic rendering;
- first-page decision snapshot;
- all typed block renderers;
- compact KPI table selection;
- semantic label rather than code;
- no `None`, raw dict repr, `block_type`, evidence IDs, or assumption IDs in primary body;
- raw provenance appears only after `审计附录`;
- Manufacturing mixed-signal display;
- Distributor funding-loop display;
- Hospitality no-fabrication behavior;
- renderer rejects inputs that are not `ResearchReportDocument`;
- release/version/gate consistency.

The Release Gate adds one renderer regression check and retains every historical gate.
