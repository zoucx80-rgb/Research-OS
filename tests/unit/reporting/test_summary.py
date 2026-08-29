from research_os.reporting.summary import DecisionSummaryBuilder


def test_decision_summary_contains_required_front_page_fields(canonical_report_result_factory):
    result = canonical_report_result_factory(
        artifacts={
            "drivers.graph": {
                "nodes": [
                    {"driver_id": "revenue", "name": "Revenue", "critical": True},
                    {"driver_id": "nwc", "name": "Net Working Capital", "critical": True},
                    {"driver_id": "debt", "name": "Debt", "critical": True},
                    {"driver_id": "extra", "name": "Extra", "critical": True},
                ]
            },
            "capital.funding_loop": {
                "reason_codes": ["cash", "inventory", "debt", "extra"]
            },
        }
    )
    summary = DecisionSummaryBuilder().build(result)
    assert summary.business_model == "distributor"
    assert len(summary.top_drivers) == 3
    assert len(summary.top_risks) == 3
    assert summary.research_os_version == result.baseline.research_os_version


def test_standard_deep_research_report_has_all_v1_1_sections_in_order():
    from research_os.reporting.summary import ResearchReportModel

    report = ResearchReportModel.standard()
    assert report.sections[0] == "Executive Decision Summary"
    assert "Anti-Thesis" in report.sections
    assert "Falsifiers" in report.sections
    assert "Evidence Ledger" in report.sections
    assert report.sections[-1] == "Version & Data Snapshot"
    assert len(report.sections) == 18
