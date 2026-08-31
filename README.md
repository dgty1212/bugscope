# BugScope

> **Stack Trace와 소스코드 구조 분석을 기반으로 오류 원인을 추적하는 RAG 기반 AI 디버깅 지원 시스템**

BugScope는 단순히 오류 메시지를 LLM에 전달하는 방식에서 벗어나,
**Stack Trace에서 오류 위치를 식별하고, Java 소스코드의 함수·파일 관계를 구조적으로 추적한 뒤 관련 코드만 선별하여 LLM에 제공하는 디버깅 지원 시스템**입니다.

오류 로그와 전체 소스코드를 그대로 LLM에 전달하는 대신, 코드 검색과 정적 구조 분석을 결합해 분석에 필요한 Context를 좁히는 것을 목표로 합니다.

---

## 1. Problem

LLM을 이용한 코드 디버깅에서는 오류 메시지만으로 실제 원인을 판단하기 어려운 경우가 많습니다.

예를 들어 다음과 같은 오류가 발생할 수 있습니다.

```text
java.lang.NullPointerException: userName is null
    at com.example.UserService.getUserName(UserService.java:16)
    at com.example.UserController.getUser(UserController.java:7)
```

단순히 에러 메시지만 LLM에 전달하면 다음과 같은 문제가 발생할 수 있습니다.

* 실제 오류가 발생한 소스코드를 확인할 수 없음
* Controller에서 발생한 오류처럼 보이지만 실제 원인은 Service 또는 Repository에 있을 수 있음
* 프로젝트 규모가 커질수록 전체 코드를 Context로 제공하기 어려움
* 관련 없는 코드가 포함되면 분석 정확도가 낮아질 수 있음
* LLM이 실제 코드에 존재하지 않는 원인이나 수정안을 추론할 가능성이 있음

BugScope는 이러한 문제를 해결하기 위해 **검색 기반 RAG와 소스코드 구조 분석을 결합**합니다.

---

## 2. Core Idea

BugScope가 목표로 하는 최종 분석 흐름은 다음과 같습니다.

```text
Stack Trace
    ↓
오류 파일 / 클래스 / 메서드 / 라인 추출
    ↓
Java AST 기반 Symbol Index
    ↓
오류 위치에 해당하는 실제 함수 식별
    ↓
Caller / Callee 관계 추적
    ↓
Structural Context 추출
        +
Vector / Hybrid Retrieval
    ↓
관련 Context 선별
    ↓
LLM 분석
    ↓
원인 / 근거 코드 / 검증 방법 / 수정안
```

기존 Vector Search만 사용하는 RAG와 달리, BugScope는 **Stack Trace와 코드의 구조적인 관계를 우선 활용하고 의미 기반 검색을 보조 수단으로 사용하는 방향**을 목표로 합니다.

---

# 3. Main Features

## 3.1 Project & Source Management

프로젝트 단위로 Java 소스코드를 관리합니다.

지원 기능:

```text
POST   /projects
GET    /projects
GET    /projects/{project_id}
PATCH  /projects/{project_id}
DELETE /projects/{project_id}
```

Java 파일 관리:

```text
POST   /projects/{project_id}/files
GET    /projects/{project_id}/files
GET    /projects/{project_id}/files/{file_id}
DELETE /projects/{project_id}/files/{file_id}
```

업로드 과정에서 다음 항목을 검증합니다.

* Java 파일 여부
* 파일 크기
* UTF-8 인코딩
* SHA-256 Content Hash
* 동일 경로 및 동일 파일 중복 여부

---

## 3.2 Code Chunking

소스코드를 RAG 검색에 사용할 수 있도록 일정 범위의 코드 Chunk로 분할합니다.

현재 기본 설정:

```text
max_lines      = 100
overlap_lines  = 20
```

예를 들어 250줄의 파일은 다음과 같이 분할됩니다.

