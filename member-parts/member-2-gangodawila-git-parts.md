# Member 2 — Gangodawila (IT24100020): Challenge Design A (Stages 1, 3, 5) — Git Parts

*One member, one file. No shared files. Every project file is assigned to exactly one member.*

## Files owned by Member 2

| File | What it is |
|---|---|
| `broker-site/build_site.py` | Generates the static broker site from the ad source data |
| `broker-site/html/` | Built site: ad pages (PUB-011…017), broker profiles (BRK04…30), landing page, theme assets |
| `broker-site/Dockerfile`, `broker-site/nginx.conf` | nginx-unprivileged container config |
| `loan-portal/app.py` | Flask portal with the intentional BOLA vulnerability (role checked, ownership not checked) |
| `loan-portal/seed_db.py` | Seeds SQLite: one BR03 test account, twelve synthetic applications across branches |
| `loan-portal/templates/`, `loan-portal/static/` | Login/dashboard/application pages and theme assets |
| `loan-portal/Dockerfile`, `loan-portal/requirements.txt` | Container build (Python 3.12 + Flask + Gunicorn, non-root) |
| `evidence-generation/output/stage1/` | Stage 1 evidence bundle |
| `evidence-generation/output/stage5/` | Stage 5 CSV bundle (auth, app_access, workstation_sessions, leave, alert note) |

## Git commands (run from the repo root)

```bash
git add broker-site/ loan-portal/ evidence-generation/output/stage1/ evidence-generation/output/stage5/
git commit -m "Member 2 (Gangodawila): stages 1, 3, 5 - broker site, loan portal, stage evidence"
```

## Notes vs the Member Parts PDF
- Unchanged in substance — the PDF's Member 2 allocation was already correct.
- `loan-portal/loan_portal.db` is gitignored (runtime artifact) — correctly not committed.
- Stage 1/5 sections of `generate_evidence.py` are Member 2's conceptually, but the file itself is committed under Member 1 (single-owner rule).
