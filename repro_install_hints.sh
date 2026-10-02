#!/usr/bin/env bash
# Issues 1 and 2: the README install line and the build backend's own install hint.
# Needs: uv. Creates a throwaway venv next to this script.
cd "$(dirname "$0")"
uv venv -p 3.12 .venv-hints >/dev/null 2>&1

echo "== 1. README: pip install runanywhere==0.20.11"
uv pip install --dry-run --python .venv-hints/bin/python runanywhere==0.20.11 2>&1 | tail -n 2
echo -n "PyPI JSON API status: "; curl -s -o /dev/null -w "%{http_code}\n" https://pypi.org/pypi/runanywhere/json

echo
echo "== 2. the build backend's hint, installed together (protobuf>=6.33,<7 + grpcio-tools==1.71.*)"
uv pip install --dry-run --python .venv-hints/bin/python 'protobuf>=6.33,<7' 'grpcio-tools==1.71.*' 2>&1 | tail -n 3

echo
echo "== 2b. only grpcio-tools==1.71.* (what actually works; pulls protobuf 5.29.x)"
uv pip install --dry-run --python .venv-hints/bin/python 'grpcio-tools==1.71.*' 2>&1 | tail -n 5
