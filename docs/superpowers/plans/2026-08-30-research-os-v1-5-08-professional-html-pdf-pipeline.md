# Research OS v1.5.08 Professional HTML/PDF Presentation Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add provenance-linked typed Markdown/HTML/PDF artifacts, a professional deterministic HTML renderer, A4 print CSS, and an isolated Playwright PDF adapter without changing research semantics.

**Architecture:** Preserve the existing `ResearchRunResult -> HumanReadableResearchView -> ResearchReportDocument -> Markdown` chain, wrap Markdown in a hashed artifact, and require HTML/PDF to consume only the immediately preceding typed artifact. Playwright is an optional delayed-import dependency and never enters the runtime graph.

**Tech Stack:** Python 3.12, Pydantic v2, stdlib HTML/hash utilities, Playwright Python `>=1.62,<1.63`, Chromium, pytest, Poppler, pypdf/PyMuPDF for acceptance inspection.

**Spec:** `docs/superpowers/specs/2026-08-30-research-os-v1-5-08-professional-html-pdf-pipeline-design.md`

## Global Constraints

- Frozen starting HEAD: `eebeb35595d8260d45ea561e970bbe13464d90e5`.
- Target Research OS version: `1.5.8`; Core API remains `1.0`.
- Presenter `professional-research-view@1.3.0`, Composer `research-report-composer@1.1.0`, and Markdown renderer `professional-markdown-renderer@1.0.0` remain unchanged.
- New fingerprints: `professional-html-renderer@1.0.0` and `professional-pdf-adapter@1.0.0`.
- No direct raw result/view/document -> PDF path.
- No semantic calculation, company-specific Core logic, fake missing values, or Factoring -> Debt relabeling.
- PDF visual QA is mandatory and separate from automated tests.

---

### Task 1: Add typed presentation artifacts and provenance hashing

**Files:**
- Create: `src/research_os/presentation/artifacts.py`
- Create: `src/research_os/presentation/__init__.py`
- Create: `tests/unit/presentation/test_artifacts.py`

**Interfaces:**
- Produces: `canonical_document_hash(document) -> str`, `MarkdownPresentationArtifact`, `HtmlPresentationArtifact`, `PdfPresentationArtifact`.
- Hashes: lowercase 64-character SHA-256; content validators reject mismatches.

- [ ] **Step 1: Write RED artifact tests.** Define minimal `ResearchReportDocument` fixture and require canonical hash determinism, exact content hashes, frozen models, invalid hash rejection, and content mutation rejection.

```python
artifact = MarkdownPresentationArtifact.from_document(
    document=document,
    renderer_version="professional-markdown-renderer@1.0.0",
    content="# report\n",
)
assert artifact.source_hash == canonical_document_hash(document)
assert artifact.content_hash == sha256(b"# report\n").hexdigest()
with pytest.raises(ValidationError):
    artifact.model_copy(update={"content": "changed"}, revalidate_instances="always")
```

- [ ] **Step 2: Run RED.**

Run: `PATH=/root/.local/bin:$PATH python -m pytest -q tests/unit/presentation/test_artifacts.py`

Expected: import failure because `research_os.presentation` does not exist.

- [ ] **Step 3: Implement minimal immutable artifact models.** Use `model_validator(mode="after")`, UTF-8 SHA-256 helpers, sorted compact JSON for the document hash, and exact `from_*` constructors.

- [ ] **Step 4: Run GREEN and full existing reporting tests.**

Run: `PATH=/root/.local/bin:$PATH python -m pytest -q tests/unit/presentation/test_artifacts.py tests/unit/reporting`

- [ ] **Step 5: Commit Task 1.**

### Task 2: Wrap the existing Markdown renderer without changing its fingerprint

**Files:**
- Create: `src/research_os/presentation/markdown_artifact_renderer.py`
- Modify: `src/research_os/presentation/__init__.py`
- Create: `tests/unit/presentation/test_markdown_artifact_renderer.py`

**Interfaces:**
- Consumes: `ResearchReportDocument` only.
- Produces: `MarkdownArtifactRenderer.render(document) -> MarkdownPresentationArtifact`.
- Delegates to: unchanged `ResearchReportMarkdownRenderer.render(document) -> str`.

- [ ] **Step 1: Write RED boundary/delegation tests.** Require exact byte equality with the existing Markdown renderer, correct source/content hashes, unchanged Markdown renderer version, and `TypeError` for view/result/dict inputs.

