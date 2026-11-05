#!/bin/sh
# Optional global registration; the default notebook runner uses a private kernel.
set -eu
cd -- "$(dirname -- "$0")"
.runtime/venv/bin/python -m ipykernel install --user --name diverging-paths --display-name "Diverging Paths"
