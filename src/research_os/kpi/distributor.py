class DistributorPack:
    """Industry applicability metadata and core metric selection only."""

    pack_id = "distributor"
    pack_version = "distributor@2.0.0"
    eligible_business_models = ("distributor",)
    required_facts = frozenset({"revenue", "cogs", "avg_ar", "avg_inventory", "avg_ap"})
    optional_facts = frozenset(
        {
            "ar",
            "inventory",
            "ap",
            "delta_nwc",
            "delta_revenue",
            "short_debt",
            "equity",
            "gross_profit",
            "interest_expense",
            "financing_cost",
            "ocf",
            "net_profit",
            "nopat",
            "avg_invested_capital",
            "credit_impairment",
            "inventory_impairment",
            "revenue_growth",
            "working_capital_growth",
            "delta_nopat",
            "delta_invested_capital",
            "delta_debt",
            "external_equity_financing",
            "factoring_balance",
            "derecognized_receivables",
            "receivable_transfer_balance",
            "other_working_capital_financing",
        }
    )
    missing_policy = "preserve_missing"
    valuation_preferences = ("pe", "pb", "ev_ebitda", "dcf")
    metric_ids = frozenset(
        {
            "dso_days",
            "dio_days",
            "dpo_days",
            "ccc_days",
            "inventory_turns",
            "inventory_turns_period",
            "inventory_turns_annualized",
            "nwc_intensity",
            "gross_profit_to_working_capital",
            "incremental_nwc_intensity",
            "short_debt_to_inventory",
            "short_debt_to_equity",
            "interest_to_gross_profit",
            "total_financing_cost_to_gross_profit",
            "factoring_to_ar",
            "working_capital_financing_to_gross_profit",
            "credit_impairment_to_gross_profit",
            "inventory_impairment_to_gross_profit",
            "cash_conversion",
            "revenue_growth_vs_working_capital_growth",
            "funding_loop_debt_share",
            "funding_loop_external_share",
            "roic",
            "incremental_roic",
        }
    )


__all__ = ["DistributorPack"]
