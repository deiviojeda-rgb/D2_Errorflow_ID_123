#!/usr/bin/env bash
set -eu

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$script_dir/campus_preflight.py" --prepare \
  --venv "$HOME/.venvs/bassein-12-10" \
  --output "$script_dir/preflight.json" \
  "$@"
