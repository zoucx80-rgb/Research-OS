from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
import re

from research_os.presentation.artifacts import (
    HtmlPresentationArtifact,
    PdfPresentationArtifact,
)


class PlaywrightPdfAdapter:
    """Optional Playwright/Chromium HTML-to-PDF presentation boundary."""

    version = "professional-pdf-adapter@1.0.0"

    def __init__(
        self,
        *,
        executable_path: str | Path | None = None,
        timeout_ms: int = 30_000,
    ) -> None:
        self._executable_path = (
            str(Path(executable_path).resolve()) if executable_path is not None else None
        )
        self._timeout_ms = timeout_ms

    @staticmethod
    def _playwright_version() -> str:
        try:
            return package_version("playwright")
        except PackageNotFoundError as exc:
            raise RuntimeError(
                "Playwright is optional; install research-os[pdf] and run "
                "`python -m playwright install chromium`"
            ) from exc

    @staticmethod
    def _validate_passive_html(content: str) -> None:
        forbidden = (
            r"<(?:script|iframe|object|embed|form|svg)\b",
            r"\bon[a-z]+\s*=",
            r"\b(?:src|href|srcdoc)\s*=",
            r"@import\b",
            r"url\s*\(",
            r"javascript\s*:",
        )
        if any(re.search(pattern, content, flags=re.IGNORECASE) for pattern in forbidden):
            raise ValueError("PlaywrightPdfAdapter accepts only passive, self-contained HTML")

    def render(self, html: HtmlPresentationArtifact) -> PdfPresentationArtifact:
        if not isinstance(html, HtmlPresentationArtifact):
            raise TypeError("PlaywrightPdfAdapter.render requires HtmlPresentationArtifact")
        self._validate_passive_html(html.content)

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is optional; install research-os[pdf] and run "
                "`python -m playwright install chromium`"
            ) from exc

        browser = None
        context = None
        try:
            with sync_playwright() as playwright:
                try:
                    if self._executable_path is None:
                        browser = playwright.chromium.launch(headless=True)
                    else:
                        browser = playwright.chromium.launch(
                            headless=True,
                            executable_path=self._executable_path,
                        )
                    context = browser.new_context(
                        java_script_enabled=False,
                        service_workers="block",
                    )
                    page = context.new_page()
                    page.set_default_timeout(self._timeout_ms)
                    page.route("**/*", lambda route: route.abort())
                    page.set_content(html.content, wait_until="load")
                    page.emulate_media(media="print")
                    content = page.pdf(
                        format="A4",
                        prefer_css_page_size=True,
                        print_background=True,
                        display_header_footer=True,
                        header_template="<span></span>",
                        footer_template=(
                            '<div style="width:100%;font-size:8px;color:#666;'
                            'text-align:center;font-family:sans-serif;">'
                            '<span class="pageNumber"></span> / '
                            '<span class="totalPages"></span></div>'
                        ),
                    )
                    backend_version = (
                        f"playwright@{self._playwright_version()}/chromium@{browser.version}"
                    )
                finally:
                    if context is not None:
                        context.close()
                    if browser is not None and browser.is_connected():
                        browser.close()
        except Exception as exc:
            message = str(exc)
            if "Executable doesn't exist" in message or "executable" in message.lower():
                raise RuntimeError(
                    "Playwright Chromium is unavailable; run "
                    "`python -m playwright install chromium`"
                ) from exc
            raise RuntimeError(f"Playwright PDF rendering failed: {message}") from exc

        return PdfPresentationArtifact.from_html(
            html=html,
            renderer_version=self.version,
            backend_version=backend_version,
            content=content,
        )
