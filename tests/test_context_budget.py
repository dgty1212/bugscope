import unittest
from types import SimpleNamespace

try:
    from app.services.context_budget import allocate_context_budget as allocate
except ModuleNotFoundError as error:
    if error.name != "app":
        raise
    from context_budget import allocate_context_budget as allocate


def c(name, start=1, end=10):
    return SimpleNamespace(file_path=name + ".java", start_line=start, end_line=end)


def names(values):
    return [value.file_path.removesuffix(".java") for value in values]


class BudgetPolicyTests(unittest.TestCase):
    def setUp(self):
        self.trace = [c("trace")]
        self.direct = [c("a"), c("b"), c("c"), c("d")]

    def test_no_pressure_preserves_order(self):
        self.assertEqual(names(allocate(self.trace, [c("a")], [c("leaf")], [],
                                        [c("semantic")], 5)), ["trace", "a", "leaf", "semantic"])

    def test_wide_graph_reserves_second_hop(self):
        result = allocate(self.trace, self.direct, [c("leaf")], [], [], 5)
        self.assertEqual(names(result), ["trace", "a", "b", "c", "leaf"])

    def test_last_direct_target_is_preserved_with_hybrid_evidence(self):
        result = allocate(self.trace, self.direct, [c("leaf")], [], [c("d")], 5)
        self.assertEqual(names(result), ["trace", "d", "a", "b", "leaf"])

    def test_external_semantic_slot(self):
        result = allocate(self.trace, self.direct, [c("leaf")], [], [c("outside")], 5)
        self.assertEqual(names(result), ["trace", "a", "b", "leaf", "outside"])

    def test_highest_ranked_second_hop_wins(self):
        result = allocate(self.trace, self.direct, [c("x"), c("y")], [], [c("y")], 5)
        self.assertIn("y", names(result))
        self.assertNotIn("x", names(result))

    def test_multiple_traces_are_preserved(self):
        result = allocate([c("t1"), c("t2")], self.direct, [c("leaf")], [], [c("outside")], 5)
        self.assertEqual(names(result), ["t1", "t2", "a", "leaf", "outside"])

    def test_duplicate_trace_cycle_and_diamond(self):
        result = allocate(self.trace * 2, [c("trace"), c("a"), c("a")],
                          [c("a"), c("leaf"), c("leaf")], [c("leaf")], [], 5)
        self.assertEqual(names(result), ["trace", "a", "leaf"])

    def test_tiny_budgets(self):
        for limit in range(6):
            result = allocate(self.trace, self.direct, [c("leaf")], [], [c("outside")], limit)
            self.assertLessEqual(len(result), limit)
            if limit:
                self.assertEqual(names(result)[0], "trace")

    def test_semantic_only_control(self):
        self.assertEqual(names(allocate([], [], [], [], [c("a"), c("b")], 1)), ["a"])

    def test_overlapping_graph_chunk_is_evidence_not_extra_slot(self):
        result = allocate(self.trace, self.direct, [c("leaf")], [], [c("d", 1, 100)], 5)
        self.assertEqual(names(result), ["trace", "d", "a", "b", "leaf"])

    def test_same_file_nonoverlapping_methods_not_false_match(self):
        result = allocate(self.trace, self.direct, [c("leaf")], [], [c("d", 30, 40)], 5)
        self.assertEqual(result[-1].start_line, 30)
        self.assertEqual(names(result)[:4], ["trace", "a", "b", "leaf"])

    def test_caller_fills_unused_quota(self):
        result = allocate(self.trace, [], [c("leaf")], [c("p1"), c("p2"), c("p3")], [], 3)
        self.assertEqual(names(result), ["trace", "leaf", "p1"])

    def test_unranked_last_direct_can_be_displaced_documented_tradeoff(self):
        result = allocate(self.trace, self.direct, [c("leaf")], [], [], 5)
        self.assertNotIn("d", names(result))

    def test_full_direct_budget_leaves_external_semantic_slot(self):
        result = allocate(self.trace, self.direct, [], [], [c("outside")], 5)
        self.assertEqual(names(result), ["trace", "a", "b", "c", "outside"])

    def test_inputs_not_mutated(self):
        before = names(self.direct)
        allocate(self.trace, self.direct, [c("leaf")], [], [c("d")], 5)
        self.assertEqual(names(self.direct), before)


if __name__ == "__main__":
    unittest.main()
