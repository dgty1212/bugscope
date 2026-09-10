import json
from pathlib import Path

import httpx

BASE_URL = "http://127.0.0.1:8000"
PROJECT_ID = 6

GROUND_TRUTH_PATH = Path(
    "sample/bugscope_benchmark_v2/ground_truth.json"
)

def find_matching_debug_case(
    debug_cases: list[dict],
    ground_truth: dict,
) -> dict | None:
    expected_log = normalize_error_log(
        ground_truth["error_log"]
    )

    # 1. error_log 전체 일치
    exact_matches = [
        debug_case
        for debug_case in debug_cases
        if debug_case.get("error_log")
        and normalize_error_log(
            debug_case["error_log"]
        ) == expected_log
    ]

    if exact_matches:
        return max(
            exact_matches,
            key=lambda item: item["id"],
        )

    # 2. Stack Trace의 파일명 + Symbol로 fallback
    expected_file = ground_truth[
        "expected_file"
    ].split("/")[-1]

    expected_symbol = ground_truth[
        "expected_symbol"
    ]

    candidates: list[dict] = []

    for debug_case in debug_cases:
        error_log = debug_case.get(
            "error_log",
            "",
        )

        if (
            expected_file in error_log
            and expected_symbol in error_log
        ):
            candidates.append(
                debug_case
            )

    if not candidates:
        return None

    return max(
        candidates,
        key=lambda item: item["id"],
    )

def normalize_error_log(value: str) -> str:
    return "\n".join(
        line.strip()
        for line in value.strip().splitlines()
        if line.strip()
    )


def load_ground_truth() -> list[dict]:
    with GROUND_TRUTH_PATH.open(
        encoding="utf-8"
    ) as file:
        return json.load(file)


def extract_debug_cases(
    response_data,
) -> list[dict]:
    """
    API가 list를 직접 반환하거나
    {"items": [...]} 형태여도 처리한다.
    """

    if isinstance(response_data, list):
        return response_data

    if isinstance(response_data, dict):
        for key in (
            "items",
            "cases",
            "debug_cases",
        ):
            value = response_data.get(key)

            if isinstance(value, list):
                return value

    raise RuntimeError(
        "DebugCase 목록 응답 형식을 알 수 없습니다."
    )


def main() -> None:
    ground_truth_cases = load_ground_truth()

    registered = 0
    missing: list[str] = []

    with httpx.Client(
        base_url=BASE_URL,
        timeout=30.0,
    ) as client:
        response = client.get(
            f"/projects/{PROJECT_ID}/debug-cases"
        )
        response.raise_for_status()

        debug_case_summaries = extract_debug_cases(
            response.json()
        )

        debug_cases: list[dict] = []

        # 목록 API가 error_log 전체를 제공하지 않을 수도 있으므로
        # 각 DebugCase 상세 정보를 다시 가져온다.
        for summary in debug_case_summaries:
            debug_case_id = summary["id"]

            detail_response = client.get(
                
                    f"/projects/{PROJECT_ID}"
                    f"/debug-cases/"
                    f"{debug_case_id}"
                
            )
            detail_response.raise_for_status()

            debug_cases.append(
                detail_response.json()
            )

        print(
            f"loaded debug cases: "
            f"{len(debug_cases)}"
        )

        for ground_truth in ground_truth_cases:
            debug_case = find_matching_debug_case(
                debug_cases=debug_cases,
                ground_truth=ground_truth,
            )

            if debug_case is None:
                missing.append(
                    ground_truth["name"]
                )
                continue

            debug_case_id = debug_case["id"]

            patch_response = client.patch(
                (
                    f"/projects/{PROJECT_ID}"
                    f"/debug-cases/"
                    f"{debug_case_id}"
                ),
                json={
                    "expected_file": (
                        ground_truth[
                            "expected_file"
                        ]
                    ),
                    "expected_symbol": (
                        ground_truth[
                            "expected_symbol"
                        ]
                    ),
                    "actual_cause": (
                        ground_truth[
                            "actual_cause"
                        ]
                    ),
                    "resolved": True,
                },
            )

            patch_response.raise_for_status()

            registered += 1

            print(
                "[REGISTERED]",
                ground_truth["name"],
                "->",
                debug_case_id,
            )

    print()
    print(
        f"registered: {registered}"
    )
    print(
        f"missing: {len(missing)}"
    )

    if missing:
        print()

        for name in missing:
            print(
                "[MISSING]",
                name,
            )


if __name__ == "__main__":
    main()