```text
Chunk 0 : 1   ~ 100
Chunk 1 : 81  ~ 180
Chunk 2 : 161 ~ 250
```

각 Chunk에는 다음 정보가 저장됩니다.

```text
project_id
source_file_id
file_path
language
chunk_index
start_line
end_line
content
content_hash
embedding
```

---

## 3.3 Embedding & Vector Search

각 코드 Chunk를 OpenAI Embedding Model을 이용해 Vector로 변환하여 PostgreSQL + pgvector에 저장합니다.

현재 Embedding Model:

```text
text-embedding-3-small
```

Embedding Dimension:

```text
1536
```

검색 시 오류 로그를 Query Embedding으로 변환한 뒤 pgvector의 cosine distance를 이용해 관련 코드 Chunk를 탐색합니다.

```text
Error Log
    ↓
Query Embedding
    ↓
pgvector Cosine Search
    ↓
Top-K Code Chunks
```

---

## 3.4 Hybrid Retrieval

Vector Similarity만으로 관련 코드를 찾는 방식의 한계를 보완하기 위해 Stack Trace의 명시적 정보를 검색 점수에 반영합니다.

현재 Hybrid Score는 다음 요소를 사용합니다.

```text
Vector Similarity     60%
Filename Match        25%
Identifier Match      15%
```

Stack Trace에서 다음 정보를 추출합니다.

```text
UserService.java
getUserName
NullPointerException
```

이를 Vector Search 후보에 추가 점수로 반영하여 재정렬합니다.

```text
Vector Candidates
      ↓
Filename Matching
      +
Identifier Matching
      ↓
Hybrid Re-ranking
      ↓
Final Top-K
```

Vector 방식과 Hybrid 방식은 각각 독립적으로 실행할 수 있어 검색 성능 비교가 가능합니다.

---

# 4. Structural Code Analysis

BugScope의 주요 차별화 기능입니다.

단순 문자열 검색에서 벗어나 Java 소스코드 자체의 구조를 분석합니다.

---

## 4.1 Stack Trace Parser

Java Stack Trace를 다음과 같은 구조로 변환합니다.

입력:

```text
at com.example.users.UserService.getUserName(UserService.java:16)
```

파싱 결과:

```json
{
  "package_name": "com.example.users",
  "class_name": "UserService",
  "method_name": "getUserName",
  "file_name": "UserService.java",
  "line_number": 16,
  "depth": 0
}
```

이를 통해 Stack Trace를 단순 검색 문자열이 아니라 **구조화된 오류 위치 정보**로 사용할 수 있습니다.

---

## 4.2 Java AST Symbol Index

Tree-sitter 기반 Java AST 분석을 통해 다음 Symbol을 추출합니다.

```text
class
method
constructor
```

예:

```java
public class UserService {

    public String getUserName(Long id) {
        ...
    }
}
```

저장되는 Symbol:

```text
class_name   = UserService
symbol_name  = getUserName
symbol_type  = method
start_line   = 9
end_line     = 12
```

따라서 Stack Trace의

```text
UserService.getUserName(UserService.java:16)
```

정보를 실제 프로젝트 내부의 `CodeSymbol`과 연결할 수 있습니다.

---

## 4.3 Stack Frame → Symbol Matching

Stack Trace Frame과 AST Symbol을 다음 정보를 기준으로 매칭합니다.

```text
package_name
file_name
class_name
method_name
line_number
```

이를 통해 Semantic Search 없이도 Stack Trace가 직접 가리키는 함수의 위치를 찾을 수 있습니다.

---

## 4.4 Caller / Callee Call Graph

Java AST의 `method_invocation`을 분석하여 함수 간 호출 관계를 저장합니다.

예:

```java
public class UserController {

    private final UserService userService;

    public String getUser(Long id) {
        return userService.getUserName(id);
    }
}
```

BugScope는 다음 관계를 생성합니다.

```text
UserController.getUser
        │
        │ calls
        ▼
UserService.getUserName
```

