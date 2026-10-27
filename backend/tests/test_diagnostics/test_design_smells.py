"""Tests for graph and metric-based design smell rules."""

from analysis.graph import DirectedGraph
from diagnostics.models import Severity
from diagnostics.rules.smells.cyclic_dependency import CyclicDependencyRule
from diagnostics.rules.smells.dead_code import DeadCodeRule
from diagnostics.rules.smells.deep_inheritance import DeepInheritanceRule
from diagnostics.rules.smells.feature_envy import FeatureEnvyRule
from diagnostics.rules.smells.god_class import GodClassRule
from diagnostics.rules.smells.high_coupling import HighCouplingRule
from diagnostics.rules.smells.long_method import LongMethodRule


class TestGodClassRule:
    rule = GodClassRule(loc_threshold=200, method_threshold=10)

    def test_god_class_detected(self) -> None:
        g = DirectedGraph()
        g.add_node(
            "com.example.MegaManager",
            name="MegaManager",
            node_type="class",
            path="MegaManager.java",
            metrics={"loc": 450, "num_methods": 25, "num_fields": 15},
        )
        findings = self.rule.check_graph(g)
        assert len(findings) == 1
        assert findings[0].rule_id == "SMELL-GOD-CLASS"
        assert findings[0].severity == Severity.HIGH

    def test_compact_class_clean(self) -> None:
        g = DirectedGraph()
        g.add_node(
            "com.example.UserDto",
            name="UserDto",
            node_type="class",
            metrics={"loc": 40, "num_methods": 4, "num_fields": 4},
        )
        findings = self.rule.check_graph(g)
        assert len(findings) == 0


class TestCyclicDependencyRule:
    rule = CyclicDependencyRule()

    def test_cycle_detected(self) -> None:
        g = DirectedGraph()
        g.add_edge("ServiceA", "ServiceB")
        g.add_edge("ServiceB", "ServiceC")
        g.add_edge("ServiceC", "ServiceA")

        findings = self.rule.check_graph(g)
        assert len(findings) >= 3
        cycle_node_ids = {f.node_id for f in findings}
        assert {"ServiceA", "ServiceB", "ServiceC"} <= cycle_node_ids

    def test_dag_clean(self) -> None:
        g = DirectedGraph()
        g.add_edge("Controller", "Service")
        g.add_edge("Service", "Repository")

        findings = self.rule.check_graph(g)
        assert len(findings) == 0


class TestHighCouplingRule:
    rule = HighCouplingRule(fan_out_threshold=4, total_coupling_threshold=6)

    def test_high_fan_out_detected(self) -> None:
        g = DirectedGraph()
        g.add_node("HubService", node_type="class")
        for i in range(6):
            g.add_node(f"Dep{i}", node_type="class")
            g.add_edge("HubService", f"Dep{i}")

        findings = self.rule.check_graph(g)
        assert any(f.node_id == "HubService" for f in findings)

    def test_low_coupling_clean(self) -> None:
        g = DirectedGraph()
        g.add_edge("A", "B")
        findings = self.rule.check_graph(g)
        assert len(findings) == 0


class TestLongMethodRule:
    rule = LongMethodRule(loc_threshold=40, complexity_threshold=8)

    def test_long_method_detected(self) -> None:
        g = DirectedGraph()
        g.add_node(
            "OrderService#processOrder",
            name="processOrder",
            node_type="method",
            metrics={"loc": 90, "cyclomatic_complexity": 14},
        )
        findings = self.rule.check_graph(g)
        assert len(findings) == 1
        assert findings[0].rule_id == "SMELL-LONG-METHOD"

    def test_concise_method_clean(self) -> None:
        g = DirectedGraph()
        g.add_node(
            "OrderService#getId",
            name="getId",
            node_type="method",
            metrics={"loc": 5, "cyclomatic_complexity": 1},
        )
        findings = self.rule.check_graph(g)
        assert len(findings) == 0


class TestDeepInheritanceRule:
    rule = DeepInheritanceRule(depth_threshold=3)

    def test_deep_inheritance_detected(self) -> None:
        g = DirectedGraph()
        g.add_node("Base", node_type="class")
        g.add_node("Level1", node_type="class")
        g.add_node("Level2", node_type="class")
        g.add_node("Level3", node_type="class")
        g.add_node("Level4", node_type="class")

        g.add_edge("Level1", "Base", edge_type="extends")
        g.add_edge("Level2", "Level1", edge_type="extends")
        g.add_edge("Level3", "Level2", edge_type="extends")
        g.add_edge("Level4", "Level3", edge_type="extends")

        findings = self.rule.check_graph(g)
        flagged_nodes = {f.node_id for f in findings}
        assert "Level3" in flagged_nodes or "Level4" in flagged_nodes

    def test_shallow_inheritance_clean(self) -> None:
        g = DirectedGraph()
        g.add_node("Animal", node_type="class")
        g.add_node("Dog", node_type="class")
        g.add_edge("Dog", "Animal", edge_type="extends")

        findings = self.rule.check_graph(g)
        assert len(findings) == 0


class TestFeatureEnvyRule:
    rule = FeatureEnvyRule()

    def test_feature_envy_detected(self) -> None:
        g = DirectedGraph()
        g.add_node("OrderClass", node_type="class")
        g.add_node("CustomerClass", node_type="class")
        g.add_node("OrderClass#printCustomerReport", node_type="method")

        # Contains edge: OrderClass contains printCustomerReport
        g.add_edge("OrderClass", "OrderClass#printCustomerReport", edge_type="contains")

        # printCustomerReport calls CustomerClass methods 4 times, own class 0 times
        for i in range(4):
            c_method = f"CustomerClass#field{i}"
            g.add_node(c_method, node_type="method")
            g.add_edge("OrderClass#printCustomerReport", c_method, edge_type="calls")

        findings = self.rule.check_graph(g)
        assert len(findings) == 1
        assert findings[0].rule_id == "SMELL-FEATURE-ENVY"


class TestDeadCodeRule:
    rule = DeadCodeRule()

    def test_unreferenced_dead_code_detected(self) -> None:
        g = DirectedGraph()
        g.add_node(
            "com.example.LegacyHelper",
            name="LegacyHelper",
            node_type="class",
            path="legacy/helper.py",
            metrics={"loc": 45},
        )
        findings = self.rule.check_graph(g)
        assert len(findings) >= 1
        assert findings[0].rule_id == "SMELL-DEAD-CODE"
