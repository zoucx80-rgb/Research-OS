from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from hypothesis import given, strategies as st

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.temporal.models import FinancialPeriodObservation
from research_os.temporal.service import TemporalAnalysisService


DECISION_TS = datetime(2026, 4, 1, tzinfo=timezone.utc)


def _observations() -> tuple[FinancialPeriodObservation, ...]:
    return tuple(
        FinancialPeriodObservation(
            metric_id="revenue",
            reporting_period=ReportingPeriod(
                period_type="FY",
                period_start=date(year, 1, 1),
                period_end=date(year, 12, 31),
                period_days=366 if year % 4 == 0 else 365,
                is_cumulative=True,
            ),
            period_kind="FLOW",
            value=Decimal(value),
            unit="CNY",
            accounting_scope=AccountingScope(consolidation="consolidated"),
            value_kind="reported",
            comparison_basis="YOY_PERIOD",
            available_ts=datetime(year + 1, 3, 31, tzinfo=timezone.utc),
            evidence_refs=(
                EvidenceRef(
                    evidence_id=f"ev:revenue:{year}",
                    revision=1,
                    content_fingerprint="a" * 64,
                ),
            ),
        )
        for year, value in ((2023, "100"), (2024, "110"), (2025, "121"))
    )


@given(st.permutations(_observations()))
def test_input_order_does_not_change_temporal_analysis(
    items: list[FinancialPeriodObservation],
) -> None:
    service = TemporalAnalysisService()

    assert service.analyze(tuple(items), decision_ts=DECISION_TS) == service.analyze(
        _observations(),
        decision_ts=DECISION_TS,
    )
