"""Minimal offline Core API 2.0 research run.

The explicit attestor is only for this synthetic, repository-local example. Production
code should normally keep ResearchApplication's default GitRepositoryAttestor.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone

from research_os.application import (
    ResearchApplication,
    ResearchRunCommand,
    ResearchRunOptions,
    RepositoryAttestation,
)
from research_os.contracts.values import AccountingScope
from research_os.domain.evidence import Evidence
from research_os.period.models import ReportingPeriod
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


class ExampleRepositoryAttestor:
    def __init__(self, head_sha: str) -> None:
        self._head_sha = head_sha

    def attest(self) -> RepositoryAttestation:
        return RepositoryAttestation(
            repository_host="github.com",
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            head_sha=self._head_sha,
        )


def _head_sha() -> str:
    return subprocess.check_output(
        ("git", "rev-parse", "HEAD"), text=True
    ).strip()


def build_command(head_sha: str) -> ResearchRunCommand:
    decision_ts = datetime(2026, 9, 3, 8, 0, tzinfo=timezone.utc)
    company_id = "example:manufacturing"
    values = {
        "business_description": "precision manufacturing producer",
        "revenue": 1000.0,
        "net_profit_parent": 80.0,
        "assets_begin": 800.0,
        "assets_end": 920.0,
        "equity_begin": 410.0,
        "equity_end": 470.0,
        "fixed_asset_to_assets": 0.42,
        "gross_margin": 0.31,
    }
    evidence = tuple(
        Evidence(
            evidence_id=f"example:{fact_id}",
            revision_no=1,
            company_id=company_id,
            evidence_type="filing_fact",
            publish_ts=decision_ts,
            ingested_at=decision_ts,
            period="2025",
            source_table=fact_id,
            value=value,
            confidence_grade="A",
            verification_status="PRIMARY_VERIFIED",
        )
        for fact_id, value in values.items()
    )
    evidence_view = EvidenceView(
        evidence,
        company_id=company_id,
        decision_ts=decision_ts,
    )
    refs = {
        reference.evidence_id.removeprefix("example:"): reference
        for reference in evidence_view.refs()
    }
    return ResearchRunCommand(
        context=ResearchContext(
            run_id="example:core-api-v2",
            company=CompanyRef(company_id=company_id),
            decision_ts=decision_ts,
            baseline=BaselineFingerprint(
                repository_full_name="zoucx80-rgb/Research-OS",
                repository_id=1350382205,
                branch="main",
                commit_sha=head_sha,
                research_os_version=RESEARCH_OS_VERSION,
                core_api_version=CORE_API_VERSION,
            ),
            evidence=evidence_view,
            facts=FactView(
                company_id=company_id,
                decision_ts=decision_ts,
                values=values,
                evidence_refs_by_fact={key: (refs[key],) for key in values},
                reporting_period=ReportingPeriod(period_type="FY"),
                accounting_scope=AccountingScope(),
            ),
        ),
        options=ResearchRunOptions(persist_snapshot=False),
    )


def main() -> None:
    head_sha = _head_sha()
    result = ResearchApplication.build(
        repository_attestor=ExampleRepositoryAttestor(head_sha)
    ).run(build_command(head_sha))
    print(
        json.dumps(
            {
                "run_id": result.run_id,
                "core_api_version": result.versions.core_api_version,
                "plugin_api_version": result.versions.plugin_api_version,
                "snapshot_schema_version": result.versions.snapshot_schema_version,
                "execution_completion": result.execution_completion.final_status,
                "research_readiness": result.research_readiness.final_status,
                "artifact_count": len(result.artifacts.envelopes()),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
