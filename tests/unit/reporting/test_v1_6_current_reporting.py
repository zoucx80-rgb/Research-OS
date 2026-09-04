from __future__ import annotations

import inspect
import subprocess
from datetime import datetime, timezone

import pytest

from research_os.application import ResearchApplication, ResearchRunCommand
from research_os.application.bootstrap import RepositoryAttestation
from research_os.application.command import ResearchRunOptions
from research_os.contracts.values import AccountingScope
from research_os.domain.evidence import Evidence
from research_os.period.models import ReportingPeriod
from research_os.reporting import (
    MarkdownArtifactRenderer,
    ResearchReportComposer,
    ResearchViewPresenter,
    semantic_fingerprint,
)
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)
from research_os.version import RESEARCH_OS_VERSION


DECISION_TS = datetime(2026, 9, 3, 8, 0, tzinfo=timezone.utc)
COMPANY_ID = "synthetic:m4-reporting"


def _head() -> str:
    return subprocess.check_output(("git", "rev-parse", "HEAD"), text=True).strip()


class _Attestor:
    def attest(self) -> RepositoryAttestation:
        return RepositoryAttestation(
            repository_host="github.com",
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            head_sha=_head(),
        )


def _result():
    item = Evidence(
        evidence_id="ev:m4-business",
        revision_no=3,
        company_id=COMPANY_ID,
        evidence_type="filing_fact",
        publish_ts=DECISION_TS,
        ingested_at=DECISION_TS,
        source_table="business_description",
        value="precision manufacturing",
        confidence_grade="A",
        verification_status="PRIMARY_VERIFIED",
    )
    evidence = EvidenceView((item,), company_id=COMPANY_ID, decision_ts=DECISION_TS)
    ref = evidence.refs()[0]
    command = ResearchRunCommand(
        context=ResearchContext(
            run_id="run:m4-reporting",
            company=CompanyRef(company_id=COMPANY_ID),
            decision_ts=DECISION_TS,
            baseline=BaselineFingerprint(
                repository_full_name="zoucx80-rgb/Research-OS",
                repository_id=1350382205,
                branch="main",
                commit_sha=_head(),
                research_os_version=RESEARCH_OS_VERSION,
                core_api_version="2.0",
            ),
            evidence=evidence,
            facts=FactView(
                company_id=COMPANY_ID,
                decision_ts=DECISION_TS,
                values={"business_description": item.value},
                evidence_refs_by_fact={"business_description": (ref,)},
                reporting_period=ReportingPeriod(period_type="FY"),
                accounting_scope=AccountingScope(),
            ),
        ),
        options=ResearchRunOptions(persist_snapshot=False),
    )
    return ResearchApplication.build(repository_attestor=_Attestor()).run(command)


def test_presenter_accepts_only_core_api_v2_result_and_preserves_envelopes() -> None:
    result = _result()
    presenter = ResearchViewPresenter()

    view = presenter.present(result)

    assert view.company_id == COMPANY_ID
    assert view.execution_completion == result.execution_completion.final_status
    assert view.research_readiness == result.research_readiness.final_status
    assert view.semantic_fingerprint == semantic_fingerprint(result.artifacts)
    expected = {
        (item.key.artifact_id, item.key.schema_version): item
        for item in result.artifacts.envelopes()
    }
    assert {(item.artifact_id, item.schema_version) for item in view.artifacts} == set(expected)
    for artifact in view.artifacts:
        source = expected[(artifact.artifact_id, artifact.schema_version)]
        assert artifact.producer_ids == source.producer_ids
        assert artifact.evidence_refs == source.evidence_refs
        assert artifact.value_fingerprint == source.value_fingerprint

    with pytest.raises(TypeError):
        presenter.present({"run_id": result.run_id})  # type: ignore[arg-type]


def test_semantic_fingerprint_ignores_run_and_snapshot_identity() -> None:
    result = _result()
    other = result.model_copy(update={"run_id": "run:other", "snapshot": None})

    assert ResearchViewPresenter().present(result).semantic_fingerprint == (
        ResearchViewPresenter().present(other).semantic_fingerprint
    )


def test_composer_and_markdown_preserve_semantic_fingerprint_without_lineage_leak() -> None:
    result = _result()
    view = ResearchViewPresenter().present(result)
    composer = ResearchReportComposer()

    document = composer.compose(view)
    markdown = MarkdownArtifactRenderer().render(document)

    assert document.semantic_fingerprint == view.semantic_fingerprint
    assert markdown.semantic_fingerprint == document.semantic_fingerprint
    assert "None" not in markdown.content
    assert "ev:m4-business" not in markdown.content.split("## 审计附录", maxsplit=1)[0]
    assert "ev:m4-business" in markdown.content.split("## 审计附录", maxsplit=1)[1]

    with pytest.raises(TypeError):
        composer.compose(result)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        composer.compose({})  # type: ignore[arg-type]


def test_current_reporting_source_does_not_import_research_engines_or_legacy_versioned_views() -> (
    None
):
    from research_os.reporting import composer, research_view

    source = inspect.getsource(research_view) + inspect.getsource(composer)
    forbidden = (
        "research_os.runtime.result",
        "research_view_v1_",
        "historical_professional",
        "ThesisService",
        "ValuationReconciler",
        "ExpectationGapValidator",
    )

    assert all(token not in source for token in forbidden)


def test_v1_6_01_investor_body_is_compact_decision_first_and_audit_separated() -> None:
    result = _result()
    document = ResearchReportComposer().compose(ResearchViewPresenter().present(result))
    markdown = MarkdownArtifactRenderer().render(document).content
    body, audit = markdown.split("## 审计附录", maxsplit=1)

    assert len(body.splitlines()) <= 350
    section_titles = [line for line in body.splitlines() if line.startswith("## ")]
    assert section_titles[0] == "## 投资决策快照"
    assert "Schema:" not in body
    assert "Value Fingerprint" not in body
    assert "producer_ids" not in body
    assert "evidence_refs" not in body
    assert result.semantic_fingerprint if hasattr(result, "semantic_fingerprint") else True
    assert document.semantic_fingerprint in audit
