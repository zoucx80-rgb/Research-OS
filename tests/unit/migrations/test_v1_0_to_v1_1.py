from research_os.migrations.v1_0_to_v1_1 import migrate_snapshot_metadata

def test_legacy_snapshot_gets_explicit_v1_defaults():
    m=migrate_snapshot_metadata({"dataset_version":"2026-08-25.2","formula_version":"finance-core@1.8.0","valuation_version":"valuation@1.3.2","report_version":"gaona-template@2.1"})
    assert m["research_os_version"]=="1.0.0"
    assert m["router_version"]=="legacy-manufacturing-default"
    assert m["dataset_version"]=="2026-08-25.2"
