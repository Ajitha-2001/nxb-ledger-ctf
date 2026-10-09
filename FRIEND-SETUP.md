# NXB Ledger CTF — Setup Guide (for the teammate receiving this ZIP)

## What you get
- **CTFd** (`:8000`) — the main CTF platform, red/black hacker theme with code rain
- **Broker board** (`:8081`) — Stage 1 OSINT site
- **Loan portal** (`:8080`) — Stage 3 site
- **Evidence checker** (`:8082`) — submit Stage 1/4/5/6 answers, styled like the broker board

> **Keep this package private.** It contains all six flags and the answer keys.

## Setup (Ubuntu + Docker)

**1.** Extract the ZIP and enter it:
```bash
cd nxb-ledger-ctf
```

**2.** Start Docker (run `newgrp docker` on its own line first if your user was just added to the docker group):
```bash
newgrp docker
```
then:
```bash
docker compose up -d --build
docker compose ps
```

**3.** Open `http://127.0.0.1:8000`, complete the CTFd setup wizard and create your admin account.

**4.** In CTFd, go to **Admin Panel → Settings → Access Tokens** and generate a token. Copy it. (Each machine needs its own token — tokens don't transfer.)

**5.** Import the six challenges (needs Python `requests`: `pip install requests` if missing):
```bash
python3 ctfd-setup/import_challenges.py --url http://127.0.0.1:8000 --token PASTE_YOUR_TOKEN_HERE
```

**6.** Apply the hacker theme — **this step is what makes CTFd look like the screenshots; without it CTFd looks plain**:
```bash
python3 ctfd-setup/apply_theme.py --url http://127.0.0.1:8000 --token PASTE_YOUR_TOKEN_HERE
```

**7.** Hard-refresh CTFd (`Ctrl+Shift+R`). Done — you should see the NXB LEDGER banner, red stage cards, and falling code rain.

## Notes
- The broker board, loan portal, and evidence checker are styled automatically — no extra step.
- Stages 2–6 stay locked until the previous stage is solved. Use a normal participant account to test progression (admins bypass locks).
- Do **not** "fix" the loan portal's missing authorization check — the Stage 3 BOLA is the intended vulnerability.
- Do **not** re-run the evidence generator — flags and answer keys are already generated and matched in this package.
- If a port is already in use on your machine, check `HOST_IP` in `.env`.
