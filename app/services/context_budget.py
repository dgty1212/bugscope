"""Budget arbitration for already collected contexts; no database or LLM calls."""


def key(context):
    return (context.file_path, context.start_line, context.end_line)


def overlaps(left, right):
    return (left.file_path == right.file_path
            and left.start_line <= right.end_line
            and right.start_line <= left.end_line)


def unique(contexts, seen=None):
    seen = set() if seen is None else seen
    result = []
    for context in contexts:
        location = key(context)
        if location not in seen:
            seen.add(location)
            result.append(context)
    return result


def allocate_context_budget(traces, direct, second, callers, semantic, limit, audit=None):
    """Keep legacy order unless graph candidates fill the remaining budget.

    Under pressure: reserve one second-hop slot with >=2 free slots,
    and one external semantic slot with >=3. Rank graph candidates by
    overlapping hybrid chunk rank, then retain stable graph order for ties.
    A reservation is not a guarantee of correctness: unranked direct targets
    can still be displaced. Preserve this tradeoff in benchmark reports.
    """
    if audit is not None:
        audit.begin(traces, direct, second, callers, semantic)

    def finish(selected, pressure=False, reasons=None):
        if audit is not None:
            return audit.finish(selected, limit, pressure, reasons)
        return selected

    if limit <= 0:
        return finish([])
    seen = set()
    traces = unique(traces, seen)[:limit]
    direct = unique(direct, seen)
    second = unique(second, seen)
    callers = unique(callers, seen)
    slots = limit - len(traces)
    if slots <= 0:
        return finish(traces)
    graph = direct + second + callers
    if len(graph) < slots:
        return finish(unique(traces + graph + semantic)[:limit])

    def relevance(context):
        return next((i for i, hit in enumerate(semantic) if overlaps(context, hit)),
                    len(semantic))

    direct = sorted(direct, key=relevance)
    second = sorted(second, key=relevance)
    callers = sorted(callers, key=relevance)
    # A chunk covering a trace/graph symbol is ranking evidence, not an
    # additional external semantic slot (which would waste the reservation).
    external = unique([hit for hit in semantic
                       if not any(overlaps(hit, node) for node in traces + graph)])
    second_slots = int(bool(second) and slots >= 2)
    semantic_slots = int(bool(external) and slots >= 3)
    direct_slots = max(0, slots - second_slots - semantic_slots)
    picked = direct[:direct_slots] + second[:second_slots] + external[:semantic_slots]
    reservation_reasons = {key(c): ("direct_quota_hybrid_rank" if relevance(c) < len(semantic)
                                      else "direct_quota_graph_order")
                           for c in direct[:direct_slots]}
    reservation_reasons.update({key(c): "second_hop_reservation" for c in second[:second_slots]})
    reservation_reasons.update({key(c): "semantic_reservation" for c in external[:semantic_slots]})
    picked = unique(picked)
    picked = unique(picked + direct + second + callers + external + semantic)[:slots]
    # Keep the response convention: trace, direct, second-hop, caller, semantic.
    category = {key(c): group for group, values in enumerate((direct, second, callers))
                for c in values}
    picked.sort(key=lambda c: category.get(key(c), 3))
    for context in picked:
        reservation_reasons.setdefault(key(context), "remaining_budget_fill")
    return finish(traces + picked, True, reservation_reasons)
