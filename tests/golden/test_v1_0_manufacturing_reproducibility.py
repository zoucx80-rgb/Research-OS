import json
from pathlib import Path
import pytest
from research_os.kpi.manufacturing import ManufacturingPack

def test_legacy_manufacturing_outputs_are_reproducible():
    fixture=json.loads(Path("tests/fixtures/manufacturing_legacy_snapshot.json").read_text())
    actual={m.metric_id:m.value for m in ManufacturingPack().calculate(fixture["facts"])}
    for k,v in fixture["expected"].items(): assert actual[k]==pytest.approx(v)
