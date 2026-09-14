#!/usr/bin/env python3
"""v2 analyze -> ground truth -> compare protocol, isolated to a v3 project."""

import argparse
import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def req(method, path, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        BASE_URL + path,
        data=body,
        method=method,
        headers={} if body is None else {"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else None
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"{method} {path}: {error.code}\n{error.read().decode('utf-8', errors='replace')}"
        ) from error


def save(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def fingerprint():
    paths = [ROOT / "cases.json", *sorted(ROOT.glob("src/**/*.java"))]
    return hashlib.sha256(
        b"".join(
            p.relative_to(ROOT).as_posix().encode() + b"\0" + p.read_bytes()
            for p in paths
        )
    ).hexdigest()


def preflight(project_id):
    prefix = f"/projects/{project_id}"
    project = req("GET", prefix)
    if not project["name"].startswith("bugscope-benchmark-v3-"):
        raise ValueError("Use a dedicated project named bugscope-benchmark-v3-<run>.")
    files = req("GET", prefix + "/files")
    expected = {
        p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in ROOT.glob("src/**/*.java")
    }
    actual = {f["file_path"]: f["content_hash"] for f in files}
    if actual != expected or len(files) != len(expected):
        raise ValueError(
            "Uploaded source inventory/hash differs from v3; use only v3 Java sources."
        )


def check_structure(project_id, cases):
    """Verify every required edge through the server's existing trace endpoint."""
    package = "com.example.bugscope.benchmark.v3"
    for case in cases:
        for source, target in zip(case["graph_path"], case["graph_path"][1:]):
            class_name, method = source.split(".")
            target_class, target_method = target.split(".")
            matches = req(
                "POST",
                f"/projects/{project_id}/structure/trace",
                {"error_log": f"at {package}.{source}({class_name}.java:6)"},
            )["matches"]
            matched = matches[0]["matched_symbol"] if matches else None
            if (
                not matched
                or matched["class_name"] != class_name
                or matched["symbol_name"] != method
                or not any(
                    c["class_name"] == target_class
                    and c["symbol_name"] == target_method
                    for c in matches[0]["callees"]
                )
            ):
                raise ValueError(
                    f"Missing indexed edge {source} -> {target}; run structure/index."
                )


def case_ids(project_id):
    result = []
    offset = 0
    while True:
        page = req(
            "GET", f"/projects/{project_id}/debug-cases?offset={offset}&limit=100"
        )
        result.extend(c["id"] for c in page)
        if len(page) < 100:
            return result
        offset += 100


def summarize(evaluation, mapping):
    rows = evaluation["cases"]
    expected_ids = {item["debug_case_id"] for item in mapping}
    if (
        len(rows) != len(mapping)
        or {r["debug_case_id"] for r in rows} != expected_ids
        or evaluation["evaluated_cases"] != len(mapping)
    ):
        raise ValueError(
            "Evaluation membership differs from this run; results rejected."
        )
    by_id = {r["debug_case_id"]: r for r in rows}
    groups = {}
    for group in ("direct_callee", "two_hop_callee", "control"):
        members = [m for m in mapping if m["category"] == group]
        selected = [by_id[m["debug_case_id"]] for m in members]
        metrics = {"cases": len(selected)}
        for mode in ("vector", "hybrid", "structural"):
            metrics[mode] = {}
            for kind in ("file", "symbol"):
                ranks = [r[f"{mode}_{kind}_rank"] for r in selected]
                metrics[mode][kind] = {
                    **{
                        f"top{k}": sum(r is not None and r <= k for r in ranks)
                        / len(ranks)
                        for k in (1, 3, 5)
                    },
                    "mrr": sum(1 / r if r else 0 for r in ranks) / len(ranks),
                }
        metrics["ground_truth_context_sources"] = {
            m["case_id"]: [
                detail.split(":", 1)[0]
                for detail in by_id[m["debug_case_id"]]["structural_context_details"]
                if detail.split(":", 1)[1]
                == f"{m['expected_file']}:{m['expected_symbol']}"
            ]
            for m in members
        }
        metrics["semantic_only_cases"] = sum(
            set(r["structural_context_types"]) == {"semantic"} for r in selected
        )
        groups[group] = metrics
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_id", type=int)
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["vector", "hybrid", "structural"],
        default="structural",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--evaluate-only", type=Path, metavar="MANIFEST")
    args = parser.parse_args()
    cases = json.loads((ROOT / "cases.json").read_text())
    preflight(args.project_id)
    check_structure(args.project_id, cases)
    prefix = f"/projects/{args.project_id}"
    if args.evaluate_only:
        manifest = json.loads(args.evaluate_only.read_text())
        if (
            manifest["project_id"] != args.project_id
            or manifest["base_url"] != BASE_URL
            or manifest["dataset_sha256"] != fingerprint()
            or manifest["status"] != "registered"
            or len(manifest["mapping"]) != len(cases)
        ):
            raise ValueError(
                "Manifest does not match this completed registration/dataset/server."
            )
    else:
        if case_ids(args.project_id):
            raise ValueError(
                "Project already has debug cases. Use a fresh project; no cases deleted."
            )
        manifest = {
            "project_id": args.project_id,
            "base_url": BASE_URL,
            "dataset_sha256": fingerprint(),
            "registration_mode": args.mode,
            "status": "registering",
            "mapping": [],
        }
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    output = args.output or ROOT / "results" / f"{args.project_id}-{stamp}"
    output.mkdir(parents=True, exist_ok=False)
    manifest["run_time_utc"] = stamp
    manifest["git_commit"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()
    manifest["git_status"] = subprocess.check_output(
        ["git", "status", "--short"],
        cwd=ROOT,
        text=True,
    )
    save(output / "manifest.json", manifest)
    if not args.evaluate_only:
        for case in cases:
            response = req(
                "POST",
                prefix + "/analyze",
                {
                    "error_log": case["error_log"],
                    "situation": case["situation"],
                    "top_k": 5,
                    "retrieval_mode": args.mode,
                },
            )
            item = {
                k: case[k]
                for k in ("case_id", "category", "expected_file", "expected_symbol")
            }
            item["debug_case_id"] = response["debug_case_id"]
            manifest["mapping"].append(item)
            save(output / "manifest.json", manifest)
            req(
                "PATCH",
                prefix + f"/debug-cases/{item['debug_case_id']}",
                {
                    "actual_cause": case["actual_cause"],
                    "expected_file": case["expected_file"],
                    "expected_symbol": case["expected_symbol"],
                    "resolved": True,
                },
            )
            print(
                f"{case['case_id']}: debug_case_id={item['debug_case_id']}", flush=True
            )
        manifest["status"] = "registered"
        save(output / "manifest.json", manifest)
    if set(case_ids(args.project_id)) != {
        m["debug_case_id"] for m in manifest["mapping"]
    }:
        raise ValueError("Foreign cases found in project; refusing mixed evaluation.")
    evaluation = req("POST", prefix + "/evaluations/retrieval/compare")
    summary = summarize(evaluation, manifest["mapping"])
    save(output / "evaluation.json", evaluation)
    save(output / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Results: {output}")


if __name__ == "__main__":
    main()
