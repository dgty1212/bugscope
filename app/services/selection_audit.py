"""Selection diagnostics: location-based identity, no source content or query text."""
from dataclasses import dataclass, field, is_dataclass, replace


def location(context):
    return (context.file_path, context.start_line, context.end_line)


def reference(symbol):
    return {
        "source_id": getattr(symbol, "id", getattr(symbol, "source_id", None)),
        "file_path": symbol.file_path,
        "class_name": getattr(symbol, "class_name", None),
        "symbol_name": getattr(symbol, "symbol_name", None),
        "start_line": symbol.start_line,
        "end_line": symbol.end_line,
    }


@dataclass
class SelectionAudit:
    """Only candidates actually collected by the selector are described."""
    policy: str = "balanced"
    routes: dict = field(default_factory=dict)
    skipped: list = field(default_factory=list)
    candidates: list = field(default_factory=list)
    report: dict = field(default_factory=dict)

    def trace(self, symbol):
        ref = reference(symbol)
        self.routes[symbol.id] = {"hop_depth": 0, "trace_origin": ref,
                                  "call_path": [ref], "direction": "trace"}

    def callee(self, parent, symbol):
        route = self.routes[parent.id]
        self.routes[symbol.id] = {
            "hop_depth": route["hop_depth"] + 1,
            "trace_origin": route["trace_origin"],
            "call_path": [*route["call_path"], reference(symbol)],
            "direction": "callee",
        }

    def caller(self, trace, symbol):
        self.routes[symbol.id] = {
            "hop_depth": 1, "trace_origin": reference(trace),
            "call_path": [reference(symbol), reference(trace)], "direction": "caller",
        }

    def skip(self, symbol, reason="already_visited"):
        self.skipped.append({**reference(symbol), "exclusion_reason": reason})

    def begin(self, traces, direct, second, callers, semantic):
        self.candidates = [(group, c) for group, values in (
            ("trace", traces), ("direct", direct), ("second", second),
            ("caller", callers), ("semantic", semantic)) for c in values]

    def finish(self, selected, limit, pressure=False, reasons=None):
        reasons = reasons or {}
        positions = {location(c): i + 1 for i, c in enumerate(selected)}
        seen = set()
        included, excluded = [], []
        for group, context in self.candidates:
            key = location(context)
            duplicate = key in seen
            seen.add(key)
            source_id = getattr(context, "source_id", None)
            route = self.routes.get(source_id, {}) if group != "semantic" else {}
            entry = {
                **reference(context), "source_id": source_id,
                "context_type": getattr(context, "context_type", group),
                "candidate_group": group,
                "hop_depth": route.get("hop_depth"),
                "trace_origin": route.get("trace_origin"),
                "call_path": route.get("call_path", []),
                "direction": route.get("direction", "semantic" if group == "semantic" else None),
            }
            if not duplicate and key in positions:
                entry.update(selected_rank=positions[key], selection_reason=reasons.get(
                    key, "trace_match" if group == "trace" else "priority_order"))
                included.append(entry)
            else:
                entry["exclusion_reason"] = "duplicate_location" if duplicate else "context_budget"
                excluded.append(entry)
        included.sort(key=lambda c: c["selected_rank"])
        self.report = {
            "schema_version": 1, "policy": self.policy, "max_contexts": limit,
            "budget_pressure": pressure, "selected": included, "excluded": excluded,
            "skipped_graph_candidates": self.skipped,
            "scope": "collected candidates only; not every project symbol or every possible path",
        }
        by_location = {(c["file_path"], c["start_line"], c["end_line"]): c for c in included}
        annotated = []
        for context in selected:
            metadata = by_location.get(location(context), {})
            if is_dataclass(context) and "hop_depth" in context.__dataclass_fields__:
                context = replace(context, hop_depth=metadata.get("hop_depth"),
                                  trace_origin=metadata.get("trace_origin"),
                                  call_path=tuple(metadata.get("call_path", [])),
                                  selection_reason=metadata.get("selection_reason"),
                                  traversal_direction=metadata.get("direction"))
            annotated.append(context)
        return annotated
