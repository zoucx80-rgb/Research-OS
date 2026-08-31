# Changelog

## 1.5.10 — 2026-08-31

### Added
Canonical v1.5.10 professional research-completeness contracts for financial time series, operating observations, cash-flow quality, consensus distributions, peer comparables, sensitivity cases, monitoring rules, verification calendars, prior-run review, and methodology disclosure; `research_completeness@1.0.0`; `professional-research-view@1.5.0`; `research-report-composer@1.3.0`; and `professional-markdown-renderer@1.2.0`.

### Changed
Field acceptance now requires three independent downstream checks: `presentation`, `research_depth`, and `research_completeness`. Completeness uses explicit dimension statuses `PASS`, `INCOMPLETE`, and `NOT_APPLICABLE`; required missing dimensions fail closed, while a dimension may be excluded only through explicit N/A declaration. The one-way research/presentation boundary remains unchanged, and reporting layers only carry already-produced canonical completeness artifacts forward.

### Fixed
Prevents polished reports from passing when material research dimensions are absent; prevents missing values from being turned into fabricated zeros or invented sections; preserves PIT-safe consensus inputs; distinguishes simplified operating-cash-flow-minus-capex presentation from FCFF; preserves comparable peer metadata; and keeps unsupported Hospitality specialization explicit instead of manufacturing hotel KPIs or lease-adjusted economics.

### Validation
Release Gate adds `research_completeness_contracts_v1_5_10`, `research_completeness_runtime_v1_5_10`, `research_completeness_reporting_v1_5_10`, `research_completeness_field_v1_5_10`, `research_completeness_patterns_v1_5_10`, and `release_contract_v1_5_10` while retaining every historical gate. CI preserves v1.5.08 and v1.5.09 replay and adds generic Manufacturing v1.5.10 field acceptance with Markdown/HTML/PDF artifacts and a fail-closed completeness manifest.

### Migration
No database or Alembic migration is required. See `docs/migrations/v1.5.10.md`.

### Compatibility
`CORE_API_VERSION` remains `1.0`; `financial_fact_snapshot@1.0.0`, `professional-html-renderer@1.0.0`, and `professional-pdf-adapter@1.0.0` remain unchanged. No Hospitality Plugin, lease-adjusted valuation engine, second Completion Gate, second Decision Engine, automatic trading logic, or company-specific Core logic is introduced.

## 1.5.9 — 2026-08-31

### Added
Read-only `FinancialFactSnapshot` (`financial_fact_snapshot@1.0.0`) for material PIT-safe filed financial facts already present in the canonical run; `professional-research-view@1.4.0`; `research-report-composer@1.2.0`; `professional-markdown-renderer@1.1.0`; and dual-status v1.5.09 field acceptance with independent `presentation` and `research_depth` results.

### Changed
Professional output remains strictly one-way: `ResearchRunResult → HumanReadableResearchView → ResearchReportDocument → MarkdownPresentationArtifact → HtmlPresentationArtifact → PdfPresentationArtifact`. The deeper Presenter/Composer/Markdown layers carry canonical financial facts and relationships forward without recomputing research semantics. Batch field acceptance is fail-closed: `overall_status=PASS` only when both presentation and research depth pass.

### Fixed
Prevents a visually valid HTML/PDF artifact from being accepted when professional research content is materially thin; preserves Distributor debt, factoring/receivable-transfer, financing-cost and working-capital semantics as distinct concepts; preserves lease-heavy Hospitality capability gaps without fabricated hotel KPIs or lease-adjusted economics; and isolates historical v1.5.08 fingerprints from the current package version.

### Validation
Release Gate adds `financial_fact_snapshot_v1_5_09`, `research_depth_semantics_v1_5_09`, `professional_output_depth_v1_5_09`, `dual_field_acceptance_v1_5_09`, `three_company_field_depth_v1_5_09`, and `release_contract_v1_5_09` while retaining every historical gate. CI runs real Chromium/PDF rendering for permanent Manufacturing, Distributor, and lease-heavy Hospitality/no-plugin fixtures and uploads both v1.5.08 replay and v1.5.09 acceptance artifacts.

