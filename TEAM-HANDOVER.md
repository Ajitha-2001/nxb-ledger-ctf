# NXB Ledger CTF v4 — Team Handover

Six-stage forensic-investigation CTF (OSINT → decoding → BOLA →
forensics → log analysis → reconstruction). Red/black hacker theme.

## Deploy from zero
1. Clone, `cd nxb-ledger-ctf`
2. `docker compose up -d --build` (needs Docker + Compose)
3. For players on other machines: set `HOST_IP` in `.env` to this
   VM's LAN IP (default `127.0.0.1` = this machine only), then
   `docker compose up -d` again
4. Open `http://<HOST_IP>:8000/setup`, finish the CTFd wizard
5. Admin → your username → Settings → generate API token, then:
   `python3 ctfd-setup/import_challenges.py --url http://<HOST_IP>:8000 --token <TOKEN>`
   `python3 ctfd-setup/apply_theme.py --url http://<HOST_IP>:8000 --token <TOKEN>`
6. Add the six flags (type **Static**) from
   `evidence-generation/output/secrets/flags.json`:
   Admin → Challenges → each stage → Flags tab (confirm the row appears)
7. Replace any `192.168.56.10` URLs in challenge descriptions with
   your `HOST_IP`

## Services (on HOST_IP)
- `:8000` CTFd — game, submissions, scoreboard
- `:8080` Loan portal — Stage 3 BOLA (login: `br03_officer` / `Training#2026`)
- `:8081` Broker classifieds — Stage 1 OSINT ads
- `:8082` Evidence checker — Stages 1/4/5/6 (browser forms included)

## Organizers only (never players)
- Answer key: `evidence-generation/output/secrets/flags.json`
- Stage 3 flag is also in `.env` as `STAGE3_FLAG` (required by the portal)

## Notes
- Stages 2–6 are visible-but-locked until the previous stage is solved.
  Always test with a normal player account, not admin.
- This tree includes the checker browser-form patch
  (`evidence-checker/app.py`).
