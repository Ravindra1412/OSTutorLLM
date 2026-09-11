#!/usr/bin/env bash
# =============================================================================
# scripts/setup_ubuntu.sh — Part 3.12, Section 3 (Local Ubuntu Linux deployment)
#
# One-shot setup for a fresh Ubuntu machine. Idempotent where practical
# (safe to re-run) — `flask db upgrade` no-ops if already at head,
# venv creation is skipped if the directory already exists.
# =============================================================================
set -e

echo "== OSTutorLLM — Ubuntu Setup =="

if ! command -v python3 &> /dev/null; then
    echo "python3 not found. Installing..."
    sudo apt update && sudo apt install -y python3 python3-venv python3-pip
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Using Python $PYTHON_VERSION"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate

echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/change-this-to-a-long-random-value/${SECRET}/" .env
    echo "Generated a real SECRET_KEY in .env."
fi

echo "Running database migrations..."
export FLASK_APP=run.py
flask db upgrade

read -p "Seed sample data (topics, lessons, demo users)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    flask seed-db
fi

echo ""
echo "== Setup complete =="
echo "Start the server with:"
echo "  source venv/bin/activate && python run.py"
echo "Then open http://localhost:5000"
