#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID="${1:-1}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAVA_ROOT="$ROOT_DIR/src/main/java"
find "$JAVA_ROOT" -type f -name '*.java' | sort | while read -r file; do
  relative_path="${file#"$ROOT_DIR/"}"
  echo "Uploading: $relative_path"
  curl --fail --silent --show-error -X POST "$BASE_URL/projects/$PROJECT_ID/files" -F "file=@$file" -F "file_path=$relative_path"
  echo
done
echo "Upload complete."
