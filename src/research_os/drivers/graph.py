from __future__ import annotations

from .models import DriverEdge, DriverGraphResult, DriverNode, Relation


class DriverValidationError(ValueError):
    pass


class DriverGraph:
    def __init__(self, nodes: list[DriverNode], edges: list[DriverEdge]):
        self.nodes = nodes
        self.edges = edges

    def validate(self):
        ids = {n.driver_id for n in self.nodes}
        for node in self.nodes:
            if node.critical and not node.evidence_ids:
                raise DriverValidationError(f"critical driver {node.driver_id} lacks evidence")
        for edge in self.edges:
            if edge.from_driver not in ids or edge.to_driver not in ids:
                raise DriverValidationError("edge references missing node")
        return True

    @staticmethod
    def _evidence_index(evidence) -> dict[str, list[str]]:
        index: dict[str, list[str]] = {}
        for item in evidence:
            key = item.source_table or item.evidence_id
            index.setdefault(str(key), []).append(item.evidence_id)
        return index

    @staticmethod
    def _ids(index: dict[str, list[str]], *keys: str) -> list[str]:
        result: list[str] = []
        for key in keys:
            for evidence_id in index.get(key, []):
                if evidence_id not in result:
                    result.append(evidence_id)
        return result

    @classmethod
    def _add_node(
        cls,
        nodes: list[DriverNode],
        index: dict[str, list[str]],
        *,
        driver_id: str,
        name: str,
        driver_type: str,
        facts: tuple[str, ...],
        critical: bool = False,
    ) -> None:
        evidence_ids = cls._ids(index, *facts)
        if not evidence_ids:
            return
        nodes.append(
            DriverNode(
                driver_id=driver_id,
                name=name,
                driver_type=driver_type,
                evidence_ids=evidence_ids,
                critical=critical,
            )
        )

    @staticmethod
    def _edge_if_present(
        edges: list[DriverEdge],
        ids: set[str],
        source: str,
        target: str,
        relation: Relation,
    ) -> None:
        if source in ids and target in ids:
            edges.append(
                DriverEdge(
                    from_driver=source,
                    to_driver=target,
                    relation=relation,
                )
            )

    @classmethod
    def build(cls, company_id: str, pack_ids: list[str], evidence):
        index = cls._evidence_index(evidence)
        nodes: list[DriverNode] = []
        edges: list[DriverEdge] = []

        if "distributor" in pack_ids:
            cls._add_node(nodes, index, driver_id="demand", name="Demand", driver_type="demand", facts=("demand", "demand_growth"))
            cls._add_node(nodes, index, driver_id="revenue", name="Revenue", driver_type="volume", facts=("revenue", "revenue_growth"), critical=True)
            cls._add_node(nodes, index, driver_id="gross_margin", name="Gross Margin", driver_type="mix", facts=("gross_margin", "gross_profit"))
            cls._add_node(nodes, index, driver_id="ar", name="Accounts Receivable", driver_type="working_capital", facts=("ar", "avg_ar", "ar_end"))
            cls._add_node(nodes, index, driver_id="inventory", name="Inventory", driver_type="working_capital", facts=("inventory", "avg_inventory", "inventory_end"))
            cls._add_node(nodes, index, driver_id="ap", name="Accounts Payable", driver_type="working_capital", facts=("ap", "avg_ap", "ap_end"))
            cls._add_node(nodes, index, driver_id="nwc", name="Net Working Capital", driver_type="working_capital", facts=("delta_nwc", "working_capital_growth"), critical=True)
            cls._add_node(nodes, index, driver_id="debt", name="Short-term Debt", driver_type="financing", facts=("short_debt", "delta_debt"), critical=True)
            cls._add_node(nodes, index, driver_id="interest", name="Interest Expense", driver_type="financing", facts=("interest_expense", "financing_cost"))
            cls._add_node(nodes, index, driver_id="net_profit", name="Net Profit", driver_type="margin", facts=("net_profit", "net_profit_parent"))
            cls._add_node(nodes, index, driver_id="ocf", name="Operating Cash Flow", driver_type="working_capital", facts=("ocf", "operating_cash_flow"), critical=True)

            ids = {node.driver_id for node in nodes}
            edge_specs: tuple[tuple[str, str, Relation], ...] = (
                ("demand", "revenue", "positive"),
                ("revenue", "ar", "positive"),
                ("revenue", "inventory", "positive"),
                ("ar", "nwc", "positive"),
                ("inventory", "nwc", "positive"),
                ("ap", "nwc", "negative"),
                ("nwc", "debt", "positive"),
                ("debt", "interest", "positive"),
                ("interest", "net_profit", "negative"),
                ("nwc", "ocf", "negative"),
            )
            for source, target, relation in edge_specs:
                cls._edge_if_present(edges, ids, source, target, relation)
        elif "manufacturing" in pack_ids:
            cls._add_node(nodes, index, driver_id="revenue", name="Revenue", driver_type="volume", facts=("revenue", "revenue_growth"), critical=True)
            cls._add_node(nodes, index, driver_id="margin", name="Margin", driver_type="margin", facts=("gross_margin", "net_margin", "margin_change"), critical=True)
            cls._add_node(nodes, index, driver_id="ar", name="Accounts Receivable", driver_type="working_capital", facts=("ar", "ar_begin", "ar_end", "avg_ar"))
            cls._add_node(nodes, index, driver_id="inventory", name="Inventory", driver_type="working_capital", facts=("inventory", "inventory_begin", "inventory_end", "avg_inventory"))
            cls._add_node(nodes, index, driver_id="capex", name="Capital Expenditure", driver_type="capital", facts=("capex_cash", "ppe_begin", "ppe_end"))
            cls._add_node(nodes, index, driver_id="ocf", name="Operating Cash Flow", driver_type="cash", facts=("ocf", "operating_cash_flow"), critical=True)
            fcf_ids = cls._ids(index, "ocf", "operating_cash_flow", "capex_cash")
            if fcf_ids:
                nodes.append(DriverNode(driver_id="fcf", name="Free Cash Flow", driver_type="cash", evidence_ids=fcf_ids, critical=False))

            ids = {node.driver_id for node in nodes}
            edge_specs = (
                ("revenue", "margin", "positive"),
                ("revenue", "ar", "positive"),
                ("revenue", "inventory", "positive"),
                ("margin", "ocf", "positive"),
                ("ar", "ocf", "negative"),
                ("inventory", "ocf", "negative"),
                ("capex", "fcf", "negative"),
                ("ocf", "fcf", "positive"),
            )
            for source, target, relation in edge_specs:
                cls._edge_if_present(edges, ids, source, target, relation)
        else:
            cls._add_node(nodes, index, driver_id="revenue", name="Revenue", driver_type="volume", facts=("revenue", "revenue_growth"))
            cls._add_node(nodes, index, driver_id="margin", name="Margin", driver_type="margin", facts=("gross_margin", "net_margin", "margin_change"))
            cls._add_node(nodes, index, driver_id="fcf", name="Free Cash Flow", driver_type="cash", facts=("ocf", "operating_cash_flow", "capex_cash"))
            ids = {node.driver_id for node in nodes}
            cls._edge_if_present(edges, ids, "revenue", "fcf", "positive")
            cls._edge_if_present(edges, ids, "margin", "fcf", "positive")

        graph = cls(nodes, edges)
        graph.validate()
        return DriverGraphResult(company_id=company_id, nodes=nodes, edges=edges)
