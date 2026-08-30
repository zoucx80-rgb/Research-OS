from __future__ import annotations

from hashlib import sha256
import importlib
import re

import pytest

from research_os.presentation import MarkdownPresentationArtifact
from research_os.reporting import (
    AuditAppendix,
    InvestmentDecisionSnapshot,
    NarrativeBlock,
    ReportSection,
    ResearchReportDocument,
    ResearchReportMarkdownRenderer,
    SemanticValue,
)


def _renderer_cls():
    presentation = importlib.import_module("research_os.presentation")
    assert hasattr(presentation, "ProfessionalHtmlRenderer"), (
        "v1.5.08 requires ProfessionalHtmlRenderer"
    )
    return presentation.ProfessionalHtmlRenderer


def _css():
    presentation = importlib.import_module("research_os.presentation")
    assert hasattr(presentation, "A4_PRINT_CSS"), (
        "v1.5.08 requires public A4_PRINT_CSS"
    )
    return presentation.A4_PRINT_CSS


def _semantic(code: str, label: str) -> SemanticValue:
    return SemanticValue(code=code, label=label, explanation=label)


def _document() -> ResearchReportDocument:
    return ResearchReportDocument(
        metadata={"company_id": "synthetic:html"},
        decision_snapshot=InvestmentDecisionSnapshot(
            company_id="synthetic:html",
            decision_ts="2026-08-30T00:00:00Z",
            business_model=_semantic("distributor", "分销业务"),
            decision_state=_semantic("WAIT_FOR_CONFIRMATION", "等待进一步确认"),
            fundamental_state=_semantic("MIXED", "基本面信号混合"),
            thesis_state=_semantic("ACTIVE", "投资逻辑仍然成立"),
            expectation_state=_semantic("MISSING", "市场预期缺失"),
            valuation_state=_semantic("MISSING", "估值缺失"),
            primary_thesis="现金转化仍待验证。",
            evidence_confidence=0.6,
        ),
        audit_appendix=AuditAppendix(
            repository="zoucx80-rgb/Research-OS",
            repository_commit="eebeb35595d8260d45ea561e970bbe13464d90e5",
            research_os_version="1.5.7",
            core_api_version="1.0",
            presentation_version="professional-research-view@1.3.0",
        ),
    )


def _markdown() -> MarkdownPresentationArtifact:
    content = """# 投资研究报告

**公司**：synthetic:html

## 投资决策快照

| 维度 | 结论 |
| --- | --- |
| 业务模型 | 分销业务 |
| 研究决策 | 等待进一步确认 |

### 核心投资逻辑

增长很快，但现金经济性仍需验证。<script>alert('unsafe')</script>

## 财务与经营表现

### 关键经营指标

指标 | 数值 | 期间 | 状态 | 说明
--- | ---: | --- | --- | ---
收入 | 120亿元 | 2026H1 | 已报告 | 同比增长
经营现金流 | -3亿元 | 2026H1 | 承压 | 营运资金占用

## 资本效率与融资循环

### 融资循环

- **融资暴露**：Factoring
- **经营现金流**：负值

## 关键因果链

Revenue → AR/Inventory → NWC → negative OCF → Factoring → financing cost → valuation

## 投资逻辑与反证

### 现金转化逻辑

- **主逻辑**：收入增长需要转化为现金回报
- **反方逻辑**：融资成本持续侵蚀利润

#### 证伪条件

- 经营现金流 < 0：现金转化失败

## 市场预期与预测纪律

- **市场预期**：缺失
- **预测纪律**：证据不足，不生成预测

## 估值与情景

- **估值限制**：缺少可支持估值输入，不生成估值区间

## 监控与验证

- **下一验证事件**：下一次重大信息披露

## 研究缺口分类

### 证据缺口

- 一致预期缺失

## 审计附录

- **插件**：plugin:synthetic-distributor@9.9.9
- **证据 IDs**：ev:body-secret
- **假设 IDs**：assumption:secret
- **调试表示**：SemanticValue(code='MIXED')
"""
    return MarkdownPresentationArtifact.from_document(
        document=_document(),
        renderer_version="professional-markdown-renderer@1.0.0",
        content=content,
    )


