from datetime import datetime, timezone
import pytest
from research_os.snapshots.service import SnapshotService, SnapshotFrozenError

VERSIONS={
    "research_os_version":"1.1.0","dataset_version":"2026-08-29.1",
    "parser_version":"parser@1.0.0","formula_version":"finance-core@2.0.0",
    "router_version":"router@1.0.0","kpi_pack_version":"distributor@1.0.0",
    "driver_model_version":"drivers@1.0.0","forecast_version":"forecast@1.0.0",
    "valuation_version":"valuation@2.0.0","report_version":"report@3.0.0",
}

def test_freeze_persists_all_required_versions():
    svc=SnapshotService()
    snap=svc.freeze("001287.SZ", datetime(2026,8,29,8,tzinfo=timezone.utc), VERSIONS)
    assert snap.versions.research_os_version == "1.1.0"


def test_frozen_snapshot_is_not_mutable():
    svc=SnapshotService(); snap=svc.freeze("X", datetime.now(timezone.utc), VERSIONS)
    with pytest.raises(SnapshotFrozenError):
        svc.replace_versions(snap.snapshot_id,{"report_version":"x"})
