from pydantic import BaseModel, Field

from research_os.period.comparison import comparable_ratio, common_comparison_basis
from research_os.policies import PolicyRegistry, builtin_policy_registry


def safe_ratio(n, d):
    return None if n is None or d is None or d == 0 else n / d


class CapitalEfficiencyResult(BaseModel):
    roic: float | None = None
    incremental_roic: float | None = None
    iwcr: float | None = None
    iwcr_reason_code: str | None = None


class FundingLoopResult(BaseModel):
    funding_state: str
    incremental_revenue: float | None = None
    incremental_nwc: float | None = None
    incremental_debt: float | None = None
    incremental_equity: float | None = None
    reported_equity_change: float | None = None
    operating_cash_flow: float | None = None
    factoring_balance: float | None = None
    derecognized_receivables: float | None = None
    receivable_transfer_balance: float | None = None
    other_working_capital_financing: float | None = None
    factoring_to_ar: float | None = None
    reason_codes: list[str] = Field(default_factory=list)
    comparison_basis_status: str = "NOT_APPLICABLE"
    comparison_basis_errors: list[str] = Field(default_factory=list)


class CapitalEfficiencyEngine:
    def __init__(self, *, policy_registry: PolicyRegistry | None = None) -> None:
        self._policy = policy_registry or builtin_policy_registry()

    def calculate(self, f):
        b = f.get("invested_capital_begin")
        e = f.get("invested_capital_end")
        avg = None if b is None or e is None else (b + e) / 2
        iwcr, iwcr_reason = comparable_ratio(f, "delta_nwc", "delta_revenue")
        return CapitalEfficiencyResult(
            roic=safe_ratio(f.get("nopat"), avg),
            incremental_roic=safe_ratio(
                None
                if f.get("nopat") is None or f.get("nopat_prev") is None
                else f["nopat"] - f["nopat_prev"],
                None
                if e is None or f.get("invested_capital_prev") is None
                else e - f["invested_capital_prev"],
            ),
            iwcr=iwcr,
            iwcr_reason_code=iwcr_reason,
        )

    def funding_loop(self, f):
        factoring_materiality = float(
            self._policy.value("funding_loop", "factoring_to_ar_materiality")
        )
        high_iwcr = float(self._policy.value("funding_loop", "incremental_working_capital_high"))
        high_debt_share = float(self._policy.value("funding_loop", "debt_share_high"))
        stressed_debt_share = float(self._policy.value("funding_loop", "debt_share_stressed"))
        dnwc = f.get("delta_nwc")
        drev = f.get("delta_revenue")
        dd = f.get("delta_debt")
        reported_equity_change = f.get("delta_equity")
        de = f.get("external_equity_financing")
        ocf = f.get("operating_cash_flow")
        factoring = f.get("factoring_balance")
        derecognized = f.get("derecognized_receivables")
        transfer = f.get("receivable_transfer_balance")
        other_wc_financing = f.get("other_working_capital_financing")
        ar = f.get("ar")
        reasons = []

        iwcr, iwcr_reason = comparable_ratio(f, "delta_nwc", "delta_revenue")
        debt_share, debt_share_reason = comparable_ratio(f, "delta_debt", "delta_nwc")
        external_basis_reason = None
        if None not in (dnwc, dd, de):
            external_basis_reason = common_comparison_basis(
                f,
                ("delta_nwc", "delta_debt", "external_equity_financing"),
            )
        comparison_errors = list(
            dict.fromkeys(
                reason
                for reason in (iwcr_reason, debt_share_reason, external_basis_reason)
                if reason is not None
            )
        )
        comparison_basis_status = (
            "INSUFFICIENT_EVIDENCE"
            if comparison_errors
            else "PASS"
            if any(
                all(value is not None for value in values)
                for values in ((dnwc, drev), (dd, dnwc), (de, dd, dnwc))
            )
            else "NOT_APPLICABLE"
        )
        factoring_exposure = factoring if factoring is not None else derecognized
        factoring_to_ar = safe_ratio(factoring_exposure, ar)

        if dnwc is not None and dnwc > 0 and iwcr is not None and iwcr >= high_iwcr:
            reasons.append("HIGH_IWCR")
        if (
            dnwc is not None
            and dnwc > 0
            and debt_share is not None
            and debt_share >= high_debt_share
        ):
            reasons.append("DEBT_FUNDS_NWC")
        if ocf is not None and ocf < 0:
            reasons.append("NEGATIVE_OCF")
        if f.get("equity_dilution") is True:
            reasons.append("EQUITY_DILUTION")
        if factoring_to_ar is not None and factoring_to_ar >= factoring_materiality:
            reasons.append("MATERIAL_FACTORING_EXPOSURE")

        state = "unknown"
        if (
            dnwc is not None
            and dnwc > 0
            and dd is not None
            and ocf is not None
            and ocf < 0
            and debt_share is not None
            and debt_share > stressed_debt_share
            and dd > 0
        ):
            state = "stressed"
        elif (
            dnwc is not None
            and dnwc > 0
            and dd is not None
            and debt_share is not None
            and debt_share >= high_debt_share
            and dd > 0
        ):
            state = "debt_funded"
        elif (
            None not in (dnwc, de, dd)
            and external_basis_reason is None
            and dnwc > 0
            and de > 0
            and de >= dd
        ):
            state = "equity_funded"
        elif (
            None not in (dnwc, dd, de, ocf)
            and debt_share_reason is None
            and external_basis_reason is None
            and ocf >= max(dnwc, 0)
            and dd <= 0
            and de <= 0
        ):
            state = "self_funded"
        elif (
            None not in (dnwc, dd, de, ocf)
            and debt_share_reason is None
            and external_basis_reason is None
        ):
            state = "mixed"

        return FundingLoopResult(
            funding_state=state,
            incremental_revenue=drev,
            incremental_nwc=dnwc,
            incremental_debt=dd,
            incremental_equity=de,
            reported_equity_change=reported_equity_change,
            operating_cash_flow=ocf,
            factoring_balance=factoring,
            derecognized_receivables=derecognized,
            receivable_transfer_balance=transfer,
            other_working_capital_financing=other_wc_financing,
            factoring_to_ar=factoring_to_ar,
            reason_codes=reasons,
            comparison_basis_status=comparison_basis_status,
            comparison_basis_errors=comparison_errors,
        )

    def growth_quality_components(self, f):
        return {
            "growth": f.get("revenue_growth"),
            "margin": f.get("margin_change"),
            "roic": f.get("roic"),
            "cash_conversion": f.get("cash_conversion"),
            "incremental_nwc_efficiency": f.get("incremental_nwc_efficiency"),
            "leverage_deterioration": f.get("leverage_deterioration"),
            "dilution": f.get("dilution"),
        }
