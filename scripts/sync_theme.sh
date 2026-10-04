#!/usr/bin/env bash
# Copy the shared theme (theme/) into the loan portal and the broker site.
# Run this after editing theme/nxb-theme.css or theme/nxb-fx.js, then rebuild the services.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p loan-portal/static broker-site/html/assets
cp theme/nxb-theme.css theme/nxb-fx.js loan-portal/static/
cp theme/nxb-theme.css theme/nxb-fx.js broker-site/html/assets/
echo "[+] Theme synced to loan-portal/static and broker-site/html/assets"
