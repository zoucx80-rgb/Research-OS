from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src/research_os"


def test_active_semantic_correctness_components_are_versioned_and_one_way():
    presenter = (SRC / "reporting/research_view_v1_5_11.py").read_text(encoding="utf-8")
    renderer = (SRC / "reporting/markdown_renderer_v1_5_11.py").read_text(encoding="utf-8")
    professional = (SRC / "runtime/professional_modules.py").read_text(encoding="utf-8")

    assert 'professional-research-view@1.6.0' in presenter
    assert 'professional-markdown-renderer@1.3.0' in renderer
    assert 'thesis.semantic_signal_assessment' in professional
    assert 'self.theses.assess_signals(evidence)' in professional
    assert 'SemanticThesisService' not in renderer
    assert 'DecisionEngine' not in renderer


def test_production_source_contains_no_acceptance_company_identity_branches():
    forbidden = (
        "300034.SZ",
        "001287.SZ",
        "301073.SZ",
        "钢研高纳",
        "中电港",
    )
    violations = []
    for path in SRC.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)}:{token}")
    assert violations == []


def test_historical_reporting_implementations_remain_present_for_replay():
    assert (SRC / "reporting/research_view_v1_5_09.py").exists()
    assert (SRC / "reporting/research_view_v1_5_10.py").exists()
    assert (SRC / "reporting/markdown_renderer_v1_5_09.py").exists()
    assert (SRC / "reporting/markdown_renderer_v1_5_10.py").exists()
