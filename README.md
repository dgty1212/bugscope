# BugScope

Java 오류 로그와 소스코드에서 디버깅에 필요한 근거 코드를 선별하고, LLM으로 원인 후보·검증 절차·수정안을 생성하는 FastAPI 기반 연구용 시스템입니다. Stack Trace, Tree-sitter AST, 호출 관계와 Vector/Hybrid 검색을 결합합니다.

## 현재 상태 (2026-09-17 검토)

기준 커밋은 `2334534`입니다. 아래 구현 상태는 코드와 테스트를 확인한 결과이며, 평가 수치는 저장소 작업 공간에 남아 있는 최신 검증 자료를 기준으로 합니다.

| 상태 | 기능 |
| --- | --- |
| 커밋된 구현 | 프로젝트 CRUD, Java 파일 업로드·검증, 라인 기반 chunking, 임베딩·Vector/Hybrid 검색 |
| 커밋된 구현 | Java Stack Trace 파싱, AST symbol index, caller/callee 관계, Structural RAG와 Hybrid 통합 |
| 커밋된 구현 | 최대 2-hop callee 탐색, balanced context budget, context observability |
| 커밋된 구현 | Structured LLM 분석, Debug Case 저장·ground truth 등록, Vector/Hybrid/Structural 비교, Benchmark v3 |
| 로컬 구현·미커밋 | hop별 검색 지표와 선택/제외 사유 집계, compare 응답 확장, v3 summary 및 evaluate-only 검증 확장 |
| 향후 과제 | LLM 원인 진단의 별도 평가, 실제 프로젝트 데이터 확장, AST method chunking 비교, DB migration, CI, Demo UI |

**이 README만 갱신하는 커밋에는 평가 집계 확장 코드를 포함하지 않습니다.** 미커밋 대상은 `app/api/evaluation.py`, `app/schemas/evaluation.py`, `app/services/evaluation_service.py`, 새 `app/services/benchmark_metrics.py`, v3 runner·README 및 관련 테스트입니다. 아래 최신 평가의 추가 집계 필드는 이 로컬 변경에 의존하며, 이 README 커밋만 checkout하면 아직 제공되지 않습니다.

## 분석 흐름과 구현 범위

```text
Java 파일 → 라인 chunk → OpenAI embedding → PostgreSQL/pgvector
         → Tree-sitter → CodeSymbol / CodeCall

오류 로그 + 상황 설명
  → Stack Trace의 symbol 매칭
  → trace / 1-hop callee / 2-hop callee / 1-hop caller 수집
  + Hybrid 검색
  → context budget에 맞게 선택
  → LLM Structured Output → Debug Case 저장
```

- 파일 업로드는 Java 확장자, 크기, UTF-8 및 content hash 등을 검증합니다.
- 기본 chunk 크기는 100줄, overlap은 20줄입니다. 임베딩 기본값은 `text-embedding-3-small`, 저장 차원은 1536입니다.
- Vector 검색은 cosine distance를 사용합니다. Hybrid는 vector similarity 0.60, 파일명 0.25, 식별자 0.15를 반영해 후보를 재정렬합니다.
- AST에서 class/method/constructor와 호출 관계를 추출합니다. Stack Frame은 package·file·class·method·line 정보를 이용해 symbol과 연결합니다.
- `/analyze`는 `vector`, `hybrid`, `structural`을 지원하며 기본값은 `structural`입니다. `top_k` 기본값은 5, 허용 범위는 1~10입니다.
- LLM 결과는 `summary`, `root_causes`, `verification_steps`, `suggested_fixes`, `insufficient_context`, `additional_information_needed`를 포함합니다. 원인 후보는 `evidence_context_ids`로 근거 context를 참조합니다.
- 분석 결과와 선택 context를 저장하고 `actual_cause`, `expected_file`, `expected_symbol`, `resolved`, `user_score`를 ground truth로 추가할 수 있습니다.

### 2-hop 탐색과 balanced context budget

[context_selector.py](app/services/context_selector.py)는 trace symbol의 직접 callee를 먼저 수집하고 그 callee에서 한 단계 더 확장합니다. caller는 trace의 직접 caller까지만 수집합니다. 방문한 symbol을 중복 제거하며 3-hop으로 확장하지 않습니다. trace가 매칭되지 않으면 semantic 검색으로 보완합니다. `/structure/trace`는 직접 caller/callee를 보여주는 점검 API이며, 2-hop context 선택은 분석 selector에서 수행합니다.

[context_budget.py](app/services/context_budget.py)의 기본 정책은 `balanced`입니다.

