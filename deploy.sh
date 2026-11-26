#!/usr/bin/env bash
# Update the bot from git and restart only this service.
set -euo pipefail

cd "$(dirname "$0")"
git pull --ff-only
.venv/bin/pip install -r requirements.txt
sudo systemctl restart steam-guard-bot
sleep 2
sudo systemctl status steam-guard-bot --no-pager -l || true
echo "--- last 20 journal lines ---"
sudo journalctl -u steam-guard-bot -n 20 --no-pager
