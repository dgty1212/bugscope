from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from app.api import analysis as analysis_api
from app.schemas.analysis import DebugAnalysisRequest, DebugAnalysisResult
from app.services import analysis_service, context_selector
from app.services.selection_audit import SelectionAudit


def context():
    return context_selector.SelectedContext(
        context_type="callee", source_type="symbol", source_id=3,
        file_path="src/Leaf.java", class_name="Leaf", symbol_name="run",
        start_line=1, end_line=4, content="void run() {}",
        hop_depth=2, trace_origin={"source_id": 1},
        call_path=({"source_id": 1}, {"source_id": 2}, {"source_id": 3}),
        selection_reason="second_hop_reservation", traversal_direction="callee",
    )


def test_response_and_stored_metadata_match():
    selected = context()
    response = analysis_api.build_analysis_contexts([selected])[0].model_dump()
    stored = analysis_api.serialize_contexts([selected])[0]
    assert response == stored
    assert response["hop_depth"] == 2
    assert len(response["call_path"]) == 3


def test_metadata_does_not_change_llm_prompt():
    annotated = context()
    plain = replace(annotated, hop_depth=None, trace_origin=None, call_path=(),
                    selection_reason=None, traversal_direction=None)
    assert analysis_service.build_llm_prompt("error", "situation", [plain]) == (
        analysis_service.build_llm_prompt("error", "situation", [annotated])
    )


def test_report_persisted_with_analysis_without_changing_llm_payload():
    llm = DebugAnalysisResult(summary="summary", root_causes=[], verification_steps=[],
                              suggested_fixes=[], insufficient_context=False,
                              additional_information_needed=[])
    report = {"schema_version": 1, "selected": [], "excluded": [{"exclusion_reason": "context_budget"}]}
    pipeline = analysis_service.DebugAnalysisPipelineResult(
        retrieval_query="query", contexts=[context()], analysis=llm, selection_report=report)
    with (patch.object(analysis_api, "validate_project_exists"),
          patch.object(analysis_api.analysis_service, "analyze_debug_case", return_value=pipeline),
          patch.object(analysis_api.debug_case_service, "create_debug_case",
                       return_value=SimpleNamespace(id=123)) as save):
        response = analysis_api.analyze_project_error(1, DebugAnalysisRequest(error_log="error"), None)
    assert save.call_args.kwargs["analysis_result"]["_context_selection"] == report
    assert save.call_args.kwargs["retrieved_chunks"][0]["hop_depth"] == 2
    assert response.selection_report == report
    assert "_context_selection" not in response.analysis.model_dump()


def test_selector_captures_two_hop_route_and_cycle_skip():
    nodes = {i: SimpleNamespace(id=i, file_path=f"src/N{i}.java", class_name=f"N{i}",
             symbol_name="run", start_line=1, end_line=4, content="code") for i in (1, 2, 3)}
    edges = {1: [2], 2: [1, 3]}
    audit = SelectionAudit()
    with (patch.object(context_selector, "parse_stack_trace", return_value=SimpleNamespace(frames=[1])),
          patch.object(context_selector, "find_symbol_for_stack_frame", return_value=nodes[1]),
          patch.object(context_selector, "get_callees", side_effect=lambda **kw: [nodes[i] for i in edges.get(kw["symbol_id"], [])]),
          patch.object(context_selector, "get_callers", return_value=[]),
          patch.object(context_selector, "search_code_chunks_hybrid", return_value=[])):
        selected = context_selector.select_debug_context(None, 1, "log", "query", 5, audit=audit)
    assert selected[2].hop_depth == 2
    assert [step["source_id"] for step in selected[2].call_path] == [1, 2, 3]
    assert audit.report["skipped_graph_candidates"][0]["exclusion_reason"] == "already_visited"
