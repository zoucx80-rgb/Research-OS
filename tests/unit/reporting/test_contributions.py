from research_os.reporting.contributions import ReportContribution


def test_report_contribution_contains_presentation_metadata_only():
    contribution = ReportContribution(
        contribution_id="industry:manufacturing:kpi-section",
        section="Operating KPIs",
        order=200,
        artifact_keys=["kpi.metrics"],
        required=True,
    )
    assert contribution.artifact_keys == ["kpi.metrics"]
    assert contribution.required is True
    assert "final_status" not in ReportContribution.model_fields
    assert "decision_state" not in ReportContribution.model_fields
    assert "completion" not in ReportContribution.model_fields
