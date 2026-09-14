# BugScope Benchmark v3 — structural retrieval baseline

## 현재 구현 점검

v2: 30건 중 TRACE 9, CALLER 3, CALLEE 3, semantic-only 21이며 Hybrid/Structural 지표가 동일했다.
v2 runner는 analyze → PATCH ground truth → 프로젝트 전체 compare 순서다.
동일 프로젝트에서 반복 등록하면 예전 resolved case도 평가에 포함된다.

현재 `app/services/context_selector.py`는 TRACE → 직접 CALLEE → CALLER → SEMANTIC 순서다.
callee는 trace symbol에 대해서만 탐색한다. 이번 변경에는 2-hop traversal을 추가하지 않는다.
`symbol_index_service.py`는 AST가 추론한 receiver class와 method 이름으로 callee를 resolve한다.
그래서 명시적 타입을 가진 필드를 사용하고, decoy는 같은 method 이름과 본문을 갖되 클래스 이름을 구분했다.

## 구성과 해석

- direct_callee 5건: 경계 execute → 정답 transform (거리 1)
- two_hop_callee 5건: 경계 execute → forward → 정답 transform (거리 2)
- control 5건: 애플리케이션 stack frame 없는 증상 검색
- Java 50개: 경계 10, 중간 노드 5, 정답 15, decoy 20

구조 케이스는 결과 검증 경계에서 새 예외를 발생시킨다. 하위 함수가 예외를 던진 뒤
trace를 임의로 숨기는 방식이 아니다. 실제 throw 위치는 경계의 9번째 줄이다.
각 case의 invocation, actual_cause, graph_path에 재현 입력, 결함, 정답 경로를 기록했다.
5가지 결함은 문자 수 off-by-one, 숫자 뒷자리 손실, signed byte overflow,
올림 누락, 정수 비율 계산 오류다. 같은 유형을 1-hop/2-hop에 각각 배치한다.

error_log와 situation 모두 정답 클래스/파일/심볼 이름을 포함하지 않는다.
각 정답과 동일 본문을 가진 decoy 2개가 있어 query 의미만으로 실제 실행 대상을 구분하기 어렵다.
실제 call graph에서는 지정 정답만 연결된다. 이는 구조에 의한 식별을 검증하는 synthetic 실험이며,
vector/hybrid가 우연히 정답을 검색할 가능성까지 제거하는 것은 아니다.
control의 설명 주석은 의미 검색을 위한 양성 대조군이다. 실제 업무 정확도로 일반화하지 않는다.

현재 구현에서는 direct 정답이 보통 trace 다음에 나오므로 Top-1만으로 판단하지 않는다.
그룹별 file/symbol Top-1/3/5, MRR와 ground_truth_context_sources를 함께 본다.
2-hop 정답이 semantic으로 검색되면 이를 graph traversal 성공으로 해석하지 않는다.
테스트의 빈 semantic 결과는 graph 동작을 분리한 검증이며 실제 retrieval 점수가 아니다.

## 실행 (저장소 루트에서)

서버와 PostgreSQL, OpenAI 설정이 준비되어 있어야 한다. analyze와 embedding은 API를 사용한다.
등록과 평가 중에는 이 프로젝트의 소스/케이스를 다른 작업에서 변경하지 않는다.

```bash
export BASE_URL=http://127.0.0.1:8000
curl --fail-with-body -sS -X POST "$BASE_URL/projects" \
  -H 'Content-Type: application/json' \
  -d '{"name":"bugscope-benchmark-v3-baseline-001","language":"java"}'
# 반환된 새 id 사용. 기존 v2 프로젝트 ID를 사용하지 않는다.
export PROJECT_ID=<새_ID>
bash sample/bugscope_benchmark_v3/upload_all.sh "$PROJECT_ID"
curl --fail-with-body -sS -X POST "$BASE_URL/projects/$PROJECT_ID/index" \
  -H 'Content-Type: application/json' -d '{"max_lines":100,"overlap_lines":20}'
curl --fail-with-body -sS -X POST "$BASE_URL/projects/$PROJECT_ID/embeddings" \
  -H 'Content-Type: application/json' -d '{}'
curl --fail-with-body -sS -X POST "$BASE_URL/projects/$PROJECT_ID/structure/index"
uv run python sample/bugscope_benchmark_v3/run_cases.py "$PROJECT_ID" structural
```

Java 파일만 업로드한다. cases.json/README는 검색 corpus에 포함하지 않는다.
구조 인덱싱을 생략하면 semantic fallback이 발생하므로 반드시 실행한다.
현재 기본 chunk 설정은 v2와 동일한 100/20, 비교 top_k는 기존 API의 5이다.

runner는 v2의 stdlib HTTP 및 analyze/PATCH/compare 순서를 재사용한다.
v3 전용 이름, 정확한 Java 파일 목록/해시, 빈 debug-case 목록을 등록 전에 확인한다.
서버의 structure/trace API로 필요한 15개 call edge의 존재도 확인한다.
기존 케이스를 삭제하거나 resolved 값을 바꾸지 않는다. 결과 case ID 집합도 검사하여 혼합 평가를 거부한다.
user_score는 실제 사람이 평가한 점수가 아니므로 자동으로 5점을 부여하지 않는다.

결과는 `sample/bugscope_benchmark_v3/results/<project-id>-<UTC>/`에 저장된다:

- manifest.json: 데이터 해시, commit, 작업 상태, 등록 모드, case ID ↔ debug case ID
- evaluation.json: 서버의 원본 비교 응답 (context 출처 포함)
- summary.json: 3개 그룹별 지표와 정답 context 출처

기존 결과를 덮어쓰지 않으며 results는 git에서 제외한다. 실패 시 manifest에 등록된 ID가 남는다.
등록 도중 실패했다면 새 프로젝트로 다시 시작한다. 등록 완료 후 평가만 실패했다면 다음 명령으로
LLM 분석을 재실행하지 않고 재평가한다. 새 결과 폴더가 생성된다.

```bash
uv run python sample/bugscope_benchmark_v3/run_cases.py "$PROJECT_ID" \
  --evaluate-only sample/bugscope_benchmark_v3/results/<이전실행>/manifest.json
```

향후 2-hop 구현 후에도 동일 dataset 및 등록된 케이스로 이 명령을 실행하여 전후를 비교한다.
embedding/analysis 모델, 서버의 commit과 설정도 실험 기록에 함께 보관한다.
manifest의 commit은 로컬 checkout이므로 원격 서버 사용 시 서버 버전은 별도로 기록해야 한다.

## 검증

```bash
uv run ruff check sample/bugscope_benchmark_v3 tests/test_benchmark_v3.py
uv run pytest tests/test_benchmark_v3.py
uv run pytest
```

SQLite에서 실제 AST 인덱서로 CodeSymbol/CodeCall을 생성하여 최단 거리 1/2,
decoy 비연결, 정확한 trace 위치, query 정답명 미노출, control 무trace를 확인한다.
기존 selector의 순수 구조 결과는 direct 5건 callee 성공, 2-hop 5건 미도달이어야 한다.
이 테스트 외에 실제 Vector/Hybrid/Structural 성능은 위 서버 평가로 측정해야 한다.
