"""Unit tests for dead code candidate identification."""

from __future__ import annotations


from analysis.dead_code import find_dead_code_candidates
from analysis.graph import DirectedGraph


class TestDeadCodeDetection:
    def test_distinguish_dead_code_from_entry_points(self) -> None:
        g = DirectedGraph()

        # 1. Real Dead Code: an unused helper class with 0 incoming dependencies
        g.add_node(
            "LegacyCalculatorHelper",
            name="LegacyCalculatorHelper",
            node_type="class",
            path="src/utils/legacy.py",
            metrics={"loc": 150},
        )
        g.add_edge("LegacyCalculatorHelper", "SharedUtils")  # Out-degree > 0, In-degree == 0

        # 2. Main function: 0 in-degree, but name is main -> NOT dead code
        g.add_node("main_func", name="main", node_type="function", path="src/main.py", metrics={"loc": 25})

        # 3. Web controller: 0 in-degree, but annotated with @app.get -> NOT dead code
        g.add_node(
            "UserController",
            name="UserController",
            node_type="class",
            path="src/api/user.py",
            annotations=["@app.get", "@router.post"],
            metrics={"loc": 80},
        )

        # 4. Test method: 0 in-degree, but in test file -> NOT dead code
        g.add_node(
            "test_user_login",
            name="test_user_login",
            node_type="function",
            path="tests/test_user.py",
            metrics={"loc": 15},
        )

        # 5. Shared active node: has incoming dependencies -> NOT dead code
        g.add_node("SharedUtils", name="SharedUtils", node_type="class", path="src/utils.py", metrics={"loc": 50})

        res = find_dead_code_candidates(g)

        assert res.total_candidates == 1
        candidate = res.candidates[0]
        assert candidate.node_id == "LegacyCalculatorHelper"
        assert candidate.loc == 150
        assert candidate.confidence == 0.95
        assert res.total_wasted_loc == 150