- [ ] **Step 2: Verify RED.**

Run: `PATH=/root/.local/bin:$PATH python -m pytest -q tests/unit/presentation/test_markdown_artifact_renderer.py`

- [ ] **Step 3: Implement the thin wrapper.** It may perform type checking and hashing only; it must not inspect or modify report sections.

- [ ] **Step 4: Verify GREEN plus v1.5.07 regressions.**

Run: `PATH=/root/.local/bin:$PATH python -m pytest -q tests/unit/presentation/test_markdown_artifact_renderer.py tests/unit/reporting/test_markdown_renderer.py tests/regression/research_patterns/test_v1_5_07_renderer_patterns.py`

- [ ] **Step 5: Commit Task 2.**

### Task 3: Implement professional HTML rendering and A4 CSS

**Files:**
- Create: `src/research_os/presentation/print_css.py`
- Create: `src/research_os/presentation/html_renderer.py`
- Modify: `src/research_os/presentation/__init__.py`
- Create: `tests/unit/presentation/test_html_renderer.py`

**Interfaces:**
- Consumes: `MarkdownPresentationArtifact` only.
- Produces: `ProfessionalHtmlRenderer.render(markdown) -> HtmlPresentationArtifact`.
- Fingerprint: `professional-html-renderer@1.0.0`.

- [ ] **Step 1: Write RED HTML structure tests.** Require `<!doctype html>`, `lang="zh-CN"`, UTF-8, embedded `A4_PRINT_CSS`, a snapshot section, typed major section classes, real HTML tables with `thead`/`tbody`, a page-break audit section, and escaped raw HTML.

- [ ] **Step 2: Write RED CSS contract tests.** Require A4 `@page`, Chinese font fallbacks, grayscale colors, heading break protection, repeating table headers, row break avoidance, long-text wrapping, fixed table layout, snapshot break, and audit break.

- [ ] **Step 3: Write RED truthfulness tests.** Split body before the audit section and assert no Python repr/internal fields/plugin IDs/evidence IDs/assumption IDs. Require missing expectation/valuation content to remain absent and `Factoring` to remain present without automatic replacement by `Debt`.

- [ ] **Step 4: Verify RED.**

Run: `PATH=/root/.local/bin:$PATH python -m pytest -q tests/unit/presentation/test_html_renderer.py`

- [ ] **Step 5: Implement the deterministic Markdown dialect parser.** HTML-escape input, support only emitted headings/paragraphs/emphasis/bullets/tables, wrap known human-facing sections with presentation classes, and embed exact CSS.

- [ ] **Step 6: Build `HtmlPresentationArtifact`.** Set `source_hash=markdown.content_hash`, compute `style_hash`, and validate the final HTML content hash.

- [ ] **Step 7: Verify GREEN and presentation suites.**

Run: `PATH=/root/.local/bin:$PATH python -m pytest -q tests/unit/presentation tests/unit/reporting`

- [ ] **Step 8: Commit Task 3.**

### Task 4: Add the isolated Playwright PDF adapter

**Files:**
- Modify: `pyproject.toml`
- Create: `src/research_os/presentation/pdf_adapter.py`
- Modify: `src/research_os/presentation/__init__.py`
- Create: `tests/unit/presentation/test_pdf_adapter.py`
- Create: `tests/integration/presentation/test_playwright_pdf_adapter.py`

**Interfaces:**
- Consumes: `HtmlPresentationArtifact` only.
- Produces: `PlaywrightPdfAdapter.render(html) -> PdfPresentationArtifact`.
- Fingerprint: `professional-pdf-adapter@1.0.0`.

- [ ] **Step 1: Add optional dependency metadata.** Add `pdf = ["playwright>=1.62,<1.63"]`; do not add Playwright to default dependencies.

- [ ] **Step 2: Install the selected test backend.**

Run: `python -m pip install 'playwright>=1.62,<1.63' && python -m playwright install chromium`

- [ ] **Step 3: Write RED unit boundary tests.** Require `TypeError` for str/dict/document inputs and prove importing `research_os.runtime` does not import `playwright` or `research_os.presentation.pdf_adapter`.

- [ ] **Step 4: Write RED real-browser integration test.** Render a self-contained Chinese HTML artifact and require `%PDF-`, `source_hash == html.content_hash`, a SHA-256 content hash, recorded Playwright/Chromium backend version, and extractable Chinese text.

- [ ] **Step 5: Verify RED.**

