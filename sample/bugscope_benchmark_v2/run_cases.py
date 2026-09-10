#!/usr/bin/env python3

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


BASE_URL = "http://127.0.0.1:8000"


def req(
    method: str,
    path: str,
    payload: dict | None = None,
):
    body = None
    headers = {}

    if payload is not None:
        body = json.dumps(
            payload
        ).encode("utf-8")

        headers[
            "Content-Type"
        ] = "application/json"

    request = urllib.request.Request(
        BASE_URL + path,
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(
            request
        ) as response:
            text = (
                response
                .read()
                .decode("utf-8")
            )

            if not text:
                return None

            return json.loads(text)

    except urllib.error.HTTPError as error:
        text = (
            error
            .read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        raise RuntimeError(
            f"{method} {path} failed: "
            f"{error.code}\n{text}"
        ) from error


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python run_cases.py "
            "<PROJECT_ID> "
            "[vector|hybrid|structural]"
        )

    project_id = int(
        sys.argv[1]
    )

    retrieval_mode = (
        sys.argv[2]
        if len(sys.argv) >= 3
        else "structural"
    )

    allowed_modes = {
        "vector",
        "hybrid",
        "structural",
    }

    if retrieval_mode not in allowed_modes:
        raise SystemExit(
            "mode must be "
            "vector, hybrid, or structural"
        )

    cases_path = (
        Path(__file__)
        .resolve()
        .parent
        / "cases.json"
    )

    cases = json.loads(
        cases_path.read_text(
            encoding="utf-8"
        )
    )

    debug_case_ids: list[int] = []

    print(
        "===================================="
    )
    print(
        " BugScope Benchmark v2"
    )
    print(
        "===================================="
    )
    print(
        f"Project ID     : {project_id}"
    )
    print(
        f"Retrieval Mode : {retrieval_mode}"
    )
    print(
        f"Cases          : {len(cases)}"
    )
    print()

    for index, case in enumerate(
        cases,
        start=1,
    ):
        difficulty = case.get(
            "difficulty",
            "unknown",
        ).upper()

        title = case.get(
            "title",
            f"Case {index}",
        )

        print(
            f"[{index}/{len(cases)}] "
            f"{difficulty} - {title}"
        )

        # --------------------------------
        # 1. Debug Analysis
        # --------------------------------
        analysis_response = req(
            "POST",
            (
                f"/projects/{project_id}"
                "/analyze"
            ),
            {
                "error_log": (
                    case["error_log"]
                ),
                "situation": (
                    case["situation"]
                ),
                "top_k": 5,
                "retrieval_mode": (
                    retrieval_mode
                ),
            },
        )

        debug_case_id = (
            analysis_response[
                "debug_case_id"
            ]
        )

        debug_case_ids.append(
            debug_case_id
        )

        # --------------------------------
        # 2. Ground Truth 등록
        # --------------------------------
        req(
            "PATCH",
            (
                f"/projects/{project_id}"
                f"/debug-cases/"
                f"{debug_case_id}"
            ),
            {
                "actual_cause": (
                    case["actual_cause"]
                ),
                "expected_file": (
                    case["expected_file"]
                ),
                "expected_symbol": (
                    case["expected_symbol"]
                ),
                "resolved": True,
                "user_score": 5.0,
            },
        )

        print(
            f"    debug_case_id="
            f"{debug_case_id}"
        )
        print(
            "    ground truth registered"
        )

    print()
    print(
        "===================================="
    )
    print(
        " Benchmark cases completed"
    )
    print(
        "===================================="
    )
    print(
        f"Created cases: "
        f"{len(debug_case_ids)}"
    )

    # ------------------------------------
    # 3. Vector / Hybrid / Structural 비교
    # ------------------------------------
    print()
    print(
        "Running comparative retrieval "
        "evaluation..."
    )
    print()

    evaluation = req(
        "POST",
        (
            f"/projects/{project_id}"
            "/evaluations/"
            "retrieval/compare"
        ),
    )

    print(
        json.dumps(
            evaluation,
            ensure_ascii=False,
            indent=2,
        )
    )

    print()
    print(
        "Created debug_case_ids:"
    )
    print(
        debug_case_ids
    )


if __name__ == "__main__":
    main()