- TRACE를 먼저 확보합니다. graph 후보가 남은 context 슬롯보다 적으면 기존 우선순위로 채웁니다.
- graph 후보가 남은 슬롯을 채울 만큼 많으면, 남은 슬롯이 2개 이상일 때 2-hop 후보 1개, 3개 이상일 때 graph/trace와 겹치지 않는 semantic 후보 1개를 예약합니다. 해당 후보가 있을 때만 예약합니다.
- graph 후보는 겹치는 Hybrid chunk 순위를 참고해 정렬하며, 동률은 기존 graph 순서를 유지합니다.
- 출력 순서는 TRACE → 직접 CALLEE → 2-hop CALLEE → CALLER → SEMANTIC입니다. 비교용 `breadth_first` 정책은 내부 함수 인자로 남아 있습니다.

이 budget은 **context 개수 제한**이며 토큰 수 제한은 아닙니다. 예약은 정답 선택을 보장하지 않으며, Hybrid 근거가 없는 직접 callee 정답이 밀릴 수 있습니다. TRACE만으로 슬롯을 모두 쓰면 다른 후보는 포함되지 않습니다.

### Context observability

선택 context에는 `hop_depth`, `trace_origin`, `call_path`, `selection_reason`, `traversal_direction`이 포함됩니다. 분석 응답의 `selection_report`는 선택·제외·graph 탐색 중 건너뛴 후보를 기록하며, 저장된 분석의 `_context_selection`에도 보존됩니다. 선택 메타데이터와 보고서는 [selection_audit.py](app/services/selection_audit.py)에서 구성합니다.

추가된 **미커밋 평가 집계**는 compare 사례의 `structural_hop_ranks`, `selection_report`, 전체 `diagnostics`와 v3 그룹별 `hop_metrics`, `selection_reason_counts`를 제공합니다.

- hop bucket: `trace`, `hop_1_callee`, `hop_2_callee`, `hop_1_caller`, `semantic`, `unknown`.
- 순위는 전체 선택 context에서의 원래 순위를 사용합니다. hop별로 순위를 다시 매기지 않습니다.
- 분모는 해당 그룹에서 hop 정보가 있는 평가 사례 전체이며 검색 실패도 포함합니다. symbol 지표는 `expected_symbol`이 있는 사례만 포함합니다. 정보가 없으면 `cases=0`, 지표는 `null`입니다.
- 선택·제외 사유는 관측한 후보의 **이벤트 수**입니다. 프로젝트 전체 후보 수나 고유 사례 수가 아닙니다. 보고서 누락은 `missing_report_cases`로 구분합니다.
- dataset의 `two_hop_callee` 그룹과 실제 선택 경로는 다릅니다. semantic으로 찾은 정답은 2-hop graph 성공으로 집계하지 않습니다.

## 실행

Python 3.12 이상, uv, Docker Compose 및 임베딩·분석용 OpenAI API 설정이 필요합니다. 사용 기술은 FastAPI, SQLAlchemy 2, Pydantic, PostgreSQL/pgvector, Tree-sitter Java입니다.

```bash
uv sync
# .env가 없다면 생성 (기존 설정은 보존)
test -f .env || cp .env.example .env
docker compose up -d
# db/init에 초기화 SQL이 없으므로 최초 DB에서 vector extension을 생성
docker compose exec postgres psql -U bugscope -d bugscope \
  -c 'CREATE EXTENSION IF NOT EXISTS vector;'
```

`.env`의 `DATABASE_URL`은 [compose.yaml](compose.yaml)의 DB 사용자·암호·포트와 맞추고, `OPENAI_API_KEY`를 설정하세요. 현재 `.env.example`의 DB 암호는 Compose 기본값과 다릅니다. 분석 모델 설정 이름은 **`OPENAI_ANALYSIS_MODEL`**이며 예제 파일의 `OPENAI_CHAT_MODEL`은 애플리케이션이 사용하지 않습니다. 코드 기본 분석 모델은 `gpt-5.4-mini`입니다. 임베딩 모델을 변경할 때는 저장 차원 1536과의 호환성을 확인해야 합니다.

```bash
uv run uvicorn app.main:app --reload
curl --fail http://127.0.0.1:8000/health/db
```

API 문서는 <http://127.0.0.1:8000/docs>에서 확인합니다. 서버 시작 시 `Base.metadata.create_all`로 없는 테이블을 생성합니다. 기존 테이블 변경을 자동 migration하지는 않습니다. `.env`와 인증정보는 커밋하지 않습니다.

일반 사용 순서:

| 순서 | API |
| --- | --- |
| 프로젝트 생성 | `POST /projects` |
| Java 업로드 | `POST /projects/{id}/files` |
| chunk 생성 | `POST /projects/{id}/index` |
| 임베딩 생성 | `POST /projects/{id}/embeddings` |
| AST/호출 관계 생성 | `POST /projects/{id}/structure/index` |
| trace 점검 | `POST /projects/{id}/structure/trace` |
| 분석 및 저장 | `POST /projects/{id}/analyze` |
| ground truth 등록 | `PATCH /projects/{id}/debug-cases/{case_id}` |
| 세 검색 방식 비교 | `POST /projects/{id}/evaluations/retrieval/compare` |

