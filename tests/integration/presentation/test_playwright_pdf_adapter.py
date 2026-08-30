from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import sys

import pytest
from pypdf import PdfReader

pytestmark = pytest.mark.skipif(
    os.environ.get("RESEARCH_OS_RUN_PDF_INTEGRATION") != "1",
    reason="set RESEARCH_OS_RUN_PDF_INTEGRATION=1 with Chromium installed",
)


def test_playwright_renders_production_pipeline_as_multipage_a4_pdf(tmp_path: Path):
    repository_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repository_root))
    from scripts.render_field_acceptance_v1_5_08 import render_case

    case_path = (
        repository_root
        / "tests/fixtures/field_acceptance/v1_5_08/300034.SZ.json"
    )

    output = render_case(
        case_path=case_path,
        output_root=tmp_path,
        repository_root=repository_root,
    )
    artifact = output.bundle.pdf

    assert artifact.content.startswith(b"%PDF-")
    assert artifact.source_hash == output.bundle.html.content_hash
    assert artifact.renderer_version == "professional-pdf-adapter@1.0.0"
    assert artifact.backend_version.startswith("playwright@1.62.0/chromium@")

    reader = PdfReader(BytesIO(artifact.content))
    assert len(reader.pages) >= 6
    for page in reader.pages:
        assert float(page.mediabox.width) == pytest.approx(595.28, abs=1.0)
        assert float(page.mediabox.height) == pytest.approx(841.89, abs=1.0)

    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
    for section in (
        "投资决策快照",
        "财务与经营表现",
        "资本效率与融资循环",
        "关键因果链",
        "投资逻辑与反证",
        "市场预期与预测纪律",
        "估值方法与适用性",
        "监控与验证",
        "研究缺口分类",
        "审计附录",
    ):
        assert section in extracted
