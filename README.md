# Research OS v1.6.0

Research OS is a Point-in-Time, evidence-linked investment research operating system. v1.6.0 is the clean-break architecture release for **Core API 2.0**, **Plugin API 2.0**, **Snapshot Schema 2.0**, and read-only **HTTP API v1**.

The current package contains only the v2 runtime contracts. Historical v1.5 releases are reproduced by commit-addressed **historical replay** in their own detached worktrees and environments; current v1.6 code does not import or emulate a v1 runtime.

## Core invariants

- **No Time Travel** — material evidence must satisfy `publish_ts <= decision_ts`.
- **No Fabricated Data** — missing facts remain missing; `None` is never silently treated as economic zero.
- **Facts ≠ Calculations ≠ Statistical Evidence ≠ Assumptions**.
- **Everything Has Lineage** — material artifacts preserve evidence or explicit assumption lineage.
- **Models Beat Simple Benchmarks** before promotion.
- **Research Signal ≠ Auto Trading**.
- Completion and Readiness are independent machine contracts; a polished report cannot convert incomplete research into complete research.
- Presentation is downstream-only and never recalculates research semantics.

## v1.6 architecture

A current research run is strictly staged:

```text
ResearchRunCommand
    ↓
Repository Preflight
    ↓
Bootstrap Plan
    ├─ PIT Evidence
    ├─ Financial Fact Snapshot
    └─ Business Model Profile
    ↓
Strategy Resolution (Plugin API 2.0)
    ↓
Professional Module Plan
    ↓
ResearchEngine
    ↓
Completion + Readiness
    ↓
ResearchRunResult
    ↓
Snapshot Schema 2.0 (optional persistence)
```

`ResearchEngine` is the sole module invoker. Modules communicate through typed `ArtifactKey` / `ArtifactEnvelope` contracts. `ResearchApplication` owns orchestration, preflight, plugin resolution, version identity, component fingerprints, finalization, and optional persistence.

### Frozen public contracts

- **Core API 2.0** — typed commands, contexts, artifacts, execution result, Completion and Readiness.
- **Plugin API 2.0** — `PluginManifest`, applicability/support assessment, typed services, explicit compatibility ranges.
- **Snapshot Schema 2.0** — canonical research digest plus separate integrity digest; operational persistence controls do not alter research semantics.
- **HTTP API v1** — read-only run, artifact, snapshot, research-view, list and health endpoints. Query paths consume verified persisted snapshots and fail closed on tampering.

See:

- `docs/architecture/core-api-v2.md`
- `docs/architecture/plugin-authoring-v2.md`
- `docs/migrations/v1.6.0.md`
- `docs/architecture/adr-0002-v1-6-0-controlled-breaking-contract-upgrade.md`

## Plugin model

Industry and methodology plugins are orthogonal. Normal runs resolve compatible plugins automatically from the PIT business-model profile. Overrides require explicit rationale; experimental plugins require explicit opt-in.

A plugin declares its API and Research OS compatibility in `PluginManifest`. Its declared `service_capabilities` must exactly match the services it returns. Missing specialized coverage remains a typed coverage limitation; generic infrastructure must not masquerade as industry expertise.

## Professional research foundations

v1.6 retains explicit typed domains for, among others:

- financial time series and operating evidence;
- KPI packs and business-model routing;
- capital efficiency, Funding Loop and cash-flow quality;
- Driver Graph;
- Thesis / Anti-Thesis / Falsifiers and semantic claims;
- market expectations and Expectation Gap;
- forecast evidence and benchmark discipline;
- valuation fitness, execution and reconciliation;
- monitoring, prior-run review and next verification events;
- Research Decision State;
- Completion and Research Readiness.

Unavailable evidence is represented as `INSUFFICIENT_EVIDENCE`, `NOT_APPLICABLE`, a coverage gap, or another explicit typed state. It is never filled to make the report look complete.

## Reporting and presentation

The current v1.6 reporting direction is strictly one-way:

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

`HumanReadableResearchView`, `ResearchReportDocument`, Markdown, HTML and PDF carry the same research semantics forward. The reporting/presentation layers may translate, organize, style, paginate and export, but may not recompute KPI, Funding Loop, Driver/Thesis, Expectation Gap, Forecast, Valuation, Decision, Completion, Readiness, sensitivity or monitoring meaning.

`SemanticPreservationValidator` verifies artifact identity, lineage, payload fingerprints, reporting-chain semantic fingerprint, and required sensitivity/monitoring qualifiers.

PDF acceptance uses a real Playwright Chromium render, not a serialization substitute.

## Historical replay

