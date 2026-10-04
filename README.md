# The NXB Ledger - CTF Play Box (Reference Implementation)

This is a working implementation of the design in CTF Play Box.

It builds exactly what that report specifies:

- CTFd control layer
- Docker-hosted challenge services (loan portal, broker site, evidence checker)
- Six progressive stages across OSINT, Encoding/Scripting, Web Security,
  Digital Forensics, Log Analysis, and Programming/Scripting
- Host-only network isolation, non-root containers, no privileged mounts
- Synthetic data only - no real bank systems, no real customer data

**This is your demo build.** Everything below has been unit-tested
component-by-component (evidence generation, the BOLA vulnerability, the
evidence checker's validation logic, and the Stage 6 dataset's solvability
under row-shuffling) but has **not** been run end-to-end inside Docker/CTFd
in this environment, since that requires your VM's Docker daemon and a
network connection this sandbox doesn't have. Follow the steps below on your
Ubuntu Server VM and run `scripts/smoke_test.py` to confirm the live stack.

---

## 1. What's in this project

```
nxb-ledger-ctf/
├── docker-compose.yml            # CTFd + MariaDB + Redis + 3 challenge services
├── evidence-generation/
│   └── generate_evidence.py      # ONE canonical seed -> all evidence for all 6 stages
├── loan-portal/                  # Stage 3: intentionally vulnerable Flask app (BOLA)
├── broker-site/                  # Stage 1: static broker classifieds site (nginx)
├── evidence-checker/             # Stages 1,4,5,6: structured-answer validation API
├── ctfd-setup/
│   └── import_challenges.py      # Creates all 6 CTFd challenges via the API
├── scripts/
│   ├── build_all.sh               # generate evidence -> build site -> .env -> docker compose up
│   ├── generate_env.py
│   ├── smoke_test.py              # end-to-end test against a live deployment
│   └── reset.sh                   # rebuild challenge services without touching CTFd scores
└── tests/reference_solutions/     # facilitator-only solve scripts (NOT for participants)
```

## 2. How the design maps to what's built

| Design report item | Implementation |
|---|---|
| CTFd control layer | `ctfd` service, MariaDB + Redis backend on an internal-only network |
| Loan portal (8080) | `loan-portal/` - Flask + SQLite, seeded with 12 synthetic applications |
| Broker site (8081) | `broker-site/` - static HTML generated from `broker_ads_source.json`, served by nginx |
| Evidence checker (8082) | `evidence-checker/` - Flask API, bounded JSON, strict field validation, rate limiting |
| Host-only network 192.168.56.0/24 | `HOST_IP` in `.env`, bind all published ports to that IP only |
| No published DB/cache ports | `db` and `cache` are on `backend_net` (marked `internal: true`), no `ports:` entries |
| Synthetic identifiers (EMP042, APP-0842, etc.) | `evidence-generation/generate_evidence.py` - `SEED` dict, matches the report exactly |
| Random 128-bit flag tokens | Generated fresh per build in `flags.json`, never hardcoded |
| Flag never in source/client JS | Stage 1/4/5/6 flags live only in `evidence-checker`'s mounted secret; Stage 2/3 flags are rendered server-side only after the task is actually solved |
| Immutable evidence masters + reset | `scripts/reset.sh` rebuilds challenge containers from the generator's output without touching CTFd's DB |

## 3. One-time build (on your Ubuntu Server 24.04 VM)