현재 Benchmark 프로젝트에서 구조 인덱싱을 수행한 결과 함수 호출 관계가 정상적으로 생성되는 것을 확인했습니다.

이를 이용하면 오류가 특정 함수에서 발생했을 때:

```text
Caller
   ↓
Trace Target
   ↓
Callee
```

방향으로 주변 코드 Context를 추적할 수 있습니다.

---

# 5. Structural RAG

현재 BugScope가 최종적으로 목표로 하는 Context 구성 방식입니다.

기존 방식:

```text
Error Log
    ↓
Vector Search
    ↓
Top-K
    ↓
LLM
```

개선 방식:

```text
                    Stack Trace
                         ↓
                    Trace Symbol
                         ↓
                 ┌───────┴───────┐
                 ▼               ▼
              Callers          Callees
                 │               │
                 └───────┬───────┘
                         ↓
                Structural Context
                         │
                         │
Hybrid Retrieval ────────┤
                         ↓
                  Context Selector
                         ↓
                        LLM
```

Context Selector는 다음 우선순위를 기반으로 구성할 예정입니다.

```text
1. TRACE
   Stack Trace와 직접 일치하는 함수

2. CALLEE
   Trace 함수가 호출하는 함수

3. CALLER
   Trace 함수를 호출하는 함수

4. SEMANTIC
   Hybrid Retrieval을 통해 검색된 관련 코드
```

예상 LLM Context:

```text
[TRACE]
UserService.getUserName
lines 9-12

[CALLER]
UserController.getUser
lines 4-7

[CALLEE]
UserRepository.findNameById
lines 21-27

[SEMANTIC]
UserValidator.validateUserId
lines 10-18
```

각 Context가 선택된 이유까지 LLM에 전달하여 단순 코드 나열보다 분석 근거를 명확하게 만드는 것이 목표입니다.

> 현재 Stack Trace → Symbol → Caller/Callee 추적까지 구현되어 있으며, Structural Context와 Hybrid Retrieval을 통합하는 Context Selector를 개발 중입니다.

---

# 6. LLM Debug Analysis

검색된 코드는 OpenAI Responses API를 통해 분석합니다.

LLM은 다음 항목을 Structured Output으로 반환합니다.

```text
summary

root_causes
 ├─ title
 ├─ file_path
 ├─ line range
 ├─ reason
 ├─ evidence_chunk_ids
 └─ confidence

verification_steps

suggested_fixes

insufficient_context

additional_information_needed
```

분석 Prompt에는 다음 제약을 적용합니다.

* 제공된 오류 로그와 검색된 소스코드만 근거로 사용할 것
* 존재하지 않는 파일, 클래스, 함수, 변수, 라인을 생성하지 않을 것
* 원인 주장에 Evidence Chunk를 연결할 것
* 확실하지 않은 내용은 불확실하다고 표시할 것
* Context가 부족하면 `insufficient_context`를 반환할 것
* 수정안보다 원인 검증 절차를 먼저 제시할 것

이를 통해 단순 Chat Completion보다 **근거 기반 디버깅 분석**을 목표로 합니다.

---

# 7. Debug Case History & Ground Truth

모든 분석 결과는 Debug Case로 저장할 수 있습니다.

자동 저장 정보:

```text
error_log
situation
retrieval_query
retrieved_chunks
analysis_result
```

사용자가 실제 디버깅 결과를 확인한 뒤 다음 Ground Truth를 추가할 수 있습니다.

```text
actual_cause
expected_file
expected_symbol
resolved
user_score
```

이를 이용해 검색 성능과 분석 성능을 반복적으로 평가할 수 있습니다.

---

# 8. Retrieval Evaluation

BugScope에는 Vector Retrieval과 Hybrid Retrieval을 비교하기 위한 평가 기능이 포함되어 있습니다.

현재 평가 지표:

```text
Top-1 Accuracy
Top-3 Accuracy
Top-5 Accuracy
```