Historical releases are immutable execution targets, not compatibility code inside v1.6.

The replay registry pins the supported field releases to exact commits:

- v1.5.08 — `f7863e0b0aeb657ac19b0a63761788d40118e6bf`
- v1.5.09 — `a3e82b3cc80b871b559ac9f5cd29e18e97b8e98d`
- v1.5.10 — `05a3ba99edc02ac93ee9fdf1130485da7e6fa8ab`
- v1.5.11 — `5067e4decb673a39cb96085e34a3a555fe24d58e`
- v1.5.12 — `72ab06c619678b35c31cf7edef7547849e803d16`

Each replay uses a detached worktree, a dedicated virtualenv, sanitized import environment and the historical release's own runner/fixtures. Artifacts are staged and published only after successful execution. The v1.5.08 Playwright cleanup compatibility is bounded by exact commit and exact source-blob identity; it does not create a general v1 adapter.

The immutable v1.5.12 reference is under `tests/fixtures/historical_replay/v1_5_12/`.

## v1.6 field acceptance

Current acceptance uses exactly three synthetic, identity-free fixtures:

- `manufacturing_typed_architecture.json` — machine semantics `PASS`, research depth `PASS`, presentation `PASS`.
- `distributor_funding_and_valuation.json` — machine semantics `PASS`, research depth `LIMITED`, presentation `PASS`.
- `coverage_limited_no_plugin.json` — machine semantics `PASS`, research depth `LIMITED`, presentation `PASS`.

The three statuses are evaluated separately. Machine semantics checks v2 contract/schema identity, typed Readiness/Thesis artifacts, Snapshot verification and Semantic Preservation. Research depth evaluates actual business-model coverage and valuation reconciliation. Presentation requires non-empty Markdown/HTML and a real `%PDF` artifact.

## Executable examples

The examples are deliberately offline and synthetic:

```bash
python examples/core_api_v2_run.py
python examples/plugin_api_v2.py
python examples/http_api_v1.py
```

- `examples/core_api_v2_run.py` — minimal Core API 2.0 run with an explicit synthetic repository attestor.
- `examples/plugin_api_v2.py` — minimal Plugin API 2.0 manifest/registry contract.
- `examples/http_api_v1.py` — constructs the HTTP API v1 adapter/OpenAPI contract without opening a server or database.

Production code should normally use the default `GitRepositoryAttestor` and a verified persistence repository.

## Repository map

- `src/research_os/application/` — Core API 2.0 command/orchestration/finalization boundary.
- `src/research_os/contracts/` — typed durable artifact/value/evidence contracts.
- `src/research_os/runtime/` — Engine, module plan/state and current v2 artifact registrations.
- `src/research_os/plugins/` — Plugin API 2.0 contracts, discovery, registry and resolver.
- `src/research_os/snapshots/` — Snapshot Schema 2.0 canonical codec, digest and service.
- `src/research_os/adapters/persistence/` — SQL persistence adapters and verified snapshot loading.
- `src/research_os/api/` — read-only HTTP API v1.
- `src/research_os/reporting/` — human-readable projection, report document and Markdown rendering.
- `src/research_os/presentation/` — typed Markdown/HTML/PDF pipeline and Playwright adapter.
- `src/research_os/semantics/` — semantic fingerprint and preservation validation.
- `src/research_os/release/` — release manifest, verification packs and historical replay isolation.

## Quality and release verification

Install development/PDF dependencies and Chromium:

```bash
python -m pip install -e ".[test,pdf]"
python -m playwright install chromium
```

The stable v1.6.0 Release Manifest selects M1, M2, M3, M4, M5 and release-governance verification packs. A full local release verification is:

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
```

CI splits these responsibilities into `quality`, `unit`, `integration`, `acceptance`, `security-package`, and `release-gate` jobs. The acceptance job checks current v1.6.0 synthetic field output plus commit-addressed v1.5.08–v1.5.12 replay with real Playwright PDF rendering. The package job audits dependencies, builds wheel/sdist, checks metadata and installs the wheel into a clean virtualenv before running Core API and HTTP API smoke examples.

M5 is delivered as exactly one commit on top of M4 main baseline `abd19bbc7e22d7958df853333e0ba8cedff39f6f`; M1–M4 squash commits are not rewritten. The final main release-gate generates the source ZIP, binary patch, Git bundle, hashes, baseline metadata, verification note and fast-forward-only push instructions only after all prerequisite CI jobs pass.

## Research invocation protocol

For company research, use `docs/prompts/stock_research.md`. Company evidence must be re-established for the requested `decision_ts`; project memory or another company's run is not company-fact evidence.
