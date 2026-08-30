# Research OS v1.5.08 Professional HTML/PDF Presentation Pipeline Design

## Status and frozen baseline

Approved on 2026-08-30 as the downstream presentation continuation of v1.5.05-v1.5.07.

- Repository: `zoucx80-rgb/Research-OS` (id `1350382205`)
- Frozen starting `main` HEAD: `eebeb35595d8260d45ea561e970bbe13464d90e5`
- Starting Research OS: `1.5.7`
- Core API: `1.0`
- Presenter: `professional-research-view@1.3.0`
- Composer: `research-report-composer@1.1.0`
- Markdown renderer: `professional-markdown-renderer@1.0.0`
- Selected PDF backend: Playwright/Chromium, isolated as an optional presentation dependency

This release does not redesign or replay the v1.5.05 composition, v1.5.06 coverage, or v1.5.07 Markdown-rendering work.

## Goal

Add a professional, provenance-linked HTML/PDF presentation pipeline whose only authority is the existing typed report document and Markdown output. The new layers may format, paginate, and export canonical content; they may not calculate or reinterpret research semantics.

Target release:

- Research OS `1.5.8`
- Core API `1.0`
- Presenter, Composer, and Markdown renderer fingerprints unchanged
- HTML renderer `professional-html-renderer@1.0.0`
- PDF adapter `professional-pdf-adapter@1.0.0`

## Hard architecture boundary

The only permitted direction is:

```text
ResearchRunResult
    -> HumanReadableResearchView
    -> ResearchReportDocument
    -> MarkdownPresentationArtifact
    -> HtmlPresentationArtifact
    -> PdfPresentationArtifact
```

The existing named components remain the producers of the first three transitions:

```text
ResearchViewPresenter
    -> ResearchReportComposer
    -> ResearchReportMarkdownRenderer
```

There is no direct `ResearchRunResult -> PDF`, `HumanReadableResearchView -> HTML`, or `ResearchReportDocument -> PDF` entry point. `ProfessionalPresentationPipeline` accepts `ResearchReportDocument` only and internally performs every transition in order.

The HTML and PDF layers must never recompute KPI, Funding Loop, Driver/Thesis, Expectation Gap, Forecast, Valuation, Decision State, or Completion State. They may not import research engines to obtain missing values. Missing content remains absent or explicitly missing exactly as supplied by Markdown.

## Typed artifacts and provenance

`research_os.presentation.artifacts` defines immutable Pydantic artifacts:

```python
class MarkdownPresentationArtifact(BaseModel):
    artifact_type: Literal["markdown"]
    media_type: Literal["text/markdown; charset=utf-8"]
    renderer_version: str
    source_hash: str
    content_hash: str
    content: str

class HtmlPresentationArtifact(BaseModel):
    artifact_type: Literal["html"]
    media_type: Literal["text/html; charset=utf-8"]
    renderer_version: str
    source_hash: str
    content_hash: str
    style_hash: str
    content: str

class PdfPresentationArtifact(BaseModel):
    artifact_type: Literal["pdf"]
    media_type: Literal["application/pdf"]
    renderer_version: str
    backend_version: str
    source_hash: str
    content_hash: str
    content: bytes
```

Hash contract:

1. Canonical document hash is SHA-256 of sorted, compact UTF-8 JSON from `ResearchReportDocument.model_dump(mode="json")`.
2. Markdown `source_hash` equals the canonical document hash.
3. Markdown `content_hash` equals SHA-256 of exact UTF-8 Markdown bytes.
4. HTML `source_hash` equals Markdown `content_hash`.
5. HTML `content_hash` equals SHA-256 of exact UTF-8 HTML bytes; `style_hash` equals SHA-256 of the exact embedded CSS.
6. PDF `source_hash` equals HTML `content_hash`.
7. PDF `content_hash` equals SHA-256 of exact PDF bytes.

Artifacts reject invalid hash syntax and content/hash mismatches. They deliberately omit wall-clock creation time so identical source and renderer inputs remain deterministic. The PDF byte hash may vary across backend/browser builds, so `backend_version` records both Playwright and Chromium versions.

## Markdown artifact adapter

`ResearchReportMarkdownRenderer.render(document) -> str` remains backward compatible and retains `professional-markdown-renderer@1.0.0`.

`MarkdownArtifactRenderer.render(document) -> MarkdownPresentationArtifact` is a thin provenance wrapper. It accepts `ResearchReportDocument` only, calls the existing Markdown renderer, and performs hashing. It contains no rendering semantics of its own.

## Professional HTML renderer

`ProfessionalHtmlRenderer.render(markdown: MarkdownPresentationArtifact) -> HtmlPresentationArtifact` accepts no other input type.

It converts only the deterministic Markdown dialect already emitted by Research OS: headings, paragraphs, emphasis, bullet lists, and pipe tables. Input text is HTML-escaped before supported inline Markdown is converted. Raw HTML is never trusted.

The renderer assigns semantic layout classes from existing human-facing section titles, not from company identities or research states:

- `投资决策快照` -> cover/snapshot section
- `财务与经营表现` -> financial/KPI section
- `资本效率与融资循环` -> capital/funding section
- `关键因果链` -> causal bridge section
- `投资逻辑与反证` -> thesis debate section
- `市场预期与预测纪律` and `市场预期差` -> expectation/forecast sections
- `估值方法与适用性` and `估值与情景` -> valuation sections
- `监控与验证` -> monitoring section
- `研究缺口分类` and `关键研究限制` -> research gaps sections
- `审计附录` -> audit appendix

The HTML is self-contained: UTF-8 metadata, embedded A4 CSS, no remote fonts, scripts, images, or network requests. It exposes renderer, source, and exact embedded-style hashes in non-body HTML metadata. The HTML `content_hash` is carried by the typed artifact and acceptance manifest, rather than embedded into the bytes it hashes; embedding it would create a self-referential hash. None of these fields is inserted into the investment body.

