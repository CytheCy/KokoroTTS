#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

if command -v python3.12 >/dev/null 2>&1; then
    python_cmd=python3.12
elif command -v python3.13 >/dev/null 2>&1; then
    python_cmd=python3.13
elif command -v python3.11 >/dev/null 2>&1; then
    python_cmd=python3.11
else
    echo "Python 3.10–3.13 is required. On Fedora, install it with: sudo dnf install python3.12" >&2
    exit 1
fi

if ! command -v espeak-ng >/dev/null 2>&1; then
    echo "espeak-ng is required. Install it with: sudo dnf install espeak-ng" >&2
    exit 1
fi

"$python_cmd" -m venv "$project_dir/.venv"
"$project_dir/.venv/bin/python" -m pip install --upgrade pip
# This app targets CPU-only Fedora systems. Installing from PyTorch's CPU index
# avoids pulling several gigabytes of unused NVIDIA CUDA libraries.
"$project_dir/.venv/bin/python" -m pip install \
    --index-url https://download.pytorch.org/whl/cpu torch
"$project_dir/.venv/bin/python" -m pip install "$project_dir"

apps_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$apps_dir"
sed "s|@PROJECT_DIR@|$project_dir|g" \
    "$project_dir/packaging/io.github.kokororeader.KokoroReader.desktop.in" \
    > "$apps_dir/io.github.kokororeader.KokoroReader.desktop"

echo
echo "Installed. Open 'Kokoro Reader' from KDE's application menu, or run:"
echo "  $project_dir/run.sh"
