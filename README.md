# Research OS v1.5.08

Research OS v1.5.08 (code SemVer `1.5.8`) is a Point-in-Time, evidence-linked investment research operating system built around one canonical, extensible runtime. This PATCH release preserves v1.5.05-v1.5.07 research/composition/Markdown semantics and adds a provenance-linked professional HTML/PDF presentation pipeline. The canonical extensible runtime introduced in `1.4.0` remains the architectural baseline.

## Core invariants

- No time travel: only evidence with `publish_ts <= decision_ts` may enter a run.
- No fabricated data: missing facts remain missing; `None` is never silently treated as economic zero.
- Facts, calculations, statistical evidence, analyst assumptions, and derived states remain distinct.
- Material metrics and conclusions retain evidence lineage and version metadata.
- Period-sensitive balance/flow metrics require truthful reporting-period semantics.
- Generic infrastructure is not specialized industry coverage.
- Missing professional coverage cannot be filled by narrative confidence.
- Funding-loop classification requires evidenced operands.
- Market-expectation claims require traceable and event-aware expectation evidence.
- Decision states are research outputs, never automatic trade orders.
- `ResearchCompletionGate` is the single authority for `COMPLETE` / `INCOMPLETE`.
- Reporting consumes canonical research state and cannot redefine completion or decision semantics.
- Human-facing presentation translates, composes, and renders canonical machine semantics without changing them.

## Canonical runtime

```text
ResearchContext + ResearchInputs
        ↓
ResearchRuntimeFactory
        ↓
ResearchRuntime
        ↓
ResearchEngine + run-scoped PluginRegistry
        ↓
ResearchRunResult + Snapshot
```

`ResearchRuntime` owns composition policy, completion evaluation, component fingerprinting, report contributions, and snapshot freezing. `ResearchEngine` executes capability dependencies only and remains unaware of company or industry identities.

## Business-model routing and strategy isolation

`BusinessModelRouter` is `router@1.2.0`. Period-sensitive `inventory_to_revenue` evidence contributes only when its Evidence period is explicitly annual. Lease-heavy operating models suppress the low-PPE distributor heuristic when right-of-use assets or lease liabilities are economically material. The standard taxonomy includes `hospitality` without pretending that a Hospitality strategy plugin exists.

`BusinessModelProfile.classification_status` distinguishes `classified`, `unsupported_taxonomy`, and `insufficient_evidence`. Canonical industry execution follows the **primary business model only**. Secondary models remain classification and coverage metadata and do not contaminate the primary KPI / Driver / Thesis chain.

## Coverage-aware professional research

When the primary model has no compatible industry strategy plugin, the Coverage Gap remains explicit; a generic Driver Graph may be produced only as an informational fallback; no active specialized Thesis or Claim is generated; and the final completion state continues to come only from `ResearchCompletionGate`.

v1.5.03 added structured professional-question coverage. Industry contributions can declare required capabilities and evidence keys, and the runtime records whether each question is supported or blocked by missing capability/evidence. Asking a professional-looking question is not treated as professional coverage by itself.

v1.5.05 report composition keeps **evidence missing**, **capability missing**, **not applicable**, and **presentation/deferred** limitations distinct instead of collapsing them into one generic gap list.

## State Provenance

High-level fundamental, valuation, and expectation states carry explicit provenance. Legacy string inputs remain compatible but are identified as **analyst assumptions** rather than being narrated as Research OS-derived conclusions. Structured state inputs can identify derived, analyst-assumption, external-model, or manual-override sources together with supporting evidence and method metadata.

## Evidence-driven Thesis and Driver lineage

The built-in thesis engine does not default to `Fundamentals improve`. Directional operating signals determine whether evidence is improving, mixed, weakening, or insufficient before a thesis is formed. Driver nodes carry fact-specific evidence IDs rather than inheriting the complete run evidence set.

Manufacturing Driver Graphs can include supported revenue, margin, receivables, inventory, capex, and cash-generation nodes. Missing order, capacity, utilization, yield, qualification, or product-mix evidence remains an explicit question-level coverage gap rather than being fabricated.

## Funding-loop and economic exposure integrity

Severe Funding Loop evidence continues to feed the existing `DecisionContext.material_risk` boundary. Distributor analytics additionally expose factoring, derecognized receivables, receivable transfers, other working-capital financing, and total financing burden relative to gross profit. These exposures remain economically visible without being automatically relabeled as debt.

v1.5.04 requires explicit matching `<fact>_comparison_basis` values before delta facts form incremental ratios. Reported book-equity change (`delta_equity`) is informational; only explicit `external_equity_financing` drives equity-funding math, and only `equity_dilution=True` emits dilution risk. Missing or mismatched semantics remain missing rather than becoming professional-looking ratios.

## Field-correctness hardening

