from types import SimpleNamespace

from app.models.code_symbol import CodeSymbol
from app.services import context_selector as selector


def run_graph(monkeypatch, seeds, edges, budget=20, callers=None):
    ids = set(seeds) | set(edges)
    for values in edges.values():
        ids.update(values)
    for values in (callers or {}).values():
        ids.update(values)
    symbols = {
        key: CodeSymbol(
            id=key, file_path=f"src/N{key}.java", class_name=f"N{key}",
            symbol_name="run", start_line=1, end_line=3, content="void run() {}",
        )
        for key in ids
    }
    expanded = []

    def get_callees(**kwargs):
        key = kwargs["symbol_id"]
        expanded.append(key)
        return [symbols[target] for target in edges.get(key, [])]

    monkeypatch.setattr(selector, "parse_stack_trace", lambda _: SimpleNamespace(frames=seeds))
    monkeypatch.setattr(selector, "find_symbol_for_stack_frame", lambda **kw: symbols[kw["frame"]])
    monkeypatch.setattr(selector, "get_callees", get_callees)
    monkeypatch.setattr(selector, "get_callers", lambda **kw: [
        symbols[key] for key in (callers or {}).get(kw["symbol_id"], [])
    ])
    monkeypatch.setattr(selector, "search_code_chunks_hybrid", lambda **kw: [])
    contexts = selector.select_debug_context(None, 1, "trace", "query", budget)
    return [(c.source_id, c.context_type) for c in contexts], expanded


def test_second_hop_is_included_but_third_is_not(monkeypatch):
    contexts, expanded = run_graph(monkeypatch, [1], {1: [2], 2: [3], 3: [4]})
    assert contexts == [(1, "trace"), (2, "callee"), (3, "callee")]
    assert expanded == [1, 2]


def test_all_direct_callees_precede_second_hop_across_traces(monkeypatch):
    contexts, _ = run_graph(monkeypatch, [1, 2], {1: [3], 2: [4], 3: [5], 4: [6]})
    assert [key for key, _ in contexts] == [1, 2, 3, 4, 5, 6]


def test_cycle_self_loop_and_diamond_are_deduplicated(monkeypatch):
    contexts, expanded = run_graph(monkeypatch, [1], {1: [1, 2, 3], 2: [1, 4], 3: [4]})
    assert [key for key, _ in contexts] == [1, 2, 3, 4]
    assert expanded == [1, 2, 3]


def test_breadth_first_budget_stops_before_second_hop(monkeypatch):
    monkeypatch.setattr(selector, "select_debug_context",
                        selector.select_debug_context_breadth_first)
    contexts, expanded = run_graph(monkeypatch, [1], {1: [2, 3], 2: [4]}, budget=3)
    assert [key for key, _ in contexts] == [1, 2, 3]
    assert expanded == [1]


def test_duplicate_trace_and_caller_are_not_repeated(monkeypatch):
    contexts, expanded = run_graph(monkeypatch, [1, 1], {1: [2], 2: [3]}, callers={1: [2, 4]})
    assert contexts == [(1, "trace"), (2, "callee"), (3, "callee"), (4, "caller")]
    assert expanded == [1, 2]


def test_empty_trace_does_not_expand_graph(monkeypatch):
    contexts, expanded = run_graph(monkeypatch, [], {1: [2]})
    assert contexts == []
    assert expanded == []


def test_zero_budget_does_not_expand_graph(monkeypatch):
    contexts, expanded = run_graph(monkeypatch, [1], {1: [2]}, budget=0)
    assert contexts == []
    assert expanded == []