### Migration
No database or Alembic migration is required. See `docs/migrations/v1.5.09.md`.

### Compatibility
`CORE_API_VERSION` remains `1.0`; HTML/PDF fingerprints remain `professional-html-renderer@1.0.0` and `professional-pdf-adapter@1.0.0`. No Hospitality Plugin, lease-adjusted valuation engine, second Completion Gate, second Decision Engine, Forecast/Evidence Quality rewrite, automatic trading logic, or company-specific Core logic is introduced.

## 1.5.8 — 2026-08-30

### Added
Immutable provenance-linked `MarkdownPresentationArtifact`, `HtmlPresentationArtifact`, and `PdfPresentationArtifact`; deterministic `ProfessionalHtmlRenderer` with fingerprint `professional-html-renderer@1.0.0`; professional A4 print CSS; and the optional `PlaywrightPdfAdapter` with fingerprint `professional-pdf-adapter@1.0.0`.

### Changed
The complete professional-output chain is now `ResearchRunResult → HumanReadableResearchView → ResearchReportDocument → MarkdownPresentationArtifact → HtmlPresentationArtifact → PdfPresentationArtifact`. Every presentation layer accepts only its immediate typed upstream artifact. Playwright/Chromium is isolated in the optional `pdf` extra and is not part of the Research Runtime dependency graph.

### Fixed
Prevents HTML/PDF publishing from becoming a second calculation path, bypassing canonical Markdown, leaking raw provenance into the investment body, filling missing expectation/valuation values, relabeling Factoring as Debt, or inventing Hospitality KPIs and lease-adjusted economics.

### Validation
Release Gate adds typed-artifact, strict-pipeline, dependency-boundary, cross-model, and real Playwright/Chromium PDF checks. A4 behavior covers first-page snapshot, repeated table headers, heading/page breaks, long-text wrapping, Chinese font fallbacks, grayscale readability, and a separately paginated Audit Appendix. Automated gates do not replace three-company rendered-PDF visual QA.

### Migration
No database or Alembic migration is required. Install `research-os[pdf]` and Chromium only where PDF export is needed. See `docs/migrations/v1.5.08.md`.

### Compatibility
`CORE_API_VERSION` remains `1.0`; `professional-research-view@1.3.0`, `research-report-composer@1.1.0`, and `professional-markdown-renderer@1.0.0` remain unchanged. No Hospitality Plugin, lease-adjusted valuation, Forecast/Evidence Quality rewrite, new Decision/Completion/Thesis engine, company-specific Core logic, or trading/portfolio/dashboard feature is introduced.

## 1.5.7 — 2026-08-30

### Added
Public `ResearchReportMarkdownRenderer` with fingerprint `professional-markdown-renderer@1.0.0`. It deterministically renders one canonical `ResearchReportDocument` into zh-CN Markdown with an investment-decision snapshot, typed research sections, monitoring, classified research gaps, limitations, and a separate audit appendix.

### Changed
The complete professional-output chain is now `ResearchRunResult → HumanReadableResearchView → ResearchReportComposer → ResearchReportDocument → ResearchReportMarkdownRenderer → Markdown`. The renderer is presentation-only: it selects and formats fields already present in the document and does not recalculate research semantics.

### Fixed
Prevents downstream report production from falling back to ad-hoc dictionary/Python-repr dumping. Raw evidence IDs, raw assumption IDs, repository/plugin/module metadata remain outside primary investment prose. Distributor financing/factoring semantics remain visible without relabeling factoring as debt, and lease-heavy Hospitality/no-plugin output remains capability-limited without fabricated RevPAR/ADR/OCC or lease-adjusted economics.

### Validation
Release Gate adds `markdown_renderer_v1_5_07` and `renderer_cross_model_v1_5_07` while retaining every historical gate. Permanent renderer regressions cover Manufacturing, Distributor, and lease-heavy Hospitality/no-plugin patterns in addition to deterministic/type-bound rendering and audit separation.

### Migration
No database or Alembic migration is required. See `docs/migrations/v1.5.07.md`.