Run: `PATH=/root/.local/bin:$PATH python -m pytest -q tests/unit/presentation/test_pdf_adapter.py tests/integration/presentation/test_playwright_pdf_adapter.py`

- [ ] **Step 6: Implement delayed-import adapter.** Block network requests, emulate print media, set content without external assets, render CSS-preferred A4 with header/footer page numbers, verify PDF signature, and always close browser resources.

- [ ] **Step 7: Verify GREEN and default-install import safety.**

Run: `PATH=/root/.local/bin:$PATH python -m pytest -q tests/unit/presentation tests/integration/presentation`

- [ ] **Step 8: Commit Task 4.**

### Task 5: Add the strict pipeline and synthetic cross-model regression

**Files:**
- Create: `src/research_os/presentation/pipeline.py`
- Modify: `src/research_os/presentation/__init__.py`
- Create: `tests/unit/presentation/test_pipeline.py`
- Create: `tests/regression/research_patterns/test_v1_5_08_presentation_patterns.py`
- Create: `tests/regression/architecture/test_presentation_dependency_boundary.py`

**Interfaces:**
- Produces: `PresentationBundle(markdown, html, pdf)` and `ProfessionalPresentationPipeline.render(document) -> PresentationBundle`.
- Pipeline accepts `ResearchReportDocument` only and calls Markdown -> HTML -> PDF in order.

- [ ] **Step 1: Write RED pipeline hash-chain test.** Require document hash -> Markdown source, Markdown content -> HTML source, and HTML content -> PDF source.

- [ ] **Step 2: Write RED architecture test.** Parse imports under runtime/Core and reject `research_os.presentation`, `playwright`, `pdf_adapter`, or a direct raw result/view -> PDF function.

- [ ] **Step 3: Write RED Manufacturing regression.** Render growth/margin plus AR/cash/Capex tension; require all supplied signals and prohibit invented backlog/utilization/yield.

- [ ] **Step 4: Write RED Distributor regression.** Require Revenue -> AR/Inventory -> NWC -> negative OCF -> Debt/Factoring -> financing cost -> valuation text, with Factoring and Debt independently preserved.

- [ ] **Step 5: Write RED Hospitality regression.** Require lease-heavy and capability-gap text; prohibit RevPAR/ADR/OCC/same-store/lease-adjusted ROIC/valuation.

- [ ] **Step 6: Verify RED, implement the minimal pipeline, then verify GREEN.**

Run: `PATH=/root/.local/bin:$PATH python -m pytest -q tests/unit/presentation/test_pipeline.py tests/regression/research_patterns/test_v1_5_08_presentation_patterns.py tests/regression/architecture/test_presentation_dependency_boundary.py`

- [ ] **Step 7: Commit Task 5.**

### Task 6: Release metadata, documentation, CI, and Release Gate

