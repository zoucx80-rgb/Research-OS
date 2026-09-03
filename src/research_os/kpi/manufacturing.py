class ManufacturingPack:
    """Industry applicability metadata and core metric selection only."""

    pack_id = "manufacturing"
    pack_version = "manufacturing@2.0.0"
    eligible_business_models = ("manufacturing", "manufacturer")
    required_facts = frozenset(
        {
            "revenue",
            "net_profit_parent",
            "assets_begin",
            "assets_end",
            "equity_begin",
            "equity_end",
        }
    )
    optional_facts = frozenset(
        {
            "ocf",
            "ar_begin",
            "ar_end",
            "inventory_begin",
            "inventory_end",
            "cogs",
            "capex_cash",
            "ppe_begin",
            "ppe_end",
        }
    )
    missing_policy = "preserve_missing"
    valuation_preferences = ("pe", "ev_ebitda", "pb", "sotp", "dcf")
    metric_ids = frozenset(
        {
            "roe",
            "net_margin",
            "asset_turnover",
            "equity_multiplier",
            "cash_conversion_parent",
            "ar_days",
            "inventory_days",
            "simple_fcf",
            "fixed_asset_turnover",
            "capex_intensity",
        }
    )


__all__ = ["ManufacturingPack"]
