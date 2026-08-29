from pydantic import BaseModel, Field

def safe_ratio(n,d): return None if n is None or d is None or d==0 else n/d

class CapitalEfficiencyResult(BaseModel):
    roic: float|None=None
    incremental_roic: float|None=None
    iwcr: float|None=None

class FundingLoopResult(BaseModel):
    funding_state: str
    incremental_revenue: float|None=None
    incremental_nwc: float|None=None
    incremental_debt: float|None=None
    incremental_equity: float|None=None
    operating_cash_flow: float|None=None
    reason_codes: list[str]=Field(default_factory=list)

class CapitalEfficiencyEngine:
    def calculate(self,f):
        b=f.get("invested_capital_begin"); e=f.get("invested_capital_end")
        avg=None if b is None or e is None else (b+e)/2
        return CapitalEfficiencyResult(roic=safe_ratio(f.get("nopat"),avg),
            incremental_roic=safe_ratio(None if f.get("nopat") is None or f.get("nopat_prev") is None else f["nopat"]-f["nopat_prev"],
                                        None if e is None or f.get("invested_capital_prev") is None else e-f["invested_capital_prev"]),
            iwcr=safe_ratio(f.get("delta_nwc"),f.get("delta_revenue")))
    def funding_loop(self,f):
        dnwc=f.get("delta_nwc") or 0; dd=f.get("delta_debt") or 0; de=f.get("delta_equity") or 0; ocf=f.get("operating_cash_flow")
        reasons=[]
        if dnwc>0 and safe_ratio(dnwc,f.get("delta_revenue")) is not None and safe_ratio(dnwc,f.get("delta_revenue"))>=.4: reasons.append("HIGH_IWCR")
        if dnwc>0 and dd/dnwc>=.6: reasons.append("DEBT_FUNDS_NWC")
        if ocf is not None and ocf<0: reasons.append("NEGATIVE_OCF")
        if de>0: reasons.append("EQUITY_DILUTION")
        if dd>0 and dnwc>0 and dd/dnwc>=.6: state="debt_funded"
        elif de>0 and de>=dd: state="equity_funded"
        elif ocf is not None and ocf>=max(dnwc,0): state="self_funded"
        else: state="mixed"
        if (ocf or 0)<0 and dd>max(dnwc,0)*1.2 and dd>0: state="stressed"
        return FundingLoopResult(funding_state=state,incremental_revenue=f.get("delta_revenue"),incremental_nwc=f.get("delta_nwc"),incremental_debt=f.get("delta_debt"),incremental_equity=f.get("delta_equity"),operating_cash_flow=ocf,reason_codes=reasons)

    def growth_quality_components(self,f):
        return {
            "growth":f.get("revenue_growth"),
            "margin":f.get("margin_change"),
            "roic":f.get("roic"),
            "cash_conversion":f.get("cash_conversion"),
            "incremental_nwc_efficiency":f.get("incremental_nwc_efficiency"),
            "leverage_deterioration":f.get("leverage_deterioration"),
            "dilution":f.get("dilution"),
        }
