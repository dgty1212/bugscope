# BugScope Evaluation Dataset

BugScope의 Vector Retrieval과 Hybrid Retrieval을 비교하기 위한 작은 Java 평가 데이터셋입니다.

## 구성
- Java 소스 파일 12개
- 정답이 포함된 오류 사례 10개
- 난이도: easy / medium / hard
- `cases.json`: API 실험용 정답 데이터
- `cases.csv`: 사람이 보기 쉬운 표 형태 데이터
- `upload_all.sh`: 모든 Java 파일을 BugScope 프로젝트에 업로드하는 스크립트

## 권장 평가 절차
1. BugScope에서 새 프로젝트를 생성합니다.
2. `./upload_all.sh <PROJECT_ID>`로 Java 파일을 업로드합니다.
3. `POST /projects/{id}/index`
4. `POST /projects/{id}/embeddings`
5. `cases.json`의 각 사례에 대해 `POST /projects/{id}/analyze`
6. 반환된 `debug_case_id`에 대해 `PATCH /projects/{id}/debug-cases/{debug_case_id}`로 정답을 기록합니다.
7. 또는 `python run_cases.py <PROJECT_ID>`로 10개 분석/정답 기록/평가를 자동 실행합니다.
8. 수동 평가 시 `POST /projects/{id}/evaluations/retrieval`을 실행합니다.

## 주의
이 10개 사례는 파이프라인 검증용 최소 데이터셋입니다. 최종 포트폴리오 수치에는 실제 프로젝트 기반 사례를 추가해 20~30개 이상으로 확장하는 것을 권장합니다.
