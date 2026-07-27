from fastapi import FastAPI

app = FastAPI(
    title="BugScope API",
    description="RAG 기반 소스코드 검색 및 오류 분석 API",
    version="0.1.0",
)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "name": "BugScope",
        "message": "API 서버가 정상적으로 실행 중입니다.",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}