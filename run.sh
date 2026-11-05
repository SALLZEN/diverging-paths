#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
WORKSPACE_DIR=$(pwd)
PYTHON_EXECUTABLE=$(printenv DAMADI_PYTHON || true)
[ -n "$PYTHON_EXECUTABLE" ] || PYTHON_EXECUTABLE="$WORKSPACE_DIR/.runtime/venv/bin/python"
[ -x "$PYTHON_EXECUTABLE" ] || { printf '%s\n' 'Run ./setup-environment.sh or set DAMADI_PYTHON to a compatible Python 3.11 environment.' >&2; exit 1; }
MODE=full
NOTEBOOK=0
for option in "$@"; do
    case "$option" in
      --analysis-only) MODE=analysis ;;
      --notebook) NOTEBOOK=1 ;;
      *) printf '%s\n' 'Usage: ./run.sh [--notebook] [--analysis-only]' >&2; exit 2 ;;
    esac
done
if [ "$MODE" = full ]; then
    [ "$(uname -s)" = Darwin ] || { printf '%s\n' 'Approved graphical exports require macOS Quartz. Use --analysis-only for the numerical route.' >&2; exit 1; }
    for program in Rscript; do
      command -v "$program" >/dev/null 2>&1 || { printf '%s\n' "Missing $program. See README.md." >&2; exit 1; }
    done
fi
mkdir -p .runtime/matplotlib verification
export PYTHONDONTWRITEBYTECODE=1
export MPLCONFIGDIR="$WORKSPACE_DIR/.runtime/matplotlib"
if [ "$MODE" = analysis ]; then export DAMADI_ANALYSIS_ONLY=1; else export DAMADI_ANALYSIS_ONLY=0; fi
if [ "$NOTEBOOK" = 1 ]; then exec "$PYTHON_EXECUTABLE" code/execute-notebook.py; fi
exec "$PYTHON_EXECUTABLE" code/01-reproduce.py