- filing YoY values rounded to two decimal percentage points pass ordinary financial-sanity validation while material discrepancies still fail;
- `cfo`, `ocf`, and `operating_cash_flow` are canonical aliases for falsifier evaluation, and new theses emit `ocf`;
- financing theses cite the evidence attached to their actual working-capital/financing drivers rather than the complete evidence set;
- a distributor PE route is penalized when the canonical Funding Loop is debt-funded with negative operating cash flow;
- no separate risk, decision or completion engine is introduced.

## Expectation gap and valuation result contracts

v1.5.05 adds structured expectation-gap and valuation-output contracts without weakening missing-value discipline.

- Missing consensus produces no fabricated expectation gap.
- Thin, stale, or pre-event consensus retains an explicit qualification.
- Directional expectation gaps do not invent numeric magnitude.
- `ValuationResult` can carry explicit Bear/Base/Bull cases, primary ranges, per-share values, sensitivities, evidence and assumption lineage.
- Presentation does not derive upside/downside merely because current price and a valuation estimate are present.

Expectation quality continues to use `ConsensusVintage.source_count`, `source_quality`, calendar age, and event-relative freshness.

## Professional human-readable research, composition, and Markdown rendering

Complete human-facing research uses:

```python
from research_os.reporting import (
    ResearchReportComposer,
    ResearchReportMarkdownRenderer,
    ResearchViewPresenter,
)

view = ResearchViewPresenter().build(result, locale="zh-CN")
document = ResearchReportComposer().compose(view)
markdown = ResearchReportMarkdownRenderer().render(document)
```

Typed HTML/PDF output uses the optional presentation pipeline:

```python
from research_os.presentation import ProfessionalPresentationPipeline

bundle = ProfessionalPresentationPipeline().render(document)
markdown_artifact = bundle.markdown
html_artifact = bundle.html
pdf_artifact = bundle.pdf
```

The canonical direction is strictly one-way:

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
MarkdownPresentationArtifact
    ↓
HtmlPresentationArtifact
    ↓
PdfPresentationArtifact
```

For v1.5.07 the full presenter fingerprint remains `professional-research-view@1.3.0`, the report-composition fingerprint remains `research-report-composer@1.1.0`, and the Markdown renderer fingerprint is `professional-markdown-renderer@1.0.0`. Historical v1.5.05 reporting remains associated with `research-report-composer@1.0.0`, and historical v1.5.04 research remains associated with `professional-research-view@1.2.0`.

For v1.5.08 those three fingerprints remain unchanged. The new downstream fingerprints are `professional-html-renderer@1.0.0` and `professional-pdf-adapter@1.0.0`. Playwright is an optional PDF dependency and is not imported by Research Runtime or reporting composition.

`HumanReadableResearchView` remains a read-only projection of canonical research artifacts. `ResearchReportComposer` accepts that view only; it does not accept a raw dictionary as an alternate semantic path and does not calculate or alter completion, decision, thesis, fundamental, expectation, valuation, funding, forecast, or business-model state.

The v1.5.05 composer established the first-page decision snapshot, semantic risk deduplication, deterministic causal bridges, monitoring, structured gaps, concise evidence notes, audit separation, display-only CNY scaling, and lease-heavy presentation safeguards.

v1.5.06 extends **composition coverage only**. When already present in `HumanReadableResearchView`, the report body includes:

- Financial Sanity and KPI metrics under `财务与经营表现`;
- Capital Efficiency and Funding Loop under `资本效率与融资循环`;
- Thesis / Anti-Thesis / Falsifiers and thesis-signal assessment under `投资逻辑与反证`;
- expectation quality and Forecast Discipline under `市场预期与预测纪律`;
- valuation model fitness and valuation execution under `估值方法与适用性`;
- canonical state provenance under `状态来源`.

v1.5.07 adds **presentation rendering only**. `ResearchReportMarkdownRenderer` accepts `ResearchReportDocument` and deterministically renders headings, tables, supported fields, monitoring conditions, classified gaps, limitations, and an audit appendix. It does not accept `ResearchRunResult`, `HumanReadableResearchView`, or arbitrary dictionaries; it does not recalculate KPI, state, thesis, Funding Loop, expectation, forecast, valuation, decision, completion, or monitoring thresholds.

v1.5.08 adds **HTML/PDF layout and export only**. Each layer accepts only its immediate typed upstream artifact, preserves an auditable SHA-256 chain, and does not fill missing values or reinterpret research semantics. A4 CSS provides print pagination, repeated table headers, Chinese font fallbacks, long-text wrapping, grayscale readability, and a separate Audit Appendix.

Raw evidence IDs, assumption IDs, repository/plugin/module metadata remain in the audit appendix rather than primary investment prose. Distributor factoring remains an economic financing exposure without being relabeled as debt. A coverage-limited Hospitality company without a compatible strategy plugin still does not receive fabricated RevPAR, ADR, OCC, same-store or lease-adjusted economics.

KPI display semantics continue to include formatted values, display units, period labels, period days, and annualization flags. Machine values remain unchanged for auditability.

`DecisionSummaryPresenter` / `semantic-report@1.0.0` remains available for compatibility.

## Repository map

- `src/research_os/runtime/` — canonical context, inputs, provenance, module graph, runtime, result, fingerprints and snapshots.
- `src/research_os/plugins/` — plugin manifests, registry, resolver, built-ins and extension protocols.
- `src/research_os/knowledge/` — PIT-aware knowledge-provider interface.
- `src/research_os/preflight/` — exact repository identity and frozen-HEAD validation.
- `src/research_os/domain/` — Evidence and lineage contracts.
- `src/research_os/validation/` — financial sanity validation.
- `src/research_os/period/` — reporting-period semantics.
- `src/research_os/completion/` — the single research completion policy.
- `src/research_os/router/` — business-model classification.
- `src/research_os/kpi/` — built-in KPI packs.
- `src/research_os/capital/` — capital efficiency, Funding Loop, and economic financing exposure.
- `src/research_os/drivers/` — Driver Graph, coverage scope, and driver-specific lineage.
- `src/research_os/thesis/` — evidence-driven Thesis / Anti-Thesis / Falsifiers.
- `src/research_os/expectations/` — expectation vintages, validation, quality, and structured expectation gaps.
- `src/research_os/valuation/` — model fitness, routing, execution validation, and additive valuation results.
- `src/research_os/decision/` — deterministic research decision-state engine.
- `src/research_os/reporting/` — semantic projection, report composition/document types, `ResearchReportMarkdownRenderer`, display formatting, and audit separation.
- `src/research_os/presentation/` — typed Markdown/HTML/PDF artifacts, deterministic HTML/A4 CSS, strict pipeline, and optional Playwright PDF adapter.
- `src/research_os/version.py` — `RESEARCH_OS_VERSION` and `CORE_API_VERSION`.

## Local verification

```bash
python -m pip install -e . --no-deps --no-build-isolation

