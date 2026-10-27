"""Unit tests for coupling metrics (Fan-in, Fan-out, Instability I = Ce / (Ca + Ce))."""

from __future__ import annotations

import pytest

from analysis.coupling import compute_coupling_metrics
from analysis.graph import DirectedGraph


class TestCouplingMetrics:
    def test_node_instability_extremes(self) -> None:
        g = DirectedGraph()
        # StableNode is depended on by 3 callers, but depends on nothing
        # Ca = 3, Ce = 0 -> I = 0.0
        g.add_edge("Caller1", "StableNode")
        g.add_edge("Caller2", "StableNode")
        g.add_edge("Caller3", "StableNode")

        # UnstableController calls 3 services, but nothing calls it
        # Ca = 0, Ce = 3 -> I = 1.0
        g.add_edge("UnstableController", "Service1")
        g.add_edge("UnstableController", "Service2")
        g.add_edge("UnstableController", "Service3")

        # BalancedNode: Ca = 2, Ce = 2 -> I = 2 / 4 = 0.5
        g.add_edge("A", "BalancedNode")
        g.add_edge("B", "BalancedNode")
        g.add_edge("BalancedNode", "X")
        g.add_edge("BalancedNode", "Y")

        # IsolatedNode: Ca = 0, Ce = 0 -> I = 0.0
        g.add_node("IsolatedNode")

        res = compute_coupling_metrics(g)
        node_map = {n.node_id: n for n in res.nodes}

        assert node_map["StableNode"].fan_in == 3
        assert node_map["StableNode"].fan_out == 0
        assert node_map["StableNode"].instability == 0.0

        assert node_map["UnstableController"].fan_in == 0
        assert node_map["UnstableController"].fan_out == 3
        assert node_map["UnstableController"].instability == 1.0

        assert node_map["BalancedNode"].fan_in == 2
        assert node_map["BalancedNode"].fan_out == 2
        assert node_map["BalancedNode"].instability == 0.5

        assert node_map["IsolatedNode"].fan_in == 0
        assert node_map["IsolatedNode"].fan_out == 0
        assert node_map["IsolatedNode"].instability == 0.0

    def test_package_level_instability_and_distance(self) -> None:
        g = DirectedGraph()
        # Package 1: com.example.web (Controllers)
        g.add_node("com.example.web.UserController", node_type="class")
        g.add_node("com.example.web.OrderController", node_type="class")

        # Package 2: com.example.service (Services)
        g.add_node("com.example.service.UserService", node_type="class")
        g.add_node("com.example.service.OrderService", node_type="interface")

        # Dependencies across packages
        g.add_edge("com.example.web.UserController", "com.example.service.UserService")
        g.add_edge("com.example.web.OrderController", "com.example.service.OrderService")

        res = compute_coupling_metrics(g)
        pkg_map = {p.package_name: p for p in res.packages}

        web_pkg = pkg_map["com.example.web"]
        assert web_pkg.ca == 0
        assert web_pkg.ce == 2
        assert web_pkg.instability == 1.0  # Maximally unstable

        svc_pkg = pkg_map["com.example.service"]
        assert svc_pkg.ca == 2
        assert svc_pkg.ce == 0
        assert svc_pkg.instability == 0.0  # Maximally stable
        assert svc_pkg.abstractness == 0.5  # 1 of 2 is interface
        assert svc_pkg.distance == pytest.approx(0.5)  # |0.5 + 0.0 - 1.0| = 0.5