### Compatibility
`CORE_API_VERSION` remains `1.0`; `professional-research-view@1.3.0` and `research-report-composer@1.1.0` remain unchanged. No HTML/CSS/PDF engine, Hospitality Plugin, lease-adjusted valuation engine, Forecast rewrite, automatic trading logic, or company-specific Core logic is introduced.

## 1.5.6 — 2026-08-30

### Added
Typed report-body blocks for Financial/Operating, Capital/Funding, Thesis Debate, Expectation/Forecast, Valuation Rationale, and State Provenance.

### Changed
`research-report-composer@1.1.0` now composes material canonical `HumanReadableResearchView` artifacts that v1.5.05 already projected, while remaining downstream and one-way. Financial Sanity/KPIs, Capital Efficiency/Funding Loop, Thesis/Anti-Thesis/Falsifiers, expectation quality/Forecast Discipline, valuation model fitness/execution, and state provenance can now enter the final report body when present. Raw evidence/assumption IDs remain outside primary investment prose.

### Fixed
Prevents final `ResearchReportDocument` from becoming materially thinner than the professional research view for Manufacturing and Distributor cases, while keeping coverage-limited Hospitality from receiving fabricated hotel KPIs or unsupported lease-adjusted economics.

### Validation
Release Gate adds `composition_coverage_v1_5_06` while retaining every historical gate. The new regression verifies body coverage, canonical-value preservation, raw-ID separation, view immutability, and Hospitality/no-plugin non-fabrication.

### Migration
No database or Alembic migration is required. See `docs/migrations/v1.5.06.md`.

### Compatibility
`CORE_API_VERSION` remains `1.0`; `professional-research-view@1.3.0` remains unchanged. No new research state engine, Hospitality Plugin, lease-adjusted valuation engine, Forecast rewrite, automatic trading logic, or company-specific Core logic is introduced.

## 1.5.5 — 2026-08-30

### Added
Structured `ExpectationGapResult` missingness/lineage, additive `ValuationResult` scenarios/ranges/sensitivities, `professional-research-view@1.3.0`, and `research-report-composer@1.0.0`. The composer adds a canonical first-page decision snapshot, deterministic causal bridges over existing valuation/Driver Graph edges, structured monitoring, gap classification, concise evidence-traceability notes, and an audit appendix for raw provenance.

### Changed
Full professional output now follows `ResearchRunResult → HumanReadableResearchView → ResearchReportComposer → ResearchReportDocument`. Material risks are deduplicated by canonical semantic code. Raw evidence/assumption IDs default to the audit appendix rather than the main body. CNY scaling is display-only and never changes machine values. Lease-heavy presentation explicitly surfaces missing lease-adjusted analysis without inferring light-asset or low-capital-intensity economics.

### Fixed
Missing consensus no longer produces a fabricated expectation gap; presentation does not derive valuation upside/downside merely from price and value fields; Composer does not invent causal edges or monitoring thresholds; evidence, capability, not-applicable, and presentation/deferred gaps remain distinct; repository/plugin/module metadata stays outside primary investment prose.

### Validation
Release Gate adds `report_composer_one_way`, `expectation_gap_missingness`, `valuation_result_contract`, `composition_dedup`, `lease_heavy_presentation_guard`, and `audit_metadata_separation`, while retaining every historical gate. Permanent synthetic reporting regressions cover Manufacturing, Distributor, and lease-heavy Hospitality/no-plugin patterns.

### Migration
No database or Alembic migration is required. Existing machine consumers may continue using canonical `ResearchRunResult`; complete v1.5.05 professional output should pass through `ResearchViewPresenter` and `ResearchReportComposer`. See `docs/migrations/v1.5.05.md`.

### Compatibility
`CORE_API_VERSION` remains `1.0`. No Hospitality Plugin, lease-adjusted valuation engine, second Completion Gate, second Decision Engine, Forecast rewrite, automatic trading logic, or company-specific Core logic is introduced.

## 1.5.4 — 2026-08-30

