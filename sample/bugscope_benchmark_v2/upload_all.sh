#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID="${1:-}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
if [[ -z "$PROJECT_ID" ]]; then echo "Usage: bash upload_all.sh <PROJECT_ID>"; exit 1; fi
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JAVA_ROOT="$ROOT_DIR/src/main/java"
COUNT=0
while IFS= read -r file; do
  relative_path="${file#"$ROOT_DIR/"}"
  echo "[$((COUNT + 1))] Uploading: $relative_path"
  curl --fail --silent --show-error -X POST "$BASE_URL/projects/$PROJECT_ID/files" -F "file=@$file" -F "file_path=$relative_path" > /dev/null
  COUNT=$((COUNT + 1))
done < <(find "$JAVA_ROOT" -type f -name '*.java' | sort)
echo "Uploaded $COUNT Java files."