**Files:**
- Modify: `src/research_os/version.py`
- Modify: `pyproject.toml`
- Modify: `research_os_version.json`
- Modify: `src/research_os/release/runtime.py`
- Modify: `scripts/release_gate_v1_1.py`
- Modify: `.github/workflows/ci.yml`
- Create: `tests/regression/architecture/test_release_contract_v1_5_08.py`
- Create: `docs/migrations/v1.5.08.md`
- Modify: `README.md`
- Modify: `docs/prompts/stock_research.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- OS/package version: `1.5.8`; Core API `1.0`.
- Module versions: existing report renderer unchanged; HTML renderer and PDF adapter `1.0.0`.
- Gate: `professional_presentation_pipeline_v1_5_08`.

- [ ] **Step 1: Write RED release contract.** Assert exact versions/fingerprints, optional-only Playwright dependency, historical component stability, migration/README/prompt/changelog text, CI Chromium install, v1.5.08 test command, and retained historical gates.

- [ ] **Step 2: Verify RED.**

Run: `PATH=/root/.local/bin:$PATH python -m pytest -q tests/regression/architecture/test_release_contract_v1_5_08.py`

- [ ] **Step 3: Update version and component metadata.** Do not change Core, Presenter, Composer, or Markdown renderer versions.

- [ ] **Step 4: Add Release Gate and CI checks.** Install Playwright/Chromium only in the presentation job, run v1.5.08 regressions, then retain the full suite and release gate.

- [ ] **Step 5: Add migration/public documentation.** Document the strict artifact chain, install command, optional dependency, field acceptance, and non-goals.

- [ ] **Step 6: Verify release contract GREEN.**

- [ ] **Step 7: Commit Task 6.**

### Task 7: Run full local verification and release gate

**Files:**
- No product files unless a reproduced regression requires a TDD fix.

- [ ] **Step 1: Run the v1.5.08 focused suites.**

Run: `PATH=/root/.local/bin:$PATH python -m pytest -q tests/unit/presentation tests/integration/presentation tests/regression/research_patterns/test_v1_5_08_presentation_patterns.py tests/regression/architecture/test_presentation_dependency_boundary.py tests/regression/architecture/test_release_contract_v1_5_08.py`

- [ ] **Step 2: Run every historical reporting/correctness regression.**

Run: `PATH=/root/.local/bin:$PATH python -m pytest -q tests/unit/reporting tests/unit/expectations tests/unit/valuation tests/regression/research_patterns/test_v1_5_05_reporting_patterns.py tests/unit/reporting/test_composition_coverage_v1_5_06.py tests/regression/research_patterns/test_v1_5_07_renderer_patterns.py`

- [ ] **Step 3: Run the full suite.**

Run: `PATH=/root/.local/bin:$PATH python -m pytest -q`

- [ ] **Step 4: Run Release Gate.**

Run: `PATH=/root/.local/bin:$PATH python scripts/release_gate_v1_1.py`

- [ ] **Step 5: Commit any TDD fixes and rerun Steps 1-4 on the same HEAD.**

### Task 8: Three-company PIT field acceptance and PDF visual QA

**Files:**
- Create outside production Core: `output/field_acceptance/v1.5.08/<ticker>/report.md`
- Create outside production Core: `output/field_acceptance/v1.5.08/<ticker>/report.html`
- Create outside production Core: `output/pdf/research-os-v1.5.08-<ticker>.pdf`
- Create outside production Core: `output/field_acceptance/v1.5.08/<ticker>/qa-manifest.json`

**Interfaces:**
- Fixed `decision_ts=2026-08-30`.
- Companies: `300034.SZ`, `001287.SZ`, `301073.SZ`.
- Evidence must be newly retrieved, source-linked, and satisfy `publish_ts <= decision_ts`.

- [ ] **Step 1: Freeze the implementation HEAD used for all three runs.** Record repository id, exact SHA, OS/Core/component versions, and evidence cutoff.

- [ ] **Step 2: Retrieve PIT evidence separately for each company.** Prefer original company/regulatory disclosures; preserve publication timestamps; never cross-contaminate company facts.

- [ ] **Step 3: Execute the canonical research flow and strict presentation pipeline.** Write exact artifact bytes and verify every source/content hash transition.

- [ ] **Step 4: Run structural PDF inspection.** Use `pdfinfo`, pypdf, and text extraction to record page count, A4 media boxes, section presence, and Chinese text presence.

- [ ] **Step 5: Render every PDF page to PNG.**

Run: `pdftoppm -png <pdf> tmp/pdfs/<ticker>/page`

- [ ] **Step 6: Visually inspect every page.** Check snapshot, tables, Funding Loop, thesis, valuation, monitoring, gaps, audit appendix, pagination, overflow, grayscale, and Chinese glyphs. Record reviewed pages and PASS/FAIL per check.

- [ ] **Step 7: If a visual defect exists, add a failing CSS/renderer regression, fix it, regenerate all affected artifacts, and repeat Steps 4-6.**

- [ ] **Step 8: Make the three Markdown/HTML/PDF deliverables and QA manifests available to the user.**

### Task 9: Exact final HEAD and remote-main verification

**Files:**
- No new files unless final release evidence documentation is required.

- [ ] **Step 1: Verify clean diff and no secret/company-specific Core content.**

- [ ] **Step 2: Commit final verified source on local `main`.**

- [ ] **Step 3: Publish the exact commit to GitHub `main` using the authorized GitHub commit/tree/ref flow; do not force-push.**

- [ ] **Step 4: Re-read remote `main` SHA and version metadata.** Require local HEAD = remote main = SHA used for full pytest, Release Gate, and field acceptance.

- [ ] **Step 5: Confirm remote branch cleanup status without blocking implementation.** The user owns deletion of the four pre-existing non-main branches.

- [ ] **Step 6: Classify remaining backlog.** P0/P1 must be empty for stable; list P2 follow-ups and decide whether v1.5.09 is warranted.

- [ ] **Step 7: Emit `READY: v1.5.8 stable` only when every required gate above is evidenced on the exact final SHA.**