### Fixed
Financial Sanity now accepts ordinary filing YoY rounding to two decimal percentage points without accepting a materially different growth rate. Thesis falsifiers resolve `cfo`, `ocf`, and `operating_cash_flow` consistently, newly emit canonical `ocf`, and financing theses retain only supporting-driver evidence. Reported book-equity change no longer implies external equity financing or dilution. Incremental capital/funding ratios require explicit comparable-period bases. Distributor PE fitness is constrained when the canonical Funding Loop is debt-funded with negative OCF.

### Added
Additive comparison-basis diagnostics for Capital Efficiency, Funding Loop and Distributor KPIs; explicit `external_equity_financing` / `equity_dilution` fact semantics; routed-valuation reason codes; and one-way human-readable projections for Financial Sanity, Capital Efficiency, Forecast Discipline and the canonical next verification event.

### Changed
The Distributor Pack is `distributor@1.3.0`, built-in Distributor Plugin is `1.2.0`, professional Driver/Thesis module is `1.3.0`, and the complete presentation fingerprint is `professional-research-view@1.2.0`. Presentation distinguishes process-validation status from economic health.

### Validation
Release Gate adds `reported_yoy_rounding`, `canonical_ocf_falsifier`, `explicit_equity_financing`, `delta_comparison_basis`, `funding_aware_pe_fitness`, and `material_artifact_projection`, while retaining every historical gate.

### Migration
No database or Alembic migration is required. Delta-ratio callers must provide matching `<fact>_comparison_basis` facts. `delta_equity` is now informational; provide explicit `external_equity_financing` and `equity_dilution` where evidenced. See `docs/migrations/v1.5.04.md`.

### Compatibility
`CORE_API_VERSION` remains `1.0`. New model fields are additive. Conservative missing results replace v1.5.03 outputs only where period or financing semantics were ambiguous. No Hospitality Plugin, lease-adjusted valuation framework, Forecast rewrite, second Completion Gate, second Decision Engine, or company-specific Core logic is added.

## 1.5.3 — 2026-08-30

### Added
State Provenance for high-level fundamental, valuation and expectation states; structured professional-question coverage with capability/evidence requirements; event-relative consensus freshness; quantitative display semantics with formatted value, unit and reporting-period context; valuation-execution and assumption-lineage fields in the professional research view; and explicit factoring / receivable-transfer / working-capital-financing exposure metrics for distributor research.

### Changed
`BusinessModelRouter` is now `router@1.2.0` and suppresses the low-PPE distributor heuristic when right-of-use assets or lease liabilities show a lease-heavy operating model. Driver lineage is fact-specific rather than attaching the complete run evidence set to every node. Manufacturing Driver Graphs use available revenue, margin, working-capital, capex and cash evidence instead of the generic Revenue/Margin/FCF-only graph. The thesis engine no longer defaults to `Fundamentals improve`; directional evidence determines whether operating evidence is improving, mixed, weakening or insufficient. Complete human-facing research now uses `professional-research-view@1.1.0`. Built-in Manufacturing and Distributor plugin manifests are `1.1.0`.

### Fixed
Prevents analyst-supplied high-level states from being narrated as Research OS-derived conclusions. Prevents mixed manufacturing evidence from producing an unsupported positive thesis. Prevents lease-heavy hotels, retailers and similar operators from receiving a distributor signal solely because owned PPE is low. Prevents a calendar-fresh consensus that predates a material new disclosure from being treated as information-fresh. Prevents professional-looking plugin questions from being mistaken for answered professional coverage. Preserves factoring and receivable-transfer exposures as economic financing information without automatically relabeling them as debt.

### Validation
Release Gate adds `state_provenance`, `driver_specific_lineage`, `evidence_driven_thesis`, `professional_question_coverage`, `event_relative_expectations`, `lease_aware_router`, `working_capital_financing_exposure`, and `quantitative_presentation_semantics`, while retaining all v1.5.02, v1.5.01, v1.4 and earlier correctness gates.

### Migration
No database or Alembic migration is required. Existing machine integrations may continue consuming canonical `ResearchRunResult` and `DecisionSummary`; complete human-facing research should use `ResearchViewPresenter`. See `docs/migrations/v1.5.03.md`.

