#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="${1:-http://localhost:8000}"
python3 "$SCRIPT_DIR/smoke_test.py" "$BASE_URL"
