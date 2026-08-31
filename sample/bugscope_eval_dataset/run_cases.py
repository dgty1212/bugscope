#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
BASE_URL = "http://127.0.0.1:8000"


def request_json(method: str, path: str, payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        BASE_URL + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urlopen(request) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except HTTPError as error:
        message = error.read().decode("utf-8")
        raise RuntimeError(
            f"{method} {path} failed: HTTP {error.code} {message}"
        ) from error


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python run_cases.py <PROJECT_ID>")

    project_id = int(sys.argv[1])
    cases = json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))

    created_ids: list[int] = []

    for case in cases:
        print(f"[{case['case_id']}/10] Analyze: {case['title']}")

        analysis = request_json(
            "POST",
            f"/projects/{project_id}/analyze",
            {
                "error_log": case["error_log"],
                "situation": case["situation"],
                "top_k": 5,
                "retrieval_mode": "hybrid",
            },
        )

        debug_case_id = analysis["debug_case_id"]
        created_ids.append(debug_case_id)

        request_json(
            "PATCH",
            f"/projects/{project_id}/debug-cases/{debug_case_id}",
            {
                "actual_cause": case["actual_cause"],
                "expected_file": case["expected_file"],
                "expected_symbol": case["expected_symbol"],
                "resolved": True,
                "user_score": 5.0,
            },
        )

        retrieved = analysis.get("retrieved_chunks", [])
        first_file = retrieved[0]["file_path"] if retrieved else "<none>"
        print(f"    debug_case_id={debug_case_id}, top1={first_file}")

    print("\nRetrieval evaluation")
    evaluation = request_json(
        "POST",
        f"/projects/{project_id}/evaluations/retrieval",
        {"limit": len(cases)},
    )

    print(json.dumps(evaluation, ensure_ascii=False, indent=2))
    print("\nCreated debug_case_ids:", created_ids)


if __name__ == "__main__":
    main()
