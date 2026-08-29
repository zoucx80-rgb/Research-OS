from research_os.reporting.summary import DecisionSummaryBuilder

def test_decision_summary_contains_required_front_page_fields():
    s=DecisionSummaryBuilder().build({"company_id":"X","business_model":"distributor","primary_thesis":"Growth converts to cash",
      "thesis_state":"weakening","fundamental_state":"improving","expectation_state":"mixed","valuation_state":"fair",
      "evidence_confidence":"B","top_drivers":["revenue","nwc","debt","extra"],"top_risks":["cash","inventory","debt","extra"],
      "next_verification_event":"2026Q3","research_os_version":"1.1.0","supporting_claim_ids":["c1"]})
    assert s.business_model=="distributor" and len(s.top_drivers)==3 and len(s.top_risks)==3
    assert s.research_os_version=="1.1.0"

def test_standard_deep_research_report_has_all_v1_1_sections_in_order():
    from research_os.reporting.summary import ResearchReportModel
    report=ResearchReportModel.standard()
    assert report.sections[0]=="Executive Decision Summary"
    assert "Anti-Thesis" in report.sections
    assert "Falsifiers" in report.sections
    assert "Evidence Ledger" in report.sections
    assert report.sections[-1]=="Version & Data Snapshot"
    assert len(report.sections)==18
