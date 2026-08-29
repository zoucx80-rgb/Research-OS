from .base import MetricResult
from .finance_core import safe_ratio
from research_os.period.models import ReportingPeriod
from research_os.period.resolver import annualized_turns, period_turns, resolve_period_days, turnover_days


class DistributorPack:
    pack_id = "distributor"
    pack_version = "distributor@1.1.0"
    formula_version = "distributor-core@1.2.0"
    eligible_business_models = ("distributor",)
    required_facts = frozenset({"revenue", "cogs", "avg_ar", "avg_inventory", "avg_ap"})
    optional_facts = frozenset({
        "ar", "inventory", "ap", "delta_nwc", "delta_revenue", "short_debt", "equity", "gross_profit",
        "interest_expense", "ocf", "net_profit", "nopat", "avg_invested_capital", "credit_impairment",
        "inventory_impairment", "revenue_growth", "working_capital_growth", "delta_nopat", "delta_invested_capital",
        "delta_debt", "delta_equity", "period_type", "period_start", "period_end", "period_days", "is_cumulative",
        "reporting_period",
    })
    missing_policy = "preserve_missing"
    valuation_preferences = ("pe", "pb", "ev_ebitda", "dcf")
    metric_dependencies = {
        "dso_days": ["avg_ar", "revenue"],
        "dio_days": ["avg_inventory", "cogs"],
        "dpo_days": ["avg_ap", "cogs"],
        "ccc_days": ["avg_ar", "revenue", "avg_inventory", "cogs", "avg_ap"],
        "inventory_turns": ["cogs", "avg_inventory"],
        "inventory_turns_period": ["cogs", "avg_inventory"],
        "inventory_turns_annualized": ["cogs", "avg_inventory"],
        "nwc_intensity": ["ar", "inventory", "ap", "revenue"],
        "gross_profit_to_working_capital": ["gross_profit", "ar", "inventory", "ap"],
        "incremental_nwc_intensity": ["delta_nwc", "delta_revenue"],
        "short_debt_to_inventory": ["short_debt", "inventory"],
        "short_debt_to_equity": ["short_debt", "equity"],
        "interest_to_gross_profit": ["interest_expense", "gross_profit"],
        "credit_impairment_to_gross_profit": ["credit_impairment", "gross_profit"],
        "inventory_impairment_to_gross_profit": ["inventory_impairment", "gross_profit"],
        "cash_conversion": ["ocf", "net_profit"],
        "revenue_growth_vs_working_capital_growth": ["revenue_growth", "working_capital_growth"],
        "funding_loop_debt_share": ["delta_debt", "delta_nwc"],
        "funding_loop_external_share": ["delta_debt", "delta_equity", "delta_nwc"],
        "roic": ["nopat", "avg_invested_capital"],
        "incremental_roic": ["delta_nopat", "delta_invested_capital"],
    }

    def calculate(self, f):
        period = ReportingPeriod.from_facts(f)
        period_days = resolve_period_days(period)
        period_reason = "PERIOD_LENGTH_REQUIRED" if period_days is None else None

        dso = turnover_days(f.get("avg_ar"), f.get("revenue"), period)
        dio = turnover_days(f.get("avg_inventory"), f.get("cogs"), period)
        dpo = turnover_days(f.get("avg_ap"), f.get("cogs"), period)
        ccc = None if None in (dso, dio, dpo) else dso + dio - dpo
        nwc = None if None in (f.get("ar"), f.get("inventory"), f.get("ap")) else f["ar"] + f["inventory"] - f["ap"]
        growth_spread = None if f.get("revenue_growth") is None or f.get("working_capital_growth") is None else f["revenue_growth"] - f["working_capital_growth"]
        external_funding = None if f.get("delta_debt") is None or f.get("delta_equity") is None else f["delta_debt"] + f["delta_equity"]
        inv_turns_period = period_turns(f.get("cogs"), f.get("avg_inventory"))
        inv_turns_annualized = annualized_turns(f.get("cogs"), f.get("avg_inventory"), period)

        vals = {
            "dso_days": dso,
            "dio_days": dio,
            "dpo_days": dpo,
            "ccc_days": ccc,
            "inventory_turns": inv_turns_period,
            "inventory_turns_period": inv_turns_period,
            "inventory_turns_annualized": inv_turns_annualized,
            "nwc_intensity": safe_ratio(nwc, f.get("revenue")),
            "gross_profit_to_working_capital": safe_ratio(f.get("gross_profit"), nwc),
            "incremental_nwc_intensity": safe_ratio(f.get("delta_nwc"), f.get("delta_revenue")),
            "short_debt_to_inventory": safe_ratio(f.get("short_debt"), f.get("inventory")),
            "short_debt_to_equity": safe_ratio(f.get("short_debt"), f.get("equity")),
            "interest_to_gross_profit": safe_ratio(f.get("interest_expense"), f.get("gross_profit")),
            "credit_impairment_to_gross_profit": safe_ratio(f.get("credit_impairment"), f.get("gross_profit")),
            "inventory_impairment_to_gross_profit": safe_ratio(f.get("inventory_impairment"), f.get("gross_profit")),
            "cash_conversion": safe_ratio(f.get("ocf"), f.get("net_profit")) if (f.get("net_profit") or 0) > 0 else None,
            "revenue_growth_vs_working_capital_growth": growth_spread,
            "funding_loop_debt_share": safe_ratio(f.get("delta_debt"), f.get("delta_nwc")),
            "funding_loop_external_share": safe_ratio(external_funding, f.get("delta_nwc")),
            "roic": safe_ratio(f.get("nopat"), f.get("avg_invested_capital")),
            "incremental_roic": safe_ratio(f.get("delta_nopat"), f.get("delta_invested_capital")),
        }
        period_sensitive = {"dso_days", "dio_days", "dpo_days", "ccc_days", "inventory_turns_annualized"}
        return [
            MetricResult(
                metric_id=k,
                value=v,
                formula_version=self.formula_version,
                status="valid" if v is not None else "missing",
                reason_code=(period_reason if v is None and k in period_sensitive else None),
            )
            for k, v in vals.items()
        ]
