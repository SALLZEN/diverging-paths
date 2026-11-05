#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
BOOTSTRAP_PYTHON=$(printenv PYTHON_BIN || true)
[ -n "$BOOTSTRAP_PYTHON" ] || BOOTSTRAP_PYTHON=python3.11
command -v "$BOOTSTRAP_PYTHON" >/dev/null 2>&1 || { printf '%s\n' 'Install Python 3.11 or set PYTHON_BIN to its executable.' >&2; exit 1; }
"$BOOTSTRAP_PYTHON" -c 'import sys; assert sys.version_info[:2] == (3, 11), "Use Python 3.11 for the tested dependency pins"'
"$BOOTSTRAP_PYTHON" -m venv .runtime/venv
.runtime/venv/bin/python -m pip install -r requirements.lock.txt
printf '%s\n' 'Python ready. Run ./run.sh --analysis-only for numerical checks.' 'R packages and macOS compiler/Quartz support are separate graphical prerequisites.'
