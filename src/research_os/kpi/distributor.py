from research_os.period.models import ReportingPeriod
from research_os.period.resolver import (
    annualized_turns,
    period_turns,
    resolve_period_days,
    turnover_days,
)
from research_os.period.comparison import comparable_ratio, common_comparison_basis

from .base import MetricResult
from .finance_core import safe_ratio


class DistributorPack:
    pack_id = "distributor"
    pack_version = "distributor@1.3.0"
    formula_version = "distributor-core@1.3.0"
    eligible_business_models = ("distributor",)
    required_facts = frozenset({"revenue", "cogs", "avg_ar", "avg_inventory", "avg_ap"})
    optional_facts = frozenset({
        "ar", "inventory", "ap", "delta_nwc", "delta_revenue", "short_debt", "equity", "gross_profit",
        "interest_expense", "financing_cost", "ocf", "net_profit", "nopat", "avg_invested_capital",
        "credit_impairment", "inventory_impairment", "revenue_growth", "working_capital_growth", "delta_nopat",
        "delta_invested_capital", "delta_debt", "delta_equity", "external_equity_financing", "equity_dilution",
        "delta_nwc_comparison_basis", "delta_revenue_comparison_basis", "delta_debt_comparison_basis",
        "external_equity_financing_comparison_basis", "factoring_balance", "derecognized_receivables",
        "receivable_transfer_balance", "other_working_capital_financing", "period_type", "period_start", "period_end",
        "period_days", "is_cumulative", "reporting_period",
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
        "incremental_nwc_intensity": ["delta_nwc", "delta_revenue", "delta_nwc_comparison_basis", "delta_revenue_comparison_basis"],
        "short_debt_to_inventory": ["short_debt", "inventory"],
        "short_debt_to_equity": ["short_debt", "equity"],
        "interest_to_gross_profit": ["interest_expense", "gross_profit"],
        "total_financing_cost_to_gross_profit": ["financing_cost", "gross_profit"],
        "factoring_to_ar": ["factoring_balance", "derecognized_receivables", "ar"],
        "working_capital_financing_to_gross_profit": [
            "factoring_balance", "derecognized_receivables", "receivable_transfer_balance",
            "other_working_capital_financing", "gross_profit",
        ],
        "credit_impairment_to_gross_profit": ["credit_impairment", "gross_profit"],
        "inventory_impairment_to_gross_profit": ["inventory_impairment", "gross_profit"],
        "cash_conversion": ["ocf", "net_profit"],
        "revenue_growth_vs_working_capital_growth": ["revenue_growth", "working_capital_growth"],
        "funding_loop_debt_share": ["delta_debt", "delta_nwc", "delta_debt_comparison_basis", "delta_nwc_comparison_basis"],
        "funding_loop_external_share": ["delta_debt", "external_equity_financing", "delta_nwc", "delta_debt_comparison_basis", "external_equity_financing_comparison_basis", "delta_nwc_comparison_basis"],
        "roic": ["nopat", "avg_invested_capital"],
        "incremental_roic": ["delta_nopat", "delta_invested_capital"],
    }

    @staticmethod
    def _period_label(period: ReportingPeriod) -> str | None:
        if period.period_end is not None:
            return f"{period.period_end.year}{period.period_type}"
        return period.period_type or None

    @staticmethod
    def _working_capital_financing(f) -> float | None:
        factoring = f.get("factoring_balance")
        derecognized = f.get("derecognized_receivables")
        primary_receivable_financing = factoring if factoring is not None else derecognized
        pieces = [
            primary_receivable_financing,
            f.get("receivable_transfer_balance"),
            f.get("other_working_capital_financing"),
        ]
        available = [value for value in pieces if value is not None]
        return sum(available) if available else None

    def calculate(self, f):
        period = ReportingPeriod.from_facts(f)
        period_days = resolve_period_days(period)
        period_reason = "PERIOD_LENGTH_REQUIRED" if period_days is None else None
        period_label = self._period_label(period)

        dso = turnover_days(f.get("avg_ar"), f.get("revenue"), period)
        dio = turnover_days(f.get("avg_inventory"), f.get("cogs"), period)
        dpo = turnover_days(f.get("avg_ap"), f.get("cogs"), period)
        ccc = None if None in (dso, dio, dpo) else dso + dio - dpo
        nwc = None if None in (f.get("ar"), f.get("inventory"), f.get("ap")) else f["ar"] + f["inventory"] - f["ap"]
        growth_spread = None if f.get("revenue_growth") is None or f.get("working_capital_growth") is None else f["revenue_growth"] - f["working_capital_growth"]
        incremental_nwc_intensity, incremental_nwc_reason = comparable_ratio(
            f,
            "delta_nwc",
            "delta_revenue",
        )
        debt_share, debt_share_reason = comparable_ratio(f, "delta_debt", "delta_nwc")
        external_funding = None
        external_share_reason = None
        if None not in (
            f.get("delta_debt"),
            f.get("external_equity_financing"),
            f.get("delta_nwc"),
        ):
            external_share_reason = common_comparison_basis(
                f,
                ("delta_debt", "external_equity_financing", "delta_nwc"),
            )
            if external_share_reason is None:
                external_funding = f["delta_debt"] + f["external_equity_financing"]
        inv_turns_period = period_turns(f.get("cogs"), f.get("avg_inventory"))
        inv_turns_annualized = annualized_turns(f.get("cogs"), f.get("avg_inventory"), period)
        factoring_exposure = f.get("factoring_balance")
        if factoring_exposure is None:
            factoring_exposure = f.get("derecognized_receivables")
        wc_financing = self._working_capital_financing(f)

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
            "incremental_nwc_intensity": incremental_nwc_intensity,
            "short_debt_to_inventory": safe_ratio(f.get("short_debt"), f.get("inventory")),
            "short_debt_to_equity": safe_ratio(f.get("short_debt"), f.get("equity")),
            "interest_to_gross_profit": safe_ratio(f.get("interest_expense"), f.get("gross_profit")),
            "total_financing_cost_to_gross_profit": safe_ratio(f.get("financing_cost"), f.get("gross_profit")),
            "factoring_to_ar": safe_ratio(factoring_exposure, f.get("ar")),
            "working_capital_financing_to_gross_profit": safe_ratio(wc_financing, f.get("gross_profit")),
            "credit_impairment_to_gross_profit": safe_ratio(f.get("credit_impairment"), f.get("gross_profit")),
            "inventory_impairment_to_gross_profit": safe_ratio(f.get("inventory_impairment"), f.get("gross_profit")),
            "cash_conversion": safe_ratio(f.get("ocf"), f.get("net_profit")) if (f.get("net_profit") or 0) > 0 else None,
            "revenue_growth_vs_working_capital_growth": growth_spread,
            "funding_loop_debt_share": debt_share,
            "funding_loop_external_share": safe_ratio(external_funding, f.get("delta_nwc")),
            "roic": safe_ratio(f.get("nopat"), f.get("avg_invested_capital")),
            "incremental_roic": safe_ratio(f.get("delta_nopat"), f.get("delta_invested_capital")),
        }
        day_metrics = {"dso_days", "dio_days", "dpo_days", "ccc_days"}
        turns_metrics = {"inventory_turns", "inventory_turns_period", "inventory_turns_annualized"}
        percent_metrics = set(vals) - day_metrics - turns_metrics
        period_sensitive = day_metrics | {"inventory_turns_annualized"}
        comparison_reasons = {
            "incremental_nwc_intensity": incremental_nwc_reason,
            "funding_loop_debt_share": debt_share_reason,
            "funding_loop_external_share": external_share_reason,
        }
        results = []
        for metric_id, value in vals.items():
            unit = "days" if metric_id in day_metrics else "x" if metric_id in turns_metrics else "percent"
            annualized = True if metric_id == "inventory_turns_annualized" else False
            results.append(
                MetricResult(
                    metric_id=metric_id,
                    value=value,
                    unit=unit,
                    formula_version=self.formula_version,
                    status="valid" if value is not None else "missing",
                    reason_code=(
                        comparison_reasons.get(metric_id)
                        or (period_reason if value is None and metric_id in period_sensitive else None)
                    ),
                    period_label=period_label,
                    period_days=period_days,
                    annualized=annualized,
                )
            )
        return results
