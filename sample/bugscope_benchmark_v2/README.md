# BugScope Benchmark v2

검색 성능 비교를 위한 난이도 확장 synthetic benchmark입니다.

- Java files: 40
- Debug cases: 30
- Easy: 6
- Medium: 9
- Hard: 15

## Why harder than v1
- 유사한 이름과 역할을 가진 decoy 파일 포함
- Controller stack trace지만 실제 원인은 Service인 사례 포함
- 파일명/클래스명이 없는 증상형 로그 포함
- 날짜/사용자/인증/파일 등 동일 도메인의 유사 구현을 함께 배치
- 100/20 chunking에서 여러 조각이 생기는 긴 파일 2개 포함
- 예외가 아니라 잘못된 반환값 때문에 실패하는 사례 포함

## Run
1. BugScope에서 새 프로젝트 생성
2. `bash upload_all.sh <PROJECT_ID>`
3. `POST /projects/<id>/index` with max_lines=100, overlap_lines=20
4. `POST /projects/<id>/embeddings`
5. `python run_cases.py <PROJECT_ID> hybrid`

동일 프로젝트에서 run_cases.py를 반복 실행하면 DebugCase가 중복 생성됩니다. 새 프로젝트에서 평가하는 것을 권장합니다.