평가 Ground Truth:

```text
DebugCase.expected_file
```

초기 10개의 synthetic sanity-check 사례에서는 Vector와 Hybrid 모두 Top-1 / Top-3 / Top-5 100%를 기록했습니다.

이 결과는 우수성 비교보다는 **검색 및 평가 파이프라인의 정상 동작 확인 목적**으로 사용했습니다.

현재는 보다 어려운 평가를 위해 다음 조건을 포함한 Benchmark v2를 사용하고 있습니다.

```text
Java Source Files : 40
Debug Cases       : 30

- 유사 클래스
- 유사 메서드
- Decoy Source
- 파일명이 없는 오류 로그
- Controller / Service 간접 관계
- 긴 Java Source
- 다중 Chunk
- 증상 중심 오류 설명
```

최종적으로 다음 세 방식을 비교할 계획입니다.

```text
1. Vector Retrieval

2. Hybrid Retrieval

3. Structural RAG
   Stack Trace
   + AST
   + Call Graph
   + Hybrid Retrieval
```

---

# 9. Architecture

```text
┌──────────────────────┐
│     Java Project     │
└──────────┬───────────┘
           │
           ├──────────────────────────────┐
           │                              │
           ▼                              ▼
┌──────────────────────┐       ┌─────────────────────┐
│    Code Chunking     │       │   Java AST Parser   │
└──────────┬───────────┘       └──────────┬──────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐       ┌─────────────────────┐
│      Embedding       │       │    Code Symbols     │
└──────────┬───────────┘       └──────────┬──────────┘
           │                              │
           ▼                              ▼
┌──────────────────────┐       ┌─────────────────────┐
│ PostgreSQL + pgvector│       │     Call Graph      │
└──────────┬───────────┘       └──────────┬──────────┘
           │                              │
           │                 Stack Trace  │
           │                      │       │
           │                      ▼       │
           │              ┌───────────────┴────┐
           │              │ Structural Context│
           │              └──────────┬─────────┘
           │                         │
           ▼                         ▼
┌──────────────────────┐      ┌──────────────────────┐
│   Hybrid Retrieval   │─────▶│   Context Selector   │
└──────────────────────┘      └──────────┬───────────┘
                                        │
                                        ▼
                              ┌──────────────────────┐
                              │        LLM           │
                              └──────────┬───────────┘
                                        │
                                        ▼
                              ┌──────────────────────┐
                              │ Root Cause           │
                              │ Evidence             │
                              │ Verification         │
                              │ Suggested Fix        │
                              └──────────────────────┘
```

---

# 10. Tech Stack

### Backend

```text
Python
FastAPI
SQLAlchemy 2
Pydantic
```

### Database

```text
PostgreSQL
pgvector
psycopg3
```

### AI / Retrieval

```text
OpenAI Responses API
text-embedding-3-small
Vector Search
Hybrid Retrieval
RAG
```

### Static Code Analysis

```text
Tree-sitter
tree-sitter-java
Java AST
Symbol Index
Call Graph
```

### Development

```text
uv
pytest
Ruff
Docker Compose
WSL2
```

---

# 11. Project Structure

```text
bugscope/
├── app/
│   ├── api/
│   │   ├── analysis.py
│   │   ├── debug_cases.py
│   │   ├── evaluation.py
│   │   ├── indexing.py
│   │   ├── projects.py
│   │   ├── retrieval.py
│   │   ├── source_files.py
│   │   └── structural.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── constants.py
│   │   └── database.py
│   │
│   ├── models/
│   │   ├── code_call.py
│   │   ├── code_chunk.py
│   │   ├── code_symbol.py
│   │   ├── debug_case.py
│   │   ├── project.py
│   │   └── source_file.py
│   │
│   ├── prompts/
│   │   └── debug_analysis.py
│   │
│   ├── schemas/
│   │
│   └── services/
│       ├── analysis_service.py
│       ├── code_chunker.py
│       ├── embedding_service.py
│       ├── evaluation_service.py
│       ├── hybrid_retrieval.py
│       ├── indexing_service.py
│       ├── java_ast_parser.py
│       ├── llm_service.py
│       ├── retrieval_service.py
│       ├── stack_trace_parser.py
│       └── symbol_index_service.py
│
├── db/
│   └── init/
│
├── sample/
│   └── bugscope_benchmark_v2/
│
├── tests/
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

---

# 12. Getting Started

## Requirements

```text
Python 3.12
Docker
Docker Compose
OpenAI API Key
```

---

## Environment

`.env`

```env
DATABASE_URL=postgresql+psycopg://bugscope:bugscope_dev_password@127.0.0.1:5432/bugscope

