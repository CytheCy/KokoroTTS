#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
venv_python="$project_dir/.venv/bin/python"

if [[ ! -x "$venv_python" ]]; then
    echo "Kokoro Reader is not installed yet. Run: $project_dir/setup.sh" >&2
    exit 1
fi

# Run the current checkout while continuing to use the environment and
# dependencies created by setup.sh.
export PYTHONPATH="$project_dir/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$venv_python" -m kokoro_reader "$@"
