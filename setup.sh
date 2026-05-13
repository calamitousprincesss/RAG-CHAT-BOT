#!/usr/bin/env bash
# RAGChatbot - one-click macOS / Linux setup (uv-powered)
set -e
cd "$(dirname "$0")"

echo
echo "==========================================="
echo "  RAGChatbot - one-click setup"
echo "==========================================="

if ! command -v uv >/dev/null 2>&1; then
  echo "[1/4] Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
else
  echo "[1/4] uv already installed."
fi

echo "[2/4] Ensuring Python 3.12..."
uv python install 3.12

echo "[3/4] Syncing dependencies from pyproject.toml..."
uv sync

[ -f .env ] || cp .env.example .env

echo "[4/4] Seeding the knowledge base..."
uv run python seed.py

echo
echo "==========================================="
echo "  Setup complete. Launching app..."
echo "  Open http://127.0.0.1:5000"
echo "==========================================="
uv run python public/index.py
