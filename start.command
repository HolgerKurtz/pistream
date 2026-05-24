#!/bin/bash
cd "$(dirname "$0")"

if ! command -v uv &> /dev/null; then
    echo ""
    echo "Bird Tracker requires 'uv' (Python package manager)."
    echo "Install it by running this in Terminal:"
    echo ""
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo ""
    read -rp "Press Enter to close..."
    exit 1
fi

echo "Starting Bird Tracker — browser will open automatically..."
echo "Press Ctrl+C to stop."
echo ""
uv run python3 main.py