OPENAI_API_KEY=your_api_key

OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_ANALYSIS_MODEL=your_analysis_model
```

---

## Install

```bash
uv sync
```

---

## Start PostgreSQL

```bash
docker compose up -d
```

---

## Start API Server

```bash
uv run uvicorn app.main:app --reload
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

# 13. Typical Workflow

```text
1. Create Project
        ↓
2. Upload Java Source
        ↓
3. Code Indexing
        ↓
4. Embedding
        ↓
5. Structural Indexing
        ↓
6. Input Error Log
        ↓
7. Retrieval / Structural Trace
        ↓
8. LLM Analysis
        ↓
9. Save Debug Case
        ↓
10. Register Ground Truth
        ↓
11. Evaluate Retrieval
```

API 예:

```text
POST /projects

POST /projects/{id}/files

POST /projects/{id}/index

POST /projects/{id}/embeddings

POST /projects/{id}/structure/index

POST /projects/{id}/structure/trace

POST /projects/{id}/analyze

POST /projects/{id}/evaluations/retrieval
```

---

# 14. Testing

```bash
uv run ruff check .
uv run pytest
```

주요 테스트 대상:

```text
Code Chunking
Stack Trace Parsing
Java AST Parsing
Method Invocation Parsing
Hybrid Retrieval
Retrieval Evaluation
```

---

# 15. Current Status

### Completed

* [x] FastAPI Project CRUD
* [x] Java Source Upload
* [x] Code Chunking
* [x] PostgreSQL + pgvector
* [x] OpenAI Embedding
* [x] Vector Retrieval
* [x] Hybrid Retrieval
* [x] Structured LLM Debug Analysis
* [x] Debug Case History
* [x] Ground Truth Registration
* [x] Vector / Hybrid Evaluation
* [x] Java Stack Trace Parser
* [x] Tree-sitter Java AST Parser
* [x] Class / Method Symbol Index
* [x] Stack Frame → Symbol Matching
* [x] Caller / Callee Call Graph

### In Progress

* [ ] Structural Context Selector
* [ ] Structural RAG + Hybrid Retrieval 통합
* [ ] Structural RAG Benchmark Evaluation
* [ ] Failure Case Analysis

### Planned

* [ ] AST-based Method Chunking 비교
* [ ] LLM Root Cause Evaluation
* [ ] Alembic Migration
* [ ] CI with GitHub Actions
* [ ] Demo UI
* [ ] Real-world Debug Dataset 확장

---

# 16. Project Goal

BugScope의 목표는 단순히 LLM API를 이용해 오류 메시지에 답변하는 도구를 만드는 것이 아닙니다.

핵심 질문은 다음과 같습니다.

> **LLM에게 전체 프로젝트를 제공하지 않고도, 오류 분석에 실제로 필요한 코드 Context를 어떻게 선별할 수 있을까?**

이를 위해 BugScope는:

```text
Semantic Retrieval
        +
Stack Trace
        +
Java AST
        +
Call Graph
```

를 결합하여 관련 코드를 추적하고, 최종적으로 최소한의 근거 Context만 LLM에 제공하는 방식을 구현하고 있습니다.

---

## License

This project is developed for personal research and portfolio purposes.
