#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "This restores challenge-service state (loan portal + evidence checker + broker site)"
echo "WITHOUT touching CTFd's database (scores/progress are preserved)."
read -p "Continue? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Aborted."
  exit 0
fi

docker compose stop loan-portal broker-site evidence-checker
docker compose build loan-portal broker-site evidence-checker
docker compose up -d loan-portal broker-site evidence-checker

echo "[+] Challenge services rebuilt and restarted from the immutable evidence masters."
echo "    Re-verify evidence hashes against evidence-generation/output/manifest.json if needed."
