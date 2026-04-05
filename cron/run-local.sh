#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root from this script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC_DIR="$REPO_ROOT/src"
LOG_DIR="$REPO_ROOT/logs"
LOCK_DIR="$REPO_ROOT/.run-lock"

mkdir -p "$LOG_DIR"

# Prevent overlapping runs
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Another run is already in progress. Exiting." >> "$LOG_DIR/cron-runner.log"
  exit 0
fi
trap 'rmdir "$LOCK_DIR" >/dev/null 2>&1 || true' EXIT

# Load local env if present (.env first, then .env.local override)
# set -a auto-exports sourced variables to subprocess environment.
set -a
if [[ -f "$REPO_ROOT/.env" ]]; then
  # shellcheck disable=SC1090
  source "$REPO_ROOT/.env"
fi
if [[ -f "$REPO_ROOT/.env.local" ]]; then
  # shellcheck disable=SC1090
  source "$REPO_ROOT/.env.local"
fi
set +a

MODEL="${MODEL:-dutch}"
PYTHON_BIN="${PYTHON_BIN:-}"

if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
  else
    PYTHON_BIN="$(command -v python3)"
  fi
fi

MODEL_ENTRY="$SRC_DIR/${MODEL}.py"
if [[ ! -f "$MODEL_ENTRY" ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Unknown MODEL='$MODEL'. Expected one of: ashburn, bowa, carlton, dutch, ennis." >> "$LOG_DIR/cron-runner.log"
  exit 1
fi

TIMESTAMP="$(date '+%Y-%m-%d %H:%M:%S')"
RUN_LOG="$LOG_DIR/${MODEL}-$(date '+%Y-%m-%d').log"

echo "[$TIMESTAMP] Starting model '$MODEL' with $PYTHON_BIN" >> "$RUN_LOG"
(
  cd "$SRC_DIR"
  "$PYTHON_BIN" "$MODEL_ENTRY"
) >> "$RUN_LOG" 2>&1

EXIT_CODE=$?
if [[ $EXIT_CODE -eq 0 ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Completed successfully" >> "$RUN_LOG"
else
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Failed with exit code $EXIT_CODE" >> "$RUN_LOG"
fi

exit $EXIT_CODE
