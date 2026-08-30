from pydantic import BaseModel, Field


def safe_ratio(n, d):
    return None if n is None or d is None or d == 0 else n / d


class CapitalEfficiencyResult(BaseModel):
    roic: float | None = None
    incremental_roic: float | None = None
    iwcr: float | None = None


class FundingLoopResult(BaseModel):
    funding_state: str
    incremental_revenue: float | None = None
    incremental_nwc: float | None = None
    incremental_debt: float | None = None
    incremental_equity: float | None = None
    operating_cash_flow: float | None = None
    factoring_balance: float | None = None
    derecognized_receivables: float | None = None
    receivable_transfer_balance: float | None = None
    other_working_capital_financing: float | None = None
    factoring_to_ar: float | None = None
    reason_codes: list[str] = Field(default_factory=list)


class CapitalEfficiencyEngine:
    FACTORING_TO_AR_MATERIALITY = 0.20

    def calculate(self, f):
        b = f.get("invested_capital_begin")
        e = f.get("invested_capital_end")
        avg = None if b is None or e is None else (b + e) / 2
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
            iwcr=safe_ratio(f.get("delta_nwc"), f.get("delta_revenue")),
        )

    def funding_loop(self, f):
        dnwc = f.get("delta_nwc")
        drev = f.get("delta_revenue")
        dd = f.get("delta_debt")
        de = f.get("delta_equity")
        ocf = f.get("operating_cash_flow")
        factoring = f.get("factoring_balance")
        derecognized = f.get("derecognized_receivables")
        transfer = f.get("receivable_transfer_balance")
        other_wc_financing = f.get("other_working_capital_financing")
        ar = f.get("ar")
        reasons = []

        iwcr = safe_ratio(dnwc, drev)
        debt_share = safe_ratio(dd, dnwc)
        factoring_exposure = factoring if factoring is not None else derecognized
        factoring_to_ar = safe_ratio(factoring_exposure, ar)

        if dnwc is not None and dnwc > 0 and iwcr is not None and iwcr >= 0.4:
            reasons.append("HIGH_IWCR")
        if dnwc is not None and dnwc > 0 and debt_share is not None and debt_share >= 0.6:
            reasons.append("DEBT_FUNDS_NWC")
        if ocf is not None and ocf < 0:
            reasons.append("NEGATIVE_OCF")
        if de is not None and de > 0:
            reasons.append("EQUITY_DILUTION")
        if factoring_to_ar is not None and factoring_to_ar >= self.FACTORING_TO_AR_MATERIALITY:
            reasons.append("MATERIAL_FACTORING_EXPOSURE")

        state = "unknown"
        if (
            dnwc is not None
            and dnwc > 0
            and dd is not None
            and ocf is not None
            and ocf < 0
            and debt_share is not None
            and debt_share > 1.2
            and dd > 0
        ):
            state = "stressed"
        elif (
            dnwc is not None
            and dnwc > 0
            and dd is not None
            and debt_share is not None
            and debt_share >= 0.6
            and dd > 0
        ):
            state = "debt_funded"
        elif de is not None and dd is not None and de > 0 and de >= dd:
            state = "equity_funded"
        elif None not in (dnwc, dd, de, ocf) and ocf >= max(dnwc, 0) and dd <= 0 and de <= 0:
            state = "self_funded"
        elif None not in (dnwc, dd, de, ocf):
            state = "mixed"

        return FundingLoopResult(
            funding_state=state,
            incremental_revenue=drev,
            incremental_nwc=dnwc,
            incremental_debt=dd,
            incremental_equity=de,
            operating_cash_flow=ocf,
            factoring_balance=factoring,
            derecognized_receivables=derecognized,
            receivable_transfer_balance=transfer,
            other_working_capital_financing=other_wc_financing,
            factoring_to_ar=factoring_to_ar,
            reason_codes=reasons,
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
