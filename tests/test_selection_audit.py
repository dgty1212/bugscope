import importlib.util
import itertools
import json
import unittest
from dataclasses import dataclass
from pathlib import Path

try:
    from app.services.context_budget import allocate_context_budget as allocate
    from app.services.selection_audit import SelectionAudit
except ModuleNotFoundError as error:
    if error.name != "app":
        raise
    from context_budget import allocate_context_budget as allocate
    from selection_audit import SelectionAudit


@dataclass(frozen=True)
class Context:
    source_id: int
    file_path: str
    context_type: str = "callee"
    start_line: int = 1
    end_line: int = 10
    symbol_name: str = "run"
    class_name: str = "Node"
    content: str = "sensitive source content"
    hop_depth: int | None = None
    trace_origin: dict | None = None
    call_path: tuple = ()
    selection_reason: str | None = None
    traversal_direction: str | None = None

    @property
    def id(self):
        return self.source_id


def c(i, kind="callee"):
    return Context(i, f"src/N{i}.java", kind)


def ids(values):
    return [x.source_id for x in values]


class SelectionAuditTests(unittest.TestCase):
    def test_two_hop_origin_and_path(self):
        trace, direct, leaf = c(1, "trace"), c(2), c(3)
        audit = SelectionAudit()
        audit.trace(trace)
        audit.callee(trace, direct)
        audit.callee(direct, leaf)
        selected = allocate([trace], [direct], [leaf], [], [], 5, audit)
        self.assertEqual(selected[2].hop_depth, 2)
        self.assertEqual(selected[2].trace_origin["source_id"], 1)
        self.assertEqual([x["source_id"] for x in selected[2].call_path], [1, 2, 3])
        self.assertEqual(selected[0].selection_reason, "trace_match")
        self.assertIsNone(leaf.hop_depth)

    def test_caller_path_is_real_call_direction(self):
        trace, caller = c(1, "trace"), c(2, "caller")
        audit = SelectionAudit()
        audit.trace(trace)
        audit.caller(trace, caller)
        selected = allocate([trace], [], [], [caller], [], 5, audit)
        self.assertEqual([x["source_id"] for x in selected[1].call_path], [2, 1])
        self.assertEqual(selected[1].traversal_direction, "caller")
        self.assertEqual(selected[1].trace_origin["source_id"], 1)

    def test_budget_and_duplicate_are_distinct(self):
        trace = c(1, "trace")
        audit = SelectionAudit()
        allocate([trace, trace], [c(2), c(3)], [], [], [], 2, audit)
        reasons = [x["exclusion_reason"] for x in audit.report["excluded"]]
        self.assertIn("duplicate_location", reasons)
        self.assertIn("context_budget", reasons)

    def test_reservations_have_correct_reasons(self):
        audit = SelectionAudit()
        allocate([c(1, "trace")], [c(i) for i in range(2, 6)], [c(6)], [],
                 [c(9, "semantic")], 5, audit)
        reasons = {x["source_id"]: x["selection_reason"] for x in audit.report["selected"]}
        self.assertEqual(reasons[6], "second_hop_reservation")
        self.assertEqual(reasons[9], "semantic_reservation")
        self.assertEqual(reasons[2], "direct_quota_graph_order")

    def test_hybrid_evidence_reason(self):
        audit = SelectionAudit()
        allocate([c(1, "trace")], [c(i) for i in range(2, 6)], [c(6)], [],
                 [c(5, "semantic")], 5, audit)
        target = next(x for x in audit.report["selected"] if x["source_id"] == 5)
        self.assertEqual(target["selection_reason"], "direct_quota_hybrid_rank")

    def test_semantic_has_no_fabricated_route(self):
        audit = SelectionAudit(policy="hybrid")
        selected = allocate([], [], [], [], [c(1, "semantic")], 5, audit)
        self.assertIsNone(selected[0].hop_depth)
        self.assertIsNone(selected[0].trace_origin)
        self.assertEqual(selected[0].call_path, ())
        self.assertEqual(selected[0].traversal_direction, "semantic")

    def test_multiple_origins_stay_separate(self):
        audit = SelectionAudit()
        audit.trace(c(1))
        audit.trace(c(2))
        audit.callee(c(2), c(3))
        self.assertEqual(audit.routes[3]["trace_origin"]["source_id"], 2)

    def test_skipped_cycle_is_not_budget_exclusion(self):
        audit = SelectionAudit()
        audit.skip(c(1))
        allocate([], [], [], [], [], 5, audit)
        self.assertEqual(audit.report["skipped_graph_candidates"][0]["exclusion_reason"], "already_visited")
        self.assertEqual(audit.report["excluded"], [])

    def test_report_contains_no_source_content(self):
        audit = SelectionAudit()
        allocate([c(1)], [], [], [], [], 5, audit)
        self.assertNotIn("sensitive source content", json.dumps(audit.report))

    def test_zero_budget_explains_collected_candidates(self):
        audit = SelectionAudit()
        self.assertEqual(allocate([c(1)], [], [], [], [], 0, audit), [])
        self.assertEqual(audit.report["excluded"][0]["exclusion_reason"], "context_budget")

    def test_selected_order_equals_report_order(self):
        audit = SelectionAudit()
        selected = allocate([c(1)], [c(i) for i in range(2, 6)], [c(6)], [], [c(5)], 5, audit)
        self.assertEqual(ids(selected), [x["source_id"] for x in audit.report["selected"]])

    def test_3780_selections_match_uninstrumented_reference(self):
        reference_path = Path(__file__).parent / "fixtures/context_budget_before.py"
        if not reference_path.exists():
            reference_path = Path(__file__).parent / "context_budget_before.py"
        spec = importlib.util.spec_from_file_location("budget_reference", reference_path)
        reference = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reference)
        count = 0
        for nt, nd, ns, nc, nm, budget in itertools.product(range(3), range(5), range(3), range(3), range(4), range(7)):
            args = ([c(i, "trace") for i in range(nt)], [c(i+3) for i in range(nd)],
                    [c(i+10) for i in range(ns)], [c(i+20, "caller") for i in range(nc)],
                    [c(i+3, "semantic") for i in range(nm)], budget)
            expected = reference.allocate_context_budget(*args)
            actual = allocate(*args, audit=SelectionAudit())
            self.assertEqual(ids(actual), ids(expected))
            self.assertEqual([x.content for x in actual], [x.content for x in expected])
            count += 1
        self.assertEqual(count, 3780)


if __name__ == "__main__":
    unittest.main()
