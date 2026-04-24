#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Load .env (skip comments and blank lines)
set -a
# shellcheck disable=SC1091
source "$PROJECT_DIR/.env"
set +a

exec /usr/bin/python3 "$PROJECT_DIR/main.py" --now