Prerequisites: Docker Engine + Docker Compose plugin, Python 3.10+, the
host-only adapter configured at `192.168.56.10` (or edit `HOST_IP` in `.env`
after step 1 to match your VM's actual host-only IP).

```bash
git clone <this project> nxb-ledger-ctf   # or copy the folder onto the VM
cd nxb-ledger-ctf
pip install --break-system-packages pillow    # only needed to run the generator once
chmod +x scripts/*.sh
./scripts/build_all.sh
```

This will:
1. Generate all synthetic evidence + fresh random flags (`evidence-generation/output/`)
2. Build the static broker site HTML
3. Write `.env` with fresh random DB/session secrets and the Stage 3 flag
4. `docker compose build` and `docker compose up -d`

## 4. Configure CTFd and import the challenges

1. Open `http://192.168.56.10:8000`, complete the CTFd setup wizard, create
   an admin account, name the CTF "The NXB Ledger".
2. Admin Panel -> Settings -> Access Tokens -> generate a token.
3. Run:
   ```bash
   python3 ctfd-setup/import_challenges.py --url http://192.168.56.10:8000 --token <TOKEN>
   ```
   This creates all six challenges with their descriptions, flags, hints and
   file attachments, and sets prerequisites so Stage *N+1* stays hidden until
   Stage *N* is solved (matches Section 4.3 of the design report).

## 5. Verify the build

```bash
python3 scripts/smoke_test.py --host 192.168.56.10
```

This exercises the intended solve path for every stage against the live
services (broker site reachability, the Stage 3 BOLA exploit, all four
evidence-checker endpoints, and basic robustness checks like rejecting
malformed/oversized JSON) - a scripted version of tests T01-T10 from the
report's Testing and Acceptance Plan (Section 15).

For Stage 6 specifically, `tests/reference_solutions/solve_stage6.py` is a
facilitator-only reference implementation of `correlate.py`, used to confirm
the dataset is solvable and reproducible even when `messages.jsonl` rows are
shuffled (T09) - **do not give this script to participants.**

## 6. Resetting between rehearsals or cohorts

```bash
./scripts/reset.sh
```

Rebuilds the loan portal, broker site and evidence checker from the
generator's immutable evidence masters, without touching CTFd's database -
so scores and progress are preserved (matches the report's "Reset boundary"
in Section 13).

To fully reset (new flags, new random secrets, wipe CTFd too):
```bash
docker compose down -v
rm .env
rm -rf evidence-generation/output
./scripts/build_all.sh
# re-run ctfd-setup/import_challenges.py after the wizard
```

## 7. Safety / isolation checklist before opening to participants

- [ ] `.env`'s `HOST_IP` matches your VM's actual host-only adapter, **not** a NAT/public IP
- [ ] Temporary NAT adapter (used only to `docker compose build`) is removed/disabled
- [ ] `docker compose ps` shows `db` and `cache` with **no** host port mappings
- [ ] Only ports 8000/8080/8081/8082 are reachable from a participant machine
- [ ] `evidence-generation/output/secrets/` and `.env` are **not** copied into any
      participant-facing archive or committed to a shared repo
- [ ] `docker compose config` shows no `privileged: true`, no Docker socket
      mounts, no `network_mode: host` anywhere

## 8. Known limitations of this reference build (be upfront about these in your report)

- The evidence-checker's `feature1`/`feature2` fields for Stage 1 are checked
  only for non-emptiness, not semantic correctness - full free-text grading
  isn't attempted; note this as a manual-review component in your report if
  your marker expects it.
- Stage 3's flag is revealed for *any* successful cross-branch view of
  `APP-0842` specifically (matching the design's single seeded target); it
  does not try to detect every possible cross-branch ID a participant might
  guess, since the report states brute-forcing isn't required.
- This build has not yet been through your own T01-T14 rehearsal or a
  beginner pilot - do that before treating it as "implemented," per the
  report's own guidance not to claim completed implementation prematurely.

---

## 9. Red/black "ops console" theme

All three web surfaces share one visual theme (black, red, scanlines, code-rain, glitch headings).
Everything is offline: no CDN, no web fonts.

| Surface | Where the theme lives | Apply changes |
|---|---|---|
| Broker site (Stage 1) | `broker-site/build_site.py` (layout/copy) + `theme/nxb-theme.css` | `./scripts/sync_theme.sh && python3 broker-site/build_site.py && docker compose up -d --build broker-site` |
| Loan portal (Stage 3) | `loan-portal/templates/*.html` + `loan-portal/static/` | `./scripts/sync_theme.sh && docker compose up -d --build loan-portal` |
| CTFd (Stages 1-6) | `theme/ctfd-theme.css` | `python3 ctfd-setup/apply_theme.py --url http://192.168.56.10:8000 --token <TOKEN>` |

Edit colours in `theme/nxb-theme.css` (variables at the top of the file), then run `scripts/sync_theme.sh`.
`apply_theme.py` only writes CTFd's Theme Header setting; it does not create challenges, so it is safe to re-run.
The theme is cosmetic only: the intentional BOLA flaw, flags, evidence and checker are unchanged.

---

## 10. Functional fixes in this version

| Issue | Fix |
|---|---|
| Stages 2-6 hidden with no later visibility update | Importer now creates every stage as `visible` and locks Stages 2-6 with prerequisites (`anonymize: true`). Test with a normal participant account; admins bypass prerequisites. |
| Re-runs generated new flags that no longer matched `.env`/CTFd | `generate_evidence.py` reuses `output/secrets/flags.json`; use `--new-flags` only for a full reset. `generate_env.py` now re-syncs `STAGE3_FLAG` in an existing `.env`. Evidence noise is seeded, so output is reproducible. |
| Broker container read-only filesystem | Uses `nginxinc/nginx-unprivileged` (non-root, port 8080 inside the container, host port still 8081) with `tmpfs: /tmp`. |
| Leave claim vs storyline | `leave.csv` now holds an EMP042 (Ruwan) leave entry; `alert_note.txt` says Ruwan points to the alert and claims leave. EMP019 only has the failed login. |
| 7 sessions with logout before login | Noise sessions use real datetime arithmetic (logout = login + 20 min). |
| Hint costs | Hints are 10 % / 20 % of the stage value (10/20, 20/40, 30/60, 40/80 points). Re-running the importer corrects existing hints. |
| Stage 4 manifest missing | `stage4/manifest_sha256.txt` is generated, recorded in `manifest.json` and attached to Stage 4. |
| Stage 6 reference solution | Rewritten: takes only the application ID and derives session, workstation, employee, message and transaction through joins; cross-checks directory vs session employee. Dataset now has decoy messages (CHAT-76/78) that carry the same application ID. |
| Importer duplicates | Re-runnable: existing challenges (matched by name) are synced, not duplicated; flags re-synced to `flags.json`. |
| CTFd theme overwrote Theme Header | `apply_theme.py` backs up the header and replaces only its own marked block. |

Run the offline checks any time: `python3 tests/check_evidence.py`.

### Applying these fixes to an already-running stack
```bash
python3 evidence-generation/generate_evidence.py      # keeps your flags, rewrites evidence
python3 broker-site/build_site.py && ./scripts/sync_theme.sh
python3 scripts/generate_env.py
docker compose up -d --build broker-site loan-portal evidence-checker
python3 ctfd-setup/import_challenges.py --url http://192.168.56.10:8000 --token <TOKEN>   # syncs, no duplicates
python3 ctfd-setup/apply_theme.py --url http://192.168.56.10:8000 --token <TOKEN>
```
Evidence files already attached in CTFd are not replaced by the importer (it only adds missing ones). The Stage 2/5/6
files changed (new leave record, decoys, fixed session times), so delete the old attachments on those three
challenges in the Admin Panel and re-run the importer, or the participants' downloads will not match the checker.

### Known report/design mismatches to correct in the Word report
- Capture event ID: the evidence uses `CAP-0312` everywhere (all other capture IDs are `CAP-0` + three digits, e.g. `CAP-0301`). The report's Stage 4 text and Section 14 table must read `CAP-0312`; a shortened `CAP-031` there is wrong. Search the Word file for `CAP-03` and fix every occurrence.
- Stage 5 and 6 evidence descriptions: mention the leave entry for EMP042 and the CHAT-76/78 decoys.
- Section 12 says "Nginx"; the broker container now uses nginx-unprivileged.

### Still unverified (needs your VM)
Docker build/run of the unprivileged nginx image, CTFd API field names for `anonymize`/hint PATCH on CTFd 3.7.4,
theme rendering in a browser, and T11-T14 (isolation, reset, concurrency, pilot).

---

## 11. Changes in v4

| Item | Change |
|---|---|
| Flag strength | New flags are `NXB{S0n_<32 hex chars>}` = 128 random bits (`secrets.token_hex(16)`). The shipped `flags.json` was regenerated with `--new-flags`, so **flags differ from v3**. Re-run `generate_env.py`, rebuild `loan-portal` and `evidence-checker`, then run the importer (it re-syncs flags in CTFd). A warning is printed if older short tokens are reused. |
| Replacing old attachments | `python3 ctfd-setup/import_challenges.py ... --replace-files` deletes and re-uploads the attachments of existing challenges. Use it after any evidence regeneration. |
| Manifest format | `manifest_sha256.txt` (Stages 2 and 4) is now `<hash>  <filename>`, so participants can run `sha256sum -c manifest_sha256.txt` in the folder with the files. |
| Stage 6 schema | `stage6/SCHEMA.md` (field tables + placeholder `evidence.json`, no answers) is generated and attached to Stage 6. |
| Resource limits | `mem_limit`, `cpus`, `pids_limit` per service in `docker-compose.yml` (RAM limits sum to about 4.25 GB). Tune after test T13. |
| Versions | `scripts/record_versions.sh` writes `versions.txt` (OS, Docker, Compose, image digests, pip freeze). Run it after the first successful deployment. |
| Checker rate limiting | Checker now runs gunicorn with 1 worker + 4 threads, so the in-memory cooldown is shared (before, 2 workers each had their own counters). |
| Smoke test | Paces itself around the 3 s cooldown (v3's test would have hit 429s), and adds distractor, wrong-field, decoy-message, oversized-body, rate-limit, flag-leak and closed-port checks. |

### Fresh deployment order
```bash
./scripts/build_all.sh
python3 tests/check_evidence.py
# CTFd setup wizard in the browser, then create an admin access token
python3 ctfd-setup/import_challenges.py --url http://192.168.56.10:8000 --token <TOKEN>     # add --replace-files on an existing CTFd
python3 ctfd-setup/apply_theme.py       --url http://192.168.56.10:8000 --token <TOKEN>
python3 scripts/smoke_test.py --host 192.168.56.10
./scripts/record_versions.sh
```

### Verified vs not verified
Verified offline in the build sandbox: `tests/check_evidence.py` (evidence, manifests via `sha256sum -c`, flag length, Stage 6
solver incl. shuffles) and Python/YAML syntax. **Not verified:** any Docker build/run, CTFd API behaviour, the live smoke test,
resource limits under load, and browser rendering.
