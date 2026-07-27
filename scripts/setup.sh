#!/usr/bin/env bash

set -euo pipefail

echo "[1/3] Python 환경 동기화"
uv sync

echo "[2/3] 환경변수 파일 확인"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ".env 파일을 생성했습니다."
    echo "OPENAI_API_KEY를 직접 입력해야 합니다."
fi

echo "[3/3] Docker 서비스 실행"
docker compose up -d

echo
echo "기본 설정이 완료되었습니다."
echo "서버 실행: uv run fastapi dev app/main.py"
