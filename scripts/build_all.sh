#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== 1/4: Generating canonical evidence (existing flags are PRESERVED; use --new-flags only for a full reset) =="
python3 -m venv /tmp/nxb-venv 2>/dev/null || true
if [ -f /tmp/nxb-venv/bin/activate ]; then source /tmp/nxb-venv/bin/activate; fi
pip install --quiet pillow >/dev/null 2>&1 || true
python3 evidence-generation/generate_evidence.py

echo "== 2/4: Building broker site HTML =="
python3 broker-site/build_site.py

echo "== 3/4: Writing .env (delete .env first to regenerate secrets) =="
python3 scripts/generate_env.py

echo "== 4/4: Building and starting containers =="
docker compose build
docker compose up -d

echo ""
echo "Stack is starting. Services (once healthy):"
echo "  CTFd              http://\${HOST_IP:-192.168.56.10}:8000"
echo "  Loan portal       http://\${HOST_IP:-192.168.56.10}:8080"
echo "  Broker site       http://\${HOST_IP:-192.168.56.10}:8081"
echo "  Evidence checker  http://\${HOST_IP:-192.168.56.10}:8082/healthz"
echo ""
echo "Next steps:"
echo "  1. Open CTFd, complete the setup wizard, create an admin account."
echo "  2. Generate an API token: Admin Panel -> Settings -> Access Tokens."
echo "  3. Run: python3 ctfd-setup/import_challenges.py --url http://<HOST_IP>:8000 --token <TOKEN>"