### Compatibility
`CORE_API_VERSION` remains `1.0`. `ResearchCompletionGate` remains the sole source of `COMPLETE` / `INCOMPLETE`; no second decision or completion system is introduced. v1.5.03 deliberately does not add a full Hospitality Plugin, comprehensive lease-adjusted valuation, or a Forecast subsystem rewrite.

## 1.5.2 — 2026-08-30

### Added
`ResearchViewPresenter` / `HumanReadableResearchView` provide a one-way human-readable zh-CN projection of the canonical `ResearchRunResult`, covering business-model classification, plugin selection, Coverage Gaps, KPI metrics, Funding Loop, Driver Graph, Thesis artifacts, expectation quality, valuation routing and the existing decision/completion summary. Built-in Manufacturing and Distributor plugins now provide structured report contributions. Expectation quality now uses the existing consensus source-count, source-quality and vintage-age metadata.

### Changed
Canonical industry execution now follows the primary business model only; secondary business models remain classification and coverage metadata so their plugins cannot contaminate the primary KPI / Driver / Thesis chain. `BusinessModelModule` reports PASS only for a classified business model. Coverage-limited generic Driver Graphs remain visible but no longer produce an active Thesis or a false Driver Graph PASS. Severe debt-funded negative-OCF Funding Loops now populate the existing decision material-risk input. The default report version is `semantic-research-view@1.0.0` and the driver model fingerprint is `core:driver-thesis@1.1.0`.

### Fixed
Prevents unsupported primary industries from receiving a generic active Thesis that looks like specialized research. Prevents secondary industry packs from mixing into the primary KPI set. Prevents the completion aggregation layer from converting a coverage-limited fallback Driver Graph into PASS merely because a graph object exists. Prevents severe working-capital debt funding from being understated by the decision layer when canonical Funding Loop evidence already indicates material financing risk.

### Validation
Release Gate adds `business_model_status_truth`, `coverage_aware_thesis`, `funding_material_risk`, `expectation_quality`, `industry_report_contributions`, `primary_industry_isolation`, `end_to_end_research_view`, and `coverage_limited_completion` while retaining all v1.5.01, v1.4 and earlier correctness gates.

### Migration
No database or Alembic migration is required. Existing machine integrations may continue consuming `ResearchRunResult` and `DecisionSummary`; complete human-facing research should use `ResearchViewPresenter`. See `docs/migrations/v1.5.02.md`.

### Compatibility
`CORE_API_VERSION` remains `1.0`. `ResearchRunResult`, `ResearchCompletionGate`, snapshot architecture, legal decision-state set, Router v1.5.01 period semantics and historical snapshot behavior remain compatible. v1.5.02 does not add a Hospitality plugin or company-specific Core logic.

## 1.5.1 — 2026-08-30

### Added
Business-model classification semantics that distinguish successful classification, unsupported taxonomy, and insufficient evidence; `hospitality` as a representable standard business-model taxonomy; structured CoverageGap metadata (`reason_code`, `affected_capabilities`, `fallback_available`); and `DecisionSummaryPresenter` / `HumanReadableDecisionSummary` for canonical zh-CN human-facing presentation.

### Changed
`BusinessModelRouter` is now `router@1.1.0`. Its period-sensitive `inventory_to_revenue` feature only contributes when its Evidence period is explicitly annual, preventing interim balance/flow ratios from silently biasing cross-company classification. `StrategyResolver` now distinguishes business-model taxonomy/evidence gaps from the normal case of a represented business model lacking an industry plugin. The default report version is `semantic-report@1.0.0`.

### Fixed
Prevents `unknown` business-model output from collapsing unsupported taxonomy and missing evidence into the same misleading industry-plugin gap. Prevents internal enum/reason-code strings from being the primary human-facing research conclusion by introducing an explicit machine-code → zh-CN label → zh-CN explanation contract. The presenter preserves raw codes only as technical metadata and does not recalculate research states.

