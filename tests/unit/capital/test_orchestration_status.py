from research_os.capital.engine import FundingLoopResult
from research_os.orchestration import ResearchOS


def test_unknown_funding_loop_is_insufficient_evidence():
    result = FundingLoopResult(funding_state="unknown")
    assert ResearchOS._funding_status(result) == "INSUFFICIENT_EVIDENCE"


def test_classified_funding_loop_is_pass():
    result = FundingLoopResult(funding_state="debt_funded", incremental_nwc=10.0, incremental_debt=8.0)
    assert ResearchOS._funding_status(result) == "PASS"
