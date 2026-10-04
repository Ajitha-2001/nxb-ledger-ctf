#!/usr/bin/env bash
# Records the exact software versions and image digests of a working deployment into versions.txt
# (design report section 12). Run on the VM after `docker compose up -d` and keep the file with your test evidence.
set -uo pipefail
cd "$(dirname "$0")/.."
{
  echo "# NXB Ledger - recorded versions  ($(date -Is))"
  echo "## OS";            . /etc/os-release; echo "$PRETTY_NAME"; uname -mr
  echo "## Docker";        docker --version; docker compose version
  echo "## Python (host)"; python3 --version
  echo "## Compose images (tag -> digest)"
  docker compose config --images | sort -u | while read -r img; do
    echo "$img  $(docker image inspect --format '{{index .RepoDigests 0}}' "$img" 2>/dev/null || echo 'local build (no registry digest)')"
  done
  echo "## Python packages inside services"
  for svc in loan-portal evidence-checker; do
    echo "### $svc"; docker compose exec -T "$svc" pip freeze 2>/dev/null || echo "(service not running)"
  done
  echo "## Evidence"; echo "seed version: 20260810"; sha256sum evidence-generation/output/manifest.json
  echo "## CTFd"; grep -n "image: ctfd" docker-compose.yml
} | tee versions.txt
echo "[+] Wrote versions.txt"
