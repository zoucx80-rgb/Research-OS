from .models import DriverNode, DriverEdge, DriverGraphResult

class DriverValidationError(ValueError): pass

class DriverGraph:
    def __init__(self,nodes:list[DriverNode],edges:list[DriverEdge]): self.nodes=nodes; self.edges=edges
    def validate(self):
        ids={n.driver_id for n in self.nodes}
        for n in self.nodes:
            if n.critical and not n.evidence_ids: raise DriverValidationError(f"critical driver {n.driver_id} lacks evidence")
        for e in self.edges:
            if e.from_driver not in ids or e.to_driver not in ids: raise DriverValidationError("edge references missing node")
        return True
    @classmethod
    def build(cls,company_id:str,pack_ids:list[str],evidence):
        ev_ids=[e.evidence_id for e in evidence]
        if "distributor" in pack_ids:
            names=[("demand","Demand","demand"),("revenue","Revenue","volume"),("gross_margin","Gross Margin","mix"),
                   ("ar","Accounts Receivable","working_capital"),("inventory","Inventory","working_capital"),("ap","Accounts Payable","working_capital"),
                   ("nwc","Net Working Capital","working_capital"),("debt","Short-term Debt","financing"),("interest","Interest Expense","financing"),
                   ("net_profit","Net Profit","margin"),("ocf","Operating Cash Flow","working_capital")]
            nodes=[DriverNode(driver_id=i,name=n,driver_type=t,evidence_ids=ev_ids,critical=i in {"revenue","nwc","debt","ocf"}) for i,n,t in names]
            edges=[DriverEdge(from_driver="demand",to_driver="revenue",relation="positive"),DriverEdge(from_driver="revenue",to_driver="ar",relation="positive"),
                   DriverEdge(from_driver="revenue",to_driver="inventory",relation="positive"),DriverEdge(from_driver="ar",to_driver="nwc",relation="positive"),
                   DriverEdge(from_driver="inventory",to_driver="nwc",relation="positive"),DriverEdge(from_driver="ap",to_driver="nwc",relation="negative"),
                   DriverEdge(from_driver="nwc",to_driver="debt",relation="positive"),DriverEdge(from_driver="debt",to_driver="interest",relation="positive"),
                   DriverEdge(from_driver="interest",to_driver="net_profit",relation="negative"),DriverEdge(from_driver="nwc",to_driver="ocf",relation="negative")]
        else:
            nodes=[DriverNode(driver_id="revenue",name="Revenue",driver_type="volume",evidence_ids=ev_ids,critical=True),
                   DriverNode(driver_id="margin",name="Margin",driver_type="margin",evidence_ids=ev_ids,critical=True),
                   DriverNode(driver_id="fcf",name="Free Cash Flow",driver_type="cash",evidence_ids=ev_ids,critical=True)]
            edges=[DriverEdge(from_driver="revenue",to_driver="fcf",relation="positive"),DriverEdge(from_driver="margin",to_driver="fcf",relation="positive")]
        g=cls(nodes,edges); g.validate(); return DriverGraphResult(company_id=company_id,nodes=nodes,edges=edges)