pytest -q \
  tests/unit/runtime \
  tests/unit/plugins \
  tests/unit/knowledge \
  tests/integration/runtime \
  tests/regression/architecture

pytest -q \
  tests/regression/research_patterns/test_v1_2_1_correctness_patterns.py \
  tests/unit/kpi/test_period_sensitive_packs.py \
  tests/unit/capital/test_engine.py \
  tests/unit/kpi/test_applicability.py \
  tests/unit/completion/test_consistency.py \
  tests/unit/test_version_consistency_v1_2_1.py

pytest -q tests/integration/storage/test_v1_2_lineage_migration.py
pytest -q tests/unit/reporting tests/unit/expectations tests/unit/valuation
pytest -q tests/regression/architecture tests/regression/research_patterns/test_v1_5_05_reporting_patterns.py
pytest -q tests/regression/architecture tests/unit/reporting/test_composition_coverage_v1_5_06.py
pytest -q tests/unit/reporting/test_markdown_renderer.py tests/regression/research_patterns/test_v1_5_07_renderer_patterns.py
RESEARCH_OS_RUN_PDF_INTEGRATION=1 pytest -q tests/unit/presentation tests/integration/presentation tests/regression/research_patterns/test_v1_5_08_presentation_patterns.py
pytest -q
python scripts/release_gate_v1_1.py
```

CI enforces architecture contracts, correctness regressions, storage migration smoke, reporting/expectation/valuation regressions, v1.5.05 cross-model reporting safeguards, v1.5.06 composition coverage, v1.5.07 Markdown regressions, v1.5.08 typed HTML/PDF and real Chromium regressions, the full suite, and the release gate.

## Version governance

`RESEARCH_OS_VERSION = "1.5.8"` and `CORE_API_VERSION = "1.0"`. Package metadata, public version metadata, plugin versions, presenter/composer/renderer fingerprints, and runtime component fingerprints must agree.

Snapshots separately freeze dataset, parser, formula, router, KPI pack, driver, forecast, valuation, report and OS versions plus payload hash and component fingerprints. Historical release tags and snapshots remain immutable.

## Migration and deferred scope

No database or Alembic migration is required for v1.5.08. Existing machine/Markdown integrations remain compatible; HTML/PDF consumers install `research-os[pdf]`, install Chromium, and use the strict typed presentation pipeline.

v1.5.08 deliberately does not add a full Hospitality Plugin, lease-adjusted valuation, a second generic-financial Decision state machine, a second Completion Gate, a Forecast/Evidence Quality rewrite, automatic trading logic, company-specific Core logic, or a second PDF backend.

See `docs/migrations/v1.5.08.md`, `docs/migrations/v1.5.07.md`, `docs/migrations/v1.5.06.md`, `docs/migrations/v1.5.05.md`, `docs/migrations/v1.5.04.md`, `docs/migrations/v1.5.03.md`, `docs/migrations/v1.5.02.md`, `docs/migrations/v1.5.01.md`, `docs/architecture/plugin-authoring-v1.md`, `CHANGELOG.md`, and the v1.5.08 design/implementation plan under `docs/superpowers/`.