### Validation
Release Gate adds `router_period_semantics`, `business_model_gap_semantics`, `human_readable_reporting`, and `presentation_single_source`. CI continues to run architecture contracts before correctness regressions, storage migration smoke, the full suite, and the release gate.

### Migration
No database or Alembic migration is required. Existing `BusinessModelProfile`, `CoverageGap`, and `ExtensionRequest` construction remains backward compatible because new fields have defaults. Human-facing clients may use `DecisionSummaryPresenter`; machine integrations may continue consuming canonical `DecisionSummary` and `ResearchRunResult`. See `docs/migrations/v1.5.01.md`.

### Compatibility
`CORE_API_VERSION` remains `1.0`. `ResearchRunResult`, `ResearchCompletionGate`, the canonical decision state, snapshot architecture, Distributor Pack, Funding Loop engine, and v1.4 plugin/runtime boundaries are unchanged. v1.5.01 does not add a hotel strategy plugin or company-specific research logic.

## 1.4.0 — 2026-08-30

### Added
A canonical run-scoped `ResearchRuntime` / `ResearchRuntimeFactory` execution boundary; immutable `ResearchInputs`; one public `ResearchRunResult`; versioned industry and methodology plugin manifests; compatibility-aware `PluginRegistry`; deterministic `StrategyResolver`; `PluginProvider` extension point; explicit `CoverageGap` and extension-request contracts; PIT-safe knowledge-provider interface; component fingerprints in frozen snapshots; and architecture regression coverage for third-party synthetic plugin extensibility.

### Changed
Research composition policy now lives in `ResearchRuntime`, while `ResearchEngine` only executes capability dependencies and has no company, industry, or plugin identifiers. Plugin registries and module instances are rebuilt per run. Stable plugins are eligible for automatic resolution and experimental plugins require explicit opt-in. Reporting now accepts canonical `ResearchRunResult` only and obtains completion fields from the runtime's `ResearchCompletionResult`. Decision records retain optional decision-context fields so reporting remains self-contained without a parallel input dictionary.

### Removed
The legacy `src/research_os/orchestration.py` policy entry point and the duplicate KPI registry/facade were removed. No replacement compatibility surface is allowed to redefine execution, KPI applicability, or completion policy.

### Validation
CI now runs architecture contracts before correctness regressions, storage migration smoke, the full test suite, and the release gate. The release gate adds 18 v1.4 architecture checks covering ResearchContext, ResearchInputs, module contracts, dependency resolution, plugin manifest/compatibility/resolution, coverage gaps, plugin failure isolation, canonical runtime/result, knowledge PIT, component fingerprints, completion single-source behavior, Core API consistency, extensibility without engine changes, and absence of duplicate legacy runtime policy.

### Migration
No new database or Alembic migration is required. Existing callers should migrate from the deleted legacy orchestrator to `ResearchRuntimeFactory`, and reporting callers should pass `ResearchRunResult` rather than an arbitrary dictionary. Custom strategy extensions should use the `PluginProvider` / `PluginManifest` contracts. See `docs/migrations/v1.4.0.md` and `docs/architecture/plugin-authoring-v1.md`.

### Compatibility
`CORE_API_VERSION` remains `1.0`. v1.2.1 period, missing-value, KPI-applicability, funding-loop, completion, PIT, evidence-lineage, valuation-safety, and decision-safety semantics remain enforced. Existing historical release tags and versioned research snapshots remain immutable.

## 1.2.1 — 2026-08-29

### Fixed
Interim balance/flow KPIs now use explicit reporting-period semantics instead of silently assuming 365 days. Missing funding facts remain missing rather than being coerced to zero. A generic CorePack no longer counts as specialized KPI support for an unsupported routed business model. Reporting now propagates the authoritative `ResearchCompletionResult` instead of applying a second completion policy. Runtime and public version surfaces now share one `RESEARCH_OS_VERSION` source.

### Changed
Distributor and Manufacturing period-sensitive metrics share one period contract. Distributor inventory turnover exposes both period turns and annualized turns where the reporting period is known. Funding-loop classification can return `unknown`, which maps to `INSUFFICIENT_EVIDENCE`. KPI Pack completion requires specialized support for the routed primary model. Claim capabilities are normalized before completion-policy evaluation so expectation, valuation and decision claims are not conflated.

