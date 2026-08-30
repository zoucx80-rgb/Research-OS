from __future__ import annotations

from hashlib import sha256
import importlib
import subprocess
import sys
from types import ModuleType

import pytest

from research_os.presentation import HtmlPresentationArtifact, MarkdownPresentationArtifact
from research_os.reporting import (
    AuditAppendix,
    InvestmentDecisionSnapshot,
    ResearchReportDocument,
    SemanticValue,
)


def _adapter_cls():
    presentation = importlib.import_module("research_os.presentation")
    assert hasattr(presentation, "PlaywrightPdfAdapter"), (
        "v1.5.08 requires PlaywrightPdfAdapter"
    )
    return presentation.PlaywrightPdfAdapter


def _semantic(code: str, label: str) -> SemanticValue:
    return SemanticValue(code=code, label=label, explanation=label)


def _document() -> ResearchReportDocument:
    return ResearchReportDocument(
        decision_snapshot=InvestmentDecisionSnapshot(
            company_id="synthetic:pdf-boundary",
            decision_ts="2026-08-30T00:00:00Z",
            business_model=_semantic("manufacturing", "制造业"),
            fundamental_state=_semantic("MIXED", "基本面信号混合"),
            thesis_state=_semantic("ACTIVE", "投资逻辑仍然成立"),
            expectation_state=_semantic("MISSING", "市场预期缺失"),
            valuation_state=_semantic("MISSING", "估值缺失"),
            primary_thesis="现金回报仍待验证。",
            evidence_confidence=0.5,
        ),
        audit_appendix=AuditAppendix(
            repository="zoucx80-rgb/Research-OS",
            repository_commit="eebeb35595d8260d45ea561e970bbe13464d90e5",
            research_os_version="1.5.7",
            core_api_version="1.0",
            presentation_version="professional-research-view@1.3.0",
        ),
    )


def _html() -> HtmlPresentationArtifact:
    markdown = MarkdownPresentationArtifact.from_document(
        document=_document(),
        renderer_version="professional-markdown-renderer@1.0.0",
        content="# 投资研究报告\n",
    )
    style = "@page { size: A4; }"
    return HtmlPresentationArtifact.from_markdown(
        markdown=markdown,
        renderer_version="professional-html-renderer@1.0.0",
        style=style,
        content=(
            '<!doctype html><html lang="zh-CN"><head>'
            f"<style>{style}</style></head><body>报告</body></html>"
        ),
    )


@pytest.mark.parametrize("invalid", ["<html></html>", {}, _document()])
def test_pdf_adapter_rejects_every_input_except_html_artifact(invalid):
    with pytest.raises(TypeError, match="HtmlPresentationArtifact"):
        _adapter_cls()().render(invalid)


def test_importing_runtime_does_not_import_presentation_or_playwright():
    command = (
        "import sys; import research_os.runtime; "
        "print('playwright' in sys.modules); "
        "print('research_os.presentation.pdf_adapter' in sys.modules)"
    )

    completed = subprocess.run(
        [sys.executable, "-c", command],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout.splitlines() == ["False", "False"]


def test_pdf_adapter_has_a_stable_presentation_fingerprint():
    assert _adapter_cls().version == "professional-pdf-adapter@1.0.0"


@pytest.mark.parametrize(
    "active_markup",
    (
        "<script>alert(1)</script>",
        '<img src="https://example.com/a.png">',
        '<div onclick="alert(1)">active</div>',
        '<iframe srcdoc="active"></iframe>',
    ),
)
def test_pdf_adapter_rejects_active_or_external_html(active_markup):
    html = _html()
    style = "@page { size: A4; }"
    content = f"<style>{style}</style>{active_markup}"
    active = html.model_copy(
        update={
            "content": content,
            "content_hash": sha256(content.encode("utf-8")).hexdigest(),
        }
    )

    with pytest.raises(ValueError, match="passive, self-contained"):
        _adapter_cls()().render(active)


def test_pdf_adapter_disables_javascript_in_browser_context(monkeypatch):
    class FakePage:
        def set_default_timeout(self, _timeout):
            return None

        def route(self, _pattern, _handler):
            return None

        def set_content(self, _content, *, wait_until):
            assert wait_until == "load"

        def emulate_media(self, *, media):
            assert media == "print"

        def pdf(self, **_options):
            return b"%PDF-1.7\nfake"

    class FakeContext:
        def __init__(self):
            self.closed = False
            self.playwright_stopped = False

        def new_page(self):
            return FakePage()

        def close(self):
            if self.playwright_stopped:
                raise RuntimeError("Event loop is closed! Is Playwright already stopped?")
            self.closed = True

    class FakeBrowser:
        version = "140.0"

        def __init__(self):
            self.context_options = None
            self.context = FakeContext()
            self.connected = True

        def new_context(self, **options):
            self.context_options = options
            return self.context

        def is_connected(self):
            return self.connected

        def close(self):
            self.connected = False

    browser = FakeBrowser()

    class FakeManager:
        def __enter__(self):
            chromium = type("Chromium", (), {"launch": lambda _self, **_kwargs: browser})()
            return type("Playwright", (), {"chromium": chromium})()

        def __exit__(self, *_args):
            browser.context.playwright_stopped = True
            return False

    playwright = ModuleType("playwright")
    sync_api = ModuleType("playwright.sync_api")
    sync_api.sync_playwright = lambda: FakeManager()
    monkeypatch.setitem(sys.modules, "playwright", playwright)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", sync_api)
    monkeypatch.setattr(_adapter_cls(), "_playwright_version", staticmethod(lambda: "1.62.0"))

    artifact = _adapter_cls()().render(_html())

    assert artifact.content.startswith(b"%PDF-")
    assert browser.context_options == {
        "java_script_enabled": False,
        "service_workers": "block",
    }
    assert browser.context.closed