분석 요청 예: `{"error_log":"java.lang.IllegalStateException: ...", "situation":"재현 상황", "retrieval_mode":"structural", "top_k":5}`. compare는 현재 인덱스에서 다시 검색하며 `top_k=5`를 사용합니다. LLM 진단을 다시 채점하는 API가 아닙니다.

## Benchmark v3 실행과 평가

[v3 dataset 및 runner](sample/bugscope_benchmark_v3/)는 Java 파일 50개와 15개 사례로 구성됩니다. direct callee 5건, two-hop callee 5건, 애플리케이션 trace가 없는 control 5건입니다. 구조 사례의 정답과 같은 본문을 가진 decoy를 두어 호출 경로 식별을 검증합니다. query에는 정답 클래스·파일·심볼 이름을 넣지 않습니다. control은 의미 검색 양성 대조군입니다.

서버가 실행 중일 때 저장소 루트에서 **새 프로젝트**로 진행합니다.

```bash
export BASE_URL=http://127.0.0.1:8000
curl --fail-with-body -sS -X POST "$BASE_URL/projects" \
  -H 'Content-Type: application/json' \
  -d '{"name":"bugscope-benchmark-v3-review-001","language":"java"}'
# 아래 값을 응답의 새 프로젝트 ID로 바꾸세요.
export PROJECT_ID=123
bash sample/bugscope_benchmark_v3/upload_all.sh "$PROJECT_ID"
curl --fail-with-body -sS -X POST "$BASE_URL/projects/$PROJECT_ID/index" \
  -H 'Content-Type: application/json' -d '{"max_lines":100,"overlap_lines":20}'
curl --fail-with-body -sS -X POST "$BASE_URL/projects/$PROJECT_ID/embeddings" \
  -H 'Content-Type: application/json' -d '{}'
curl --fail-with-body -sS -X POST "$BASE_URL/projects/$PROJECT_ID/structure/index"
uv run python sample/bugscope_benchmark_v3/run_cases.py "$PROJECT_ID" structural
```

runner는 Java corpus와 해시, 빈 case 목록 및 필요한 call edge를 확인한 뒤 analyze → ground truth PATCH → compare를 실행합니다. 임베딩과 분석은 외부 API를 호출합니다. `cases.json`과 README는 검색 corpus에 업로드하지 않습니다. 평가 중 프로젝트 내용을 변경하지 마세요.

결과는 로컬 `sample/bugscope_benchmark_v3/results/<실행>/`의 `manifest.json`, `evaluation.json`, `summary.json`에 저장됩니다. 원본 분석 로그와 결과 파일은 이번 문서 커밋에 포함하지 않습니다. 이미 등록한 사례는 다음과 같이 재평가할 수 있습니다.

```bash
uv run python sample/bugscope_benchmark_v3/run_cases.py "$PROJECT_ID" \
  --evaluate-only sample/bugscope_benchmark_v3/results/<이전실행>/manifest.json
```

재평가는 LLM 분석을 다시 실행하지 않지만 검색 질의 임베딩은 호출합니다. 미커밋 runner 확장은 unresolved 사례의 공존을 허용하되 resolved ID 집합과 manifest/dataset 매핑이 정확히 일치하는지 검사합니다. 등록 도중 실패한 경우 새 프로젝트로 시작합니다. v3 하위 README의 1-hop 제한·2-hop 향후 구현 설명은 최초 baseline 시점의 기록입니다.

### 최신 확인 결과

확인 자료는 로컬 실행 `7-hop-metrics-20260915T110832.107483Z`의 manifest/evaluation/summary/validation입니다. manifest 기준 `2334534` + 미커밋 평가 확장 상태에서 실제 DB와 embedding API를 사용해 로컬 compare API handler를 호출한 결과입니다. LLM analyze 재실행과 DB 쓰기는 하지 않았습니다. 이번 README 검토에서는 저장된 평가 코드 5개와 dataset의 SHA-256, 평가 ID를 대조했으며 유료 benchmark를 새로 실행하지 않았습니다.

프로젝트 7의 정답 사례 **55~69만 15건** 평가했습니다. 다른 프로젝트나 observability 사례는 포함하지 않습니다. manifest에 기록된 제외 unresolved ID는 75~77입니다. 모든 방식의 평균 context 수는 5입니다.

아래는 **정답 코드 검색 성공률**입니다. 이번 실행에서는 file/symbol 지표가 같았습니다. MRR은 정답 순위 역수의 평균이며 미검색은 0입니다.