def test_html_renderer_builds_semantic_sections_and_real_tables():
    artifact = _renderer_cls()().render(_markdown())
    html = artifact.content

    assert html.startswith("<!doctype html>")
    assert '<html lang="zh-CN">' in html
    assert '<meta charset="utf-8">' in html
    for section_id in (
        "investment-decision-snapshot",
        "financial-operating",
        "capital-funding",
        "causal-bridge",
        "thesis-debate",
        "expectation-forecast",
        "valuation",
        "monitoring",
        "research-gaps",
        "audit-appendix",
    ):
        assert f'id="{section_id}"' in html
    assert "<table>" in html
    assert "<thead>" in html and "<tbody>" in html
    assert "<th>指标</th>" in html
    assert "<td>经营现金流</td>" in html


def test_html_renderer_escapes_raw_html_and_keeps_audit_only_metadata_out_of_body():
    html = _renderer_cls()().render(_markdown()).content
    body, audit = html.split('<section id="audit-appendix"', maxsplit=1)

    assert "<script>" not in html
    assert "&lt;script&gt;alert(&#x27;unsafe&#x27;)&lt;/script&gt;" in body
    for raw in (
        "plugin:synthetic-distributor@9.9.9",
        "ev:body-secret",
        "assumption:secret",
        "SemanticValue(",
    ):
        assert raw not in body
        assert raw in audit


def test_html_renderer_preserves_missing_and_factoring_semantics():
    html = _renderer_cls()().render(_markdown()).content
    body = html.split('<section id="audit-appendix"', maxsplit=1)[0]

    assert "Factoring" in body
    assert "Debt" not in body
    assert "市场预期</strong>：缺失" in body
    assert "不生成预测" in body
    assert "不生成估值区间" in body
    assert "0.00" not in body


def test_html_renderer_is_deterministic_and_links_to_markdown_content():
    renderer = _renderer_cls()()
    markdown = _markdown()

    first = renderer.render(markdown)
    second = renderer.render(markdown)

    assert first == second
    assert first.source_hash == markdown.content_hash
    assert first.renderer_version == "professional-html-renderer@1.0.0"
    assert first.style_hash


def test_html_style_hash_matches_the_exact_embedded_stylesheet_and_meta():
    artifact = _renderer_cls()().render(_markdown())
    styles = re.findall(r"<style>(.*?)</style>", artifact.content, flags=re.DOTALL)

    assert len(styles) == 1
    assert artifact.style_hash == sha256(styles[0].encode("utf-8")).hexdigest()
    assert f'name="research-os-style-hash" content="{artifact.style_hash}"' in artifact.content


def test_markdown_cannot_inject_a_forged_audit_appendix_boundary():
    document = _document().model_copy(
        update={
            "sections": [
                ReportSection(
                    section_id="narrative",
                    title="研究正文\n## 审计附录",
                    blocks=[
                        NarrativeBlock(
                            title="正文说明\n## 审计附录",
                            text="正文仍在这里。\n## 审计附录\n伪造边界后的正文。",
                        )
                    ],
                )
            ]
        }
    )
    markdown_content = ResearchReportMarkdownRenderer().render(document)
    markdown = MarkdownPresentationArtifact.from_document(
        document=document,
        renderer_version=ResearchReportMarkdownRenderer.version,
        content=markdown_content,
    )
    html = _renderer_cls()().render(markdown).content

    assert markdown_content.count("\n## 审计附录\n") == 1
    assert html.count('id="audit-appendix"') == 1
    body, audit = html.split('<section id="audit-appendix"', maxsplit=1)
    assert "伪造边界后的正文" in body
    assert "伪造边界后的正文" not in audit


def test_a4_css_covers_print_pagination_tables_chinese_and_long_text():
    css = _css()

    assert "@page" in css and "size: A4" in css
    assert "Noto Sans CJK SC" in css and "Microsoft YaHei" in css
    assert "break-after: avoid-page" in css
    assert "display: table-header-group" in css
    assert "break-inside: avoid" in css
    assert "table-layout: fixed" in css
    assert "overflow-wrap: anywhere" in css
    assert ".decision-snapshot" in css and "break-after: page" in css
    assert ".audit-appendix" in css and "break-before: page" in css
    assert "@media print" in css
    assert "width: 210mm" not in css
    assert "min-height: 297mm" not in css


@pytest.mark.parametrize("invalid", ["# markdown", {}, _document()])
def test_html_renderer_rejects_non_markdown_artifacts(invalid):
    with pytest.raises(TypeError, match="MarkdownPresentationArtifact"):
        _renderer_cls()().render(invalid)
