def migrate_snapshot_metadata(legacy: dict) -> dict:
    """Add explicit legacy governance fields without changing historical outputs."""
    migrated = dict(legacy)
    defaults = {
        "research_os_version": "1.0.0",
        "parser_version": "legacy-unknown",
        "router_version": "legacy-manufacturing-default",
        "kpi_pack_version": "legacy-manufacturing-default",
        "driver_model_version": "legacy-none",
        "forecast_version": "legacy-forecast",
    }
    for k, v in defaults.items():
        migrated.setdefault(k, v)
    return migrated