### Validation
Release Gate adds five v1.2.1 semantic checks: `period_semantics`, `missing_value_semantics`, `kpi_applicability`, `completion_consistency`, and `version_consistency`. CI runs an anonymous cross-cutting v1.2.1 regression before migration smoke, the full suite and the release gate.

### Migration
No database or Alembic migration is required for v1.2.1. The reversible v1.2 Evidence-lineage migration remains the current schema baseline. Historical tags and versioned research snapshots remain immutable.

### Compatibility
This is a PATCH release. Existing v1.2 request shapes remain accepted, including `facts: dict`, optional `safety=None`, and free-text claimed conclusions. Missing or unsupported evidence may now correctly produce `INSUFFICIENT_EVIDENCE` where older behavior could produce a false PASS.

## 1.2.0 — 2026-08-29

### Added
Repository identity preflight contracts; persistent raw/normalized Evidence lineage; calculation and assumption lineage contracts; financial sanity validation; expectation-evidence validation; valuation execution/driver-bridge validation; explicit decision-state validation; research completion and temporal-consistency gates; distributor safety KPIs; completion-aware reporting; and reversible Evidence-lineage schema migration `0003_v1_2_evidence_lineage`.

### Changed
`ResearchOS.complete_run()` now composes safety gates in causal order so hard prerequisite failures cannot silently flow into valuation, decision, or a completed report. `DecisionSummary` carries machine-readable `final_status`, decision state, expectation-evidence status, and valuation-execution status. Research OS public version metadata is now `1.2.0`.

### Fixed
Prevents placeholder repository fingerprints, financial unit/scale corruption, unsupported expectation-gap claims, selected/executed valuation model mismatch, illegal decision states such as `NEUTRAL`, stale next-verification events, tool-completion being mistaken for research-completion, and loss of raw/normalized Evidence lineage during database round trips.

### Validation
Release Gate now includes repository preflight, evidence lineage, financial sanity, expectation evidence, valuation execution, decision validation, completion, temporal consistency, distributor KPI safety, complete-run integration, and reversible v1.2 lineage migration checks in addition to existing PIT/golden/regression coverage.

### Migration
See `docs/migrations/v1.1-to-v1.2.md`. Historical snapshots and the `v1.1.0` tag remain immutable.

### Compatibility
The release is additive. Existing v1.1 research-domain APIs remain available; callers that do not provide the new safety context are not silently promoted to `FINAL_STATUS=COMPLETE`. Missing evidence remains `INSUFFICIENT_EVIDENCE` rather than being fabricated for narrative completeness.

## 1.1.0 — 2026-08-29

### Added
Business Model Router, KPI Pack Registry, Distributor Pack, Capital Efficiency/Funding Loop, Driver Graph, Thesis/Falsifier Engine, Evidence Ledger, PIT Consensus Vintage, Expectation Surprise, Forecast Model Promotion, Valuation Fitness Router, Decision Engine, Event Engine, Peer Normalization, Research Post-Mortem, Drift Detection, Calibration, Decision Summary, read-only API.

### Changed
Manufacturing-specific research logic is now a versioned Manufacturing Pack instead of a global default. Automated reporting is downstream of research semantics and evidence validation.

### Deprecated
Implicit assumption that every A-share company should run the manufacturing KPI set.

### Removed
No v1.0 historical facts or research snapshots are removed.

### Fixed
Explicitly separates information availability from economic period and prevents low-fitness valuation models from dominating the primary valuation set.

### Validation
PIT no-lookahead, immutable revisions, manufacturing golden regression, distributor complete run, thesis falsifier, valuation fitness, decision-no-trade and snapshot reproducibility gates.

### Migration
See `docs/migrations/v1.0-to-v1.1.md`.

### Known Limitations
The v1.1 router is deterministic and explainable rather than ML-based. Probability calibration is optional and only applies to explicit probability forecasts. Source ingestion connectors and licensed commercial datasets are deployment integrations, not bundled data feeds.