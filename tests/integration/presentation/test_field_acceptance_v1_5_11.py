from pathlib import Path

from research_os.presentation import HtmlPresentationArtifact, PdfPresentationArtifact


class _DeterministicPdfAdapter:
    def render(self, html: HtmlPresentationArtifact) -> PdfPresentationArtifact:
        return PdfPresentationArtifact.from_html(
            html=html,
            renderer_version="professional-pdf-adapter@1.0.0",
            backend_version="semantic-correctness-test-backend@1.0",
            content=b"%PDF-1.7\nsemantic-correctness-field-test",
        )


def test_v1_5_11_generic_field_case_passes_machine_and_presentation_semantics(tmp_path: Path, monkeypatch):
    repository_root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repository_root))
    from scripts.render_field_acceptance_v1_5_11 import render_case

    case_path = (
        repository_root
        / "tests/fixtures/field_acceptance/v1_5_11/manufacturing_semantic_correctness.json"
    )
    output = render_case(
        case_path=case_path,
        output_root=tmp_path,
        repository_root=repository_root,
        pdf_adapter=_DeterministicPdfAdapter(),
    )

    acceptance = output.manifest["acceptance"]
    assert acceptance["presentation"]["status"] == "PASS"
    assert acceptance["semantic_correctness"]["status"] == "PASS", acceptance["semantic_correctness"]["errors"]
    assert acceptance["overall_status"] == "PASS"
    assert output.manifest["versions"]["presenter"] == "professional-research-view@1.6.0"
    assert output.manifest["versions"]["markdown_renderer"] == "professional-markdown-renderer@1.3.0"

    body = output.bundle.markdown.content.split("## 审计附录", 1)[0]
    assert "市场预期证据不足" in body
    assert "应收增速显著快于收入" not in body
    assert "None" not in body