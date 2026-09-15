import hashlib
import importlib.util
import json
from collections import Counter, deque
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.code_call import CodeCall
from app.models.code_symbol import CodeSymbol
from app.models.project import Project
from app.models.source_file import SourceFile
from app.services import context_selector
from app.services.java_ast_parser import JAVA_PARSER
from app.services.stack_trace_parser import parse_stack_trace
from app.services.symbol_index_service import (
    find_symbol_for_stack_frame,
    index_project_symbols,
)

ROOT = Path(__file__).resolve().parents[1] / "sample/bugscope_benchmark_v3"
CASES = json.loads((ROOT / "cases.json").read_text())
spec = importlib.util.spec_from_file_location("v3_runner", ROOT / "run_cases.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


@pytest.fixture(scope="module")
def graph():
    engine = create_engine("sqlite://")
    for model in (Project, SourceFile, CodeSymbol, CodeCall):
        model.__table__.create(engine)
    with Session(engine) as db:
        db.add(Project(id=1, name="v3-test", language="java"))
        for path in sorted(ROOT.glob("src/**/*.java")):
            content = path.read_text()
            assert not JAVA_PARSER.parse(content.encode()).root_node.has_error
            db.add(
                SourceFile(
                    project_id=1,
                    file_name=path.name,
                    file_path=path.relative_to(ROOT).as_posix(),
                    language="java",
                    content=content,
                    content_hash=hashlib.sha256(content.encode()).hexdigest(),
                    file_size=len(content.encode()),
                )
            )
        db.commit()
        index_project_symbols(db, 1)
        yield db
    engine.dispose()


def test_group_balance_and_no_answer_leakage():
    assert Counter(c["category"] for c in CASES) == {
        "direct_callee": 5,
        "two_hop_callee": 5,
        "control": 5,
    }
    assert len({c["case_id"] for c in CASES}) == 15
    for case in CASES:
        query = (case["error_log"] + " " + case["situation"]).lower()
        assert Path(case["expected_file"]).stem.lower() not in query
        assert case["expected_symbol"].lower() not in query


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["case_id"])
def test_real_graph_distance_and_current_selector(graph, monkeypatch, case):
    symbols = list(graph.scalars(select(CodeSymbol)).all())
    target = next(
        s
        for s in symbols
        if s.file_path == case["expected_file"]
        and s.symbol_name == case["expected_symbol"]
    )
    frames = parse_stack_trace(case["error_log"]).frames
    edges = list(graph.scalars(select(CodeCall)).all())
    if case["category"] == "control":
        assert frames == []
        assert not any(e.resolved_callee_symbol_id == target.id for e in edges)
    else:
        assert len(frames) == 1
        start = find_symbol_for_stack_frame(graph, 1, frames[0])
        assert start.class_name + "." + start.symbol_name == case["graph_path"][0]
        assert start.start_line <= frames[0].line_number <= start.end_line
        assert (
            "throw new IllegalStateException"
            in start.content.splitlines()[frames[0].line_number - start.start_line]
        )
        queue = deque([(start.id, 0)])
        distances = {}
        while queue:
            symbol_id, distance = queue.popleft()
            if symbol_id in distances:
                continue
            distances[symbol_id] = distance
            queue.extend(
                (e.resolved_callee_symbol_id, distance + 1)
                for e in edges
                if e.caller_symbol_id == symbol_id
                and e.resolved_callee_symbol_id is not None
            )
        assert distances[target.id] == case["expected_hops"]
        for name in case["graph_path"]:
            node = next(s for s in symbols if f"{s.class_name}.{s.symbol_name}" == name)
            assert node.id in distances
        for decoy in case["decoy_files"]:
            node = next(
                s
                for s in symbols
                if s.file_path == decoy and s.symbol_name == target.symbol_name
            )
            assert node.content == target.content
            assert node.id not in distances
    # This is a structural-only baseline probe, not a simulated vector score.
    monkeypatch.setattr(
        context_selector, "search_code_chunks_hybrid", lambda **kwargs: []
    )
    contexts = context_selector.select_debug_context(
        graph,
        1,
        case["error_log"],
        case["error_log"] + "\n" + case["situation"],
        5,
    )
    sources = [c.context_type for c in contexts if c.source_id == target.id]
    assert sources == (["callee"] if case["category"] != "control" else [])


def test_runner_rejects_foreign_evaluation():
    with pytest.raises(ValueError, match="membership"):
        runner.summarize(
            {"cases": [{"debug_case_id": 99}], "evaluated_cases": 1},
            [{"debug_case_id": 1}],
        )


def test_runner_rejects_v2_project(monkeypatch):
    monkeypatch.setattr(runner, "req", lambda *args: {"name": "benchmark-v2"})
    with pytest.raises(ValueError, match="dedicated"):
        runner.preflight(6)


def test_runner_rejects_wrong_sources(monkeypatch):
    monkeypatch.setattr(
        runner,
        "req",
        lambda method, path: (
            [] if path.endswith("/files") else {"name": "bugscope-benchmark-v3-test"}
        ),
    )
    with pytest.raises(ValueError, match="inventory"):
        runner.preflight(7)


def test_summary_separates_groups_and_context_provenance():
    mapping = [{**c, "debug_case_id": i} for i, c in enumerate(CASES)]
    rows = []
    for item in mapping:
        row = {
            "debug_case_id": item["debug_case_id"],
            "structural_context_types": ["trace", "callee"],
            "structural_context_details": [
                f"callee:{item['expected_file']}:{item['expected_symbol']}"
            ],
        }
        for mode in ("vector", "hybrid", "structural"):
            for kind in ("file", "symbol"):
                row[f"{mode}_{kind}_rank"] = 2 if mode == "structural" else None
        rows.append(row)
    summary = runner.summarize({"cases": rows, "evaluated_cases": 15}, mapping)
    assert summary["two_hop_callee"]["structural"]["symbol"]["mrr"] == 0.5
    assert summary["direct_callee"]["vector"]["file"]["top5"] == 0
    assert summary["direct_callee"]["ground_truth_context_sources"]["v3-01"] == [
        "callee"
    ]


def test_runner_rejects_missing_structure(monkeypatch):
    monkeypatch.setattr(runner, "req", lambda *args: {"matches": []})
    with pytest.raises(ValueError, match="Missing indexed edge"):
        runner.check_structure(1, CASES)
