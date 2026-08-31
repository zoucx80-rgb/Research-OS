from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_active_v1_5_11_output_uses_professional_missingness_and_confidence_labels():
    renderer = (
        ROOT / "src/research_os/reporting/markdown_renderer_v1_5_11.py"
    ).read_text(encoding="utf-8")
    semantics = (ROOT / "src/research_os/reporting/semantics.py").read_text(encoding="utf-8")

    assert "已采纳证据质量" in renderer
    assert "市场预期证据不足" in semantics
    assert "投资逻辑等待确认" in semantics
    assert "模型 | 适用性 | 说明" in renderer
    assert 'professional-markdown-renderer@1.3.0' in renderer


def test_active_v1_5_11_presenter_deduplicates_only_equivalent_ocf_aliases():
    presenter = (
        ROOT / "src/research_os/reporting/research_view_v1_5_11.py"
    ).read_text(encoding="utf-8")

    assert '"ocf": "operating_cash_flow"' in presenter
    assert '"operating_cash_flow": "operating_cash_flow"' in presenter
    assert "item.get(\"value\")" in presenter
    assert "item.get(\"period\")" in presenter
    assert "item.get(\"period_end\")" in presenter
