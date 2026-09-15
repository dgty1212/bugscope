import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services import context_selector as selector


def symbol(key):
    return SimpleNamespace(id=key, file_path=f"src/N{key}.java", class_name=f"N{key}",
                           symbol_name="run", start_line=2, end_line=4, content="code")


class SelectorBudgetTests(unittest.TestCase):
    def invoke(self, edges, seeds=(1,), semantic_ids=(), budget=5, policy="balanced"):
        nodes = {i: symbol(i) for i in range(1, 30)}
        semantic = [SimpleNamespace(file_path=f"src/N{i}.java", start_line=1, end_line=5,
                    source_id=100+i, context_type="semantic", symbol_name=None)
                    for i in semantic_ids]
        patches = [
            patch.object(selector, "parse_stack_trace", return_value=SimpleNamespace(frames=seeds)),
            patch.object(selector, "find_symbol_for_stack_frame", side_effect=lambda **kw: nodes[kw["frame"]]),
            patch.object(selector, "get_callees", side_effect=lambda **kw: [nodes[i] for i in edges.get(kw["symbol_id"], [])]),
            patch.object(selector, "get_callers", return_value=[]),
            patch.object(selector, "search_code_chunks_hybrid", return_value=semantic),
            patch.object(selector, "search_hits_to_contexts", side_effect=lambda hits: hits),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        return selector.select_debug_context(None, 1, "log", "query", budget, policy)

    def test_wide_graph_reaches_second_hop(self):
        result = self.invoke({1: [2, 3, 4, 5], 2: [6]})
        self.assertIn(6, [c.source_id for c in result])
        self.assertEqual(len(result), 5)

    def test_last_direct_target_and_external_semantic(self):
        result = self.invoke({1: [2, 3, 4, 5], 2: [6]}, semantic_ids=[5, 20])
        self.assertEqual([c.source_id for c in result], [1, 5, 2, 6, 120])

    def test_third_hop_excluded_and_cycle_deduplicated(self):
        result = self.invoke({1: [2], 2: [1, 3], 3: [4]})
        self.assertEqual([c.source_id for c in result], [1, 2, 3])

    def test_no_trace_uses_semantic(self):
        result = self.invoke({}, seeds=(), semantic_ids=[20, 21])
        self.assertEqual([c.source_id for c in result], [120, 121])

    def test_full_trace_budget(self):
        result = self.invoke({1: [3]}, seeds=(1, 2), budget=2)
        self.assertEqual([c.source_id for c in result], [1, 2])

    def test_baseline_remains_callable(self):
        with patch.object(selector, "select_debug_context_breadth_first", return_value=["baseline"]) as old:
            self.assertEqual(selector.select_debug_context(None, 1, "log", "q", 5, "breadth_first"), ["baseline"])
            old.assert_called_once()

    def test_unknown_policy_rejected(self):
        with self.assertRaises(ValueError):
            selector.select_debug_context(None, 1, "log", "q", 5, "unknown")


if __name__ == "__main__":
    unittest.main()