## A4 print CSS

The bundled `A4_PRINT_CSS` must provide:

- `@page { size: A4; ... }` with professional print margins;
- readable Chinese font fallbacks: Noto/Source Han/PingFang/Microsoft YaHei/SimSun;
- grayscale-only hierarchy that remains legible in black and white;
- a first-page decision snapshot and explicit page break after it;
- `break-after: avoid-page` for headings;
- `thead { display: table-header-group; }`, automatic table page splitting, and row-level break avoidance;
- fixed table layout, `overflow-wrap: anywhere`, and safe handling of long identifiers in the audit appendix;
- explicit page break before the audit appendix;
- no clipped content, overlapping content, horizontal page overflow, or hidden missing-data markers.

The PDF footer is supplied by the PDF adapter and contains page number / total pages only. It cannot add research content.

## Independent Playwright PDF adapter

`PlaywrightPdfAdapter.render(html: HtmlPresentationArtifact) -> PdfPresentationArtifact` is the only concrete v1.5.08 backend.

- Optional dependency: `playwright>=1.62,<1.63`, reflecting the selected 2026-08-30 backend line.
- Browser installation is an explicit deployment/CI step: `python -m playwright install chromium`.
- Playwright is imported inside the adapter method, never at Core/runtime import time.
- The adapter rejects active or externally linked markup before Playwright import, launches headless Chromium in a context with JavaScript disabled and service workers blocked, loads the self-contained HTML with networking blocked, emulates print media, and calls `page.pdf()` with CSS-preferred A4 sizing, print backgrounds, and page-number footer.
- It verifies the returned bytes start with `%PDF-` before constructing the artifact.

`src/research_os/runtime`, `ResearchRuntimeFactory`, `ResearchEngine`, plugins, valuation, decision, and completion modules must not import `research_os.presentation`, `playwright`, or a PDF backend. Default `pip install research-os` must remain valid without Playwright.

## Body/audit separation

The primary HTML/PDF body must not contain raw Python repr, raw dict/list repr, enum repr, `block_type`, internal field names, plugin IDs, raw evidence IDs, or raw assumption IDs. Those items may appear only after the `审计附录` boundary because they already exist there in canonical Markdown.

The HTML renderer cannot recover omitted IDs from any upstream object because its only input is the Markdown artifact. The PDF adapter only prints HTML. This makes body/audit separation structural rather than a template convention.

## Missing-data and economic-semantics invariants

- Missing KPI, expectation, expectation gap, valuation case, current price, monitoring threshold, or specialized hospitality metric remains missing.
- HTML/PDF may not substitute zero, `N/A` with invented meaning, a synthetic range, or prose that implies a value exists.
- Factoring, receivable transfers, and other working-capital financing retain their supplied labels. The presentation layer cannot relabel Factoring as Debt.
- Lease-heavy Hospitality remains capability-limited without fabricated RevPAR, ADR, OCC, same-store metrics, lease-adjusted ROIC, or lease-adjusted valuation.

## Cross-model permanent regression

Synthetic, company-neutral archetypes cover the full Markdown -> HTML -> PDF boundary:

1. Manufacturing: growth/margin plus receivables, cash, Capex, and capital-efficiency tension coexist without invented order/utilization/yield data.
2. Distributor: Revenue -> AR/Inventory -> NWC -> negative OCF -> Debt/Factoring -> financing cost -> valuation remains visible; Factoring stays distinct from Debt.
3. Lease-heavy Hospitality: low owned PPE plus material leases produces visible capability gaps and no fabricated hotel operating KPIs or lease-adjusted economics.

Production Core contains no ticker, real-company name, or company-specific branch.

## Field acceptance and visual QA

After the final implementation HEAD is frozen, execute three new PIT-safe research runs with `decision_ts=2026-08-30`:

- `300034.SZ`
- `001287.SZ`
- `301073.SZ`

Company evidence remains external to production Core and must satisfy `publish_ts <= decision_ts`. Each run produces Markdown, HTML, and PDF artifacts through the strict pipeline.

For every PDF:

1. verify file signature, page count, media box, and text extractability;
2. render every page to PNG with Poppler;
3. inspect the first page, KPI/financial tables, Funding Loop, thesis, valuation, monitoring, gaps, and audit appendix;
4. inspect page breaks, repeated table headers, long-text wrapping, overflow, grayscale legibility, and Chinese glyphs;
5. record a structured QA manifest with per-check PASS/FAIL and reviewed page numbers.

Automated tests cannot replace this visual review.

## Version, CI, and release gate

v1.5.08 updates:

- `RESEARCH_OS_VERSION` and package version to `1.5.8`;
- `research_os_version.json.module_versions.html_renderer = "1.0.0"`;
- `research_os_version.json.module_versions.pdf_adapter = "1.0.0"`;
- release component fingerprints for HTML and PDF presentation only;
- a permanent v1.5.08 presentation regression and CI browser-render job;
- README, stock-research protocol, changelog, and migration documentation.

The Release Gate must retain every historical check and add `professional_presentation_pipeline_v1_5_08`. Final stable status requires full pytest, Release Gate, three-company field acceptance, three visual-QA manifests, exact remote `main` verification, and no unresolved P0/P1 defect.

## Non-goals

- Hospitality Plugin
- lease-adjusted valuation
- Forecast rewrite
- Evidence Quality rewrite
- new Decision/Completion/Thesis engine
- company-specific Core logic
- trading, portfolio, or dashboard features
- direct PDF generation from `ResearchRunResult`, `HumanReadableResearchView`, or `ResearchReportDocument`
- a second PDF backend in v1.5.08