| 그룹 | 방식 | Top-1 | Top-3 | Top-5 | MRR |
| --- | --- | ---: | ---: | ---: | ---: |
| direct callee (5) | Vector / Hybrid 각각 | 0% | 0% | 0% | 0.0000 |
| direct callee (5) | Structural | 0% | 100% | 100% | 0.5000 |
| two-hop callee (5) | Vector / Hybrid 각각 | 0% | 0% | 0% | 0.0000 |
| two-hop callee (5) | Structural | 0% | 100% | 100% | 0.3333 |
| control (5) | 세 방식 각각 | 100% | 100% | 100% | 1.0000 |
| 전체 (15) | Vector / Hybrid 각각 | 33.3% | 33.3% | 33.3% | 0.3333 |
| 전체 (15) | Structural | 33.3% | 100% | 100% | 0.6111 |

추가 hop 집계는 direct 정답 5건을 `hop_1_callee`의 전체 순위 2, two-hop 정답 5건을 `hop_2_callee`의 전체 순위 3, control 정답 5건을 `semantic`의 순위 1로 확인합니다. TRACE가 먼저 나오므로 Structural Top-1만으로 callee 검색 성능을 판단하지 않습니다. 선택 보고서 누락은 0/15이며, 선택 이벤트는 `trace_match` 10회와 `priority_order` 65회, 제외 이벤트는 `context_budget` 100회입니다.

### 평가 한계

- **검색 성공률은 오류 원인 진단 정확도가 아닙니다.** 정답 코드가 context에 포함됐는지를 측정하며 LLM 설명·수정안의 정답 여부는 별도 평가가 필요합니다.
- 소규모 synthetic dataset이며 동일 본문 decoy와 단순 호출 경로를 사용합니다. 실제 서비스 일반화나 Vector/Hybrid 전반의 열세를 입증하지 않습니다.
- 이 v3 결과만으로 budget 경쟁이 심한 graph에서 balanced 정책의 개선을 입증하지 않습니다. 예약·후보 정렬·정답 탈락 가능성은 별도 budget 테스트로 검증합니다.
- 정적 receiver class와 method 이름 기반 연결이므로 동적 dispatch, reflection 및 복잡한 Java 타입 해석의 완전성을 보장하지 않습니다. 탐색은 callee 2-hop/caller 1-hop으로 제한됩니다.
- symbol 검색 지표도 context의 파일·라인과 symbol의 대응을 평가하는 값입니다. 실행 시 결함 재현이나 수정 코드의 동작 검증을 뜻하지 않습니다.
- 최신 결과 원본은 로컬 자료이며 이 문서 커밋에 포함되지 않습니다. manifest에는 dataset hash와 checkout 상태가 있지만 모델·실행 환경의 완전한 고정 정보는 없으므로 수치의 동일 재현은 보장하지 않습니다.

## 테스트와 검증 상태

```bash
uv run pytest -q
uv run ruff check .
# 현재 핵심 코드·v3·테스트 범위만 검사
uv run ruff check app sample/bugscope_benchmark_v3 tests
```

2026-09-17 현재 작업 트리에서 `.venv/bin/pytest -q`: **108 passed**. `.venv/bin/ruff check app sample/bugscope_benchmark_v3 tests`: **통과**. 전체 `.venv/bin/ruff check .`는 기존 `sample/bugscope_benchmark_v2/run_cases.py:3`의 import 정렬 오류 `I001` 1건으로 실패합니다. 이 README 변경에서 코드를 수정하지 않았습니다. 테스트 수는 미커밋 평가 확장 테스트를 포함한 값입니다.

테스트는 chunking, Stack Trace/AST/call 파싱, 검색 지표, v3 dataset의 실제 AST graph, 2-hop·cycle·중복 제거, budget 예약, 선택 audit와 분석 저장 통합을 다룹니다. SQLite 및 mock 기반 검증이 포함되며 PostgreSQL·외부 LLM 전체 경로의 실시간 성공을 보증하지 않습니다.

## 주요 코드 위치

- `app/api/`, `app/schemas/`: API와 입출력 모델
- `app/services/context_selector.py`, `context_budget.py`, `selection_audit.py`: context 탐색·선택·관측
- `app/services/evaluation_service.py`: 검색 비교 평가
- `app/services/benchmark_metrics.py`: 로컬 미커밋 추가 집계
- `app/models/`: 프로젝트, 소스, chunk, symbol, call, debug case
- `sample/bugscope_benchmark_v3/`: dataset, 업로드 및 실행 도구
- `tests/`: 회귀·단위·통합 테스트

개인 연구 및 포트폴리오 목적의 프로젝트입니다.
