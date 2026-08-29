import pytest
from research_os.drivers.models import DriverNode, DriverEdge
from research_os.drivers.graph import DriverGraph, DriverValidationError

def test_critical_driver_without_evidence_is_invalid():
    g=DriverGraph(nodes=[DriverNode(driver_id="demand",name="AI demand",driver_type="demand",critical=True,evidence_ids=[])],edges=[])
    with pytest.raises(DriverValidationError): g.validate()

def test_edge_cannot_reference_missing_node():
    g=DriverGraph(nodes=[DriverNode(driver_id="a",name="A",driver_type="demand",evidence_ids=["e1"])],
                  edges=[DriverEdge(from_driver="a",to_driver="missing",relation="positive")])
    with pytest.raises(DriverValidationError): g.validate()
