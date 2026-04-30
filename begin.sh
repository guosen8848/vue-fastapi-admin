#!/bin/sh
set -e

cd "$(dirname "$0")"
. .venv/bin/activate

# Avoid inheriting incompatible global DEBUG values such as "release".
unset DEBUG

python run.py &
backend_pid=$!
trap 'kill "$backend_pid" 2>/dev/null || true' EXIT

cd web
pnpm dev
